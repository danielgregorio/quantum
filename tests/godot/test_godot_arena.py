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


ENTER = 1   # the title's "Two players, one keyboard", chosen on tick 0: the fight's first tick is tick 1


def fight(project, ticks, holds):
    tape = tape_from_holds([('select', 0, 2)] + [(a, s + ENTER, e + ENTER) for a, s, e in holds])
    state = replay(project, ticks + ENTER, tape=tape)
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


# --- rollback (pong.q's lockstep waits; arena.q's rollback="8" guesses and corrects) ---

def kick_holds(start, n):
    holds = [('right', start, start + 90)]
    for k in range(n):
        t0 = start + 95 + k * 80
        holds += [('kick', t0, t0 + 2), ('right', t0 + 30, t0 + 70)]
    return holds


DELAY = 2   # arena.q: <qg:multiplayer delay="2" rollback="8" />


def test_rollback_peers_with_latency_end_where_one_replay_does(godot, project):
    one = tape_from_holds([('right', 0, 90), ('punch', 95, 97), ('kick', 130, 132), ('jump', 160, 162)])
    two = tape_from_holds([('left', 100, 120), ('kick', 122, 124), ('down', 140, 170), ('punch', 175, 177)])
    a, b = replay_peers(project, 240, [one, two], binary=godot, latency_ms=[120, 30], net_report=True)
    assert a['fight'] == b['fight']
    assert a['_net']['rollbacks'] > 0 and b['_net']['rollbacks'] > 0      # both guessed wrong, both corrected
    holds = [('right', 0, 90), ('punch', 95, 97), ('kick', 130, 132), ('jump', 160, 162),
             ('p2_left', 100, 120), ('p2_kick', 122, 124), ('p2_down', 140, 170), ('p2_punch', 175, 177)]
    alone = replay(project, 240 + ENTER, binary=godot, tape=tape_from_holds(
        [('select', 0, 2)] + [(x, s + DELAY + ENTER, e + DELAY + ENTER) for x, s, e in holds]))
    assert alone['fight'] == a['fight']


def test_a_match_to_the_result_under_rollback(godot, project):
    # two KOs (the second round starts at tick 900), the result scene, and the same on both peers:
    # a scene change waits until the tick that asked for it is certain, then happens on both
    one = tape_from_holds(kick_holds(0, 11) + kick_holds(900, 11))
    a, b = replay_peers(project, 1850, [one, {}], binary=godot, latency_ms=[100, 100], net_report=True)
    assert a.keys() == b.keys() and 'result' in a
    assert a['result'] == b['result']
    assert a['result']['game'] == {'wins_1': 2.0, 'wins_2': 0.0}
    assert a['result']['message'] == 'PLAYER 1 WINS - press jump'
    assert b['_net']['rollbacks'] > 0


# --- PLAN_GAMES_3.md, Phase 5: the special move (qg:on-input sequence=) and qg:rumble ---

CLOSE = [('right', 0, 30)]   # player 1 walks in to 170 px of player 2: in the blast's reach, out of a punch's


def blast(at):
    """Down, forward (right, facing right), punch: three presses four ticks apart, from tick `at`."""
    return [('down', at, at + 2), ('right', at + 4, at + 6), ('punch', at + 8, at + 10)]


def test_down_forward_punch_is_the_blast(godot, project):
    _, s = fight(project, 56, CLOSE + blast(40))
    assert s['nodes']['p2']['health'] == 88 and s['nodes']['p2']['phase'] == 'hit'   # stunned a moment
    _, s = fight(project, 80, CLOSE + [('punch', 48, 50)])
    assert s['nodes']['p2']['health'] == 100                                   # a punch alone does not reach


def test_a_sequence_too_slow_or_out_of_order_is_not_one(godot, project):
    slow = [('down', 30, 32), ('right', 50, 52), ('punch', 70, 72)]           # 40 ticks: more than 30
    _, s = fight(project, 100, CLOSE + slow)
    assert s['nodes']['p2']['health'] == 100
    _, s = fight(project, 80, CLOSE + [('right', 40, 42), ('down', 44, 46), ('punch', 48, 50)])
    assert s['nodes']['p2']['health'] == 100


def test_forward_is_the_way_the_fighter_faces(godot, project):
    # player 2 faces left: down, left, punch is its blast; down, right, punch is not
    p2 = [('p2_left', 0, 30), ('p2_down', 40, 42), ('p2_left', 44, 46), ('p2_punch', 48, 50)]
    _, s = fight(project, 80, p2)
    assert s['nodes']['p1']['health'] == 88
    _, s = fight(project, 80, [('p2_left', 0, 30), ('p2_down', 40, 42), ('p2_right', 44, 46), ('p2_punch', 48, 50)])
    assert s['nodes']['p1']['health'] == 100


def test_holding_away_blocks_the_blast(godot, project):
    _, s = fight(project, 80, CLOSE + blast(40) + [('p2_right', 46, 60)])
    assert s['nodes']['p2']['health'] == 100 and s['nodes']['p2']['x'] > 440


def test_the_blast_is_felt_on_the_joypad_of_the_one_it_hits(godot, project):
    from quantum.runtime.godot_play import PlaySession
    with PlaySession(project, binary=godot) as game:
        game.act(tap=['select'], ticks=2)
        game.act(hold=['right'], ticks=30)
        game.act(tap=['down'], ticks=4)
        game.act(tap=['right'], ticks=4)
        hit = game.act(tap=['punch'], ticks=4)
        felt = [e for e in hit['events'] if e['kind'] == 'rumble']
        assert felt and (felt[0]['player'], felt[0]['strength'], felt[0]['seconds']) == (2, 0.7, 0.3)


def test_the_blast_under_rollback_with_latency(godot, project):
    one = tape_from_holds(CLOSE + blast(40))
    two = tape_from_holds([('down', 70, 72), ('left', 74, 76), ('punch', 78, 80)])   # blasts back
    a, b = replay_peers(project, 140, [one, two], binary=godot, latency_ms=[80, 40], net_report=True)
    assert a['fight'] == b['fight']
    assert a['fight']['nodes']['p2']['health'] == 88 and a['fight']['nodes']['p1']['health'] == 88
