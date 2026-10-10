extends CanvasLayer
# qg:goto-scene fade=: the new scene comes out of black. Only the picture
# fades: the tween counts physics ticks, so a frame taken at a tick shows the
# same shade every run, and the game under it runs as it would without.

var _black: ColorRect = null


func start(seconds: float) -> void:
	name = "Fade"
	layer = 128
	process_mode = Node.PROCESS_MODE_ALWAYS
	_black = ColorRect.new()
	_black.color = Color.BLACK
	_black.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_black.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(_black)
	var tween := create_tween()
	tween.set_process_mode(Tween.TWEEN_PROCESS_PHYSICS)
	tween.tween_property(_black, "color:a", 0.0, seconds)
	tween.tween_callback(queue_free)


# For the play protocol: how dark the screen still is, 1 black to 0 clear.
func quantum_view() -> Dictionary:
	return {"kind": "fade", "dark": snappedf(_black.color.a, 0.01)}
