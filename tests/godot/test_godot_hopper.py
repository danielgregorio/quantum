"""Hopper, the platformer that drives the game language, replayed in Godot.

projects/hopper/hopper.q is compiled into a temporary directory, opened by
Godot (no script error), and driven by input tapes: the numbers below are
what the .q promises (a 90 px/s run, a 64 px jump) and what the level is
(the ground's top is at y=180, the character's hitbox 22 px tall, so it
rests at y=169).
"""

import shutil
from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_replay import replay, tape_from_holds

HOPPER = Path(__file__).resolve().parents[2] / 'projects' / 'hopper' / 'hopper.q'
REST_Y = 169.0

# The game starts on the world map; "jump" at tick 2 enters level-1 and the
# level's first tick is tick 3. Level tapes are written in level ticks.
ENTER = 4


def level(holds, extra=()):
    """A tape that enters level-1 and then plays ``holds`` (in level ticks)."""
    return tape_from_holds([('jump', 2, 4)] + [(a, s + ENTER, e + ENTER) for a, s, e in holds] + list(extra))


@pytest.fixture(scope='module')
def hopper(godot, tmp_path_factory) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    out = tmp_path_factory.mktemp('hopper') / 'godot'
    app = QuantumParser(use_cache=False).parse_file(str(HOPPER))
    compile_game(app, str(out), source_dir=str(HOPPER.parent))
    return out


def player(state: dict) -> dict:
    return state['level-1']['nodes']['player']


def test_the_game_starts_on_the_world_map(godot, hopper):
    state = replay(hopper, 10, binary=godot)
    assert list(state) == ['map']
    walker = state['map']['nodes']['player']
    assert walker['at'] == 'level-1' and walker['going_to'] == ''
    assert state['map']['game'] == {'cleared': [], 'lives': 3, 'map_at': 'level-1', 'score': 0}


def test_a_path_that_requires_a_level_stays_shut(godot, hopper):
    state = replay(hopper, 30, tape_from_holds([('right', 2, 4)]), binary=godot)
    assert state['map']['nodes']['player']['at'] == 'level-1'
    assert state['map']['nodes']['player']['going_to'] == ''


def test_jump_on_a_map_node_enters_its_level(godot, hopper):
    state = replay(hopper, ENTER + 1, tape_from_holds([('jump', 2, 4)]), binary=godot)
    assert list(state) == ['level-1']


def test_godot_opens_the_build(godot, hopper):
    assert check_project(hopper, binary=godot) == []
    assert (hopper / 'addons' / 'quantum' / 'quantum_game.gd').is_file()
    assert (hopper / 'assets' / 'kenney' / 'tilemap_packed.png').is_file()


def test_the_character_lands_and_rests_on_the_ground(godot, hopper):
    state = replay(hopper, 90 + ENTER, level([]), binary=godot)
    assert player(state) == {'x': 40.0, 'y': REST_Y, 'state': 'small'}
    assert state['level-1']['coins'] == 0
    assert state['level-1']['game']['lives'] == 3
    assert state['level-1']['things'] == {
        'coin': 2, 'enemy': 1, 'qblock': 1, 'checkpoint': 1, 'spikes': 1, 'flag': 1}


def test_running_covers_run_speed_pixels_per_second(godot, hopper):
    # 60 ticks held = one second at 90 px/s
    state = replay(hopper, 90 + ENTER, level([('right', 0, 60)]), binary=godot)
    assert player(state)['x'] == pytest.approx(40 + 90, abs=0.5)


# The block sits right above the start: step left out from under it first.
CLEAR_OF_THE_BLOCK = [('left', 0, 14)]


def test_a_held_jump_peaks_at_jump_height(godot, hopper):
    # pressed at tick 30, once the character has landed; the apex comes ~23 ticks later
    tape = level(CLEAR_OF_THE_BLOCK + [('jump', 30, 90)])
    heights = [REST_Y - player(replay(hopper, t + ENTER, tape, binary=godot))['y'] for t in (50, 52, 53, 54, 56)]
    assert max(heights) == pytest.approx(64, abs=1)


def test_a_tapped_jump_is_a_short_hop(godot, hopper):
    tape = level(CLEAR_OF_THE_BLOCK + [('jump', 30, 34)])
    heights = [REST_Y - player(replay(hopper, t + ENTER, tape, binary=godot))['y'] for t in (38, 40, 42, 45)]
    assert 15 < max(heights) < 40


def test_walking_through_a_coin_collects_it(godot, hopper):
    state = replay(hopper, 120 + ENTER, level([('right', 0, 120)]), binary=godot)
    assert state['level-1']['coins'] == 1
    assert state['level-1']['things']['coin'] == 1


def test_the_same_tape_gives_the_same_game(godot, hopper):
    tape = level([('right', 0, 50), ('jump', 30, 40), ('left', 70, 100)])
    assert replay(hopper, 110 + ENTER, tape, binary=godot) == replay(hopper, 110 + ENTER, tape, binary=godot)


def test_the_build_replaces_an_earlier_build_only(godot, hopper, tmp_path):
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import GameCompileError, compile_game
    app = QuantumParser(use_cache=False).parse_file(str(HOPPER))
    stranger = tmp_path / 'mine'
    stranger.mkdir()
    (stranger / 'notes.txt').write_text('mine')
    with pytest.raises(GameCompileError, match='not a Quantum build'):
        compile_game(app, str(stranger), source_dir=str(HOPPER.parent))
    again = tmp_path / 'again'
    shutil.copytree(hopper, again)
    (again / 'scripts' / 'stale.gd').write_text('extends Node\n')
    compile_game(app, str(again), source_dir=str(HOPPER.parent))
    assert not (again / 'scripts' / 'stale.gd').exists()


# --- the walker: stomp it, or be hurt by it ---

def test_walking_into_the_walker_hurts_once_and_respawns(godot, hopper):
    # The walker starts at x=200 walking left; held right, the character meets it
    # around tick 75 and is sent back to its start, one life down, once (cooldown).
    state = replay(hopper, 90 + ENTER, level([('right', 0, 90)]), binary=godot)
    s = state['level-1']
    assert s['game']['lives'] == 2
    assert s['sounds'].count('hurt') == 1
    assert s['things']['enemy'] == 1
    assert player(state)['x'] < 100   # respawned at x=40, walked on since


def test_landing_on_the_walker_stomps_it(godot, hopper):
    state = replay(hopper, 140 + ENTER, level([('right', 0, 140), ('jump', 52, 72)]), binary=godot)
    s = state['level-1']
    assert s['things'].get('enemy', 0) == 0
    assert s['game']['score'] == 10 + 100   # the coin on the way, and the stomp
    assert s['game']['lives'] == 3
    assert s['sounds'] == ['coin', 'jump', 'stomp']


def test_falling_into_the_pit_costs_a_life(godot, hopper):
    # Stomp the walker, keep going: the pit is at columns 13-14.
    state = replay(hopper, 300 + ENTER, level([('right', 0, 300), ('jump', 52, 72)]), binary=godot)
    s = state['level-1']
    assert s['game']['lives'] == 2
    assert s['sounds'][-1] == 'hurt'
    assert player(state)['y'] == pytest.approx(REST_Y, abs=1)   # back on the ground


# --- the block, the power-up, the states ---

def test_bumping_the_block_from_below_opens_it_and_spawns_the_power_up(godot, hopper):
    # The block is right above the start; a jump at tick 30 hits it from below.
    s = replay(hopper, 50 + ENTER, level([('jump', 30, 50)]), binary=godot)['level-1']
    assert s['things'].get('qblock', 0) == 0
    assert s['things']['usedblock'] == 1
    assert s['things']['shroom'] == 1
    assert s['sounds'] == ['jump', 'block']


def test_the_power_up_makes_the_character_big_and_a_hit_makes_it_small_again(godot, hopper):
    tape = level([('jump', 30, 50), ('right', 60, 300)])
    big = replay(hopper, 110 + ENTER, tape, binary=godot)['level-1']
    assert big['nodes']['player']['state'] == 'big'
    assert big['game']['score'] == 50 + 10   # the power-up, then the coin
    assert big['things'].get('shroom', 0) == 0
    hit = replay(hopper, 130 + ENTER, tape, binary=godot)['level-1']
    assert hit['nodes']['player']['state'] == 'small'
    assert hit['game']['lives'] == 3            # big took the hit
    assert hit['sounds'][-1] == 'hurt'
    assert hit['nodes']['player']['x'] > 100   # not sent back to the start


# --- the checkpoint, the spikes, the flag ---

CROSS_THE_PIT = [('jump', 30, 50), ('right', 60, 335), ('jump', 176, 200)]
TO_THE_FLAG = CROSS_THE_PIT + [('jump', 284, 309)]


def test_the_checkpoint_is_where_the_spikes_send_you_back(godot, hopper):
    taken = replay(hopper, 240 + ENTER, level(CROSS_THE_PIT), binary=godot)['level-1']
    assert taken['things']['checkpoint-on'] == 1 and taken['things'].get('checkpoint', 0) == 0
    assert taken['game']['lives'] == 3
    hurt = replay(hopper, 275 + ENTER, level(CROSS_THE_PIT), binary=godot)['level-1']
    assert hurt['game']['lives'] == 2
    assert hurt['sounds'][-1] == 'hurt'
    assert 297 <= hurt['nodes']['player']['x'] <= 340   # respawned at the checkpoint (x=297), walking on


def test_reaching_the_flag_wins_the_level_and_opens_the_next_on_the_map(godot, hopper):
    state = replay(hopper, 345, level(TO_THE_FLAG), binary=godot)
    assert list(state) == ['map']
    s = state['map']
    assert s['game']['cleared'] == ['level-1']
    assert s['game']['score'] == 50 + 10 + 500
    assert s['game']['lives'] == 2
    assert s['sounds'][-1] == 'win'
    assert s['nodes']['player']['at'] == 'level-1'
    # the path to level-2 is open now: right walks there, jump enters it
    walking = replay(hopper, 370, level(TO_THE_FLAG, [('right', 360, 362)]), binary=godot)
    assert walking['map']['nodes']['player']['going_to'] == 'level-2'
    entered = replay(hopper, 470, level(TO_THE_FLAG, [('right', 360, 362), ('jump', 460, 462)]), binary=godot)
    assert list(entered) == ['level-2']
    assert entered['level-2']['game']['map_at'] == 'level-2'


def test_level_two_is_a_tiled_map_whose_objects_are_the_things(godot, hopper):
    entered = replay(hopper, 470, level(TO_THE_FLAG, [('right', 360, 362), ('jump', 460, 462)]), binary=godot)
    s = entered['level-2']
    assert s['things'] == {'coin': 3, 'enemy': 2, 'flag': 1, 'ledge': 1, 'lift': 1}
    assert s['nodes']['player']['x'] == 40.0


def test_three_deaths_are_game_over_and_jump_starts_again(godot, hopper):
    over = replay(hopper, 500, level([('right', 10, 500)]), binary=godot)
    assert list(over) == ['game-over']
    assert over['game-over']['game']['lives'] == 0
    assert over['game-over']['sounds'].count('hurt') == 3
    again = replay(hopper, 530, level([('right', 10, 500), ('jump', 520, 522)]), binary=godot)
    assert list(again) == ['map']
    assert again['map']['game'] == {'cleared': [], 'lives': 3, 'map_at': 'level-1', 'score': 0}


# --- the clock, the keys, the ledge and the lift ---

def test_the_clock_loses_a_second_every_sixty_ticks(godot, hopper):
    state = replay(hopper, 120 + ENTER, level([('right', 0, 120)]), binary=godot)
    assert state['level-1']['time'] == 97


def test_the_jump_keys_are_the_games_own(godot, hopper):
    import json
    data = json.loads((hopper / 'game.json').read_text())
    assert data['inputs']['jump'] == ['Space', 'Z', 'X', 'Up', 'W']
    assert data['inputs']['right'] == ['Right', 'D']


IN_LEVEL_2 = [('right', 360, 362), ('jump', 460, 462)]


def test_a_one_way_ledge_is_jumped_through_from_below_and_stood_on(godot, hopper):
    tape = level(TO_THE_FLAG, IN_LEVEL_2 + [('right', 470, 500), ('jump', 505, 525)])
    below = replay(hopper, 500, tape, binary=godot)['level-2']
    assert below['nodes']['player']['y'] == pytest.approx(REST_Y, abs=0.5)   # walked under it
    on_it = replay(hopper, 560, tape, binary=godot)['level-2']
    assert on_it['nodes']['player'] == {'x': 84.98, 'y': 130.0}   # the ledge's top is at y=141


def test_the_lift_carries_whoever_stands_on_it(godot, hopper):
    tape = level(TO_THE_FLAG, IN_LEVEL_2 + [('right', 470, 500), ('jump', 505, 525), ('right', 700, 730)])
    low = replay(hopper, 735, tape, binary=godot)['level-2']
    high = replay(hopper, 830, tape, binary=godot)['level-2']
    lift = {w[0]: w for w in high['where']}['lift']
    assert high['nodes']['player']['x'] == low['nodes']['player']['x']    # standing still on it
    assert high['nodes']['player']['y'] < low['nodes']['player']['y'] - 30   # carried up
    assert high['nodes']['player']['y'] == pytest.approx(lift[2] - 4 - 11, abs=1)   # on its top
