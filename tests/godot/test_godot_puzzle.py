"""Puzzle and adventure in Godot (PLAN_GAMES_3.md, Phase 3): things pushed, things carried, prefabs made from
prefabs, a walk to where a click chose, the camera sent to a point, dialogue with choices, and more of Tiled.

A small room of a grid walker, played through the play protocol: a crate pushed until the wall stops it,
two crates in a row that do not move, a heavy crate (a crate it extends, pushable="false") that does not
either but is touched as a crate; a pad (a zone) stepped on; a key picked up and carried over the head, then
put down. A second scene, a maze, walks a pointer character round its walls to where it is clicked. A third
is drawn in Tiled: two tilesets, flipped tiles, an animated tile, and a zone, an exit, a path, an object's
state and the map's properties read from the map.
"""

import json
import tempfile
from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project, run_godot
from quantum.runtime.godot_play import PlaySession
from quantum.runtime.godot_replay import cursor_at, replay_peers, tape_from_holds

REPO = Path(__file__).resolve().parents[2]

PUZZLE = '''<q:application id="puzzle" type="game">
  <qg:input action="peek" keys="P" />
  <qg:input action="glance" keys="G" />
  <qg:input action="drop" keys="X" />
  <qg:input action="maze" keys="M" />
  <qg:tileset name="k" src="assets/kenney/tilemap_packed.png" tile="18" />
  <qg:spritesheet name="c" src="assets/kenney/tilemap-characters_packed.png" tile="24" />
  <qg:prefab name="Crate" tag="crate" sheet="k" frame="6" hitbox="16x16" solid="true" pushable="true" />
  <qg:prefab name="Heavy" extends="Crate" frame="7" pushable="false" />
  <qg:prefab name="Key" tag="key" sheet="k" frame="27" hitbox="12x12" />
  <qg:scene name="room" width="180" height="108">
    <q:set name="touched" value="" />
    <q:set name="pads" value="0" type="number" />
    <q:set name="held" value="false" type="boolean" />
    <q:set name="answer" value="" />
    <qg:tilemap tileset="k" collision="true">
23,23,23,23,23,23,23,23,23,23
23,0,0,0,0,0,0,0,0,23
23,0,0,0,0,0,0,0,0,23
23,0,0,0,0,0,0,0,0,23
23,0,0,0,0,0,0,0,0,23
23,23,23,23,23,23,23,23,23,23
    </qg:tilemap>
    <qg:instance prefab="Crate" name="crate" x="63" y="27" />
    <qg:instance prefab="Crate" name="c1" x="63" y="45" />
    <qg:instance prefab="Crate" name="c2" x="81" y="45" />
    <qg:instance prefab="Heavy" name="heavy" x="63" y="63" />
    <qg:instance prefab="Key" name="key" x="63" y="81" />
    <qg:zone name="pad" tag="pad" x="36" y="72" width="18" height="18" />
    <qg:character id="w" controller="grid" sheet="c" frame="0" x="27" y="27" hitbox="14x14" step-frames="6">
      <qg:on-collision with="crate"><q:set name="touched" value="{other.name}" /></qg:on-collision>
      <qg:on-collision with="pad"><q:set name="pads" value="{pads + 1}" /></qg:on-collision>
      <qg:on-collision with="key">
        <qg:attach target="other" dy="-12" />
        <q:set name="held" value="{carrying(me, 'key') != null}" />
      </qg:on-collision>
    </qg:character>
    <qg:camera follow="w" bounds="none" />
    <qg:on-input action="drop">
      <qg:detach from="w" tag="key" />
      <q:set name="held" value="{carrying(w, 'key') != null}" />
    </qg:on-input>
    <qg:on-input action="peek"><qg:camera-to x="150" y="80" zoom="2" seconds="0.25" hold="0.25" /></qg:on-input>
    <qg:on-input action="glance"><qg:camera-to target="w" zoom="3" seconds="0.25" hold="0" pause="false" /></qg:on-input>
    <qg:on-input action="jump"><qg:say dialogue="ask" /></qg:on-input>
    <qg:on-input action="maze"><qg:goto-scene name="maze" /></qg:on-input>
    <qg:dialogue name="ask" speed="30" sheet="c" size="8">
      <qg:line who="Owl" portrait="2" text="Which way?">
        <qg:choice label="Left"><q:set name="answer" value="left" /></qg:choice>
        <qg:choice label="Pad" if="{pads > 0}"><q:set name="answer" value="pad" /></qg:choice>
        <qg:choice label="{'Right ' + str(pads)}"><q:set name="answer" value="right" /></qg:choice>
      </qg:line>
      <qg:line who="Owl" text="{'So: ' + answer}" />
    </qg:dialogue>
  </qg:scene>
  <qg:scene name="maze" width="180" height="108">
    <qg:tilemap tileset="k" collision="true">
23,23,23,23,23,23,23,23,23,23
23,0,0,23,0,0,0,0,0,23
23,0,0,23,0,23,23,23,0,23
23,0,0,23,0,23,0,0,0,23
23,0,0,0,0,23,0,0,0,23
23,23,23,23,23,23,23,23,23,23
    </qg:tilemap>
    <qg:cursor player="1" grid="18" />
    <qg:instance prefab="Crate" name="box" x="117" y="81" />
    <qg:character id="p" controller="pointer" sheet="c" frame="0" x="27" y="27" hitbox="14x14" step-frames="4">
      <qg:on-collision with="crate"><qg:destroy target="other" /></qg:on-collision>
    </qg:character>
  </qg:scene>
</q:application>
'''


def build(tmp_path_factory, godot, name, source, files=None):
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    folder = tmp_path_factory.mktemp(name)
    for fname, text in (files or {}).items():
        (folder / fname).write_text(text, encoding='utf-8')
    src = folder / f'{name}.q'
    src.write_text(source, encoding='utf-8')
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(src)), str(folder / 'godot'),
                            source_dir=str(REPO)))
    assert check_project(out, binary=godot) == []
    return out


@pytest.fixture(scope='module')
def puzzle(tmp_path_factory, godot):
    return build(tmp_path_factory, godot, 'puzzle', PUZZLE)


def steps(game, action, n, frames=7):
    """n steps of a grid walker of step-frames="6" (a step, and the tick it is asked on)."""
    obs = None
    for _ in range(n):
        obs = game.act(tap=[action], ticks=frames)
    return obs


def cell(obs, name):
    thing = obs['state']['named'][name]
    return int(thing['x'] // 18), int(thing['y'] // 18)


def kinds(events, kind):
    return [e for e in events if e['kind'] == kind]


def test_a_crate_is_pushed_until_the_wall_stops_it(puzzle, godot):
    with PlaySession(puzzle, binary=godot) as game:
        obs = steps(game, 'right', 8)
        assert cell(obs, 'crate') == (8, 1)                   # against the wall
        w = obs['state']['nodes']['w']
        assert (w['col'], w['row']) == (7, 1)                 # and the walker behind it
        assert obs['state']['touched'] == 'crate'


def test_two_crates_in_a_row_and_a_heavy_one_do_not_move(puzzle, godot):
    with PlaySession(puzzle, binary=godot) as game:
        steps(game, 'down', 1)
        obs = steps(game, 'right', 3)                         # into c1, with c2 behind it
        assert (cell(obs, 'c1'), cell(obs, 'c2')) == ((3, 2), (4, 2))
        assert obs['state']['nodes']['w']['col'] == 2 and obs['state']['touched'] == 'c1'   # a touch, not a push
        assert not kinds(obs['events'], 'push')
        steps(game, 'down', 1)
        obs = steps(game, 'right', 2)                         # the heavy one: a crate, not pushable
        assert cell(obs, 'heavy') == (3, 3)
        assert obs['state']['nodes']['w']['col'] == 2
        assert [e['with'] for e in kinds(obs['events'], 'touch')] == ['crate']
        assert obs['state']['touched'] == 'heavy'


def test_a_zone_stepped_on_and_a_key_carried_and_put_down(puzzle, godot):
    with PlaySession(puzzle, binary=godot) as game:
        steps(game, 'down', 3)
        obs = steps(game, 'right', 1)                         # onto the pad
        assert [e['with'] for e in kinds(obs['events'], 'touch')] == ['pad']
        assert obs['state']['pads'] == 1
        obs = steps(game, 'right', 1)                         # into the key: it is carried
        assert [(e['what'], e['to']) for e in kinds(obs['events'], 'attach')] == [('key', 'w')]
        assert obs['state']['held'] is True
        assert obs['state']['nodes']['w']['col'] == 2         # the step into it was the touch
        obs = steps(game, 'right', 2)                         # the key goes along over its head, and stands in no cell
        w, key = obs['state']['nodes']['w'], obs['state']['named']['key']
        assert (w['col'], key['x'], key['y']) == (4, w['x'], w['y'] - 12)
        obs = game.act(tap=['drop'], ticks=2)
        assert kinds(obs['events'], 'detach') and obs['state']['held'] is False
        obs = steps(game, 'right', 2)
        assert obs['state']['named']['key'] == {'x': w['x'], 'y': w['y'] - 12}   # put down where it was


def test_the_camera_goes_to_a_point_and_back_the_scene_waiting(puzzle, godot):
    with PlaySession(puzzle, binary=godot) as game:
        obs = game.act(tap=['peek'], ticks=16)                # there in a quarter of a second
        assert kinds(obs['events'], 'camera') and kinds(obs['events'], 'pause')
        assert PlaySession.screen(obs, 'camera') == {'kind': 'camera', 'x': 150.0, 'y': 80.0, 'zoom': 2.0}
        obs = game.act(hold=['right'], ticks=10)               # held there; the walker waits
        assert PlaySession.screen(obs, 'camera')['zoom'] == 2.0 and obs['state']['nodes']['w']['col'] == 1
        obs = game.act(ticks=25)                               # and back
        assert kinds(obs['events'], 'resume')
        assert PlaySession.screen(obs, 'camera')['zoom'] == 1.0
        obs = game.act(tap=['glance'], ticks=2)               # pause="false": the walker goes on meanwhile
        obs = steps(game, 'right', 2)
        assert obs['state']['nodes']['w']['col'] == 3 and not kinds(obs['events'], 'pause')


def test_a_dialogue_typed_in_with_a_face_and_choices(puzzle, godot):
    with PlaySession(puzzle, binary=godot) as game:
        obs = game.act(tap=['jump'], ticks=10)
        talk = PlaySession.screen(obs, 'dialogue')
        assert talk['typing'] and 'choices' not in talk        # 30 letters a second: still typing
        obs = game.act(ticks=30)
        talk = PlaySession.screen(obs, 'dialogue')
        assert talk['choices'] == ['Left', 'Right 0'] and talk['focus'] == 0   # Pad only once on a pad
        obs = game.act(tap=['down'], ticks=2)
        assert PlaySession.screen(obs, 'dialogue')['focus'] == 1
        obs = game.act(tap=['select'], ticks=2)
        assert kinds(obs['events'], 'choose')[0]['choice'] == 'Right 0'
        obs = game.act(tap=['select'], ticks=40)
        talk = PlaySession.screen(obs, 'dialogue')
        assert talk['line'] == 1 and talk['text'] == 'So: right'
        obs = game.act(tap=['select'], ticks=2)
        assert kinds(obs['events'], 'said') and not obs['state'].get('paused')


def test_a_click_walks_round_the_walls_by_the_shortest_way(puzzle, godot):
    with PlaySession(puzzle, binary=godot) as game:
        game.act(tap=['maze'], ticks=3)
        obs = game.act(cursor=[117, 63], tap=['click'], ticks=2)   # (6, 3): behind two walls
        route = kinds(obs['events'], 'route')
        assert route and route[0]['cells'] == 17               # down, round the wall's foot, up, along, down
        obs = game.act(ticks=17 * 5 + 5)
        p = obs['state']['nodes']['p']
        assert (p['col'], p['row']) == (6, 3)
        obs = game.act(cursor=[117, 81], tap=['click'], ticks=12)  # (6, 4): a crate beside it, stepped into
        assert 'crate' not in obs['state']['things']


# --- a scene drawn in Tiled ---

TSX = '''<?xml version="1.0" encoding="UTF-8"?>
<tileset version="1.10" name="kenney" tilewidth="18" tileheight="18" tilecount="180" columns="20">
 <image source="../../assets/kenney/tilemap_packed.png" width="360" height="162"/>
</tileset>
'''

TMX = '''<?xml version="1.0" encoding="UTF-8"?>
<map version="1.10" orientation="orthogonal" width="6" height="4" tilewidth="18" tileheight="18">
 <properties><property name="title" value="Cellar"/><property name="par" type="int" value="7"/></properties>
 <tileset firstgid="1" source="kenney.tsx"/>
 <tileset firstgid="181" name="bg" tilewidth="18" tileheight="18" tilecount="40" columns="10">
  <image source="tilemap-backgrounds_packed.png" width="192" height="72"/>
 </tileset>
 <layer id="1" name="sky" width="6" height="4">
  <data encoding="csv">
181,182,183,181,182,183,
0,0,0,0,0,0,
0,0,0,0,0,0,
0,0,0,0,0,0
</data>
 </layer>
 <layer id="2" name="ground" width="6" height="4">
  <properties><property name="collision" type="bool" value="true"/></properties>
  <data encoding="csv">
0,0,0,0,0,0,
0,0,0,0,0,0,
0,0,0,0,0,0,
2147483672,1073741848,24,536870936,11,0
</data>
 </layer>
 <objectgroup id="3" name="things">
  <object id="1" name="gem" class="Gem" x="45" y="27"><properties><property name="state" value="lit"/></properties><point/></object>
  <object id="2" name="cool" class="zone" x="72" y="36" width="18" height="18"><properties><property name="tag" value="cool"/></properties></object>
  <object id="3" name="out" class="exit" x="90" y="36" width="18" height="18"><properties><property name="to" value="beyond"/><property name="at" value="in"/></properties></object>
  <object id="4" name="flight" class="path" x="0" y="9"><polyline points="0,0 100,0"/></object>
 </objectgroup>
</map>
'''

TILED = '''<q:application id="tiled" type="game">
  <qg:tileset name="k" src="assets/kenney/tilemap_packed.png" tile="18">
    <qg:tile frame="10" frames="3" fps="6" />
  </qg:tileset>
  <qg:tileset name="bg" src="assets/kenney/tilemap-backgrounds_packed.png" tile="18" />
  <qg:spritesheet name="c" src="assets/kenney/tilemap-characters_packed.png" tile="24" />
  <qg:prefab name="Gem" tag="gem" sheet="k" frame="67" hitbox="12x12" solid="true">
    <qg:state name="dim" initial="true" />
    <qg:state name="lit" frame="68" />
  </qg:prefab>
  <qg:prefab name="Bird" tag="bird" sheet="k" frame="150" hitbox="8x8" ai="path" speed="60" />
  <q:set name="cooled" value="0" type="number" />
  <qg:scene name="cellar" width="108" height="72">
    <q:set name="title" value="{tiled('title') + ' ' + str(tiled('par'))}" />
    <qg:tilemap tileset="k" src="maps/cellar.tmx" />
    <qg:character id="w" controller="grid" sheet="c" frame="0" x="9" y="45" hitbox="14x14" step-frames="4">
      <qg:on-collision with="cool"><q:set name="cooled" value="{cooled + 1}" /></qg:on-collision>
    </qg:character>
    <qg:timer after="1"><qg:spawn prefab="Bird" at="path" path="flight" /></qg:timer>
  </qg:scene>
  <qg:scene name="beyond" width="108" height="72">
    <qg:exit name="in" x="0" y="0" width="18" height="18" to="cellar" at="out" />
  </qg:scene>
</q:application>
'''

PROBE = '''extends SceneTree
# The Tilemap's layers of the main scene after a tick: each used cell's atlas coords and alternative (its
# flips), and the frames of each animated tile.
var ticks := 0
var scene: Node

func _initialize() -> void:
	scene = load(ProjectSettings.get_setting("application/run/main_scene")).instantiate()
	root.add_child(scene)

func _physics_process(_delta: float) -> bool:
	ticks += 1
	if ticks < 3:
		return false
	var map := root.find_child("Tilemap", true, false)
	var out := {}
	for layer in map.get_children():
		var cells := {}
		var source: TileSetAtlasSource = layer.tile_set.get_source(layer.tile_set.get_source_id(0))
		for c in layer.get_used_cells():
			var at: Vector2i = layer.get_cell_atlas_coords(c)
			cells["%d,%d" % [c.x, c.y]] = [at.x, at.y, layer.get_cell_alternative_tile(c),
				source.get_tile_animation_frames_count(at)]
		out[String(layer.name)] = {"cells": cells, "texture": [source.texture.get_width(), source.texture.get_height()]}
	var f := FileAccess.open(OS.get_cmdline_user_args()[0], FileAccess.WRITE)
	f.store_string(JSON.stringify(out))
	return true
'''


@pytest.fixture(scope='module')
def tiled(tmp_path_factory, godot):
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    folder = tmp_path_factory.mktemp('tiled')
    (folder / 'maps').mkdir()
    (folder / 'maps' / 'cellar.tmx').write_text(TMX, encoding='utf-8')
    (folder / 'maps' / 'kenney.tsx').write_text(TSX, encoding='utf-8')
    src = folder / 'tiled.q'
    src.write_text(TILED, encoding='utf-8')
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(src)), str(folder / 'godot'),
                            source_dir=str(REPO)))
    assert check_project(out, binary=godot) == []
    return out


def test_two_tilesets_flipped_tiles_and_an_animated_one(tiled, godot):
    with tempfile.TemporaryDirectory() as tmp:
        probe = Path(tmp) / 'probe.gd'
        probe.write_text(PROBE, encoding='utf-8')
        run_godot(['--path', str(tiled), '-s', str(probe), '--', str(Path(tmp) / 'out.json')], binary=godot)
        layers = json.loads((Path(tmp) / 'out.json').read_text())
    assert layers['sky']['texture'] == [192, 72]                      # the map's second tileset's picture
    assert layers['sky']['cells']['1,0'][:3] == [1, 0, 0]
    ground = layers['ground']
    assert ground['texture'] == [360, 162]
    flip_h, flip_v, transpose = 4096, 8192, 16384                        # Godot's TileSetAtlasSource flags
    assert ground['cells']['0,3'][:3] == [3, 1, flip_h]                  # tile 24, left to right
    assert ground['cells']['1,3'][:3] == [3, 1, flip_v]                  # upside down
    assert ground['cells']['2,3'][:3] == [3, 1, 0]
    assert ground['cells']['3,3'][:3] == [3, 1, transpose]               # across the diagonal
    assert ground['cells']['4,3'] == [10, 0, 0, 3]                       # tile 11: frame 10, three frames in turn


def test_the_map_places_states_zones_exits_paths_and_properties(tiled, godot):
    with PlaySession(tiled, binary=godot) as game:
        obs = game.act(ticks=3)
        state = obs['state']
        assert state['title'] == 'Cellar 7'                                 # the map's properties, as it compiled
        assert ['gem', 45.0, 27.0, 'lit'] in state['where']                 # its state from the map
        assert any(t == 'bird' for t, *_ in state['where'])                 # spawned on the map's path
        obs = steps(game, 'right', 4, frames=5)                             # onto the zone at (4, 2)
        assert [e['with'] for e in kinds(obs['events'], 'touch')] == ['cool']
        assert obs['state']['game']['cooled'] == 1
        obs = steps(game, 'right', 1, frames=5)                             # into the exit at (5, 2)
        assert obs['scene'] == 'beyond'


# --- over the network: what a click chose and what was pushed and carried, the same on both peers ---

PAIR = '''<q:application id="pair" type="game">
  <qg:tileset name="k" src="assets/kenney/tilemap_packed.png" tile="18" />
  <qg:spritesheet name="c" src="assets/kenney/tilemap-characters_packed.png" tile="24" />
  <qg:multiplayer players="2" start="yard" />
  <qg:prefab name="Crate" tag="crate" sheet="k" frame="6" hitbox="16x16" solid="true" pushable="true" />
  <qg:prefab name="Key" tag="key" sheet="k" frame="27" hitbox="12x12" />
  <qg:scene name="yard" width="180" height="108">
    <qg:tilemap tileset="k" collision="true">
23,23,23,23,23,23,23,23,23,23
23,0,0,0,0,0,0,0,0,23
23,0,0,0,0,0,0,0,0,23
23,0,0,0,0,0,0,0,0,23
23,0,0,0,0,0,0,0,0,23
23,23,23,23,23,23,23,23,23,23
    </qg:tilemap>
    <qg:cursor player="1" grid="18" />
    <qg:cursor player="2" grid="18" />
    <qg:instance prefab="Crate" name="crate" x="63" y="27" />
    <qg:instance prefab="Key" name="key" x="117" y="63" />
    <qg:character id="p1" controller="pointer" player="1" sheet="c" frame="0" x="27" y="27" hitbox="14x14" step-frames="4" />
    <qg:character id="p2" controller="pointer" player="2" sheet="c" frame="0" x="27" y="63" hitbox="14x14" step-frames="4">
      <qg:on-collision with="key"><qg:attach target="other" /></qg:on-collision>
    </qg:character>
  </qg:scene>
</q:application>
'''


def test_over_the_network_a_click_a_push_and_a_carry_are_the_same_on_both(tmp_path_factory, godot):
    project = build(tmp_path_factory, godot, 'pair', PAIR)
    pusher = tape_from_holds([('right', 10, 40)])                  # p1 walks right, pushing the crate
    walker = cursor_at(tape_from_holds([('click', 10, 14)]), 5, 117, 63)   # p2 clicks the key: walks into it
    peers = replay_peers(project, 120, [pusher, walker], binary=godot)
    assert peers[0] == peers[1]
    yard = peers[0]['yard']
    assert yard['named']['crate']['x'] > 63                        # pushed on
    p2, key = yard['nodes']['p2'], yard['named']['key']
    assert (p2['col'], p2['row']) == (5, 3) and (key['x'], key['y']) == (p2['x'], p2['y'] - 12)   # carried
