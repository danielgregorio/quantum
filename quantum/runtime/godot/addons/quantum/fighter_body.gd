extends CharacterBody2D
# The fighter (qg:character controller="fighter"): a one-on-one fighting
# game character. Walks towards or away from its opponent (the other
# fighter in the scene), jumps (jump), crouches (down), blocks by holding
# away from the opponent, and performs its qg:moves on their actions: each
# move is an animation with one active frame, in which a hit box of
# `reach` at `at` (in the facing direction) is tested against the
# opponent's body once. A hit takes `damage`, stuns for `stun` ticks and
# pushes `push` pixels; a block halves the stun and the push and takes no
# damage. At 0 health the fighter is KO: the scene's qg:on-ko runs with
# (me, the winner). Deterministic: everything in _physics_process.

const Animator := preload("res://addons/quantum/animator.gd")

var speed: float = 120.0
var jump_height: float = 96.0
var gravity: float = 1200.0
var max_health: int = 100
var health: int = 100
var hitbox_size: Vector2 = Vector2(40, 90)
var facing: int = 1
var player: int = 1
var state: String = ""          # the move in progress, "" when none
var phase: String = "free"      # free, move, hit, ko
var spawn_point: Vector2 = Vector2.ZERO
var animator: Node = null

var _moves: Dictionary = {}     # name -> spec
var _move: Dictionary = {}
var _move_tick: int = 0
var _hit_done: bool = false
var _stun: int = 0
var _push: float = 0.0
var _floor_y: float = 0.0
var _jump_speed: float = 0.0
var _scene: Node = null
var _on_ko: String = ""
var _ko_reported: bool = false
var _handlers: Array = []
var _blocking: bool = false
var _crouching: bool = false


func setup(spec: Dictionary) -> void:
	player = int(spec.get("player", 1))
	speed = float(spec.get("speed", speed))
	jump_height = float(spec.get("jump_height", jump_height))
	gravity = float(spec.get("gravity", gravity))
	max_health = int(spec.get("health", 100))
	health = max_health
	hitbox_size = Vector2(spec["hitbox"][0], spec["hitbox"][1])
	facing = -1 if spec.get("facing", "right") == "left" else 1
	for m in spec.get("moves", []):
		_moves[m["name"]] = m
	_on_ko = str(spec.get("on_ko", "")) if spec.get("on_ko") != null else ""
	motion_mode = CharacterBody2D.MOTION_MODE_FLOATING
	collision_mask = 0
	var half_step := gravity / (2.0 * Engine.physics_ticks_per_second)
	_jump_speed = half_step + sqrt(half_step * half_step + 2.0 * gravity * jump_height)


func wire(sensor: Area2D, spec: Dictionary, scene: Node, sprite: Sprite2D) -> void:
	_scene = scene
	_handlers = spec.get("on_collision", [])
	sensor.monitoring = false
	animator = Animator.new()
	animator.name = "Animator"
	var animations: Dictionary = spec.get("animations", {}).duplicate()
	for m in _moves.values():
		animations["move-" + m["name"]] = {"frames": m["frames"], "fps": m["fps"]}
	animator.setup(sprite, animations)
	add_child(animator)
	animator.play("idle")


func _ready() -> void:
	spawn_point = position
	_floor_y = position.y


func _a(action: String) -> String:
	return action if player == 1 else "p%d_%s" % [player, action]


func quantum_node_state() -> Dictionary:
	var d := {"health": health, "phase": phase, "facing": facing}
	if state != "":
		d["state"] = state
	return d


func respawn() -> void:
	position = spawn_point
	velocity = Vector2.ZERO
	health = max_health
	phase = "free"
	state = ""
	_move = {}
	_stun = 0
	_push = 0.0
	_ko_reported = false
	if animator != null:
		animator.play("idle")


# For the rollback.
func q_save() -> Dictionary:
	return {"p": position, "v": velocity, "h": health, "ph": phase, "st": state, "f": facing,
		"mv": str(_move.get("name", "")), "mt": _move_tick, "hd": _hit_done, "su": _stun, "pu": _push,
		"ko": _ko_reported, "bl": _blocking, "cr": _crouching}


func q_load(d: Dictionary) -> void:
	position = d["p"]
	velocity = d["v"]
	health = d["h"]
	phase = d["ph"]
	state = d["st"]
	facing = d["f"]
	_move = _moves[d["mv"]] if d["mv"] != "" else {}
	_move_tick = d["mt"]
	_hit_done = d["hd"]
	_stun = d["su"]
	_push = d["pu"]
	_ko_reported = d["ko"]
	_blocking = d["bl"]
	_crouching = d["cr"]


func opponent() -> Node:
	for n in get_tree().get_nodes_in_group("q_named"):
		if n != self and n.get_parent() == get_parent() and "phase" in n and "max_health" in n:
			return n
	return null


func body_rect() -> Rect2:
	var size := hitbox_size
	if _crouching:
		size = Vector2(hitbox_size.x, hitbox_size.y * 0.6)
		return Rect2(position - Vector2(size.x / 2.0, size.y - hitbox_size.y / 2.0), size)
	return Rect2(position - size / 2.0, size)


func is_blocking() -> bool:
	return _blocking


# Hit by the opponent's move (or blocked it).
func take_hit(damage: int, stun: int, push: float, from_facing: int) -> void:
	if phase == "ko":
		return
	if _blocking:
		_stun = maxi(1, stun / 2)
		_push = push / 2.0 * from_facing
		phase = "hit"
		if animator != null:
			animator.play("block")
		return
	health = maxi(0, health - damage)
	_stun = stun
	_push = push * from_facing
	_move = {}
	state = ""
	if health == 0:
		phase = "ko"
		if animator != null:
			animator.play("ko")
		return
	phase = "hit"
	if animator != null:
		animator.play("hit")


func _physics_process(delta: float) -> void:
	var other := opponent()
	var on_floor := position.y >= _floor_y
	# KO: fall, lie, report once
	if phase == "ko":
		_fall(delta, on_floor)
		if not _ko_reported and _on_ko != "" and _scene != null and _scene.has_method(_on_ko):
			_ko_reported = true
			_scene.call(_on_ko, self, other)
		return
	# facing: towards the opponent, when free on the ground
	if other != null and phase == "free" and on_floor:
		facing = -1 if other.position.x < position.x else 1
	var sprite := get_node_or_null("Sprite")
	if sprite != null:
		sprite.flip_h = facing < 0
	# stun: pushed, no control
	if phase == "hit":
		_stun -= 1
		velocity.x = _push * 4.0
		_push *= 0.8
		_fall(delta, on_floor)
		if _stun <= 0:
			phase = "free"
			if animator != null:
				animator.play("idle")
		return
	# a move in progress: its frames, its one active frame
	if phase == "move":
		_advance_move(other)
		velocity.x = 0.0
		_fall(delta, on_floor)
		return
	# free: read the player's actions
	var dir := 0
	if Q.held(_a("right")):
		dir += 1
	if Q.held(_a("left")):
		dir -= 1
	_crouching = on_floor and Q.held(_a("down"))
	_blocking = on_floor and dir != 0 and dir == -facing and other != null and other.phase == "move"
	for name_ in _moves.keys():
		if Q.tapped(_a(_moves[name_]["action"])):
			_start_move(name_)
			velocity.x = 0.0
			_fall(delta, on_floor)
			return
	if on_floor and Q.tapped(_a("jump")):
		velocity.y = -_jump_speed
		position.y -= 0.01
		on_floor = false
	velocity.x = 0.0 if _crouching else dir * speed
	_fall(delta, on_floor)
	if animator != null:
		if not on_floor and animator.has("jump"):
			animator.play("jump")
		elif _blocking and animator.has("block"):
			animator.play("block")
		elif _crouching and animator.has("crouch"):
			animator.play("crouch")
		elif dir != 0 and animator.has("walk"):
			animator.play("walk")
		elif animator.has("idle"):
			animator.play("idle")


func _fall(delta: float, on_floor: bool) -> void:
	if not on_floor or velocity.y < 0.0:
		velocity.y += gravity * delta
	position += velocity * delta
	if position.y >= _floor_y:
		position.y = _floor_y
		velocity.y = 0.0
	var w := float(_scene.q_spec.get("width", 640)) if _scene != null and "q_spec" in _scene else 640.0
	position.x = clampf(position.x, hitbox_size.x / 2.0, w - hitbox_size.x / 2.0)
	# two bodies never share the ground: the one moving is kept off the other
	var other := opponent()
	if other != null and position.y >= _floor_y and other.position.y >= other._floor_y:
		var gap: float = (hitbox_size.x + float(other.hitbox_size.x)) / 2.0
		var dx: float = position.x - float(other.position.x)
		if absf(dx) < gap:
			var side := 1.0 if dx >= 0.0 else -1.0
			if dx == 0.0:
				side = -float(facing)
			position.x = clampf(other.position.x + side * gap, hitbox_size.x / 2.0, w - hitbox_size.x / 2.0)


func _start_move(name_: String) -> void:
	_move = _moves[name_]
	_move_tick = 0
	_hit_done = false
	phase = "move"
	state = name_
	if animator != null:
		animator.play("move-" + name_)


func _advance_move(other: Node) -> void:
	var frames: Array = _move["frames"]
	var per_frame := maxi(1, int(round(Engine.physics_ticks_per_second / float(_move["fps"]))))
	var total := frames.size() * per_frame
	var active_start := int(_move["active"]) * per_frame
	if not _hit_done and _move_tick >= active_start and _move_tick < active_start + per_frame and other != null:
		var reach: Array = _move["reach"]
		var at: Array = _move["at"]
		var centre := position + Vector2(float(at[0]) * facing, float(at[1]))
		var box := Rect2(centre - Vector2(reach[0], reach[1]) / 2.0, Vector2(reach[0], reach[1]))
		if box.intersects(other.body_rect()):
			_hit_done = true
			other.take_hit(int(_move["damage"]), int(_move["stun"]), float(_move["push"]), facing)
	_move_tick += 1
	if _move_tick >= total:
		phase = "free"
		state = ""
		_move = {}
		if animator != null:
			animator.play("idle")
