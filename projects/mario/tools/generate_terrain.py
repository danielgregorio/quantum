#!/usr/bin/env python3
"""
Terrain Contour Tracer v3 — Elevation-based with proper slope ramps.

Key changes:
- Only creates collision for features significantly above ground (y < 364)
- ground-main handles all flat ground at y=384
- Each elevated region is a separate CollisionPolygon2D
- Steep walls get 45° slope ramps (extends polygon bounds if needed)
- Floating regions get proper slope entries (no vertical walls)
- Bushes and small decorations are excluded
"""

import json
import math
import sys
from pathlib import Path

from PIL import Image

TILEMAP_PATH = Path(__file__).parent / "assets/smw/sprites/yoshi-island-1.png"
IMG_HEIGHT = 432
GROUND_Y = 384
GROUND_THRESHOLD = 420
ELEVATION_THRESHOLD = 364  # Only features where y < this get collision
SAMPLE_STEP = 4
SIMPLIFY_EPSILON = 2.5
MIN_REGION_WIDTH = 16
MAX_SLOPE_ANGLE = 55  # degrees — steeper walls get ramps on HILLS only
HILL_MIN_WIDTH = 60  # Regions wider than this get slope ramps (hills)
                      # Narrower regions keep vertical walls (pipes, platforms)
HILL_PEAK_THRESHOLD = 310  # Hills must have peak above this (y < 310 = high enough)
                            # Regions with peak y >= 310 are structures (platforms/pipes)


def scan_surface_y(img, x):
    """Find ground-connected surface y at column x."""
    regions = []
    in_opaque = False
    start_y = 0
    for y in range(IMG_HEIGHT):
        a = img.getpixel((x, y))[3]
        if a > 0 and not in_opaque:
            in_opaque = True
            start_y = y
        elif a == 0 and in_opaque:
            in_opaque = False
            regions.append((start_y, y - 1))
    if in_opaque:
        regions.append((start_y, IMG_HEIGHT - 1))

    if not regions:
        return None, []

    if regions[-1][1] >= GROUND_THRESHOLD:
        ground_top = regions[-1][0]
        floating = [(r[0], r[1]) for r in regions[:-1] if r[1] - r[0] + 1 >= 12]
        return ground_top, floating
    else:
        return None, []


def scan_full_surface(img):
    """Scan tilemap and return surface array and floating regions."""
    width = img.width
    surface = []
    floating_columns = {}

    for x in range(0, width, SAMPLE_STEP):
        best_y = None
        all_floats = []
        for dx in range(min(SAMPLE_STEP, width - x)):
            sy, floats = scan_surface_y(img, x + dx)
            if sy is not None:
                if best_y is None or sy < best_y:
                    best_y = sy
            all_floats.extend(floats)

        if best_y is not None:
            surface.append((x, best_y))
            if all_floats:
                floating_columns[x] = all_floats
        else:
            surface.append((x, None))

    return surface, floating_columns


def extract_elevated_regions(surface):
    """Extract regions where surface is significantly above ground."""
    regions = []
    current_region = []
    in_elevated = False

    for x, y in surface:
        if y is None:
            if current_region:
                regions.append(current_region)
            current_region = []
            in_elevated = False
            continue

        if y < ELEVATION_THRESHOLD:
            if not in_elevated:
                in_elevated = True
                current_region = [(x, y)]
            else:
                current_region.append((x, y))
        else:
            if in_elevated:
                if len(current_region) >= MIN_REGION_WIDTH // SAMPLE_STEP:
                    regions.append(current_region)
                current_region = []
                in_elevated = False

    if in_elevated and current_region:
        if len(current_region) >= MIN_REGION_WIDTH // SAMPLE_STEP:
            regions.append(current_region)

    return regions


def ensure_slopes(points):
    """
    Ensure all transitions are walkable (≤ MAX_SLOPE_ANGLE).
    For steep transitions, EXTENDS the polygon bounds to add 45° ramps.
    This is the key fix — it creates gentle entry/exit ramps.
    """
    max_slope_tan = math.tan(math.radians(MAX_SLOPE_ANGLE))
    result = []

    for i, (x, y) in enumerate(points):
        if i == 0:
            result.append((x, y))
            continue

        x_prev, y_prev = result[-1]
        dy = y_prev - y  # positive = going UP (y decreases = up)
        dx = x - x_prev

        if dx <= 0:
            result.append((x, y))
            continue

        if dy > 0:
            # Going UP — check if slope is too steep
            actual_slope = dy / max(dx, 1)
            if actual_slope > max_slope_tan:
                # Need to extend left to create a gentler ramp
                needed_dx = int(dy / max_slope_tan)
                ramp_start_x = x - needed_dx
                # Replace previous ground-level point or insert new one
                if y_prev == GROUND_Y and len(result) >= 1:
                    result[-1] = (ramp_start_x, GROUND_Y)
                else:
                    result.append((ramp_start_x, y_prev))
                result.append((x, y))
            else:
                result.append((x, y))
        elif dy < 0:
            # Going DOWN — check if slope is too steep
            actual_slope = abs(dy) / max(dx, 1)
            if actual_slope > max_slope_tan:
                needed_dx = int(abs(dy) / max_slope_tan)
                ramp_end_x = x_prev + needed_dx
                result.append((ramp_end_x, y))
                if ramp_end_x < x:
                    result.append((x, y))
            else:
                result.append((x, y))
        else:
            result.append((x, y))

    return result


def make_region_polygon(region):
    """
    Create a closed collision polygon for an elevated region.

    HILLS (width > HILL_MIN_WIDTH): Get slope ramps at entry/exit for walkability.
    STRUCTURES (width <= HILL_MIN_WIDTH): Keep vertical walls — Mario jumps over them.
    Internal transitions are never modified (preserves pipe walls, platform edges).
    """
    if len(region) < 2:
        return None

    surface = list(region)
    region_width = surface[-1][0] - surface[0][0]
    peak_y = min(y for _, y in region)
    # Hills need BOTH: wide enough AND high peak (substantially above ground)
    # Platforms/pipes at y>=310 are only 74px above ground — too low to be a hill
    is_hill = region_width >= HILL_MIN_WIDTH and peak_y < HILL_PEAK_THRESHOLD

    first_x, first_y = surface[0]
    last_x, last_y = surface[-1]

    if is_hill:
        # HILL: add slope ramps at entry and exit
        rise_left = GROUND_Y - first_y
        ramp_dx_left = int(rise_left / math.tan(math.radians(MAX_SLOPE_ANGLE)))
        entry_x = first_x - max(ramp_dx_left, SAMPLE_STEP)
        surface.insert(0, (entry_x, GROUND_Y))

        rise_right = GROUND_Y - last_y
        ramp_dx_right = int(rise_right / math.tan(math.radians(MAX_SLOPE_ANGLE)))
        exit_x = last_x + max(ramp_dx_right, SAMPLE_STEP)
        surface.append((exit_x, GROUND_Y))
    else:
        # STRUCTURE (pipe/platform): vertical walls, add ground points directly
        surface.insert(0, (first_x, GROUND_Y))
        surface.append((last_x, GROUND_Y))

    # Close the polygon
    polygon = list(surface)
    polygon.append((polygon[0][0], polygon[0][1]))

    return polygon


def douglas_peucker(points, epsilon):
    """Simplify a polyline using the Douglas-Peucker algorithm."""
    if len(points) <= 2:
        return points

    start = points[0]
    end = points[-1]
    max_dist = 0
    max_idx = 0

    dx = end[0] - start[0]
    dy = end[1] - start[1]
    line_len = math.sqrt(dx * dx + dy * dy)

    for i in range(1, len(points) - 1):
        if line_len == 0:
            dist = math.sqrt(
                (points[i][0] - start[0]) ** 2 + (points[i][1] - start[1]) ** 2
            )
        else:
            dist = abs(
                dy * points[i][0] - dx * points[i][1] + end[0] * start[1] - end[1] * start[0]
            ) / line_len
        if dist > max_dist:
            max_dist = dist
            max_idx = i

    if max_dist > epsilon:
        left = douglas_peucker(points[: max_idx + 1], epsilon)
        right = douglas_peucker(points[max_idx:], epsilon)
        return left[:-1] + right
    else:
        return [start, end]


def simplify_polygon(polygon, epsilon=SIMPLIFY_EPSILON):
    """Simplify polygon surface (excluding closing bottom points)."""
    if len(polygon) <= 4:
        return polygon

    # Find the closing bottom segment (last points at GROUND_Y)
    # Surface = everything except the final closing point
    surface = polygon[:-1]  # remove closing duplicate

    # Reduce colinear
    reduced = [surface[0]]
    for i in range(1, len(surface)):
        if surface[i][1] != surface[i - 1][1]:
            if reduced[-1] != surface[i - 1]:
                reduced.append(surface[i - 1])
            reduced.append(surface[i])
    if reduced[-1] != surface[-1]:
        reduced.append(surface[-1])

    # Douglas-Peucker
    if len(reduced) > 2:
        reduced = douglas_peucker(reduced, epsilon)

    # Re-close
    reduced.append((reduced[0][0], reduced[0][1]))
    return reduced


def cluster_floating_regions(floating_columns):
    """Group adjacent floating column regions into clusters."""
    if not floating_columns:
        return []

    sorted_x = sorted(floating_columns.keys())
    clusters = []
    current_cluster = {sorted_x[0]: floating_columns[sorted_x[0]]}
    prev_x = sorted_x[0]

    for x in sorted_x[1:]:
        if x - prev_x <= SAMPLE_STEP + 2:
            current_cluster[x] = floating_columns[x]
        else:
            clusters.append(current_cluster)
            current_cluster = {x: floating_columns[x]}
        prev_x = x
    clusters.append(current_cluster)

    filtered = []
    for c in clusters:
        x_range = max(c.keys()) - min(c.keys())
        if x_range < MIN_REGION_WIDTH:
            continue
        has_elevated = any(
            top < ELEVATION_THRESHOLD
            for regions in c.values()
            for top, bottom in regions
        )
        if has_elevated:
            filtered.append(c)

    return filtered


def make_floating_polygon(cluster):
    """
    Create collision polygon for a floating structure (hill left-side, pipe above ground).
    Uses the actual visual bounds — no slope ramps added.
    Mario approaches these from the adjacent terrain region's slope.
    """
    sorted_x = sorted(cluster.keys())

    top_surface = []
    bottom_y = 0
    for x in sorted_x:
        regions = cluster[x]
        min_top = min(r[0] for r in regions)
        max_bottom = max(r[1] for r in regions)
        top_surface.append((x, min_top))
        bottom_y = max(bottom_y, max_bottom)

    # Use GROUND_Y as bottom to connect with ground-main
    base_y = max(bottom_y, GROUND_Y)

    first_x = top_surface[0][0]
    last_x = top_surface[-1][0]

    polygon = list(top_surface)
    polygon.append((last_x, base_y))
    polygon.append((first_x, base_y))
    polygon.append((first_x, top_surface[0][1]))  # close

    return polygon


def format_packed_vector2_array(polygon):
    """Format polygon as Godot PackedVector2Array string."""
    parts = []
    for x, y in polygon:
        parts.append(f"{int(x)}, {int(y)}")
    return "PackedVector2Array(" + ", ".join(parts) + ")"


def generate_tscn_nodes(terrain_polygons, floating_polygons):
    """Generate .tscn node text for all terrain collision polygons."""
    lines = []
    idx = 0

    for polygon in terrain_polygons:
        name = f"terrain_{idx}"
        lines.append(f'[node name="{name}" type="StaticBody2D" parent="."]')
        lines.append(f'metadata/tag = "terrain"')
        lines.append("")
        lines.append(
            f'[node name="CollisionPolygon2D" type="CollisionPolygon2D" parent="{name}"]'
        )
        lines.append(f"polygon = {format_packed_vector2_array(polygon)}")
        lines.append("")
        idx += 1

    for polygon in floating_polygons:
        name = f"terrain_float_{idx}"
        lines.append(f'[node name="{name}" type="StaticBody2D" parent="."]')
        lines.append(f'metadata/tag = "terrain"')
        lines.append("")
        lines.append(
            f'[node name="CollisionPolygon2D" type="CollisionPolygon2D" parent="{name}"]'
        )
        lines.append(f"polygon = {format_packed_vector2_array(polygon)}")
        lines.append("")
        idx += 1

    return "\n".join(lines)


def main():
    print(f"Loading tilemap: {TILEMAP_PATH}")
    img = Image.open(TILEMAP_PATH)
    print(f"Image size: {img.size}, mode: {img.mode}")

    print(f"Scanning terrain surface (step={SAMPLE_STEP})...")
    surface, floating_columns = scan_full_surface(img)

    ground_count = sum(1 for _, y in surface if y is not None)
    print(f"Ground samples: {ground_count}")

    print(f"Extracting elevated regions (threshold y < {ELEVATION_THRESHOLD})...")
    elevated_regions = extract_elevated_regions(surface)
    print(f"Elevated regions found: {len(elevated_regions)}")

    terrain_polygons = []
    for i, region in enumerate(elevated_regions):
        x_min = region[0][0]
        x_max = region[-1][0]
        y_min = min(y for _, y in region)

        polygon = make_region_polygon(region)
        if polygon:
            polygon = simplify_polygon(polygon)
            print(f"  Region {i}: x=[{x_min}-{x_max}], peak y={y_min}, {len(polygon)} pts")
            terrain_polygons.append(polygon)

    # Build terrain x-ranges (including ramp extensions) for overlap detection
    terrain_x_ranges = []
    for p in terrain_polygons:
        xs = [x for x, y in p]
        terrain_x_ranges.append((min(xs), max(xs)))

    print("Processing floating structures...")
    clusters = cluster_floating_regions(floating_columns)
    floating_polygons = []
    for cluster in clusters:
        x_min = min(cluster.keys())
        x_max = max(cluster.keys())
        # Skip floats that overlap with a terrain region (redundant with slope ramps)
        overlaps = any(
            tx_min <= x_min and tx_max >= x_max
            for tx_min, tx_max in terrain_x_ranges
        )
        if overlaps:
            print(f"  Float x=[{x_min}-{x_max}]: SKIP (inside terrain region)")
            continue
        polygon = make_floating_polygon(cluster)
        if polygon:
            print(f"  Float x=[{x_min}-{x_max}]: {len(polygon)} pts")
            floating_polygons.append(polygon)

    print(f"\nGenerating .tscn nodes...")
    tscn_text = generate_tscn_nodes(terrain_polygons, floating_polygons)

    output_path = Path(__file__).parent / "terrain_nodes.txt"
    output_path.write_text(tscn_text, encoding="utf-8")
    print(f"Written to: {output_path}")

    json_data = {
        "terrain_polygons": [[(x, y) for x, y in p] for p in terrain_polygons],
        "floating_polygons": [[(x, y) for x, y in p] for p in floating_polygons],
    }
    json_path = Path(__file__).parent / "terrain_data.json"
    json_path.write_text(json.dumps(json_data, indent=2), encoding="utf-8")

    total = len(terrain_polygons) + len(floating_polygons)
    print(f"Total: {len(terrain_polygons)} terrain + {len(floating_polygons)} floating = {total} nodes")

    return 0


if __name__ == "__main__":
    sys.exit(main())
