extends Node
# Q: the helpers the compiled scripts call. An autoload (project.godot),
# so every script sees `Q`.
#
# Where GDScript's operators differ from Quantum's expression semantics
# (quantum/core/expressions.py), the compiler emits one of these instead.

var _sounds: Dictionary = {}   # name -> AudioStreamPlayer
# qg:cursor: where each player points, {player: Vector2}, in scene pixels.
# raw_cursor is the local pointer before the lockstep (the mouse, or the
# replay tape's "cursor" events); under lockstep it travels with the input
# and lands in cursors[p] on every peer; alone it is cursors[player] at once.
var cursors: Dictionary = {}
var raw_cursor: Vector2 = Vector2.ZERO
var tape_cursor = null   # the replay tape's pointer (Vector2), instead of the mouse
var sounds_played: Array = []  # names, in order — the replay harness reads it

# --- the input of the tick ---
# Every action is read once per physics tick, here, before any node of the
# game runs (Q is an autoload, first in the tree, and runs at the lowest
# priority); the runtime asks Q, never Input. So a tick's input is a value:
# the lockstep and the rollback set it themselves (external_input), and the
# rollback can replay old ticks with their input in one frame.
var _now: Dictionary = {}    # action -> strength (0..1), only the pressed ones
var _prev: Dictionary = {}
var external_input: bool = false


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


# --- events, for the play protocol (PLAN_PLAY_PROTOCOL.md) ---
# What happened, as a player would notice it: a touch, a hit, a thing made or
# gone, a sound, a scene, a line said. Recorded only while a play session
# traces (godot_play.gd sets `tracing`); otherwise each call is one check.
var tracing: bool = false
var events: Array = []
var events_dropped: int = 0
var event_tick: int = 0


static func event(kind: String, data: Dictionary = {}) -> void:
	var q = (Engine.get_main_loop() as SceneTree).root.get_node_or_null("Q")
	if q == null or not q.tracing or q.resimulating:
		return
	if q.events.size() >= 500:
		q.events_dropped += 1
		return
	var e := data.duplicate()
	e["kind"] = kind
	e["tick"] = q.event_tick
	q.events.append(e)


# How an event names a node: a character or a named thing by its name, a thing by its tag.
static func who(node) -> String:
	node = _thing(node)
	if node == null:
		return ""
	if node.is_in_group("q_named") or node.has_meta("q_named"):
		return String(node.name)
	if "tag" in node:
		return str(node.tag)
	return String(node.name)


# Removes a thing from the scene at the end of the tick.
static func destroy(node) -> void:
	node = _thing(node)
	if node == null:
		return
	if node is Node2D:
		event("destroy", {"what": who(node), "x": snappedf(node.position.x, 0.1), "y": snappedf(node.position.y, 0.1)})
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


# qg:put: a thing or a character moved to a point.
static func put(node, x: float, y: float) -> void:
	node = _thing(node)
	if node != null and node is Node2D:
		(node as Node2D).position = Vector2(x, y)


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


# qg:spawn at="path": at the start of the scene's path, which an ai="path" thing then follows.
static func spawn_on_path(scene: Node, prefab: String, path_name: String) -> Node:
	var paths: Dictionary = scene.q_paths if "q_paths" in scene else {}
	if not paths.has(path_name):
		return null
	var points: Array = paths[path_name]
	var builder = load("res://addons/quantum/scene_builder.gd")
	var made = builder.instance(scene.q_game, scene, prefab, Vector2(points[0][0], points[0][1]), true)
	if made != null and "path_points" in made:
		made.path_points = points
	return made


# count(tag): how many things of the tag are in the scene (zones are not things).
static func count(scene: Node, tag: String) -> int:
	var n := 0
	for t in scene.get_tree().get_nodes_in_group("q_thing"):
		if t.get_parent() == scene and t.quantum_tag() == tag and not t.is_queued_for_deletion():
			n += 1
	return n


# thing_at(tag, x, y): the thing (or zone) of the tag whose box covers the point ("" for any thing), or null.
static func thing_at(scene: Node, tag: String, x: float, y: float):
	var point := Vector2(x, y)
	for t in scene.get_tree().get_nodes_in_group("q_thing"):
		if t.get_parent() != scene or t.is_queued_for_deletion():
			continue
		if tag != "" and t.quantum_tag() != tag:
			continue
		var size: Vector2 = t.hitbox_size if "hitbox_size" in t else Vector2(16, 16)
		if Rect2((t as Node2D).position - size / 2.0, size).has_point(point):
			return t
	if tag != "":
		for z in scene.get_children():
			if z is Area2D and "tag" in z and z.tag == tag and "hitbox_size" in z:
				if Rect2((z as Node2D).position - z.hitbox_size / 2.0, z.hitbox_size).has_point(point):
					return z
	return null


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
		event("damage", {"what": who(node), "amount": amount, "health": node.get("health")})
		if node.get("health") != null and int(node.get("health")) <= 0:
			event("death", {"what": who(node)})


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


# qg:pause / qg:resume, and paused(): the scene the handler is in, or the
# current one (a prefab's handler).
static func _current_scene(node) -> Node:
	if node is Node and (node as Node).has_method("q_pause"):
		return node
	return (Engine.get_main_loop() as SceneTree).get_first_node_in_group("q_scene")


static func pause(node, on: bool) -> void:
	var scene := _current_scene(node)
	event("pause" if on else "resume")
	if scene != null:
		scene.q_pause(on)


static func paused(node) -> bool:
	var scene := _current_scene(node)
	return scene != null and scene.q_paused


# qg:say: opens a qg:dialogue of the scene (it pauses the scene until its last line).
static func say(node, dialogue: String) -> void:
	var scene := _current_scene(node)
	var box = scene.get_node_or_null("Dialogue_" + dialogue) if scene != null else null
	if box != null and not box.is_open():
		box.open()


# talking(): a qg:dialogue of the scene is open.
static func talking(node) -> bool:
	var scene := _current_scene(node)
	return scene != null and scene.q_talking() != ""


# Leaves the scene for another at the end of the tick (qg:goto-scene).
static func goto_scene(scene: Node, name_: String) -> void:
	var game := scene.get_parent()
	if game == null or not game.has_method("go_to_scene"):
		return
	# under the rollback, a scene change waits until the tick that asked is certain
	var net = game.get("lockstep")
	if net != null and net.has_method("request_scene") and net.started:
		net.request_scene(name_)
		return
	game.call_deferred("go_to_scene", name_)


# The solid part of a solid prefab: its shape= polygon (from its centre), or
# its hitbox. A polygon may be concave: CollisionPolygon2D splits it.
static func solid_shape(prefab: Dictionary) -> Node2D:
	var one_way := bool(prefab.get("one_way", false))
	if prefab.get("shape") != null:
		var poly := CollisionPolygon2D.new()
		var points := PackedVector2Array()
		for p in prefab["shape"]:
			points.append(Vector2(float(p[0]), float(p[1])))
		poly.polygon = points
		poly.one_way_collision = one_way
		return poly
	var rect := RectangleShape2D.new()
	rect.size = Vector2(prefab["hitbox"][0], prefab["hitbox"][1])
	var shape := CollisionShape2D.new()
	shape.shape = rect
	shape.one_way_collision = one_way
	return shape


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
	process_physics_priority = -1000
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--persist-dir="):
			persist_dir = a.substr(14)


func _physics_process(_delta: float) -> void:
	if external_input:
		return
	set_input(sample_local())


# The game's actions pressed and released again between two ticks: a quick
# click, a tap on a screen. Sampling only what is held at each tick would lose
# them; they count as pressed for the next tick.
var _taps: Dictionary = {}


func _input(event: InputEvent) -> void:
	if not event.is_pressed() or event.is_echo():
		return
	for a in InputMap.get_actions():
		var name_ := String(a)
		if not name_.begins_with("ui_") and event.is_action_pressed(name_):
			_taps[name_] = true


# This machine's keys, for the tick: what is held, with its strength, and what
# was tapped since the last tick. The lockstep sends it; alone, it is the input.
func sample_local() -> Dictionary:
	var next := {}
	for a in InputMap.get_actions():
		var name_ := String(a)
		if name_.begins_with("ui_"):
			continue
		var v := Input.get_action_strength(name_)
		if v > 0.0:
			next[name_] = v
	for name_ in _taps.keys():
		if not next.has(name_):
			next[name_] = 1.0
	_taps.clear()
	return next


# The input of the next tick: {action: strength}, only what is pressed.
func set_input(next: Dictionary) -> void:
	_prev = _now
	_now = next
	if OS.has_feature("web"):
		for a in next.keys():
			if not _web_pressed.has(a):
				_web_pressed[a] = true
				web_report("quantumActions", ",".join(PackedStringArray(_web_pressed.keys())))


# In a browser, what the game is doing, for a page to read: window.quantumScene
# is the scene being played and window.quantumActions every action pressed
# since the start, comma-separated. The CI's browser check
# (scripts/check-games-in-browser.py) plays the web builds with them.
var _web_pressed: Dictionary = {}


static func web_report(key: String, value: String) -> void:
	if not OS.has_feature("web"):
		return
	var window = JavaScriptBridge.get_interface("window")
	if window != null:
		window[key] = value


func held(action: String) -> bool:
	return float(_now.get(action, 0.0)) > 0.0


func tapped(action: String) -> bool:
	return float(_now.get(action, 0.0)) > 0.0 and float(_prev.get(action, 0.0)) <= 0.0


func strength(action: String) -> float:
	return float(_now.get(action, 0.0))


# --- the network, from a scene: qg:host, qg:join, qg:leave, net_*() ---

static func _game() -> Node:
	return (Engine.get_main_loop() as SceneTree).root.get_node_or_null("Game")


static func net_host(port: int) -> void:
	var g := _game()
	if g != null:
		g.net_host(port)


static func net_join(address) -> void:
	var g := _game()
	if g != null:
		g.net_join(str(address))


static func net_leave() -> void:
	var g := _game()
	if g != null:
		g.net_leave()


static func net_status() -> String:
	var g := _game()
	return g.net_status() if g != null else "offline"


static func net_players() -> int:
	var g := _game()
	return g.net_players() if g != null else 0


static func net_player() -> int:
	var g := _game()
	return g.net_player() if g != null else 0


# For the rollback: the input state, and back to it.
func input_state() -> Array:
	return [_now.duplicate(), _prev.duplicate()]


func restore_input(state: Array) -> void:
	_now = state[0].duplicate()
	_prev = state[1].duplicate()


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

# --- the game's files: images, sounds, fonts ---
#
# A project on disk (the editor, a replay, the tests) has the files
# themselves, read as they are: no import step needed. An exported game (the
# browser, a desktop zip) carries only Godot's imported version of each file,
# which load() finds.

static func _imported(src: String) -> Resource:
	var path := "res://" + src
	if not FileAccess.file_exists(path) and ResourceLoader.exists(path):
		return load(path)
	return null


static func texture(src: String) -> Texture2D:
	var res := _imported(src)
	if res is Texture2D:
		return res
	var image := Image.load_from_file(ProjectSettings.globalize_path("res://" + src))
	if image == null:
		return null
	return ImageTexture.create_from_image(image)


static func audio(src: String, loop: bool) -> AudioStream:
	var stream: AudioStream = null
	var res := _imported(src)
	if res is AudioStream:
		stream = res
	elif src.ends_with(".ogg"):
		stream = AudioStreamOggVorbis.load_from_file(ProjectSettings.globalize_path("res://" + src))
	elif src.ends_with(".wav"):
		stream = AudioStreamWAV.load_from_file(ProjectSettings.globalize_path("res://" + src))
	if stream == null:
		return null
	if stream is AudioStreamOggVorbis:
		stream.loop = loop
	elif stream is AudioStreamWAV and loop:
		var wav := stream as AudioStreamWAV
		wav.loop_mode = AudioStreamWAV.LOOP_FORWARD
		wav.loop_end = wav.data.size() / max(1, 2 if wav.format == AudioStreamWAV.FORMAT_16_BITS else 1) / max(1, 2 if wav.stereo else 1)
	return stream


static func font(src: String) -> Font:
	var res := _imported(src)
	if res is Font:
		return res
	var file := FontFile.new()
	if file.load_dynamic_font(ProjectSettings.globalize_path("res://" + src)) == OK:
		return file
	return null


# Quitting while a sound plays would leave its playback, and the imported
# stream it reads, alive after the engine: stop and drop them first.
func _exit_tree() -> void:
	for player in _sounds.values():
		player.stop()
		player.stream = null
	_sounds.clear()


func load_sounds(sounds: Dictionary) -> void:
	for name_ in sounds.keys():
		var src: String = sounds[name_]["src"]
		var stream := audio(src, bool(sounds[name_].get("loop", false)))
		if stream == null:
			push_warning("quantum: cannot load the sound " + src)
			continue
		var player := AudioStreamPlayer.new()
		player.name = name_
		player.stream = stream
		apply_gd(player, sounds[name_].get("gd"))
		add_child(player)
		_sounds[name_] = player


var resimulating: bool = false   # the rollback replays old ticks: record sounds, play none


func play(name_: String) -> void:
	sounds_played.append(name_)
	event("sound", {"name": name_})
	if resimulating:
		return
	var player: AudioStreamPlayer = _sounds.get(name_)
	if player != null:
		player.play()


# qg:stop: the sound is silent (the replay state records it as "-name").
func stop(name_: String) -> void:
	sounds_played.append("-" + name_)
	var player: AudioStreamPlayer = _sounds.get(name_)
	if player != null:
		player.stop()
