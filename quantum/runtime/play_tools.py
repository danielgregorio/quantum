"""The play protocol's tools (PLAN_PLAY_PROTOCOL.md, phase 4): sessions by id.

``PlayTools`` is what the MCP server (``play_mcp.py``) and the console
(``quantum play``) both stand on: it opens games by name, keeps their
``PlaySession``s, and answers each call with a compact observation, small
enough to read in a conversation. Nothing here imports the MCP package.

    tools = PlayTools()
    start = tools.start('rpg')                    # {"session": "s1", "tick": 0, ...}
    tools.until('s1', 'talking', hold=['right'])
    tools.end('s1')
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Union

from quantum.runtime.godot_play import PlayError, PlaySession

REPO = Path(__file__).resolve().parents[2]


class PlayTools:
    """Open games, play them through their sessions, close them."""

    def __init__(self, projects: Optional[Union[str, Path]] = None, binary: Optional[Path] = None):
        self.projects = Path(projects) if projects else REPO / 'projects'
        self.binary = binary
        self.sessions: Dict[str, PlaySession] = {}
        self.snapshots: Dict[str, dict] = {}
        self._count = 0
        self._tmp = Path(tempfile.mkdtemp(prefix='quantum-play-tools-'))

    # --- the games ---

    def games(self) -> List[dict]:
        """Every game of the projects folder: its name, and what projects/games.json says of it."""
        about = {}
        listing = self.projects / 'games.json'
        if listing.is_file():
            about = {g['name']: g for g in json.loads(listing.read_text(encoding='utf-8')).get('games', [])}
        out = []
        for q in sorted(self.projects.glob('*/*.q')):
            if q.stem != q.parent.name:
                continue
            g = about.get(q.stem, {})
            out.append({'game': q.stem, 'title': g.get('title', q.stem), 'players': g.get('players', ''),
                        'about': g.get('blurb', ''), 'controls': g.get('controls', '')})
        return out

    def _source(self, game: str) -> Path:
        path = Path(game)
        if path.suffix == '.q' and path.is_file():
            return path
        q = self.projects / game / f'{game}.q'
        if not q.is_file():
            names = ', '.join(g['game'] for g in self.games())
            raise PlayError(f'no game named {game!r} (the games: {names})')
        return q

    # --- sessions ---

    def start(self, game: str, frames: bool = False) -> dict:
        """Opens a game (a name from ``games()``, or a .q) and answers its first observation,
        with the game's actions and its first scene's map."""
        session = PlaySession.open(self._source(game), binary=self.binary, frames=frames)
        self._count += 1
        sid = f's{self._count}'
        self.sessions[sid] = session
        obs = session.observe()
        out = {'session': sid, **self.compact(obs), 'controls': obs.get('controls', [])}
        out['map'] = session.map()
        return out

    def _session(self, sid: str) -> PlaySession:
        if sid not in self.sessions:
            raise PlayError(f'no session {sid!r} (open: {", ".join(self.sessions) or "none"})')
        return self.sessions[sid]

    def observe(self, sid: str) -> dict:
        return self.compact(self._session(sid).observe())

    def act(self, sid: str, hold: List[str] = (), tap: List[str] = (), press: List[str] = (),
            release: List[str] = (), cursor: Optional[List[float]] = None, ticks: int = 1) -> dict:
        return self.compact(self._session(sid).act(hold=hold, tap=tap, press=press, release=release,
                                                   cursor=cursor, ticks=ticks))

    def until(self, sid: str, condition: Union[str, List[str], dict], hold: List[str] = (), tap: List[str] = (),
              press: List[str] = (), release: List[str] = (), cursor: Optional[List[float]] = None,
              max_ticks: int = 600) -> dict:
        return self.compact(self._session(sid).until(condition, hold=hold, tap=tap, press=press, release=release,
                                                     cursor=cursor, max_ticks=max_ticks))

    def view(self, sid: str) -> dict:
        return self._session(sid).view()

    def map(self, sid: str) -> Optional[dict]:
        return self._session(sid).map()

    def frame(self, sid: str, path: Optional[str] = None) -> dict:
        """The picture on the screen as a PNG (a session started with frames)."""
        session = self._session(sid)
        target = Path(path) if path else self._tmp / f'{sid}-{session.last["tick"] if session.last else 0}.png'
        return session.frame(target)

    def snapshot(self, sid: str) -> dict:
        snap = self._session(sid).snapshot()
        name = f'{sid}:{len([k for k in self.snapshots if k.startswith(sid + ":")]) + 1}'
        self.snapshots[name] = snap
        return {'snapshot': name, 'tick': snap['ticks']}

    def restore(self, sid: str, snapshot: str) -> dict:
        if snapshot not in self.snapshots or not snapshot.startswith(sid + ':'):
            raise PlayError(f'no snapshot {snapshot!r} of session {sid!r}')
        return self.compact(self._session(sid).restore(self.snapshots[snapshot]))

    def tape(self, sid: str, path: str) -> dict:
        """Saves the session as a replay tape (a test, as it is)."""
        saved = self._session(sid).save_tape(path)
        return {'tape': str(saved), 'ticks': self._session(sid).tape()['ticks']}

    def end(self, sid: str) -> dict:
        self._session(sid).close()
        del self.sessions[sid]
        for k in [k for k in self.snapshots if k.startswith(sid + ':')]:
            del self.snapshots[k]
        return {'ended': sid}

    def close(self) -> None:
        for sid in list(self.sessions):
            self.end(sid)

    # --- what goes back to the agent ---

    @staticmethod
    def compact(obs: dict) -> dict:
        """An observation without what does not change or is told elsewhere: the actions (in
        ``start``), the cumulative list of sounds (each is an event), the held actions when none;
        an event repeated in a row is told once."""
        out = {k: v for k, v in obs.items() if k not in ('controls',)}
        state = dict(out.get('state', {}))
        state.pop('sounds', None)
        out['state'] = state
        if not out.get('held'):
            out.pop('held', None)
        if out.get('events'):
            out['events'] = PlayTools.squeeze(out['events'])
        else:
            out.pop('events', None)
        return out

    @staticmethod
    def squeeze(events: List[dict]) -> List[dict]:
        """The same event again and again (a walker bumping a wall each step) as one, with
        ``times`` and the tick of the last (``until``). A number that changes tick after tick
        (a countdown) is one ``set`` too, from its first value to its last, even when other
        variables change between; a text (whose turn it is) is told at each change."""
        out: List[dict] = []
        for e in events:
            if e.get('kind') == 'set' and PlayTools._counter(e) and PlayTools._counts_on(out, e):
                continue
            same = {k: v for k, v in e.items() if k != 'tick'}
            if out:
                last = {k: v for k, v in out[-1].items() if k not in ('tick', 'times', 'until')}
                if last == same:
                    out[-1]['times'] = out[-1].get('times', 1) + 1
                    out[-1]['until'] = e['tick']
                    continue
            out.append(dict(e))
        return out

    @staticmethod
    def _counter(e: dict) -> bool:
        return all(isinstance(e.get(k), (int, float)) and not isinstance(e.get(k), bool) for k in ('from', 'to'))

    @staticmethod
    def _counts_on(out: List[dict], e: dict) -> bool:
        """Folds a ``set`` into the last one of the same variable, back through the run of
        ``set``s it ends (any other event between keeps them apart)."""
        for told in reversed(out):
            if told.get('kind') != 'set':
                return False
            if told.get('name') == e.get('name'):
                told['to'] = e.get('to')
                told['times'] = told.get('times', 1) + 1
                told['until'] = e['tick']
                return True
        return False
