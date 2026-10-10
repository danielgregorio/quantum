"""RPG — Godot's "JRPG" demo, transcribed — replayed in Godot.

projects/rpg/rpg.q is compiled and driven by input tapes. The numbers are
the demo's: 64 px cells, a step and a bump of 0.25 s (15 ticks), the player
at cell (3, 4), the key at (8, 4), the opponent at (12, 7). In the fight the
player has 10 life, 2 damage, 1 defense and 1 armor; the opponent 7 life,
3 damage, 1 defense and no armor, and hits a quarter of a second into its
turn. A hit takes the damage less the armor.
"""

import shutil
from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_replay import replay, tape_from_holds

RPG = Path(__file__).resolve().parents[2] / 'projects' / 'rpg' / 'rpg.q'
# down three cells, then right to (11, 7), and one more step: into the opponent
TO_THE_OPPONENT = [('down', 1, 40), ('right', 50, 180)]
TALK = [('select', 200, 201), ('select', 215, 216), ('select', 230, 231)]   # its three lines: the fight


@pytest.fixture(scope='module')
def project(godot, tmp_path_factory) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    src_dir = tmp_path_factory.mktemp('rpg')
    shutil.copytree(RPG.parent, src_dir / 'rpg', ignore=shutil.ignore_patterns('godot'))
    app = QuantumParser(use_cache=False).parse_file(str(src_dir / 'rpg' / 'rpg.q'))
    out = compile_game(app, str(src_dir / 'godot'), source_dir=str(src_dir / 'rpg'))
    assert check_project(Path(out), binary=godot) == []
    return Path(out)


def play(project, ticks, holds=()):
    state = replay(project, ticks, tape=tape_from_holds(list(holds)) if holds else None)
    assert len(state) == 1
    name, scene = next(iter(state.items()))
    scene['scene'] = name
    return scene


def player(state):
    return state['nodes']['player']


def test_the_player_steps_a_cell_in_a_quarter_of_a_second(project):
    start = play(project, 5)
    assert (player(start)['col'], player(start)['row']) == (3, 4)
    assert (player(start)['x'], player(start)['y']) == (224.0, 288.0)          # the cell's centre, as in the demo
    assert player(play(project, 9, [('right', 1, 3)]))['x'] == pytest.approx(224.0 + 64 * 7 / 15, abs=0.01)
    one = play(project, 30, [('right', 1, 3)])
    assert (player(one)['x'], player(one)['col']) == (288.0, 4)                # released: one cell, no more
    # held: a step after the other, each read on the tick after the last one ends, as the demo's tween
    held = play(project, 33, [('right', 1, 60)])
    assert (player(held)['x'], player(held)['col']) == (352.0, 5)
    assert player(play(project, 60, [('right', 1, 60)]))['col'] == 5            # then the rocks at (6, 4)


def test_two_directions_step_diagonally(project):
    state = play(project, 20, [('right', 1, 3), ('down', 1, 3)])
    assert (player(state)['col'], player(state)['row']) == (4, 5)


def test_a_wall_is_a_bump_that_takes_as_long_as_a_step(project):
    # up from (3, 4): (3, 3), (3, 2), (3, 1), then the wall of row 0
    state = play(project, 80, [('up', 1, 80)])
    assert (player(state)['col'], player(state)['row']) == (3, 1)
    assert player(state)['y'] == 96.0 and 'talking' not in state


def test_the_key_says_what_it_is_and_is_taken(project):
    # (3, 4) down to row 7, right to column 11, up the gap of the rocks to row 4, left into the key at (8, 4)
    walk = [('down', 1, 40), ('right', 50, 165), ('up', 180, 215), ('left', 230, 265)]
    state = play(project, 275, walk)
    assert (player(state)['col'], player(state)['row']) == (9, 4)
    assert state['talking'] == 'key' and state['paused'] is True
    assert 'key' not in state['things'] and state['game']['keys'] == 1        # beyond the demo: it is taken
    assert state['game']['taken'] == ['key']
    closed = play(project, 310, walk + [('select', 285, 286), ('select', 300, 301)])
    assert 'talking' not in closed and 'paused' not in closed


# Beyond the demo: two potions on the map, and a Potion button in the fight.
TO_THE_POTION = [('up', 1, 45), ('left', 50, 70)]           # (3, 4) up to (3, 1), left to (2, 1), into (1, 1)


def test_a_potion_is_picked_up(project):
    state = play(project, 80, TO_THE_POTION)
    assert state['talking'] == 'potion' and state['game']['potions'] == 1
    assert state['things'] == {'key': 1, 'opponent': 1, 'potion': 1}           # the other one, at (14, 9)


def test_a_potion_gives_back_five_life_up_to_ten_in_the_fight(project):
    # from (2, 1): right to (11, 1), down to (11, 7), into the opponent; its three lines; the fight
    to_fight = TO_THE_POTION + [('select', 90, 91), ('right', 100, 235), ('down', 240, 330), ('right', 340, 345),
                                ('select', 360, 361), ('select', 375, 376), ('select', 390, 391)]
    fight = play(project, 395, to_fight)
    assert fight['scene'] == 'combat' and fight['game']['potions'] == 1
    hit = to_fight + [('select', 400, 401)]                                     # Attack; the answer: 8 life
    assert play(project, 425, hit)['life'] == 8
    drunk = play(project, 445, hit + [('down', 428, 429), ('down', 432, 433), ('select', 440, 441)])
    assert (drunk['life'], drunk['game']['potions'], drunk['turn']) == (10, 0, 'opponent')   # 8 + 5, at most 10


def test_the_opponent_talks_three_lines_then_fights(project):
    state = play(project, 190, TO_THE_OPPONENT)
    assert (player(state)['col'], player(state)['row']) == (11, 7)             # it stepped into it: no move
    assert state['talking'] == 'npc' and state['line'] == 0
    assert state['game']['back_col'] == 11 and state['game']['back_row'] == 7
    assert play(project, 220, TO_THE_OPPONENT + TALK[:2])['line'] == 2
    fight = play(project, 240, TO_THE_OPPONENT + TALK)
    assert fight['scene'] == 'combat'
    assert (fight['life'], fight['foe_life'], fight['turn']) == (10, 7, 'player')


def test_an_attack_and_the_answer_a_quarter_second_later(project):
    attacked = play(project, 252, TO_THE_OPPONENT + TALK + [('select', 250, 251)])
    assert (attacked['foe_life'], attacked['turn']) == (5, 'opponent')         # 2 damage, no armor
    answered = play(project, 270, TO_THE_OPPONENT + TALK + [('select', 250, 251)])
    assert (answered['life'], answered['turn']) == (8, 'player')               # 3 damage less 1 armor


def test_a_fighter_just_hit_makes_a_face_for_half_a_second(project):
    attack = [('select', 250, 251)]
    hit = play(project, 255, TO_THE_OPPONENT + TALK + attack)
    assert (hit['foe_hurt'], hit['hurt']) == (25, 0)                           # 30 from the hit, a tick after the press
    answered = play(project, 270, TO_THE_OPPONENT + TALK + attack)
    assert answered['hurt'] > 0 and answered['foe_hurt'] > 0
    assert play(project, 320, TO_THE_OPPONENT + TALK + attack)['hurt'] == 0


def test_defending_adds_armor_for_one_hit(project):
    state = play(project, 300, TO_THE_OPPONENT + TALK + [('down', 248, 249), ('select', 250, 251)])
    assert state['life'] == 9 and state['armor'] == 1                          # 3 less 2; back to 1 on its turn


def test_four_attacks_win_and_the_opponent_says_so_on_the_map(project):
    attacks = [('select', t, t + 1) for t in (250, 280, 310, 340)]
    state = play(project, 360, TO_THE_OPPONENT + TALK + attacks)
    assert state['scene'] == 'exploration'
    assert (player(state)['col'], player(state)['row']) == (11, 7)             # where it started the fight
    assert state['talking'] == 'won' and state['game']['outcome'] == 'won'
    after = play(project, 380, TO_THE_OPPONENT + TALK + attacks + [('select', 370, 371)])
    assert 'talking' not in after and after['game']['outcome'] == ''


def test_fleeing_loses(project):
    flee = [('down', 248, 249), ('down', 252, 253), ('select', 256, 257)]      # Attack, Defend, Flee
    state = play(project, 270, TO_THE_OPPONENT + TALK + flee)
    assert state['scene'] == 'exploration' and state['talking'] == 'lost'
