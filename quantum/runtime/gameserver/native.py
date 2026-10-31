"""The Rust engine (native/world, the module `quantum_world`; PLAN_WORLD_ENGINE.md), as the server and the
conformance harness use it.

E1: the world's tick is still world.py's `World.step`. After it the engine is handed what changed (the entities
changed, as they are now; those gone; the acks, the refusals, the events) and works out what each player is told,
frames.py's frames to the byte, a player per task on every core. In a server it also holds the sockets (net.rs):
it reads each message, checks its size, its rate and a command's seq and name, answers the pings, and writes each
player's frames, on threads of its own; what is the world's to decide (a hello and its ticket, "step", "sync",
"peek") it hands here, in the order it came.

A view whose where= is more than near(it, me, n) is read by the interpreter, here, for those views only (E2's
bytecode will read it in the engine); the engine works out what changed in it.

Built by maturin (`pip install ./native/world`). Without it, `available()` is false, and a world asked to run on
it runs on the Python engine, and says so.
"""

from __future__ import annotations

import asyncio
import json
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Set

from quantum.runtime.gameserver.frames import by_python, dirty_cells_of, view_members

try:
    import quantum_world
except ImportError:  # not built here: the Python engine runs the world
    quantum_world = None

ENGINE_ENV = 'QUANTUM_WORLD_ENGINE'
ENGINES = ('python', 'rust')
RULES_ENV = 'QUANTUM_WORLD_RULES'
RULES = ('python', 'machine')
BUILD = 'pip install ./native/world'


def available() -> bool:
    return quantum_world is not None


def engine_wanted(engine: Optional[str] = None) -> str:
    """The engine asked for (`--engine`, else QUANTUM_WORLD_ENGINE, else python)."""
    wanted = engine or os.environ.get(ENGINE_ENV) or 'python'
    if wanted not in ENGINES:
        raise ValueError(f'there is no engine {wanted!r}: the engines are {", ".join(ENGINES)}')
    return wanted


def world_class(rules: Optional[str] = None, quiet: bool = False):
    """The World a server runs (`--rules`, else QUANTUM_WORLD_RULES, else python): its rules on the interpreter
    (rules.py), or as bytecode on the engine's machine (machine.py, E2) when the engine is built here."""
    from quantum.runtime.gameserver.world import World
    wanted = rules or os.environ.get(RULES_ENV) or 'python'
    if wanted not in RULES:
        raise ValueError(f'there are no rules {wanted!r}: the rules run on {" or ".join(RULES)}')
    if wanted == 'machine':
        if available():
            from quantum.runtime.gameserver.machine import MachineWorld
            return MachineWorld
        if not quiet:
            print(f'[gameserver] the Rust engine is not built here ({BUILD}): the interpreter runs the rules',
                  flush=True)
    return World


class NativeFrames:
    """frames.py's Frames, worked out by the engine: the same messages, as JSON texts, for its seats (the players
    it tells; a server's connections)."""

    def __init__(self, world):
        definition = world.definition
        self.definition = definition
        self.python_views = [v for v in definition.views.values() if by_python(v)]
        views = [(v.name, None if by_python(v) else v.radius, by_python(v)) for v in definition.views.values()]
        welcome = json.dumps({'rate': definition.tick_rate, 'world': definition.name, 'client': definition.client,
                              'map': definition.map.path.name, 'views': list(definition.views)},
                             separators=(',', ':'))
        private = {kind: sorted(fields) for kind, fields in world._private.items()}
        self.engine = quantum_world.Engine(views, private, definition.reach, welcome[1:-1])
        self.engine.reset(world.entities.values())
        self._seated: Set[str] = set()
        self._joined: Set[str] = set()
        self._had: Dict[str, Dict[str, Set[str]]] = {}      # what each seat has of the views Python reads

    def seat(self, account: str, conn: Optional[int] = None) -> None:
        """A player to tell from now on, told nothing yet (a new connection's)."""
        self.engine.seat(account, conn)
        self._seated.add(account)
        self._joined.discard(account)
        self._had[account] = {}

    def unseat(self, account: str) -> None:
        self.engine.unseat(account)
        self._seated.discard(account)
        self._joined.discard(account)
        self._had.pop(account, None)

    def seated(self, account: str) -> bool:
        return account in self._seated

    def joined(self, account: str) -> bool:
        return account in self._joined

    def tick(self, world, out, welcoming: Iterable[str] = (), every_tick: bool = False, send: bool = False):
        """The tick's messages of each seat, {account: [JSON texts]}; with send, written to their connections (the
        bytes sent)."""
        welcoming = set(welcoming)
        welcomed = [a for a in self._seated if a in out.joined or (a in welcoming and a in world.players)]
        self._joined.update(welcomed)
        given: Dict[str, List[Optional[Set[str]]]] = {}
        if self.python_views:
            for account in welcomed:
                self._had[account] = {}
            dirty_cells = dirty_cells_of(world)
            for account in self._joined:
                if account not in world.players:
                    continue
                me = world.entities[world.players[account]]
                had = self._had[account]
                each: List[Optional[Set[str]]] = []
                for view in self.definition.views.values():
                    if by_python(view):
                        had[view.name] = view_members(world, view, me, had.get(view.name), dirty_cells)
                        each.append(had[view.name])
                    else:
                        each.append(None)
                given[account] = each
        dirty = [(eid, world.entities.get(eid)) for eid in world.dirty]
        events = [(e.message, e.tile, e.to, e.everyone, e.accounts) for e in world.events]
        return self.engine.tick(out.tick, dirty, list(world.gone), world.players, list(out.joined), welcoming,
                                out.acks, out.refused, events, given, every_tick, send)


def rust_engine():
    """The conformance harness's Rust engine (conform.py): the world of world.py, the frames of the engine."""
    from quantum.runtime.gameserver.conform import PythonEngine

    class RustEngine(PythonEngine):
        name = 'rust'

        def __init__(self, definition, snapshot=None):
            super().__init__(definition, snapshot)
            self.native = NativeFrames(self.world)
            for account in self.world.players:
                self.native.seat(account)

        def step(self, inputs: List[tuple]) -> dict:
            for item in inputs:
                if item[0] == 'join' and not self.native.seated(item[1]):
                    self.native.seat(item[1])
            out = self.world.step(inputs)
            for account in out.full:
                self.native.unseat(account)
            texts = self.native.tick(self.world, out)
            self.texts = texts                          # as they were written, for a test that reads them
            frames = {account: [json.loads(t) for t in said] for account, said in texts.items()}
            for account in out.left:
                self.native.unseat(account)
            self.world.dirty.clear()
            self.world.gone.clear()
            return {'acks': out.acks, 'refused': out.refused, 'joined': out.joined, 'left': sorted(out.left),
                    'full': sorted(out.full), 'entries': out.entries, 'frames': frames}

    return RustEngine


# -- the server on the engine's network ------------------------------------------------------------------------

@dataclass
class NativeConnection:
    """A connection of the engine's network: its id there, and its player (None: a test world's control)."""
    id: int
    account: Optional[str]
    sent_bytes: int = 0
    last_seq: Any = 0


def native_server():
    """server.py's WorldServer with the engine's network and frames: the same protocol, the same world."""
    from quantum.runtime.gameserver.server import MAX_MESSAGE, MESSAGES_A_SECOND, WorldServer

    class NativeServer(WorldServer):
        engine_name = 'rust'

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.conns: Dict[int, NativeConnection] = {}
            self.native: Optional[NativeFrames] = None
            self._engine_parts: List[tuple] = []           # each tick's bridge, frames and sending, in the engine

        async def run(self) -> None:
            self._loop = asyncio.get_running_loop()
            self._lock = asyncio.Lock()
            self._stop = asyncio.Event()
            self._restore()
            self.native = NativeFrames(self.world)
            engine = self.native.engine
            self.port = engine.listen(self.host, self.port, self.step_mode, MAX_MESSAGE, MESSAGES_A_SECOND,
                                      self.world.tick)
            pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='world-net')
            reader = asyncio.create_task(self._read(pool))
            try:
                self.say(f'{self.definition.name} on {self.url} (the Rust engine)' +
                         (' (a test world: it ticks on "step")' if self.step_mode else
                          f' at {self.definition.tick_rate} ticks a second')
                         + (', its rules as bytecode on the machine' if self.rules_name == 'machine' else ''))
                self.ready.set()
                if self.step_mode:
                    await self._stop.wait()
                else:
                    await self._clock()
            finally:
                reader.cancel()
                engine.shutdown()
                pool.shutdown(wait=False)
                if self._minds_pool is not None:
                    self._minds_pool.shutdown(wait=False, cancel_futures=True)
                if self._crashed:
                    if self.log._file:
                        self.log._file.close()
                else:
                    self.log.write_snapshot(self.world)
                    self.log.close()

        async def _read(self, pool) -> None:
            loop = asyncio.get_running_loop()
            engine = self.native.engine
            while True:
                events = await loop.run_in_executor(pool, engine.wait, 0.2)
                for event in events:
                    try:
                        await self._handle(event)
                    except Exception as e:  # noqa: BLE001 - one connection's trouble is not the world's
                        self.say(f'a message could not be handled: {e!r}')

        async def _handle(self, event: tuple) -> None:
            """server.py's _handler, a message at a time, in the order they came."""
            kind, conn_id = event[0], event[1]
            if kind == 'closed':
                conn = self.conns.pop(conn_id, None)
                if conn is None:
                    return
                if conn.account is None:
                    if conn in self.controls:
                        self.controls.remove(conn)
                elif self.connections.get(conn.account) is conn:
                    del self.connections[conn.account]
                    self.native.unseat(conn.account)
                    self.inbox.append(('leave', conn.account))
                return
            if kind == 'hello':
                await self._hello(conn_id, event[2])
                return
            conn = self.conns.get(conn_id)
            if conn is None:
                return
            if kind == 'cmd':
                _, _, seq, name, args = event
                self.inbox.append(('cmd', conn.account, seq, name, args))
                conn.last_seq = seq
                return
            message = event[2]
            kind = message.get('type')
            if kind == 'peek' and conn.account is None:
                async with self._lock:
                    await self._send_to(conn, self._peek())
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

        async def _hello(self, conn_id: int, message: dict) -> None:
            engine = self.native.engine
            if message.get('control'):
                if not self.step_mode:
                    engine.close(conn_id, 'A control connection is a test world\'s (--step).')
                    return
                conn = NativeConnection(conn_id, None)
                self.conns[conn_id] = conn
                self.controls.append(conn)
                engine.accept(conn_id, None)
                await self._send_to(conn, {'type': 'greeting', 'world': self.definition.name,
                                           'rate': self.definition.tick_rate, 'step': True,
                                           'control': True, 'views': list(self.definition.views)})
                return
            who = self._who(message)
            if isinstance(who, str):
                engine.close(conn_id, who)
                return
            account, name = who
            conn = NativeConnection(conn_id, account)
            self.conns[conn_id] = conn
            old = self.connections.get(account)
            welcomed_before = old is not None and self.native.joined(account)
            self.connections[account] = conn
            if old is not None:                 # a site's account, signed in again: it takes its hero
                if welcomed_before:
                    self.welcoming.add(account)
                await self._close(old, 'You signed in somewhere else.')
            elif account not in self.world.players or ('leave', account) in self.inbox:
                self.inbox.append(('join', account, name))
            else:                               # in the world with no connection: its hero, as it is
                self.welcoming.add(account)
            self.native.seat(account, conn_id)
            engine.accept(conn_id, account)
            await self._send_to(conn, {'type': 'greeting', 'world': self.definition.name,
                                       'rate': self.definition.tick_rate, 'step': self.step_mode})

        async def _send(self, out) -> None:
            for account, conn in list(self.connections.items()):
                if account in out.full:
                    await self._close(conn, 'The world is full.')
            self.native.tick(self.world, out, self.welcoming, every_tick=self.step_mode, send=True)
            self.welcoming.clear()
            if self.stats_ticks:
                self._engine_parts.append(self.native.engine.timings())

        async def _send_to(self, conn, message: dict) -> None:
            self.native.engine.send(conn.id, json.dumps(message, separators=(',', ':')))

        async def _close(self, conn, reason: str) -> None:
            self.native.engine.close(conn.id, reason)
            account = conn.account
            if account is not None and self.connections.get(account) is conn:
                del self.connections[account]
                self.native.unseat(account)
                if account in self.world.players or any(i[0] == 'join' and i[1] == account for i in self.inbox):
                    self.inbox.append(('leave', account))

        def stats(self) -> dict:
            if self.native is not None:
                total, sent, _ = self.native.engine.counters()
                self.bytes_out = total
                for conn in self.connections.values():
                    conn.sent_bytes = sent.get(conn.id, conn.sent_bytes)
            parts, self._engine_parts = self._engine_parts, []
            numbers = super().stats()
            for n, name in enumerate(('bridge', 'frames', 'write')):     # the engine's share of the sending
                values = sorted(p[n] for p in parts)
                numbers[f'{name}_ms_p50'] = round(values[len(values) // 2] * 1000, 2) if values else 0.0
            return numbers

    return NativeServer
