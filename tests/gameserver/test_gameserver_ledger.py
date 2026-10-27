"""The game server, Phase 4 of PLAN_GAME_SERVER.md: the ledger.

Gold and things are made, moved and spent only by q:give, q:pay, q:take and q:loot, and the world's books count
them by where it happened. A hero's gold and bag are private fields no q:set may write. A command refused makes and
spends nothing. And after an hour of bots buying, selling, eating, tipping and killing rats, what the holders have
of each thing is exactly what was made of it less what was spent.
"""

import random
from pathlib import Path

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.gameserver import GameServerError, World, read_world

DEN = Path(__file__).resolve().parent / 'worlds' / 'den' / 'den.server.q'
TMX = DEN.parent / 'den.tmx'


def den_with(tmp_path, more=''):
    (tmp_path / 'den.tmx').write_text(TMX.read_text())
    path = tmp_path / 'den.server.q'
    path.write_text(DEN.read_text().replace('</q:gameserver>', more + '\n  </q:gameserver>'))
    return World(read_world(QuantumParser(use_cache=False).parse_file(str(path)), str(path)))


def den():
    return World(read_world(QuantumParser(use_cache=False).parse_file(str(DEN)), str(DEN)))


def cmd(world, account, name, **args):
    world.counter = getattr(world, 'counter', 0) + 1
    out = world.step([('cmd', account, world.counter, name, args)])
    return out.acks.get(account) == [world.counter], (out.refused.get(account) or [{}])[0].get('reason')


def test_a_hero_comes_in_with_its_start_and_the_books_say_where_it_came_from():
    world = den()
    world.step([('join', 'ana'), ('join', 'bo')])
    ana = world.entities['hero:ana']
    assert (ana['gold'], ana['bag']) == (10, {})
    assert world.books['made']['gold'] == {'start': 20} and world.balanced() == {}
    assert world.public(ana, 'bo').get('gold') is None and world.public(ana, 'ana')['gold'] == 10


def test_buying_selling_eating_and_a_tip_move_what_they_say():
    world = den()
    world.step([('join', 'ana'), ('join', 'bo')])
    ana, bo = world.entities['hero:ana'], world.entities['hero:bo']
    assert cmd(world, 'ana', 'buy', item='sword') == (True, None)
    assert (ana['gold'], ana['bag']) == (2, {'sword': 1})
    assert cmd(world, 'ana', 'buy', item='sword') == (False, 'Not enough gold.')
    assert (ana['gold'], ana['bag']) == (2, {'sword': 1})                  # refused: nothing made, nothing spent
    assert cmd(world, 'ana', 'sell', item='sword') == (True, None)
    assert (ana['gold'], ana['bag']) == (6, {})                            # half its price; none left: out
    assert cmd(world, 'ana', 'buy', item='cheese') == (True, None)
    ana['hp'] = 20                                                         # as if bitten (a test's own hand)
    assert cmd(world, 'ana', 'eat', item='cheese') == (True, None)
    assert ana['hp'] == 25 and ana['bag'] == {}
    assert cmd(world, 'ana', 'eat', item='sword') == (False, 'Not to eat.')
    assert cmd(world, 'ana', 'tip', who='hero:bo', amount=3) == (True, None)
    assert (ana['gold'], bo['gold']) == (1, 13)
    assert cmd(world, 'ana', 'tip', who='hero:bo', amount=5) == (False, 'Not enough gold.')
    made, spent = world.books['made'], world.books['spent']
    assert made['sword'] == {'q:command buy': 1} and spent['sword'] == {'q:command sell': 1}
    assert spent['gold'] == {'q:command buy': 10} and made['gold'] == {'start': 20, 'q:command sell': 4}
    assert spent['cheese'] == {'q:command eat': 1} and world.balanced() == {}


def test_no_set_writes_the_ledger(tmp_path):
    world = den_with(tmp_path, '<q:command name="cheat"><q:set name="me.gold" value="{1000}" /></q:command>'
                               '<q:command name="stuff"><q:set name="me.bag.sword" value="{9}" /></q:command>')
    world.step([('join', 'ana')])
    assert cmd(world, 'ana', 'cheat') == (False, 'The world could not run it.')
    assert "gold is the ledger's" in world.errors[-1]['message']
    assert cmd(world, 'ana', 'stuff') == (False, 'The world could not run it.')
    assert world.entities['hero:ana']['gold'] == 10 and world.entities['hero:ana']['bag'] == {}


def test_a_rats_loot_is_made_by_the_ledger_as_its_loot():
    world = den()
    world.step([('join', 'ana')])
    rat = next(e for e in world.entities.values() if e['kind'] == 'Rat')
    world.step([('cmd', 'ana', 1, 'go', {'to': {'x': rat['at']['x'] - 3, 'y': rat['at']['y']}})])
    for _ in range(60):
        world.step([])
    world.step([('cmd', 'ana', 2, 'attack', {'who': rat['id']})])
    while rat['id'] in world.entities:
        world.step([])
    made = world.books['made']
    assert made['cheese'] == {'loot of Rat': 1} and 1 <= made['gold']['loot of Rat'] <= 3
    assert world.balanced() == {}


def test_a_hero_who_leaves_for_good_takes_nothing_out_of_the_books():
    world = den()
    world.step([('join', 'ana')])
    cmd(world, 'ana', 'buy', item='cheese')
    world.step([('leave', 'ana')])
    assert world.books['spent']['gold'] == {'q:command buy': 2, 'left the world': 8}
    assert world.books['spent']['cheese'] == {'left the world': 1} and world.balanced() == {}


def test_an_hour_of_bots_and_the_books_hold():
    """Twelve heroes, an hour of the world's time (36000 ticks): buying, selling, eating, tipping each other,
    walking to the rats and fighting them, coming and going. Every ten minutes, and at the end, what is held of each
    thing is what was made of it less what was spent."""
    world = den()
    rng = random.Random(11)
    names = [f'b{i}' for i in range(12)]
    world.step([('join', n) for n in names])
    seq, checks = 0, 0
    for tick in range(36000):
        inputs = []
        for n in names:
            if rng.random() > 0.05:
                continue
            seq += 1
            kind = rng.random()
            if n not in world.players:
                inputs.append(('join', n))
            elif kind < 0.05:
                inputs.append(('leave', n))
            elif kind < 0.25:
                inputs.append(('cmd', n, seq, 'buy', {'item': rng.choice(['cheese', 'sword'])}))
            elif kind < 0.4:
                inputs.append(('cmd', n, seq, 'sell', {'item': rng.choice(['cheese', 'sword'])}))
            elif kind < 0.5:
                inputs.append(('cmd', n, seq, 'eat', {'item': 'cheese'}))
            elif kind < 0.6:
                inputs.append(('cmd', n, seq, 'tip', {'who': f'hero:{rng.choice(names)}', 'amount': rng.randint(0, 4)}))
            elif kind < 0.75:
                inputs.append(('cmd', n, seq, 'go', {'to': 'square'}))
            else:
                rats = sorted(e['id'] for e in world.entities.values() if e['kind'] == 'Rat')
                if rats:
                    inputs.append(('cmd', n, seq, 'attack', {'who': rng.choice(rats)}))
        world.step(inputs)
        if tick % 6000 == 0:
            assert world.balanced() == {}, tick
            checks += 1
    assert world.balanced() == {} and checks == 6
    made, spent = world.books['made'], world.books['spent']
    assert made['gold'].get('loot of Rat', 0) > 0 and made['cheese'].get('loot of Rat', 0) > 0
    assert spent['gold']['q:command buy'] > 0 and spent['cheese']['q:command eat'] > 0
    assert world.errors == []


@pytest.mark.parametrize('more, says', [
    ('<q:entity name="cat" kind="Cat"><q:loot><q:drop item="fish" /></q:loot></q:entity>',
     'the world has no q:item of that name'),
    ('<q:currency name="gold" />', 'a name the world has already'),
    ('<q:entity name="cat" kind="Cat"><q:field name="gold" value="3" /></q:entity>', 'a currency is private'),
])
def test_what_the_ledger_refuses_in_a_file(tmp_path, more, says):
    with pytest.raises(GameServerError, match=says):
        den_with(tmp_path, more)
