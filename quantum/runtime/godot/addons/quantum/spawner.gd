extends Node
# qg:spawner: places `count` instances of a prefab, one every `every`
# ticks from tick `from`, at (x, y) — x "random" across the scene width,
# from the scene's seeded random source, so a run is the same run.

var prefab: String = ""
var from_tick: int = 0
var every: int = 60
var count: int = 1
var x = "random"
var y: float = -12.0
var _ticks: int = 0
var _placed: int = 0


func setup(spec: Dictionary) -> void:
	prefab = spec["prefab"]
	from_tick = int(spec.get("from", 0))
	every = maxi(1, int(spec.get("every", 60)))
	count = int(spec.get("count", 1))
	x = spec.get("x", "random")
	y = float(spec.get("y", -12.0))
	name = "spawner-" + prefab


func _physics_process(_delta: float) -> void:
	_ticks += 1
	if _placed >= count or _ticks < from_tick:
		return
	if (_ticks - from_tick) % every != 0:
		return
	var scene := get_parent()
	var at_x: float
	if x is String:
		var w := float(scene.q_spec.get("width", 256)) if "q_spec" in scene else 256.0
		at_x = scene.rng.randf_range(16.0, w - 16.0) if "rng" in scene else w / 2.0
	else:
		at_x = float(x)
	Q.spawn_at(scene, prefab, Vector2(at_x, y))
	_placed += 1
