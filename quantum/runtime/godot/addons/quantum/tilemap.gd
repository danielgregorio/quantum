extends Node2D
# The level from tile rows: 0 is empty, n is tile n-1 of the tileset (left
# to right, top to bottom), -n the same tile flipped left to right. Each
# layer is a TileMapLayer; a layer with collision makes every placed tile a
# solid square — the tile is the unit of the world — unless the tileset's
# qg:tile gives that tile a shape of its own (a lower top, a slope, a ledge
# to jump through), or none.

var columns: int = 0
var rows_count: int = 0
var tile: int = 16


static func build(spec: Dictionary, sheet: Dictionary, texture_of: Callable) -> Node2D:
	var map = load("res://addons/quantum/tilemap.gd").new()
	map.name = "Tilemap"
	map.process_physics_priority = -100   # first in a tick: the cells set in the last one take their shapes
	var size := int(sheet["tile"][0])
	map.tile = size
	var texture: Texture2D = texture_of.call(sheet)
	map._per_row = maxi(1, int(texture.get_width()) / size)
	map._shapes = sheet.get("tiles", {})
	for layer_spec in spec["layers"]:
		var layer := TileMapLayer.new()
		layer.name = layer_spec.get("name", "layer")
		var set := TileSet.new()
		set.tile_size = Vector2i(size, size)
		var collision: bool = layer_spec.get("collision", false)
		if collision:
			set.add_physics_layer()
		var source := TileSetAtlasSource.new()
		source.texture = texture
		source.texture_region_size = Vector2i(size, size)
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
	_unshaped.clear()
var changed: Dictionary = {}   # "col,row" (and ",layer" past the first) -> the tile a qg:set-tile put there


# Puts tile n (1 is the tileset's first; -n the same flipped left to right; 0
# nothing) in a cell of a layer. A tile of a layer with collision is a solid
# square, unless the tileset's qg:tile gives that tile a shape of its own, or none.
func _place(layer: TileMapLayer, cell: Vector2i, n: int) -> void:
	if n == 0:
		layer.erase_cell(cell)
		return
	var flip := n < 0
	n = absi(n)
	var coords := Vector2i((n - 1) % _per_row, (n - 1) / _per_row)
	var source: TileSetAtlasSource = layer.tile_set.get_source(layer.tile_set.get_source_id(0))
	if not source.has_tile(coords):
		source.create_tile(coords)
		var frame := str(n - 1)
		var half := tile / 2.0
		if layer.get_meta("q_collision", false) and not (_shapes.has(frame) and _shapes[frame]["shape"] == null):
			var data := source.get_tile_data(coords, 0)
			var points := PackedVector2Array([
				Vector2(-half, -half), Vector2(half, -half),
				Vector2(half, half), Vector2(-half, half)])
			if _shapes.has(frame):
				# from the tile's top-left corner, as the .q gives them, to its centre
				points = PackedVector2Array()
				for p in _shapes[frame]["shape"]:
					points.append(Vector2(float(p[0]) - half, float(p[1]) - half))
			data.add_collision_polygon(0)
			data.set_collision_polygon_points(0, 0, points)
			if _shapes.has(frame) and _shapes[frame].get("one_way", false):
				data.set_collision_polygon_one_way(0, 0, true)
	# a flipped tile: the transform flags of the alternative id; Godot flips its shape too
	layer.set_cell(cell, layer.tile_set.get_source_id(0), coords,
		TileSetAtlasSource.TRANSFORM_FLIP_H if flip else 0)


# qg:set-tile: a cell of a layer (by name; the first with collision, else the
# first, when none is given) gets tile n, at once; its collision, at the start
# of the next tick (_physics_process), so that tick sees it on every peer,
# however many ticks a frame runs.
func set_tile(col: int, row: int, n: int, layer_name: String = "") -> void:
	var layer := _layer(layer_name)
	if layer == null or col < 0 or row < 0 or col >= columns or row >= rows_count:
		return
	_place(layer, Vector2i(col, row), n)
	if not _unshaped.has(layer):
		_unshaped.append(layer)
	var key := "%d,%d" % [col, row]
	if layer != _layer(""):
		key += "," + String(layer.name)
	changed[key] = n
	_blocked = null   # the free cells are found again (ai="pathfind")


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
		var n := c.y * _per_row + c.x + 1
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
	return Vector2(columns * tile, rows_count * tile)


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


func cell_of(p: Vector2) -> Vector2i:
	return Vector2i(floori((p.x - position.x) / tile), floori((p.y - position.y) / tile))


func centre_of(cell: Vector2i) -> Vector2:
	return position + Vector2((cell.x + 0.5) * tile, (cell.y + 0.5) * tile)


const _STEPS := [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]


# The cells from `from` to `to`, shortest first found over the free cells
# (breadth first, the neighbours always in the same order: the same way on
# every peer and in every replay); [] when there is none.
func path(from: Vector2i, to: Vector2i, limit: int = 4096) -> Array:
	var walls := blocked()
	if from == to:
		return [to]
	var came := {from: from}
	var todo: Array = [from]
	var head := 0
	while head < todo.size() and head < limit:
		var at: Vector2i = todo[head]
		head += 1
		for step in _STEPS:
			var next: Vector2i = at + step
			if came.has(next) or walls.has(next):
				continue
			if next.x < 0 or next.y < 0 or next.x >= columns or next.y >= rows_count:
				continue
			came[next] = at
			if next == to:
				var out := [next]
				while out[0] != from:
					out.push_front(came[out[0]])
				return out
			todo.append(next)
	return []
