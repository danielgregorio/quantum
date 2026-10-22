"""Rally — two cars round a circuit wider than the screen, split in two — played in Godot.

projects/rally/rally.q is compiled and driven: each car has a view of its own (qg:camera player=), the barrier
holds the grid until the green light, a lap counts at the line only after halfway round, the first to finish
the laps wins, and over the network both machines run the same race.
"""

from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_play import PlaySession
from quantum.runtime.godot_replay import replay_peers, tape_from_holds

RALLY = Path(__file__).resolve().parents[2] / 'projects' / 'rally' / 'rally.q'
# one lap for red, from the grid: each leg held until the car is where the next begins
LAP = [('right', 'red.x >= 888'), ('down', 'red.y >= 472'), ('left', 'red.x <= 616'), ('up', 'red.y <= 280'),
       ('left', 'red.x <= 360'), ('down', 'red.y >= 472'), ('left', 'red.x <= 72'), ('up', 'red.y <= 56'),
       ('right', 'red.x >= 500')]


def _project(godot, tmp_path_factory, laps=None) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    out_dir = tmp_path_factory.mktemp('rally')
    source = RALLY
    if laps is not None:   # the same race, shorter; its pictures and its circuit where they are
        source = out_dir / 'rally.q'
        source.write_text(RALLY.read_text(encoding='utf-8').replace(
            '<q:set name="race_laps" value="3"', f'<q:set name="race_laps" value="{laps}"'), encoding='utf-8')
    app = QuantumParser(use_cache=False).parse_file(str(source))
    out = compile_game(app, str(out_dir / 'godot'), source_dir=str(RALLY.parent))
    assert check_project(Path(out), binary=godot) == []
    return Path(out)


@pytest.fixture(scope='module')
def rally(godot, tmp_path_factory) -> Path:
    return _project(godot, tmp_path_factory)


@pytest.fixture(scope='module')
def one_lap(godot, tmp_path_factory) -> Path:
    return _project(godot, tmp_path_factory, laps=1)


def _race(game):
    """From the title to the race (two players, one keyboard): the tick the race began on."""
    seen = game.act(tap=['select'], ticks=40)
    assert seen['scene'] == 'race'
    return next(e['tick'] for e in seen['events'] if e['kind'] == 'scene')


def _lap(game, start):
    """Red's lap, leg by leg; the legs as holds, in the race's own ticks."""
    holds = []
    for key, cond in LAP:
        begin = game.observe()['tick']
        seen = game.until([cond, 'changed scene'], hold=[key], max_ticks=900)   # the last lap ends the race
        assert seen['stopped'] == 'condition', (key, cond, seen['state']['nodes'].get('red'))
        holds.append((key, begin - start, seen['tick'] - start))
    return holds, seen


def views(obs):
    return {v['player']: v for v in obs['screen'] if v['kind'] == 'camera'}


def hud(obs):
    return [i for v in obs['screen'] if v['kind'] == 'hud' for i in v['items']]


def test_each_car_has_a_view_of_its_own(rally, godot):
    with PlaySession(rally, binary=godot) as game:
        _race(game)
        seen = game.act(ticks=1)
        cars, seen_by = seen['state']['nodes'], views(seen)
        assert sorted(seen_by) == [1, 2]
        assert seen_by[1]['x'] == cars['red']['x'] and seen_by[2]['x'] == cars['blue']['x']
        assert 'RED  LAP 1/3' in hud(seen) and 'BLUE  LAP 1/3' in hud(seen)


def test_the_barrier_holds_the_grid_until_the_green_light(rally, godot):
    with PlaySession(rally, binary=godot) as game:
        start = _race(game)
        held = game.act(hold=['right'], ticks=150 - (game.observe()['tick'] - start))
        assert held['state']['nodes']['red']['x'] < 460                     # against the barrier
        off = game.act(hold=['right'], ticks=120)
        assert off['state']['nodes']['red']['x'] > 500                       # it lifted at tick 210
        assert any(e['kind'] == 'destroy' for e in off['events'])


def test_a_lap_counts_only_after_halfway(rally, godot):
    with PlaySession(rally, binary=godot) as game:
        start = _race(game)
        game.until('red.x >= 520', hold=['right'], max_ticks=600)          # over the line at the start
        back = game.until('red.x <= 440', hold=['left'], max_ticks=300)    # and back over it
        game.until('red.x >= 520', hold=['right'], max_ticks=300)          # and over it again
        assert game.observe()['state']['laps'] == [0, 0]                     # never halfway: no lap
        assert back['stopped'] == 'condition'
        game.until('red.y <= 56', hold=['left'], max_ticks=300)
        _, seen = _lap(game, start)
        assert seen['state']['laps'] == [1, 0] and 'RED  LAP 2/3' in hud(seen)


def test_the_first_to_finish_wins_and_the_network_runs_the_same_race(one_lap, godot):
    with PlaySession(one_lap, binary=godot) as game:
        start = _race(game)
        holds, seen = _lap(game, start)
        flag = game.until("scene == 'flag'", max_ticks=120)
        assert 'RED WINS' in hud(flag)
    # the same lap over the network: red on one machine, blue (standing still) on the other
    end = holds[-1][2] + 60
    states = replay_peers(one_lap, end, [tape_from_holds(holds), {}], binary=godot)
    assert states[0] == states[1]
    assert 'flag' in states[0]
