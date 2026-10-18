"""qg:set-tile in Godot: a wall that opens, and what moves sees it at once.

The room of test_godot_pathfind.py with its wall whole: the monster that
pathfinds is walled off and waits. On tick 60 a timer empties one cell of
the wall; the monster finds the way through it to the hero. The cells
changed are part of the state, and tile_at() reads them. A lever the hero
walks into sets a tile the map had nowhere yet from a collision handler,
which runs while the physics server is busy: the cell's collision is made
the tick after.
"""

import math
from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_replay import replay, tape_from_holds

REPO = Path(__file__).resolve().parents[2]

SOURCE = '''<q:application id="tiles" type="game">
  <qg:tileset name="dungeon" src="projects/keep/assets/dungeon.png" tile="18">
    <qg:tile frame="0" shape="none" />
  </qg:tileset>
  <qg:spritesheet name="hero" src="projects/keep/assets/hero.png" tile="24" />
  <qg:prefab name="Lever" tag="lever" sheet="dungeon" frame="4" hitbox="14x14" />
  <qg:prefab name="Finder" tag="enemy" sheet="dungeon" frame="9" hitbox="12x12" ai="pathfind" speed="40" sight="400" />
  <qg:scene name="room" width="180" height="126">
    <q:set name="before" value="-1" type="number" />
    <q:set name="after" value="-1" type="number" />
    <qg:tilemap tileset="dungeon" collision="true">
2,2,2,2,2,2,2,2,2,2
2,1,1,1,2,1,1,1,1,2
2,1,1,1,2,1,1,1,1,2
2,1,1,1,2,1,1,1,1,2
2,1,1,1,2,1,1,1,1,2
2,1,1,1,2,1,1,1,1,2
2,2,2,2,2,2,2,2,2,2
    </qg:tilemap>
    <qg:character id="hero" controller="topdown" sheet="hero" frame="0" x="135" y="45" hitbox="12x12">
      <qg:on-collision with="lever"><qg:set-tile col="5" row="4" tile="4" /></qg:on-collision>
    </qg:character>
    <qg:instance prefab="Lever" name="lever" x="135" y="99" />
    <qg:instance prefab="Finder" name="finder" x="45" y="45" />
    <qg:timer after="60">
      <q:set name="before" value="{tile_at(4, 2)}" />
      <qg:set-tile col="4" row="2" tile="{1 - 1}" />
      <q:set name="after" value="{tile_at(4, 2)}" />
    </qg:timer>
  </qg:scene>
</q:application>
'''


@pytest.fixture(scope='module')
def project(godot, tmp_path_factory) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    src = tmp_path_factory.mktemp('tiles') / 'tiles.q'
    src.write_text(SOURCE, encoding='utf-8')
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(src)), str(src.parent / 'godot'),
                            source_dir=str(REPO)))
    assert check_project(out, binary=godot) == []
    return out


def test_walled_off_it_waits(project, godot):
    room = replay(project, 59, binary=godot)['room']
    assert 'tiles' not in room                                   # nothing changed yet
    finder = room['named']['finder']
    assert (finder['x'], finder['y']) == (45.0, 45.0)


def test_an_opened_cell_lets_it_through(project, godot):
    room = replay(project, 400, binary=godot)['room']
    assert room['tiles'] == {'4,2': 0}
    assert (room['before'], room['after']) == (2, 0)
    hero, finder = room['nodes']['hero'], room['named']['finder']
    assert math.dist((finder['x'], finder['y']), (hero['x'], hero['y'])) < 14
    assert replay(project, 400, binary=godot)['room'] == room


def test_a_lever_sets_a_new_tile_from_a_collision_handler(project, godot):
    room = replay(project, 120, tape_from_holds([('down', 1, 60)]), binary=godot)['room']   # no Godot error either
    assert room['tiles'] == {'4,2': 0, '5,4': 4}             # a tile the map had nowhere yet: made then
