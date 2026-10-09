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
ACTIONS = ('destroy', 'bounce', 'play', 'respawn', 'become', 'spawn', 'swap', 'checkpoint', 'goto-scene')

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
    'sound': Tag(
        'A sound the game can play (qg:play).',
        {'name': Attr('ident', required=True),
         'src': Attr('str', required=True, doc='an .ogg or .wav')},
        parents=('application',)),
    'prefab': Tag(
        'A kind of thing the scene places with qg:instance. With ai= it moves.',
        {'name': Attr('ident', required=True),
         'tag': Attr('ident', doc='what collisions see it as (`with="coin"`)'),
         'sheet': Attr('ident', required=True, doc='a qg:spritesheet or qg:tileset'),
         'frame': Attr('int', 0),
         'hitbox': Attr('size', required=True),
         'ai': Attr('enum:patrol', None, doc='patrol: walks, turns at walls (and at edges with turns-at)'),
         'speed': Attr('float', 30.0, doc='pixels per second, for ai='),
         'direction': Attr('enum:left|right', 'left', doc='where it walks first'),
         'turns-at': Attr('enum:wall|edge', 'wall', doc='edge: also turns before falling off'),
         'gravity': Attr('float', 900.0),
         'solid': Attr('bool', False, doc='characters stand on it and bump it (a block)')},
        parents=('application',)),
    'state': Tag(
        'A form of the character (small, big...): its hitbox, its frame, its animations. '
        '`me.state` reads it; qg:become changes it.',
        {'name': Attr('ident', required=True),
         'hitbox': Attr('size', required=True),
         'frame': Attr('int', 0),
         'initial': Attr('bool', False, doc='the state it starts in (else the first one)')},
        parents=('character',)),
    'animation': Tag(
        'Frames of the sheet, cycled. A character plays "idle", "walk" and "jump" by what it does; a prefab plays "walk".',
        {'name': Attr('ident', required=True),
         'frames': Attr('str', required=True, doc='comma-separated frame numbers'),
         'fps': Attr('float', 8.0)},
        parents=('character', 'prefab', 'state')),
    'scene': Tag(
        'A screen of the game. The first one is where the game starts.',
        {'name': Attr('ident', required=True),
         'width': Attr('int', 256), 'height': Attr('int', 224),
         'background': Attr('color', '#000000'),
         'seed': Attr('int', 0, doc='the random seed; the same seed gives the same game')},
        parents=('application',)),
    'tilemap': Tag(
        'The level: CSV rows of tile numbers (0 is empty, n is tile n-1 of the tileset), '
        'or a Tiled map (src=) whose tile layers draw it and whose object layers place prefabs by class.',
        {'tileset': Attr('ident', required=True),
         'collision': Attr('bool', False, doc='every tile is solid (a Tiled layer says so with a collision property)'),
         'src': Attr('str', None, doc='a .tmx, relative to the .q or a folder above it')},
        parents=('scene',), text='the CSV rows'),
    'character': Tag(
        'A body the player moves: a platformer, or a walker on a world map.',
        {'id': Attr('ident', required=True),
         'controller': Attr('enum:platformer|map', required=True),
         'at': Attr('expr', None, doc='map: the qg:map-node it starts on (a name, or an expression)'),
         'speed': Attr('float', 60.0, doc='map: pixels per second between nodes'),
         'sheet': Attr('ident', required=True), 'frame': Attr('int', 0),
         'x': Attr('float', required=True), 'y': Attr('float', required=True),
         'hitbox': Attr('size', required=True),
         'run-speed': Attr('float', 90.0, doc='pixels per second'),
         'jump-height': Attr('float', 64.0, doc='pixels, with the button held'),
         'variable-jump': Attr('bool', True, doc='releasing the button cuts the jump'),
         'coyote-frames': Attr('int', 6, doc='ticks after leaving a ledge in which a jump still works'),
         'gravity': Attr('float', 900.0, doc='pixels per second squared'),
         'max-fall': Attr('float', 300.0, doc='terminal velocity, pixels per second'),
         'jump-sound': Attr('ident', None, doc='a qg:sound, played on take-off')},
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
    'text': Tag(
        'A string from the scene state, in the HUD.',
        {'bind': Attr('ident', required=True, doc='a q:set of the scene')},
        parents=('hud',)),
    'on-collision': Tag(
        'What happens when this character touches something. Holds actions and statements; '
        '`me` is the character, `other` what it touched.',
        {'with': Attr('ident', required=True, doc='the tag of what it touches'),
         'side': Attr('enum:any|top|bottom', 'any',
                      doc='top: landing on it; bottom: hitting it from below. A side handler runs '
                          'before the "any" one, which then does not'),
         'cooldown': Attr('int', 0, doc='ticks before this handler can fire again')},
        parents=('character',)),
    'map-node': Tag(
        'A place on a world map. With scene=, pressing jump there enters that scene.',
        {'name': Attr('ident', required=True),
         'x': Attr('float', required=True), 'y': Attr('float', required=True),
         'sheet': Attr('ident', required=True), 'frame': Attr('int', 0),
         'scene': Attr('ident', None)},
        parents=('scene',)),
    'map-path': Tag(
        'A way between two map nodes, both directions.',
        {'from': Attr('ident', required=True), 'to': Attr('ident', required=True),
         'requires': Attr('ident', None, doc='a scene name that must be in the game state `cleared`')},
        parents=('scene',)),
    'on-input': Tag(
        'What happens when the player presses an action in this scene. Holds actions and statements.',
        {'action': Attr('enum:jump|left|right|up|down', required=True)},
        parents=('scene',)),
    'on-fall': Tag(
        'What happens when this character falls below the tilemap. Holds actions and statements.',
        {},
        parents=('character',)),
    # actions
    'destroy': Tag(
        'Removes a thing from the scene.',
        {'target': Attr('enum:other|me', 'other')},
        parents=('handler',)),
    'bounce': Tag(
        'Throws the character up, as after a stomp.',
        {'target': Attr('enum:me', 'me'),
         'height': Attr('float', 32.0, doc='pixels')},
        parents=('handler',)),
    'play': Tag(
        'Plays a qg:sound.',
        {'sound': Attr('ident', required=True)},
        parents=('handler',)),
    'respawn': Tag(
        'Puts the character back at its start or its last checkpoint, still.',
        {'target': Attr('enum:me', 'me')},
        parents=('handler',)),
    'become': Tag(
        'Changes the character to one of its qg:states.',
        {'target': Attr('enum:me', 'me'),
         'state': Attr('ident', required=True)},
        parents=('handler',)),
    'spawn': Tag(
        'Places a new prefab instance in the scene.',
        {'prefab': Attr('ident', required=True),
         'at': Attr('enum:other|me', 'other', doc='whose position'),
         'dx': Attr('float', 0.0), 'dy': Attr('float', 0.0, doc='offset in pixels')},
        parents=('handler',)),
    'swap': Tag(
        'Replaces a thing with an instance of another prefab, in its place.',
        {'target': Attr('enum:other', 'other'),
         'prefab': Attr('ident', required=True)},
        parents=('handler',)),
    'checkpoint': Tag(
        "Makes the other thing's position where the character respawns.",
        {'target': Attr('enum:me', 'me'),
         'at': Attr('enum:other', 'other')},
        parents=('handler',)),
    'goto-scene': Tag(
        'Leaves this scene for another, at the end of the tick. Scene state is lost; game state stays.',
        {'name': Attr('ident', required=True)},
        parents=('handler',)),
}

# q: statements the compiler reads itself (see model.py).
STATEMENTS = ('set', 'if', 'else', 'elseif', 'loop', 'function', 'return', 'call')
