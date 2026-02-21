"""
Extract simplified tileset for Yoshi's Island 1 from SMW Ground Tileset
"""
from PIL import Image
import os

# Load original tileset
src = Image.open('sprites/tileset_ground.png')
width, height = src.size
print(f"Original size: {width}x{height}")

# The tileset is organized in 3 main columns (palettes)
# First column: "A lot of stages" (verde/marrom - Yoshi's Island)
# We'll extract from x=0 to x=270 approximately

# Key tiles needed for Yoshi's Island 1:
# - Ground top (grass)
# - Ground fill (dirt)
# - Slopes (45 degrees)
# - Gentle slopes
# - Platform edges
# - Hills (decorative)

# Create new tileset image (16x16 tiles)
# Layout: 16 tiles wide x 8 tiles tall = 256x128 pixels
TILE_SIZE = 16
NEW_WIDTH = 16 * TILE_SIZE  # 256 px
NEW_HEIGHT = 8 * TILE_SIZE  # 128 px

new_tileset = Image.new('RGBA', (NEW_WIDTH, NEW_HEIGHT), (255, 0, 255, 255))  # Magenta background

# Define tiles to extract from the first palette column
# Format: (source_x, source_y, dest_tile_index, description)
# Based on visual analysis of the tileset

# The first palette block starts at approximately x=0
# Tiles are 16x16, arranged in chunks

# Row 1 of tileset (y=12 approx, after the header)
# Ground tiles
tiles_to_extract = [
    # Ground basics (top row of tileset)
    (0, 12, 0, "empty"),

    # Ground with grass top - from the assembled chunks section
    # Looking at y ~450-500 area for the first palette
    (0, 458, 1, "ground_top_left"),
    (16, 458, 2, "ground_top_mid"),
    (32, 458, 3, "ground_top_right"),

    # Ground fill (solid dirt)
    (0, 474, 4, "ground_fill_left"),
    (16, 474, 5, "ground_fill_mid"),
    (32, 474, 6, "ground_fill_right"),

    # Slopes 45 degrees - looking at y~80-120 area
    (0, 76, 7, "slope_45_up_1"),
    (16, 76, 8, "slope_45_up_2"),
    (48, 76, 9, "slope_45_down_1"),
    (64, 76, 10, "slope_45_down_2"),

    # Gentle slopes
    (0, 108, 11, "slope_gentle_up_1"),
    (16, 108, 12, "slope_gentle_up_2"),
    (32, 108, 13, "slope_gentle_up_3"),
    (48, 108, 14, "slope_gentle_up_4"),

    # More slope variants
    (96, 76, 15, "slope_corner_1"),

    # Second row - ground edges
    (0, 44, 16, "ground_edge_left"),
    (64, 44, 17, "ground_edge_right"),
    (32, 28, 18, "ground_edge_top"),
    (32, 60, 19, "ground_edge_bottom"),

    # Corner pieces
    (0, 28, 20, "ground_corner_tl"),
    (64, 28, 21, "ground_corner_tr"),
    (0, 60, 22, "ground_corner_bl"),
    (64, 60, 23, "ground_corner_br"),

    # Hills from bottom section (y ~820)
    (0, 820, 24, "hill_1"),
    (48, 820, 25, "hill_2"),
    (96, 820, 26, "hill_3"),
    (144, 820, 27, "hill_4"),

    # Decorative bushes
    (0, 852, 28, "bush_1"),
    (48, 852, 29, "bush_2"),
    (96, 852, 30, "bush_3"),

    # Pipe (from the bottom)
    (192, 820, 31, "pipe_top_left"),
]

print(f"Extracting {len(tiles_to_extract)} tiles...")

# Actually, let me take a simpler approach
# Just crop the first palette column which has the complete tile chunks
# This will be more useful for manual tile selection

# First palette column is roughly 0-260 pixels wide
# Let's crop just the essential parts

# Crop the first column (Yoshi's Island palette)
first_palette = src.crop((0, 0, 270, 500))
first_palette.save('sprites/tileset_yi1_full.png')
print(f"Saved first palette column: sprites/tileset_yi1_full.png")

# Also save the hills/decorative section
hills_section = src.crop((0, 800, 300, 896))
hills_section.save('sprites/tileset_yi1_hills.png')
print(f"Saved hills section: sprites/tileset_yi1_hills.png")

# Create a minimal tileset with just the basic tiles needed
# Using the "assembled chunks" which are pre-combined 32x32 or 48x48 blocks
minimal = Image.new('RGBA', (256, 256), (0, 0, 0, 0))

# Copy some basic ground tiles from the first palette
# Row 1: Top row of ground tiles (y starts around 12-28)
y_offset = 12
for i, x in enumerate([0, 16, 32, 48, 64, 80, 96, 112]):
    if x + 16 <= src.width:
        tile = src.crop((x, y_offset, x + 16, y_offset + 16))
        minimal.paste(tile, (i * 16, 0))

# Row 2: Second row
y_offset = 28
for i, x in enumerate([0, 16, 32, 48, 64, 80, 96, 112]):
    if x + 16 <= src.width:
        tile = src.crop((x, y_offset, x + 16, y_offset + 16))
        minimal.paste(tile, (i * 16, 16))

# Row 3: Third row (ground fill)
y_offset = 44
for i, x in enumerate([0, 16, 32, 48, 64, 80, 96, 112]):
    if x + 16 <= src.width:
        tile = src.crop((x, y_offset, x + 16, y_offset + 16))
        minimal.paste(tile, (i * 16, 32))

# Row 4: Fourth row
y_offset = 60
for i, x in enumerate([0, 16, 32, 48, 64, 80, 96, 112]):
    if x + 16 <= src.width:
        tile = src.crop((x, y_offset, x + 16, y_offset + 16))
        minimal.paste(tile, (i * 16, 48))

# Row 5-8: Slopes
for row, y_offset in enumerate([76, 92, 108, 124], start=4):
    for i, x in enumerate([0, 16, 32, 48, 64, 80, 96, 112]):
        if x + 16 <= src.width and y_offset + 16 <= src.height:
            tile = src.crop((x, y_offset, x + 16, y_offset + 16))
            minimal.paste(tile, (i * 16, row * 16))

# Rows 9-12: More tiles
for row, y_offset in enumerate([140, 156, 172, 188], start=8):
    for i, x in enumerate([0, 16, 32, 48, 64, 80, 96, 112]):
        if x + 16 <= src.width and y_offset + 16 <= src.height:
            tile = src.crop((x, y_offset, x + 16, y_offset + 16))
            minimal.paste(tile, (i * 16, row * 16))

# Rows 13-16: Hills (from bottom)
for row, y_offset in enumerate([820, 836, 852, 868], start=12):
    for i, x in enumerate([0, 16, 32, 48, 64, 80, 96, 112]):
        if x + 16 <= src.width and y_offset + 16 <= src.height:
            tile = src.crop((x, y_offset, x + 16, y_offset + 16))
            minimal.paste(tile, (i * 16, row * 16))

minimal.save('sprites/tileset_yi1_minimal.png')
print(f"Saved minimal tileset: sprites/tileset_yi1_minimal.png")

print("\nDone! Created:")
print("  - tileset_yi1_full.png (first palette, full)")
print("  - tileset_yi1_hills.png (hills/decorations)")
print("  - tileset_yi1_minimal.png (256x256 essential tiles)")
