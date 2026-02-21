"""
Create a clean, organized tileset for Yoshi's Island 1
With proper transparency and tile indexing
"""
from PIL import Image
import os

# Load original tileset
src = Image.open('sprites/tileset_ground.png').convert('RGBA')
width, height = src.size

# Define the magenta color used for transparency
MAGENTA = (255, 0, 255, 255)
SKY_BLUE = (92, 148, 252)  # Approximate SMW sky blue

# Create clean tileset: 16 columns x 16 rows = 256 tiles max
TILE_SIZE = 16
COLS = 16
ROWS = 16
new_tileset = Image.new('RGBA', (COLS * TILE_SIZE, ROWS * TILE_SIZE), (0, 0, 0, 0))

# Function to extract and clean a tile
def extract_tile(x, y, make_transparent=True):
    """Extract 16x16 tile from source, optionally making bg transparent"""
    tile = src.crop((x, y, x + TILE_SIZE, y + TILE_SIZE)).convert('RGBA')

    if make_transparent:
        pixels = tile.load()
        for py in range(TILE_SIZE):
            for px in range(TILE_SIZE):
                r, g, b, a = pixels[px, py]
                # Make magenta transparent
                if (r, g, b) == (255, 0, 255):
                    pixels[px, py] = (0, 0, 0, 0)
                # Make sky blue transparent
                elif abs(r - 92) < 20 and abs(g - 148) < 20 and abs(b - 252) < 20:
                    pixels[px, py] = (0, 0, 0, 0)
    return tile

# Tile mapping for Yoshi's Island 1 style (first palette column)
# Analyzed from visual inspection
tiles = []
tile_names = []

# === ROW 0: Basic ground corners and edges ===
# Top-left corner
tiles.append(extract_tile(0, 28))
tile_names.append("corner_tl")
# Top edge
tiles.append(extract_tile(16, 28))
tile_names.append("edge_top")
tiles.append(extract_tile(32, 28))
tile_names.append("edge_top_mid")
tiles.append(extract_tile(48, 28))
tile_names.append("edge_top_2")
# Top-right corner
tiles.append(extract_tile(64, 28))
tile_names.append("corner_tr")
# Left edge
tiles.append(extract_tile(0, 44))
tile_names.append("edge_left")
# Fill/solid
tiles.append(extract_tile(16, 44))
tile_names.append("fill")
tiles.append(extract_tile(32, 44))
tile_names.append("fill_2")
# Right edge
tiles.append(extract_tile(64, 44))
tile_names.append("edge_right")
# Bottom-left corner
tiles.append(extract_tile(0, 60))
tile_names.append("corner_bl")
# Bottom edge
tiles.append(extract_tile(16, 60))
tile_names.append("edge_bottom")
tiles.append(extract_tile(32, 60))
tile_names.append("edge_bottom_2")
# Bottom-right corner
tiles.append(extract_tile(64, 60))
tile_names.append("corner_br")
# Additional fills
tiles.append(extract_tile(48, 44))
tile_names.append("fill_3")
tiles.append(extract_tile(80, 44))
tile_names.append("fill_4")
# Empty/transparent
tiles.append(Image.new('RGBA', (16, 16), (0, 0, 0, 0)))
tile_names.append("empty")

# === ROW 1: 45-degree slopes ===
# Slope up (left to right, going up)
tiles.append(extract_tile(0, 76))
tile_names.append("slope45_up_1")
tiles.append(extract_tile(16, 76))
tile_names.append("slope45_up_2")
# Slope down (left to right, going down)
tiles.append(extract_tile(48, 76))
tile_names.append("slope45_down_1")
tiles.append(extract_tile(64, 76))
tile_names.append("slope45_down_2")
# Slope fill pieces
tiles.append(extract_tile(0, 92))
tile_names.append("slope45_fill_1")
tiles.append(extract_tile(16, 92))
tile_names.append("slope45_fill_2")
tiles.append(extract_tile(48, 92))
tile_names.append("slope45_fill_3")
tiles.append(extract_tile(64, 92))
tile_names.append("slope45_fill_4")

# === ROW 2: Gentle slopes ===
tiles.append(extract_tile(0, 108))
tile_names.append("slope_gentle_1")
tiles.append(extract_tile(16, 108))
tile_names.append("slope_gentle_2")
tiles.append(extract_tile(32, 108))
tile_names.append("slope_gentle_3")
tiles.append(extract_tile(48, 108))
tile_names.append("slope_gentle_4")
tiles.append(extract_tile(64, 108))
tile_names.append("slope_gentle_5")
tiles.append(extract_tile(80, 108))
tile_names.append("slope_gentle_6")
tiles.append(extract_tile(96, 108))
tile_names.append("slope_gentle_7")
tiles.append(extract_tile(112, 108))
tile_names.append("slope_gentle_8")

# Gentle slope fills
tiles.append(extract_tile(0, 124))
tile_names.append("slope_gentle_fill_1")
tiles.append(extract_tile(16, 124))
tile_names.append("slope_gentle_fill_2")
tiles.append(extract_tile(32, 124))
tile_names.append("slope_gentle_fill_3")
tiles.append(extract_tile(48, 124))
tile_names.append("slope_gentle_fill_4")
tiles.append(extract_tile(64, 124))
tile_names.append("slope_gentle_fill_5")
tiles.append(extract_tile(80, 124))
tile_names.append("slope_gentle_fill_6")
tiles.append(extract_tile(96, 124))
tile_names.append("slope_gentle_fill_7")
tiles.append(extract_tile(112, 124))
tile_names.append("slope_gentle_fill_8")

# === Hills (decorative) ===
tiles.append(extract_tile(16, 820))
tile_names.append("hill_small_1")
tiles.append(extract_tile(32, 820))
tile_names.append("hill_small_2")
tiles.append(extract_tile(48, 820))
tile_names.append("hill_small_3")
tiles.append(extract_tile(64, 836))
tile_names.append("hill_med_1")
tiles.append(extract_tile(80, 836))
tile_names.append("hill_med_2")
tiles.append(extract_tile(96, 836))
tile_names.append("hill_med_3")
tiles.append(extract_tile(112, 836))
tile_names.append("hill_med_4")
tiles.append(extract_tile(128, 836))
tile_names.append("hill_med_5")

# Bush
tiles.append(extract_tile(0, 852))
tile_names.append("bush_1")
tiles.append(extract_tile(16, 852))
tile_names.append("bush_2")
tiles.append(extract_tile(32, 852))
tile_names.append("bush_3")
tiles.append(extract_tile(48, 852))
tile_names.append("bush_4")

# Add grass top variations
tiles.append(extract_tile(16, 12))
tile_names.append("grass_top_1")
tiles.append(extract_tile(32, 12))
tile_names.append("grass_top_2")
tiles.append(extract_tile(48, 12))
tile_names.append("grass_top_3")

# Place tiles in the new tileset
for i, tile in enumerate(tiles):
    row = i // COLS
    col = i % COLS
    new_tileset.paste(tile, (col * TILE_SIZE, row * TILE_SIZE))

# Save the clean tileset
new_tileset.save('sprites/tileset_yi1_clean.png')

# Also save individual tile references
print("Tileset created with", len(tiles), "tiles")
print("\nTile Index Reference:")
for i, name in enumerate(tile_names):
    print(f"  {i:3d}: {name}")

# Save tile reference as JSON for the game
import json
tile_ref = {
    "tile_size": TILE_SIZE,
    "columns": COLS,
    "rows": ROWS,
    "tiles": {name: i for i, name in enumerate(tile_names)}
}
with open('sprites/tileset_yi1_clean.json', 'w') as f:
    json.dump(tile_ref, f, indent=2)

print(f"\nSaved: sprites/tileset_yi1_clean.png ({COLS*TILE_SIZE}x{len(tiles)//COLS*TILE_SIZE + TILE_SIZE})")
print("Saved: sprites/tileset_yi1_clean.json")
