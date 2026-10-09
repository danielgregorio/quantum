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


func _ready() -> void:
	rng.seed = q_seed
	if q_camera != null:
		q_camera.make_current()


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
	for n in get_tree().get_nodes_in_group("q_thing"):
		if n.get_parent() == self and not n.is_queued_for_deletion():
			things[n.tag] = int(things.get(n.tag, 0)) + 1
			# A thing with a name of its own (qg:instance name=) is reported by it.
			if n.name != n.prefab_name:
				named[n.name] = {"x": snappedf(n.position.x, 0.01), "y": snappedf(n.position.y, 0.01)}
	state["nodes"] = nodes
	state["things"] = things
	state["named"] = named
	state["sounds"] = Q.sounds_played.duplicate()
	state["game"] = G.quantum_state()
	return state


# The qg:on-input handlers of the scene: {action: method name}.
var q_on_input: Dictionary = {}


func _physics_process(_delta: float) -> void:
	for action in q_on_input.keys():
		if Input.is_action_just_pressed(action):
			call(q_on_input[action], null, null)


# Below this y a character has fallen out of the level (qg:on-fall).
func q_fall_line() -> float:
	return q_fall_y
