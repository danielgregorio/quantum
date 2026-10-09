extends Node
# qg:timer: runs the scene's handler after so many ticks from entering the
# scene (once), or every so many ticks (count times, or forever).

var after: int = -1
var every: int = -1
var from_tick: int = 0
var count: int = 0
var handler: String = ""
var _ticks: int = 0
var _runs: int = 0
var _scene: Node = null


func setup(spec: Dictionary, scene: Node) -> void:
	after = int(spec["after"]) if spec.get("after") != null else -1
	every = int(spec["every"]) if spec.get("every") != null else -1
	from_tick = int(spec.get("from", 0)) if spec.get("from") != null else 0
	count = int(spec.get("count", 0))
	handler = spec["handler"]
	_scene = scene
	name = "timer-" + handler


func _physics_process(_delta: float) -> void:
	_ticks += 1
	if after >= 0:
		if _ticks == after and _scene.has_method(handler):
			_scene.call(handler, null, null)
		return
	if every > 0 and _ticks > from_tick and (_ticks - from_tick) % every == 0 and (count == 0 or _runs < count):
		_runs += 1
		if _scene.has_method(handler):
			_scene.call(handler, null, null)
