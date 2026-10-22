"""A Tiled map (.tmx) read for a qg:tilemap src=.

What is read: every tile layer with CSV data (its `collision` boolean
property makes it solid), and every object layer. An object places a
prefab: its class (Tiled 1.9+; `type` before) names the prefab, or its name
when it has no class. A point object is placed at its point, a rectangle at
its centre, a tile object (one with a gid) at the centre of its tile, whose
y in Tiled is the bottom edge. Its name is the instance's name; a `state`
property is the qg:state it starts in.

Three classes are not prefabs: `zone`, a rectangle that becomes a qg:zone
(its `tag` property says what collisions see it as); `exit`, a rectangle
that becomes a qg:exit (its `to` and `at` properties, its name); and `path`,
a polyline (or a polygon) that becomes a qg:path of its name.

A map may use several tilesets; each layer draws from one of them, and each
is a qg:tileset of the game with the same image. A tile may be flipped left
to right, upside down or across its diagonal (Tiled's flip and rotate): a
tile number of a row is then -n (left to right only) or n with Tiled's flag
bits (29 across, 30 upside down, 31 left to right). The map's own
properties are read with `tiled('name')`. A tile of a tileset (embedded, or
an external .tsx) with a class, or a `kind` property, of ladder, water, ice
or hurt is a tile of that kind (qg:tile kind=).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from xml.etree import ElementTree as ET

from quantum.runtime.godot.errors import GameCompileError

FLIP_H, FLIP_V, FLIP_D = 1 << 31, 1 << 30, 1 << 29
_FLIP_BITS = FLIP_H | FLIP_V | FLIP_D | (1 << 28)   # 28: a hexagonal map's rotation, which the language has not
KINDS = ('ladder', 'water', 'ice', 'hurt')
NOT_PREFABS = ('zone', 'exit', 'path')


@dataclass
class TiledLayer:
    name: str
    rows: List[List[int]]
    collision: bool
    tileset: int = 0          # which of the map's tilesets it draws from


@dataclass
class TiledObject:
    prefab: str
    x: float
    y: float
    name: str = ''
    state: Optional[str] = None


@dataclass
class TiledZone:
    name: str
    tag: str
    x: float
    y: float
    width: float
    height: float


@dataclass
class TiledExit:
    name: str
    to: str
    at: str
    x: float
    y: float
    width: float
    height: float


@dataclass
class TiledPath:
    name: str
    points: List[List[float]]


@dataclass
class TiledTileset:
    image: str                # its image's file name: the qg:tileset of the game with the same
    firstgid: int
    kinds: Dict[int, str] = field(default_factory=dict)   # tile frame -> ladder, water, ice or hurt


@dataclass
class TiledMap:
    width: int
    height: int
    tile_width: int
    tile_height: int
    layers: List[TiledLayer] = field(default_factory=list)
    objects: List[TiledObject] = field(default_factory=list)
    zones: List[TiledZone] = field(default_factory=list)
    exits: List[TiledExit] = field(default_factory=list)
    paths: List[TiledPath] = field(default_factory=list)
    tilesets: List[TiledTileset] = field(default_factory=list)
    properties: Dict[str, object] = field(default_factory=dict)

    @property
    def kinds(self) -> Dict[int, str]:
        """The first tileset's tile kinds (the scene's tileset)."""
        return self.tilesets[0].kinds if self.tilesets else {}


def _properties(el: ET.Element, where: str, line: Optional[int]) -> Dict[str, object]:
    out: Dict[str, object] = {}
    props = el.find('properties')
    for prop in (props.findall('property') if props is not None else []):
        kind, raw = prop.get('type', 'string'), prop.get('value', prop.text or '')
        try:
            if kind == 'int':
                out[prop.get('name')] = int(raw)
            elif kind == 'float':
                out[prop.get('name')] = float(raw)
            elif kind == 'bool':
                out[prop.get('name')] = str(raw).lower() == 'true'
            else:
                out[prop.get('name')] = raw
        except ValueError:
            raise GameCompileError(f'{where}property {prop.get("name")!r} is not a {kind}: {raw!r}', line)
    return out


def _tileset(path: Path, el: ET.Element, where: str, line: Optional[int]) -> TiledTileset:
    firstgid = int(el.get('firstgid', 1))
    tileset = el
    if el.get('source'):   # an external .tsx, next to the map
        try:
            tileset = ET.parse(str(path.parent / el.get('source'))).getroot()
        except (OSError, ET.ParseError) as e:
            raise GameCompileError(f'{where}cannot read the tileset {el.get("source")!r} ({e})', line)
    image = tileset.find('image')
    if image is None or not image.get('source'):
        raise GameCompileError(f'{where}tileset {tileset.get("name")!r} is not one image (a collection of images '
                               f'is not a tileset of the game)', line)
    out = TiledTileset(Path(image.get('source')).name, firstgid)
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
            out.kinds[int(tile.get('id'))] = kind
    return out


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
    tmap.properties = _properties(root, where, line)
    tmap.tilesets = sorted((_tileset(path, ts, where, line) for ts in root.findall('tileset')),
                           key=lambda t: t.firstgid)
    if not tmap.tilesets:
        raise GameCompileError(f'{where}the map has no tileset', line)

    def tileset_of(gid: int) -> int:
        i = 0
        for k, ts in enumerate(tmap.tilesets):
            if gid >= ts.firstgid:
                i = k
        return i

    for layer in root.findall('layer'):
        data = layer.find('data')
        if data is None or data.get('encoding') != 'csv':
            raise GameCompileError(
                f'{where}layer {layer.get("name")!r} must be saved as CSV (Tiled: Map > Map Properties > '
                f'Tile Layer Format)', line)
        rows, used = [], set()
        for raw in (data.text or '').strip().splitlines():
            raw = raw.strip().rstrip(',')
            if not raw:
                continue
            row = []
            for v in raw.split(','):
                value = int(v.strip())
                flags, gid = value & _FLIP_BITS, value & ~_FLIP_BITS
                if flags & (1 << 28):
                    raise GameCompileError(f'{where}layer {layer.get("name")!r} has a tile turned as on a hexagonal '
                                           f'map; the game language\'s maps are square', line)
                if not gid:
                    row.append(0)
                    continue
                k = tileset_of(gid)
                used.add(k)
                n = gid - tmap.tilesets[k].firstgid + 1
                row.append(-n if flags == FLIP_H else n | flags)
            rows.append(row)
        if len(used) > 1:
            raise GameCompileError(f'{where}layer {layer.get("name")!r} draws from {len(used)} tilesets: a layer '
                                   f'draws from one (put the others\' tiles on a layer of their own)', line)
        collision = bool(_properties(layer, where, line).get('collision', False))
        tmap.layers.append(TiledLayer(layer.get('name', ''), rows, collision, used.pop() if used else 0))

    for group in root.findall('objectgroup'):
        for obj in group.findall('object'):
            cls = obj.get('class') or obj.get('type') or ''
            props = _properties(obj, where, line)
            x, y = float(obj.get('x', 0)), float(obj.get('y', 0))
            w, h = float(obj.get('width', 0)), float(obj.get('height', 0))
            name = obj.get('name', '')
            if cls == 'path':
                shape = obj.find('polyline')
                if shape is None:
                    shape = obj.find('polygon')
                if shape is None or not name:
                    raise GameCompileError(f'{where}a path in layer {group.get("name")!r} is a polyline with a '
                                           f'name', line)
                points = [[x + float(a), y + float(b)]
                          for a, b in (p.split(',') for p in shape.get('points', '').split())]
                tmap.paths.append(TiledPath(name, points))
                continue
            if cls in ('zone', 'exit'):
                if not (w and h) or not name:
                    raise GameCompileError(f'{where}a {cls} in layer {group.get("name")!r} is a rectangle with a '
                                           f'name', line)
                if cls == 'zone':
                    if not props.get('tag'):
                        raise GameCompileError(f'{where}zone {name!r} needs a tag property (what collisions see '
                                               f'it as)', line)
                    tmap.zones.append(TiledZone(name, str(props['tag']), x, y, w, h))
                else:
                    if not props.get('to') or not props.get('at'):
                        raise GameCompileError(f'{where}exit {name!r} needs to and at properties (the scene, and '
                                               f'the exit there it arrives at)', line)
                    tmap.exits.append(TiledExit(name, str(props['to']), str(props['at']), x, y, w, h))
                continue
            prefab = cls or name
            if not prefab:
                raise GameCompileError(
                    f'{where}an object in layer {group.get("name")!r} has no class (the prefab it places)', line)
            unknown = sorted(set(props) - {'state'})
            if unknown:
                raise GameCompileError(f'{where}object {name or prefab!r} has properties {", ".join(unknown)}: an '
                                       f'object placing a prefab takes state (the qg:state it starts in)', line)
            if obj.get('gid') is not None:
                x, y = x + w / 2, y - h / 2
            elif obj.find('point') is None and (w or h):
                x, y = x + w / 2, y + h / 2
            tmap.objects.append(TiledObject(prefab, x, y, name if cls else '',
                                            str(props['state']) if 'state' in props else None))
    if not tmap.layers:
        raise GameCompileError(f'{where}the map has no tile layer', line)
    return tmap
