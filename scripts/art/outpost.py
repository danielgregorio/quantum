"""Draws Outpost's art and its map (projects/outpost/): a frontier town seen from above.

Pixel art at the game's own size (16x16 tiles), drawn without smoothing and outlined, like scripts/art/crates.py.
The map is the world's and the game's at once: the server keeps its walls and its areas, the game draws it.

- assets/land.png, 16x16 tiles: 0 grass, 1 a path, 2 the town's flagstones, 3 planks (a house's floor), 4 the
  sewers' floor, 5 the cave's floor, 6 water, 7 stairs down; 8 the palisade, 9 a house's wall, 10 the shop's
  counter, 11 a tree, 12 rock, 13 the sewers' wall, 14 a bush, 15 the temple's altar
- assets/folk.png, 16x16 frames: 0 a hero, 1 a hero in green, 2 Old Marta, the trader, 3 Captain Rhea
- assets/beasts.png, 16x16 frames: 0 a rat, 1 a wolf, 2 the Old Bear (drawn twice its size by the game)
- maps/mainland.tmx, 96x64 tiles: the town (its temple, Marta's shop, the gate east), the sewers under it (south),
  the forest east of the gate, a lake, and the cave north-east, where the Old Bear sleeps. The tile layer `walls`
  is what no one walks through; the object layer `areas` names the places, as zones: temple, shop-counter, town,
  gate, sewers, forest, cave.

    python scripts/art/outpost.py
CC0.
"""
import random
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[2] / 'projects' / 'outpost'
OUTLINE = (24, 20, 28, 255)
W, H, T = 96, 64, 16


def rgb(r, g, b):
    return (r, g, b, 255)


GRASS, GRASS_DARK, GRASS_LIGHT = rgb(86, 140, 64), rgb(66, 116, 52), rgb(112, 166, 80)
DIRT, DIRT_DARK = rgb(164, 132, 92), rgb(136, 106, 72)
STONE, STONE_DARK, STONE_LIGHT = rgb(132, 130, 124), rgb(104, 102, 98), rgb(156, 154, 148)
WOOD, WOOD_DARK, WOOD_LIGHT = rgb(150, 104, 60), rgb(110, 74, 42), rgb(184, 136, 84)
SEWER, SEWER_DARK = rgb(62, 70, 66), rgb(44, 50, 48)
CAVE, CAVE_DARK = rgb(88, 78, 70), rgb(66, 58, 52)
WATER, WATER_LIGHT = rgb(52, 98, 156), rgb(92, 140, 196)
SKIN = rgb(232, 188, 150)


def tile(fill=(0, 0, 0, 0)):
    return Image.new('RGBA', (T, T), fill)


def speckled(base, dots, seed, n=14):
    rnd = random.Random(seed)
    im = tile(base)
    for _ in range(n):
        im.putpixel((rnd.randrange(T), rnd.randrange(T)), rnd.choice(dots))
    return im


def flagstones():
    im = tile(STONE)
    d = ImageDraw.Draw(im)
    for y in (0, 8):
        d.line((0, y, 15, y), fill=STONE_DARK)
    for x, y in ((0, 0), (8, 0), (4, 8), (12, 8)):
        d.line((x, y, x, y + 7), fill=STONE_DARK)
    d.point([(2, 2), (10, 3), (6, 11), (14, 12)], fill=STONE_LIGHT)
    return im


def planks():
    im = tile(WOOD)
    d = ImageDraw.Draw(im)
    for y in (3, 7, 11, 15):
        d.line((0, y, 15, y), fill=WOOD_DARK)
    d.point([(5, 1), (12, 5), (3, 9), (9, 13)], fill=WOOD_LIGHT)
    return im


def water():
    im = tile(WATER)
    d = ImageDraw.Draw(im)
    for x, y in ((2, 4), (9, 9), (5, 13)):
        d.line((x, y, x + 3, y), fill=WATER_LIGHT)
    return im


def stairs():
    im = tile(SEWER_DARK)
    d = ImageDraw.Draw(im)
    for i, y in enumerate(range(1, 16, 3)):
        d.rectangle((1, y, 14, y + 1), fill=STONE if i % 2 == 0 else STONE_LIGHT)
    return im


def palisade():
    im = tile()
    d = ImageDraw.Draw(im)
    for x in (0, 4, 8, 12):
        d.rectangle((x, 1, x + 3, 15), fill=WOOD_DARK, outline=OUTLINE)
        d.polygon([(x, 1), (x + 1, 0), (x + 2, 0), (x + 3, 1)], fill=WOOD_LIGHT)
    return im


def house_wall():
    im = tile(rgb(196, 176, 140))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 15, 3), fill=rgb(150, 70, 52))              # the roof's eaves
    d.line((0, 3, 15, 3), fill=OUTLINE)
    for y in (8, 13):
        d.line((0, y, 15, y), fill=rgb(170, 150, 116))
    return im


def counter():
    im = planks()
    d = ImageDraw.Draw(im)
    d.rectangle((0, 2, 15, 12), fill=WOOD_DARK, outline=OUTLINE)
    d.line((1, 3, 14, 3), fill=WOOD_LIGHT)
    return im


def tree():
    im = tile(GRASS)
    d = ImageDraw.Draw(im)
    d.rectangle((7, 11, 8, 15), fill=WOOD_DARK)
    d.ellipse((1, 0, 14, 12), fill=rgb(40, 96, 44), outline=OUTLINE)
    d.ellipse((4, 2, 9, 6), fill=rgb(64, 128, 60))
    return im


def rock():
    im = tile(CAVE_DARK)
    d = ImageDraw.Draw(im)
    d.polygon([(0, 15), (2, 4), (7, 1), (13, 3), (15, 15)], fill=rgb(112, 104, 96), outline=OUTLINE)
    d.line((5, 5, 9, 4), fill=rgb(140, 132, 122))
    return im


def sewer_wall():
    im = tile(rgb(80, 86, 82))
    d = ImageDraw.Draw(im)
    for y in (4, 9, 14):
        d.line((0, y, 15, y), fill=SEWER_DARK)
    for x, y in ((3, 0), (11, 0), (7, 5), (15, 5), (3, 10), (11, 10)):
        d.line((x, y, x, y + 3), fill=SEWER_DARK)
    d.point([(1, 15), (6, 15), (12, 15)], fill=rgb(96, 140, 90))       # moss
    return im


def bush():
    im = tile(GRASS)
    d = ImageDraw.Draw(im)
    d.ellipse((2, 4, 13, 14), fill=rgb(52, 108, 48), outline=OUTLINE)
    d.point([(6, 7), (9, 9)], fill=rgb(200, 60, 60))                     # berries
    return im


def altar():
    im = planks()
    d = ImageDraw.Draw(im)
    d.rectangle((2, 5, 13, 14), fill=STONE_LIGHT, outline=OUTLINE)
    d.rectangle((6, 1, 9, 5), fill=rgb(236, 196, 60), outline=OUTLINE)    # a candle's flame, gold
    return im


def land():
    tiles = [speckled(GRASS, [GRASS_DARK, GRASS_LIGHT], 1), speckled(DIRT, [DIRT_DARK], 2, 10), flagstones(),
             planks(), speckled(SEWER, [SEWER_DARK, rgb(70, 96, 74)], 3, 12), speckled(CAVE, [CAVE_DARK], 4, 12),
             water(), stairs(), palisade(), house_wall(), counter(), tree(), rock(), sewer_wall(), bush(), altar()]
    sheet = Image.new('RGBA', (8 * T, 2 * T))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % 8) * T, (i // 8) * T))
    return sheet


def person(shirt, hat=None, beard=False, cloak=None):
    im = tile()
    d = ImageDraw.Draw(im)
    if cloak:
        d.rectangle((3, 6, 12, 14), fill=cloak, outline=OUTLINE)
    d.rectangle((5, 7, 10, 13), fill=shirt, outline=OUTLINE)             # the body
    d.rectangle((5, 13, 6, 15), fill=OUTLINE)
    d.rectangle((9, 13, 10, 15), fill=OUTLINE)                           # the legs
    d.rectangle((5, 1, 10, 6), fill=SKIN, outline=OUTLINE)               # the head
    d.point([(6, 3), (9, 3)], fill=OUTLINE)
    if hat:
        d.rectangle((4, 0, 11, 2), fill=hat, outline=OUTLINE)
    if beard:
        d.rectangle((6, 5, 9, 6), fill=rgb(220, 220, 220))
    return im


def folk():
    frames = [person(rgb(60, 90, 170)), person(rgb(60, 150, 70)),
              person(rgb(140, 70, 120), hat=rgb(220, 220, 220), cloak=rgb(110, 60, 90)),   # Old Marta, a white hood
              person(rgb(170, 60, 50), hat=rgb(150, 150, 160))]                            # Rhea, a helmet
    sheet = Image.new('RGBA', (len(frames) * T, T))
    for i, f in enumerate(frames):
        sheet.paste(f, (i * T, 0))
    return sheet


def beast(body, dark, size, ears=False, tail=False):
    im = tile()
    d = ImageDraw.Draw(im)
    x0, y0 = 8 - size, 15 - size
    d.ellipse((x0, y0, 8 + size, 15), fill=body, outline=OUTLINE)
    hx = 8 + size - 2
    d.ellipse((hx - 3, y0 - 1, hx + 3, y0 + 5), fill=body, outline=OUTLINE)      # the head, to the right
    d.point([(hx + 1, y0 + 1)], fill=rgb(230, 40, 40))
    if ears:
        d.polygon([(hx - 2, y0), (hx - 1, y0 - 3), (hx, y0)], fill=dark)
    if tail:
        d.line((x0, y0 + size, x0 - 3, y0 + size - 2), fill=dark, width=2)
    return im


def beasts():
    frames = [beast(rgb(120, 110, 104), rgb(90, 80, 76), 4, tail=True),
              beast(rgb(130, 130, 136), rgb(90, 90, 96), 6, ears=True, tail=True),
              beast(rgb(110, 70, 40), rgb(80, 50, 28), 7, ears=True)]
    sheet = Image.new('RGBA', (len(frames) * T, T))
    for i, f in enumerate(frames):
        sheet.paste(f, (i * T, 0))
    return sheet


# -- the map ----------------------------------------------------------------------------------------------------

GRASS_T, PATH, FLAG, PLANK, SEWER_F, CAVE_F, WATER_T, STAIRS = range(1, 9)
PALISADE, HOUSE, COUNTER, TREE, ROCK, SEWER_W, BUSH, ALTAR = range(9, 17)

AREAS = {                                     # name: (x0, y0, x1, y1), tiles, inclusive
    'town': (9, 17, 38, 42),
    'temple': (13, 20, 17, 23),
    'shop-counter': (29, 20, 31, 20),         # behind the counter: where Marta stands
    'gate': (41, 27, 43, 31),
    'sewers': (10, 50, 37, 59),
    'forest': (48, 34, 88, 58),
    'cave': (70, 8, 86, 20),
}


def mainland():
    rnd = random.Random(7)
    ground = [[GRASS_T] * W for _ in range(H)]
    walls = [[0] * W for _ in range(H)]

    def fill(layer, x0, y0, x1, y1, t):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                layer[y][x] = t

    def box(x0, y0, x1, y1, t):
        for x in range(x0, x1 + 1):
            walls[y0][x] = walls[y1][x] = t
        for y in range(y0, y1 + 1):
            walls[y][x0] = walls[y][x1] = t

    # the edge of the world: trees, and rock in the north-east
    box(0, 0, W - 1, H - 1, TREE)
    # the town: flagstones inside a palisade, the gate east, the stairs to the sewers south
    fill(ground, 8, 16, 39, 43, FLAG)
    box(8, 16, 39, 43, PALISADE)
    for y in range(28, 31):
        walls[y][39] = 0
    for x in (23, 24):
        walls[43][x] = 0
    # the temple (north-west) and Marta's shop (north-east), their doors south
    fill(ground, 12, 19, 18, 25, PLANK)
    box(12, 19, 18, 25, HOUSE)
    walls[25][15] = 0
    walls[20][15] = ALTAR
    fill(ground, 26, 18, 34, 25, PLANK)
    box(26, 18, 34, 25, HOUSE)
    walls[25][30] = 0
    for x in range(28, 33):
        walls[21][x] = COUNTER
    walls[21][27] = walls[21][33] = HOUSE
    # the road from the gate east, then north to the cave and south into the forest
    fill(ground, 40, 28, 60, 30, PATH)
    fill(ground, 58, 10, 60, 30, PATH)
    fill(ground, 60, 10, 70, 12, PATH)
    fill(ground, 58, 30, 60, 46, PATH)
    # the sewers: down the stairs, a dark hall with pillars
    fill(ground, 23, 44, 24, 48, STAIRS)
    fill(walls, 8, 44, 22, 48, SEWER_W)
    fill(walls, 25, 44, 39, 48, SEWER_W)
    fill(ground, 9, 49, 38, 60, SEWER_F)
    box(8, 49, 39, 61, SEWER_W)
    walls[49][23] = walls[49][24] = 0
    for x in range(12, 37, 6):
        for y in (52, 57):
            walls[y][x] = SEWER_W
    # the lake, north of the road
    for y in range(9, 20):
        for x in range(44, 56):
            if (x - 49.5) ** 2 / 36 + (y - 14) ** 2 / 25 <= 1:
                walls[y][x] = WATER_T
                ground[y][x] = WATER_T
    # the cave: rock with a hall inside, its mouth to the road
    fill(walls, 66, 2, 94, 24, ROCK)
    fill(ground, 66, 2, 94, 24, CAVE_F)
    fill(walls, 70, 7, 87, 21, 0)
    fill(walls, 66, 10, 70, 12, 0)
    for x, y in ((74, 10), (82, 9), (78, 17), (85, 15)):
        walls[y][x] = ROCK
    # the forest: trees and bushes, never on the paths, sparse enough to walk between
    for y in range(26, 62):
        for x in range(42, 95):
            if walls[y][x] or ground[y][x] == PATH or (39 <= x <= 44 and 26 <= y <= 32):
                continue
            r = rnd.random()
            if r < 0.11:
                walls[y][x] = TREE
            elif r < 0.14:
                walls[y][x] = BUSH
    # and a few trees about the town
    for x, y in ((3, 6), (5, 10), (20, 7), (30, 5), (40, 40), (4, 50), (42, 12), (62, 40)):
        walls[y][x] = TREE
    return ground, walls


def tmx(ground, walls) -> str:
    def csv(rows):
        return ',\n'.join(','.join(str(t) for t in row) for row in rows)
    objects = []
    for i, (name, (x0, y0, x1, y1)) in enumerate(AREAS.items(), start=1):
        objects.append(f'  <object id="{i}" name="{name}" class="zone" x="{x0 * T}" y="{y0 * T}" '
                       f'width="{(x1 - x0 + 1) * T}" height="{(y1 - y0 + 1) * T}">\n'
                       f'   <properties>\n    <property name="tag" value="area"/>\n   </properties>\n  </object>')
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<map version="1.10" tiledversion="1.10.2" orientation="orthogonal" renderorder="right-down" '
            f'width="{W}" height="{H}" tilewidth="{T}" tileheight="{T}" infinite="0" nextlayerid="4" '
            f'nextobjectid="{len(AREAS) + 1}">\n'
            f' <tileset firstgid="1" name="land" tilewidth="{T}" tileheight="{T}" tilecount="16" columns="8">\n'
            f'  <image source="../assets/land.png" width="{8 * T}" height="{2 * T}"/>\n'
            f' </tileset>\n'
            f' <layer id="1" name="ground" width="{W}" height="{H}">\n  <data encoding="csv">\n{csv(ground)}\n'
            f'</data>\n </layer>\n'
            f' <layer id="2" name="walls" width="{W}" height="{H}">\n  <properties>\n'
            f'   <property name="collision" type="bool" value="true"/>\n  </properties>\n'
            f'  <data encoding="csv">\n{csv(walls)}\n</data>\n </layer>\n'
            f' <objectgroup id="3" name="areas">\n' + '\n'.join(objects) + '\n </objectgroup>\n</map>\n')


def main() -> int:
    (OUT / 'assets').mkdir(parents=True, exist_ok=True)
    (OUT / 'maps').mkdir(parents=True, exist_ok=True)
    land().save(OUT / 'assets' / 'land.png')
    folk().save(OUT / 'assets' / 'folk.png')
    beasts().save(OUT / 'assets' / 'beasts.png')
    ground, walls = mainland()
    (OUT / 'maps' / 'mainland.tmx').write_text(tmx(ground, walls), encoding='utf-8')
    print(f'wrote {OUT.relative_to(OUT.parents[1])}/assets/{{land,folk,beasts}}.png and maps/mainland.tmx')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
