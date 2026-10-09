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


# `str()` as Quantum writes a number: 7, not 7.0, for a whole one.
static func to_str(v) -> String:
	if v is float and v == floorf(v) and absf(v) < 1e15:
		return str(int(v))
	return str(v)


# `len()` of a string, an array or a dictionary.
static func len(v) -> int:
	if v is String:
		return (v as String).length()
	if v is Array or v is Dictionary:
		return v.size()
	return 0


# `a[start:end]` of a string or an array, like Python (null: from the start / to the end).
static func slice(v, start, end):
	var n: int = v.length() if v is String else v.size()
	var s: int = 0 if start == null else int(start)
	var e: int = n if end == null else int(end)
	if s < 0:
		s = maxi(0, n + s)
	if e < 0:
		e = maxi(0, n + e)
	s = mini(s, n)
	e = mini(e, n)
	if e <= s:
		return "" if v is String else []
	if v is String:
		return (v as String).substr(s, e - s)
	return (v as Array).slice(s, e)


# gd: attributes: properties of the Godot node a tag became, as game.json
# carries them ({name: {type, value}}), set as they are — nothing is
# interpreted here; the compiler checked them against Godot's reference.
static func apply_gd(node: Node, gd) -> void:
	if gd == null:
		return
	for name_ in gd.keys():
		var entry: Dictionary = gd[name_]
		var v = entry["value"]
		match str(entry["type"]):
			"Vector2": v = Vector2(v[0], v[1])
			"Vector2i": v = Vector2i(int(v[0]), int(v[1]))
			"Color": v = Color(v)
			"int": v = int(v)
			"float": v = float(v)
		node.set(name_, v)


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


# qg:deflect on a flying thing.
static func deflect_axis(node, axis: String) -> void:
	node = _thing(node)
	if node != null and node.has_method("deflect_axis"):
		node.deflect_axis(axis)


static func deflect_to(node, dx: float, dy: float) -> void:
	node = _thing(node)
	if node != null and node.has_method("deflect_to"):
		node.deflect_to(dx, dy)


# random(a, b) in an expression: a float in [a, b] from the scene's seeded
# source, so the same seed gives the same game. `ctx` is the scene script
# (self in its handlers) or P (a prefab handler): then the current scene's.
static func random(ctx, a: float, b: float) -> float:
	var scene = ctx
	if ctx == null or not ("rng" in ctx):
		var scenes: Array = Engine.get_main_loop().get_nodes_in_group("q_scene")
		scene = scenes[0] if scenes.size() > 0 else null
	if scene == null:
		return a
	return scene.rng.randf_range(a, b)


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


# Takes health from a thing (qg:damage).
static func damage(node, amount: int) -> void:
	node = _thing(node)
	if node != null and node.has_method("take_damage"):
		node.take_damage(amount)


# Places a prefab at a point of the scene, at the end of the tick.
static func spawn_at(scene: Node, prefab: String, at: Vector2) -> Node:
	var builder = load("res://addons/quantum/scene_builder.gd")
	return builder.instance(scene.q_game, scene, prefab, at, true)


# A puff of particles where a thing is (qg:burst). Cosmetic.
static func burst(node, color: String, count: int) -> void:
	node = _thing(node)
	if node == null or not (node is Node2D):
		return
	var scene := (node as Node).get_parent()
	if scene == null:
		return
	var puff := CPUParticles2D.new()
	puff.one_shot = true
	puff.emitting = true
	puff.amount = count
	puff.lifetime = 0.5
	puff.explosiveness = 1.0
	puff.direction = Vector2.ZERO
	puff.spread = 180.0
	puff.initial_velocity_min = 30.0
	puff.initial_velocity_max = 80.0
	puff.color = Color(color)
	puff.position = (node as Node2D).position
	scene.call_deferred("add_child", puff)
	puff.finished.connect(puff.queue_free)


# Shakes the scene a thing is in (qg:shake). Cosmetic.
static func shake(node, frames: int, strength: float) -> void:
	node = _thing(node)
	if node == null:
		return
	var scene := (node as Node).get_parent()
	if scene != null and scene.has_method("q_shake"):
		scene.q_shake(frames, strength)


# Leaves the scene for another at the end of the tick (qg:goto-scene).
static func goto_scene(scene: Node, name_: String) -> void:
	var game := scene.get_parent()
	if game != null and game.has_method("go_to_scene"):
		game.call_deferred("go_to_scene", name_)


# A collision hands the handler a hitbox area; the thing is its owner.
static func _thing(node):
	if node == null or not is_instance_valid(node):
		return null
	if node.has_method("quantum_owner"):
		return node.quantum_owner()
	return node


# --- persistence: the q:sets with saved="true" (G calls these) ---

# Where the file goes: --persist-dir=<dir> from the command line (the
# replay harness passes a temporary one), else user://.
var persist_dir: String = ""


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--persist-dir="):
			persist_dir = a.substr(14)


func _persist_path() -> String:
	var base := persist_dir if persist_dir != "" else "user://"
	if not base.ends_with("/"):
		base += "/"
	return base + "quantum-state.json"


func load_persisted(state: Node, names: Array) -> void:
	if names.is_empty():
		return
	var f := FileAccess.open(_persist_path(), FileAccess.READ)
	if f == null:
		return
	var data = JSON.parse_string(f.get_as_text())
	if typeof(data) != TYPE_DICTIONARY:
		return
	for n in names:
		if data.has(n):
			state.set(n, data[n])


func save_persisted(state: Node, names: Array) -> void:
	if names.is_empty():
		return
	var data := {}
	for n in names:
		data[n] = state.get(n)
	var f := FileAccess.open(_persist_path(), FileAccess.WRITE)
	if f == null:
		push_warning("quantum: cannot write " + _persist_path())
		return
	f.store_string(JSON.stringify(data))


# --- sounds (an instance method: Q is an autoload node) ---

func load_sounds(sounds: Dictionary) -> void:
	for name_ in sounds.keys():
		var src: String = sounds[name_]["src"]
		var stream: AudioStream = null
		var path := ProjectSettings.globalize_path("res://" + src)
		if src.ends_with(".ogg"):
			stream = AudioStreamOggVorbis.load_from_file(path)
			if stream != null:
				stream.loop = bool(sounds[name_].get("loop", false))
		elif src.ends_with(".wav"):
			stream = AudioStreamWAV.load_from_file(path)
			if stream != null and sounds[name_].get("loop", false):
				stream.loop_mode = AudioStreamWAV.LOOP_FORWARD
				stream.loop_end = stream.data.size() / max(1, 2 if stream.format == AudioStreamWAV.FORMAT_16_BITS else 1) / max(1, 2 if stream.stereo else 1)
		if stream == null:
			push_warning("quantum: cannot load the sound " + src)
			continue
		var player := AudioStreamPlayer.new()
		player.name = name_
		player.stream = stream
		apply_gd(player, sounds[name_].get("gd"))
		add_child(player)
		_sounds[name_] = player


func play(name_: String) -> void:
	sounds_played.append(name_)
	var player: AudioStreamPlayer = _sounds.get(name_)
	if player != null:
		player.play()


# qg:stop: the sound is silent (the replay state records it as "-name").
func stop(name_: String) -> void:
	sounds_played.append("-" + name_)
	var player: AudioStreamPlayer = _sounds.get(name_)
	if player != null:
		player.stop()
