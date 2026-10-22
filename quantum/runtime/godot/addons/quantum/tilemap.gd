extends Node2D
# The level from tile rows: 0 is empty, n is tile n-1 of the tileset (left
# to right, top to bottom), -n the same tile flipped left to right, and n with
# Tiled's flag bits (29 across the diagonal, 30 upside down, 31 left to right)
# a tile turned as a Tiled map turns it. Each layer is a TileMapLayer, drawn
# from the scene's tileset or, in a Tiled map, one of its own; a layer with
# collision makes every placed tile a solid square — the tile is the unit of
# the world — unless the tileset's qg:tile gives that tile a shape of its own
# (a lower top, a slope, a ledge to jump through), or none. A qg:tile with
# frames= is animated: it and the frames after it in the sheet's row, in turn.
#
# A tileset with shape="hex" draws hexes with their points up, every other
# row half a hex to the right; shape="iso", diamonds, every other row half a
# diamond to the right. The rows of the .q are the rows seen, and a cell's
# neighbours, its middle and the cell at a point are Godot's for that shape.
# A step onto a tile costs its qg:tile cost= (1 when not given): the way a
# walker finds is the cheapest.

var columns: int = 0
var rows_count: int = 0
var tile: int = 16
var tile_height: int = 16
var shape: String = "square"


static func build(spec: Dictionary, sheet: Dictionary, texture_of: Callable, sheets: Dictionary = {}) -> Node2D:
	var map = load("res://addons/quantum/tilemap.gd").new()
	map.name = "Tilemap"
	map.process_physics_priority = -100   # first in a tick: the cells set in the last one take their shapes
	var size := int(sheet["tile"][0])
	map.tile = size
	map.tile_height = int(sheet["tile"][1])
	map.shape = str(sheet.get("shape", "square"))
	var texture: Texture2D = texture_of.call(sheet)
	map._per_row = maxi(1, int(texture.get_width()) / size)
	map._shapes = sheet.get("tiles", {})
	for layer_spec in spec["layers"]:
		var layer := TileMapLayer.new()
		layer.name = layer_spec.get("name", "layer")
		# a layer of a Tiled map may draw from another of the game's tilesets
		var own: Dictionary = sheets.get(layer_spec["tileset"], sheet) if layer_spec.get("tileset") != null else sheet
		var picture: Texture2D = texture if own == sheet else texture_of.call(own)
		layer.set_meta("q_per_row", maxi(1, int(picture.get_width()) / size))
		layer.set_meta("q_shapes", own.get("tiles", {}))
		var set := TileSet.new()
		set.tile_size = Vector2i(size, map.tile_height)
		if map.shape == "hex":
			set.tile_shape = TileSet.TILE_SHAPE_HEXAGON
			set.tile_offset_axis = TileSet.TILE_OFFSET_AXIS_HORIZONTAL   # points up; every other row half a hex on
		elif map.shape == "iso":
			set.tile_shape = TileSet.TILE_SHAPE_ISOMETRIC
		set.tile_layout = TileSet.TILE_LAYOUT_STACKED   # the rows of the .q are the rows seen
		var collision: bool = layer_spec.get("collision", false)
		if collision:
			set.add_physics_layer()
		var source := TileSetAtlasSource.new()
		source.texture = picture
		source.texture_region_size = Vector2i(size, map.tile_height)
		set.add_source(source)
		layer.tile_set = set
		layer.set_meta("q_collision", collision)
		map.add_child(layer)
		var rows: Array = layer_spec["rows"]
		map.rows_count = maxi(map.rows_count, rows.size())
		map.columns = maxi(map.columns, rows[0].size() if rows.size() > 0 else 0)
		for y in rows.size():
			var row: Array = rows[y]
			for x in row.size():
				var n := int(row[x])
				if n != 0:
					map._place(layer, Vector2i(x, y), n)
	if spec.get("shadows", false) and map.shape == "square":   # a dark scene (ambient=): the solid tiles stop the lights
		map._shadows = true
		map._occlude()
	return map


var _per_row := 1
var _shapes: Dictionary = {}
var _unshaped: Array = []   # layers with cells set whose collision is not made yet


# The collision of the cells set since the last tick, made before anything of
# this one moves. Not in set_tile itself: a qg:set-tile in a collision handler
# runs while the physics server flushes its queries, when bodies may not change;
# and not at the end of the frame, which runs many ticks while a rejoin catches up.
func _physics_process(_delta: float) -> void:
	for layer in _unshaped:
		layer.update_internals()
	if _shadows and not _unshaped.is_empty():
		_occlude()   # a wall opened (qg:set-tile) lets the light through
	_unshaped.clear()
var changed: Dictionary = {}   # "col,row" (and ",layer" past the first) -> the tile a qg:set-tile put there
var _first: Dictionary = {}    # the same keys -> the tile the level had there, for the rollback (q_load)


# Puts tile n (1 is the tileset's first; -n the same flipped left to right; 0
# nothing) in a cell of a layer. A tile of a layer with collision is a solid
# square, unless the tileset's qg:tile gives that tile a shape of its own, or none.
const TILED_ACROSS := 1 << 29
const TILED_UPSIDE := 1 << 30
const TILED_LEFT_RIGHT := 1 << 31


func _place(layer: TileMapLayer, cell: Vector2i, n: int) -> void:
	if n == 0:
		layer.erase_cell(cell)
		return
	# how it is turned: the transform flags of the alternative id; Godot turns its shape too
	var turned := 0
	if n < 0:
		turned = TileSetAtlasSource.TRANSFORM_FLIP_H
		n = -n
	elif n >= TILED_ACROSS:
		if n & TILED_LEFT_RIGHT:
			turned |= TileSetAtlasSource.TRANSFORM_FLIP_H
		if n & TILED_UPSIDE:
			turned |= TileSetAtlasSource.TRANSFORM_FLIP_V
		if n & TILED_ACROSS:
			turned |= TileSetAtlasSource.TRANSFORM_TRANSPOSE
		n &= TILED_ACROSS - 1
	var per_row: int = layer.get_meta("q_per_row", _per_row)
	var shapes: Dictionary = layer.get_meta("q_shapes", _shapes)
	var coords := Vector2i((n - 1) % per_row, (n - 1) / per_row)
	var source: TileSetAtlasSource = layer.tile_set.get_source(layer.tile_set.get_source_id(0))
	if not source.has_tile(coords):
		source.create_tile(coords)
		var frame := str(n - 1)
		var half := tile / 2.0
		var half_h := tile_height / 2.0
		if shapes.has(frame) and int(shapes[frame].get("frames", 1)) > 1:
			# an animated tile: it and the frames after it in the row, in turn (only seen)
			source.set_tile_animation_columns(coords, 0)
			source.set_tile_animation_frames_count(coords, mini(int(shapes[frame]["frames"]), per_row - coords.x))
			source.set_tile_animation_speed(coords, float(shapes[frame].get("fps", 4.0)))
		if layer.get_meta("q_collision", false) and not (shapes.has(frame) and shapes[frame]["shape"] == null):
			var data := source.get_tile_data(coords, 0)
			var points := PackedVector2Array([
				Vector2(-half, -half_h), Vector2(half, -half_h),
				Vector2(half, half_h), Vector2(-half, half_h)])
			if shape == "hex":
				points = PackedVector2Array([Vector2(0, -half_h), Vector2(half, -half_h / 2.0), Vector2(half, half_h / 2.0),
					Vector2(0, half_h), Vector2(-half, half_h / 2.0), Vector2(-half, -half_h / 2.0)])
			elif shape == "iso":
				points = PackedVector2Array([Vector2(0, -half_h), Vector2(half, 0), Vector2(0, half_h), Vector2(-half, 0)])
			if shapes.has(frame) and shapes[frame]["shape"] is Array:
				# from the tile's top-left corner, as the .q gives them, to its centre
				points = PackedVector2Array()
				for p in shapes[frame]["shape"]:
					points.append(Vector2(float(p[0]) - half, float(p[1]) - half_h))
			data.add_collision_polygon(0)
			data.set_collision_polygon_points(0, 0, points)
			if shapes.has(frame) and shapes[frame].get("one_way", false):
				data.set_collision_polygon_one_way(0, 0, true)
	layer.set_cell(cell, layer.tile_set.get_source_id(0), coords, turned)


# qg:set-tile: a cell of a layer (by name; the first with collision, else the
# first, when none is given) gets tile n, at once; its collision, at the start
# of the next tick (_physics_process), so that tick sees it on every peer,
# however many ticks a frame runs.
func set_tile(col: int, row: int, n: int, layer_name: String = "") -> void:
	var layer := _layer(layer_name)
	if layer == null or col < 0 or row < 0 or col >= columns or row >= rows_count:
		return
	var key := "%d,%d" % [col, row]
	if layer != _layer(""):
		key += "," + String(layer.name)
	if not _first.has(key):
		_first[key] = tile_at(col, row, String(layer.name))
	_place(layer, Vector2i(col, row), n)
	if not _unshaped.has(layer):
		_unshaped.append(layer)
	changed[key] = n
	_blocked = null   # the free cells are found again (ai="pathfind")


# For the rollback: the cells changed so far, and back to them — every cell
# changed now or then gets the tile it had then (the level's, if none).
func q_save() -> Dictionary:
	return {"changed": changed.duplicate()}


func q_load(d: Dictionary) -> void:
	var then: Dictionary = d["changed"]
	for key in changed.keys() + then.keys():
		var parts: PackedStringArray = String(key).split(",")
		var layer := _layer(parts[2] if parts.size() > 2 else "")
		if layer == null:
			continue
		_place(layer, Vector2i(int(parts[0]), int(parts[1])), int(then.get(key, _first.get(key, 0))))
		if not _unshaped.has(layer):
			_unshaped.append(layer)
	changed = then.duplicate()
	_blocked = null


# tile_at(): the tile in a cell (0: none), of the layer named, or the topmost that has one.
func tile_at(col: int, row: int, layer_name: String = "") -> int:
	var layers: Array = [_layer(layer_name)] if layer_name != "" else get_children()
	layers.reverse()
	for layer in layers:
		if not (layer is TileMapLayer):
			continue
		var cell := Vector2i(col, row)
		if layer.get_cell_source_id(cell) == -1:
			continue
		var c: Vector2i = layer.get_cell_atlas_coords(cell)
		var n := c.y * int(layer.get_meta("q_per_row", _per_row)) + c.x + 1
		return -n if layer.get_cell_alternative_tile(cell) & TileSetAtlasSource.TRANSFORM_FLIP_H else n
	return 0


func _layer(layer_name: String) -> TileMapLayer:
	var first: TileMapLayer = null
	for c in get_children():
		if not (c is TileMapLayer):
			continue
		if layer_name != "" and String(c.name) == layer_name:
			return c
		if layer_name == "" and c.get_meta("q_collision", false):
			return c
		if first == null:
			first = c
	return null if layer_name != "" else first


func pixel_size() -> Vector2:
	if shape == "hex":   # rows three quarters of a hex apart, every other one half a hex on
		return Vector2(columns * tile + tile / 2.0, (rows_count - 1) * tile_height * 0.75 + tile_height)
	if shape == "iso":   # rows half a diamond apart
		return Vector2(columns * tile + tile / 2.0, (rows_count - 1) * tile_height * 0.5 + tile_height)
	return Vector2(columns * tile, rows_count * tile)


# --- the shadows of the walls, in a dark scene ---

var _shadows := false
var _occluders: Node2D = null


# The edges between the solid cells and the rest, joined into lines, each a
# LightOccluder2D that stops only the light coming from inside the wall (cull
# mode): a light lights a wall's face, and the wall's far side casts its
# shadow. Not a polygon per tile, whose edges between two walls would cast
# shadows across the walls themselves. Only seen.
func _occlude() -> void:
	if _occluders != null:
		_occluders.free()
	_occluders = Node2D.new()
	_occluders.name = "Occluders"
	add_child(_occluders)
	var solid := blocked()
	# each solid cell's open edges, wound as its tile is (top left to right, right side down, ...)
	var sides := [[Vector2i(0, -1), Vector2(0, 0), Vector2(1, 0)], [Vector2i(1, 0), Vector2(1, 0), Vector2(1, 1)],
		[Vector2i(0, 1), Vector2(1, 1), Vector2(0, 1)], [Vector2i(-1, 0), Vector2(0, 1), Vector2(0, 0)]]
	for side in sides:
		var edges := {}   # its start -> its end, to join edges in a line
		for cell in solid.keys():
			if not solid.has(cell + side[0]):
				edges[(Vector2(cell) + side[1]) * tile] = (Vector2(cell) + side[2]) * tile
		for start in edges.keys():
			if edges.values().has(start):
				continue   # another edge ends here: the line starts before
			var end: Vector2 = edges[start]
			while edges.has(end):
				end = edges[end]
			var line := OccluderPolygon2D.new()
			line.closed = false
			line.cull_mode = OccluderPolygon2D.CULL_COUNTER_CLOCKWISE
			line.polygon = PackedVector2Array([start, end])
			var occluder := LightOccluder2D.new()
			occluder.occluder = line
			_occluders.add_child(occluder)


# --- the free cells, for ai="pathfind" ---

var _blocked = null   # Vector2i -> true: a cell holding a solid tile (computed once)


func blocked() -> Dictionary:
	if _blocked != null:
		return _blocked
	_blocked = {}
	for layer in get_children():
		if not (layer is TileMapLayer) or layer.tile_set == null or layer.tile_set.get_physics_layers_count() == 0:
			continue
		for cell in layer.get_used_cells():
			var data: TileData = layer.get_cell_tile_data(cell)
			if data != null and data.get_collision_polygons_count(0) > 0:
				_blocked[cell] = true
	return _blocked


# The kind (qg:tile kind=: ladder, water, ice, hurt) of the tile at a point
# of the scene, from the topmost layer that has one there; "" for none.
func kind_at(p: Vector2) -> String:
	var cell := cell_of(p)
	var layers := get_children()
	layers.reverse()
	for layer in layers:
		if not (layer is TileMapLayer) or layer.get_cell_source_id(cell) == -1:
			continue
		var coords: Vector2i = layer.get_cell_atlas_coords(cell)
		var frame := str(coords.x + coords.y * int(layer.get_meta("q_per_row", _per_row)))
		var shapes: Dictionary = layer.get_meta("q_shapes", _shapes)   # the layer's own tileset's (a Tiled map's)
		if shapes.has(frame) and shapes[frame].get("kind") != null:
			return str(shapes[frame]["kind"])
	return ""


# The kinds a body of `size` centred at `p` touches: what it is in (its
# middle), what it stands on (just under its feet), and what it bumps (just
# past each side and its head). {"in": kind, "under": kind, "touching": [kinds]}.
func kinds_about(p: Vector2, size: Vector2) -> Dictionary:
	var half := size / 2.0
	var in_ := kind_at(p)
	var under := kind_at(p + Vector2(0, half.y + 1))
	var touching := []
	for k in [in_, under, kind_at(p - Vector2(0, half.y + 1)), kind_at(p + Vector2(half.x + 1, 0)),
			kind_at(p - Vector2(half.x + 1, 0))]:
		if k != "" and not touching.has(k):
			touching.append(k)
	return {"in": in_, "under": under, "touching": touching}


func cell_of(p: Vector2) -> Vector2i:
	if shape != "square":
		return _first_layer().local_to_map(p - position)
	return Vector2i(floori((p.x - position.x) / tile), floori((p.y - position.y) / tile))


func centre_of(cell: Vector2i) -> Vector2:
	if shape != "square":
		return position + _first_layer().map_to_local(cell)
	return position + Vector2((cell.x + 0.5) * tile, (cell.y + 0.5) * tile)


func _first_layer() -> TileMapLayer:
	for c in get_children():
		if c is TileMapLayer:
			return c
	return null


func inside(c: Vector2i) -> bool:
	return c.x >= 0 and c.y >= 0 and c.x < columns and c.y < rows_count


const _STEPS := [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]


# The cells next to one, always in the same order: right, left, down, up on
# square tiles; Godot's six of a hex, or four of a diamond, round it.
func neighbours(c: Vector2i) -> Array:
	if shape == "square":
		return _STEPS.map(func(s): return c + s)
	return Array(_first_layer().get_surrounding_cells(c))


# The neighbour of a cell most in a direction on the screen: a key held on
# a hex map (up with the right side facing: up and to the right).
func toward(c: Vector2i, dir: Vector2) -> Vector2i:
	if shape == "square":
		return c + Vector2i(signi(int(dir.x)), signi(int(dir.y)))
	var best := c
	var most := 0.0
	var here := centre_of(c)
	for n in neighbours(c):
		var d := (centre_of(n) - here).normalized().dot(dir.normalized())
		if d > most + 0.001:
			best = n
			most = d
	return best


# The neighbour a key held goes to (a grid walker's): on hexes, left and
# right along the row, up and down to the side it faces; on diamonds, the
# keys turned an eighth (right is down and to the right, up is up and to the
# right), as an isometric game has them.
func toward_key(c: Vector2i, dir: Vector2i, facing_x: int) -> Vector2i:
	var way := Vector2(dir.x, dir.y)
	if shape == "hex" and dir.x == 0:
		way.x = 0.5 if facing_x >= 0 else -0.5
	elif shape == "iso":
		way = Vector2(dir.x - dir.y, dir.x + dir.y)
	return toward(c, way)


# The cell past `b`, coming from `a` (a crate pushed on).
func beyond(a: Vector2i, b: Vector2i) -> Vector2i:
	if shape == "square":
		return b + (b - a)
	return toward(b, centre_of(b) - centre_of(a))


func has_costs() -> bool:
	for layer in get_children():
		if layer is TileMapLayer:
			for t in layer.get_meta("q_shapes", _shapes).values():
				if t.has("cost"):
					return true
	return false


# What a step onto a cell costs (qg:tile cost=): the topmost layer's tile there that says, else 1.
func cost_at(c: Vector2i) -> int:
	var layers := get_children()
	layers.reverse()
	for layer in layers:
		if not (layer is TileMapLayer) or layer.get_cell_source_id(c) == -1:
			continue
		var coords: Vector2i = layer.get_cell_atlas_coords(c)
		var frame := str(coords.y * int(layer.get_meta("q_per_row", _per_row)) + coords.x)
		var shapes: Dictionary = layer.get_meta("q_shapes", _shapes)
		if shapes.has(frame) and shapes[frame].has("cost"):
			return int(shapes[frame]["cost"])
	return 1


# The cells from `from` to `to` by the cheapest way over the free cells (and
# not through the cells of `avoid`, but to one of them), each step costing
# the cell stepped onto; among ways as cheap, the first found, the
# neighbours always in the same order: the same way on every peer and in
# every replay. With every cost 1, it is the shortest, breadth first. []
# when there is none.
func path(from: Vector2i, to: Vector2i, limit: int = 4096, avoid: Dictionary = {}) -> Array:
	var walls := blocked()
	if from == to:
		return [to]
	var came := {from: from}
	var best := {from: 0}
	var buckets := {0: [from]}   # cost so far -> the cells reached for it, in the order found
	var cost := 0
	var left := 1
	var seen := 0
	while left > 0 and seen < limit:
		while not buckets.has(cost) or buckets[cost].is_empty():
			buckets.erase(cost)
			cost += 1
		var at: Vector2i = buckets[cost].pop_front()
		left -= 1
		if best[at] < cost:
			continue   # reached more cheaply since
		seen += 1
		if at == to:
			var out := [at]
			while out[0] != from:
				out.push_front(came[out[0]])
			return out
		for next in neighbours(at):
			if walls.has(next) or not inside(next) or (avoid.has(next) and next != to):
				continue
			var c: int = cost + cost_at(next)
			if c < int(best.get(next, 1 << 30)):
				best[next] = c
				came[next] = at
				if not buckets.has(c):
					buckets[c] = []
				buckets[c].append(next)
				left += 1
	return []


# What the cheapest way from one cell to another costs; -1 when there is none.
func path_cost(from: Vector2i, to: Vector2i, avoid: Dictionary = {}) -> int:
	var way := path(from, to, 4096, avoid)
	if way.is_empty():
		return -1
	var total := 0
	for i in range(1, way.size()):
		total += cost_at(way[i])
	return total
