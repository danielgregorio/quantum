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
#   {"op": "map"}     the scene's tilemap as a grid of what is solid ("#"), one-way ("-") or open (".")
#   {"op": "view"}    the screen as text at the map's cell size: walls, characters, things, with a legend
#   {"op": "frame", "path": "/tmp/x.png"}   the real picture (a session with a display only)
#   {"op": "tape"}    the session's inputs so far, as a replay tape ({tick: [[action, pressed], ["cursor", [x, y]]]})
#   {"op": "replay", "tape": {...}, "ticks": N, "held": [...]}   runs to tick N applying a tape: how a
#                     snapshot is restored, in a fresh game, by the determinism every replay test relies on
#   {"op": "end"}
# Every answer to an act or an until carries the events of its ticks: what
# the runtime reported (Q.event: touch, hit, step, bump, spawn, destroy,
# damage, death, sound, scene, say, said, choose, pause, resume) and every
# change of a scene's or the game's variable ("set": name, from, to). An
# answer after a scene change carries the new scene's map.
# What the agent may do is what a player may do: press and release the
# game's actions and point its cursor. Nothing else in the game is reachable.
#
# A condition, checked after every tick of an until:
#   {"path": "player.col", "op": "==", "value": 11}   (==, !=, <, <=, >, >=; "truthy", "falsy")
#   {"changed": "scene"}                              (differs from when the until began)
#   {"event": "say"} / {"event": "touch", "with": "key"}  (one happened during the until)
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
var q: Node = null              # the Q autoload, which records the events
var vars_before: Dictionary = {}  # the variables after the last tick, for the "set" events
var scene_before := ""
var map_sent := ""               # the scene whose map the agent has
var log := {}                    # tick -> the input changes made on it: the session as a replay tape
var replay_tape := {}            # tick -> input changes to make, while a "replay" runs


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
	if q == null:
		q = root.get_node_or_null("Q")
		if q != null:
			q.tracing = true
	_note_sets()
	if not taps.is_empty() and request.has("_first_done"):
		for a in taps:
			if not held.has(a):
				_release(a)
		taps = []
	# Every frame this returns false from runs one tick of the game, so a frame
	# either runs a tick that was asked for or waits here for the next request.
	if run_left > 0 and request.get("op") == "until" and request.has("_first_done") \
			and _holds(request.get("condition", {}), observation()):
		_finish("condition")
	if run_left > 0:
		_tick()
		return false
	if not request.is_empty():
		_finish("max_ticks" if request.get("op") == "until" else "ticks")
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
				_tick()
				return false
			"map":
				_answer({"tick": ticks, "map": game_map()})
			"tape":
				_answer({"tick": ticks, "tape": log, "held": held.keys()})
			"replay":
				if ticks != 0:
					_answer({"error": "a replay starts a fresh game, at tick 0"})
					continue
				replay_tape = {}
				var given: Dictionary = req.get("tape", {})
				for k in given.keys():
					replay_tape[int(k)] = given[k]
				request = {"op": "replay"}
				run_left = maxi(0, int(req.get("ticks", 0)))
				for a in req.get("held", []):
					held[str(a)] = true
				if run_left == 0:
					_finish("replayed")
					continue
				_tick()
				return false
			"view":
				_answer(view())
			"frame":
				_answer(frame(str(req.get("path", "user://frame.png"))))
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
		_release(str(a))
	for a in req.get("press", []):
		held[str(a)] = true
		_press(str(a))
	holds = []
	for a in req.get("hold", []):
		holds.append(str(a))
		_press(str(a))
	taps = []
	for a in req.get("tap", []):
		taps.append(str(a))
		_press(str(a))
	if req.has("cursor"):
		var c: Array = req["cursor"]
		_cursor(float(c[0]), float(c[1]))
	if str(req["op"]) == "until":
		run_left = maxi(0, int(req.get("max_ticks", 600)))
		until_start = observation()
	else:
		run_left = maxi(0, int(req.get("ticks", 1)))
	return ""


# Every input change goes through these, so the session is a tape (the log)
# that replays the same game.
func _press(a: String) -> void:
	Input.action_press(a)
	_log([a, true])


func _release(a: String) -> void:
	Input.action_release(a)
	_log([a, false])


func _cursor(x: float, y: float) -> void:
	root.get_node("Q").tape_cursor = Vector2(x, y)
	_log(["cursor", [x, y]])


func _log(e: Array) -> void:
	var at: Array = log.get(ticks, [])
	at.append(e)
	log[ticks] = at


func _tick() -> void:
	if replay_tape.has(ticks):
		for e in replay_tape[ticks]:
			if e[0] == "cursor":
				_cursor(float(e[1][0]), float(e[1][1]))
			elif e[1]:
				_press(str(e[0]))
			else:
				_release(str(e[0]))
	if q != null:
		q.event_tick = ticks
	run_left -= 1
	ticks += 1
	request["_first_done"] = true


# A variable of the scene or the game that changed on the tick just run is a
# "set" event; a scene change is reported by the runtime ("scene") instead.
func _note_sets() -> void:
	var now := _vars()
	var name_ := _scene_name()
	if name_ == scene_before and q != null and q.tracing:
		for k in now.keys():
			if vars_before.has(k) and JSON.stringify(now[k]) != JSON.stringify(vars_before[k]):
				var e := {"kind": "set", "name": k, "from": vars_before[k], "to": now[k], "tick": ticks - 1}
				if q.events.size() < 500:
					q.events.append(e)
	vars_before = now
	scene_before = name_


func _vars() -> Dictionary:
	var out := {}
	var s := _scene_node()
	if s != null and s.has_method("_q_state"):
		var own: Dictionary = s._q_state()
		for k in own.keys():
			out[k] = own[k]
	var g := root.get_node_or_null("G")
	if g != null and g.has_method("quantum_state"):
		var game: Dictionary = g.quantum_state()
		for k in game.keys():
			out["game." + str(k)] = game[k]
	return out


func _scene_node() -> Node:
	for n in _walk(scene):
		if n.has_method("q_pause"):
			return n
	return null


func _scene_name() -> String:
	var s := _scene_node()
	return String(s.name) if s != null else ""


func _finish(why: String) -> void:
	for a in holds:
		if not held.has(a):
			_release(a)
	holds = []
	if request.get("op") == "replay":
		why = "replayed"
		# the changes on the last tick itself (a hold let go as its request ended) are part of it
		for e in replay_tape.get(ticks, []):
			if e[0] == "cursor":
				_cursor(float(e[1][0]), float(e[1][1]))
			elif e[1]:
				_press(str(e[0]))
			else:
				_release(str(e[0]))
		replay_tape = {}
		if q != null:
			q.events.clear()   # what happened on the way back is not news
	var obs := observation()
	obs["stopped"] = why
	if q != null:
		obs["events"] = q.events.duplicate()
		if q.events_dropped > 0:
			obs["events_dropped"] = q.events_dropped
		q.events.clear()
		q.events_dropped = 0
	if obs["scene"] != map_sent:
		map_sent = obs["scene"]
		obs["map"] = game_map()
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
	if cond.has("event"):
		for e in (q.events if q != null else []):
			if e["kind"] != str(cond["event"]):
				continue
			var all_match := true
			for k in cond.keys():
				if k != "event" and (not e.has(k) or str(e[k]) != str(cond[k])):
					all_match = false
			if all_match:
				return true
		return false
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


# --- the map, the view, the picture ---

func _tilemap() -> Node:
	var s := _scene_node()
	return s.get_node_or_null("Tilemap") if s != null else null


# The scene's tilemap as rows of text: "#" a tile that stops (a layer with
# collision, the tile not shape="none"), "-" one a body stands on from above
# only, "." open. null for a scene without a tilemap.
func game_map():
	var map := _tilemap()
	if map == null:
		return null
	var rows := []
	for y in map.rows_count:
		var row := ""
		for x in map.columns:
			row += _cell(map, Vector2i(x, y))
		rows.append(row)
	return {"tile": map.tile, "columns": map.columns, "rows": map.rows_count, "cells": rows}


func _cell(map: Node, c: Vector2i) -> String:
	var mark := "."
	for layer in map.get_children():
		if not (layer is TileMapLayer) or layer.tile_set.get_physics_layers_count() == 0:
			continue
		var data: TileData = layer.get_cell_tile_data(c)
		if data == null or data.get_collision_polygons_count(0) == 0:
			continue
		if data.is_collision_polygon_one_way(0, 0):
			mark = "-"
		else:
			return "#"
	return mark


# What is on the screen, as text, one character a cell of the map's size (16
# px without a map): the map's marks, then the things (the first letter of
# their tag) and the characters (the first letter of their name, upper case;
# "@" for the one the camera follows). The legend says which is which.
func view() -> Dictionary:
	var s := _scene_node()
	if s == null:
		return {"error": "no scene"}
	var map := _tilemap()
	var cell := float(map.tile) if map != null else 16.0
	var size := Vector2(float(ProjectSettings.get_setting("display/window/size/viewport_width", 256)),
		float(ProjectSettings.get_setting("display/window/size/viewport_height", 224)))
	var top_left := Vector2.ZERO
	var cam = s.get("q_camera")
	if cam != null and is_instance_valid(cam):
		top_left = cam.get_screen_center_position() - size / 2.0
	var c0 := Vector2i(floori(top_left.x / cell), floori(top_left.y / cell))
	var cols := int(ceil(size.x / cell)) + (1 if fmod(top_left.x, cell) != 0.0 else 0)
	var rows := int(ceil(size.y / cell)) + (1 if fmod(top_left.y, cell) != 0.0 else 0)
	var grid := []
	for y in rows:
		var line := []
		for x in cols:
			var c := c0 + Vector2i(x, y)
			if map != null and c.x >= 0 and c.y >= 0 and c.x < map.columns and c.y < map.rows_count:
				line.append(_cell(map, c))
			else:
				line.append(" " if map != null else ".")
		grid.append(line)
	var legend := {}
	var followed = cam.get_parent() if cam != null and is_instance_valid(cam) else null
	var marks := []
	for n in s.get_children():
		if not (n is Node2D) or n.is_queued_for_deletion():
			continue
		var letter := ""
		var label := ""
		if n.is_in_group("q_thing"):
			label = str(n.tag)
			letter = label.left(1).to_lower()
		elif n.is_in_group("q_named"):
			label = String(n.name)
			letter = "@" if n == followed else label.left(1).to_upper()
		else:
			continue
		marks.append([n, letter, label])
	for m in marks:   # things first, characters over them
		if m[1] == m[1].to_lower() and m[1] != "@":
			_put(grid, m[0], m[1], c0, cell)
	for m in marks:
		if not (m[1] == m[1].to_lower() and m[1] != "@"):
			_put(grid, m[0], m[1], c0, cell)
	for m in marks:
		var names: Array = legend.get(m[1], [])
		if not m[2] in names:
			names.append(m[2])
		legend[m[1]] = names
	var text := []
	for line in grid:
		text.append("".join(line))
	return {"tick": ticks, "scene": _scene_name(), "cell": cell, "origin": [c0.x, c0.y], "view": text,
		"legend": legend}


func _put(grid: Array, n: Node2D, letter: String, c0: Vector2i, cell: float) -> void:
	var c := Vector2i(floori(n.position.x / cell), floori(n.position.y / cell)) - c0
	if c.y >= 0 and c.y < grid.size() and c.x >= 0 and c.x < grid[c.y].size():
		grid[c.y][c.x] = letter


# The picture on the screen, saved as a PNG: only with a display (a session
# opened with frames), as headless Godot draws nothing.
func frame(path: String) -> Dictionary:
	if DisplayServer.get_name() == "headless":
		return {"error": "no picture in a headless session: open it with frames=True"}
	var img := root.get_viewport().get_texture().get_image()
	if img == null or img.is_empty():
		return {"error": "nothing drawn yet"}
	var err := img.save_png(path)
	if err != OK:
		return {"error": "cannot write " + path}
	return {"tick": ticks, "frame": path, "width": img.get_width(), "height": img.get_height()}
