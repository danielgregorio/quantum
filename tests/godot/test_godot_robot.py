"""Robot — Godot's "Platformer 2D" demo, transcribed — replayed in Godot.

projects/robot/robot.q is compiled and driven by input tapes. The numbers
are the original's: a 2100 px/s² world, a robot that runs at 300 px/s
reached at 1800 px/s², takes off at 725 px/s, jumps once more in the air
(2.5 times faster across), and shoots 850 px/s bullets every 0.3 s; enemies
crawl at 22 px/s. The level is the demo's map moved by (768, 704), so the
robot starts at (858, 1329) on a grassy top 10 px below its tiles' edge.
"""

import shutil
from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_replay import replay, tape_from_holds

ROBOT = Path(__file__).resolve().parents[2] / 'projects' / 'robot' / 'robot.q'
FEET = 22.0   # half the robot's 44 px hitbox


@pytest.fixture(scope='module')
def project(godot, tmp_path_factory) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    src_dir = tmp_path_factory.mktemp('robot')
    shutil.copytree(ROBOT.parent, src_dir / 'robot', ignore=shutil.ignore_patterns('godot'))
    app = QuantumParser(use_cache=False).parse_file(str(src_dir / 'robot' / 'robot.q'))
    out = compile_game(app, str(src_dir / 'godot'), source_dir=str(src_dir / 'robot'))
    assert check_project(Path(out), binary=godot) == []
    return Path(out)


def level(project, ticks, holds=()):
    return replay(project, ticks, tape=tape_from_holds(list(holds)) if holds else None)['level']


def robot(state):
    return state['nodes']['robot']


def where(state, tag):
    return [w for w in state['where'] if w[0] == tag]


def test_the_robot_stands_on_the_lowered_grass_and_the_world_moves(project):
    state = level(project, 60)
    assert robot(state)['y'] + FEET == pytest.approx(1354.0, abs=0.1)     # row 21 at 1344, its top 10 px down
    assert state['things'] == {'coin': 21, 'enemy': 3, 'ledge': 1, 'lift': 2}
    assert state['named'] == {}                       # 21 coins of one prefab: no made-up names reported
    enemies = sorted(e[1] for e in where(state, 'enemy'))
    assert enemies == [1185.0, 1282.0, 1334.0]        # 22 px in a second, from 1163, 1260 and 1312
    lifts = sorted(where(state, 'lift'))
    assert lifts == [['lift', 740.0, 1275.3], ['lift', 1568.0, 1009.0]]


def test_it_runs_up_to_speed_and_collects_coins(project):
    assert robot(level(project, 10, [('right', 0, 200)]))['x'] == 885.5       # 30, 60 ... 270 px/s: accelerating
    assert robot(level(project, 30, [('right', 0, 200)]))['x'] == 985.5     # then 5 px a tick
    state = level(project, 40, [('right', 0, 200)])
    assert state['coins'] == 3 and state['sounds'] == ['coin'] * 3             # the row of three at 968-1028


def test_a_jump_held_rises_higher_than_one_released_early(project):
    held = level(project, 32, [('jump', 10, 60)])
    cut = level(project, 32, [('jump', 10, 13)])
    assert 1332.0 - robot(held)['y'] > 105.0          # 725 px/s against 2100 px/s²: about 119 px
    assert robot(cut)['y'] > robot(held)['y'] + 30.0  # released: the rise is cut to 0.6
    assert held['sounds'] == ['jump']


def test_one_more_jump_in_the_air_faster_across_and_no_third(project):
    single = level(project, 40, [('right', 0, 200), ('jump', 10, 40)])
    double = level(project, 40, [('right', 0, 200), ('jump', 10, 20), ('jump', 22, 40)])
    triple = level(project, 40, [('right', 0, 200), ('jump', 10, 20), ('jump', 22, 26), ('jump', 28, 40)])
    assert robot(double)['x'] > robot(single)['x'] + 40.0      # 2.5 times across on the air jump
    assert double['sounds'].count('jump') == 2
    assert triple['sounds'].count('jump') == 2


def test_it_shoots_the_way_it_faces_every_three_tenths(project):
    state = level(project, 20, [('shoot', 5, 6), ('shoot', 10, 11)])
    assert state['sounds'] == ['shoot']               # the second press is within the 18-tick cooldown
    assert where(state, 'bullet') == [['bullet', 1073.3, 1332.0]]
    # facing left, towards the wall at x=576: the bullet is gone on it, long before its second is up
    left = level(project, 40, [('left', 0, 2), ('shoot', 5, 6)])
    assert left['sounds'] == ['shoot'] and 'bullet' not in left['things']
    assert robot(left)['x'] < 858.0


def test_a_bullet_destroys_the_enemy_it_meets(project):
    state = level(project, 60, [('shoot', 5, 6)])
    assert state['sounds'] == ['shoot', 'explode']
    assert state['things']['enemy'] == 2 and 'bullet' not in state['things']


def test_the_slope_is_walked_up_after_the_step(project):
    state = level(project, 220, [('right', 0, 400), ('jump', 150, 152)])
    x, y = robot(state)['x'], robot(state)['y']
    assert 1600.0 < x < 1664.0 and y < 1290.0         # on the slope tile, above the floor at 1354


def test_the_lift_carries_it_up(project):
    state = level(project, 200, [('left', 0, 12), ('jump', 40, 50)])
    lift = [w for w in where(state, 'lift') if w[1] == 740.0][0]
    assert robot(state)['y'] + FEET == pytest.approx(lift[2] - 21.0, abs=1.5)   # its feet on the lift's top
    assert robot(state)['y'] < 1100.0


def test_pause_freezes_the_world_and_the_menu_resumes_it(project):
    paused = level(project, 50, [('pause', 20, 21)])
    assert paused.get('paused') is True
    assert where(paused, 'enemy') == where(level(project, 20), 'enemy')        # stopped on the tick it was asked
    resumed = level(project, 50, [('pause', 20, 21), ('select', 30, 31)])    # Resume has the focus
    assert 'paused' not in resumed
    assert where(resumed, 'enemy') == where(level(project, 39), 'enemy')       # still on ticks 20 to 30, both included
    # not paused, the menu is not there: select chooses nothing
    assert 'paused' not in level(project, 30, [('select', 10, 11)])
