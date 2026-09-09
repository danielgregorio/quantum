extends CharacterBody2D

@export var patrol_speed: float = 30.0
@export var turn_on_edge: bool = true
var _direction = -1.0

var _turn_cooldown: float = 0.15
var _turn_timer: float = 0.0

var _health: int = 2
var _is_squished: bool = false
var _squish_speed_mult: float = 1.5
var frame_h: float = 28

var _anim_timer: float = 0.0
var _anim_frames: Array = [0, 1]
var _anim_idx: int = 0
var _anim_speed: float = 0.15

func _ready():
	collision_layer = 2
	collision_mask = 1

func _physics_process(delta: float):
	if not is_on_floor():
		velocity.y += 750.0 * delta
	else:
		velocity.y = 0

	if _turn_timer > 0:
		_turn_timer -= delta

	velocity.x = _direction * patrol_speed

	if is_on_wall() and _turn_timer <= 0:
		_direction *= -1
		_turn_timer = _turn_cooldown

	move_and_slide()

	# Flip sprite to face movement direction
	if has_node("Sprite2D"):
		$Sprite2D.flip_h = _direction > 0

	# Animate sprite
	_anim_timer += delta
	if _anim_timer >= _anim_speed:
		_anim_timer = 0.0
		_anim_idx = (_anim_idx + 1) % _anim_frames.size()
		if has_node("Sprite2D"):
			$Sprite2D.frame = _anim_frames[_anim_idx]

func stomp():
	_health -= 1
	if _health <= 0:
		QuantumEventBus.emit_event("enemy-killed", {"score": 200, "other": self})
		queue_free()
	else:
		_is_squished = true
		# Squish visual + reposition body
		if has_node("Sprite2D"):
			$Sprite2D.scale.y = 0.5
			$Sprite2D.position.y += frame_h * 0.25
		global_position.y += frame_h * 0.25
		# Shrink collision to match squished sprite
		if has_node("CollisionShape2D"):
			var shape = $CollisionShape2D.shape.duplicate()
			$CollisionShape2D.shape = shape
			if shape is RectangleShape2D:
				shape.size.y *= 0.5
		# Speed up after hit
		patrol_speed *= _squish_speed_mult
		QuantumEventBus.emit_event("enemy-stomped", {"score": 100, "other": self})

func die():
	QuantumEventBus.emit_event("enemy-killed", {"other": self})
	queue_free()

func set_patrol(speed: float):
	patrol_speed = speed
