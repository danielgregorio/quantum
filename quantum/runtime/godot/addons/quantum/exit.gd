extends Area2D
# A way out of the scene (qg:exit): a rectangle. A character that enters it
# leaves for the scene `to`, arriving at that scene's exit named `at`. An
# exit the character arrives inside is disarmed until it has left it, so
# arriving does not send it straight back.

var to: String = ""
var at: String = ""
var _armed: bool = true
var _scene: Node = null


func setup(spec: Dictionary, scene: Node) -> void:
	name = "exit-" + spec["name"]
	to = spec["to"]
	at = spec["at"]
	_scene = scene
	monitorable = false
	collision_mask = 1
	position = Vector2(spec["x"] + spec["width"] / 2.0, spec["y"] + spec["height"] / 2.0)
	var shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = Vector2(spec["width"], spec["height"])
	shape.shape = rect
	add_child(shape)
	body_entered.connect(_on_body_entered)
	body_exited.connect(_on_body_exited)


func disarm() -> void:
	_armed = false


func _on_body_entered(body: Node) -> void:
	if not _armed or not body.is_in_group("q_named"):
		return
	G.set("_q_arrive_at", at)
	Q.goto_scene(_scene, to)


func _on_body_exited(body: Node) -> void:
	if body.is_in_group("q_named"):
		_armed = true
