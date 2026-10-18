extends Node
# qg:tween: one property of a thing goes from what it is to a value, eased,
# over so many ticks. It is a child of the thing: it runs in the physics
# tick (the same on every peer, in every replay), stops while the scene is
# paused or the lockstep waits, and goes when the thing goes. A new tween of
# the same property replaces it.
#
#   x, y        the thing's position (it moves in the game: collisions see it)
#   rotation    its picture's turn, in degrees
#   scale       its picture's size (1 is as drawn)
#   alpha       how opaque it is (0 to 1)

var target: Node2D
var property := ""
var from := 0.0
var to := 0.0
var ticks := 1
var trans := Tween.TRANS_LINEAR
var ease := Tween.EASE_IN_OUT
var repeat := 0      # times it plays again (-1: for ever)
var yoyo := false    # each time back the other way
var _t := 0


func start(target_: Node2D, property_: String, to_: float, seconds: float, trans_: int, ease_: int,
		repeat_: int, yoyo_: bool, from_ = null) -> void:
	target = target_
	property = property_
	to = to_
	ticks = maxi(1, int(round(seconds * Q.TICK_RATE)))
	trans = trans_
	ease = ease_
	repeat = repeat_
	yoyo = yoyo_
	from = float(from_) if from_ != null else read(target, property)
	name = "Tween_" + property
	process_physics_priority = -50   # before the thing's own tick: it sees where the tween put it


func _physics_process(_delta: float) -> void:
	if not is_instance_valid(target):
		queue_free()
		return
	_t += 1
	write(target, property, Tween.interpolate_value(from, to - from, float(_t), float(ticks), trans, ease))
	if _t < ticks:
		return
	if repeat == 0:
		queue_free()
		return
	if repeat > 0:
		repeat -= 1
	_t = 0
	if yoyo:
		var f := from
		from = to
		to = f
	else:
		write(target, property, from)


static func _picture(node: Node2D) -> Node2D:
	var sprite = node.get_node_or_null("Sprite")
	return sprite if sprite is Node2D else node


static func read(node: Node2D, prop: String) -> float:
	match prop:
		"x":
			return node.position.x
		"y":
			return node.position.y
		"rotation":
			return _picture(node).rotation_degrees
		"scale":
			return _picture(node).scale.x
		"alpha":
			return node.modulate.a
	return 0.0


static func write(node: Node2D, prop: String, v: float) -> void:
	match prop:
		"x":
			node.position.x = v
		"y":
			node.position.y = v
		"rotation":
			_picture(node).rotation_degrees = v
		"scale":
			_picture(node).scale = Vector2(v, v)
		"alpha":
			node.modulate.a = v


# For the rollback: where it is, and back (q_save / q_load). A scene under
# rollback= may not hold tweens today (the compiler says so); this is for later.
func q_save() -> Dictionary:
	return {"t": _t, "from": from, "to": to, "repeat": repeat}


func q_load(d: Dictionary) -> void:
	_t = d["t"]
	from = d["from"]
	to = d["to"]
	repeat = d["repeat"]
