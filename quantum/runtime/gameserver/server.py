"""`quantum gameserver run`: a world on a WebSocket, a tick at a time.

The protocol is JSON, a message a frame, and small enough to write down here:

    client: {"type": "hello", "name": "ana"}                         a guest world's player
            {"type": "hello", "ticket": "eyJh...Q.5f..."}             a site's account (accounts="site"): tickets.py
            {"type": "hello", "control": true}                        a test world's (--step) harness: no entity
            {"type": "cmd", "seq": 3, "name": "step", "args": {"dir": "north"}}
            {"type": "ping", "t": 12.5}
            {"type": "sync"}                                          answered once every frame before it is sent
            {"type": "step", "ticks": 5}                              a test world only (--step)
            {"type": "peek"}                                          a control connection: the whole world
    server: {"type": "greeting", "world": "yard", "rate": 10, "step": false}    at once: the join waits for a tick
            {"type": "welcome", "you": "hero:ana", "tick": 41, "rate": 10, "world": "yard", "client": "...",
             "map": "...", "views": ["around"]}
            {"type": "tick", "tick": 42, "ack": [3], "refused": [{"seq": 4, "name": "step", "reason": "Blocked."}],
             "views": {"around": {"enter": [{...}], "update": [{"id": "hero:bo", "at": {...}}], "leave": ["hero:cy"]}},
             "events": [{"name": "hit", "value": 3, "at": {"x": 4, "y": 2}, "of": "rat-2"}]}
            {"type": "pong", "t": 12.5, "tick": 42} · {"type": "synced", "tick": 42} · {"type": "stepped", "tick": 47}
            {"type": "peeked", "tick": 47, "entities": {...}, "vars": {...}, "players": {...}, "errors": [...],
             "connected": {"ana": 3}}                                 who is connected, and the seq it sent last
            {"type": "error", "reason": "..."}                        and the connection closes

A tick frame goes to a player only when it has something for them: what of each view (q:view) changed for them,
and the events (q:emit) where they see (in a test world, every tick: a harness knows its clients heard it). A view's entities are the public fields, and its player's own entity's
private ones too; an update holds only the fields that changed. A test world (--step) does not tick by itself: it
waits for a "step", so a test is exact and as fast as the machine.

In a world of a site's accounts a hello is a ticket, and one comes in once. An account that signs in again while its
connection is still open takes its hero over: the old connection is told so and closed, and the hero stays where it
is, in its party, with its trade. The world never sees a password: the site signs the ticket (tickets.py), with the
secret the two share in their environments (QUANTUM_WORLD_SECRET).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import signal
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from quantum.runtime.gameserver import tickets
from quantum.runtime.gameserver.errors import GameServerError
from quantum.runtime.gameserver.frames import Frames
from quantum.runtime.gameserver.log import WorldLog, replay
from quantum.runtime.gameserver.npc import FALLBACK, answer_of
from quantum.runtime.gameserver.model import WorldDef
from quantum.runtime.gameserver.world import TickOut, World

_NAME = re.compile(r'^[A-Za-z0-9_-]{1,24}$')
MAX_MESSAGE = 16 * 1024
MESSAGES_A_SECOND = 60
HEARTBEAT_SECONDS = 10


UNLIMITED = ('step', 'sync', 'peek')        # a test world's harness says these as fast as it runs


@dataclass
class Connection:
    ws: Any
    account: Optional[str]                                   # None: a control connection
    joined: bool = False
    views: Dict[str, Set[str]] = field(default_factory=dict)  # what the player has of each view, by id
    window: List[float] = field(default_factory=list)
    sent_bytes: int = 0
    last_seq: int = 0                                        # the seq of the last command it sent


def _memory_mb() -> float:
    """What the process holds at most, in MB (0 where the machine does not say)."""
    try:
        import resource
    except ImportError:                      # not Unix
        return 0.0
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return round(peak / (1024 * 1024 if sys.platform == 'darwin' else 1024), 1)   # bytes on a Mac, KB on Linux


class WorldServer:
    def __init__(self, definition: WorldDef, *, host: str = '127.0.0.1', port: int = 7700, step: bool = False,
                 data_dir: Optional[Path] = None, snapshot_every: float = 300.0, quiet: bool = False,
                 stats: float = 0.0, secret: Optional[bytes] = None, mind: Optional[Any] = None,
                 mind_seconds: float = 20.0, digest_every: float = 0.0):
        self.definition = definition
        self.digest_ticks = max(1, round(digest_every * definition.tick_rate)) if digest_every else 0
        self.mind = mind                                    # the NPCs' (npc.py): a function of a question
        self.mind_seconds = mind_seconds                    # longer, and the NPC says a line of its fallback
        self._minds_pool = None
        self._thinking: Set[asyncio.Task] = set()
        self.secret = secret if secret is not None else tickets.secret_from_env()
        if definition.accounts == 'site' and not self.secret:
            raise GameServerError(f'{definition.name}: accounts="site" signs its tickets with {tickets.SECRET_ENV}, '
                                  'and the environment has none (16 characters or more)')
        self.used: Dict[str, int] = {}                      # the tickets that came in, till they end
        self.host, self.port = host, port
        self.step_mode = step
        self.data_dir = Path(data_dir) if data_dir else Path('.quantum') / 'gameserver' / definition.name
        self.snapshot_ticks = max(1, round(snapshot_every * definition.tick_rate))
        self.quiet = quiet
        self.world: Optional[World] = None
        self.log: Optional[WorldLog] = None
        self.connections: Dict[str, Connection] = {}
        self.controls: List[Connection] = []
        self.inbox: List[tuple] = []
        self.welcoming: Set[str] = set()                    # accounts that took their hero over: welcomed next tick
        self.frames = Frames(definition)                    # what each player is told of each tick
        self.bytes_out = 0
        self.replayed: List[str] = []
        self.ready = threading.Event()
        self._lock: Optional[asyncio.Lock] = None
        self._stop: Optional[asyncio.Event] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._last_snapshot = 0
        self._crashed = False
        self.tick_seconds: List[float] = []                 # the last ticks' time, for the numbers of the plan
        self.stats_ticks = max(1, round(stats * definition.tick_rate)) if stats else 0
        self._stats_mark: tuple = (time.monotonic(), 0, {})
        self._interval: List[float] = []                    # the ticks' time since the numbers were last said

    def say(self, text: str) -> None:
        if not self.quiet:
            print(f'[gameserver] {text}', flush=True)

    @property
    def url(self) -> str:
        return f'ws://{self.host}:{self.port}'

    # -- the world, from its log -----------------------------------------------------------------------------

    def _restore(self) -> None:
        self.log = WorldLog(self.data_dir)
        snap, entries = self.log.load()
        self.world = World.from_snapshot(self.definition, snap) if snap else World(self.definition)
        start = self.world.tick
        self.replayed = replay(self.world, entries)
        for line in self.replayed:
            self.say(f'replay: {line}')
        self.log.open(snap['tick'] if snap else 0)
        self._last_snapshot = snap['tick'] if snap else 0
        if self.world.players:                 # they were in when it stopped: they are not now
            out = self.world.step([('leave', a) for a in sorted(self.world.players)])
            self.log.append(out.entries)
            self.log.flush()
        self.world.dirty.clear()
        self.world.gone.clear()
        if entries or snap:
            self.say(f'{self.definition.name}: back at tick {self.world.tick} (snapshot {start}, '
                     f'{len(entries)} entries again)')

    # -- a tick ------------------------------------------------------------------------------------------------

    async def _tick(self) -> None:
        began = time.perf_counter()
        inputs, self.inbox = self.inbox, []
        out = self.world.step(inputs)
        for ask in out.asks:
            self._think(ask)
        self.log.append(out.entries)
        if self.world.tick % (HEARTBEAT_SECONDS * self.definition.tick_rate) == 0:
            self.log.append([{'t': self.world.tick, 'k': 'tick'}])
        if self.digest_ticks and self.world.tick % self.digest_ticks == 0:
            self.log.append([{'t': self.world.tick, 'k': 'digest', 'd': self.world.digest()}])
        self.log.flush()                       # on the disk before anyone is told it ran
        if self.world.tick - self._last_snapshot >= self.snapshot_ticks:
            self.log.write_snapshot(self.world)
            self._last_snapshot = self.world.tick
        await self._send(out)
        self.world.dirty.clear()
        self.world.gone.clear()
        self.tick_seconds.append(time.perf_counter() - began)
        del self.tick_seconds[:-600]
        if self.stats_ticks:
            self._interval.append(self.tick_seconds[-1])
        if self.stats_ticks and self.world.tick % self.stats_ticks == 0:
            print(f'[gameserver] stats {json.dumps(self.stats())}', flush=True)

    def _think(self, ask: dict) -> None:
        """An NPC asked: its mind answers off the tick, and the answer is an input of a tick to come."""
        if self.mind is None:
            self.inbox.append(('npc', ask['account'], ask['npc'], dict(FALLBACK)))
            return
        task = asyncio.get_running_loop().create_task(self._mind(ask))
        self._thinking.add(task)
        task.add_done_callback(self._thinking.discard)

    async def _mind(self, ask: dict) -> None:
        from concurrent.futures import ThreadPoolExecutor
        if self._minds_pool is None:
            self._minds_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix='mind')
        try:
            answer = await asyncio.wait_for(asyncio.get_running_loop().run_in_executor(
                self._minds_pool, self.mind, ask), self.mind_seconds)
            answer = answer_of(answer)
        except Exception:  # noqa: BLE001 - a mind that fails or is too slow: the NPC says its lines
            answer = dict(FALLBACK)
        self.inbox.append(('npc', ask['account'], ask['npc'], answer))

    def stats(self) -> dict:
        """The numbers since the last time they were asked: the ticks' time, and what went out, to each player."""
        now = time.monotonic()
        since, out_before, sent_before = self._stats_mark
        seconds = max(1e-6, now - since)
        ticks = sorted(self._interval or self.tick_seconds)
        rates = sorted((c.sent_bytes - sent_before.get(a, 0)) / seconds / 1000
                       for a, c in self.connections.items() if a in sent_before)
        self._stats_mark = (now, self.bytes_out, {a: c.sent_bytes for a, c in self.connections.items()})
        self._interval = []

        def at(values, q):
            return values[min(len(values) - 1, int(q * len(values)))] if values else 0.0
        return {'tick': self.world.tick, 'players': len(self.world.players),
                'entities': len(self.world.entities),
                'beasts': sum(1 for e in self.world.entities.values() if e.get('_player') is None),
                'memory_mb': _memory_mb(),
                'tick_ms_p50': round(at(ticks, 0.5) * 1000, 2), 'tick_ms_p99': round(at(ticks, 0.99) * 1000, 2),
                'tick_ms_max': round((ticks[-1] if ticks else 0) * 1000, 2),
                'out_kb_s': round((self.bytes_out - out_before) / seconds / 1000, 2),
                'player_kb_s_p50': round(at(rates, 0.5), 3), 'player_kb_s_max': round(rates[-1] if rates else 0, 3)}

    async def _send(self, out: TickOut) -> None:
        """The tick's frames (frames.py) to each player: who found the world full is told and let go."""
        for account, conn in list(self.connections.items()):
            if account in out.full:
                await self._close(conn, 'The world is full.')
        seen = {a: c for a, c in self.connections.items() if a not in out.full}
        messages = self.frames.tick(self.world, out, seen, self.welcoming, every_tick=self.step_mode)
        self.welcoming.clear()
        for account, said in messages.items():
            conn = self.connections.get(account)
            for message in said:
                if conn is not None:
                    await self._send_to(conn, message)

    async def _send_to(self, conn: Connection, message: dict) -> None:
        data = json.dumps(message, separators=(',', ':'))
        conn.sent_bytes += len(data)
        self.bytes_out += len(data)
        try:
            await conn.ws.send(data)
        except Exception:  # noqa: BLE001 - a closed connection: its reader takes it out
            pass

    async def _close(self, conn: Connection, reason: str) -> None:
        """The connection told why and closed; its player leaves the world (if it came in, or is coming)."""
        await self._send_to(conn, {'type': 'error', 'reason': reason})
        try:
            await conn.ws.close()
        except Exception:  # noqa: BLE001
            pass
        account = conn.account
        if account is not None and self.connections.get(account) is conn:
            del self.connections[account]
            if account in self.world.players or any(i[0] == 'join' and i[1] == account for i in self.inbox):
                self.inbox.append(('leave', account))

    # -- a connection ------------------------------------------------------------------------------------------

    async def _handler(self, ws) -> None:
        conn: Optional[Connection] = None
        try:
            async for raw in ws:
                try:
                    message = json.loads(raw)
                    kind = message.get('type') if isinstance(message, dict) else None
                except (ValueError, TypeError):
                    kind, message = None, None
                if kind is None:
                    await self._refuse(ws, 'A message is a JSON object with a type.')
                    return
                if conn is not None and not (self.step_mode and kind in UNLIMITED):
                    now = time.monotonic()
                    conn.window = [t for t in conn.window if t > now - 1] + [now]
                    if len(conn.window) > MESSAGES_A_SECOND:
                        await self._close(conn, f'More than {MESSAGES_A_SECOND} messages a second.')
                        return
                if conn is None:
                    if kind != 'hello':
                        await self._refuse(ws, 'Say hello first.')
                        return
                    if message.get('control'):
                        if not self.step_mode:
                            await self._refuse(ws, 'A control connection is a test world\'s (--step).')
                            return
                        conn = Connection(ws, None)
                        self.controls.append(conn)
                        await self._send_to(conn, {'type': 'greeting', 'world': self.definition.name,
                                                   'rate': self.definition.tick_rate, 'step': True,
                                                   'control': True, 'views': list(self.definition.views)})
                        continue
                    who = self._who(message)
                    if isinstance(who, str):
                        await self._refuse(ws, who)
                        return
                    account, name = who
                    conn = Connection(ws, account)
                    old = self.connections.get(account)
                    self.connections[account] = conn
                    if old is not None:                 # a site's account, signed in again: it takes its hero
                        if old.joined:
                            self.welcoming.add(account)
                        await self._close(old, 'You signed in somewhere else.')
                    elif account not in self.world.players or ('leave', account) in self.inbox:
                        self.inbox.append(('join', account, name))
                    else:                               # in the world with no connection: its hero, as it is
                        self.welcoming.add(account)
                    await self._send_to(conn, {'type': 'greeting', 'world': self.definition.name,
                                               'rate': self.definition.tick_rate, 'step': self.step_mode})
                elif kind == 'cmd' and conn.account is None:
                    await self._close(conn, 'A control connection has no entity: it sends no commands.')
                    return
                elif kind == 'peek' and conn.account is None:
                    async with self._lock:
                        await self._send_to(conn, self._peek())
                elif kind == 'cmd':
                    seq, name, args = message.get('seq'), message.get('name'), message.get('args', {})
                    if not isinstance(seq, int) or not isinstance(name, str):
                        await self._close(conn, 'A command has an integer seq and a name.')
                        return
                    self.inbox.append(('cmd', conn.account, seq, name, args))
                    conn.last_seq = seq
                elif kind == 'ping':
                    await self._send_to(conn, {'type': 'pong', 't': message.get('t'), 'tick': self.world.tick})
                elif kind == 'sync':
                    async with self._lock:
                        await self._send_to(conn, {'type': 'synced', 'tick': self.world.tick})
                elif kind == 'step':
                    if not self.step_mode:
                        await self._close(conn, 'This world keeps its own time (no --step).')
                        return
                    ticks = message.get('ticks', 1)
                    if not isinstance(ticks, int) or not 0 <= ticks <= 100_000:
                        await self._close(conn, 'step: ticks is a number from 0 to 100000.')
                        return
                    async with self._lock:
                        for _ in range(ticks):
                            await self._tick()
                        await self._send_to(conn, {'type': 'stepped', 'tick': self.world.tick})
                else:
                    await self._close(conn, f'There is no message of type {kind!r}.')
                    return
        except Exception:  # noqa: BLE001 - the connection broke: the player leaves
            pass
        finally:
            if conn is not None and conn.account is None:
                if conn in self.controls:
                    self.controls.remove(conn)
            elif conn is not None and self.connections.get(conn.account) is conn:
                del self.connections[conn.account]
                self.inbox.append(('leave', conn.account))

    def _who(self, message: dict):
        """(account, name) of a hello, or why it may not come in."""
        if self.definition.accounts == 'site':
            if 'ticket' not in message:
                return 'The players of this world sign in: a hello has a ticket of the site, not a name.'
            try:
                ticket = tickets.verify(message['ticket'], self.secret)
            except tickets.TicketError as e:
                return str(e)
            now = time.time()
            self.used = {t: end for t, end in self.used.items() if end >= now}
            signature = message['ticket'].rsplit('.', 1)[1]
            if signature in self.used:
                return 'The ticket was used already: sign in again.'
            self.used[signature] = ticket.ends
            return ticket.account, ticket.name
        name = message.get('name')
        if not isinstance(name, str) or not _NAME.match(name):
            return 'A name is 1 to 24 letters, digits, _ or -.'
        if name in self.connections or (name in self.world.players and ('leave', name) not in self.inbox):
            return f'{name} is in the world already.'
        return name, name

    def _peek(self) -> dict:
        """The god's view, for a test: every entity with all its fields but the world's own (_...)."""
        world = self.world
        entities = {eid: {k: v for k, v in e.items() if not k.startswith('_')} for eid, e in world.entities.items()}
        return {'type': 'peeked', 'tick': world.tick, 'entities': entities, 'vars': world.vars,
                'players': world.players, 'errors': world.errors[-20:],
                'connected': {a: c.last_seq for a, c in self.connections.items()}}

    async def _refuse(self, ws, reason: str) -> None:
        try:
            await ws.send(json.dumps({'type': 'error', 'reason': reason}))
            await ws.close()
        except Exception:  # noqa: BLE001
            pass

    # -- running -----------------------------------------------------------------------------------------------

    async def run(self) -> None:
        from websockets.asyncio.server import serve

        self._loop = asyncio.get_running_loop()
        self._lock = asyncio.Lock()
        self._stop = asyncio.Event()
        self._restore()
        try:
            async with serve(self._handler, self.host, self.port, max_size=MAX_MESSAGE) as server:
                self.port = server.sockets[0].getsockname()[1]
                self.say(f'{self.definition.name} on {self.url}' + (' (a test world: it ticks on "step")'
                                                                      if self.step_mode else
                                                                      f' at {self.definition.tick_rate} ticks a second'))
                self.ready.set()
                if self.step_mode:
                    await self._stop.wait()
                else:
                    await self._clock()
        finally:                                # stopped, or interrupted: the world as it is now, on the disk
            if self._minds_pool is not None:
                self._minds_pool.shutdown(wait=False, cancel_futures=True)
            if self._crashed:
                if self.log._file:
                    self.log._file.close()
            else:
                self.log.write_snapshot(self.world)
                self.log.close()

    async def _clock(self) -> None:
        period = 1.0 / self.definition.tick_rate
        loop = asyncio.get_running_loop()
        due = loop.time()
        while not self._stop.is_set():
            due += period
            delay = due - loop.time()
            if delay < -1.0:                   # a second behind: the world takes its time, not the lost ticks
                due = loop.time()
                delay = 0
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=max(0.0, delay))
                break
            except asyncio.TimeoutError:
                pass
            async with self._lock:
                await self._tick()

    def stop(self) -> None:
        """From any thread: the world writes its snapshot and the server ends."""
        if self._loop and self._stop:
            self._loop.call_soon_threadsafe(self._stop.set)

    def crash(self) -> None:
        """For a test: the server ends as if killed, with no snapshot: what is on the disk is the log."""
        self._crashed = True
        self.stop()


# -- the command line ------------------------------------------------------------------------------------------

def add_arguments(parser: argparse.ArgumentParser) -> None:
    sub = parser.add_subparsers(dest='gameserver_command')
    run = sub.add_parser('run', help='run a world (a q:application type="gameserver")')
    run.add_argument('file', help='the world\'s .q')
    run.add_argument('--host', default='127.0.0.1')
    run.add_argument('--port', type=int, default=7700)
    run.add_argument('--step', action='store_true', help='a test world: it ticks only when a client says "step"')
    run.add_argument('--data', help='where the world keeps its snapshot and log (.quantum/gameserver/<name>)')
    run.add_argument('--snapshot-every', type=float, default=300.0, metavar='SECONDS')
    run.add_argument('--stats', type=float, default=0.0, metavar='SECONDS',
                     help='say the numbers (the ticks\' time, what went out) every so often')
    run.add_argument('--no-minds', action='store_true',
                     help='the NPCs say the lines of their fallback, and no model is asked')
    run.add_argument('--digest-every', type=float, default=0.0, metavar='SECONDS',
                     help='write the world\'s digest into its log every so often, for `conform` to check a replay '
                          'against (a digest copies the whole world: a pause of its own)')
    conform = sub.add_parser('conform', help='run a world\'s log again on an engine, against the record or another '
                                             'engine, and say the first tick where they differ (PLAN_WORLD_ENGINE.md)')
    conform.add_argument('file', help='the world\'s .q')
    conform.add_argument('--data', help='its snapshot and log (.quantum/gameserver/<name>)')
    conform.add_argument('--engine', default='python', help='the engine to run it on (python)')
    conform.add_argument('--against', help='a second engine: the two compared tick by tick, frames and all')
    conform.add_argument('--digest-every', type=int, default=1, metavar='TICKS',
                         help='compare the two worlds\' digests every so many ticks (0: only at the end)')
    check = sub.add_parser('check', help='read a world against its schema, and say what is wrong')
    check.add_argument('file')
    ticket = sub.add_parser('ticket', help=f'a ticket into a world of a site\'s accounts (accounts="site"), '
                                           f'signed with {tickets.SECRET_ENV} from the environment')
    ticket.add_argument('--account', required=True, help='the site\'s id of the account (its hero: hero:<it>)')
    ticket.add_argument('--name', default='', help='the name its hero shows (else the account)')
    ticket.add_argument('--seconds', type=float, default=60.0, help='how long it lasts (a minute)')


def load(path: str) -> WorldDef:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.gameserver.model import read_world

    app = QuantumParser(use_cache=False).parse_file(path)
    if app.app_type != 'gameserver':
        raise SystemExit(f'{path}: a q:application type="gameserver" is a world; this one is type="{app.app_type}"')
    return read_world(app, path)


def main(args) -> int:
    command = getattr(args, 'gameserver_command', None)
    if command not in ('run', 'check', 'ticket', 'conform'):
        print('quantum gameserver run FILE | quantum gameserver check FILE | quantum gameserver ticket --account A | '
              'quantum gameserver conform FILE')
        return 2
    if command == 'conform':
        from quantum.runtime.gameserver.conform import main as conform_main
        return conform_main(args)
    if command == 'ticket':
        secret = tickets.secret_from_env()
        if not secret:
            print(f'[ERROR] {tickets.SECRET_ENV} is not in the environment (16 characters or more)', file=sys.stderr)
            return 1
        try:
            print(tickets.issue(args.account, args.name, secret, seconds=args.seconds))
        except tickets.TicketError as e:
            print(f'[ERROR] {e}', file=sys.stderr)
            return 1
        return 0
    try:
        definition = load(args.file)
    except GameServerError as e:
        print(f'[ERROR] {e}')
        return 1
    if command == 'check':
        print(f'[OK] {definition.name}: {len(definition.entities)} entities, {len(definition.commands)} commands, '
              f'{len(definition.every)} rules every so often, a map of {definition.map.width}x{definition.map.height}')
        return 0
    try:
        from quantum.runtime.gameserver.npc import LLMMind
        server = WorldServer(definition, host=args.host, port=args.port, step=args.step,
                             data_dir=Path(args.data) if args.data else None, snapshot_every=args.snapshot_every,
                             stats=args.stats, mind=None if args.no_minds or not definition.npcs else LLMMind(),
                             digest_every=args.digest_every)
    except GameServerError as e:
        print(f'[ERROR] {e}', file=sys.stderr)
        return 1
    return serve_forever(server)


def serve_forever(server: WorldServer) -> int:

    def stop(*_):
        server.stop()

    try:
        signal.signal(signal.SIGTERM, stop)
    except ValueError:                          # not the main thread
        pass
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        pass
    except OSError as e:
        print(f'[ERROR] {e}', file=sys.stderr)
        return 1
    return 0
