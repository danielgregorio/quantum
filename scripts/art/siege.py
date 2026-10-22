"""Draws Siege's art (projects/siege/assets/): the ground, and the things of a siege.

Pixel art at the game's own size (a 320x240 screen, 16-pixel tiles), seen
from above, shapes drawn without smoothing, a dark outline, like
scripts/art/bricks.py.

- ground.png, 16x16 tiles: 0 grass, 1 grass with flowers, 2 the keep's
  floor (flagstones), 3 a wall
- siege.png, 16x16 frames: 0-1 the archer walking (blue), 2-3 the knight on
  a horse, 4-5 a raider walking (red hood), 6-7 a brute walking, 8 an
  arrow (pointing right), 9 a bolt (pointing right, glowing), 10 a ram (its
  shield on its right, the way it goes), 11 the tower, 12 the aim's cross

    python scripts/art/siege.py
CC0.
"""
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[2] / 'projects' / 'siege' / 'assets'
OUTLINE = (20, 18, 16, 255)


def rgb(*c):
    return tuple(c) + (255,)


GRASS = rgb(76, 116, 52)
GRASS_DARK = rgb(62, 98, 42)
STONE = rgb(150, 144, 132)
STONE_DARK = rgb(110, 104, 96)
STONE_LIGHT = rgb(186, 180, 166)


def tile():
    return Image.new('RGBA', (16, 16), (0, 0, 0, 0))


def grass(flowers=False):
    im = tile()
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 15, 15), fill=GRASS)
    for x, y in ((2, 3), (9, 1), (13, 6), (5, 10), (11, 12), (1, 14), (7, 6)):
        d.line((x, y, x, y + 1), fill=GRASS_DARK)          # tufts
    if flowers:
        for (x, y), c in (((4, 4), rgb(240, 220, 90)), ((11, 9), rgb(240, 240, 240)), ((6, 13), rgb(220, 120, 200))):
            d.point((x, y), fill=c)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                d.point((x + dx, y + dy), fill=rgb(250, 250, 210))
    return im


def floor():
    im = tile()
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 15, 15), fill=rgb(132, 124, 112))
    for box in ((0, 0, 7, 7), (8, 0, 15, 7), (0, 8, 7, 15), (8, 8, 15, 15)):
        d.rectangle(box, outline=rgb(104, 98, 90))
        d.line((box[0] + 1, box[1] + 1, box[2] - 1, box[1] + 1), fill=rgb(150, 142, 128))
    return im


def wall():
    im = tile()
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 15, 15), fill=STONE_DARK)
    for y0 in (0, 5, 10):
        off = 0 if (y0 // 5) % 2 == 0 else 4
        for x0 in range(-4 + off, 16, 8):
            d.rectangle((x0, y0, x0 + 7, y0 + 4), fill=STONE, outline=STONE_DARK)
            d.line((x0 + 1, y0 + 1, x0 + 6, y0 + 1), fill=STONE_LIGHT)
    d.rectangle((0, 15, 15, 15), fill=OUTLINE)
    return im


def person(cloth, step, hood=None, bow=False, big=False):
    """Seen from above: a round head on shoulders, the feet out by turns."""
    im = tile()
    d = ImageDraw.Draw(im)
    feet = ((5, 12), (10, 13)) if step == 0 else ((5, 13), (10, 12))
    for x, y in feet:
        d.rectangle((x, y, x + 1, y + 2), fill=OUTLINE)
    body = (2, 5, 13, 13) if big else (3, 6, 12, 12)
    d.ellipse(body, fill=OUTLINE)
    d.ellipse((body[0] + 1, body[1] + 1, body[2] - 1, body[3] - 1), fill=cloth)
    head = hood or rgb(232, 188, 150)
    d.ellipse((5, 2, 10, 7), fill=OUTLINE)
    d.ellipse((6, 3, 9, 6), fill=head)
    if bow:
        d.arc((9, 3, 16, 13), 270, 90, fill=rgb(140, 90, 40))
        d.line((13, 3, 13, 13), fill=rgb(230, 230, 230))
    return im


def knight(step):
    im = tile()
    d = ImageDraw.Draw(im)
    horse = rgb(130, 86, 52)
    d.ellipse((1, 5, 14, 13), fill=OUTLINE)
    d.ellipse((2, 6, 13, 12), fill=horse)                  # the horse's back
    d.ellipse((11, 6, 16, 11), fill=OUTLINE)
    d.ellipse((12, 7, 15, 10), fill=horse)                 # its head, to the right
    for x in ((3, 10) if step == 0 else (5, 8)):
        d.rectangle((x, 13, x + 1, 15), fill=OUTLINE)      # legs, by turns
    d.ellipse((4, 3, 10, 9), fill=OUTLINE)
    d.ellipse((5, 4, 9, 8), fill=rgb(196, 200, 210))       # the rider's helmet
    d.line((9, 6, 15, 2), fill=rgb(220, 220, 230))         # the lance
    return im


def arrow():
    im = tile()
    d = ImageDraw.Draw(im)
    d.line((2, 8, 12, 8), fill=rgb(150, 100, 50))
    d.polygon(((12, 6), (15, 8), (12, 10)), fill=rgb(200, 200, 210))
    d.line((2, 6, 4, 8), fill=rgb(240, 240, 240))
    d.line((2, 10, 4, 8), fill=rgb(240, 240, 240))
    return im


def bolt():
    im = tile()
    d = ImageDraw.Draw(im)
    d.ellipse((3, 5, 14, 11), fill=rgb(255, 200, 80))
    d.ellipse((5, 6, 13, 10), fill=rgb(255, 240, 170))
    d.polygon(((11, 5), (15, 8), (11, 11)), fill=rgb(255, 255, 230))
    return im


def ram():
    im = tile()
    d = ImageDraw.Draw(im)
    d.rectangle((1, 5, 13, 11), fill=OUTLINE)
    d.rectangle((2, 6, 12, 10), fill=rgb(120, 80, 44))     # the log
    d.line((3, 7, 11, 7), fill=rgb(150, 104, 60))
    d.rectangle((12, 2, 15, 14), fill=OUTLINE)
    d.rectangle((13, 3, 14, 13), fill=rgb(170, 170, 180))  # the shield in front
    for x in (3, 7, 10):
        d.ellipse((x, 1, x + 3, 4), fill=rgb(170, 50, 50))  # the raiders carrying it
        d.ellipse((x, 12, x + 3, 15), fill=rgb(170, 50, 50))
    return im


def tower():
    im = tile()
    d = ImageDraw.Draw(im)
    d.ellipse((0, 0, 15, 15), fill=OUTLINE)
    d.ellipse((1, 1, 14, 14), fill=STONE)
    d.ellipse((4, 4, 11, 11), fill=STONE_DARK)
    d.ellipse((5, 5, 10, 10), fill=rgb(90, 60, 40))        # the brazier
    for a, b in ((7, 1), (14, 7), (7, 14), (1, 7)):
        d.point((a, b), fill=STONE_LIGHT)
    return im


def cross():
    im = tile()
    d = ImageDraw.Draw(im)
    white = rgb(255, 255, 255)
    for box in ((7, 1, 8, 5), (7, 10, 8, 14), (1, 7, 5, 8), (10, 7, 14, 8)):
        d.rectangle(box, fill=white)
    d.ellipse((5, 5, 10, 10), outline=white)
    return im


def sheet(frames):
    out = Image.new('RGBA', (16 * len(frames), 16), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        out.paste(f, (16 * i, 0))
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sheet([grass(), grass(True), floor(), wall()]).save(OUT / 'ground.png')
    blue, red, dark = rgb(64, 110, 210), rgb(190, 54, 48), rgb(120, 36, 40)
    hood = rgb(150, 40, 36)
    sheet([person(blue, 0, bow=True), person(blue, 1, bow=True), knight(0), knight(1),
           person(red, 0, hood=hood), person(red, 1, hood=hood),
           person(dark, 0, hood=rgb(90, 30, 30), big=True), person(dark, 1, hood=rgb(90, 30, 30), big=True),
           arrow(), bolt(), ram(), tower(), cross()]).save(OUT / 'siege.png')
    print('wrote', OUT / 'ground.png', 'and', OUT / 'siege.png')


if __name__ == '__main__':
    main()
