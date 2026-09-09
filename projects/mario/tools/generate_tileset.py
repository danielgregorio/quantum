#!/usr/bin/env python3
"""
TileSet Generator — Extracts unique tiles from the level tilemap,
classifies collision types per tile (SMW-style tile-based collision).

Etapas 1+2:
  1. Read yoshi-island-1.png (5120x432), split into 16x16 grid, deduplicate
  2. Generate tileset_atlas.png, tile_map.json, tile_catalog.png
  3. Classify each tile's collision type (EMPTY, SOLID, SLOPE, CUSTOM, etc.)
  4. Output tile_classifications.json, tile_debug.png
"""

import json
import hashlib
import struct
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# --- Constants ---
TILE_SIZE = 16
TILEMAP_PATH = Path(__file__).parent / "assets/smw/sprites/yoshi-island-1.png"
OUTPUT_DIR = Path(__file__).parent
ATLAS_COLUMNS = 16  # tiles per row in atlas

# Collision type IDs
EMPTY = 0
SOLID = 1
SLOPE_R_45 = 2         # right-ascending 45°
SLOPE_L_45 = 3         # left-ascending 45°
SLOPE_R_GENTLE_LOW = 4  # right gentle, low half
SLOPE_R_GENTLE_HIGH = 5 # right gentle, high half
SLOPE_L_GENTLE_LOW = 6  # left gentle, low half
SLOPE_L_GENTLE_HIGH = 7 # left gentle, high half
CUSTOM = 8
DECORATION = 9          # visual only, no collision

# Manual overrides: tile index → collision type
# These override the automatic classification for tiles that are visually
# identifiable but hard to auto-classify correctly.
CLASSIFICATION_OVERRIDES = {
    # Bush/shrub tiles — walk-through decorations
    0: DECORATION,   # bush dome (left)
    1: DECORATION,   # bush dome (right)
    22: DECORATION,  # bush/grass transition left
    23: DECORATION,  # bush/grass transition center
    24: DECORATION,  # bush/grass transition right
    66: DECORATION,  # small vegetation detail
    67: DECORATION,  # small vegetation detail
    70: DECORATION,  # small vegetation detail
    # Hill back-face tiles — brown dirt edges behind slopes.
    # These must be SOLID walls so entities can't climb hills from behind.
    # Only the green grass surface (SLOPE_*) should be walkable.
    2: SOLID,    # hill edge, top-left corner rounded
    30: SOLID,   # hill edge, top-left corner rounded (variant)
    31: SOLID,   # hill edge, top-right corner rounded
    40: SOLID,   # hill edge, top-right corner rounded (variant)
    43: SOLID,   # hill structural tile, both top corners rounded
    72: SOLID,   # hill edge, top-left corner rounded (narrow variant)
}

# Tiles to EXCLUDE from the TileMapLayer entirely (rendered only via prefabs).
# These are the midway checkpoint gate tiles baked into yoshi-island-1.png.
EXCLUDED_TILES = {38, 39, 55, 56, 57, 65}

COLLISION_NAMES = {
    EMPTY: "EMPTY",
    SOLID: "SOLID",
    SLOPE_R_45: "SLOPE_R_45",
    SLOPE_L_45: "SLOPE_L_45",
    SLOPE_R_GENTLE_LOW: "SLOPE_R_GENTLE_LOW",
    SLOPE_R_GENTLE_HIGH: "SLOPE_R_GENTLE_HIGH",
    SLOPE_L_GENTLE_LOW: "SLOPE_L_GENTLE_LOW",
    SLOPE_L_GENTLE_HIGH: "SLOPE_L_GENTLE_HIGH",
    CUSTOM: "CUSTOM",
    DECORATION: "DECORATION",
}

# Collision polygons (relative to tile center 0,0; tile is 16x16 so half=8)
COLLISION_POLYGONS = {
    EMPTY: None,
    SOLID: [(-8, -8), (8, -8), (8, 8), (-8, 8)],
    SLOPE_R_45: [(-8, 8), (8, -8), (8, 8)],
    SLOPE_L_45: [(-8, -8), (8, 8), (-8, 8)],
    SLOPE_R_GENTLE_LOW: [(-8, 8), (8, 0), (8, 8)],
    SLOPE_R_GENTLE_HIGH: [(-8, 0), (8, -8), (8, 8), (-8, 8)],
    SLOPE_L_GENTLE_LOW: [(-8, 0), (8, 8), (-8, 8)],
    SLOPE_L_GENTLE_HIGH: [(-8, -8), (8, 0), (8, 8), (-8, 8)],
    DECORATION: None,
    # CUSTOM polygons are computed per-tile
}

# Debug colors per type (RGBA)
DEBUG_COLORS = {
    EMPTY: (0, 0, 0, 0),           # transparent
    SOLID: (255, 0, 0, 100),       # red
    SLOPE_R_45: (0, 255, 0, 100),  # green
    SLOPE_L_45: (0, 200, 0, 100),  # dark green
    SLOPE_R_GENTLE_LOW: (0, 255, 255, 100),   # cyan
    SLOPE_R_GENTLE_HIGH: (0, 200, 200, 100),  # dark cyan
    SLOPE_L_GENTLE_LOW: (255, 255, 0, 100),   # yellow
    SLOPE_L_GENTLE_HIGH: (200, 200, 0, 100),  # dark yellow
    CUSTOM: (255, 0, 255, 100),    # magenta
    DECORATION: (128, 128, 128, 60),  # grey
}


def tile_hash(tile_data: np.ndarray) -> str:
    """Hash a 16x16 RGBA tile for deduplication."""
    return hashlib.md5(tile_data.tobytes()).hexdigest()


def extract_tiles(img_array: np.ndarray):
    """
    Extract all tiles from the tilemap, deduplicate, build atlas mapping.

    Returns:
        unique_tiles: list of (hash, np.ndarray[16,16,4]) — unique tile images
        tile_map: list of lists [row][col] = (atlas_col, atlas_row) or None for empty
        hash_to_atlas: dict hash -> (atlas_col, atlas_row)
    """
    h, w, _ = img_array.shape
    cols = w // TILE_SIZE
    rows = h // TILE_SIZE

    print(f"Grid: {cols}x{rows} = {cols * rows} cells")

    unique_hashes = {}  # hash -> tile_data
    unique_order = []   # ordered list of hashes
    tile_map = []

    for row in range(rows):
        row_data = []
        for col in range(cols):
            y0 = row * TILE_SIZE
            x0 = col * TILE_SIZE
            tile_data = img_array[y0:y0+TILE_SIZE, x0:x0+TILE_SIZE]

            # Check if fully transparent
            alpha = tile_data[:, :, 3]
            if np.all(alpha == 0):
                row_data.append(None)
                continue

            h = tile_hash(tile_data)
            if h not in unique_hashes:
                unique_hashes[h] = tile_data.copy()
                unique_order.append(h)
            row_data.append(h)
        tile_map.append(row_data)

    # Build atlas mapping
    hash_to_atlas = {}
    for i, h in enumerate(unique_order):
        atlas_col = i % ATLAS_COLUMNS
        atlas_row = i // ATLAS_COLUMNS
        hash_to_atlas[h] = (atlas_col, atlas_row)

    unique_tiles = [(h, unique_hashes[h]) for h in unique_order]
    print(f"Unique tiles: {len(unique_tiles)}")

    return unique_tiles, tile_map, hash_to_atlas


def next_power_of_2(x: int) -> int:
    """Round up to the next power of 2."""
    p = 1
    while p < x:
        p *= 2
    return p


def generate_atlas(unique_tiles: list) -> Image.Image:
    """Generate atlas image from unique tiles. Padded to power-of-2 dimensions."""
    n = len(unique_tiles)
    atlas_rows = (n + ATLAS_COLUMNS - 1) // ATLAS_COLUMNS
    atlas_w = next_power_of_2(ATLAS_COLUMNS * TILE_SIZE)
    atlas_h = next_power_of_2(atlas_rows * TILE_SIZE)

    atlas = Image.new("RGBA", (atlas_w, atlas_h), (0, 0, 0, 0))

    for i, (h, tile_data) in enumerate(unique_tiles):
        col = i % ATLAS_COLUMNS
        row = i // ATLAS_COLUMNS
        tile_img = Image.fromarray(tile_data)
        atlas.paste(tile_img, (col * TILE_SIZE, row * TILE_SIZE))

    return atlas


def generate_catalog(unique_tiles: list) -> Image.Image:
    """Generate a debug catalog showing each tile with its index."""
    n = len(unique_tiles)
    cell_size = 48  # larger for readability
    cols = 16
    rows = (n + cols - 1) // cols

    catalog = Image.new("RGBA", (cols * cell_size, rows * cell_size), (40, 40, 40, 255))
    draw = ImageDraw.Draw(catalog)

    for i, (h, tile_data) in enumerate(unique_tiles):
        col = i % cols
        row = i // cols
        x0 = col * cell_size
        y0 = row * cell_size

        # Draw tile (scaled 2x)
        tile_img = Image.fromarray(tile_data)
        tile_scaled = tile_img.resize((32, 32), Image.NEAREST)
        catalog.paste(tile_scaled, (x0 + 8, y0 + 2), tile_scaled)

        # Draw index
        draw.text((x0 + 2, y0 + 35), str(i), fill=(255, 255, 255, 200))

    return catalog


def compute_surface_profile(tile_data: np.ndarray) -> list:
    """
    For each of the 16 columns, find the surface height (first opaque pixel
    scanning from TOP to BOTTOM). Returns list of 16 values:
      - None if column is fully transparent
      - 0..15 (y position of first opaque pixel from top)
    """
    alpha = tile_data[:, :, 3]
    profile = []
    for col in range(TILE_SIZE):
        col_alpha = alpha[:, col]
        opaque = np.where(col_alpha > 0)[0]
        if len(opaque) == 0:
            profile.append(None)
        else:
            profile.append(int(opaque[0]))
    return profile


def compute_opacity_ratio(tile_data: np.ndarray) -> float:
    """Fraction of opaque pixels in tile."""
    alpha = tile_data[:, :, 3]
    return float(np.count_nonzero(alpha > 0)) / (TILE_SIZE * TILE_SIZE)


def compute_bottom_connected(tile_data: np.ndarray) -> bool:
    """Check if the tile has opaque pixels in the bottom row."""
    alpha = tile_data[:, :, 3]
    return bool(np.any(alpha[-1, :] > 0))


def is_dome_profile(valid_cols: list) -> bool:
    """
    Detect dome-shaped tiles (bushes/shrubs).
    A dome has: both edges significantly lower (higher y) than a centered peak,
    with a gradual curve (not a flat top with just edge drops).
    """
    if len(valid_cols) < 8:
        return False

    surface_ys = [p for _, p in valid_cols]
    min_y = min(surface_ys)  # peak (lowest y = highest point)
    left_y = surface_ys[0]
    right_y = surface_ys[-1]

    # Both edges must be significantly below the peak
    min_edge_drop = 3
    if left_y <= min_y + min_edge_drop or right_y <= min_y + min_edge_drop:
        return False

    # Peak must be somewhere in the middle (not at an edge)
    peak_indices = [i for i, (_, p) in enumerate(valid_cols) if p == min_y]
    first_idx = 0
    last_idx = len(valid_cols) - 1
    quarter = max(1, (last_idx - first_idx) // 4)
    peak_in_center = any(quarter <= pi <= last_idx - quarter for pi in peak_indices)
    if not peak_in_center:
        return False

    # Surface must curve gradually (not flat top with sudden edge drops).
    # Count how many columns are at the peak level — if too many, it's a flat
    # structural tile, not a dome.
    at_peak = sum(1 for y in surface_ys if y <= min_y + 1)
    if at_peak > len(surface_ys) * 0.7:
        return False  # >70% flat at top = structural, not dome

    return True


def classify_tile(tile_data: np.ndarray, tile_idx: int) -> dict:
    """
    Classify a tile's collision type based on its alpha channel.

    Returns dict with:
      - type: collision type ID
      - polygon: list of (x,y) points or None
      - profile: surface profile (16 values)
      - excluded: True if tile should be excluded from TileMapLayer
    """
    profile = compute_surface_profile(tile_data)

    # Manual override takes priority
    if tile_idx in CLASSIFICATION_OVERRIDES:
        override_type = CLASSIFICATION_OVERRIDES[tile_idx]
        polygon = COLLISION_POLYGONS.get(override_type)
        return {"type": override_type, "polygon": polygon, "profile": profile,
                "excluded": tile_idx in EXCLUDED_TILES}

    # Excluded tiles (checkpoint etc.) are DECORATION with no collision
    if tile_idx in EXCLUDED_TILES:
        return {"type": DECORATION, "polygon": None, "profile": profile, "excluded": True}

    alpha = tile_data[:, :, 3]
    opacity = compute_opacity_ratio(tile_data)
    bottom_connected = compute_bottom_connected(tile_data)

    # Fully transparent
    if opacity == 0:
        return {"type": EMPTY, "polygon": None, "profile": profile}

    # Fully opaque (all 256 pixels)
    if opacity >= 0.98 and all(p == 0 for p in profile if p is not None):
        return {"type": SOLID, "polygon": COLLISION_POLYGONS[SOLID], "profile": profile}

    # Not bottom-connected → likely decoration (cloud, bush top, etc.)
    if not bottom_connected:
        return {"type": DECORATION, "polygon": None, "profile": profile}

    # Has content and is bottom-connected — analyze surface shape
    # Get valid columns (non-None profile entries)
    valid_cols = [(i, p) for i, p in enumerate(profile) if p is not None]
    if not valid_cols:
        return {"type": EMPTY, "polygon": None, "profile": profile}

    # Check if solid with flat top
    surface_values = [p for _, p in valid_cols]
    min_surface = min(surface_values)
    max_surface = max(surface_values)

    # Nearly solid (top is flat, within 2px tolerance)
    if max_surface - min_surface <= 2 and len(valid_cols) == TILE_SIZE and min_surface <= 2:
        return {"type": SOLID, "polygon": COLLISION_POLYGONS[SOLID], "profile": profile}

    # Check for dome-shaped tiles (bushes, shrubs) → DECORATION
    if is_dome_profile(valid_cols):
        return {"type": DECORATION, "polygon": None, "profile": profile}

    # Check for slope patterns
    slope_result = detect_slope(valid_cols, profile, alpha)
    if slope_result:
        return slope_result

    # Generate custom polygon from profile
    custom_poly = generate_custom_polygon(profile, alpha)
    return {"type": CUSTOM, "polygon": custom_poly, "profile": profile}


def detect_slope(valid_cols: list, profile: list, alpha: np.ndarray) -> dict | None:
    """
    Detect if tile matches a known slope pattern.
    Returns classification dict or None.
    """
    if len(valid_cols) < 8:
        return None

    # Extract surface heights for leftmost and rightmost
    cols_indices = [c for c, _ in valid_cols]
    surface_vals = [p for _, p in valid_cols]

    first_col = cols_indices[0]
    last_col = cols_indices[-1]

    # Only consider tiles that span most of the width
    if last_col - first_col < 10:
        return None

    left_height = surface_vals[0]   # surface y at leftmost column
    right_height = surface_vals[-1]  # surface y at rightmost column

    height_diff = right_height - left_height  # positive = goes DOWN left to right (slope_L)

    # Check linearity: how well do intermediate points fit a line?
    n = len(valid_cols)
    if n < 4:
        return None

    # Expected values for linear interpolation
    deviations = []
    for i, (col, surface_y) in enumerate(valid_cols):
        t = (col - first_col) / max(last_col - first_col, 1)
        expected = left_height + t * height_diff
        deviations.append(abs(surface_y - expected))

    avg_deviation = sum(deviations) / len(deviations)
    max_deviation = max(deviations)

    # Tight linearity check
    if avg_deviation > 2.0 or max_deviation > 4:
        return None

    total_drop = abs(height_diff)

    # 45° slope: surface goes from ~0 to ~15 or vice versa
    if total_drop >= 12:
        if height_diff < 0:
            # Surface goes UP left-to-right (right-ascending)
            return {"type": SLOPE_R_45, "polygon": COLLISION_POLYGONS[SLOPE_R_45], "profile": profile}
        else:
            # Surface goes DOWN left-to-right (left-ascending)
            return {"type": SLOPE_L_45, "polygon": COLLISION_POLYGONS[SLOPE_L_45], "profile": profile}

    # Gentle slope: surface goes ~half the tile
    if 5 <= total_drop < 12:
        if height_diff < 0:
            # Right-ascending
            if left_height >= 8:
                return {"type": SLOPE_R_GENTLE_LOW, "polygon": COLLISION_POLYGONS[SLOPE_R_GENTLE_LOW], "profile": profile}
            else:
                return {"type": SLOPE_R_GENTLE_HIGH, "polygon": COLLISION_POLYGONS[SLOPE_R_GENTLE_HIGH], "profile": profile}
        else:
            # Left-ascending
            if right_height >= 8:
                return {"type": SLOPE_L_GENTLE_LOW, "polygon": COLLISION_POLYGONS[SLOPE_L_GENTLE_LOW], "profile": profile}
            else:
                return {"type": SLOPE_L_GENTLE_HIGH, "polygon": COLLISION_POLYGONS[SLOPE_L_GENTLE_HIGH], "profile": profile}

    return None


def generate_custom_polygon(profile: list, alpha: np.ndarray) -> list:
    """
    Generate a custom collision polygon from the surface profile.
    Traces the surface from left to right, then closes along the bottom.
    All coordinates relative to tile center (0,0).
    """
    half = TILE_SIZE // 2  # 8

    # Build surface points (top edge of opaque area per column)
    surface_points = []
    for col in range(TILE_SIZE):
        if profile[col] is not None:
            x = col - half  # -8..+7
            y = profile[col] - half  # -8..+7
            surface_points.append((x, y))

    if not surface_points:
        return [(-8, -8), (8, -8), (8, 8), (-8, 8)]

    # Simplify: remove collinear points
    simplified = [surface_points[0]]
    for i in range(1, len(surface_points) - 1):
        prev = simplified[-1]
        curr = surface_points[i]
        next_pt = surface_points[i + 1]
        # Check if collinear
        dx1 = curr[0] - prev[0]
        dy1 = curr[1] - prev[1]
        dx2 = next_pt[0] - curr[0]
        dy2 = next_pt[1] - curr[1]
        if dx1 * dy2 != dy1 * dx2:  # not collinear
            simplified.append(curr)
    simplified.append(surface_points[-1])

    # Close polygon along the bottom
    polygon = list(simplified)
    # Add bottom-right and bottom-left corners
    last_x = simplified[-1][0]
    first_x = simplified[0][0]
    polygon.append((last_x, half))   # bottom at last column
    polygon.append((first_x, half))  # bottom at first column

    return polygon


def build_tile_map_json(tile_map: list, hash_to_atlas: dict,
                        classifications: dict) -> dict:
    """Build the tile_map.json data structure, excluding tiles marked for exclusion."""
    # Build hash-to-index lookup
    hash_to_idx = {}
    for h, (ax, ay) in hash_to_atlas.items():
        hash_to_idx[h] = ay * ATLAS_COLUMNS + ax

    grid = []
    excluded_count = 0
    for row_data in tile_map:
        row_out = []
        for cell in row_data:
            if cell is None:
                row_out.append(None)
            else:
                cls = classifications.get(cell, {})
                if cls.get("excluded", False):
                    row_out.append(None)  # skip excluded tiles
                    excluded_count += 1
                else:
                    ax, ay = hash_to_atlas[cell]
                    row_out.append([ax, ay])
        grid.append(row_out)

    if excluded_count > 0:
        print(f"  Excluded {excluded_count} tile cells (checkpoint/dynamic prefabs)")

    return {
        "tile_size": TILE_SIZE,
        "grid_cols": len(tile_map[0]) if tile_map else 0,
        "grid_rows": len(tile_map),
        "grid": grid,
    }


def build_classifications_json(unique_tiles: list, classifications: dict) -> dict:
    """Build tile_classifications.json."""
    tiles = []
    for i, (h, tile_data) in enumerate(unique_tiles):
        cls = classifications[h]
        entry = {
            "index": i,
            "hash": h,
            "type_id": cls["type"],
            "type_name": COLLISION_NAMES[cls["type"]],
        }
        if cls.get("excluded", False):
            entry["excluded"] = True
        if cls["polygon"]:
            entry["polygon"] = cls["polygon"]
        tiles.append(entry)

    # Summary
    type_counts = {}
    for t in tiles:
        name = t["type_name"]
        type_counts[name] = type_counts.get(name, 0) + 1

    return {
        "tile_size": TILE_SIZE,
        "total_unique": len(tiles),
        "type_summary": type_counts,
        "tiles": tiles,
    }


def generate_debug_overlay(img: Image.Image, tile_map: list, hash_to_atlas: dict,
                           classifications: dict, hash_lookup: dict) -> Image.Image:
    """Generate debug image showing collision types overlaid on tilemap."""
    debug = img.copy().convert("RGBA")
    overlay = Image.new("RGBA", debug.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for row_idx, row_data in enumerate(tile_map):
        for col_idx, cell in enumerate(row_data):
            if cell is None:
                continue
            cls = classifications.get(cell)
            if cls is None:
                continue

            color = DEBUG_COLORS.get(cls["type"], (255, 255, 255, 80))
            x0 = col_idx * TILE_SIZE
            y0 = row_idx * TILE_SIZE
            draw.rectangle([x0, y0, x0 + TILE_SIZE - 1, y0 + TILE_SIZE - 1], fill=color)

    debug = Image.alpha_composite(debug, overlay)
    return debug


def main():
    print(f"Loading tilemap: {TILEMAP_PATH}")
    img = Image.open(TILEMAP_PATH).convert("RGBA")
    img_array = np.array(img)
    print(f"Image size: {img.size}, shape: {img_array.shape}")

    # Debug/intermediate files go to _debug/ (has .gdignore so Godot skips it)
    debug_dir = OUTPUT_DIR / "_debug"
    debug_dir.mkdir(exist_ok=True)
    gdignore = debug_dir / ".gdignore"
    if not gdignore.exists():
        gdignore.write_text("")

    # --- Etapa 1: Extract & deduplicate tiles ---
    print("\n=== Etapa 1: Extracting tiles ===")
    unique_tiles, tile_map, hash_to_atlas = extract_tiles(img_array)

    # Generate atlas (power-of-2 dimensions for GPU compatibility)
    atlas = generate_atlas(unique_tiles)
    atlas_path = OUTPUT_DIR / "assets/smw/sprites/tileset_atlas.png"
    atlas.save(atlas_path, optimize=False)
    print(f"Atlas saved: {atlas_path} ({atlas.size[0]}x{atlas.size[1]})")

    # Generate catalog (debug)
    catalog = generate_catalog(unique_tiles)
    catalog_path = debug_dir / "tile_catalog.png"
    catalog.save(catalog_path)
    print(f"Catalog saved: {catalog_path}")

    # --- Etapa 2: Classify collision ---
    print("\n=== Etapa 2: Classifying collision ===")
    classifications = {}
    hash_lookup = {}  # hash -> tile_data for debug
    for i, (h, tile_data) in enumerate(unique_tiles):
        cls = classify_tile(tile_data, i)
        classifications[h] = cls
        hash_lookup[h] = tile_data

    # Print summary
    type_counts = {}
    for h, cls in classifications.items():
        name = COLLISION_NAMES[cls["type"]]
        type_counts[name] = type_counts.get(name, 0) + 1
    print("Classification summary:")
    for name, count in sorted(type_counts.items()):
        print(f"  {name}: {count}")

    # Save classifications JSON
    cls_data = build_classifications_json(unique_tiles, classifications)
    cls_path = OUTPUT_DIR / "tile_classifications.json"
    cls_path.write_text(json.dumps(cls_data, indent=2), encoding="utf-8")
    print(f"Classifications saved: {cls_path}")

    # Save tile map JSON (after classification, to exclude checkpoint tiles)
    tile_map_data = build_tile_map_json(tile_map, hash_to_atlas, classifications)
    tile_map_path = OUTPUT_DIR / "tile_map.json"
    tile_map_path.write_text(json.dumps(tile_map_data, separators=(",", ":")), encoding="utf-8")
    print(f"Tile map saved: {tile_map_path}")

    # Generate debug overlay (in _debug/)
    debug_img = generate_debug_overlay(img, tile_map, hash_to_atlas, classifications, hash_lookup)
    debug_path = debug_dir / "tile_debug.png"
    debug_img.save(debug_path)
    print(f"Debug overlay saved: {debug_path}")

    print(f"\nDone! {len(unique_tiles)} unique tiles classified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
