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
    alone = replay(project, 300 + 1, tape=tape_from_holds(
        [('select', 0, 2)] + [(a, s + 1, e + 1) for a, s, e in
                              [('down', DELAY, 60 + DELAY), ('p2_up', DELAY, 60 + DELAY), ('p2_up', 100 + DELAY, 200 + DELAY)]]),
        binary=godot)
    assert alone['court'] == peers[0]['court']


def test_through_a_relay_that_takes_no_seat(godot, project):
    # quantum relay's Godot hosts without playing: both players join it and it passes
    # their frames on; the game is the same as when player 1 hosts
    player1 = tape_from_holds([('down', 0, 60)])
    player2 = tape_from_holds([('up', 0, 60), ('up', 100, 200)])
    peers = replay_peers(project, 300, [player1, player2], binary=godot, relay=True)
    assert peers[0] == peers[1]
    hosted = replay_peers(project, 300, [player1, player2], binary=godot, transport='websocket')
    assert peers[0]['court'] == hosted[0]['court']


@pytest.mark.parametrize('relay', [False, True], ids=['hosted', 'relay'])
def test_a_player_who_leaves_can_come_back(godot, project, relay):
    # player 2 leaves at tick 150; the game waits; someone joins in their place, catches up
    # (the whole game so far, fast) and plays on: the same game on both, to the last tick
    player1 = tape_from_holds([('down', 0, 60), ('up', 250, 280)])
    player2 = tape_from_holds([('up', 0, 100)])
    back = tape_from_holds([('down', 300, 360)])
    peers = replay_peers(project, 420, [player1, player2], binary=godot, relay=relay, rejoin=(150, back))
    assert peers[0] == peers[1]
    right = peers[0]['court']['nodes']['right']['y']
    stayed = replay_peers(project, 420, [player1, player2], binary=godot, relay=relay, rejoin=(150, {}))
    assert stayed[0] == stayed[1]
    assert right > stayed[0]['court']['nodes']['right']['y']   # the one who came back moved the paddle down


FREEZE = """extends SceneTree
# A tick every other frame, a wait (the lockstep's freeze) between: one area
# slides into another and stays. It touched once, however often it waited.
var hits := 0
var frame := 0
var ls
var parent: Node2D
var a: Area2D


func _area(size: float) -> Area2D:
	var area := Area2D.new()
	var shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = Vector2(size, size)
	shape.shape = rect
	area.add_child(shape)
	return area


func _initialize() -> void:
	ls = load("res://addons/quantum/lockstep.gd").new()
	parent = Node2D.new()
	root.add_child(parent)
	a = _area(8)
	a.position = Vector2(-30, 0)
	a.area_entered.connect(func(_other): hits += 1)
	parent.add_child(a)
	parent.add_child(_area(32))


func _physics_process(_delta: float) -> bool:
	frame += 1
	ls._freeze(parent, frame % 2 == 1)
	if frame % 2 == 0:
		a.position.x += 1
	if frame == 120:
		print("HITS %d" % hits)
		quit()
	return false
"""


def test_waiting_for_the_others_is_no_new_touch(godot, project, tmp_path):
    # A peer waiting for the others' input freezes the scene. Its collision objects stay in the
    # physics: a disabled node leaves it by default, and coming back was a new touch, on that peer
    # alone (a paddle hit the ball it was already touching: another random slant, a desync).
    import subprocess
    script = tmp_path / 'freeze.gd'
    script.write_text(FREEZE, encoding='utf-8')
    out = subprocess.run([str(godot), '--headless', '--path', str(project), '-s', str(script)],
                         capture_output=True, text=True, timeout=120).stdout
    assert 'HITS 1' in out, out[-800:]


def test_the_ball_is_returned_on_both_peers_alike(godot, project):
    # nobody moves: the left paddle returns the ball at a random slant from the scene seed, on both
    peers = replay_peers(project, 200, [{}, {}], binary=godot)
    assert peers[0] == peers[1]
    ball = peers[0]['court']['named']['ball']
    assert ball['x'] > 90 and ball['y'] != 191.12


def presses(*holds):
    """A lobby tape: each (action, tick) pressed for two ticks."""
    return tape_from_holds([(a, t, t + 2) for a, t in holds])


# The title's menu: 0 one keyboard, 1 Host, 2 the address field, 3 Join (4 Cancel is hidden).
HOST = presses(('down', 5), ('select', 10))
JOIN = presses(('down', 5), ('down', 10), ('down', 15), ('select', 40))


@pytest.mark.parametrize('transport', [None, 'websocket'])
def test_host_and_join_from_the_title_then_play_the_same_game(godot, project, transport):
    # the title's own Host and Join start the network (on a free port the harness gives both);
    # then the same game tapes as above must give the same court as over the command line
    player1 = tape_from_holds([('down', 0, 60)])
    player2 = tape_from_holds([('up', 0, 60), ('up', 100, 200)])
    peers = replay_peers(project, 300, [player1, player2], binary=godot, lobby_tapes=[HOST, JOIN],
                         transport=transport)
    assert peers[0] == peers[1]
    by_flags = replay_peers(project, 300, [player1, player2], binary=godot)
    assert peers[0]['court'] == by_flags[0]['court']
