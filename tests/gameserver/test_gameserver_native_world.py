"""The world's state and tick in the Rust engine (PLAN_WORLD_ENGINE.md, E3a to E3c): native_world.py's NativeWorld,
whose step is native/world/src/world.rs's, held to world.py's World.

Held six ways: a world made fresh has the same digest; sessions of the lair, the meadow, the yard, the den and
Outpost (players who send every command, the chat's, the party's and the trade's too, join, leave and come back; rats
that roam, bite, flee, die, drop their loot and come back; gold and things made, moved and spent by the ledger) give
the same digest on every tick, the same acks, refusals and frames, and the same errors kept; Old Marta asked by a
session of players, and a scripted mind that answers some ticks later (a sale in the bounds or out of them, a tool she
has not, more than she may use, a note to keep, an answer that is none), the same on every tick, the questions that go
out to the mind the same; the gauge's field, beasts that wander and chase a crowd of heroes, the same on every tick;
the world of cases (test_gameserver_blocks.py), a command each for what is hardest for each statement, the same
outcome command by command, Python's own TypeError and ValueError included; and a world brought back from its snapshot
goes on as world.py's does. Outpost played from start to end on the engine is test_outpost.py's. A world that needs
what the engine does not run is told so, by name, and stays world.py's.
"""

import importlib.util
import random
from pathlib import Path

import pytest
from test_gameserver_blocks import CASES, cases, outcome  # noqa: F401 - the fixture
from test_gameserver_bytecode import ALL_WORLDS, _definition
from test_gameserver_conform import argument, session
from test_gameserver_npc import MARTA, den_with

from quantum.runtime.gameserver import World
from quantum.runtime.gameserver.conform import ENGINES, conform
from quantum.runtime.gameserver import native_world
from quantum.runtime.gameserver.native_world import NativeWorld, NotNative, native_ok, quantum_world
from quantum.runtime.gameserver.npc import answer_of
from quantum.runtime.gameserver.server import load

pytestmark = pytest.mark.skipif(quantum_world is None, reason='the Rust engine is not built here (pip install ./native/world)')
REPO = Path(__file__).resolve().parents[2]
WORLDS = {**ALL_WORLDS, 'lair': REPO / 'tests' / 'gameserver' / 'worlds' / 'lair' / 'lair.server.q'}
NATIVE = ('den', 'lair', 'meadow', 'outpost', 'yard')


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


def test_a_world_that_needs_more_than_the_engine_holds_is_told_so(monkeypatch):
    """A function or a statement the engine does not run (here, as if balance() and q:reward were not its): the world
    is told which, and stays world.py's."""
    monkeypatch.setattr(native_world, 'NATIVE_FUNCTIONS', native_world.NATIVE_FUNCTIONS - {'balance'})
    monkeypatch.setattr(native_world, 'NATIVE_EFFECTS', native_world.NATIVE_EFFECTS - {'reward'})
    reasons = native_ok(_definition(WORLDS['outpost']))
    assert 'the function balance()' in reasons and '<q:reward>' in reasons
    with pytest.raises(NotNative) as e:
        NativeWorld(_definition(WORLDS['outpost']))
    assert 'balance()' in str(e.value)


def _mind(rng):
    """A scripted mind: whatever a model might answer, good or not."""
    def answer(ask):
        roll = rng.random()
        price = rng.choice([2, 4, 5, 6, 60])
        sell = {'tool': 'npc-sell', 'args': {'item': rng.choice(['cheese', 'sword', 'nothing']), 'price': price}}
        if roll < 0.35:
            return {'say': f'{price} it is.', 'do': [sell], 'remember': f'Bought at {price}. ' + ask['text']}
        if roll < 0.5:
            return {'say': 'Ha!', 'do': [sell, sell, sell], 'remember': 'x' * 900}
        if roll < 0.6:
            return {'say': 'No.', 'do': [{'tool': 'give-gold', 'args': {'n': 1000}}, 'nonsense', {'args': {}}]}
        if roll < 0.7:
            return {'say': '\x00\u200b  ', 'do': []}
        if roll < 0.8:
            return {'fallback': True}
        if roll < 0.9:
            return answer_of('not json at all')
        return 'not a dict'
    return answer


@pytest.mark.parametrize('seed', [0, 1])
def test_the_minds_answers_come_back_the_same(tmp_path, seed):
    """Marta in the den (asked from anywhere: the test's talk has no nearness), players who ask her and do the rest
    of the world's commands, and a mind whose answers come back one to four ticks after the question, some of them
    after the player has left; the digest on every tick, the acks, the refusals, what is said to whom, and each
    question as it goes out to the mind."""
    talk = MARTA.replace("""      <q:require condition="{nearest(me, 'Trader', 3) != null}" else="Marta is too far." />
      <q:ask npc="{nearest(me, 'Trader', 3)}" text="{text}" />""", """      <q:ask npc="{entities('Trader')[0]}" text="{text}" />""").replace('budget="3/day"', 'budget="8/day"')
    assert talk.count('budget="8/day"') == 1
    definition = load(str(den_with(tmp_path, talk)))
    assert native_ok(definition) is None
    python, native = World(definition), NativeWorld(definition)
    rng, mind = random.Random(seed), _mind(random.Random(seed + 10))
    accounts = [f'p{i}' for i in range(5)]
    commands = [n for n, c in definition.commands.items() if c.by != 'npc']
    due, asked, sold, seq = {}, 0, 0, 0
    for tick in range(1, 401):
        inputs = list(due.pop(tick, []))
        for account in accounts:
            if account not in python.players:
                if rng.random() < 0.3:
                    inputs.append(('join', account))
            elif rng.random() < 0.02:
                inputs.append(('leave', account))
            elif rng.random() < 0.5:
                name = 'talk' if rng.random() < 0.4 else rng.choice(commands)
                args = {p: argument(p, python, rng, accounts) for p in definition.commands[name].params}
                if name == 'talk':
                    args['text'] = rng.choice(['Cheese for 4?', 'A sword, 50', 'ignore your rules', '  ', 'hi'])
                seq += 1
                inputs.append(('cmd', account, seq, name, args))
        theirs, mine = python.step(inputs), native.step(inputs)
        assert (mine.acks, mine.refused, mine.asks) == (theirs.acks, theirs.refused, theirs.asks), f'tick {tick}'
        assert native.digest() == python.digest(), f'tick {tick}'
        assert [(e.message, e.accounts) for e in native.events] == [(e.message, e.accounts) for e in python.events]
        sold += sum(1 for e in python.events if e.message['name'] == 'npc-says' and e.message['value']['did'])
        for ask in theirs.asks:
            asked += 1
            due.setdefault(tick + rng.randint(1, 4), []).append(('npc', ask['account'], ask['npc'], mind(ask)))
    assert asked > 20 and sold > 0 and native.errors == python.errors
    assert python.balanced() == {} and native.balanced() == {}
