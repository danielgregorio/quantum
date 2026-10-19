extends RefCounted
# What a character feels of the tiles about it, each tick: the kinds
# (qg:tile kind=) it is in, stands on and bumps, from the scene's tilemap;
# and its qg:on-tile handlers, run as it comes to touch a tile of their kind,
# and again each time their cooldown runs out while it still does.

var handlers: Array = []
var about := {"in": "", "under": "", "touching": []}
var _scene: Node = null
var _map: Node = null
var _was: Dictionary = {}    # handler -> it touched that kind last tick
var _next: Dictionary = {}   # handler -> the tick it may run again


func setup(spec: Dictionary, scene: Node) -> void:
	handlers = spec.get("on_tile", [])
	_scene = scene


func sense(body: Node2D, size: Vector2, tick: int) -> Dictionary:
	if _map == null and _scene != null:
		_map = _scene.get_node_or_null("Tilemap")
	if _map == null:
		return about
	about = _map.kinds_about(body.position, size)
	for h in handlers:
		var name_: String = h["handler"]
		var on: bool = about["touching"].has(h["kind"])
		var cooldown := int(h.get("cooldown", 0))
		if on and tick >= int(_next.get(name_, 0)) and (cooldown > 0 or not _was.get(name_, false)):
			_next[name_] = tick + cooldown
			Q.event("tile-touch", {"who": String(body.name), "kind": h["kind"]})
			if _scene.has_method(name_):
				_scene.call(name_, body, null)
		_was[name_] = on
	return about
