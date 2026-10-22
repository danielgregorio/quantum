"""To ship a game in Godot (PLAN_GAMES_3.md, Phase 4): an options screen kept between runs, keys chosen by the
player, save slots, a HUD with pictures, menus in a grid that scroll, and controls for a touch screen.

One small game. Its title is a menu of two columns, two rows shown at a time: the music's slider, a number's
slider, the full screen, the fire key, a button that silences the effects, a save in slot 2 and going on from
it, and Play. Its room counts the shots fired, with a picture beside the count and a line that shows only from
the second shot. Its touch controls show everywhere (show="always"), so a probe can touch them.
"""

import json
import tempfile
from pathlib import Path

import pytest

from quantum.runtime.godot_bin import check_project, run_godot
from quantum.runtime.godot_play import PlaySession

REPO = Path(__file__).resolve().parents[2]

SHIP = '''<q:application id="ship" type="game">
  <q:set name="pace" value="5" type="number" />
  <q:set name="fired" value="0" type="number" />
  <qg:tileset name="k" src="assets/kenney/tilemap_packed.png" tile="18" />
  <qg:spritesheet name="c" src="assets/kenney/tilemap-characters_packed.png" tile="24" />
  <qg:sound name="song" src="assets/kenney/audio/win.ogg" loop="true" bus="music" />
  <qg:sound name="hit" src="assets/kenney/audio/stomp.ogg" bus="effects" />
  <qg:input action="fire" keys="J" />
  <qg:touch-button action="fire" label="F" x="200" y="120" size="40" show="always" />
  <qg:touch-stick x="40" y="120" size="60" show="always" />
  <qg:scene name="title" width="240" height="160">
    <qg:menu position="center" size="10" columns="2" rows="2">
      <qg:slider label="Music" bus="music" />
      <qg:slider label="Pace" bind="pace" min="1" max="9" step="2" />
      <qg:button label="{'Full ' + str(fullscreen())}"><qg:fullscreen /></qg:button>
      <qg:rebind label="Fire" action="fire" />
      <qg:button label="Quiet"><qg:volume bus="effects" value="{volume('effects') - 100}" /></qg:button>
      <qg:button label="Save 2"><qg:save slot="2" scene="room" /></qg:button>
      <qg:button label="Go on 2" if="{has_save(2)}"><qg:continue slot="{1 + 1}" /></qg:button>
      <qg:button label="Play"><qg:goto-scene name="room" /></qg:button>
    </qg:menu>
  </qg:scene>
  <qg:scene name="room" width="240" height="160" save="true">
    <qg:character id="hero" controller="topdown" sheet="c" x="120" y="80" hitbox="14x14" speed="60" />
    <qg:on-input action="fire"><q:set name="fired" value="{fired + 1}" /></qg:on-input>
    <qg:hud position="bottom-right" size="8">
      <qg:icon sheet="k" frame="{fired % 3}" scale="0.5" />
      <qg:counter bind="fired" label="FIRED" color="#ff4040" />
    </qg:hud>
    <qg:hud position="top-left" if="{fired >= 2}"><qg:text value="{'TWICE'}" /></qg:hud>
  </qg:scene>
</q:application>
'''

# A probe: the main scene, run tick by tick, with what a player does on given ticks (a key, a touch, a drag,
# a menu item chosen), and at the end the settings, the keys of some actions and the scene's state.
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
		match s["do"]:
			"key":
				var k := InputEventKey.new()
				k.physical_keycode = OS.find_keycode_from_string(s["key"])
				k.pressed = s.get("pressed", true)
				Input.parse_input_event(k)
				Input.flush_buffered_events()   # now: several ticks may run before the next frame
			"touch":
				var t := InputEventScreenTouch.new()
				t.index = int(s.get("finger", 0))
				t.position = root.get_final_transform() * Vector2(s["x"], s["y"])   # on the window, as a finger
				t.pressed = s.get("pressed", true)
				Input.parse_input_event(t)
				Input.flush_buffered_events()
			"drag":
				var d := InputEventScreenDrag.new()
				d.index = int(s.get("finger", 0))
				d.position = root.get_final_transform() * Vector2(s["x"], s["y"])
				Input.parse_input_event(d)
				Input.flush_buffered_events()
			"choose":
				var menu = game.current_scene.get_node("Menu")
				menu._choose(int(s["item"]))
	ticks += 1
	if ticks < last:
		return false
	var scene = game.current_scene
	var keys := {}
	for a in ["fire", "jump"]:
		keys[a] = InputMap.action_get_events(a).map(func(e): return e.as_text())
	var dump := {"scene": String(scene.name), "keys": keys, "settings": root.get_node("Q").settings,
		"pressed": {"fire": Input.is_action_pressed("fire"), "right": Input.get_action_strength("right"),
			"up": Input.get_action_strength("up")}, "state": scene.quantum_state()}
	var f := FileAccess.open(out_path, FileAccess.WRITE)
	f.store_string(JSON.stringify(dump))
	return true
'''


@pytest.fixture(scope='module')
def ship(tmp_path_factory, godot):
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    folder = tmp_path_factory.mktemp('ship')
    src = folder / 'ship.q'
    src.write_text(SHIP, encoding='utf-8')
    out = Path(compile_game(QuantumParser(use_cache=False).parse_file(str(src)), str(folder / 'godot'),
                            source_dir=str(REPO)))
    assert check_project(out, binary=godot) == []
    return out


def probe(project, godot, steps, ticks, persist):
    with tempfile.TemporaryDirectory() as tmp:
        script, spec, out = Path(tmp) / 'probe.gd', Path(tmp) / 'steps.json', Path(tmp) / 'out.json'
        script.write_text(PROBE, encoding='utf-8')
        spec.write_text(json.dumps({'steps': steps, 'ticks': ticks}), encoding='utf-8')
        run_godot(['--path', str(project), '-s', str(script), '--', str(spec), str(out),
                   f'--persist-dir={persist}'], binary=godot)
        return json.loads(out.read_text())


def menu(obs):
    return PlaySession.screen(obs, 'menu')


def kinds(obs, kind):
    return [e for e in obs['events'] if e['kind'] == kind]


def test_sliders_full_screen_and_a_bus_kept_between_runs(ship, godot, tmp_path):
    with PlaySession(ship, binary=godot, persist_dir=tmp_path) as game:
        items = menu(game.observe())['items']
        assert items[0] == {'slider': 'Music', 'value': 100.0, 'shown': True}
        obs = game.act(tap=['left'], ticks=2)
        assert menu(obs)['items'][0]['value'] == 90.0 and kinds(obs, 'volume')[0]['bus'] == 'music'
        for action in ('down', 'right', 'up'):                     # a grid of two: down a row, across, up
            obs = game.act(tap=[action], ticks=2)
        assert menu(obs)['focus'] == 1
        obs = game.act(tap=['right'], ticks=2)
        assert menu(obs)['items'][1]['value'] == 7.0               # a number of the game, a step of 2
        assert obs["state"]["game"]["pace"] == 7.0
        obs = game.act(tap=['right'], ticks=2)
        obs = game.act(tap=['right'], ticks=2)
        assert obs["state"]["game"]["pace"] == 9.0                # no further than max=
        obs = game.act(tap=['down'], ticks=2)                       # Fire's key
        obs = game.act(tap=['left'], ticks=2)                       # across to the full screen
        obs = game.act(tap=['select'], ticks=2)
        assert [e['on'] for e in kinds(obs, 'fullscreen')] == [True]
        assert menu(obs)['items'][2]['button'] == 'Full true'
    assert json.loads((tmp_path / 'quantum-settings.json').read_text()) == {'volume': {'music': 90.0}, 'fullscreen': True}
    with PlaySession(ship, binary=godot, persist_dir=tmp_path) as game:   # the next run: as they were left
        items = menu(game.observe())['items']
        assert items[0]['value'] == 90.0 and items[2]['button'] == 'Full true'


def test_the_rows_beyond_scroll_into_view(ship, godot, tmp_path):
    with PlaySession(ship, binary=godot, persist_dir=tmp_path) as game:
        assert menu(game.observe())['scroll'] == 0
        for _ in range(3):                                           # down to the fourth row: Play (Go on 2 hidden)
            obs = game.act(tap=['down'], ticks=3)
        assert menu(obs)['focus'] == 7 and menu(obs)['scroll'] > 0


def test_a_key_chosen_is_the_actions_and_is_kept(ship, godot, tmp_path):
    steps = [{'tick': 3, 'do': 'choose', 'item': 3}, {'tick': 5, 'do': 'key', 'key': 'K'},
             {'tick': 6, 'do': 'key', 'key': 'K', 'pressed': False}]
    first = probe(ship, godot, steps, 10, tmp_path)
    assert first['keys']['fire'] == ['K (Physical)']
    assert first['settings']['keys'] == {'fire': ['K']}
    again = probe(ship, godot, [], 3, tmp_path)                   # the next run: K still
    assert again['keys']['fire'] == ['K (Physical)']
    # Escape leaves it as it was
    kept = probe(ship, godot, [{'tick': 3, 'do': 'choose', 'item': 3}, {'tick': 5, 'do': 'key', 'key': 'Escape'}],
                 8, tmp_path)
    assert kept['keys']['fire'] == ['K (Physical)']


def test_a_volume_from_a_rule(ship, godot, tmp_path):
    first = probe(ship, godot, [{'tick': 3, 'do': 'choose', 'item': 4}], 5, tmp_path)
    assert first['settings']['volume'] == {'effects': 0.0}


def test_save_slots(ship, godot, tmp_path):
    with PlaySession(ship, binary=godot, persist_dir=tmp_path) as game:
        assert not menu(game.observe())['items'][6]['shown']        # Go on 2: nothing saved in slot 2
    first = probe(ship, godot, [{'tick': 3, 'do': 'choose', 'item': 5}], 5, tmp_path)
    assert first['scene'] == 'title'
    saved = json.loads((tmp_path / 'quantum-save-2.json').read_text())
    assert saved['scene'] == 'room' and not (tmp_path / 'quantum-save.json').exists()
    on = probe(ship, godot, [{'tick': 3, 'do': 'choose', 'item': 6}], 6, tmp_path)
    assert on['scene'] == 'room'                                   # gone on in slot 2, which the room saves into
    assert json.loads((tmp_path / 'quantum-save-2.json').read_text())['scene'] == 'room'


def test_a_hud_with_a_picture_a_colour_and_a_line_that_waits(ship, godot, tmp_path):
    with PlaySession(ship, binary=godot, persist_dir=tmp_path) as game:
        for _ in range(3):                                           # down to Play
            game.act(tap=['down'], ticks=2)
        obs = game.until("scene == 'room'", tap=['select'], max_ticks=10)
        huds = [v for v in obs['screen'] if v['kind'] == 'hud']
        assert huds == [{'kind': 'hud', 'items': [{'icon': 0}, 'FIRED 0']}]   # the second one waits
        obs = game.act(tap=['fire'], ticks=3)
        obs = game.act(tap=['fire'], ticks=3)
        huds = [v for v in obs['screen'] if v['kind'] == 'hud']
        assert huds == [{'kind': 'hud', 'items': [{'icon': 2}, 'FIRED 2']}, {'kind': 'hud', 'items': ['TWICE']}]


def test_touch_controls_press_the_actions(ship, godot, tmp_path):
    steps = [{'tick': 3, 'do': 'choose', 'item': 7},                # Play
             {'tick': 6, 'do': 'touch', 'x': 200, 'y': 120},       # the fire button, held
             {'tick': 8, 'do': 'touch', 'x': 40, 'y': 120, 'finger': 1},   # the stick, then pushed right and up
             {'tick': 9, 'do': 'drag', 'x': 70, 'y': 100, 'finger': 1}]
    held = probe(ship, godot, steps, 12, tmp_path)
    assert held['scene'] == 'room' and held['state']['game']['fired'] == 1   # pressed once: one shot
    assert held['pressed']['fire'] is True
    assert held['pressed']['right'] > 0.5 and 0.0 < held['pressed']['up'] < held['pressed']['right']
    let_go = probe(ship, godot, steps + [{'tick': 12, 'do': 'touch', 'x': 200, 'y': 120, 'pressed': False},
                                         {'tick': 12, 'do': 'touch', 'x': 70, 'y': 100, 'finger': 1, 'pressed': False}],
                   15, tmp_path)
    assert let_go['pressed'] == {'fire': False, 'right': 0.0, 'up': 0.0}
