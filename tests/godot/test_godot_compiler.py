"""The game compiler, without Godot: what it writes, and what it refuses.

The language has no escape hatch and no silent defaults: a tag or an
attribute the schema does not know, a name no q:set declared, text where
statements go — each is a GameCompileError naming the line.
"""

import json
import re
from pathlib import Path

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.godot import GameCompileError, compile_game
from quantum.runtime.godot.expressions import Scope, compile_expression

ASSETS = Path(__file__).resolve().parents[2] / 'assets' / 'kenney'

HEAD = '''<q:application id="t" type="game">
  <qg:tileset name="k" src="assets/kenney/tilemap_packed.png" tile="18" />
  <qg:spritesheet name="c" src="assets/kenney/tilemap-characters_packed.png" tile="24" />
  <qg:prefab name="Coin" tag="coin" sheet="k" frame="151" hitbox="12x12" />
'''
TAIL = '</q:application>\n'


def game(body: str) -> str:
    return HEAD + body + TAIL


def build(tmp_path: Path, source: str) -> Path:
    src = tmp_path / 'game.q'
    src.write_text(source, encoding='utf-8')
    app = QuantumParser(use_cache=False).parse_file(str(src))
    out = tmp_path / 'godot'
    compile_game(app, str(out), source_dir=str(ASSETS.parents[1]))
    return out


def refuse(tmp_path: Path, source: str) -> GameCompileError:
    with pytest.raises(GameCompileError) as info:
        build(tmp_path, source)
    return info.value


SCENE = '''  <qg:scene name="main">
    <q:set name="coins" value="0" type="number" />
    <q:set name="title" value="Hop" />
    <q:set name="done" value="false" type="boolean" />
    <qg:tilemap tileset="k" collision="true">
0,0,0
23,23,23
    </qg:tilemap>
    <qg:character id="player" controller="platformer" sheet="c" x="10" y="10" hitbox="18x22">
      <qg:on-collision with="coin">
        <qg:destroy />
        <q:set name="coins" value="{coins + 1}" />
        <q:if condition="{coins >= 2 and not done}">
          <q:set name="done" value="true" />
        <q:else>
          <q:set name="title" value="{title + '!'}" />
        </q:else>
        </q:if>
      </qg:on-collision>
    </qg:character>
    <qg:instance prefab="Coin" x="30" y="10" />
    <qg:camera follow="player" />
    <qg:hud><qg:counter bind="coins" label="COINS" /></qg:hud>
  </qg:scene>
'''


class TestWhatItWrites:
    def test_the_project_files(self, tmp_path):
        out = build(tmp_path, game(SCENE))
        assert (out / 'project.godot').read_text().count('run/main_scene="res://main.tscn"') == 1
        assert 'script = ExtResource("1")' in (out / 'main.tscn').read_text()
        assert (out / 'addons' / 'quantum' / 'scene_builder.gd').is_file()
        assert (out / 'assets' / 'kenney' / 'tilemap_packed.png').is_file()
        data = json.loads((out / 'game.json').read_text())
        assert data['initial'] == 'main'
        scene = data['scenes']['main']
        assert scene['script'] == 'res://scripts/scene_main.gd'
        kinds = [n['kind'] for n in scene['nodes']]
        assert kinds == ['tilemap', 'character', 'instance', 'camera', 'hud']
        assert scene['nodes'][0]['layers'] == [{'name': 'tiles', 'rows': [[0, 0, 0], [23, 23, 23]], 'collision': True}]
        assert scene['nodes'][1]['on_collision'] == [
            {'with': 'coin', 'side': 'any', 'cooldown': 0, 'handler': '_on_player_collision_0'}]
        coin = data['prefabs']['Coin']
        assert {k: coin[k] for k in ('tag', 'sheet', 'frame', 'hitbox')} == {
            'tag': 'coin', 'sheet': 'k', 'frame': 151, 'hitbox': [12, 12]}
        assert coin['ai'] is None and coin['animations'] == {}

    def test_the_scene_script(self, tmp_path):
        out = build(tmp_path, game(SCENE))
        script = (out / 'scripts' / 'scene_main.gd').read_text()
        assert script.startswith('extends "res://addons/quantum/quantum_scene.gd"\n')
        assert 'var coins: float = 0.0\n' in script
        assert 'var title: String = "Hop"\n' in script
        assert 'var done: bool = false\n' in script
        assert 'return {"coins": coins, "title": title, "done": done}' in script
        assert ('func _on_player_collision_0(me, other) -> void:\n'
                '\tQ.destroy(other)\n'
                '\tcoins = (coins + 1)\n'
                '\tif ((coins >= 2) and (not done)):\n'
                '\t\tdone = true\n'
                '\telse:\n'
                '\t\ttitle = (title + "!")\n') in script

    def test_a_function_and_a_loop(self, tmp_path):
        out = build(tmp_path, game('''  <qg:scene name="main">
    <q:set name="total" value="0" type="number" />
    <q:function name="add" params="n, times">
      <q:loop var="i" from="1" to="{times}">
        <q:set name="total" value="{total + n}" />
      </q:loop>
      <q:return value="{total}" />
    </q:function>
  </qg:scene>
'''))
        script = (out / 'scripts' / 'scene_main.gd').read_text()
        assert ('func add(n, times):\n'
                '\tfor i in range(int(1), int(times) + 1):\n'
                '\t\ttotal = (total + n)\n'
                '\treturn total\n') in script


class TestEnemiesSoundsAndAnimations:
    SOURCE = HEAD + '''  <qg:sound name="hurt" src="assets/kenney/audio/hurt.ogg" />
  <qg:prefab name="Walker" tag="enemy" sheet="c" frame="18" hitbox="18x18" ai="patrol" speed="30" turns-at="edge">
    <qg:animation name="walk" frames="18, 19,20" fps="6" />
  </qg:prefab>
  <qg:scene name="main">
    <q:set name="lives" value="3" type="number" />
    <qg:tilemap tileset="k" collision="true">
23,23
    </qg:tilemap>
    <qg:character id="player" controller="platformer" sheet="c" x="10" y="10" hitbox="18x22" jump-sound="hurt">
      <qg:animation name="idle" frames="0" />
      <qg:on-collision with="enemy" side="top">
        <qg:destroy target="other" />
        <qg:bounce target="me" height="32" />
      </qg:on-collision>
      <qg:on-collision with="enemy" cooldown="60">
        <qg:play sound="hurt" />
        <q:set name="lives" value="{lives - 1}" />
        <qg:respawn target="me" />
      </qg:on-collision>
      <qg:on-fall>
        <qg:respawn />
      </qg:on-fall>
    </qg:character>
    <qg:instance prefab="Walker" x="30" y="10" />
  </qg:scene>
''' + TAIL

    def test_the_json(self, tmp_path):
        out = build(tmp_path, self.SOURCE)
        data = json.loads((out / 'game.json').read_text())
        assert data['sounds'] == {'hurt': {'src': 'assets/kenney/audio/hurt.ogg'}}
        assert (out / 'assets' / 'kenney' / 'audio' / 'hurt.ogg').is_file()
        walker = data['prefabs']['Walker']
        assert walker['ai'] == 'patrol' and walker['speed'] == 30 and walker['turns_at'] == 'edge'
        assert walker['direction'] == 'left'
        assert walker['animations'] == {'walk': {'frames': [18, 19, 20], 'fps': 6}}
        character = data['scenes']['main']['nodes'][1]
        assert character['jump_sound'] == 'hurt'
        assert character['animations'] == {'idle': {'frames': [0], 'fps': 8}}
        assert character['on_collision'] == [
            {'with': 'enemy', 'side': 'top', 'cooldown': 0, 'handler': '_on_player_collision_0'},
            {'with': 'enemy', 'side': 'any', 'cooldown': 60, 'handler': '_on_player_collision_1'},
        ]
        assert character['on_fall'] == '_on_player_fall'

    def test_the_actions(self, tmp_path):
        out = build(tmp_path, self.SOURCE)
        script = (out / 'scripts' / 'scene_main.gd').read_text()
        assert 'func _on_player_collision_0(me, other) -> void:\n\tQ.destroy(other)\n\tQ.bounce(me, 32.0)\n' in script
        assert ('func _on_player_collision_1(me, other) -> void:\n\tQ.play("hurt")\n'
                '\tlives = (lives - 1)\n\tQ.respawn(me)\n') in script
        assert 'func _on_player_fall(me, other) -> void:\n\tQ.respawn(me)\n' in script

    def test_a_sound_nobody_declared(self, tmp_path):
        e = refuse(tmp_path, game('''  <qg:scene name="main">
    <qg:character id="p" controller="platformer" sheet="c" x="0" y="0" hitbox="1x1">
      <qg:on-collision with="coin"><qg:play sound="ding" /></qg:on-collision>
    </qg:character>
  </qg:scene>
'''))
        assert '<qg:play sound="ding">: no qg:sound of that name' in e.message

    def test_a_jump_sound_nobody_declared(self, tmp_path):
        e = refuse(tmp_path, game('''  <qg:scene name="main">
    <qg:character id="p" controller="platformer" sheet="c" x="0" y="0" hitbox="1x1" jump-sound="boing" />
  </qg:scene>
'''))
        assert 'jump-sound="boing": no qg:sound of that name' in e.message

    def test_frames_must_be_numbers(self, tmp_path):
        e = refuse(tmp_path, game('''  <qg:scene name="main">
    <qg:character id="p" controller="platformer" sheet="c" x="0" y="0" hitbox="1x1">
      <qg:animation name="walk" frames="a,b" />
    </qg:character>
  </qg:scene>
'''))
        assert 'frames="a,b": comma-separated frame numbers' in e.message

    def test_an_action_outside_a_handler(self, tmp_path):
        e = refuse(tmp_path, game('  <qg:scene name="main"><qg:bounce /></qg:scene>\n'))
        assert '<qg:bounce> cannot go inside <scene>' in e.message


class TestStatesBlocksAndSpawns:
    SOURCE = HEAD + '''  <qg:prefab name="QBlock" tag="qblock" sheet="k" frame="10" hitbox="18x18" solid="true" />
  <qg:prefab name="Used" tag="used" sheet="k" frame="11" hitbox="18x18" solid="true" />
  <qg:prefab name="Shroom" tag="shroom" sheet="k" frame="128" hitbox="12x12" ai="patrol" direction="right" />
  <qg:prefab name="Post" tag="post" sheet="k" frame="111" hitbox="18x18" />
  <qg:scene name="main">
    <q:set name="message" value="" />
    <qg:character id="player" controller="platformer" sheet="c" x="10" y="10" hitbox="18x22">
      <qg:state name="small" hitbox="18x22" frame="0" initial="true" />
      <qg:state name="big" hitbox="18x30" frame="3">
        <qg:animation name="walk" frames="4,5" />
      </qg:state>
      <qg:on-collision with="qblock" side="bottom">
        <qg:swap target="other" prefab="Used" />
        <qg:spawn prefab="Shroom" at="other" dy="-18" />
      </qg:on-collision>
      <qg:on-collision with="shroom">
        <qg:destroy />
        <qg:become state="big" />
      </qg:on-collision>
      <qg:on-collision with="post">
        <qg:checkpoint target="me" at="other" />
        <q:if condition="{me.state == 'big'}"><q:set name="message" value="big!" /></q:if>
      </qg:on-collision>
    </qg:character>
    <qg:instance prefab="QBlock" x="30" y="10" />
    <qg:hud><qg:text bind="message" /></qg:hud>
  </qg:scene>
''' + TAIL

    def test_the_json(self, tmp_path):
        out = build(tmp_path, self.SOURCE)
        data = json.loads((out / 'game.json').read_text())
        assert data['prefabs']['QBlock']['solid'] is True
        character = data['scenes']['main']['nodes'][0]
        assert character['initial_state'] == 'small'
        assert character['states'] == {
            'small': {'hitbox': [18, 22], 'frame': 0, 'speed': None, 'fire_every': None, 'animations': {}},
            'big': {'hitbox': [18, 30], 'frame': 3, 'speed': None, 'fire_every': None,
                    'animations': {'walk': {'frames': [4, 5], 'fps': 8}}},
        }
        assert character['on_collision'][0]['side'] == 'bottom'
        assert data['scenes']['main']['nodes'][2]['items'] == [{'kind': 'text', 'bind': 'message', 'label': ''}]

    def test_the_actions(self, tmp_path):
        out = build(tmp_path, self.SOURCE)
        script = (out / 'scripts' / 'scene_main.gd').read_text()
        assert '\tQ.swap(self, other, "Used")\n\tQ.spawn(self, "Shroom", other, 0.0, -18.0)\n' in script
        assert '\tQ.destroy(other)\n\tQ.become(me, "big")\n' in script
        assert '\tQ.checkpoint(me, other)\n\tif (me.state == "big"):\n\t\tmessage = "big!"\n' in script

    def test_a_state_nobody_declared(self, tmp_path):
        e = refuse(tmp_path, game('''  <qg:scene name="main">
    <qg:character id="p" controller="platformer" sheet="c" x="0" y="0" hitbox="1x1">
      <qg:state name="small" hitbox="1x1" />
      <qg:on-collision with="coin"><qg:become state="huge" /></qg:on-collision>
    </qg:character>
  </qg:scene>
'''))
        assert '<qg:become state="huge">: \'p\' has no qg:state of that name (it has: small)' in e.message

    def test_a_spawned_prefab_nobody_declared(self, tmp_path):
        e = refuse(tmp_path, game('''  <qg:scene name="main">
    <qg:character id="p" controller="platformer" sheet="c" x="0" y="0" hitbox="1x1">
      <qg:on-collision with="coin"><qg:spawn prefab="Gem" /></qg:on-collision>
    </qg:character>
  </qg:scene>
'''))
        assert "no qg:prefab named 'Gem' (declared: Coin)" in e.message
        assert e.line == 7

    def test_solid_and_ai_exclude_each_other(self, tmp_path):
        e = refuse(tmp_path, HEAD + '  <qg:prefab name="X" sheet="k" hitbox="1x1" solid="true" ai="patrol" />\n'
                   '  <qg:scene name="main" />\n' + TAIL)
        assert 'solid or has ai=, not both' in e.message


class TestScenesMapAndGameState:
    SOURCE = '''<q:application id="t" type="game">
  <q:set name="lives" value="3" type="number" />
  <q:set name="cleared" value="[]" type="array" />
  <q:set name="map_at" value="one" />
  <qg:tileset name="k" src="assets/kenney/tilemap_packed.png" tile="18" />
  <qg:spritesheet name="c" src="assets/kenney/tilemap-characters_packed.png" tile="24" />
  <qg:prefab name="Flag" tag="flag" sheet="k" hitbox="18x18" />
  <qg:scene name="map">
    <qg:map-node name="one" x="10" y="10" sheet="k" scene="one" />
    <qg:map-node name="two" x="50" y="10" sheet="k" scene="two" />
    <qg:map-path from="one" to="two" requires="one" />
    <qg:character id="player" controller="map" sheet="c" at="{map_at}" x="0" y="0" hitbox="1x1" />
    <qg:hud><qg:counter bind="lives" label="LIVES" /></qg:hud>
  </qg:scene>
  <qg:scene name="one">
    <q:set name="coins" value="0" type="number" />
    <q:function name="die" params="me">
      <q:set name="lives" value="{lives - 1}" />
      <q:if condition="{lives <= 0}"><qg:goto-scene name="over" /><q:else><qg:respawn /></q:else></q:if>
    </q:function>
    <qg:character id="player" controller="platformer" sheet="c" x="0" y="0" hitbox="1x1">
      <qg:on-collision with="flag">
        <q:set name="cleared" value="{cleared + ['one']}" />
        <q:set name="coins" value="{coins + lives}" />
        <qg:goto-scene name="map" />
      </qg:on-collision>
      <qg:on-fall><q:call function="die" args="me" /></qg:on-fall>
    </qg:character>
  </qg:scene>
  <qg:scene name="two" />
  <qg:scene name="over">
    <qg:on-input action="jump"><q:set name="lives" value="3" /><qg:goto-scene name="map" /></qg:on-input>
  </qg:scene>
</q:application>
'''

    def test_the_game_state_is_an_autoload(self, tmp_path):
        out = build(tmp_path, self.SOURCE)
        assert 'G="*res://scripts/game_state.gd"' in (out / 'project.godot').read_text()
        state = (out / 'scripts' / 'game_state.gd').read_text()
        assert 'var lives: float = 3.0\nvar cleared: Array = []\nvar map_at: String = "one"\n' in state
        assert 'return {"lives": lives, "cleared": cleared, "map_at": map_at}' in state

    def test_scene_logic_reads_and_writes_it_through_g(self, tmp_path):
        out = build(tmp_path, self.SOURCE)
        one = (out / 'scripts' / 'scene_one.gd').read_text()
        assert ('func die(me):\n\tG.lives = (G.lives - 1)\n\tif (G.lives <= 0):\n'
                '\t\tQ.goto_scene(self, "over")\n\telse:\n\t\tQ.respawn(me)\n') in one
        assert '\tG.cleared = (G.cleared + ["one"])\n\tcoins = (coins + G.lives)\n\tQ.goto_scene(self, "map")\n' in one
        assert 'func _on_player_fall(me, other) -> void:\n\tdie(me)\n' in one
        over = (out / 'scripts' / 'scene_over.gd').read_text()
        assert 'func _on_input_jump(me, other) -> void:\n\tG.lives = 3.0\n\tQ.goto_scene(self, "map")\n' in over

    def test_the_map(self, tmp_path):
        out = build(tmp_path, self.SOURCE)
        data = json.loads((out / 'game.json').read_text())
        assert data['initial'] == 'map'
        m = data['scenes']['map']
        assert m['map_paths'] == [{'from': 'one', 'to': 'two', 'requires': 'one'}]
        assert m['nodes'][0] == {'kind': 'map-node', 'name': 'one', 'x': 10, 'y': 10, 'sheet': 'k',
                                 'frame': 0, 'scene': 'one'}
        walker = m['nodes'][2]
        assert walker['controller'] == 'map' and walker['at_method'] == '_q_at_player'
        assert 'func _q_at_player():\n\treturn G.map_at\n' in (out / 'scripts' / 'scene_map.gd').read_text()
        assert data['scenes']['over']['on_input'] == {'jump': '_on_input_jump'}

    def test_a_scene_nobody_declared(self, tmp_path):
        e = refuse(tmp_path, game('''  <qg:scene name="main">
    <qg:on-input action="jump"><qg:goto-scene name="credits" /></qg:on-input>
  </qg:scene>
'''))
        assert "no qg:scene named 'credits' (declared: main)" in e.message

    def test_a_map_path_to_nowhere(self, tmp_path):
        e = refuse(tmp_path, game('''  <qg:scene name="map">
    <qg:map-node name="one" x="1" y="1" sheet="k" />
    <qg:map-path from="one" to="two" />
  </qg:scene>
'''))
        assert '<qg:map-path to="two">: no map node of that name' in e.message

    def test_requires_needs_the_cleared_state(self, tmp_path):
        e = refuse(tmp_path, game('''  <qg:scene name="map">
    <qg:map-node name="one" x="1" y="1" sheet="k" />
    <qg:map-node name="two" x="9" y="1" sheet="k" />
    <qg:map-path from="one" to="two" requires="map" />
  </qg:scene>
'''))
        assert '<q:set name="cleared" type="array" /> in <q:application>' in e.message

    def test_a_scene_state_cannot_shadow_the_game_state(self, tmp_path):
        e = refuse(tmp_path, '<q:application id="t" type="game">\n  <q:set name="lives" value="3" type="number" />\n'
                   '  <qg:scene name="main"><q:set name="lives" value="1" type="number" /></qg:scene>\n</q:application>\n')
        assert "'lives' is already the game's state" in e.message

    def test_only_q_set_goes_in_the_application(self, tmp_path):
        e = refuse(tmp_path, '<q:application id="t" type="game">\n  <q:function name="f" />\n'
                   '  <qg:scene name="main" />\n</q:application>\n')
        assert '<q:function> goes inside a <qg:scene>; only q:set goes here, as game state' in e.message

    def test_a_call_to_no_function(self, tmp_path):
        e = refuse(tmp_path, game('''  <qg:scene name="main">
    <qg:on-input action="jump"><q:call function="boom" /></qg:on-input>
  </qg:scene>
'''))
        assert '<q:call function="boom">: no q:function of that name' in e.message


TMX = '''<?xml version="1.0" encoding="UTF-8"?>
<map version="1.10" orientation="orthogonal" width="3" height="2" tilewidth="18" tileheight="18">
 <tileset firstgid="1" name="kenney" tilewidth="18" tileheight="18" tilecount="180" columns="20">
  <image source="x.png" width="360" height="162"/>
 </tileset>
 <layer id="1" name="decor" width="3" height="2">
  <data encoding="csv">
0,11,0,
0,0,0
</data>
 </layer>
 <layer id="2" name="ground" width="3" height="2">
  <properties><property name="collision" type="bool" value="true"/></properties>
  <data encoding="csv">
0,0,0,
23,23,23
</data>
 </layer>
 <objectgroup id="3" name="things">
  <object id="1" name="a" class="Coin" x="30" y="10"><point/></object>
  <object id="2" type="Coin" x="10" y="10" width="20" height="10"/>
  <object id="3" name="Coin" gid="5" x="40" y="36" width="18" height="18"/>
 </objectgroup>
</map>
'''


class TestTiledMaps:
    def scene(self, tmp_path, tmx=TMX, extra=''):
        (tmp_path / 'level.tmx').write_text(tmx, encoding='utf-8')
        return game(f'  <qg:scene name="main">\n    <qg:tilemap tileset="k" src="level.tmx" {extra}/>\n  </qg:scene>\n')

    def test_layers_and_objects(self, tmp_path):
        out = build(tmp_path, self.scene(tmp_path))
        scene = json.loads((out / 'game.json').read_text())['scenes']['main']
        tilemap = scene['nodes'][0]
        assert tilemap['layers'] == [
            {'name': 'decor', 'rows': [[0, 11, 0], [0, 0, 0]], 'collision': False},
            {'name': 'ground', 'rows': [[0, 0, 0], [23, 23, 23]], 'collision': True},
        ]
        placed = [(n['prefab'], n['x'], n['y']) for n in scene['nodes'][1:]]
        assert placed == [('Coin', 30.0, 10.0),      # a point
                          ('Coin', 20.0, 15.0),      # a rectangle, at its centre
                          ('Coin', 49.0, 27.0)]      # a tile, whose y is its bottom edge

    def test_collision_on_the_tag_makes_every_layer_solid(self, tmp_path):
        out = build(tmp_path, self.scene(tmp_path, extra='collision="true" '))
        scene = json.loads((out / 'game.json').read_text())['scenes']['main']
        assert [ly['collision'] for ly in scene['nodes'][0]['layers']] == [True, True]

    def test_an_object_whose_class_is_no_prefab(self, tmp_path):
        tmx = TMX.replace('class="Coin"', 'class="Gem"')
        e = refuse(tmp_path, self.scene(tmp_path, tmx))
        assert "level.tmx: object 'a' has class 'Gem', no qg:prefab of that name" in e.message

    def test_a_flipped_tile(self, tmp_path):
        tmx = TMX.replace('23,23,23', '23,2147483671,23')
        e = refuse(tmp_path, self.scene(tmp_path, tmx))
        assert "layer 'ground' has a flipped or rotated tile" in e.message

    def test_a_layer_not_saved_as_csv(self, tmp_path):
        tmx = TMX.replace('<data encoding="csv">\n0,11,0,\n0,0,0\n</data>', '<data encoding="base64">AAAA</data>')
        e = refuse(tmp_path, self.scene(tmp_path, tmx))
        assert "layer 'decor' must be saved as CSV" in e.message

    def test_two_tilesets(self, tmp_path):
        tmx = TMX.replace('</tileset>', '</tileset><tileset firstgid="181" name="b" tilewidth="18" tileheight="18"/>')
        e = refuse(tmp_path, self.scene(tmp_path, tmx))
        assert 'one tileset per map (2 found)' in e.message

    def test_tile_size_must_match_the_tileset(self, tmp_path):
        tmx = TMX.replace('tilewidth="18" tileheight="18">\n <tileset', 'tilewidth="16" tileheight="16">\n <tileset')
        e = refuse(tmp_path, self.scene(tmp_path, tmx))
        assert "tiles are 16x16, the tileset 'k' has 18x18" in e.message

    def test_src_or_rows_not_both(self, tmp_path):
        (tmp_path / 'level.tmx').write_text(TMX, encoding='utf-8')
        e = refuse(tmp_path, game('  <qg:scene name="main"><qg:tilemap tileset="k" src="level.tmx">\n1\n</qg:tilemap></qg:scene>\n'))
        assert 'has src= or the CSV rows, not both' in e.message

    def test_a_missing_map(self, tmp_path):
        e = refuse(tmp_path, game('  <qg:scene name="main"><qg:tilemap tileset="k" src="levels/none.tmx" /></qg:scene>\n'))
        assert 'file not found: levels/none.tmx' in e.message


class TestTopDownExitsAndHits:
    SOURCE = '''<q:application id="t" type="game">
  <q:set name="taken" value="[]" type="array" />
  <qg:tileset name="k" src="assets/kenney/tilemap_packed.png" tile="18" />
  <qg:spritesheet name="c" src="assets/kenney/tilemap-characters_packed.png" tile="24" />
  <qg:sound name="hit" src="assets/kenney/audio/stomp.ogg" />
  <qg:prefab name="Slime" tag="enemy" sheet="c" hitbox="14x14" ai="wander" speed="25" />
  <qg:prefab name="Bat" tag="enemy" sheet="c" hitbox="14x14" ai="chase" speed="40" sight="90" />
  <qg:prefab name="Key" tag="key" sheet="k" hitbox="12x12" />
  <qg:scene name="a">
    <qg:character id="player" controller="topdown" sheet="c" x="10" y="10" hitbox="14x14" speed="70"
                  attack-action="jump" attack-reach="16" attack-frames="12" attack-sound="hit">
      <qg:on-hit with="enemy"><qg:destroy /></qg:on-hit>
      <qg:on-collision with="key">
        <q:set name="taken" value="{taken + [other.name]}" />
        <qg:destroy />
      </qg:on-collision>
    </qg:character>
    <qg:instance prefab="Key" name="key-1" x="30" y="10" if="{'key-1' not in taken}" />
    <qg:instance prefab="Slime" x="50" y="10" />
    <qg:exit name="east" x="252" y="99" width="8" height="36" to="b" at="west" />
  </qg:scene>
  <qg:scene name="b">
    <qg:exit name="west" x="-4" y="99" width="8" height="36" to="a" at="east" />
  </qg:scene>
</q:application>
'''

    def test_the_json(self, tmp_path):
        out = build(tmp_path, self.SOURCE)
        data = json.loads((out / 'game.json').read_text())
        assert data['prefabs']['Slime']['ai'] == 'wander'
        assert data['prefabs']['Bat']['sight'] == 90
        a = data['scenes']['a']
        player = a['nodes'][0]
        assert player['controller'] == 'topdown' and player['speed'] == 70
        assert (player['attack_action'], player['attack_reach'], player['attack_frames'], player['attack_sound']) == \
            ('jump', 16, 12, 'hit')
        assert player['on_hit'] == [{'with': 'enemy', 'handler': '_on_player_hit_0'}]
        key, slime, exit_ = a['nodes'][1], a['nodes'][2], a['nodes'][3]
        assert key['name'] == 'key-1' and key['if'] == '_q_if_1'
        assert slime['name'] is None and slime['if'] is None
        assert exit_ == {'kind': 'exit', 'name': 'east', 'x': 252, 'y': 99, 'width': 8, 'height': 36,
                         'to': 'b', 'at': 'west'}

    def test_the_script(self, tmp_path):
        out = build(tmp_path, self.SOURCE)
        script = (out / 'scripts' / 'scene_a.gd').read_text()
        assert 'func _q_if_1() -> bool:\n\treturn ("key-1" not in G.taken)\n' in script
        assert 'func _on_player_hit_0(me, other) -> void:\n\tQ.destroy(other)\n' in script
        assert '\tG.taken = (G.taken + [other.name])\n' in script
        assert 'var _q_arrive_at: String = ""' in (out / 'scripts' / 'game_state.gd').read_text()

    def test_an_exit_to_an_exit_that_is_not_there(self, tmp_path):
        e = refuse(tmp_path, game('''  <qg:scene name="a">
    <qg:exit name="east" x="0" y="0" width="8" height="8" to="b" at="north" />
  </qg:scene>
  <qg:scene name="b">
    <qg:exit name="west" x="0" y="0" width="8" height="8" to="a" at="east" />
  </qg:scene>
'''))
        assert "<qg:exit to=\"b\" at=\"north\">: scene 'b' has no exit named 'north' (it has: west)" in e.message

    def test_on_hit_needs_an_attack(self, tmp_path):
        e = refuse(tmp_path, game('''  <qg:scene name="a">
    <qg:character id="p" controller="topdown" sheet="c" x="0" y="0" hitbox="1x1">
      <qg:on-hit with="coin" />
    </qg:character>
  </qg:scene>
'''))
        assert '<qg:on-hit> needs attack-action= on the character' in e.message

    def test_a_hit_with_a_tag_no_prefab_has(self, tmp_path):
        e = refuse(tmp_path, game('''  <qg:scene name="a">
    <qg:character id="p" controller="topdown" sheet="c" x="0" y="0" hitbox="1x1" attack-action="jump">
      <qg:on-hit with="ghost" />
    </qg:character>
  </qg:scene>
'''))
        assert '<qg:on-hit with="ghost">: no prefab has that tag' in e.message


class TestArcadePrefabsAndSpawners:
    SOURCE = '''<q:application id="t" type="game">
  <q:set name="score" value="0" type="number" />
  <q:set name="best" value="0" type="number" saved="true" />
  <qg:tileset name="k" src="assets/kenney/tilemap_packed.png" tile="18" />
  <qg:spritesheet name="c" src="assets/kenney/tilemap-characters_packed.png" tile="24" />
  <qg:sound name="boom" src="assets/kenney/audio/block.ogg" />
  <qg:prefab name="Shot" tag="shot" sheet="k" hitbox="6x6" ai="fly" heading="up" speed="240" lifetime="80">
    <qg:on-collision with="enemy"><qg:damage target="other" amount="2" /><qg:destroy target="me" /></qg:on-collision>
  </qg:prefab>
  <qg:prefab name="Drone" tag="enemy" sheet="c" hitbox="14x14" ai="fly" speed="45" health="3"
             fire-prefab="Shot" fire-every="90">
    <qg:state name="calm" frame="1" speed="30" fire-every="60" initial="true" />
    <qg:state name="angry" frame="2" speed="70" fire-every="25" />
    <qg:on-damage><q:if condition="{me.health <= 1}"><qg:become target="me" state="angry" /></q:if></qg:on-damage>
    <qg:on-death><qg:play sound="boom" /><qg:burst at="me" color="#ffcc44" count="10" /><qg:shake at="me" />
      <q:set name="score" value="{score + 100}" /></qg:on-death>
  </qg:prefab>
  <qg:scene name="play">
    <q:if condition="{score > best}"><q:set name="best" value="{score}" /></q:if>
    <qg:character id="ship" controller="ship" sheet="c" x="128" y="196" hitbox="14x14" speed="120"
                  fire-action="jump" fire-prefab="Shot" fire-every="10" />
    <qg:spawner prefab="Drone" from="60" every="40" count="8" x="random" y="-12" />
    <qg:spawner prefab="Drone" from="500" every="1" count="1" x="128" y="40" />
    <qg:on-death of="enemy"><q:set name="score" value="{score + 1}" /></qg:on-death>
  </qg:scene>
</q:application>
'''

    def test_the_prefabs_script_is_an_autoload(self, tmp_path):
        out = build(tmp_path, self.SOURCE)
        assert 'P="*res://scripts/prefabs.gd"' in (out / 'project.godot').read_text()
        p = (out / 'scripts' / 'prefabs.gd').read_text()
        assert 'func _Shot_on_collision_0(me, other) -> void:\n\tQ.damage(other, 2)\n\tQ.destroy(me)\n' in p
        assert ('func _Drone_on_damage(me, other) -> void:\n\tif (me.health <= 1):\n'
                '\t\tQ.become(me, "angry")\n') in p
        assert ('func _Drone_on_death(me, other) -> void:\n\tQ.play("boom")\n\tQ.burst(me, "#ffcc44", 10)\n'
                '\tQ.shake(me, 10, 3.0)\n\tG.score = (G.score + 100)\n') in p

    def test_the_json(self, tmp_path):
        out = build(tmp_path, self.SOURCE)
        data = json.loads((out / 'game.json').read_text())
        shot, drone = data['prefabs']['Shot'], data['prefabs']['Drone']
        assert (shot['ai'], shot['heading'], shot['lifetime'], shot['health']) == ('fly', 'up', 80, 1)
        assert shot['on_collision'] == [{'with': 'enemy', 'cooldown': 0, 'handler': '_Shot_on_collision_0'}]
        assert (drone['health'], drone['fire_prefab'], drone['fire_every']) == (3, 'Shot', 90)
        assert drone['on_damage'] == '_Drone_on_damage' and drone['on_death'] == '_Drone_on_death'
        assert drone['initial_state'] == 'calm'
        assert drone['states']['angry'] == {'hitbox': None, 'frame': 2, 'speed': 70, 'fire_every': 25,
                                            'animations': {}}
        play = data['scenes']['play']
        ship = play['nodes'][0]
        assert (ship['controller'], ship['fire_action'], ship['fire_prefab'], ship['fire_every']) == \
            ('ship', 'jump', 'Shot', 10)
        assert play['nodes'][1] == {'kind': 'spawner', 'prefab': 'Drone', 'from': 60, 'every': 40, 'count': 8,
                                    'x': 'random', 'y': -12}
        assert play['nodes'][2]['x'] == 128
        assert play['on_death'] == {'enemy': '_on_death_of_enemy'}

    def test_saved_state_and_enter_logic(self, tmp_path):
        out = build(tmp_path, self.SOURCE)
        g = (out / 'scripts' / 'game_state.gd').read_text()
        assert 'const PERSISTED := ["best"]' in g
        assert 'Q.load_persisted(self, PERSISTED)' in g and 'Q.save_persisted(self, PERSISTED)' in g
        play = (out / 'scripts' / 'scene_play.gd').read_text()
        assert 'func _q_enter() -> void:\n\tif (G.score > G.best):\n\t\tG.best = G.score\n' in play

    def test_saved_is_for_the_game_state(self, tmp_path):
        e = refuse(tmp_path, game('  <qg:scene name="main"><q:set name="x" value="0" type="number" saved="true" /></qg:scene>\n'))
        assert 'saved= is for the game state' in e.message

    def test_a_fire_prefab_nobody_declared(self, tmp_path):
        e = refuse(tmp_path, HEAD + '  <qg:prefab name="D" sheet="c" hitbox="1x1" ai="fly" fire-prefab="Pew" fire-every="9" />\n'
                   '  <qg:scene name="main" />\n' + TAIL)
        assert "no qg:prefab named 'Pew'" in e.message

    def test_a_scene_on_death_needs_a_tag(self, tmp_path):
        e = refuse(tmp_path, game('  <qg:scene name="main"><qg:on-death /></qg:scene>\n'))
        assert '<qg:on-death> in a scene needs of=' in e.message

    def test_a_scene_on_death_of_an_unknown_tag(self, tmp_path):
        e = refuse(tmp_path, game('  <qg:scene name="main"><qg:on-death of="ghost" /></qg:scene>\n'))
        assert '<qg:on-death of="ghost">: no prefab has that tag' in e.message

    def test_a_spawner_x_is_a_number_or_random(self, tmp_path):
        e = refuse(tmp_path, game('  <qg:scene name="main"><qg:spawner prefab="Coin" x="left" /></qg:scene>\n'))
        assert '<qg:spawner x="left">: a number, or random' in e.message


class TestWhatItRefuses:
    def test_an_unknown_tag_with_its_line(self, tmp_path):
        e = refuse(tmp_path, game('  <qg:scene name="main">\n    <qg:sprite id="x" />\n  </qg:scene>\n'))
        assert '<qg:sprite> is not a game tag' in e.message
        assert e.line == 6

    def test_an_unknown_attribute_lists_the_known_ones(self, tmp_path):
        e = refuse(tmp_path, game('  <qg:scene name="main" colour="#fff" />\n'))
        assert "<qg:scene> has no attribute 'colour'" in e.message
        assert 'background' in e.message

    def test_a_missing_required_attribute(self, tmp_path):
        e = refuse(tmp_path, game('  <qg:scene name="main"><qg:character id="p" /></qg:scene>\n'))
        assert '<qg:character> needs controller=' in e.message

    def test_a_wrong_enum_value(self, tmp_path):
        e = refuse(tmp_path, game(
            '  <qg:scene name="main"><qg:character id="p" controller="flying" sheet="c" x="0" y="0" hitbox="1x1" /></qg:scene>\n'))
        assert 'controller="flying": must be one of platformer' in e.message

    def test_text_where_statements_go_is_refused(self, tmp_path):
        e = refuse(tmp_path, game('''  <qg:scene name="main">
    <q:set name="coins" value="0" type="number" />
    <qg:character id="p" controller="platformer" sheet="c" x="0" y="0" hitbox="1x1">
      <qg:on-collision with="coin">
        coins += 1;
      </qg:on-collision>
    </qg:character>
  </qg:scene>
'''))
        assert "holds text ('coins += 1;')" in e.message
        assert 'not in script' in e.message
        assert e.line == 8

    def test_an_undeclared_name_in_an_expression(self, tmp_path):
        e = refuse(tmp_path, game('''  <qg:scene name="main">
    <q:set name="coins" value="0" type="number" />
    <qg:character id="p" controller="platformer" sheet="c" x="0" y="0" hitbox="1x1">
      <qg:on-collision with="coin"><q:set name="coins" value="{coins + bonus}" /></qg:on-collision>
    </qg:character>
  </qg:scene>
'''))
        assert "'bonus' is not declared" in e.message
        assert e.line == 8

    def test_assigning_an_undeclared_variable(self, tmp_path):
        e = refuse(tmp_path, game('''  <qg:scene name="main">
    <qg:character id="p" controller="platformer" sheet="c" x="0" y="0" hitbox="1x1">
      <qg:on-collision with="coin"><q:set name="score" value="1" /></qg:on-collision>
    </qg:character>
  </qg:scene>
'''))
        assert "'score' is not declared" in e.message

    def test_a_collision_with_a_tag_no_prefab_has(self, tmp_path):
        e = refuse(tmp_path, game('''  <qg:scene name="main">
    <qg:character id="p" controller="platformer" sheet="c" x="0" y="0" hitbox="1x1">
      <qg:on-collision with="gem" />
    </qg:character>
  </qg:scene>
'''))
        assert 'no prefab has that tag (tags: coin)' in e.message

    def test_an_asset_that_does_not_exist(self, tmp_path):
        e = refuse(tmp_path, '<q:application id="t" type="game">\n'
                             '  <qg:tileset name="k" src="art/none.png" tile="18" />\n'
                             '  <qg:scene name="main" />\n</q:application>\n')
        assert 'file not found: art/none.png' in e.message
        assert e.line == 2

    def test_a_ragged_tilemap(self, tmp_path):
        e = refuse(tmp_path, game('  <qg:scene name="main"><qg:tilemap tileset="k">\n1,2\n1\n</qg:tilemap></qg:scene>\n'))
        assert 'row 2 has 1 tiles, row 1 has 2' in e.message

    def test_a_game_without_a_scene(self, tmp_path):
        e = refuse(tmp_path, HEAD + TAIL)
        assert 'at least one <qg:scene>' in e.message

    def test_the_error_names_the_file(self, tmp_path):
        e = refuse(tmp_path, game('  <qg:scene name="main"><qg:bogus /></qg:scene>\n'))
        assert str(e).startswith(str(tmp_path / 'game.q') + ':5: ')


class TestExpressions:
    scope = Scope(['coins', 'name', 'items'], functions=['bonus'])

    @pytest.mark.parametrize('source,gd', [
        ('coins + 1', '(coins + 1)'),
        ('{coins * 2 - 1}', '((coins * 2) - 1)'),
        ('coins / 2', 'Q.div(coins, 2)'),
        ('coins // 2', 'Q.floordiv(coins, 2)'),
        ('coins % 3', 'Q.mod(coins, 3)'),
        ('coins ** 2', 'pow(coins, 2)'),
        ('-coins', '(-coins)'),
        ('coins > 1 && coins < 5', '((coins > 1) and (coins < 5))'),
        ('!(coins == 0) || true', '((not (coins == 0)) or true)'),
        ('1 < coins <= 3', '((1 < coins) and (coins <= 3))'),
        ('"a" in name', '("a" in name)'),
        ('coins if name else 0', '(coins if name else 0)'),
        ('items[0].x', 'items[0].x'),
        ('len(name)', 'Q.len(name)'),
        ('max(coins, 10)', 'max(coins, 10)'),
        ('round(coins)', 'roundi(coins)'),
        ('bonus(coins)', 'bonus(coins)'),
        ("name + 'x'", '(name + "x")'),
        ('[1, 2]', '[1, 2]'),
        ('{{"a": coins}}', '{"a": coins}'),   # the outer braces mark the expression
        ('null', 'null'),
    ])
    def test_compiles_like_the_core_evaluator_reads(self, source, gd):
        assert compile_expression(source, self.scope) == gd

    @pytest.mark.parametrize('source,message', [
        ('coins + ', 'cannot read the expression'),
        ('score', "'score' is not declared"),
        ('items[1:2]', 'slices are not part'),
        ('name.upper()', 'method calls are not part'),
        ('lambda: 1', 'Lambda is not part of the language'),
        ('nope(1)', 'nope() is not a built-in nor a q:function'),
        ('len(1, 2)', 'len() takes 1 argument(s), 2 given'),
    ])
    def test_refuses(self, source, message):
        with pytest.raises(GameCompileError, match=re.escape(message)):
            compile_expression(source, self.scope)
