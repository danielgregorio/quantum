extends Camera2D
# qg:camera: what the screen shows. It follows a character, or the middle of
# several, in the game's ticks, so a replay and every peer frame the same.
# Only seen: nothing in the game's state depends on it.
#
#   zoom=       2 is twice as close
#   dead-zone=  WxH: the box about the middle of the screen in which the
#               followed one moves before the camera does
#   lead=       pixels it looks ahead, the way the followed one goes
#   smooth=     how fast it catches up, per second (0: at once)
#   fit=        several followed: it zooms out to keep them all on the
#               screen, down to zoom-min, and back in as they come together

var targets: Array = []
var zoom_base := 1.0
var zoom_min := 0.5
var dead := Vector2.ZERO          # half the dead zone
var lead := 0.0
var smooth := 0.0
var fit := false
var _focus := Vector2.ZERO        # where it aims, before smoothing
var _ahead := Vector2.ZERO        # the look-ahead, eased


func setup(spec: Dictionary, characters: Dictionary) -> void:
	name = "Camera"
	position_smoothing_enabled = false
	for id in spec.get("follow", []):
		if characters.has(id):            # a character placed only sometimes (if=) may be absent
			targets.append(characters[id])
	zoom_base = float(spec.get("zoom", 1.0))
	zoom_min = minf(float(spec.get("zoom_min", 0.5)), zoom_base)
	zoom = Vector2(zoom_base, zoom_base)
	if spec.get("dead_zone") != null:
		dead = Vector2(spec["dead_zone"][0], spec["dead_zone"][1]) / 2.0
	lead = float(spec.get("lead", 0.0))
	smooth = float(spec.get("smooth", 0.0))
	fit = bool(spec.get("fit", false))
	process_physics_priority = 100     # after the bodies have moved this tick
	var at = _middle()
	if at != null:
		position = at
		_focus = at


# qg:camera-to: a shot away from what it follows — there in `go` ticks, `hold`
# ticks there, and back in `go` — the scene waiting meanwhile when asked.
var _shot: Dictionary = {}


func show_point(scene: Node, at: Vector2, zoom_to: float, go: int, hold: int, pause_: bool) -> void:
	_shot = {"from": position, "to": at, "zoom_from": zoom.x, "zoom_to": zoom_to if zoom_to > 0.0 else zoom.x,
		"go": maxi(1, go), "hold": hold, "t": 0, "phase": "go", "pause": pause_}
	if pause_ and not scene.q_paused:
		Q.pause(scene, true)
	else:
		_shot["pause"] = false   # it did not pause the scene: it does not resume it


func _step_shot() -> void:
	_shot["t"] += 1
	var k := float(_shot["t"]) / float(_shot["go"])
	match _shot["phase"]:
		"go":
			var e := ease(minf(k, 1.0), -2.0)   # in and out
			position = (_shot["from"] as Vector2).lerp(_shot["to"], e)
			zoom = Vector2.ONE * lerpf(_shot["zoom_from"], _shot["zoom_to"], e)
			if _shot["t"] >= _shot["go"]:
				_shot["phase"] = "hold"
				_shot["t"] = 0
		"hold":
			if _shot["t"] >= _shot["hold"]:
				_shot["phase"] = "back"
				_shot["t"] = 0
		"back":
			var middle = _middle()
			var home: Vector2 = middle if middle != null else _shot["from"]
			var e := ease(minf(k, 1.0), -2.0)
			position = (_shot["to"] as Vector2).lerp(home, e)
			zoom = Vector2.ONE * lerpf(_shot["zoom_to"], zoom_base, e)
			if _shot["t"] >= _shot["go"]:
				_focus = position
				var resume: bool = _shot["pause"]
				_shot = {}
				var scene := get_parent()
				if resume and scene != null and scene.q_paused:
					Q.pause(scene, false)


# For the rollback: a shot as far as it has got (it pauses the scene, which is the game's state).
func q_save() -> Dictionary:
	return {"shot": _shot.duplicate(true), "position": position, "zoom": zoom.x, "focus": _focus}


func q_load(d: Dictionary) -> void:
	_shot = d["shot"].duplicate(true)
	position = d["position"]
	zoom = Vector2.ONE * float(d["zoom"])
	_focus = d["focus"]


func _physics_process(delta: float) -> void:
	if not _shot.is_empty():
		_step_shot()
		return
	var middle = _middle()
	if middle == null:
		return
	if lead > 0.0:
		var going := Vector2.ZERO
		var first: Node = _alive()[0]
		if "velocity" in first and (first.velocity as Vector2).length() > 1.0:
			going = (first.velocity as Vector2).normalized() * lead
		_ahead = _ahead.move_toward(going, lead * 2.0 * delta)   # half a second to turn round
	var want: Vector2 = middle + _ahead
	if dead == Vector2.ZERO:
		_focus = want
	else:   # only as far as the followed one has left the box
		var off := want - _focus
		if absf(off.x) > dead.x:
			_focus.x = want.x - signf(off.x) * dead.x
		if absf(off.y) > dead.y:
			_focus.y = want.y - signf(off.y) * dead.y
	position = _focus if smooth <= 0.0 else position.lerp(_focus, minf(1.0, smooth * delta))
	if fit:
		_fit()


# The followed ones still there. They are the scene's children, as the camera is:
# their positions are in its space, from the moment the scene is built.
func _alive() -> Array:
	return targets.filter(func(t): return is_instance_valid(t) and not t.is_queued_for_deletion())


func _middle():
	var alive := _alive()
	if alive.is_empty():
		return null
	var sum := Vector2.ZERO
	for t in alive:
		sum += (t as Node2D).position
	return sum / alive.size()


# Close enough to show every followed one, with a margin of a sixth of the screen.
func _fit() -> void:
	var alive := _alive()
	if alive.size() < 2:
		zoom = Vector2(zoom_base, zoom_base)
		return
	var lo: Vector2 = (alive[0] as Node2D).position
	var hi := lo
	for t in alive:
		var p: Vector2 = (t as Node2D).position
		lo = Vector2(minf(lo.x, p.x), minf(lo.y, p.y))
		hi = Vector2(maxf(hi.x, p.x), maxf(hi.y, p.y))
	var screen := get_viewport_rect().size
	var span := (hi - lo) + screen / 3.0
	var z := minf(zoom_base, minf(screen.x / maxf(span.x, 1.0), screen.y / maxf(span.y, 1.0)))
	z = maxf(zoom_min, z)
	zoom = Vector2(z, z)


# For the play protocol: where the screen looks, and how close.
func quantum_view() -> Dictionary:
	return {"kind": "camera", "x": snappedf(get_screen_center_position().x, 0.1),
		"y": snappedf(get_screen_center_position().y, 0.1), "zoom": snappedf(zoom.x, 0.01)}
