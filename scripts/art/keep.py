"""Draws Keep's art (projects/keep/assets/): a dungeon seen from above, its hero and monsters.

Pixel art at the game's own size (a 256x224 screen), shapes drawn without
smoothing and outlined, like scripts/art/drift.py.

- dungeon.png, 18x18 tiles: 0 floor, 1 wall, 2 door, 3 gate, 4 switch, 5 switch
  (pressed), 6 sign, 7 chest, 8 key, 9 heart
- hero.png, 24x24 frames: 0 idle, 1-2 walking (to the right), 3-4 walking up,
  5-6 walking down, 7 the sword swung right, 8 up, 9 down; 10-12 a slime,
  13-15 a bat

    python scripts/art/keep.py
CC0.
"""
import random
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[2] / 'projects' / 'keep' / 'assets'
OUTLINE = (20, 16, 26, 255)


def outlined(im):
    px = im.load()
    w, h = im.size
    out = im.copy()
    po = out.load()
    for y in range(h):
        for x in range(w):
            if px[x, y][3] == 0 and any(0 <= x + dx < w and 0 <= y + dy < h and px[x + dx, y + dy][3] > 0
                                        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                po[x, y] = OUTLINE
    return out


# ---- tiles ----

FLOOR, SEAM, CRACK = (58, 54, 72), (44, 40, 56), (50, 46, 62)


def floor(rnd=random.Random(3)):
    im = Image.new('RGBA', (18, 18), FLOOR)
    d = ImageDraw.Draw(im)
    d.line([(0, 8), (17, 8)], fill=SEAM)
    d.line([(0, 17), (17, 17)], fill=SEAM)
    d.line([(8, 0), (8, 8)], fill=SEAM)
    d.line([(13, 9), (13, 17)], fill=SEAM)
    d.line([(17, 0), (17, 8)], fill=SEAM)
    d.line([(4, 9), (4, 17)], fill=SEAM)
    for _ in range(6):
        d.point((rnd.randrange(18), rnd.randrange(18)), fill=CRACK)
    d.line([(1, 1), (6, 1)], fill=(66, 62, 80))
    d.line([(10, 10), (12, 10)], fill=(66, 62, 80))
    return im


def wall():
    im = Image.new('RGBA', (18, 18), (92, 84, 108))
    d = ImageDraw.Draw(im)
    for row, y in enumerate((0, 6, 12)):
        d.line([(0, y + 5), (17, y + 5)], fill=(40, 34, 48))
        off = 0 if row % 2 == 0 else 4
        for x in range(off, 18, 9):
            d.line([(x, y), (x, y + 5)], fill=(40, 34, 48))
        d.line([(0, y), (17, y)], fill=(126, 116, 142))
    return im


def door():
    im = floor()
    d = ImageDraw.Draw(im)
    d.rectangle([1, 0, 16, 17], fill=(120, 74, 40))
    for x in (5, 9, 13):
        d.line([(x, 0), (x, 17)], fill=(92, 54, 28))
    for y in (3, 13):
        d.rectangle([1, y, 16, y + 1], fill=(70, 70, 82))
    d.rectangle([7, 7, 10, 10], fill=(220, 180, 70))
    d.point((8, 9), fill=OUTLINE)
    return im


def gate():
    im = floor()
    d = ImageDraw.Draw(im)
    for x in (1, 5, 9, 13, 16):
        d.line([(x, 0), (x, 17)], fill=(150, 150, 168))
        d.point((x, 0), fill=(200, 200, 216))
    d.rectangle([0, 3, 17, 4], fill=(110, 110, 124))
    d.rectangle([0, 13, 17, 14], fill=(110, 110, 124))
    return im


def switch(on):
    im = Image.new('RGBA', (18, 18), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([2, 10, 15, 15], fill=(110, 104, 120))
    d.rectangle([3, 11, 14, 14], fill=(86, 80, 96))
    if on:
        d.line([(9, 12), (13, 4)], fill=(180, 180, 190), width=2)
        d.rectangle([12, 2, 14, 4], fill=(90, 220, 110))
    else:
        d.line([(8, 12), (4, 4)], fill=(180, 180, 190), width=2)
        d.rectangle([3, 2, 5, 4], fill=(220, 80, 70))
    return outlined(im)


def sign():
    im = Image.new('RGBA', (18, 18), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([8, 10, 9, 16], fill=(110, 70, 40))
    d.rectangle([2, 2, 15, 10], fill=(176, 120, 64))
    for y in (4, 6, 8):
        d.line([(4, y), (13, y)], fill=(110, 70, 40))
    return outlined(im)


def chest():
    im = Image.new('RGBA', (18, 18), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([2, 4, 15, 15], fill=(150, 90, 40))
    d.rectangle([2, 4, 15, 7], fill=(178, 112, 54))
    d.rectangle([2, 8, 15, 8], fill=(220, 180, 70))
    d.rectangle([7, 7, 10, 11], fill=(240, 200, 80))
    d.point((8, 10), fill=OUTLINE)
    d.line([(2, 15), (15, 15)], fill=(110, 64, 28))
    return outlined(im)


def key():
    im = Image.new('RGBA', (18, 18), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([2, 3, 8, 9], fill=(240, 200, 70))
    d.ellipse([4, 5, 6, 7], fill=(0, 0, 0, 0))
    d.rectangle([7, 5, 15, 7], fill=(240, 200, 70))
    d.rectangle([12, 8, 13, 10], fill=(240, 200, 70))
    d.rectangle([15, 8, 15, 10], fill=(240, 200, 70))
    d.point((3, 4), fill=(255, 240, 180))
    return outlined(im)


def heart():
    im = Image.new('RGBA', (18, 18), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([3, 4, 9, 10], fill=(230, 50, 70))
    d.ellipse([8, 4, 14, 10], fill=(230, 50, 70))
    d.polygon([(3, 8), (14, 8), (9, 15), (8, 15)], fill=(230, 50, 70))
    d.point([(5, 6), (6, 5)], fill=(255, 180, 190))
    return outlined(im)


# ---- the hero, the slime, the bat ----

SKIN, HAIR, TUNIC, TUNIC_D, BELT, BOOT = (240, 196, 150), (120, 70, 40), (60, 150, 80), (40, 110, 60), (110, 70, 40), (80, 52, 36)
BLADE, HILT = (220, 226, 236), (230, 180, 60)


def hero(view, step=0, attack=False):
    """view: 'down', 'up', 'side' (facing right). step: 0, 1 or -1 (the legs)."""
    im = Image.new('RGBA', (24, 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # legs and boots
    if view == 'side':
        d.rectangle([10 + step, 17, 12 + step, 20], fill=BOOT)
        d.rectangle([12 - step, 17, 14 - step, 20], fill=BOOT)
    else:
        d.rectangle([9, 17 + max(step, 0), 11, 20], fill=BOOT)
        d.rectangle([13, 17 + max(-step, 0), 15, 20], fill=BOOT)
    # body
    d.rectangle([8, 11, 15, 17], fill=TUNIC)
    d.rectangle([8, 15, 15, 17], fill=TUNIC_D)
    d.line([(8, 14), (15, 14)], fill=BELT)
    # head
    d.rectangle([8, 3, 15, 10], fill=SKIN)
    if view == 'down':
        d.rectangle([8, 3, 15, 5], fill=HAIR)
        d.point([(10, 7), (13, 7)], fill=OUTLINE)
        d.rectangle([7, 12, 7, 15], fill=SKIN)
        d.rectangle([16, 12, 16, 15], fill=SKIN)
    elif view == 'up':
        d.rectangle([8, 3, 15, 9], fill=HAIR)
        d.rectangle([7, 12, 7, 15], fill=SKIN)
        d.rectangle([16, 12, 16, 15], fill=SKIN)
    else:
        d.rectangle([8, 3, 15, 5], fill=HAIR)
        d.rectangle([8, 3, 10, 9], fill=HAIR)
        d.point((14, 7), fill=OUTLINE)
        d.point((16, 8), fill=SKIN)
    if attack:
        if view == 'side':
            d.rectangle([15, 12, 17, 13], fill=SKIN)          # the arm, out
            d.rectangle([18, 11, 18, 14], fill=HILT)
            d.rectangle([19, 12, 23, 13], fill=BLADE)
        elif view == 'up':
            d.rectangle([16, 6, 17, 11], fill=SKIN)
            d.rectangle([15, 5, 18, 5], fill=HILT)
            d.rectangle([16, 0, 17, 4], fill=BLADE)
        else:
            d.rectangle([16, 15, 17, 17], fill=SKIN)
            d.rectangle([15, 18, 18, 18], fill=HILT)
            d.rectangle([16, 19, 17, 23], fill=BLADE)
    elif view == 'side':
        d.rectangle([11, 12, 13, 15], fill=SKIN)              # the near arm, swinging with the step
    return outlined(im)


def slime(squash):
    im = Image.new('RGBA', (24, 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    h = (7, 9, 8)[squash]
    w = (16, 12, 14)[squash]
    x0 = 12 - w // 2
    d.ellipse([x0, 20 - h * 2, x0 + w, 20], fill=(90, 200, 90))
    d.rectangle([x0, 16, x0 + w, 20], fill=(90, 200, 90))
    d.ellipse([x0 + 2, 20 - h * 2 + 2, x0 + 6, 20 - h * 2 + 5], fill=(190, 250, 190))
    d.point([(10, 15), (14, 15)], fill=OUTLINE)
    return outlined(im)


def bat(wing):
    im = Image.new('RGBA', (24, 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    body = (120, 70, 150)
    d.ellipse([9, 9, 15, 16], fill=body)
    d.polygon([(10, 9), (11, 6), (12, 9)], fill=body)
    d.polygon([(12, 9), (13, 6), (14, 9)], fill=body)
    tip = (4, 12, 20)[wing]
    d.polygon([(9, 11), (1, tip), (4, 15), (9, 14)], fill=(90, 50, 120))
    d.polygon([(15, 11), (23, tip), (20, 15), (15, 14)], fill=(90, 50, 120))
    d.point([(11, 11), (13, 11)], fill=(255, 220, 90))
    return outlined(im)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tiles = [floor(), wall(), door(), gate(), switch(False), switch(True), sign(), chest(), key(), heart()]
    sheet = Image.new('RGBA', (18 * len(tiles), 18))
    for i, t in enumerate(tiles):
        sheet.paste(t, (i * 18, 0))
    sheet.save(OUT / 'dungeon.png', optimize=True)
    frames = [hero('down'), hero('side', 1), hero('side', -1), hero('up', 1), hero('up', -1),
              hero('down', 1), hero('down', -1), hero('side', attack=True), hero('up', attack=True),
              hero('down', attack=True), slime(0), slime(1), slime(2), bat(0), bat(1), bat(2)]
    sheet = Image.new('RGBA', (24 * len(frames), 24))
    for i, f in enumerate(frames):
        sheet.paste(f, (i * 24, 0))
    sheet.save(OUT / 'hero.png', optimize=True)
    print(OUT)


if __name__ == '__main__':
    main()
