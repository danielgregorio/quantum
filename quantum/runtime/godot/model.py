"""The game model: the .q's elements, read and checked against the schema.

`read_game(app)` takes the ApplicationNode (for its `xml_root`) and returns
a `Game`. Every `qg:` element becomes an `Element` (tag, typed attributes,
children, text, line); every `q:` statement inside a handler becomes a
`Statement`. Anything the schema does not know is a GameCompileError with
the line. Raw text where statements go (the JavaScript of the old backend)
is an error too: the language has no escape hatch.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union
from xml.etree import ElementTree as ET

from quantum.runtime.godot.errors import GameCompileError
from quantum.runtime.godot.schema import ACTIONS, STATEMENTS, TAGS, Attr

GAME_NS = '{https://quantum.lang/game}'
Q_NS = '{https://quantum.lang/ns}'

_IDENT = re.compile(r'^[A-Za-z_][A-Za-z0-9_-]*$')
_SIZE = re.compile(r'^(\d+)x(\d+)$')
_COLOR = re.compile(r'^#[0-9A-Fa-f]{6}$')


@dataclass
class Statement:
    """A q: statement: set, if, loop, function, return."""
    kind: str
    attrs: Dict[str, str]
    line: Optional[int]
    body: List['Node'] = field(default_factory=list)
    # for `if`: the elseif/else branches, in order
    branches: List['Statement'] = field(default_factory=list)


@dataclass
class Element:
    """A qg: element with its attributes converted by the schema."""
    tag: str
    attrs: Dict[str, object]
    line: Optional[int]
    children: List['Node'] = field(default_factory=list)
    text: str = ''

    def get(self, name: str, default=None):
        return self.attrs.get(name, default)

    def find_all(self, tag: str) -> List['Element']:
        return [c for c in self.children if isinstance(c, Element) and c.tag == tag]


Node = Union[Element, Statement]


@dataclass
class Game:
    id: str
    tilesets: Dict[str, Element]
    sheets: Dict[str, Element]
    prefabs: Dict[str, Element]
    scenes: List[Element]
    source_path: Optional[str]
    sounds: Dict[str, Element] = field(default_factory=dict)
    state: List[Statement] = field(default_factory=list)   # q:set at the application level


def _local(element: ET.Element) -> tuple:
    """(namespace, local name) of an element: ('game', 'scene'), ('q', 'set'), (None, 'p')."""
    tag = element.tag
    if tag.startswith(GAME_NS):
        return 'game', tag[len(GAME_NS):]
    if tag.startswith(Q_NS):
        return 'q', tag[len(Q_NS):]
    if tag.startswith('qg:'):
        return 'game', tag[3:]
    if tag.startswith('q:'):
        return 'q', tag[2:]
    return None, tag.split('}')[-1]


def _line(element: ET.Element) -> Optional[int]:
    return getattr(element, 'sourceline', None)


def _convert(name: str, attr: Attr, raw: str, line: Optional[int]) -> object:
    t = attr.type
    try:
        if t == 'str' or t == 'expr':
            return raw
        if t == 'int':
            return int(raw)
        if t == 'float':
            return float(raw)
        if t == 'bool':
            low = raw.strip().lower()
            if low in ('true', '1', 'yes'):
                return True
            if low in ('false', '0', 'no'):
                return False
            raise ValueError
        if t == 'ident':
            if not _IDENT.match(raw):
                raise ValueError
            return raw
        if t == 'size':
            m = _SIZE.match(raw.strip())
            if not m:
                raise ValueError
            return (int(m.group(1)), int(m.group(2)))
        if t == 'color':
            if not _COLOR.match(raw.strip()):
                raise ValueError
            return raw.strip().lower()
        if t.startswith('enum:'):
            options = t[5:].split('|')
            if raw not in options:
                raise GameCompileError(
                    f'{name}="{raw}": must be one of {", ".join(options)}', line)
            return raw
    except ValueError:
        raise GameCompileError(f'{name}="{raw}" is not a {t}', line)
    raise GameCompileError(f'schema bug: unknown attribute type {t}', line)


def _read_attrs(tag: str, element: ET.Element) -> Dict[str, object]:
    spec = TAGS[tag]
    line = _line(element)
    out: Dict[str, object] = {}
    for name, raw in element.attrib.items():
        if name.startswith('xmlns') or name.startswith('{'):
            continue
        if name not in spec.attrs:
            known = ', '.join(sorted(spec.attrs)) or 'none'
            raise GameCompileError(f'<qg:{tag}> has no attribute {name!r} (it has: {known})', line)
        out[name] = _convert(name, spec.attrs[name], raw, line)
    for name, attr in spec.attrs.items():
        if name not in out:
            if attr.required:
                raise GameCompileError(f'<qg:{tag}> needs {name}=', line)
            out[name] = attr.default
    return out


def _no_raw_text(element: ET.Element, what: str) -> None:
    """Text where statements go is the old backend's JavaScript: refused."""
    if element.text and element.text.strip():
        raise GameCompileError(
            f'{what} holds text ({element.text.strip().splitlines()[0][:40]!r}): '
            f'a game is written in tags, not in script', _line(element))
    for child in element:
        if child.tail and child.tail.strip():
            raise GameCompileError(
                f'{what} holds text ({child.tail.strip().splitlines()[0][:40]!r}): '
                f'a game is written in tags, not in script', _line(child))


def _read_children(element: ET.Element, parent_tag: str, where: str) -> List[Node]:
    out: List[Node] = []
    for child in element:
        ns, name = _local(child)
        if ns == 'game':
            out.append(_read_element(child, parent_tag))
        elif ns == 'q':
            out.append(_read_statement(child, parent_tag))
        elif isinstance(child.tag, str) and child.tag.startswith('<'):
            continue  # a comment
        else:
            raise GameCompileError(f'<{name}> is not a game tag; {where} holds qg: and q: tags', _line(child))
    return out


def _read_element(element: ET.Element, parent_tag: str) -> Element:
    ns, tag = _local(element)
    line = _line(element)
    if tag not in TAGS:
        raise GameCompileError(f'<qg:{tag}> is not a game tag', line)
    spec = TAGS[tag]
    allowed = spec.parents
    parent_ok = parent_tag in allowed or ('handler' in allowed and parent_tag == 'handler')
    if not parent_ok:
        raise GameCompileError(
            f'<qg:{tag}> cannot go inside <{parent_tag}>; it goes inside ' +
            ', '.join(f'<qg:{p}>' if p not in ('application', 'handler') else
                      ('<q:application>' if p == 'application' else 'a handler (qg:on-collision, q:if...)')
                      for p in allowed), line)
    node = Element(tag, _read_attrs(tag, element), line)
    if spec.text:
        node.text = (element.text or '').strip()
        if len(element):
            raise GameCompileError(f'<qg:{tag}> holds {spec.text}, not tags', line)
        return node
    _no_raw_text(element, f'<qg:{tag}>')
    child_parent = 'handler' if tag in ('on-collision', 'on-fall', 'on-input') else tag
    node.children = _read_children(element, child_parent, f'<qg:{tag}>')
    return node


def _read_statement(element: ET.Element, parent_tag: str) -> Statement:
    ns, kind = _local(element)
    line = _line(element)
    if kind not in STATEMENTS:
        raise GameCompileError(
            f'<q:{kind}> is not part of the game language (it has: ' +
            ', '.join(f'q:{s}' for s in STATEMENTS) + ')', line)
    if kind in ('else', 'elseif'):
        raise GameCompileError(f'<q:{kind}> goes inside its <q:if>', line)
    attrs = {k: v for k, v in element.attrib.items() if not k.startswith('{')}
    st = Statement(kind, attrs, line)
    if kind == 'set':
        if 'name' not in attrs:
            raise GameCompileError('<q:set> needs name=', line)
        if len(element) or (element.text and element.text.strip()):
            raise GameCompileError('<q:set> in a game takes value=, not a body', line)
        return st
    if kind == 'return':
        return st
    if kind == 'call':
        if 'function' not in attrs:
            raise GameCompileError('<q:call> needs function=', line)
        return st
    # if, loop, function: a body of statements and actions
    _no_raw_text(element, f'<q:{kind}>')
    if kind == 'if':
        if 'condition' not in attrs:
            raise GameCompileError('<q:if> needs condition=', line)
        for child in element:
            cns, cname = _local(child)
            if cns == 'q' and cname in ('else', 'elseif'):
                branch = Statement(cname, {k: v for k, v in child.attrib.items()}, _line(child))
                if cname == 'elseif' and 'condition' not in branch.attrs:
                    raise GameCompileError('<q:elseif> needs condition=', _line(child))
                _no_raw_text(child, f'<q:{cname}>')
                branch.body = _read_children(child, 'handler', f'<q:{cname}>')
                st.branches.append(branch)
            else:
                st.body.extend(_read_children_of_one(child, 'handler', '<q:if>'))
        return st
    if kind == 'loop':
        if 'items' not in attrs and 'from' not in attrs:
            raise GameCompileError('<q:loop> needs items= or from=/to=', line)
        if 'var' not in attrs:
            raise GameCompileError('<q:loop> needs var=', line)
    if kind == 'function':
        if 'name' not in attrs:
            raise GameCompileError('<q:function> needs name=', line)
        if parent_tag != 'scene':
            raise GameCompileError('<q:function> goes directly inside <qg:scene>', line)
    st.body = _read_children(element, 'handler', f'<q:{kind}>')
    return st


def _read_children_of_one(child: ET.Element, parent_tag: str, where: str) -> List[Node]:
    wrapper = ET.Element('wrapper')
    wrapper.append(child)
    return _read_children(wrapper, parent_tag, where)


def read_game(app) -> Game:
    root = getattr(app, 'xml_root', None)
    if root is None:
        raise GameCompileError('the application was not parsed from a file with its elements')
    source_path = getattr(app, 'source_path', None)
    tilesets: Dict[str, Element] = {}
    sheets: Dict[str, Element] = {}
    prefabs: Dict[str, Element] = {}
    sounds: Dict[str, Element] = {}
    scenes: List[Element] = []
    game_state: List[Statement] = []
    try:
        for child in root:
            ns, name = _local(child)
            if ns == 'game':
                el = _read_element(child, 'application')
                if el.tag == 'tileset':
                    _unique(tilesets, el, 'tileset')
                elif el.tag == 'spritesheet':
                    _unique(sheets, el, 'spritesheet')
                elif el.tag == 'prefab':
                    _unique(prefabs, el, 'prefab')
                elif el.tag == 'sound':
                    _unique(sounds, el, 'sound')
                elif el.tag == 'scene':
                    if any(s.get('name') == el.get('name') for s in scenes):
                        raise GameCompileError(f'two scenes named {el.get("name")!r}', el.line)
                    scenes.append(el)
                else:
                    raise GameCompileError(f'<qg:{el.tag}> goes inside a scene', el.line)
            elif ns == 'q':
                if name != 'set':
                    raise GameCompileError(
                        f'<q:{name}> goes inside a <qg:scene>; only q:set goes here, as game state', _line(child))
                game_state.append(_read_statement(child, 'application'))
            elif isinstance(child.tag, str):
                raise GameCompileError(f'<{name}> is not a game tag', _line(child))
    except GameCompileError as e:
        if e.file is None:
            e.file = source_path
        raise
    if not scenes:
        raise GameCompileError('a game needs at least one <qg:scene>', file=source_path)
    return Game(getattr(app, 'app_id', 'game'), tilesets, sheets, prefabs, scenes, source_path, sounds,
                game_state)


def _unique(table: Dict[str, Element], el: Element, what: str) -> None:
    name = el.get('name')
    if name in table:
        raise GameCompileError(f'two {what}s named {name!r}', el.line)
    table[name] = el


ACTION_TAGS = ACTIONS
