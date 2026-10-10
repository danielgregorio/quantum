#!/usr/bin/env python
"""Pack the art of Godot's "JRPG" demo for projects/rpg/.

    python scripts/art/rpg.py <godot-demo-projects>/2d/role_playing_game

The demo (godotengine/godot-demo-projects, 2d/role_playing_game, MIT) draws
its world with three TileMapLayers whose tiles are single images, each
placed flipped or transposed. Here every (image, transform) used becomes one
64 px tile of assets/tiles.png, and the layers are printed as the CSV rows of
the qg:tilemaps in rpg.q (the visible 20x11 cells). The pawns, the
combatants and the combat background are packed as they are.
"""

import base64
import re
import struct
import sys
from pathlib import Path

from PIL import Image

OUT = Path(__file__).resolve().parents[2] / 'projects' / 'rpg' / 'assets'
TILE, COLS, ROWS = 64, 20, 11
LAYERS = ('Ground', 'Pathways', 'Grid')     # drawn in this order; Grid is the one that stops the walkers
PAWNS = ('grid_movement/pawns/player_exploration.png', 'grid_movement/pawns/player_exploration_bump.png',
         'grid_movement/pawns/opponent_exploration.png', 'grid_movement/grid/tiles/object.png')
FIGHTERS = ('combat/combatants/sprites/player_battle.png', 'combat/combatants/sprites/player_surprised.png',
            'combat/combatants/sprites/opponent_battle.png', 'combat/combatants/sprites/opponent_surprised.png',
            'combat/combatants/sprites/shadow.png')


def _ext(text: str, kind: str) -> dict:
    return {m[2]: m[1] for m in re.finditer(
        rf'\[ext_resource type="{kind}"[^\]]*? path="res://([^"]+)" id="([^"]+)"\]', text)}


def tileset(demo: Path, path: str) -> dict:
    """source id -> (image path, {alternative id: [flags]})"""
    text = (demo / path).read_text()
    textures = _ext(text, 'Texture2D')
    subs = {}
    for block in re.split(r'\n\[sub_resource ', text):
        m = re.match(r'type="TileSetAtlasSource" id="([^"]+)"', block)
        if not m:
            continue
        tex = re.search(r'texture = ExtResource\("([^"]+)"\)', block)
        alts = {}
        for a in re.finditer(r'0:0/(\d+)/(flip_h|flip_v|transpose) = true', block):
            alts.setdefault(int(a[1]), []).append(a[2])
        subs[m[1]] = (textures[tex[1]] if tex else None, alts)
    return {int(m[1]): subs[m[2]] for m in re.finditer(r'sources/(\d+) = SubResource\("([^"]+)"\)', text)}


def layers(demo: Path) -> dict:
    scene = (demo / 'grid_movement' / 'exploration.tscn').read_text()
    resources = _ext(scene, 'TileSet')
    out = {}
    for m in re.finditer(r'\[node name="([^"]+)" type="TileMapLayer"[^\]]*\]\n(.*?)(?=\n\[)', scene, re.S):
        name, body = m[1], m[2]
        if name not in LAYERS:
            continue
        sources = tileset(demo, resources[re.search(r'tile_set = ExtResource\("([^"]+)"\)', body)[1]])
        data = base64.b64decode(re.search(r'tile_map_data = PackedByteArray\("([^"]*)"\)', body)[1])
        cells = {}
        for i in range(2, len(data), 12):
            x, y, source, _, _, alt = struct.unpack('<hhHHHH', data[i:i + 12])
            if 0 <= x < COLS and 0 <= y < ROWS:
                image, alts = sources[source]
                cells[(x, y)] = (image, tuple(alts.get(alt, [])))
        out[name] = cells
    return out


def transformed(demo: Path, image: str, flags: tuple) -> Image.Image:
    # Godot's order: transpose, then the flips
    im = Image.open(demo / image).convert('RGBA')
    if 'transpose' in flags:
        im = im.transpose(Image.Transpose.TRANSPOSE)
    if 'flip_h' in flags:
        im = im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    if 'flip_v' in flags:
        im = im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return im


def sheet(demo: Path, files, cell: int) -> Image.Image:
    out = Image.new('RGBA', (cell * len(files), cell), (0, 0, 0, 0))
    for i, f in enumerate(files):
        im = Image.open(demo / f).convert('RGBA')
        out.alpha_composite(im, (i * cell + (cell - im.width) // 2, (cell - im.height) // 2))
    return out


def main(argv) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    demo = Path(argv[0])
    OUT.mkdir(parents=True, exist_ok=True)
    found = layers(demo)
    tiles: list = []
    for name in LAYERS:
        for y in range(ROWS):
            for x in range(COLS):
                t = found[name].get((x, y))
                if t is not None and t not in tiles:
                    tiles.append(t)
    per_row = 8
    atlas = Image.new('RGBA', (per_row * TILE, -(-len(tiles) // per_row) * TILE), (0, 0, 0, 0))
    for i, (image, flags) in enumerate(tiles):
        atlas.alpha_composite(transformed(demo, image, flags), ((i % per_row) * TILE, (i // per_row) * TILE))
    atlas.save(OUT / 'tiles.png')
    sheet(demo, PAWNS, 64).save(OUT / 'pawns.png')
    sheet(demo, FIGHTERS, 128).save(OUT / 'fighters.png')
    Image.open(demo / 'combat' / 'background' / 'combat_background.png').convert('RGB').save(OUT / 'arena.png')
    for name in LAYERS:
        print(f'<!-- {name} -->')
        for y in range(ROWS):
            print(','.join(str(tiles.index(found[name][(x, y)]) + 1 if (x, y) in found[name] else 0)
                           for x in range(COLS)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
