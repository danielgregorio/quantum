"""Draws Delve's art (projects/delve/assets/): crypts seen from above, two delvers, their foes.

Pixel art at the game's own size (a 256x224 screen), shapes drawn without
smoothing and outlined, like scripts/art/keep.py.

- crypt.png, 18x18 tiles: 0 floor, 1 wall, 2 wall with a torch, 3 lever, 4 lever
  (pulled), 5 gem, 6 heart, 7 chest, 8 stairs down, 9 a crusher slab, 10 bones,
  11 rubble (a wall broken open: walked on)
- delvers.png, 24x24 frames: for the first delver (rust) and then the second
  (blue), ten each: 0 idle, 1-2 walking (to the right), 3-4 walking up, 5-6
  walking down, 7 the sword swung right, 8 up, 9 down; then 20-22 a skeleton
  walking, 23-25 a bat, 26-28 a skeleton falling to a heap of bones

    python scripts/art/delve.py
CC0.
"""
import random
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[2] / 'projects' / 'delve' / 'assets'
OUTLINE = (14, 12, 20, 255)


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


def on(base, sprite):
    im = base.copy()
    im.alpha_composite(sprite)
    return im


# ---- tiles ----

FLOOR, SEAM, MOSS = (44, 42, 54), (32, 30, 40), (58, 76, 52)


def floor(seed=5):
    rnd = random.Random(seed)
    im = Image.new('RGBA', (18, 18), FLOOR)
    d = ImageDraw.Draw(im)
    # large slabs, offset
    d.line([(0, 0), (17, 0)], fill=SEAM)
    d.line([(0, 9), (17, 9)], fill=SEAM)
    d.line([(6, 0), (6, 9)], fill=SEAM)
    d.line([(14, 9), (14, 17)], fill=SEAM)
    d.line([(1, 1), (5, 1)], fill=(54, 52, 66))
    d.line([(7, 10), (13, 10)], fill=(54, 52, 66))
    for _ in range(4):
        d.point((rnd.randrange(18), rnd.randrange(18)), fill=MOSS)
    for _ in range(5):
        d.point((rnd.randrange(18), rnd.randrange(18)), fill=(38, 36, 46))
    return im


def wall():
    im = Image.new('RGBA', (18, 18), (72, 66, 86))
    d = ImageDraw.Draw(im)
    for row, y in enumerate((0, 9)):
        d.line([(0, y + 8), (17, y + 8)], fill=(34, 30, 42))
        off = 0 if row == 0 else 6
        for x in range(off, 18, 12):
            d.line([(x, y), (x, y + 8)], fill=(34, 30, 42))
        d.line([(0, y), (17, y)], fill=(98, 90, 114))
    d.point([(3, 4), (12, 13), (9, 3)], fill=(58, 54, 70))
    return im


def torch_wall():
    im = wall()
    d = ImageDraw.Draw(im)
    d.rectangle([7, 9, 10, 11], fill=(60, 56, 60))          # the iron bracket
    d.rectangle([8, 4, 9, 10], fill=(110, 72, 40))          # the stick; its flame is a qg:emitter
    d.rectangle([7, 3, 10, 4], fill=(70, 46, 30))
    d.point([(8, 2), (9, 2)], fill=(255, 190, 80))
    return im


def lever(pulled):
    im = Image.new('RGBA', (18, 18), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([3, 11, 14, 15], fill=(96, 92, 104))
    d.rectangle([4, 12, 13, 14], fill=(70, 66, 80))
    if pulled:
        d.line([(9, 13), (14, 5)], fill=(170, 170, 180), width=2)
        d.rectangle([13, 3, 15, 5], fill=(110, 230, 140))
    else:
        d.line([(8, 13), (3, 5)], fill=(170, 170, 180), width=2)
        d.rectangle([2, 3, 4, 5], fill=(230, 110, 70))
    return outlined(im)


def gem():
    im = Image.new('RGBA', (18, 18), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(9, 3), (14, 8), (9, 15), (4, 8)], fill=(70, 200, 230))
    d.polygon([(9, 3), (14, 8), (9, 8)], fill=(150, 235, 250))
    d.polygon([(4, 8), (9, 8), (9, 15)], fill=(40, 140, 190))
    d.point((7, 6), fill=(240, 255, 255))
    return outlined(im)


def heart():
    im = Image.new('RGBA', (18, 18), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([3, 4, 9, 10], fill=(220, 60, 80))
    d.ellipse([8, 4, 14, 10], fill=(220, 60, 80))
    d.polygon([(3, 8), (14, 8), (9, 15), (8, 15)], fill=(220, 60, 80))
    d.point([(5, 6), (6, 5)], fill=(255, 190, 200))
    return outlined(im)


def chest():
    im = Image.new('RGBA', (18, 18), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([1, 5, 16, 16], fill=(120, 70, 36))
    d.rectangle([1, 5, 16, 8], fill=(150, 92, 46))
    for x in (1, 16):
        d.line([(x, 5), (x, 16)], fill=(200, 170, 70))
    d.line([(1, 9), (16, 9)], fill=(200, 170, 70))
    d.rectangle([7, 8, 10, 12], fill=(250, 214, 90))
    d.point((8, 11), fill=OUTLINE)
    return outlined(im)


def stairs():
    im = Image.new('RGBA', (18, 18), (20, 18, 26))
    d = ImageDraw.Draw(im)
    for i, y in enumerate((1, 5, 9, 13)):
        shade = 92 - i * 20
        d.rectangle([1 + i, y, 16 - i, y + 3], fill=(shade, shade - 6, shade + 12))
        d.line([(1 + i, y), (16 - i, y)], fill=(shade + 24, shade + 18, shade + 34))
    return im


def slab():
    im = Image.new('RGBA', (18, 18), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 17, 17], fill=(104, 98, 116))
    d.rectangle([0, 0, 17, 2], fill=(136, 128, 150))
    d.rectangle([0, 15, 17, 17], fill=(76, 70, 88))
    # a skull scratched in it: keep away
    d.ellipse([5, 4, 12, 10], fill=(188, 182, 170))
    d.rectangle([7, 10, 10, 12], fill=(188, 182, 170))
    d.point([(7, 7), (10, 7)], fill=OUTLINE)
    return outlined(im)


def bones():
    im = Image.new('RGBA', (18, 18), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.line([(3, 12), (13, 6)], fill=(214, 206, 186), width=2)
    d.line([(4, 6), (12, 13)], fill=(196, 188, 170), width=2)
    d.ellipse([10, 9, 15, 14], fill=(226, 218, 200))
    d.point([(12, 11)], fill=OUTLINE)
    return im


def rubble():
    im = floor(seed=11)
    d = ImageDraw.Draw(im)
    for x, y, r in ((3, 4, 2), (12, 3, 1), (8, 11, 2), (14, 13, 1), (4, 14, 1)):
        d.ellipse([x - r, y - r, x + r, y + r], fill=(84, 78, 96))
        d.point((x - r + 1, y - r + 1), fill=(110, 102, 124))
    return im


# ---- the delvers, the skeleton, the bat ----

SKIN, BOOT, BLADE, HILT, BELT = (232, 190, 150), (60, 42, 32), (218, 224, 236), (226, 176, 60), (90, 60, 36)
PALETTES = {
    'rust': {'cloak': (176, 84, 44), 'dark': (128, 56, 30), 'trim': (230, 170, 80)},
    'blue': {'cloak': (56, 112, 186), 'dark': (36, 76, 136), 'trim': (150, 210, 240)},
}


def delver(p, view, step=0, attack=False):
    """A hooded delver. view: 'down', 'up', 'side' (facing right); step: 0, 1 or -1."""
    im = Image.new('RGBA', (24, 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cloak, dark, trim = p['cloak'], p['dark'], p['trim']
    # boots
    if view == 'side':
        d.rectangle([9 + step, 18, 11 + step, 21], fill=BOOT)
        d.rectangle([12 - step, 18, 14 - step, 21], fill=BOOT)
    else:
        d.rectangle([9, 18 + max(step, 0), 11, 21], fill=BOOT)
        d.rectangle([13, 18 + max(-step, 0), 15, 21], fill=BOOT)
    # the cloak, wider at the hem
    d.polygon([(8, 10), (16, 10), (17, 19), (7, 19)], fill=cloak)
    d.line([(7, 19), (17, 19)], fill=dark)
    d.line([(8, 15), (16, 15)], fill=BELT)
    # the hood
    d.rectangle([7, 2, 16, 11], fill=cloak)
    d.line([(7, 2), (16, 2)], fill=trim)
    if view == 'down':
        d.rectangle([9, 5, 14, 10], fill=SKIN)                 # the face, in the hood
        d.rectangle([9, 5, 14, 5], fill=dark)
        d.point([(10, 7), (13, 7)], fill=OUTLINE)
        d.line([(12, 11), (12, 18)], fill=trim)                # the cloak's clasp and seam
    elif view == 'up':
        d.rectangle([9, 4, 14, 9], fill=dark)                  # the back of the hood
        d.polygon([(10, 10), (14, 10), (12, 13)], fill=dark)
    else:
        d.rectangle([12, 5, 16, 10], fill=SKIN)                # the face, to the right
        d.rectangle([12, 5, 13, 10], fill=dark)
        d.point((15, 7), fill=OUTLINE)
        d.point((17, 8), fill=SKIN)
    if attack:
        if view == 'side':
            d.rectangle([15, 12, 17, 13], fill=SKIN)
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
        d.rectangle([10 + step, 12, 12 + step, 15], fill=dark)  # the near arm, swinging with the step
    return outlined(im)


def delver_frames(p):
    return [delver(p, 'down'), delver(p, 'side', 1), delver(p, 'side', -1), delver(p, 'up', 1),
            delver(p, 'up', -1), delver(p, 'down', 1), delver(p, 'down', -1), delver(p, 'side', attack=True),
            delver(p, 'up', attack=True), delver(p, 'down', attack=True)]


BONE, BONE_D = (226, 220, 204), (170, 164, 150)


def skeleton(step):
    im = Image.new('RGBA', (24, 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    # legs
    d.line([(10 + step, 17), (10 + step, 21)], fill=BONE, width=2)
    d.line([(14 - step, 17), (14 - step, 21)], fill=BONE, width=2)
    # ribs
    d.rectangle([9, 11, 15, 16], fill=BONE_D)
    for y in (12, 14):
        d.line([(9, y), (15, y)], fill=BONE)
    d.line([(12, 10), (12, 17)], fill=BONE)
    # arms
    d.line([(8, 11), (6, 15 - step)], fill=BONE, width=2)
    d.line([(16, 11), (18, 15 + step)], fill=BONE, width=2)
    # skull
    d.ellipse([8, 2, 16, 10], fill=BONE)
    d.rectangle([10, 8, 14, 10], fill=BONE)
    d.rectangle([10, 5, 11, 6], fill=(220, 60, 60))           # the eyes glow
    d.rectangle([13, 5, 14, 6], fill=(220, 60, 60))
    d.line([(11, 9), (13, 9)], fill=OUTLINE)
    return outlined(im)


def collapse(stage):
    """A slain skeleton: 0 buckling, 1 falling apart, 2 a heap of bones."""
    im = Image.new('RGBA', (24, 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if stage == 0:
        d.line([(9, 17), (11, 21)], fill=BONE, width=2)          # the knees give
        d.line([(15, 17), (13, 21)], fill=BONE, width=2)
        d.rectangle([9, 12, 15, 17], fill=BONE_D)
        d.line([(9, 14), (15, 14)], fill=BONE)
        d.line([(8, 13), (5, 18)], fill=BONE, width=2)
        d.line([(16, 13), (19, 18)], fill=BONE, width=2)
        d.ellipse([8, 5, 16, 13], fill=BONE)
        d.rectangle([10, 8, 11, 9], fill=(150, 40, 40))         # the glow fades
        d.rectangle([13, 8, 14, 9], fill=(150, 40, 40))
    elif stage == 1:
        for (x0, y0, x1, y1) in ((5, 19, 10, 17), (14, 18, 19, 20), (8, 21, 13, 21), (11, 15, 16, 16)):
            d.line([(x0, y0), (x1, y1)], fill=BONE, width=2)
        d.rectangle([9, 13, 14, 16], fill=BONE_D)
        d.ellipse([12, 8, 19, 14], fill=BONE)                    # the skull rolls
        d.point([(14, 11), (17, 11)], fill=OUTLINE)
    else:
        for (x0, y0, x1, y1) in ((4, 21, 11, 19), (12, 20, 20, 21), (7, 18, 15, 19), (9, 21, 17, 18)):
            d.line([(x0, y0), (x1, y1)], fill=BONE, width=2)
        d.ellipse([9, 13, 16, 19], fill=BONE)                    # the skull on top of the heap
        d.point([(11, 16), (14, 16)], fill=OUTLINE)
        d.line([(12, 18), (13, 18)], fill=OUTLINE)
    return outlined(im)


def bat(wing):
    im = Image.new('RGBA', (24, 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    body = (110, 40, 60)
    d.ellipse([9, 9, 15, 16], fill=body)
    d.polygon([(10, 9), (11, 6), (12, 9)], fill=body)
    d.polygon([(12, 9), (13, 6), (14, 9)], fill=body)
    tip = (4, 12, 20)[wing]
    d.polygon([(9, 11), (1, tip), (4, 15), (9, 14)], fill=(80, 26, 44))
    d.polygon([(15, 11), (23, tip), (20, 15), (15, 14)], fill=(80, 26, 44))
    d.point([(11, 11), (13, 11)], fill=(255, 230, 120))
    return outlined(im)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    base = floor()
    tiles = [floor(), wall(), torch_wall(), on(base, lever(False)), on(base, lever(True)), gem(), heart(), chest(),
             stairs(), slab(), on(base, bones()), rubble()]
    sheet = Image.new('RGBA', (18 * len(tiles), 18))
    for i, t in enumerate(tiles):
        sheet.paste(t, (i * 18, 0))
    sheet.save(OUT / 'crypt.png', optimize=True)
    frames = (delver_frames(PALETTES['rust']) + delver_frames(PALETTES['blue'])
              + [skeleton(0), skeleton(1), skeleton(-1), bat(0), bat(1), bat(2), collapse(0), collapse(1),
                 collapse(2)])
    sheet = Image.new('RGBA', (24 * len(frames), 24))
    for i, f in enumerate(frames):
        sheet.paste(f, (i * 24, 0))
    sheet.save(OUT / 'delvers.png', optimize=True)
    print(OUT)


if __name__ == '__main__':
    main()
