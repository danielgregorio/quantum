"""The world's state and tick in the Rust engine (PLAN_WORLD_ENGINE.md, E3a and E3b): native_world.py's NativeWorld,
whose step is native/world/src/world.rs's, held to world.py's World.

Held five ways: a world made fresh has the same digest; sessions of the lair, the meadow and the yard (players who
send every command, join, leave and come back; rats that roam, bite, flee, die, drop their loot and come back) give the
same digest on every tick, the same acks, refusals and frames, and the same errors kept; the gauge's field, beasts that
wander and chase a crowd of heroes, the same on every tick; the world of cases (test_gameserver_blocks.py), a command
each for what is hardest for each statement, the same outcome command by command, Python's own TypeError and
ValueError included; and a world brought back from its snapshot goes on as world.py's does. A world that needs what
the engine does not hold yet (the ledger, the chat, parties, trades, quests, NPCs: E3c) is told so, by name, and stays
world.py's.
"""

import importlib.util
import random
from pathlib import Path

import pytest
from test_gameserver_blocks import CASES, cases, outcome  # noqa: F401 - the fixture
from test_gameserver_bytecode import ALL_WORLDS, _definition
from test_gameserver_conform import session

from quantum.runtime.gameserver import World
from quantum.runtime.gameserver.conform import ENGINES, conform
from quantum.runtime.gameserver.native_world import NativeWorld, NotNative, native_ok, quantum_world
from quantum.runtime.gameserver.server import load

pytestmark = pytest.mark.skipif(quantum_world is None, reason='the Rust engine is not built here (pip install ./native/world)')
REPO = Path(__file__).resolve().parents[2]
WORLDS = {**ALL_WORLDS, 'lair': REPO / 'tests' / 'gameserver' / 'worlds' / 'lair' / 'lair.server.q'}
NATIVE = ('lair', 'meadow', 'yard')


@pytest.mark.parametrize('name', NATIVE)
def test_a_world_made_fresh_is_the_same_world(name):
    definition = _definition(WORLDS[name])
    assert native_ok(definition) is None
    python, native = World(definition), NativeWorld(definition)
    assert native.digest() == python.digest()
    assert native.snapshot() == python.snapshot()


@pytest.mark.parametrize('name', NATIVE)
@pytest.mark.parametrize('seed', [0, 1])
def test_a_session_runs_the_same_on_the_engine(name, seed, monkeypatch):
    """A session of the world on both, its digest compared on every tick; then the same session played on each, the
    errors each kept the same, word for word."""
    definition = _definition(WORLDS[name])
    entries, world = session(definition, ticks=300, players=8, seed=seed)
    report = conform(definition, None, entries, ['python', 'native'], digest_every=1)
    assert report.same, '\n'.join(map(str, report.differences[:3]))
    assert report.ticks == world.tick
    import test_gameserver_conform
    monkeypatch.setattr(test_gameserver_conform, 'World', NativeWorld)
    again, on_engine = session(definition, ticks=300, players=8, seed=seed)
    assert again == entries
    assert on_engine.errors == world.errors and on_engine.digest() == world.digest()


@pytest.mark.parametrize('name', sorted(CASES))
def test_each_statement_gives_the_same_on_the_engine(cases, name):  # noqa: F811 - the fixture
    python, native = ENGINES['python'](cases), ENGINES['native'](cases)
    assert isinstance(native.world, NativeWorld)
    for run in (python, native):
        run.step([('join', 'p1')])
    for seq, x in enumerate(CASES[name][1], 1):
        theirs = outcome(python, [('cmd', 'p1', seq, name, {'x': x})])
        mine = outcome(native, [('cmd', 'p1', seq, name, {'x': x})])
        assert mine == theirs, f'{name}({x!r})'
        if theirs[0] == 'raised':
            break


def test_a_world_brought_back_goes_on_as_it_would(monkeypatch):
    """The yard after a session, kept as its snapshot and brought back on each: the same world for a hundred ticks
    more of the same players."""
    definition = _definition(WORLDS['yard'])
    entries, world = session(definition, ticks=200, players=6, seed=3)
    snap = world.snapshot()
    python, native = World.from_snapshot(definition, snap), NativeWorld.from_snapshot(definition, snap)
    assert native.digest() == python.digest() == world.digest()
    for tick in range(100):
        inputs = [('cmd', a, 1000 + tick, 'step', {'dir': 'east' if tick % 2 else 'north'})
                  for a in sorted(python.players)]
        if tick == 50:
            inputs.append(('join', 'late'))
        assert native.step(inputs).acks == python.step(inputs).acks
        assert native.digest() == python.digest()


def test_the_gauges_field_of_beasts_runs_the_same(tmp_path):
    """scripts/gameserver-bots.py's field: beasts that wander near home, chase a hero near and give up, among a crowd
    of heroes who step every way; the digest on every tick."""
    spec = importlib.util.spec_from_file_location('bots', REPO / 'scripts' / 'gameserver-bots.py')
    bots = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bots)
    definition = load(str(bots.world_of(tmp_path, 48, 9, 40, 150)))
    assert native_ok(definition) is None
    python, native = World(definition), NativeWorld(definition)
    rng = random.Random(4)
    accounts = [f'b{i}' for i in range(40)]
    for tick in range(150):
        inputs = [('join', a) for a in accounts] if tick == 0 else \
            [('cmd', a, tick, 'step', {'dir': rng.choice(['north', 'south', 'east', 'west'])})
             for a in accounts if rng.random() < 0.4]
        if tick == 75:
            inputs += [('leave', a) for a in accounts[:10]]
        assert native.step(inputs).acks == python.step(inputs).acks
        assert native.digest() == python.digest(), f'tick {tick + 1}'
    assert any(e.get('state') == 'chase' for e in python.entities.values())


def test_a_world_that_needs_more_than_the_engine_holds_is_told_so():
    for name in ('den', 'outpost'):
        reasons = native_ok(_definition(WORLDS[name]))
        assert reasons and any('the ledger' in r for r in reasons) and any('q:chat' in r for r in reasons)
    with pytest.raises(NotNative) as e:
        NativeWorld(_definition(WORLDS['den']))
    assert 'the ledger' in str(e.value)
