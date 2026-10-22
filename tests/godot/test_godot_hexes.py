"""Maps of hexes and diamonds, and terrain costs (PLAN_GAMES_3.md, Phase 6), with Marches that asked for them.

shape="hex" on a qg:tileset draws hexes with their points up, every other row half a hex to the right; shape="iso"
diamonds, every other row half a diamond on. The rows of the .q are the rows seen. A grid walker steps to the
neighbour most the way held (up and down on the side it faces); a cursor with cells="true" snaps to the cells. A
step onto a tile costs its qg:tile cost=, and the way a walker finds is the cheapest: a pointer's click, an enemy
with ai="pathfind", qg:travel (which stops where its budget= runs out) and cost(). Marches is played in
tests/godot/test_godot_marches.py.
"""

from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_play import PlaySession
from quantum.runtime.godot_replay import replay, tape_from_holds

REPO = Path(__file__).resolve().parents[2]

LAND = """  <qg:tileset name="land" src="projects/marches/assets/land.png" tile="28x32" shape="{shape}">
    <qg:tile frame="0" shape="none" />
    <qg:tile frame="1" shape="none" cost="3" />
  </qg:tileset>
  <qg:spritesheet name="units" src="projects/marches/assets/units.png" tile="24" />
"""
GRASS = ','.join(['1'] * 8)

HEX_WALKER = f"""<q:application id="hexes" type="game">
{LAND.format(shape='hex')}  <qg:scene name="field" width="240" height="160">
    <qg:tilemap tileset="land" collision="true">
{chr(10).join([GRASS] * 5)}
    </qg:tilemap>
    <qg:character id="rider" controller="grid" sheet="units" x="70" y="64" hitbox="12x12" step-frames="10" />
  </qg:scene>
</q:application>
"""
ISO_WALKER = HEX_WALKER.replace('shape="hex"', 'shape="iso"').replace('id="hexes"', 'id="diamonds"').replace(
    'x="70" y="64"', 'x="70" y="48"')

# a band of forest (3 a step) across the middle row, grass round it: the cheapest way goes round
WOODS = ','.join(['1'] + ['2'] * 6 + ['1'])
COSTS = f"""<q:application id="costs" type="game">
{LAND.format(shape='hex')}  <qg:prefab name="Hunter" tag="hunter" sheet="units" frame="2" hitbox="12x12" ai="pathfind" speed="60" />
  <qg:prefab name="Raider" tag="raider" sheet="units" frame="2" hitbox="12x12" />
  <qg:scene name="field" width="240" height="160">
    <q:set name="arrived" value="0" type="number" />
    <q:set name="picked" value="[]" type="array" />
    <qg:tilemap tileset="land" collision="true">
{GRASS}
{WOODS}
{GRASS}
    </qg:tilemap>
    <qg:cursor id="aim" player="1" cells="true" />
    <qg:instance prefab="Raider" name="walker" x="28" y="40" />
    <qg:instance prefab="Raider" name="second" x="56" y="40" />
    <qg:on-select>
      <q:set name="picked" value="{{[cursor.col, cursor.row, cursor.x, cursor.y]}}" />
      <qg:travel target="walker" to="aim" budget="{{budget}}" step="4">
        <qg:on-end><q:set name="arrived" value="{{arrived + 1}}" /></qg:on-end>
      </qg:travel>
    </qg:on-select>
    <qg:on-input action="jump">
      <qg:travel target="second" to="aim" step="4" />
    </qg:on-input>
    <qg:hud><qg:text value="{{str(cost(walker, aim))}}" /></qg:hud>
  </qg:scene>
</q:application>
"""


def _build(folder: Path, text: str) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    (folder / 'game.q').write_text(text, encoding='utf-8')
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(folder / 'game.q')), str(folder / 'godot'),
                            source_dir=str(REPO)))
    return out


@pytest.fixture(scope='module')
def built(godot, tmp_path_factory):
    out = {}
    for name, text in (('hex', HEX_WALKER), ('iso', ISO_WALKER), ('costs', COSTS.replace('{budget}', '-1')),
                       ('budget', COSTS.replace('{budget}', '4'))):
        out[name] = _build(tmp_path_factory.mktemp(name), text)
        assert check_project(out[name], binary=godot) == []
    return out


def _rider(project, holds, ticks):
    return replay(project, ticks, tape=tape_from_holds(holds))['field']['nodes']['rider']


def test_a_grid_walker_steps_from_hex_to_hex(built):
    # it stands at column 2 of row 2 (x 70, y 64): a hex is 28 wide, its rows 24 apart, the odd ones 14 on
    right = _rider(built['hex'], [('right', 1, 2)], 20)
    assert (right['col'], right['row'], right['x'], right['y']) == (3, 2, 98.0, 64.0)
    down = _rider(built['hex'], [('right', 1, 2), ('down', 20, 21)], 40)     # facing right: down and to the right
    assert (down['col'], down['row'], down['x'], down['y']) == (3, 3, 112.0, 88.0)
    left_down = _rider(built['hex'], [('left', 1, 2), ('down', 20, 21)], 40)  # facing left: down and to the left
    assert (left_down['col'], left_down['row'], left_down['x'], left_down['y']) == (0, 3, 28.0, 88.0)


def test_a_grid_walker_on_diamonds(built):
    # diamonds 28 wide and 32 high: rows 16 apart, the odd ones 14 on
    start = _rider(built['iso'], [], 2)
    assert (start['col'], start['row'], start['x'], start['y']) == (2, 2, 70.0, 48.0)
    # the keys turned an eighth, as an isometric game has them: right is down and to the right, down is down and
    # to the left
    right = _rider(built['iso'], [('right', 1, 2)], 20)
    assert (right['col'], right['row'], right['x'], right['y']) == (2, 3, 84.0, 64.0)
    down = _rider(built['iso'], [('right', 1, 2), ('down', 20, 21)], 40)
    assert (down['col'], down['row'], down['x'], down['y']) == (2, 4, 70.0, 80.0)


def _walk(project, godot, to, then=None):
    with PlaySession(project, binary=godot) as game:
        game.act(cursor=to, ticks=2)
        seen = game.act(cursor=to, tap=['select'], ticks=2)
        walked = [e for e in seen['events'] if e['kind'] == 'travel']
        hud = PlaySession.screen(seen, 'hud')['items']
        if then is not None:
            game.act(cursor=then, ticks=2)
            seen = game.act(cursor=then, tap=['jump'], ticks=2)
            walked += [e for e in seen['events'] if e['kind'] == 'travel']
        seen = game.act(ticks=80)
        return walked, hud, seen['state']


def test_the_cheapest_way_goes_round_the_woods(built, godot):
    # from column 0 of row 1 to column 7 of row 1 (an odd row: x 28 + 28 a column, y 40): straight through six
    # forest hexes costs 19; round them, by the row above or the row below, 8
    walked, hud, state = _walk(built['costs'], godot, (7 * 28 + 28, 40))
    assert hud == ['8']                                                       # cost(walker, aim)
    assert walked == [{'kind': 'travel', 'who': 'walker', 'cells': 8, 'tick': walked[0]['tick']}]
    assert (state['named']['walker']['x'], state['named']['walker']['y']) == (224.0, 40.0)
    assert state['arrived'] == 1                                              # its qg:on-end ran


def test_a_walk_stops_where_its_budget_runs_out(built, godot):
    walked, _, state = _walk(built['budget'], godot, (7 * 28 + 28, 40))
    assert walked[0]['cells'] == 4 and state['arrived'] == 1                 # four moves: four hexes of grass
    assert state['named']['walker']['x'] == 126.0 and state['named']['walker']['y'] in (16.0, 64.0)


def test_walks_go_round_things_and_do_not_end_together(built, godot):
    # the other raider stands in the way of the first, and then walks to the same hex: it stops beside it
    walked, _, state = _walk(built['costs'], godot, (7 * 28 + 28, 40), then=(7 * 28 + 28, 40))
    first, second = state["named"]["walker"], state["named"]["second"]
    assert (first['x'], first['y']) == (224.0, 40.0)
    assert (second['x'], second['y']) != (224.0, 40.0) and walked[1]['cells'] >= 1


def test_a_cursor_snaps_to_hexes(built, godot):
    with PlaySession(built['costs'], binary=godot) as game:
        game.act(cursor=(60, 70), ticks=2)
        seen = game.act(cursor=(60, 70), tap=['select'], ticks=2)
    assert seen['state']['picked'] == [2, 2, 70.0, 64.0]                   # the hex at column 2 of row 2, its middle


# square tiles too: a pointer's click goes round the mud (frame 1: 3 a step) by the grass rows
MUD = f"""<q:application id="mud" type="game">
  <qg:tileset name="k" src="assets/kenney/tilemap_packed.png" tile="18">
    <qg:tile frame="1" shape="none" cost="3" />
  </qg:tileset>
  <qg:spritesheet name="people" src="assets/kenney/tilemap-characters_packed.png" tile="24" />
  <qg:scene name="field" width="144" height="54">
    <qg:tilemap tileset="k">
{','.join(['1'] * 8)}
{','.join(['1'] + ['2'] * 6 + ['1'])}
{','.join(['1'] * 8)}
    </qg:tilemap>
    <qg:cursor player="1" />
    <qg:character id="worker" controller="pointer" sheet="people" x="9" y="27" hitbox="12x12" step-frames="4" />
  </qg:scene>
</q:application>
"""


def test_a_click_walks_round_the_mud(godot, tmp_path):
    out = _build(tmp_path, MUD)
    assert check_project(out, binary=godot) == []
    with PlaySession(out, binary=godot) as game:
        game.act(cursor=(135, 27), ticks=2)
        clicked = game.act(cursor=(135, 27), tap=['click'], ticks=2)
        walked = game.act(ticks=60)
    route = [e for e in clicked['events'] if e['kind'] == 'route']
    steps = [e['to'] for e in clicked['events'] + walked['events'] if e['kind'] == 'step']
    assert route[0]['cells'] == 9                                             # up, seven along, down: 9 for 19
    assert steps[0][1] != 1 and steps[-1] == [7, 1]
    assert (walked['state']['nodes']['worker']['col'], walked['state']['nodes']['worker']['row']) == (7, 1)
