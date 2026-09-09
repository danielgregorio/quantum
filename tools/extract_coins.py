"""
Extract animated coins from SMW items tileset.
The tileset has cyan background that needs to be made transparent.
"""
from PIL import Image
import os

def extract_coins():
    # Load the items tileset
    img = Image.open('assets/smw/sprites/items_animated.png').convert('RGBA')
    pixels = img.load()
    width, height = img.size

    print(f"Image size: {width}x{height}")

    # The cyan background color (approximate)
    cyan_colors = [
        (0, 176, 248, 255),   # Common SMW cyan
        (0, 176, 240, 255),
        (0, 184, 248, 255),
        (0, 168, 248, 255),
    ]

    # Find the actual cyan color by sampling the background
    bg_color = pixels[0, 0]
    print(f"Background color at (0,0): {bg_color}")

    # Make cyan transparent
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            # Check if it's cyan-ish (high blue, medium-high green, low red)
            if b > 200 and g > 150 and r < 50:
                pixels[x, y] = (0, 0, 0, 0)

    # Looking at the image, the "Coin (loop)" row appears to be around y=112
    # Let me find it by looking for the yellow coin pixels

    # The coins appear to be 16x16, let me extract them
    # Based on visual inspection:
    # - Coin row starts around y=112
    # - 4 frames horizontally starting around x=0

    # Let me scan for yellow pixels to find coin locations
    coin_regions = []

    # Scan for yellow pixels (coins are yellow/gold)
    for y in range(0, height, 8):
        for x in range(0, width, 8):
            r, g, b, a = pixels[x, y] if pixels[x, y][3] > 0 else (0, 0, 0, 0)
            # Yellow: high red, high green, low blue
            if r > 200 and g > 150 and b < 100 and a > 0:
                print(f"Yellow pixel at ({x}, {y}): {pixels[x, y]}")

    # Based on visual analysis, extract coin frames
    # Coins appear to be at these approximate locations (16x16 each):
    # Row "Coin (loop)" - let me extract starting from the label position

    # From the image, "Coin (loop)" text is at around y=104
    # The actual coin sprites are below/beside the text
    # Looking at row around y=112, coins start at x=0

    # Let me try different approach - find the coin row by scanning
    # The coins are in a row, 4 frames, each 16x16

    # Manual coordinates based on visual inspection:
    # Looking at the image layout:
    # - "Coin (loop)" label is on left side
    # - The actual coin sprites are the small yellow circles
    # - They appear to be at row starting around y=120, after the Yoshi Coin row
    # - The row with "Coin (loop)" text, the sprites are to the right of label

    # Based on visual analysis, the small spinning coins are at:
    # y around 120 (below Yoshi Coin), x starts after the label text
    # The coins are 16x16 with 4 frames

    # Let me try y=120, and scan for the first non-transparent column
    coin_y = 120  # Row for "Coin (loop)"
    coin_size = 16
    num_frames = 4

    # Find where coins actually start by scanning for non-transparent pixels in that row
    coin_x_start = 0
    for x in range(0, 100):
        found_coin = False
        for dy in range(16):
            px = pixels[x, coin_y + dy]
            # Look for yellow/gold pixels
            if px[3] > 0 and px[0] > 180 and px[1] > 100:
                coin_x_start = x
                found_coin = True
                break
        if found_coin:
            break

    print(f"Found coin start at x={coin_x_start}")

    # Extract coin frames
    coin_frames = []
    for i in range(num_frames):
        x = coin_x_start + i * coin_size
        frame = img.crop((x, coin_y, x + coin_size, coin_y + coin_size))
        coin_frames.append(frame)
        print(f"Extracted coin frame {i} from ({x}, {coin_y})")

    # Create a horizontal strip of coin frames (64x16 for 4 frames)
    coin_strip = Image.new('RGBA', (coin_size * num_frames, coin_size), (0, 0, 0, 0))
    for i, frame in enumerate(coin_frames):
        coin_strip.paste(frame, (i * coin_size, 0))

    # Save the coin strip
    os.makedirs('assets/smw/sprites', exist_ok=True)
    coin_strip.save('assets/smw/sprites/coin_animated.png')
    print(f"Saved coin strip: {coin_size * num_frames}x{coin_size}")

    # Also extract ?-Block (loop)
    # ?-Block appears to be around y=144
    qblock_y = 144
    qblock_frames = []
    for i in range(4):
        x = i * coin_size
        frame = img.crop((x, qblock_y, x + coin_size, qblock_y + coin_size))
        qblock_frames.append(frame)

    qblock_strip = Image.new('RGBA', (coin_size * 4, coin_size), (0, 0, 0, 0))
    for i, frame in enumerate(qblock_frames):
        qblock_strip.paste(frame, (i * coin_size, 0))
    qblock_strip.save('assets/smw/sprites/qblock_animated.png')
    print("Saved ?-block strip")

    # Let me also save the full image with transparency
    img.save('assets/smw/sprites/items_animated_transparent.png')
    print("Saved transparent version of full tileset")

if __name__ == '__main__':
    extract_coins()
