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

var spawn_point: Vector2 = Vector2.ZERO
var animator: Node = null

var _coyote: int = 0
var _jump_speed: float = 0.0
var _handlers: Array = []
var _cooldowns: Dictionary = {}   # handler name -> tick it may fire again
var _on_fall: String = ""
var _fell: bool = false
var _scene: Node = null
var _ticks: int = 0


func setup(spec: Dictionary) -> void:
	run_speed = float(spec.get("run_speed", run_speed))
	jump_height = float(spec.get("jump_height", jump_height))
	variable_jump = bool(spec.get("variable_jump", variable_jump))
	coyote_frames = int(spec.get("coyote_frames", coyote_frames))
	gravity = float(spec.get("gravity", gravity))
	max_fall = float(spec.get("max_fall", max_fall))
	jump_sound = str(spec.get("jump_sound", "")) if spec.get("jump_sound") != null else ""
	hitbox_size = Vector2(spec["hitbox"][0], spec["hitbox"][1])
	_jump_speed = _speed_for_height(jump_height)
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
	animator = Animator.new()
	animator.name = "Animator"
	animator.setup(sprite, spec.get("animations", {}))
	add_child(animator)
	animator.play("idle")


func bounce(height: float) -> void:
	velocity.y = -_speed_for_height(height)
	_coyote = 0


func respawn() -> void:
	position = spawn_point
	velocity = Vector2.ZERO
	_fell = false


func _on_area_entered(area: Area2D) -> void:
	if not area.has_method("quantum_tag"):
		return
	var tag: String = area.quantum_tag()
	var other: Node = area.quantum_owner() if area.has_method("quantum_owner") else area
	var on_top := _is_on_top_of(other)
	var matched := false
	for h in _handlers:
		if h["with"] == tag and h.get("side", "any") == "top" and on_top:
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
		_scene.call(name_, self, other)
	return true


# Landing on it: falling, with the feet above its middle.
func _is_on_top_of(other: Node) -> bool:
	if not (other is Node2D):
		return false
	var feet := global_position.y + hitbox_size.y / 2.0
	return velocity.y > 0.0 and feet <= (other as Node2D).global_position.y + 2.0


func _physics_process(delta: float) -> void:
	_ticks += 1
	var dir := 0
	if Input.is_action_pressed("right"):
		dir += 1
	if Input.is_action_pressed("left"):
		dir -= 1
	velocity.x = dir * run_speed

	if is_on_floor():
		_coyote = coyote_frames
	elif _coyote > 0:
		_coyote -= 1

	if Input.is_action_just_pressed("jump") and _coyote > 0:
		velocity.y = -_jump_speed
		_coyote = 0
		if jump_sound != "":
			Q.play(jump_sound)

	var g := gravity
	if variable_jump and velocity.y < 0.0 and not Input.is_action_pressed("jump"):
		g *= 3.0
	velocity.y = minf(velocity.y + g * delta, max_fall)

	var sprite := get_node_or_null("Sprite")
	if sprite != null and dir != 0:
		sprite.flip_h = dir < 0

	move_and_slide()

	if animator != null:
		if not is_on_floor() and animator.has("jump"):
			animator.play("jump")
		elif dir != 0 and animator.has("walk"):
			animator.play("walk")
		elif animator.has("idle"):
			animator.play("idle")

	if _on_fall != "" and not _fell and _scene != null and _scene.has_method("q_fall_line"):
		if position.y > _scene.q_fall_line():
			_fell = true
			_scene.call(_on_fall, self, null)
