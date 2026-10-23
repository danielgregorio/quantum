"""PandaFoot's art and sounds (projects/pandafoot/assets/): a text screen's box, a goal, the whistles.

- frame.png, 24x24: a box of a DOS screen, a double line in light grey on blue, a nine-slice picture
  (qg:spritesheet slice="8"): its corners stay as drawn, its edges and middle stretch to the panel
- goal.ogg: a crowd roaring a goal, rising and falling (noise through a moving band, and a horn)
- whistle.ogg: the referee's whistle, a short trill (kick-off, half time)
- final.ogg: the final whistle, two short and one long

The sounds are synthesized here (scripts/art/rpg_music.py's .ogg writer). DejaVuSansMono.ttf is copied from
the DejaVu fonts, its licence beside it.

    python scripts/art/pandafoot.py
CC0. Needs numpy and ffmpeg (with libvorbis).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rpg_music import RATE, _envelope, write_ogg  # noqa: E402

OUT = Path(__file__).resolve().parents[2] / 'projects' / 'pandafoot' / 'assets'
BLUE, GREY = (0, 0, 170, 255), (170, 170, 170, 255)


def frame() -> Image.Image:
    im = Image.new('RGBA', (24, 24), BLUE)
    d = ImageDraw.Draw(im)
    d.rectangle((2, 2, 21, 21), outline=GREY)    # ═ and ║: two lines, a pixel apart
    d.rectangle((4, 4, 19, 19), outline=GREY)
    return im


def whistle(seconds: float, seed: int) -> np.ndarray:
    """A pea whistle: a high tone warbling as the pea spins, with breath in it."""
    t = np.arange(int(seconds * RATE)) / RATE
    rng = np.random.default_rng(seed)
    f = 2900 + 120 * np.sin(2 * np.pi * 34 * t)          # the pea's trill
    tone = np.sin(2 * np.pi * np.cumsum(f) / RATE)
    tone += 0.25 * np.sin(2 * np.pi * np.cumsum(2 * f) / RATE)
    breath = rng.uniform(-1, 1, len(t)) * 0.12
    return (tone + breath) * _envelope(len(t), 0.02, 0.06) * 0.45


def silence(seconds: float) -> np.ndarray:
    return np.zeros(int(seconds * RATE))


def goal() -> np.ndarray:
    """A crowd's roar: noise through a band that opens as it swells, and a horn over it."""
    seconds = 2.6
    t = np.arange(int(seconds * RATE)) / RATE
    rng = np.random.default_rng(10)
    hiss = rng.uniform(-1, 1, len(t))
    # a moving band: two one-pole filters, low-passed noise minus a lower one
    out = np.zeros(len(t))
    lo = hi = 0.0
    for i, x in enumerate(hiss):
        k = 0.05 + 0.12 * min(1.0, t[i] / 0.6)
        lo += k * (x - lo)
        hi += 0.01 * (lo - hi)
        out[i] = lo - hi
    swell = np.minimum(1, t / 0.35) * np.exp(-np.maximum(0, t - 1.2) * 1.6)
    voices = 1 + 0.25 * np.sin(2 * np.pi * 3.1 * t) * np.sin(2 * np.pi * 0.7 * t)
    crowd = out * swell * voices
    crowd /= np.max(np.abs(crowd))
    horn_t = t[t < 1.4]
    horn = (np.sign(np.sin(2 * np.pi * 233 * horn_t)) * 0.5 + np.sin(2 * np.pi * 466 * horn_t) * 0.5) \
        * _envelope(len(horn_t), 0.05, 0.3) * 0.18
    crowd[:len(horn)] += horn
    return crowd * 0.8


def final() -> np.ndarray:
    return np.concatenate([whistle(0.22, 1), silence(0.12), whistle(0.22, 2), silence(0.12), whistle(0.9, 3)])


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    frame().save(OUT / 'frame.png')
    for name, samples in (('goal', goal()), ('whistle', whistle(0.45, 0)), ('final', final())):
        write_ogg(samples, OUT / f'{name}.ogg')
        print(f'{name}.ogg: {len(samples) / RATE:.1f} s')
    return 0


if __name__ == '__main__':
    sys.exit(main())
