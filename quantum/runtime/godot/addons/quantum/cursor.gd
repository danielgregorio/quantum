extends Node2D
# A player's pointer (qg:cursor): the mouse, or that player's directions by
# `step` pixels a tick, snapped to a grid of `grid` when asked, drawn with a
# sprite when given one. Alone, it lands in Q.cursors[player] at once; under
# the lockstep it is the raw pointer the lockstep sends with the input, and
# Q.cursors[player] is what came back — the same on every peer.

var player: int = 1
var step: float = 16.0
var grid: int = 0
var _scene: Node = null
var _pos: Vector2 = Vector2.ZERO
var _mouse_seen: Vector2 = Vector2(-1, -1)


func setup(spec: Dictionary, scene: Node) -> void:
	player = int(spec.get("player", 1))
	step = float(spec.get("step", 16.0))
	grid = int(spec["grid"]) if spec.get("grid") != null else 0
	_scene = scene
	name = "cursor-%d" % player
	var w := float(scene.q_spec.get("width", 256)) if "q_spec" in scene else 256.0
	var h := float(scene.q_spec.get("height", 224)) if "q_spec" in scene else 224.0
	_pos = Vector2(w / 2.0, h / 2.0)
	_publish()


func _a(action: String) -> String:
	return action if player == 1 else "p%d_%s" % [player, action]


func _physics_process(_delta: float) -> void:
	var lockstep: bool = _scene.get_parent() != null and "lockstep" in _scene.get_parent() and _scene.get_parent().lockstep != null
	var mine: bool = not lockstep or _scene.get_parent().lockstep.player == player
	if mine:
		if Q.tape_cursor != null:
			_pos = Q.tape_cursor
		else:
			var mouse := get_global_mouse_position()
			if mouse != _mouse_seen:
				_mouse_seen = mouse
				_pos = mouse
		# under the lockstep, this peer's own keys (player 1's actions) before they travel;
		# alone, the tick's input of this cursor's player
		var dir: Vector2
		if lockstep:
			dir = Vector2(Input.get_action_strength("right") - Input.get_action_strength("left"),
				Input.get_action_strength("down") - Input.get_action_strength("up"))
		else:
			dir = Vector2(Q.strength(_a("right")) - Q.strength(_a("left")),
				Q.strength(_a("down")) - Q.strength(_a("up")))
		_pos += dir * step
		var w := float(_scene.q_spec.get("width", 256)) if "q_spec" in _scene else 256.0
		var h := float(_scene.q_spec.get("height", 224)) if "q_spec" in _scene else 224.0
		_pos = Vector2(clampf(_pos.x, 0.0, w), clampf(_pos.y, 0.0, h))
		if lockstep:
			Q.raw_cursor = _pos
		else:
			Q.cursors[player] = _pos
	_publish()


func snapped_of(p: Vector2) -> Vector2:
	if grid <= 0:
		return p
	return Vector2(floorf(p.x / grid) * grid + grid / 2.0, floorf(p.y / grid) * grid + grid / 2.0)


func _publish() -> void:
	var p: Vector2 = Q.cursors.get(player, _pos)
	position = snapped_of(p)


# What qg:on-select sees.
func where() -> Dictionary:
	var p: Vector2 = Q.cursors.get(player, _pos)
	var s := snapped_of(p)
	var d := {"x": s.x, "y": s.y, "player": player}
	if grid > 0:
		d["col"] = int(floorf(p.x / grid))
		d["row"] = int(floorf(p.y / grid))
	return d
