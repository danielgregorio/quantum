"""Arena — the fighting game — replayed in Godot, alone and on two peers.

projects/arena/arena.q is compiled and driven by input tapes. The numbers
are the game's: fighters at x=200 and x=440 walking at 140 px/s, a punch
of 8 and a kick of 12, 100 health, rounds reset two seconds after a KO.
"""

import shutil
from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project
from quantum.runtime.godot_replay import replay, replay_peers, tape_from_holds

ARENA = Path(__file__).resolve().parents[2] / 'projects' / 'arena' / 'arena.q'
WALK_IN = [('right', 0, 90)]   # player 1 walks up to player 2


@pytest.fixture(scope='module')
def project(godot, tmp_path_factory) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    src_dir = tmp_path_factory.mktemp('arena')
    shutil.copytree(ARENA.parent, src_dir / 'arena', ignore=shutil.ignore_patterns('godot'))
    app = QuantumParser(use_cache=False).parse_file(str(src_dir / 'arena' / 'arena.q'))
    out = compile_game(app, str(src_dir / 'godot'), source_dir=str(src_dir / 'arena'))
    assert check_project(Path(out), binary=godot) == []
    return Path(out)


def fight(project, ticks, holds):
    state = replay(project, ticks, tape=tape_from_holds(list(holds)))
    scene = next(iter(state))
    return scene, state[scene]


def kicks(n):
    """Walk in, then a kick every 80 ticks, walking after the push back."""
    holds = list(WALK_IN)
    for k in range(n):
        t0 = 95 + k * 80
        holds += [('kick', t0, t0 + 2), ('right', t0 + 30, t0 + 70)]
    return holds


def test_a_punch_and_a_kick_land_for_their_damage_and_push(godot, project):
    _, s = fight(project, 110, WALK_IN + [('punch', 95, 97)])
    assert s['nodes']['p1']['x'] == 400.0 and s['nodes']['p2']['health'] == 92   # stopped at p2's body
    assert s['nodes']['p2']['phase'] == 'hit' and s['nodes']['p2']['x'] > 440
    _, s = fight(project, 140, WALK_IN + [('punch', 95, 97), ('kick', 120, 122)])
    assert s['nodes']['p2']['health'] == 80


def test_holding_away_blocks(godot, project):
    _, s = fight(project, 110, WALK_IN + [('p2_right', 85, 130), ('punch', 95, 97)])
    assert s['nodes']['p2']['health'] == 100 and s['nodes']['p2']['x'] > 440    # pushed, not hurt


def test_bodies_do_not_cross_on_the_ground(godot, project):
    _, s = fight(project, 300, [('right', 0, 300)])
    assert s['nodes']['p1']['x'] == 400.0 and s['nodes']['p2']['x'] == 440.0    # held off the other's body


def test_kicks_to_a_ko_give_the_round_and_the_next_one_starts_at_the_marks(godot, project):
    _, s = fight(project, 700, kicks(11))
    assert s['nodes']['p2']['health'] == 4 and s['round'] == 1
    _, s = fight(project, 800, kicks(11))
    assert s['nodes']['p2'] == {'facing': -1, 'health': 0, 'phase': 'ko', 'x': 620.0, 'y': 252.0}
    assert s['game'] == {'wins_1': 1.0, 'wins_2': 0.0} and s['message'] == 'PLAYER 1 WINS THE ROUND'
    _, s = fight(project, 900, kicks(11))
    assert s['round'] == 2 and s['message'] == 'ROUND 2 - FIGHT' and s['clock'] == 98
    assert s['nodes']['p2'] == {'facing': -1, 'health': 100, 'phase': 'free', 'x': 440.0, 'y': 252.0}
    assert s['nodes']['p1']['health'] == 100 and s['nodes']['p1']['x'] < 300


def test_two_peers_fight_the_same_fight(godot, project):
    one = tape_from_holds(WALK_IN + [('punch', 95, 97)])
    two = tape_from_holds([('left', 100, 120), ('kick', 122, 124)])
    peers = replay_peers(project, 140, [one, two], binary=godot)
    assert peers[0] == peers[1]
    nodes = peers[0]['fight']['nodes']
    assert nodes['p2']['health'] == 92 and nodes['p1']['health'] == 88
