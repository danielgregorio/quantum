"""The play protocol's door into a world (PLAN_GAME_SERVER.md, "The play protocol in a world"): a `WorldSession`
speaks the server's protocol, with no Godot, with the play protocol's words: `observe`, `act`, `until`.

    with serve_world('tests/gameserver/worlds/yard/yard.server.q') as server:      # a test world: --step
        with WorldSession(server.url, 'ana') as ana, WorldSession(server.url, 'bo') as bo:
            seen = ana.act(send=[('step', {'dir': 'east'})], ticks=3)
            assert seen['acks'] and bo.observe()['world'][ana.me_id]['at'] == seen['me']['at']

An observation is what the player knows: its own entity with its private fields (`me`), every entity it sees
(`world`, by id), the commands that ran (`acks`) and those refused, with why (`refused`), since the last one. In a
test world a session's `act` steps the world itself; in a live one it waits the world's ticks.
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
                snapshot_every: float = 300.0, quiet: bool = True):
    """A world served on this machine, in a thread, on a free port: the server, with `.url` and `.world`."""
    from quantum.runtime.gameserver.server import WorldServer, load
    import asyncio
    import tempfile

    definition = load(str(world)) if isinstance(world, (str, Path)) else world
    with tempfile.TemporaryDirectory() as scratch:
        server = WorldServer(definition, port=0, step=step, data_dir=Path(data) if data else Path(scratch),
                             snapshot_every=snapshot_every, quiet=quiet)
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
    def __init__(self, url: str, name: str, timeout: float = 10.0):
        from websockets.sync.client import connect

        self.url, self.name, self.timeout = url, name, timeout
        # entered as its context (websockets 17.1 warns of a connection used without one); left in close()
        self.ws = connect(url, max_size=8 * 1024 * 1024, open_timeout=timeout).__enter__()
        self.me_id: Optional[str] = None
        self.tick = 0
        self.rate = 10
        self.world: Dict[str, dict] = {}
        self.acks: List[int] = []
        self.refused: List[dict] = []
        self.welcome: Optional[dict] = None
        self.step_mode: Optional[bool] = None
        self._seq = 0
        self._send({'type': 'hello', 'name': name})
        self._join()

    # -- the wire ------------------------------------------------------------------------------------------------

    def _send(self, message: dict) -> None:
        self.ws.send(json.dumps(message))

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
            self.world = {}
        if 'tick' in message:
            self.tick = max(self.tick, message['tick'])
        if kind == 'tick':
            self.acks += message.get('ack', [])
            self.refused += message.get('refused', [])
            for name, view in message.get('views', {}).items():
                for entity in view.get('enter', []):
                    self.world[entity['id']] = entity
                for change in view.get('update', []):
                    self.world.setdefault(change['id'], {'id': change['id']}).update(
                        {k: v for k, v in change.items() if k != 'id'})
                for eid in view.get('leave', []):
                    self.world.pop(eid, None)

    def _join(self) -> None:
        """The join waits for a tick: in a test world this session gives it one (the world steps a tick); in a live
        one it comes."""
        greeting = self._read(lambda m: m.get('type') == 'greeting')
        self.step_mode = bool(greeting.get('step'))
        self.rate = greeting.get('rate', 10)
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
        seen = {'tick': self.tick, 'me': copy.deepcopy(self.world.get(self.me_id)),
                'world': copy.deepcopy(self.world), 'acks': self.acks, 'refused': self.refused}
        self.acks, self.refused = [], []
        return seen

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
        expression over it: "me.at.x == 5"). The observation says whether it did: `until`."""
        holds = condition if callable(condition) else _expression(condition)
        seen = self.act(send, ticks=every)
        acks, refused = list(seen['acks']), list(seen['refused'])
        ticks = every
        while not holds(seen) and ticks < max_ticks:
            seen = self.act(ticks=every)
            acks += seen['acks']
            refused += seen['refused']
            ticks += every
        seen['acks'], seen['refused'] = acks, refused
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
