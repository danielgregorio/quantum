"""Draws Rally's art and its track (projects/rally/): two cars on a circuit seen from above.

Pixel art at the game's own size (a 384x216 screen of 16x16 tiles, split in two
for two players), drawn without smoothing and outlined, like scripts/art/crates.py.

- assets/cars.png, 16x16 frames: the red car 0 facing right (flipped for
  left), 1 up, 2 down; the blue car 3, 4, 5 the same
- assets/track.png, 16x16 tiles: 0 asphalt, 1 grass, 2 the finish line's
  squares, 3 a tyre wall, 4 grass with a bush, 5 a grid mark on the asphalt
- assets/gate.png, 16x80: the barrier across the road at the start, lifted
  at the green light
- track/track.tmx (and track.tsx): the circuit, 60x34 tiles, drawn below as
  text — a ground layer, a walls layer that stops the cars (the grass, and
  tyres on three sides), and the zones the laps are counted by: the finish line, and halfway
  round, at the top of the loop in the infield

    python scripts/art/rally.py
CC0.
"""
import random
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2] / 'projects' / 'rally'
OUTLINE = (20, 20, 26, 255)


def rgb(r, g, b):
    return (r, g, b, 255)


ASPHALT, ASPHALT_DARK, ASPHALT_LIGHT = rgb(84, 86, 94), rgb(72, 74, 82), rgb(98, 100, 108)
GRASS, GRASS_DARK, GRASS_LIGHT = rgb(72, 150, 64), rgb(58, 128, 54), rgb(96, 174, 80)
WHITE, BLACK, RED = rgb(240, 240, 236), rgb(28, 28, 32), rgb(206, 52, 48)
CARS = [(rgb(214, 56, 48), rgb(150, 34, 30)), (rgb(60, 112, 222), rgb(36, 72, 160))]
GLASS, TYRE = rgb(150, 210, 236), rgb(30, 30, 34)

# The circuit: g grass, . asphalt, = the finish line, s a grid mark; the edge is tyres.
W, H = 60, 34
ROADS = [(2, 2, 57, 6),      # the straight at the top, run to the right
         (53, 2, 57, 31),    # down the right side
         (36, 27, 57, 31),   # along the bottom, to the loop
         (36, 15, 40, 31),   # up the loop's right leg
         (20, 15, 40, 19),   # across its top: halfway
         (20, 15, 24, 31),   # down its left leg
         (2, 27, 24, 31),    # along the bottom again
         (2, 2, 6, 31)]      # and up the left side to the line
FINISH = 30                  # the column of the finish line, on the top straight
HALF = 30                    # and of halfway, across the loop's top
GRID = [(27, 3), (27, 5)]    # where the cars start, behind the line


def circuit():
    rows = [['g'] * W for _ in range(H)]
    for c0, r0, c1, r1 in ROADS:
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                rows[r][c] = '.'
    for r in range(2, 7):
        rows[r][FINISH] = '='
    for c, r in GRID:
        rows[r][c] = 's'
    return rows


def noise(d, colors, seed, n=18):
    rnd = random.Random(seed)
    for _ in range(n):
        d.point((rnd.randrange(16), rnd.randrange(16)), fill=rnd.choice(colors))


def tiles():
    sheet = Image.new('RGBA', (16 * 6, 16), (0, 0, 0, 0))
    for i in range(6):
        im = Image.new('RGBA', (16, 16), ASPHALT)
        d = ImageDraw.Draw(im)
        if i in (0, 5):
            noise(d, [ASPHALT_DARK, ASPHALT_LIGHT], 1)
            if i == 5:   # a grid mark: a white bracket the car stands in
                d.line((2, 2, 13, 2), fill=WHITE)
                d.line((2, 2, 2, 13), fill=WHITE)
                d.line((2, 13, 13, 13), fill=WHITE)
        elif i in (1, 4):
            d.rectangle((0, 0, 15, 15), fill=GRASS)
            noise(d, [GRASS_DARK, GRASS_LIGHT], 2, 24)
            if i == 4:   # a bush
                d.ellipse((3, 4, 12, 12), fill=OUTLINE)
                d.ellipse((4, 4, 11, 11), fill=GRASS_DARK)
                d.ellipse((5, 5, 9, 8), fill=GRASS_LIGHT)
        elif i == 2:     # the finish line: squares of four
            for y in range(4):
                for x in range(4):
                    d.rectangle((x * 4, y * 4, x * 4 + 3, y * 4 + 3), fill=WHITE if (x + y) % 2 == 0 else BLACK)
        elif i == 3:     # tyres, stacked, painted red and white
            d.rectangle((0, 0, 15, 15), fill=GRASS_DARK)
            for k, (x, y) in enumerate(((0, 0), (8, 0), (0, 8), (8, 8))):
                d.ellipse((x, y, x + 7, y + 7), fill=OUTLINE)
                d.ellipse((x + 1, y + 1, x + 6, y + 6), fill=RED if k in (0, 3) else WHITE)
                d.ellipse((x + 3, y + 3, x + 4, y + 4), fill=OUTLINE)
        sheet.paste(im, (i * 16, 0))
    return sheet


def car(body, dark):
    """Facing right: the nose at the right, the windscreen before it, a white stripe down the middle."""
    im = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for x in (2, 10):    # the tyres, standing out above and below
        d.rectangle((x, 2, x + 3, 13), fill=TYRE)
    d.rounded_rectangle((1, 4, 14, 11), radius=2, fill=OUTLINE)
    d.rounded_rectangle((2, 5, 13, 10), radius=1, fill=body)
    d.line((2, 10, 13, 10), fill=dark)
    d.rectangle((9, 5, 10, 10), fill=GLASS)           # the windscreen
    d.rectangle((4, 5, 5, 10), fill=dark)             # the rear window
    d.line((2, 7, 13, 7), fill=WHITE)                 # the stripe
    d.line((2, 8, 8, 8), fill=WHITE)
    return im


def cars():
    sheet = Image.new('RGBA', (16 * 6, 16), (0, 0, 0, 0))
    for k, (body, dark) in enumerate(CARS):
        right = car(body, dark)
        for j, im in enumerate((right, right.rotate(90), right.rotate(-90))):   # right, up, down
            sheet.paste(im, ((k * 3 + j) * 16, 0))
    return sheet


def gate():
    im = Image.new('RGBA', (16, 80), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((5, 0, 10, 79), fill=OUTLINE)
    for y in range(1, 79, 8):
        d.rectangle((6, y, 9, min(78, y + 6)), fill=RED if (y // 8) % 2 == 0 else WHITE)
    for y in (0, 74):   # its feet
        d.rectangle((3, y, 12, y + 5), fill=OUTLINE)
        d.rectangle((4, y + 1, 11, y + 4), fill=rgb(60, 60, 68))
    return im


def tmx(rows):
    rnd = random.Random(7)
    ground, walls = [], []
    for r in range(H):
        for c in range(W):
            cell = rows[r][c]
            edge = r == H - 1 or c in (0, W - 1)   # tyres round the edge; grass along the top, under the HUD
            ground.append({'.': 1, '=': 3, 's': 6}.get(cell, 2))
            if edge:
                walls.append(4)
            elif cell == 'g':
                walls.append(5 if rnd.random() < 0.08 else 2)
            else:
                walls.append(0)

    def csv(gids):
        return ',\n'.join(','.join(str(g) for g in gids[r * W:(r + 1) * W]) for r in range(H))

    def zone(i, name, col, top):
        return (f'  <object id="{i}" name="{name}" class="zone" x="{col * 16}" y="{top * 16}" width="16" '
                f'height="80">\n   <properties>\n    <property name="tag" value="{name}"/>\n   </properties>\n'
                f'  </object>\n')

    return (f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<map version="1.10" tiledversion="1.10.2" orientation="orthogonal" renderorder="right-down" '
            f'width="{W}" height="{H}" tilewidth="16" tileheight="16" infinite="0" nextlayerid="4" nextobjectid="3">\n'
            f' <tileset firstgid="1" source="track.tsx"/>\n'
            f' <layer id="1" name="ground" width="{W}" height="{H}">\n  <data encoding="csv">\n{csv(ground)}\n</data>\n'
            f' </layer>\n'
            f' <layer id="2" name="walls" width="{W}" height="{H}">\n  <properties>\n'
            f'   <property name="collision" type="bool" value="true"/>\n  </properties>\n'
            f'  <data encoding="csv">\n{csv(walls)}\n</data>\n </layer>\n'
            f' <objectgroup id="3" name="laps">\n'
            + zone(1, 'finish', FINISH, 2) + zone(2, 'half', HALF, 15) +
            ' </objectgroup>\n</map>\n')


def main():
    (ROOT / 'assets').mkdir(parents=True, exist_ok=True)
    (ROOT / 'track').mkdir(parents=True, exist_ok=True)
    tiles().save(ROOT / 'assets' / 'track.png')
    cars().save(ROOT / 'assets' / 'cars.png')
    gate().save(ROOT / 'assets' / 'gate.png')
    (ROOT / 'track' / 'track.tsx').write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<tileset version="1.10" tiledversion="1.10.2" name="track" tilewidth="16" tileheight="16" tilecount="6" '
        'columns="6">\n <image source="../assets/track.png" width="96" height="16"/>\n</tileset>\n', encoding='utf-8')
    (ROOT / 'track' / 'track.tmx').write_text(tmx(circuit()), encoding='utf-8')
    print('\n'.join(''.join(r) for r in circuit()))


if __name__ == '__main__':
    main()
