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
from quantum.runtime.godot.schema import ACTIONS, HANDLERS, STATEMENTS, TAGS, Attr

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
    gd: Dict[str, str] = field(default_factory=dict)   # gd:name="raw": Godot node properties

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
    inputs: List[Element] = field(default_factory=list)
    multiplayer: Optional[Element] = None
    languages: List[Element] = field(default_factory=list)
    particles: Dict[str, Element] = field(default_factory=dict)
    items: Dict[str, Element] = field(default_factory=dict)
    functions: List[Statement] = field(default_factory=list)   # q:function at the application level: every scene's
    touch: List[Element] = field(default_factory=list)   # qg:touch-button and qg:touch-stick: every scene's
    overlays: Dict[str, Element] = field(default_factory=dict)   # qg:overlay: a panel over any scene
    connect: Optional[Element] = None   # qg:connect: the game is a world's client


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
        if t == 'tile':
            m = _SIZE.match(raw.strip())
            if m:
                return (int(m.group(1)), int(m.group(2)))
            return (int(raw), int(raw))
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


GD_NS = '{https://quantum.lang/godot}'


def _read_gd(element: ET.Element) -> Dict[str, str]:
    return {name[len(GD_NS):]: raw for name, raw in element.attrib.items() if name.startswith(GD_NS)}


def _read_attrs(tag: str, element: ET.Element) -> Dict[str, object]:
    spec = TAGS[tag]
    line = _line(element)
    out: Dict[str, object] = {}
    for name, raw in element.attrib.items():
        if name.startswith('xmlns') or name.startswith('{'):
            continue
        if name not in spec.attrs:
            if spec.extra:
                out.setdefault('_extra', {})[name] = raw    # qg:send: the command's arguments, as written
                continue
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
    node = Element(tag, _read_attrs(tag, element), line, gd=_read_gd(element))
    if spec.text:
        node.text = (element.text or '').strip()
        if len(element):
            raise GameCompileError(f'<qg:{tag}> holds {spec.text}, not tags', line)
        if node.text and node.attrs.get('src'):
            raise GameCompileError(f'<qg:{tag}> has src= or {spec.text}, not both', line)
        return node
    _no_raw_text(element, f'<qg:{tag}>')
    child_parent = 'handler' if tag in HANDLERS else tag
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
        if parent_tag not in ('scene', 'overlay', 'application'):
            raise GameCompileError('<q:function> goes directly inside <qg:scene> (or <qg:overlay>), or '
                                   '<q:application> for every scene', line)
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
    inputs: List[Element] = []
    multiplayer: Optional[Element] = None
    languages: List[Element] = []
    particles: Dict[str, Element] = {}
    items: Dict[str, Element] = {}
    functions: List[Statement] = []
    touch: List[Element] = []
    overlays: Dict[str, Element] = {}
    connect: Optional[Element] = None
    try:
        made = _extended_prefabs(root)
        for child in root:
            child = made.get(id(child), child)
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
                elif el.tag == 'particles':
                    _unique(particles, el, 'particles')
                elif el.tag == 'item':
                    _unique(items, el, 'item')
                elif el.tag == 'input':
                    inputs.append(el)
                elif el.tag == 'language':
                    if any(lang.get('lang') == el.get('lang') for lang in languages):
                        raise GameCompileError(f'two <qg:language lang="{el.get("lang")}">', el.line)
                    languages.append(el)
                elif el.tag in ('touch-button', 'touch-stick'):
                    touch.append(el)
                elif el.tag == 'multiplayer':
                    if multiplayer is not None:
                        raise GameCompileError('one <qg:multiplayer> per game', el.line)
                    multiplayer = el
                elif el.tag == 'connect':
                    if connect is not None:
                        raise GameCompileError('one <qg:connect> per game: a game is the client of one world', el.line)
                    connect = el
                elif el.tag == 'scene':
                    if any(s.get('name') == el.get('name') for s in scenes):
                        raise GameCompileError(f'two scenes named {el.get("name")!r}', el.line)
                    scenes.append(el)
                elif el.tag == 'overlay':
                    _unique(overlays, el, 'overlay')
                else:
                    raise GameCompileError(f'<qg:{el.tag}> goes inside a scene', el.line)
            elif ns == 'q':
                if name not in ('set', 'function'):
                    raise GameCompileError(
                        f'<q:{name}> goes inside a <qg:scene>; only q:set (game state) and q:function (one every '
                        f'scene has) go here', _line(child))
                st = _read_statement(child, 'application')
                if name == 'function':
                    if any(f.attrs['name'] == st.attrs['name'] for f in functions):
                        raise GameCompileError(f'two q:functions named {st.attrs["name"]!r} in the game', st.line)
                    functions.append(st)
                else:
                    game_state.append(st)
            elif isinstance(child.tag, str):
                raise GameCompileError(f'<{name}> is not a game tag', _line(child))
    except GameCompileError as e:
        if e.file is None:
            e.file = source_path
        raise
    if not scenes:
        raise GameCompileError('a game needs at least one <qg:scene>', file=source_path)
    for name, el in overlays.items():
        if any(s.get('name') == name for s in scenes):
            raise GameCompileError(f'<qg:overlay name="{name}">: a scene has that name; an overlay needs another',
                                   el.line, file=source_path)
    return Game(getattr(app, 'app_id', 'game'), tilesets, sheets, prefabs, scenes, source_path, sounds,
                game_state, inputs, multiplayer, languages, particles, items, functions, touch, overlays, connect)


def _child_key(child: ET.Element) -> tuple:
    """What a child of a prefab replaces in the one it extends: the same animation or state (by name), the
    same touch (with= and side=), or the one of its kind (qg:behavior, qg:on-death...)."""
    _, tag = _local(child)
    if child.get('name') is not None:
        return tag, child.get('name')
    if child.get('with') is not None:
        return tag, child.get('with'), child.get('side', 'any')
    return (tag,)


def _keep_line(out: ET.Element, el: ET.Element) -> None:
    try:
        out.sourceline = _line(el)
    except AttributeError:
        pass


def _extended_prefabs(root: ET.Element) -> Dict[int, ET.Element]:
    """The qg:prefabs with extends=, each made into one whole element: the attributes and children of the
    prefab it extends (itself perhaps extending another), with its own over them. Keyed by the element's id."""
    raw = {}
    for child in root:
        ns, name = _local(child)
        if ns == 'game' and name == 'prefab' and child.get('name'):
            raw[child.get('name')] = child
    made: Dict[str, ET.Element] = {}

    def make(name: str, seen: tuple) -> ET.Element:
        if name in made:
            return made[name]
        el = raw[name]
        base_name = el.get('extends')
        if base_name is None:
            return el
        if base_name not in raw:
            raise GameCompileError(f'<qg:prefab name="{name}" extends="{base_name}">: no qg:prefab of that name '
                                   f'(declared: {", ".join(sorted(raw))})', _line(el))
        if base_name in seen:
            raise GameCompileError(f'<qg:prefab name="{name}" extends="{base_name}">: the prefabs extend each other '
                                   f'in a circle ({" > ".join(seen + (base_name,))})', _line(el))
        base = make(base_name, seen + (base_name,))
        out = el.makeelement(el.tag, {k: v for k, v in base.attrib.items() if k != 'extends'})
        out.attrib.update({k: v for k, v in el.attrib.items() if k != 'extends'})
        out.text = el.text
        mine = {_child_key(c) for c in el if isinstance(c.tag, str) and not c.tag.startswith('<')}
        for c in list(base) + list(el):
            if c in list(base) and isinstance(c.tag, str) and _child_key(c) in mine:
                continue
            out.append(c)
        _keep_line(out, el)   # errors name the derived prefab's line
        made[name] = out
        return out

    return {id(raw[name]): make(name, (name,)) for name in raw if raw[name].get('extends') is not None}


def _unique(table: Dict[str, Element], el: Element, what: str) -> None:
    name = el.get('name')
    if name in table:
        raise GameCompileError(f'two {what}s named {name!r}', el.line)
    table[name] = el


ACTION_TAGS = ACTIONS
