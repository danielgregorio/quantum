extends CanvasLayer
# Text over the game (qg:hud): counters bound to the scene's state, read
# every frame so the HUD is never stale.

var _scene: Node = null
var _labels: Array = []   # [{label, bind, prefix}]


func setup(spec: Dictionary, scene: Node) -> void:
	_scene = scene
	name = "Hud"
	var box := VBoxContainer.new()
	var viewport_w: int = ProjectSettings.get_setting("display/window/size/viewport_width", 256)
	match spec.get("position", "top-left"):
		"top-center":
			box.position = Vector2(viewport_w / 2.0 - 40, 4)
		"top-right":
			box.position = Vector2(viewport_w - 84, 4)
		_:
			box.position = Vector2(4, 4)
	add_child(box)
	for item in spec.get("items", []):
		if item["kind"] == "counter" or item["kind"] == "text":
			var label := Label.new()
			label.add_theme_font_size_override("font_size", 8)
			box.add_child(label)
			_labels.append({"label": label, "bind": item["bind"], "prefix": item.get("label", "")})
	_refresh()


func _process(_delta: float) -> void:
	_refresh()


func _refresh() -> void:
	for entry in _labels:
		var value = _scene.get(entry["bind"])
		if value == null:
			value = G.get(entry["bind"])
		var text: String = str(value)
		if value is float and value == floorf(value):
			text = str(int(value))
		entry["label"].text = (entry["prefix"] + " " if entry["prefix"] != "" else "") + text
