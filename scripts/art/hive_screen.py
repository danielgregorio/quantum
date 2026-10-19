"""Draws the Hive's screen art (os/config/screen/art/): the cells of a honeycomb, one a service, and a bee.

Pixel art at the screen's own size (a 320x180 scene), shapes drawn without
smoothing, like scripts/art/keep.py.

- cells.png, 24x24 frames: 0 a cell with honey (the service runs), 1 an empty
  cell (it is off), 2 a cracked cell (it crashed), 3-6 smoke rising from the
  cracked cell, 7 a dim cell (something is wrong in its logs)
- bee.png, 16x16 frames: 0 and 1 the bee, wings up and down

    python scripts/art/hive_screen.py
CC0.
"""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[2] / 'os' / 'config' / 'screen' / 'art'

WAX, WAX_DARK, WAX_LIGHT = (196, 150, 52, 255), (132, 96, 30, 255), (228, 190, 92, 255)
HONEY, HONEY_LIGHT = (240, 170, 40, 255), (252, 212, 110, 255)
EMPTY = (62, 50, 34, 255)
CRACK = (28, 20, 12, 255)
SMOKE, SMOKE_LIGHT = (120, 120, 128, 255), (170, 170, 178, 255)
CLEAR = (0, 0, 0, 0)

# a flat-topped hexagon that fits 24x24, one column of edge pixels per row
HEX = [(7, 16), (5, 18), (3, 20), (2, 21), (1, 22), (1, 22), (0, 23), (0, 23), (0, 23), (0, 23), (0, 23), (0, 23),
       (0, 23), (0, 23), (0, 23), (0, 23), (0, 23), (0, 23), (1, 22), (1, 22), (2, 21), (3, 20), (5, 18), (7, 16)]


def cell(filling, light=None):
    im = Image.new('RGBA', (24, 24), CLEAR)
    px = im.load()
    for y, (x0, x1) in enumerate(HEX):
        for x in range(x0, x1 + 1):
            edge = x in (x0, x1) or y in (0, 23) or (y < 6 and x in (x0 + 1, x1 - 1)) or (y > 17 and x in (x0 + 1, x1 - 1))
            if edge:
                px[x, y] = WAX_DARK if (y > 12 or x > 12) else WAX
            else:
                px[x, y] = filling
    if light is not None:
        for x, y in ((8, 6), (9, 6), (8, 7), (7, 8)):
            px[x, y] = light
    for x, y in ((2, 7), (3, 7), (2, 8)):
        px[x, y] = WAX_LIGHT
    return im


def honey():
    return cell(HONEY, HONEY_LIGHT)


def empty():
    return cell(EMPTY)


def cracked():
    im = cell(EMPTY)
    d = ImageDraw.Draw(im)
    d.line([(11, 4), (12, 9), (9, 12), (12, 16), (10, 20)], fill=CRACK)
    d.line([(12, 9), (16, 11)], fill=CRACK)
    d.line([(9, 12), (5, 13)], fill=CRACK)
    for x, y in ((13, 10), (10, 13), (13, 17)):
        im.putpixel((x, y), WAX_DARK)
    return im


def smoke(step):
    """The cracked cell with a puff rising: step 0 just above the crack, 3 high and thin."""
    im = cracked()
    d = ImageDraw.Draw(im)
    puffs = [
        [((9, 9, 13, 12), SMOKE)],
        [((8, 5, 14, 10), SMOKE), ((10, 3, 13, 6), SMOKE_LIGHT)],
        [((7, 1, 12, 6), SMOKE), ((12, 0, 16, 4), SMOKE_LIGHT), ((10, 7, 13, 9), SMOKE)],
        [((9, 0, 12, 2), SMOKE_LIGHT), ((14, 0, 17, 2), SMOKE_LIGHT)],
    ][step]
    for box, colour in puffs:
        d.ellipse(box, fill=colour)
    return im


def dim():
    im = cell((150, 110, 36, 255))
    im.putpixel((11, 7), WAX_DARK)
    im.putpixel((11, 8), WAX_DARK)
    im.putpixel((11, 9), WAX_DARK)
    im.putpixel((11, 11), WAX_DARK)
    return im


def bee(wings_up):
    im = Image.new('RGBA', (16, 16), CLEAR)
    d = ImageDraw.Draw(im)
    body = (236, 196, 50, 255)
    stripe = (40, 32, 20, 255)
    wing = (210, 230, 250, 255)
    d.ellipse((3, 6, 13, 13), fill=body, outline=stripe)
    for x in (6, 9):
        d.line([(x, 7), (x, 12)], fill=stripe)
    d.ellipse((1, 7, 5, 11), fill=stripe)          # the head
    im.putpixel((2, 8), (255, 255, 255, 255))      # an eye
    if wings_up:
        d.ellipse((5, 1, 9, 6), fill=wing, outline=(120, 140, 170, 255))
        d.ellipse((8, 1, 12, 6), fill=wing, outline=(120, 140, 170, 255))
    else:
        d.ellipse((5, 4, 10, 7), fill=wing, outline=(120, 140, 170, 255))
        d.ellipse((8, 4, 13, 7), fill=wing, outline=(120, 140, 170, 255))
    d.point((14, 10), fill=stripe)                 # the sting
    return im


def sheet(frames, size):
    im = Image.new('RGBA', (size * len(frames), size), CLEAR)
    for i, frame in enumerate(frames):
        im.paste(frame, (i * size, 0))
    return im


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sheet([honey(), empty(), cracked(), smoke(0), smoke(1), smoke(2), smoke(3), dim()], 24).save(OUT / 'cells.png')
    sheet([bee(True), bee(False)], 16).save(OUT / 'bee.png')
    print(f'wrote {OUT / "cells.png"} and {OUT / "bee.png"}')


if __name__ == '__main__':
    main()
