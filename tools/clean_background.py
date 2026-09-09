"""
Clean background image (yoshi-island-1.png) by removing painted entities
that overlap with interactive game objects.

Only erases: yoshi coins, qblocks, and rotating blocks.
Regular coins are NOT painted in the background.

Uses the transparency key color (248, 0, 248) to fill erased areas.
"""

from PIL import Image
import os

TRANS = (248, 0, 248)  # Magenta transparency key

# Entities CONFIRMED to be painted in the background.
# Format: (name, center_x, center_y, half_w, half_h)

YOSHI_COINS = [
    # yoshi_coin sprite is 16x24 → erase 18x28 (with 1px outline margin)
    ("ycoin1", 279, 271, 9, 14),
    ("ycoin2", 1415, 271, 9, 14),
    ("ycoin3", 2871, 239, 9, 14),
    ("ycoin4", 4615, 271, 9, 14),
]

QBLOCKS = [
    # qblock sprite is 16x16 → erase 18x18 (with 1px outline margin)
    ("qb1", 1927, 327, 9, 9),
    ("qb2", 1943, 327, 9, 9),
    ("qb3", 2503, 327, 9, 9),
    ("qb4", 3351, 247, 9, 9),
    ("qb9", 3831, 327, 9, 9),
    ("qb10", 3895, 279, 9, 9),
    ("qb11", 3895, 343, 9, 9),
    ("qb12", 3959, 327, 9, 9),
]

ROTATING_BLOCKS = [
    # rotating_block 16x16 → erase 18x18
    ("rb1", 3384, 264, 9, 9),
    ("rb2", 3400, 264, 9, 9),
    ("rb3", 3416, 264, 9, 9),
    ("rb4", 3432, 264, 9, 9),
    ("rb5", 3448, 264, 9, 9),
    ("rb6", 3464, 264, 9, 9),
    ("rb7", 3480, 264, 9, 9),
    ("rb8", 3496, 264, 9, 9),
    ("rb9", 3512, 264, 9, 9),
    ("rb10", 3528, 264, 9, 9),
    ("rb11", 3544, 264, 9, 9),
    ("rb12", 3560, 264, 9, 9),
    ("rb13", 3576, 264, 9, 9),
    ("rb14", 3592, 264, 9, 9),
    ("rb15", 3608, 264, 9, 9),
    # Pipe-adjacent rotating blocks
    ("rb16", 3415, 391, 9, 9),
    ("rb17", 3431, 391, 9, 9),
    ("rb18", 3655, 391, 9, 9),
    ("rb19", 3671, 391, 9, 9),
]

ALL_ENTITIES = YOSHI_COINS + QBLOCKS + ROTATING_BLOCKS


def erase_entity(img, name, cx, cy, hw, hh):
    """Replace non-transparent pixels in the entity bounding box with TRANS."""
    w, h = img.size
    left = max(0, cx - hw)
    top = max(0, cy - hh)
    right = min(w, cx + hw + 1)  # +1 for inclusive range
    bottom = min(h, cy + hh + 1)

    erased = 0
    for y in range(top, bottom):
        for x in range(left, right):
            pixel = img.getpixel((x, y))
            if pixel != TRANS:
                img.putpixel((x, y), TRANS)
                erased += 1

    return erased


def main():
    src = "assets/smw/sprites/yoshi-island-1.png"
    dst1 = "assets/smw/sprites/yoshi-island-1.png"
    dst2 = "projects/mario/assets/sprites/yoshi-island-1.png"

    print(f"Loading {src}...")
    img = Image.open(src)
    print(f"  Size: {img.size}, Mode: {img.mode}")
    print(f"  Transparency info: {img.info.get('transparency', 'None')}")

    # Preserve original PNG info
    png_info = img.info.copy()

    total = len(ALL_ENTITIES)
    print(f"\nErasing {total} entities (yoshi coins + qblocks + rotating blocks)...")

    total_erased = 0
    for i, (name, cx, cy, hw, hh) in enumerate(ALL_ENTITIES):
        erased = erase_entity(img, name, cx, cy, hw, hh)
        total_erased += erased
        if erased > 0:
            print(f"  [{i+1}/{total}] {name} at ({cx},{cy}): erased {erased} pixels")
        else:
            print(f"  [{i+1}/{total}] {name} at ({cx},{cy}): no pixels to erase")

    print(f"\nTotal pixels erased: {total_erased}")

    # Save with transparency info preserved
    save_kwargs = {"format": "PNG"}
    if "transparency" in png_info:
        save_kwargs["transparency"] = png_info["transparency"]
    if "dpi" in png_info:
        save_kwargs["dpi"] = png_info["dpi"]

    for dst in [dst1, dst2]:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        img.save(dst, **save_kwargs)
        print(f"  Saved: {dst}")

    print("\nDone! Background cleaned.")


if __name__ == "__main__":
    main()
