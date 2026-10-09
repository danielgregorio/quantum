extends Node
# The root of every Quantum game: reads game.json, registers the inputs and
# builds the first scene. The scene tree it builds is the whole game; the
# compiled scripts (scripts/*.gd) only hold the game's logic.

const SceneBuilder := preload("res://addons/quantum/scene_builder.gd")
const Lockstep := preload("res://addons/quantum/lockstep.gd")

var spec: Dictionary = {}
var current_scene: Node = null
var lockstep: Node = null


func _ready() -> void:
	var f := FileAccess.open("res://game.json", FileAccess.READ)
	if f == null:
		push_error("quantum: game.json is missing")
		return
	spec = JSON.parse_string(f.get_as_text())
	_register_inputs(spec.get("inputs", {}))
	# qg:multiplayer, with --q-host=PORT or --q-join=HOST:PORT: the game waits
	# for every player, and the local keys only reach it through the lockstep
	var host := ""
	var port := -1
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--q-host="):
			port = int(a.substr(9))
		elif a.begins_with("--q-join="):
			var parts: PackedStringArray = a.substr(9).split(":")
			host = parts[0]
			port = int(parts[1]) if parts.size() > 1 else -1
	if spec.has("multiplayer") and port > 0:
		lockstep = Lockstep.new()
		add_child(lockstep)
		lockstep.setup(spec["multiplayer"], self, host, port)
		return
	go_to_scene(spec["initial"])


func _q_lockstep_ready() -> void:
	go_to_scene(spec["initial"])


func _register_inputs(inputs: Dictionary) -> void:
	for action in inputs.keys():
		if not InputMap.has_action(action):
			InputMap.add_action(action)
		for key in inputs[action]:
			if key is Dictionary and key.has("joy_button"):
				var jb := InputEventJoypadButton.new()
				jb.button_index = int(key["joy_button"])
				jb.device = int(key.get("device", 0))
				InputMap.action_add_event(action, jb)
			elif key is Dictionary and key.has("mouse_button"):
				var mb := InputEventMouseButton.new()
				mb.button_index = int(key["mouse_button"])
				InputMap.action_add_event(action, mb)
			elif key is Dictionary and key.has("joy_axis"):
				var ja := InputEventJoypadMotion.new()
				ja.axis = int(key["joy_axis"])
				ja.axis_value = float(key["value"])
				ja.device = int(key.get("device", 0))
				InputMap.action_add_event(action, ja)
			else:
				var ev := InputEventKey.new()
				ev.physical_keycode = OS.find_keycode_from_string(str(key))
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
	if G.has_method("_q_save"):
		G._q_save()


func _exit_tree() -> void:
	if G.has_method("_q_save"):
		G._q_save()
