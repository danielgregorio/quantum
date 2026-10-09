"""Creeps — Godot's "Dodge the Creeps" demo, transcribed — replayed in Godot.

projects/creeps/creeps.q is compiled and driven by input tapes. The numbers
are the original's: a 480x720 screen, the player at (240, 450) moving at
400 px/s, "Get Ready" for two seconds, then a creep every half second from
the border and a point a second.
"""

import shutil
from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_replay import replay, tape_from_holds

CREEPS = Path(__file__).resolve().parents[2] / 'projects' / 'creeps' / 'creeps.q'
START = [('jump', 1, 3)]   # the title scene: jump starts the game on tick 2


@pytest.fixture(scope='module')
def project(godot, tmp_path_factory) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    src_dir = tmp_path_factory.mktemp('creeps')
    shutil.copytree(CREEPS.parent, src_dir / 'creeps', ignore=shutil.ignore_patterns('godot'))
    app = QuantumParser(use_cache=False).parse_file(str(src_dir / 'creeps' / 'creeps.q'))
    out = compile_game(app, str(src_dir / 'godot'), source_dir=str(src_dir / 'creeps'))
    assert check_project(Path(out), binary=godot) == []
    return Path(out)


def run(project, ticks, holds=()):
    state = replay(project, ticks, tape=tape_from_holds(START + list(holds)))
    scene = next(iter(state))
    return scene, state[scene]


def test_the_title_waits_for_the_start_key(godot, project):
    state = replay(project, 30)
    assert list(state) == ['title']
    assert state['title']['message'] == 'Dodge the\nCreeps' and state['title']['start'] == 'Start'


def test_get_ready_then_creeps_from_the_border_and_a_point_a_second(godot, project):
    scene, play = run(project, 100)
    assert scene == 'play' and play['message'] == 'Get Ready' and play['things'] == {}
    assert play['sounds'] == ['music'] and play['game'] == {'score': 0.0}
    scene, play = run(project, 185)
    assert play['message'] == '' and play['things'] == {'creep': 2} and play['game'] == {'score': 1.0}
    for tag, x, y in play['where']:
        assert tag == 'creep' and -40 <= x <= 520 and -40 <= y <= 760
    assert run(project, 185) == run(project, 185)   # the seed makes the creeps the same creeps


def test_the_player_moves_at_400_and_stays_on_the_screen(godot, project):
    _, play = run(project, 80, [('left', 10, 80), ('up', 10, 80)])
    player = play['nodes']['player']
    assert player['x'] == 27.0                                     # the left edge: half the hitbox
    assert abs(player['y'] - (450 - 70 * 400 / 60 / 2 ** 0.5)) < 0.5  # diagonal, 70 ticks


def test_a_creep_ends_the_run_and_the_score_stays(godot, project):
    holds = [('left', 10, 80), ('up', 10, 80)]
    scene, over = run(project, 300, holds)
    assert scene == 'over' and over['message'] == 'Game Over' and over['start'] == ''
    assert over['sounds'][-2:] == ['-music', 'death'] and over['game']['score'] >= 1
    scene, over = run(project, 600, holds)
    assert over['message'] == 'Dodge the\nCreeps' and over['start'] == 'Start'
