extends SceneTree
# Opens a built game's main scene, runs one physics tick (or --ticks=, and as many frames drawn), and dumps the class
# of every node under the root (the autoloads too: sounds live under Q) and the values of the properties asked for:
#   godot --headless --path <project> -s <this file> -- --props=zoom,modulate --out=<json> [--ticks=3]
# Written for tests/godot/test_godot_gd.py: the compiler's tag → Godot class
# table and the gd: values must match what the runtime built.

var out_path := ""
var props: PackedStringArray = []
var scene: Node
var ticks := 0
var frames := 0
var wait := 1


func _initialize() -> void:
	for a in OS.get_cmdline_user_args():
		if a.begins_with("--out="):
			out_path = a.substr(6)
		elif a.begins_with("--props="):
			props = a.substr(8).split(",", false)
		elif a.begins_with("--ticks="):
			wait = int(a.substr(8))
	var main: String = ProjectSettings.get_setting("application/run/main_scene", "")
	scene = load(main).instantiate()
	root.add_child(scene)


func _process(_delta: float) -> bool:
	frames += 1
	return false


func _physics_process(_delta: float) -> bool:
	if ticks < wait or (wait > 1 and frames < wait):
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
