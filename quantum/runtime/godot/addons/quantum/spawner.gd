extends Node
# qg:spawner: places `count` instances (0: no end) of a prefab — one of
# several, drawn from the scene's seeded source — one every `every` ticks
# from tick `from`, at (x, y) with x "random" across the scene width, or
# along="edges": a random point on the scene's border, a flying prefab
# headed into the scene (heading="inward") turned by up to `spread`
# degrees. Every draw is from the scene's seed, so a run is the same run.

var prefabs: Array = []
var from_tick: int = 0
var every: int = 60
var count: int = 1
var x = "random"
var y: float = -12.0
var along: String = ""
var heading: String = ""
var spread: float = 0.0
var _ticks: int = 0
var _placed: int = 0


func setup(spec: Dictionary) -> void:
	prefabs = spec.get("prefabs", [spec.get("prefab", "")])
	from_tick = int(spec.get("from", 0))
	every = maxi(1, int(spec.get("every", 60)))
	count = int(spec.get("count", 1))
	x = spec.get("x", "random")
	y = float(spec.get("y", -12.0))
	along = str(spec.get("along", "")) if spec.get("along") != null else ""
	heading = str(spec.get("heading", "")) if spec.get("heading") != null else ""
	spread = float(spec.get("spread", 0.0))
	name = "spawner-" + str(prefabs[0])


func _physics_process(_delta: float) -> void:
	_ticks += 1
	if (count > 0 and _placed >= count) or _ticks < from_tick:
		return
	if (_ticks - from_tick) % every != 0:
		return
	var scene := get_parent()
	var w := float(scene.q_spec.get("width", 256)) if "q_spec" in scene else 256.0
	var h := float(scene.q_spec.get("height", 224)) if "q_spec" in scene else 224.0
	var rng: RandomNumberGenerator = scene.rng if "rng" in scene else RandomNumberGenerator.new()
	var prefab: String = str(prefabs[0]) if prefabs.size() == 1 else str(prefabs[rng.randi_range(0, prefabs.size() - 1)])
	var at: Vector2
	var inward := Vector2.ZERO
	if along == "edges":
		# a point on the border, going round from the top-left corner
		var t := rng.randf_range(0.0, 2.0 * (w + h))
		if t < w:
			at = Vector2(t, 0.0)
			inward = Vector2.DOWN
		elif t < w + h:
			at = Vector2(w, t - w)
			inward = Vector2.LEFT
		elif t < 2.0 * w + h:
			at = Vector2(w - (t - w - h), h)
			inward = Vector2.UP
		else:
			at = Vector2(0.0, h - (t - 2.0 * w - h))
			inward = Vector2.RIGHT
	else:
		var at_x: float
		if x is String:
			at_x = rng.randf_range(16.0, w - 16.0)
		else:
			at_x = float(x)
		at = Vector2(at_x, y)
	var thing := Q.spawn_at(scene, prefab, at)
	if heading == "inward" and thing != null and "heading" in thing:
		var turn := deg_to_rad(rng.randf_range(-spread, spread)) if spread > 0.0 else 0.0
		thing.heading = inward.rotated(turn)
	_placed += 1
