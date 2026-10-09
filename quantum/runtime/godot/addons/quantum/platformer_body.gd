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

var run_speed: float = 90.0
var jump_height: float = 64.0
var variable_jump: bool = true
var coyote_frames: int = 6
var gravity: float = 900.0
var max_fall: float = 300.0

var _coyote: int = 0
var _jump_speed: float = 0.0
var _handlers: Array = []
var _scene: Node = null


func setup(spec: Dictionary) -> void:
	run_speed = float(spec.get("run_speed", run_speed))
	jump_height = float(spec.get("jump_height", jump_height))
	variable_jump = bool(spec.get("variable_jump", variable_jump))
	coyote_frames = int(spec.get("coyote_frames", coyote_frames))
	gravity = float(spec.get("gravity", gravity))
	max_fall = float(spec.get("max_fall", max_fall))
	var half_step := gravity / (2.0 * Engine.physics_ticks_per_second)
	_jump_speed = half_step + sqrt(half_step * half_step + 2.0 * gravity * jump_height)
	floor_snap_length = 4.0


func wire_collisions(sensor: Area2D, handlers: Array, scene: Node) -> void:
	_handlers = handlers
	_scene = scene
	sensor.area_entered.connect(_on_area_entered)


func _on_area_entered(area: Area2D) -> void:
	if not area.has_method("quantum_tag"):
		return
	var tag: String = area.quantum_tag()
	for h in _handlers:
		if h["with"] == tag and _scene.has_method(h["handler"]):
			_scene.call(h["handler"], self, area)


func _physics_process(delta: float) -> void:
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

	var g := gravity
	if variable_jump and velocity.y < 0.0 and not Input.is_action_pressed("jump"):
		g *= 3.0
	velocity.y = minf(velocity.y + g * delta, max_fall)

	var sprite := get_node_or_null("Sprite")
	if sprite != null and dir != 0:
		sprite.flip_h = dir < 0

	move_and_slide()
