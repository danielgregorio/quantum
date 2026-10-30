"""The game server, Phase 3 of PLAN_GAME_SERVER.md: what a world does by itself.

The den's rat (worlds/den) roams near where it was made, bites a hero who comes near, dies of two blows, leaves
cheese and gold to its killer and comes back thirty seconds later; at night there are two. A beast with no hero near
sleeps. A hero walks around a wall by a click (q:travel). A kill is a transaction like any other: refused, the beast
lives. And all of it is the world's seeded random: the same inputs make the same world, beasts and all.
"""

import copy
from pathlib import Path

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.gameserver import GameServerError, World, read_world
from quantum.runtime.gameserver.log import replay
from quantum.runtime.gameserver.session import WorldSession, serve_world

DEN = Path(__file__).resolve().parent / 'worlds' / 'den' / 'den.server.q'
TMX = DEN.parent / 'den.tmx'


def den() -> World:
    return World(read_world(QuantumParser(use_cache=False).parse_file(str(DEN)), str(DEN)))


def world_of(tmp_path, body, tmx=TMX, name='t'):
    path = tmp_path / f'{name}.server.q'
    path.write_text(f'<q:application id="{name}" type="gameserver">\n  <q:gameserver name="{name}">\n    '
                    f'<q:map name="m" tiled="{tmx}" />\n{body}\n  </q:gameserver>\n</q:application>\n')
    return read_world(QuantumParser(use_cache=False).parse_file(str(path)), str(path))


def rats(world):
    return sorted((e for e in world.entities.values() if e['kind'] == 'Rat'), key=lambda e: e['id'])


def den_with(tmp_path, more='', changes=()):
    """The den, with more in its q:gameserver and some of its words changed."""
    source = DEN.read_text().replace('</q:gameserver>', more + '\n  </q:gameserver>')
    for old, new in changes:
        assert old in source
        source = source.replace(old, new)
    (tmp_path / 'den.tmx').write_text(TMX.read_text())
    path = tmp_path / 'den.server.q'
    path.write_text(source)
    return World(read_world(QuantumParser(use_cache=False).parse_file(str(path)), str(path)))


def near_the_rat(world):
    """ana comes into the den and walks (q:travel) to three tiles west of the rat, around the meadow's wall."""
    world.step([('join', 'ana')])
    rat = rats(world)[0]
    to = {'x': rat['at']['x'] - 3, 'y': rat['at']['y']}
    out = world.step([('cmd', 'ana', 1, 'go', {'to': to})])
    assert out.acks == {'ana': [1]}, out.refused
    for _ in range(60):
        world.step([])
    return world.entities['hero:ana'], rat


# --- the rat ----------------------------------------------------------------------------------------------------

def test_a_rat_bites_dies_drops_and_comes_back_in_thirty_seconds():
    world = den()
    ana, rat = near_the_rat(world)
    assert rat['state'] == 'bite' and rat['target'] == 'hero:ana'           # it saw her, and came
    assert ana['hp'] < 30                                                    # and bit
    out = world.step([('cmd', 'ana', 2, 'attack', {'who': rat['id']})])
    assert out.acks == {'ana': [2]}
    while rat['id'] in world.entities:
        world.step([])
        assert world.tick < 200
    died = world.tick
    assert ana['bag'] == {'cheese': 1} and 11 <= ana['gold'] <= 13 and ana['kills'] == 1 and ana['target'] == ''
    assert rats(world) == [] and world.spawned['0']['due'] == [died + 300]
    while not rats(world):
        world.step([])
    assert world.tick == died + 300                                          # thirty seconds at ten ticks a second
    back = rats(world)[0]
    assert back['id'] == 'rat-2' and back['state'] == 'roam' and back['hp'] == 10 and not world.errors


def test_the_same_inputs_make_the_same_world_beasts_and_all():
    a, b = den(), den()
    near_the_rat(a)
    near_the_rat(b)
    assert a.digest() == b.digest()
    snap = copy.deepcopy(a.snapshot())
    entries = []
    for i in range(120):                                                  # a fight, a death, roaming
        out = a.step([('cmd', 'ana', 10, 'attack', {'who': 'rat-1'})] if i == 0 else [])
        entries += out.entries
    assert 'rat-1' not in a.entities
    again = World.from_snapshot(a.definition, snap)
    assert replay(again, entries) == []
    while again.tick < a.tick:                                            # the ticks with no input, as the log's
        again.step([])                                                    # heartbeat brings them
    assert again.digest() == a.digest()


def test_a_kill_refused_leaves_the_beast_alive(tmp_path):
    world = den_with(tmp_path, '<q:command name="smite" params="who"><q:kill entity="{who}" by="{me}" />'
                               '<q:require condition="{false}" else="Not today." /></q:command>')
    world.step([('join', 'ana')])
    rat = rats(world)[0]
    out = world.step([('cmd', 'ana', 1, 'smite', {'who': rat['id']})])
    assert out.refused['ana'][0]['reason'] == 'Not today.'
    assert world.entities[rat['id']] is rat and world.entities['hero:ana']['bag'] == {}
    assert world.spawned['0'] == {'alive': [rat['id']], 'due': []}
    assert rat['id'] in world.cells[world.cell_of[rat['id']]] and rat['id'] not in world.gone


def test_at_night_there_are_two(tmp_path):
    world = den_with(tmp_path, changes=[('day="10m" night="0.25"', 'day="10s" night="0.5"')])
    world.step([])
    assert not world.is_night() and len(rats(world)) == 1
    while not world.is_night():
        world.step([])
    assert world.tick == 50 and len(rats(world)) == 2                    # night falls at half the day: two
    while world.is_night():
        world.step([])
    assert len(rats(world)) == 2                                          # by day they stay until killed


def test_rats_called_for_a_while_go_without_dying():
    world = den()
    world.step([('join', 'ana')])
    out = world.step([('cmd', 'ana', 1, 'call-rats', {})])
    assert out.acks == {'ana': [1]} and len(rats(world)) == 4
    called = [e for e in rats(world) if '_expires' in e]
    assert len(called) == 3 and all(e['at']['x'] >= 40 for e in called)
    for _ in range(50):
        world.step([])
    assert len(rats(world)) == 1 and world.entities['hero:ana']['kills'] == 0


# --- moving by itself -------------------------------------------------------------------------------------------

def test_a_hero_travels_around_the_wall_and_a_step_ends_the_way():
    world = den()
    world.step([('join', 'ana')])                                         # at (3, 3); the wall is y = 16, x 10-37
    world.step([('cmd', 'ana', 1, 'go', {'to': {'x': 20, 'y': 20}})])
    ana = world.entities['hero:ana']
    path = [tuple(t) for t in ana['_path']]
    assert path[-1] == (20, 20) and all(t not in world.definition.map.walls for t in path)
    assert any(t[1] == 16 for t in path) and all(t[0] < 10 or t[0] > 37 for t in path if t[1] == 16)
    for _ in range(5):
        world.step([])
    here = dict(ana['at'])
    world.step([('cmd', 'ana', 2, 'step', {'dir': 'north'})])
    assert ana['_path'] == [] and 'hero:ana' not in world.travelers
    for _ in range(5):
        world.step([])
    assert ana['at'] == {'x': here['x'], 'y': here['y'] - 1}
    out = world.step([('cmd', 'ana', 3, 'go', {'to': {'x': 20, 'y': 16}})])   # a wall: no way there
    assert out.refused['ana'][0]['reason'] == 'No way there.'


def wide_map(tmp_path, width=120, height=12):
    """A long field, walled round, an area at each end: farther apart than a brain is awake."""
    from importlib.util import module_from_spec, spec_from_file_location
    spec = spec_from_file_location('bots', Path(__file__).resolve().parents[2] / 'scripts' / 'gameserver-bots.py')
    bots = module_from_spec(spec)
    spec.loader.exec_module(bots)
    path = tmp_path / 'wide.tmx'
    path.write_text(bots.tmx_of(width, height, areas={'home': (2, 2, 3, 3), 'far': (110, 4, 112, 6)}))
    return path


def test_a_beast_with_no_hero_near_sleeps(tmp_path):
    body = ('<q:entity name="hero" kind="Hero" per-player="true" speed="10/s" />'
            '<q:entity name="rat" kind="Rat" speed="4/s"><q:brain><q:state name="roam" do="wander" within="2" />'
            '</q:brain></q:entity>'
            '<q:spawn entity="rat" area="far" count="1" />'
            '<q:command name="go" params="to"><q:move entity="{me}" to="{to}" /></q:command>'
            '<q:on-join><q:move entity="{me}" to="home" /></q:on-join>')
    world = World(world_of(tmp_path, body, tmx=wide_map(tmp_path)))
    world.step([('join', 'ana')])
    rat = rats(world)[0]
    where = dict(rat['at'])
    for _ in range(200):
        world.step([])
    assert rat['at'] == where and rat['_until'] == 0                     # a hundred tiles away: asleep
    world.step([('cmd', 'ana', 1, 'go', {'to': {'x': 100, 'y': 5}})])
    for _ in range(100):
        world.step([])
    assert rat['_until'] > 0 and max(abs(rat['at']['x'] - rat['_home'][0]),
                                     abs(rat['at']['y'] - rat['_home'][1])) <= 2   # awake, and within its two


def test_a_hurt_rat_flees_for_three_seconds_then_roams(tmp_path):
    world = den_with(tmp_path, changes=[('hp="10" attack="2"', 'hp="6" attack="2"')])   # one blow leaves it 1
    ana, rat = near_the_rat(world)
    world.step([('cmd', 'ana', 2, 'attack', {'who': rat['id']})])
    while rat['state'] != 'flee':
        world.step([])
        assert world.tick < 200
    since, before = rat['_since'], rat['hp']
    world.step([('cmd', 'ana', 3, 'attack', {'who': ''})])                 # refused: she lets it go
    ana['target'] = ''
    far = max(abs(rat['at']['x'] - ana['at']['x']), abs(rat['at']['y'] - ana['at']['y']))
    for _ in range(10):
        world.step([])
    assert max(abs(rat['at']['x'] - ana['at']['x']), abs(rat['at']['y'] - ana['at']['y'])) > far
    while rat['state'] == 'flee':
        world.step([])
    assert world.tick - since == 30 and rat['hp'] == before == 1


def test_a_brain_that_fails_is_undone_and_kept_in_the_errors(tmp_path):
    body = ('<q:entity name="hero" kind="Hero" per-player="true" />'
            '<q:entity name="rat" kind="Rat"><q:brain><q:state name="roam" do="wander">'
            '<q:when condition="{it.nothing.more > 1}" become="roam" /></q:state></q:brain></q:entity>'
            '<q:spawn entity="rat" area="square" count="1" />'
            '<q:on-join><q:move entity="{me}" to="west" /></q:on-join>')
    world = World(world_of(tmp_path, body))
    world.step([('join', 'ana')])
    for _ in range(5):
        world.step([])
    assert world.errors and world.errors[-1]['where'] == 'q:brain of rat-1'
    assert world.tick == 6                                                # and the world goes on


# --- the file -----------------------------------------------------------------------------------------------------

HERO = '<q:entity name="hero" kind="Hero" per-player="true" />'
RAT = '<q:entity name="rat" kind="Rat" hp="5" />'


@pytest.mark.parametrize('body, says', [
    (HERO + '<q:spawn entity="hero" area="west" />', "a player's entity comes with its player"),
    (HERO + RAT + '<q:spawn entity="rat" area="moon" />', 'the map has no area of that name'),
    (HERO + RAT + '<q:spawn entity="rat" area="west" night-count="3" />', 'the world has no q:clock'),
    (HERO + '<q:on-death kind="Dragon"></q:on-death>', 'no entity of the world is of that kind'),
    (HERO + '<q:entity name="rat" kind="Rat"><q:brain><q:state name="a"><q:when condition="{true}" become="b" />'
     '</q:state></q:brain></q:entity>', 'the brain has no such state'),
    (HERO + '<q:entity name="rat" kind="Rat"><q:brain><q:state name="a" do="chase" /></q:brain></q:entity>',
     'needs target='),
    ('<q:entity name="hero" kind="Hero" per-player="true"><q:brain><q:state name="a" /></q:brain></q:entity>',
     'its player is its brain'),
    (HERO + '<q:entity name="rat" kind="Rat"><q:loot><q:drop item="cheese" gold="2" /></q:loot></q:entity>',
     'an item= or gold=, one of them'),
    (HERO + '<q:command name="hop" params="dir" predict="true"><q:set name="me.x" value="1" /></q:command>',
     'its body is q:requires and one q:move'),
    (HERO + '<q:command name="hop" params="dir" predict="true"><q:move entity="{me}" to="west" /></q:command>',
     'its q:move is of me to ahead(me, one of its params)'),
    (HERO + '<q:entity name="rat" kind="Rat" state="x" />', 'every entity has id, kind, at, facing'),
    (HERO + '<q:entity name="rat" kind="Rat" hp="5"><q:field name="hp" value="6" /></q:entity>', 'hp twice'),
])
def test_what_a_world_says_wrong_of_its_life(tmp_path, body, says):
    with pytest.raises(GameServerError) as e:
        world_of(tmp_path, body)
    assert says in e.value.message, e.value.message


def test_an_entity_that_fights_has_its_health_top_and_its_target():
    world = den()
    world.step([('join', 'ana')])
    ana = world.entities['hero:ana']
    assert (ana['hp'], ana['max_hp'], ana['target'], ana['attack']) == (30, 30, '', 5)
    assert world.definition.commands['step'].predict == 'dir'


# --- through the protocol ----------------------------------------------------------------------------------------

def test_a_player_sees_the_rat_come_bite_and_go():
    with serve_world(DEN) as server:
        with WorldSession(server.url, 'ana') as ana:
            rat = next(e for e in ana.observe()['world'].values() if e['kind'] == 'Rat') if any(
                e['kind'] == 'Rat' for e in ana.observe()['world'].values()) else None
            assert rat is None                                            # the square is far from the west
            seen = ana.act(send=[('go', {'to': {'x': 19, 'y': 21}})], ticks=60)
            rat = next(e for e in seen['world'].values() if e['kind'] == 'Rat')
            assert rat['state'] == 'bite' and rat['target'] == 'hero:ana'
            assert any(e['name'] == 'hit' and e['of'] == 'hero:ana' for e in seen['events'])
            seen = ana.until(lambda s: rat['id'] not in s['world'], send=[('attack', {'who': rat['id']})],
                             max_ticks=200)
            assert seen['until'] and seen['me']['bag'] == {'cheese': 1} and seen['me']['kills'] == 1
            assert any(e['name'] == 'hit' and e['of'] == rat['id'] for e in seen['events'])


def test_a_spawn_picks_its_tile_as_it_always_did():
    """A beast is made at a free tile of its area, drawn from the world's random among them in the order of the
    area's rows: read from the index's cells (fast), the free tiles are the ones the world tile by tile would find,
    so the same draw lands on the same tile and an old log makes the same world."""
    world = den()
    for k in range(12):                                   # heroes and rats about, some in the square
        world.step([('join', f'p{k}')])
    spec = world.definition.entities['rat']
    for area in world.definition.map.areas:
        x0, y0, x1, y1 = world.definition.map.areas[area]
        for _ in range(6):
            free = [(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1) if world.free((x, y))]
            if not free:
                assert world.make_at(spec, area, None) is None
                break
            state = world.rng.getstate()
            expected = free[world.rng.randrange(len(free))]
            world.rng.setstate(state)
            made = world.make_at(spec, area, None)
            assert (made['at']['x'], made['at']['y']) == expected
