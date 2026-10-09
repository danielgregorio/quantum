extends Node
# The root of every Quantum game: reads game.json, registers the inputs and
# builds the first scene. The scene tree it builds is the whole game; the
# compiled scripts (scripts/*.gd) only hold the game's logic.

const SceneBuilder := preload("res://addons/quantum/scene_builder.gd")

var spec: Dictionary = {}
var current_scene: Node = null


func _ready() -> void:
	var f := FileAccess.open("res://game.json", FileAccess.READ)
	if f == null:
		push_error("quantum: game.json is missing")
		return
	spec = JSON.parse_string(f.get_as_text())
	_register_inputs(spec.get("inputs", {}))
	go_to_scene(spec["initial"])


func _register_inputs(inputs: Dictionary) -> void:
	for action in inputs.keys():
		if not InputMap.has_action(action):
			InputMap.add_action(action)
		for key_name in inputs[action]:
			var ev := InputEventKey.new()
			ev.physical_keycode = OS.find_keycode_from_string(key_name)
			InputMap.action_add_event(action, ev)


func go_to_scene(scene_name: String) -> void:
	if not spec["scenes"].has(scene_name):
		push_error("quantum: no scene named " + scene_name)
		return
	if current_scene != null:
		if current_scene.name == scene_name and current_scene.is_queued_for_deletion():
			return
		remove_child(current_scene)
		current_scene.queue_free()
		current_scene = null
	var scene_spec: Dictionary = spec["scenes"][scene_name]
	current_scene = SceneBuilder.build(spec, scene_spec)
	current_scene.name = scene_name
	add_child(current_scene)
