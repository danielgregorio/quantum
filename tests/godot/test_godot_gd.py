"""`gd:` attributes reach the Godot node, and the compiler's table says the truth.

The compiler checks a `gd:` attribute against the class it says the tag
becomes (quantum/runtime/godot/gd.py: NODE_CLASS, PREFAB_CLASS). This runs
a game using one on every kind of node in Godot and reads back, through
tests/godot/gd_probe.gd, the class the runtime actually built and the value
each property holds.
"""

import json
from pathlib import Path

import pytest

from quantum.runtime.godot import gd as gdprops
from quantum.runtime.godot_bin import run_godot, script_errors

REPO = Path(__file__).resolve().parents[2]
PROBE = Path(__file__).with_name('gd_probe.gd')

SOURCE = '''<q:application id="gdprobe" type="game">
  <qg:tileset name="k" src="assets/kenney/tilemap_packed.png" tile="18" />
  <qg:spritesheet name="c" src="assets/kenney/tilemap-characters_packed.png" tile="24" />
  <qg:sound name="hurt" src="assets/kenney/audio/hurt.ogg" gd:volume_db="-6" gd:pitch_scale="1.25" />
  <qg:prefab name="Coin" tag="coin" sheet="k" frame="151" hitbox="12x12" gd:modulate="#ff000080" />
  <qg:prefab name="Crate" tag="crate" sheet="k" frame="9" hitbox="18x18" solid="true" gd:z_index="3" />
  <qg:prefab name="Walker" tag="enemy" sheet="c" frame="18" hitbox="18x18" ai="patrol" speed="30" gd:scale="2,2" />
  <qg:prefab name="Lift" tag="lift" sheet="k" frame="9" hitbox="18x8" solid="true" ai="shuttle" dy="-40" period="120" gd:visible="false" />
  <qg:scene name="main" gd:y_sort_enabled="true">
    <q:set name="coins" value="0" type="number" />
    <qg:tilemap tileset="k" collision="true" gd:z_index="-5">
0,0,0,0
23,23,23,23
    </qg:tilemap>
    <qg:character id="player" controller="platformer" sheet="c" x="10" y="10" hitbox="18x22" gd:floor_max_angle="0.5" />
    <qg:instance prefab="Coin" name="coin1" x="30" y="10" />
    <qg:instance prefab="Crate" name="crate1" x="50" y="10" gd:rotation="1.5" />
    <qg:instance prefab="Walker" name="walker1" x="60" y="10" />
    <qg:instance prefab="Lift" name="lift1" x="70" y="10" />
    <qg:exit name="door" x="60" y="10" width="18" height="18" to="main" at="door" gd:monitorable="false" />
    <qg:timer every="1" gd:process_priority="2" />
    <qg:camera follow="player" gd:zoom="2,2" gd:position_smoothing_enabled="true" />
    <qg:hud gd:layer="7">
      <qg:counter bind="coins" label="COINS" gd:modulate="#00ff00" />
      <qg:text bind="coins" gd:uppercase="true" />
    </qg:hud>
  </qg:scene>
</q:application>
'''

PROPS = ['zoom', 'position_smoothing_enabled', 'modulate', 'z_index', 'scale', 'visible', 'rotation',
         'floor_max_angle', 'monitorable', 'process_priority', 'layer', 'uppercase', 'y_sort_enabled',
         'volume_db', 'pitch_scale']


@pytest.fixture(scope='module')
def probed(godot, tmp_path_factory):
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    src = tmp_path_factory.mktemp('gd') / 'game.q'
    src.write_text(SOURCE, encoding='utf-8')
    app = QuantumParser(use_cache=False).parse_file(str(src))
    out = compile_game(app, str(src.parent / 'godot'), source_dir=str(REPO))
    dump = src.parent / 'probe.json'
    result = run_godot(['--path', str(out), '-s', str(PROBE), '--', f'--props={",".join(PROPS)}',
                        f'--out={dump}'], binary=godot)
    assert script_errors(result.stdout + result.stderr) == []
    return json.loads(dump.read_text(encoding='utf-8'))


def by_name(probed, name):
    found = [v for k, v in probed.items() if k.split('/')[-1] == name]
    assert found, f'no node named {name} in {sorted(probed)}'
    return found[0]


@pytest.mark.parametrize('name,cls', [
    ('player', 'CharacterBody2D'), ('coin1', 'Area2D'), ('crate1', 'StaticBody2D'),
    ('walker1', 'CharacterBody2D'), ('lift1', 'AnimatableBody2D'), ('exit-door', 'Area2D'),
    ('Camera', 'Camera2D'),
])
def test_the_runtime_builds_the_class_the_compiler_checks_against(probed, name, cls):
    assert by_name(probed, name)['class'] == cls


def test_every_class_in_the_table_is_in_godots_reference():
    classes = gdprops.table()['classes']
    for cls in list(gdprops.NODE_CLASS.values()) + list(gdprops.PREFAB_CLASS.values()):
        assert cls in classes, cls


def test_the_values_reach_the_nodes(probed):
    cam = by_name(probed, 'Camera')
    assert cam['zoom'] == 'Vector2(2, 2)' and cam['position_smoothing_enabled'] == 'true'
    assert by_name(probed, 'player')['floor_max_angle'] == '0.5'
    assert by_name(probed, 'coin1')['modulate'] == 'Color(1, 0, 0, 0.501961)'
    crate = by_name(probed, 'crate1')
    assert crate['z_index'] == '3' and crate['rotation'] == '1.5'      # the prefab's, and the instance's own
    assert by_name(probed, 'walker1')['scale'] == 'Vector2(2, 2)'
    assert by_name(probed, 'lift1')['visible'] == 'false'
    assert by_name(probed, 'exit-door')['monitorable'] == 'false'
    timers = [v for v in probed.values() if 'process_priority' in v and v['process_priority'] == '2']
    assert timers, 'the timer carries its process_priority'
    scene = [v for k, v in probed.items() if v['class'] == 'Node2D' and v.get('y_sort_enabled') == 'true']
    assert scene, 'the scene node carries gd:y_sort_enabled'


def test_the_hud_and_its_labels(probed):
    huds = [v for v in probed.values() if v['class'] == 'CanvasLayer']
    assert huds and huds[0]['layer'] == '7'
    labels = [v for v in probed.values() if v['class'] == 'Label']
    assert sorted(label.get('uppercase') for label in labels) == ['false', 'true']
    assert any(label['modulate'] == 'Color(0, 1, 0, 1)' for label in labels)


def test_the_tilemap_layers_and_the_sound(probed):
    layers = [v for v in probed.values() if v['class'] == 'TileMapLayer']
    assert layers and all(layer['z_index'] == '-5' for layer in layers)
    players = [v for v in probed.values() if v['class'] == 'AudioStreamPlayer']
    assert players and players[0]['volume_db'] == '-6.0' and players[0]['pitch_scale'] == '1.25'
