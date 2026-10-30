"""The same log on two engines (PLAN_WORLD_ENGINE.md): where they part, if they part.

A world is deterministic, so a snapshot and the inputs after it are the world. Two engines that run the same world
must give, on every tick, the same state (its digest), the same acks and refusals, the same joins, leaves and full
worlds, and the same frames to each player (frames.py): then a player cannot tell them apart. `conform` runs a
world's log on each engine, tick by tick, and names the first tick where they differ, and in what.

With one engine it runs the log against what the log itself recorded: each command's result, and the world's digest
where the server wrote one (`quantum gameserver run --digest-every SECONDS`).

    quantum gameserver conform world.server.q --data .quantum/gameserver/world                 # against the record
    quantum gameserver conform world.server.q --data DIR --engine python --against rust        # two engines
    quantum gameserver conform world.server.q --data DIR --engine python --against machine     # the rules, as bytecode
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from quantum.runtime.gameserver.frames import Frames, Seen
from quantum.runtime.gameserver.model import WorldDef
from quantum.runtime.gameserver.world import World


class PythonEngine:
    """The reference engine: the world of world.py, the frames of frames.py, every player connected while in it."""
    name = 'python'
    world_class = World

    def __init__(self, definition: WorldDef, snapshot: Optional[dict] = None):
        kind = self.world_class
        self.world = kind.from_snapshot(definition, snapshot) if snapshot else kind(definition)
        self.frames = Frames(definition)
        self.seen: Dict[str, Seen] = {a: Seen(a) for a in self.world.players}

    @property
    def tick(self) -> int:
        return self.world.tick

    def step(self, inputs: List[tuple]) -> dict:
        """One tick: what came out of it, as the two engines are compared."""
        for item in inputs:
            if item[0] == 'join' and item[1] not in self.seen:
                self.seen[item[1]] = Seen(item[1])
        out = self.world.step(inputs)
        for account in out.full:
            self.seen.pop(account, None)
        frames = self.frames.tick(self.world, out, self.seen)
        for account in out.left:
            self.seen.pop(account, None)
        self.world.dirty.clear()
        self.world.gone.clear()
        return {'acks': out.acks, 'refused': out.refused, 'joined': out.joined, 'left': sorted(out.left),
                'full': sorted(out.full), 'entries': out.entries, 'frames': frames}

    def digest(self) -> str:
        return self.world.digest()


ENGINES: Dict[str, Callable[..., Any]] = {'python': PythonEngine}


def _with_rust() -> None:
    from quantum.runtime.gameserver import native
    if native.available():
        from quantum.runtime.gameserver.machine import MachineWorld

        class MachineEngine(PythonEngine):
            """The world's rules as bytecode on the engine's machine (machine.py), the rest Python's."""
            name = 'machine'
            world_class = MachineWorld

        ENGINES['rust'] = native.rust_engine()
        ENGINES['machine'] = MachineEngine


_with_rust()


@dataclass
class Difference:
    tick: int
    what: str                    # digest, acks, refused, joined, left, full, frames of <account>, result, recorded digest
    first: Any
    second: Any

    def __str__(self) -> str:
        def short(v: Any) -> str:
            text = json.dumps(v, sort_keys=True, default=str) if not isinstance(v, str) else v
            return text if len(text) <= 300 else text[:300] + '...'
        return f'tick {self.tick}: {self.what} differ\n  first:  {short(self.first)}\n  second: {short(self.second)}'


@dataclass
class Report:
    engines: List[str]
    start: int
    ticks: int = 0                                   # ticks run on each engine
    digests: int = 0                                 # digests compared
    commands: int = 0
    differences: List[Difference] = field(default_factory=list)

    @property
    def same(self) -> bool:
        return not self.differences


def inputs_of(entries: List[dict]) -> List[tuple]:
    """A tick's lines of the log as the world's inputs, in the order they ran (log.replay reads them the same)."""
    inputs = []
    for e in entries:
        if e['k'] == 'join':
            inputs.append(('join', e['a'], e.get('n')))
        elif e['k'] == 'leave':
            inputs.append(('leave', e['a']))
        elif e['k'] == 'cmd':
            inputs.append(('cmd', e['a'], e.get('s'), e.get('n'), e.get('x')))
        elif e['k'] == 'npc':
            inputs.append(('npc', e['a'], e.get('n'), e.get('x')))
    return inputs


def _plain(value: Any) -> Any:
    """A value compared as JSON would carry it: a tuple is a list, a dict's keys are texts."""
    return json.loads(json.dumps(value, sort_keys=True, default=str))


def conform(definition: WorldDef, snapshot: Optional[dict], entries: List[dict], engines: List[str],
            digest_every: int = 1, until: Optional[int] = None, stop_at_first: bool = True) -> Report:
    """Runs the entries on each engine (one: against the record), tick by tick, and compares what came out.
    digest_every: the digests are compared every so many ticks (a digest copies the whole world; 0: only at the end).
    until: the last tick to run (the last of the log, if not given)."""
    runs = [ENGINES[name](definition, snapshot) for name in engines]
    start = runs[0].tick
    report = Report(engines=list(engines), start=start)
    by_tick: Dict[int, List[dict]] = {}
    for e in entries:
        by_tick.setdefault(e['t'], []).append(e)
    last = until if until is not None else max(by_tick, default=start)

    def differ(tick: int, what: str, a: Any, b: Any) -> bool:
        if _plain(a) == _plain(b):
            return False
        report.differences.append(Difference(tick, what, a, b))
        return True

    for tick in range(start + 1, last + 1):
        lines = by_tick.get(tick, [])
        inputs = inputs_of(lines)
        outs = [run.step(inputs) for run in runs]
        report.ticks += 1
        found = False
        if len(runs) == 1:                          # against the record: each command's result, and its digests
            ran = [x for x in outs[0]['entries'] if x['k'] == 'cmd']
            recorded = [e for e in lines if e['k'] == 'cmd']
            report.commands += len(recorded)
            for a, b in zip(recorded, ran):
                if a.get('r') != b.get('r'):
                    found |= differ(tick, f"result of {a['a']}'s {a.get('n')} (seq {a.get('s')})", a.get('r'),
                                    b.get('r'))
            for e in lines:
                if e['k'] == 'digest':
                    report.digests += 1
                    found |= differ(tick, 'recorded digest', e['d'], runs[0].digest())
        else:
            a, b = outs[0], outs[1]
            report.commands += len([e for e in lines if e['k'] == 'cmd'])
            for key in ('acks', 'refused', 'joined', 'left', 'full'):
                found |= differ(tick, key, a[key], b[key])
            for account in sorted(set(a['frames']) | set(b['frames'])):
                found |= differ(tick, f'frames of {account}', a['frames'].get(account), b['frames'].get(account))
            if (digest_every and tick % digest_every == 0) or tick == last:
                report.digests += 1
                found |= differ(tick, 'digest', runs[0].digest(), runs[1].digest())
        if found and stop_at_first:
            break
    return report


def load_data(directory: Path):
    """A world's data directory as conform reads it: the last snapshot, and every line after it."""
    from quantum.runtime.gameserver.log import WorldLog
    log = WorldLog.__new__(WorldLog)            # read only: nothing is made in the directory
    log.directory = Path(directory)
    return log.load()


def main(args) -> int:
    from quantum.runtime.gameserver.errors import GameServerError
    from quantum.runtime.gameserver.server import load

    try:
        definition = load(args.file)
    except GameServerError as e:
        print(f'[ERROR] {e}')
        return 1
    directory = Path(args.data) if args.data else Path('.quantum') / 'gameserver' / definition.name
    if not (directory / 'log').is_dir():
        print(f'[ERROR] {directory}: no log of the world here (its --data directory)')
        return 1
    engines = [args.engine] + ([args.against] if args.against else [])
    unknown = [e for e in engines if e not in ENGINES]
    if unknown:
        from quantum.runtime.gameserver.native import BUILD
        if unknown[0] == 'rust':
            print(f'[ERROR] the Rust engine is not built here ({BUILD})')
        else:
            print(f'[ERROR] no engine {unknown[0]!r}: the engines are {", ".join(sorted(ENGINES))}')
        return 1
    snapshot, entries = load_data(directory)
    report = conform(definition, snapshot, entries, engines, digest_every=args.digest_every)
    against = f'{engines[0]} against {engines[1]}' if len(engines) == 2 else f'{engines[0]} against the record'
    if report.same:
        print(f'[OK] {against}: {report.ticks} ticks from {report.start}, {report.commands} commands, '
              f'{report.digests} digests, the same')
        return 0
    print(f'[DIFFERENT] {against}, {report.ticks} ticks from {report.start}:')
    for d in report.differences:
        print(str(d))
    return 1
