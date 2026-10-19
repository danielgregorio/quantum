"""Tile kinds in Godot: ladders, water, ice and tiles that hurt.

Small levels of 18 px tiles, each with a platformer (run 90 px/s, gravity
900) or a top-down walker (60 px/s). In the rows, 2 is a plain solid tile;
3 a ladder, 4 water, 5 ice, 6 a hurting tile (frames 2 to 5 of the tileset,
given their kind by qg:tile). The floor is row 7: its top is y=126, and a
16 px tall character stands on it at y=118.
"""

from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_replay import replay, tape_from_holds

REPO = Path(__file__).resolve().parents[2]

HEAD = '''<q:application id="kinds" type="game">
  <qg:tileset name="k" src="assets/kenney/tilemap_packed.png" tile="18">
    <qg:tile frame="2" kind="ladder" />
    <qg:tile frame="3" kind="water" />
    <qg:tile frame="4" kind="{ice_shape}" />
    <qg:tile frame="5" kind="hurt" />
  </qg:tileset>
  <qg:spritesheet name="hero" src="projects/keep/assets/hero.png" tile="24" />
  <qg:scene name="main" width="270" height="144">
    <q:set name="hurts" value="0" type="number" />
    <q:set name="iced" value="0" type="number" />
    <qg:tilemap tileset="k" collision="true">
{rows}
    </qg:tilemap>
{characters}
  </qg:scene>
</q:application>
'''

EMPTY = '0,0,0,0,0,0,0,0,0,0,0,0,0,0,0'


def level(rows):
    """Eight rows, the given ones at the bottom: the last is row 7, the floor."""
    return '\n'.join([EMPTY] * (8 - len(rows)) + rows)


def platformer(cid, x, y=118, extra=''):
    return (f'    <qg:character id="{cid}" controller="platformer" sheet="hero" frame="0" x="{x}" y="{y}" '
            f'hitbox="12x16">{extra}</qg:character>')


def build(tmp_path_factory, godot, name, rows, characters, ice_shape='ice'):
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    src = tmp_path_factory.mktemp(name) / f'{name}.q'
    head = HEAD.replace('kind="{ice_shape}" />', 'kind="ice" />' if ice_shape == 'ice'
                        else 'kind="ice" shape="none" />')
    src.write_text(head.format(rows=level(rows), characters='\n'.join(characters)), encoding='utf-8')
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(src)), str(src.parent / 'godot'),
                            source_dir=str(REPO)))
    assert check_project(out, binary=godot) == []
    return out


def at(project, godot, ticks, holds):
    return replay(project, ticks, tape_from_holds(holds), binary=godot)['main']


# --- ladders ---

LADDER = ['0,0,0,0,0,3,0,0,0,0,0,0,0,0,0'] * 6 + ['2,2,2,2,2,2,2,2,2,2,2,2,2,2,2']


@pytest.fixture(scope='module')
def ladder(tmp_path_factory, godot):
    return build(tmp_path_factory, godot, 'ladder', LADDER, [platformer('hero', 99)])


def test_up_climbs_a_ladder_and_stops_at_its_top(ladder, godot):
    climbing = at(ladder, godot, 40, [('up', 1, 200)])['nodes']['hero']
    assert 80 < climbing['y'] < 118                          # going up, 54 px/s, no gravity
    top = at(ladder, godot, 150, [('up', 1, 200)])['nodes']['hero']
    assert 18 <= top['y'] <= 22                               # the ladder's top cell is row 1 (y 18..36)
    held = at(ladder, godot, 170, [('up', 1, 150)])['nodes']['hero']
    assert held['y'] == top['y']                              # let go of up: it holds on, it does not fall


def test_jump_lets_go_of_the_ladder(ladder, godot):
    off = at(ladder, godot, 260, [('up', 1, 150), ('jump', 160, 162)])['nodes']['hero']
    assert off['y'] == pytest.approx(118, abs=0.5)            # back down on the floor


# --- water ---

POOL = ['0,0,4,4,4,4,4,4,0,0,0,0,0,0,0'] * 3 + ['2,2,2,2,2,2,2,2,2,2,2,2,2,2,2']


@pytest.fixture(scope='module')
def pool(tmp_path_factory, godot):
    return build(tmp_path_factory, godot, 'pool', POOL, [platformer('hero', 81, y=20)])


def test_water_slows_the_fall(pool, godot):
    # in the air it would fall at up to 300 px/s; in water at 105 at most: under 18 px in 10 ticks
    a = at(pool, godot, 40, [])['nodes']['hero']['y']
    b = at(pool, godot, 50, [])['nodes']['hero']['y']
    assert 72 < a < b and b - a < 18


def test_a_jump_in_water_is_a_stroke(pool, godot):
    sinking = at(pool, godot, 45, [])['nodes']['hero']['y']
    stroke = at(pool, godot, 52, [('jump', 45, 46)])['nodes']['hero']['y']
    assert stroke < sinking                                    # up it goes, though nothing is under it


# --- ice ---

RINK = ['2,2,2,2,2,5,5,5,5,5,5,5,5,5,5']


@pytest.fixture(scope='module')
def rink(tmp_path_factory, godot):
    return build(tmp_path_factory, godot, 'rink', RINK, [platformer('dry', 27), platformer('icy', 117)])


def test_on_ice_it_slides(rink, godot):
    holds = [('right', 10, 40)]                                 # once both stand on the floor
    let_go = at(rink, godot, 41, holds)['nodes']
    later = at(rink, godot, 55, holds)['nodes']
    assert later['dry']['x'] == let_go['dry']['x']            # on the plain floor it stops at once
    assert later['icy']['x'] > let_go['icy']['x'] + 5          # on ice it slides on
    assert let_go['icy']['x'] - 117 < let_go['dry']['x'] - 27  # and it took longer to get going


# --- tiles that hurt, and qg:on-tile ---

SPIKES = ['2,2,2,6,6,6,2,2,2,5,5,5,2,2,2']


@pytest.fixture(scope='module')
def spikes(tmp_path_factory, godot):
    on_tile = ('<qg:on-tile kind="hurt" cooldown="30"><q:set name="hurts" value="{hurts + 1}" /></qg:on-tile>'
               '<qg:on-tile kind="ice"><q:set name="iced" value="{iced + 1}" /></qg:on-tile>')
    return build(tmp_path_factory, godot, 'spikes', SPIKES, [platformer('hero', 81, extra=on_tile)])


def test_a_hurting_tile_runs_on_tile_each_cooldown_while_touched(spikes, godot):
    main = at(spikes, godot, 95, [])
    assert main['hurts'] == 4                                  # ticks 1, 31, 61, 91
    assert main['iced'] == 0


def test_without_a_cooldown_on_tile_runs_once_as_it_comes_to_touch(spikes, godot):
    # walk right from the spikes over plain tiles onto the ice (x 162..216) and stay there
    main = at(spikes, godot, 200, [('right', 1, 70)])
    assert main['iced'] == 1
    assert main['nodes']['hero']['x'] > 162


# --- top-down: wading and sliding ---

FLOOR = ['0,0,0,0,0,0,0,0,0,0,0,0,0,0,0'] * 2 + ['4,4,4,4,4,4,4,4,4,4,4,4,4,4,4'] + [EMPTY] \
    + ['5,5,5,5,5,5,5,5,5,5,5,5,5,5,5'] + [EMPTY] * 3


def topdown(cid, y):
    return (f'    <qg:character id="{cid}" controller="topdown" sheet="hero" frame="0" x="20" y="{y}" '
            f'hitbox="12x12" speed="60" />')


@pytest.fixture(scope='module')
def field(tmp_path_factory, godot):
    return build(tmp_path_factory, godot, 'field', FLOOR, [topdown('dry', 9), topdown('wet', 45),
                                                          topdown('icy', 81)], ice_shape='floor')


def test_top_down_water_halves_the_speed_and_ice_slides(field, godot):
    holds = [('right', 1, 60)]
    walked = at(field, godot, 61, holds)['nodes']
    assert walked['dry']['x'] - 20 == pytest.approx(60, abs=1.5)
    assert walked['wet']['x'] - 20 == pytest.approx(30, abs=1.5)          # wading: half
    after = at(field, godot, 80, holds)['nodes']
    assert after['dry']['x'] == walked['dry']['x']
    assert after['icy']['x'] > walked['icy']['x'] + 3                     # still sliding
