"""A world's game, compiled (PLAN_GAME_SERVER.md, Phase 2): what the compiler reads of the world.

A game with qg:connect is a world's client, and its compiler reads the world's file: a qg:send of a command the
world has not, or without its arguments, a mirror of a view it has not, an event it never emits, a field none of its
entities has, a kind with no prefab to draw it: each is an error as the game compiles, with its line, not a refusal
of the server as it runs. (Godot plays the meadow's game in tests/godot/test_godot_world.py.)
"""

import json
import shutil
from pathlib import Path

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.godot import compile_game
from quantum.runtime.godot.errors import GameCompileError

MEADOW = Path(__file__).resolve().parent / 'worlds' / 'meadow'
GAME = (MEADOW / 'meadow.q').read_text()


def build(tmp_path: Path, source: str) -> Path:
    for name in ('meadow.server.q', 'meadow.tmx', 'meadow.png', 'folk.png'):
        shutil.copy(MEADOW / name, tmp_path / name)
    src = tmp_path / 'game.q'
    src.write_text(source, encoding='utf-8')
    return Path(compile_game(QuantumParser(use_cache=False).parse_file(str(src)), str(tmp_path / 'godot'),
                             source_dir=str(tmp_path)))


def test_the_meadows_game_compiles_with_what_it_needs_of_the_world(tmp_path):
    out = build(tmp_path, GAME)
    game = json.loads((out / 'game.json').read_text())
    assert game['world'] == {'name': 'meadow', 'local': 'ws://127.0.0.1:7700', 'server': None,
                             'kinds': {'Hero': 0.1}, 'views': ['around', 'loud'], 'hero': 'Hero'}
    scene = game['scenes']['meadow']
    assert scene['world'] is True and list(scene['on_event']) == ['shout']
    assert scene['on_refused'][0]['command'] == 'step'
    assert {'kind': 'mirror', 'view': 'around'} in scene['nodes']
    assert game['overlays']['bag']['overlay']['freeze'] is False
    script = (out / 'scripts' / 'scene_meadow.gd').read_text()
    assert 'Q.world_send("step", {"dir": "north"})' in script
    assert 'Q.wf(Q.world_me(), "purse")' in script                 # a field of the world's entity


@pytest.mark.parametrize('change, says', [
    (('<qg:send command="earn" />', '<qg:send command="dig" />'),
     'the world \'meadow\' has no such command (it has: boast, earn, go, hush, ring, shout, step, whisper)'),
    (('<qg:send command="shout" text="hello" />', '<qg:send command="shout" />'), 'it needs text='),
    (('<qg:send command="earn" />', '<qg:send command="earn" much="2" />'), 'it takes no much='),
    (('<qg:mirror view="around" />', '<qg:mirror view="everything" />'), 'has no such view (it has: around, loud)'),
    (('<qg:on-event name="shout">', '<qg:on-event name="hit">'), 'emits no such event (its q:emit say: bell, shout'),
    (('<qg:on-refused command="step">', '<qg:on-refused command="jump">'), 'has no such command'),
    (('{me.name}', '{me.title}'), 'me.title: no such field'),
    (('<qg:prefab name="Hero"', '<qg:prefab name="Folk"'), 'the world has entities of kind \'Hero\''),
    (('<qg:prefab name="Hero" sheet="folk"', '<qg:prefab name="Hero" ai="wander" sheet="folk"'),
     'moves as the world says; its prefab has no ai='),
    (('world="true"', ''), '<qg:mirror> is in a scene of the world'),
    (('<qg:connect world="meadow.server.q" />', '<qg:connect world="nowhere.server.q" />'), 'nowhere.server.q'),
    (('<qg:connect world="meadow.server.q" />', '<qg:connect world="meadow.server.q" />\n'
                                                '  <qg:multiplayer players="2" />'), 'not both'),
])
def test_what_the_world_has_not_is_an_error_as_the_game_compiles(tmp_path, change, says):
    old, new = change
    assert old in GAME
    with pytest.raises(GameCompileError) as e:
        build(tmp_path, GAME.replace(old, new, 1))
    assert says in str(e.value), str(e.value)


def test_a_game_that_is_no_worlds_client_has_no_world(tmp_path):
    game = GAME.replace('  <qg:connect world="meadow.server.q" />\n', '')
    with pytest.raises(GameCompileError, match="the game is no world's client"):
        build(tmp_path, game)
    plain = ('<q:application id="p" type="game"><qg:scene name="s">'
             '<qg:hud><qg:text value="{me().name}" /></qg:hud></qg:scene></q:application>')
    with pytest.raises(GameCompileError, match=r"me\(\) is a world's"):
        build(tmp_path, plain)


# --- Phase 3: the step shown at once, and the bars --------------------------------------------------------------

DEN = Path(__file__).resolve().parent / 'worlds' / 'den'


def build_den(tmp_path: Path, source: str = None) -> Path:
    for name in ('den.server.q', 'den.tmx', 'den.png', 'folk.png', 'rat.png'):
        shutil.copy(DEN / name, tmp_path / name)
    src = tmp_path / 'den.q'
    src.write_text(source or (DEN / 'den.q').read_text(), encoding='utf-8')
    return Path(compile_game(QuantumParser(use_cache=False).parse_file(str(src)), str(tmp_path / 'godot'),
                             source_dir=str(tmp_path)))


def test_the_game_knows_the_steps_it_may_show_at_once_and_the_walls(tmp_path):
    world = json.loads((build_den(tmp_path) / 'game.json').read_text())['world']
    assert world['predict'] == {'step': 'dir'} and world['kinds'] == {'Hero': 0.1, 'Rat': 0.5}
    walls = world['walls']
    assert (walls['width'], walls['height']) == (48, 32) and walls['rows'][16][10:38] == '1' * 28
    assert walls['rows'][3][3] == '0' and walls['rows'][0] == '1' * 48


def test_a_health_bar_and_a_bar_of_an_expression(tmp_path):
    out = build_den(tmp_path)
    game = json.loads((out / 'game.json').read_text())
    assert game['prefabs']['Rat']['bars'][0]['method'] == '_Rat_bar_0'
    prefabs = (out / 'scripts' / 'prefabs.gd').read_text()
    assert 'func _Rat_bar_0_max(me) -> float:' in prefabs and 'Q.wf(me, "max_hp")' in prefabs
    hud = next(n for n in game['scenes']['den']['nodes'] if n['kind'] == 'hud')
    bar = next(i for i in hud['items'] if i['kind'] == 'bar')
    assert bar['value_method'] == '_q_bar_0' and bar['max_method'] == '_q_bar_0_max'


@pytest.mark.parametrize('change, says', [
    (('<qg:bar value="{me().hp}"', '<qg:bar bind="note" value="{me().hp}"'), 'bind= or value=, one of them'),
    (('<qg:health-bar value="{me.hp}" max="{me.max_hp}" dy="-9" />',
      '<qg:health-bar value="{me.hp}" max="{me.max_hp}" width="0" />'), 'width= and height= 1 or more'),
    (('max="{me.max_hp}" dy="-8"', 'max="{me.top}" dy="-8"'), 'me.top: no such field'),
])
def test_what_the_bars_refuse(tmp_path, change, says):
    source = (DEN / 'den.q').read_text()
    assert change[0] in source
    with pytest.raises(GameCompileError) as e:
        build_den(tmp_path, source.replace(change[0], change[1], 1))
    assert says in str(e.value), str(e.value)
