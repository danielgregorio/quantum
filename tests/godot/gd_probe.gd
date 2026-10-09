extends SceneTree
# Opens a built game's main scene, runs one physics tick, and dumps the class
# of every node under the root (the autoloads too: sounds live under Q) and the values of the properties asked for:
#   godot --headless --path <project> -s <this file> -- --props=zoom,modulate --out=<json>
# Written for tests/godot/test_godot_gd.py: the compiler's tag → Godot class
# table and the gd: values must match what the runtime built.

var out_path := ""
var props: PackedStringArray = []
var scene: Node
var ticks := 0


func _initialize() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			out_path = a.substr(6)
		elif a.begins_with("--props="):
			props = a.substr(8).split(",", false)
	var main: String = ProjectSettings.get_setting("application/run/main_scene", "")
	scene = load(main).instantiate()
	root.add_child(scene)


func _physics_process(_delta: float) -> bool:
	if ticks < 1:
		ticks += 1
		return false
	var dump := {}
	for n in _walk(root):
		var entry := {"class": n.get_class()}
		for p in props:
			if p in n:
				entry[p] = var_to_str(n.get(p))
		dump[String(root.get_path_to(n))] = entry
	var f := FileAccess.open(out_path, FileAccess.WRITE)
	f.store_string(JSON.stringify(dump, "", true))
	return true


func _walk(n: Node) -> Array:
	var out := [n]
	for c in n.get_children():
		out += _walk(c)
	return out
