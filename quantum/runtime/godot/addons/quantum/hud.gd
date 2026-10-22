extends CanvasLayer
# Text over the game (qg:hud): counters and texts bound to the scene's (or
# the game's) state, read every frame so the HUD is never stale. With a
# font= the labels use it; size= is the font size. qg:inventory is a row of
# the items held (qg:item), each its picture and how many. A qg:icon is a
# picture, and the item after it shares its line (a heart, then the hearts).
# With if=, it shows only while that is true.
#
# A qg:table is rows of the state in columns, a label for each cell (a grid,
# so the columns line up a space apart whatever the font); its cells are made
# again when the number of rows changes. x= and y= put the HUD's top-left
# corner on the screen; box= draws it in a frame of the game's (a sheet with
# slice=), as a panel of a text screen.

var _scene: Node = null
var _labels: Array = []   # [{label, bind, prefix}], or {inventory: row, size, shown}, or {icon, method, sheet}
var _font: Font = null
var _if_method = null     # if=: shown only while it is true


func setup(spec: Dictionary, scene: Node) -> void:
	_scene = scene
	name = "Hud"
	var box: BoxContainer = VBoxContainer.new()
	var viewport_w: int = ProjectSettings.get_setting("display/window/size/viewport_width", 256)
	var viewport_h: int = ProjectSettings.get_setting("display/window/size/viewport_height", 224)
	var position_ := "xy" if spec.get("xy") != null else str(spec.get("position", "top-left"))
	var centered := position_ == "top-center" or position_ == "center" or position_ == "bottom-center"
	var right := position_ == "top-right" or position_ == "bottom-right"
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
		"bottom-left":
			box.position = Vector2(4, 0)
			box.size = Vector2(viewport_w - 8, viewport_h - 4)
			box.alignment = BoxContainer.ALIGNMENT_END
		"bottom-right":
			box.position = Vector2(0, 0)
			box.size = Vector2(viewport_w - 4, viewport_h - 4)
			box.alignment = BoxContainer.ALIGNMENT_END
		"xy":
			box.position = Vector2(float(spec["xy"][0]), float(spec["xy"][1]))
		_:
			box.position = Vector2(4, 4)
	add_child(box)
	var font: Font = null
	if spec.get("font") != null:
		font = Q.font(str(spec["font"]))
		if font == null:
			push_warning("quantum: cannot load the font " + str(spec["font"]))
	var size := int(spec.get("size", 8))
	if spec.get("box") != null:   # in a frame of the game's, stretched to what it shows
		var panel := PanelContainer.new()
		panel.add_theme_stylebox_override("panel", Q.frame_box(scene.q_game["sheets"][spec["box"]], size * 0.5))
		panel.size_flags_horizontal = Control.SIZE_SHRINK_END if right else (Control.SIZE_SHRINK_CENTER if centered
			else Control.SIZE_SHRINK_BEGIN)
		box.add_child(panel)
		var inside := VBoxContainer.new()
		panel.add_child(inside)
		box = inside
	_font = font
	_if_method = spec.get("if_method")
	var outer: BoxContainer = box
	var line: HBoxContainer = null   # the line an icon opened, for the item after it
	for item in spec.get("items", []):
		box = outer
		if line != null:
			box = line
			line = null
		if item["kind"] == "icon":
			line = HBoxContainer.new()
			line.add_theme_constant_override("separation", 3)
			if centered or right:
				line.alignment = BoxContainer.ALIGNMENT_END if right else BoxContainer.ALIGNMENT_CENTER
			outer.add_child(line)
			var icon := TextureRect.new()
			icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
			icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
			icon.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
			var sheet: Dictionary = scene.q_game["sheets"][item["sheet"]]
			icon.custom_minimum_size = Vector2(sheet["tile"][0], sheet["tile"][1]) * float(item.get("scale", 1.0))
			Q.apply_gd(icon, item.get("gd"))
			line.add_child(icon)
			var entry := {"icon": icon, "sheet": sheet, "frame": int(item.get("frame", 0)), "method": item.get("frame_method"),
				"shown": -1}
			_labels.append(entry)
			continue
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
		if item["kind"] == "table":
			var grid := GridContainer.new()
			grid.columns = item["columns"].size()
			var f: Font = font if font != null else ThemeDB.fallback_font
			# a space between the columns; the rows as close as a text screen's lines
			grid.add_theme_constant_override("h_separation", int(ceilf(f.get_string_size(" ", HORIZONTAL_ALIGNMENT_LEFT,
				-1, size).x)))
			grid.add_theme_constant_override("v_separation", 0)
			if centered or right:
				grid.size_flags_horizontal = Control.SIZE_SHRINK_END if right else Control.SIZE_SHRINK_CENTER
			Q.apply_gd(grid, item.get("gd"))
			box.add_child(grid)
			_labels.append({"table": grid, "spec": item, "size": size, "count": -1, "shown": []})
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
			if item.get("color") != null:
				label.add_theme_color_override("font_color", Color(str(item["color"])))
			if centered or right:
				label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT if right else HORIZONTAL_ALIGNMENT_CENTER
				label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			Q.apply_gd(label, item.get("gd"))
			box.add_child(label)
			_labels.append({"label": label, "bind": item.get("bind"), "prefix": item.get("label", ""),
				"method": item.get("value_method"), "item": item.get("item"), "color_method": item.get("color_method"),
				"color": null})
	_refresh()


func _process(_delta: float) -> void:
	_refresh()


# What a player reads on it (the play protocol): each text as shown, each bar
# as its value against its maximum.
func quantum_view() -> Dictionary:
	_refresh()
	if not visible:
		return {}
	var shown := []
	for entry in _labels:
		if entry.has("icon"):
			shown.append({"icon": entry["shown"]})
		elif entry.has("bar"):
			shown.append({"bar": entry["bind"], "value": entry["bar"].value, "max": entry["bar"].max_value})
		elif entry.has("inventory"):
			shown.append({"inventory": entry["shown"]})
		elif entry.has("table"):
			# the headings, then each row's cells as shown (without the padding)
			var labels := []
			for c in entry["spec"]["columns"]:
				labels.append(Q.translate(str(c.get("label", ""))))
			shown.append({"table": labels, "rows": entry["shown"]})
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
	if _if_method != null:
		visible = bool(_scene.call(_if_method))
	if not visible:
		return   # what it shows is read while it is shown (if="{len(live) > 0}" guards a live[0])
	for entry in _labels:
		if entry.has("icon"):
			var f: int = int(_scene.call(entry["method"])) if entry["method"] != null else int(entry["frame"])
			if f != entry["shown"]:
				entry["shown"] = f
				entry["icon"].texture = Q.frame_texture(entry["sheet"], f)
			continue
		if entry.has("bar"):
			var v = _bound(entry["bind"])
			entry["bar"].value = float(v) if v != null else 0.0
			continue
		if entry.has("inventory"):
			_refresh_inventory(entry)
			continue
		if entry.has("table"):
			_refresh_table(entry)
			continue
		if entry["color_method"] != null:   # color="{...}": read every frame
			var color := str(_scene.call(entry["color_method"]))
			if color != entry["color"]:
				entry["color"] = color
				if color == "":
					entry["label"].remove_theme_color_override("font_color")
				else:
					entry["label"].add_theme_color_override("font_color", Color.from_string(color, Color.WHITE))
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
			var texture := Q.texture(Q.src_of(sheet))
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


# The rows of a qg:table: a label for each cell, made again when how many rows
# there are changes; each cell its column's value of the row, cut or padded to
# the column's width, in its colour.
func _refresh_table(entry: Dictionary) -> void:
	var spec: Dictionary = entry["spec"]
	var columns: Array = spec["columns"]
	var rows: Array = _scene.call(spec["source"])
	if spec.get("rows") != null and rows.size() > int(spec["rows"]):
		rows = rows.slice(0, int(spec["rows"]))
	var heading := false
	for c in columns:
		heading = heading or str(c.get("label", "")) != ""
	var grid: GridContainer = entry["table"]
	if rows.size() != entry["count"]:
		entry["count"] = rows.size()
		for c in grid.get_children():
			grid.remove_child(c)
			c.queue_free()
		for i in (rows.size() + (1 if heading else 0)) * columns.size():
			var label := Label.new()
			label.add_theme_font_size_override("font_size", int(entry["size"]))
			if _font != null:
				label.add_theme_font_override("font", _font)
			var c: Dictionary = columns[i % columns.size()]
			if heading and i < columns.size():
				label.text = Q.fit(Q.translate(str(c.get("label", ""))), int(c["width"]), c["align"])
			grid.add_child(label)
	var cells := grid.get_children()
	var start := columns.size() if heading else 0
	var shown := []
	for r in rows.size():
		var row = rows[r]
		var line := []
		for k in columns.size():
			var c: Dictionary = columns[k]
			var text := Q.fit(str(_scene.call(c["value"], row)), int(c["width"]), c["align"])
			line.append(text.strip_edges())   # as shown, cut to the column, without its padding
			var label: Label = cells[start + r * columns.size() + k]
			label.text = text
			var color = c.get("color")
			if c.get("color_method") != null:
				color = str(_scene.call(c["color_method"], row))
			if color == null or color == "":
				label.remove_theme_color_override("font_color")
			else:
				label.add_theme_color_override("font_color", Color.from_string(str(color), Color.WHITE))
		shown.append(line)
	entry["shown"] = shown
