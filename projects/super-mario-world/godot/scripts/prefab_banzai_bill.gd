extends CharacterBody2D

@export var charge_speed: float = 90.0
var _direction = -1.0

var _health: int = 1

var _anim_timer: float = 0.0
var _anim_frames: Array = [0]
var _anim_idx: int = 0
var _anim_speed: float = 0.15
var _launch_sound_played: bool = false

func _ready():
	collision_layer = 2
	collision_mask = 1

func _physics_process(delta: float):
	# Launch sound when entering viewport
	if not _launch_sound_played:
		var camera = get_viewport().get_camera_2d()
		if camera:
			var vp_w = get_viewport_rect().size.x
			if global_position.x < camera.global_position.x + vp_w + 100:
				_launch_sound_played = true
				QuantumEventBus.emit_event("banzai-launch", {"other": self})

	# Charge AI: horizontal flight, no gravity
	velocity.x = _direction * charge_speed
	velocity.y = 0
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

	# Destroy if off-screen (far left)
	if global_position.x < -200:
		queue_free()

func stomp():
	_health -= 1
	if _health <= 0:
		QuantumEventBus.emit_event("enemy-killed", {"score": 400, "other": self})
		queue_free()

func die():
	QuantumEventBus.emit_event("enemy-killed", {"other": self})
	queue_free()
