"""A world's file, read and checked against the schema: what `quantum gameserver run` runs.

`read_world(app)` takes the ApplicationNode of a `q:application type="gameserver"` (for its `xml_root`, whose
elements know their lines) and returns a `WorldDef`. A tag or an attribute the schema does not know, a value of the
wrong kind, an expression that does not parse, a map that cannot be read: each is a GameServerError with its line.
"""

from __future__ import annotations

import ast
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from xml.etree import ElementTree as ET

from quantum.core.expressions import _normalise_js_operators
from quantum.runtime.gameserver.errors import GameServerError
from quantum.runtime.gameserver.expressions import parts_of, unbraced, validate
from quantum.runtime.gameserver.schema import HANDLERS, TAGS, Attr

Q_NS = '{https://quantum.lang/ns}'
_IDENT = re.compile(r'^[A-Za-z_][A-Za-z0-9_-]*$')
_RATE = re.compile(r'^\s*(\d+)\s*/\s*(\d*\.?\d*)\s*(ms|s|m|h)\s*$')
_DURATION = re.compile(r'^\s*(\d*\.?\d+)\s*(ms|s|m|h)\s*$')
_UNIT = {'ms': 0.001, 's': 1.0, 'm': 60.0, 'h': 3600.0}
# what a view's where= may not call: the server reads it for each player, outside the ticks the log replays
NOT_IN_A_VIEW = ('random', 'chance', 'pick', 'now')


def rate_of(raw: str) -> Tuple[int, float]:
    """'8/s' as (8, 1.0); '1/3s' as (1, 3.0); '30/m' as (30, 60.0)."""
    m = _RATE.match(raw or '')
    if not m:
        raise ValueError(raw)
    count, many, unit = int(m.group(1)), m.group(2), m.group(3)
    return count, (float(many) if many else 1.0) * _UNIT[unit]


def seconds_of(raw: str) -> float:
    m = _DURATION.match(raw or '')
    if not m:
        raise ValueError(raw)
    return float(m.group(1)) * _UNIT[m.group(2)]


@dataclass
class MapDef:
    name: str
    path: Path
    width: int
    height: int
    walls: Set[Tuple[int, int]]
    areas: Dict[str, Tuple[int, int, int, int]]          # a name: its first and last tile, x0, y0, x1, y1


@dataclass
class FieldDef:
    name: str
    value: str                                           # as written
    private: bool
    line: Optional[int]


@dataclass
class EntityDef:
    name: str
    kind: str
    per_player: bool
    persist: bool
    step_ticks: int                                      # how many ticks a step takes
    fields: List[FieldDef]
    line: Optional[int]


@dataclass
class CommandDef:
    name: str
    params: List[str]
    limit: Optional[Tuple[int, int]]                     # so many in so many ticks
    body: ET.Element
    line: Optional[int]


@dataclass
class FunctionDef:
    name: str
    params: List[str]
    body: ET.Element
    line: Optional[int]


@dataclass
class ViewDef:
    name: str
    where: Optional[str]                                 # the expression, unbraced; None: every entity
    radius: Optional[int]                                # n of a near(it, me, n) it needs: read from the index
    rest: bool                                           # more than the near(): the whole where= is read too
    line: Optional[int]


def near_of(expression: Optional[str]) -> Tuple[Optional[int], bool]:
    """A where= as (n, rest): n when it needs near(it, me, n) (alone, or with `and` more), and whether there is more
    to it than that."""
    if expression is None:
        return None, False
    tree = ast.parse(_normalise_js_operators(expression.strip()), mode='eval').body
    terms = tree.values if isinstance(tree, ast.BoolOp) and isinstance(tree.op, ast.And) else [tree]
    for term in terms:
        if (isinstance(term, ast.Call) and isinstance(term.func, ast.Name) and term.func.id == 'near'
                and not term.keywords and len(term.args) == 3
                and {a.id for a in term.args[:2] if isinstance(a, ast.Name)} == {'it', 'me'}
                and isinstance(term.args[2], ast.Constant) and type(term.args[2].value) is int
                and term.args[2].value >= 0):
            return term.args[2].value, len(terms) > 1
    return None, True


@dataclass
class WorldDef:
    name: str
    source: Optional[Path]
    client: str
    tick_rate: int
    players: int
    accounts: str
    map: Optional[MapDef]
    entities: Dict[str, EntityDef] = field(default_factory=dict)
    commands: Dict[str, CommandDef] = field(default_factory=dict)
    functions: Dict[str, FunctionDef] = field(default_factory=dict)
    every: List[Tuple[int, ET.Element]] = field(default_factory=list)   # (every so many ticks, the rule)
    on_join: List[ET.Element] = field(default_factory=list)
    on_leave: List[ET.Element] = field(default_factory=list)
    variables: List[Tuple[str, str, Optional[int]]] = field(default_factory=list)   # (name, value, line)
    views: Dict[str, ViewDef] = field(default_factory=dict)

    @property
    def reach(self) -> Optional[int]:
        """How far a player sees: the most n of the views' near(); None if a view sees the whole world."""
        if any(v.radius is None for v in self.views.values()):
            return None
        return max(v.radius for v in self.views.values())

    @property
    def hero(self) -> EntityDef:
        """The entity each player gets."""
        return next(e for e in self.entities.values() if e.per_player)


def _line(element: ET.Element) -> Optional[int]:
    return getattr(element, 'sourceline', None)


def _local(element: ET.Element) -> Tuple[str, str]:
    tag = element.tag
    if not isinstance(tag, str):
        return 'comment', ''
    if tag.startswith(Q_NS):
        return 'q', tag[len(Q_NS):]
    if tag.startswith('q:'):
        return 'q', tag[2:]
    return 'other', tag.split('}')[-1]


def _check_value(tag: str, name: str, attr: Attr, raw: str, line: Optional[int]) -> None:
    kind = attr.type
    where = f'<q:{tag}> {name}='
    try:
        if kind == 'ident':
            if not _IDENT.match(raw):
                raise ValueError
        elif kind == 'names':
            if raw.strip() and not all(_IDENT.match(n.strip()) for n in raw.split(',')):
                raise ValueError
        elif kind == 'int':
            int(raw)
        elif kind == 'bool':
            if raw not in ('true', 'false'):
                raise ValueError
        elif kind == 'rate':
            rate_of(raw)
        elif kind == 'duration':
            if seconds_of(raw) <= 0:
                raise ValueError
        elif kind.startswith('enum:'):
            if raw not in kind[5:].split('|'):
                raise GameServerError(f'{where}"{raw}" is not one of: {", ".join(kind[5:].split("|"))}', line)
    except ValueError:
        what = {'ident': 'a name', 'names': 'names separated by commas', 'int': 'a whole number',
                'bool': 'true or false', 'rate': 'so many in so long (8/s, 1/3s)',
                'duration': 'a time (500ms, 2s, 5m)'}[kind]
        raise GameServerError(f'{where} is {what}, not {raw!r}', line)
    # an expression is checked now, not at the first tick that reaches it
    try:
        if kind == 'expr':
            validate(raw)
        elif kind in ('text', 'value', 'place'):
            for literal, expression in parts_of(raw):
                if expression is not None:
                    validate(expression, braced=False)
    except GameServerError as e:
        raise GameServerError(f'{where} {e.message}', line)


def _check(element: ET.Element, parent: str) -> None:
    """The element against the schema, and all it holds."""
    space, name = _local(element)
    line = _line(element)
    if space == 'comment':
        return
    if space != 'q' or name not in TAGS:
        shown = f'q:{name}' if space == 'q' else element.tag.split('}')[-1]
        raise GameServerError(f'<{shown}> is not a tag of a world (PLAN_GAME_SERVER.md says in which phase each '
                              f'comes)', line)
    spec = TAGS[name]
    allowed = spec.parents
    if parent not in allowed and not (parent in HANDLERS and 'handler' in allowed):
        where = ', '.join(f'q:{p}' if p not in ('application', 'handler') else
                          ('a block (a command, q:every, q:on-join, a q:function...)' if p == 'handler'
                           else 'q:application') for p in allowed)
        raise GameServerError(f'<q:{name}> goes in {where}, not in <q:{parent}>', line)
    for attr in element.attrib:
        if attr not in spec.attrs:
            known = ', '.join(spec.attrs) or 'none'
            raise GameServerError(f'<q:{name}> has no attribute {attr}= (it has: {known})', line)
    for attr, a in spec.attrs.items():
        if a.required and attr not in element.attrib:
            raise GameServerError(f'<q:{name}> needs {attr}=', line)
        if attr in element.attrib:
            _check_value(name, attr, a, element.attrib[attr], line)
    if (element.text or '').strip() and spec.text is None:
        raise GameServerError(f'<q:{name}> holds text ({element.text.strip().splitlines()[0][:40]!r}): a world is '
                              f'tags, its texts in attributes', line)
    for child in element:
        if (child.tail or '').strip():
            raise GameServerError(f'text after <{_local(child)[1]}>: {child.tail.strip()[:40]!r}', _line(child))
        _check(child, name)


def _read_map(element: ET.Element, base: Path) -> MapDef:
    from quantum.runtime.godot.errors import GameCompileError
    from quantum.runtime.godot.tiled import read_tmx
    line = _line(element)
    path = (base / element.get('tiled')).resolve()
    if not path.is_file():
        raise GameServerError(f'<q:map> tiled="{element.get("tiled")}": there is no such file ({path})', line)
    try:
        tmap = read_tmx(path, line)
    except GameCompileError as e:
        raise GameServerError(f'<q:map> {e.message if hasattr(e, "message") else e}', line)
    wanted = element.get('walls', '')
    layers = [layer for layer in tmap.layers if (layer.name == wanted if wanted else layer.collision)]
    if wanted and not layers:
        raise GameServerError(f'<q:map> walls="{wanted}": the map has no tile layer of that name '
                              f'({", ".join(layer.name for layer in tmap.layers)})', line)
    walls = {(x, y) for layer in layers for y, row in enumerate(layer.rows) for x, tile in enumerate(row) if tile}
    areas = {}
    tw, th = tmap.tile_width or 1, tmap.tile_height or 1
    for zone in tmap.zones:
        x0, y0 = int(zone.x // tw), int(zone.y // th)
        x1 = max(x0, int(math.ceil((zone.x + zone.width) / tw)) - 1)
        y1 = max(y0, int(math.ceil((zone.y + zone.height) / th)) - 1)
        areas[zone.name] = (x0, y0, x1, y1)
    return MapDef(element.get('name'), path, tmap.width, tmap.height, walls, areas)


def read_world(app, source: Optional[str] = None) -> WorldDef:
    """The world of a q:application type="gameserver"."""
    root = app.xml_root
    file = source or getattr(app, 'source_path', None)
    try:
        return _read(root, Path(file) if file else None)
    except GameServerError as e:
        if file and not e.file:
            e.file = str(file)
            e.args = (str(e),)
        raise


def _read(root: ET.Element, file: Optional[Path]) -> WorldDef:
    servers = [c for c in root if _local(c) == ('q', 'gameserver')]
    others = [c for c in root if _local(c)[0] != 'comment' and _local(c) != ('q', 'gameserver')]
    if others:
        space, name = _local(others[0])
        raise GameServerError(f'<{"q:" if space == "q" else ""}{name}> in a gameserver application: what a world '
                              f'holds goes in its q:gameserver', _line(others[0]))
    if len(servers) != 1:
        raise GameServerError('a q:application type="gameserver" holds one q:gameserver' +
                              (f', not {len(servers)}' if servers else ''), _line(root))
    server = servers[0]
    _check(server, 'application')
    base = file.parent if file else Path.cwd()
    tick = int(server.get('tick', TAGS['gameserver'].attrs['tick'].default))
    if not 1 <= tick <= 60:
        raise GameServerError(f'<q:gameserver> tick="{tick}": from 1 to 60 ticks a second', _line(server))
    world = WorldDef(server.get('name'), file, server.get('client', ''), tick,
                     int(server.get('players', TAGS['gameserver'].attrs['players'].default)),
                     server.get('accounts', 'guest'), None)
    for child in server:
        space, name = _local(child)
        line = _line(child)
        if name == 'map':
            if world.map is not None:
                raise GameServerError('a world has one q:map (the regions of PLAN_GAME_SERVER.md come later)', line)
            world.map = _read_map(child, base)
        elif name == 'entity':
            if child.get('name') in world.entities:
                raise GameServerError(f'two entities named {child.get("name")!r}', line)
            count, seconds = rate_of(child.get('speed', TAGS['entity'].attrs['speed'].default))
            fields = [FieldDef(f.get('name'), f.get('value', ''), f.get('private') == 'true', _line(f))
                      for f in child]
            reserved = {'id', 'kind', 'at', 'facing'} & {f.name for f in fields}
            if reserved:
                raise GameServerError(f'<q:entity name="{child.get("name")}"> declares {", ".join(sorted(reserved))}: '
                                      f'every entity has id, kind, at and facing already', line)
            world.entities[child.get('name')] = EntityDef(
                child.get('name'), child.get('kind'), child.get('per-player') == 'true',
                child.get('persist') == 'true', max(1, math.ceil(world.tick_rate * seconds / count)), fields, line)
        elif name == 'command':
            if child.get('name') in world.commands:
                raise GameServerError(f'two commands named {child.get("name")!r}', line)
            limit = None
            if child.get('limit'):
                count, seconds = rate_of(child.get('limit'))
                limit = (count, max(1, round(seconds * world.tick_rate)))
            params = [p.strip() for p in child.get('params', '').split(',') if p.strip()]
            world.commands[child.get('name')] = CommandDef(child.get('name'), params, limit, child, line)
        elif name == 'function':
            if child.get('name') in world.functions:
                raise GameServerError(f'two functions named {child.get("name")!r}', line)
            params = [p.strip() for p in child.get('params', '').split(',') if p.strip()]
            world.functions[child.get('name')] = FunctionDef(child.get('name'), params, child, line)
        elif name == 'every':
            ticks = round(seconds_of(child.get('interval')) * world.tick_rate)
            if ticks < 1:
                raise GameServerError(f'<q:every interval="{child.get("interval")}">: shorter than a tick '
                                      f'({1000 // world.tick_rate}ms at tick="{world.tick_rate}")', line)
            world.every.append((ticks, child))
        elif name == 'on-join':
            world.on_join.append(child)
        elif name == 'on-leave':
            world.on_leave.append(child)
        elif name == 'set':
            world.variables.append((child.get('name'), child.get('value', ''), line))
        elif name == 'view':
            if child.get('name') in world.views:
                raise GameServerError(f'two views named {child.get("name")!r}', line)
            where = unbraced(child.get('where')) if child.get('where') is not None else None
            radius, rest = near_of(where)
            world.views[child.get('name')] = ViewDef(child.get('name'), where, radius, rest, line)
    if not world.views:
        world.views['world'] = ViewDef('world', None, None, False, _line(server))
    for view in world.views.values():
        if view.where is None:
            continue
        for node in ast.walk(ast.parse(_normalise_js_operators(view.where.strip()), mode='eval')):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                called = node.func.id
                if called in NOT_IN_A_VIEW or called in world.functions:
                    raise GameServerError(f'<q:view name="{view.name}"> where= calls {called}(): a view reads the '
                                          f'world and changes nothing, so not the world\'s random nor a '
                                          f'q:function', view.line)
    if world.map is None:
        raise GameServerError('a world needs its q:map', _line(server))
    players = [e for e in world.entities.values() if e.per_player]
    if len(players) != 1:
        raise GameServerError('a world has one entity with per-player="true": the one each player gets' +
                              (f' (it has {len(players)})' if players else ''), _line(server))
    for e in world.entities.values():
        if e.persist and not e.per_player:
            raise GameServerError(f'<q:entity name="{e.name}"> persist="true" is for a player\'s entity '
                                  f'(the world keeps all the others with it)', e.line)
    return world
