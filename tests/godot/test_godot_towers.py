"""Towers — the Godot 4 Tower Defense Template, transcribed — replayed in Godot.

projects/towers/towers.q is compiled and driven by input tapes: the cursor
("cursor" events, as a mouse would), select, and the buy keys. The numbers
are the template's: 100 gold, a 50-gold gatling that shoots every half
second, dinos at 100 px/s a unit along a 3,337 px road, a base of 10.
"""

import shutil
from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_replay import cursor_at, replay, replay_peers, tape_from_holds

TOWERS = Path(__file__).resolve().parents[2] / 'projects' / 'towers' / 'towers.q'


@pytest.fixture(scope='module')
def project(godot, tmp_path_factory) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    src_dir = tmp_path_factory.mktemp('towers')
    shutil.copytree(TOWERS.parent, src_dir / 'towers', ignore=shutil.ignore_patterns('godot'))
    app = QuantumParser(use_cache=False).parse_file(str(src_dir / 'towers' / 'towers.q'))
    out = compile_game(app, str(src_dir / 'godot'), source_dir=str(src_dir / 'towers'))
    assert check_project(Path(out), binary=godot) == []
    return Path(out)


ENTER = 1   # the title's "Play alone", chosen on tick 0: the map's first tick is tick 1


def run(project, ticks, holds=(), cursor=()):
    tape = tape_from_holds([('select', 0, 2)] + [(a, s + ENTER, e + ENTER) for a, s, e in holds])
    for tick, x, y in cursor:
        cursor_at(tape, tick + ENTER, x, y)
    state = replay(project, ticks + ENTER, tape=tape)
    scene = next(iter(state))
    return scene, state[scene]


def towers_in(state):
    return [w for w in state['where'] if w[0] == 'tower']


def test_a_click_builds_the_chosen_tower_where_the_cursor_is_snapped_to_the_grid(godot, project):
    _, s = run(project, 30, [('select', 20, 22)], [(10, 610, 590)])
    assert s['game']['gold'] == 50 and towers_in(s) == [['tower', 600.0, 600.0, 'level1']]


def test_the_road_and_the_gold_refuse_a_tower(godot, project):
    _, s = run(project, 30, [('select', 20, 22)], [(10, 600, 420)])      # on the road
    assert s['game']['gold'] == 100 and towers_in(s) == []
    _, s = run(project, 60, [('select', 20, 22), ('buy-explosive', 30, 32), ('select', 40, 42)],
               [(10, 600, 600), (35, 230, 300)])                          # 50 left: no 70-gold explosive
    assert s['game']['gold'] == 50 and s['things'] == {'tower': 1}


def test_a_click_on_a_tower_upgrades_it(godot, project):
    _, s = run(project, 60, [('select', 20, 22), ('select', 40, 42)], [(10, 600, 600)])
    assert s['game']['gold'] == 0 and towers_in(s) == [['tower', 600.0, 600.0, 'level2']]


def test_waves_come_down_the_road_and_the_gatling_earns_gold(godot, project):
    _, s = run(project, 700, [('select', 20, 22)], [(10, 600, 600)])
    assert s['game']['wave'] == 1 and s['game']['gold'] == 90      # four of the eight dinos shot, 10 each
    assert s['things'] == {'dino': 4, 'tower': 1}
    assert run(project, 700, [('select', 20, 22)], [(10, 600, 600)]) == \
        run(project, 700, [('select', 20, 22)], [(10, 600, 600)])


def test_with_no_tower_the_base_falls(godot, project):
    scene, s = run(project, 2300)
    assert scene == 'map' and s['game']['base_hp'] == 5
    scene, s = run(project, 2500)
    assert scene == 'lost' and s['game']['base_hp'] == 0


def test_two_players_build_the_same_defence_in_lockstep(godot, project):
    one = tape_from_holds([('select', 20, 22)])
    cursor_at(one, 10, 600, 600)
    two = tape_from_holds([('buy-explosive', 25, 27), ('select', 40, 42)])
    cursor_at(two, 30, 230, 300)
    peers = replay_peers(project, 700, [one, two], binary=godot)
    assert peers[0] == peers[1]
    s = peers[0]['map']
    assert s['game']['gold'] == 40          # 100 - 50 - 70, plus six dinos shot by two towers
    assert sorted(towers_in(s)) == [['tower', 216.0, 312.0, 'level1'], ['tower', 600.0, 600.0, 'level1']]
