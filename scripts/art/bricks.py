"""Draws Bricks' art (projects/bricks/assets/): bricks, four paddles, a ball.

Pixel art at the game's own size (a 320x240 screen), shapes drawn without
smoothing, a light edge on top and a dark one below, like scripts/art/keep.py.

- bricks.png, 32x12 frames: 0 red, 1 orange, 2 yellow, 3 green, 4 blue,
  5 steel (two hits), 6 steel cracked (one left), 7 a bomb brick (a spark)
- paddles.png, 48x8 frames: 0-3 the paddles of players 1 to 4 (cyan, magenta,
  lime, amber)
- ball.png, 8x8: the ball

    python scripts/art/bricks.py
CC0.
"""
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[2] / 'projects' / 'bricks' / 'assets'
OUTLINE = (16, 14, 24, 255)

BRICKS = [(214, 64, 64), (232, 128, 48), (236, 200, 56), (88, 184, 88), (72, 132, 220)]
STEEL = (150, 156, 172)
PADDLES = [(64, 220, 230), (230, 80, 200), (150, 230, 70), (240, 176, 48)]


def shade(color, k):
    return tuple(max(0, min(255, int(c * k))) for c in color) + (255,)


def brick(color, cracked=False, bomb=False):
    im = Image.new('RGBA', (32, 12), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 31, 11), fill=OUTLINE)
    d.rectangle((1, 1, 30, 10), fill=shade(color, 1.0))
    d.line((1, 1, 30, 1), fill=shade(color, 1.35))      # light from above
    d.line((1, 1, 1, 10), fill=shade(color, 1.2))
    d.line((1, 10, 30, 10), fill=shade(color, 0.6))     # shadow below
    d.line((30, 2, 30, 10), fill=shade(color, 0.75))
    if cracked:
        for a, b in (((9, 2), (13, 6)), ((13, 6), (11, 9)), ((13, 6), (19, 5)), ((19, 5), (23, 9))):
            d.line(a + b, fill=OUTLINE)
    if bomb:
        d.ellipse((12, 2, 19, 9), fill=(40, 36, 52, 255))
        d.point((17, 3), fill=(255, 255, 255, 255))
        for p in ((20, 1), (21, 2), (22, 1), (21, 0)):
            d.point(p, fill=(255, 220, 80, 255))         # the spark on its fuse
    return im


def paddle(color):
    im = Image.new('RGBA', (48, 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, 47, 7), radius=3, fill=OUTLINE)
    d.rounded_rectangle((1, 1, 46, 6), radius=2, fill=shade(color, 1.0))
    d.line((3, 1, 44, 1), fill=shade(color, 1.4))
    d.line((3, 6, 44, 6), fill=shade(color, 0.6))
    return im


def ball():
    im = Image.new('RGBA', (8, 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((0, 0, 7, 7), fill=OUTLINE)
    d.ellipse((1, 1, 6, 6), fill=(244, 244, 250, 255))
    d.point((2, 2), fill=(255, 255, 255, 255))
    d.point((5, 5), fill=(170, 170, 190, 255))
    return im


def sheet(frames, size):
    im = Image.new('RGBA', (size[0] * len(frames), size[1]), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        im.paste(f, (i * size[0], 0))
    return im


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    frames = [brick(c) for c in BRICKS] + [brick(STEEL), brick(STEEL, cracked=True), brick((96, 60, 140), bomb=True)]
    sheet(frames, (32, 12)).save(OUT / 'bricks.png')
    sheet([paddle(c) for c in PADDLES], (48, 8)).save(OUT / 'paddles.png')
    ball().save(OUT / 'ball.png')
    print('wrote', ', '.join(sorted(p.name for p in OUT.glob('*.png'))))


if __name__ == '__main__':
    main()
