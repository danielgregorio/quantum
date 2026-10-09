extends SceneTree
# Replays an input tape through a game, headless, and dumps its state.
#
# Run by quantum/runtime/godot_replay.py:
#   godot --headless --path <project> -s <this file> -- --ticks=N --tape=<json> --out=<json>
#
# The tape maps a physics tick (as a string key) to the actions that change
# on it: {"0": [["right", true]], "10": [["right", false]]}. Actions are
# pressed and released through Input, so the game reads them exactly as it
# reads a keyboard; the tick is the fixed physics step, so the same tape
# gives the same game.
#
# The main scene runs exactly N physics ticks. Then every node with a
# quantum_state() method contributes its dictionary, keyed by its path from
# the scene root, and the whole is written as JSON. Nodes without the method
# are not in the dump: a game says what its state is.

var ticks := 0
var max_ticks := 0
var tape := {}
var game_tape := {}          # --game-tape: the networked game's input, by the lockstep's tick
var has_game_tape := false
var lobby_ticks := 0         # with a game tape, the ticks before the networked game starts
const LOBBY_LIMIT := 6000
var out_path := ""
var scene: Node


func _read_tape(path: String) -> Dictionary:
	var out := {}
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		push_error("replay: cannot read the tape at " + path)
		quit(2)
		return out
	var data = JSON.parse_string(f.get_as_text())
	if typeof(data) != TYPE_DICTIONARY:
		push_error("replay: the tape is not a JSON object")
		quit(2)
		return out
	for k in data.keys():
		out[int(k)] = data[k]
	return out


func _initialize() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--ticks="):
			max_ticks = int(a.substr(8))
		elif a.begins_with("--tape="):
			tape = _read_tape(a.substr(7))
		elif a.begins_with("--game-tape="):
			game_tape = _read_tape(a.substr(12))
			has_game_tape = true
		elif a.begins_with("--out="):
			out_path = a.substr(6)
	var main: String = ProjectSettings.get_setting("application/run/main_scene", "")
	if main == "":
		push_error("replay: the project has no main scene")
		quit(2)
		return
	scene = load(main).instantiate()
	root.add_child(scene)


func _apply(events: Array) -> void:
	for ev in events:
		if ev[0] == "cursor":
			root.get_node("Q").tape_cursor = Vector2(ev[1][0], ev[1][1])
		elif ev[1]:
			Input.action_press(ev[0])
		else:
			Input.action_release(ev[0])


# MainLoop runs this before the nodes' _physics_process of the same tick, so
# when ticks == max_ticks the scene has run exactly max_ticks ticks.
#
# Under qg:multiplayer the networked game's tick is the lockstep's, which
# stalls while a peer's input is late: the count and the tape follow it,
# and the tape presses this peer's keys (player 1's actions). With a game
# tape, --tape is the lobby's: it runs by this script's own count until the
# networked game starts (qg:host / qg:join in a scene), and those ticks do
# not count towards --ticks.
func _physics_process(_delta: float) -> bool:
	var lockstep: Node = scene.get("lockstep") if "lockstep" in scene else null
	if lockstep != null and lockstep.started:
		if lockstep.desynced:
			_dump()
			return true
		var t: int = lockstep.tick
		if t >= max_ticks or (lockstep.ended and lockstep.stalled()):
			_dump()
			return true
		if t == ticks:
			var source: Dictionary = game_tape if has_game_tape else tape
			if source.has(t):
				_apply(source[t])
			ticks += 1
		return false
	if has_game_tape or lockstep != null:
		# before the networked game: the lobby's tape (or, from the command line, nothing)
		if tape.has(lobby_ticks) and has_game_tape:
			_apply(tape[lobby_ticks])
		lobby_ticks += 1
		if lobby_ticks > LOBBY_LIMIT:
			push_error("replay: the networked game did not start within %d ticks" % LOBBY_LIMIT)
			_dump()
			return true
		return false
	if ticks >= max_ticks:
		_dump()
		return true
	if tape.has(ticks):
		_apply(tape[ticks])
	ticks += 1
	return false


func _dump() -> void:
	var state := {}
	for n in _walk(scene):
		if n.has_method("quantum_state"):
			state[String(scene.get_path_to(n))] = n.quantum_state()
	var txt := JSON.stringify(state, "", true)
	if out_path == "":
		print(txt)
		return
	var f := FileAccess.open(out_path, FileAccess.WRITE)
	if f == null:
		push_error("replay: cannot write " + out_path)
		return
	f.store_string(txt)


func _walk(n: Node) -> Array:
	var out := [n]
	for c in n.get_children():
		out += _walk(c)
	return out
