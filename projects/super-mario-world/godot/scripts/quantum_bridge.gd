extends Node
## Quantum Bridge - Game API autoload
## Provides centralized game object management and utility functions.

var sprites: Dictionary = {}
var event_bus: Node
var game_state: Dictionary = {}

func save_game_state(data: Dictionary):
	game_state = data.duplicate()

func get_game_state() -> Dictionary:
	return game_state

func clear_game_state():
	game_state = {}

func _ready():
	event_bus = get_node("/root/QuantumEventBus")

func register_sprite(id: String, node: Node):
	sprites[id] = node

func destroy_sprite(id: String):
	if id in sprites:
		sprites[id].queue_free()
		sprites.erase(id)

func respawn(id: String, x: float, y: float):
	if id in sprites:
		sprites[id].position = Vector2(x, y)
		if sprites[id] is CharacterBody2D:
			sprites[id].velocity = Vector2.ZERO

func get_sprite(id: String) -> Node:
	if id in sprites:
		return sprites[id]
	return null

func emit_event(event_name: String, data: Dictionary = {}):
	if event_bus:
		event_bus.emit_event(event_name, data)

func camera_shake(intensity: float = 5.0, duration: float = 0.3):
	var cam = get_viewport().get_camera_2d()
	if cam and cam.has_method("shake"):
		cam.shake(intensity, duration)

func set_patrol_ai(id: String, speed: float):
	if id in sprites and sprites[id].has_method("set_patrol"):
		sprites[id].set_patrol(speed)

func kill_player(id: String):
	if id in sprites and sprites[id].has_method("die"):
		sprites[id].die()

func play_sound(id: String, opts: Dictionary = {}):
	var player = get_node_or_null("/root/Main/Sounds/" + id)
	if player and player is AudioStreamPlayer:
		if opts.has("volume"):
			player.volume_db = linear_to_db(opts["volume"])
		player.play()

func pause():
	get_tree().paused = true

func resume():
	get_tree().paused = false

func load_scene(scene_name: String):
	var path = "res://scenes/" + scene_name + ".tscn"
	get_tree().change_scene_to_file(path)

func iris_in(duration: float = 0.5):
	emit_event("iris_in", {"duration": duration})

func iris_out(duration: float = 0.5):
	emit_event("iris_out", {"duration": duration})

func save_state(key: String, value) -> void:
	var save_data: Dictionary = {}
	var path = "user://quantum_save.json"
	if FileAccess.file_exists(path):
		var f = FileAccess.open(path, FileAccess.READ)
		save_data = JSON.parse_string(f.get_as_text()) if f else {}
		if f: f.close()
	if save_data == null:
		save_data = {}
	save_data[key] = value
	var f = FileAccess.open(path, FileAccess.WRITE)
	if f:
		f.store_string(JSON.stringify(save_data))
		f.close()

func load_state(key: String, default_value = null):
	var path = "user://quantum_save.json"
	if not FileAccess.file_exists(path):
		return default_value
	var f = FileAccess.open(path, FileAccess.READ)
	if not f:
		return default_value
	var data = JSON.parse_string(f.get_as_text())
	f.close()
	if data is Dictionary and data.has(key):
		return data[key]
	return default_value
