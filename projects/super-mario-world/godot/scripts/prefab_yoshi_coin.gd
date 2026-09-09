extends Area2D

var _collected: bool = false
var _shimmer_time: float = randf() * TAU

var _anim_timer: float = 0.0
var _anim_frames: Array = [0, 1, 2, 1]
var _anim_idx: int = 0
var _anim_speed: float = 0.15

func _ready():
	body_entered.connect(_on_body_entered)

func _process(delta: float):
	_shimmer_time += delta * 3.0
	var shimmer = 0.15 * sin(_shimmer_time)
	if has_node("Sprite2D"):
		$Sprite2D.modulate = Color(1.0 + shimmer, 1.0 + shimmer * 0.5, 0.7, 1.0)
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
		QuantumEventBus.emit_event("yoshi_coin-collected", {"score": 50, "other": self})
		queue_free()
