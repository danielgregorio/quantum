extends StaticBody2D

var _is_breaking: bool = false

func hit():
	if _is_breaking:
		return
	_is_breaking = true
	var tween = create_tween()
	tween.tween_property(self, "rotation_degrees", 360.0, 0.25)
	tween.set_loops(4)
	tween.tween_callback(_on_break_complete)

func _on_break_complete():
	if has_node("CollisionShape2D"):
		$CollisionShape2D.disabled = true
	QuantumEventBus.emit_event("block-broken", {"other": self})
	var timer = get_tree().create_timer(2.0)
	timer.timeout.connect(_restore)

func _restore():
	rotation_degrees = 0.0
	_is_breaking = false
	if has_node("CollisionShape2D"):
		$CollisionShape2D.disabled = false
