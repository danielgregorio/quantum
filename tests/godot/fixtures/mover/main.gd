extends Node2D
# The smallest game: a node that moves right while "right" is held, and
# counts physics ticks. The replay harness is tested on it.
var ticks := 0

func _physics_process(_delta: float) -> void:
	ticks += 1
	if Input.is_action_pressed("right"):
		$Player.position.x += 2

func quantum_state() -> Dictionary:
	return {"ticks": ticks, "player_x": $Player.position.x}
