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
# UI-21: what a tag with a state of its own holds now, by key, kept across layouts: {open} a fold or a
# dropdown, {closed} a modal, {gone} a toast, {at} the slide or the step shown, {done} a stepper's steps done,
# {month} the month a calendar shows (YYYY-MM)
var held: Dictionary
var motion_on := true
var focus_key := ""           # the key of the item with the focus: a tooltip's tip shows while it is inside it
var pointer := Vector2i(-1, -1)   # the cell under the mouse: a tooltip's tip shows while it is over its element
var view_top := 0             # the first row on the screen, and how many it shows: a modal and a toast stay
var view_rows := 40           # on the screen as the page scrolls under them
var streams: Dictionary       # IA-7: a stream's text so far, by its url
var textures: Dictionary      # an image's size in cells once it has loaded, by its src

# UI-21: what is drawn over the page, once it is laid out
var overlays: Array = []      # what asked to be drawn over it, as it was met: {kind, node, key, ctx, ...}
var layers: Array = []        # the boxes drawn over it, bottom first: {kind, key, x, y, w, h, closable}
var follows_view := false     # a layer stays on the screen: laid out again when the page scrolls
var toasts: Array = []        # {key, ms}: the toasts shown, each gone after its duration (tui.gd)
var tips: Array = []          # {key, x, y, w, h, shown}: the elements of the tooltips
var autoplay: Array = []      # {key, ms, next, x, y, w, h}: the carousels that move on by themselves


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


static func kind_of(node: Dictionary) -> String:
	# UI-21: a tag beyond the layout set that is a composition of it says which kind it is drawn as
	return str(node.get("as", node.get("type", "")))


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
	overlays = []
	layers = []
	follows_view = false
	toasts = []
	tips = []
	autoplay = []
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
	_layers()
	for layer in layers:
		height = max(height, int(layer["y"]) + int(layer["h"]))
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
	var kind := kind_of(node)
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
		"progress", "skeleton":
			return 24
		"chart":
			return 40
		"avatar":
			return text_width(str(prop(node, "initials", "?"))) + 4
		"loading":
			return text_width(str(prop(node, "text", ""))) + 2
		"treeitem":
			return text_width(tree_guides(node)) + text_width(label_of(node))
		"modal", "toast":
			return 0                       # drawn over the page, they take no room in it (UI-21)
		"dropdown":
			return text_width(_dropdown_label(node)) + 6
		"calendar":
			return CALENDAR_WIDTH + (3 if truthy(prop(node, "week_numbers", false)) else 0)
		"accordion":
			var widest := 0
			for c in children:
				if c is Dictionary:
					widest = max(widest, max(text_width(str(prop(c, "title", ""))), natural(c)) + 2)
			return widest
		"carousel":
			var widest := 4 * children.size() + 6
			for c in children:
				if c is Dictionary:
					widest = max(widest, natural(c))
			return widest
		"stepper":
			var row := 0
			var body := 16
			for c in children:
				if c is Dictionary:
					row += text_width(str(prop(c, "title", ""))) + 8
					body = max(body, natural(c))
			return max(row, body)
		"rule":
			return 1 if truthy(prop(node, "vertical", false)) else 4
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
	if error != "" and kind_of(node) in ["input", "select", "checkbox", "switch", "radio"]:
		for line in wrap_text(error, w):
			put(x, y + h, line, "error", w)
			h += 1
	return h


func _place(node: Dictionary, x: int, y: int, w: int, ctx: Dictionary) -> int:
	var kind := kind_of(node)
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
			var marker := str(prop(node, "marker", "•"))
			put(x, y, marker, "muted")
			return max(1, stack(children, x + text_width(marker) + 1, y, w - text_width(marker) - 1, ctx, 0))
		"text", "footer":
			return _text(node, kind, x, y, w)
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
			if truthy(prop(node, "vertical", false)):
				put(x, y, "│", "border")      # the hbox draws it down to its tallest child
				return 1
			put(x, y, "─".repeat(w), "border")
			return 1
		"avatar", "chart", "skeleton", "loading", "treeitem":
			return _more(node, kind, x, y, w, ctx)
		"accordion", "modal", "toast", "tooltip", "dropdown", "carousel", "stepper", "calendar":
			return _stateful(node, kind, x, y, w, ctx)
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
			var entry := {"kind": "link", "x": x, "y": y, "w": min(w, text_width(label)), "h": lines.size(), "key": key,
						  "label": label, "to": str(prop(node, "to", "/")), "card": ctx["card"], "form": ctx["form"]}
			if node.has("event"):
				entry["event"] = node["event"]      # UI-21: a link that posts an action (a menu's option)
			_item(entry)
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
		# narrower than it can be drawn in (a separator ">" needs one cell, a field more)
		if int(widths[i]) < min(3, natural(children[i])):
			too_narrow = true
	if too_narrow:
		return stack(node.get("children", []), x, y, w, ctx, 0)
	var at := x
	var tallest := 0
	var index := 0
	var dividers: Array = []
	for i in node.get("children", []).size():
		var c = node.get("children", [])[i]
		if not (c is Dictionary):
			continue
		var inner := ctx.duplicate()
		inner["key"] = "%s/%d" % [ctx["key"], i]
		tallest = max(tallest, place(c, at, y, int(widths[index]), inner))
		if kind_of(c) == "rule" and truthy(prop(c, "vertical", false)):
			dividers.append(at)
		at += int(widths[index]) + gap
		index += 1
	for column in dividers:                   # UI-21: a dividedbox's divider, as tall as its panes
		for r in range(y, y + tallest):
			put(column, r, "│", "border", 1)
	return tallest


# -- the tags beyond the layout set (UI-21) -------------------------------------

static func tree_guides(node: Dictionary) -> String:
	# the lines before a tree's row: one for each level that goes on, then its branch (ui_more.tree_guides)
	var depth := num(node, "depth")
	if depth == 0:
		return ""
	var out := ""
	for on in prop(node, "lines", []):
		out += "│  " if truthy(on) else "   "
	return out + ("└─ " if truthy(prop(node, "last", false)) else "├─ ")


func _text(node: Dictionary, kind: String, x: int, y: int, w: int) -> int:
	# a text, with its look (bold, a heading, code, a quote, muted) and its spans
	var style := "muted" if kind == "footer" or truthy(prop(node, "muted", false)) else ""
	if str(prop(node, "weight", "")) == "bold" or has_num(node, "heading"):
		style = "bold"
	if truthy(prop(node, "code", false)):
		var used := 0
		for line in str(prop(node, "text", "")).split("\n"):
			fill(x, y + used, w, "code")
			put(x + 1, y + used, cut(line, w - 2), "code")
			used += 1
		return used
	var quote := truthy(prop(node, "quote", false))
	var left := x + (2 if quote else 0)
	var room := w - (2 if quote else 0)
	var spans: Array = prop(node, "spans", [])
	var used := 0
	if spans.is_empty():
		for line in wrap_text(str(prop(node, "text", "")), room):
			put(left, y + used, line, "muted" if quote else style)
			used += 1
	else:
		used = _spans(spans, left, y, room, style)
	if quote:
		for r in max(1, used):
			put(x, y + r, "│", "border")
	return max(1, used)


func _spans(spans: Array, x: int, y: int, w: int, base: String) -> int:
	# words of each span, wrapped together, each in its span's style; a link's target after it (a terminal
	# shows where it goes)
	var words: Array = []
	var space_before := false
	for span in spans:
		var style := base
		if truthy(span.get("code", false)):
			style = "code"
		elif span.has("to"):
			style = "link"
		elif truthy(span.get("bold", false)):
			style = "bold"
		elif truthy(span.get("italic", false)):
			style = "accent"
		var text := str(span.get("text", ""))
		var pieces := text.split(" ")
		for i in pieces.size():
			if pieces[i] != "":
				words.append([pieces[i], style, space_before or i > 0])
				space_before = false
			elif i > 0 or text == "":
				space_before = true            # "Some " and then "bold": a space between them
			else:
				space_before = true
		if text.ends_with(" "):
			space_before = true
		if span.has("to"):
			words.append(["(" + str(span["to"]) + ")", "muted", true])
	var row := 0
	var at := 0
	for word in words:
		var piece: String = word[0]
		if piece == "":
			continue
		var need := text_width(piece) + (1 if word[2] and at > 0 else 0)
		if at > 0 and at + need > w:
			row += 1
			at = 0
			need = text_width(piece)
		if word[2] and at > 0:
			at += 1
		at += put(x + at, y + row, cut(piece, w - at), word[1])
	return row + 1


func _more(node: Dictionary, kind: String, x: int, y: int, w: int, ctx: Dictionary) -> int:
	match kind:
		"avatar":
			var used := put(x, y, "(" + str(prop(node, "initials", "?")) + ")", "bold")
			var status := str(prop(node, "status", ""))
			var mark := {"online": ["●", "fill:success"], "away": ["◐", "fill:warning"],
						 "busy": ["●", "fill:danger"], "offline": ["○", "muted"]}
			if mark.has(status):
				put(x + used + 1, y, mark[status][0], mark[status][1])
			return 1
		"chart":
			var used := 0
			var title := str(prop(node, "title", ""))
			if title != "":
				put(x, y, cut(title, w), "bold")
				used = 1
			var bars: Array = node.get("bars", [])
			var share := str(prop(node, "chart_type", "bar")) in ["pie", "doughnut"]
			var names := 0
			var values := 0
			for bar in bars:
				names = max(names, text_width(str(bar["label"])))
				values = max(values, text_width(_shown(bar, share)))
			var room: int = max(4, w - names - values - 2)
			for bar in bars:
				put(x, y + used, cut(str(bar["label"]), names))
				var percent := float(bar["percent"])
				var length: int = max(1 if percent > 0 else 0, int(round(room * percent / 100.0)))
				put(x + names + 1, y + used, "█".repeat(length), "fill:" + str(bar["color"]))
				put(x + names + 2 + length, y + used, _shown(bar, share), "muted")
				used += 1
			return max(1, used)
		"skeleton":
			var variant := str(prop(node, "variant", "text"))
			if variant == "circle":
				put(x, y, "(░░)", "muted")
				return 1
			var lines := num(node, "lines", 1) if variant == "text" else 3
			for r in lines:
				var length: int = w if r < lines - 1 or lines == 1 else max(1, w * 3 / 5)
				put(x, y + r, "░".repeat(length), "muted")
			return lines
		"loading":
			put(x, y, "⠋", "spinner")     # it turns as it is drawn (tui.gd)
			put(x + 2, y, cut(str(prop(node, "text", "Loading")), w - 2), "muted")
			return 1
		"treeitem":
			var guides := tree_guides(node)
			var at := put(x, y, guides, "border")
			var label := label_of(node)
			if node.has("event") or str(prop(node, "to", "")) != "":
				put(x + at, y, cut(label, w - at), "link")
				var entry := {"kind": "link", "x": x + at, "y": y, "w": min(w - at, text_width(label)), "h": 1,
							  "key": ctx["key"], "label": label, "to": str(prop(node, "to", "/")),
							  "card": ctx["card"], "form": ctx["form"]}
				if node.has("event"):
					entry["event"] = node["event"]
				_item(entry)
			else:
				put(x + at, y, cut(label, w - at))
			return 1
	return 1


static func _shown(bar: Dictionary, share: bool) -> String:
	if share:
		var percent := float(bar["percent"])
		return ("%d%%" % int(percent)) if percent == floor(percent) else ("%.1f%%" % percent)
	return str(bar["shown"])


# -- the tags with a state of their own (UI-21) ---------------------------------
#
# What the user changes of them is kept in `held`, by key: tui.gd changes it when one of their items is
# activated (it carries what it changes to), and on the clock (a toast's duration, a carousel's interval).
# A modal, a toast, a tooltip's tip and an open dropdown's options take no room in the page: they are
# drawn over it once it is laid out (`_layers`).

const TOAST_ICONS := {"info": "i", "success": "✓", "warning": "⚠", "danger": "✗"}
const MODAL_WIDTHS := {"sm": 38, "md": 62, "lg": 100, "xl": 137}
const MONTH_NAMES := ["January", "February", "March", "April", "May", "June", "July", "August", "September",
					  "October", "November", "December"]
const DAY_NAMES := ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]
const CALENDAR_WIDTH := 24        # a calendar's box: seven columns of three cells, its border and margins
const NO_DAY := -100000000        # what day_of says of a text that is not a date


func _held(key: String, field: String, fallback: Variant) -> Variant:
	var kept: Dictionary = held.get(key, {})
	return kept.get(field, fallback)


static func _dropdown_label(node: Dictionary) -> String:
	var label := str(prop(node, "label", ""))
	return label if label != "" else "Menu"


static func _reacting(it: Dictionary) -> bool:
	return str(it.get("kind", "")) != "stream" and bool(it.get("react", true))


func _stateful(node: Dictionary, kind: String, x: int, y: int, w: int, ctx: Dictionary) -> int:
	var key: String = ctx["key"]
	match kind:
		"accordion":
			return _accordion(node, x, y, w, ctx)
		"modal":
			# open as the page is drawn (`open`), until it is closed
			if truthy(prop(node, "open", false)) and not bool(_held(key, "closed", false)):
				overlays.append({"kind": "modal", "node": node, "key": key, "ctx": ctx.duplicate()})
			return 0
		"toast":
			if not bool(_held(key, "gone", false)):
				overlays.append({"kind": "toast", "node": node, "key": key, "ctx": ctx.duplicate()})
			return 0
		"tooltip":
			return _tooltip(node, x, y, w, ctx)
		"dropdown":
			# a button with its label; open, its options under it, each posting its action
			var label := _dropdown_label(node)
			var open := bool(_held(key, "open", false))
			var used := put(x, y, cut("[ " + label + (" ▴ ]" if open else " ▾ ]"), w), "button")
			_item({"kind": "dropdown", "x": x, "y": y, "w": used, "h": 1, "key": key, "label": label, "open": open,
				   "card": ctx["card"]})
			if open:
				overlays.append({"kind": "menu", "node": node, "key": key, "ctx": ctx.duplicate(), "label": label,
								 "x": x, "y": y, "w": used})
			return 1
		"carousel":
			return _carousel(node, x, y, w, ctx)
		"stepper":
			return _stepper(node, x, y, w, ctx)
		"calendar":
			return _calendar(node, x, y, w, ctx)
	return 0


func _accordion(node: Dictionary, x: int, y: int, w: int, ctx: Dictionary) -> int:
	# each section a fold, its title a header that opens and closes it by itself; the first open
	var children: Array = node.get("children", [])
	var used := 0
	var first := true
	for i in children.size():
		var c = children[i]
		if not (c is Dictionary):
			continue
		var inner := ctx.duplicate()
		inner["key"] = "%s/%d" % [ctx["key"], i]
		if str(c.get("type", "")) != "section":
			used += place(c, x, y + used, w, inner)
			continue
		var open := bool(_held(inner["key"], "open", first))
		first = false
		var title := str(prop(c, "title", ""))
		var n := put(x, y + used, cut(("▾ " if open else "▸ ") + title, w), "bold")
		_item({"kind": "fold", "x": x, "y": y + used, "w": n, "h": 1, "key": inner["key"], "label": title,
			   "open": open, "card": ctx["card"]})
		used += 1
		if open:
			used += stack(c.get("children", []), x + 2, y + used, w - 2, inner, gap_rows(c))
	return used


func _tooltip(node: Dictionary, x: int, y: int, w: int, ctx: Dictionary) -> int:
	# its element is drawn; the tip shows next to it while the mouse is over it or the focus is in it
	var key: String = ctx["key"]
	var first := items.size()
	var h := stack(node.get("children", []), x, y, w, ctx, 0)
	if h == 0:
		return 0
	var drawn: int = max(1, _drawn_width(x, y, w, h))
	var reacts := false
	for i in range(first, items.size()):
		if _reacting(items[i]):
			reacts = true
	if not reacts:
		# an element that does not react takes the focus for its tip
		_item({"kind": "tooltip", "x": x, "y": y, "w": drawn, "h": h, "key": key, "label": _grid_text(x, y, drawn, h),
			   "card": ctx["card"]})
	var tip := {"key": key, "x": x, "y": y, "w": drawn, "h": h}
	tip["shown"] = _tip_wanted(tip)
	tips.append(tip)
	var text := str(prop(node, "text", ""))
	if bool(tip["shown"]) and text != "":
		overlays.append({"kind": "tip", "key": key, "text": text, "position": str(prop(node, "position", "top")),
						 "x": x, "y": y, "w": drawn, "h": h})
	return h


func _tip_wanted(tip: Dictionary) -> bool:
	var key: String = tip["key"]
	if focus_key != "" and (focus_key == key or focus_key.begins_with(key + "/")):
		return true
	return pointer.x >= int(tip["x"]) and pointer.x < int(tip["x"]) + int(tip["w"]) \
		and pointer.y >= int(tip["y"]) and pointer.y < int(tip["y"]) + int(tip["h"])


func tips_changed() -> bool:
	# whether a tooltip's tip is to show or go now that the mouse or the focus moved (tui.gd lays out again)
	for tip in tips:
		if _tip_wanted(tip) != bool(tip["shown"]):
			return true
	return false


func _mover(kind: String, x: int, y: int, text: String, label: String, key: String, goto: int, ctx: Dictionary,
		style: String = "button", done: Array = []) -> int:
	# a control that moves a carousel or a stepper to `goto`; drawn dim when it cannot (-1)
	if goto < 0:
		return put(x, y, text, "button_disabled")
	var used := put(x, y, text, style)
	_item({"kind": kind, "x": x, "y": y, "w": used, "h": 1, "key": key, "label": label, "goto": goto, "done": done,
		   "card": ctx["card"]})
	return used


func _carousel(node: Dictionary, x: int, y: int, w: int, ctx: Dictionary) -> int:
	# one slide at a time (`current`), the arrows to the one before and after (around when `loop`), a dot a slide
	var key: String = ctx["key"]
	var children: Array = node.get("children", [])
	var slides: Array = []                 # the slides' places among the children
	for i in children.size():
		if children[i] is Dictionary and str(children[i].get("type", "")) == "slide":
			slides.append(i)
	if slides.is_empty():                  # without ui:slide, each child is a slide
		for i in children.size():
			if children[i] is Dictionary:
				slides.append(i)
	var total := slides.size()
	if total == 0:
		return 0
	var at: int = clamp(int(_held(key, "at", num(node, "current", 0))), 0, total - 1)
	var loop := truthy(prop(node, "loop", true))
	var inner := ctx.duplicate()
	inner["key"] = "%s/%d" % [key, slides[at]]
	var used := place(children[slides[at]], x, y, w, inner)
	var arrows := truthy(prop(node, "show_arrows", true))
	var dots := truthy(prop(node, "show_indicators", true))
	if total > 1 and (arrows or dots):
		var row := y + used
		var at_x := x
		var before: int = (at - 1 + total) % total if loop else at - 1
		var after: int = (at + 1) % total if loop else (at + 1 if at + 1 < total else -1)
		if arrows:
			at_x += _mover("carousel", at_x, row, " ‹ ", "Previous slide", key, before, ctx) + 1
		if dots:
			for k in total:
				if k == at:
					put(at_x, row, "●", "accent")
				else:
					put(at_x, row, "○", "muted")
					_item({"kind": "carousel", "x": at_x, "y": row, "w": 1, "h": 1, "key": key,
						   "label": "Go to slide %d" % (k + 1), "goto": k, "card": ctx["card"]})
				at_x += 2
		else:
			at_x += put(at_x, row, "%d/%d" % [at + 1, total], "muted") + 1
		if arrows:
			_mover("carousel", at_x, row, " › ", "Next slide", key, after, ctx)
		used += 1
	if truthy(prop(node, "auto_play", false)) and total > 1:
		var next: int = (at + 1) % total if loop else at + 1
		if next < total:
			autoplay.append({"key": key, "ms": max(500, num(node, "interval", 5000)), "next": next,
							 "x": x, "y": y, "w": w, "h": used})
	return used


func _stepper(node: Dictionary, x: int, y: int, w: int, ctx: Dictionary) -> int:
	# the steps' titles in a row (one under the other when vertical), the current one marked, a step done
	# ticked; only the current step's content; Back and Next. Done, as the browser counts it: what the step
	# says (`completed`), else a step before the current one (ui_html_adapter.completed_step_indices).
	var key: String = ctx["key"]
	var children: Array = node.get("children", [])
	var steps: Array = []                  # the steps' places among the children
	for i in children.size():
		if children[i] is Dictionary and str(children[i].get("type", "")) == "step":
			steps.append(i)
	var total := steps.size()
	if total == 0:
		return 0
	var first: int = clamp(num(node, "current", 0), 0, total - 1)
	var at: int = clamp(int(_held(key, "at", first)), 0, total - 1)
	var done: Array = []
	var kept: Dictionary = held.get(key, {})
	if kept.has("done"):
		done = kept["done"]
	else:
		for k in total:
			var said = prop(children[steps[k]], "completed", null)
			if (truthy(said) if said != null else k < first):
				done.append(k)
	var linear := truthy(prop(node, "linear", true))
	var clickable := truthy(prop(node, "clickable", false))
	var vertical := str(prop(node, "orientation", "horizontal")) == "vertical"
	var notes := false
	for k in total:
		if _step_note(children[steps[k]]) != "":
			notes = true
	var row := y
	var at_x := x
	for k in total:
		var step: Dictionary = children[steps[k]]
		var title := str(prop(step, "title", ""))
		if title == "":
			title = "Step %d" % (k + 1)
		var error := str(prop(step, "error", "")) != ""
		var mark := "!" if error else ("✓" if k in done and k != at else str(k + 1))
		var mark_style := "tab_open" if k == at else ("flash_error" if error else ("flash" if k in done else "tab"))
		var title_style := "bold" if k == at else ("error" if error else ("" if k in done else "muted"))
		var note := _step_note(step)
		var seg: int = min(w, 4 + max(text_width(title), text_width(note)))
		if vertical:
			at_x = x
		elif k > 0:
			if at_x + 4 + seg > x + w:
				row += 2 if notes else 1
				at_x = x
			else:
				at_x += put(at_x, row, " ── ", "border")
		var start := at_x
		put(start, row, " " + mark + " ", mark_style)
		var used := put(start + 4, row, cut(title, x + w - start - 4), title_style)
		if clickable and k != at and (not linear or k < at or (k == at + 1 and at in done)):
			_item({"kind": "step", "x": start, "y": row, "w": 4 + used, "h": 1, "key": key, "label": title, "goto": k,
				   "done": done, "card": ctx["card"]})
		if note != "":
			put(start + 4, row + 1, cut(note, seg - 4), "error" if error else "muted")
		at_x = start + seg
		if vertical:
			row += 2 if note != "" else 1
			if k == at:
				var inner := ctx.duplicate()
				inner["key"] = "%s/%d" % [key, steps[k]]
				row += stack(step.get("children", []), x + 4, row, w - 4, inner, gap_rows(step))
	var used_rows := row - y
	if not vertical:
		used_rows += 2 if notes else 1
		var inner := ctx.duplicate()
		inner["key"] = "%s/%d" % [key, steps[at]]
		var step: Dictionary = children[steps[at]]
		used_rows += stack(step.get("children", []), x, y + used_rows, w, inner, gap_rows(step))
	# Next marks the step done and goes to the one after it
	var after := done.duplicate()
	if not (at in after):
		after.append(at)
	var nav_x := x + _mover("stepper", x, y + used_rows, "[ Back ]", "Back", key, at - 1, ctx, "button", done) + 2
	_mover("stepper", nav_x, y + used_rows, "[ Next ]", "Next", key, at + 1 if at + 1 < total else -1, ctx,
		   "button_primary", after)
	return used_rows + 1


static func _step_note(step: Dictionary) -> String:
	# what is said under a step's title: its error, its description, or that it is optional
	var error := str(prop(step, "error", ""))
	if error != "":
		return error
	var description := str(prop(step, "description", ""))
	if description != "":
		return description
	return "Optional" if truthy(prop(step, "optional", false)) else ""


# -- a calendar: a date field shown as a month (UI-21) ---------------------------------
#
# The view sends its meaning (ui_more.calendar_of): its field (`bind`), its value, the month shown first, `min`
# and `max`, the dates and the weekdays that cannot be picked (0 = Sunday), the first day of the week and
# whether the weeks' numbers show. A date is counted here as its day from 1970-01-01.

static func days_from(year: int, month: int, day: int) -> int:
	var t := Time.get_unix_time_from_datetime_dict({"year": year, "month": month, "day": day, "hour": 0,
													"minute": 0, "second": 0})
	return floori(t / 86400.0)


static func days_in(year: int, month: int) -> int:
	return days_from(year + 1 if month == 12 else year, 1 if month == 12 else month + 1, 1) - days_from(year, month, 1)


static func day_of(date: String) -> int:
	# a date (YYYY-MM-DD) as its day from 1970-01-01; NO_DAY when it is not one
	var parts := date.split("-")
	if parts.size() != 3 or not (parts[0].is_valid_int() and parts[1].is_valid_int() and parts[2].is_valid_int()):
		return NO_DAY
	var year := parts[0].to_int()
	var month := parts[1].to_int()
	var day := parts[2].to_int()
	if month < 1 or month > 12 or day < 1 or day > days_in(year, month):
		return NO_DAY
	return days_from(year, month, day)


static func date_of(day: int) -> String:
	return Time.get_date_string_from_unix_time(day * 86400)


static func weekday_of(day: int) -> int:
	# 0 = Sunday, as the view counts them (1970-01-01 was a Thursday)
	return posmod(day + 4, 7)


static func iso_week(day: int) -> int:
	# the date's ISO week: counted from the week of its year's first Thursday (the browser's, ui_html_adapter)
	var thursday := day + 3 - posmod(weekday_of(day) + 6, 7)
	var year := int(Time.get_datetime_dict_from_unix_time(thursday * 86400)["year"])
	return (thursday - days_from(year, 1, 1)) / 7 + 1


static func day_open(rules: Dictionary, date: String) -> bool:
	# whether a calendar's day can be picked: not before `min`, not after `max`, not one of `dates`, not on one of
	# `days` (weekdays); dates written YYYY-MM-DD compare as text
	var low := str(rules.get("min", ""))
	var high := str(rules.get("max", ""))
	if (low != "" and date < low) or (high != "" and date > high):
		return false
	var dates: Array = rules.get("dates", [])
	var days: Array = rules.get("days", [])
	return not (date in dates) and not (weekday_of(day_of(date)) in days)


static func _month_start(shown: String, value: String) -> Array:
	# [year, month] a calendar shows: `shown` (YYYY-MM), else its value's month, else today's
	for text: String in [shown, value.substr(0, 7), Time.get_date_string_from_system().substr(0, 7)]:
		var parts := text.split("-")
		if parts.size() == 2 and parts[0].is_valid_int() and parts[1].is_valid_int() \
				and parts[1].to_int() >= 1 and parts[1].to_int() <= 12:
			return [parts[0].to_int(), parts[1].to_int()]
	return [1970, 1]


func _calendar(node: Dictionary, x: int, y: int, w: int, ctx: Dictionary) -> int:
	# In a box: the month's title between the arrows to the month before and the month after (it moves here, kept
	# in `held`), the weekdays from `first_day`, the month's days in their columns, each week's number before it
	# when asked. A day clicked is the field's value, kept in `state` as an input's (tui.gd), which its form sends
	# under `bind`; outside a form it is only marked. The day picked is marked, today in the accent's colour; a day
	# that cannot be picked is drawn dim and does not react. Tab reaches one day; the arrow keys move between them.
	var key: String = ctx["key"]
	var value := _field_value(key, node)
	var start := _month_start(str(_held(key, "month", prop(node, "month", ""))), value)
	var year: int = start[0]
	var month: int = start[1]
	var first := days_from(year, month, 1)
	var count := days_in(year, month)
	var first_day := posmod(num(node, "first_day", 0), 7)
	var lead := 3 if truthy(prop(node, "week_numbers", false)) else 0      # the weeks' numbers' column
	var bw: int = CALENDAR_WIDTH + lead
	var dates: Array = []
	var days: Array = []
	var listed: Variant = prop(node, "disabled_dates", [])
	if listed is Array:
		for d: Variant in listed:
			dates.append(str(d))
	listed = prop(node, "disabled_days", [])
	if listed is Array:
		for d: Variant in listed:
			days.append(posmod(int(d), 7))
	var rules := {"min": str(prop(node, "min", "")), "max": str(prop(node, "max", "")), "dates": dates, "days": days}
	var offset := posmod(weekday_of(first) - first_day, 7)
	var h := (offset + count + 6) / 7 + 4
	box(x, y, bw, h, "")
	var left := x + 2
	# the title between the arrows
	var before := "%04d-%02d" % [year - 1 if month == 1 else year, 12 if month == 1 else month - 1]
	var after := "%04d-%02d" % [year + 1 if month == 12 else year, 1 if month == 12 else month + 1]
	var used := put(left, y + 1, " ‹ ", "button")
	_item({"kind": "month", "x": left, "y": y + 1, "w": used, "h": 1, "key": key, "label": "Previous month",
		   "goto": before, "card": ctx["card"]})
	var title := "%s %d" % [MONTH_NAMES[month - 1], year]
	var room := bw - 10
	var shown := cut(title, room)
	var tx := left + 3 + (room - text_width(shown)) / 2
	put(tx, y + 1, shown, "bold")
	_add_field({"kind": "calendar", "x": tx, "y": y + 1, "w": text_width(shown), "h": 1, "key": key, "label": title,
				"bind": str(prop(node, "bind", "")), "value": value, "month": "%04d-%02d" % [year, month],
				"rules": rules, "react": false, "card": ctx["card"], "form": ctx["form"]})
	used = put(x + bw - 5, y + 1, " › ", "button")
	_item({"kind": "month", "x": x + bw - 5, "y": y + 1, "w": used, "h": 1, "key": key, "label": "Next month",
		   "goto": after, "card": ctx["card"]})
	# the weekdays, and the days under them
	for k in 7:
		put(left + lead + 3 * k, y + 2, DAY_NAMES[(first_day + k) % 7], "muted")
	if lead > 0:
		for r in h - 4:
			put(left, y + 3 + r, "%2d" % iso_week(first - offset + 7 * r), "muted")
	var today := Time.get_date_string_from_system()
	var open: Array = []                   # the items of the days that can be picked
	var entry := -1                        # the one Tab reaches: the day picked, else today, else the first
	for d in range(1, count + 1):
		var cell := offset + d - 1
		var at := left + lead + 3 * (cell % 7)
		var row := y + 3 + cell / 7
		var date := "%04d-%02d-%02d" % [year, month, d]
		var can := day_open(rules, date)
		var style := "dim"
		if date == value:
			style = "tab_open"
		elif can:
			style = "today" if date == today else ""
		put(at, row, "%2d" % d, style)
		if can:
			open.append(_item({"kind": "day", "x": at, "y": row, "w": 2, "h": 1, "key": key, "label": str(d),
							   "date": date, "selected": date == value, "tab": false, "card": ctx["card"]}))
			if date == value or (date == today and entry < 0):
				entry = open[-1]
	if entry < 0 and not open.is_empty():
		entry = open[0]
	if entry >= 0:
		items[entry]["tab"] = true
	return h


func _drawn_width(x: int, y: int, w: int, h: int) -> int:
	# how far to the right what was drawn in the rows from `y` goes
	var right := x
	for r in range(max(0, y), min(grid.size(), y + h)):
		var row: Array = grid[r]
		for c in range(max(0, x), min(cols, x + w)):
			if str(row[c][0]) != " " or str(row[c][1]) != "":
				right = max(right, c + 1)
	return right - x


func _grid_text(x: int, y: int, w: int, h: int) -> String:
	var parts: Array = []
	for r in range(max(0, y), min(grid.size(), y + h)):
		var line := ""
		for c in range(max(0, x), min(cols, x + w)):
			line += str(grid[r][c][0])
		if line.strip_edges() != "":
			parts.append(line.strip_edges())
	return " ".join(parts)


func _measure(nodes: Array, w: int, ctx: Dictionary) -> int:
	# the rows the nodes take `w` cells wide, laid out aside: nothing of it is kept
	var kept := [grid, items, regions, tab_regions, progress, images, forms, motions, unsupported, overlays, tips,
				 toasts, autoplay]
	grid = []
	items = items.duplicate()
	regions = []
	tab_regions = []
	progress = []
	images = []
	forms = forms.duplicate(true)
	motions = []
	unsupported = []
	overlays = []
	tips = []
	toasts = []
	autoplay = []
	var outer_edge := right_edge
	right_edge = cols
	var h := stack(nodes, 0, 0, w, ctx, 0)
	right_edge = outer_edge
	grid = kept[0]
	items = kept[1]
	regions = kept[2]
	tab_regions = kept[3]
	progress = kept[4]
	images = kept[5]
	forms = kept[6]
	motions = kept[7]
	unsupported = kept[8]
	overlays = kept[9]
	tips = kept[10]
	toasts = kept[11]
	autoplay = kept[12]
	return h


func _layers() -> void:
	# what is drawn over the page once it is laid out: an open dropdown's options and a tooltip's tip next to
	# their element, an open modal over them, the toasts at their corner of the screen over it all (as in the
	# browser, where they stay clickable); what a layer opens in turn (a dropdown in a modal) goes over it
	var modal := false
	for o in overlays:
		modal = modal or str(o["kind"]) == "modal"
	var queue: Array = []
	for kind in ["menu", "tip", "modal", "toast"]:
		for o in overlays:
			# an open modal takes the mouse: the page's tooltips under it do not show their tips
			if str(o["kind"]) == kind and not (modal and kind == "tip"):
				queue.append(o)
	overlays = []
	right_edge = cols
	var corners := {}                      # the rows the toasts at each corner take so far
	var i := 0
	while i < queue.size():
		var o: Dictionary = queue[i]
		match str(o["kind"]):
			"menu":
				_menu_layer(o)
			"tip":
				_tip_layer(o)
			"toast":
				_toast_layer(o, corners)
			"modal":
				_modal_layer(o)
		queue.append_array(overlays)
		overlays = []
		i += 1


func _layer(kind: String, key: String, x: int, y: int, w: int, h: int) -> Dictionary:
	# a box over the page: what was drawn under it is hidden, and what reacted there cannot be reached
	for it in items:
		if int(it["x"]) < x + w and int(it["x"]) + max(1, int(it["w"])) > x \
				and int(it["y"]) < y + h and int(it["y"]) + max(1, int(it["h"])) > y:
			it["react"] = false
			it["covered"] = true
	for image in images:
		if int(image["x"]) < x + w and int(image["x"]) + int(image["w"]) > x \
				and int(image["y"]) < y + h and int(image["y"]) + int(image["h"]) > y:
			image["covered"] = true
	for r in h:
		fill(x, y + r, w, "")
	var layer := {"kind": kind, "key": key, "x": x, "y": y, "w": w, "h": h}
	layers.append(layer)
	return layer


func _modal_layer(o: Dictionary) -> void:
	# a box over the page, in the middle of the screen: its title, a close control when `closable`, its
	# content; while it is open it takes the clicks, and what is under it does not react
	var node: Dictionary = o["node"]
	var key: String = o["key"]
	var title := str(prop(node, "title", ""))
	var closable := truthy(prop(node, "closable", true))
	for it in items:
		it["react"] = false
		it["covered"] = true
	var size := str(prop(node, "size", ""))
	var mw: int = cols - 4 if size == "full" else int(MODAL_WIDTHS.get(size, 62))
	mw = min(mw, max(16, cols * 9 / 10), cols)
	var inner: Dictionary = (o["ctx"] as Dictionary).duplicate()
	inner["key"] = key
	inner["card"] = title
	var children: Array = node.get("children", [])
	var mh := _measure(children, mw - 4, inner) + 4
	var mx: int = (cols - mw) / 2
	var my := 0
	if mh <= view_rows:
		my = view_top + (view_rows - mh) / 2
		follows_view = true
	var layer := _layer("modal", key, mx, my, mw, mh)
	layer["closable"] = closable
	box(mx, my, mw, mh, "", "border")
	if title != "":
		put(mx + 2, my, " " + cut(title, mw - 10) + " ", "title")
	if closable:
		var used := put(mx + mw - 5, my, " × ", "bold")
		_item({"kind": "close", "x": mx + mw - 5, "y": my, "w": used, "h": 1, "key": key,
			   "label": title if title != "" else "Close", "of": "modal", "card": title})
	stack(children, mx + 2, my + 2, mw - 4, inner, gap_rows(node))


func _toast_layer(o: Dictionary, corners: Dictionary) -> void:
	# a small box at its corner of the screen (`position`), the toasts at one corner one under the other: its
	# icon and title in its variant's colour, its message, a close control when `dismissible`; it goes after
	# `duration` ms (tui.gd)
	var node: Dictionary = o["node"]
	var key: String = o["key"]
	var variant := str(prop(node, "variant", "info"))
	if variant == "error":
		variant = "danger"
	if not TOAST_ICONS.has(variant):
		variant = "info"
	var icon := cut(str(prop(node, "icon", "")), 2)
	if icon == "":
		icon = TOAST_ICONS[variant]
	var title := str(prop(node, "title", ""))
	var message := str(prop(node, "message", ""))
	if message == "":
		message = str(prop(node, "text", ""))
	var dismissible := truthy(prop(node, "dismissible", true))
	var room: int = min(44, cols - 2)
	var lines := wrap_text(message, room - 4) if message != "" else []
	var widest := text_width(icon) + text_width(title) + 8 + (4 if dismissible else 0)
	for line in lines:
		widest = max(widest, text_width(line) + 4)
	var tw: int = min(room, max(widest, 24))
	var th: int = lines.size() + 2
	var position := str(prop(node, "position", "top-right"))
	var taken: int = corners.get(position, 0)
	corners[position] = taken + th
	var ty: int = view_top + taken
	if position.begins_with("bottom"):
		ty = view_top + view_rows - th - taken
	ty = max(0, ty)
	var tx: int = cols - tw - 1
	if position.ends_with("left"):
		tx = 1
	elif position.ends_with("center"):
		tx = (cols - tw) / 2
	follows_view = true
	_layer("toast", key, tx, ty, tw, th)
	box(tx, ty, tw, th, "", "fill:" + variant)
	var at := tx + 2 + put(tx + 2, ty, " " + icon, "fill:" + variant)
	if title != "":
		at += put(at, ty, " " + cut(title, tw - 12), "bold")
	put(at, ty, " ", "")
	for k in lines.size():
		put(tx + 2, ty + 1 + k, lines[k], "")
	if dismissible:
		var used := put(tx + tw - 5, ty, " × ", "muted")
		_item({"kind": "close", "x": tx + tw - 5, "y": ty, "w": used, "h": 1, "key": key,
			   "label": title if title != "" else message, "of": "toast", "card": ""})
	var ms := num(node, "duration", 3000)
	if ms > 0:
		toasts.append({"key": key, "ms": ms})


func _tip_layer(o: Dictionary) -> void:
	# the tip in a small box next to its element (`position`: top, bottom, left, right), turned to the other
	# side when there is no room on the screen
	var lines := wrap_text(str(o["text"]), min(40, cols - 4))
	var widest := 0
	for line in lines:
		widest = max(widest, text_width(line))
	var tw: int = min(cols, widest + 2)
	var th := lines.size()
	var ex: int = o["x"]
	var ey: int = o["y"]
	var ew: int = o["w"]
	var eh: int = o["h"]
	var position := str(o["position"])
	var tx: int = ex + ew / 2 - tw / 2
	var ty: int = ey - th
	match position:
		"bottom":
			ty = ey + eh
		"left":
			tx = ex - tw - 1
			ty = ey
			if tx < 0:
				tx = ex + ew + 1
		"right":
			tx = ex + ew + 1
			ty = ey
			if tx + tw > cols:
				tx = ex - tw - 1
		_:
			if ty < view_top:
				ty = ey + eh
	tx = clamp(tx, 0, max(0, cols - tw))
	ty = max(0, ty)
	_layer("tip", str(o["key"]), tx, ty, tw, th)
	for k in th:
		fill(tx, ty + k, tw, "tip")
		put(tx + 1, ty + k, lines[k], "tip")


func _menu_layer(o: Dictionary) -> void:
	# an open dropdown's options in a box under its button (over it when the screen has no room under it),
	# each option a link that posts its action, as a menu's
	var node: Dictionary = o["node"]
	var key: String = o["key"]
	var options: Array = node.get("children", [])
	var widest := 8
	for c in options:
		if c is Dictionary:
			widest = max(widest, natural(c))
	var mw: int = min(cols, max(int(o["w"]), widest + 4))
	var inner: Dictionary = (o["ctx"] as Dictionary).duplicate()
	inner["key"] = key
	var mh: int = max(1, _measure(options, mw - 4, inner)) + 2
	var mx: int = int(o["x"])
	if str(prop(node, "dropdown_align", "left")) == "right":
		mx = int(o["x"]) + int(o["w"]) - mw
	mx = clamp(mx, 0, max(0, cols - mw))
	var my: int = int(o["y"]) + 1
	if my + mh > view_top + view_rows and int(o["y"]) - mh >= view_top:
		my = int(o["y"]) - mh
	_layer("menu", key, mx, my, mw, mh)
	box(mx, my, mw, mh, "", "border")
	var first := items.size()
	stack(options, mx + 2, my + 1, mw - 4, inner, 0)
	for k in range(first, items.size()):
		items[k]["menu"] = str(o["label"])


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
