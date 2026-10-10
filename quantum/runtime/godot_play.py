"""Play a built game step by step: the play protocol (PLAN_PLAY_PROTOCOL.md).

A ``PlaySession`` runs ``godot_play.gd`` (next to this file) as the main
loop of a Godot project, headless, and talks to it one JSON line at a time.
The game stands still between requests; an ``act`` runs exactly the ticks
it asks for, at the fixed physics step, as a replay does::

    with PlaySession.open('projects/rpg/rpg.q') as game:
        seen = game.observe()
        seen = game.act(hold=['right'], ticks=16)          # one cell to the right
        seen = game.until('talking', hold=['right'])        # walk until someone talks
        PlaySession.screen(seen, 'dialogue')                # what is on the screen to read

Every answer is an observation: the tick, the scene, its state as
``quantum_state()`` reports it, what the screen shows (``screen``: the HUD,
the menus, the dialogue), the actions held, and the game's actions. An
answer to ``act`` or ``until`` also carries the ``events`` of its ticks
(a touch, a hit, a line said, a variable set...), and, after a scene
change, the new scene's ``map``. ``view()`` draws the screen as text;
``frame()`` saves the real picture, in a session opened with ``frames=True``.
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
    path is truthy), ``"not talking"``, ``"changed scene"``, ``"event:say"``,
    ``"event:touch with=key"`` (such an event happened); a list is any of
    them; a dict is passed as it is (``{"all": [...]}``).
    """
    if isinstance(spec, dict):
        return spec
    if isinstance(spec, (list, tuple)):
        return {'any': [condition(s) for s in spec]}
    text = spec.strip()
    if text.startswith('event:'):   # "event:say", "event:touch with=key"
        name, *pairs = text[6:].split()
        cond = {'event': name}
        for pair in pairs:
            k, _, v = pair.partition('=')
            cond[k] = v
        return cond
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
                 persist_dir: Optional[Path] = None, timeout: float = 120, frames: bool = False):
        self.project_dir = Path(project_dir)
        self.timeout = timeout
        self._tmp = tempfile.TemporaryDirectory(prefix='quantum-play-')
        # what the game had saved when the session began: a restored game starts from it again
        self._persist_origin = Path(self._tmp.name) / 'persist-origin'
        if persist_dir and Path(persist_dir).is_dir():
            shutil.copytree(persist_dir, self._persist_origin)
        else:
            self._persist_origin.mkdir(parents=True)
        self._persist_dir = Path(persist_dir) if persist_dir else None
        self._starts = 0
        self.log: List[str] = []      # what Godot printed besides the answers
        godot = [str(binary or ensure_godot())]
        if frames:
            # a display to draw on: a virtual one (xvfb), and a renderer that works in it
            if not shutil.which('xvfb-run'):
                raise PlayError('frames=True needs xvfb-run (a virtual display) on this machine')
            width = self._setting('display/window/size/viewport_width', 1280)
            height = self._setting('display/window/size/viewport_height', 720)
            godot = ['xvfb-run', '-a', '-s', f'-screen 0 {width + 64}x{height + 64}x24', *godot,
                     '--rendering-driver', 'opengl3', '--resolution', f'{width}x{height}']
        else:
            godot.append('--headless')
        self._godot = godot
        self.last: Optional[dict] = None
        self._spawn()

    def _spawn(self) -> None:
        """A fresh game at tick 0, from the saved state the session began with."""
        self._starts += 1
        if self._persist_dir is not None and self._starts == 1:
            persist = self._persist_dir
        else:
            persist = Path(self._tmp.name) / f'persist-{self._starts}'
            shutil.copytree(self._persist_origin, persist)
        persist.mkdir(parents=True, exist_ok=True)
        self._proc = subprocess.Popen(
            [*self._godot, '--fixed-fps', '60', '--path', str(self.project_dir),
             '-s', str(PLAY_SCRIPT), '--', f'--persist-dir={persist}'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

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

    def map(self) -> Optional[dict]:
        """The scene's tilemap as rows of text: "#" stops, "-" one-way, "." open."""
        return self.request({'op': 'map'})['map']

    def view(self) -> dict:
        """The screen drawn as text at the map's cell size, with a legend of its letters."""
        return self.request({'op': 'view'})

    def frame(self, path: Union[str, Path]) -> dict:
        """Saves the picture on the screen as a PNG (a session opened with ``frames=True``)."""
        return self.request({'op': 'frame', 'path': str(Path(path).resolve())})

    # --- branching, and every session is a tape ---

    def tape(self) -> dict:
        """The session's inputs so far, as a replay tape: ``replay(project, ticks, tape=...)``
        gives the same game (``quantum.runtime.godot_replay``)."""
        answer = self.request({'op': 'tape'})
        return {'ticks': answer['tick'], 'held': answer['held'],
                'tape': {int(k): [tuple(e) for e in v] for k, v in answer['tape'].items()}}

    def snapshot(self) -> dict:
        """This point of the game, to come back to with ``restore``: its tick and the inputs
        that led to it. It holds no state of its own; the game is deterministic."""
        return self.tape()

    def restore(self, snap: dict) -> dict:
        """Back to a snapshot: a fresh game replayed to its tick, headless and fast, with
        the actions it held still held. Answers the observation there."""
        self._stop()
        self._spawn()
        tape = {str(k): [list(e) for e in v] for k, v in snap['tape'].items()}
        return self.request({'op': 'replay', 'tape': tape, 'ticks': snap['ticks'], 'held': snap['held']})

    def save_tape(self, path: Union[str, Path]) -> Path:
        """The session as a replay test's input: ``{"ticks": N, "tape": {...}}`` in a JSON file."""
        t = self.tape()
        path = Path(path)
        path.write_text(json.dumps({'ticks': t['ticks'], 'tape': {str(k): [list(e) for e in v]
                                                                  for k, v in t['tape'].items()}}, indent=1),
                        encoding='utf-8')
        return path

    def _setting(self, key: str, default: int) -> int:
        text = (self.project_dir / 'project.godot').read_text(encoding='utf-8')
        m = re.search(rf'^{re.escape(key.split("/")[-1])}=(\d+)', text, re.M)
        return int(m.group(1)) if m else default

    # --- reading an observation ---

    @staticmethod
    def screen(obs: dict, kind: str) -> Optional[dict]:
        """The first screen view of a kind (``"dialogue"``, ``"menu"``, ``"hud"``) that is shown."""
        for v in obs.get('screen', []):
            if v.get('kind') == kind and v.get('shown', True):
                return v
        return None

    # --- the end ---

    def _stop(self) -> None:
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

    def close(self) -> None:
        self._stop()
        self._tmp.cleanup()
        build = getattr(self, '_build', None)
        if build:
            shutil.rmtree(build, ignore_errors=True)

    def __enter__(self) -> 'PlaySession':
        return self

    def __exit__(self, *exc) -> None:
        self.close()
