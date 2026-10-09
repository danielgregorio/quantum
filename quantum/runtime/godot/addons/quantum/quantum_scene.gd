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
var q_camera: Camera2D = null
var q_fall_y: float = 100000.0
var rng := RandomNumberGenerator.new()


var q_on_death: Dictionary = {}   # tag -> handler, from qg:on-death of= in the scene
var _shake_frames: int = 0
var _shake_strength: float = 0.0


func _ready() -> void:
	add_to_group("q_scene")
	rng.seed = q_seed
	if q_camera != null:
		q_camera.make_current()
	if has_method("_q_enter"):
		call("_q_enter")


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
		position = Vector2(rng.randf_range(-_shake_strength, _shake_strength),
			rng.randf_range(-_shake_strength, _shake_strength)) if _shake_frames > 0 else Vector2.ZERO


# Overridden by the compiled script: the scene's q:set variables.
func _q_state() -> Dictionary:
	return {}


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
			# A thing with a name of its own (qg:instance name=) is reported by it.
			if n.name != n.prefab_name:
				named[n.name] = {"x": snappedf(n.position.x, 0.01), "y": snappedf(n.position.y, 0.01)}
	state["nodes"] = nodes
	state["things"] = things
	state["named"] = named
	where.sort()
	state["where"] = where
	state["sounds"] = Q.sounds_played.duplicate()
	var menus := []
	for m in get_tree().get_nodes_in_group("q_menu"):
		if m.get_parent() == self:
			menus.append(m.focus)
	if not menus.is_empty():
		state["menus"] = menus
	state["game"] = G.quantum_state()
	return state


# The qg:on-input handlers of the scene: {action: method name}.
var q_on_input: Dictionary = {}
# The qg:on-select handlers: {"0": any player, "2": player 2...}; and the qg:paths: {name: points}.
var q_on_select: Dictionary = {}
var q_cursors: Array = []
var q_paths: Dictionary = {}


func _physics_process(_delta: float) -> void:
	for action in q_on_input.keys():
		if Q.tapped(action):
			call(q_on_input[action], null, null)
	for cursor in q_cursors:
		var p: int = cursor.player
		var select: String = "select" if p == 1 else "p%d_select" % p
		if not Q.tapped(select):
			continue
		var handler = q_on_select.get(str(p), q_on_select.get("0"))
		if handler == null:
			continue
		var at: Dictionary = cursor.where()
		var other = Q.thing_at(self, "", at["x"], at["y"])
		call(handler, at, other)


# Below this y a character has fallen out of the level (qg:on-fall).
func q_fall_line() -> float:
	return q_fall_y
