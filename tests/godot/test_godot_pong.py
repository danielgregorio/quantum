"""Pong — Godot's own demo, transcribed — replayed in Godot.

projects/pong/pong.q is compiled and driven by input tapes. The numbers are
the original's: the ball starts at (320.5, 191.1) going left at 100 px/s
and 2 px/s² faster; the paddles are 8x32 at x=67.6 and x=563.8 and move at
100 px/s; the court is 640x400.
"""

import shutil
from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_replay import replay, tape_from_holds

PONG = Path(__file__).resolve().parents[2] / 'projects' / 'pong' / 'pong.q'
START = {'x': 320.5, 'y': 191.12}


@pytest.fixture(scope='module')
def project(godot, tmp_path_factory) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    src_dir = tmp_path_factory.mktemp('pong')
    shutil.copytree(PONG.parent, src_dir / 'pong', ignore=shutil.ignore_patterns('godot'))
    app = QuantumParser(use_cache=False).parse_file(str(src_dir / 'pong' / 'pong.q'))
    out = compile_game(app, str(src_dir / 'godot'), source_dir=str(src_dir / 'pong'))
    assert check_project(Path(out), binary=godot) == []
    return Path(out)


# The title's first button, "Two players, one keyboard", chosen on tick 0: the
# court's first tick is the replay's tick 1. Court tapes are in court ticks.
ENTER = 1


def court(project, ticks, holds=()):
    tape = tape_from_holds([('select', 0, 2)] + [(a, s + ENTER, e + ENTER) for a, s, e in holds])
    return replay(project, ticks + ENTER, tape=tape)['court']


def test_the_ball_flies_left_faster_and_faster(godot, project):
    first = court(project, 1)['named']['ball']
    assert first == {'x': round(320.5 - 100 / 60, 2), 'y': START['y']}      # 100 px/s, one tick
    at_100 = court(project, 100)['named']['ball']['x']
    assert 320.5 - 100 * 100 / 60 - 3 < at_100 < 320.5 - 100 * 100 / 60    # a little faster than 100 px/s


def test_the_left_paddle_sends_it_back_at_a_slant(godot, project):
    before = court(project, 140)['named']['ball']
    after = court(project, 200)['named']['ball']
    assert before['x'] < 90 and before['y'] == START['y']
    assert after['x'] > before['x'] and after['y'] != START['y']   # going right, with a random dy from the seed
    assert court(project, 200) == court(project, 200)            # and the same every time


def test_the_ball_stays_in_the_court_and_resets_past_a_paddle(godot, project):
    # Nobody moves the right paddle: the ball, sent up by the left one, bounces
    # off the ceiling and leaves the court at the right wall; then it is back.
    assert min(court(project, t)['named']['ball']['y'] for t in (440, 460)) >= 0
    back = court(project, 470)['named']['ball']
    assert back['y'] == START['y'] and 300 < back['x'] < START['x']   # going left again, from the start


def test_each_paddle_has_its_own_player(godot, project):
    nodes = court(project, 60, [('down', 0, 60), ('p2_up', 0, 60)])['nodes']
    assert nodes['left'] == {'x': 67.63, 'y': 292.59}
    assert nodes['right'] == {'x': 563.82, 'y': 88.92}
    # a paddle stops at the edge of the court, and never moves sideways
    nodes = court(project, 200, [('up', 0, 200), ('p2_down', 0, 200), ('left', 0, 200), ('right', 0, 200)])['nodes']
    assert nodes['left'] == {'x': 67.63, 'y': 16.0}
    assert nodes['right'] == {'x': 563.82, 'y': 384.0}


def test_a_paddle_out_of_the_way_lets_the_ball_through(godot, project):
    tape = [('up', 0, 200)]
    assert court(project, 170, tape)['named']['ball']['x'] < 40
    back = court(project, 190, tape)['named']['ball']
    assert back['y'] == START['y'] and 300 < back['x'] < START['x']
