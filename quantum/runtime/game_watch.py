"""`quantum run game.q --watch`: play the game, and see each change of the .q in it at once.

The game runs in Godot through ``godot_watch.gd``, which records what the
person presses. The watcher looks at the .q and the files beside it (the
pictures, the sounds, a Tiled map) twice a second. When one changes, it
builds again; a build the compiler refuses is printed and the game plays on
as it was. A new build asks the game to stop (a stamp file), and starts it
again on the new build with what was pressed so far: the game plays that
tape again, quickly, and the person is back at the same tick, under the new
rules. The replay tests rely on the same thing: the same inputs give the
same game. So that they do here too, every run starts from the same fresh
saves.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional

WATCH_SCRIPT = Path(__file__).with_name('godot_watch.gd')


class GameWatch:
    """A game played while its .q is edited."""

    def __init__(self, q_file: Path, build: Callable[[], Optional[Path]], binary: Optional[Path] = None,
                 headless: bool = False, poll: float = 0.5, say: Callable[[str], None] = print,
                 extra: List[str] = ()):
        self.q_file = Path(q_file).resolve()
        self.build = build            # builds the project; its folder, or None when the compiler refused
        self.binary = binary
        self.headless = headless      # the tests: no window
        self.extra = list(extra)      # the tests: more arguments for godot_watch.gd (--dump=)
        self.poll = poll
        self.say = say
        self.work = Path(tempfile.mkdtemp(prefix='quantum-watch-'))
        self.tape = self.work / 'tape.json'
        self.project: Optional[Path] = None
        self.process: Optional[subprocess.Popen] = None
        self.reloads = 0

    # --- what is watched ---

    def files(self) -> Dict[Path, float]:
        """The .q and the files of its folder, but the builds (godot/) and hidden ones: when each changed."""
        out = {self.q_file: self.q_file.stat().st_mtime}
        for f in self.q_file.parent.rglob('*'):
            rel = f.relative_to(self.q_file.parent).parts
            if f.is_file() and not any(p.startswith('.') or p == 'godot' for p in rel):
                out[f] = f.stat().st_mtime
        return out

    # --- the game ---

    def command(self, resume: bool) -> List[str]:
        from quantum.runtime.godot_bin import ensure_godot
        binary = self.binary or ensure_godot()
        persist = self.work / 'saves'
        shutil.rmtree(persist, ignore_errors=True)    # the same fresh saves every run: the replay is the same game
        persist.mkdir()
        cmd = [str(binary)] + (['--headless'] if self.headless else []) + [
            '--path', str(self.project), '-s', str(WATCH_SCRIPT), '--',
            f'--tape-out={self.tape}', f'--stamp={self.stamp()}', f'--persist-dir={persist}']
        if resume and self.tape.is_file():
            cmd.append(f'--resume={self.tape}')
        return cmd

    def stamp(self) -> Path:
        return self.work / 'reload'

    def start(self, resume: bool = False) -> None:
        self.process = subprocess.Popen(self.command(resume) + self.extra, stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL)

    def stop_for_reload(self, timeout: float = 10.0) -> None:
        """The game writes what was pressed and quits; the stamp asks it to."""
        if self.process is None or self.process.poll() is not None:
            return
        self.stamp().write_text('reload', encoding='utf-8')
        try:
            self.process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()

    # --- the loop ---

    def reload(self) -> bool:
        """A change: build again; on a new build, the game again where it was. Whether it reloaded."""
        project = self.build()
        if project is None:
            return False
        self.project = Path(project)
        self.stop_for_reload()
        self.start(resume=True)
        self.reloads += 1
        self.say(f'[RELOAD] {self.q_file.name}: the game goes on where it was, under the new build')
        return True

    def run(self, max_reloads: Optional[int] = None) -> int:
        project = self.build()
        if project is None:
            return 1
        self.project = Path(project)
        self.start()
        self.say(f'[WATCH] playing {self.q_file.name}; save it to see the change in the game (Ctrl+C stops)')
        seen = self.files()
        try:
            while self.process is not None and self.process.poll() is None:
                time.sleep(self.poll)
                now = self.files()
                if now != seen:
                    seen = now
                    self.reload()
                    if max_reloads is not None and self.reloads >= max_reloads:
                        break
        except KeyboardInterrupt:
            pass
        finally:
            if self.process is not None and self.process.poll() is None and max_reloads is None:
                self.process.terminate()
        return 0


def build_game(q_file: Path, say: Callable[[str], None] = print, out: Optional[Path] = None) -> Optional[Path]:
    """The .q built as `quantum run` builds it (into projects/<id>/godot, or `out`); None, with the
    compiler's words, when it is refused."""
    from quantum.core.parser import QuantumParser, QuantumParseError
    from quantum.runtime.game_builder import GameBuilder, GameBuildError
    from quantum.runtime.godot import GameCompileError
    q_file = Path(q_file).resolve()
    try:
        app = QuantumParser(use_cache=False).parse_file(str(q_file))
        if getattr(app, 'app_type', None) != 'game':
            say(f'[ERROR] {q_file.name} is not a game (type="game"): --watch plays games')
            return None
        return Path(GameBuilder(source_dir=str(q_file.parent)).build_to_file(app, str(out) if out else None))
    except (QuantumParseError, GameCompileError, GameBuildError) as e:
        say(f'[ERROR] {e} (the game plays on as it was)')
        return None


def watch_game(q_file: str) -> int:
    """`quantum run game.q --watch`."""
    path = Path(q_file)
    return GameWatch(path, lambda: build_game(path)).run()
