extends Node2D
# The base of every compiled scene script (scripts/scene_*.gd extends this).
#
# The compiled script adds the scene's state (its q:sets) as properties,
# its q:functions as methods and its handlers as methods; this base holds
# what every scene shares: the seeded random source and the state report
# the replay harness reads (quantum_state).

var q_spec: Dictionary = {}
var q_game: Dictionary = {}
var q_seed: int = 0
var q_entered := false   # _q_enter has run: the scene's computed q:sets have their values
var q_camera: Camera2D = null
var q_views: Array = []   # qg:camera player=: [camera, its view's size] each (split.gd); [] for one camera
var q_fall_y: float = 100000.0
var rng := RandomNumberGenerator.new()


var q_on_death: Dictionary = {}   # tag -> handler, from qg:on-death of= in the scene
var _shake_frames: int = 0
var _shake_strength: float = 0.0
# The shake runs in _process, once per drawn frame, so it has a random source of
# its own: drawing at another rate on another machine must not move the scene's.
var _shake_rng := RandomNumberGenerator.new()


func _ready() -> void:
	add_to_group("q_scene")
	if q_spec.has("seed_method"):
		q_seed = int(call(q_spec["seed_method"]))   # seed="{...}": a world's number
	rng.seed = q_seed
	if Q.slow != 1.0:
		Q.time_scale(1.0)   # a new scene starts at the usual speed
	if q_camera != null:
		q_camera.make_current()
	if has_method("_q_enter"):
		call("_q_enter")
	q_entered = true


# A thing of the scene died (health 0): the scene's qg:on-death of= its tag.
func q_thing_died(thing: Node) -> void:
	var handler = q_on_death.get(thing.tag)
	if handler != null and has_method(handler):
		call(handler, null, thing)


# qg:shake: the scene jolts for a few frames. Cosmetic: nodes keep their
# positions, the scene itself moves.
func q_shake(frames: int, strength: float) -> void:
	_shake_frames = frames
	_shake_strength = strength


func _process(_delta: float) -> void:
	if _shake_frames > 0:
		_shake_frames -= 1
		position = Vector2(_shake_rng.randf_range(-_shake_strength, _shake_strength),
			_shake_rng.randf_range(-_shake_strength, _shake_strength)) if _shake_frames > 0 else Vector2.ZERO


# qg:pause: everything that plays stops where it is — characters, things,
# timers, spawners (and the bodies leave the physics until resumed). The
# scene itself goes on, for qg:on-input; so do its menus and HUD (canvas
# layers) and the cursors that point at the menus.
var q_paused: bool = false


func q_pause(on: bool) -> void:
	if on == q_paused:
		return
	q_paused = on
	for c in get_children():
		if c is CanvasLayer or c.is_in_group("q_cursor") or c is Camera2D:
			continue   # a camera goes on: a qg:camera-to may be what paused the scene
		c.process_mode = Node.PROCESS_MODE_DISABLED if on else Node.PROCESS_MODE_INHERIT


# For the rollback: the scene's state (its q:sets) and its random source, and back.
func q_save() -> Dictionary:
	return {"vars": _q_state().duplicate(true), "rng": rng.state}


func q_load(d: Dictionary) -> void:
	for k in d["vars"].keys():
		var v = d["vars"][k]
		set(k, v.duplicate(true) if (v is Array or v is Dictionary) else v)
	rng.state = d["rng"]


# Overridden by the compiled script: the scene's q:set variables.
func _q_state() -> Dictionary:
	return {}


# A thing a qg:tween has touched also says how it looks: its picture's scale
# (and its height apart, when a scale-y made it differ) and rotation, and its
# alpha. One that visible= hides says so.
static func _look(n: Node, entry: Dictionary) -> void:
	if n is CanvasItem and not (n as CanvasItem).visible:
		entry["hidden"] = true
	if not n.has_meta("q_tweened"):
		return
	var tween = load("res://addons/quantum/tween.gd")
	for prop in ["scale", "rotation", "alpha"]:
		entry[prop] = snappedf(tween.read(n, prop), 0.001)
	var tall: float = snappedf(tween.read(n, "scale-y"), 0.001)
	if tall != entry["scale"]:
		entry["scale_y"] = tall
	var tint: Color = tween.read(n, "tint")
	if tint != Color.WHITE:
		entry["tint"] = tint.to_html(false)


# What the replay harness records: the state variables, and the position
# of every named node (characters), rounded so a dump reads clean.
func quantum_state() -> Dictionary:
	var state := _q_state()
	var nodes := {}
	for n in get_tree().get_nodes_in_group("q_named"):
		if n.get_parent() == self:
			var entry := {"x": snappedf(n.position.x, 0.01), "y": snappedf(n.position.y, 0.01)}
			if n.has_method("quantum_node_state"):
				entry.merge(n.quantum_node_state())
			_look(n, entry)
			nodes[n.name] = entry
	var things := {}
	var named := {}
	var where := []
	for n in get_tree().get_nodes_in_group("q_thing"):
		if n.get_parent() == self and not n.is_queued_for_deletion():
			things[n.tag] = int(things.get(n.tag, 0)) + 1
			var entry := [n.tag, snappedf(n.position.x, 0.1), snappedf(n.position.y, 0.1)]
			if "state" in n and n.state != "":
				entry.append(n.state)
			where.append(entry)
			# A thing with a name of its own (qg:instance name=) is reported by it; the
			# names Godot makes up for a second thing of the same prefab are not.
			if n.has_meta("q_named"):
				named[n.name] = {"x": snappedf(n.position.x, 0.01), "y": snappedf(n.position.y, 0.01)}
				if "doing" in n and n.doing != "":
					named[n.name]["doing"] = n.doing   # the part that moves an enemy of parts
				_look(n, named[n.name])
	state["nodes"] = nodes
	state["things"] = things
	state["named"] = named
	where.sort()
	state["where"] = where
	var map := get_node_or_null("Tilemap")
	if map != null and not map.changed.is_empty():
		state["tiles"] = map.changed.duplicate()   # the cells a qg:set-tile changed
	state["sounds"] = Q.sounds_played.duplicate()
	if q_paused:
		state["paused"] = true
	if q_talking() != "":
		state["talking"] = q_talking()
		state["line"] = get_node("Dialogue_" + q_talking()).line
	var menus := []
	for m in get_tree().get_nodes_in_group("q_menu"):
		if m.get_parent() == self:
			menus.append(m.focus)
	if not menus.is_empty():
		state["menus"] = menus
	state["game"] = G.quantum_state()
	return state


# The qg:on-input handlers of the scene: {action: method name}; on="release" ones apart.
var q_on_input: Dictionary = {}
var q_on_release: Dictionary = {}
var q_sequences: Array = []   # qg:on-input sequence=: [{steps, within, player, handler}]
# The qg:on-select handlers: {"0": any player, "2": player 2...}; and the qg:paths: {name: points}.
var q_on_select: Dictionary = {}
var q_cursors: Array = []
var q_paths: Dictionary = {}


func _physics_process(_delta: float) -> void:
	_screen()
	for s in q_sequences:
		if Q.sequence(_steps(s), int(s["within"])) and has_method(s["handler"]):
			call(s["handler"], null, null)
	for action in q_on_input.keys():
		if Q.tapped(action):
			call(q_on_input[action], null, null)
	for action in q_on_release.keys():
		if Q.released(action):
			call(q_on_release[action], null, null)
	for cursor in q_cursors:
		var p: int = cursor.player
		for action in _select_actions():
			if not Q.tapped(action if p == 1 else "p%d_%s" % [p, action]):
				continue
			var suffix: String = "" if action == "select" else ":" + action
			var handler = q_on_select.get(str(p) + suffix, q_on_select.get("0" + suffix))
			if handler == null:
				continue
			var at: Dictionary = cursor.where()
			var other = Q.thing_at(self, "", at["x"], at["y"])
			call(handler, at, other)


# The actions qg:on-select answers: select, and those of its action= (a right click).
var _select_actions_: Array = []


func _select_actions() -> Array:
	if _select_actions_.is_empty():
		for key in q_on_select.keys():
			var action: String = "select" if not ":" in str(key) else str(key).split(":")[1]
			if not action in _select_actions_:
				_select_actions_.append(action)
	return _select_actions_


# --- qg:on-screen-exit and qg:on-screen-enter ---
# Each tick, before anything moves, the scene looks at what has screen
# handlers (its own, or the scene's of= its tag) and compares where it is with
# where it was: on the screen, or beyond one of its edges. Only a change runs a
# handler, so a thing placed off the screen has not left it. The screen is the
# camera's view, worked out from the camera's own position in the game's ticks
# (not from what was drawn), or the scene when it has no camera.
var q_on_screen: Array = []   # the scene's own handlers, each of= a tag


func _screen() -> void:
	if q_paused:
		return
	var views := q_view_rects()
	for n in get_children():
		if not (n is Node2D) or not Q.alive(n):
			continue
		var own: Array = n.get_meta("q_on_screen", [])
		var theirs := []
		if n.is_in_group("q_thing"):
			for h in q_on_screen:
				if h["of"] == n.quantum_tag():
					theirs.append(h)
		if own.is_empty() and theirs.is_empty():
			continue
		var side := _beyond(n, views)
		if not n.has_meta("q_screen"):
			n.set_meta("q_screen", side)   # where it was placed: nothing happened yet
			continue
		var was: String = n.get_meta("q_screen")
		n.set_meta("q_screen", side)
		var on := ""
		var edge := ""
		if was == "" and side != "":
			on = "exit"
			edge = side
		elif was != "" and side == "":
			on = "enter"
			edge = was
		else:
			continue   # still on the screen, or still off it
		Q.event("screen", {"what": Q.who(n), "on": on, "side": edge})
		var caller: Object = P if n.is_in_group("q_thing") else self
		for h in own:
			if h["on"] == on and (h["side"] == "any" or h["side"] == edge) and caller.has_method(h["handler"]):
				caller.call(h["handler"], n, null)
		for h in theirs:
			if h["on"] == on and (h["side"] == "any" or h["side"] == edge) and has_method(h["handler"]):
				call(h["handler"], null, n)


# A sequence's steps as the player's actions: "forward" and "back" are right
# and left as that player's character faces now (left and right when it faces left).
func _steps(s: Dictionary) -> Array:
	var p := int(s["player"])
	var faces := 1
	for n in get_children():
		if n.get("player") == p and "facing" in n:
			var f = n.get("facing")
			faces = (-1 if f < 0 else 1) if f is int or f is float else (-1 if (f as Vector2).x < 0 else 1)
			break
	var out := []
	for step in s["steps"]:
		var a := str(step)
		if a == "forward":
			a = "right" if faces > 0 else "left"
		elif a == "back":
			a = "left" if faces > 0 else "right"
		out.append(a if p == 1 else "p%d_%s" % [p, a])
	return out


# The edge a node is beyond ("bottom", "top", "right", "left"), or "" on the
# screen: in a view. Off every view, the edge is the nearest view's.
static func _beyond(n: Node2D, views: Array) -> String:
	var size = n.get("hitbox_size")
	if not (size is Vector2):
		size = Vector2(8, 8)
	var r := Rect2(n.position - size / 2.0, size)
	var view: Rect2 = views[0]
	var best := INF
	for v in views:
		if r.intersects(v):
			return ""
		var d: float = ((v as Rect2).get_center() - n.position).length_squared()
		if d < best:
			best = d
			view = v
	if r.position.y >= view.end.y:
		return "bottom"
	if r.end.y <= view.position.y:
		return "top"
	if r.position.x >= view.end.x:
		return "right"
	return "left"


# What the screen shows of the scene, in scene pixels.
func q_view() -> Rect2:
	var size := Vector2(float(q_spec.get("width", 256)), float(q_spec.get("height", 224)))
	if q_camera == null or not is_instance_valid(q_camera):
		return Rect2(Vector2.ZERO, size)
	return _seen(q_camera, size)


# What each view shows (qg:camera player=: one a player), or the screen.
func q_view_rects() -> Array:
	if q_views.is_empty():
		return [q_view()]
	return q_views.map(func(v): return _seen(v[0], v[1]))


# The cameras of the scene: one, or one a player.
func q_cameras() -> Array:
	if not q_views.is_empty():
		return q_views.map(func(v): return v[0])
	return [q_camera] if q_camera != null and is_instance_valid(q_camera) else []


static func _seen(cam: Camera2D, size: Vector2) -> Rect2:
	var half := size / cam.zoom / 2.0
	var c := cam.position
	c.x = clampf(c.x, cam.limit_left + half.x, maxf(cam.limit_left + half.x, cam.limit_right - half.x))
	c.y = clampf(c.y, cam.limit_top + half.y, maxf(cam.limit_top + half.y, cam.limit_bottom - half.y))
	return Rect2(c - half, half * 2.0)


# The qg:dialogue open now (qg:say), or "".
func q_talking() -> String:
	for c in get_children():
		if c.has_method("is_open") and c.is_open():
			return c.dialogue_name
	return ""


# Below this y a character has fallen out of the level (qg:on-fall).
func q_fall_line() -> float:
	return q_fall_y
