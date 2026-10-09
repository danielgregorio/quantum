"""`gd:` attributes: a property of the Godot node a tag becomes, checked against Godot's own reference.

`<qg:camera follow="player" gd:zoom="2,2" />` sets `Camera2D.zoom`. The
property must exist on the node's class (or one it inherits from), with
one of the types the compiler can write: float, int, bool, String,
Vector2, Vector2i, Color. The table, `godot_properties.json`, is generated
from Godot's class reference by scripts/generate-godot-properties.py.

Properties only: never a method, a signal, or anything that reads the
world — those stay the language's (`qg:` actions and handlers, and the
expressions). A `gd:` attribute is a declaration like any other: wrong
name or value is a compile error with the line.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

from quantum.runtime.godot.errors import GameCompileError

GD_NS = '{https://quantum.lang/godot}'
TABLE = Path(__file__).with_name('godot_properties.json')

# The Godot class each tag's node is (instances: by the prefab's kind).
NODE_CLASS: Dict[str, str] = {
    'scene': 'Node2D', 'character': 'CharacterBody2D', 'camera': 'Camera2D', 'tilemap': 'TileMapLayer',
    'hud': 'CanvasLayer', 'counter': 'Label', 'text': 'Label', 'map-node': 'Sprite2D', 'exit': 'Area2D',
    'sound': 'AudioStreamPlayer', 'timer': 'Node', 'spawner': 'Node', 'zone': 'Area2D', 'sprite': 'Sprite2D',
    'cursor': 'Node2D', 'path': 'Node2D',
}
# Where a gd: attribute on a prefab (or an instance of it) lands, by what the prefab is.
PREFAB_CLASS = {'item': 'Area2D', 'thing': 'CharacterBody2D', 'block': 'StaticBody2D', 'shuttle': 'AnimatableBody2D'}

_COLOR = re.compile(r'^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$')


@lru_cache(maxsize=1)
def table() -> dict:
    return json.loads(TABLE.read_text(encoding='utf-8'))


def properties_of(cls: str) -> Dict[str, str]:
    """Every settable property of the class, inherited ones included."""
    classes = table()['classes']
    out: Dict[str, str] = {}
    while cls and cls in classes:
        for name, typ in classes[cls]['properties'].items():
            out.setdefault(name, typ)
        cls = classes[cls]['inherits']
    return out


def members_of(cls: str) -> frozenset:
    """Every property, method and signal name of the class, inherited ones included."""
    classes = table()['classes']
    out = set()
    while cls and cls in classes:
        out.update(classes[cls].get('members', ()))
        cls = classes[cls]['inherits']
    return frozenset(out)


def prefab_kind(prefab: dict) -> str:
    if prefab.get('ai') == 'shuttle':
        return 'shuttle'
    if prefab.get('ai'):
        return 'thing'
    if prefab.get('solid'):
        return 'block'
    return 'item'


def convert(name: str, typ: str, raw: str, line: Optional[int]) -> dict:
    """{'type': ..., 'value': ...} as game.json carries it for the runtime."""
    raw = raw.strip()
    try:
        if typ == 'float':
            return {'type': typ, 'value': float(raw)}
        if typ == 'int':
            return {'type': typ, 'value': int(raw)}
        if typ == 'bool':
            low = raw.lower()
            if low not in ('true', 'false', '1', '0', 'yes', 'no'):
                raise ValueError
            return {'type': typ, 'value': low in ('true', '1', 'yes')}
        if typ in ('String', 'StringName'):
            return {'type': 'String', 'value': raw}
        if typ in ('Vector2', 'Vector2i'):
            parts = [p.strip() for p in raw.split(',')]
            if len(parts) != 2:
                raise ValueError
            cast = int if typ == 'Vector2i' else float
            return {'type': typ, 'value': [cast(parts[0]), cast(parts[1])]}
        if typ == 'Color':
            if not _COLOR.match(raw):
                raise ValueError
            return {'type': typ, 'value': raw.lower()}
    except ValueError:
        example = {'float': '1.5', 'int': '2', 'bool': 'true', 'Vector2': '2,2', 'Vector2i': '2,2',
                   'Color': '#rrggbb', 'String': 'text', 'StringName': 'text'}[typ]
        raise GameCompileError(f'gd:{name}="{raw}": a {typ} (e.g. {example})', line)
    raise GameCompileError(f'gd:{name}: {typ} is not a type the compiler writes', line)


def resolve(cls: str, raw_attrs: Dict[str, str], where: str, line: Optional[int]) -> Dict[str, dict]:
    """The gd: attributes of an element, checked against the class and converted."""
    if not raw_attrs:
        return {}
    props = properties_of(cls)
    out: Dict[str, dict] = {}
    for name, raw in raw_attrs.items():
        if name not in props:
            known = ', '.join(sorted(props))
            raise GameCompileError(
                f'{where}: gd:{name} is not a property of {cls} (it has: {known})', line)
        out[name] = convert(name, props[name], raw, line)
    return out


def attach(spec: dict, cls: str, raw_attrs: Dict[str, str], where: str, line: Optional[int]) -> None:
    """Puts the resolved gd: attributes on a game.json entry — only when there are any,
    so a game without them is written exactly as before."""
    if raw_attrs:
        spec['gd'] = resolve(cls, raw_attrs, where, line)
