"""ai="pathfind" in Godot: around the walls, where chase stops at them.

A room of 10x7 tiles with a wall down its middle and one gap, low. The hero
stands right of the wall; two monsters start left of it, at the same cell:
one chases (straight at the hero, into the wall), one pathfinds (down to
the gap, through it, and up to the hero).
"""

import math
from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_replay import replay

REPO = Path(__file__).resolve().parents[2]

SOURCE = '''<q:application id="paths" type="game">
  <qg:tileset name="dungeon" src="projects/keep/assets/dungeon.png" tile="18">
    <qg:tile frame="0" shape="none" />
  </qg:tileset>
  <qg:spritesheet name="hero" src="projects/keep/assets/hero.png" tile="24" />
  <qg:prefab name="Chaser" tag="enemy" sheet="dungeon" frame="9" hitbox="12x12" ai="chase" speed="40" sight="400" />
  <qg:prefab name="Finder" tag="enemy" sheet="dungeon" frame="9" hitbox="12x12" ai="pathfind" speed="40" sight="400" />
  <qg:scene name="room" width="180" height="126">
    <qg:tilemap tileset="dungeon" collision="true">
2,2,2,2,2,2,2,2,2,2
2,1,1,1,2,1,1,1,1,2
2,1,1,1,2,1,1,1,1,2
2,1,1,1,2,1,1,1,1,2
2,1,1,1,1,1,1,1,1,2
2,1,1,1,2,1,1,1,1,2
2,2,2,2,2,2,2,2,2,2
    </qg:tilemap>
    <qg:character id="hero" controller="topdown" sheet="hero" frame="0" x="135" y="45" hitbox="12x12" />
    <qg:instance prefab="Chaser" name="chaser" x="45" y="45" />
    <qg:instance prefab="Finder" name="finder" x="45" y="45" />
  </qg:scene>
</q:application>
'''


@pytest.fixture(scope='module')
def project(godot, tmp_path_factory) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    src = tmp_path_factory.mktemp('paths') / 'paths.q'
    src.write_text(SOURCE, encoding='utf-8')
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(src)), str(src.parent / 'godot'),
                            source_dir=str(REPO)))
    assert check_project(out, binary=godot) == []
    return out


def test_pathfind_goes_around_the_wall_where_chase_stops(project, godot):
    room = replay(project, 400, binary=godot)['room']
    hero, chaser, finder = room['nodes']['hero'], room['named']['chaser'], room['named']['finder']
    assert chaser['x'] < 72                                         # against the wall's left side (x 72..90)
    assert math.dist((finder['x'], finder['y']), (hero['x'], hero['y'])) < 14   # at the hero
    assert replay(project, 400, binary=godot)['room'] == room       # the same way every time


def test_it_goes_through_the_gap(project, godot):
    # on its way, it is in the gap's cell (column 4, row 4: x 72..90, y 72..90)
    seen = [replay(project, t, binary=godot)['room']['named']['finder'] for t in range(60, 241, 20)]
    assert any(72 <= f['x'] <= 90 and 72 <= f['y'] <= 90 for f in seen), seen
