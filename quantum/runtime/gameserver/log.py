"""What a world keeps on disk: a snapshot now and then, and every input after it, in the order it ran.

    <data>/snapshot.json            the world at a tick (written aside and renamed: a crash leaves the last one)
    <data>/log/000000003000.jsonl   every join, leave and command after that tick, a line each

The world is deterministic, so the snapshot and the lines after it are the world: a restart reads the snapshot and
runs the ticks again with the same inputs (`replay`). A command is acknowledged only once its line is on the disk
(the server flushes the tick's lines, and syncs them, before it sends the tick's frames), so a restart loses none
that a player was told ran. Older segments stay, for the history of Phase 6.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from quantum.runtime.gameserver.world import World


class WorldLog:
    def __init__(self, directory: Path):
        self.directory = Path(directory)
        (self.directory / 'log').mkdir(parents=True, exist_ok=True)
        self._buffer: List[str] = []
        self._file = None

    @property
    def snapshot_path(self) -> Path:
        return self.directory / 'snapshot.json'

    def segment(self, tick: int) -> Path:
        return self.directory / 'log' / f'{tick:012d}.jsonl'

    def load(self) -> Tuple[Optional[dict], List[dict]]:
        """The last snapshot (None: the world is new) and the entries after it."""
        snap = None
        if self.snapshot_path.is_file():
            snap = json.loads(self.snapshot_path.read_text(encoding='utf-8'))
        start = snap['tick'] if snap else 0
        entries: List[dict] = []
        path = self.segment(start)
        if path.is_file():
            for line in path.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    break                     # the last line, cut by a crash: it was never acknowledged
        return snap, [e for e in entries if e['t'] > start]

    def open(self, tick: int) -> None:
        """Lines from now on go to the segment that follows the snapshot of this tick."""
        if self._file:
            self._file.close()
        self._file = open(self.segment(tick), 'a', encoding='utf-8')

    def append(self, entries: Iterable[dict]) -> None:
        for e in entries:
            self._buffer.append(json.dumps(e, separators=(',', ':'), sort_keys=True))

    def flush(self) -> None:
        if not self._buffer or self._file is None:
            return
        self._file.write('\n'.join(self._buffer) + '\n')
        self._buffer = []
        self._file.flush()
        os.fsync(self._file.fileno())

    def write_snapshot(self, world: World) -> None:
        self.flush()
        snap = world.snapshot()
        aside = self.snapshot_path.with_suffix('.json.new')
        aside.write_text(json.dumps(snap, separators=(',', ':')), encoding='utf-8')
        with open(aside, 'rb') as f:
            os.fsync(f.fileno())
        os.replace(aside, self.snapshot_path)
        self.open(snap['tick'])

    def close(self) -> None:
        self.flush()
        if self._file:
            self._file.close()
            self._file = None


def replay(world: World, entries: List[dict]) -> List[str]:
    """The entries run again on their ticks, in their order; what ran differently than the first time, said."""
    differences = []
    by_tick = {}
    for e in entries:
        by_tick.setdefault(e['t'], []).append(e)
    for tick in sorted(by_tick):
        while world.tick < tick - 1:
            world.step([])
        inputs = []
        for e in by_tick[tick]:
            if e['k'] == 'join':
                inputs.append(('join', e['a'], e.get('n')))
            elif e['k'] == 'leave':
                inputs.append(('leave', e['a']))
            elif e['k'] == 'cmd':
                inputs.append(('cmd', e['a'], e.get('s'), e.get('n'), e.get('x')))
        out = world.step(inputs)
        again = [x for x in out.entries if x['k'] == 'cmd']
        first = [e for e in by_tick[tick] if e['k'] == 'cmd']
        for a, b in zip(first, again):
            if a.get('r') != b.get('r'):
                differences.append(f'tick {tick}: {a["a"]}\'s {a.get("n")} was {a.get("r")!r}, now {b.get("r")!r}')
        world.dirty.clear()
        world.gone.clear()
    return differences
