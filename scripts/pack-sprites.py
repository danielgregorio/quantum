#!/usr/bin/env python
"""Pack separate frame images into one sprite sheet for a qg:spritesheet.

    python scripts/pack-sprites.py OUT.png --tile WxH [--scale 0.75] [--columns N] FRAME.png ...

Every frame is scaled (if asked), centred in a WxH cell, and the cells are
laid out left to right, top to bottom: frame i is `frame="i"` in the .q.
A frame larger than the cell is an error. Needs Pillow.
"""

import argparse
import sys
from pathlib import Path


def main(argv) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('out')
    ap.add_argument('--tile', required=True, help='cell size WxH')
    ap.add_argument('--scale', type=float, default=1.0)
    ap.add_argument('--columns', type=int, default=0, help='cells per row (default: all in one row)')
    ap.add_argument('frames', nargs='+')
    args = ap.parse_args(argv)
    from PIL import Image
    w, h = (int(v) for v in args.tile.lower().split('x'))
    columns = args.columns or len(args.frames)
    rows = -(-len(args.frames) // columns)
    sheet = Image.new('RGBA', (w * columns, h * rows), (0, 0, 0, 0))
    for i, path in enumerate(args.frames):
        im = Image.open(path).convert('RGBA')
        if args.scale != 1.0:
            im = im.resize((round(im.width * args.scale), round(im.height * args.scale)), Image.LANCZOS)
        if im.width > w or im.height > h:
            print(f'{path}: {im.width}x{im.height} does not fit a {w}x{h} cell', file=sys.stderr)
            return 1
        x = (i % columns) * w + (w - im.width) // 2
        y = (i // columns) * h + (h - im.height) // 2
        sheet.alpha_composite(im, (x, y))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out, optimize=True)
    print(f'wrote {args.out}: {len(args.frames)} frames of {w}x{h}, {columns} per row')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
