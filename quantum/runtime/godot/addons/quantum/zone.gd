extends Area2D
# An invisible rectangle with a tag (qg:zone): a wall the ball resets at, a
# pit, a goal line. It does nothing itself; what touches it (a character's
# sensor, a thing's hitbox) runs its own qg:on-collision with= the tag.

var tag: String = ""
var hitbox_size: Vector2 = Vector2.ZERO


func setup(spec: Dictionary) -> void:
	name = "zone-" + spec["name"]
	tag = spec["tag"]
	monitoring = false
	collision_layer = 1
	collision_mask = 0
	position = Vector2(spec["x"] + spec["width"] / 2.0, spec["y"] + spec["height"] / 2.0)
	var shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = Vector2(spec["width"], spec["height"])
	hitbox_size = rect.size
	shape.shape = rect
	add_child(shape)


func quantum_tag() -> String:
	return tag
