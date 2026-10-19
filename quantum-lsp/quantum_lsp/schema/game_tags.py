"""
The game tags (qg:), read from the game compiler's own schema.

quantum/runtime/godot/schema.py describes every qg: tag, its attributes and
where it may go; the compiler checks a game against it. Read here, completion
and hover offer what the compiler accepts, and scripts/generate-editor-schemas.py
writes the same into vscode-quantum, so neither drifts from it. Without the
framework (the server installed on its own), there are no game tags.
"""

from typing import Dict

from .types import AttributeInfo, AttributeType, TagInfo

_TYPES = {'int': AttributeType.INTEGER, 'float': AttributeType.DECIMAL, 'bool': AttributeType.BOOLEAN,
          'expr': AttributeType.EXPRESSION, 'enum': AttributeType.ENUM, 'color': AttributeType.CSS_COLOR}


def _default(value) -> str:
    if value is None:
        return None
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, float):
        return f'{value:g}'
    return str(value)


def _attribute(name: str, attr) -> AttributeInfo:
    kind, _, values = attr.type.partition(':')
    return AttributeInfo(name=name, type=_TYPES.get(kind, AttributeType.STRING), required=attr.required,
                         default=_default(attr.default), description=attr.doc,
                         enum_values=values.split('|') if kind == 'enum' else [])


def _game_tags() -> Dict[str, TagInfo]:
    try:
        from quantum.runtime.godot.schema import ACTIONS, HANDLERS, TAGS
    except Exception:
        return {}
    children: Dict[str, list] = {}
    for name, spec in TAGS.items():
        for parent in spec.parents:
            children.setdefault(parent, []).append(name)
    tags = {}
    for name, spec in TAGS.items():
        inside = children.get('handler', list(ACTIONS)) if name in HANDLERS else children.get(name, [])
        tags[f'qg:{name}'] = TagInfo(
            name=name, namespace='qg', description=spec.doc,
            attributes={n: _attribute(n, a) for n, a in spec.attrs.items()},
            children=[f'qg:{c}' for c in inside],
            parent_tags=[{'application': 'q:application', 'handler': 'handler'}.get(p, f'qg:{p}')
                         for p in spec.parents])
    return tags


GAME_TAGS: Dict[str, TagInfo] = _game_tags()
