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


def replay_peers(project_dir: Path, ticks: int, tapes: List[Optional[Tape]], port: int = 17777,
                 binary: Optional[Path] = None, timeout: float = 300) -> List[dict]:
    """Run the project under qg:multiplayer: one Godot per player, on localhost.

    The first tape is player 1's, who hosts; the others join in order. Each
    tape names the actions as a single-player tape does (``up``, ``jump``):
    the lockstep turns them into that player's actions, ``delay`` ticks
    later, on every peer. Returns the state each peer dumped at ``ticks``
    — the same dictionary on every peer, or the game is not deterministic.
    """
    import subprocess
    import time
    from quantum.runtime.godot_bin import ensure_godot
    project_dir = Path(project_dir)
    binary = Path(binary) if binary else ensure_godot()
    with tempfile.TemporaryDirectory(prefix='quantum-peers-') as tmp:
        procs = []
        outs = []
        for i, tape in enumerate(tapes):
            tape_path = Path(tmp) / f'tape{i}.json'
            out_path = Path(tmp) / f'state{i}.json'
            persist = Path(tmp) / f'persist{i}'
            persist.mkdir()
            tape_path.write_text(json.dumps({str(k): [list(e) for e in v] for k, v in (tape or {}).items()}),
                                 encoding='utf-8')
            peer_arg = f'--q-host={port}' if i == 0 else f'--q-join=127.0.0.1:{port}'
            log = open(Path(tmp) / f'log{i}.txt', 'w', encoding='utf-8')
            procs.append((subprocess.Popen(
                [str(binary), '--headless', '--path', str(project_dir), '-s', str(REPLAY_SCRIPT), '--',
                 f'--ticks={ticks}', f'--tape={tape_path}', f'--out={out_path}', f'--persist-dir={persist}',
                 peer_arg], stdout=log, stderr=subprocess.STDOUT), log))
            outs.append(out_path)
            if i == 0:
                time.sleep(1.0)   # the host listens before anyone joins
        deadline = time.time() + timeout
        for proc, log in procs:
            remaining = max(1.0, deadline - time.time())
            try:
                proc.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                for p_, _ in procs:
                    p_.kill()
                raise ReplayError(f'a peer did not finish within {timeout}s')
            log.close()
        states = []
        for i, out_path in enumerate(outs):
            output = (Path(tmp) / f'log{i}.txt').read_text(encoding='utf-8')
            errors = script_errors(output)
            if not out_path.is_file():
                raise ReplayError(f'peer {i + 1} wrote no state' + (': ' + '; '.join(errors) if errors else f'\n{output}'))
            if errors:
                raise ReplayError(f'peer {i + 1}: ' + '; '.join(errors))
            states.append(json.loads(out_path.read_text(encoding='utf-8')))
        return states
