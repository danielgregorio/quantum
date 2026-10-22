extends CanvasLayer
# On a touch screen, what presses the game's actions: buttons
# (qg:touch-button) and sticks (qg:touch-stick), over the scene. A button
# presses its action while a finger is on it; a stick, dragged from its
# middle, presses left, right, up and down as far as it is pushed (the
# strength() of each). They press the actions as keys would, so the tick
# reads them the same way, a replay records the actions, and the lockstep
# carries them. show="touch" (the default) puts them only on a device with
# a touch screen; show="always" everywhere, the mouse working them too.

const DEAD := 0.25   # how far a stick goes before it presses a direction

var _controls: Array = []   # [{spec, at, radius, finger, pushed: Vector2}]
var _canvas: Node2D = null


func setup(specs: Array) -> void:
	name = "Touch"
	layer = 30
	var touchscreen := DisplayServer.is_touchscreen_available()
	for spec in specs:
		if str(spec.get("show", "touch")) == "touch" and not touchscreen:
			continue
		_controls.append({"spec": spec, "at": Vector2(float(spec["x"]), float(spec["y"])),
			"radius": float(spec["size"]) / 2.0, "finger": null, "pushed": Vector2.ZERO})
	_canvas = Node2D.new()
	_canvas.draw.connect(_draw_controls)
	add_child(_canvas)


func _action(spec: Dictionary, action: String) -> String:
	var p := int(spec.get("player", 1))
	return action if p == 1 else "p%d_%s" % [p, action]


func _input(event: InputEvent) -> void:
	var finger = null
	var at := Vector2.ZERO
	var down := false
	var moved := false
	if event is InputEventScreenTouch:
		finger = event.index
		at = event.position
		down = event.pressed
	elif event is InputEventScreenDrag:
		finger = event.index
		at = event.position
		moved = true
	elif event.device == InputEvent.DEVICE_ID_EMULATION:
		return   # a mouse event Godot made from a touch: the touch itself is what counts
	elif event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		finger = "mouse"   # the mouse works a control only where it is shown everywhere (show="always")
		at = event.position
		down = event.pressed
	elif event is InputEventMouseMotion and (event.button_mask & MOUSE_BUTTON_MASK_LEFT) != 0:
		finger = "mouse"
		at = event.position
		moved = true
	else:
		return
	for c in _controls:
		if finger is String and str(c["spec"].get("show", "touch")) != "always":
			continue
		var same: bool = typeof(c["finger"]) == typeof(finger) and c["finger"] == finger
		if moved:
			if same and c["spec"]["kind"] == "stick":
				_push(c, at)
			continue
		if down and c["finger"] == null and at.distance_to(c["at"]) <= c["radius"] * 1.25:
			c["finger"] = finger
			if c["spec"]["kind"] == "button":
				Input.action_press(_action(c["spec"], str(c["spec"]["action"])))
			else:
				_push(c, at)
			_canvas.queue_redraw()
		elif not down and same:
			c["finger"] = null
			if c["spec"]["kind"] == "button":
				Input.action_release(_action(c["spec"], str(c["spec"]["action"])))
			else:
				_push(c, c["at"])
			_canvas.queue_redraw()


# Leaving the scene with a finger on a control: what it pressed is let go.
func _exit_tree() -> void:
	for c in _controls:
		if c["finger"] == null:
			continue
		c["finger"] = null
		if c["spec"]["kind"] == "button":
			Input.action_release(_action(c["spec"], str(c["spec"]["action"])))
		else:
			_push(c, c["at"])


# A stick pushed to `at`: each direction pressed as far as it goes past the dead zone.
func _push(c: Dictionary, at: Vector2) -> void:
	var v: Vector2 = (at - c["at"]) / c["radius"]
	if v.length() > 1.0:
		v = v.normalized()
	c["pushed"] = v
	var spec: Dictionary = c["spec"]
	for pair in [["right", v.x], ["left", -v.x], ["down", v.y], ["up", -v.y]]:
		var action := _action(spec, pair[0])
		if not InputMap.has_action(action):
			continue
		if pair[1] > DEAD:
			Input.action_press(action, clampf((pair[1] - DEAD) / (1.0 - DEAD), 0.05, 1.0))
		elif Input.is_action_pressed(action):
			Input.action_release(action)
	_canvas.queue_redraw()


func _draw_controls() -> void:
	for c in _controls:
		var held: bool = c["finger"] != null
		var at: Vector2 = c["at"]
		var r: float = c["radius"]
		_canvas.draw_circle(at, r, Color(1, 1, 1, 0.22 if held else 0.12))
		_canvas.draw_arc(at, r, 0.0, TAU, 32, Color(1, 1, 1, 0.5), 1.5)
		if c["spec"]["kind"] == "stick":
			_canvas.draw_circle(at + (c["pushed"] as Vector2) * r * 0.6, r * 0.38, Color(1, 1, 1, 0.45))
		elif str(c["spec"].get("label", "")) != "":
			var font := ThemeDB.fallback_font
			var size := int(r * 0.9)
			var text := str(c["spec"]["label"])
			var w := font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x
			_canvas.draw_string(font, at + Vector2(-w / 2.0, size * 0.35), text, HORIZONTAL_ALIGNMENT_LEFT, -1, size,
				Color(1, 1, 1, 0.8))


# What a player sees of them (the play protocol): each control, and what it presses now.
func quantum_view() -> Dictionary:
	if _controls.is_empty():
		return {}
	var shown := []
	for c in _controls:
		var item := {"kind": c["spec"]["kind"], "x": c["at"].x, "y": c["at"].y, "held": c["finger"] != null}
		if c["spec"]["kind"] == "button":
			item["action"] = c["spec"]["action"]
		shown.append(item)
	return {"kind": "touch", "controls": shown}
