extends SceneTree
# The play protocol's driver (PLAN_PLAY_PROTOCOL.md): a game an agent plays.
#
# Run by quantum/runtime/godot_play.py:
#   godot --headless --fixed-fps 60 --path <project> -s <this file> -- [--persist-dir=<dir>]
#
# It reads one request per line on stdin (JSON) and answers each with one
# line on stdout: "QPP " and JSON (Godot prints other things there too). The
# game stands still while it waits for a request; an act runs exactly the
# ticks it asks for, at the fixed physics step, as the replay does, so the
# same requests give the same game.
#
# Requests:
#   {"op": "observe"}
#   {"op": "act", "ticks": N, "hold": [...], "tap": [...], "press": [...], "release": [...], "cursor": [x, y]}
#   {"op": "until", "max_ticks": N, "condition": {...}, ...the same actions as act}
#   {"op": "end"}
# What the agent may do is what a player may do: press and release the
# game's actions and point its cursor. Nothing else in the game is reachable.
#
# A condition, checked after every tick of an until:
#   {"path": "player.col", "op": "==", "value": 11}   (==, !=, <, <=, >, >=; "truthy", "falsy")
#   {"changed": "scene"}                              (differs from when the until began)
#   {"any": [...]} / {"all": [...]}
# A path is looked up in the observation, then in its state, the state's
# nodes, the game's state, and the screen's views by kind ("dialogue.text").

var scene: Node
var ticks := 0                # physics ticks run since the start
var run_left := 0             # ticks still to run for the request being served
var request: Dictionary = {}  # the request being served
var holds: Array = []         # released when the request is done
var taps: Array = []          # released after the request's first tick
var held: Dictionary = {}     # pressed by "press", until a "release"
var until_start: Dictionary = {}
var ended := false


func _initialize() -> void:
	var main: String = ProjectSettings.get_setting("application/run/main_scene", "")
	if main == "":
		_answer({"error": "the project has no main scene"})
		quit(2)
		return
	scene = load(main).instantiate()
	root.add_child(scene)


func _physics_process(_delta: float) -> bool:
	if ended:
		return true
	if not taps.is_empty() and request.has("_first_done"):
		for a in taps:
			if not held.has(a):
				Input.action_release(a)
		taps = []
	# Every frame this returns false from runs one tick of the game, so a frame
	# either runs a tick that was asked for or waits here for the next request.
	if run_left > 0 and request.get("op") == "until" and request.has("_first_done") \
			and _holds(request.get("condition", {}), observation()):
		_finish("condition")
	if run_left > 0:
		run_left -= 1
		ticks += 1
		request["_first_done"] = true
		return false
	if not request.is_empty():
		_finish("ticks" if request.get("op") == "act" else "max_ticks")
		if ended:
			return true
	# wait for the next request that runs ticks; answer the ones that do not
	while true:
		var line := OS.read_string_from_stdin(1 << 20).strip_edges()
		if line == "":
			ended = true   # stdin closed: the agent is gone
			return true
		var parsed = JSON.parse_string(line)
		if typeof(parsed) != TYPE_DICTIONARY:
			_answer({"error": "a request is a JSON object: " + line.left(80)})
			continue
		var req: Dictionary = parsed
		match str(req.get("op", "")):
			"observe":
				_answer(observation())
			"end":
				_answer({"ended": true, "tick": ticks})
				ended = true
				return true
			"act", "until":
				var error := _start(req)
				if error != "":
					_answer({"error": error})
					continue
				if run_left == 0:
					_finish("ticks")
					continue
				run_left -= 1
				ticks += 1
				request["_first_done"] = true
				return false
			_:
				_answer({"error": "no such request: " + str(req.get("op", ""))})
	return false


# The request's actions, applied on its first tick; an error, or "".
func _start(req: Dictionary) -> String:
	var known := {}
	for a in InputMap.get_actions():
		known[String(a)] = true
	for key in ["hold", "tap", "press", "release"]:
		for a in req.get(key, []):
			if not known.has(str(a)) or str(a).begins_with("ui_"):
				return "no such action: %s (the game's actions: %s)" % [a, ", ".join(controls())]
	request = req.duplicate(true)
	request.erase("_first_done")
	for a in req.get("release", []):
		held.erase(str(a))
		Input.action_release(str(a))
	for a in req.get("press", []):
		held[str(a)] = true
		Input.action_press(str(a))
	holds = []
	for a in req.get("hold", []):
		holds.append(str(a))
		Input.action_press(str(a))
	taps = []
	for a in req.get("tap", []):
		taps.append(str(a))
		Input.action_press(str(a))
	if req.has("cursor"):
		var c: Array = req["cursor"]
		root.get_node("Q").tape_cursor = Vector2(float(c[0]), float(c[1]))
	if str(req["op"]) == "until":
		run_left = maxi(0, int(req.get("max_ticks", 600)))
		until_start = observation()
	else:
		run_left = maxi(0, int(req.get("ticks", 1)))
	return ""


func _finish(why: String) -> void:
	for a in holds:
		if not held.has(a):
			Input.action_release(a)
	holds = []
	var obs := observation()
	obs["stopped"] = why
	request = {}
	run_left = 0
	_answer(obs)


func _answer(d: Dictionary) -> void:
	print("QPP " + JSON.stringify(d))


func controls() -> Array:
	var out := []
	for a in InputMap.get_actions():
		var name_ := String(a)
		if not name_.begins_with("ui_") and not name_.begins_with("raw_"):
			out.append(name_)
	out.sort()
	return out


# What a player knows by looking: the scene and its state (quantum_state(),
# as the replay reports it), what the screen shows to read and choose
# (quantum_view() of the HUD, the menus, the dialogue), and the actions.
func observation() -> Dictionary:
	var obs := {"tick": ticks, "scene": "", "state": {}, "screen": [], "held": held.keys(), "controls": controls()}
	for n in _walk(scene):
		if n.has_method("quantum_state") and n.has_method("q_pause"):
			obs["scene"] = String(n.name)
			obs["state"] = n.quantum_state()
		if n.has_method("quantum_view"):
			var v: Dictionary = n.quantum_view()
			if not v.is_empty():
				obs["screen"].append(v)
	return obs


func _walk(n: Node) -> Array:
	var out := [n]
	for c in n.get_children():
		out += _walk(c)
	return out


# --- conditions ---

func _holds(cond: Dictionary, obs: Dictionary) -> bool:
	if cond.has("any"):
		for c in cond["any"]:
			if _holds(c, obs):
				return true
		return false
	if cond.has("all"):
		for c in cond["all"]:
			if not _holds(c, obs):
				return false
		return true
	if cond.has("changed"):
		return JSON.stringify(lookup(obs, str(cond["changed"]))) != JSON.stringify(lookup(until_start, str(cond["changed"])))
	if cond.has("path"):
		var v = lookup(obs, str(cond["path"]))
		var op := str(cond.get("op", "truthy"))
		var w = cond.get("value")
		match op:
			"truthy":
				return _truthy(v)
			"falsy":
				return not _truthy(v)
			"==":
				return _same(v, w)
			"!=":
				return not _same(v, w)
		if not (v is float or v is int) or not (w is float or w is int):
			return false
		match op:
			"<":
				return v < w
			"<=":
				return v <= w
			">":
				return v > w
			">=":
				return v >= w
	return false


func _truthy(v) -> bool:
	if v == null:
		return false
	if v is bool:
		return v
	if v is float or v is int:
		return v != 0
	if v is String or v is Array or v is Dictionary:
		return not v.is_empty()
	return true


func _same(v, w) -> bool:
	if (v is float or v is int) and (w is float or w is int):
		return is_equal_approx(float(v), float(w))
	return JSON.stringify(v) == JSON.stringify(w)


# "player.col": the observation's own keys first, then the state, the
# state's nodes, the game's state; "dialogue.text": the screen's view of
# that kind.
func lookup(obs: Dictionary, path: String):
	var parts := path.split(".")
	var bases := [obs, obs.get("state", {}), obs.get("state", {}).get("nodes", {}),
		obs.get("state", {}).get("game", {})]
	var views := {}
	for v in obs.get("screen", []):
		if not views.has(v["kind"]):
			views[v["kind"]] = v
	bases.append(views)
	for base in bases:
		if base is Dictionary and base.has(parts[0]):
			var cur = base
			var ok := true
			for p in parts:
				if cur is Dictionary and cur.has(p):
					cur = cur[p]
				elif cur is Array and p.is_valid_int() and int(p) < cur.size():
					cur = cur[int(p)]
				else:
					ok = false
					break
			if ok:
				return cur
	return null
