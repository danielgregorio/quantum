extends TileMapLayer
## Loads tile data from res://tile_map.json and populates the TileMapLayer at runtime.

func _ready():
	var file = FileAccess.open("res://tile_map.json", FileAccess.READ)
	if not file:
		push_error("tilemap_loader: Could not open res://tile_map.json")
		return
	var json_text = file.get_as_text()
	file.close()

	var json = JSON.parse_string(json_text)
	if json == null:
		push_error("tilemap_loader: Failed to parse res://tile_map.json")
		return

	var grid = json["grid"]
	var count = 0
	for row_idx in grid.size():
		var row = grid[row_idx]
		for col_idx in row.size():
			var cell = row[col_idx]
			if cell != null:
				var atlas_x = int(cell[0])
				var atlas_y = int(cell[1])
				set_cell(Vector2i(col_idx, row_idx), 0, Vector2i(atlas_x, atlas_y))
				count += 1

	print("TileMapLayer: loaded ", count, " tiles")
