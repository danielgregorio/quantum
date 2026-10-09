"""The replay harness: a tape in, the game's state out, the same every time.

On tests/godot/fixtures/mover: a node that moves 2 px to the right per
physics tick while "right" is held.
"""

import pytest

from quantum.runtime.godot_replay import ReplayError, replay, tape_from_holds


def test_the_scene_runs_exactly_the_ticks_asked(godot, mover_project):
    state = replay(mover_project, ticks=30, binary=godot)
    assert state == {'.': {'ticks': 30, 'player_x': 10.0}}


def test_a_held_action_moves_the_player_for_the_held_ticks(godot, mover_project):
    tape = tape_from_holds([('right', 0, 10)])
    state = replay(mover_project, ticks=30, tape=tape, binary=godot)
    assert state['.']['player_x'] == 10.0 + 2 * 10


def test_the_same_tape_gives_the_same_state(godot, mover_project):
    tape = tape_from_holds([('right', 3, 7), ('right', 12, 25)])
    first = replay(mover_project, ticks=40, tape=tape, binary=godot)
    second = replay(mover_project, ticks=40, tape=tape, binary=godot)
    assert first == second == {'.': {'ticks': 40, 'player_x': 10.0 + 2 * (4 + 13)}}


def test_a_broken_game_is_a_replay_error(godot, mover_project):
    (mover_project / 'main.gd').write_text('extends Node2D\nfunc _ready():\n\tvar x = \n',
                                           encoding='utf-8')
    with pytest.raises(ReplayError, match='Parse Error'):
        replay(mover_project, ticks=5, binary=godot)


def test_tape_from_holds():
    assert tape_from_holds([('right', 0, 10), ('jump', 5, 10)]) == {
        0: [('right', True)],
        5: [('jump', True)],
        10: [('right', False), ('jump', False)],
    }
