"""qg:menu in Godot: keys and the pointer choose, the same way in a replay as with a mouse.

A small game: a menu of three buttons (one shown only once `unlocked`, one
with a label read from the state) and a field, and the state the buttons
change. The buttons are stacked in the centre of a 320x240 scene.
"""

import json
from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project, run_godot
from quantum.runtime.godot_play import PlaySession
from quantum.runtime.godot_replay import cursor_at, replay, tape_from_holds

REPO = Path(__file__).resolve().parents[2]

SOURCE = '''<q:application id="menus" type="game">
  <qg:tileset name="k" src="assets/kenney/tilemap_packed.png" tile="18" />
  <q:set name="player_name" value="anon" />
  <qg:scene name="title" width="320" height="240">
    <q:set name="clicks" value="0" type="number" />
    <q:set name="unlocked" value="false" type="boolean" />
    <q:set name="cancels" value="0" type="number" />
    <qg:on-input action="cancel"><q:set name="cancels" value="{cancels + 1}" /></qg:on-input>
    <qg:menu size="16">
      <qg:button label="{'Clicked ' + str(clicks)}"><q:set name="clicks" value="{clicks + 1}" /></qg:button>
      <qg:button label="Unlock"><q:set name="unlocked" value="true" /></qg:button>
      <qg:button label="Play" if="{unlocked}"><qg:goto-scene name="play" /></qg:button>
      <qg:field label="Name" bind="player_name" />
    </qg:menu>
  </qg:scene>
  <qg:scene name="play" />
</q:application>
'''


@pytest.fixture(scope='module')
def project(godot, tmp_path_factory) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    src = tmp_path_factory.mktemp('menus') / 'menus.q'
    src.write_text(SOURCE, encoding='utf-8')
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(src)), str(src.parent / 'godot'),
                            source_dir=str(REPO)))
    assert check_project(out, binary=godot) == []
    return out


def run(project, ticks, holds=(), cursor=()):
    tape = tape_from_holds(list(holds))
    for tick, x, y in cursor:
        cursor_at(tape, tick, x, y)
    state = replay(project, ticks, tape=tape)
    scene = next(iter(state))
    return scene, state[scene]


def test_select_chooses_the_focused_button(godot, project):
    _, s = run(project, 20, [('select', 5, 7), ('select', 10, 12)])
    assert s['clicks'] == 2 and s['menus'] == [0]


def test_down_moves_the_focus_and_skips_a_hidden_button(godot, project):
    # Clicked, Unlock, (Play hidden), Name: down twice from Clicked is the field, a third time wraps
    _, s = run(project, 30, [('down', 5, 7), ('down', 10, 12)])
    assert s['menus'] == [3]
    _, s = run(project, 30, [('down', 5, 7), ('down', 10, 12), ('down', 15, 17)])
    assert s['menus'] == [0]


def test_a_shown_button_once_its_condition_holds(godot, project):
    scene, s = run(project, 40, [('down', 5, 7), ('select', 10, 12), ('down', 15, 17), ('select', 20, 22)])
    assert scene == 'play'


def test_the_pointer_focuses_and_a_click_chooses_what_is_under_it(godot, project):
    # the buttons are stacked around the scene's centre (160, 120); find the first one from the top
    for y in range(80, 130, 4):
        scene, s = run(project, 20, [('select', 10, 12), ('click', 10, 12)], [(3, 160, y)])
        if s.get('clicks') == 1:
            break
    else:
        pytest.fail('no click on the first button between y=80 and y=130')
    assert s['menus'] == [0]
    # a click where there is no button chooses nothing, whatever has the focus
    _, s = run(project, 20, [('select', 10, 12), ('click', 10, 12)], [(3, 10, 10)])
    assert s['clicks'] == 0
    # but Enter chooses the focused button wherever the pointer rests: a page clicked to give the game
    # the keyboard leaves the pointer off the buttons
    _, s = run(project, 20, [('select', 10, 12)], [(3, 10, 10)])
    assert s['clicks'] == 1


def _typing(obs) -> bool:
    return bool(PlaySession.screen(obs, 'menu')['items'][3].get('typing'))


def _into_the_box(game):
    """Down to the Name field (Clicked, Unlock, Name: Play is hidden) and into it."""
    game.act(ticks=3)
    for _ in range(2):
        game.act(tap=['down'], ticks=2)
    assert _typing(game.act(tap=['select'], ticks=2))


def _first_button(game):
    """Where the pointer is on the first button: the focus follows it (the buttons are around (160, 120))."""
    for y in range(80, 130, 4):
        if PlaySession.screen(game.act(cursor=(160, y), ticks=2), 'menu')['focus'] == 0:
            return 160, y
    pytest.fail('no button under the pointer between y=80 and y=130')


def test_a_click_away_from_the_box_ends_the_typing_and_chooses_what_is_under_it(godot, project):
    """Typing takes the keys, not the mouse: a click on a button ends it, what was typed stays, and the button
    is chosen (a player who clicks a field, types and clicks Send is not left in the box)."""
    with PlaySession(project, binary=godot) as game:
        at = _first_button(game)
        game.act(cursor=(10, 10), ticks=2)
        _into_the_box(game)
        game.act(text='Bo', ticks=2)
        game.act(cursor=at, ticks=2)                                     # the mouse goes to the button...
        clicked = game.act(cursor=at, tap=['select'], hold=['click'], ticks=3)   # ...and clicks it
        assert not _typing(clicked)
        assert clicked['state']['game']['player_name'] == 'anonBo' and clicked['state']['clicks'] == 1


def test_escape_ends_the_typing_and_the_keys_play_again(godot, project):
    with PlaySession(project, binary=godot) as game:
        _into_the_box(game)
        left = game.act(text='Al\u001b', ticks=2)                       # Escape
        assert not _typing(left) and left['state']['game']['player_name'] == 'anonAl'
        assert PlaySession.screen(game.act(tap=['down'], ticks=2), 'menu')['focus'] == 0


# A probe: the game run tick by tick with a keyboard's events (a key down on one tick, up on another), and the
# field chosen as a select would; at the end, whether a text box still has the keys and the scene's state.
PROBE = '''extends SceneTree
var steps := {}
var ticks := 0
var last := 0
var out_path := ""
var game: Node

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	var spec = JSON.parse_string(FileAccess.get_file_as_string(args[0]))
	out_path = args[1]
	for s in spec["steps"]:
		steps[int(s["tick"])] = steps.get(int(s["tick"]), []) + [s]
	last = int(spec["ticks"])
	game = load(ProjectSettings.get_setting("application/run/main_scene")).instantiate()
	root.add_child(game)

func _physics_process(_delta: float) -> bool:
	for s in steps.get(ticks, []):
		if s["do"] == "choose":
			game.current_scene.get_node("Menu")._choose(int(s["item"]))
		else:
			var k := InputEventKey.new()
			k.keycode = OS.find_keycode_from_string(s["key"])
			k.physical_keycode = k.keycode
			k.unicode = s["key"].unicode_at(0) if s["key"].length() == 1 else 0
			k.pressed = s["do"] == "down"
			Input.parse_input_event(k)
			Input.flush_buffered_events()
	ticks += 1
	if ticks < last:
		return false
	var dump := {"typing": root.get_node("Q").typing(), "state": game.current_scene.quantum_state()}
	var f := FileAccess.open(out_path, FileAccess.WRITE)
	f.store_string(JSON.stringify(dump))
	return true
'''


def keyboard(project, godot, tmp_path, steps, ticks=40):
    script, spec, out = tmp_path / 'probe.gd', tmp_path / 'steps.json', tmp_path / 'out.json'
    script.write_text(PROBE, encoding='utf-8')
    spec.write_text(json.dumps({'steps': steps, 'ticks': ticks}), encoding='utf-8')
    run_godot(['--path', str(project), '-s', str(script), '--', str(spec), str(out)], binary=godot)
    return json.loads(out.read_text())


@pytest.mark.parametrize('key', ['Enter', 'Escape'])
def test_the_key_that_ends_the_typing_plays_only_once_let_go(godot, project, tmp_path, key):
    """A key is down for some ticks after it ends the typing: Enter still held is not a select that chooses the
    box again, Escape still held is not a cancel. Once let go, the keys play again."""
    typed = [{'tick': 5, 'do': 'choose', 'item': 3}, {'tick': 8, 'do': 'down', 'key': 'B'},
             {'tick': 9, 'do': 'up', 'key': 'B'}, {'tick': 12, 'do': 'down', 'key': key}]
    held = keyboard(project, godot, tmp_path, typed, ticks=24)
    assert not held['typing'] and held['state']['game']['player_name'] == 'anonB'
    assert held['state']['cancels'] == 0
    again = keyboard(project, godot, tmp_path, typed + [{'tick': 24, 'do': 'up', 'key': key},
                                                        {'tick': 28, 'do': 'down', 'key': 'Escape'}], ticks=34)
    assert again['state']['cancels'] == 1
