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
        assert scene['nodes'][0]['rows'] == [[0, 0, 0], [23, 23, 23]]
        assert scene['nodes'][1]['on_collision'] == [{'with': 'coin', 'handler': '_on_player_collision_0'}]
        assert data['prefabs']['Coin'] == {'tag': 'coin', 'sheet': 'k', 'frame': 151, 'hitbox': [12, 12]}

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
        assert 'asset not found: art/none.png' in e.message
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
