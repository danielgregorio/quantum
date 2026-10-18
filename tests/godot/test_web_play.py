"""The browser bridge's conditions read an observation as the driver's do (godot_play.gd's _holds).

The web build answers through window.quantumPlay; WebPlaySession plays it in
real time, so it evaluates `until`'s conditions itself. CI plays the RPG's
web build to victory with it (scripts/check-play-in-browser.py); these are
the conditions alone.
"""

from quantum.runtime.godot_play import condition
from quantum.runtime.web_play import holds, lookup

OBS = {'tick': 40, 'scene': 'exploration',
       'state': {'talking': 'npc', 'nodes': {'player': {'col': 11, 'row': 7}},
                 'named': {'ball': {'y': 120.0}}, 'game': {'keys': 1}},
       'screen': [{'kind': 'dialogue', 'who': 'UNKNOWN', 'text': 'Hi'}]}
START = {'tick': 0, 'scene': 'exploration', 'state': {'nodes': {'player': {'col': 3, 'row': 4}}}, 'screen': []}


def check(spec, obs=OBS, events=()):
    return holds(condition(spec), obs, START, list(events))


def test_paths_reach_the_state_its_nodes_its_things_the_game_and_the_screen():
    assert lookup(OBS, 'player.col') == 11
    assert lookup(OBS, 'ball.y') == 120.0
    assert lookup(OBS, 'keys') == 1
    assert lookup(OBS, 'dialogue.text') == 'Hi'
    assert lookup(OBS, 'nothing.here') is None


def test_comparisons_truth_and_change():
    assert check('player.row == 7') and check('player.col >= 11') and not check('player.col < 11')
    assert check("scene == 'exploration'") and check('talking') and not check('not talking')
    assert check('changed player') and not check('changed scene')
    assert check(['player.row == 1', 'talking'])          # a list is any of them
    assert not check({'all': [condition('talking'), condition('player.row == 1')]})


def test_events_with_their_details():
    said = [{'kind': 'say', 'who': 'UNKNOWN', 'dialogue': 'npc', 'tick': 30}]
    assert check('event:say', events=said)
    assert check('event:say dialogue=npc', events=said)
    assert not check('event:say dialogue=key', events=said)
    assert not check('event:touch')
