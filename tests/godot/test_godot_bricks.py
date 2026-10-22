"""Bricks — the brick breaker of the tags of 2026-10-21 — replayed in Godot.

projects/bricks/bricks.q is compiled and driven by input tapes: the serve as
jump is let go, a ball off the bottom costing a life, a brick broken from the
first serve, and — in a copy whose only level is one brick — the end of a level:
slow motion, the balls fading out, the paddle's hop and then the next scene.
"""

from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_replay import replay, tape_from_holds

BRICKS = Path(__file__).resolve().parents[2] / 'projects' / 'bricks' / 'bricks.q'
START = [('select', 1, 3)]          # Play alone, the title's first button
SERVE = [('jump', 60, 66)]          # let go on tick 66


def _project(godot, tmp_path_factory, levels=None) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    out_dir = tmp_path_factory.mktemp('bricks')
    source = BRICKS
    if levels is not None:   # the same game with other levels; its pictures and sounds where they are
        text = BRICKS.read_text(encoding='utf-8')
        start = text.index('<q:set name="levels"')
        end = text.index('/>', start) + 2
        source = out_dir / 'bricks.q'
        source.write_text(text[:start] + f"<q:set name=\"levels\" type=\"array\" value='{levels}' />" + text[end:],
                          encoding='utf-8')
    app = QuantumParser(use_cache=False).parse_file(str(source))
    out = compile_game(app, str(out_dir / 'godot'), source_dir=str(BRICKS.parent))
    assert check_project(Path(out), binary=godot) == []
    return Path(out)


@pytest.fixture(scope='module')
def project(godot, tmp_path_factory) -> Path:
    return _project(godot, tmp_path_factory)


@pytest.fixture(scope='module')
def one_brick(godot, tmp_path_factory) -> Path:
    return _project(godot, tmp_path_factory, '[["....R...."]]')


def run(project, ticks, holds=()):
    state = replay(project, ticks, tape=tape_from_holds(START + list(holds)))
    scene = next(iter(state))
    return scene, state[scene]


def balls(state):
    return [w for w in state['where'] if w[0] == 'ball']


def test_the_level_is_built_from_its_letters(godot, project):
    scene, level = run(project, 50)
    assert scene == 'level' and level['things'] == {'brick': 44, 'bomb': 1}
    assert ['bomb', 160.0, 64.0] in level['where']                   # row 2, the fifth letter: X
    assert level['serving'] is True and balls(level) == []


def test_the_serve_is_on_letting_go(godot, project):
    _, held = run(project, 65, SERVE)
    assert balls(held) == [] and held['serving'] is True              # held: nothing yet
    _, let_go = run(project, 70, SERVE)
    assert let_go['serving'] is False and len(balls(let_go)) == 1     # let go: a ball leaves the paddle


def test_the_first_serve_breaks_the_brick_above(godot, project):
    _, level = run(project, 130, SERVE)
    assert level['things']['brick'] == 43 and level['game']['score'] == 10.0   # the blue one, worth 10


def test_a_ball_off_the_bottom_costs_a_life(godot, project):
    # the paddle leaves as the ball comes back down: it falls past
    _, level = run(project, 260, SERVE + [('left', 140, 200)])
    assert level['game']['lives'] == 2.0 and level['serving'] is True and balls(level) == []


def test_the_last_brick_ends_the_level_in_slow_motion(godot, one_brick):
    scene, level = run(one_brick, 150, SERVE)
    assert scene == 'level' and level['done'] is True and level['game']['score'] == 50.0   # the red one, worth 50
    assert level['things'] == {'ball': 1} and level['nodes']['p1']['y'] < 226               # fading; the paddle hops
    scene, level = run(one_brick, 175, SERVE)
    assert scene == 'level' and level['things'] == {}                 # the ball faded out, and is gone
    scene, _ = run(one_brick, 220, SERVE)
    assert scene == 'won'                                             # after the hop: the only level is done


def test_the_same_tape_gives_the_same_game(godot, project):
    holds = SERVE + [('right', 100, 140)]
    assert run(project, 300, holds) == run(project, 300, holds)
