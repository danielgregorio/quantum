"""qg:tween in Godot: a property eased over ticks, the same in every replay.

A small game: a coin that a timer slides down 60 px over one second
(linear), a box that pulses its scale back and forth (yoyo, for ever), and a
key, eased in with `back`, whose tween a second one replaces halfway.
"""

from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_replay import replay

REPO = Path(__file__).resolve().parents[2]

SOURCE = '''<q:application id="tweens" type="game">
  <qg:tileset name="k" src="assets/kenney/tilemap_packed.png" tile="18" />
  <qg:prefab name="Coin" tag="coin" sheet="k" frame="151" hitbox="12x12" />
  <qg:scene name="main" width="320" height="240">
    <qg:instance prefab="Coin" name="coin" x="100" y="40" />
    <qg:instance prefab="Coin" name="box" x="200" y="40" />
    <qg:instance prefab="Coin" name="key" x="40" y="200" />
    <qg:timer after="1">
      <qg:tween target="coin" property="y" to="100" seconds="1" trans="linear" />
      <qg:tween target="box" property="scale" to="{1 + 1}" seconds="0.5" trans="linear" repeat="-1" yoyo="true" />
      <qg:tween target="key" property="x" to="240" seconds="1" trans="back" ease="out" />
    </qg:timer>
    <qg:timer after="31">
      <qg:tween target="key" property="alpha" from="1" to="0" seconds="0.25" />
      <qg:tween target="key" property="x" to="40" seconds="0.5" trans="linear" />
    </qg:timer>
  </qg:scene>
</q:application>
'''


@pytest.fixture(scope='module')
def project(godot, tmp_path_factory) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    src = tmp_path_factory.mktemp('tweens') / 'tweens.q'
    src.write_text(SOURCE, encoding='utf-8')
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(src)), str(src.parent / 'godot'),
                            source_dir=str(REPO)))
    assert check_project(out, binary=godot) == []
    return out


def named(project, ticks, godot):
    return replay(project, ticks, binary=godot)['main']['named']


def test_a_tween_eases_a_property_over_its_ticks(project, godot):
    at = {t: named(project, t, godot) for t in (1, 31, 61, 90)}
    assert at[1]['coin']['y'] == 40.0                     # the timer runs on tick 1; the tween from tick 2
    assert at[31]['coin']['y'] == 70.0                    # half of 60 ticks: half of 60 px
    assert at[61]['coin']['y'] == 100.0 and at[90]['coin']['y'] == 100.0   # there, and it stays


def test_yoyo_goes_back_and_forth_for_ever(project, godot):
    scales = [named(project, t, godot)['box']['scale'] for t in (31, 61, 91, 121)]
    assert scales == [2.0, 1.0, 2.0, 1.0]


def test_a_new_tween_of_a_property_replaces_the_old(project, godot):
    key = named(project, 61, godot)['key']
    assert key['x'] < 240.0                                # turned back halfway, not on to 240
    assert named(project, 61 + 30, godot)['key']['x'] == 40.0
    assert key['alpha'] == 0.0                             # its own tween, alongside


def test_the_same_tape_gives_the_same_tweens(project, godot):
    assert replay(project, 77, binary=godot) == replay(project, 77, binary=godot)
