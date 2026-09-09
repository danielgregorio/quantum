extends Area2D

signal checkpoint_activated(pos: Vector2)

var _activated: bool = false

func _ready():
	body_entered.connect(_on_body_entered)
	# Ensure collision_mask detects player layer (2)
	collision_layer = 0
	collision_mask = 2

func _on_body_entered(body: Node):
	if _activated:
		return
	if body is CharacterBody2D:
		_activated = true
		checkpoint_activated.emit(global_position)
		QuantumEventBus.emit_event("checkpoint-activated", {"position": global_position, "other": self})

		# Visual feedback: flash green then fade to semi-transparent
		var tween = create_tween()
		tween.tween_property(self, "modulate", Color(0.0, 1.0, 0.0, 1.0), 0.1)
		tween.tween_property(self, "modulate", Color(0.5, 1.0, 0.5, 0.6), 0.3)

		# Hide bar/cordao child if present
		if has_node("Bar"):
			var bar_tween = create_tween()
			bar_tween.tween_property($Bar, "scale", Vector2(0, 1), 0.2)
			bar_tween.tween_callback($Bar.queue_free)
