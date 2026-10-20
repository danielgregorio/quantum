"""Draws the Hive's screen art (os/config/screen/art/): the cells of a honeycomb, one a service, and a bee.

Pixel art at the screen's own size (a 320x180 scene), shapes drawn without
smoothing, like scripts/art/keep.py.

- cells.png, 24x24 frames, each a rounded cell of wax with a bevel and a
  2-px shadow: 0 a cell with honey (the service runs), 1 an empty cell (it
  is off), 2 a cracked cell (it crashed), 3-6 smoke rising from the cracked
  cell, 7 a dim cell (something is wrong in its logs)
- bee.png, 16x16 frames: 0 and 1 the bee, wings up and down

    python scripts/art/hive_screen.py
CC0.
"""
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[2] / 'os' / 'config' / 'screen' / 'art'

# the wax of a cell: its body, the lit rim at the top left, the dark rim and the hollow inside
WAX, WAX_LIGHT, WAX_DARK = (62, 50, 34, 255), (132, 96, 30, 255), (28, 20, 12, 255)
HOLLOW = (44, 34, 22, 255)
HONEY, HONEY_LIGHT = (240, 170, 40, 255), (252, 212, 110, 255)
DIM = (150, 110, 36, 255)
CRACK = (28, 20, 12, 255)
SMOKE, SMOKE_LIGHT = (120, 120, 128, 255), (170, 170, 178, 255)
SHADOW = (0, 0, 0, 90)
CLEAR = (0, 0, 0, 0)


def cell(core=None):
    """A cell of the comb in the look of the screen's windows: a rounded body of wax with a bevel (lit at the top
    left, dark at the bottom right), a 2-px shadow down and right inside the 24x24 frame, and a hollow that holds
    `core` (honey when the service runs) or nothing."""
    im = Image.new('RGBA', (24, 24), CLEAR)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([2, 2, 23, 23], radius=6, fill=SHADOW)
    d.rounded_rectangle([0, 0, 21, 21], radius=6, fill=WAX, outline=WAX_DARK)
    d.arc([0, 0, 21, 21], 180, 300, fill=WAX_LIGHT)
    d.rounded_rectangle([3, 3, 18, 18], radius=5, fill=HOLLOW)
    if core is not None:
        d.rounded_rectangle([5, 5, 16, 16], radius=4, fill=core)
    return im


def honey():
    im = cell(HONEY)
    for x, y in ((7, 7), (8, 7), (7, 8)):
        im.putpixel((x, y), HONEY_LIGHT)
    return im


def empty():
    return cell()


def cracked():
    im = cell()
    d = ImageDraw.Draw(im)
    d.line([(10, 3), (12, 8), (9, 11), (12, 15), (10, 19)], fill=CRACK)
    d.line([(12, 8), (16, 9)], fill=CRACK)
    d.line([(9, 11), (5, 12)], fill=CRACK)
    for x, y in ((13, 9), (10, 12), (13, 16)):
        im.putpixel((x, y), WAX_LIGHT)
    return im


def smoke(step):
    """The cracked cell with a puff rising: step 0 just above the crack, 3 high and thin."""
    im = cracked()
    d = ImageDraw.Draw(im)
    puffs = [
        [((8, 8, 12, 11), SMOKE)],
        [((7, 4, 13, 9), SMOKE), ((9, 2, 12, 5), SMOKE_LIGHT)],
        [((6, 0, 11, 5), SMOKE), ((11, 0, 15, 3), SMOKE_LIGHT), ((9, 6, 12, 8), SMOKE)],
        [((8, 0, 11, 1), SMOKE_LIGHT), ((13, 0, 16, 1), SMOKE_LIGHT)],
    ][step]
    for box, colour in puffs:
        d.ellipse(box, fill=colour)
    return im


def dim():
    im = cell(DIM)
    for y in (7, 8, 9, 11):
        im.putpixel((10, y), WAX_DARK)
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
