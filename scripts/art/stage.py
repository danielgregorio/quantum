"""Draws Arena's stage (projects/arena/assets/stage.png, 640x360): a dojo yard at dusk.

A sky going from orange to violet, a low sun, two ranges of hills, a wooden
gate, paper lanterns and a plank floor whose top is the line the fighters
stand on (y = 300). Drawn at 2x and shrunk. CC0.

    python scripts/art/stage.py
"""
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

S = 2
W, H = 640, 360
FLOOR = 300
OUT = Path(__file__).resolve().parents[2] / 'projects' / 'arena' / 'assets' / 'stage.png'


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


def main():
    rnd = random.Random(7)
    im = Image.new('RGBA', (W * S, H * S))
    d = ImageDraw.Draw(im)
    top, mid, low = (52, 36, 92), (196, 84, 104), (250, 170, 92)
    for y in range(FLOOR * S):
        t = y / (FLOOR * S)
        c = lerp(top, mid, t / 0.6) if t < 0.6 else lerp(mid, low, (t - 0.6) / 0.4)
        d.line([(0, y), (W * S, y)], fill=c)
    # the sun, low, with a glow
    glow = Image.new('RGBA', im.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    cx, cy = 430 * S, 236 * S
    for r in range(90, 0, -3):
        gd.ellipse([cx - r * S, cy - r * S, cx + r * S, cy + r * S], fill=(255, 210, 120, int(60 * (1 - r / 90))))
    im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(6 * S)))
    d.ellipse([cx - 34 * S, cy - 34 * S, cx + 34 * S, cy + 34 * S], fill=(255, 222, 150))
    # two ranges of hills
    for base, amp, col, seed in ((232, 26, (120, 60, 110), 1), (262, 18, (78, 40, 84), 2)):
        r2 = random.Random(seed)
        pts = [(0, H * S)]
        phase = [r2.uniform(0, 6) for _ in range(3)]
        for x in range(0, W * S + 8, 8):
            fx = x / S
            y = base - amp * (0.6 * math.sin(fx / 70 + phase[0]) + 0.3 * math.sin(fx / 29 + phase[1])
                              + 0.1 * math.sin(fx / 11 + phase[2]))
            pts.append((x, y * S))
        pts.append((W * S, H * S))
        d.polygon(pts, fill=col)
    # the wall of the yard: dark wood posts and a beam, paper panels between
    wall_top = 196
    d.rectangle([0, wall_top * S, W * S, FLOOR * S], fill=(62, 34, 40))
    for x in range(0, W, 80):
        d.rectangle([(x + 8) * S, (wall_top + 10) * S, (x + 72) * S, (FLOOR - 12) * S], fill=(232, 210, 170))
        for gx in range(x + 8, x + 72, 16):
            d.line([(gx * S, (wall_top + 10) * S), (gx * S, (FLOOR - 12) * S)], fill=(150, 112, 92), width=S)
        for gy in range(wall_top + 10, FLOOR - 12, 18):
            d.line([((x + 8) * S, gy * S), ((x + 72) * S, gy * S)], fill=(150, 112, 92), width=S)
        d.rectangle([x * S, wall_top * S, (x + 8) * S, FLOOR * S], fill=(44, 22, 26))
    d.rectangle([0, (wall_top - 6) * S, W * S, (wall_top + 10) * S], fill=(44, 22, 26))
    # the gate in the middle: two red posts, two beams
    gx0, gx1 = 250, 390
    for x in (gx0, gx1):
        d.rectangle([(x - 7) * S, 120 * S, (x + 7) * S, FLOOR * S], fill=(176, 40, 36))
        d.rectangle([(x - 7) * S, 120 * S, (x - 3) * S, FLOOR * S], fill=(208, 66, 52))
    d.polygon([((gx0 - 34) * S, 112 * S), ((gx1 + 34) * S, 112 * S), ((gx1 + 26) * S, 124 * S), ((gx0 - 26) * S, 124 * S)],
              fill=(30, 18, 22))
    d.rectangle([(gx0 - 20) * S, 136 * S, (gx1 + 20) * S, 146 * S], fill=(176, 40, 36))
    # lanterns hanging from the beam
    for x in (60, 170, 470, 580):
        d.line([(x * S, (wall_top + 10) * S), (x * S, (wall_top + 24) * S)], fill=(30, 18, 22), width=S)
        lg = Image.new('RGBA', im.size, (0, 0, 0, 0))
        ImageDraw.Draw(lg).ellipse([(x - 22) * S, (wall_top + 18) * S, (x + 22) * S, (wall_top + 62) * S], fill=(255, 190, 90, 90))
        im.alpha_composite(lg.filter(ImageFilter.GaussianBlur(8 * S)))
        d.rounded_rectangle([(x - 9) * S, (wall_top + 24) * S, (x + 9) * S, (wall_top + 50) * S], radius=7 * S, fill=(236, 74, 52))
        d.rectangle([(x - 7) * S, (wall_top + 22) * S, (x + 7) * S, (wall_top + 25) * S], fill=(30, 18, 22))
        d.rectangle([(x - 7) * S, (wall_top + 49) * S, (x + 7) * S, (wall_top + 52) * S], fill=(30, 18, 22))
        for ly in range(wall_top + 29, wall_top + 48, 5):
            d.line([((x - 8) * S, ly * S), ((x + 8) * S, ly * S)], fill=(200, 52, 40), width=S)
    # the floor: planks running into the distance, lit along the edge
    d.rectangle([0, FLOOR * S, W * S, H * S], fill=(150, 98, 62))
    d.rectangle([0, FLOOR * S, W * S, (FLOOR + 3) * S], fill=(214, 156, 98))
    vx = W / 2
    for i in range(-12, 13):
        x_top = vx + i * 34
        x_bot = vx + i * 70
        d.line([(x_top * S, (FLOOR + 3) * S), (x_bot * S, H * S)], fill=(118, 74, 46), width=S)
    for k, y in enumerate((310, 324, 342)):
        d.line([(0, y * S), (W * S, y * S)], fill=(126, 82, 52), width=S)
    # wood grain flecks
    for _ in range(600):
        x, y = rnd.uniform(0, W), rnd.uniform(FLOOR + 4, H)
        d.line([(x * S, y * S), ((x + rnd.uniform(4, 12)) * S, y * S)], fill=(136, 88, 56), width=S)
    # a soft shadow under the wall, where it meets the floor
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle([0, (FLOOR + 2) * S, W * S, (FLOOR + 12) * S], fill=(40, 20, 20, 90))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(4 * S)))
    im.resize((W, H), Image.LANCZOS).convert('RGB').save(OUT, optimize=True)
    print(OUT)


if __name__ == '__main__':
    main()
