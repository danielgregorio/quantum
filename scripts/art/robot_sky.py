#!/usr/bin/env python
"""Compose the sky of Godot's "Platformer 2D" demo for projects/robot/.

    python scripts/art/robot_sky.py <godot-demo-projects>/2d/platformer

The demo's ParallaxBackground (level/background/parallax_background.tscn)
has a sky and four groups of clouds, which scroll at a fiftieth and a
hundredth of the camera, and two rows of distant platforms at a fiftieth and
a twenty-fifth. Here they are drawn as the 800x480 screen first shows them,
into two pictures that repeat across: assets/sky.png (the sky and the clouds)
and assets/hills.png (the two rows of platforms, clear above them). robot.q
places them with qg:parallax.
"""

import sys
from pathlib import Path

from PIL import Image

OUT = Path(__file__).resolve().parents[2] / 'projects' / 'robot' / 'assets'
H = 480
# (texture, x, y, scale) in screen pixels: the scene's positions, its groups and the clouds' motion_offset added
CLOUDS = [('cloud_2', -780 + 470, 4, 1), ('cloud_3', -780 + 726, 91, 1), ('cloud_3', -780 + 1133, 113, 1),
          ('cloud_3', -780 + 1513, 165, 1), ('cloud_1', -780 + 396, 109, 1),
          ('cloud_2', -135, 213, 1), ('cloud_1', 19, 77, 0.5), ('cloud_3', 140, 261, 0.5),
          ('cloud_2', 390 + 1034, -60, 1), ('cloud_2', 390 + 491, 251, 1), ('cloud_2', 390 + 545, 108, 1),
          ('cloud_1', 390 - 164, 212, 1), ('cloud_1', 390 + 287, 220, 0.5),
          ('cloud_2', 780 - 293, 64, 1), ('cloud_2', 780 - 229, 199, 1), ('cloud_1', 780 + 83, 115, 1),
          ('cloud_1', 780 + 7, 177, 1), ('cloud_3', 780 + 226, 14, 0.5)]


def load(demo: Path, name: str, scale: float = 1.0) -> Image.Image:
    im = Image.open(demo / 'level' / 'background' / f'{name}.webp').convert('RGBA')
    if scale != 1.0:
        im = im.resize((round(im.width * scale), round(im.height * scale)), Image.LANCZOS)
    return im


def row(texture: Image.Image, width: int) -> Image.Image:
    out = Image.new('RGBA', (width, texture.height), (0, 0, 0, 0))
    for x in range(0, width, texture.width):
        out.alpha_composite(texture, (x, 0))
    return out


def main(argv) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    demo = Path(argv[0])
    OUT.mkdir(parents=True, exist_ok=True)
    sky_tex = load(demo, 'sky', 1.2)                   # 2458 wide: one picture across, repeated
    width = sky_tex.width
    left = -809                                        # where the demo's sky starts
    sky = Image.new('RGBA', (width, H), (0, 0, 0, 255))
    sky.alpha_composite(sky_tex.crop((0, 0, width, H)), (0, 0))
    for name, x, y, scale in CLOUDS:
        cloud = load(demo, name, scale)
        for shift in (-width, 0, width):               # a cloud across the seam shows on both sides
            sky.alpha_composite(cloud, (x - 550 - left + shift, y)) if 0 <= y < H else None
    sky.convert('RGB').save(OUT / 'sky.png', optimize=True)

    # the platforms: Sprite2Ds centred on their layer's y plus their own, a 2048 px region repeating the texture
    hills = Image.new('RGBA', (2048, H), (0, 0, 0, 0))
    far = row(load(demo, 'distant_platforms_2'), 2048).crop((0, 0, 2048, 251))
    hills.alpha_composite(far, (0, round(243 + 301.2 - 251 / 2)))
    near = row(load(demo, 'distant_platforms_1'), 2048).crop((0, 0, 2048, 251))
    near = near.resize((round(2048 * 1.2), round(251 * 1.2)), Image.LANCZOS).crop((0, 0, 2048, round(251 * 1.2)))
    top = round(246 + 278.2 - 251 * 1.2 / 2)
    hills.alpha_composite(near.crop((0, 0, 2048, H - top)), (0, top))
    hills.save(OUT / 'hills.png', optimize=True)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
