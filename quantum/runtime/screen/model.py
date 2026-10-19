"""The screen model: the .q's elements, read and checked against the schema.

`read_screen(app)` takes the ApplicationNode (for its `xml_root` and
`source_path`) and returns a `Screen`: the sheets and their animations,
the particle effects, the scene's nodes and the rules (an event, its
actions). Anything the schema does not know is a ScreenCompileError with
the line, and so is a promise the file cannot keep: a sprite of a sheet
that does not exist, a frame the sheet does not have, an animation its
sheet lacks, a `{field}` the event does not have, a literal target no
sprite is named.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET

from quantum.runtime.screen import png
from quantum.runtime.screen.errors import ScreenCompileError
from quantum.runtime.screen.schema import ACTIONS, EVENTS, SCREEN_NS, TAGS, Attr

NS = '{' + SCREEN_NS + '}'
Q_NS = '{https://quantum.lang/ns}'

_PLACEHOLDER = re.compile(r'\{([^{}]*)\}')
_INT = re.compile(r'^-?\d+$')
_FLOAT = re.compile(r'^-?(\d+\.?\d*|\.\d+)$')
_IDENT = re.compile(r'^[A-Za-z0-9_][A-Za-z0-9_@.:-]*$')
_COLOR = re.compile(r'^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$')

NODE_KINDS = ('sprite', 'text', 'emitter', 'offers', 'notices')


@dataclass
class Animation:
    name: str
    frames: List[int]
    fps: float
    loop: bool
    line: Optional[int]


@dataclass
class Sheet:
    name: str
    src: str                     # as written, relative to the .q
    path: Path                   # where it is
    tile: Tuple[int, int]
    frames: int                  # how many the PNG holds
    animations: Dict[str, Animation] = field(default_factory=dict)
    line: Optional[int] = None


@dataclass
class Particles:
    name: str
    preset: str
    overrides: Dict[str, object]  # color, amount, lifetime, speed, size: only those given
    line: Optional[int]


@dataclass
class Node:
    kind: str                    # one of NODE_KINDS
    attrs: Dict[str, object]
    line: Optional[int]


@dataclass
class Action:
    kind: str                    # one of ACTIONS
    attrs: Dict[str, object]
    line: Optional[int]


@dataclass
class Rule:
    event: str
    actions: List[Action]
    line: Optional[int]


@dataclass
class Screen:
    id: str
    source_path: Optional[str]
    width: int = 320
    height: int = 180
    background: str = '#000000'
    sheets: Dict[str, Sheet] = field(default_factory=dict)
    particles: Dict[str, Particles] = field(default_factory=dict)
    nodes: List[Node] = field(default_factory=list)
    rules: List[Rule] = field(default_factory=list)

    def sprite(self, name: str) -> Optional[Node]:
        for node in self.nodes:
            if node.kind == 'sprite' and node.attrs.get('name') == name:
                return node
        return None


def _local(element: ET.Element) -> tuple:
    tag = element.tag
    if not isinstance(tag, str):
        return None, None             # a comment
    if tag.startswith(NS):
        return 'screen', tag[len(NS):]
    if tag.startswith(Q_NS):
        return 'q', tag[len(Q_NS):]
    if tag.startswith('qs:'):
        return 'screen', tag[3:]
    if tag.startswith('q:'):
        return 'q', tag[2:]
    return 'other', tag.split('}')[-1]


def _line(element: ET.Element) -> Optional[int]:
    return getattr(element, 'sourceline', None)


def _no_text(element: ET.Element, what: str) -> None:
    texts = [element.text] + [child.tail for child in element]
    for text in texts:
        if text and text.strip():
            raise ScreenCompileError(
                f'{what} holds text ({text.strip().splitlines()[0][:40]!r}): a screen file is declarations, '
                f'not script', _line(element))


def _no_children(element: ET.Element, what: str) -> None:
    for child in element:
        ns, name = _local(child)
        if ns is not None:
            raise ScreenCompileError(f'{what} holds no tags', _line(child))


def _convert(tag: str, name: str, attr: Attr, raw: str, line: Optional[int]) -> object:
    t = attr.type
    what = f'<qs:{tag}> {name}='
    if t == 'text':
        return raw
    if t == 'ident':
        if not _IDENT.match(raw):
            raise ScreenCompileError(f'{what} is a name (letters, digits, _ @ . : -), not {raw!r}', line)
        return raw
    if t == 'src':
        if not raw or raw.startswith('/') or '..' in raw.split('/') or not raw.lower().endswith('.png'):
            raise ScreenCompileError(f'{what} is a PNG next to the .q or in a folder below it, not {raw!r}', line)
        return raw
    if t == 'bool':
        low = raw.strip().lower()
        if low in ('true', '1', 'yes'):
            return True
        if low in ('false', '0', 'no'):
            return False
        raise ScreenCompileError(f'{what} is true or false, not {raw!r}', line)
    if t == 'int':
        if _INT.match(raw.strip()):
            return int(raw)
        raise ScreenCompileError(f'{what} is a whole number, not {raw!r}', line)
    if t == 'float':
        if _FLOAT.match(raw.strip()):
            return float(raw)
        raise ScreenCompileError(f'{what} is a number, not {raw!r}', line)
    if t == 'color':
        if not _COLOR.match(raw.strip()):
            raise ScreenCompileError(f'{what} is a colour, #rgb or #rrggbb, not {raw!r}', line)
        value = raw.strip().lower()
        if len(value) == 4:
            value = '#' + ''.join(c + c for c in value[1:])
        return value
    if t == 'tile':
        parts = raw.lower().split('x')
        if not all(_INT.match(p) and int(p) > 0 for p in parts) or len(parts) > 2:
            raise ScreenCompileError(f'{what} is a frame size in pixels, 24 or 16x24, not {raw!r}', line)
        return (int(parts[0]), int(parts[-1]))
    if t == 'frames':
        parts = [p.strip() for p in raw.split(',')]
        if not parts or not all(_INT.match(p) and int(p) >= 0 for p in parts):
            raise ScreenCompileError(f'{what} is frame numbers separated by commas, not {raw!r}', line)
        return [int(p) for p in parts]
    if t.startswith('enum:'):
        options = t[5:].split('|')
        if raw not in options:
            raise ScreenCompileError(f'{what}"{raw}" is not one of: {", ".join(options)}', line)
        return raw
    raise ScreenCompileError(f'{what}: unknown type {t}', line)


def _read_attrs(tag: str, element: ET.Element, what: str) -> Dict[str, object]:
    attrs = TAGS[tag].attrs
    line = _line(element)
    out: Dict[str, object] = {}
    for name, raw in element.attrib.items():
        if name.startswith('xmlns') or name.startswith('{'):
            continue
        if name not in attrs:
            raise ScreenCompileError(f'{what} has no attribute {name!r} (it has: {", ".join(attrs)})', line)
        out[name] = _convert(tag, name, attrs[name], raw, line)
    for name, attr in attrs.items():
        if name not in out:
            if attr.required:
                raise ScreenCompileError(f'{what} needs {name}=', line)
            out[name] = attr.default
    return out


def placeholders(text: str) -> List[str]:
    return _PLACEHOLDER.findall(text)


def is_literal(text: str) -> bool:
    return not placeholders(text)


def _check_placeholders(event: str, text: str, what: str, line: Optional[int]) -> None:
    fields = EVENTS[event].fields
    for name in placeholders(text):
        if name not in fields:
            raise ScreenCompileError(
                f'{what} holds {{{name}}}, which is not a field of {event} (it has: {", ".join(fields)})', line)


def _no_placeholders(text: str, what: str, line: Optional[int]) -> None:
    if placeholders(text):
        raise ScreenCompileError(
            f'{what} holds {{{placeholders(text)[0]}}}: a {{field}} is filled in from an event, so it goes in a '
            f'<qs:on>, not in the scene', line)


# ---------------------------------------------------------------- sheets, particles

def _read_sheet(element: ET.Element, source_dir: Optional[Path]) -> Sheet:
    line = _line(element)
    _no_text(element, '<qs:sheet>')
    values = _read_attrs('sheet', element, '<qs:sheet>')
    src = values['src']
    path = (source_dir or Path('.')) / src
    if not path.is_file():
        raise ScreenCompileError(f'<qs:sheet name="{values["name"]}"> src="{src}": no such file next to the .q', line)
    try:
        width, height = png.size_of(path)
    except ValueError as e:
        raise ScreenCompileError(f'<qs:sheet name="{values["name"]}"> src="{src}": {e}', line) from None
    tw, th = values['tile']
    if width % tw or height % th:
        raise ScreenCompileError(
            f'<qs:sheet name="{values["name"]}"> is {width}x{height}, not a whole number of {tw}x{th} frames', line)
    sheet = Sheet(values['name'], src, path, (tw, th), (width // tw) * (height // th), line=line)
    for child in element:
        ns, name = _local(child)
        if ns is None:
            continue
        if ns != 'screen' or name != 'animation':
            raise ScreenCompileError(f'<{"qs:" if ns == "screen" else ""}{name}> cannot go inside <qs:sheet>; '
                                     f'it holds <qs:animation>s', _line(child))
        _no_text(child, '<qs:animation>')
        _no_children(child, '<qs:animation>')
        a = _read_attrs('animation', child, '<qs:animation>')
        if a['name'] in sheet.animations:
            raise ScreenCompileError(f'two <qs:animation name="{a["name"]}"> in sheet {sheet.name}', _line(child))
        bad = [f for f in a['frames'] if f >= sheet.frames]
        if bad:
            raise ScreenCompileError(
                f'<qs:animation name="{a["name"]}"> uses frame {bad[0]}; sheet {sheet.name} has '
                f'{sheet.frames} (0 to {sheet.frames - 1})', _line(child))
        if a['fps'] <= 0:
            raise ScreenCompileError('<qs:animation> fps= is more than 0', _line(child))
        sheet.animations[a['name']] = Animation(a['name'], a['frames'], a['fps'], a['loop'], _line(child))
    return sheet


def _read_particles(element: ET.Element) -> Particles:
    line = _line(element)
    _no_text(element, '<qs:particles>')
    _no_children(element, '<qs:particles>')
    values = _read_attrs('particles', element, '<qs:particles>')
    overrides = {k: values[k] for k in ('color', 'amount', 'lifetime', 'speed', 'size') if values[k] is not None}
    for k in ('amount',):
        if k in overrides and overrides[k] < 1:
            raise ScreenCompileError('<qs:particles> amount= is at least 1', line)
    for k in ('lifetime', 'speed', 'size'):
        if k in overrides and overrides[k] <= 0:
            raise ScreenCompileError(f'<qs:particles> {k}= is more than 0', line)
    return Particles(values['name'], values['preset'], overrides, line)


# ---------------------------------------------------------------- the scene

def _read_scene(element: ET.Element, screen: Screen) -> None:
    line = _line(element)
    _no_text(element, '<qs:scene>')
    values = _read_attrs('scene', element, '<qs:scene>')
    if values['width'] < 64 or values['height'] < 64 or values['width'] > 1920 or values['height'] > 1080:
        raise ScreenCompileError('<qs:scene> is between 64x64 and 1920x1080 pixels', line)
    screen.width, screen.height, screen.background = values['width'], values['height'], values['background']
    for child in element:
        ns, name = _local(child)
        if ns is None:
            continue
        if ns != 'screen':
            raise ScreenCompileError(
                f'<{name}> is not a screen tag; <qs:scene> holds {", ".join("qs:" + k for k in NODE_KINDS)}',
                _line(child))
        if name not in NODE_KINDS:
            where = 'inside <qs:on>' if name in ACTIONS else 'at the top of the file'
            if name in TAGS:
                raise ScreenCompileError(f'<qs:{name}> goes {where}, not inside <qs:scene>', _line(child))
            raise ScreenCompileError(f'<qs:{name}> is not a screen tag (they are: {", ".join(TAGS)})', _line(child))
        what = f'<qs:{name}>'
        _no_text(child, what)
        _no_children(child, what)
        attrs = _read_attrs(name, child, what)
        _check_node(name, attrs, screen, _line(child))
        screen.nodes.append(Node(name, attrs, _line(child)))


def _check_node(kind: str, attrs: Dict[str, object], screen: Screen, line: Optional[int]) -> None:
    if kind == 'sprite':
        sheet = screen.sheets.get(attrs['sheet'])
        if sheet is None:
            raise ScreenCompileError(
                f'<qs:sprite sheet="{attrs["sheet"]}">: no <qs:sheet> of that name '
                f'(there are: {", ".join(screen.sheets) or "none"})', line)
        if attrs['frame'] >= sheet.frames:
            raise ScreenCompileError(
                f'<qs:sprite> frame="{attrs["frame"]}": sheet {sheet.name} has {sheet.frames} frames '
                f'(0 to {sheet.frames - 1})', line)
        if attrs['animation'] is not None and attrs['animation'] not in sheet.animations:
            raise ScreenCompileError(
                f'<qs:sprite animation="{attrs["animation"]}">: sheet {sheet.name} has no animation of that name '
                f'(it has: {", ".join(sheet.animations) or "none"})', line)
        if attrs['name'] is not None and screen.sprite(attrs['name']) is not None:
            raise ScreenCompileError(f'two <qs:sprite name="{attrs["name"]}">', line)
    elif kind == 'text':
        if not attrs['value'].strip():
            raise ScreenCompileError('<qs:text> needs a value', line)
        _no_placeholders(attrs['value'], '<qs:text> value=', line)
    elif kind == 'emitter':
        if attrs['particles'] not in screen.particles:
            raise ScreenCompileError(
                f'<qs:emitter particles="{attrs["particles"]}">: no <qs:particles> of that name '
                f'(there are: {", ".join(screen.particles) or "none"})', line)
        if attrs['width'] < 0:
            raise ScreenCompileError('<qs:emitter> width= is 0 or more', line)
    elif kind in ('offers', 'notices'):
        if any(n.kind == kind for n in screen.nodes):
            raise ScreenCompileError(f'one <qs:{kind}> per screen', line)
        if attrs['width'] < 60 or attrs['rows'] < 1:
            raise ScreenCompileError(f'<qs:{kind}> is at least 60 pixels wide and one row', line)


# ---------------------------------------------------------------- rules

def _read_on(element: ET.Element, screen: Screen) -> Rule:
    line = _line(element)
    values = _read_attrs('on', element, '<qs:on>')
    event = values['event']
    what_on = f'<qs:on event="{event}">'
    _no_text(element, what_on)
    actions: List[Action] = []
    for child in element:
        ns, name = _local(child)
        if ns is None:
            continue
        if ns != 'screen':
            raise ScreenCompileError(
                f'<{name}> is not a screen tag; <qs:on> holds {", ".join("qs:" + a for a in ACTIONS)}', _line(child))
        if name not in ACTIONS:
            if name in TAGS:
                raise ScreenCompileError(f'<qs:{name}> cannot go inside <qs:on>; it holds '
                                         f'{", ".join("qs:" + a for a in ACTIONS)}', _line(child))
            raise ScreenCompileError(f'<qs:{name}> is not a screen tag (they are: {", ".join(TAGS)})', _line(child))
        what = f'<qs:{name}>'
        _no_text(child, what)
        _no_children(child, what)
        attrs = _read_attrs(name, child, what)
        _check_action(name, attrs, event, screen, _line(child))
        actions.append(Action(name, attrs, _line(child)))
    if not actions:
        raise ScreenCompileError(f'{what_on} does nothing: give it an action, or leave it out', line)
    return Rule(event, actions, line)


def _target_sprite(target: str, event: str, what: str, screen: Screen, line: Optional[int]) -> Optional[Node]:
    """The sprite a literal target names (an error when none has the name); None for a placeholder."""
    _check_placeholders(event, target, what, line)
    if not is_literal(target):
        return None
    sprite = screen.sprite(target)
    if sprite is None:
        names = [n.attrs['name'] for n in screen.nodes if n.kind == 'sprite' and n.attrs['name']]
        raise ScreenCompileError(
            f'{what}"{target}": no <qs:sprite name="{target}"> in the scene '
            f'(named sprites: {", ".join(names) or "none"})', line)
    return sprite


def _check_action(kind: str, attrs: Dict[str, object], event: str, screen: Screen, line: Optional[int]) -> None:
    what = f'<qs:{kind}>'
    if kind in ('animate', 'frame', 'show', 'tween'):
        sprite = _target_sprite(attrs['target'], event, f'{what} target=', screen, line)
        sheet = screen.sheets[sprite.attrs['sheet']] if sprite is not None else None
        if kind == 'animate':
            if sheet is not None and attrs['name'] not in sheet.animations:
                raise ScreenCompileError(
                    f'{what} name="{attrs["name"]}": sheet {sheet.name} of sprite {attrs["target"]} has no '
                    f'animation of that name (it has: {", ".join(sheet.animations) or "none"})', line)
            if sheet is None and not any(attrs['name'] in s.animations for s in screen.sheets.values()):
                raise ScreenCompileError(f'{what} name="{attrs["name"]}": no sheet has an animation of that name', line)
        elif kind == 'frame':
            if sheet is not None and attrs['frame'] >= sheet.frames:
                raise ScreenCompileError(
                    f'{what} frame="{attrs["frame"]}": sheet {sheet.name} has {sheet.frames} frames '
                    f'(0 to {sheet.frames - 1})', line)
        elif kind == 'tween':
            if attrs['seconds'] <= 0:
                raise ScreenCompileError(f'{what} seconds= is more than 0', line)
            if attrs['repeat'] < -1:
                raise ScreenCompileError(f'{what} repeat= is -1 (for ever), 0 or more', line)
    elif kind == 'emit':
        if attrs['particles'] not in screen.particles:
            raise ScreenCompileError(
                f'{what} particles="{attrs["particles"]}": no <qs:particles> of that name '
                f'(there are: {", ".join(screen.particles) or "none"})', line)
        _target_sprite(attrs['at'], event, f'{what} at=', screen, line)
    elif kind == 'say':
        _check_placeholders(event, attrs['text'], f'{what} text=', line)
        if not attrs['text'].strip():
            raise ScreenCompileError(f'{what} needs a text', line)
        if attrs['seconds'] <= 0:
            raise ScreenCompileError(f'{what} seconds= is more than 0', line)


# ---------------------------------------------------------------- the file

def read_screen(app) -> Screen:
    root = getattr(app, 'xml_root', None)
    if root is None:
        raise ScreenCompileError('the application was not parsed from a file with its elements')
    source_path = getattr(app, 'source_path', None)
    screen = Screen(getattr(app, 'app_id', 'screen'), source_path)
    source_dir = Path(source_path).resolve().parent if source_path else None
    try:
        _no_text(root, '<q:application>')
        scene = None
        rules_seen: Dict[str, Optional[int]] = {}
        children = [(c, *_local(c)) for c in root]
        # sheets and particles first, whatever the order: the scene and the rules refer to them
        for child, ns, name in children:
            if ns == 'screen' and name == 'sheet':
                sheet = _read_sheet(child, source_dir)
                if sheet.name in screen.sheets:
                    raise ScreenCompileError(f'two <qs:sheet name="{sheet.name}">', sheet.line)
                screen.sheets[sheet.name] = sheet
            elif ns == 'screen' and name == 'particles':
                p = _read_particles(child)
                if p.name in screen.particles:
                    raise ScreenCompileError(f'two <qs:particles name="{p.name}">', p.line)
                screen.particles[p.name] = p
        for child, ns, name in children:
            if ns is None or (ns == 'screen' and name in ('sheet', 'particles')):
                continue
            if ns == 'screen' and name == 'scene':
                if scene is not None:
                    raise ScreenCompileError('one <qs:scene> per screen', _line(child))
                scene = child
                _read_scene(child, screen)
            elif ns == 'screen' and name == 'on':
                pass                  # after the scene: a rule's targets are its sprites
            elif ns == 'screen' and name in TAGS:
                where = {'animation': '<qs:sheet>', 'on': None}.get(name)
                if name in ACTIONS:
                    where = '<qs:on>'
                elif name in NODE_KINDS:
                    where = '<qs:scene>'
                raise ScreenCompileError(f'<qs:{name}> goes inside {where}', _line(child))
            elif ns == 'screen':
                raise ScreenCompileError(
                    f'<qs:{name}> is not a screen tag (they are: {", ".join(TAGS)})', _line(child))
            elif ns == 'q':
                raise ScreenCompileError(
                    f'<q:{name}> is not part of the screen language: a screen file is declarations '
                    f'(qs:sheet, qs:particles, qs:scene, qs:on), with nothing to compute', _line(child))
            else:
                raise ScreenCompileError(f'<{name}> is not a screen tag', _line(child))
        if scene is None:
            raise ScreenCompileError('a screen needs a <qs:scene>', _line(root))
        for child, ns, name in children:
            if ns == 'screen' and name == 'on':
                rule = _read_on(child, screen)
                if rule.event in rules_seen:
                    raise ScreenCompileError(
                        f'two <qs:on event="{rule.event}">: put everything for it in one', rule.line)
                rules_seen[rule.event] = rule.line
                screen.rules.append(rule)
    except ScreenCompileError as e:
        if e.file is None:
            e.file = source_path
        raise
    return screen
