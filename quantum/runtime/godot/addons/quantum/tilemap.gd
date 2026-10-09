extends TileMapLayer
# The level from CSV rows: 0 is empty, n is tile n-1 of the tileset (left
# to right, top to bottom). With collision, every placed tile is a solid
# square — the tile is the unit of the world.

var columns: int = 0
var rows_count: int = 0
var tile: int = 16


static func build(spec: Dictionary, sheet: Dictionary, texture_of: Callable) -> TileMapLayer:
	var layer = load("res://addons/quantum/tilemap.gd").new()
	layer.name = "Tilemap"
	var size := int(sheet["tile"])
	layer.tile = size
	var texture: Texture2D = texture_of.call(sheet)
	var set := TileSet.new()
	set.tile_size = Vector2i(size, size)
	var collision: bool = spec.get("collision", false)
	if collision:
		set.add_physics_layer()
	var source := TileSetAtlasSource.new()
	source.texture = texture
	source.texture_region_size = Vector2i(size, size)
	var source_id := set.add_source(source)
	layer.tile_set = set
	var per_row := maxi(1, int(texture.get_width()) / size)
	var rows: Array = spec["rows"]
	layer.rows_count = rows.size()
	layer.columns = rows[0].size() if rows.size() > 0 else 0
	var created := {}
	var half := size / 2.0
	for y in rows.size():
		var row: Array = rows[y]
		for x in row.size():
			var n := int(row[x])
			if n <= 0:
				continue
			var coords := Vector2i((n - 1) % per_row, (n - 1) / per_row)
			if not created.has(coords):
				source.create_tile(coords)
				if collision:
					var data := source.get_tile_data(coords, 0)
					data.add_collision_polygon(0)
					data.set_collision_polygon_points(0, 0, PackedVector2Array([
						Vector2(-half, -half), Vector2(half, -half),
						Vector2(half, half), Vector2(-half, half)]))
				created[coords] = true
			layer.set_cell(Vector2i(x, y), source_id, coords)
	return layer


func pixel_size() -> Vector2:
	return Vector2(columns * tile, rows_count * tile)
