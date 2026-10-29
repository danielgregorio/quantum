extends Node2D
# What a character or a prefab looks like besides its frame, kept up every
# tick by one child node ("Looks"): the qg:labels over it (their text a
# method of the script that owns it: the scene's for a character, P's for a
# prefab, called with `me`), when it is shown (visible=), an effect kept
# going on it (particles=), the lights it carries (qg:light) and the line it
# leaves behind it (trail=). A
# qg:label in a scene is one of these too, at its place, its method called
# with nothing. All of it is only seen: the game's state never reads it.

const TRAIL_POINTS := 10

var caller: Object = null
var with_me: bool = true          # the methods take `me` (a thing's), or nothing (a scene's label)
var visible_method: String = ""
var labels: Array = []            # [Label, method]
var bars: Array = []              # [the fill, its width, method]: qg:health-bar
var trail: Line2D = null
var _owner: Node = null           # the thing, as setup is called (it is made before it joins the tree)


func setup(spec: Dictionary, caller_: Object, game: Dictionary, thing: Node = null) -> void:
	name = "Looks"
	caller = caller_
	_owner = thing
	with_me = thing != null
	z_index = 20   # the labels over what is near
	visible_method = str(spec.get("visible", "")) if spec.get("visible") != null else ""
	for lb in spec.get("labels", []):
		# if=: placed only when it holds as the thing is placed
		if lb.get("if") != null and caller.has_method(str(lb["if"])) and not caller.call(str(lb["if"]), _owner):
			continue
		labels.append([make_label(lb), str(lb["method"])])
	for hb in spec.get("bars", []):
		var w := float(hb.get("width", 14))
		var h := float(hb.get("height", 2))
		var at := Vector2(float(hb.get("dx", 0.0)) - w / 2.0, float(hb.get("dy", -10.0)) - h / 2.0)
		var back := ColorRect.new()
		back.color = Color(0, 0, 0, 0.6)
		back.position = at
		back.size = Vector2(w, h)
		back.mouse_filter = Control.MOUSE_FILTER_IGNORE
		add_child(back)
		var fill := ColorRect.new()
		fill.color = Color(str(hb.get("color", "#40e040")))
		fill.position = at
		fill.size = Vector2(w, h)
		fill.mouse_filter = Control.MOUSE_FILTER_IGNORE
		add_child(fill)
		bars.append([fill, w, str(hb["method"])])
	if spec.get("particles") != null and game.get("particles", {}).has(spec["particles"]):
		var fx: CPUParticles2D = load("res://addons/quantum/particles.gd").make(game["particles"][spec["particles"]])
		fx.one_shot = false
		fx.emitting = true
		fx.z_index = -1
		add_child(fx)
	for spec_light in spec.get("lights", []):   # a lantern it carries, a glow
		var light := PointLight2D.new()
		light.set_script(load("res://addons/quantum/light.gd"))
		light.setup(spec_light)
		light.position = Vector2(float(spec_light.get("dx", 0.0)), float(spec_light.get("dy", 0.0)))
		add_child(light)
	if spec.get("trail") != null:
		trail = Line2D.new()
		trail.top_level = true   # its points are the scene's: it stays where the thing was
		trail.width = 2.0
		trail.z_index = -21      # under the thing
		var colour := Color(spec["trail"])
		var fade := Gradient.new()
		fade.set_color(0, Color(colour, 0.0))
		fade.set_color(1, Color(colour, 0.8))
		trail.gradient = fade
		add_child(trail)


func make_label(lb: Dictionary) -> Label:
	var label := Label.new()
	var size := int(lb.get("size", 8))
	label.add_theme_font_size_override("font_size", size)
	label.add_theme_color_override("font_color", Color(str(lb.get("color", "#ffffff"))))
	label.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.8))
	label.add_theme_constant_override("outline_size", 2)
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	label.size = Vector2(160, size + 6)
	label.position = Vector2(float(lb.get("dx", 0.0)), float(lb.get("dy", 0.0))) - label.size / 2.0
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(label)
	return label


func _ready() -> void:
	_update()


func _physics_process(_delta: float) -> void:
	_update()


func _update() -> void:
	var me = get_parent() if with_me else null
	if not is_instance_valid(caller):
		return
	if visible_method != "" and me != null and caller.has_method(visible_method):
		me.visible = bool(caller.call(visible_method, me))
	for entry in labels:
		var label: Label = entry[0]
		if caller.has_method(entry[1]):
			label.text = str(caller.call(entry[1], me) if with_me else caller.call(entry[1]))
	for entry in bars:
		var top := float(caller.call(entry[2] + "_max", me)) if caller.has_method(entry[2] + "_max") else 0.0
		var v := float(caller.call(entry[2], me)) if caller.has_method(entry[2]) else 0.0
		(entry[0] as ColorRect).size.x = float(entry[1]) * clampf(v / top, 0.0, 1.0) if top > 0.0 else 0.0
	if trail != null and me is Node2D:
		trail.add_point((me as Node2D).global_position)
		while trail.get_point_count() > TRAIL_POINTS:
			trail.remove_point(0)


# What the play protocol's screen shows of it: the labels' texts, and where (a
# name over a player, what an enemy has left). Nothing while it is hidden.
func quantum_view() -> Dictionary:
	if (labels.is_empty() and bars.is_empty()) or not is_visible_in_tree():
		return {}
	var texts := []
	for entry in labels:
		if (entry[0] as Label).visible and (entry[0] as Label).text != "":
			texts.append(Q.translate((entry[0] as Label).text))
	var filled := []
	for entry in bars:                # how full each bar is, 0 to 1
		filled.append(snappedf((entry[0] as ColorRect).size.x / float(entry[1]), 0.01))
	if texts.is_empty() and filled.is_empty():
		return {}
	var out := {"kind": "label", "items": texts, "x": snappedf(global_position.x, 0.1),
		"y": snappedf(global_position.y, 0.1)}
	if not filled.is_empty():
		out["bars"] = filled
	return out
