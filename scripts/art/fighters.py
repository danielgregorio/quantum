"""Draws Arena's two fighters (projects/arena/assets/red.png, blue.png): 14 frames of 64x96.

Each frame is a pose of one jointed figure, facing right (the runtime mirrors
it). The figure is drawn as silhouettes, not as separate bones: the far arm
and leg first, a shade darker, then the body, head, near leg and near arm,
each layer with every outline under every fill, so the joints of a layer
melt into one shape. Drawn at 4x and shrunk. CC0.

    python scripts/art/fighters.py
"""
import math
from pathlib import Path
from PIL import Image, ImageDraw

S = 4                      # drawn at 4x
W, H = 64, 96
OUT = Path(__file__).resolve().parents[2] / 'projects' / 'arena' / 'assets'

THIGH, SHIN = 15, 15
UPPER, FORE = 11, 11
TORSO = 21

# A pose: the hip (frame pixels), the torso's lean (degrees, + leans back), the head's tilt,
# each leg as (thigh, knee bend) and each arm as (upper arm, elbow bend), angles in degrees from
# straight down, + towards the front (the right). A knee bends backwards, an elbow forwards.
POSES = [
    dict(n='idle',   hip=(30, 58), lean=4,   head=0,  back=(-24, 22), front=(26, 18), barm=(70, 95), farm=(55, 110)),
    dict(n='walk1',  hip=(31, 57), lean=6,   head=0,  back=(-30, 30), front=(30, 6),  barm=(72, 95), farm=(52, 112)),
    dict(n='walk2',  hip=(31, 58), lean=6,   head=0,  back=(-8, 34),  front=(12, 30), barm=(66, 98), farm=(60, 105)),
    dict(n='jump',   hip=(32, 46), lean=8,   head=-4, back=(30, 100), front=(70, 110), barm=(80, 80), farm=(95, 70)),
    dict(n='crouch', hip=(30, 74), lean=16,  head=-6, back=(-40, 110), front=(75, 115), barm=(75, 95), farm=(65, 105)),
    dict(n='block',  hip=(28, 58), lean=-6,  head=8,  back=(-26, 20), front=(20, 20), barm=(110, 120), farm=(95, 130)),
    dict(n='punch1', hip=(29, 58), lean=-2,  head=0,  back=(-26, 22), front=(24, 18), barm=(70, 100), farm=(40, 130)),
    dict(n='punch2', hip=(32, 58), lean=-14, head=0,  back=(-34, 14), front=(30, 10), barm=(40, 110), farm=(92, 0)),
    dict(n='punch3', hip=(30, 58), lean=-6,  head=0,  back=(-28, 18), front=(26, 14), barm=(55, 100), farm=(80, 50)),
    dict(n='kick1',  hip=(28, 58), lean=4,   head=0,  back=(-6, 10),  front=(80, 120), barm=(70, 95), farm=(50, 110)),
    dict(n='kick2',  hip=(22, 58), lean=26,  head=4,  back=(-4, 6),   front=(98, 4),   barm=(40, 80), farm=(30, 100)),
    dict(n='kick3',  hip=(28, 58), lean=8,   head=0,  back=(-8, 10),  front=(60, 70),  barm=(60, 95), farm=(45, 105)),
    dict(n='hit',    hip=(27, 58), lean=24,  head=-22, back=(-30, 20), front=(14, 14), barm=(-30, 60), farm=(-10, 70)),
    dict(n='ko',     hip=(22, 88), lean=40,  head=24, back=(140, 70), front=(125, 60), barm=(-20, 10), farm=(10, 20)),
]

PALETTES = {
    'red':  dict(gi=(218, 60, 50), shade=(160, 38, 36), belt=(34, 28, 28), skin=(240, 194, 156),
                 skin_shade=(206, 156, 120), hair=(56, 38, 30), band=(250, 246, 240), outline=(32, 18, 24)),
    'blue': dict(gi=(64, 120, 220), shade=(40, 78, 158), belt=(36, 30, 30), skin=(198, 142, 106),
                 skin_shade=(160, 108, 78), hair=(24, 22, 30), band=(252, 212, 64), outline=(16, 20, 40)),
}


def at(origin, length, angle):
    """From origin, `length` along `angle` degrees from straight down, + towards the right."""
    a = math.radians(angle)
    return origin[0] + length * math.sin(a), origin[1] + length * math.cos(a)


class Layer:
    """Shapes drawn outline-first: every outline of the layer, then every fill."""

    def __init__(self):
        self.shapes = []

    def capsule(self, a, b, width, fill):
        self.shapes.append(('capsule', a, b, width, fill))

    def disc(self, c, r, fill):
        self.shapes.append(('disc', c, r, 0, fill))

    def poly(self, pts, fill):
        self.shapes.append(('poly', pts, None, 0, fill))

    def draw(self, d, outline, line=1.3):
        for pass_ in (0, 1):
            for kind, a, b, w, fill in self.shapes:
                grow = line if pass_ == 0 else 0
                col = outline if pass_ == 0 else fill
                if kind == 'capsule':
                    _capsule(d, a, b, w + 2 * grow, col)
                elif kind == 'disc':
                    r = (b + grow) * S
                    d.ellipse([a[0] * S - r, a[1] * S - r, a[0] * S + r, a[1] * S + r], fill=col)
                else:
                    pts = [(x * S, y * S) for x, y in a]
                    if grow:
                        cx = sum(p[0] for p in pts) / len(pts)
                        cy = sum(p[1] for p in pts) / len(pts)
                        pts2 = []
                        for x, y in pts:
                            dx, dy = x - cx, y - cy
                            n = math.hypot(dx, dy) or 1
                            pts2.append((x + dx / n * grow * S, y + dy / n * grow * S))
                        pts = pts2
                    d.polygon(pts, fill=col)


def _capsule(d, a, b, width, col):
    a = (a[0] * S, a[1] * S)
    b = (b[0] * S, b[1] * S)
    r = width * S / 2
    d.line([a, b], fill=col, width=int(width * S))
    for p in (a, b):
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=col)


def frame(pose, pal):
    im = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    hip = pose['hip']
    up = 180 + pose['lean']               # the torso's direction: up, its top leaning back when lean > 0
    neck = at(hip, TORSO, up)
    shoulder = at(hip, TORSO - 3, up)
    shoulder_back = at(shoulder, 2.5, up - 90)
    shoulder_front = at(shoulder, 2.5, up + 90)

    def leg(spec, shade):
        thigh, bend = spec
        knee = at(hip, THIGH, thigh)
        ankle = at(knee, SHIN, thigh - bend)
        heel_dir = thigh - bend + 90          # the foot points forward, square to the shin
        toe = at(ankle, 6, heel_dir)
        return knee, ankle, toe

    def arm(spec, base):
        upper, bend = spec
        elbow = at(base, UPPER, upper)
        hand = at(elbow, FORE, upper + bend if bend else upper)
        return elbow, hand

    # --- the far side: arm and leg, a shade darker ---
    far = Layer()
    knee, ankle, toe = leg(pose['back'], True)
    far.capsule(hip, knee, 10, pal['shade'])
    far.capsule(knee, ankle, 9, pal['shade'])
    far.capsule(ankle, toe, 4.5, pal['skin_shade'])
    elbow, hand = arm(pose['barm'], shoulder_back)
    far.capsule(shoulder_back, elbow, 7.5, pal['shade'])
    far.capsule(elbow, hand, 6, pal['skin_shade'])
    far.disc(hand, 3.6, pal['skin_shade'])
    far.draw(d, pal['outline'])

    # --- the body: torso, belt, head, near leg ---
    body = Layer()
    waist_l, waist_r = at(hip, 6.5, up - 90), at(hip, 6.5, up + 90)
    chest_l, chest_r = at(shoulder, 8.5, up - 90), at(shoulder, 8.5, up + 90)
    body.poly([waist_l, chest_l, at(chest_l, 2, up), at(chest_r, 2, up), chest_r, waist_r], pal['gi'])
    nknee, nankle, ntoe = leg(pose['front'], False)
    body.capsule(hip, nknee, 10.5, pal['gi'])
    body.capsule(nknee, nankle, 9.5, pal['gi'])
    body.capsule(nankle, ntoe, 4.8, pal['skin'])
    tilt = up + pose['head']
    head = at(neck, 8.5, tilt)
    body.capsule(neck, at(neck, 3, tilt), 6, pal['skin'])    # the neck
    body.disc(head, 8.2, pal['skin'])
    body.draw(d, pal['outline'])
    # details on the body, no outline: the gi's lapels, the belt across the waist, its knot
    o = pal['outline']
    lap = at(shoulder, 1, up)
    v1, v2 = at(lap, 4, up - 90), at(lap, 4, up + 90)
    v3 = at(hip, 8, up)
    d.polygon([(v1[0] * S, v1[1] * S), (v2[0] * S, v2[1] * S), (v3[0] * S, v3[1] * S)], fill=pal['skin'])
    d.line([(v2[0] * S, v2[1] * S), (v3[0] * S, v3[1] * S)], fill=pal['shade'], width=int(1.2 * S))
    b1, b2 = at(at(hip, 3.2, up), 7.2, up - 90), at(at(hip, 3.2, up), 7.2, up + 90)
    _capsule(d, b1, b2, 3.4, pal['belt'])
    knot = at(at(hip, 3.2, up), 3, up + 90)
    _capsule(d, knot, at(knot, 5, 15), 1.8, pal['belt'])
    _capsule(d, knot, at(knot, 4.5, -10), 1.8, pal['belt'])
    # the head: hair on top and at the back, the headband with its tails, an eye and a brow
    hx, hy = head[0] * S, head[1] * S
    r = 8.2 * S
    t = math.radians(tilt - 180)                     # 0 when upright
    d.pieslice([hx - r, hy - r, hx + r, hy + r], 180 + math.degrees(t) - 10, 360 + math.degrees(t) - 60, fill=pal['hair'])
    d.chord([hx - r, hy - r, hx + r, hy + r], 120 + math.degrees(t), 230 + math.degrees(t), fill=pal['hair'])
    band_y = -2.2
    bl = (hx + (-r) * math.cos(t) - band_y * S * math.sin(t), hy + (-r) * math.sin(t) + band_y * S * math.cos(t))
    br = (hx + r * math.cos(t) - band_y * S * math.sin(t), hy + r * math.sin(t) + band_y * S * math.cos(t))
    d.line([bl, br], fill=pal['band'], width=int(2.6 * S))
    d.line([bl, (bl[0] - 5 * S, bl[1] + 3 * S)], fill=pal['band'], width=int(1.8 * S))
    d.line([bl, (bl[0] - 4 * S, bl[1] + 6 * S)], fill=pal['band'], width=int(1.6 * S))
    ex = hx + 4.6 * S * math.cos(t) - 0.6 * S * math.sin(t)
    ey = hy + 4.6 * S * math.sin(t) + 0.6 * S * math.cos(t)
    if pose['n'] in ('ko', 'hit'):
        for s1, s2 in ((-1, -1), (-1, 1)):
            d.line([(ex - 1.6 * S, ey + s1 * 1.6 * S), (ex + 1.6 * S, ey - s1 * s2 * 1.6 * S)], fill=o, width=int(0.9 * S))
    else:
        d.ellipse([ex - 1.1 * S, ey - 1.5 * S, ex + 1.1 * S, ey + 1.5 * S], fill=o)
        d.line([(ex - 2 * S, ey - 2.6 * S), (ex + 1.6 * S, ey - 2.2 * S)], fill=o, width=int(0.9 * S))
    # a nose at the front of the face
    nx = hx + 8.2 * S * math.cos(t)
    ny = hy + 8.2 * S * math.sin(t) + 1.5 * S
    d.ellipse([nx - 1.4 * S, ny - 1.2 * S, nx + 0.8 * S, ny + 1.2 * S], fill=pal['skin'])

    # --- the near arm, over everything ---
    near = Layer()
    elbow, hand = arm(pose['farm'], shoulder_front)
    near.capsule(shoulder_front, elbow, 8, pal['gi'])
    near.capsule(elbow, hand, 6.5, pal['skin'])
    near.disc(hand, 4.2, pal['skin'])
    near.draw(d, pal['outline'])
    return im.resize((W, H), Image.LANCZOS)


def main():
    for name, pal in PALETTES.items():
        sheet = Image.new('RGBA', (W * len(POSES), H), (0, 0, 0, 0))
        for i, pose in enumerate(POSES):
            sheet.paste(frame(pose, pal), (i * W, 0))
        sheet.save(OUT / f'{name}.png', optimize=True)
        print(OUT / f'{name}.png')


if __name__ == '__main__':
    main()
