"""
Extract Mario sprites - with horizontal flip so Mario faces RIGHT by default.
"""

from PIL import Image
import os

def extract_mario():
    img = Image.open("assets/smw/sprites/mario_region.png").convert("RGBA")
    pixels = img.load()
    width, height = img.size

    def is_bg(p):
        if len(p) == 4 and p[3] < 128:
            return True
        r, g, b = p[:3]
        if r < 20 and 40 < g < 160 and 40 < b < 160:
            return True
        return False

    boxes = {
        'idle': (8, 33, 48, 47),
        'walk': (164, 33, 48, 47),
    }

    def find_sprites_in_box(box_x, box_y, box_w, box_h):
        sprites = []
        col_ranges = []
        col_start = None

        for x in range(box_x, box_x + box_w):
            has_content = False
            for y in range(box_y, box_y + box_h):
                if not is_bg(pixels[x, y]):
                    has_content = True
                    break
            if has_content:
                if col_start is None:
                    col_start = x
            else:
                if col_start is not None:
                    col_ranges.append((col_start, x - 1))
                    col_start = None
        if col_start is not None:
            col_ranges.append((col_start, box_x + box_w - 1))

        for start_x, end_x in col_ranges:
            row_ranges = []
            row_start = None
            for y in range(box_y, box_y + box_h):
                has_content = False
                for x in range(start_x, end_x + 1):
                    if not is_bg(pixels[x, y]):
                        has_content = True
                        break
                if has_content:
                    if row_start is None:
                        row_start = y
                else:
                    if row_start is not None:
                        row_ranges.append((row_start, y - 1))
                        row_start = None
            if row_start is not None:
                row_ranges.append((row_start, box_y + box_h - 1))

            for y_start, y_end in row_ranges:
                min_x, max_x = end_x + 1, start_x
                min_y, max_y = y_end + 1, y_start
                for y in range(y_start, y_end + 1):
                    for x in range(start_x, end_x + 1):
                        if not is_bg(pixels[x, y]):
                            min_x = min(min_x, x)
                            max_x = max(max_x, x)
                            min_y = min(min_y, y)
                            max_y = max(max_y, y)
                if min_x <= max_x and min_y <= max_y:
                    sprites.append({
                        'x': min_x, 'y': min_y,
                        'w': max_x - min_x + 1,
                        'h': max_y - min_y + 1
                    })
        return sprites

    idle_sprites = find_sprites_in_box(*boxes['idle'])
    walk_sprites = find_sprites_in_box(*boxes['walk'])

    print(f"Found {len(idle_sprites)} idle, {len(walk_sprites)} walk sprites")

    frame_w = 16
    frame_h = 16
    output = Image.new("RGBA", (frame_w * 3, frame_h), (0, 0, 0, 0))

    def extract_frame(sprite_info, frame_index, flip_horizontal=True):
        x, y, w, h = sprite_info['x'], sprite_info['y'], sprite_info['w'], sprite_info['h']

        crop = img.crop((x, y, x + w, y + h)).convert("RGBA")
        data = crop.load()

        for py in range(crop.height):
            for px in range(crop.width):
                if is_bg(data[px, py]):
                    data[px, py] = (0, 0, 0, 0)

        # FLIP HORIZONTALLY so Mario faces RIGHT by default
        if flip_horizontal:
            crop = crop.transpose(Image.FLIP_LEFT_RIGHT)

        if w > frame_w or h > frame_h:
            scale = min(frame_w / w, frame_h / h)
            new_w = max(1, int(w * scale))
            new_h = max(1, int(h * scale))
            crop = crop.resize((new_w, new_h), Image.NEAREST)
            w, h = new_w, new_h

        offset_x = (frame_w - w) // 2
        offset_y = frame_h - h
        dest_x = frame_index * frame_w + offset_x
        output.paste(crop, (dest_x, offset_y), crop)
        print(f"Frame {frame_index}: placed (flipped={flip_horizontal})")

    if idle_sprites:
        extract_frame(idle_sprites[0], 0, flip_horizontal=True)

    if len(walk_sprites) >= 2:
        extract_frame(walk_sprites[0], 1, flip_horizontal=True)
        extract_frame(walk_sprites[1], 2, flip_horizontal=True)
    elif len(walk_sprites) == 1:
        extract_frame(walk_sprites[0], 1, flip_horizontal=True)
        if idle_sprites:
            extract_frame(idle_sprites[0], 2, flip_horizontal=True)

    output.save("assets/smw/sprites/mario_small.png")
    print(f"\nSaved: assets/smw/sprites/mario_small.png (Mario faces RIGHT)")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    extract_mario()
