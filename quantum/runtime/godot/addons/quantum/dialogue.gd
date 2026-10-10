extends CanvasLayer
# A qg:dialogue: lines shown one at a time in a box along the bottom of the
# screen, who says it over what is said. qg:say opens it and pauses the
# scene (qg:pause: the walkers, things and timers stop; a CanvasLayer like
# this one goes on); select shows the next line; after the last one the box
# closes, the scene goes on and the qg:on-end handler runs.

var dialogue_name: String = ""
var line: int = -1          # the line shown; -1 while closed
var _lines: Array = []
var _on_end = null
var _scene: Node = null
var _opened_at: int = -1    # the tick it opened: the press that opened it is not "next"
var _panel: PanelContainer = null
var _who: Label = null
var _text: Label = null


func setup(spec: Dictionary, scene: Node) -> void:
	_scene = scene
	dialogue_name = str(spec["name"])
	name = "Dialogue_" + dialogue_name
	_lines = spec["lines"]
	_on_end = spec.get("on_end")
	layer = 20
	var w: int = ProjectSettings.get_setting("display/window/size/viewport_width", 256)
	var h: int = ProjectSettings.get_setting("display/window/size/viewport_height", 224)
	var size := int(spec.get("size", 24))
	var font: Font = null
	if spec.get("font") != null:
		font = Q.font(str(spec["font"]))
	var margin := maxf(4.0, w * 0.02)
	_panel = PanelContainer.new()
	var box := StyleBoxFlat.new()
	box.bg_color = Color("#5f7d8c")
	box.border_color = Color("#b0bec5")
	box.set_border_width_all(maxi(2, size / 8))
	box.set_corner_radius_all(maxi(4, size / 2))
	box.set_content_margin_all(size * 0.6)
	_panel.add_theme_stylebox_override("panel", box)
	_panel.position = Vector2(margin, h - margin - size * 4.2)
	_panel.size = Vector2(w - margin * 2, size * 4.2)
	var column := VBoxContainer.new()
	_panel.add_child(column)
	_who = Label.new()
	_text = Label.new()
	_text.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	for label in [_who, _text]:
		label.add_theme_font_size_override("font_size", size)
		label.add_theme_color_override("font_color", Color("#eceff1"))
		if font != null:
			label.add_theme_font_override("font", font)
		column.add_child(label)
	_who.add_theme_color_override("font_color", Color("#ffca28"))
	add_child(_panel)
	visible = false


func open() -> void:
	line = 0
	_opened_at = Engine.get_physics_frames()
	visible = true
	_show()
	Q.pause(_scene, true)


func is_open() -> bool:
	return line >= 0


# What a player reads in it (the play protocol): who says what, while it is open.
func quantum_view() -> Dictionary:
	if line < 0:
		return {}
	return {"kind": "dialogue", "name": dialogue_name, "line": line, "lines": _lines.size(),
		"who": _who.text, "text": _text.text}


func _show() -> void:
	var spec: Dictionary = _lines[line]
	_who.text = _value(spec, "who")
	_who.visible = _who.text != ""
	_text.text = _value(spec, "text")


func _value(spec: Dictionary, key: String) -> String:
	if spec.get(key + "_method") != null:
		return str(_scene.call(spec[key + "_method"]))
	return str(spec.get(key, ""))


func _physics_process(_delta: float) -> void:
	if line < 0 or Engine.get_physics_frames() == _opened_at:
		return
	if not Q.tapped("select"):
		return
	line += 1
	if line < _lines.size():
		_show()
		return
	line = -1
	visible = false
	Q.pause(_scene, false)
	if _on_end != null and _scene.has_method(_on_end):
		_scene.call(_on_end, null, null)
