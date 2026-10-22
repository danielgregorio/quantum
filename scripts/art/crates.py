"""Draws Crates' art (projects/crates/assets/): a dockside warehouse seen from above.

Pixel art at the game's own size (a 320x192 screen of 16x16 tiles), drawn
without smoothing and outlined, like scripts/art/siege.py.

- warehouse.png, 16x16 tiles: 0 concrete, 1 brick wall, 2 a wall's corner
  (the top-left one: Tiled flips it for the other three), 3 a wall's top
  edge (flipped upside down for the bottom one, across the diagonal for the
  sides), 4 a pad painted on the concrete, 5 planks, 6 an arrow on the floor
  (to the right: flipped for the left), 7 hazard stripes
- water.png, 16x16 tiles: 0-3 the harbour's water (an animated tile, its four
  frames in turn), 4 a pier's planks over it
- people.png, 16x16 frames: 0 the worker, 1-2 walking, 3 pushing, 4 the
  foreman, 5 the foreman pleased, 6 a crate, 7 a barrel, 8 a gate shut, 9 a
  gate locked, 10 a key, 11-12 a gull
- faces.png, 32x32 frames: 0 the foreman, 1 the foreman pleased, 2 the worker

    python scripts/art/crates.py
CC0.
"""
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[2] / 'projects' / 'crates' / 'assets'
OUTLINE = (24, 20, 28, 255)


def rgb(r, g, b):
    return (r, g, b, 255)


CONCRETE, CONCRETE_DARK, CONCRETE_LIGHT = rgb(122, 124, 128), rgb(104, 106, 112), rgb(138, 140, 144)
BRICK, BRICK_DARK, MORTAR = rgb(150, 72, 52), rgb(116, 52, 40), rgb(70, 40, 36)
WOOD, WOOD_DARK, WOOD_LIGHT = rgb(176, 122, 66), rgb(126, 82, 42), rgb(206, 156, 96)
YELLOW = rgb(236, 196, 60)
SKIN = rgb(232, 188, 150)


def tile(fill=(0, 0, 0, 0), size=16):
    return Image.new('RGBA', (size, size), fill)


def concrete(rnd=None):
    rnd = rnd or random.Random(5)
    im = tile(CONCRETE)
    d = ImageDraw.Draw(im)
    for _ in range(10):
        d.point((rnd.randrange(16), rnd.randrange(16)), fill=CONCRETE_DARK)
    for _ in range(4):
        d.point((rnd.randrange(16), rnd.randrange(16)), fill=CONCRETE_LIGHT)
    d.line((0, 15, 15, 15), fill=CONCRETE_DARK)
    d.line((15, 0, 15, 15), fill=CONCRETE_DARK)
    return im


def brick():
    im = tile(BRICK)
    d = ImageDraw.Draw(im)
    for row, y in enumerate((0, 4, 8, 12)):
        d.line((0, y + 3, 15, y + 3), fill=MORTAR)
        off = 0 if row % 2 == 0 else 4
        for x in range(off, 16, 8):
            d.line((x, y, x, y + 3), fill=MORTAR)
        d.line((0, y, 15, y), fill=BRICK_DARK)
    return im


def corner():
    """The top-left outer corner of a wall: its lit edge along the top and the left."""
    im = brick()
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 15, 2), fill=rgb(196, 120, 92))
    d.rectangle((0, 0, 2, 15), fill=rgb(196, 120, 92))
    d.rectangle((0, 0, 2, 2), fill=rgb(230, 170, 140))
    return im


def edge():
    """A wall's top edge: its lit coping along the top."""
    im = brick()
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 15, 2), fill=rgb(196, 120, 92))
    d.line((0, 3, 15, 3), fill=MORTAR)
    return im


def pad():
    im = concrete(random.Random(9))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 15, 15), outline=YELLOW)
    d.rectangle((1, 1, 14, 14), outline=rgb(196, 160, 40))
    for a in range(2, 14, 4):
        d.point((a, a), fill=YELLOW)
        d.point((15 - a, a), fill=YELLOW)
    return im


def planks():
    im = tile(WOOD)
    d = ImageDraw.Draw(im)
    for y in (0, 5, 10):
        d.line((0, y, 15, y), fill=WOOD_DARK)
        d.line((0, y + 1, 15, y + 1), fill=WOOD_LIGHT)
    for x, y in ((6, 2), (12, 7), (3, 12)):
        d.line((x, y, x, y + 2), fill=WOOD_DARK)
    return im


def arrow():
    im = concrete(random.Random(11))
    d = ImageDraw.Draw(im)
    d.rectangle((3, 7, 9, 8), fill=YELLOW)
    d.polygon(((9, 4), (13, 7.5), (9, 11)), fill=YELLOW)
    return im


def stripes():
    im = tile(rgb(40, 40, 44))
    d = ImageDraw.Draw(im)
    for k in range(-16, 16, 6):
        d.polygon(((k, 15), (k + 3, 15), (k + 18, 0), (k + 15, 0)), fill=YELLOW)
    return im


def water(frame):
    im = tile(rgb(40, 88, 140))
    d = ImageDraw.Draw(im)
    for row in range(4):
        y = row * 4 + 1
        for x in range(16):
            # a wave that moves a quarter of the tile each frame, so the four frames loop
            if math.sin((x + frame * 4 + row * 3) * math.pi / 8) > 0.7:
                d.point((x, y), fill=rgb(110, 170, 210))
            elif math.sin((x + frame * 4 + row * 3) * math.pi / 8) < -0.8:
                d.point((x, y + 1), fill=rgb(30, 70, 116))
    return im


def pier():
    im = water(0)
    d = ImageDraw.Draw(im)
    d.rectangle((1, 0, 14, 15), fill=WOOD_DARK)
    for x in (1, 6, 11):
        d.rectangle((x, 0, x + 3, 15), fill=WOOD)
        d.line((x, 0, x, 15), fill=WOOD_LIGHT)
    return im


def worker(step=None, push=False):
    im = tile()
    d = ImageDraw.Draw(im)
    feet = ((5, 12), (9, 12)) if step is None else (((4, 12), (10, 13)) if step == 0 else ((5, 13), (9, 12)))
    for x, y in feet:
        d.rectangle((x, y, x + 1, y + 2), fill=OUTLINE)
    d.ellipse((3, 5, 12, 13), fill=OUTLINE)
    d.ellipse((4, 6, 11, 12), fill=rgb(230, 120, 40))      # the overalls, orange
    d.line((6, 6, 6, 11), fill=rgb(250, 220, 80))          # a reflective stripe
    d.ellipse((5, 1, 11, 7), fill=OUTLINE)
    d.ellipse((6, 2, 10, 6), fill=SKIN)
    d.rectangle((5, 1, 11, 3), fill=rgb(250, 210, 40))      # the hard hat
    if push:
        d.rectangle((11, 7, 15, 9), fill=OUTLINE)
        d.rectangle((12, 8, 15, 8), fill=SKIN)               # arms out, to the right
    return im


def foreman(pleased=False):
    im = tile()
    d = ImageDraw.Draw(im)
    for x in (5, 9):
        d.rectangle((x, 12, x + 1, 14), fill=OUTLINE)
    d.ellipse((2, 5, 13, 13), fill=OUTLINE)
    d.ellipse((3, 6, 12, 12), fill=rgb(60, 90, 150))       # a blue coat
    d.ellipse((5, 1, 11, 7), fill=OUTLINE)
    d.ellipse((6, 2, 10, 6), fill=SKIN)
    d.rectangle((5, 1, 11, 2), fill=rgb(240, 240, 240))     # a white hat: the foreman
    d.line((7, 5, 9, 5), fill=OUTLINE)                      # a moustache
    if pleased:
        d.line((2, 7, 0, 3), fill=OUTLINE)
        d.line((13, 7, 15, 3), fill=OUTLINE)                # arms up
    else:
        d.rectangle((12, 8, 14, 11), fill=rgb(230, 230, 220))  # a clipboard
    return im


def crate():
    im = tile()
    d = ImageDraw.Draw(im)
    d.rectangle((2, 2, 13, 13), fill=OUTLINE)
    d.rectangle((3, 3, 12, 12), fill=WOOD)
    d.rectangle((3, 3, 12, 4), fill=WOOD_LIGHT)
    d.line((3, 3, 12, 12), fill=WOOD_DARK)
    d.line((12, 3, 3, 12), fill=WOOD_DARK)
    d.rectangle((3, 3, 12, 12), outline=WOOD_DARK)
    return im


def barrel():
    im = tile()
    d = ImageDraw.Draw(im)
    d.ellipse((2, 2, 13, 13), fill=OUTLINE)
    d.ellipse((3, 3, 12, 12), fill=rgb(70, 120, 80))
    d.ellipse((5, 5, 10, 10), outline=rgb(160, 160, 170))  # its hoop, from above
    d.point((6, 5), fill=rgb(130, 180, 140))
    return im


def gate(locked=False):
    im = concrete(random.Random(13))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 1, 15, 14), fill=OUTLINE)
    for x in range(1, 16, 3):
        d.rectangle((x, 2, x + 1, 13), fill=rgb(150, 156, 166))
    d.rectangle((0, 6, 15, 8), fill=rgb(110, 116, 126))
    if locked:
        d.rectangle((5, 6, 10, 12), fill=OUTLINE)
        d.rectangle((6, 8, 9, 11), fill=YELLOW)
        d.arc((5, 3, 10, 9), 180, 360, fill=OUTLINE)
        d.point((7, 9), fill=OUTLINE)
    return im


def key():
    im = tile()
    d = ImageDraw.Draw(im)
    d.ellipse((2, 4, 8, 10), fill=OUTLINE)
    d.ellipse((3, 5, 7, 9), fill=YELLOW)
    d.ellipse((4, 6, 6, 8), fill=OUTLINE)
    d.rectangle((7, 6, 14, 8), fill=OUTLINE)
    d.line((8, 7, 13, 7), fill=YELLOW)
    d.rectangle((11, 8, 12, 10), fill=OUTLINE)
    return im


def gull(up):
    im = tile()
    d = ImageDraw.Draw(im)
    white = rgb(240, 240, 240)
    wing = ((1, 4 if up else 9), (7, 7), (14, 4 if up else 9))
    d.line(wing, fill=OUTLINE, width=3)
    d.line(wing, fill=white)
    d.ellipse((6, 6, 9, 9), fill=white)
    d.point((10, 7), fill=YELLOW)
    return im


def pointer():
    im = tile()
    d = ImageDraw.Draw(im)
    for (x, y), (dx, dy) in (((0, 0), (1, 1)), ((15, 0), (-1, 1)), ((0, 15), (1, -1)), ((15, 15), (-1, -1))):
        d.line((x, y, x + 4 * dx, y), fill=rgb(255, 255, 255))      # a corner of the cell, each way
        d.line((x, y, x, y + 4 * dy), fill=rgb(255, 255, 255))
    return im


def face(who, pleased=False):
    im = tile(rgb(52, 60, 84), 32)
    d = ImageDraw.Draw(im)
    coat = rgb(60, 90, 150) if who == 'foreman' else rgb(230, 120, 40)
    d.ellipse((4, 22, 28, 40), fill=OUTLINE)
    d.ellipse((5, 23, 27, 40), fill=coat)
    d.ellipse((8, 5, 24, 24), fill=OUTLINE)
    d.ellipse((9, 6, 23, 23), fill=SKIN)
    if who == 'foreman':
        d.rectangle((7, 3, 25, 9), fill=rgb(240, 240, 240))
        d.rectangle((11, 17, 21, 18), fill=rgb(90, 60, 40))   # the moustache
        mouth = (13, 19, 19, 22) if pleased else None
        if mouth:
            d.arc(mouth, 0, 180, fill=OUTLINE)
        brow = 11 if pleased else 12
        d.line((11, brow, 14, brow - (1 if pleased else 0)), fill=OUTLINE)
        d.line((18, brow - (1 if pleased else 0), 21, brow), fill=OUTLINE)
    else:
        d.rectangle((7, 3, 25, 9), fill=rgb(250, 210, 40))
        d.arc((12, 16, 20, 21), 0, 180, fill=OUTLINE)
    d.point((13, 14), fill=OUTLINE)
    d.point((19, 14), fill=OUTLINE)
    return im


def sheet(frames, size=16):
    out = Image.new('RGBA', (size * len(frames), size), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        out.paste(f, (size * i, 0))
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sheet([concrete(), brick(), corner(), edge(), pad(), planks(), arrow(), stripes()]).save(OUT / 'warehouse.png')
    sheet([water(0), water(1), water(2), water(3), pier()]).save(OUT / 'water.png')
    sheet([worker(), worker(0), worker(1), worker(push=True), foreman(), foreman(True), crate(), barrel(),
           gate(), gate(True), key(), gull(True), gull(False), pointer()]).save(OUT / 'people.png')
    sheet([face('foreman'), face('foreman', True), face('worker')], 32).save(OUT / 'faces.png')
    print('wrote', ', '.join(str(OUT / n) for n in ('warehouse.png', 'water.png', 'people.png', 'faces.png')))


if __name__ == '__main__':
    main()
