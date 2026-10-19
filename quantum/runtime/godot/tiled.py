"""A Tiled map (.tmx) read for a qg:tilemap src=.

What is read: every tile layer with CSV data (its `collision` boolean
property makes it solid), and every object layer, whose objects place
prefabs: the object's class (Tiled 1.9+; `type` before) names the prefab,
or its name when it has no class. A point object is placed at its point,
a rectangle at its centre, a tile object (one with a gid) at the centre of
its tile, whose y in Tiled is the bottom edge.

One tileset per map, and no flipped tiles: the map's tile numbers become
the same CSV rows an inline qg:tilemap holds (0 empty, n = tile n-1). A tile
of the tileset (embedded, or an external .tsx) with a class, or a `kind`
property, of ladder, water, ice or hurt is a tile of that kind (qg:tile kind=).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from xml.etree import ElementTree as ET

from quantum.runtime.godot.errors import GameCompileError

_FLIP_BITS = 0xF0000000
KINDS = ('ladder', 'water', 'ice', 'hurt')


@dataclass
class TiledLayer:
    name: str
    rows: List[List[int]]
    collision: bool


@dataclass
class TiledObject:
    prefab: str
    x: float
    y: float
    name: str = ''


@dataclass
class TiledMap:
    width: int
    height: int
    tile_width: int
    tile_height: int
    layers: List[TiledLayer] = field(default_factory=list)
    objects: List[TiledObject] = field(default_factory=list)
    kinds: Dict[int, str] = field(default_factory=dict)   # tile frame -> ladder, water, ice or hurt


def read_tmx(path: Path, line: Optional[int] = None) -> TiledMap:
    where = f'{path.name}: '
    try:
        root = ET.parse(str(path)).getroot()
    except ET.ParseError as e:
        raise GameCompileError(f'{where}not a Tiled map ({e})', line)
    if root.tag != 'map':
        raise GameCompileError(f'{where}not a Tiled map (the root is <{root.tag}>)', line)
    tmap = TiledMap(int(root.get('width', 0)), int(root.get('height', 0)),
                    int(root.get('tilewidth', 0)), int(root.get('tileheight', 0)))
    tilesets = root.findall('tileset')
    if len(tilesets) != 1:
        raise GameCompileError(f'{where}one tileset per map ({len(tilesets)} found)', line)
    firstgid = int(tilesets[0].get('firstgid', 1))
    tileset = tilesets[0]
    if tileset.get('source'):   # an external .tsx, next to the map
        try:
            tileset = ET.parse(str(path.parent / tileset.get('source'))).getroot()
        except (OSError, ET.ParseError) as e:
            raise GameCompileError(f'{where}cannot read the tileset {tileset.get("source")!r} ({e})', line)
    for tile in tileset.findall('tile'):
        kind = tile.get('class') or tile.get('type')
        kind = kind if kind in KINDS else None          # a class of the game's own is not a kind
        props = tile.find('properties')
        for prop in (props.findall('property') if props is not None else []):
            if prop.get('name') == 'kind':
                kind = prop.get('value')
                if kind not in KINDS:
                    raise GameCompileError(f'{where}tile {tile.get("id")} is of kind {kind!r}: a kind is one of '
                                           f'{", ".join(KINDS)}', line)
        if kind:
            tmap.kinds[int(tile.get('id'))] = kind

    for layer in root.findall('layer'):
        data = layer.find('data')
        if data is None or data.get('encoding') != 'csv':
            raise GameCompileError(
                f'{where}layer {layer.get("name")!r} must be saved as CSV (Tiled: Map > Map Properties > '
                f'Tile Layer Format)', line)
        rows = []
        for raw in (data.text or '').strip().splitlines():
            raw = raw.strip().rstrip(',')
            if not raw:
                continue
            row = []
            for v in raw.split(','):
                gid = int(v.strip())
                if gid & _FLIP_BITS:
                    raise GameCompileError(
                        f'{where}layer {layer.get("name")!r} has a flipped or rotated tile; '
                        f'the game language has none', line)
                row.append(gid - firstgid + 1 if gid else 0)
            rows.append(row)
        collision = False
        props = layer.find('properties')
        if props is not None:
            for prop in props.findall('property'):
                if prop.get('name') == 'collision':
                    collision = str(prop.get('value', 'false')).lower() in ('true', '1')
        tmap.layers.append(TiledLayer(layer.get('name', ''), rows, collision))

    for group in root.findall('objectgroup'):
        for obj in group.findall('object'):
            prefab = obj.get('class') or obj.get('type') or obj.get('name')
            if not prefab:
                raise GameCompileError(
                    f'{where}an object in layer {group.get("name")!r} has no class (the prefab it places)', line)
            x, y = float(obj.get('x', 0)), float(obj.get('y', 0))
            w, h = float(obj.get('width', 0)), float(obj.get('height', 0))
            if obj.get('gid') is not None:
                x, y = x + w / 2, y - h / 2
            elif obj.find('point') is None and (w or h):
                x, y = x + w / 2, y + h / 2
            tmap.objects.append(TiledObject(prefab, x, y, obj.get('name', '')))
    if not tmap.layers:
        raise GameCompileError(f'{where}the map has no tile layer', line)
    return tmap
