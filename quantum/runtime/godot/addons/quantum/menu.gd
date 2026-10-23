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
# the lockstep carries. A shared field (shared="true") is a draft until Enter
# sends it: the text goes with this machine's input for a tick, and on that
# tick, on every machine, it becomes the bound state and what the field holds
# runs, with `sender` (the seat that sent it) and `text`. In a networked game
# only the machine whose seat the menu is takes the keyboard; the menu waits,
# on every machine, until the text comes back, so it goes on the same there.
# A local menu (local="true", shared fields only) is the menu of whoever
# plays at this machine: of this machine's seat.
#
# A slider (qg:slider) is changed by left and right while it has the focus, a
# step a press, or set where it is clicked: a bus's volume (kept between
# runs) or a number of the state. A key (qg:rebind), once chosen, waits for
# the next key, mouse button or joypad button pressed, which becomes the
# action's; Escape leaves it as it was. Like typing, that is local.
#
# columns= lays the items out in a grid (left and right move along a row,
# unless a slider has the focus); rows= shows so many rows at once, and the
# rest scroll into view with the focus.
#
# A menu of rows (source= and as=) has one button, shown once for each row of
# a list of the state, read every tick: its label, its if= and what it runs
# are of the row (a player of the squad, a club to manage). The buttons are
# made again when the number of rows changes. x= and y= put the menu's top-left
# corner on the screen, in place of position=.
#
# Menus of the same player shown at once (a form and a list beside it) are one
# column for the keys, in the scene's order: one has the keys, down from its
# last item goes to the next one's first, up from its first to the previous
# one's last, and the pointer moving onto an item (or a click on one) brings
# the keys to its menu. Alone, a menu's last item goes round to its first.

var player: int = 1
var local_menu: bool = false      # qg:menu local="true": this machine's seat's
var focus: int = 0
var _scene: Node = null
var _items: Array = []            # [{spec, control, line}]
var _editing: int = -1            # the field being typed in, or -1
var _pointer_seen = null          # the pointer at the last tick (null: not yet seen)
var _if_method = null             # qg:menu if=: the menu is there only while it is true
var _waiting: int = -1            # the key (qg:rebind) waiting for the next key pressed, or -1
var _columns: int = 1
var _scroll: ScrollContainer = null
var _rows_method = null           # source=: the method that reads the rows
var _rows: Array = []             # the rows, as read last
var _row_spec: Dictionary = {}    # the button shown for each row
var _list: Container = null       # where the rows' buttons go
var _font: Font = null
var _size: int = 16
var _keys: bool = false           # of the menus of its player shown at once, this one has the keys
var _skip: bool = false           # the keys came on this tick, from a menu before it: that tap is spent
var _row_box: StyleBoxFlat = null # a row of a list, and the focused one
var _row_lit: StyleBoxFlat = null


var _hidden := false   # if= hid it on a frame before
static var _chose_on := -1   # the physics frame a menu last chose on


func setup(spec: Dictionary, scene: Node) -> void:
	_scene = scene
	player = int(spec.get("player", 1))
	local_menu = bool(spec.get("local", false))
	_if_method = spec.get("if_method")
	name = "Menu"
	layer = 10
	add_to_group("q_menu")
	var box := VBoxContainer.new()
	var w: int = ProjectSettings.get_setting("display/window/size/viewport_width", 256)
	var h: int = ProjectSettings.get_setting("display/window/size/viewport_height", 224)
	box.alignment = BoxContainer.ALIGNMENT_CENTER
	var placed: bool = spec.get("xy") != null   # x= and y=: its top-left corner
	match "xy" if placed else str(spec.get("position", "center")):
		"xy":
			box.position = Vector2(float(spec["xy"][0]), float(spec["xy"][1]))
			box.alignment = BoxContainer.ALIGNMENT_BEGIN
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
	_font = font
	_size = size
	_rows_method = spec.get("rows_method")
	if _rows_method != null:   # a list's rows: lines of text, the focused one lit
		_row_box = StyleBoxFlat.new()
		_row_box.bg_color = Color(0, 0, 0, 0)
		_row_box.set_content_margin_all(1)
		_row_box.content_margin_left = 3
		_row_box.content_margin_right = 3
		_row_lit = _row_box.duplicate()
		_row_lit.bg_color = Color(1, 1, 1, 0.2)
	# the items: a column, or a grid of columns=; in a box that scrolls when rows= says how many show
	_columns = int(spec.get("columns", 1))
	var holder: Container
	if _columns > 1:
		var grid := GridContainer.new()
		grid.columns = _columns
		grid.add_theme_constant_override("h_separation", size)
		holder = grid
	else:
		holder = VBoxContainer.new()
		if _rows_method != null:
			holder.add_theme_constant_override("separation", 0)
	holder.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var start: bool = placed or str(spec.get("position", "center")) in ["top-left", "top-right"]
	var outer: Container = box
	if spec.get("box") != null:   # the items in a frame of the game's, stretched (a sheet with slice=)
		var panel := PanelContainer.new()
		panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
		panel.add_theme_stylebox_override("panel", Q.frame_box(scene.q_game["sheets"][spec["box"]], size * 0.5))
		panel.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN if start else Control.SIZE_SHRINK_CENTER
		box.add_child(panel)
		outer = panel
	if spec.get("rows") != null:
		_scroll = ScrollContainer.new()
		_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
		_scroll.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_SHOW_NEVER
		_scroll.mouse_filter = Control.MOUSE_FILTER_IGNORE
		var line := size * 1.75 + 4   # a button's height
		if _rows_method != null:
			line = ceilf((font if font != null else ThemeDB.fallback_font).get_height(size)) + 2
		_scroll.custom_minimum_size = Vector2(0, int(spec["rows"]) * line)
		_scroll.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN if start else Control.SIZE_SHRINK_CENTER
		_scroll.add_child(holder)
		outer.add_child(_scroll)
	else:
		holder.size_flags_horizontal = Control.SIZE_SHRINK_BEGIN if start else Control.SIZE_SHRINK_CENTER
		outer.add_child(holder)
	var list: Container = holder
	if _rows_method != null:
		_row_spec = spec["items"][0]
		_list = holder
		_sync_rows()
		_refresh()
		return
	for item in spec.get("items", []):
		var entry := {"spec": item, "control": null, "line": null}
		if item["kind"] == "slider" or item["kind"] == "rebind":
			var row := HBoxContainer.new()
			row.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
			row.mouse_filter = Control.MOUSE_FILTER_IGNORE
			row.add_theme_constant_override("separation", size / 2)
			var label := Label.new()
			label.text = str(item.get("label", ""))
			_style(label, font, size)
			row.add_child(label)
			if item["kind"] == "slider":
				var bar := HSlider.new()
				bar.min_value = float(item["min"])
				bar.max_value = float(item["max"])
				bar.step = 0.0
				bar.editable = false
				bar.focus_mode = Control.FOCUS_NONE
				bar.mouse_filter = Control.MOUSE_FILTER_IGNORE
				bar.custom_minimum_size = Vector2(size * 6, size)
				bar.size_flags_vertical = Control.SIZE_SHRINK_CENTER
				row.add_child(bar)
				entry["bar"] = bar
			var value := Label.new()
			_style(value, font, size)
			row.add_child(value)
			entry["value"] = value
			list.add_child(row)
			entry["control"] = row
			_items.append(entry)
			continue
		if item["kind"] == "button":
			var b := _button(item)
			list.add_child(b)
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
			line.text_submitted.connect(_on_submitted.bind(entry))
			line.focus_exited.connect(_on_focus_lost.bind(entry))
			row.add_child(line)
			list.add_child(row)
			entry["control"] = row
			entry["line"] = line
		_items.append(entry)
	_refresh()


func _button(item: Dictionary) -> Button:
	var b := Button.new()
	b.focus_mode = Control.FOCUS_NONE
	b.mouse_filter = Control.MOUSE_FILTER_IGNORE
	if _rows_method != null:   # a list's rows: each as wide as the widest, its text from the left
		b.size_flags_horizontal = Control.SIZE_FILL
		b.alignment = HORIZONTAL_ALIGNMENT_LEFT
		for look in ["normal", "hover", "pressed", "disabled", "focus"]:
			b.add_theme_stylebox_override(look, _row_box)
	else:
		b.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	b.text = str(item.get("label", ""))
	_style(b, _font, _size)
	Q.apply_gd(b, item.get("gd"))
	return b


# source=: the rows read again; a button for each, made again when how many there are changes.
func _sync_rows() -> void:
	if _rows_method == null or ("q_entered" in _scene and not _scene.q_entered):
		return   # before the scene is entered, its computed q:sets (what the rows read) are not set yet
	_rows = _scene.call(_rows_method)
	if _rows.size() == _items.size():
		return
	for entry in _items:
		_list.remove_child(entry["control"])
		entry["control"].queue_free()
	_items.clear()
	for i in _rows.size():
		var b := _button(_row_spec)
		_list.add_child(b)
		_items.append({"spec": _row_spec, "control": b, "line": null})
	if focus >= _items.size():
		focus = maxi(0, _items.size() - 1)


func _style(c: Control, font: Font, size: int) -> void:
	c.add_theme_font_size_override("font_size", size)
	if font != null:
		c.add_theme_font_override("font", font)


func _a(action: String) -> String:
	return action if player == 1 else "p%d_%s" % [player, action]


func _read(bind: String, game: bool):
	return G.get(bind) if game else _scene.get(bind)


func _on_typed(text: String, item: Dictionary) -> void:
	if item.get("shared", false):
		return   # a draft, until it is sent
	if item.get("game", false):
		G.set(item["bind"], text)
	else:
		_scene.set(item["bind"], text)


func _on_submitted(text: String, entry: Dictionary) -> void:
	var spec: Dictionary = entry["spec"]
	if not spec.get("shared", false):
		_stop_editing()
		return
	if entry.has("pending"):
		return
	entry["pending"] = text   # shown until it comes back
	var line: LineEdit = entry["line"]
	if line.has_focus():
		line.release_focus()   # the keys play again; the menu waits for the text to come back
	Q.share(str(spec["key"]), text, player)
	Q.event("sent", {"field": Q.translate(spec.get("label", "")), "text": text})


func _on_focus_lost(entry: Dictionary) -> void:
	if not entry["spec"].get("shared", false):
		_stop_editing()
	elif _editing >= 0 and is_same(_items[_editing], entry) and not entry.has("pending"):
		_on_submitted(entry["line"].text, entry)   # sent as it is


# A text sent from a shared field, on the tick it is for (Q.deliver_said):
# true if it is one of this menu's fields.
func receive(key: String, sender: int, text: String, mine: bool) -> bool:
	for entry in _items:
		var spec: Dictionary = entry["spec"]
		if not spec.get("shared", false) or str(spec["key"]) != key:
			continue
		if spec.get("game", false):
			G.set(spec["bind"], text)
		else:
			_scene.set(spec["bind"], text)
		if mine:
			entry.erase("pending")
		if sender == player and _editing >= 0 and is_same(_items[_editing], entry):
			_editing = -1   # its own seat's text: on every machine on this tick, the menu goes on
			var line: LineEdit = entry["line"]
			if line.has_focus():
				line.release_focus()
		Q.event("message", {"field": Q.translate(spec.get("label", "")), "sender": sender, "text": text})
		if spec.get("handler") != null and _scene.has_method(spec["handler"]):
			_scene.call(spec["handler"], sender, text)
		return true
	return false


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
		return bool(_scene.call(spec["if_method"], _rows[i]) if _rows_method != null else _scene.call(spec["if_method"]))
	return true


func _label(i: int) -> String:
	var spec: Dictionary = _items[i]["spec"]
	if spec.get("label_method") == null:
		return str(spec.get("label", ""))
	return str(_scene.call(spec["label_method"], _rows[i]) if _rows_method != null else _scene.call(spec["label_method"]))


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
	_sync_rows()
	var items := []
	for i in _items.size():
		var spec: Dictionary = _items[i]["spec"]
		var item := {"shown": _shown(i)}
		if spec["kind"] == "button":
			item["button"] = Q.translate(_label(i))
		elif spec["kind"] == "slider":
			item["slider"] = Q.translate(spec.get("label", ""))
			item["value"] = _slider_value(spec)
		elif spec["kind"] == "rebind":
			item["rebind"] = Q.translate(spec.get("label", ""))
			item["key"] = "..." if _waiting == i else Q.key_name(spec["action"])
		else:
			item["field"] = Q.translate(spec.get("label", ""))
			item["value"] = str(_read(spec["bind"], spec.get("game", false)))
			if _editing == i and _items[i]["line"].has_focus():
				item["typing"] = true   # this machine's keys type into it
			if _items[i].has("pending"):
				item["sending"] = _items[i]["pending"]
		items.append(item)
	var view := {"kind": "menu", "player": player, "shown": active(), "focus": focus, "items": items}
	if not _keys and _peers().size() > 1:
		view["keys"] = false   # another menu of its player, shown with it, has them
	if _scroll != null:
		view["scroll"] = _scroll.scroll_vertical   # pixels scrolled down (rows=)
	return view


# For the rollback.
func q_save() -> Dictionary:
	return {"f": focus, "ps": _pointer_seen, "e": _editing, "k": _keys, "s": _skip}


func q_load(d: Dictionary) -> void:
	focus = d["f"]
	_pointer_seen = d["ps"]
	_editing = d["e"]
	_keys = d["k"]
	_skip = d["s"]


# The menus of this player shown now in the scene, in its order (this one among them when it is shown).
func _peers() -> Array:
	var out := []
	if not is_inside_tree():
		return out   # being built
	for m in get_tree().get_nodes_in_group("q_menu"):
		if m.get_parent() == get_parent() and m.player == player and m.active() and not m._shown_indices().is_empty():
			out.append(m)
	return out


func _take(peers: Array) -> void:
	for m in peers:
		m._keys = false
	_keys = true


# Down from the last item, up from the first: the keys go to the next menu (or the previous).
func _pass(peers: Array, step: int) -> void:
	var at := peers.find(self)
	var next = peers[(at + step + peers.size()) % peers.size()]
	_keys = false
	next._keys = true
	next._skip = peers.find(next) > at   # it reads this tick's keys after this one: not this tap again
	var shown: Array = next._shown_indices()
	next.focus = shown[0] if step > 0 else shown[shown.size() - 1]


func active() -> bool:
	return _if_method == null or bool(_scene.call(_if_method))


func _physics_process(_delta: float) -> void:
	if local_menu:
		player = Q.net_player() if Q.external_input else 1   # 0: one who watches, with no seat
		if player == 0:
			return
	if _editing >= 0 or _waiting >= 0:
		return
	if not active():
		_pointer_seen = null   # a pointer that moved while it was away does not choose when it comes back
		_hidden = true
		return
	if _hidden:
		_hidden = false
		if _chose_on == Engine.get_physics_frames():
			return   # shown by what another menu chose on this frame (if="{...}"): that key is not for it
	_sync_rows()
	var shown := _shown_indices()
	if shown.is_empty():
		return
	if not focus in shown:
		focus = shown[0]
	var peers := _peers()
	var holder = null
	for m in peers:
		if m._keys:
			if holder == null:
				holder = m
			else:
				m._keys = false
	if holder == null:
		peers[0]._keys = true   # the first menu shown has the keys until they move
	var pointer = Q.cursors.get(player)
	if pointer != null:
		if _pointer_seen == null:
			_pointer_seen = pointer
		elif pointer != _pointer_seen:
			_pointer_seen = pointer
			var hit := _item_at(pointer)
			if hit >= 0:
				focus = hit
				if not _keys:
					_take(peers)
	if not _keys:
		var clicked := Q.tapped(_a("select")) and Q.held(_a("click")) and pointer != null and _item_at(pointer) >= 0
		if not clicked:
			return
		_take(peers)   # a click on one of its items: the keys come here, and the item is chosen
	if _skip:
		_skip = false
		return
	var at := shown.find(focus)
	var sliding: bool = _items[focus]["spec"]["kind"] == "slider"
	var moved := int(Q.tapped(_a("right"))) - int(Q.tapped(_a("left")))
	var several := peers.size() > 1
	if Q.tapped(_a("down")):
		if several and at + _columns >= shown.size():
			_pass(peers, 1)
			return
		focus = shown[(at + _columns) % shown.size()] if _columns > 1 else shown[(at + 1) % shown.size()]
	elif Q.tapped(_a("up")):
		if several and at - _columns < 0:
			_pass(peers, -1)
			return
		focus = shown[(at - _columns + shown.size() * _columns) % shown.size()] if _columns > 1 \
			else shown[(at - 1 + shown.size()) % shown.size()]
	elif moved != 0 and sliding:
		var spec: Dictionary = _items[focus]["spec"]
		_slide(spec, _slider_value(spec) + moved * float(spec["step"]))
	elif moved != 0 and _columns > 1:
		focus = shown[(at + moved + shown.size()) % shown.size()]
	if Q.tapped(_a("select")):
		var target := focus
		if Q.held(_a("click")) and pointer != null:
			target = _item_at(pointer)
		if target >= 0:
			if _items[target]["spec"]["kind"] == "slider" and Q.held(_a("click")) and pointer != null:
				_slide_to(target, pointer)   # where on the bar it was clicked
			else:
				_choose(target)
	if _scroll != null:
		_see_focus.call_deferred()


func _see_focus() -> void:
	if focus < _items.size() and is_instance_valid(_items[focus]["control"]):
		_scroll.ensure_control_visible(_items[focus]["control"])


func _slider_value(spec: Dictionary) -> float:
	if spec.get("bus") != null:
		return Q.volume(str(spec["bus"]))
	return float(_read(spec["bind"], spec.get("game", false)))


# A slider's new value: within min and max, on a step from min.
func _slide(spec: Dictionary, v: float) -> void:
	var lo := float(spec["min"])
	var step := float(spec["step"])
	v = clampf(lo + roundf((v - lo) / step) * step, lo, float(spec["max"]))
	if spec.get("bus") != null:
		Q.set_volume(str(spec["bus"]), v)
	elif spec.get("game", false):
		G.set(spec["bind"], v)
	else:
		_scene.set(spec["bind"], v)
	Q.event("slide", {"slider": Q.translate(spec.get("label", "")), "value": v})


func _slide_to(i: int, p: Vector2) -> void:
	focus = i
	var bar: HSlider = _items[i]["bar"]
	var r := bar.get_global_rect()
	var spec: Dictionary = _items[i]["spec"]
	var k := clampf((p.x - r.position.x) / maxf(r.size.x, 1.0), 0.0, 1.0)
	_slide(spec, float(spec["min"]) + k * (float(spec["max"]) - float(spec["min"])))


# A key waiting (qg:rebind): the next key, mouse button or joypad button pressed is the action's.
func _input(event: InputEvent) -> void:
	if _waiting < 0 or not event.is_pressed() or event.is_echo():
		return
	var action: String = _items[_waiting]["spec"]["action"]
	var chosen: InputEvent = null
	if event is InputEventKey:
		if (event as InputEventKey).physical_keycode == KEY_ESCAPE:
			_waiting = -1   # as it was
			get_viewport().set_input_as_handled()
			return
		var key := InputEventKey.new()
		key.physical_keycode = (event as InputEventKey).physical_keycode
		chosen = key
	elif event is InputEventMouseButton:
		var mb := InputEventMouseButton.new()
		mb.button_index = (event as InputEventMouseButton).button_index
		chosen = mb
	elif event is InputEventJoypadButton:
		var jb := InputEventJoypadButton.new()
		jb.button_index = (event as InputEventJoypadButton).button_index
		jb.device = event.device
		chosen = jb
	if chosen == null:
		return
	_waiting = -1
	Q.rebind(action, chosen)
	get_viewport().set_input_as_handled()


func _choose(i: int) -> void:
	focus = i
	_chose_on = Engine.get_physics_frames()
	var spec: Dictionary = _items[i]["spec"]
	Q.event("choose", quantum_view()["items"][i])
	if spec["kind"] == "button":
		if _scene.has_method(spec["handler"]):
			if _rows_method != null:
				_scene.call(spec["handler"], _rows[i])   # the row of the button chosen
			else:
				_scene.call(spec["handler"], null, null)
	elif spec["kind"] == "rebind":
		_waiting = i
	elif spec["kind"] == "slider":
		pass   # left and right change it
	else:
		_editing = i
		if Q.resimulating:
			return   # the rollback runs this tick again: the box, and what is typed in it, stay as they are
		var line: LineEdit = _items[i]["line"]
		line.text = str(_read(spec["bind"], spec.get("game", false)))
		line.caret_column = line.text.length()   # typing goes on from the end
		if not Q.external_input or Q.net_player() == player:   # the keyboard of the machine whose seat it is
			line.grab_focus()


func _process(_delta: float) -> void:
	_refresh()


func _refresh() -> void:
	if "q_entered" in _scene and not _scene.q_entered:
		return   # built before the scene is entered: its computed q:sets are not set yet
	visible = active()
	if not visible:
		return   # what a hidden menu shows is read when it shows (if="{subbing}" guards its source)
	_sync_rows()
	var lit := _keys or _peers().size() <= 1   # the focus shows on the menu that has the keys
	for i in _items.size():
		var entry: Dictionary = _items[i]
		var spec: Dictionary = entry["spec"]
		var c: Control = entry["control"]
		c.visible = _shown(i)
		if spec["kind"] == "button" and spec.get("label_method") != null:
			(c as Button).text = _label(i)
		if spec["kind"] == "field" and _editing != i:
			var value := str(entry.get("pending", _read(spec["bind"], spec.get("game", false))))
			if entry["line"].text != value:
				entry["line"].text = value
		if spec["kind"] == "slider":
			var v := _slider_value(spec)
			entry["bar"].value = v
			entry["value"].text = str(int(v)) if v == floorf(v) else str(snappedf(v, 0.01))
		if spec["kind"] == "rebind":
			entry["value"].text = "..." if _waiting == i else Q.key_name(spec["action"])
		c.modulate = Color(1, 1, 1) if i == focus and lit else Color(0.62, 0.62, 0.62)
		if _rows_method != null:
			var box: StyleBoxFlat = _row_lit if i == focus and lit else _row_box
			if c.get_theme_stylebox("normal") != box:
				c.add_theme_stylebox_override("normal", box)
