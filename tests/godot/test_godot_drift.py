"""Drift, the vertical shooter that drives the game language, replayed in Godot.

projects/drift/drift.q is compiled into a temporary directory, opened by
Godot and driven by one tape: the ship sweeps 40 px each way around the
centre, dwelling at each end so its last shot column stands at the
extreme, firing all along. The waves come from the scene's seed, so the
run is the same run every time.
"""

from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_replay import replay, tape_from_holds

DRIFT = Path(__file__).resolve().parents[2] / 'projects' / 'drift' / 'drift.q'


def sweep(until: int = 4500):
    holds = [('jump', 0, until), ('left', 0, 20)]
    t = 20
    for i in range(60):
        holds.append((('right' if i % 2 == 0 else 'left'), t, t + 40))
        t += 48
    return tape_from_holds(holds)


SWEEP = sweep()


@pytest.fixture(scope='module')
def drift(godot, tmp_path_factory) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    out = tmp_path_factory.mktemp('drift') / 'godot'
    app = QuantumParser(use_cache=False).parse_file(str(DRIFT))
    compile_game(app, str(out), source_dir=str(DRIFT.parent))
    return out


def scene(state: dict) -> str:
    return list(state)[0]


def test_godot_opens_the_build(godot, drift):
    assert check_project(drift, binary=godot) == []
    assert 'P="*res://scripts/prefabs.gd"' in (drift / 'project.godot').read_text()


def test_the_waves_come_from_the_seed_the_same_way_every_run(godot, drift):
    first = replay(drift, 300, binary=godot)
    assert scene(first) == 'play'
    assert first['play']['things'] == {'enemy': 7}           # wave 1: a drone every 40 ticks from tick 60
    assert first['play']['nodes']['ship'] == {'x': 128.0, 'y': 196.0}
    assert first == replay(drift, 300, binary=godot)


def test_shots_kill_drones_and_the_score_counts(godot, drift):
    state = replay(drift, 500, SWEEP, binary=godot)['play']
    assert state['game']['score'] == 500          # five drones, 100 each
    assert state['game']['lives'] == 3
    assert state['things']['shot'] > 0
    assert state['sounds'].count('boom') == 5


def test_tanks_take_three_hits_and_shoot_back(godot, drift):
    state = replay(drift, 900, SWEEP, binary=godot)['play']
    assert state['game']['score'] == 800          # ...and a tank, 300
    assert 'enemy-shot' in state['things']        # the tanks outside the sweep shoot down
    assert state['sounds'].count('hit') == 2      # the tank's on-damage: the first two hits; the third is its death
    assert state['sounds'].count('boom') == 6     # five drones and the tank


def test_drones_that_get_through_cost_lives(godot, drift):
    # Not shooting, not moving: the drones that come down the middle hit the ship.
    state = replay(drift, 1000, binary=godot)
    assert scene(state) == 'play'
    assert state['play']['game']['lives'] == 1
    assert state['play']['sounds'].count('hurt') == 2


def test_the_boss_sways_turns_angry_and_its_death_wins(godot, drift):
    # spawned at tick 1500 at (128, 40), right over the sweep: calm at first, angry within a hundred ticks
    arrived = replay(drift, 1520, SWEEP, binary=godot)['play']
    boss = [w for w in arrived['where'] if w[0] == 'boss']
    assert len(boss) == 1 and boss[0][2] == 40.0 and boss[0][3] == 'calm'
    later = replay(drift, 1600, SWEEP, binary=godot)['play']
    boss = [w for w in later['where'] if w[0] == 'boss']
    assert len(boss) == 1 and boss[0][3] == 'angry'
    assert boss[0][1] != 128.0   # it sways
    won = replay(drift, 2000, SWEEP, binary=godot)
    assert scene(won) == 'victory'
    assert won['victory']['game']['score'] == 6800
    assert won['victory']['game']['lives'] == 2
    assert won['victory']['sounds'][-1] == 'win'


def test_the_high_score_survives_into_the_next_run(godot, drift, tmp_path):
    persist = tmp_path / 'saved'
    won = replay(drift, 2000, SWEEP, binary=godot, persist_dir=persist)
    assert won['victory']['game']['high_score'] == 6800
    assert (persist / 'quantum-state.json').is_file()
    fresh = replay(drift, 10, binary=godot, persist_dir=persist)
    assert fresh['play']['game'] == {'score': 0, 'lives': 3, 'high_score': 6800}
    assert replay(drift, 10, binary=godot)['play']['game']['high_score'] == 0   # another run starts from nothing


def test_three_lives_lost_are_game_over_and_jump_starts_again(godot, drift):
    over = replay(drift, 1400, binary=godot)
    assert scene(over) == 'game-over'
    assert over['game-over']['game']['lives'] == 0
    again = replay(drift, 1430, tape_from_holds([('jump', 1410, 1412)]), binary=godot)
    assert scene(again) == 'play'
    assert again['play']['game']['lives'] == 3 and again['play']['game']['score'] == 0
