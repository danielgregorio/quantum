"""The same log on two engines (PLAN_WORLD_ENGINE.md, E0): `quantum gameserver conform`.

A session is made for each world (meadow, den, Outpost): players come, send every kind of command with arguments
drawn from the world (ways, areas, items, quests, the others), leave and come back, beasts live and die. Its log, run
again on the Python engine against itself and against what the log recorded, is the same on every tick; a log or an
engine changed on one tick is found on that tick, and in what.
"""

import json
import random
import subprocess
import sys
from pathlib import Path

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.gameserver import World, read_world
from quantum.runtime.gameserver import conform as conform_module
from quantum.runtime.gameserver.conform import ENGINES, PythonEngine, conform
from quantum.runtime.gameserver.log import WorldLog

REPO = Path(__file__).resolve().parents[2]
WORLDS = {
    'meadow': REPO / 'tests' / 'gameserver' / 'worlds' / 'meadow' / 'meadow.server.q',
    'den': REPO / 'tests' / 'gameserver' / 'worlds' / 'den' / 'den.server.q',
    'outpost': REPO / 'projects' / 'outpost' / 'outpost.server.q',
}
WAYS = ['north', 'south', 'east', 'west', 'northeast', 'northwest', 'southeast', 'southwest']


def definition_of(name):
    path = WORLDS[name]
    return read_world(QuantumParser(use_cache=False).parse_file(str(path)), str(path))


def argument(name, world, rng, accounts):
    """A value for a command's parameter, drawn from what the world has (a guess by its name: some are refused)."""
    d = world.definition
    others = [e for e in world.entities.values()]
    if name == 'dir':
        return rng.choice(WAYS)
    if name == 'to':
        areas = list(d.map.areas)
        return rng.choice(areas + accounts) if areas else rng.choice(accounts)
    if name in ('who', 'npc'):
        return rng.choice(others)['id'] if others else 'nobody'
    if name == 'item':
        return rng.choice(list(d.items) or ['stone'])
    if name in ('name', 'quest'):
        return rng.choice(list(d.quests) or ['none'])
    if name == 'channel':
        return rng.choice(['say', 'yell', 'help', 'trade'])
    if name in ('gold', 'amount', 'price'):
        return rng.randint(0, 60)
    if name == 'items':
        return {rng.choice(list(d.items)): 1} if d.items and rng.random() < 0.5 else {}
    return rng.choice(['hello', 'forty, and not a coin less', 'rats!', 'wolves at the gate'])


def session(definition, ticks=240, players=6, seed=11, digest_every=0):
    """A world played by players who send whatever they like: the log's lines, in order, as the server writes them."""
    rng = random.Random(seed)
    world = World(definition)
    accounts = [f'p{i}' for i in range(players)]
    commands = [n for n, c in definition.commands.items() if c.by != 'npc']
    entries = []
    for _ in range(ticks):
        inputs, seq = [], world.tick * 10
        for account in accounts:
            if account not in world.players:
                if rng.random() < 0.3:
                    inputs.append(('join', account))
                continue
            if rng.random() < 0.02:
                inputs.append(('leave', account))
                continue
            if rng.random() < 0.6:
                name = rng.choice(['step'] * 4 + commands) if 'step' in commands else rng.choice(commands)
                args = {p: argument(p, world, rng, accounts) for p in definition.commands[name].params}
                seq += 1
                inputs.append(('cmd', account, seq, name, args))
        out = world.step(inputs)
        entries.extend(out.entries)
        if digest_every and world.tick % digest_every == 0:
            entries.append({'t': world.tick, 'k': 'digest', 'd': world.digest()})
        world.dirty.clear()
        world.gone.clear()
    return entries, world


@pytest.mark.parametrize('name', sorted(WORLDS))
def test_the_python_engine_agrees_with_itself_and_with_the_record(name):
    """Two runs of the same log give the same digests, acks, refusals and frames on every tick; one run gives each
    command the result the log recorded, and the world the digests it recorded."""
    definition = definition_of(name)
    entries, world = session(definition, digest_every=20)
    assert {e['k'] for e in entries} >= {'join', 'cmd', 'digest'}
    assert any(e['k'] == 'cmd' and e['r'] == 'ok' for e in entries)            # some ran
    assert any(e['k'] == 'cmd' and e['r'] != 'ok' for e in entries)            # and some were refused
    twice = conform(definition, None, entries, ['python', 'python'], digest_every=10)
    assert twice.same, '\n'.join(map(str, twice.differences))
    assert twice.ticks == world.tick and twice.digests == world.tick // 10
    recorded = conform(definition, None, entries, ['python'])
    assert recorded.same, '\n'.join(map(str, recorded.differences))
    assert recorded.digests == world.tick // 20
    assert recorded.commands == len([e for e in entries if e['k'] == 'cmd'])


def test_a_result_or_a_digest_changed_in_the_log_is_found_on_its_tick():
    definition = definition_of('meadow')
    entries, _ = session(definition, ticks=120, digest_every=10)
    forged = json.loads(json.dumps(entries))
    cmd = next(e for e in forged if e['k'] == 'cmd' and e['t'] > 40)
    cmd['r'] = 'A forged result.'
    report = conform(definition, None, forged, ['python'])
    (first,) = report.differences
    assert first.tick == cmd['t'] and first.what.startswith(f"result of {cmd['a']}'s {cmd['n']}")
    assert first.first == 'A forged result.' and report.ticks == cmd['t']               # it stops at the first

    forged = json.loads(json.dumps(entries))
    digest = next(e for e in forged if e['k'] == 'digest' and e['t'] == 70)
    digest['d'] = '0' * 64
    (first,) = conform(definition, None, forged, ['python']).differences
    assert first.tick == 70 and first.what == 'recorded digest'


class _Drifting(PythonEngine):
    """An engine that is the Python one but for a field written on tick 33: what a wrong engine would be like."""
    name = 'drifting'

    def step(self, inputs):
        out = super().step(inputs)
        if self.world.tick == 33:
            hero = self.world.entities[sorted(self.world.players.values())[0]]
            hero['_drift'] = True                     # the world's own field: no player sees it, its digest does
        return out


class _Loud(PythonEngine):
    """An engine that tells one player something more on tick 50."""
    name = 'loud'

    def step(self, inputs):
        out = super().step(inputs)
        if self.world.tick == 50:
            account = sorted(out['frames'] or self.world.players)[0]
            out['frames'].setdefault(account, []).append({'type': 'tick', 'tick': 50, 'extra': True})
        return out


def test_two_engines_that_differ_are_told_apart_on_the_tick_they_part(monkeypatch):
    monkeypatch.setitem(ENGINES, 'drifting', _Drifting)
    monkeypatch.setitem(ENGINES, 'loud', _Loud)
    definition = definition_of('den')
    entries, _ = session(definition, ticks=80)
    (first,) = conform(definition, None, entries, ['python', 'drifting'], digest_every=1).differences
    assert (first.tick, first.what) == (33, 'digest')
    # compared every ten ticks, the drift is found on the tick of the next comparison
    (first,) = conform(definition, None, entries, ['python', 'drifting'], digest_every=10).differences
    assert (first.tick, first.what) == (40, 'digest')
    (first,) = conform(definition, None, entries, ['python', 'loud'], digest_every=0).differences
    assert first.tick == 50 and first.what.startswith('frames of ')
    # all of them, when asked: the loud one differs on that tick only
    report = conform(definition, None, entries, ['python', 'loud'], digest_every=0, stop_at_first=False)
    assert [d.tick for d in report.differences] == [50] and report.ticks == 80


def test_a_world_from_its_snapshot_and_log_and_the_command_line(tmp_path):
    """What a server wrote (a snapshot, the lines after it, the digests it recorded) is what `quantum gameserver
    conform` reads: the same, against the record and against the engine itself; a line forged, and it says where."""
    definition = definition_of('meadow')
    entries, world = session(definition, ticks=60, digest_every=15)
    snap = world.snapshot()                                   # the world as a server would have kept it at 60
    log = WorldLog(tmp_path)
    log.write_snapshot(world)                                 # opens the segment after it
    rest = World.from_snapshot(definition, snap)
    rng = random.Random(3)
    lines = []
    for _ in range(40):
        inputs = [('cmd', a, rest.tick, 'step', {'dir': rng.choice(WAYS)}) for a in sorted(rest.players)]
        out = rest.step(inputs)
        lines.extend(out.entries)
        if rest.tick % 10 == 0:
            lines.append({'t': rest.tick, 'k': 'digest', 'd': rest.digest()})
        rest.dirty.clear()
        rest.gone.clear()
    log.append(lines)
    log.close()

    def run(*more):
        return subprocess.run([sys.executable, '-m', 'quantum.cli.runner', 'gameserver', 'conform',
                               str(WORLDS['meadow']), '--data', str(tmp_path), *more],
                              cwd=REPO, capture_output=True, text=True, timeout=120)
    done = run()
    assert done.returncode == 0, done.stdout + done.stderr
    assert done.stdout.startswith('[OK] python against the record: 40 ticks from 60') and '4 digests' in done.stdout
    done = run('--against', 'python', '--digest-every', '5')
    assert done.returncode == 0 and '[OK] python against python: 40 ticks from 60' in done.stdout
    segment = next((tmp_path / 'log').glob('*.jsonl'))
    first_ok = next(json.loads(line)['t'] for line in segment.read_text().splitlines() if '"r":"ok"' in line)
    segment.write_text(segment.read_text().replace('"r":"ok"', '"r":"forged"', 1))
    done = run()
    assert done.returncode == 1 and done.stdout.startswith('[DIFFERENT] python against the record')
    assert f'tick {first_ok}: result of' in done.stdout
    assert run('--engine', 'nope').stdout.startswith("[ERROR] no engine 'nope'")
    assert conform_module.load_data(tmp_path)[0]['tick'] == 60


def test_a_server_writes_the_digests_conform_checks(tmp_path):
    """`quantum gameserver run --digest-every`: the world's digest in its log, every so often."""
    from quantum.runtime.gameserver.server import WorldServer

    import asyncio

    definition = definition_of('meadow')
    server = WorldServer(definition, step=True, quiet=True, data_dir=tmp_path, digest_every=0.5)
    server._restore()

    async def ticks():
        server.inbox.append(('join', 'ana'))
        for k in range(12):
            if k > 1:
                server.inbox.append(('cmd', 'ana', k, 'step', {'dir': WAYS[k % 4]}))
            await server._tick()
    asyncio.run(ticks())
    server.log.close()
    snap, entries = conform_module.load_data(tmp_path)
    assert [e['t'] for e in entries if e['k'] == 'digest'] == [5, 10]
    report = conform(definition, snap, entries, ['python'])
    assert report.same and report.digests == 2 and report.commands == 10
