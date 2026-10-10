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
        assert 'var title: Variant = "Hop"\n' in script   # no type= written: any value may follow
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
        assert data['sounds'] == {'hurt': {'src': 'assets/kenney/audio/hurt.ogg', 'loop': False}}
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
            'small': {'hitbox': [18, 22], 'frame': 0, 'speed': None, 'fire_every': None, 'fire_prefab': None, 'range': None, 'animations': {}},
            'big': {'hitbox': [18, 30], 'frame': 3, 'speed': None, 'fire_every': None, 'fire_prefab': None, 'range': None,
                    'animations': {'walk': {'frames': [4, 5], 'fps': 8}}},
        }
        assert character['on_collision'][0]['side'] == 'bottom'
        assert data['scenes']['main']['nodes'][2]['items'] == [{'kind': 'text', 'bind': 'message', 'label': '', 'size': None}]

    def test_the_actions(self, tmp_path):
        out = build(tmp_path, self.SOURCE)
        script = (out / 'scripts' / 'scene_main.gd').read_text()
        assert '\tQ.swap(self, other, "Used")\n\tQ.spawn(self, "Shroom", other, 0.0, -18.0)\n' in script
        assert '\tQ.destroy(other)\n\tQ.become(me, "big")\n' in script
        assert '\tQ.checkpoint(me, other)\n\tif (me.state == "big"):\n\t\tmessage = "big!"\n' in script

    def test_a_godot_property_name_is_refused(self, tmp_path):
        e = refuse(tmp_path, game('  <qg:scene name="main"><q:set name="position" value="1" type="number" /></qg:scene>\n'))
        assert "'position' is a property of every Godot node" in e.message

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
        assert 'var lives: float = 3.0\nvar cleared: Array = []\nvar map_at: Variant = "one"\n' in state
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
        assert '<qg:on-hit with="ghost">: no prefab or zone has that tag' in e.message


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
        assert (shot['ai'], shot['heading'], shot['lifetime'], shot['health']) == ('fly', [0.0, -1.0], 80, 1)
        assert shot['on_collision'] == [{'with': 'enemy', 'cooldown': 0, 'handler': '_Shot_on_collision_0'}]
        assert (drone['health'], drone['fire_prefab'], drone['fire_every']) == (3, 'Shot', 90)
        assert drone['on_damage'] == '_Drone_on_damage' and drone['on_death'] == '_Drone_on_death'
        assert drone['initial_state'] == 'calm'
        assert drone['states']['angry'] == {'hitbox': None, 'frame': 2, 'speed': 70, 'fire_every': 25, 'fire_prefab': None, 'range': None,
                                            'animations': {}}
        play = data['scenes']['play']
        ship = play['nodes'][0]
        assert (ship['controller'], ship['fire_action'], ship['fire_prefab'], ship['fire_every']) == \
            ('ship', 'jump', 'Shot', 10)
        assert play['nodes'][1] == {'kind': 'spawner', 'prefabs': ['Drone'], 'along': None, 'heading': None,
                                    'spread': 0.0, 'from': 60, 'every': 40, 'count': 8,
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


class TestInputsTimersAndPlatforms:
    SOURCE = HEAD + '''  <qg:input action="jump" keys="Space, Enter" />
  <qg:prefab name="Ledge" tag="ledge" sheet="k" hitbox="18x6" solid="true" one-way="true" />
  <qg:prefab name="Lift" tag="lift" sheet="k" hitbox="18x8" solid="true" ai="shuttle" dy="-80" period="120" />
  <qg:scene name="main">
    <q:set name="time" value="9" type="number" />
    <qg:timer every="60" count="9"><q:set name="time" value="{time - 1}" /></qg:timer>
    <qg:timer after="30"><q:set name="time" value="{time + 100}" /></qg:timer>
  </qg:scene>
''' + TAIL

    def test_the_json(self, tmp_path):
        out = build(tmp_path, self.SOURCE)
        data = json.loads((out / 'game.json').read_text())
        assert data['inputs']['jump'] == ['Space', 'Enter']
        assert data['inputs']['left'][:2] == ['Left', 'A']   # the others keep their defaults (keys, then the joypad)
        assert data['prefabs']['Ledge']['one_way'] is True
        lift = data['prefabs']['Lift']
        assert (lift['ai'], lift['solid'], lift['dx'], lift['dy'], lift['period']) == ('shuttle', True, 0, -80, 120)
        timers = [n for n in data['scenes']['main']['nodes'] if n['kind'] == 'timer']
        assert timers == [{'kind': 'timer', 'after': None, 'every': 60, 'from': 0, 'count': 9, 'handler': '_on_timer_0'},
                          {'kind': 'timer', 'after': 30, 'every': None, 'from': 0, 'count': 0, 'handler': '_on_timer_1'}]
        script = (out / 'scripts' / 'scene_main.gd').read_text()
        assert 'func _on_timer_0(me, other) -> void:\n\ttime = (time - 1)\n' in script

    def test_a_timer_takes_after_or_every(self, tmp_path):
        e = refuse(tmp_path, game('  <qg:scene name="main"><qg:timer after="1" every="2" /></qg:scene>\n'))
        assert '<qg:timer> takes after= or every=, one of them' in e.message
        e = refuse(tmp_path, game('  <qg:scene name="main"><qg:timer /></qg:scene>\n'))
        assert 'one of them' in e.message

    def test_a_shuttle_is_a_solid(self, tmp_path):
        e = refuse(tmp_path, HEAD + '  <qg:prefab name="L" sheet="k" hitbox="1x1" ai="shuttle" />\n  <qg:scene name="main" />\n' + TAIL)
        assert 'ai="shuttle" is a solid: add solid="true"' in e.message

    def test_one_way_is_for_a_solid(self, tmp_path):
        e = refuse(tmp_path, HEAD + '  <qg:prefab name="L" sheet="k" hitbox="1x1" one-way="true" />\n  <qg:scene name="main" />\n' + TAIL)
        assert 'one-way="true" is for a solid prefab' in e.message

    def test_an_input_needs_a_key(self, tmp_path):
        e = refuse(tmp_path, HEAD + '  <qg:input action="jump" keys=" , " />\n  <qg:scene name="main" />\n' + TAIL)
        assert '<qg:input> needs at least one key' in e.message


class TestWhatItRefuses:
    def test_an_unknown_tag_with_its_line(self, tmp_path):
        e = refuse(tmp_path, game('  <qg:scene name="main">\n    <qg:ghost id="x" />\n  </qg:scene>\n'))
        assert '<qg:ghost> is not a game tag' in e.message
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
        assert "'score' is set and never read" in e.message

    def test_a_collision_with_a_tag_no_prefab_has(self, tmp_path):
        e = refuse(tmp_path, game('''  <qg:scene name="main">
    <qg:character id="p" controller="platformer" sheet="c" x="0" y="0" hitbox="1x1">
      <qg:on-collision with="gem" />
    </qg:character>
  </qg:scene>
'''))
        assert 'no prefab or zone has that tag (tags: coin)' in e.message

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
        ('items[1:3]', 'Q.slice(items, 1, 3)'),
        ('name[:2]', 'Q.slice(name, null, 2)'),
        ('items[-2:]', 'Q.slice(items, (-2), null)'),
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
        ('name.upper()', 'method calls are not part'),
        ('lambda: 1', 'Lambda is not part of the language'),
        ('items[::2]', 'a slice with a step is not part'),
        ('nope(1)', 'nope() is not a built-in nor a q:function'),
        ('len(1, 2)', 'len() takes 1 argument(s), 2 given'),
    ])
    def test_refuses(self, source, message):
        with pytest.raises(GameCompileError, match=re.escape(message)):
            compile_expression(source, self.scope)


class TestGdAttributes:
    """`gd:name="value"`: a property of the Godot node the tag becomes, checked
    against Godot's own class reference (quantum/runtime/godot/gd.py)."""

    def test_a_property_is_converted_and_carried_in_game_json(self, tmp_path):
        out = build(tmp_path, game('''  <qg:scene name="main" gd:y_sort_enabled="true">
    <qg:character id="player" controller="platformer" sheet="c" x="10" y="10" hitbox="18x22" gd:floor_max_angle="0.5" />
    <qg:instance prefab="Coin" x="30" y="10" gd:modulate="#FF000080" gd:z_index="3" />
    <qg:camera follow="player" bounds="none" gd:zoom="2,2" gd:position_smoothing_enabled="yes" />
    <qg:hud gd:layer="7"><qg:counter bind="x" label="X" gd:uppercase="true" /></qg:hud>
    <q:set name="x" value="0" type="number" />
  </qg:scene>
'''))
        scene = json.loads((out / 'game.json').read_text())['scenes']['main']
        assert scene['gd'] == {'y_sort_enabled': {'type': 'bool', 'value': True}}
        gd = {n['kind']: n['gd'] for n in scene['nodes']}
        assert gd['character'] == {'floor_max_angle': {'type': 'float', 'value': 0.5}}
        assert gd['instance'] == {'modulate': {'type': 'Color', 'value': '#ff000080'},
                                  'z_index': {'type': 'int', 'value': 3}}
        assert gd['camera'] == {'zoom': {'type': 'Vector2', 'value': [2.0, 2.0]},
                                'position_smoothing_enabled': {'type': 'bool', 'value': True}}
        hud = [n for n in scene['nodes'] if n['kind'] == 'hud'][0]
        assert hud['gd'] == {'layer': {'type': 'int', 'value': 7}}
        assert hud['items'][0]['gd'] == {'uppercase': {'type': 'bool', 'value': True}}

    def test_a_prefab_is_checked_against_what_it_becomes(self, tmp_path):
        out = build(tmp_path, HEAD + '''  <qg:prefab name="Crate" tag="crate" sheet="k" frame="9" hitbox="18x18" solid="true" gd:constant_linear_velocity="10,0" />
  <qg:sound name="hurt" src="assets/kenney/audio/hurt.ogg" gd:volume_db="-6" />
  <qg:scene name="main"><qg:instance prefab="Crate" x="30" y="10" /></qg:scene>
''' + TAIL)
        data = json.loads((out / 'game.json').read_text())
        assert data['prefabs']['Crate']['gd'] == {'constant_linear_velocity': {'type': 'Vector2', 'value': [10.0, 0.0]}}
        assert data['sounds']['hurt']['gd'] == {'volume_db': {'type': 'float', 'value': -6.0}}
        # an item is an Area2D: a StaticBody2D property is not its
        err = refuse(tmp_path, HEAD + '''  <qg:prefab name="Gem" tag="gem" sheet="k" frame="9" hitbox="18x18" gd:constant_linear_velocity="10,0" />
  <qg:scene name="main"><qg:instance prefab="Gem" x="30" y="10" /></qg:scene>
''' + TAIL)
        assert 'gd:constant_linear_velocity is not a property of Area2D' in str(err)

    def test_an_unknown_property_names_the_class_and_what_it_has(self, tmp_path):
        err = refuse(tmp_path, game('''  <qg:scene name="main">
    <qg:character id="player" controller="platformer" sheet="c" x="10" y="10" hitbox="18x22" />
    <qg:camera follow="player" bounds="none" gd:zoom_level="2" />
  </qg:scene>
'''))
        message = str(err)
        assert '<qg:camera>: gd:zoom_level is not a property of Camera2D (it has:' in message
        assert ', zoom)' in message and 'limit_left' in message and 'modulate' in message
        assert message.startswith(str(tmp_path / 'game.q') + ':7:')

    @pytest.mark.parametrize('attr,message', [
        ('gd:zoom="2"', 'gd:zoom="2": a Vector2 (e.g. 2,2)'),
        ('gd:zoom="a,b"', 'a Vector2'),
        ('gd:limit_left="1.5"', 'gd:limit_left="1.5": a int (e.g. 2)'),
        ('gd:position_smoothing_enabled="maybe"', 'a bool (e.g. true)'),
        ('gd:modulate="red"', 'gd:modulate="red": a Color (e.g. #rrggbb)'),
    ])
    def test_a_value_of_the_wrong_type(self, tmp_path, attr, message):
        err = refuse(tmp_path, game(f'''  <qg:scene name="main">
    <qg:character id="player" controller="platformer" sheet="c" x="10" y="10" hitbox="18x22" />
    <qg:camera follow="player" bounds="none" {attr} />
  </qg:scene>
'''))
        assert message in str(err)

    def test_a_tag_that_becomes_no_node_takes_none(self, tmp_path):
        err = refuse(tmp_path, '''<q:application id="t" type="game">
  <qg:tileset name="k" src="assets/kenney/tilemap_packed.png" tile="18" gd:modulate="#ffffff" />
  <qg:scene name="main" />
</q:application>
''')
        assert 'becomes no Godot node: gd: attributes go on what is placed' in str(err)

    def test_the_table_comes_from_the_pinned_godot(self):
        from quantum.runtime.godot import gd
        from quantum.runtime.godot_bin import GODOT_VERSION
        assert gd.table()['godot'] == GODOT_VERSION
        assert gd.properties_of('Camera2D')['zoom'] == 'Vector2'
        assert gd.properties_of('Camera2D')['modulate'] == 'Color'      # inherited from CanvasItem
        assert 'name' not in gd.properties_of('Node')                   # the runtime's, never a gd:


class TestWhatPongAsked:
    """The six things Godot's Pong demo made the language say (projects/pong/README.md)."""

    def test_a_second_player_its_keys_and_a_vertical_ship(self, tmp_path):
        out = build(tmp_path, HEAD + '''  <qg:input player="2" action="up" keys="Up" />
  <qg:input player="2" action="down" keys="Down" />
  <qg:scene name="main">
    <qg:character id="left" controller="ship" sheet="c" x="10" y="10" hitbox="8x32" axis="vertical" />
    <qg:character id="right" controller="ship" player="2" sheet="c" x="100" y="10" hitbox="8x32" axis="vertical" />
  </qg:scene>
''' + TAIL)
        data = json.loads((out / 'game.json').read_text())
        assert data['inputs']['p2_up'] == ['Up'] and data['inputs']['p2_down'] == ['Down']
        assert data['inputs']['up'][:2] == ['Up', 'W']      # player 1 keeps the defaults
        left, right = data['scenes']['main']['nodes']
        assert (left['player'], left['axis']) == (1, 'vertical')
        assert (right['player'], right['axis']) == (2, 'vertical')

    def test_a_player_without_keys(self, tmp_path):
        err = refuse(tmp_path, game('''  <qg:scene name="main">
    <qg:character id="right" controller="ship" player="2" sheet="c" x="100" y="10" hitbox="8x32" />
  </qg:scene>
'''))
        assert '<qg:character player="2">: no keys for that player' in str(err)

    def test_axis_is_for_the_ship(self, tmp_path):
        err = refuse(tmp_path, game('''  <qg:scene name="main">
    <qg:character id="p" controller="topdown" axis="vertical" sheet="c" x="100" y="10" hitbox="8x32" />
  </qg:scene>
'''))
        assert 'axis= is for controller="ship"' in str(err)

    def test_frames_that_are_not_square(self, tmp_path):
        out = build(tmp_path, '''<q:application id="t" type="game">
  <qg:tileset name="k" src="assets/kenney/tilemap_packed.png" tile="18" />
  <qg:spritesheet name="tall" src="assets/kenney/tilemap-characters_packed.png" tile="8x32" />
  <qg:scene name="main"><qg:sprite sheet="tall" frame="2" x="20" y="30" /></qg:scene>
</q:application>
''')
        data = json.loads((out / 'game.json').read_text())
        assert data['sheets']['k']['tile'] == [18, 18] and data['sheets']['tall']['tile'] == [8, 32]
        assert data['scenes']['main']['nodes'] == [{'kind': 'sprite', 'sheet': 'tall', 'frame': 2, 'x': 20.0, 'y': 30.0}]

    def test_a_heading_as_a_vector_and_an_acceleration(self, tmp_path):
        out = build(tmp_path, HEAD + '''  <qg:prefab name="Ball" tag="ball" sheet="k" frame="151" hitbox="8x8" ai="fly" heading="3,-4" accel="2" />
  <qg:scene name="main"><qg:instance prefab="Ball" x="30" y="10" /></qg:scene>
''' + TAIL)
        ball = json.loads((out / 'game.json').read_text())['prefabs']['Ball']
        assert ball['heading'] == [0.6, -0.8] and ball['accel'] == 2.0
        err = refuse(tmp_path, HEAD + '''  <qg:prefab name="Ball" tag="ball" sheet="k" frame="151" hitbox="8x8" ai="fly" heading="north" />
  <qg:scene name="main" />
''' + TAIL)
        assert 'heading="north": up, down, left, right, or x,y' in str(err)

    def test_zones_deflect_and_respawn(self, tmp_path):
        out = build(tmp_path, HEAD + '''  <qg:prefab name="Ball" tag="ball" sheet="k" frame="151" hitbox="8x8" ai="fly" heading="left" speed="100">
    <qg:on-collision with="edge"><qg:deflect target="me" axis="y" /></qg:on-collision>
    <qg:on-collision with="wall"><qg:respawn target="me" /></qg:on-collision>
  </qg:prefab>
  <qg:scene name="main">
    <qg:character id="left" controller="ship" sheet="c" x="10" y="10" hitbox="8x32">
      <qg:on-collision with="ball"><qg:deflect target="other" dx="1" dy="{random(-1, 1)}" /></qg:on-collision>
    </qg:character>
    <qg:instance prefab="Ball" name="ball" x="30" y="10" />
    <qg:zone name="ceiling" tag="edge" x="0" y="-20" width="640" height="20" />
    <qg:zone name="left-wall" tag="wall" x="-20" y="0" width="20" height="400" />
  </qg:scene>
''' + TAIL)
        prefabs = (out / 'scripts' / 'prefabs.gd').read_text()
        assert '\tQ.deflect_axis(me, "y")\n' in prefabs and '\tQ.respawn(me)\n' in prefabs
        scene = (out / 'scripts' / 'scene_main.gd').read_text()
        assert '\tQ.deflect_to(other, 1, Q.random(self, (-1), 1))\n' in scene
        nodes = json.loads((out / 'game.json').read_text())['scenes']['main']['nodes']
        assert nodes[2] == {'kind': 'zone', 'name': 'ceiling', 'tag': 'edge', 'x': 0.0, 'y': -20.0,
                            'width': 640.0, 'height': 20.0}

    @pytest.mark.parametrize('attrs,message', [
        ('target="me" axis="y" dx="1" dy="0"', 'axis=, or dx= and dy=, not both'),
        ('target="me" dx="1"', 'needs axis="x|y", or dx= and dy='),
    ])
    def test_a_deflect_that_says_too_much_or_too_little(self, tmp_path, attrs, message):
        err = refuse(tmp_path, HEAD + f'''  <qg:prefab name="Ball" tag="ball" sheet="k" frame="151" hitbox="8x8" ai="fly">
    <qg:on-collision with="coin"><qg:deflect {attrs} /></qg:on-collision>
  </qg:prefab>
  <qg:scene name="main" />
''' + TAIL)
        assert message in str(err)


class TestWhatCreepsAsked:
    """What Godot's "Dodge the Creeps" made the language say (projects/creeps/README.md)."""

    def test_joypad_names_on_the_players_pad(self, tmp_path):
        out = build(tmp_path, HEAD + '''  <qg:input action="jump" keys="Space, JoyA, JoyStart" />
  <qg:input player="2" action="up" keys="Up, JoyUp, JoyLeftStickUp" />
  <qg:scene name="main" />
''' + TAIL)
        inputs = json.loads((out / 'game.json').read_text())['inputs']
        assert inputs['jump'] == ['Space', {'joy_button': 0, 'device': 0}, {'joy_button': 6, 'device': 0}]
        assert inputs['p2_up'] == ['Up', {'joy_button': 11, 'device': 1}, {'joy_axis': 1, 'value': -1.0, 'device': 1}]
        assert inputs['left'] == ['Left', 'A', {'joy_button': 13, 'device': 0}, {'joy_axis': 0, 'value': -1.0, 'device': 0}]
        err = refuse(tmp_path, HEAD + '  <qg:input action="jump" keys="JoyZ" />\n  <qg:scene name="main" />\n' + TAIL)
        assert 'keys="JoyZ": not a joypad name' in str(err)

    def test_a_spawner_along_the_edges_with_several_prefabs(self, tmp_path):
        out = build(tmp_path, HEAD + '''  <qg:prefab name="A" tag="creep" sheet="k" frame="1" hitbox="8x8" ai="fly" speed="150..250" rotate="true" />
  <qg:prefab name="B" tag="creep" sheet="k" frame="2" hitbox="8x8" ai="fly" />
  <qg:scene name="main">
    <qg:spawner prefab="A, B" along="edges" heading="inward" spread="45" every="30" count="0" />
  </qg:scene>
''' + TAIL)
        data = json.loads((out / 'game.json').read_text())
        assert data['prefabs']['A']['speed'] == [150.0, 250.0] and data['prefabs']['A']['rotate'] is True
        assert data['prefabs']['B']['speed'] == 30.0
        spawner = data['scenes']['main']['nodes'][0]
        assert (spawner['prefabs'], spawner['along'], spawner['heading'], spawner['spread'], spawner['count']) == (
            ['A', 'B'], 'edges', 'inward', 45.0, 0)
        err = refuse(tmp_path, HEAD + '''  <qg:prefab name="W" tag="w" sheet="k" frame="1" hitbox="8x8" ai="patrol" />
  <qg:scene name="main"><qg:spawner prefab="W" along="edges" heading="inward" /></qg:scene>
''' + TAIL)
        assert 'every prefab must be ai="fly"' in str(err)
        err = refuse(tmp_path, HEAD + '''  <qg:prefab name="W" tag="w" sheet="k" frame="1" hitbox="8x8" ai="fly" speed="fast" />
  <qg:scene name="main" />
''' + TAIL)
        assert 'speed="fast": a number, or a range like 150..250' in str(err)

    def test_sounds_that_loop_and_stop_as_a_scene_is_entered(self, tmp_path):
        out = build(tmp_path, HEAD + '''  <qg:sound name="music" src="assets/kenney/audio/hurt.ogg" loop="true" />
  <qg:scene name="main">
    <qg:play sound="music" />
    <q:set name="x" value="0" type="number" />
  </qg:scene>
  <qg:scene name="end">
    <qg:stop sound="music" />
  </qg:scene>
''' + TAIL)
        data = json.loads((out / 'game.json').read_text())
        assert data['sounds']['music']['loop'] is True
        assert '\tQ.play("music")\n' in (out / 'scripts' / 'scene_main.gd').read_text()
        assert '\tQ.stop("music")\n' in (out / 'scripts' / 'scene_end.gd').read_text()

    def test_the_hud_font_size_and_centre_and_a_timer_from(self, tmp_path):
        out = build(tmp_path, HEAD + '''  <qg:scene name="main">
    <q:set name="message" value="Hi" />
    <qg:hud position="center" font="assets/kenney/tilemap_packed.png" size="60">
      <qg:text bind="message" size="30" />
    </qg:hud>
    <qg:timer every="60" from="120"><q:set name="message" value="" /></qg:timer>
  </qg:scene>
''' + TAIL)
        nodes = json.loads((out / 'game.json').read_text())['scenes']['main']['nodes']
        assert nodes[0]['position'] == 'center' and nodes[0]['font'] == 'assets/kenney/tilemap_packed.png'
        assert nodes[0]['size'] == 60 and nodes[0]['items'][0]['size'] == 30
        assert nodes[1]['from'] == 120

    def test_the_games_state_set_as_a_scene_is_entered(self, tmp_path):
        out = build(tmp_path, '''<q:application id="t" type="game">
  <q:set name="score" value="0" type="number" />
  <qg:tileset name="k" src="assets/kenney/tilemap_packed.png" tile="18" />
  <qg:scene name="main"><q:set name="score" value="0" /></qg:scene>
</q:application>
''')
        assert 'func _q_enter() -> void:\n\tG.score = 0.0\n' in (out / 'scripts' / 'scene_main.gd').read_text()

    def test_a_state_named_like_a_node_member(self, tmp_path):
        err = refuse(tmp_path, game('  <qg:scene name="main"><q:set name="ready" value="false" type="boolean" /></qg:scene>\n'))
        assert "'ready' is a property of every Godot node" in str(err)


class TestMultiplayer:
    def test_the_declaration_and_every_players_actions(self, tmp_path):
        out = build(tmp_path, HEAD + '''  <qg:multiplayer players="3" delay="2" check-every="30" />
  <qg:scene name="main">
    <qg:character id="a" controller="ship" sheet="c" x="10" y="10" hitbox="8x8" />
    <qg:character id="b" controller="ship" player="2" sheet="c" x="20" y="10" hitbox="8x8" />
    <qg:character id="c" controller="ship" player="3" sheet="c" x="30" y="10" hitbox="8x8" />
  </qg:scene>
''' + TAIL)
        data = json.loads((out / 'game.json').read_text())
        assert data['multiplayer'] == {'players': 3, 'delay': 2, 'check_every': 30, 'transport': 'enet'}
        assert data['inputs']['p2_up'] == [] and data['inputs']['p3_jump'] == []   # pressed by the lockstep, not keys

    @pytest.mark.parametrize('source,message', [
        ('<qg:multiplayer players="1" />\n  <qg:scene name="main" />', 'players=>: 2 or more'),
        ('<qg:multiplayer players="2" delay="0" />\n  <qg:scene name="main" />', 'delay=>: 1 or more'),
        ('<qg:multiplayer players="2" />\n  <qg:multiplayer players="2" />\n  <qg:scene name="main" />',
         'one <qg:multiplayer> per game'),
        ('<qg:multiplayer players="2" />\n  <qg:scene name="main">\n'
         '    <qg:character id="c" controller="ship" player="3" sheet="c" x="30" y="10" hitbox="8x8" />\n  </qg:scene>',
         'player="3">: the game has 2 players'),
    ])
    def test_what_it_refuses(self, tmp_path, source, message):
        assert message in str(refuse(tmp_path, HEAD + '  ' + source + '\n' + TAIL))


class TestWhatTowersAsked:
    """What the tower defense made the language say (projects/towers/README.md)."""

    def test_named_actions_the_mouse_and_the_defaults(self, tmp_path):
        out = build(tmp_path, HEAD + '''  <qg:input action="buy" keys="1, MouseRight" />
  <qg:scene name="main">
    <q:set name="n" value="0" type="number" />
    <qg:on-input action="buy"><q:set name="n" value="{n + 1}" /></qg:on-input>
    <qg:on-input action="select"><q:set name="n" value="{n + 2}" /></qg:on-input>
  </qg:scene>
''' + TAIL)
        data = json.loads((out / 'game.json').read_text())
        assert data['inputs']['buy'] == ['1', {'mouse_button': 2}]
        assert data['inputs']['select'] == ['Enter', {'mouse_button': 1}, {'joy_button': 0, 'device': 0}]
        assert data['inputs']['click'] == [{'mouse_button': 1}]      # the mouse button alone: a menu's click
        assert data['actions'] == ['left', 'right', 'up', 'down', 'jump', 'select', 'cancel', 'click', 'buy']
        assert set(data['scenes']['main']['on_input']) == {'buy', 'select'}
        err = refuse(tmp_path, game('  <qg:scene name="main"><qg:on-input action="fire"><q:set name="x" value="1" /></qg:on-input></qg:scene>\n'))
        assert '<qg:on-input action="fire">: no such action' in str(err)

    def test_a_cursor_a_select_handler_and_a_spawn_at_the_cursor(self, tmp_path):
        out = build(tmp_path, HEAD + '''  <qg:prefab name="Tower" tag="tower" sheet="k" frame="1" hitbox="16x16" ai="turret" targets="coin" range="80" fire-every="30" attack="area" damage="2" />
  <qg:scene name="main">
    <q:set name="gold" value="100" type="number" />
    <qg:cursor player="1" grid="16" sheet="k" frame="2" />
    <qg:zone name="r" tag="road" x="0" y="0" width="50" height="50" />
    <qg:on-select>
      <q:if condition="{other == null and thing_at('road', cursor.x, cursor.y) == null and gold >= 10 and count('tower') < 5}">
        <q:set name="gold" value="{gold - 10}" />
        <qg:spawn prefab="Tower" at="cursor" />
      </q:if>
      <q:if condition="{other != null and other.tag == 'tower'}"><qg:become target="other" state="x" /></q:if>
    </qg:on-select>
  </qg:scene>
''' + TAIL)
        data = json.loads((out / 'game.json').read_text())
        tower = data['prefabs']['Tower']
        assert (tower['ai'], tower['targets'], tower['range'], tower['attack'], tower['damage']) == ('turret', 'coin', 80.0, 'area', 2)
        nodes = data['scenes']['main']['nodes']
        assert nodes[0] == {'kind': 'cursor', 'player': 1, 'step': 16.0, 'grid': 16, 'sheet': 'k', 'frame': 2}
        assert data['scenes']['main']['on_select'] == {'0': '_on_select_0'}
        script = (out / 'scripts' / 'scene_main.gd').read_text()
        assert 'func _on_select_0(cursor, other) -> void:' in script
        assert 'Q.thing_at(self, "road", cursor.x, cursor.y)' in script and 'Q.count(self, "tower")' in script
        assert 'Q.spawn_at(self, "Tower", Vector2(cursor.x + 0.0, cursor.y + 0.0))' in script
        err = refuse(tmp_path, game('  <qg:scene name="main"><q:set name="x" value="0" type="number" />'
                                    '<qg:on-select><q:set name="x" value="1" /></qg:on-select></qg:scene>\n'))
        assert '<qg:on-select> in a scene without a <qg:cursor>' in str(err)

    def test_a_path_and_what_follows_it(self, tmp_path):
        out = build(tmp_path, HEAD + '''  <qg:prefab name="Walker" tag="w" sheet="k" frame="1" hitbox="16x16" ai="path" speed="100" />
  <qg:scene name="main">
    <qg:path name="road" points="0,10; 100,10; 100,200" />
    <qg:timer every="30"><qg:spawn prefab="Walker" at="path" path="road" /></qg:timer>
  </qg:scene>
''' + TAIL)
        data = json.loads((out / 'game.json').read_text())
        assert data['scenes']['main']['nodes'][0] == {'kind': 'path', 'name': 'road', 'points': [[0.0, 10.0], [100.0, 10.0], [100.0, 200.0]]}
        assert 'Q.spawn_on_path(self, "Walker", "road")' in (out / 'scripts' / 'scene_main.gd').read_text()
        err = refuse(tmp_path, HEAD + '''  <qg:prefab name="Walker" tag="w" sheet="k" frame="1" hitbox="16x16" ai="path" />
  <qg:scene name="main"><qg:timer every="30"><qg:spawn prefab="Walker" at="path" path="lane" /></qg:timer></qg:scene>
''' + TAIL)
        assert '<qg:spawn path="lane">: no qg:path of that name' in str(err)
        err = refuse(tmp_path, game('  <qg:scene name="main"><qg:path name="p" points="1,2" /></qg:scene>\n'))
        assert 'points= needs at least two points' in str(err)


class TestWhatArenaAsked:
    """What the fighting game made the language say (projects/arena/README.md)."""

    FIGHTERS = '''  <qg:input action="punch" keys="J" />
  <qg:scene name="main">
    <q:set name="wins" value="0" type="number" />
    <qg:character id="p1" controller="fighter" sheet="c" x="100" y="100" hitbox="20x40" health="80" facing="left">
      <qg:animation name="idle" frames="0" />
      <qg:move name="jab" action="punch" frames="1, 2, 3" fps="15" active="1" reach="20x10" at="16,-4" damage="7" />
      <qg:on-ko><q:set name="wins" value="{wins + 1}" /></qg:on-ko>
    </qg:character>
    <qg:character id="p2" controller="fighter" player="2" sheet="c" x="200" y="100" hitbox="20x40" />
    <qg:timer after="10"><qg:respawn target="p2" /><q:set name="wins" value="{p1.health + p2.health}" /></qg:timer>
    <qg:hud><qg:bar bind="p1.health" max="80" width="60" /></qg:hud>
  </qg:scene>
'''

    def test_a_fighter_its_moves_and_its_ko(self, tmp_path):
        out = build(tmp_path, HEAD + '  <qg:input player="2" action="left" keys="Left" />\n' + self.FIGHTERS + TAIL)
        data = json.loads((out / 'game.json').read_text())
        p1, p2 = [n for n in data['scenes']['main']['nodes'] if n['kind'] == 'character']
        assert (p1['controller'], p1['health'], p1['facing'], p1['on_ko']) == ('fighter', 80, 'left', '_on_p1_ko')
        assert p1['moves'] == [{'name': 'jab', 'action': 'punch', 'frames': [1, 2, 3], 'fps': 15.0, 'active': 1,
                                'reach': [20, 10], 'at': [16.0, -4.0], 'damage': 7, 'stun': 12, 'push': 40.0}]
        assert p2['moves'] == [] and p2['health'] == 100
        hud = [n for n in data['scenes']['main']['nodes'] if n['kind'] == 'hud'][0]
        assert hud['items'] == [{'kind': 'bar', 'bind': 'p1.health', 'max': 80.0, 'width': 60, 'height': 10, 'color': '#e04040'}]
        script = (out / 'scripts' / 'scene_main.gd').read_text()
        assert '\tQ.respawn(get_node("p2"))\n' in script
        assert 'wins = (get_node("p1").health + get_node("p2").health)' in script

    @pytest.mark.parametrize('bad,message', [
        ('<qg:move name="m" action="fire" frames="1" reach="4x4" />', 'action="fire">: no such action'),
        ('<qg:move name="m" action="punch" frames="1, 2" active="2" reach="4x4" />', 'active="2">: a frame index'),
        ('<qg:move name="m" action="punch" frames="1" reach="4x4" at="3" />', 'at= is dx,dy'),
    ])
    def test_a_move_that_is_wrong(self, tmp_path, bad, message):
        src = self.FIGHTERS.replace('<qg:animation name="idle" frames="0" />', bad)
        assert message in str(refuse(tmp_path, HEAD + '  <qg:input player="2" action="left" keys="Left" />\n' + src + TAIL))

    def test_a_move_and_a_bar_where_they_do_not_belong(self, tmp_path):
        err = refuse(tmp_path, HEAD + '''  <qg:input action="punch" keys="J" />
  <qg:scene name="main">
    <qg:character id="p" controller="ship" sheet="c" x="1" y="1" hitbox="4x4">
      <qg:move name="m" action="punch" frames="1" reach="4x4" />
    </qg:character>
  </qg:scene>
''' + TAIL)
        assert '<qg:move> is for controller="fighter"' in str(err)
        err = refuse(tmp_path, game('  <qg:scene name="main"><qg:hud><qg:bar bind="p9.health" /></qg:hud></qg:scene>\n'))
        assert '<qg:bar bind="p9.health">: a fighter of this scene' in str(err)


class TestWhatChessAsked:
    """What chess made the language say (projects/chess/README.md)."""

    def test_a_functions_own_variables_and_an_element_of_an_array(self, tmp_path):
        out = build(tmp_path, game('''  <qg:scene name="main">
    <q:set name="board" type="array" value="{['a', 'b']}" />
    <q:function name="swap_first" params="i">
      <q:set name="held" value="{board[0]}" />
      <q:set name="flag" value="true" />
      <q:set name="n" value="3" />
      <q:set name="board" index="0" value="{board[i]}" />
      <q:set name="board" index="{i}" value="x" />
      <q:return value="{held if flag else n}" />
    </q:function>
  </qg:scene>
'''))
        script = (out / 'scripts' / 'scene_main.gd').read_text()
        assert ('func swap_first(i):\n\tvar held = null\n\tvar flag = null\n\tvar n = null\n'
                '\theld = board[0]\n\tflag = true\n\tn = 3.0\n\tboard[int(0)] = board[i]\n\tboard[int(i)] = "x"\n'
                '\treturn (held if flag else n)\n') in script
        assert 'var held' not in script.split('func swap_first')[0]      # the scene's state has no `held`

    def test_a_variable_set_and_never_read_is_a_misspelt_state(self, tmp_path):
        err = refuse(tmp_path, game('''  <qg:scene name="main">
    <q:set name="score" value="0" type="number" />
    <q:function name="f"><q:set name="scroe" value="{score + 1}" /></q:function>
  </qg:scene>
'''))
        assert "'scroe' is set and never read" in str(err)

    def test_an_element_of_what_is_not_an_array(self, tmp_path):
        err = refuse(tmp_path, game('''  <qg:scene name="main">
    <q:function name="f"><q:set name="nothing" index="0" value="x" /></q:function>
  </qg:scene>
'''))
        assert "'nothing' is not declared" in str(err)

    def test_put_and_destroy_on_a_name_holding_a_thing_and_a_named_instance(self, tmp_path):
        out = build(tmp_path, game('''  <qg:scene name="main">
    <qg:cursor player="1" grid="16" />
    <qg:instance prefab="Coin" name="mark" x="30" y="10" />
    <qg:on-select>
      <q:set name="hit" value="{thing_at('coin', cursor.x, cursor.y)}" />
      <q:if condition="{hit != null}"><qg:destroy target="hit" /></q:if>
      <qg:put target="mark" x="{cursor.x}" y="{cursor.y + 1}" />
    </qg:on-select>
  </qg:scene>
'''))
        script = (out / 'scripts' / 'scene_main.gd').read_text()
        assert '\t\tQ.destroy(hit)\n' in script and '\tQ.put(get_node("mark"), cursor.x, (cursor.y + 1))\n' in script


class TestMenus:
    def test_buttons_labels_conditions_and_a_field(self, tmp_path):
        out = build(tmp_path, game('''  <qg:scene name="main">
    <q:set name="n" value="0" type="number" />
    <q:set name="who" value="x" />
    <qg:menu player="1" position="top-left" size="12">
      <qg:button label="Go"><q:set name="n" value="{n + 1}" /></qg:button>
      <qg:button label="{'N ' + str(n)}" if="{n &gt; 0}"><qg:goto-scene name="main" /></qg:button>
      <qg:field label="Who" bind="who" max-length="8" />
    </qg:menu>
  </qg:scene>
'''))
        menu = json.loads((out / 'game.json').read_text())['scenes']['main']['nodes'][0]
        assert (menu['kind'], menu['player'], menu['position'], menu['size']) == ('menu', 1, 'top-left', 12)
        go, n, who = menu['items']
        assert go == {'kind': 'button', 'handler': '_on_menu_1_button_0', 'label': 'Go'}
        assert n['label_method'] == '_q_menu_1_label_1' and n['if_method'] == '_q_menu_1_if_1'
        assert who == {'kind': 'field', 'bind': 'who', 'label': 'Who', 'max_length': 8, 'game': False}
        script = (out / 'scripts' / 'scene_main.gd').read_text()
        assert 'func _on_menu_1_button_0(me, other) -> void:\n\tn = (n + 1)\n' in script
        assert 'func _q_menu_1_label_1():\n\treturn Q.to_str(("N " + Q.to_str(n)))\n' in script
        assert 'func _q_menu_1_if_1():\n\treturn (n > 0)\n' in script

    @pytest.mark.parametrize('body,message', [
        ('<qg:menu />', 'needs at least one qg:button'),
        ('<qg:menu><qg:field bind="nope" /></qg:menu>', '<qg:field bind="nope">: no q:set of that name'),
        ('<q:set name="k" value="0" type="number" /><qg:menu><qg:field bind="k" /></qg:menu>', "a field holds text; 'k' is a number"),
    ])
    def test_what_a_menu_refuses(self, tmp_path, body, message):
        assert message in str(refuse(tmp_path, game(f'  <qg:scene name="main">{body}</qg:scene>\n')))


class TestLobby:
    MP = '  <qg:multiplayer players="2" start="play" transport="websocket" />\n'

    def test_host_join_leave_and_the_network_in_expressions(self, tmp_path):
        out = build(tmp_path, HEAD + self.MP + '''  <qg:scene name="title">
    <q:set name="where" value="127.0.0.1:9000" />
    <qg:menu>
      <qg:button label="Host"><qg:host port="9000" /></qg:button>
      <qg:button label="Join" if="{net_status() == 'offline'}"><qg:join address="{where}" /></qg:button>
      <qg:button label="Leave"><qg:leave /></qg:button>
    </qg:menu>
    <qg:hud><qg:text value="{net_status() + ' ' + str(net_players()) + ' ' + str(net_player())}" /></qg:hud>
  </qg:scene>
  <qg:scene name="play" />
''' + TAIL)
        data = json.loads((out / 'game.json').read_text())
        assert data['multiplayer'] == {'players': 2, 'delay': 3, 'check_every': 60, 'transport': 'websocket', 'start': 'play'}
        script = (out / 'scripts' / 'scene_title.gd').read_text()
        assert '\tQ.net_host(9000)\n' in script and '\tQ.net_join(where)\n' in script and '\tQ.net_leave()\n' in script
        assert 'return (Q.net_status() == "offline")' in script
        assert 'Q.to_str(Q.net_players())' in script and 'Q.to_str(Q.net_player())' in script
        hud = [n for n in data['scenes']['title']['nodes'] if n['kind'] == 'hud'][0]
        assert hud['items'][0]['value_method'] == '_q_text_1'

    def test_a_lobby_is_a_menu_a_field_and_a_status_line(self, tmp_path):
        out = build(tmp_path, HEAD + self.MP + '''  <qg:scene name="title"><qg:lobby local="play" port="9000" address="10.0.0.2:9000" /></qg:scene>
  <qg:scene name="play" />
''' + TAIL)
        title = json.loads((out / 'game.json').read_text())['scenes']['title']
        menu, hud = title['nodes']
        assert [i.get('label') for i in menu['items']] == ['Play here', 'Host a game', 'Address', 'Join', 'Cancel']
        assert menu['items'][2] == {'kind': 'field', 'bind': 'lobby_address', 'label': 'Address', 'max_length': 64, 'game': False}
        assert hud['position'] == 'bottom-center' and 'value_method' in hud['items'][0]
        script = (out / 'scripts' / 'scene_title.gd').read_text()
        assert 'var lobby_address: Variant = "10.0.0.2:9000"' in script
        assert '\tQ.net_host(9000)\n' in script and '\tQ.net_join(lobby_address)\n' in script
        assert 'Q.goto_scene(self, "play")' in script

    @pytest.mark.parametrize('source,message', [
        ('<qg:scene name="t"><qg:menu><qg:button label="H"><qg:host /></qg:button></qg:menu></qg:scene>',
         'qg:host, qg:join and qg:leave need a <qg:multiplayer>'),
        ('<qg:scene name="t"><qg:lobby /></qg:scene>', '<qg:lobby> needs a <qg:multiplayer>'),
        ('<qg:multiplayer players="2" start="nowhere" /><qg:scene name="t" />', 'start="nowhere">: no scene of that name'),
        ('<qg:scene name="t"><qg:hud><qg:text /></qg:hud></qg:scene>', '<qg:text> takes bind= or value=, one of them'),
    ])
    def test_what_it_refuses(self, tmp_path, source, message):
        assert message in str(refuse(tmp_path, HEAD + '  ' + source + '\n' + TAIL))


class TestRollback:
    def test_rollback_on_a_scene_of_fighters(self, tmp_path):
        out = build(tmp_path, HEAD + '''  <qg:input action="punch" keys="J" />
  <qg:multiplayer players="2" delay="1" rollback="6" start="fight" />
  <qg:scene name="title"><qg:lobby local="fight" /></qg:scene>
  <qg:scene name="fight">
    <qg:character id="a" controller="fighter" sheet="c" x="10" y="10" hitbox="8x8" />
    <qg:character id="b" controller="fighter" player="2" sheet="c" x="40" y="10" hitbox="8x8" />
    <qg:timer every="60"><qg:goto-scene name="end" /></qg:timer>
    <qg:hud><qg:bar bind="a.health" /></qg:hud>
  </qg:scene>
  <qg:scene name="end"><qg:hud><qg:text value="{'over'}" /></qg:hud></qg:scene>
''' + TAIL)
        assert json.loads((out / 'game.json').read_text())['multiplayer']['rollback'] == 6

    @pytest.mark.parametrize('scene,message', [
        ('<qg:instance prefab="Coin" x="1" y="1" />', "holds instance, which goes through physics"),
        ('<qg:character id="p" controller="platformer" sheet="c" x="1" y="1" hitbox="4x4" />', 'holds controller="platformer"'),
        ('<qg:timer every="5"><qg:spawn prefab="Coin" at="path" path="r" /></qg:timer><qg:path name="r" points="0,0; 9,9" />',
         'holds path'),
    ])
    def test_what_rollback_refuses(self, tmp_path, scene, message):
        err = refuse(tmp_path, HEAD + f'''  <qg:multiplayer players="2" rollback="6" />
  <qg:scene name="fight">{scene}</qg:scene>
''' + TAIL)
        assert message in str(err)


class TestWhatRobotAsked:
    """What Godot's "Platformer 2D" made the language say (projects/robot/README.md)."""

    def test_tiles_with_shapes_of_their_own(self, tmp_path):
        out = build(tmp_path, HEAD.replace('tile="18" />', '''tile="18">
    <qg:tile frame="0" shape="0,4; 18,4; 18,18; 0,18" />
    <qg:tile frame="1" shape="0,0; 18,18; 0,18" one-way="true" />
    <qg:tile frame="2" shape="none" />
    <qg:tile frame="3" one-way="true" />
  </qg:tileset>''', 1) + '''  <qg:scene name="main">
    <qg:tilemap tileset="k" collision="true">
1,-2,3,4
    </qg:tilemap>
  </qg:scene>
''' + TAIL)
        data = json.loads((out / 'game.json').read_text())
        tiles = data['sheets']['k']['tiles']
        assert tiles['0'] == {'shape': [[0.0, 4.0], [18.0, 4.0], [18.0, 18.0], [0.0, 18.0]], 'one_way': False}
        assert tiles['1']['one_way'] is True and len(tiles['1']['shape']) == 3
        assert tiles['2'] == {'shape': None, 'one_way': False}
        assert tiles['3']['shape'] == [[0.0, 0.0], [18.0, 0.0], [18.0, 18.0], [0.0, 18.0]]   # the full square
        assert data['scenes']['main']['nodes'][0]['layers'][0]['rows'] == [[1, -2, 3, 4]]   # -2: flipped
        assert 'tiles' not in data['sheets']['c']
        for tile, message in (('<qg:tile frame="0" shape="0,0; 4,4" />', 'at least three points'),
                              ('<qg:tile frame="0" shape="none" one-way="true" />', 'one-way= means nothing'),
                              ('<qg:tile frame="0" /><qg:tile frame="0" />', 'two <qg:tile frame="0">')):
            err = refuse(tmp_path, HEAD.replace('tile="18" />', f'tile="18">{tile}</qg:tileset>', 1)
                         + '  <qg:scene name="main" />\n' + TAIL)
            assert message in str(err)
        err = refuse(tmp_path, HEAD.replace('tile="24" />', 'tile="24"><qg:tile frame="0" /></qg:spritesheet>', 1)
                     + '  <qg:scene name="main" />\n' + TAIL)
        assert '<qg:tile> cannot go inside <spritesheet>' in str(err)

    def test_solid_shapes_picture_scale_and_shots_stopped_by_walls(self, tmp_path):
        out = build(tmp_path, HEAD + '''  <qg:prefab name="Lift" tag="lift" sheet="k" hitbox="64x16" solid="true" one-way="true"
             shape="-32,-8; 32,-8; 32,4; -32,4" ai="shuttle" dy="-100" />
  <qg:prefab name="Shot" tag="shot" sheet="k" hitbox="4x4" ai="fly" heading="right" walls="stop" scale="0.5" />
  <qg:scene name="main">
    <qg:instance prefab="Lift" x="10" y="10" gd:rotation="0.3" />
  </qg:scene>
''' + TAIL)
        data = json.loads((out / 'game.json').read_text())
        assert data['prefabs']['Lift']['shape'][0] == [-32.0, -8.0]
        assert (data['prefabs']['Shot']['walls'], data['prefabs']['Shot']['scale']) == ('stop', 0.5)
        assert data['scenes']['main']['nodes'][0]['gd'] == {'rotation': {'type': 'float', 'value': 0.3}}
        for prefab, message in (('hitbox="4x4" shape="0,0; 1,0; 1,1"', 'shape= is for a solid prefab'),
                                ('hitbox="4x4" ai="patrol" walls="stop"', 'walls= is for ai="fly"'),
                                ('hitbox="4x4" scale="0"', 'scale=>: more than 0')):
            err = refuse(tmp_path, HEAD + f'  <qg:prefab name="X" tag="x" sheet="k" {prefab} />\n'
                         '  <qg:scene name="main" />\n' + TAIL)
            assert message in str(err)

    def test_the_platformer_accelerates_jumps_in_the_air_and_shoots(self, tmp_path):
        out = build(tmp_path, HEAD + '''  <qg:input action="shoot" keys="Ctrl" />
  <qg:prefab name="Shot" tag="shot" sheet="k" hitbox="4x4" ai="fly" heading="right" />
  <qg:scene name="main">
    <qg:character id="p" controller="platformer" sheet="c" x="0" y="0" hitbox="18x22" scale="0.8"
                  accel="1800" jump-speed="725" air-jumps="1" air-jump-boost="2.5" jump-cut="0.6"
                  fire-action="shoot" fire-prefab="Shot" fire-every="18">
      <qg:animation name="fall" frames="3" />
    </qg:character>
  </qg:scene>
''' + TAIL)
        p = json.loads((out / 'game.json').read_text())['scenes']['main']['nodes'][0]
        assert (p['accel'], p['jump_speed'], p['air_jumps'], p['air_jump_boost'], p['jump_cut'], p['scale']) == (
            1800.0, 725.0, 1, 2.5, 0.6, 0.8)
        assert (p['fire_action'], p['fire_prefab'], p['fire_every']) == ('shoot', 'Shot', 18)
        assert p['animations']['fall'] == {'frames': [3], 'fps': 8.0}
        cases = (
            ('controller="topdown" accel="10"', 'accel= is for controller="platformer"'),
            ('controller="platformer" jump-cut="2"', 'jump-cut=: between 0 and 1'),
            ('controller="platformer" fire-action="fire" fire-prefab="Shot"', 'fire-action="fire": no such action'),
            ('controller="platformer" fire-action="jump"', 'fire-action= needs fire-prefab='),
            ('controller="platformer" fire-action="jump" fire-prefab="Coin"', 'a platformer shoots a prefab with ai="fly"'),
            ('controller="topdown" fire-action="jump" fire-prefab="Shot"', 'fire-action= is for controller="ship" or "platformer"'),
        )
        for attrs, message in cases:
            err = refuse(tmp_path, HEAD + '''  <qg:prefab name="Shot" tag="shot" sheet="k" hitbox="4x4" ai="fly" />
  <qg:scene name="main">
    <qg:character id="p" sheet="c" x="0" y="0" hitbox="18x22" ''' + attrs + ''' />
  </qg:scene>
''' + TAIL)
            assert message in str(err), attrs

    def test_pause_resume_paused_and_a_menu_shown_while_paused(self, tmp_path):
        out = build(tmp_path, HEAD + '''  <qg:input action="pause" keys="Escape" />
  <qg:scene name="main">
    <qg:on-input action="pause">
      <q:if condition="{paused()}"><qg:resume /><q:else><qg:pause /></q:else></q:if>
    </qg:on-input>
    <qg:menu if="{paused()}">
      <qg:button label="Resume"><qg:resume /></qg:button>
    </qg:menu>
  </qg:scene>
''' + TAIL)
        script = (out / 'scripts' / 'scene_main.gd').read_text()
        assert 'if Q.paused(self):' in script and 'Q.pause(self, false)' in script and 'Q.pause(self, true)' in script
        menu = [n for n in json.loads((out / 'game.json').read_text())['scenes']['main']['nodes'] if n['kind'] == 'menu'][0]
        assert menu['if_method'] == '_q_menu_1_if'
        assert 'func _q_menu_1_if():\n\treturn Q.paused(self)' in script


class TestWhatTheArtAsked:
    """What redrawing the games asked of the language: a spawn at a point (Chess's dots)."""

    def test_spawn_at_a_point(self, tmp_path):
        out = build(tmp_path, HEAD + '''  <qg:scene name="main">
    <q:set name="c" value="2" type="number" />
    <qg:on-input action="jump">
      <qg:spawn prefab="Coin" x="{c * 62 + 31}" y="{93}" dy="-2" />
    </qg:on-input>
  </qg:scene>
''' + TAIL)
        script = (out / 'scripts' / 'scene_main.gd').read_text()
        assert 'Q.spawn_at(self, "Coin", Vector2(float(((c * 62) + 31)) + 0.0, float(93) + -2.0))' in script
        for attrs, message in (('x="1"', 'x= and y= together'), ('x="1" y="2" at="me"', 'x= and y=, or at=, not both')):
            err = refuse(tmp_path, HEAD + '''  <qg:scene name="main"><qg:on-input action="jump">
      <qg:spawn prefab="Coin" ''' + attrs + ''' />
    </qg:on-input></qg:scene>
''' + TAIL)
            assert message in str(err)
