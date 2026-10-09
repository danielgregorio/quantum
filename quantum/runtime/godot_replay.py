"""Replay an input tape through a built game, headless, and read its state.

The test of a game: the same tape, the same number of physics ticks, the
same state. ``replay()`` runs ``godot_replay.gd`` (next to this file) as the
main loop of a Godot project and returns the JSON it dumps: every node with
a ``quantum_state()`` method, keyed by its path from the scene root.

A tape is ``{tick: [(action, pressed), ...]}``; ``tape_from_holds`` builds
one from "hold *action* from tick a to tick b" spans, which is how a test
reads best.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from quantum.runtime.godot_bin import run_godot, script_errors

REPLAY_SCRIPT = Path(__file__).with_name('godot_replay.gd')

Tape = Dict[int, List[Tuple[str, bool]]]


class ReplayError(RuntimeError):
    """The replay did not produce a state: Godot reported errors."""


def tape_from_holds(holds: Iterable[Tuple[str, int, int]]) -> Tape:
    """``[("right", 0, 10), ("jump", 5, 8)]``: pressed on the first tick,
    released on the second (exclusive)."""
    tape: Tape = {}
    for action, start, end in holds:
        tape.setdefault(start, []).append((action, True))
        tape.setdefault(end, []).append((action, False))
    return tape


def replay(project_dir: Path, ticks: int, tape: Optional[Tape] = None,
           binary: Optional[Path] = None, timeout: float = 300,
           persist_dir: Optional[Path] = None) -> dict:
    """Run the project's main scene for ``ticks`` physics ticks under ``tape``.

    ``persist_dir`` is where the game's persisted state (``q:set
    persist="true"``) is read and written; a fresh temporary directory
    when not given, so a replay starts from nothing.
    """
    project_dir = Path(project_dir)
    with tempfile.TemporaryDirectory(prefix='quantum-replay-') as tmp:
        tape_path = Path(tmp) / 'tape.json'
        out_path = Path(tmp) / 'state.json'
        tape_path.write_text(json.dumps({str(k): [list(e) for e in v]
                                         for k, v in (tape or {}).items()}),
                             encoding='utf-8')
        persist = Path(persist_dir) if persist_dir else Path(tmp) / 'persist'
        persist.mkdir(parents=True, exist_ok=True)
        result = run_godot(['--path', str(project_dir), '-s', str(REPLAY_SCRIPT), '--',
                            f'--ticks={ticks}', f'--tape={tape_path}', f'--out={out_path}',
                            f'--persist-dir={persist}'],
                           binary=binary, timeout=timeout)
        output = result.stdout + result.stderr
        errors = script_errors(output)
        if not out_path.is_file():
            raise ReplayError('the replay wrote no state' +
                              (': ' + '; '.join(errors) if errors else f'\n{output}'))
        if errors:
            raise ReplayError('; '.join(errors))
        return json.loads(out_path.read_text(encoding='utf-8'))
