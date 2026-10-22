extends CanvasLayer
# A qg:dialogue: lines shown one at a time in a box along the bottom of the
# screen, who says it over what is said, a face beside it (portrait=, a
# frame of the dialogue's sheet=). qg:say opens it and pauses the scene
# (qg:pause: the walkers, things and timers stop; a CanvasLayer like this one
# goes on); select shows the next line; after the last one the box closes,
# the scene goes on and the qg:on-end handler runs. With speed=, a line is
# typed in, so many letters a second of the game's ticks (select shows it
# whole). A line with qg:choice offers them under it: up and down move the
# focus, select chooses, and the choice's handler runs before the next line.

var dialogue_name: String = ""
var line: int = -1          # the line shown; -1 while closed
var _lines: Array = []
var _on_end = null
var _scene: Node = null
var _opened_at: int = -1    # the tick it opened: the press that opened it is not "next"
var _panel: PanelContainer = null
var _who: Label = null
var _text: Label = null
var _face: TextureRect = null
var _list: VBoxContainer = null
var _speed: float = 0.0       # letters a second; 0: the whole line at once
var _typed: float = 0.0       # letters shown of the line, as it is typed
var _choices: Array = []      # the choices offered by the line shown (those whose if= holds)
var _focus: int = 0
var _size: int = 24
var _font: Font = null
var _bottom: float = 0.0      # where the box's bottom edge stays, however many lines and choices it holds


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
	_size = size
	_speed = float(spec.get("speed", 0.0))
	var font: Font = null
	if spec.get("font") != null:
		font = Q.font(str(spec["font"]))
	var margin := maxf(4.0, w * 0.02)
	_panel = PanelContainer.new()
	if spec.get("box") != null:   # a frame of the game's, stretched (a sheet with slice=)
		_panel.add_theme_stylebox_override("panel", Q.frame_box(scene.q_game["sheets"][spec["box"]], size * 0.3))
	else:
		var box := StyleBoxFlat.new()
		box.bg_color = Color("#5f7d8c")
		box.border_color = Color("#b0bec5")
		box.set_border_width_all(maxi(2, size / 8))
		box.set_corner_radius_all(maxi(4, size / 2))
		box.set_content_margin_all(size * 0.6)
		_panel.add_theme_stylebox_override("panel", box)
	_panel.position = Vector2(margin, h - margin - size * 4.2)
	_panel.size = Vector2(w - margin * 2, size * 4.2)
	_bottom = h - margin
	var row := HBoxContainer.new()
	_panel.add_child(row)
	if spec.get("sheet") != null and scene.q_game.get("sheets", {}).has(spec["sheet"]):
		var sheet: Dictionary = scene.q_game["sheets"][spec["sheet"]]
		var atlas := AtlasTexture.new()
		atlas.atlas = Q.texture(Q.src_of(sheet))
		atlas.set_meta("q_tile", sheet["tile"])
		_face = TextureRect.new()
		_face.texture = atlas
		_face.custom_minimum_size = Vector2(size * 2.6, size * 2.6)
		_face.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		_face.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		_face.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
		row.add_child(_face)
	var column := VBoxContainer.new()
	column.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(column)
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
	_list = VBoxContainer.new()
	column.add_child(_list)
	_font = font
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


# What a player reads in it (the play protocol): who says what, while it is open,
# and the choices offered, the one with the focus.
func quantum_view() -> Dictionary:
	if line < 0:
		return {}
	var view := {"kind": "dialogue", "name": dialogue_name, "line": line, "lines": _lines.size(),
		"who": Q.translate(_who.text), "text": Q.translate(_text.text)}
	if _typing():
		view["typing"] = true
	if not _choices.is_empty() and not _typing():
		view["choices"] = _choices.map(func(c): return Q.translate(c["shown"]))
		view["focus"] = _focus
	return view


func _show() -> void:
	var spec: Dictionary = _lines[line]
	_who.text = _value(spec, "who")
	_who.visible = _who.text != ""
	_text.text = _value(spec, "text")
	_typed = 0.0
	_text.visible_characters = -1 if _speed <= 0.0 else 0
	if _face != null:
		_face.visible = spec.get("portrait") != null
		if _face.visible:
			var atlas: AtlasTexture = _face.texture
			var tile: Array = atlas.get_meta("q_tile")
			var per_row := maxi(1, int(atlas.atlas.get_width()) / int(tile[0]))
			var f := int(spec["portrait"])
			atlas.region = Rect2((f % per_row) * int(tile[0]), (f / per_row) * int(tile[1]), int(tile[0]), int(tile[1]))
	# the choices of this line whose if= holds as it shows
	_choices = []
	for c in spec.get("choices", []):
		if c.get("if") == null or bool(_scene.call(c["if"])):
			var shown: String = str(_scene.call(c["label_method"])) if c.get("label_method") != null else str(c["label"])
			_choices.append({"shown": shown, "handler": c["handler"]})
	_focus = 0
	_draw_choices()
	Q.event("say", {"dialogue": dialogue_name, "who": Q.translate(_who.text), "text": Q.translate(_text.text)})


func _typing() -> bool:
	return _speed > 0.0 and _text.visible_characters >= 0 and _text.visible_characters < _text.text.length()


func _draw_choices() -> void:
	for c in _list.get_children():
		c.queue_free()
	_list.visible = not _choices.is_empty() and not _typing()
	for i in _choices.size():
		var label := Label.new()
		label.text = ("> " if i == _focus else "  ") + Q.translate(_choices[i]["shown"])
		label.add_theme_font_size_override("font_size", _size)
		label.add_theme_color_override("font_color", Color("#ffca28") if i == _focus else Color("#eceff1"))
		if _font != null:
			label.add_theme_font_override("font", _font)
		_list.add_child(label)
	_fit.call_deferred()


# The box grows upwards to hold its choices (and shrinks back), its bottom where it was.
func _fit() -> void:
	var width := _panel.size.x
	_panel.reset_size()
	_panel.size = Vector2(width, maxf(_panel.get_combined_minimum_size().y, _size * 4.2))
	_panel.position.y = _bottom - _panel.size.y


func _value(spec: Dictionary, key: String) -> String:
	if spec.get(key + "_method") != null:
		return str(_scene.call(spec[key + "_method"]))
	return str(spec.get(key, ""))


func _physics_process(_delta: float) -> void:
	if line < 0 or Engine.get_physics_frames() == _opened_at:
		return
	if _typing():
		_typed += _speed / Q.TICK_RATE
		_text.visible_characters = mini(int(_typed), _text.text.length())
		if Q.tapped("select"):
			_text.visible_characters = -1   # the whole line at once
		if not _typing():
			_draw_choices()
		return
	if not _choices.is_empty():
		var moved := int(Q.tapped("down")) - int(Q.tapped("up"))
		if moved != 0:
			_focus = posmod(_focus + moved, _choices.size())
			_draw_choices()
			return
	if not Q.tapped("select"):
		return
	if not _choices.is_empty():
		var chosen: Dictionary = _choices[_focus]
		Q.event("choose", {"dialogue": dialogue_name, "choice": Q.translate(chosen["shown"])})
		if _scene.has_method(chosen["handler"]):
			_scene.call(chosen["handler"], null, null)
		if _diverted():
			return
	line += 1
	if line < _lines.size():
		_show()
		return
	line = -1
	visible = false
	Q.event("said", {"dialogue": dialogue_name})
	Q.pause(_scene, false)
	if _on_end != null and _scene.has_method(_on_end):
		_scene.call(_on_end, null, null)


# A choice that opened another dialogue (qg:say) goes on there: this one closes
# without its qg:on-end, and the scene stays paused for the other.
func _diverted() -> bool:
	for box in _scene.get_children():
		if box != self and box.has_method("is_open") and String(box.name).begins_with("Dialogue_") and box.is_open():
			line = -1
			visible = false
			Q.event("said", {"dialogue": dialogue_name})
			return true
	return false
