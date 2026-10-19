extends CanvasLayer
# Text over the game (qg:hud): counters and texts bound to the scene's (or
# the game's) state, read every frame so the HUD is never stale. With a
# font= the labels use it; size= is the font size. qg:inventory is a row of
# the items held (qg:item), each its picture and how many.

var _scene: Node = null
var _labels: Array = []   # [{label, bind, prefix}], or {inventory: row, size, shown}
var _font: Font = null


func setup(spec: Dictionary, scene: Node) -> void:
	_scene = scene
	name = "Hud"
	var box := VBoxContainer.new()
	var viewport_w: int = ProjectSettings.get_setting("display/window/size/viewport_width", 256)
	var viewport_h: int = ProjectSettings.get_setting("display/window/size/viewport_height", 224)
	var position_ := str(spec.get("position", "top-left"))
	var centered := position_ == "top-center" or position_ == "center" or position_ == "bottom-center"
	var right := position_ == "top-right"
	match position_:
		"top-center":
			box.position = Vector2(0, 4)
			box.size = Vector2(viewport_w, 0)
		"top-right":
			# flush with the right edge, whatever the width of what it shows
			box.position = Vector2(0, 4)
			box.size = Vector2(viewport_w - 4, 0)
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
		font = Q.font(str(spec["font"]))
		if font == null:
			push_warning("quantum: cannot load the font " + str(spec["font"]))
	var size := int(spec.get("size", 8))
	_font = font
	for item in spec.get("items", []):
		if item["kind"] == "inventory":
			var row := HBoxContainer.new()
			row.add_theme_constant_override("separation", 6)
			if centered or right:
				row.alignment = BoxContainer.ALIGNMENT_END if right else BoxContainer.ALIGNMENT_CENTER
			Q.apply_gd(row, item.get("gd"))
			box.add_child(row)
			_labels.append({"inventory": row, "size": int(item["size"]) if item.get("size") != null else size,
				"shown": null})
			continue
		if item["kind"] == "bar":
			var bar := ProgressBar.new()
			bar.show_percentage = false
			bar.max_value = float(item.get("max", 100))
			bar.custom_minimum_size = Vector2(int(item.get("width", 100)), int(item.get("height", 10)))
			bar.size_flags_horizontal = Control.SIZE_SHRINK_END if right else Control.SIZE_SHRINK_BEGIN
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
			if centered or right:
				label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT if right else HORIZONTAL_ALIGNMENT_CENTER
				label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			Q.apply_gd(label, item.get("gd"))
			box.add_child(label)
			_labels.append({"label": label, "bind": item.get("bind"), "prefix": item.get("label", ""),
				"method": item.get("value_method"), "item": item.get("item")})
	_refresh()


func _process(_delta: float) -> void:
	_refresh()


# What a player reads on it (the play protocol): each text as shown, each bar
# as its value against its maximum.
func quantum_view() -> Dictionary:
	_refresh()
	var shown := []
	for entry in _labels:
		if entry.has("bar"):
			shown.append({"bar": entry["bind"], "value": entry["bar"].value, "max": entry["bar"].max_value})
		elif entry.has("inventory"):
			shown.append({"inventory": entry["shown"]})
		else:
			shown.append(Q.translate(entry["label"].text))   # as shown: in the player's language
	return {"kind": "hud", "items": shown}


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
		if entry.has("inventory"):
			_refresh_inventory(entry)
			continue
		var value
		if entry.get("item") != null:
			value = Q.items_held(entry["item"])
		elif entry.get("method") != null:
			value = _scene.call(entry["method"])
		else:
			value = _scene.get(entry["bind"])
			if value == null:
				value = G.get(entry["bind"])
		var text: String = str(value)
		if value is float and value == floorf(value):
			text = str(int(value))
		# a counter's label in the player's language (qg:language), its number as it is
		entry["label"].text = (Q.translate(entry["prefix"]) + " " if entry["prefix"] != "" else "") + text


# The row of items held: built again only when what is held changes.
func _refresh_inventory(entry: Dictionary) -> void:
	var held := {}
	if "Q_ITEMS" in G:
		for item in G.Q_ITEMS:
			if Q.items_held(item) > 0:
				held[item] = Q.items_held(item)
	if held == entry["shown"]:
		return
	entry["shown"] = held
	var row: HBoxContainer = entry["inventory"]
	for c in row.get_children():
		row.remove_child(c)
		c.queue_free()
	var sheets: Dictionary = _scene.q_game.get("sheets", {}) if "q_game" in _scene else {}
	for item in held:
		var spec: Dictionary = G.Q_ITEMS[item]
		if spec.get("sheet") != null and sheets.has(spec["sheet"]):
			var sheet: Dictionary = sheets[spec["sheet"]]
			var texture := Q.texture(str(sheet["src"]))
			if texture != null:
				var w := int(sheet["tile"][0])
				var h := int(sheet["tile"][1])
				var cols := maxi(1, texture.get_width() / w)
				var frame := int(spec.get("frame", 0))
				var atlas := AtlasTexture.new()
				atlas.atlas = texture
				atlas.region = Rect2((frame % cols) * w, (frame / cols) * h, w, h)
				var icon := TextureRect.new()
				icon.texture = atlas
				icon.stretch_mode = TextureRect.STRETCH_KEEP_CENTERED
				row.add_child(icon)
		var count := Label.new()
		count.add_theme_font_size_override("font_size", int(entry["size"]))
		if _font != null:
			count.add_theme_font_override("font", _font)
		count.text = str(held[item]) if spec.get("sheet") != null else Q.translate(str(spec["label"])) + " " + str(held[item])
		row.add_child(count)
