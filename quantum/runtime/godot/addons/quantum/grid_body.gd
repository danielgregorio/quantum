extends CharacterBody2D
# The grid controller (qg:character controller="grid"): steps from the
# centre of one cell of the scene's tilemap to the next, in step_frames
# ticks, while a direction is held. A cell is closed by a tile of a layer
# with collision, by the edge of the map, or by a thing standing in it
# (a qg:instance). Stepping into a thing runs the character's
# qg:on-collision with the thing's tag and does not move it, unless it is
# pushable (a crate) and the cell beyond it is free: then both go a cell on;
# stepping into anything else closed is a bump, which takes as long as a step.
# Arriving in a cell, it touches the zones there (qg:zone, a Tiled zone), and
# an exit there takes it on. As Godot's JRPG demo: two directions held at
# once step diagonally only with diagonal. On a map of hexes it steps to the
# neighbour most the way held: left and right along the row, up and down to
# the side it faces; on diamonds, the keys turned an eighth (right is down
# and to the right). Deterministic: everything in
# _physics_process at the fixed tick.

const Animator := preload("res://addons/quantum/animator.gd")

# The demo's bump: where the picture shakes to over the bump, in its fifths.
const BUMP := [Vector2(0, 0), Vector2(-3, -4), Vector2(2, 1.5), Vector2(-2.6, 2), Vector2(1.8, -1.9), Vector2(0, 0)]
const HOP := 20.0   # how high the picture hops on a step

var step_frames: int = 15
var diagonal: bool = false
var player: int = 1
var facing: Vector2i = Vector2i.RIGHT
var animator: Node = null
var state: String = ""

# The cell it stands in, for the .q: `me.col`, `me.row`, `player.col`.
var col: int:
	get:
		return cell().x
var row: int:
	get:
		return cell().y

var _handlers: Array = []
var _scene: Node = null
var _sprite: Sprite2D = null
var _tile: float = 64.0
var _from: Vector2 = Vector2.ZERO
var _to: Vector2 = Vector2.ZERO
var _moving: int = 0      # ticks left of a step
var _bumping: int = 0     # ticks left of a bump
var _pushed: Node2D = null   # the thing it pushes on this step, and from where to where
var _pushed_from: Vector2 = Vector2.ZERO
var _pushed_to: Vector2 = Vector2.ZERO
var _routed: bool = false   # this tick's step is a route's next cell (a pointer's), not a key's way


func setup(spec: Dictionary) -> void:
	player = int(spec.get("player", 1))
	step_frames = maxi(1, int(spec.get("step_frames", step_frames)))
	diagonal = bool(spec.get("diagonal", false))
	motion_mode = CharacterBody2D.MOTION_MODE_FLOATING
	collision_layer = 1   # an exit sees it come in; it moves by its cells, nothing stops it
	collision_mask = 0


func wire(_sensor: Area2D, spec: Dictionary, scene: Node, sprite: Sprite2D) -> void:
	_handlers = spec.get("on_collision", [])
	_scene = scene
	_sprite = sprite
	animator = Animator.new()
	animator.name = "Animator"
	animator.setup(sprite, spec.get("animations", {}))
	add_child(animator)
	animator.play("idle")


func _ready() -> void:
	var map := _map()
	if map != null:
		_tile = float(map.tile)
	position = _centre(cell())


func quantum_node_state() -> Dictionary:
	var c := cell()
	return {"col": c.x, "row": c.y, "facing": [facing.x, facing.y]}


func respawn() -> void:
	_moving = 0
	_bumping = 0


# The cell it stands in (the one it is stepping to, mid-step).
func cell() -> Vector2i:
	var at := _to if _moving > 0 else position
	return _cell_at(at)


func _cell_at(at: Vector2) -> Vector2i:
	var map := _map()
	if map != null and map.shape != "square":
		return map.cell_of(at)
	return Vector2i(floori(at.x / _tile), floori(at.y / _tile))


func _centre(c: Vector2i) -> Vector2:
	var map := _map()
	if map != null and map.shape != "square":
		return map.centre_of(c)
	return Vector2((c.x + 0.5) * _tile, (c.y + 0.5) * _tile)


# The cell past `b`, from `a`: where a pushed crate goes.
func _beyond(a: Vector2i, b: Vector2i) -> Vector2i:
	var map := _map()
	return map.beyond(a, b) if map != null else b + (b - a)


func _map() -> Node:
	return _scene.get_node_or_null("Tilemap") if _scene != null else null


# A tile that stops walkers: one of a layer with collision, unless its
# qg:tile says shape="none".
func _wall(c: Vector2i) -> bool:
	var map := _map()
	if map == null:
		return false
	if c.x < 0 or c.y < 0 or c.x >= map.columns or c.y >= map.rows_count:
		return true
	for layer in map.get_children():
		if not (layer is TileMapLayer) or layer.tile_set.get_physics_layers_count() == 0:
			continue
		var data: TileData = layer.get_cell_tile_data(c)
		if data != null and data.get_collision_polygons_count(0) > 0:
			return true
	return false


func _thing_in(c: Vector2i) -> Node:
	for n in get_tree().get_nodes_in_group("q_thing"):
		if n.get_parent() == _scene and not n.is_queued_for_deletion() and n != self and not n.has_meta("q_carrier"):
			if _cell_at(n.position) == c:
				return n
	return null


func _physics_process(_delta: float) -> void:
	if _moving > 0:
		_moving -= 1
		var t := 1.0 - float(_moving) / step_frames
		position = _from.lerp(_to, t)
		_sprite.position = Vector2(0, -HOP * sin(PI * t))
		if is_instance_valid(_pushed):
			_pushed.position = _pushed_from.lerp(_pushed_to, t)
		if _moving == 0:
			position = _to
			_sprite.position = Vector2.ZERO
			_pushed = null
			_play("idle")
			_arrive()
		return
	if _bumping > 0:
		_bumping -= 1
		var k := (1.0 - float(_bumping) / step_frames) * (BUMP.size() - 1)
		var i := mini(int(k), BUMP.size() - 2)
		_sprite.position = (BUMP[i] as Vector2).lerp(BUMP[i + 1], k - i)
		if _bumping == 0:
			_sprite.position = Vector2.ZERO
			_play("idle")
		return
	var dir := _wanted()
	if dir == Vector2i.ZERO:
		return
	var target := cell() + dir
	if _map() != null and _map().shape != "square" and not _routed:
		# a key held on a map of hexes or diamonds: the neighbour that way (tilemap.gd's toward_key)
		target = _map().toward_key(cell(), dir, facing.x)
		if target == cell():
			return
	_routed = false
	var across := signi(int(_centre(target).x - _centre(cell()).x))
	facing = dir if across == 0 else Vector2i(across, dir.y)
	if _sprite != null and facing.x != 0:
		_sprite.flip_h = facing.x < 0
	var thing := _thing_in(target)
	var past := _beyond(cell(), target)
	# a pushable thing with a free cell beyond: both go on, and the step is a touch
	if thing != null and thing.get("pushable") == true and not _wall(past) and _thing_in(past) == null:
		_pushed = thing
		_pushed_from = thing.position
		_pushed_to = _centre(past)
		Q.event("push", {"who": String(name), "what": Q.who(thing), "to": [past.x, past.y]})
		_touch_handlers(thing)
		_step(target)
		return
	if thing != null:
		Q.touched(self, thing)
		if thing.is_queued_for_deletion():
			return   # picked up, or a door it opened: the next step goes in
		if _touch_handlers(thing):
			return
	if thing != null or _wall(target):
		Q.event("bump", {"who": String(name), "at": [target.x, target.y]})
		_bumping = step_frames
		_play("bump")
		return
	_step(target)


# The way it is asked to go this tick: the keys held (one of the overrides is the pointer's).
func _wanted() -> Vector2i:
	var dir := Vector2i(
		int(Q.held(_a("right"))) - int(Q.held(_a("left"))),
		int(Q.held(_a("down"))) - int(Q.held(_a("up"))))
	if dir != Vector2i.ZERO and dir.x != 0 and dir.y != 0 and not diagonal:
		dir.y = 0   # the way across wins
	return dir


func _step(target: Vector2i) -> void:
	_from = position
	_to = _centre(target)
	Q.event("step", {"who": String(name), "to": [target.x, target.y]})
	_moving = step_frames
	_play("walk")


# The character's qg:on-collision handlers with the tag of what it steps into; whether any ran.
func _touch_handlers(thing: Node) -> bool:
	var fired := false
	if thing.has_method("quantum_tag"):
		for h in _handlers:
			if h["with"] == thing.quantum_tag() and _scene.has_method(h["handler"]):
				Q.event("touch", {"who": String(name), "with": thing.quantum_tag()})
				_scene.call(h["handler"], self, thing)
				fired = true
	return fired


# In a new cell: the zones there are touched (a goal, a trap, a sign), in their names' order.
func _arrive() -> void:
	var query := PhysicsPointQueryParameters2D.new()
	query.position = global_position
	query.collide_with_areas = true
	query.collide_with_bodies = false
	var zones := []
	for hit in get_world_2d().direct_space_state.intersect_point(query, 32):
		var area = hit["collider"]
		if area is Area2D and area.has_method("quantum_tag") and not area.is_in_group("q_thing") \
				and area.get_parent() == _scene:
			zones.append(area)
	zones.sort_custom(func(a, b): return String(a.name) < String(b.name))
	for zone in zones:
		_touch_handlers(zone)


func _play(anim: String) -> void:
	if animator == null:
		return
	if animator.has(anim):
		animator.play(anim)
	elif animator.has("idle"):
		animator.play("idle")


# The input action of this player: "up" for player 1, "p2_up" for player 2.
func _a(action: String) -> String:
	return action if player == 1 else "p%d_%s" % [player, action]
