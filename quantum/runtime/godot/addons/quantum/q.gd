extends Node
# Q: the helpers the compiled scripts call. An autoload (project.godot),
# so every script sees `Q`.
#
# Where GDScript's operators differ from Quantum's expression semantics
# (quantum/core/expressions.py), the compiler emits one of these instead.

var _sounds: Dictionary = {}   # name -> AudioStreamPlayer
var sounds_played: Array = []  # names, in order — the replay harness reads it


# `/` in Quantum is a float division, whatever the operands.
static func div(a, b):
	return float(a) / float(b)


# `//` floors, like Python.
static func floordiv(a, b):
	return floori(float(a) / float(b))


# `%` follows the divisor's sign, like Python.
static func mod(a, b):
	return fposmod(float(a), float(b))


# `len()` of a string, an array or a dictionary.
static func len(v) -> int:
	if v is String:
		return (v as String).length()
	if v is Array or v is Dictionary:
		return v.size()
	return 0


# Removes a thing from the scene at the end of the tick.
static func destroy(node) -> void:
	node = _thing(node)
	if node == null:
		return
	if node.has_method("quantum_destroy"):
		node.quantum_destroy()
	else:
		node.queue_free()


# Throws a character up `height` pixels (qg:bounce).
static func bounce(node, height: float) -> void:
	node = _thing(node)
	if node != null and node.has_method("bounce"):
		node.bounce(height)


# Puts a character back where it started the scene (qg:respawn).
static func respawn(node) -> void:
	node = _thing(node)
	if node != null and node.has_method("respawn"):
		node.respawn()


# Changes a character to one of its states (qg:become).
static func become(node, state: String) -> void:
	node = _thing(node)
	if node != null and node.has_method("become"):
		node.become(state)


# Places a prefab where `at` is, offset (qg:spawn).
static func spawn(scene: Node, prefab: String, at, dx: float, dy: float) -> Node:
	at = _thing(at)
	if at == null or not (at is Node2D):
		return null
	var builder = load("res://addons/quantum/scene_builder.gd")
	return builder.instance(scene.q_game, scene, prefab, (at as Node2D).position + Vector2(dx, dy), true)


# Replaces a thing with another prefab, in its place (qg:swap).
static func swap(scene: Node, node, prefab: String) -> Node:
	node = _thing(node)
	if node == null or not (node is Node2D):
		return null
	var builder = load("res://addons/quantum/scene_builder.gd")
	var made = builder.instance(scene.q_game, scene, prefab, (node as Node2D).position, true)
	destroy(node)
	return made


# The other thing's position becomes where the character respawns (qg:checkpoint).
static func checkpoint(node, at) -> void:
	node = _thing(node)
	at = _thing(at)
	if node != null and at != null and node.has_method("set_checkpoint") and at is Node2D:
		node.set_checkpoint((at as Node2D).position)


# A collision hands the handler a hitbox area; the thing is its owner.
static func _thing(node):
	if node == null or not is_instance_valid(node):
		return null
	if node.has_method("quantum_owner"):
		return node.quantum_owner()
	return node


# --- sounds (an instance method: Q is an autoload node) ---

func load_sounds(sounds: Dictionary) -> void:
	for name_ in sounds.keys():
		var src: String = sounds[name_]["src"]
		var stream: AudioStream = null
		var path := ProjectSettings.globalize_path("res://" + src)
		if src.ends_with(".ogg"):
			stream = AudioStreamOggVorbis.load_from_file(path)
		elif src.ends_with(".wav"):
			stream = AudioStreamWAV.load_from_file(path)
		if stream == null:
			push_warning("quantum: cannot load the sound " + src)
			continue
		var player := AudioStreamPlayer.new()
		player.name = name_
		player.stream = stream
		add_child(player)
		_sounds[name_] = player


func play(name_: String) -> void:
	sounds_played.append(name_)
	var player: AudioStreamPlayer = _sounds.get(name_)
	if player != null:
		player.play()
