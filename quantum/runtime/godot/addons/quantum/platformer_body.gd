extends CharacterBody2D
# The platformer controller: kinematic, deterministic, tuned by numbers the
# .q gives (qg:character controller="platformer").
#
# Everything happens in _physics_process at the fixed tick, from Input
# actions "left", "right" and "jump". The replay harness presses the same
# actions, so a recorded tape plays back exactly.
#
# jump_height is what the player gets with the button held, to the pixel:
# gravity is applied before the move each tick, so the take-off speed that
# peaks at exactly h is g*dt/2 + sqrt((g*dt/2)^2 + 2*g*h), not sqrt(2*g*h).
# Releasing the button early (when variable_jump) applies extra gravity, so
# a tap is a short hop.
#
# jump_speed, when given, is the take-off speed instead. accel eases the run
# speed in and out (0: at once); air_jumps are jumps taken in the air, each
# multiplying the speed across by air_jump_boost; jump_cut, when given,
# multiplies the rise once as the button is released instead of the extra
# gravity. fire_action shoots fire_prefab (a fly prefab) the way it faces.
#
# Collisions: the Sensor area reports what the character overlaps; each
# qg:on-collision handler has a tag, a side ("top": landing on it) and a
# cooldown in ticks. For one touch, the side handlers that match run; only
# when none did do the "any" handlers run.

const Animator := preload("res://addons/quantum/animator.gd")

var run_speed: float = 90.0
var jump_height: float = 64.0
var variable_jump: bool = true
var coyote_frames: int = 6
var gravity: float = 900.0
var max_fall: float = 300.0
var jump_sound: String = ""
var hitbox_size: Vector2 = Vector2(16, 16)
var accel: float = 0.0
var air_jumps: int = 0
var air_jump_boost: float = 1.0
var jump_cut: float = 0.0
var fire_action: String = ""
var fire_prefab: String = ""
var fire_every: int = 10
var fire_sound: String = ""
var facing: int = 1
var _air_jumps_left: int = 0
var _jump_was_held: bool = false
var _fire_in: int = 0

var spawn_point: Vector2 = Vector2.ZERO
var animator: Node = null
var state: String = ""
var player: int = 1
var _states: Dictionary = {}
var _base_animations: Dictionary = {}
var _base_frame: int = 0

var _coyote: int = 0
var _jump_speed: float = 0.0
var _handlers: Array = []
var _cooldowns: Dictionary = {}   # handler name -> tick it may fire again
var _on_fall: String = ""
var _fell: bool = false
var _scene: Node = null
var _ticks: int = 0
# The velocity before move_and_slide, which zeroes it on a floor or a
# ceiling: the side of a touch is judged by where the body was going.
var _moving: Vector2 = Vector2.ZERO


func setup(spec: Dictionary) -> void:
	player = int(spec.get("player", 1))
	run_speed = float(spec.get("run_speed", run_speed))
	jump_height = float(spec.get("jump_height", jump_height))
	variable_jump = bool(spec.get("variable_jump", variable_jump))
	coyote_frames = int(spec.get("coyote_frames", coyote_frames))
	gravity = float(spec.get("gravity", gravity))
	max_fall = float(spec.get("max_fall", max_fall))
	jump_sound = str(spec.get("jump_sound", "")) if spec.get("jump_sound") != null else ""
	hitbox_size = Vector2(spec["hitbox"][0], spec["hitbox"][1])
	_jump_speed = _speed_for_height(jump_height)
	if spec.get("jump_speed") != null:
		_jump_speed = float(spec["jump_speed"])
	accel = float(spec.get("accel", 0.0))
	air_jumps = int(spec.get("air_jumps", 0))
	air_jump_boost = float(spec.get("air_jump_boost", 1.0))
	jump_cut = float(spec.get("jump_cut", 0.0))
	fire_action = str(spec.get("fire_action", "")) if spec.get("fire_action") != null else ""
	fire_prefab = str(spec.get("fire_prefab", "")) if spec.get("fire_prefab") != null else ""
	fire_every = int(spec.get("fire_every", 10))
	fire_sound = str(spec.get("fire_sound", "")) if spec.get("fire_sound") != null else ""
	floor_snap_length = 4.0
	spawn_point = position


func _speed_for_height(height: float) -> float:
	var half_step := gravity / (2.0 * Engine.physics_ticks_per_second)
	return half_step + sqrt(half_step * half_step + 2.0 * gravity * height)


func wire(sensor: Area2D, spec: Dictionary, scene: Node, sprite: Sprite2D) -> void:
	_handlers = spec.get("on_collision", [])
	_on_fall = str(spec.get("on_fall", "")) if spec.get("on_fall") != null else ""
	_scene = scene
	sensor.area_entered.connect(_on_area_entered)
	_base_animations = spec.get("animations", {})
	_base_frame = int(spec.get("frame", 0))
	_states = spec.get("states", {})
	animator = Animator.new()
	animator.name = "Animator"
	animator.setup(sprite, _base_animations)
	add_child(animator)
	animator.play("idle")
	if spec.get("initial_state") != null:
		become(str(spec["initial_state"]))


func bounce(height: float) -> void:
	velocity.y = -_speed_for_height(height)
	_coyote = 0


func respawn() -> void:
	position = spawn_point
	velocity = Vector2.ZERO
	_fell = false


func quantum_node_state() -> Dictionary:
	return {"state": state} if state != "" else {}


func set_checkpoint(at: Vector2) -> void:
	spawn_point = Vector2(at.x, at.y - 2.0)


# One of the qg:states: its hitbox, its frame, its animations (the
# character's own where the state has none).
func become(name_: String) -> void:
	if not _states.has(name_) or name_ == state:
		return
	state = name_
	var st: Dictionary = _states[name_]
	var old_h := hitbox_size.y
	hitbox_size = Vector2(st["hitbox"][0], st["hitbox"][1])
	# Deferred: a state change comes from a collision handler, while
	# physics refuses shape changes.
	var shape := get_node_or_null("Shape")
	if shape != null:
		shape.shape.set_deferred("size", hitbox_size)
	var sensor_shape := get_node_or_null("Sensor/Shape")
	if sensor_shape != null:
		sensor_shape.shape.set_deferred("size", hitbox_size + Vector2(4, 4))
	# Keep the feet where they were.
	position.y -= (hitbox_size.y - old_h) / 2.0
	var sprite: Sprite2D = get_node_or_null("Sprite")
	if sprite != null:
		sprite.frame = int(st.get("frame", _base_frame))
	if animator != null:
		var anims: Dictionary = _base_animations.duplicate()
		for k in st.get("animations", {}).keys():
			anims[k] = st["animations"][k]
		animator.animations = anims
		animator.current = ""


func _on_area_entered(area: Area2D) -> void:
	if not area.has_method("quantum_tag"):
		return
	var tag: String = area.quantum_tag()
	var other: Node = area.quantum_owner() if area.has_method("quantum_owner") else area
	var on_top := _is_on_top_of(other)
	var from_below := _is_below(other)
	var matched := false
	for h in _handlers:
		var side: String = h.get("side", "any")
		if h["with"] == tag and ((side == "top" and on_top) or (side == "bottom" and from_below)):
			if _fire(h, other):
				matched = true
	if matched:
		return
	for h in _handlers:
		if h["with"] == tag and h.get("side", "any") == "any":
			_fire(h, other)


func _fire(h: Dictionary, other: Node) -> bool:
	var name_: String = h["handler"]
	var cooldown := int(h.get("cooldown", 0))
	if cooldown > 0 and _cooldowns.get(name_, -1) > _ticks:
		return false
	if cooldown > 0:
		_cooldowns[name_] = _ticks + cooldown
	if _scene.has_method(name_):
		Q.event("touch", {"who": String(name), "with": Q.who(other)})
		_scene.call(name_, self, other)
	return true


# Hitting it from below: rising, with the head below its middle.
func _is_below(other: Node) -> bool:
	if not (other is Node2D):
		return false
	var head := global_position.y - hitbox_size.y / 2.0
	return _moving.y < 0.0 and head >= (other as Node2D).global_position.y - 2.0


# Landing on it: falling, with the feet above its middle.
func _is_on_top_of(other: Node) -> bool:
	if not (other is Node2D):
		return false
	var feet := global_position.y + hitbox_size.y / 2.0
	return _moving.y > 0.0 and feet <= (other as Node2D).global_position.y + 2.0


func _physics_process(delta: float) -> void:
	_ticks += 1
	var dir := 0
	if Q.held(_a("right")):
		dir += 1
	if Q.held(_a("left")):
		dir -= 1
	if accel > 0.0:
		velocity.x = move_toward(velocity.x, dir * run_speed, accel * delta)
	else:
		velocity.x = dir * run_speed

	if is_on_floor():
		_coyote = maxi(coyote_frames, 1)   # standing, a jump works whatever coyote-frames says
		_air_jumps_left = air_jumps
	elif _coyote > 0:
		_coyote -= 1

	if Q.tapped(_a("jump")):
		if _coyote > 0:
			_jump()
			_coyote = 0
		elif _air_jumps_left > 0:
			_air_jumps_left -= 1
			velocity.x *= air_jump_boost
			_jump()

	var g := gravity
	var holding := Q.held(_a("jump"))
	if variable_jump and velocity.y < 0.0 and not holding:
		if jump_cut <= 0.0:
			g *= 3.0
		elif _jump_was_held:
			velocity.y *= jump_cut
	_jump_was_held = holding
	velocity.y = minf(velocity.y + g * delta, max_fall)

	if not is_zero_approx(velocity.x):
		facing = 1 if velocity.x > 0.0 else -1
	var sprite := get_node_or_null("Sprite")
	if sprite != null:
		sprite.flip_h = facing < 0

	_moving = velocity
	move_and_slide()

	if _fire_in > 0:
		_fire_in -= 1
	if fire_action != "" and fire_prefab != "" and Q.tapped(_a(fire_action)) and _fire_in == 0:
		_fire_in = fire_every
		_shoot()

	if animator != null:
		if not is_on_floor() and velocity.y > 0.0 and animator.has("fall"):
			animator.play("fall")
		elif not is_on_floor() and animator.has("jump"):
			animator.play("jump")
		elif absf(velocity.x) > 0.1 and animator.has("walk"):
			animator.play("walk")
		elif animator.has("idle"):
			animator.play("idle")

	if _on_fall != "" and not _fell and _scene != null and _scene.has_method("q_fall_line"):
		if position.y > _scene.q_fall_line():
			_fell = true
			_scene.call(_on_fall, self, null)


func _jump() -> void:
	velocity.y = -_jump_speed
	if jump_sound != "":
		Q.play(jump_sound)


# fire_prefab, in front of it at its middle, heading the way it faces.
func _shoot() -> void:
	if _scene == null:
		return
	var shot: Node = Q.spawn_at(_scene, fire_prefab, position + Vector2(facing * hitbox_size.x / 2.0, 0.0))
	if shot is PhysicsBody2D:
		(shot as PhysicsBody2D).add_collision_exception_with(self)
	if "heading" in shot and facing < 0:
		shot.heading = Vector2(-shot.heading.x, shot.heading.y)
		if shot.has_method("_face"):
			shot._face(shot.heading.x)
	if fire_sound != "":
		Q.play(fire_sound)


# The input action of this player: "up" for player 1, "p2_up" for player 2.
func _a(action: String) -> String:
	return action if player == 1 else "p%d_%s" % [player, action]
