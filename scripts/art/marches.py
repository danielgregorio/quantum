"""Draws Marches' art (projects/marches/assets/), for PLAN_GAMES_3.md's Phase 6: a hex map's land, the units
and the cursor. CC0.

- land.png, 28x32 pointy-topped hexes in a row: grass, forest, hills, marsh, water, rocks, the ford's
  stones (a road), and the keep the riders hold
- units.png, 24x24: a rider, a rider that has acted, a raider, a raider hurt, the rider chosen
- marks.png, 28x32: the cursor, a hex's outline (white, and gold)

    python scripts/art/marches.py
"""
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[2] / 'projects' / 'marches' / 'assets'
W, H = 28, 32
HEX = [(W / 2, 0), (W - 0.5, H / 4), (W - 0.5, 3 * H / 4), (W / 2, H - 0.5), (0, 3 * H / 4), (0, H / 4)]
INK = (24, 22, 30, 255)


def _mask() -> Image.Image:
    """The hexagon's own pixels."""
    m = Image.new('L', (W, H), 0)
    ImageDraw.Draw(m).polygon(HEX, fill=255)
    return m


def hexagon(fill, speckle=None, seed=0) -> Image.Image:
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon(HEX, fill=fill)
    if speckle:
        rng = random.Random(seed)
        inside = _mask()
        for _ in range(26):
            x, y = rng.randrange(3, W - 3), rng.randrange(4, H - 4)
            if inside.getpixel((x, y)):
                im.putpixel((x, y), speckle)
    d.line(HEX + [HEX[0]], fill=(0, 0, 0, 60), width=1)
    return im


def grass(seed=1) -> Image.Image:
    return hexagon((104, 160, 72, 255), (128, 184, 88, 255), seed)


def forest() -> Image.Image:
    im = grass(2)
    d = ImageDraw.Draw(im)
    for x, y in ((9, 12), (19, 11), (14, 20), (8, 22), (20, 22)):
        d.polygon([(x, y - 6), (x + 4, y + 2), (x - 4, y + 2)], fill=(40, 96, 48, 255))
        d.line([(x, y + 2), (x, y + 4)], fill=(90, 60, 30, 255))
    return im


def hills() -> Image.Image:
    im = hexagon((150, 150, 84, 255), (170, 170, 100, 255), 3)
    d = ImageDraw.Draw(im)
    for x, y, r in ((10, 19, 7), (19, 16, 6)):
        d.pieslice((x - r, y - r, x + r, y + r), 180, 360, fill=(120, 118, 66, 255))
        d.arc((x - r, y - r, x + r, y + r), 200, 300, fill=(184, 182, 120, 255))
    return im


def marsh() -> Image.Image:
    im = hexagon((88, 120, 92, 255), (70, 104, 110, 255), 4)
    d = ImageDraw.Draw(im)
    for x, y in ((8, 12), (16, 18), (11, 24), (21, 11)):
        d.line([(x, y), (x, y - 4)], fill=(150, 170, 80, 255))
        d.line([(x + 2, y), (x + 3, y - 3)], fill=(150, 170, 80, 255))
    return im


def water() -> Image.Image:
    im = hexagon((52, 104, 168, 255))
    d = ImageDraw.Draw(im)
    for y in (10, 17, 24):
        d.arc((6, y - 2, 13, y + 2), 200, 340, fill=(120, 170, 220, 255))
        d.arc((15, y - 1, 22, y + 3), 200, 340, fill=(120, 170, 220, 255))
    return im


def rocks() -> Image.Image:
    im = hexagon((110, 104, 112, 255), (130, 124, 132, 255), 6)
    d = ImageDraw.Draw(im)
    d.polygon([(6, 24), (13, 7), (20, 24)], fill=(150, 144, 156, 255))
    d.polygon([(13, 24), (19, 11), (24, 24)], fill=(128, 122, 134, 255))
    d.polygon([(11, 11), (13, 7), (15, 11)], fill=(236, 236, 240, 255))
    return im


def ford() -> Image.Image:
    im = water()
    d = ImageDraw.Draw(im)
    for x, y in ((8, 9), (14, 13), (19, 9), (10, 19), (17, 21), (13, 26)):
        d.ellipse((x - 3, y - 2, x + 3, y + 2), fill=(176, 160, 128, 255), outline=(120, 104, 80, 255))
    return im


def keep() -> Image.Image:
    im = grass(8)
    d = ImageDraw.Draw(im)
    d.rectangle((7, 10, 21, 25), fill=(160, 150, 140, 255), outline=INK)
    for x in (7, 12, 17):
        d.rectangle((x, 7, x + 3, 10), fill=(160, 150, 140, 255), outline=INK)
    d.rectangle((12, 18, 16, 25), fill=(70, 50, 40, 255))
    d.line([(14, 2), (14, 8)], fill=INK)
    d.polygon([(14, 2), (20, 4), (14, 6)], fill=(60, 110, 200, 255))
    return im


def unit(body, trim, acted=False, hurt=False, chosen=False) -> Image.Image:
    im = Image.new('RGBA', (24, 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if acted:
        body = tuple(int(c * 0.55) for c in body[:3]) + (255,)
        trim = tuple(int(c * 0.55) for c in trim[:3]) + (255,)
    if chosen:
        d.ellipse((2, 16, 22, 23), outline=(255, 210, 80, 255), width=2)   # a gold ring at its feet
    else:
        d.ellipse((5, 18, 19, 23), fill=(0, 0, 0, 90))                 # its shadow
    d.polygon([(6, 20), (8, 9), (16, 9), (18, 20)], fill=body, outline=INK)
    d.ellipse((8, 2, 16, 10), fill=(236, 200, 160, 255) if not acted else (130, 110, 88, 255), outline=INK)
    d.rectangle((8, 2, 16, 5), fill=trim)
    d.line([(19, 4), (19, 19)], fill=(200, 200, 210, 255) if not acted else (110, 110, 116, 255), width=2)
    if hurt:
        d.line([(7, 12), (17, 17)], fill=(255, 240, 240, 255), width=2)
    return im


def mark(colour) -> Image.Image:
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.line(HEX + [HEX[0]], fill=colour, width=2)
    return im


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    land = [grass(), forest(), hills(), marsh(), water(), rocks(), ford(), keep()]
    sheet = Image.new('RGBA', (W * len(land), H), (0, 0, 0, 0))
    for i, tile in enumerate(land):
        sheet.paste(tile, (i * W, 0))
    sheet.save(OUT / 'land.png')
    blue, red = (60, 100, 200, 255), (190, 56, 48, 255)
    units = [unit(blue, (230, 200, 70, 255)), unit(blue, (230, 200, 70, 255), acted=True),
             unit(red, (40, 30, 30, 255)), unit(red, (40, 30, 30, 255), hurt=True),
             unit(blue, (230, 200, 70, 255), chosen=True)]
    sheet = Image.new('RGBA', (24 * len(units), 24), (0, 0, 0, 0))
    for i, u in enumerate(units):
        sheet.paste(u, (i * 24, 0))
    sheet.save(OUT / 'units.png')
    marks = [mark((255, 255, 255, 230)), mark((255, 210, 80, 255))]
    sheet = Image.new('RGBA', (W * len(marks), H), (0, 0, 0, 0))
    for i, m in enumerate(marks):
        sheet.paste(m, (i * W, 0))
    sheet.save(OUT / 'marks.png')


if __name__ == '__main__':
    sys.exit(main())
