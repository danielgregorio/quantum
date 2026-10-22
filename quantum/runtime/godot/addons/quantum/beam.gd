extends Line2D
# qg:beam: a line from one thing to another for so many ticks, its ends where
# the two are each tick (a laser, a zap, a rope, an aiming line). It goes when
# its time is up or either end is gone. Only seen.

var _a: Node2D = null
var _b: Node2D = null
var _left: int = 1


func setup(a: Node2D, b: Node2D, ticks: int, colour: Color, width_: float) -> void:
	_a = a
	_b = b
	_left = maxi(1, ticks)
	default_color = colour
	width = width_
	z_index = 25
	points = PackedVector2Array([a.position, b.position])


func _physics_process(_delta: float) -> void:
	if not is_instance_valid(_a) or not is_instance_valid(_b) or _left <= 0:
		queue_free()
		return
	_left -= 1
	points = PackedVector2Array([_a.position, _b.position])
