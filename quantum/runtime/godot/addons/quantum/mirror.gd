extends Node2D
# qg:mirror: a view of the world (qg:connect), drawn. Each entity the player sees in it is an instance of the
# prefab of its kind, named for its id, whose `me` reads the entity's fields (Q.wf): it comes when the entity comes
# into the view and goes when it leaves; a step to the next tile is walked in the time the world gives a step of
# its kind (its speed=), a move farther is a jump. The world's tiles are the scene's tilemap's (16 pixels without
# one). Only seen: the world is the server's.

var view := ""
var scene_node: Node = null
var game: Dictionary = {}
var step_seconds: Dictionary = {}   # a kind -> the seconds a step takes in the world
var nodes: Dictionary = {}          # an entity's id -> its node
var _walk: Dictionary = {}          # an entity's id -> [from, to, frame, frames]
var _at: Dictionary = {}            # an entity's id -> the tile it was last drawn at


func setup(spec: Dictionary, scene: Node, game_: Dictionary) -> void:
	view = str(spec["view"])
	name = "Mirror_" + view
	scene_node = scene
	game = game_
	step_seconds = game.get("world", {}).get("kinds", {})
	process_physics_priority = -10      # before the scene's things and its camera


func pixel_of(tile) -> Vector2:
	var x := int(tile.get("x", 0))
	var y := int(tile.get("y", 0))
	var map = scene_node.get_node_or_null("Tilemap") if scene_node != null else null
	if map != null:
		return map.centre_of(Vector2i(x, y))
	return Vector2((x + 0.5) * 16.0, (y + 0.5) * 16.0)


func node_of(id) -> Node:
	var n = nodes.get(str(id))
	return n if n != null and is_instance_valid(n) else null


func _physics_process(_delta: float) -> void:
	var world = Q.world
	if world == null:
		return
	var seen: Dictionary = world.views.get(view, {})
	for id in nodes.keys():
		if not seen.has(id) or not is_instance_valid(nodes[id]):
			_drop(id)
	for id in seen:
		var e: Dictionary = seen[id]
		var shown = world.shown(id)       # the player's own: where its guessed step is (predict)
		if shown == null:
			if nodes.has(id):
				_drop(id)                # nowhere: not drawn
			continue
		var tile: Vector2i = shown
		var at := {"x": tile.x, "y": tile.y}
		if not nodes.has(id):
			_make(id, e, tile)
			continue
		var node: Node2D = nodes[id]
		node.set_meta("q_entity", e)
		if _at.get(id) != tile:
			var before: Vector2i = _at[id]
			_at[id] = tile
			var far := maxi(absi(tile.x - before.x), absi(tile.y - before.y))
			var frames := roundi(float(step_seconds.get(str(e.get("kind", "")), 0.25)) * Engine.physics_ticks_per_second)
			if far == 1 and frames > 1:
				_walk[id] = [node.position, pixel_of(at), 0, frames]
			else:
				_walk.erase(id)
				node.position = pixel_of(at)
		if _walk.has(id):
			var w: Array = _walk[id]
			w[2] += 1
			node.position = (w[0] as Vector2).lerp(w[1], minf(1.0, float(w[2]) / float(w[3])))
			if w[2] >= w[3]:
				_walk.erase(id)


func _make(id: String, e: Dictionary, tile: Vector2i) -> void:
	var kind := str(e.get("kind", ""))
	if not game.get("prefabs", {}).has(kind):
		return                           # the compiler saw a prefab for every kind of the world
	var node: Node2D = load("res://addons/quantum/scene_builder.gd").instance(game, scene_node, kind,
		pixel_of({"x": tile.x, "y": tile.y}))
	node.name = id.replace(":", "_").replace("/", "_").replace(".", "_").replace("@", "_").replace("%", "_")
	node.set_meta("q_entity", e)
	node.set_meta("q_entity_id", id)
	var looks = node.get_node_or_null("Looks")
	if looks != null:
		looks._update()                  # its labels and bars read the entity now, not a tick later
	nodes[id] = node
	_at[id] = tile
	if id == Q.world.you and scene_node != null:
		var cam = scene_node.get("q_camera")
		if cam != null and cam.has_meta("q_follow_me") and not node in cam.targets:
			cam.targets.append(node)     # qg:camera follow="me": the player's own entity, once it is seen
	Q.event("mirror", {"view": view, "id": id, "kind": kind, "enter": true})


func _drop(id: String) -> void:
	var node = nodes.get(id)
	nodes.erase(id)
	_walk.erase(id)
	_at.erase(id)
	if node != null and is_instance_valid(node):
		if scene_node != null:
			var cam = scene_node.get("q_camera")
			if cam != null and node in cam.targets:
				cam.targets.erase(node)
		if node.is_in_group("q_thing"):
			node.remove_from_group("q_thing")
		node.queue_free()
	Q.event("mirror", {"view": view, "id": id, "enter": false})


# what the play protocol sees of it: the entities drawn, where
func quantum_view() -> Dictionary:
	var items := []
	for id in nodes.keys():
		var n = nodes[id]
		if is_instance_valid(n):
			items.append({"id": id, "x": snappedf(n.position.x, 0.01), "y": snappedf(n.position.y, 0.01)})
	return {"kind": "mirror", "view": view, "items": items}
