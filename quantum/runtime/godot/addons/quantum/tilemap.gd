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
	var size := int(sheet["tile"][0])
	map.tile = size
	var texture: Texture2D = texture_of.call(sheet)
	var per_row := maxi(1, int(texture.get_width()) / size)
	var half := size / 2.0
	var shapes: Dictionary = sheet.get("tiles", {})
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
		var source_id := set.add_source(source)
		layer.tile_set = set
		var rows: Array = layer_spec["rows"]
		map.rows_count = maxi(map.rows_count, rows.size())
		map.columns = maxi(map.columns, rows[0].size() if rows.size() > 0 else 0)
		var created := {}
		for y in rows.size():
			var row: Array = rows[y]
			for x in row.size():
				var n := int(row[x])
				if n == 0:
					continue
				var flip := n < 0
				n = absi(n)
				var coords := Vector2i((n - 1) % per_row, (n - 1) / per_row)
				if not created.has(coords):
					source.create_tile(coords)
					var frame := str(n - 1)
					if collision and not (shapes.has(frame) and shapes[frame]["shape"] == null):
						var data := source.get_tile_data(coords, 0)
						var points := PackedVector2Array([
							Vector2(-half, -half), Vector2(half, -half),
							Vector2(half, half), Vector2(-half, half)])
						if shapes.has(frame):
							# from the tile's top-left corner, as the .q gives them, to its centre
							points = PackedVector2Array()
							for p in shapes[frame]["shape"]:
								points.append(Vector2(float(p[0]) - half, float(p[1]) - half))
						data.add_collision_polygon(0)
						data.set_collision_polygon_points(0, 0, points)
						if shapes.has(frame) and shapes[frame].get("one_way", false):
							data.set_collision_polygon_one_way(0, 0, true)
					created[coords] = true
				# a flipped tile: the transform flags of the alternative id; Godot flips its shape too
				layer.set_cell(Vector2i(x, y), source_id, coords,
					TileSetAtlasSource.TRANSFORM_FLIP_H if flip else 0)
		map.add_child(layer)
	return map


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
