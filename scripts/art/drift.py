"""Draws Drift's art (projects/drift/assets/): the ship, the enemies, the shots, the sky.

Pixel art at the game's own size (a 256x224 screen): shapes drawn without
smoothing, then a one-pixel dark outline round each, so they read at 1x.

- ships.png, 24x24 frames: 0-1 the ship (its flame flickers), 2-4 a drone
  (its light turns), 5-7 a tank (its treads roll), 8 the ship's shot, 9 an
  enemy shot
- boss.png, 40x40 frames: 0 calm, 1 angry
- space.png, 256x224: stars on a dark violet sky, a faint nebula

    python scripts/art/drift.py
CC0.
"""
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parents[2] / 'projects' / 'drift' / 'assets'
OUTLINE = (12, 10, 28, 255)


def outlined(im):
    """A one-pixel outline round every opaque pixel."""
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


def ship(flame):
    im = Image.new('RGBA', (24, 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # flame under the engines
    fl = 3 + flame * 2
    d.polygon([(9, 18), (11, 18), (10, 18 + fl)], fill=(255, 160, 40))
    d.polygon([(13, 18), (15, 18), (14, 18 + fl)], fill=(255, 160, 40))
    d.point([(10, 19), (14, 19)], fill=(255, 240, 160))
    # wings
    d.polygon([(12, 7), (21, 16), (21, 18), (14, 17), (10, 17), (3, 18), (3, 16)], fill=(70, 120, 210))
    d.polygon([(12, 9), (19, 16), (14, 16)], fill=(110, 160, 240))
    d.polygon([(12, 9), (5, 16), (10, 16)], fill=(110, 160, 240))
    # hull
    d.polygon([(12, 1), (15, 8), (15, 18), (9, 18), (9, 8)], fill=(220, 228, 240))
    d.line([(10, 9), (10, 17)], fill=(170, 180, 200))
    # cockpit
    d.polygon([(12, 5), (13, 8), (13, 11), (11, 11), (11, 8)], fill=(80, 230, 255))
    d.point((12, 7), fill=(220, 255, 255))
    # wing tips
    d.point([(3, 16), (21, 16)], fill=(255, 80, 80))
    return outlined(im)


def drone(phase):
    im = Image.new('RGBA', (24, 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([3, 7, 20, 16], fill=(120, 60, 150))          # the saucer
    d.ellipse([3, 9, 20, 15], fill=(90, 40, 120))
    d.ellipse([7, 3, 16, 12], fill=(180, 120, 210))         # the dome
    d.ellipse([9, 5, 13, 8], fill=(230, 210, 250))
    for i, x in enumerate((5, 9, 14, 18)):                  # lights going round
        on = (i == phase) or (i == phase + 1)
        d.point((x, 12), fill=(255, 230, 90) if on else (110, 70, 40))
    d.rectangle([10, 16, 13, 18], fill=(255, 90, 160))      # the eye that looks down
    return outlined(im)


def tank(step):
    im = Image.new('RGBA', (24, 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for x0 in (2, 17):                                      # treads, rolling
        d.rectangle([x0, 3, x0 + 4, 20], fill=(60, 60, 70))
        for y in range(3 + step, 21, 3):
            d.line([(x0, y), (x0 + 4, y)], fill=(100, 100, 110))
    d.rectangle([6, 4, 17, 19], fill=(150, 90, 50))         # hull
    d.rectangle([7, 5, 16, 8], fill=(190, 120, 70))
    d.ellipse([7, 8, 16, 17], fill=(110, 64, 36))           # turret
    d.ellipse([9, 10, 14, 15], fill=(170, 104, 60))
    d.rectangle([11, 15, 12, 22], fill=(70, 70, 80))        # gun, pointing down
    d.point((11, 6), fill=(255, 220, 120))
    return outlined(im)


def shot():
    im = Image.new('RGBA', (24, 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([11, 4, 12, 19], fill=(90, 230, 255))
    d.rectangle([11, 6, 12, 10], fill=(230, 255, 255))
    return im


def enemy_shot():
    im = Image.new('RGBA', (24, 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([8, 8, 15, 15], fill=(255, 70, 120))
    d.ellipse([10, 10, 13, 13], fill=(255, 210, 230))
    return im


def boss(angry):
    im = Image.new('RGBA', (40, 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    body = (170, 40, 60) if angry else (70, 90, 130)
    light = (230, 80, 90) if angry else (120, 150, 200)
    dark = (100, 20, 34) if angry else (40, 52, 84)
    d.polygon([(2, 14), (8, 8), (14, 12), (8, 24), (3, 22)], fill=dark)        # the claws
    d.polygon([(37, 14), (31, 8), (25, 12), (31, 24), (36, 22)], fill=dark)
    d.ellipse([6, 6, 33, 30], fill=body)                                          # the shell
    d.ellipse([9, 8, 30, 20], fill=light)
    for x in (12, 19, 26):
        d.line([(x, 9), (x - 1, 17)], fill=body)
    d.rectangle([12, 28, 27, 33], fill=dark)                                       # the cannons, below
    for x in (14, 19, 24):
        d.rectangle([x, 33, x + 1, 37], fill=(80, 80, 90))
    eye = (255, 60, 40) if angry else (120, 240, 255)
    d.ellipse([13, 19, 17, 23], fill=eye)
    d.ellipse([22, 19, 26, 23], fill=eye)
    if angry:
        d.line([(12, 17), (17, 19)], fill=(40, 10, 14))
        d.line([(27, 17), (22, 19)], fill=(40, 10, 14))
    return outlined(im)


def space():
    rnd = random.Random(11)
    im = Image.new('RGBA', (256, 224), (10, 10, 30, 255))
    d = ImageDraw.Draw(im)
    for y in range(224):                                    # a slight gradient
        c = (10 + y // 28, 9 + y // 40, 30 + y // 14)
        d.line([(0, y), (256, y)], fill=c)
    neb = Image.new('RGBA', (256, 224), (0, 0, 0, 0))
    nd = ImageDraw.Draw(neb)
    for _ in range(26):
        x, y, r = rnd.uniform(20, 236), rnd.uniform(10, 140), rnd.uniform(12, 34)
        col = rnd.choice([(120, 50, 160, 26), (40, 90, 170, 24), (170, 60, 110, 18)])
        nd.ellipse([x - r, y - r * 0.6, x + r, y + r * 0.6], fill=col)
    im.alpha_composite(neb.filter(ImageFilter.GaussianBlur(8)))
    d = ImageDraw.Draw(im)
    for _ in range(140):
        x, y = rnd.randrange(256), rnd.randrange(224)
        b = rnd.choice((90, 120, 160, 210, 255))
        d.point((x, y), fill=(b, b, min(255, b + 30)))
    for _ in range(10):                                     # a few bright ones, with a cross
        x, y = rnd.randrange(8, 248), rnd.randrange(8, 216)
        d.point([(x, y)], fill=(255, 255, 255))
        d.point([(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)], fill=(150, 160, 220))
    return im.convert('RGB')


def main():
    frames = [ship(0), ship(1), drone(0), drone(1), drone(2), tank(0), tank(1), tank(2), shot(), enemy_shot()]
    sheet = Image.new('RGBA', (24 * len(frames), 24))
    for i, f in enumerate(frames):
        sheet.paste(f, (i * 24, 0))
    sheet.save(OUT / 'ships.png', optimize=True)
    b = Image.new('RGBA', (80, 40))
    b.paste(boss(False), (0, 0))
    b.paste(boss(True), (40, 0))
    b.save(OUT / 'boss.png', optimize=True)
    space().save(OUT / 'space.png', optimize=True)
    print(OUT)


if __name__ == '__main__':
    main()
