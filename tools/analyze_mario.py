"""
Analyze mario_region.png pixel by pixel to find exact sprite locations.
"""

from PIL import Image
import os

def analyze():
    img = Image.open("assets/smw/sprites/mario_region.png").convert("RGBA")
    pixels = img.load()
    width, height = img.size

    print(f"Image size: {width}x{height}")

    # Analyze the exact pixel colors
    # Check the cyan background color
    print("\nSample pixels from corners:")
    print(f"  (0,0): {pixels[0, 0]}")
    print(f"  ({width-1},0): {pixels[width-1, 0]}")
    print(f"  (0,{height-1}): {pixels[0, height-1]}")
    print(f"  ({width-1},{height-1}): {pixels[width-1, height-1]}")

    # Get the exact cyan color
    cyan = pixels[width-1, height-1]  # Most likely pure cyan
    print(f"\nCyan background color: {cyan}")

    def is_bg(p):
        """Check if pixel is the cyan background."""
        if len(p) == 4 and p[3] < 128:
            return True
        # Exact or near-exact cyan match
        r, g, b = p[:3]
        cr, cg, cb = cyan[:3]
        if abs(r - cr) < 10 and abs(g - cg) < 10 and abs(b - cb) < 10:
            return True
        return False

    # Scan each row and find which have non-bg content
    print("\nRow-by-row analysis (non-cyan content):")
    for y in range(height):
        non_bg_cols = []
        for x in range(width):
            if not is_bg(pixels[x, y]):
                non_bg_cols.append(x)
        if non_bg_cols:
            # Group consecutive columns
            groups = []
            start = non_bg_cols[0]
            prev = start
            for col in non_bg_cols[1:]:
                if col > prev + 1:
                    groups.append((start, prev))
                    start = col
                prev = col
            groups.append((start, prev))
            print(f"  Row {y}: {len(groups)} groups - {groups[:10]}...")

    # Scan for distinct sprites by looking at column groups
    print("\n\nLooking for sprites (connected non-bg regions)...")

    # Start from the bottom half where sprites actually are
    # Skip top rows which contain text
    SPRITE_START_Y = 25  # Sprites should start around here

    visited = set()
    sprites = []

    def flood_fill(start_x, start_y):
        """Find connected non-bg region."""
        stack = [(start_x, start_y)]
        min_x, max_x = start_x, start_x
        min_y, max_y = start_y, start_y
        count = 0

        while stack:
            x, y = stack.pop()
            if (x, y) in visited:
                continue
            if x < 0 or x >= width or y < 0 or y >= height:
                continue
            if is_bg(pixels[x, y]):
                continue

            visited.add((x, y))
            count += 1
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)

            # Check neighbors
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                stack.append((x + dx, y + dy))

        return (min_x, min_y, max_x - min_x + 1, max_y - min_y + 1, count)

    # Find all connected regions in the sprite area
    for y in range(SPRITE_START_Y, height):
        for x in range(width):
            if (x, y) not in visited and not is_bg(pixels[x, y]):
                region = flood_fill(x, y)
                if region[4] > 20:  # At least 20 pixels (ignore tiny specks)
                    sprites.append(region)
                    print(f"Found sprite: x={region[0]}, y={region[1]}, w={region[2]}, h={region[3]}, pixels={region[4]}")

    print(f"\nTotal sprites found: {len(sprites)}")

    # Create a visual debug image
    from PIL import ImageDraw
    debug = img.copy().convert("RGB")
    draw = ImageDraw.Draw(debug)

    colors = [(255,0,0), (0,255,0), (0,0,255), (255,255,0), (255,0,255), (0,255,255)]
    for i, spr in enumerate(sprites):
        x, y, w, h, _ = spr
        color = colors[i % len(colors)]
        draw.rectangle([x, y, x+w-1, y+h-1], outline=color, width=2)

    debug.save("assets/smw/sprites/mario_analysis.png")
    print(f"\nSaved analysis to: assets/smw/sprites/mario_analysis.png")

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    analyze()
