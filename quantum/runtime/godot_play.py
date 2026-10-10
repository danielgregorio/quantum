"""Play a built game step by step: the play protocol (PLAN_PLAY_PROTOCOL.md).

A ``PlaySession`` runs ``godot_play.gd`` (next to this file) as the main
loop of a Godot project, headless, and talks to it one JSON line at a time.
The game stands still between requests; an ``act`` runs exactly the ticks
it asks for, at the fixed physics step, as a replay does::

    with PlaySession.open('projects/rpg/rpg.q') as game:
        seen = game.observe()
        seen = game.act(hold=['right'], ticks=16)          # one cell to the right
        seen = game.until('talking', hold=['right'])        # walk until someone talks
        seen['screen']                                      # what is on the screen to read

Every answer is an observation: the tick, the scene, its state as
``quantum_state()`` reports it, what the screen shows (``screen``: the HUD,
the menus, the dialogue), the actions held, and the game's actions.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable, List, Optional, Union

from quantum.runtime.godot_bin import ensure_godot

PLAY_SCRIPT = Path(__file__).with_name('godot_play.gd')
PREFIX = 'QPP '


class PlayError(RuntimeError):
    """The game refused a request, or stopped answering."""


_COMPARE = re.compile(r'^\s*([\w.]+)\s*(==|!=|<=|>=|<|>)\s*(.+?)\s*$')


def condition(spec: Union[str, dict, list]) -> dict:
    """A condition for ``until``, from its short form.

    ``"player.col == 11"``, ``"scene != 'exploration'"``, ``"talking"`` (the
    path is truthy), ``"not talking"``, ``"changed scene"``; a list is any
    of them; a dict is passed as it is (``{"all": [...]}``).
    """
    if isinstance(spec, dict):
        return spec
    if isinstance(spec, (list, tuple)):
        return {'any': [condition(s) for s in spec]}
    text = spec.strip()
    if text.startswith('changed '):
        return {'changed': text[8:].strip()}
    if text.startswith('not '):
        return {'path': text[4:].strip(), 'op': 'falsy'}
    m = _COMPARE.match(text)
    if m:
        raw = m.group(3)
        try:
            value = json.loads(raw.replace("'", '"'))
        except json.JSONDecodeError:
            value = raw
        return {'path': m.group(1), 'op': m.group(2), 'value': value}
    return {'path': text, 'op': 'truthy'}


class PlaySession:
    """One running game, played request by request."""

    def __init__(self, project_dir: Union[str, Path], binary: Optional[Path] = None,
                 persist_dir: Optional[Path] = None, timeout: float = 120):
        self.project_dir = Path(project_dir)
        self.timeout = timeout
        self._tmp = tempfile.TemporaryDirectory(prefix='quantum-play-')
        persist = Path(persist_dir) if persist_dir else Path(self._tmp.name) / 'persist'
        persist.mkdir(parents=True, exist_ok=True)
        self.log: List[str] = []      # what Godot printed besides the answers
        self._proc = subprocess.Popen(
            [str(binary or ensure_godot()), '--headless', '--fixed-fps', '60', '--path', str(self.project_dir),
             '-s', str(PLAY_SCRIPT), '--', f'--persist-dir={persist}'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        self.last: Optional[dict] = None

    @classmethod
    def open(cls, game: Union[str, Path], **kwargs) -> 'PlaySession':
        """A session on a ``.q`` (compiled into a temporary directory) or a built project."""
        game = Path(game)
        if game.suffix != '.q':
            return cls(game, **kwargs)
        from quantum.core.parser import QuantumParser
        from quantum.runtime.godot import compile_game
        from quantum.runtime.godot_bin import check_project
        build = Path(tempfile.mkdtemp(prefix='quantum-play-build-'))
        out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(game)), str(build / 'godot'),
                                source_dir=str(game.parent)))
        errors = check_project(out, binary=kwargs.get('binary'))   # imports the assets, as a replay needs
        if errors:
            shutil.rmtree(build, ignore_errors=True)
            raise PlayError('the game does not load: ' + '; '.join(errors))
        session = cls(out, **kwargs)
        session._build = build
        return session

    # --- requests ---

    def request(self, req: dict) -> dict:
        if self._proc.poll() is not None:
            raise PlayError('the game has stopped: ' + ' | '.join(self.log[-5:]))
        self._proc.stdin.write(json.dumps(req) + '\n')
        self._proc.stdin.flush()
        while True:
            line = self._proc.stdout.readline()
            if line == '':
                raise PlayError('the game stopped answering: ' + ' | '.join(self.log[-5:]))
            if line.startswith(PREFIX):
                answer = json.loads(line[len(PREFIX):])
                if 'error' in answer:
                    raise PlayError(answer['error'])
                if 'tick' in answer and 'scene' in answer:
                    self.last = answer
                return answer
            self.log.append(line.rstrip('\n'))

    def observe(self) -> dict:
        return self.request({'op': 'observe'})

    def act(self, hold: Iterable[str] = (), tap: Iterable[str] = (), press: Iterable[str] = (),
            release: Iterable[str] = (), cursor: Optional[tuple] = None, ticks: int = 1) -> dict:
        """Apply the actions on the first tick and run ``ticks`` ticks: ``hold`` is
        released after them, ``tap`` after the first, ``press`` stays until a ``release``."""
        return self.request(self._actions('act', hold, tap, press, release, cursor, ticks=ticks))

    def until(self, cond: Union[str, dict, list], hold: Iterable[str] = (), tap: Iterable[str] = (),
              press: Iterable[str] = (), release: Iterable[str] = (), cursor: Optional[tuple] = None,
              max_ticks: int = 600) -> dict:
        """As ``act``, but runs until ``cond`` holds (checked after each tick) or
        ``max_ticks`` have run; the answer's ``stopped`` says which."""
        return self.request(self._actions('until', hold, tap, press, release, cursor,
                                          max_ticks=max_ticks, condition=condition(cond)))

    @staticmethod
    def _actions(op, hold, tap, press, release, cursor, **more) -> dict:
        req = {'op': op, 'hold': list(hold), 'tap': list(tap), 'press': list(press), 'release': list(release)}
        if cursor is not None:
            req['cursor'] = [float(cursor[0]), float(cursor[1])]
        req.update(more)
        return req

    # --- reading an observation ---

    @staticmethod
    def view(obs: dict, kind: str) -> Optional[dict]:
        """The first screen view of a kind (``"dialogue"``, ``"menu"``, ``"hud"``) that is shown."""
        for v in obs.get('screen', []):
            if v.get('kind') == kind and v.get('shown', True):
                return v
        return None

    # --- the end ---

    def close(self) -> None:
        if self._proc.poll() is None:
            try:
                self.request({'op': 'end'})
            except PlayError:
                pass
            try:
                self._proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        for stream in (self._proc.stdin, self._proc.stdout):
            if stream:
                stream.close()
        self._tmp.cleanup()
        build = getattr(self, '_build', None)
        if build:
            shutil.rmtree(build, ignore_errors=True)

    def __enter__(self) -> 'PlaySession':
        return self

    def __exit__(self, *exc) -> None:
        self.close()
