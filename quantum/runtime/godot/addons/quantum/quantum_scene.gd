extends Node2D
# The base of every compiled scene script (scripts/scene_*.gd extends this).
#
# The compiled script adds the scene's state (its q:sets) as properties,
# its q:functions as methods and its handlers as methods; this base holds
# what every scene shares: the seeded random source and the state report
# the replay harness reads (quantum_state).

var q_spec: Dictionary = {}
var q_seed: int = 0
var q_camera: Camera2D = null
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
			nodes[n.name] = {"x": snappedf(n.position.x, 0.01), "y": snappedf(n.position.y, 0.01)}
	var items := 0
	for n in get_tree().get_nodes_in_group("q_item"):
		if n.get_parent() == self and not n.is_queued_for_deletion():
			items += 1
	state["nodes"] = nodes
	state["items"] = items
	return state
