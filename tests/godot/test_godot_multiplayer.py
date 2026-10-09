"""qg:multiplayer: two Godots on localhost play Pong in lockstep and agree.

Every peer runs the whole game; a tick runs when every player's input for
it has arrived; the state is the same on every peer — and the same as one
Godot replaying both players' tapes, shifted by the input delay. The
lockstep is only the exchange of inputs: determinism does the rest.
"""

import shutil
from pathlib import Path

import pytest

from quantum.runtime.godot_replay import replay, replay_peers, tape_from_holds

PONG = Path(__file__).resolve().parents[2] / 'projects' / 'pong' / 'pong.q'
DELAY = 3   # pong.q: <qg:multiplayer players="2" delay="3" />


@pytest.fixture(scope='module')
def project(godot, tmp_path_factory) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    src_dir = tmp_path_factory.mktemp('pong-mp')
    shutil.copytree(PONG.parent, src_dir / 'pong', ignore=shutil.ignore_patterns('godot'))
    app = QuantumParser(use_cache=False).parse_file(str(src_dir / 'pong' / 'pong.q'))
    return Path(compile_game(app, str(src_dir / 'godot'), source_dir=str(src_dir / 'pong')))


def test_two_peers_see_the_same_game_as_one_replay(godot, project):
    player1 = tape_from_holds([('down', 0, 60)])
    player2 = tape_from_holds([('up', 0, 60), ('up', 100, 200)])
    peers = replay_peers(project, 300, [player1, player2], binary=godot)
    assert peers[0] == peers[1]
    court = peers[0]['court']
    assert court['nodes']['left']['y'] == 292.59 and court['nodes']['right']['y'] == 16.0
    # one Godot, both tapes shifted by the delay, player 2's actions as p2_*
    alone = replay(project, 300, tape=tape_from_holds(
        [('down', DELAY, 60 + DELAY), ('p2_up', DELAY, 60 + DELAY), ('p2_up', 100 + DELAY, 200 + DELAY)]),
        binary=godot)
    assert alone == peers[0]


def test_the_ball_is_returned_on_both_peers_alike(godot, project):
    # nobody moves: the left paddle returns the ball at a random slant from the scene seed, on both
    peers = replay_peers(project, 200, [{}, {}], binary=godot, port=17778)
    assert peers[0] == peers[1]
    ball = peers[0]['court']['named']['ball']
    assert ball['x'] > 90 and ball['y'] != 191.12
