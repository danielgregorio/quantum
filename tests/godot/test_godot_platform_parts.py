"""Enemies of parts under gravity in Godot: qg:gravity and qg:leap in a prefab's qg:behavior.

A side-on level of 18 px tiles, 15 across and 8 down: the floor is row 7
(its top at y=126, where a 12 px tall enemy stands at y=120), a one-tile
step at column 9 (x 162..180, its top at y=108), and a ledge in the air on
row 3, columns 1 to 5 (x 18..108, its top at y=54). The enemies walk 30 px/s.
"""

from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_replay import replay

REPO = Path(__file__).resolve().parents[2]

GAME = '''<q:application id="ledges" type="game">
  <qg:tileset name="k" src="assets/kenney/tilemap_packed.png" tile="18" />
  <qg:spritesheet name="c" src="assets/kenney/tilemap-characters_packed.png" tile="24" />
  <q:set name="jumpy" value="false" type="boolean" />
  <qg:prefab name="Walker" tag="walker" sheet="k" frame="151" hitbox="12x12" ai="behavior" speed="30" turns-at="edge">
    <qg:behavior><qg:gravity /><qg:patrol heading="right" /></qg:behavior>
  </qg:prefab>
  <qg:prefab name="Hound" tag="hound" sheet="k" frame="151" hitbox="12x12" ai="behavior" speed="30">
    <qg:behavior><qg:gravity /><qg:leap height="30" /><qg:seek target="hero" sight="300" through-walls="true" /></qg:behavior>
  </qg:prefab>
  <qg:prefab name="Dog" tag="dog" sheet="k" frame="151" hitbox="12x12" ai="behavior" speed="30">
    <qg:behavior><qg:gravity /><qg:seek target="hero" sight="300" through-walls="true" /></qg:behavior>
  </qg:prefab>
  <qg:prefab name="Jumper" tag="jumper" sheet="k" frame="151" hitbox="12x12" ai="behavior">
    <qg:behavior><qg:gravity /><qg:leap height="20" at-wall="false" every="40" when="{jumpy}" /><qg:stand />
    </qg:behavior>
  </qg:prefab>
  <qg:scene name="level" width="270" height="144">
    <qg:tilemap tileset="k" collision="true">
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,1,1,1,1,1,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,1,0,0,0,0,0
1,1,1,1,1,1,1,1,1,1,1,1,1,1,1
    </qg:tilemap>
    <qg:character id="hero" controller="platformer" sheet="c" frame="0" x="240" y="118" hitbox="12x16" />
    <qg:instance prefab="Walker" name="walker" x="45" y="48" />
    <qg:instance prefab="Hound" name="hound" x="60" y="120" />
    <qg:instance prefab="Dog" name="dog" x="45" y="120" />
    <qg:instance prefab="Jumper" name="jumper" x="130" y="120" />
    <qg:timer after="30"><q:set name="jumpy" value="true" /></qg:timer>
  </qg:scene>
</q:application>
'''


@pytest.fixture(scope='module')
def project(tmp_path_factory, godot):
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    src = tmp_path_factory.mktemp('ledges') / 'ledges.q'
    src.write_text(GAME, encoding='utf-8')
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(src)), str(src.parent / 'godot'),
                            source_dir=str(REPO)))
    assert check_project(out, binary=godot) == []
    return out


def at(project, godot, ticks):
    return replay(project, ticks, binary=godot)['level']['named']


def test_turns_at_edge_keeps_a_walker_on_its_ledge(project, godot):
    for ticks in (100, 300):
        walker = at(project, godot, ticks)['walker']
        assert walker['y'] == pytest.approx(48, abs=0.5)               # never off the ledge (its top at 54)
        assert 18 < walker['x'] < 108 and walker['doing'] == 'patrol'


def test_a_leap_gets_a_seeker_over_a_step_one_without_stays(project, godot):
    named = at(project, godot, 300)                                          # landed, short of the hero
    assert named['hound']['x'] > 180 and named['hound']['doing'] == 'seek'   # over the step, on to the hero
    assert named['hound']['y'] == pytest.approx(120, abs=0.5)
    assert named['dog']['x'] == pytest.approx(156, abs=0.5)                  # up against the step (x 162)


def test_a_leap_when_its_condition_holds(project, godot):
    assert at(project, godot, 25)['jumper']['y'] == pytest.approx(120, abs=0.5)   # jumpy is false
    assert at(project, godot, 40)['jumper']['y'] < 112                           # up it goes
