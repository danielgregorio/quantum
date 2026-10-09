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
var out_path := ""
var scene: Node


func _initialize() -> void:
	var tape_path := ""
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--ticks="):
			max_ticks = int(a.substr(8))
		elif a.begins_with("--tape="):
			tape_path = a.substr(7)
		elif a.begins_with("--out="):
			out_path = a.substr(6)
	if tape_path != "":
		var f := FileAccess.open(tape_path, FileAccess.READ)
		if f == null:
			push_error("replay: cannot read the tape at " + tape_path)
			quit(2)
			return
		var data = JSON.parse_string(f.get_as_text())
		if typeof(data) != TYPE_DICTIONARY:
			push_error("replay: the tape is not a JSON object")
			quit(2)
			return
		for k in data.keys():
			tape[int(k)] = data[k]
	var main: String = ProjectSettings.get_setting("application/run/main_scene", "")
	if main == "":
		push_error("replay: the project has no main scene")
		quit(2)
		return
	scene = load(main).instantiate()
	root.add_child(scene)


# MainLoop runs this before the nodes' _physics_process of the same tick, so
# when ticks == max_ticks the scene has run exactly max_ticks ticks.
func _physics_process(_delta: float) -> bool:
	# Under qg:multiplayer (--q-host / --q-join) the game's tick is the
	# lockstep's, which stalls while a peer's input is late: the tape and
	# the count follow it, and the tape presses raw_<action> like a key.
	var lockstep: Node = scene.get("lockstep") if "lockstep" in scene else null
	if lockstep != null:
		if not lockstep.started or lockstep.desynced:
			if lockstep.desynced:
				_dump()
				return true
			return false
		var t: int = lockstep.tick
		if t >= max_ticks or (lockstep.ended and lockstep.stalled()):
			_dump()
			return true
		if t == ticks:
			if tape.has(t):
				for ev in tape[t]:
					if ev[0] == "cursor":
						root.get_node("Q").tape_cursor = Vector2(ev[1][0], ev[1][1])
					elif ev[1]:
						Input.action_press("raw_" + ev[0])
					else:
						Input.action_release("raw_" + ev[0])
			ticks += 1
		return false
	if ticks >= max_ticks:
		_dump()
		return true
	if tape.has(ticks):
		for ev in tape[ticks]:
			if ev[0] == "cursor":
				root.get_node("Q").tape_cursor = Vector2(ev[1][0], ev[1][1])
			elif ev[1]:
				Input.action_press(ev[0])
			else:
				Input.action_release(ev[0])
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
