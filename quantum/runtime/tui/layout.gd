extends RefCounted
# A page's view tree (quantum/runtime/ui_view.py) laid out in cells (SPEC.md UI-20).
#
# The same tree the console and the Hive's screen draw, in a grid of characters
# of one width: boxes with borders, rows of fields, tables in columns. What it
# makes is data the window draws and a test reads: the grid (a character and a
# style a cell), the items that react (where each is, what it is), the regions
# the motions move, the progress bars and the images. A cell is one column; a
# wide character (CJK, most emoji) takes two, the second left empty.

const BREAKPOINTS := {"sm": 80, "md": 96, "lg": 128}

var cols := 120
var grid: Array = []          # rows of [char, style] pairs; "" is the right half of a wide character
var items: Array = []         # what reacts: {kind, x, y, w, h, key, label, bind, ...}
var regions: Array = []       # {kind, speed, what, ms, x, y, w, h}: what a motion moves, as `motions`
var tab_regions: Array = []   # {what, x, y, w, h}: the open tab's content, which expands when the user opens it
var progress: Array = []      # {id, value, max}
var images: Array = []        # {src, alt, x, y, w, h}
var forms: Array = []         # {event, items: [item index]}
var motions: Array = []       # in document order, as the page asks for them (UI-19)
var unsupported: Array = []   # the kinds of ui:* drawn as "not drawn" (UI-7)
var height := 0
var right_edge := 1000000      # the column a node being laid out may not write past (its x + w)

var state: Dictionary         # what the user changed, by key: {value, checked}; kept across layouts
var tabs: Dictionary          # the open tab of each tab panel, by key
var motion_on := true
var focus_key := ""           # the item with the focus: its field shows its value as typed
var streams: Dictionary       # IA-7: a stream's text so far, by its url
var textures: Dictionary      # an image's size in cells once it has loaded, by its src


# -- characters -------------------------------------------------------------

static func char_width(c: int) -> int:
	if c < 0x1100:
		return 1
	if (c <= 0x115F) or (c >= 0x2E80 and c <= 0x303E) or (c >= 0x3041 and c <= 0x33FF) \
			or (c >= 0x3400 and c <= 0x4DBF) or (c >= 0x4E00 and c <= 0x9FFF) or (c >= 0xA000 and c <= 0xA4CF) \
			or (c >= 0xAC00 and c <= 0xD7A3) or (c >= 0xF900 and c <= 0xFAFF) or (c >= 0xFE30 and c <= 0xFE4F) \
			or (c >= 0xFF00 and c <= 0xFF60) or (c >= 0xFFE0 and c <= 0xFFE6) or (c >= 0x1F300 and c <= 0x1F64F) \
			or (c >= 0x1F900 and c <= 0x1F9FF) or (c >= 0x20000 and c <= 0x3FFFD):
		return 2
	return 1


static func text_width(text: String) -> int:
	var n := 0
	for i in text.length():
		n += char_width(text.unicode_at(i))
	return n


static func cut(text: String, width: int) -> String:
	# As much of the text as fits in `width` cells.
	var out := ""
	var used := 0
	for i in text.length():
		var w := char_width(text.unicode_at(i))
		if used + w > width:
			break
		out += text[i]
		used += w
	return out


static func wrap_text(text: String, width: int) -> Array:
	# The text in lines of at most `width` cells, broken at spaces (a longer word is cut).
	var lines: Array = []
	width = max(1, width)
	for paragraph in text.split("\n"):
		var line := ""
		for word in paragraph.split(" "):
			var candidate := word if line == "" else line + " " + word
			if text_width(candidate) <= width:
				line = candidate
				continue
			if line != "":
				lines.append(line)
			line = word
			while text_width(line) > width:
				var head := cut(line, width)
				lines.append(head)
				line = line.substr(head.length())
		lines.append(line)
	return lines


static func truthy(value) -> bool:
	if value is bool:
		return value
	if value == null:
		return false
	var s := str(value).strip_edges().to_lower()
	return s != "" and s != "false" and s != "0" and s != "off" and s != "no"


static func prop(node: Dictionary, name: String, fallback = "") -> Variant:
	var props: Dictionary = node.get("props", {})
	var value = props.get(name, fallback)
	return fallback if value == null else value


static func num(node: Dictionary, name: String, fallback: int = 0) -> int:
	# a number the page gave as text ("300") or as JSON (300, read as 300.0); `fallback` when it is neither
	var value = prop(node, name, null)
	if value is int or value is float:
		return int(value)
	var text := str(value).strip_edges() if value != null else ""
	return int(text.to_float()) if text.is_valid_float() else fallback


static func has_num(node: Dictionary, name: String) -> bool:
	var value = prop(node, name, null)
	return value is int or value is float or (value != null and str(value).strip_edges().is_valid_float())


static func label_of(node: Dictionary) -> String:
	var text := str(prop(node, "text", ""))
	if text == "":
		text = str(prop(node, "label", ""))
	return text


# -- the grid ---------------------------------------------------------------

func _row(y: int) -> Array:
	while grid.size() <= y:
		var row: Array = []
		row.resize(cols)
		for x in cols:
			row[x] = [" ", ""]
		grid.append(row)
	return grid[y]


func put(x: int, y: int, text: String, style: String = "", width: int = -1) -> int:
	# Writes the text from (x, y), at most `width` cells (the row's end by default); the cells used.
	var row := _row(y)
	var limit: int = min(cols, right_edge) if width < 0 else min(cols, right_edge, x + width)
	var at := x
	for i in text.length():
		var c := text.unicode_at(i)
		var w := char_width(c)
		if at + w > limit:
			break
		if at >= 0:
			row[at] = [text[i], style]
			if w == 2:
				row[at + 1] = ["", style]
		at += w
	return at - x


func fill(x: int, y: int, w: int, style: String, ch: String = " ") -> void:
	var row := _row(y)
	for i in range(max(0, x), min(cols, right_edge, x + w)):
		row[i] = [ch, style]


func box(x: int, y: int, w: int, h: int, title: String, style: String = "border") -> void:
	# A frame of box-drawing characters, its title in the top edge.
	if w < 2 or h < 2:
		return
	put(x, y, "┌" + "─".repeat(w - 2) + "┐", style)
	for r in range(y + 1, y + h - 1):
		put(x, r, "│", style)
		put(x + w - 1, r, "│", style)
	put(x, y + h - 1, "└" + "─".repeat(w - 2) + "┘", style)
	if title != "":
		put(x + 2, y, " " + cut(title, w - 6) + " ", "title")


func text_rows() -> Array:
	# The grid as lines of text, the trailing spaces gone (what a test reads).
	var out: Array = []
	for row in grid:
		var line := ""
		for cell in row:
			line += cell[0]
		out.append(line.rstrip(" "))
	return out


# -- laying out -------------------------------------------------------------

func run(view: Array, width: int, flash: String = "", flash_error := false) -> void:
	cols = max(20, width)
	grid = []
	items = []
	regions = []
	tab_regions = []
	progress = []
	images = []
	forms = []
	motions = []
	unsupported = []
	var y := 0
	if flash != "":
		for line in wrap_text(flash, cols - 4):
			fill(0, y, cols, "flash_error" if flash_error else "flash")
			put(2, y, line, "flash_error" if flash_error else "flash")
			y += 1
		y += 1
	right_edge = cols
	var ctx := {"form": -1, "card": "", "key": "v"}
	y += stack(view, 1, y, cols - 2, ctx, 0)
	height = y
	_row(max(0, height - 1))


func gap_rows(node: Dictionary) -> int:
	var gap := str(prop(node, "gap", ""))
	return 1 if gap in ["md", "lg", "xl", "2xl"] else 0


func stack(nodes: Array, x: int, y: int, w: int, ctx: Dictionary, gap: int) -> int:
	# The nodes one under the other; the rows they take.
	var used := 0
	var first := true
	for i in nodes.size():
		var node = nodes[i]
		if not (node is Dictionary):
			continue
		if not first and gap > 0:
			used += gap
		var inner := ctx.duplicate()
		inner["key"] = "%s/%d" % [ctx["key"], i]
		var h := place(node, x, y + used, w, inner)
		if h > 0:
			first = false
		used += h
	return used


func natural(node: Dictionary) -> int:
	# The width a node asks for, in cells, before it is given any.
	var kind := str(node.get("type", ""))
	var children: Array = node.get("children", [])
	if has_num(node, "width"):
		return max(4, num(node, "width") / 8)
	match kind:
		"text", "footer", "stream", "alert":
			var longest := 0
			for line in str(prop(node, "text", "")).split("\n"):
				longest = max(longest, text_width(line))
			return min(longest, 60)
		"badge":
			return text_width(label_of(node)) + 2
		"link":
			return max(1, text_width(label_of(node)))
		"button":
			return text_width(label_of(node)) + 4
		"input":
			return 24
		"checkbox", "switch":
			return 6 + text_width(str(prop(node, "label", "")))
		"select":
			var longest := 4
			for o in _options(node):
				longest = max(longest, text_width(o[0]))
			return longest + 4
		"radio":
			var n := 0
			for o in _options(node):
				n += text_width(o[0]) + 6
			return n
		"image":
			return text_width(str(prop(node, "alt", "image"))) + 2
		"progress":
			return 24
		"hbox":
			var total := 0
			for c in children:
				if c is Dictionary:
					total += natural(c) + 1
			return total
		"panel", "card":
			var inner := text_width(str(prop(node, "title", ""))) + 4
			for c in children:
				if c is Dictionary:
					inner = max(inner, natural(c) + 4)
			return inner
		_:
			var widest := 0
			if str(prop(node, "title", "")) != "":
				widest = text_width(str(prop(node, "title", "")))
			for c in children:
				if c is Dictionary:
					widest = max(widest, natural(c))
			return widest


func _options(node: Dictionary) -> Array:
	# [label, value] of a select's or a radio's options (options="a,b" and ui:option children).
	var out: Array = []
	for o in str(prop(node, "options", "")).split(","):
		if o.strip_edges() != "":
			out.append([o.strip_edges(), o.strip_edges()])
	for c in node.get("children", []):
		if c is Dictionary and c.get("type", "") == "option":
			var value := str(prop(c, "value", ""))
			var label := str(prop(c, "label", value))
			out.append([label if label != "" else value, value])
	return out


func _note_motion(node: Dictionary, x: int, y: int, w: int, h: int) -> void:
	# UI-19: what moves when the page is shown, recorded in document order.
	if not motion_on:
		return
	var kind := str(node.get("type", ""))
	var props: Dictionary = node.get("props", {})
	var m := ""
	var what := ""
	if kind == "window":
		m = str(props.get("transition", "")) if props.get("transition", null) != null else ""
		what = "page"
	else:
		m = str(props.get("enter", "")) if props.get("enter", null) != null else ""
		if m == "" and kind == "animate" and str(props.get("anim_type", "")) in ["fade", "slide", "expand"]:
			m = str(props.get("anim_type", ""))
		what = str(props.get("ui_id", "")) if props.get("ui_id", null) != null and str(props.get("ui_id", "")) != "" else kind
	if not (m in ["fade", "slide", "expand"]):
		return
	var speed := str(props.get("speed", "normal")) if props.get("speed", null) != null else "normal"
	if speed == "":
		speed = "normal"
	var ms := 150 if speed == "fast" else 250
	motions.append({"kind": m, "speed": speed, "what": what})
	regions.append({"kind": m, "speed": speed, "what": what, "ms": ms, "x": x, "y": y, "w": w, "h": h})


func _item(entry: Dictionary) -> int:
	entry["card"] = entry.get("card", "")
	items.append(entry)
	return items.size() - 1


func _field_value(key: String, node: Dictionary) -> String:
	var kept: Dictionary = state.get(key, {})
	if kept.has("value"):
		return str(kept["value"])
	return str(prop(node, "value", ""))


func _field_checked(key: String, node: Dictionary) -> bool:
	var kept: Dictionary = state.get(key, {})
	if kept.has("checked"):
		return bool(kept["checked"])
	return truthy(prop(node, "checked", false))


func place(node: Dictionary, x: int, y: int, w: int, ctx: Dictionary) -> int:
	# Lays the node out at (x, y), `w` cells wide; the rows it takes.
	var first_motion := motions.size()
	var outer_edge := right_edge
	right_edge = min(right_edge, x + w)
	var h := _place(node, x, y, w, ctx)
	right_edge = outer_edge
	if h > 0:
		var before := motions.size()
		_note_motion(node, x, y, w, h)
		if motions.size() > before:
			# its motion comes before its children's, in document order as the browser runs them
			motions.insert(first_motion, motions.pop_back())
			regions.insert(first_motion, regions.pop_back())
	var error := str(prop(node, "error", ""))
	if error != "" and str(node.get("type", "")) in ["input", "select", "checkbox", "switch", "radio"]:
		for line in wrap_text(error, w):
			put(x, y + h, line, "error", w)
			h += 1
	return h


func _place(node: Dictionary, x: int, y: int, w: int, ctx: Dictionary) -> int:
	var kind := str(node.get("type", ""))
	var children: Array = node.get("children", [])
	var key: String = ctx["key"]
	if has_num(node, "width") and kind in ["vbox", "panel", "card", "input", "select", "progress", "section"]:
		w = min(w, max(4, num(node, "width") / 8))
	match kind:
		"window", "vbox", "scrollbox", "cardbody", "cardfooter", "tab", "animate", "list", "page":
			return stack(children, x, y, w, ctx, gap_rows(node))
		"form":
			var inner := ctx.duplicate()
			forms.append({"event": node.get("event", {}), "items": [], "key": key})
			inner["form"] = forms.size() - 1
			return stack(children, x, y, w, inner, gap_rows(node))
		"section", "header", "cardheader":
			var title := str(prop(node, "title", ""))
			if title == "" and kind != "section":
				title = str(prop(node, "text", ""))
			var used := 0
			if title != "":
				for line in wrap_text(title, w):
					put(x, y + used, line, "bold")
					used += 1
			return used + stack(children, x, y + used, w, ctx, gap_rows(node))
		"formitem":
			var used := 0
			var label := str(prop(node, "label", ""))
			if label != "":
				put(x, y, cut(label, w), "muted")
				used = 1
			return used + stack(children, x, y + used, w, ctx, 0)
		"panel", "card":
			var inner := ctx.duplicate()
			inner["card"] = str(prop(node, "title", ""))
			var body := stack(children, x + 2, y + 1, w - 4, inner, gap_rows(node))
			var h := body + 2
			box(x, y, w, h, str(prop(node, "title", "")))
			return h
		"hbox":
			return _hbox(node, x, y, w, ctx)
		"grid":
			return _grid(node, x, y, w, ctx)
		"tabpanel":
			return _tabpanel(node, x, y, w, ctx)
		"table":
			return _table(node, x, y, w, ctx)
		"item":
			put(x, y, "•", "muted")
			return max(1, stack(children, x + 2, y, w - 2, ctx, 0))
		"text", "footer":
			var style := "muted" if kind == "footer" else ("bold" if str(prop(node, "weight", "")) == "bold" else "")
			var used := 0
			for line in wrap_text(str(prop(node, "text", "")), w):
				put(x, y + used, line, style)
				used += 1
			return used
		"stream":
			var url := str(prop(node, "url", ""))
			var text := str(streams.get(url, prop(node, "text", "")))
			var used := 0
			for line in wrap_text(text, w):
				put(x, y + used, line, "")
				used += 1
			_item({"kind": "stream", "x": x, "y": y, "w": w, "h": max(1, used), "key": key, "url": url,
				   "label": "", "card": ctx["card"], "react": false})
			return max(1, used)
		"alert":
			var danger := str(prop(node, "variant", "")) in ["danger", "error"]
			var title := str(prop(node, "title", ""))
			var text := (title + ": " if title != "" else "") + str(prop(node, "text", ""))
			var style := "flash_error" if danger else "flash"
			var lines := wrap_text(text, w - 2)
			for i in lines.size():
				fill(x, y + i, w, style)
				put(x + 1, y + i, lines[i], style)
			return lines.size()
		"badge":
			var text := " " + label_of(node) + " "
			put(x, y, text, "badge")
			return 1
		"rule":
			put(x, y, "─".repeat(w), "border")
			return 1
		"spacer":
			return 1
		"progress":
			var maximum := float(num(node, "max", 100)) if not str(prop(node, "max", "")).contains(".") else str(prop(node, "max", "")).to_float()
			var value := str(prop(node, "value", "0")).to_float() if has_num(node, "value") else 0.0
			var bar: int = max(4, min(w, 40) - 6)
			var done := int(round(bar * clamp(value / max(maximum, 0.0001), 0.0, 1.0)))
			put(x, y, "█".repeat(done), "accent")
			put(x + done, y, "░".repeat(bar - done), "muted")
			put(x + bar + 1, y, "%d%%" % int(round(100.0 * value / max(maximum, 0.0001))), "muted")
			progress.append({"id": str(prop(node, "ui_id", "")), "value": value, "max": maximum})
			return 1
		"image":
			var alt := str(prop(node, "alt", ""))
			if alt == "":
				alt = str(prop(node, "src", "image"))
			var src := str(prop(node, "src", ""))
			var size: Vector2i = textures.get(src, Vector2i.ZERO)
			var iw: int = min(w, size.x) if size.x > 0 else min(w, text_width(alt) + 2)
			var ih: int = size.y if size.y > 0 else 1
			put(x, y, "[" + cut(alt, max(1, iw - 2)) + "]", "muted")
			images.append({"src": src, "alt": alt, "x": x, "y": y, "w": iw, "h": ih, "loaded": size.x > 0})
			return ih
		"link":
			var label := label_of(node)
			if label == "":
				label = str(prop(node, "to", ""))
			var lines := wrap_text(label, w)
			for i in lines.size():
				put(x, y + i, lines[i], "link")
			_item({"kind": "link", "x": x, "y": y, "w": min(w, text_width(label)), "h": lines.size(), "key": key,
				   "label": label, "to": str(prop(node, "to", "/")), "card": ctx["card"], "form": ctx["form"]})
			return lines.size()
		"button":
			var label := label_of(node)
			var text := "[ " + label + " ]"
			var disabled := truthy(prop(node, "disabled", false))
			var variant := str(prop(node, "variant", ""))
			var style := "button_disabled" if disabled else ("button_" + variant if variant in ["primary", "danger"] else "button")
			var used := put(x, y, cut(text, w), style)
			if not disabled:
				var entry := {"kind": "button", "x": x, "y": y, "w": used, "h": 1, "key": key, "label": label,
							  "card": ctx["card"], "form": ctx["form"]}
				if node.has("event"):
					entry["event"] = node["event"]
				_item(entry)
			return 1
		"input":
			return _input(node, x, y, w, ctx)
		"checkbox", "switch":
			var checked := _field_checked(key, node)
			var mark := ("[x] " if checked else "[ ] ") if kind == "checkbox" else ("[ON ] " if checked else "[OFF] ")
			var label := str(prop(node, "label", ""))
			var used := put(x, y, mark + label, "", w)
			_add_field({"kind": kind, "x": x, "y": y, "w": used, "h": 1, "key": key, "label": label,
						"bind": str(prop(node, "bind", "")), "checked": checked, "card": ctx["card"],
						"form": ctx["form"]})
			return 1
		"radio":
			var chosen := _field_value(key, node)
			var at := x
			var row := y
			for o in _options(node):
				var text: String = ("(•) " if o[1] == chosen else "( ) ") + o[0]
				if at > x and at + text_width(text) > x + w:
					at = x
					row += 1
				var used := put(at, row, text)
				_add_field({"kind": "radio", "x": at, "y": row, "w": used, "h": 1, "key": key, "label": o[0],
							"value": o[1], "bind": str(prop(node, "bind", "")), "checked": o[1] == chosen,
							"card": ctx["card"], "form": ctx["form"]})
				at += used + 2
			return row - y + 1
		"select":
			var options := _options(node)
			var value := _field_value(key, node)
			var values: Array = []
			for o in options:
				values.append(o[1])
			if not (value in values) and values.size() > 0:
				value = values[0]
			var shown := value
			for o in options:
				if o[1] == value:
					shown = o[0]
			var width: int = min(w, max(natural(node), text_width(shown) + 4))
			fill(x, y, width, "field")
			put(x + 1, y, cut(shown, width - 4), "field")
			put(x + width - 2, y, "▾", "field")
			_add_field({"kind": "select", "x": x, "y": y, "w": width, "h": 1, "key": key, "label": shown,
						"value": value, "options": options, "bind": str(prop(node, "bind", "")),
						"card": ctx["card"], "form": ctx["form"]})
			return 1
		_:
			# UI-7: outside what the TUI draws, it says so; never something else in its place
			if not (kind in unsupported):
				unsupported.append(kind)
			put(x, y, cut("[ui:%s is not drawn in the TUI]" % kind, w), "unsupported")
			return 1


func _add_field(entry: Dictionary) -> void:
	var i := _item(entry)
	if int(entry.get("form", -1)) >= 0:
		forms[int(entry["form"])]["items"].append(i)


func _input(node: Dictionary, x: int, y: int, w: int, ctx: Dictionary) -> int:
	var key: String = ctx["key"]
	var used := 0
	var label := str(prop(node, "label", ""))
	if label != "":
		put(x, y, cut(label, w), "muted")
		used = 1
	var input_type := str(prop(node, "input_type", "text"))
	var bind := str(prop(node, "bind", ""))
	var invalid := str(prop(node, "error", "")) != ""
	var style := "field_error" if invalid else "field"
	if input_type == "file":
		# UI-14: the TUI's own dialog picks the file; the form sends it as a browser would
		var chosen := str(state.get(key, {}).get("file", ""))
		var text := "[ Choose a file… ]" + ("  " + chosen.get_file() if chosen != "" else "  no file chosen")
		var n := put(x, y + used, cut(text, w), "button")
		_add_field({"kind": "file", "x": x, "y": y + used, "w": min(n, 18), "h": 1, "key": key, "label": bind,
					"bind": bind, "value": chosen, "accept": str(prop(node, "accept", "")), "card": ctx["card"],
					"form": ctx["form"]})
		return used + 1
	var value := _field_value(key, node)
	var rows := num(node, "rows", 0)
	var width: int = w
	if has_num(node, "width"):
		width = min(w, max(8, num(node, "width") / 8))
	var shown := "•".repeat(value.length()) if input_type == "password" else value
	if rows > 0:
		var lines := wrap_text(shown, width - 2)
		var h: int = max(rows, lines.size())
		for r in h:
			fill(x, y + used + r, width, style)
			if r < lines.size():
				put(x + 1, y + used + r, lines[r], style, width - 2)
		_add_field({"kind": "textarea", "x": x, "y": y + used, "w": width, "h": h, "key": key, "label": label,
					"bind": bind, "value": value, "card": ctx["card"], "form": ctx["form"]})
		return used + h
	fill(x, y + used, width, style)
	if shown == "" and str(prop(node, "placeholder", "")) != "":
		put(x + 1, y + used, cut(str(prop(node, "placeholder", "")), width - 2), "placeholder")
	else:
		# the end of what was typed shows when it is longer than the field
		var room := width - 2
		var tail := shown
		while text_width(tail) > room:
			tail = tail.substr(1)
		put(x + 1, y + used, tail, style)
	var entry := {"kind": "input", "x": x, "y": y + used, "w": width, "h": 1, "key": key, "label": label,
				  "bind": bind, "value": value, "input_type": input_type, "card": ctx["card"], "form": ctx["form"]}
	if truthy(prop(node, "search", false)):
		entry["search"] = num(node, "delay", 300)
	_add_field(entry)
	return used + 1


func _hbox(node: Dictionary, x: int, y: int, w: int, ctx: Dictionary) -> int:
	var children: Array = []
	for c in node.get("children", []):
		if c is Dictionary:
			children.append(c)
	if children.is_empty():
		return 0
	var stack_below := str(prop(node, "stack_below", ""))
	if stack_below != "" and cols < int(BREAKPOINTS.get(stack_below, 0)):
		return stack(node.get("children", []), x, y, w, ctx, max(1, gap_rows(node)) if gap_rows(node) > 0 else 0)
	var gap := 2 if gap_rows(node) > 0 else 1
	var n := children.size()
	var widths: Array = []
	var flexible: Array = []
	var taken := gap * (n - 1)
	for i in n:
		var c: Dictionary = children[i]
		if has_num(c, "width"):
			widths.append(max(4, num(c, "width") / 8))
			taken += widths[i]
		else:
			widths.append(0)
			flexible.append(i)
	var left: int = w - taken
	if not flexible.is_empty():
		var growers: Array = []
		for i in flexible:
			if truthy(prop(children[i], "grow", false)):
				growers.append(i)
		if growers.is_empty():
			# nothing grows: each its natural width, the rest left over; too little room, equal shares
			var wanted := 0
			for i in flexible:
				wanted += natural(children[i])
			if wanted <= left:
				for i in flexible:
					widths[i] = natural(children[i])
			else:
				# too little room: each asks for its natural width; who asks for less than an equal share gets
				# it, and the room left is shared again among the rest (water-filling)
				var waiting: Array = flexible.duplicate()
				var room := left
				var settled := true
				while settled and not waiting.is_empty():
					settled = false
					var share: int = room / waiting.size()
					for i in waiting.duplicate():
						if natural(children[i]) <= share:
							widths[i] = natural(children[i])
							room -= widths[i]
							waiting.erase(i)
							settled = true
				for k in waiting.size():
					widths[waiting[k]] = room / waiting.size() + (1 if k < room % waiting.size() else 0)
		else:
			var rest := left
			for i in flexible:
				if not (i in growers):
					widths[i] = min(natural(children[i]), max(4, left / flexible.size()))
					rest -= widths[i]
			for k in growers.size():
				widths[growers[k]] = rest / growers.size() + (1 if k < rest % growers.size() else 0)
	var too_narrow := false
	for i in n:
		if int(widths[i]) < 3:
			too_narrow = true
	if too_narrow:
		return stack(node.get("children", []), x, y, w, ctx, 0)
	var at := x
	var tallest := 0
	var index := 0
	for i in node.get("children", []).size():
		var c = node.get("children", [])[i]
		if not (c is Dictionary):
			continue
		var inner := ctx.duplicate()
		inner["key"] = "%s/%d" % [ctx["key"], i]
		tallest = max(tallest, place(c, at, y, int(widths[index]), inner))
		at += int(widths[index]) + gap
		index += 1
	return tallest


func _grid(node: Dictionary, x: int, y: int, w: int, ctx: Dictionary) -> int:
	# UI-2: columns="1 sm:2 lg:3" counted in the TUI's columns; "1fr 2fr" is two.
	var spec := str(prop(node, "columns", "1")).split(" ", false)
	var count := 1
	var all_fr := spec.size() > 1
	for part in spec:
		if not part.ends_with("fr"):
			all_fr = false
	if all_fr:
		count = spec.size()
	else:
		for part in spec:
			var band := ""
			var value := part
			if ":" in part:
				band = part.get_slice(":", 0)
				value = part.get_slice(":", 1)
			if value.is_valid_int() and (band == "" or cols >= int(BREAKPOINTS.get(band, 1000000))):
				count = int(value)
	count = max(1, count)
	var children: Array = node.get("children", [])
	var cell_w: int = max(4, (w - (count - 1) * 2) / count)
	var used := 0
	var column := 0
	var row_h := 0
	for i in children.size():
		var c = children[i]
		if not (c is Dictionary):
			continue
		var inner := ctx.duplicate()
		inner["key"] = "%s/%d" % [ctx["key"], i]
		row_h = max(row_h, place(c, x + column * (cell_w + 2), y + used, cell_w, inner))
		column += 1
		if column == count:
			used += row_h
			row_h = 0
			column = 0
	return used + row_h


func _tabpanel(node: Dictionary, x: int, y: int, w: int, ctx: Dictionary) -> int:
	var key: String = ctx["key"]
	var panes: Array = []
	var titles: Array = []
	for c in node.get("children", []):
		if c is Dictionary and c.get("type", "") == "tab":
			panes.append(c)
			var title := str(prop(c, "title", ""))
			titles.append(title if title != "" else str(panes.size()))
	if panes.is_empty():
		return 0
	# UI-17: the tab `open` names opens; else the first; then the one the user chose
	var wanted := str(prop(node, "open", "")).strip_edges()
	var opened: int = titles.find(wanted) if wanted in titles else 0
	if tabs.has(key) and str(tabs[key]) in titles:
		opened = titles.find(str(tabs[key]))
	var at := x
	for i in titles.size():
		var text: String = " " + titles[i] + " "
		var style := "tab_open" if i == opened else "tab"
		var used := put(at, y, text, style, x + w - at)
		_item({"kind": "tab", "x": at, "y": y, "w": used, "h": 1, "key": key, "label": titles[i],
			   "open": i == opened, "card": ctx["card"]})
		at += used + 1
	put(x, y + 1, "─".repeat(w), "border")
	var inner := ctx.duplicate()
	inner["key"] = "%s/tab:%s" % [key, titles[opened]]
	var body := stack(panes[opened].get("children", []), x, y + 2, w, inner, 0)
	tab_regions.append({"what": "tab:" + titles[opened], "x": x, "y": y + 2, "w": w, "h": body})
	return 2 + body


func _table(node: Dictionary, x: int, y: int, w: int, ctx: Dictionary) -> int:
	# UI-5: a header and a row a record; a cell holds text or elements. UI-13: a sortable header is a link.
	var columns: Array = node.get("columns", [])
	var rows: Array = node.get("rows", [])
	var n := columns.size()
	if n == 0:
		return 0
	var sep := 3
	var widths: Array = []
	var free := w - sep * (n - 1)
	var flexible := 0
	for c in columns:
		var fixed := str(c.get("width", "")) if c.get("width", null) != null else ""
		if fixed.is_valid_float():
			widths.append(max(3, int(fixed.to_float()) / 8))
			free -= widths[-1]
		else:
			widths.append(-1)
			flexible += 1
	# a flexible column is as wide as its widest content, the room left shared among them
	var wanted: Array = []
	for i in n:
		var widest := text_width(str(columns[i].get("label", "")))
		for row in rows:
			if i < row.size():
				for item in row[i]:
					if item is Dictionary:
						widest = max(widest, natural(item))
		wanted.append(widest)
	var flex_total := 0
	for i in n:
		if int(widths[i]) < 0:
			flex_total += int(wanted[i])
	for i in n:
		if int(widths[i]) < 0:
			if flex_total <= free:
				widths[i] = int(wanted[i]) + (free - flex_total) / max(1, flexible)
			else:
				widths[i] = max(3, free / max(1, flexible))
	var lefts: Array = []
	var at := x
	for i in n:
		lefts.append(at)
		at += int(widths[i]) + sep
	# the header
	for i in n:
		var c: Dictionary = columns[i]
		var label := str(c.get("label", ""))
		if c.get("to", null) != null and str(c.get("to", "")) != "":
			var used := put(lefts[i], y, cut(label, widths[i]), "link")
			_item({"kind": "link", "x": lefts[i], "y": y, "w": used, "h": 1, "key": "%s/h%d" % [ctx["key"], i],
				   "label": label, "to": str(c["to"]), "card": ctx["card"], "form": -1})
		else:
			_aligned(lefts[i], y, widths[i], label, "bold", str(c.get("align", "")))
		if i < n - 1:
			put(lefts[i] + int(widths[i]) + 1, y, "│", "border")
	var rule := ""
	for i in n:
		rule += "─".repeat(int(widths[i]) + (1 if i > 0 else 0)) + ("─┼" if i < n - 1 else "")
	put(x, y + 1, cut(rule, w), "border")
	var used_rows := 2
	for r in rows.size():
		var row: Array = rows[r]
		var tallest := 1
		for i in min(n, row.size()):
			var cell_nodes: Array = row[i]
			var inner := ctx.duplicate()
			inner["key"] = "%s/r%d/c%d" % [ctx["key"], r, i]
			var align := str(columns[i].get("align", "")) if columns[i].get("align", null) != null else ""
			if cell_nodes.size() == 1 and cell_nodes[0] is Dictionary and cell_nodes[0].get("type", "") == "text" \
					and align == "right":
				_aligned(lefts[i], y + used_rows, widths[i], str(prop(cell_nodes[0], "text", "")), "", "right")
				tallest = max(tallest, 1)
			else:
				tallest = max(tallest, stack(cell_nodes, lefts[i], y + used_rows, int(widths[i]), inner, 0))
		for i in n - 1:
			for k in tallest:
				put(lefts[i] + int(widths[i]) + 1, y + used_rows + k, "│", "border")
		used_rows += tallest
	return used_rows


func _aligned(x: int, y: int, w: int, text: String, style: String, align: String) -> void:
	var shown := cut(text, w)
	if align == "right":
		put(x + w - text_width(shown), y, shown, style)
	elif align == "center":
		put(x + (w - text_width(shown)) / 2, y, shown, style)
	else:
		put(x, y, shown, style)
