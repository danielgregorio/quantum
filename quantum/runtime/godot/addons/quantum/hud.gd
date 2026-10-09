extends CanvasLayer
# Text over the game (qg:hud): counters and texts bound to the scene's (or
# the game's) state, read every frame so the HUD is never stale. With a
# font= the labels use it; size= is the font size.

var _scene: Node = null
var _labels: Array = []   # [{label, bind, prefix}]


func setup(spec: Dictionary, scene: Node) -> void:
	_scene = scene
	name = "Hud"
	var box := VBoxContainer.new()
	var viewport_w: int = ProjectSettings.get_setting("display/window/size/viewport_width", 256)
	var viewport_h: int = ProjectSettings.get_setting("display/window/size/viewport_height", 224)
	var position_ := str(spec.get("position", "top-left"))
	var centered := position_ == "top-center" or position_ == "center" or position_ == "bottom-center"
	match position_:
		"top-center":
			box.position = Vector2(0, 4)
			box.size = Vector2(viewport_w, 0)
		"top-right":
			box.position = Vector2(viewport_w - 84, 4)
		"center":
			box.position = Vector2(0, 0)
			box.size = Vector2(viewport_w, viewport_h)
			box.alignment = BoxContainer.ALIGNMENT_CENTER
		"bottom-center":
			box.position = Vector2(0, 0)
			box.size = Vector2(viewport_w, viewport_h - 4)
			box.alignment = BoxContainer.ALIGNMENT_END
		_:
			box.position = Vector2(4, 4)
	add_child(box)
	var font: Font = null
	if spec.get("font") != null:
		var file := FontFile.new()
		if file.load_dynamic_font(ProjectSettings.globalize_path("res://" + str(spec["font"]))) == OK:
			font = file
		else:
			push_warning("quantum: cannot load the font " + str(spec["font"]))
	var size := int(spec.get("size", 8))
	for item in spec.get("items", []):
		if item["kind"] == "bar":
			var bar := ProgressBar.new()
			bar.show_percentage = false
			bar.max_value = float(item.get("max", 100))
			bar.custom_minimum_size = Vector2(int(item.get("width", 100)), int(item.get("height", 10)))
			bar.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN
			var fill := StyleBoxFlat.new()
			fill.bg_color = Color(str(item.get("color", "#e04040")))
			bar.add_theme_stylebox_override("fill", fill)
			var back := StyleBoxFlat.new()
			back.bg_color = Color(0, 0, 0, 0.5)
			bar.add_theme_stylebox_override("background", back)
			Q.apply_gd(bar, item.get("gd"))
			box.add_child(bar)
			_labels.append({"bar": bar, "bind": item["bind"]})
			continue
		if item["kind"] == "counter" or item["kind"] == "text":
			var label := Label.new()
			label.add_theme_font_size_override("font_size", int(item["size"]) if item.get("size") != null else size)
			if font != null:
				label.add_theme_font_override("font", font)
			if centered:
				label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
				label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			Q.apply_gd(label, item.get("gd"))
			box.add_child(label)
			_labels.append({"label": label, "bind": item.get("bind"), "prefix": item.get("label", ""),
				"method": item.get("value_method")})
	_refresh()


func _process(_delta: float) -> void:
	_refresh()


func _bound(bind: String):
	if "." in bind:
		var parts: PackedStringArray = bind.split(".", true, 1)
		var node: Node = _scene.get_node_or_null(parts[0])
		return node.get(parts[1]) if node != null else null
	var value = _scene.get(bind)
	return value if value != null else G.get(bind)


func _refresh() -> void:
	for entry in _labels:
		if entry.has("bar"):
			var v = _bound(entry["bind"])
			entry["bar"].value = float(v) if v != null else 0.0
			continue
		var value
		if entry.get("method") != null:
			value = _scene.call(entry["method"])
		else:
			value = _scene.get(entry["bind"])
			if value == null:
				value = G.get(entry["bind"])
		var text: String = str(value)
		if value is float and value == floorf(value):
			text = str(int(value))
		entry["label"].text = (entry["prefix"] + " " if entry["prefix"] != "" else "") + text
