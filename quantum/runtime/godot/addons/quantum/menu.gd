extends CanvasLayer
# A menu (qg:menu): buttons and text fields over the scene, for one player.
#
# Everything that chooses runs in the physics tick, from the tick's input
# (Q): up/down move the focus, select chooses. The pointer is the player's
# qg:cursor (the builder adds a hidden one when the scene has none), so the
# mouse goes through the same path as in a replay or the lockstep: when the
# pointer moves onto a button the focus goes there. A click (select with the
# mouse button, the "click" action) chooses what is under the pointer, or
# nothing; Enter or the joypad (select alone) chooses what has the focus,
# wherever the pointer rests. Godot's own GUI focus and mouse handling are
# off, so they cannot choose a second way.
#
# A field, once chosen, takes the keyboard until Enter or until it loses the
# focus; what is typed is the bound state. Typing is local: it is not input
# the replay or the lockstep carries.

var player: int = 1
var focus: int = 0
var _scene: Node = null
var _items: Array = []            # [{spec, control, line}]
var _editing: int = -1            # the field being typed in, or -1
var _pointer_seen = null          # the pointer at the last tick (null: not yet seen)
var _if_method = null             # qg:menu if=: the menu is there only while it is true


func setup(spec: Dictionary, scene: Node) -> void:
	_scene = scene
	player = int(spec.get("player", 1))
	_if_method = spec.get("if_method")
	name = "Menu"
	layer = 10
	add_to_group("q_menu")
	var box := VBoxContainer.new()
	var w: int = ProjectSettings.get_setting("display/window/size/viewport_width", 256)
	var h: int = ProjectSettings.get_setting("display/window/size/viewport_height", 224)
	box.alignment = BoxContainer.ALIGNMENT_CENTER
	match str(spec.get("position", "center")):
		"top-left":
			box.position = Vector2(4, 4)
		"top-right":
			box.position = Vector2(w - 160, 4)
		"top-center":
			box.position = Vector2(0, 4)
			box.size = Vector2(w, 0)
		"bottom-center":
			box.size = Vector2(w, h - 8)
			box.alignment = BoxContainer.ALIGNMENT_END
		_:
			box.size = Vector2(w, h)
	add_child(box)
	var font: Font = null
	if spec.get("font") != null:
		font = Q.font(str(spec["font"]))
	var size := int(spec.get("size", 16))
	for item in spec.get("items", []):
		var entry := {"spec": item, "control": null, "line": null}
		if item["kind"] == "button":
			var b := Button.new()
			b.focus_mode = Control.FOCUS_NONE
			b.mouse_filter = Control.MOUSE_FILTER_IGNORE
			b.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
			b.text = str(item.get("label", ""))
			_style(b, font, size)
			Q.apply_gd(b, item.get("gd"))
			box.add_child(b)
			entry["control"] = b
		else:
			var row := HBoxContainer.new()
			row.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
			row.mouse_filter = Control.MOUSE_FILTER_IGNORE
			if str(item.get("label", "")) != "":
				var label := Label.new()
				label.text = str(item["label"])
				_style(label, font, size)
				row.add_child(label)
			var line := LineEdit.new()
			line.max_length = int(item.get("max_length", 64))
			line.custom_minimum_size = Vector2(size * 10, 0)
			line.mouse_filter = Control.MOUSE_FILTER_IGNORE
			line.focus_mode = Control.FOCUS_CLICK
			line.text = str(_read(item["bind"], item.get("game", false)))
			_style(line, font, size)
			line.text_changed.connect(_on_typed.bind(item))
			line.text_submitted.connect(func(_t): _stop_editing())
			line.focus_exited.connect(_stop_editing)
			row.add_child(line)
			box.add_child(row)
			entry["control"] = row
			entry["line"] = line
		_items.append(entry)
	_refresh()


func _style(c: Control, font: Font, size: int) -> void:
	c.add_theme_font_size_override("font_size", size)
	if font != null:
		c.add_theme_font_override("font", font)


func _a(action: String) -> String:
	return action if player == 1 else "p%d_%s" % [player, action]


func _read(bind: String, game: bool):
	return G.get(bind) if game else _scene.get(bind)


func _on_typed(text: String, item: Dictionary) -> void:
	if item.get("game", false):
		G.set(item["bind"], text)
	else:
		_scene.set(item["bind"], text)


func _stop_editing() -> void:
	if _editing < 0:
		return
	var line: LineEdit = _items[_editing]["line"]
	_editing = -1
	if line.has_focus():
		line.release_focus()


func _shown(i: int) -> bool:
	var spec: Dictionary = _items[i]["spec"]
	if spec.get("if_method") != null:
		return bool(_scene.call(spec["if_method"]))
	return true


func _shown_indices() -> Array:
	var out := []
	for i in _items.size():
		if _shown(i):
			out.append(i)
	return out


func _item_at(p: Vector2) -> int:
	for i in _shown_indices():
		var c: Control = _items[i]["control"]
		if c.get_global_rect().has_point(p):
			return i
	return -1


# What a player sees of it (the play protocol, PLAN_PLAY_PROTOCOL.md): its
# buttons and fields as shown, which are choosable, and which has the focus.
func quantum_view() -> Dictionary:
	var items := []
	for i in _items.size():
		var spec: Dictionary = _items[i]["spec"]
		var item := {"shown": _shown(i)}
		if spec["kind"] == "button":
			item["button"] = str(_scene.call(spec["label_method"])) if spec.get("label_method") != null \
				else str(spec.get("label", ""))
		else:
			item["field"] = str(spec.get("label", ""))
			item["value"] = str(_read(spec["bind"], spec.get("game", false)))
		items.append(item)
	return {"kind": "menu", "player": player, "shown": active(), "focus": focus, "items": items}


# For the rollback.
func q_save() -> Dictionary:
	return {"f": focus, "ps": _pointer_seen}


func q_load(d: Dictionary) -> void:
	focus = d["f"]
	_pointer_seen = d["ps"]


func active() -> bool:
	return _if_method == null or bool(_scene.call(_if_method))


func _physics_process(_delta: float) -> void:
	if _editing >= 0:
		return
	if not active():
		_pointer_seen = null   # a pointer that moved while it was away does not choose when it comes back
		return
	var shown := _shown_indices()
	if shown.is_empty():
		return
	if not focus in shown:
		focus = shown[0]
	var pointer = Q.cursors.get(player)
	if pointer != null:
		if _pointer_seen == null:
			_pointer_seen = pointer
		elif pointer != _pointer_seen:
			_pointer_seen = pointer
			var hit := _item_at(pointer)
			if hit >= 0:
				focus = hit
	var at := shown.find(focus)
	if Q.tapped(_a("down")):
		focus = shown[(at + 1) % shown.size()]
	elif Q.tapped(_a("up")):
		focus = shown[(at - 1 + shown.size()) % shown.size()]
	if Q.tapped(_a("select")):
		var target := focus
		if Q.held(_a("click")) and pointer != null:
			target = _item_at(pointer)
		if target >= 0:
			_choose(target)


func _choose(i: int) -> void:
	focus = i
	var spec: Dictionary = _items[i]["spec"]
	Q.event("choose", quantum_view()["items"][i])
	if spec["kind"] == "button":
		if _scene.has_method(spec["handler"]):
			_scene.call(spec["handler"], null, null)
	else:
		_editing = i
		var line: LineEdit = _items[i]["line"]
		line.text = str(_read(spec["bind"], spec.get("game", false)))
		line.grab_focus()


func _process(_delta: float) -> void:
	_refresh()


func _refresh() -> void:
	visible = active()
	for i in _items.size():
		var entry: Dictionary = _items[i]
		var spec: Dictionary = entry["spec"]
		var c: Control = entry["control"]
		c.visible = _shown(i)
		if spec["kind"] == "button" and spec.get("label_method") != null:
			(c as Button).text = str(_scene.call(spec["label_method"]))
		if spec["kind"] == "field" and _editing != i:
			var value := str(_read(spec["bind"], spec.get("game", false)))
			if entry["line"].text != value:
				entry["line"].text = value
		c.modulate = Color(1, 1, 1) if i == focus else Color(0.62, 0.62, 0.62)
