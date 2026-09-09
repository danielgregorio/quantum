extends StaticBody2D

var _hits_remaining: int = 1
var _content: String = "coin"
var _is_used: bool = false

var _anim_timer: float = 0.0
var _anim_frames: Array = [0, 1, 2, 1]
var _anim_idx: int = 0
var _anim_speed: float = 0.15

func _process(delta: float):
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
	QuantumEventBus.emit_event("block-hit", {"content": _content, "other": self})
	if _hits_remaining <= 0:
		_is_used = true
		if has_node("Sprite2D"):
			$Sprite2D.frame = _anim_frames[-1]
