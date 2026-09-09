#!/usr/bin/env python3
"""
Patches main.tscn to replace polygon collision system with TileMapLayer.

Removes:
  - level-bg (Sprite2D) — replaced by TileMapLayer visual
  - ground-main (StaticBody2D) — replaced by solid tiles
  - terrain_* nodes (StaticBody2D + CollisionPolygon2D)
  - terrain_float_* nodes
  - terrain_pipe nodes
  - SubResource id="1" (ground-main rectangle)
  - ExtResource id="4" (yoshi-island-1.png, no longer needed directly)

Adds:
  - ExtResource for collision_tileset.tres
  - TileMapLayer node with tile_map_data
"""

import re
import sys
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent


def main():
    tscn_path = OUTPUT_DIR / "main.tscn"
    tile_data_path = OUTPUT_DIR / "tile_map_data.txt"

    tscn = tscn_path.read_text(encoding="utf-8")
    tile_map_data = tile_data_path.read_text(encoding="utf-8").strip()

    lines = tscn.split("\n")
    new_lines = []

    # Track which sections to skip
    skip_until_next_section = False
    # Names of nodes to remove (and their children)
    remove_nodes = set()

    # First pass: identify terrain node names
    for line in lines:
        m = re.match(r'\[node name="(terrain_\w*|terrain_pipe|ground-main|level-bg)" ', line)
        if m:
            remove_nodes.add(m.group(1))

    # Determine which ext_resource IDs to add
    # Find the highest ext_resource id
    max_ext_id = 0
    for line in lines:
        m = re.match(r'\[ext_resource .* id="(\d+)"\]', line)
        if m:
            max_ext_id = max(max_ext_id, int(m.group(1)))

    tileset_ext_id = str(max_ext_id + 1)

    print(f"Nodes to remove: {sorted(remove_nodes)}")
    print(f"TileSet ext_resource id: {tileset_ext_id}")

    # Second pass: rebuild the file
    i = 0
    while i < len(lines):
        line = lines[i]

        # Skip sub_resource id="1" (ground-main rectangle)
        if line.startswith('[sub_resource type="RectangleShape2D" id="1"]'):
            # Skip this sub_resource block (2 lines: header + size)
            i += 1
            while i < len(lines) and lines[i].strip() and not lines[i].startswith("["):
                i += 1
            # Skip trailing blank line
            if i < len(lines) and lines[i].strip() == "":
                i += 1
            continue

        # Remove ext_resource id="4" (yoshi-island-1.png — no longer used directly)
        if 'id="4"' in line and "yoshi-island-1.png" in line:
            i += 1
            continue

        # After last ext_resource, inject TileSet ext_resource
        if line.startswith("[ext_resource") and "id=\"" + str(max_ext_id) + "\"" in line:
            new_lines.append(line)
            new_lines.append(f'[ext_resource type="TileSet" path="res://collision_tileset.tres" id="{tileset_ext_id}"]')
            i += 1
            continue

        # Check if this is a node to remove
        node_match = re.match(r'\[node name="([^"]+)"', line)
        if node_match:
            node_name = node_match.group(1)

            # Check if it's a removed node or child of removed node
            is_removed = node_name in remove_nodes
            if not is_removed:
                # Check parent path for children of removed nodes
                parent_match = re.search(r'parent="([^"]*)"', line)
                if parent_match:
                    parent = parent_match.group(1)
                    # Direct child: parent="ground-main" or parent="terrain_0" etc
                    if parent in remove_nodes:
                        is_removed = True
                    # Check if parent path contains a removed node
                    for rn in remove_nodes:
                        if parent.startswith(rn + "/") or parent == rn:
                            is_removed = True
                            break

            if is_removed:
                # Skip this node block entirely
                i += 1
                while i < len(lines) and lines[i].strip() and not lines[i].startswith("["):
                    i += 1
                # Skip trailing blank line
                if i < len(lines) and lines[i].strip() == "":
                    i += 1
                continue

        new_lines.append(line)
        i += 1

    # Now inject the TileMapLayer node right after the Background node block
    # Find where Background ends and insert TileMapLayer + preloads
    final_lines = []
    for i, line in enumerate(new_lines):
        final_lines.append(line)

        # After the _preload_death node block, insert TileMapLayer
        if '[node name="_preload_death"' in line:
            # Let the _preload_death block finish (next lines until next [node)
            pass

    # Actually, let's do it differently — find the right insertion point
    # Insert TileMapLayer after _preload_death block, replacing where level-bg was
    result_lines = []
    inserted_tilemap = False

    for i, line in enumerate(new_lines):
        result_lines.append(line)

        # After the goal node's position line, that's the right spot...
        # Actually, insert right where level-bg used to be (after _preload_death block)
        if not inserted_tilemap and '[node name="_preload_death"' in line:
            # Let the rest of _preload_death properties be added first
            # Look ahead to find the end of this block
            j = i + 1
            while j < len(new_lines) and new_lines[j].strip() and not new_lines[j].startswith("["):
                result_lines.append(new_lines[j])
                j += 1
            # Add blank line then TileMapLayer
            result_lines.append("")
            result_lines.append(f'[node name="level-tilemap" type="TileMapLayer" parent="."]')
            result_lines.append(f'tile_set = ExtResource("{tileset_ext_id}")')
            result_lines.append(f'tile_map_data = {tile_map_data}')
            result_lines.append("")
            inserted_tilemap = True
            # Skip the lines we already added
            # Remove the duplicate lines that will be added by the main loop
            # We need to mark them as consumed
            # Let's use a different approach...

    # The approach above is getting complex. Let me use a cleaner method.
    # Rebuild completely.

    output = []
    i = 0
    inserted_tilemap = False
    lines = new_lines

    while i < len(lines):
        line = lines[i]
        output.append(line)

        # After _preload_death block, insert TileMapLayer
        if not inserted_tilemap and '[node name="_preload_death"' in line:
            i += 1
            # Copy rest of _preload_death properties
            while i < len(lines) and lines[i].strip() and not lines[i].startswith("["):
                output.append(lines[i])
                i += 1
            # Add TileMapLayer
            output.append("")
            output.append(f'[node name="level-tilemap" type="TileMapLayer" parent="."]')
            output.append(f'tile_set = ExtResource("{tileset_ext_id}")')
            output.append(f'tile_map_data = {tile_map_data}')
            inserted_tilemap = True
            continue

        i += 1

    result = "\n".join(output)

    # Write back
    tscn_path.write_text(result, encoding="utf-8")
    print(f"Patched: {tscn_path}")

    # Verify
    with open(tscn_path, "r", encoding="utf-8") as f:
        content = f.read()
    has_tilemap = "level-tilemap" in content
    has_no_terrain = "terrain_0" not in content
    has_no_ground = "ground-main" not in content
    has_no_levelbg = "level-bg" not in content
    has_tileset = "collision_tileset.tres" in content

    print(f"  TileMapLayer present: {has_tilemap}")
    print(f"  terrain_0 removed: {has_no_terrain}")
    print(f"  ground-main removed: {has_no_ground}")
    print(f"  level-bg removed: {has_no_levelbg}")
    print(f"  TileSet reference: {has_tileset}")

    if all([has_tilemap, has_no_terrain, has_no_ground, has_no_levelbg, has_tileset]):
        print("\nAll checks passed!")
    else:
        print("\nWARNING: Some checks failed!")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
