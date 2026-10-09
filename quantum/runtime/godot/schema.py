"""What the game language is: every `qg:` tag, its attributes, where it goes.

This table is the single source: the model validates against it, the
reference page is generated from it, and a tag with no entry does not
exist. Attribute types:

- `str`, `int`, `float`, `bool`
- `ident`: a name (`[A-Za-z_][A-Za-z0-9_-]*`)
- `size`: `WxH` in pixels, e.g. `18x22`
- `color`: `#rrggbb`
- `expr`: a Quantum expression, with or without braces
- `enum:a|b|c`
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


@dataclass(frozen=True)
class Attr:
    type: str
    default: object = None
    required: bool = False
    doc: str = ''


@dataclass(frozen=True)
class Tag:
    doc: str
    attrs: Dict[str, Attr] = field(default_factory=dict)
    # Which tags may contain it. 'application' is the q:application root;
    # 'handler' is any block that holds statements (on-collision, q:if...).
    parents: Tuple[str, ...] = ()
    text: Optional[str] = None   # what the element's text is, if it may have any


# The actions a handler can hold, besides q: statements.
ACTIONS = ('destroy',)

TAGS: Dict[str, Tag] = {
    'tileset': Tag(
        'A sheet of equal tiles; tilemaps and sprites name it.',
        {'name': Attr('ident', required=True),
         'src': Attr('str', required=True, doc='the image, relative to the .q or a folder above it'),
         'tile': Attr('int', required=True, doc='tile size in pixels (square)')},
        parents=('application',)),
    'spritesheet': Tag(
        'A sheet of equal frames for characters and items.',
        {'name': Attr('ident', required=True),
         'src': Attr('str', required=True),
         'tile': Attr('int', required=True, doc='frame size in pixels (square)')},
        parents=('application',)),
    'prefab': Tag(
        'A kind of thing the scene places with qg:instance.',
        {'name': Attr('ident', required=True),
         'tag': Attr('ident', doc='what collisions see it as (`with="coin"`)'),
         'sheet': Attr('ident', required=True, doc='a qg:spritesheet or qg:tileset'),
         'frame': Attr('int', 0),
         'hitbox': Attr('size', required=True)},
        parents=('application',)),
    'scene': Tag(
        'A screen of the game. The first one is where the game starts.',
        {'name': Attr('ident', required=True),
         'width': Attr('int', 256), 'height': Attr('int', 224),
         'background': Attr('color', '#000000'),
         'seed': Attr('int', 0, doc='the random seed; the same seed gives the same game')},
        parents=('application',)),
    'tilemap': Tag(
        'The level, as CSV rows of tile numbers: 0 is empty, n is tile n-1 of the tileset.',
        {'tileset': Attr('ident', required=True),
         'collision': Attr('bool', False, doc='every tile is solid')},
        parents=('scene',), text='the CSV rows'),
    'character': Tag(
        'A body the player or the game moves.',
        {'id': Attr('ident', required=True),
         'controller': Attr('enum:platformer', required=True),
         'sheet': Attr('ident', required=True), 'frame': Attr('int', 0),
         'x': Attr('float', required=True), 'y': Attr('float', required=True),
         'hitbox': Attr('size', required=True),
         'run-speed': Attr('float', 90.0, doc='pixels per second'),
         'jump-height': Attr('float', 64.0, doc='pixels, with the button held'),
         'variable-jump': Attr('bool', True, doc='releasing the button cuts the jump'),
         'coyote-frames': Attr('int', 6, doc='ticks after leaving a ledge in which a jump still works'),
         'gravity': Attr('float', 900.0, doc='pixels per second squared'),
         'max-fall': Attr('float', 300.0, doc='terminal velocity, pixels per second')},
        parents=('scene',)),
    'instance': Tag(
        'A prefab placed in the scene.',
        {'prefab': Attr('ident', required=True),
         'x': Attr('float', required=True), 'y': Attr('float', required=True)},
        parents=('scene',)),
    'camera': Tag(
        'What the screen shows.',
        {'follow': Attr('ident', required=True, doc='a character id'),
         'bounds': Attr('enum:tilemap|none', 'tilemap')},
        parents=('scene',)),
    'hud': Tag(
        'Text over the game.',
        {'position': Attr('enum:top-left|top-center|top-right', 'top-left')},
        parents=('scene',)),
    'counter': Tag(
        'A number from the scene state, in the HUD.',
        {'bind': Attr('ident', required=True, doc='a q:set of the scene'),
         'label': Attr('str', '', doc='text before the number')},
        parents=('hud',)),
    'on-collision': Tag(
        'What happens when this character touches something. Holds actions and statements.',
        {'with': Attr('ident', required=True, doc='the tag of what it touches')},
        parents=('character',)),
    # actions
    'destroy': Tag(
        'Removes a thing from the scene.',
        {'target': Attr('enum:other|self', 'other')},
        parents=('handler',)),
}

# q: statements the compiler reads itself (see model.py).
STATEMENTS = ('set', 'if', 'else', 'elseif', 'loop', 'function', 'return')
