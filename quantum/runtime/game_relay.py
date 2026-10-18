"""``quantum relay``: where two browsers meet to play a networked game.

A web page cannot host: it has no server sockets. Two people on the site
can still play each other through a relay that both join:

    quantum relay --port 8765                                   # ws://, for a local test
    quantum relay --port 443 --cert fullchain.pem --key privkey.pem   # wss://, for the site

and each player joins ``wss://relay.example/pong/ROOM`` from the game's
title (any room name both agree on). The first player into a room starts,
for that room, the game itself in a headless Godot as a host that takes no
seat (``--q-relay``): every player joins it, and Godot's multiplayer passes
each player's inputs on to the others. The relay never plays and never
sees the game; the lockstep's hash check still proves that both players'
games are the same. When the last player leaves, the room's Godot stops.

The relay here only carries WebSocket messages between a player and the
room's Godot, unchanged. It compiles each game of ``projects/`` (those with
``qg:multiplayer``) once, the first time a room asks for it. Needs the
``websockets`` package (``pip install "quantum[websocket]"``).
"""

from __future__ import annotations

import asyncio
import logging
import re
import shutil
import socket
import ssl
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Set

from quantum.runtime.godot_replay import free_port

REPO = Path(__file__).resolve().parents[2]
ROOM = re.compile(r'^/([a-z0-9-]{1,32})/([A-Za-z0-9_-]{1,32})/?$')
log = logging.getLogger('quantum.relay')


@dataclass
class Room:
    game: str
    name: str
    port: int
    proc: subprocess.Popen
    players: Set[object] = field(default_factory=set)


class GameRelay:
    """Rooms of networked games, each a seatless Godot that the players join."""

    def __init__(self, projects: Optional[Path] = None, binary: Optional[Path] = None, max_rooms: int = 50):
        self.projects = Path(projects) if projects else REPO / 'projects'
        self.binary = binary
        self.max_rooms = max_rooms
        self.rooms: Dict[str, Room] = {}
        self.builds: Dict[str, Path] = {}
        self._tmp = Path(tempfile.mkdtemp(prefix='quantum-relay-'))
        self._lock = asyncio.Lock()

    # --- the games ---

    def build(self, game: str) -> Path:
        """The game compiled once, assets imported, ready to run headless."""
        if game in self.builds:
            return self.builds[game]
        from quantum.core.parser import QuantumParser
        from quantum.runtime.godot import compile_game
        from quantum.runtime.godot_bin import check_project
        source = self.projects / game / f'{game}.q'
        if not source.is_file():
            raise LookupError(f'no game named {game!r}')
        text = source.read_text(encoding='utf-8')
        if '<qg:multiplayer' not in text:
            raise LookupError(f'{game} is not a networked game')
        out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(source)),
                                str(self._tmp / game), source_dir=str(source.parent)))
        errors = check_project(out, binary=self.binary)
        if errors:
            raise RuntimeError(f'{game} does not load: ' + '; '.join(errors))
        self.builds[game] = out
        return out

    # --- the rooms ---

    async def room(self, game: str, name: str) -> Room:
        key = f'{game}/{name}'
        async with self._lock:
            room = self.rooms.get(key)
            if room is not None and room.proc.poll() is None:
                return room
            if len(self.rooms) >= self.max_rooms:
                raise LookupError('the relay is full')
            project = await asyncio.to_thread(self.build, game)
            from quantum.runtime.godot_bin import ensure_godot
            port = free_port()
            proc = subprocess.Popen([str(self.binary or ensure_godot()), '--headless', '--path', str(project), '--',
                                     f'--q-relay={port}'],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            await _listening(port, proc)
            room = Room(game, name, port, proc)
            self.rooms[key] = room
            log.info('room %s opened (Godot on port %d)', key, port)
            return room

    def close_room(self, room: Room) -> None:
        key = f'{room.game}/{room.name}'
        if self.rooms.get(key) is room:
            del self.rooms[key]
        if room.proc.poll() is None:
            room.proc.terminate()
            try:
                room.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                room.proc.kill()
        log.info('room %s closed', key)

    # --- a player ---

    async def handle(self, ws) -> None:
        import websockets
        path = ws.request.path
        m = ROOM.match(path)
        if not m:
            await ws.close(1008, 'the address is /game/room')
            return
        try:
            room = await self.room(m.group(1), m.group(2))
        except (LookupError, RuntimeError) as e:
            await ws.close(1008, str(e)[:120])
            return
        room.players.add(ws)
        try:
            async with websockets.connect(f'ws://127.0.0.1:{room.port}', max_size=None) as godot:
                await _pump(ws, godot)
        except OSError:
            await ws.close(1011, 'the room has closed')
        finally:
            room.players.discard(ws)
            if not room.players:
                self.close_room(room)

    async def serve(self, host: str, port: int, cert: Optional[str] = None, key: Optional[str] = None):
        import websockets
        context = None
        if cert:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(cert, key)
        return await websockets.serve(self.handle, host, port, ssl=context, max_size=None)

    def shutdown(self) -> None:
        for room in list(self.rooms.values()):
            self.close_room(room)
        shutil.rmtree(self._tmp, ignore_errors=True)


async def _pump(a, b) -> None:
    """Messages both ways, unchanged, until either side closes."""
    async def one_way(src, dst):
        async for message in src:
            await dst.send(message)
    tasks = [asyncio.create_task(one_way(a, b)), asyncio.create_task(one_way(b, a))]
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    for t in pending:
        t.cancel()
    for t in done:
        if t.exception() and not _closed(t.exception()):
            raise t.exception()


def _closed(e: BaseException) -> bool:
    import websockets
    return isinstance(e, websockets.ConnectionClosed)


async def _listening(port: int, proc: subprocess.Popen, seconds: float = 20.0) -> None:
    """Until the room's Godot takes connections."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + seconds
    while loop.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError('the room could not start')
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.2):
                pass
        except OSError:
            await asyncio.sleep(0.1)
            continue
        # the port answers; it is the room's Godot only if that Godot still runs (one that
        # found its port taken, by another program in between, gives up)
        await asyncio.sleep(0.3)
        if proc.poll() is not None:
            raise RuntimeError('the room could not start')
        return
    proc.kill()
    raise RuntimeError('the room did not start in time')


def main(args) -> int:
    try:
        import websockets  # noqa: F401
    except ImportError:
        print('quantum relay needs the websockets package: pip install "quantum[websocket]"')
        return 1
    if bool(args.cert) != bool(args.key):
        print('quantum relay: --cert and --key go together')
        return 2
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    relay = GameRelay(projects=Path(args.projects) if args.projects else None, max_rooms=args.max_rooms)

    async def run():
        server = await relay.serve(args.bind, args.port, args.cert, args.key)
        scheme = 'wss' if args.cert else 'ws'
        print(f'quantum relay: {scheme}://{args.bind}:{args.port}/<game>/<room>')
        async with server:
            await asyncio.Future()

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
    finally:
        relay.shutdown()
    return 0


def add_arguments(parser) -> None:
    parser.add_argument('--port', type=int, default=8765, help='the port players join (default 8765)')
    parser.add_argument('--bind', default='0.0.0.0', help='the address to listen on (default all)')
    parser.add_argument('--cert', help='a TLS certificate (PEM): the relay is then wss://, as a page on HTTPS needs')
    parser.add_argument('--key', help="the certificate's private key (PEM)")
    parser.add_argument('--projects', help='the folder of games (default: projects/)')
    parser.add_argument('--max-rooms', type=int, default=50, help='rooms open at once (default 50)')
