"""What the game language is: every `qg:` tag, its attributes, where it goes.

This table is the single source: the model validates against it, the
reference page is generated from it, and a tag with no entry does not
exist. Attribute types:

- `str`, `int`, `float`, `bool`
- `ident`: a name (`[A-Za-z_][A-Za-z0-9_-]*`)
- `size`: `WxH` in pixels, e.g. `18x22`
- `tile`: a square tile size (`18`) or `WxH` frames (`8x32`)
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
ACTIONS = ('destroy', 'bounce', 'play', 'respawn', 'become', 'spawn', 'swap', 'checkpoint', 'goto-scene',
           'damage', 'burst', 'shake', 'deflect', 'stop', 'put')

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
         'tile': Attr('tile', required=True, doc='frame size in pixels: 24, or 8x32 for frames that are not square')},
        parents=('application',)),
    'input': Tag(
        'The keys of an action, instead of the defaults (arrows/WASD to move, space/Z/X to jump). '
        'A second player has no defaults: every action it uses is declared with player="2".',
        {'action': Attr('ident', required=True, doc='left, right, up, down, jump, select, cancel — or a name of '
                                                     'the game\'s own (buy, pause): qg:on-input reads it'),
         'keys': Attr('str', required=True,
                      doc='comma-separated: Godot key names (Space, Left, A, Enter...) and joypad names — '
                          'JoyA JoyB JoyX JoyY JoyL JoyR JoyL2 JoyR2 JoyStart JoySelect, JoyUp JoyDown JoyLeft '
                          'JoyRight (the pad), JoyLeftStickUp/Down/Left/Right, JoyRightStickUp/Down/Left/Right; '
                          'MouseLeft, MouseRight, MouseMiddle. Player n reads joypad n-1'),
         'player': Attr('int', 1, doc='whose keys: the character with the same player=')},
        parents=('application',)),
    'multiplayer': Tag(
        'The game is played by several people, each on their own machine, in lockstep: every peer runs '
        'the whole game and a tick runs when every player\'s input for it has arrived. One hosts '
        '(`--q-host=PORT`, player 1), the others join (`--q-join=HOST:PORT`, players 2.. in order). '
        'The players\' characters are told apart by player=; nobody declares keys for players 2..',
        {'players': Attr('int', required=True, doc='how many, 2 or more'),
         'delay': Attr('int', 3, doc='ticks between a press and its effect, everywhere: hides the round trip'),
         'check-every': Attr('int', 60, doc='ticks between comparisons of the whole state across peers; '
                                           'a difference is a desync, reported and fatal (0: never)')},
        parents=('application',)),
    'sound': Tag(
        'A sound the game can play (qg:play).',
        {'name': Attr('ident', required=True),
         'src': Attr('str', required=True, doc='an .ogg or .wav'),
         'loop': Attr('bool', False, doc='plays until qg:stop (music)')},
        parents=('application',)),
    'prefab': Tag(
        'A kind of thing the scene places with qg:instance. With ai= it moves.',
        {'name': Attr('ident', required=True),
         'tag': Attr('ident', doc='what collisions see it as (`with="coin"`)'),
         'sheet': Attr('ident', required=True, doc='a qg:spritesheet or qg:tileset'),
         'frame': Attr('int', 0),
         'hitbox': Attr('size', required=True),
         'ai': Attr('enum:patrol|wander|chase|fly|sway|shuttle|path|turret', None,
                    doc='patrol: walks under gravity, turns at walls (and at edges with turns-at); '
                        'wander: top-down, changes direction now and then (from the scene seed); '
                        'chase: top-down, goes for the character within sight=; '
                        'fly: straight along heading=; sway: side to side across the scene; '
                        'shuttle: a solid that goes dx=,dy= and back every period= ticks, carrying what stands on it; '
                        'path: follows the qg:path it was spawned on (qg:spawn at="path"), then stands at its end; '
                        'turret: stands, and fires fire-prefab at the nearest targets= within range= every fire-every'),
         'range': Attr('float', 100.0, doc='turret: pixels'),
         'targets': Attr('ident', None, doc='turret: the tag it shoots at'),
         'attack': Attr('enum:shoot|area', 'shoot', doc='turret: shoot spawns fire-prefab headed at the target; '
                                                        'area damages every target in range by damage='),
         'damage': Attr('int', 1, doc='turret attack="area": the damage'),
         'dx': Attr('float', 0.0, doc='shuttle: how far it goes, pixels'),
         'dy': Attr('float', 0.0, doc='shuttle: how far it goes, pixels'),
         'period': Attr('int', 240, doc='shuttle: ticks for there and back'),
         'one-way': Attr('bool', False, doc='solid: can be jumped through from below and stood on'),
         'sight': Attr('float', 80.0, doc='chase: pixels'),
         'heading': Attr('str', 'down', doc='fly: up, down, left, right, or a direction as x,y (-1,0.5)'),
         'accel': Attr('float', 0.0, doc='fly: pixels per second added to its speed every second'),
         'lifetime': Attr('int', 0, doc='fly: gone after this many ticks (0: never); any fly is gone off-screen'),
         'health': Attr('int', 1, doc='hits it takes (qg:damage); at 0 its qg:on-death runs and it is gone'),
         'fire-prefab': Attr('ident', None, doc='what it shoots, placed below it (or above, when heading is up)'),
         'fire-every': Attr('int', 0, doc='ticks between shots (0: never)'),
         'fire-sound': Attr('ident', None),
         'speed': Attr('str', '30', doc='pixels per second, for ai=; or a range, 150..250, drawn from the '
                                        'scene seed as each instance is placed'),
         'rotate': Attr('bool', False, doc='fly: the sprite turns to face the heading'),
         'direction': Attr('enum:left|right', 'left', doc='where it walks first'),
         'turns-at': Attr('enum:wall|edge', 'wall', doc='edge: also turns before falling off'),
         'gravity': Attr('float', 900.0),
         'solid': Attr('bool', False, doc='characters stand on it and bump it (a block)')},
        parents=('application',)),
    'state': Tag(
        'A form of a character or a prefab (small, big; calm, angry): hitbox, frame, animations, '
        'and for a prefab its speed and fire-every. `me.state` reads it; qg:become changes it.',
        {'name': Attr('ident', required=True),
         'hitbox': Attr('size', None, doc='a character needs one; a prefab keeps its own'),
         'frame': Attr('int', 0),
         'speed': Attr('float', None, doc='prefab: overrides its speed'),
         'fire-every': Attr('int', None, doc='prefab: overrides its fire-every'),
         'fire-prefab': Attr('ident', None, doc='prefab: overrides its fire-prefab'),
         'range': Attr('float', None, doc='turret: overrides its range'),
         'initial': Attr('bool', False, doc='the state it starts in (else the first one)')},
        parents=('character', 'prefab')),
    'animation': Tag(
        'Frames of the sheet, cycled. A character plays "idle", "walk" and "jump" by what it does (a topdown one '
        '"walk-up" and "walk-down" when it has them, "walk-up" upside down for down); a prefab plays "walk".',
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
         'controller': Attr('enum:platformer|map|topdown|ship|fighter', required=True),
         'player': Attr('int', 1, doc='whose keys move it (qg:input player=); 1 has the defaults'),
         'health': Attr('int', 100, doc='fighter: hits it takes; at 0 it is KO and qg:on-ko runs'),
         'facing': Attr('enum:left|right', 'right', doc='fighter: where it looks at first'),
         'bounds': Attr('enum:scene|none', None, doc='kept inside the scene: a ship unless none, a topdown '
                                                    'character when scene'),
         'axis': Attr('enum:both|vertical|horizontal', 'both', doc='ship: which way it can move'),
         'fire-action': Attr('enum:jump', None, doc='ship: the action that shoots'),
         'fire-prefab': Attr('ident', None, doc='ship: what it shoots, placed above it'),
         'fire-every': Attr('int', 10, doc='ship: ticks between shots while the action is held'),
         'fire-sound': Attr('ident', None),
         'at': Attr('expr', None, doc='map: the qg:map-node it starts on (a name, or an expression)'),
         'speed': Attr('float', 60.0, doc='map, topdown: pixels per second'),
         'attack-action': Attr('enum:jump', None, doc='topdown: the action that swings in front'),
         'attack-reach': Attr('float', 16.0, doc='topdown: how far the swing reaches, pixels'),
         'attack-frames': Attr('int', 12, doc='topdown: how many ticks the swing lasts'),
         'attack-sound': Attr('ident', None, doc='a qg:sound, played on the swing'),
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
         'x': Attr('float', required=True), 'y': Attr('float', required=True),
         'name': Attr('ident', None, doc='the node name (`other.name` in a handler); the prefab name otherwise'),
         'if': Attr('expr', None, doc='placed only when this is true as the scene is built')},
        parents=('scene',)),
    'cursor': Tag(
        'A player\'s pointer in the scene: the mouse, moved also by that player\'s left/right/up/down by step= '
        'pixels. `cursor.x`, `cursor.y` (and, with grid=, `cursor.col`, `cursor.row`, snapped) in qg:on-select; '
        'with sheet= it is drawn. Under qg:multiplayer every player\'s cursor travels with their input.',
        {'player': Attr('int', 1),
         'step': Attr('float', 16.0, doc='pixels per tick while a direction is held'),
         'grid': Attr('int', None, doc='cell size: the cursor snaps to cell centres'),
         'sheet': Attr('ident', None), 'frame': Attr('int', 0)},
        parents=('scene',)),
    'path': Tag(
        'A route through the scene, straight from point to point, that ai="path" prefabs follow '
        '(qg:spawn at="path" path=).',
        {'name': Attr('ident', required=True),
         'points': Attr('str', required=True, doc='x,y pairs separated by semicolons: 0,100; 200,100; 200,300')},
        parents=('scene',)),
    'on-select': Tag(
        'What happens when a player presses select with their qg:cursor somewhere. Holds actions and statements; '
        '`cursor` is where (x, y, col, row, player), `other` the thing under it, or null.',
        {'player': Attr('int', None, doc='only this player\'s cursor (any, when not given)')},
        parents=('scene',)),
    'menu': Tag(
        'A list of buttons (and text fields) over the scene. A player moves through it with up/down and '
        'chooses with select (Enter, a click, the joypad\'s A), or points at a button with the mouse — the '
        'pointer is that player\'s qg:cursor, so a click is replayed and travels in the lockstep like a key.',
        {'player': Attr('int', 1, doc='whose keys and pointer choose'),
         'position': Attr('enum:top-left|top-center|top-right|center|bottom-center', 'center'),
         'font': Attr('str', None, doc='a .ttf, relative to the .q or a folder above it'),
         'size': Attr('int', 16, doc='font size')},
        parents=('scene',)),
    'button': Tag(
        'A button of a qg:menu. What it holds runs when it is chosen: actions and statements, like a handler.',
        {'label': Attr('str', required=True, doc='its text, or an expression ({...}) read every frame'),
         'if': Attr('expr', None, doc='shown, and choosable, only while this is true')},
        parents=('menu',)),
    'field': Tag(
        'A text box of a qg:menu, bound to a string state: what is typed is the state. Typing is local to '
        'the machine (an address, a name) — a replay cannot type, and the lockstep does not carry it.',
        {'bind': Attr('ident', required=True, doc='a q:set of the scene or the game'),
         'label': Attr('str', '', doc='text before the box'),
         'max-length': Attr('int', 64)},
        parents=('menu',)),
    'zone': Tag(
        'An invisible rectangle with a tag: what touches it runs its qg:on-collision with= that tag.',
        {'name': Attr('ident', required=True),
         'tag': Attr('ident', required=True),
         'x': Attr('float', required=True), 'y': Attr('float', required=True),
         'width': Attr('float', required=True), 'height': Attr('float', required=True)},
        parents=('scene',)),
    'sprite': Tag(
        'A picture in the scene, with no behaviour: a backdrop, a divider, a sign.',
        {'sheet': Attr('ident', required=True), 'frame': Attr('int', 0),
         'x': Attr('float', required=True), 'y': Attr('float', required=True)},
        parents=('scene',)),
    'exit': Tag(
        'A rectangle that leads to another scene; the character arrives at the exit named at= there.',
        {'name': Attr('ident', required=True),
         'x': Attr('float', required=True), 'y': Attr('float', required=True),
         'width': Attr('float', required=True), 'height': Attr('float', required=True),
         'to': Attr('ident', required=True), 'at': Attr('ident', required=True)},
        parents=('scene',)),
    'camera': Tag(
        'What the screen shows.',
        {'follow': Attr('ident', required=True, doc='a character id'),
         'bounds': Attr('enum:tilemap|none', 'tilemap')},
        parents=('scene',)),
    'hud': Tag(
        'Text over the game.',
        {'position': Attr('enum:top-left|top-center|top-right|center|bottom-center', 'top-left'),
         'font': Attr('str', None, doc='a .ttf, relative to the .q or a folder above it'),
         'size': Attr('int', 8, doc='the font size of its items, unless an item says otherwise')},
        parents=('scene',)),
    'counter': Tag(
        'A number from the scene state, in the HUD.',
        {'bind': Attr('ident', required=True, doc='a q:set of the scene'),
         'label': Attr('str', '', doc='text before the number'),
         'size': Attr('int', None, doc='font size')},
        parents=('hud',)),
    'text': Tag(
        'A string from the scene state, in the HUD.',
        {'bind': Attr('ident', required=True, doc='a q:set of the scene'),
         'size': Attr('int', None, doc='font size')},
        parents=('hud',)),
    'on-collision': Tag(
        'What happens when this character or prefab touches something. Holds actions and statements; '
        '`me` is the toucher, `other` what it touched. In a prefab, only the game state is in reach.',
        {'with': Attr('ident', required=True, doc='the tag of what it touches'),
         'side': Attr('enum:any|top|bottom', 'any',
                      doc='top: landing on it; bottom: hitting it from below. A side handler runs '
                          'before the "any" one, which then does not'),
         'cooldown': Attr('int', 0, doc='ticks before this handler can fire again')},
        parents=('character', 'prefab')),
    'on-damage': Tag(
        'What happens when this prefab takes qg:damage and lives (`me.health` is what is left).',
        {},
        parents=('prefab',)),
    'on-death': Tag(
        'What happens when this prefab\'s health reaches 0, before it goes. In a scene, with of=, '
        'when any thing of that tag dies there.',
        {'of': Attr('ident', None, doc='scene: the tag')},
        parents=('prefab', 'scene')),
    'timer': Tag(
        'Runs its handler after so many ticks, or every so many ticks, in this scene.',
        {'after': Attr('int', None, doc='ticks from entering the scene, once'),
         'every': Attr('int', None, doc='ticks between runs, from entering the scene (or from=)'),
         'from': Attr('int', 0, doc='every: the tick the count starts at'),
         'count': Attr('int', 0, doc='every: stop after this many runs (0: never)')},
        parents=('scene',)),
    'spawner': Tag(
        'Places count instances of a prefab, one every so many ticks, from a tick on.',
        {'prefab': Attr('str', required=True, doc='a prefab name, or several comma-separated: one is drawn '
                                                 'from the seed for each instance'),
         'from': Attr('int', 0, doc='the tick of the first one'),
         'every': Attr('int', 60), 'count': Attr('int', 1, doc='0: no end'),
         'x': Attr('str', 'random', doc='a number, or random across the scene width (from the seed)'),
         'y': Attr('float', -12.0),
         'along': Attr('enum:edges', None, doc='edges: instead of x,y, a random point on the scene\'s border'),
         'heading': Attr('enum:inward', None, doc='along: a flying prefab heads into the scene...'),
         'spread': Attr('float', 0.0, doc='...turned by up to this many degrees either way, from the seed')},
        parents=('scene',)),
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
        {'action': Attr('ident', required=True, doc='a default action, or one a qg:input declares')},
        parents=('scene',)),
    'on-hit': Tag(
        'What happens when this character\'s swing (attack-action) reaches something. Holds actions and statements.',
        {'with': Attr('ident', required=True, doc='the tag of what it hits')},
        parents=('character',)),
    'on-fall': Tag(
        'What happens when this character falls below the tilemap. Holds actions and statements.',
        {},
        parents=('character',)),
    'move': Tag(
        'A fighter\'s attack, on an action: an animation with one active frame, in which a box of reach= '
        'at at= (in front, in the facing direction) is tested against the opponent once. A hit takes '
        'damage=, stuns for stun= ticks and pushes push= pixels; blocked (the opponent holding away), it '
        'takes no damage and half the rest.',
        {'name': Attr('ident', required=True),
         'action': Attr('ident', required=True, doc='a default action or one a qg:input declares'),
         'frames': Attr('str', required=True, doc='comma-separated frame numbers'),
         'fps': Attr('float', 12.0),
         'active': Attr('int', 1, doc='which frame (0-based) hits'),
         'reach': Attr('size', required=True, doc='the hit box, WxH'),
         'at': Attr('str', '0,0', doc='the hit box\'s centre from the body\'s, dx,dy; dx is forward'),
         'damage': Attr('int', 5), 'stun': Attr('int', 12), 'push': Attr('float', 40.0)},
        parents=('character',)),
    'on-ko': Tag(
        'What happens when this fighter\'s health reaches 0. Holds actions and statements; `me` is the loser, '
        '`other` the winner.',
        {},
        parents=('character',)),
    'bar': Tag(
        'A bar in the HUD: a number against its maximum — a q:set, or a fighter\'s health as `id.health`.',
        {'bind': Attr('str', required=True, doc='a q:set of the scene or the game, or a fighter\'s id and .health (p1.health)'),
         'max': Attr('float', 100.0),
         'width': Attr('int', 100), 'height': Attr('int', 10),
         'color': Attr('color', '#e04040')},
        parents=('hud',)),
    # actions
    'destroy': Tag(
        'Removes a thing from the scene.',
        {'target': Attr('ident', 'other', doc='other, me, or a q:set holding a thing (thing_at)')},
        parents=('handler',)),
    'bounce': Tag(
        'Throws the character up, as after a stomp.',
        {'target': Attr('enum:me', 'me'),
         'height': Attr('float', 32.0, doc='pixels')},
        parents=('handler',)),
    'play': Tag(
        'Plays a qg:sound. Directly in a scene: as the scene is entered.',
        {'sound': Attr('ident', required=True)},
        parents=('handler', 'scene')),
    'stop': Tag(
        'Stops a qg:sound (a looping one, mostly). Directly in a scene: as the scene is entered.',
        {'sound': Attr('ident', required=True)},
        parents=('handler', 'scene')),
    'respawn': Tag(
        'Puts a character back at its start or its last checkpoint, still; a thing back where it was '
        'placed, with its first heading and speed.',
        {'target': Attr('ident', 'me', doc='me, other, or a character of the scene by id')},
        parents=('handler',)),
    'deflect': Tag(
        'Changes where a flying thing (ai="fly") goes: flips one axis of its heading, or sets the heading '
        'to dx,dy (expressions; the length does not matter).',
        {'target': Attr('enum:other|me', 'other'),
         'axis': Attr('enum:x|y', None, doc='the axis to flip'),
         'dx': Attr('expr', None), 'dy': Attr('expr', None)},
        parents=('handler',)),
    'become': Tag(
        'Changes a character or a thing to one of its qg:states.',
        {'target': Attr('enum:me|other', 'me'),
         'state': Attr('ident', required=True)},
        parents=('handler',)),
    'spawn': Tag(
        'Places a new prefab instance in the scene.',
        {'prefab': Attr('ident', required=True),
         'at': Attr('enum:other|me|cursor|path', 'other',
                    doc='whose position; cursor: where the qg:on-select cursor is; path: the start of path='),
         'path': Attr('ident', None, doc='at="path": a qg:path of the scene, which an ai="path" prefab follows'),
         'dx': Attr('float', 0.0), 'dy': Attr('float', 0.0, doc='offset in pixels')},
        parents=('handler',)),
    'swap': Tag(
        'Replaces a thing with an instance of another prefab, in its place.',
        {'target': Attr('ident', 'other', doc='other, or a q:set holding a thing'),
         'prefab': Attr('ident', required=True)},
        parents=('handler',)),
    'checkpoint': Tag(
        "Makes the other thing's position where the character respawns.",
        {'target': Attr('enum:me', 'me'),
         'at': Attr('enum:other', 'other')},
        parents=('handler',)),
    'damage': Tag(
        'Takes health from a thing; at 0 its qg:on-death runs and it goes.',
        {'target': Attr('enum:other|me', 'other'),
         'amount': Attr('int', 1)},
        parents=('handler',)),
    'burst': Tag(
        'A puff of particles where a thing is. Cosmetic.',
        {'at': Attr('enum:other|me', 'me'),
         'color': Attr('color', '#ffffff'),
         'count': Attr('int', 12)},
        parents=('handler',)),
    'shake': Tag(
        'Shakes the scene a thing is in. Cosmetic.',
        {'at': Attr('enum:other|me', 'me'),
         'frames': Attr('int', 10),
         'strength': Attr('float', 3.0, doc='pixels')},
        parents=('handler',)),
    'put': Tag(
        'Moves a thing or a character to a point, at once.',
        {'target': Attr('ident', 'other', doc='me, other, a character id, or a q:set holding a thing (thing_at)'),
         'x': Attr('expr', required=True), 'y': Attr('expr', required=True)},
        parents=('handler',)),
    'goto-scene': Tag(
        'Leaves this scene for another, at the end of the tick. Scene state is lost; game state stays.',
        {'name': Attr('ident', required=True)},
        parents=('handler',)),
}

# q: statements the compiler reads itself (see model.py).
STATEMENTS = ('set', 'if', 'else', 'elseif', 'loop', 'function', 'return', 'call')
