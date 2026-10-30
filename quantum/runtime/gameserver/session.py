"""The play protocol's door into a world (PLAN_GAME_SERVER.md, "The play protocol in a world"): a `WorldSession`
speaks the server's protocol, with no Godot, with the play protocol's words: `observe`, `act`, `until`.

    with serve_world('tests/gameserver/worlds/yard/yard.server.q') as server:      # a test world: --step
        with WorldSession(server.url, 'ana') as ana, WorldSession(server.url, 'bo') as bo:
            seen = ana.act(send=[('step', {'dir': 'east'})], ticks=3)
            assert seen['acks'] and bo.observe()['world'][ana.me_id]['at'] == seen['me']['at']

An observation is what the player knows: its own entity with its private fields (`me`), what it sees of each view
(`views`, by name, then by id) and of them all (`world`, by id), the events where it sees (`events`), the commands
that ran (`acks`) and those refused, with why (`refused`), since the last one. In a test world a session's `act`
steps the world itself; in a live one it waits the world's ticks.

A site's account comes in with its ticket (`WorldSession(url, ticket=tickets.issue(...))`, accounts="site").

A control session (`WorldSession(url, control=True)`, a test world's) has no entity: it steps the world for a
harness whose players are elsewhere (Godot clients), and `peek()` is the god's view.
"""

from __future__ import annotations

import contextlib
import copy
import json
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Union

from quantum.core.expressions import ExpressionError, ExpressionEvaluator


class WorldSessionError(Exception):
    pass


@contextlib.contextmanager
def serve_world(world: Union[str, Path, Any], *, step: bool = True, data: Optional[Path] = None,
                snapshot_every: float = 300.0, quiet: bool = True, secret: Optional[bytes] = None,
                mind: Optional[Any] = None, mind_seconds: float = 20.0, engine: Optional[str] = None):
    """A world served on this machine, in a thread, on a free port: the server, with `.url` and `.world`. engine:
    python or rust (else QUANTUM_WORLD_ENGINE, else python)."""
    from quantum.runtime.gameserver.server import load, make_server
    import asyncio
    import tempfile

    definition = load(str(world)) if isinstance(world, (str, Path)) else world
    with tempfile.TemporaryDirectory() as scratch:
        server = make_server(definition, engine, port=0, step=step, data_dir=Path(data) if data else Path(scratch),
                             snapshot_every=snapshot_every, quiet=quiet, secret=secret, mind=mind,
                             mind_seconds=mind_seconds)
        failure: List[BaseException] = []

        def run() -> None:
            try:
                asyncio.run(server.run())
            except BaseException as e:  # noqa: BLE001
                failure.append(e)
                server.ready.set()

        thread = threading.Thread(target=run, name=f'gameserver-{definition.name}', daemon=True)
        thread.start()
        server.ready.wait(30)
        if failure:
            raise failure[0]
        try:
            yield server
        finally:
            server.stop()
            thread.join(30)


class WorldSession:
    def __init__(self, url: str, name: str = 'control', timeout: float = 10.0, control: bool = False,
                 keep_frames: bool = False, ticket: Optional[str] = None):
        from websockets.sync.client import connect

        self.url, self.name, self.timeout, self.control = url, name, timeout, control
        # entered as its context (websockets 17.1 warns of a connection used without one); left in close()
        self.ws = connect(url, max_size=8 * 1024 * 1024, open_timeout=timeout).__enter__()
        self.me_id: Optional[str] = None
        self.tick = 0
        self.rate = 10
        self.views: Dict[str, Dict[str, dict]] = {}
        self.acks: List[int] = []
        self.refused: List[dict] = []
        self.events: List[dict] = []
        self.welcome: Optional[dict] = None
        self.step_mode: Optional[bool] = None
        self.frames: List[dict] = []                 # every message the world sent, with keep_frames
        self.keep_frames = keep_frames
        self._seq = 0
        self._send({'type': 'hello', 'control': True} if control else
                   {'type': 'hello', 'ticket': ticket} if ticket else {'type': 'hello', 'name': name})
        self._join()

    @property
    def world(self) -> Dict[str, dict]:
        """Every entity the player sees, in any of its views."""
        seen: Dict[str, dict] = {}
        for view in self.views.values():
            seen.update(view)
        return seen

    # -- the wire ------------------------------------------------------------------------------------------------

    def _send(self, message: dict) -> None:
        try:
            self.ws.send(json.dumps(message))
        except Exception:  # noqa: BLE001 - the world closed it: what it said last says why
            self._read(lambda m: False)

    def _read(self, until: Callable[[dict], bool]) -> dict:
        deadline = time.monotonic() + self.timeout
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                raise WorldSessionError(f'{self.name}: no answer from the world in {self.timeout}s')
            try:
                raw = self.ws.recv(timeout=left)
            except TimeoutError:
                continue
            except Exception as e:  # noqa: BLE001 - the server closed
                raise WorldSessionError(f'{self.name}: the world closed the connection ({e})')
            message = json.loads(raw)
            if self.keep_frames:
                self.frames.append(message)
            self._apply(message)
            if until(message):
                return message

    def _apply(self, message: dict) -> None:
        kind = message.get('type')
        if kind == 'error':
            raise WorldSessionError(f'{self.name}: {message.get("reason")}')
        if kind == 'welcome':
            self.welcome = message
            self.me_id = message['you']
            self.rate = message.get('rate', 10)
            self.views = {name: {} for name in message.get('views', ['world'])}
        if 'tick' in message:
            self.tick = max(self.tick, message['tick'])
        if kind == 'tick':
            self.acks += message.get('ack', [])
            self.refused += message.get('refused', [])
            self.events += message.get('events', [])
            for name, view in message.get('views', {}).items():
                seen = self.views.setdefault(name, {})
                for entity in view.get('enter', []):
                    seen[entity['id']] = entity
                for change in view.get('update', []):
                    seen.setdefault(change['id'], {'id': change['id']}).update(
                        {k: v for k, v in change.items() if k != 'id'})
                for eid in view.get('leave', []):
                    seen.pop(eid, None)

    def _join(self) -> None:
        """The join waits for a tick: in a test world this session gives it one (the world steps a tick); in a live
        one it comes."""
        greeting = self._read(lambda m: m.get('type') == 'greeting')
        self.step_mode = bool(greeting.get('step'))
        self.rate = greeting.get('rate', 10)
        if self.control:
            return
        if self.step_mode:
            self._send({'type': 'step', 'ticks': 1})
            self._read(lambda m: m.get('type') == 'stepped')
        else:
            self._read(lambda m: m.get('type') == 'welcome')
        if self.welcome is None:
            raise WorldSessionError(f'{self.name}: the world did not let us in')

    # -- the play protocol's words ---------------------------------------------------------------------------

    def send(self, name: str, **args: Any) -> int:
        self._seq += 1
        self._send({'type': 'cmd', 'seq': self._seq, 'name': name, 'args': args})
        return self._seq

    def observe(self) -> dict:
        """What the player knows now (every frame of every tick so far has arrived)."""
        self._send({'type': 'sync'})
        self._read(lambda m: m.get('type') == 'synced')
        return self._observation()

    def _observation(self) -> dict:
        world = self.world
        seen = {'tick': self.tick, 'me': copy.deepcopy(world.get(self.me_id)) if self.me_id else None,
                'world': copy.deepcopy(world), 'views': copy.deepcopy(self.views), 'events': self.events,
                'acks': self.acks, 'refused': self.refused}
        self.acks, self.refused, self.events = [], [], []
        return seen

    def peek(self) -> dict:
        """A control session's: the whole world now, every entity with all its fields (the god's view)."""
        if not self.control:
            raise WorldSessionError('peek is a control session\'s (WorldSession(url, control=True))')
        self._send({'type': 'peek'})
        return self._read(lambda m: m.get('type') == 'peeked')

    def act(self, send: Optional[Iterable[Tuple[str, dict]]] = None, ticks: int = 1) -> dict:
        """Sends the commands, and the world runs `ticks` ticks (the first takes them)."""
        for name, args in (send or []):
            self.send(name, **args)
        if self.step_mode:
            self._send({'type': 'step', 'ticks': ticks})
            self._read(lambda m: m.get('type') == 'stepped')
            return self._observation()
        target = self.tick + ticks                     # a live world: its ticks come at its pace
        while self.tick < target:
            self._send({'type': 'sync'})
            self._read(lambda m: m.get('type') == 'synced')
            if self.tick < target:
                time.sleep(min(0.05, (target - self.tick) / self.rate))
        return self._observation()

    def until(self, condition: Union[str, Callable[[dict], bool]], max_ticks: int = 600,
              send: Optional[Iterable[Tuple[str, dict]]] = None, every: int = 1) -> dict:
        """As act, then a tick at a time until the condition holds (a function of the observation, or an
        expression over it: "me.at.x == 5"). The observation says whether it did: `until`; its acks, refusals
        and events are those of every tick it took."""
        holds = condition if callable(condition) else _expression(condition)
        seen = self.act(send, ticks=every)
        acks, refused, events = list(seen['acks']), list(seen['refused']), list(seen['events'])
        ticks = every
        while not holds(seen) and ticks < max_ticks:
            seen = self.act(ticks=every)
            acks += seen['acks']
            refused += seen['refused']
            events += seen['events']
            ticks += every
        seen['acks'], seen['refused'], seen['events'] = acks, refused, events
        seen['until'] = bool(holds(seen))
        return seen

    def close(self) -> None:
        with contextlib.suppress(Exception):
            self.ws.__exit__(None, None, None)

    def __enter__(self) -> 'WorldSession':
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def _expression(text: str) -> Callable[[dict], bool]:
    evaluator = ExpressionEvaluator()

    def holds(seen: dict) -> bool:
        try:
            return bool(evaluator.evaluate(text.strip().strip('{}'), seen, absent_scope_key_is_none=True))
        except ExpressionError:
            return False
    return holds
