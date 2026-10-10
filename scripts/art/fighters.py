"""Draws Arena's two fighters (projects/arena/assets/red.png, blue.png): 14 frames of 64x96.

Each frame is a pose of one jointed figure: angles for the torso, the head, both
arms and both legs, drawn at 4x as outlined rounded limbs and shrunk, so the two
fighters and all their frames share one figure. Facing right; the runtime
mirrors it. CC0, like everything this script draws.

    python scripts/art/fighters.py
"""
import math
from pathlib import Path
from PIL import Image, ImageDraw

S = 4                      # drawn at 4x
W, H = 64, 96
OUT = Path(__file__).resolve().parents[2] / 'projects' / 'arena' / 'assets'

# lengths, in frame pixels
THIGH, SHIN, FOOT = 16, 16, 7
UPPER, FORE = 12, 11
TORSO = 23
HEAD = 9

POSES = [
    # name: hip (x, y), torso lean (deg from up), legs (thigh, shin) back/front from straight down
    # (positive = forward), arms (upper, fore) back/front from straight down (positive = forward/up)
    dict(n='idle',   hip=(30, 58), lean=6,  bt=-18, bs=-8,  ft=22, fs=-20, ba=(35, 110), fa=(55, 120), head=0),
    dict(n='walk1',  hip=(31, 57), lean=8,  bt=-28, bs=-12, ft=30, fs=-10, ba=(40, 110), fa=(50, 125), head=0),
    dict(n='walk2',  hip=(31, 58), lean=8,  bt=6,   bs=-24, ft=4,  fs=-30, ba=(30, 112), fa=(60, 118), head=0),
    dict(n='jump',   hip=(32, 48), lean=10, bt=40,  bs=-95, ft=70,  fs=-100, ba=(70, 90), fa=(100, 70), head=-5),
    dict(n='crouch', hip=(31, 72), lean=22, bt=-60, bs=95, ft=70, fs=-110, ba=(45, 100), fa=(65, 110), head=-10),
    dict(n='block',  hip=(29, 58), lean=-4, bt=-16, bs=-10, ft=20, fs=-18, ba=(85, 150), fa=(100, 150), head=6),
    dict(n='punch1', hip=(29, 58), lean=-2, bt=-20, bs=-8,  ft=22, fs=-18, ba=(70, 100), fa=(20, 140), head=0),
    dict(n='punch2', hip=(33, 58), lean=14, bt=-30, bs=-4,  ft=26, fs=-16, ba=(30, 120), fa=(92, 0),   head=0),
    dict(n='punch3', hip=(31, 58), lean=8,  bt=-22, bs=-8,  ft=24, fs=-18, ba=(40, 115), fa=(70, 60),  head=0),
    dict(n='kick1',  hip=(29, 58), lean=-6, bt=-6,  bs=-4,  ft=85, fs=-95, ba=(30, 100), fa=(60, 110), head=0),
    dict(n='kick2',  hip=(27, 58), lean=-24, bt=-4, bs=0,   ft=96, fs=0,   ba=(20, 90),  fa=(50, 100), head=4),
    dict(n='kick3',  hip=(29, 58), lean=-8, bt=-8,  bs=-4,  ft=60, fs=-60, ba=(30, 100), fa=(55, 110), head=0),
    dict(n='hit',    hip=(27, 58), lean=-22, bt=-26, bs=-6, ft=16, fs=-12, ba=(-30, 40), fa=(-20, 50), head=-18),
    dict(n='ko',     hip=(29, 90), lean=22, bt=150, bs=-105, ft=138, fs=-95, ba=(-5, 0), fa=(20, 0), head=12),
]

PALETTES = {
    'red':  dict(gi=(214, 58, 50), gi_dark=(150, 34, 34), belt=(40, 32, 30), skin=(236, 188, 150),
                 hair=(52, 36, 30), band=(250, 240, 230), outline=(36, 22, 26)),
    'blue': dict(gi=(58, 112, 214), gi_dark=(36, 70, 150), belt=(240, 236, 220), skin=(196, 140, 104),
                 hair=(24, 22, 30), band=(250, 210, 60), outline=(18, 22, 40)),
}


def point(origin, length, angle_deg):
    """From origin, `length` along an angle measured from straight down, positive towards +x."""
    a = math.radians(angle_deg)
    return origin[0] + length * math.sin(a), origin[1] + length * math.cos(a)


def limb(d, a, b, width, fill, outline):
    a = (a[0] * S, a[1] * S)
    b = (b[0] * S, b[1] * S)
    for w, col in ((width + 2.4, outline), (width, fill)):
        r = w * S / 2
        d.line([a, b], fill=col, width=int(w * S))
        for p in (a, b):
            d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=col)


def frame(pose, pal):
    im = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    o = pal['outline']
    hip = pose['hip']
    lean = pose['lean']
    neck = point(hip, TORSO, 180 + lean)           # up the torso
    shoulder = point(hip, TORSO - 4, 180 + lean)

    def leg(thigh, shin, near):
        knee = point(hip, THIGH, thigh)
        ankle = point(knee, SHIN, thigh + shin)
        toe = point(ankle, FOOT, thigh + shin + 90 if pose['n'] != 'ko' else thigh + shin + 90)
        g = pal['gi'] if near else pal['gi_dark']
        limb(d, hip, knee, 10, g, o)
        limb(d, knee, ankle, 8.5, g, o)
        limb(d, ankle, toe, 4.8, pal['skin'] if near else tuple(int(c * .85) for c in pal['skin']), o)

    def arm(upper, fore, near):
        elbow = point(shoulder, UPPER, upper)
        wrist = point(elbow, FORE, upper + fore - 180 if fore else upper)
        g = pal['gi'] if near else pal['gi_dark']
        skin = pal['skin'] if near else tuple(int(c * .85) for c in pal['skin'])
        limb(d, shoulder, elbow, 8, g, o)
        limb(d, elbow, wrist, 6, skin, o)
        r = 4.2 * S
        w = (wrist[0] * S, wrist[1] * S)
        d.ellipse([w[0] - r - 1.2 * S, w[1] - r - 1.2 * S, w[0] + r + 1.2 * S, w[1] + r + 1.2 * S], fill=o)
        d.ellipse([w[0] - r, w[1] - r, w[0] + r, w[1] + r], fill=skin)

    arm(*pose['ba'], near=False)
    leg(pose['bt'], pose['bs'], near=False)
    # the torso: a thick rounded limb, the gi, a belt across the hip
    limb(d, hip, neck, 17, pal['gi'], o)
    # the belt: a band round the waist, its knot hanging in front
    limb(d, point(hip, 2, 180 + lean), point(hip, 5, 180 + lean), 16.5, pal['belt'], pal['belt'])
    knot = point(point(hip, 3.5, 180 + lean), 6, 90 + lean)
    limb(d, knot, point(knot, 6, 20), 2.6, pal['belt'], o)
    # the gi's opening: a skin V at the chest
    chest = point(hip, TORSO - 7, 180 + lean)
    limb(d, chest, point(chest, 5, 180 + lean), 3.2, pal['skin'], pal['skin'])
    leg(pose['ft'], pose['fs'], near=True)
    # head: a circle with hair on the back, a headband, an eye looking forward
    head = point(neck, HEAD + 2, 180 + lean + pose['head'])
    hx, hy = head[0] * S, head[1] * S
    r = HEAD * S
    d.ellipse([hx - r - 1.2 * S, hy - r - 1.2 * S, hx + r + 1.2 * S, hy + r + 1.2 * S], fill=o)
    d.ellipse([hx - r, hy - r, hx + r, hy + r], fill=pal['skin'])
    d.pieslice([hx - r, hy - r, hx + r, hy + r], 150 + lean, 330 + lean, fill=pal['hair'])
    tilt = math.radians(lean + pose['head'])
    bx, by = hx - math.sin(tilt) * r * .35, hy - math.cos(tilt) * r * .35
    d.line([(bx - r * math.cos(tilt), by + r * math.sin(tilt)), (bx + r * math.cos(tilt), by - r * math.sin(tilt))],
           fill=pal['band'], width=int(2.6 * S))
    tail = (bx - r * math.cos(tilt), by + r * math.sin(tilt))
    d.line([tail, (tail[0] - 5 * S, tail[1] + 4 * S)], fill=pal['band'], width=int(2 * S))
    ex, ey = hx + r * .45 * math.cos(tilt), hy + r * .15
    if pose['n'] in ('ko',):
        d.line([(ex - 2 * S, ey - 2 * S), (ex + 2 * S, ey + 2 * S)], fill=o, width=S)
        d.line([(ex - 2 * S, ey + 2 * S), (ex + 2 * S, ey - 2 * S)], fill=o, width=S)
    else:
        d.ellipse([ex - 1.3 * S, ey - 1.6 * S, ex + 1.3 * S, ey + 1.6 * S], fill=o)
    arm(*pose['fa'], near=True)
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
