extends Area2D

var _collected: bool = false

var _anim_timer: float = 0.0
var _anim_frames: Array = [0, 1, 2, 1]
var _anim_idx: int = 0
var _anim_speed: float = 0.12

func _ready():
	body_entered.connect(_on_body_entered)

func _process(delta: float):
	_anim_timer += delta
	if _anim_timer >= _anim_speed:
		_anim_timer = 0.0
		_anim_idx = (_anim_idx + 1) % _anim_frames.size()
		if has_node("Sprite2D"):
			$Sprite2D.frame = _anim_frames[_anim_idx]

func _on_body_entered(body: Node):
	if _collected:
		return
	if body is CharacterBody2D:
		_collected = true
		QuantumEventBus.emit_event("coin-collected", {"score": 10, "other": self})
		queue_free()
