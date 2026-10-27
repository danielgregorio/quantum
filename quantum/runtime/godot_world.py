"""A test world and the games of its players, played together a step at a time (PLAN_GAME_SERVER.md, Phase 2).

    with WorldTable('meadow.server.q', 'build/meadow', seats=['ana', 'bo']) as table:
        seen = table.act('ana', tap=['right'])            # ana's game presses right; the world runs a tick
        assert seen['bo']['world']['entities']['hero:ana']['at'] == seen['ana']['world']['me']['at']

The world is a test world (`--step`): it ticks only when the table says. `act` gives a seat's game its input, runs
every game the ticks of one tick of the world (six at sixty a second against the world's ten), waits until the
server has every command the games sent, steps the world, and runs each game until it has heard that tick. So the
server and the Godot clients go in step and come out the same every run, faster than real time. An observation is
the play protocol's, with `world`: what that player knows of the world (its `me`, its views, its entities, the
world's tick). `peek()` is the god's view.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Dict, Iterable, Optional, Union

from quantum.runtime.gameserver.session import WorldSession, serve_world
from quantum.runtime.godot_play import PlayError, PlaySession


class WorldTable:
    def __init__(self, world: Union[str, Path], project: Union[str, Path], seats: Iterable[str],
                 binary: Optional[Path] = None, timeout: float = 60.0, latency: Optional[int] = None):
        """latency (ms): each game's messages to and from the world held half that long each way."""
        self.timeout = timeout
        self._serving = serve_world(world)
        self.server = self._serving.__enter__()
        self.games: Dict[str, PlaySession] = {}
        try:
            self.control = WorldSession(self.server.url, control=True)
            self.frames = max(1, round(60 / self.server.definition.tick_rate))
            for seat in seats:
                self.games[seat] = PlaySession(project, binary=binary, world=self.server.url, name=seat,
                                               latency=latency)
            self._come_in()
        except BaseException:
            self.close()
            raise

    @property
    def tick(self) -> int:
        """The world's tick."""
        return self.control.tick

    def peek(self) -> dict:
        return self.control.peek()

    def _deadline(self, what: str):
        end = time.monotonic() + self.timeout

        def check() -> None:
            if time.monotonic() > end:
                raise PlayError(f'the world table: {what} in {self.timeout}s')
        return check

    def _come_in(self) -> None:
        """Each game opens its connection as its scene of the world is entered: the games run until the server has
        every one of them; then the world's tick lets them in."""
        late = self._deadline('the games did not all connect')
        while not set(self.games) <= set(self.peek()['connected']):
            late()
            for game in self.games.values():
                game.act(ticks=1)
        self._step()

    def _step(self, ticks: int = 1) -> None:
        """The world runs, once the server has every command the games sent; then each game hears its tick."""
        late = self._deadline('the server did not get the commands the games sent')
        while True:
            connected = self.peek()['connected']
            if all(connected.get(seat, 0) >= ((game.last or {}).get('world') or {}).get('sent', 0)
                   for seat, game in self.games.items()):
                break
            late()
            time.sleep(0.005)
        self.control.act(ticks=ticks)
        target = self.control.tick
        for seat, game in self.games.items():
            heard = game.until({'path': 'world.tick', 'op': '>=', 'value': target}, max_ticks=600)
            if ((heard.get('world') or {}).get('tick') or 0) < target:
                raise PlayError(f'{seat}\'s game did not hear the world\'s tick {target} '
                                f'(its world: {heard.get("world")})')

    def act(self, seat: Optional[str] = None, tap: Iterable[str] = (), hold: Iterable[str] = (),
            ticks: int = 1) -> Dict[str, dict]:
        """`ticks` ticks of the world, the seat's game given its input in the first (tap) or all (hold); the
        observation of every seat after."""
        tap, hold = list(tap), list(hold)
        for n in range(ticks):
            for name, game in self.games.items():
                mine = name == seat
                game.act(tap=tap if mine and n == 0 else (), hold=hold if mine else (), ticks=self.frames)
            self._step()
        return {name: game.last for name, game in self.games.items()}

    def observe(self) -> Dict[str, dict]:
        return {name: game.observe() for name, game in self.games.items()}

    def close(self) -> None:
        for game in self.games.values():
            try:
                game.close()
            except Exception:  # noqa: BLE001 - closing what may already be gone
                pass
        control = getattr(self, 'control', None)
        if control is not None:
            control.close()
        self._serving.__exit__(None, None, None)

    def __enter__(self) -> 'WorldTable':
        return self

    def __exit__(self, *exc) -> None:
        self.close()
