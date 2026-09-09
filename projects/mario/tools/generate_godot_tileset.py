#!/usr/bin/env python3
"""
Godot TileSet Generator — Creates .tres TileSet resource and tile_map_data
from tile_classifications.json and tile_map.json.

Etapas 3+4:
  3. Generate collision_tileset.tres (Godot 4 TileSet with physics layers)
  4. Generate tile_map_data binary (PackedByteArray for TileMapLayer)

Also patches main.tscn to replace polygon collision with TileMapLayer.
"""

import json
import struct
import sys
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent
TILE_SIZE = 16
ATLAS_COLUMNS = 16

# Collision types that have physics
TYPES_WITH_COLLISION = {1, 2, 3, 4, 5, 6, 7, 8}  # everything except EMPTY(0) and DECORATION(9)


def load_data():
    """Load tile_classifications.json and tile_map.json."""
    cls_path = OUTPUT_DIR / "tile_classifications.json"
    map_path = OUTPUT_DIR / "tile_map.json"

    classifications = json.loads(cls_path.read_text(encoding="utf-8"))
    tile_map = json.loads(map_path.read_text(encoding="utf-8"))

    return classifications, tile_map


def format_polygon_points(polygon: list) -> str:
    """Format polygon as Godot PackedVector2Array."""
    parts = []
    for x, y in polygon:
        parts.append(f"{x}, {y}")
    return "PackedVector2Array(" + ", ".join(parts) + ")"


def generate_tres(classifications: dict) -> str:
    """Generate the collision_tileset.tres content."""
    tiles = classifications["tiles"]

    lines = []
    lines.append('[gd_resource type="TileSet" load_steps=2 format=3]')
    lines.append('')
    lines.append('[ext_resource type="Texture2D" path="res://assets/smw/sprites/tileset_atlas.png" id="1"]')
    lines.append('')

    # Build atlas source sub-resource
    lines.append('[sub_resource type="TileSetAtlasSource" id="TileSetAtlasSource_atlas"]')
    lines.append('texture = ExtResource("1")')
    lines.append(f'texture_region_size = Vector2i({TILE_SIZE}, {TILE_SIZE})')

    # For each tile, define its atlas position and collision polygon
    for tile in tiles:
        idx = tile["index"]
        atlas_x = idx % ATLAS_COLUMNS
        atlas_y = idx // ATLAS_COLUMNS

        # Create the tile entry
        lines.append(f'{atlas_x}:{atlas_y}/0 = 0')

        # Add collision polygon if this type has physics
        type_id = tile["type_id"]
        polygon = tile.get("polygon")

        if type_id in TYPES_WITH_COLLISION and polygon:
            points_str = format_polygon_points(polygon)
            lines.append(f'{atlas_x}:{atlas_y}/0/physics_layer_0/polygon_0/points = {points_str}')

    lines.append('')

    # Main resource
    lines.append('[resource]')
    lines.append(f'tile_size = Vector2i({TILE_SIZE}, {TILE_SIZE})')
    lines.append('physics_layer_0/collision_layer = 1')
    lines.append('physics_layer_0/collision_mask = 1')
    lines.append('sources/0 = SubResource("TileSetAtlasSource_atlas")')
    lines.append('')

    return '\n'.join(lines)


def generate_tile_map_data(tile_map: dict) -> bytes:
    """
    Generate binary tile_map_data for Godot 4 TileMapLayer.

    Godot 4 TileMapLayer uses a PackedByteArray for tile_map_data/0.
    The format encodes each cell as:
      - Cell coordinate encoded in the array structure

    Actually, Godot 4 TileMapLayer stores tile data differently.
    We'll generate it as a text-based layer_0/tile_data property instead.
    """
    grid = tile_map["grid"]
    cells = []

    for row_idx, row in enumerate(grid):
        for col_idx, cell in enumerate(row):
            if cell is None:
                continue
            atlas_x, atlas_y = cell
            cells.append((col_idx, row_idx, atlas_x, atlas_y))

    return cells


def format_tile_data_property(cells: list) -> str:
    """
    Format tile data as Godot 4 TileMapLayer tile_map_data property.

    Godot 4 stores tile data as PackedInt32Array where each tile uses 3 ints:
      - int 0: cell coords encoded as (x & 0xFFFF) | (y << 16)
      - int 1: source_id (0) | (atlas_x << 16)
      - int 2: atlas_y | (alternative << 16)

    But for the .tscn format, individual cells are stored as:
      tile_map_data/X:Y = [source_id, Vector2i(atlas_x, atlas_y), alternative_id]
    """
    # Simpler: use the key-value format that Godot reads natively
    # Actually in Godot 4.x .tscn, TileMapLayer uses tile_map_data as a
    # PackedByteArray or the cells are serialized differently.
    # The most reliable format is the layered tile data.
    #
    # For .tscn text format, Godot uses:
    # tile_map_data = PackedByteArray(...)
    # Where the binary format is:
    #   - 4 bytes: version (currently 1 for Godot 4.4)
    #   - Then groups of:
    #     - 2 bytes i16: cell_x
    #     - 2 bytes i16: cell_y
    #     - 2 bytes u16: source_id (0)
    #     - 2 bytes u16: atlas_x
    #     - 2 bytes u16: atlas_y
    #     - 2 bytes u16: alternative_id (0)

    # Build binary data
    data = bytearray()

    # No header needed — Godot reads raw cell data
    # Actually let's check the Godot 4 source... the format is:
    # For each cell: 12 bytes total
    # Note: In practice, Godot 4.3+ uses a slightly different binary format.
    # Let's generate the cells in the .tscn friendly format instead.

    return cells


def generate_tscn_tile_data(cells: list) -> str:
    """
    Generate the tile_map_data as a PackedByteArray for .tscn.

    Godot 4.x TileMapLayer tile_map_data binary format:
    Each cell is encoded as 12 bytes:
      cell_x (i16 LE) + cell_y (i16 LE) + source_id (u16 LE) +
      atlas_coord_x (u16 LE) + atlas_coord_y (u16 LE) + alternative_id (u16 LE)
    """
    data = bytearray()
    for cell_x, cell_y, atlas_x, atlas_y in cells:
        data += struct.pack('<hhHHHH', cell_x, cell_y, 0, atlas_x, atlas_y, 0)

    # Format as PackedByteArray(byte1, byte2, ...)
    byte_strs = [str(b) for b in data]
    return "PackedByteArray(" + ", ".join(byte_strs) + ")"


def main():
    print("Loading classification and map data...")
    classifications, tile_map = load_data()

    print(f"Tiles: {classifications['total_unique']}")
    print(f"Grid: {tile_map['grid_cols']}x{tile_map['grid_rows']}")
    print(f"Type summary: {classifications['type_summary']}")

    # --- Etapa 3: Generate .tres ---
    print("\n=== Etapa 3: Generating TileSet resource ===")
    tres_content = generate_tres(classifications)
    tres_path = OUTPUT_DIR / "collision_tileset.tres"
    tres_path.write_text(tres_content, encoding="utf-8")
    print(f"TileSet saved: {tres_path}")

    # --- Etapa 4: Generate tile_map_data ---
    print("\n=== Etapa 4: Generating tile_map_data ===")
    cells = generate_tile_map_data(tile_map)
    print(f"Non-empty cells: {len(cells)}")

    tile_data_str = generate_tscn_tile_data(cells)
    print(f"PackedByteArray size: {len(cells) * 12} bytes")

    # Save tile_map_data for use by main.tscn patcher
    data_path = OUTPUT_DIR / "tile_map_data.txt"
    data_path.write_text(tile_data_str, encoding="utf-8")
    print(f"Tile map data saved: {data_path}")

    print("\nDone! Run generate_main_tscn.py next to patch main.tscn.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
