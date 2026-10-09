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


def test_godot_opens_the_build(godot, hopper):
    assert check_project(hopper, binary=godot) == []
    assert (hopper / 'addons' / 'quantum' / 'quantum_game.gd').is_file()
    assert (hopper / 'assets' / 'kenney' / 'tilemap_packed.png').is_file()


def test_the_character_lands_and_rests_on_the_ground(godot, hopper):
    state = replay(hopper, 90, binary=godot)
    assert player(state) == {'x': 40.0, 'y': REST_Y}
    assert state['level-1']['coins'] == 0
    assert state['level-1']['things'] == {'coin': 2, 'enemy': 1}


def test_running_covers_run_speed_pixels_per_second(godot, hopper):
    # 60 ticks held = one second at 90 px/s
    state = replay(hopper, 90, tape_from_holds([('right', 0, 60)]), binary=godot)
    assert player(state)['x'] == pytest.approx(40 + 90, abs=0.5)


def test_a_held_jump_peaks_at_jump_height(godot, hopper):
    # pressed at tick 30, once the character has landed; the apex comes ~23 ticks later
    heights = [REST_Y - player(replay(hopper, t, tape_from_holds([('jump', 30, 90)]), binary=godot))['y']
               for t in (50, 52, 53, 54, 56)]
    assert max(heights) == pytest.approx(64, abs=1)


def test_a_tapped_jump_is_a_short_hop(godot, hopper):
    heights = [REST_Y - player(replay(hopper, t, tape_from_holds([('jump', 30, 34)]), binary=godot))['y']
               for t in (38, 40, 42, 45)]
    assert 15 < max(heights) < 40


def test_walking_through_a_coin_collects_it(godot, hopper):
    state = replay(hopper, 120, tape_from_holds([('right', 0, 120)]), binary=godot)
    assert state['level-1']['coins'] == 1
    assert state['level-1']['things']['coin'] == 1


def test_the_same_tape_gives_the_same_game(godot, hopper):
    tape = tape_from_holds([('right', 0, 50), ('jump', 30, 40), ('left', 70, 100)])
    assert replay(hopper, 110, tape, binary=godot) == replay(hopper, 110, tape, binary=godot)


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
    state = replay(hopper, 90, tape_from_holds([('right', 0, 90)]), binary=godot)
    s = state['level-1']
    assert s['lives'] == 2
    assert s['sounds'].count('hurt') == 1
    assert s['things']['enemy'] == 1
    assert player(state)['x'] < 100   # respawned at x=40, walked on since


def test_landing_on_the_walker_stomps_it(godot, hopper):
    state = replay(hopper, 140, tape_from_holds([('right', 0, 140), ('jump', 52, 72)]), binary=godot)
    s = state['level-1']
    assert s['things'].get('enemy', 0) == 0
    assert s['score'] == 10 + 100   # the coin on the way, and the stomp
    assert s['lives'] == 3
    assert s['sounds'] == ['coin', 'jump', 'stomp']


def test_falling_into_the_pit_costs_a_life(godot, hopper):
    # Stomp the walker, keep going: the pit is at columns 13-14.
    state = replay(hopper, 300, tape_from_holds([('right', 0, 300), ('jump', 52, 72)]), binary=godot)
    s = state['level-1']
    assert s['lives'] == 2
    assert s['sounds'][-1] == 'hurt'
    assert player(state)['y'] == pytest.approx(REST_Y, abs=1)   # back on the ground
