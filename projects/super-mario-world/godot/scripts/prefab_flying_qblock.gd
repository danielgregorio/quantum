extends StaticBody2D

var _hits_remaining: int = 1
var _content: String = "mushroom"
var _is_used: bool = false
var _is_flying: bool = true
var _fly_time: float = 0.0
@export var fly_speed: float = 30.0
@export var fly_amplitude: float = 40.0
var _base_x: float = 0.0

var _anim_timer: float = 0.0
var _anim_frames: Array = [0, 1, 2, 1]
var _anim_idx: int = 0
var _anim_speed: float = 0.15

func _ready():
	_base_x = position.x

func _process(delta: float):
	if _is_flying:
		_fly_time += delta
		position.x = _base_x + sin(_fly_time * 2.0) * fly_amplitude

	if _is_used:
		return
	_anim_timer += delta
	if _anim_timer >= _anim_speed:
		_anim_timer = 0.0
		_anim_idx = (_anim_idx + 1) % _anim_frames.size()
		if has_node("Sprite2D"):
			$Sprite2D.frame = _anim_frames[_anim_idx]

func hit():
	if _is_used:
		return
	_hits_remaining -= 1

	# Stop flying and remove wings
	_is_flying = false
	if has_node("Wings"):
		$Wings.queue_free()

	QuantumEventBus.emit_event("block-hit", {"content": _content, "other": self})
	if _hits_remaining <= 0:
		_is_used = true
		if has_node("Sprite2D"):
			$Sprite2D.frame = _anim_frames[-1]
