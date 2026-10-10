extends Sprite2D
# A qg:sprite whose frame= is an expression: each tick it shows the frame the
# scene's compiled method answers (a fighter's face while it is hurt...).

var _scene: Node = null
var _method: String = ""


func follow(scene: Node, method: String) -> void:
	_scene = scene
	_method = method
	_show()


func _physics_process(_delta: float) -> void:
	_show()


func _show() -> void:
	var f := int(_scene.call(_method))
	if f >= 0 and f < hframes * vframes:
		frame = f
