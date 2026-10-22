extends SceneTree
# The game as `quantum run game.q --watch` plays it: a person plays, and when
# the .q changes the game comes back with the new build where it was.
#
# Run by quantum/runtime/game_watch.py:
#   godot --path <project> -s <this file> -- --tape-out=<json> --stamp=<file> [--resume=<json>] [--dump=<json>]
#
# It records what the person presses, tick by tick, as a replay tape (the
# game's actions, and where the mouse is, which a qg:cursor reads), from the
# first tick. When the
# stamp file appears (the watcher writes it after a new build), it writes the
# tape and the ticks played to --tape-out and quits. Started again with
# --resume, it plays that tape first, many ticks a frame (the lockstep's
# catching up), as a replay does: the same inputs on the new rules, to the
# same tick; then the person plays on, and the recording goes on from there.
# A replay is the same game only from the same saves: the watcher gives every
# run the same fresh --persist-dir. With --dump, the state as the replay
# dumps it is written too as it quits (the tests compare the two).

const FAST := 16   # ticks a frame while the tape is played again

var ticks := 0
var tape := {}            # tick -> the input changes on it: what was played (and is being recorded)
var resume := {}          # tick -> the changes to make, while the tape is played again
var resume_until := 0     # the tick the last run had reached
var tape_out := ""
var stamp := ""
var dump := ""
var scene: Node
var _was := {}            # action -> pressed, as last recorded
var _mouse = null         # the mouse as last recorded
var _actions: Array = []


func _initialize() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--tape-out="):
			tape_out = a.substr(11)
		elif a.begins_with("--stamp="):
			stamp = a.substr(8)
		elif a.begins_with("--resume="):
			_read(a.substr(9))
		elif a.begins_with("--dump="):
			dump = a.substr(7)
	var main: String = ProjectSettings.get_setting("application/run/main_scene", "")
	scene = load(main).instantiate()
	root.add_child(scene)
	for action in InputMap.get_actions():
		if not String(action).begins_with("ui_"):
			_actions.append(String(action))
	_actions.sort()
	if resume_until > 0:
		_speed(FAST)


func _read(path: String) -> void:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		return
	var data = JSON.parse_string(f.get_as_text())
	if typeof(data) != TYPE_DICTIONARY:
		return
	for k in data.get("tape", {}).keys():
		resume[int(k)] = data["tape"][k]
	resume_until = int(data.get("ticks", 0))


func _speed(times: int) -> void:
	var q := root.get_node_or_null("Q")
	if q != null:
		q.catch_up = times
		q.apply_clock()


# Before the nodes' own tick, as the replay applies its tape.
func _physics_process(_delta: float) -> bool:
	if stamp != "" and FileAccess.file_exists(stamp):
		DirAccess.remove_absolute(stamp)
		_write()
		return true   # quit: the watcher starts the new build
	var q := root.get_node_or_null("Q")
	if ticks < resume_until:
		for ev in resume.get(ticks, []):
			if ev[0] == "mouse":
				q.tape_mouse = Vector2(ev[1][0], ev[1][1])   # where the mouse was: the cursors read it as theirs
			elif ev[1]:
				Input.action_press(ev[0])
			else:
				Input.action_release(ev[0])
		tape[ticks] = resume.get(ticks, [])
		if tape[ticks].is_empty():
			tape.erase(ticks)
		ticks += 1
		return false
	if resume_until > 0 and ticks == resume_until:
		# where the last run was: the person plays on. What the tape held is let go (and recorded so,
		# for the next run), the real mouse comes back, at the usual speed.
		_speed(1)
		_mouse = q.mouse_seen
		q.tape_mouse = null
		for action in _actions:
			_was[action] = Input.is_action_pressed(action)
			Input.action_release(action)
	_record(q)
	ticks += 1
	return false


# What changed since the last tick: an action pressed or let go on this one;
# the mouse moved on the last one (as the cursors saw it then).
func _record(q: Node) -> void:
	if q != null and q.mouse_seen != null and q.mouse_seen != _mouse and ticks > 0:
		_mouse = q.mouse_seen
		var before: Array = tape.get(ticks - 1, [])
		before.append(["mouse", [_mouse.x, _mouse.y]])
		tape[ticks - 1] = before
	var changes := []
	for action in _actions:
		var now := Input.is_action_pressed(action)
		if now != bool(_was.get(action, false)):
			changes.append([action, now])
			_was[action] = now
	if not changes.is_empty():
		tape[ticks] = changes


func _write() -> void:
	if dump != "":
		var state := {}
		for n in _walk(scene):
			if n.has_method("quantum_state"):
				state[String(scene.get_path_to(n))] = n.quantum_state()
		var d := FileAccess.open(dump, FileAccess.WRITE)
		if d != null:
			d.store_string(JSON.stringify(state, "", true))
			d.close()
	if tape_out == "":
		return
	var out := {}
	for k in tape.keys():
		out[str(k)] = tape[k]
	var f := FileAccess.open(tape_out, FileAccess.WRITE)
	if f != null:
		f.store_string(JSON.stringify({"ticks": ticks, "tape": out}))
		f.close()


func _walk(n: Node) -> Array:
	var out := [n]
	for c in n.get_children():
		out += _walk(c)
	return out
