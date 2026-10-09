"""Keep, the top-down adventure that drives the game language, replayed in Godot.

projects/keep/keep.q is compiled into a temporary directory, opened by
Godot and driven by input tapes through its six rooms. The tick numbers
are what the rooms are: the character walks 70 px/s (1.17 px per tick),
rooms are 252 px wide, exits sit in the walls.
"""

from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_replay import replay, tape_from_holds

KEEP = Path(__file__).resolve().parents[2] / 'projects' / 'keep' / 'keep.q'


@pytest.fixture(scope='module')
def keep(godot, tmp_path_factory) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    out = tmp_path_factory.mktemp('keep') / 'godot'
    app = QuantumParser(use_cache=False).parse_file(str(KEEP))
    compile_game(app, str(out), source_dir=str(KEEP.parent))
    return out


def scene(state: dict) -> str:
    return list(state)[0]


def player(state: dict) -> dict:
    return state[scene(state)]['nodes']['player']


def game(state: dict) -> dict:
    return state[scene(state)]['game']


# Room 1 to room 2 (right), then the bat of room 2 comes and is cut down.
TO_ROOM_2 = [('right', 0, 272)]
CUT_THE_BAT = TO_ROOM_2 + [('jump', 365, 367)]
# ...south to room 4, the switch, the bat there; north again, up to room 3
# for the heart and the key; back to room 2 and east through the door, the
# opened gate of room 5, to the chest of room 6.
THE_WHOLE_KEEP = CUT_THE_BAT + [
    ('down', 375, 467), ('down', 470, 599), ('jump', 605, 607), ('left', 652, 653), ('jump', 656, 658),
    ('up', 665, 805), ('up', 810, 1005), ('up', 1010, 1163), ('left', 1170, 1247), ('down', 1250, 1313),
    ('right', 1320, 1389), ('down', 1395, 1503), ('down', 1505, 1595), ('right', 1600, 2250)]


def test_godot_opens_the_build(godot, keep):
    assert check_project(keep, binary=godot) == []


def test_the_game_starts_in_room_one(godot, keep):
    state = replay(keep, 30, binary=godot)
    assert scene(state) == 'room-1'
    assert player(state) == {'x': 60.0, 'y': 108.0, 'facing': [0, 1]}
    assert state['room-1']['things'] == {'enemy': 1, 'sign': 1}
    assert game(state) == {'hearts': 3, 'keys': 0, 'taken': [], 'opened': [], 'message': ''}


def test_the_slime_wanders_the_same_way_from_the_same_seed(godot, keep):
    at_100 = replay(keep, 100, binary=godot)['room-1']['named']['slime-1']
    at_200 = replay(keep, 200, binary=godot)['room-1']['named']['slime-1']
    assert at_100 != {'x': 180.0, 'y': 150.0} and at_200 != at_100
    assert replay(keep, 200, binary=godot) == replay(keep, 200, binary=godot)


def test_walking_into_an_exit_changes_room_and_arrives_at_the_matching_exit(godot, keep):
    state = replay(keep, 200, tape_from_holds(TO_ROOM_2), binary=godot)
    assert scene(state) == 'room-2'
    # arrived at room 2's west exit (x=0, y=117) around tick 160 and kept walking
    assert player(state)['y'] == 117.0
    assert 30 < player(state)['x'] < 60
    assert replay(keep, 230, tape_from_holds(TO_ROOM_2), binary=godot) and scene(state) == 'room-2'


def test_the_bat_chases_within_sight_and_hurts_once_per_cooldown(godot, keep):
    before = replay(keep, 300, tape_from_holds(TO_ROOM_2), binary=godot)['room-2']
    assert before['named']['bat-1'] != {'x': 190.0, 'y': 60.0}
    assert before['game']['hearts'] == 3
    first = replay(keep, 365, tape_from_holds(TO_ROOM_2), binary=godot)['room-2']
    assert first['game']['hearts'] == 2 and first['sounds'].count('hurt') == 1
    second = replay(keep, 430, tape_from_holds(TO_ROOM_2), binary=godot)['room-2']
    assert second['game']['hearts'] == 1 and second['sounds'].count('hurt') == 2


def test_the_swing_cuts_down_the_bat_that_sits_on_you(godot, keep):
    state = replay(keep, 380, tape_from_holds(CUT_THE_BAT), binary=godot)['room-2']
    assert state['things'] == {'door': 1}
    assert state['sounds'][-2:] == ['hurt', 'hit']
    assert state['game']['hearts'] == 2


def test_the_switch_in_room_four_opens_the_gate_of_room_five(godot, keep):
    state = replay(keep, 615, tape_from_holds(THE_WHOLE_KEEP), binary=godot)['room-4']
    assert state['game']['opened'] == ['gate-1']
    assert state['things'] == {'enemy': 1, 'switch-on': 1}
    assert state['game']['message'] == 'SOMETHING OPENED FAR AWAY.'


def test_the_gate_stands_until_the_switch_is_thrown(godot, keep):
    key_only = TO_ROOM_2 + [('up', 280, 383), ('up', 400, 510), ('down', 520, 650),
                            ('down', 660, 736), ('right', 740, 1100)]
    state = replay(keep, 1000, tape_from_holds(key_only), binary=godot)['room-5']
    assert state['things']['gate'] == 2
    assert state['nodes']['player']['x'] == 155.0   # against the gate
    assert state['game']['message'] == 'A GATE. A SWITCH MUST OPEN IT.'


def test_the_key_opens_the_door(godot, keep):
    before = replay(keep, 1600, tape_from_holds(THE_WHOLE_KEEP), binary=godot)['room-2']
    assert before['game']['keys'] == 1 and before['things']['door'] == 1
    after = replay(keep, 1670, tape_from_holds(THE_WHOLE_KEEP), binary=godot)['room-2']
    assert after['game']['keys'] == 0
    assert after['game']['opened'] == ['gate-1', 'door-1']
    assert 'door' not in after['things']
    assert after['sounds'][-1] == 'open'


def test_the_heart_and_the_key_are_taken_once(godot, keep):
    state = replay(keep, 1392, tape_from_holds(THE_WHOLE_KEEP), binary=godot)['room-3']
    assert sorted(state['game']['taken']) == ['heart-1', 'key-1']   # the key is on the way up to the heart
    assert state['things'] == {'enemy': 1}


def test_the_chest_ends_the_game(godot, keep):
    state = replay(keep, 2100, tape_from_holds(THE_WHOLE_KEEP), binary=godot)
    assert scene(state) == 'the-end'
    assert game(state)['message'] == 'THE TREASURE OF THE KEEP IS YOURS.'
    assert game(state)['hearts'] == 2
    assert state['the-end']['sounds'][-1] == 'win'


def test_three_hurts_are_game_over_and_jump_starts_again(godot, keep):
    over = replay(keep, 520, tape_from_holds(TO_ROOM_2), binary=godot)
    assert scene(over) == 'game-over'
    assert game(over)['hearts'] == 0
    again = replay(keep, 560, tape_from_holds(TO_ROOM_2 + [('jump', 540, 542)]), binary=godot)
    assert scene(again) == 'room-1'
    assert game(again) == {'hearts': 3, 'keys': 0, 'taken': [], 'opened': [], 'message': ''}
