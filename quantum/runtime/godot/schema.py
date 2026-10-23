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


# The tags that hold a handler: actions (and q: statements), run when it fires.
HANDLERS = ('on-collision', 'on-fall', 'on-input', 'on-select', 'on-hit', 'on-ko', 'on-death', 'on-tile',
            'on-animation-end', 'on-locked', 'on-damage', 'timer', 'button', 'on-end', 'on-separate',
            'on-screen-exit', 'on-screen-enter', 'for-each', 'after', 'when', 'choice', 'field')

# The actions a handler can hold, besides q: statements.
ACTIONS = ('destroy', 'bounce', 'play', 'respawn', 'become', 'spawn', 'swap', 'checkpoint', 'goto-scene',
           'damage', 'burst', 'shake', 'deflect', 'stop', 'put', 'host', 'join', 'leave', 'pause', 'resume',
           'say', 'save', 'continue', 'next-language', 'tween', 'velocity', 'emit', 'set-tile',
           'play-animation', 'give', 'take', 'reset-items', 'for-each', 'time-scale', 'quit', 'start-now', 'watch',
           'after', 'beam', 'camera-to', 'attach', 'detach', 'volume', 'fullscreen', 'rumble', 'music', 'travel')

TAGS: Dict[str, Tag] = {
    'tileset': Tag(
        'A sheet of equal tiles; tilemaps and sprites name it. With shape="hex" its tiles are hexes with their '
        'points up, every other row of a map half a hex to the right (a strategy map); with shape="iso", '
        'diamonds, every other row half a diamond on. The rows of a qg:tilemap are the rows seen; a walker\'s '
        'neighbours, its way and the cell at a point follow the shape.',
        {'name': Attr('ident', required=True),
         'src': Attr('str', required=True, doc='the image, relative to the .q or a folder above it'),
         'tile': Attr('tile', required=True, doc='tile size in pixels: 18 (square), or WxH for hexes and diamonds '
                                                 '(28x32)'),
         'shape': Attr('enum:square|hex|iso', 'square', doc='square tiles, hexes or diamonds')},
        parents=('application',)),
    'tile': Tag(
        'One tile of a qg:tileset that is not a full solid square, for the tilemap layers with collision: '
        'a lower top, a thin ledge, a slope, a tile to jump through from below, or no collision at all. '
        'A flipped tile (a negative number in the tilemap) flips its shape too.',
        {'frame': Attr('int', required=True, doc='which tile: its number in the tilemap is frame+1'),
         'shape': Attr('str', None, doc='the solid part, as x,y points from the tile\'s top-left corner '
                                        'separated by semicolons (0,10; 64,10; 64,64; 0,64); none: not solid'),
         'one-way': Attr('bool', False, doc='stood on from above, jumped through from below'),
         'kind': Attr('enum:ladder|water|ice|hurt', None,
                      doc='ladder: passed through, climbed with up and down, let go of with jump; water: passed '
                          'through, slow to sink in, a jump is a stroke, slower to walk; ice: slid on (a solid '
                          'tile to stand on in a platformer, a floor in a top-down game); hurt: a '
                          'character\'s qg:on-tile kind="hurt" runs while it touches one. In a Tiled tileset: a '
                          'tile\'s class, or its kind property'),
         'frames': Attr('int', 1, doc='an animated tile (water, lava, a torch): how many frames it shows in turn, '
                                      'itself and the ones after it in the sheet\'s row, which are then not tiles of '
                                      'their own. Only seen'),
         'fps': Attr('float', 4.0, doc='frames a second, with frames='),
         'cost': Attr('int', 1, doc='what a step onto it costs a walker finding its way (ai="pathfind", qg:seek, '
                                    'a pointer\'s click, qg:travel, cost()): a forest 2, a marsh 3. The way found is '
                                    'the cheapest')},
        parents=('tileset',)),
    'spritesheet': Tag(
        'A sheet of equal frames for characters and items. With slice=, it is a frame that stretches to a box '
        '(a dialogue\'s box=): its corners stay as drawn, its edges and middle stretch.',
        {'name': Attr('ident', required=True),
         'src': Attr('str', required=True),
         'tile': Attr('tile', required=True, doc='frame size in pixels: 24, or 8x32 for frames that are not square'),
         'slice': Attr('str', None, doc='how wide its edges are, in pixels, that do not stretch: 16, or left, top, '
                                        'right, bottom (16, 8, 16, 8); its first frame is the frame')},
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
        '(`--q-host=PORT`, player 1), the others join (`--q-join=HOST:PORT`, players 2.. in order, or the '
        'seat `--q-seat=N` asks for). '
        'The players\' characters are told apart by player=; nobody declares keys for players 2... '
        'A player who leaves can come back: the others wait, and the next to join takes the seat, catching '
        'up the game so far (not under rollback=, where the game ends).',
        {'players': Attr('int', required=True, doc='how many, 2 or more: the game starts by itself as the last '
                                                     'of them joins'),
         'min-players': Attr('int', None, doc='fewer may play: once this many are there, the host may start '
                                              'the game (qg:start-now, or the lobby\'s Start now) with those who '
                                              'are; `net_players()` then says how many play'),
         'delay': Attr('int', 3, doc='ticks between a press and its effect, everywhere: hides the round trip'),
         'check-every': Attr('int', 60, doc='ticks between comparisons of the whole state across peers; '
                                           'a difference is a desync, reported and fatal (0: never)'),
         'rollback': Attr('int', 0, doc='rollback instead of waiting: up to this many ticks run ahead on a guess of '
                                        'the others\' input and are run again when it was wrong (0: plain lockstep). '
                                        'The scenes the networked game reaches may only hold fighters, timers, '
                                        'menus, the HUD, pictures and a camera — nothing that goes through physics'),
         'start': Attr('ident', None, doc='the scene the networked game starts in, on every peer, once all the '
                                          'players are there (the first scene when not given); the scenes before '
                                          'it — a title, a lobby — run on each machine alone'),
         'transport': Attr('enum:enet|websocket', 'enet',
                           doc='enet (desktop to desktop), or websocket (a browser build can join a desktop host)')},
        parents=('application',)),
    'sound': Tag(
        'A sound the game can play (qg:play).',
        {'name': Attr('ident', required=True),
         'src': Attr('str', required=True, doc='an .ogg or .wav'),
         'loop': Attr('bool', False, doc='plays until qg:stop (music)'),
         'bus': Attr('ident', None, doc='the bus it is heard on (music, effects...): how loud a bus is, qg:volume '
                                        'and a menu\'s qg:slider set, kept between runs')},
        parents=('application',)),
    'particles': Tag(
        'A particle effect the game can show: a preset and a few overrides. qg:emit plays it once where a thing '
        'is; qg:emitter keeps it going in a scene. Only seen: the game\'s state never depends on it.',
        {'name': Attr('ident', required=True),
         'preset': Attr('enum:puff|sparks|smoke|dust|fire|rain|snow|confetti|stars', required=True,
                        doc='puff, sparks, smoke, dust, confetti and stars play once; fire, rain and snow keep going'),
         'color': Attr('color', None, doc='the preset\'s own when not given (confetti is every colour)'),
         'amount': Attr('int', None, doc='how many particles'),
         'lifetime': Attr('float', None, doc='seconds each one lives'),
         'speed': Attr('float', None, doc='pixels a second, about'),
         'size': Attr('float', None, doc='pixels, about')},
        parents=('application',)),
    'language': Tag(
        'The game\'s texts in another language: each qg:phrase gives one text as written in the game, and '
        'what it is in this language. A text with no phrase stays as written. The language is ?lang= in a '
        'web page, --q-lang= on the command line, else the system\'s, when the game has it; `tr(text)` '
        'translates a text an expression puts together, and `tr_n(one, other, n)` a count\'s word (1 potion, 2 '
        'potions) by the language\'s plural rule. In pt and es, a qg:lobby\'s own texts come translated. A '
        'qg:asset gives a picture or a sound drawn or spoken in the language.',
        {'lang': Attr('str', required=True, doc='a language code: pt, es, zh, pt_BR...'),
         'name': Attr('str', '', doc='its own name for it (Português)'),
         'font': Attr('str', None, doc='a .ttf with the letters of its alphabet that the game\'s fonts lack '
                                       '(Cyrillic, Greek, Japanese): every text draws them from it')},
        parents=('application',)),
    'phrase': Tag(
        'One text of the game, in a qg:language. The plural word of a count (`tr_n(\'potion\', \'potions\', n)`) '
        'takes the forms its language has: in Russian, 1 зелье, 2 зелья, 5 зелий.',
        {'text': Attr('str', required=True, doc='the text exactly as the game shows it (a button, a line, a HUD text)'),
         'as': Attr('str', required=True, doc='what it is in this language; for a plural word, the form of the '
                                               'counts the others are not (5 зелий)'),
         'one': Attr('str', None, doc='a plural word\'s form for one (1, 21, 31 in ru, uk, be; 1 elsewhere); when '
                                      'not given, the phrase of the word for one'),
         'few': Attr('str', None, doc='its form for a few: 2 to 4 (22 to 24...) in ru, uk, be and pl; 2 to 4 in cs '
                                      'and sk'),
         'many': Attr('str', None, doc='its form for many (5 to 20, 25...) in ru, uk, be and pl; as= when not given')},
        parents=('language',)),
    'asset': Tag(
        'A picture or a sound of the game as it is in a qg:language: the banner with its words in the language, a '
        'voice. The scenes that start while the language is shown draw the picture; the sound plays from the '
        'moment it is chosen.',
        {'name': Attr('ident', required=True, doc='a qg:spritesheet, qg:tileset or qg:sound of the game'),
         'src': Attr('str', required=True, doc='its file in this language, relative to the .q or a folder above it; '
                                               'a picture has the same frame size')},
        parents=('language',)),
    'item': Tag(
        'A kind of thing the players carry: keys, gems, potions. How many they hold is the game\'s state, kept '
        'across scenes and in a qg:save; `held(\'key\')` reads it. A prefab with gives= is picked up as one; a '
        'solid prefab with opens-with= opens for one; qg:give and qg:take add and spend them; qg:inventory '
        'shows them.',
        {'name': Attr('ident', required=True),
         'label': Attr('str', None, doc='what a player reads (else its name), in the HUD'),
         'sheet': Attr('ident', None, doc='a qg:spritesheet or qg:tileset: its picture in qg:inventory'),
         'frame': Attr('int', 0),
         'max': Attr('int', 0, doc='the most they can hold (0: no limit)'),
         'start': Attr('int', 0, doc='how many they hold when the game starts'),
         'sound': Attr('ident', None, doc='a qg:sound, played as one is picked up'),
         'particles': Attr('ident', None, doc='a qg:particles, burst where one is picked up')},
        parents=('application',)),
    'prefab': Tag(
        'A kind of thing the scene places with qg:instance. With ai= it moves.',
        {'name': Attr('ident', required=True),
         'tag': Attr('ident', doc='what collisions see it as (`with="coin"`)'),
         'sheet': Attr('ident', required=True, doc='a qg:spritesheet or qg:tileset'),
         'frame': Attr('int', 0),
         'hitbox': Attr('size', required=True),
         'ai': Attr('enum:patrol|wander|chase|pathfind|fly|sway|shuttle|path|turret|behavior', None,
                    doc='patrol: walks under gravity, turns at walls (and at edges with turns-at); '
                        'wander: top-down, changes direction now and then (from the scene seed); '
                        'chase: top-down, goes for the character within sight=, straight at it; '
                        'pathfind: as chase, but around the walls, by the shortest way over the tilemap\'s free cells; '
                        'fly: straight along heading=; sway: side to side across the scene; '
                        'shuttle: a solid that goes dx=,dy= and back every period= ticks, carrying what stands on it; '
                        'path: follows the qg:path it was spawned on (qg:spawn at="path"), then stands at its end; '
                        'turret: stands, and fires fire-prefab at the nearest targets= within range= every fire-every; '
                        'behavior: top-down, made of the parts its qg:behavior lists (qg:seek, qg:flee...)'),
         'range': Attr('float', 100.0, doc='turret: pixels'),
         'targets': Attr('ident', None, doc='turret: the tag it shoots at'),
         'attack': Attr('enum:shoot|area', 'shoot', doc='turret: shoot spawns fire-prefab headed at the target; '
                                                        'area damages every target in range by damage='),
         'damage': Attr('int', 1, doc='turret attack="area": the damage'),
         'dx': Attr('float', 0.0, doc='shuttle: how far it goes, pixels'),
         'dy': Attr('float', 0.0, doc='shuttle: how far it goes, pixels'),
         'period': Attr('int', 240, doc='shuttle: ticks for there and back'),
         'one-way': Attr('bool', False, doc='solid: can be jumped through from below and stood on'),
         'shape': Attr('str', None, doc='solid: the solid part as x,y points from its centre, separated by '
                                        'semicolons (-96,-21; 96,-21; 96,6; -96,6), instead of the hitbox'),
         'scale': Attr('float', 1.0, doc='the picture\'s size, times its frame (the hitbox stays as given)'),
         'walls': Attr('enum:pass|stop|bounce', 'pass', doc='fly: pass goes through the tiles; stop is gone on '
                                                           'touching one; bounce turns off it, as a ball off a '
                                                           'wall (the way across it reverses)'),
         'trail': Attr('color', None, doc='a line it leaves behind it as it moves, fading (a shot\'s streak, a '
                                          'ship\'s wake): only seen'),
         'pushable': Attr('bool', False, doc='solid: a character controller="grid" or "pointer" that steps into it '
                                             'pushes it a cell on, if that cell is free (no wall, no thing): a crate'),
         'extends': Attr('ident', None, doc='another prefab it is made from: it has all of it (attributes, '
                                            'animations, states, handlers) but what it says itself; a qg:animation '
                                            'or qg:state of the same name, a handler with the same with= and side=, '
                                            'a qg:behavior, replace the other\'s'),
         'spacing': Attr('float', 0.0, doc='things of its tag keep at least this many pixels apart as they move: a '
                                           'crowd, not a pile (0: they may overlap)'),
         'sight': Attr('float', 80.0, doc='chase, pathfind, and the parts of a behavior: pixels'),
         'heading': Attr('str', 'down', doc='fly: up, down, left, right, or a direction as x,y (-1,0.5)'),
         'accel': Attr('float', 0.0, doc='fly: pixels per second added to its speed every second'),
         'lifetime': Attr('int', 0, doc='fly: gone after this many ticks (0: never); any fly is gone off-screen'),
         'particles': Attr('ident', None, doc='a qg:particles kept going where it is, as it moves (a fire, an '
                                              'engine\'s flame, a torch carried): only seen'),
         'visible': Attr('expr', None, doc='shown only while this is true, read every tick (`me` is it): blinking '
                                           'while hurt, hidden in the dark; it still collides'),
         'flip-v': Attr('bool', False, doc='its picture upside down'),
         'layer': Attr('int', 0, doc='drawn over things of a lower layer and under those of a higher one, '
                                     'whatever y-sort says'),
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
         'solid': Attr('bool', False, doc='characters stand on it and bump it (a block)'),
         'gives': Attr('ident', None, doc='a qg:item: a character that touches it picks it up (amount= of '
                                          'them) and it is gone; a named instance stays gone when the scene '
                                          'is entered again'),
         'amount': Attr('int', 1, doc='gives=: how many'),
         'opens-with': Attr('ident', None, doc='solid: a qg:item. A character that bumps it holding one '
                                               'spends it and it opens (it is gone; a named one stays gone); '
                                               'without one, its qg:on-locked runs'),
         'keeps': Attr('bool', False, doc='opens-with=: the item is not spent (a key for every door)')},
        parents=('application',)),
    'state': Tag(
        'A form of a character or a prefab (small, big; calm, angry): hitbox, frame, animations, '
        'and for a prefab its speed and fire-every. `me.state` reads it; qg:become changes it.',
        {'name': Attr('ident', required=True),
         'hitbox': Attr('size', None, doc='a character needs one; a prefab keeps its own'),
         'frame': Attr('int', None, doc='its picture in this state (its own frame when not given)'),
         'speed': Attr('float', None, doc='prefab: overrides its speed'),
         'fire-every': Attr('int', None, doc='prefab: overrides its fire-every'),
         'fire-prefab': Attr('ident', None, doc='prefab: overrides its fire-prefab'),
         'range': Attr('float', None, doc='turret: overrides its range'),
         'initial': Attr('bool', False, doc='the state it starts in (else the first one)')},
        parents=('character', 'prefab')),
    'animation': Tag(
        'Frames of the sheet, cycled. A character plays "idle", "walk" and "jump" by what it does (a platformer '
        '"fall" while it comes down, when it has one; a topdown one '
        '"walk-up" and "walk-down" when it has them, "walk-up" upside down for down, and while it swings '
        '"attack", or "attack-up" and "attack-down" by where it faces); a prefab plays "walk".',
        {'name': Attr('ident', required=True),
         'frames': Attr('str', required=True, doc='comma-separated frame numbers'),
         'fps': Attr('float', 8.0),
         'loop': Attr('bool', True, doc='false: it plays once, stays on its last frame, and its '
                                       'qg:on-animation-end runs (an attack, a fall, a death)')},
        parents=('character', 'prefab', 'state')),
    'scene': Tag(
        'A screen of the game. The first one is where the game starts.',
        {'name': Attr('ident', required=True),
         'width': Attr('int', 256), 'height': Attr('int', 224),
         'background': Attr('color', '#000000'),
         'seed': Attr('expr', '0', doc='the random seed, a number or an expression of the game\'s state read as the '
                                      'scene is entered (a world\'s number); the same seed gives the same game, so a '
                                      'scene entered again and again draws the same each time unless its seed is '
                                      'read from the state (seed="{round}")'),
         'save': Attr('bool', False, doc='entering the scene saves the game to continue here (qg:save), '
                      'as a room of an adventure does'),
         'y-sort': Attr('bool', False, doc='characters and things are drawn by how low they stand, the lower in '
                                           'front: depth seen from above (a layer= still comes first)'),
         'ambient': Attr('color', None, doc='a dark scene: the light where no qg:light reaches (#000000 is black, '
                                            '#ffffff as drawn); its solid tiles cast the shadows of the lights with '
                                            'shadows="true"')},
        parents=('application',)),
    'tilemap': Tag(
        'The level: CSV rows of tile numbers (0 is empty, n is tile n-1 of the tileset), '
        'or a Tiled map (src=) whose tile layers draw it and whose object layers place prefabs by class. '
        'Several in a scene are layers of one map, drawn in order (a floor, a path, the walls), on one tileset. '
        'A Tiled map may use several tilesets (each layer draws from one, which is the qg:tileset of the game with '
        'the same image) and flipped or turned tiles; an object\'s state property is the qg:state it starts in; '
        'objects of class zone (a tag property), exit (to and at properties) and path (a polyline) are the '
        'scene\'s qg:zone, qg:exit and qg:path; the map\'s own properties are read with tiled(\'name\').',
        {'tileset': Attr('ident', required=True),
         'collision': Attr('bool', False, doc='every tile is solid (a Tiled layer says so with a collision property)'),
         'src': Attr('str', None, doc='a .tmx, relative to the .q or a folder above it')},
        parents=('scene',), text='the CSV rows'),
    'character': Tag(
        'A body the player moves: a platformer, or a walker on a world map.',
        {'id': Attr('ident', required=True),
         'controller': Attr('enum:platformer|map|topdown|ship|fighter|grid|pointer|behavior', required=True,
                            doc='grid: steps from cell to cell of the tilemap; the tiles of a layer with collision, '
                                'and the things, stop it, and stepping into a thing runs its qg:on-collision '
                                'with the thing\'s tag; `me.col` and `me.row` are its cell. pointer: as grid, and '
                                'a click (its player\'s qg:cursor) walks it to that cell by the shortest way '
                                'around the walls and things. behavior: made of the parts its qg:behavior lists'),
         'step-frames': Attr('int', 15, doc='grid: ticks to walk one cell (a bump takes as long)'),
         'diagonal': Attr('bool', False, doc='grid: two directions held at once step diagonally'),
         'player': Attr('int', 1, doc='whose keys move it (qg:input player=); 1 has the defaults'),
         'health': Attr('int', 100, doc='fighter: hits it takes; at 0 it is KO and qg:on-ko runs'),
         'facing': Attr('enum:left|right', 'right', doc='fighter: where it looks at first'),
         'bounds': Attr('enum:scene|none', None, doc='kept inside the scene: a ship unless none, a topdown '
                                                    'character when scene'),
         'axis': Attr('enum:both|vertical|horizontal', 'both', doc='ship: which way it can move'),
         'fire-action': Attr('ident', None, doc='ship, platformer: the action that shoots (jump, or one a qg:input '
                                                 'declares)'),
         'fire-prefab': Attr('ident', None, doc='ship: what it shoots, placed above it; platformer: in front of it, '
                                                'a fly prefab heading the way it faces'),
         'fire-every': Attr('int', 10, doc='ship: ticks between shots while the action is held; platformer: the '
                                           'fewest ticks between two presses that shoot'),
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
         'buffer-frames': Attr('int', 0, doc='platformer: a jump pressed up to this many ticks before landing jumps '
                                             'as it lands (0: only a press on the floor)'),
         'gravity': Attr('float', 900.0, doc='pixels per second squared'),
         'max-fall': Attr('float', 300.0, doc='terminal velocity, pixels per second'),
         'jump-sound': Attr('ident', None, doc='a qg:sound, played on take-off'),
         'jump-speed': Attr('float', None, doc='platformer: the take-off speed, pixels per second, instead of '
                                               'jump-height'),
         'accel': Attr('float', 0.0, doc='platformer: pixels per second squared towards the run speed '
                                         '(0: at once)'),
         'air-jumps': Attr('int', 0, doc='platformer: jumps it may take in the air before landing again'),
         'air-jump-boost': Attr('float', 1.0, doc='platformer: an air jump multiplies the speed across by this'),
         'jump-cut': Attr('float', 0.0, doc='platformer: releasing the button while rising multiplies the rise by '
                                            'this, once (0: the extra gravity of variable-jump instead)'),
         'scale': Attr('float', 1.0, doc='the picture\'s size, times its frame (the hitbox stays as given)'),
         'if': Attr('expr', None, doc='placed only when this is true as the scene is built: a second player\'s '
                                      'character only in a networked game, `net_status() != \'offline\'`'),
         'particles': Attr('ident', None, doc='a qg:particles kept going where it is, as it moves (a fire, an '
                                              'engine\'s flame, a torch carried): only seen'),
         'visible': Attr('expr', None, doc='shown only while this is true, read every tick (`me` is it): blinking '
                                           'while hurt, hidden in the dark; it still collides'),
         'flip-v': Attr('bool', False, doc='its picture upside down'),
         'layer': Attr('int', 0, doc='drawn over things of a lower layer and under those of a higher one, '
                                     'whatever y-sort says')},
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
        {'id': Attr('ident', None, doc='its name in expressions, as a character\'s: `aim.x`, `aim.y` (with grid=, '
                                       '`aim.col`, `aim.row`), and a target of qg:beam'),
         'player': Attr('int', 1),
         'step': Attr('float', 16.0, doc='pixels per tick while a direction is held'),
         'grid': Attr('int', None, doc='cell size: the cursor snaps to cell centres'),
         'cells': Attr('bool', False, doc='it snaps to the middles of the cells of the scene\'s qg:tilemap, '
                                          'whatever their shape (a hex map\'s); `cursor.col`, `cursor.row` are '
                                          'the cell'),
         'sheet': Attr('ident', None), 'frame': Attr('int', 0)},
        parents=('scene',)),
    'path': Tag(
        'A route through the scene, straight from point to point, that ai="path" prefabs follow '
        '(qg:spawn at="path" path=).',
        {'name': Attr('ident', required=True),
         'points': Attr('str', required=True, doc='x,y pairs separated by semicolons: 0,100; 200,100; 200,300')},
        parents=('scene',)),
    'on-select': Tag(
        'What happens when a player presses select with their qg:cursor somewhere (or another action: action= '
        'with a qg:input of the right mouse button, MouseRight, is a right click on a thing). Holds actions and '
        'statements; `cursor` is where (x, y, col, row, player), `other` the thing under it, or null. '
        '`hovered()` reads the thing under a cursor at any time.',
        {'player': Attr('int', None, doc='only this player\'s cursor (any, when not given)'),
         'action': Attr('ident', 'select', doc='the action that chooses: select (the left button, Enter), or one '
                                               'a qg:input declares (keys="MouseRight", "WheelUp", "WheelDown")')},
        parents=('scene',)),
    'menu': Tag(
        'A list of buttons (and text fields) over the scene. A player moves through it with up/down and '
        'chooses with select (Enter, the joypad\'s A: the button that has the focus), or points at a button '
        'with the mouse and clicks it (a click away from the buttons chooses nothing) — the pointer is that '
        'player\'s qg:cursor and the click its "click" action, so a click is replayed and travels in the '
        'lockstep like a key.',
        {'player': Attr('int', 1, doc='whose keys and pointer choose'),
         'local': Attr('bool', False, doc='the menu of whoever plays at this machine (its seat, in a networked '
                                          'game); it holds only shared fields, whose texts reach the others'),
         'if': Attr('expr', None, doc='shown, and choosable, only while this is true: paused(), a q:set...'),
         'position': Attr('enum:top-left|top-center|top-right|center|bottom-center', 'center'),
         'x': Attr('int', None, doc='with y=, its top-left corner on the screen, in pixels (in place of position=)'),
         'y': Attr('int', None),
         'source': Attr('expr', None, doc='a list: the menu holds one qg:button, and shows it once for each row of '
                                          'it, read every frame (a squad to choose from, the clubs, a shop\'s goods); '
                                          'the row is as= in its label=, if= and what it runs'),
         'as': Attr('ident', None, doc='with source=: the name of the row'),
         'font': Attr('str', None, doc='a .ttf, relative to the .q or a folder above it'),
         'size': Attr('int', 16, doc='font size'),
         'box': Attr('ident', None, doc='a qg:spritesheet with slice=: the buttons are in a box drawn with it, '
                                        'stretched (a frame)'),
         'columns': Attr('int', 1, doc='its items in a grid of so many columns: left and right move along a row'),
         'rows': Attr('int', 0, doc='how many rows show at once; the others scroll into view with the focus '
                                    '(0: all of them)')},
        parents=('scene',)),
    'button': Tag(
        'A button of a qg:menu. What it holds runs when it is chosen: actions and statements, like a handler.',
        {'label': Attr('str', required=True, doc='its text, or an expression ({...}) read every frame'),
         'if': Attr('expr', None, doc='shown, and choosable, only while this is true')},
        parents=('menu',)),
    'field': Tag(
        'A text box of a qg:menu, bound to a string state: what is typed is the state. Typing is local to '
        'the machine (an address) — the lockstep does not carry it. A shared field (shared="true") is a '
        'draft until Enter sends it: the text goes with the player\'s input for a tick, and on that tick, on '
        'every machine of a networked game, it becomes the bound state and what the field holds runs, with '
        '`sender` (the seat that sent it) and `text` — names, a short chat. While a field is typed in, the '
        'keys type and play nothing.',
        {'bind': Attr('ident', required=True, doc='a q:set of the scene or the game'),
         'label': Attr('str', '', doc='text before the box'),
         'max-length': Attr('int', 64),
         'shared': Attr('bool', False, doc='sent to every machine with the inputs, on Enter')},
        parents=('menu',)),
    'slider': Tag(
        'A value of a qg:menu that left and right change while it has the focus: how loud a bus is (bus=, '
        'from 0 to 100, kept between runs), or a number of the scene or the game (bind=).',
        {'label': Attr('str', '', doc='text before it'),
         'bus': Attr('ident', None, doc='a bus of the game\'s sounds (qg:sound bus=), or bind='),
         'bind': Attr('ident', None, doc='a number q:set of the scene or the game, or bus='),
         'min': Attr('float', 0.0), 'max': Attr('float', 100.0),
         'step': Attr('float', 10.0, doc='how much a press of left or right changes it'),
         'if': Attr('expr', None, doc='shown, and choosable, only while this is true')},
        parents=('menu',)),
    'rebind': Tag(
        'A key of a qg:menu: it shows the action\'s key, and once chosen, the next key, mouse button or joypad '
        'button pressed becomes the action\'s (Escape keeps the old one). Kept between runs. Local to the '
        'machine, as a field is: the replay and the lockstep carry the actions, not the keys.',
        {'action': Attr('ident', required=True, doc='an action of the game (qg:input, or a default one)'),
         'label': Attr('str', '', doc='text before the key; the action\'s name when not given'),
         'player': Attr('int', 1, doc='whose action'),
         'if': Attr('expr', None, doc='shown, and choosable, only while this is true')},
        parents=('menu',)),
    'dialogue': Tag(
        'Lines someone says, shown one at a time in a box at the bottom of the screen (qg:say opens it).',
        {'name': Attr('ident', required=True),
         'font': Attr('str', None, doc='a .ttf, relative to the .q or a folder above it'),
         'size': Attr('int', 24, doc='font size'),
         'speed': Attr('float', 0.0, doc='letters a second, typed in as each line shows (select shows it whole '
                                         'at once); 0: the whole line at once'),
         'sheet': Attr('ident', None, doc='a qg:spritesheet of faces: a line\'s portrait= is a frame of it'),
         'box': Attr('ident', None, doc='a qg:spritesheet with slice=: the box is drawn with it, stretched (a frame)')},
        parents=('scene',)),
    'line': Tag(
        'One line of a qg:dialogue: who says it, and what. With qg:choice inside, the player chooses (up and '
        'down, select, or a click), and the choice\'s actions run before the next line.',
        {'who': Attr('str', '', doc='the name over the text, or an expression ({...})'),
         'text': Attr('str', required=True, doc='the line, or an expression ({...}) read as it is shown'),
         'portrait': Attr('int', None, doc='a frame of the dialogue\'s sheet=, beside the text')},
        parents=('dialogue',)),
    'choice': Tag(
        'One answer to a qg:line: what the player reads, and what happens when it is chosen (then the next line). '
        'Holds actions and statements: a qg:say opens another dialogue, a q:set remembers the answer.',
        {'label': Attr('str', required=True, doc='what it says, or an expression ({...})'),
         'if': Attr('expr', None, doc='offered only when this is true as the line shows')},
        parents=('line',)),
    'on-end': Tag(
        'What happens when a qg:dialogue has shown its last line, or when a qg:tween is done (the last of its '
        'repeats; `me` is the thing it moved, and another tween in it plays after: a sequence). Holds actions and '
        'statements.',
        {},
        parents=('dialogue', 'tween', 'travel')),
    'on-separate': Tag(
        'What happens when this character or prefab stops touching something it touched: a plate stepped off, '
        'a door that closes behind. Holds actions and statements; `me` is the one that touched, `other` what it '
        'touched. Not when the other is destroyed: it left nothing.',
        {'with': Attr('ident', required=True, doc='the tag of what it stops touching')},
        parents=('character', 'prefab')),
    'on-screen-exit': Tag(
        'What happens when this character or prefab leaves the screen: the camera\'s view, or the scene when it '
        'has no camera. In a scene, with of=, when any thing of that tag does (`other` is the thing). Holds '
        'actions and statements; it runs in the game\'s tick, the same on every peer.',
        {'of': Attr('ident', None, doc='scene: the tag'),
         'side': Attr('enum:any|top|bottom|left|right', 'any', doc='the edge it left by')},
        parents=('character', 'prefab', 'scene')),
    'on-screen-enter': Tag(
        'What happens when this character or prefab comes onto the screen from outside it (one placed on the '
        'screen has not come onto it). In a scene, with of=, when any thing of that tag does.',
        {'of': Attr('ident', None, doc='scene: the tag'),
         'side': Attr('enum:any|top|bottom|left|right', 'any', doc='the edge it came in by')},
        parents=('character', 'prefab', 'scene')),
    'zone': Tag(
        'An invisible rectangle with a tag: what touches it runs its qg:on-collision with= that tag.',
        {'name': Attr('ident', required=True),
         'tag': Attr('ident', required=True),
         'x': Attr('float', required=True), 'y': Attr('float', required=True),
         'width': Attr('float', required=True), 'height': Attr('float', required=True)},
        parents=('scene',)),
    'parallax': Tag(
        'A backdrop behind the level that the camera scrolls slower than the level: a sky, distant hills. '
        'Its picture is one frame of a sheet, placed on the screen, repeating across. Several are drawn in order.',
        {'sheet': Attr('ident', required=True), 'frame': Attr('int', 0),
         'y': Attr('float', 0.0, doc='where its top is on the screen'),
         'scroll': Attr('float', 0.0, doc='how fast it scrolls across with the camera: 0 stays still, '
                                          '1 moves with the level'),
         'repeat': Attr('bool', True, doc='repeats across, so it never ends')},
        parents=('scene',)),
    'sprite': Tag(
        'A picture in the scene, with no behaviour: a backdrop, a divider, a sign.',
        {'sheet': Attr('ident', required=True),
         'frame': Attr('expr', '0', doc='a number, or an expression the picture follows tick by tick: '
                       '`{1 if hurt > 0 else 0}`'),
         'x': Attr('float', required=True), 'y': Attr('float', required=True)},
        parents=('scene',)),
    'emitter': Tag(
        'A qg:particles effect that keeps going in the scene: rain across its width, a fire on a spot.',
        {'particles': Attr('ident', required=True),
         'x': Attr('float', required=True), 'y': Attr('float', required=True),
         'width': Attr('float', 0.0, doc='rain and snow: the band they fall across, pixels (0: a point)')},
        parents=('scene',)),
    'exit': Tag(
        'A rectangle that leads to another scene; the character arrives at the exit named at= there.',
        {'name': Attr('ident', required=True),
         'x': Attr('float', required=True), 'y': Attr('float', required=True),
         'width': Attr('float', required=True), 'height': Attr('float', required=True),
         'to': Attr('ident', required=True), 'at': Attr('ident', required=True)},
        parents=('scene',)),
    'camera': Tag(
        'What the screen shows: it follows a character, or the middle of several, in the game\'s ticks (a replay '
        'and every peer frame the same). Only seen: nothing in the game\'s state depends on it.',
        {'follow': Attr('str', required=True, doc='a character id, or several: "p1, p2" (their middle)'),
         'bounds': Attr('enum:tilemap|none', 'tilemap'),
         'zoom': Attr('float', 1.0, doc='2: twice as close'),
         'dead-zone': Attr('size', None, doc='WxH: the box about the middle of the screen in which the followed one '
                                             'moves before the camera does'),
         'lead': Attr('float', 0.0, doc='pixels it looks ahead, the way the followed one goes'),
         'smooth': Attr('float', 0.0, doc='how fast it catches up, per second (0: at once)'),
         'fit': Attr('bool', False, doc='several followed: it zooms out to keep them all on the screen, down to '
                                        'zoom-min, and back in as they come together'),
         'zoom-min': Attr('float', 0.5, doc='fit: as far out as it goes'),
         'player': Attr('int', None, doc='one view per player: this is that player\'s. On one machine the screen '
                                         'splits (side by side for two, quarters for three or four); over the '
                                         'network each machine shows its own player\'s. A camera that follows no '
                                         'one present has no view')},
        parents=('scene',)),
    'hud': Tag(
        'Text and pictures over the game.',
        {'position': Attr('enum:top-left|top-center|top-right|center|bottom-left|bottom-center|bottom-right',
                          'top-left'),
         'x': Attr('int', None, doc='with y=, its top-left corner on the screen, in pixels (in place of position=): '
                                    'a panel of a screen laid out by hand'),
         'y': Attr('int', None),
         'box': Attr('ident', None, doc='a qg:spritesheet with slice=: what it shows is in a box drawn with it, '
                                        'stretched (a frame)'),
         'font': Attr('str', None, doc='a .ttf, relative to the .q or a folder above it'),
         'size': Attr('int', 8, doc='the font size of its items, unless an item says otherwise'),
         'if': Attr('expr', None, doc='shown only while this is true')},
        parents=('scene',)),
    'table': Tag(
        'Rows from the state in the HUD, a line each, in columns: a squad, a league table, a shop, the '
        'best scores. source= is read every frame; each qg:column is an expression of the row (as=). '
        'With a monospaced font the columns line up as on a text screen.',
        {'source': Attr('expr', required=True, doc='a list: of records, numbers, texts'),
         'as': Attr('ident', required=True, doc='the name of the row in the columns\' expressions'),
         'rows': Attr('int', 0, doc='at most so many rows shown, from the first (0: all of them)')},
        parents=('hud',)),
    'column': Tag(
        'A column of a qg:table: its heading and, for each row, what it shows.',
        {'value': Attr('expr', required=True, doc='an expression of the row'),
         'label': Attr('str', '', doc='its heading (a table whose columns have none has no heading row)'),
         'width': Attr('int', 8, doc='how many characters wide: a longer text is cut, a shorter one padded'),
         'align': Attr('enum:left|right', 'left', doc='right: numbers'),
         'color': Attr('str', None, doc='#rrggbb, or an expression of the row giving one (red when negative)')},
        parents=('table',)),
    'icon': Tag(
        'A picture in the HUD: a frame of a sheet (a heart before the hearts, a logo on a title).',
        {'sheet': Attr('ident', required=True, doc='a qg:spritesheet or qg:tileset'),
         'frame': Attr('expr', '0', doc='a frame of it, or an expression read every frame'),
         'scale': Attr('float', 1.0, doc='how large: 2 is twice its size')},
        parents=('hud',)),
    'counter': Tag(
        'A number from the scene state, or how many of an item the players hold, in the HUD.',
        {'bind': Attr('ident', None, doc='a q:set of the scene or the game (or item=)'),
         'item': Attr('ident', None, doc='a qg:item: how many are held (or bind=)'),
         'label': Attr('str', '', doc='text before the number'),
         'size': Attr('int', None, doc='font size'),
         'color': Attr('color', None, doc='its colour (#rrggbb)')},
        parents=('hud',)),
    'text': Tag(
        'A string from the scene state, in the HUD.',
        {'bind': Attr('ident', None, doc='a q:set of the scene (or value=)'),
         'value': Attr('expr', None, doc='an expression, read every frame (or bind=)'),
         'size': Attr('int', None, doc='font size'),
         'color': Attr('str', None, doc='its colour: #rrggbb, or an expression giving one, read every frame '
                                        '(red when a balance is below zero)')},
        parents=('hud',)),
    'on-collision': Tag(
        'What happens when this character or prefab touches something. Holds actions and statements; '
        '`me` is the toucher, `other` what it touched. In a prefab, only the game state is in reach.',
        {'with': Attr('ident', required=True, doc='the tag of what it touches'),
         'side': Attr('enum:any|top|bottom|left|right', 'any',
                      doc='top: landing on it; bottom: hitting it from below; left: hitting it from its left (it is '
                          'to the right); right: from its right. A side handler runs before the "any" one, which '
                          'then does not'),
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
    'label': Tag(
        'Text in the world, read every tick: over a character or a prefab, following it (a name over a player, '
        'what an enemy has left), or at a place of the scene (a sign). Only seen.',
        {'value': Attr('expr', required=True, doc='an expression; on a character or a prefab, `me` is it'),
         'x': Attr('float', None, doc='in a scene: where its middle is'),
         'y': Attr('float', None),
         'dx': Attr('float', 0.0, doc='on a character or a prefab: how far from its middle'),
         'dy': Attr('float', -12.0),
         'size': Attr('int', 8),
         'color': Attr('color', '#ffffff'),
         'if': Attr('expr', None, doc='placed only when this is true as the scene is built')},
        parents=('scene', 'character', 'prefab')),
    'light': Tag(
        'A light: a torch on a wall, a lantern a character carries, the glow of a gem. In a scene with ambient= it '
        'is what can be seen; elsewhere it brightens what it reaches. Only seen: the game\'s state never reads it.',
        {'x': Attr('float', None, doc='in a scene: where it is'),
         'y': Attr('float', None),
         'dx': Attr('float', 0.0, doc='on a character or a prefab: how far from its middle'),
         'dy': Attr('float', 0.0),
         'radius': Attr('float', 64.0, doc='how far it reaches, pixels'),
         'color': Attr('color', '#ffffff'),
         'energy': Attr('float', 1.0, doc='how bright: 1 as drawn, 2 twice'),
         'flicker': Attr('float', 0.0, doc='0 to 1: how much it flickers, as a flame does (the same in every replay)'),
         'shadows': Attr('bool', False, doc='the solid tiles of a scene with ambient= stop it, and cast shadows')},
        parents=('scene', 'character', 'prefab')),
    'when': Tag(
        'Runs its handler when a condition turns true: a wave beaten (`count(\'enemy\') == 0`), a room solved, a '
        'score reached. The condition is read at the start of every tick, from the scene\'s first, after the '
        'qg:afters due then (not while the scene is paused); the handler runs on the tick it is first true, and '
        'again only after it has been false. Holds actions and statements.',
        {'condition': Attr('expr', required=True, doc='an expression of the scene\'s state')},
        parents=('scene',)),
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
        'What happens when the player presses an action in this scene, or lets it go (on="release"); or, with '
        'sequence=, when a player presses several in order in a short time — a special move: "down, forward, '
        'punch" holds on the tick punch is pressed, if down and then forward were pressed before it within '
        'within= ticks (other presses between them do not matter, and the presses it uses are used up). '
        '"forward" and "back" are right and left as that player\'s character faces. Holds actions and statements.',
        {'action': Attr('ident', None, doc='a default action, or one a qg:input declares; or sequence='),
         'on': Attr('enum:press|release', 'press', doc='press: as it goes down; release: as it is let go'),
         'sequence': Attr('str', None, doc='actions in the order pressed, separated by commas; forward and back '
                                           'follow the way the player\'s character faces'),
         'within': Attr('int', 30, doc='sequence: how many ticks from its first press to its last (60 a second)'),
         'player': Attr('int', 1, doc='sequence: whose presses')},
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
    'behavior': Tag(
        'What a character controller="behavior" is made of: parts, each a small rule. A platformer is '
        'qg:gravity, qg:walk and qg:jump; a top-down walker is qg:walk axis="both"; a flapping bird is qg:gravity '
        'and a qg:jump with air=; a ship that comes back round the screen is qg:walk axis="both" and qg:wrap. '
        'Each tick, whatever their order: walk and jump read the keys, gravity pulls, the body moves, then '
        'keep-inside, wrap and face. `me.vx`, `me.vy` and `me.on_floor` read it; qg:velocity sets its speed '
        'from the game\'s rules (a dash, a knock-back), so what no part covers is written in the game. '
        'In a qg:prefab ai="behavior", an enemy\'s parts instead: what it moves by is the first of qg:seek, '
        'qg:flee, qg:keep-distance, qg:patrol, qg:wander and qg:stand, in their order, whose when= holds and '
        'that has something to do (a seek with nothing in sight has not); it stands when none has. Its '
        'qg:shoot parts fire besides. `me.doing` reads the part that moved it ("" for none). With qg:gravity '
        'the enemy walks on floors: the parts move it left and right only, a seek goes straight, the prefab\'s '
        'turns-at="edge" keeps it from walking off a ledge, and qg:leap jumps; `me.on_floor` reads whether it '
        'stands.',
        {},
        parents=('character', 'prefab')),
    'gravity': Tag(
        'A part: it falls, and stands on floors (without it, the body floats: top-down). A character\'s or an '
        'enemy\'s.',
        {'strength': Attr('float', 900.0, doc='pixels per second squared'),
         'max-fall': Attr('float', 300.0, doc='the speed it falls at most, pixels per second')},
        parents=('behavior',)),
    'walk': Tag(
        'A part: left and right (and up and down, with axis="both") set its speed.',
        {'speed': Attr('float', 90.0, doc='pixels per second'),
         'accel': Attr('float', 0.0, doc='pixels per second squared towards the speed (0: at once)'),
         'axis': Attr('enum:x|both', 'x', doc='x: across only (with gravity); both: in eight directions')},
        parents=('behavior',)),
    'jump': Tag(
        'A part: a press on the floor leaps; with air=, also in the air. It needs qg:gravity.',
        {'action': Attr('ident', 'jump', doc='a default action, or one a qg:input declares'),
         'height': Attr('float', 64.0, doc='pixels, with the button held'),
         'speed': Attr('float', None, doc='the take-off speed, pixels per second, instead of height='),
         'coyote': Attr('int', 6, doc='ticks after leaving a ledge in which a jump still works'),
         'buffer': Attr('int', 0, doc='a press up to this many ticks before landing jumps as it lands (0: only a '
                                      'press on the floor)'),
         'air': Attr('int', 0, doc='jumps it may take in the air before landing again'),
         'variable': Attr('bool', True, doc='letting go while rising cuts the leap'),
         'cut': Attr('float', 0.0, doc='letting go multiplies the rise by this, once (0: three times the '
                                       'gravity while it rises instead)'),
         'sound': Attr('ident', None, doc='a qg:sound, played on take-off')},
        parents=('behavior',)),
    'steer': Tag(
        'A part: left and right turn the body, up pushes it the way it points and down holds it back; it '
        'drifts, and slows by drag= on its own. Its picture turns with it. An Asteroids ship, a car seen from '
        'above, a horse. It needs no qg:walk.',
        {'turn': Attr('float', 180.0, doc='degrees a second'),
         'thrust': Attr('float', 200.0, doc='pixels per second, added every second up is held'),
         'drag': Attr('float', 1.0, doc='the part of its speed it loses every second on its own (0: none, it '
                                        'drifts for ever)'),
         'max': Attr('float', 160.0, doc='its top speed, pixels per second'),
         'heading': Attr('float', 0.0, doc='where it points at first, degrees: 0 right, 90 down')},
        parents=('behavior',)),
    'keep-inside': Tag(
        'A part: the scene\'s edges stop it.',
        {},
        parents=('behavior',)),
    'wrap': Tag(
        'A part: past an edge of the scene, it comes back on the other side.',
        {},
        parents=('behavior',)),
    'face': Tag(
        'A part: its picture turns left or right the way it goes.',
        {'by': Attr('enum:velocity|input', 'velocity', doc='velocity: the way it moves; input: the way it is '
                                                         'pushed (it faces while it walks into a wall)')},
        parents=('behavior',)),
    'seek': Tag(
        'An enemy\'s part: it goes for the nearest target it notices, around the walls by the shortest way over '
        'the tilemap\'s free cells (way="straight": straight at it).',
        {'target': Attr('str', None, doc='a character\'s id or a thing\'s tag; none: any character'),
         'sight': Attr('float', None, doc='pixels it notices a target within (else the prefab\'s sight=)'),
         'through-walls': Attr('bool', False, doc='it notices a target behind a solid tile (else only one it sees)'),
         'way': Attr('enum:around|straight', 'around'),
         'speed': Attr('float', None, doc='pixels per second (else the prefab\'s speed=)'),
         'when': Attr('expr', None, doc='only while this is true (`me` is the enemy)')},
        parents=('behavior',)),
    'flee': Tag(
        'An enemy\'s part: it runs from the nearest one it notices, straight away from it.',
        {'from': Attr('str', None, doc='a character\'s id or a thing\'s tag; none: any character'),
         'sight': Attr('float', None, doc='pixels (else the prefab\'s sight=)'),
         'through-walls': Attr('bool', False),
         'speed': Attr('float', None),
         'when': Attr('expr', None)},
        parents=('behavior',)),
    'keep-distance': Tag(
        'An enemy\'s part: it keeps between min= and max= pixels from the nearest one it notices: away when '
        'closer, towards it when farther, and still in between.',
        {'from': Attr('str', None, doc='a character\'s id or a thing\'s tag; none: any character'),
         'min': Attr('float', required=True),
         'max': Attr('float', required=True),
         'sight': Attr('float', None, doc='pixels (else the prefab\'s sight=)'),
         'through-walls': Attr('bool', False),
         'speed': Attr('float', None),
         'when': Attr('expr', None)},
        parents=('behavior',)),
    'patrol': Tag(
        'An enemy\'s part: to and fro along a line, turning at walls (and after distance= pixels).',
        {'heading': Attr('enum:left|right|up|down', None, doc='where it goes first (else the prefab\'s direction=)'),
         'distance': Attr('float', 0.0, doc='pixels before it turns (0: only at walls)'),
         'speed': Attr('float', None),
         'when': Attr('expr', None)},
        parents=('behavior',)),
    'wander': Tag(
        'An enemy\'s part: a new heading every 30 to 90 ticks (from the scene seed), and at once on bumping a wall.',
        {'speed': Attr('float', None),
         'when': Attr('expr', None)},
        parents=('behavior',)),
    'leap': Tag(
        'An enemy\'s part, with qg:gravity: it jumps, from the floor, when it bumps a wall as it walks (a step '
        'to climb) or while its when= holds; at most once every every= ticks.',
        {'height': Attr('float', 40.0, doc='pixels'),
         'at-wall': Attr('bool', True, doc='it jumps on bumping a wall as it walks'),
         'every': Attr('int', 30, doc='ticks between two leaps at least'),
         'sound': Attr('ident', None),
         'when': Attr('expr', None, doc='it jumps while this is true too (`me` is the enemy)')},
        parents=('behavior',)),
    'stand': Tag(
        'An enemy\'s part: it stands still; the parts after it wait.',
        {'when': Attr('expr', None)},
        parents=('behavior',)),
    'shoot': Tag(
        'An enemy\'s part: it fires prefab= at the nearest target within range=, headed at it, at most once '
        'every every= ticks. It shoots whatever part moves it.',
        {'prefab': Attr('ident', required=True, doc='what it fires: a prefab with ai="fly"'),
         'at': Attr('str', None, doc='a character\'s id or a thing\'s tag; none: any character'),
         'every': Attr('int', 60, doc='ticks between shots'),
         'range': Attr('float', 100.0, doc='pixels'),
         'through-walls': Attr('bool', False, doc='it fires at a target behind a solid tile (else only one it sees)'),
         'sound': Attr('ident', None),
         'when': Attr('expr', None)},
        parents=('behavior',)),
    'on-tile': Tag(
        'What happens while this character touches a tile of a kind (qg:tile kind=): stands on it, is in it, or '
        'bumps it. Holds actions and statements; `me` is the character. Without a cooldown, once as it comes to '
        'touch one; with one, again each time the cooldown runs out while it still does.',
        {'kind': Attr('enum:ladder|water|ice|hurt', required=True),
         'cooldown': Attr('int', 0, doc='ticks before it may run again while still touching')},
        parents=('character',)),
    'on-animation-end': Tag(
        'What happens when an animation of this character or prefab with loop="false" has played to its last '
        'frame. Holds actions and statements; `me` is whose animation it is.',
        {'name': Attr('ident', required=True, doc='the animation')},
        parents=('character', 'prefab')),
    'on-ko': Tag(
        'What happens when this fighter\'s health reaches 0. Holds actions and statements; `me` is the loser, '
        '`other` the winner.',
        {},
        parents=('character',)),
    'inventory': Tag(
        'In the HUD: the items held, each its picture (the qg:item\'s sheet= and frame=) and how many, in a row; '
        'an item held 0 times is not shown.',
        {'size': Attr('int', None, doc='the font size of the numbers')},
        parents=('hud',)),
    'bar': Tag(
        'A bar in the HUD: a number against its maximum — a q:set, or a fighter\'s health as `id.health`.',
        {'bind': Attr('str', required=True, doc='a q:set of the scene or the game, or a fighter\'s id and .health (p1.health)'),
         'max': Attr('float', 100.0),
         'width': Attr('int', 100), 'height': Attr('int', 10),
         'color': Attr('color', '#e04040')},
        parents=('hud',)),
    'on-locked': Tag(
        'What happens when a character bumps this prefab (opens-with=) without the item. Holds actions and '
        'statements; `me` is the locked thing, `other` the character.',
        {},
        parents=('prefab',)),
    # actions
    'give': Tag(
        'The players get some of an item (up to its max=).',
        {'item': Attr('ident', required=True, doc='a qg:item'),
         'amount': Attr('int', 1)},
        parents=('handler',)),
    'take': Tag(
        'The players spend some of an item (not below 0): a potion drunk, a key used.',
        {'item': Attr('ident', required=True, doc='a qg:item'),
         'amount': Attr('int', 1)},
        parents=('handler',)),
    'for-each': Tag(
        'Runs what it holds once for every thing of a tag in the scene, in the scene\'s order, with var= naming '
        'the thing: freeze every enemy, break the bricks near a bomb. The things are those there as it starts; '
        'one destroyed meanwhile is skipped.',
        {'tag': Attr('ident', required=True, doc='the things\' tag'),
         'var': Attr('ident', 'it', doc='the name of each thing in turn (a target=, an expression)')},
        parents=('handler',)),
    'camera-to': Tag(
        'The camera goes to a thing or a point, stays a while, and comes back to what it follows: a cutscene, a '
        'boss\'s entrance, the gate a lever opened. The scene waits meanwhile (unless pause="false"). The scene '
        'needs a qg:camera (in a q:function of the game, a scene without one is not shown anything).',
        {'target': Attr('ident', None, doc='me, other, a character or cursor id, or a parameter, loop variable or '
                                           'q:set holding a thing (or x= and y=)'),
         'x': Attr('expr', None), 'y': Attr('expr', None, doc='a point of the scene instead'),
         'zoom': Attr('float', None, doc='how close it goes (the camera\'s own when not given)'),
         'seconds': Attr('float', 0.6, doc='to go there, and as long to come back'),
         'hold': Attr('float', 1.0, doc='seconds it stays'),
         'pause': Attr('bool', True, doc='the scene waits while the camera is away')},
        parents=('handler',)),
    'attach': Tag(
        'A thing is carried by another: it goes where its carrier goes, dx,dy from it (a key over a head, a '
        'torch in a hand, a turret on a tank). While carried it touches nothing and nothing touches it, and it '
        'stands in no cell; `carrying(me, \'key\')` finds it.',
        {'target': Attr('ident', 'other', doc='what is carried: other, me, a character id, or a parameter, loop '
                                              'variable or q:set holding a thing'),
         'to': Attr('ident', 'me', doc='its carrier, the same'),
         'dx': Attr('float', 0.0), 'dy': Attr('float', -12.0, doc='from the carrier\'s middle')},
        parents=('handler',)),
    'detach': Tag(
        'A carried thing is put down where it is (qg:attach): it touches again.',
        {'target': Attr('ident', None, doc='what is put down (or from= and tag=)'),
         'from': Attr('ident', None, doc='the carrier: me, other, a character id...'),
         'tag': Attr('ident', None, doc='with from=: every thing of this tag it carries')},
        parents=('handler',)),
    'beam': Tag(
        'A line between two things for a while, following them as they move: a laser, a zap, a rope, an aiming '
        'line. Only seen.',
        {'from': Attr('ident', 'me', doc='me, other, a character or cursor id, or a parameter, loop variable or '
                                         'q:set holding a thing'),
         'to': Attr('ident', required=True, doc='the same'),
         'seconds': Attr('float', 0.1, doc='how long it shows'),
         'color': Attr('color', '#ffffff'),
         'width': Attr('float', 2.0, doc='pixels')},
        parents=('handler',)),
    'after': Tag(
        'Runs what it holds later, so many ticks (or seconds) after the handler reached it: a power-up that runs '
        'out, a bomb\'s fuse, a pause before the next serve. It counts the game\'s ticks, so a replay and every '
        'peer see the same; it waits while the scene is paused, and goes with the scene. The names it reads (me, '
        'other, a loop variable, a parameter) are what they were as it started; a thing gone by then is null, and '
        'an action on it does nothing.',
        {'ticks': Attr('expr', None, doc='how many ticks from now (60 a second)'),
         'seconds': Attr('expr', None, doc='or how many seconds, rounded to ticks'),
         'name': Attr('ident', None, doc='one of this name still waiting is replaced: the count starts again (a '
                                         'second power-up before the first runs out)')},
        parents=('handler',)),
    'time-scale': Tag(
        'Slow motion, or fast: the whole game runs at this speed — its ticks come further apart (or closer), '
        'each the same tick as ever, so a replay and every peer see the same game. The music is not slowed. A '
        'new scene starts at 1.',
        {'scale': Attr('float', required=True, doc='0.25: four times slower; 1: as usual; up to 4'),
         'seconds': Attr('float', 0.0, doc='seconds as the player sees them, then back to 1 (0: until another '
                                           'qg:time-scale)')},
        parents=('handler',)),
    'quit': Tag(
        'Ends the game: the window closes. In a browser there is nothing to quit to and it does nothing; '
        '`can_quit()` says whether it would.',
        {},
        parents=('handler',)),
    'watch': Tag(
        'Joins a networked game at an address with no seat, to watch it: the players\' inputs reach this '
        'machine too, and it runs the same game, its keys doing nothing. One who comes after the game has begun '
        'catches up on it first. `net_status()` is then "watching" and `net_player()` 0. Not under rollback=.',
        {'address': Attr('expr', required=True, doc='host:port, or a relay\'s wss:// room')},
        parents=('handler',)),
    'start-now': Tag(
        'The host starts the networked game with the players who are there, once qg:multiplayer\'s '
        'min-players= are (before that, and on the other machines, it does nothing). The lobby has a Start now '
        'button that does this.',
        {},
        parents=('handler',)),
    'reset-items': Tag(
        'A new game: every qg:item back to its start=, and the named things picked up or opened come back.',
        {},
        parents=('handler',)),
    'destroy': Tag(
        'Removes a thing from the scene.',
        {'target': Attr('ident', 'other', doc='other, me, or a q:set holding a thing (thing_at)')},
        parents=('handler',)),
    'bounce': Tag(
        'Throws the character up, as after a stomp.',
        {'target': Attr('enum:me', 'me'),
         'height': Attr('float', 32.0, doc='pixels')},
        parents=('handler',)),
    'play-animation': Tag(
        'Plays an animation of a thing or a character from its first frame. Its own animations (idle, walk...) '
        'wait until it ends; a looping one holds until the next qg:play-animation, and name="" gives it its own '
        'animations back.',
        {'target': Attr('ident', 'me', doc='me, other, a character id, or a q:set holding a thing'),
         'name': Attr('str', required=True, doc='an animation of the target (empty: back to its own)')},
        parents=('handler',)),
    'play': Tag(
        'Plays a qg:sound. Directly in a scene: as the scene is entered. With volume=, pitch= or vary=, it plays '
        'in a voice of its own, so the same sound can overlap itself. With sounds=, one of several, drawn each '
        'time (footsteps, hits that do not all sound alike). Only heard: the game\'s state records the sound\'s '
        'name (sounds= as written), never how it was played nor which one.',
        {'sound': Attr('ident', None, doc='a qg:sound; or sounds='),
         'sounds': Attr('str', None, doc='several qg:sounds, separated by commas: one of them each time'),
         'volume': Attr('float', 0.0, doc='decibels added (-6: about half as loud)'),
         'pitch': Attr('float', 1.0, doc='2: an octave up, 0.5: an octave down'),
         'vary': Attr('float', 0.0, doc='a random pitch between pitch - vary and pitch + vary, each time: '
                                        'twenty hits that do not sound the same'),
         'at': Attr('ident', None, doc='heard from where a thing is (me, other, a character id, or a parameter '
                                       'holding one): softer and to one side the farther it is from the middle of '
                                       'the screen, silent two screens away. A thing\'s own sounds (its fire-sound, '
                                       'a leap\'s or a shot\'s sound=) are heard where it is')},
        parents=('handler', 'scene')),
    'music': Tag(
        'The music of a scene: a looping qg:sound that plays while the scene is on. Going to a scene '
        'with other music crossfades from one to the other; a scene with the same music lets it play on; '
        'a scene with none fades it out. In a handler, it changes the music there and then, crossfading over '
        'fade= (a boss\'s theme as the fight starts, the scene\'s own back as it ends). Only heard, like a sound.',
        {'sound': Attr('ident', required=True, doc='a qg:sound with loop="true"'),
         'fade': Attr('float', 1.0, doc='seconds the crossfade takes'),
         'volume': Attr('float', 0.0, doc='decibels (0: as recorded; -6: half as loud)')},
        parents=('scene', 'handler')),
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
        {'target': Attr('ident', 'other', doc='other, me, or a parameter, loop variable or q:set holding a thing'),
         'axis': Attr('enum:x|y', None, doc='the axis to flip'),
         'dx': Attr('expr', None), 'dy': Attr('expr', None)},
        parents=('handler',)),
    'become': Tag(
        'Changes a character or a thing to one of its qg:states.',
        {'target': Attr('ident', 'me', doc='other, me, or a parameter, loop variable or q:set holding a thing'),
         'state': Attr('ident', required=True)},
        parents=('handler',)),
    'spawn': Tag(
        'Places a new prefab instance in the scene.',
        {'prefab': Attr('ident', required=True),
         'at': Attr('ident', 'other',
                    doc='whose position: other, me, a character id, or a parameter, loop variable or q:set holding '
                        'a thing; cursor: where the qg:on-select cursor is; path: the start of path='),
         'path': Attr('ident', None, doc='at="path": a qg:path of the scene, which an ai="path" prefab follows'),
         'x': Attr('expr', None, doc='a point of the scene instead of at= (with y=): an expression, in pixels'),
         'y': Attr('expr', None),
         'dx': Attr('float', 0.0), 'dy': Attr('float', 0.0, doc='offset in pixels'),
         'heading': Attr('str', None, doc='an ai="fly" prefab: the way it goes, as x,y, each an expression '
                                          '(`{aim.x - me.x},{aim.y - me.y}`: at the pointer), instead of its own')},
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
        {'target': Attr('ident', 'other', doc='other, me, or a parameter, loop variable or q:set holding a thing'),
         'amount': Attr('expr', '1')},
        parents=('handler',)),
    'burst': Tag(
        'A puff of particles where a thing is. Cosmetic.',
        {'at': Attr('ident', 'me', doc='other, me, or a parameter, loop variable or q:set holding a thing'),
         'color': Attr('color', '#ffffff'),
         'count': Attr('int', 12)},
        parents=('handler',)),
    'rumble': Tag(
        'A player\'s joypad shakes (and a phone, in the hand): a hit felt. Felt only, like a shake: nothing in the '
        'game depends on it. Over the network only the machine of that player\'s seat feels it; on one machine, '
        'player N\'s is the Nth joypad connected.',
        {'player': Attr('expr', '1', doc='whose joypad'),
         'strength': Attr('float', 0.5, doc='0 to 1'),
         'seconds': Attr('float', 0.2)},
        parents=('handler',)),
    'shake': Tag(
        'Shakes the scene a thing is in. Cosmetic.',
        {'at': Attr('ident', 'me', doc='other, me, or a parameter, loop variable or q:set holding a thing'),
         'frames': Attr('int', 10),
         'strength': Attr('float', 3.0, doc='pixels')},
        parents=('handler',)),
    'tween': Tag(
        'Eases a property of a thing from what it is to a value, over some seconds: a coin that rises, a door '
        'that slides, a pulse. It runs in the game\'s ticks, so a replay and every peer see the same; it stops '
        'while the scene is paused, and a new tween of the same property replaces it.',
        {'target': Attr('ident', 'me', doc='me, other, a character id, or a q:set holding a thing'),
         'property': Attr('enum:x|y|rotation|scale|scale-x|scale-y|alpha|tint', required=True,
                          doc='x, y: where it is (collisions see it); rotation (degrees), scale, scale-x and scale-y '
                              '(across and up: a squash, a stretch), alpha, tint (a colour its picture is multiplied '
                              'by: #ffffff is as drawn): its picture'),
         'to': Attr('expr', required=True, doc='a number, or for tint a colour (#rrggbb)'),
         'from': Attr('expr', None, doc='where it starts (what it is now when not given)'),
         'seconds': Attr('float', 0.5),
         'trans': Attr('enum:linear|sine|quad|cubic|back|bounce|elastic', 'sine', doc='the curve'),
         'ease': Attr('enum:in|out|in-out', 'out', doc='which end of the curve is slow'),
         'repeat': Attr('int', 0, doc='times it plays again (-1: for ever)'),
         'yoyo': Attr('bool', False, doc='each repeat goes back the other way')},
        parents=('handler',)),
    'travel': Tag(
        'A thing travels to a place by the cheapest way over the scene\'s qg:tilemap (qg:tile cost=), round the '
        'things and characters on it and where other travels end, a cell at a time: a unit of a tactics game. '
        'Its qg:on-end runs as it arrives (`me` the traveller); with no way, at once, where it is. In the game\'s '
        'ticks, so a replay and every peer see the same; a new travel of the same thing replaces it.',
        {'target': Attr('ident', 'me', doc='me, other, a parameter, a loop variable or a q:set holding a thing'),
         'to': Attr('expr', required=True, doc='a cursor (its cell), or a thing or character (up to it, beside it)'),
         'budget': Attr('expr', None, doc='how much of the way\'s cost it may spend: it stops where the next step '
                                          'would cost more (all the way when not given)'),
         'step': Attr('int', 10, doc='ticks a cell')},
        parents=('handler',)),
    'velocity': Tag(
        'Sets the speed of a character controller="behavior", in pixels per second: a dash, a knock-back, a '
        'wind, a spring. An axis not given keeps its speed. Its parts go on from there (gravity pulls it back '
        'down; walk sets the speed across again on the next tick, unless it has accel=).',
        {'target': Attr('ident', 'me', doc='me, other, or a character id'),
         'x': Attr('expr', None), 'y': Attr('expr', None)},
        parents=('handler',)),
    'set-tile': Tag(
        'Puts a tile in a cell of the scene\'s tilemap, or empties it: a block that breaks, a door drawn as tiles. '
        'Its collision changes from the next tick, monsters that pathfind find their way again, and the cells changed '
        'are part of the game\'s state (a replay, every peer). `tile_at(col, row)` reads a cell.',
        {'col': Attr('expr', required=True, doc='the column, from 0 at the left'),
         'row': Attr('expr', required=True, doc='the row, from 0 at the top'),
         'tile': Attr('expr', '0', doc='as in the rows of qg:tilemap: 0 nothing, n tile n-1 of the tileset, '
                      '-n the same flipped'),
         'layer': Attr('str', None, doc='a layer\'s name (a Tiled map\'s); the first with collision, else the '
                       'first, when not given')},
        parents=('handler',)),
    'emit': Tag(
        'Plays a qg:particles effect once where a thing is, or a text that floats up from it and fades (a '
        'damage number, +10). Only seen: the game\'s state never depends on it.',
        {'particles': Attr('ident', None, doc='the effect (or text=)'),
         'text': Attr('expr', None, doc='a text instead: "+10", or an expression (`{str(amount)}`)'),
         'color': Attr('color', '#ffffff', doc='the text\'s colour'),
         'size': Attr('int', 8, doc='the text\'s size'),
         'at': Attr('ident', 'me', doc='me, other, a character id, or a q:set holding a thing'),
         'dx': Attr('float', 0.0), 'dy': Attr('float', 0.0, doc='offset in pixels')},
        parents=('handler',)),
    'put': Tag(
        'Moves a thing or a character to a point, at once.',
        {'target': Attr('ident', 'other', doc='me, other, a character id, or a q:set holding a thing (thing_at)'),
         'x': Attr('expr', required=True), 'y': Attr('expr', required=True)},
        parents=('handler',)),
    'lobby': Tag(
        'The usual networked-game menu, ready made: play here (local=), host, an address field, join, cancel, '
        'and a line that says where things are. It is a qg:menu and a qg:hud the compiler writes; the address '
        'is the scene\'s `lobby_address`.',
        {'local': Attr('ident', None, doc='a scene to play on this machine alone (a button for it when given)'),
         'local-label': Attr('str', 'Play here'),
         'port': Attr('int', 7777),
         'address': Attr('str', '127.0.0.1:7777',
                         doc="what the address field starts with, unless the web page's address has ?join=..."),
         'font': Attr('str', None), 'size': Attr('int', 16),
         'options': Attr('ident', None, doc='a scene of the game\'s options (how loud, the full screen, the keys): '
                                            'an Options button goes there')},
        parents=('scene',)),
    'host': Tag(
        'Hosts the networked game (qg:multiplayer): this machine is player 1 and waits for the others; the game '
        'starts in the start= scene when they are all there. `net_status()` says where things are.',
        {'port': Attr('int', 7777)},
        parents=('handler',)),
    'join': Tag(
        'Joins a networked game at an address: host:port, or a quantum relay\'s room '
        '(wss://relay.example/pong/ROOM, where two browsers meet); this machine is the next player.',
        {'address': Attr('expr', required=True, doc='an expression: a q:set a qg:field fills, or text')},
        parents=('handler',)),
    'leave': Tag(
        'Leaves the networked game, or stops hosting or joining.',
        {},
        parents=('handler',)),
    'pause': Tag(
        'Pauses the scene: its characters, things, timers and spawners stop where they are. Menus, the HUD, '
        'the camera and qg:on-input go on, so a key or a button can resume it. `paused()` says whether it is.',
        {},
        parents=('handler',)),
    'resume': Tag(
        'Goes on with a paused scene.',
        {},
        parents=('handler',)),
    'say': Tag(
        'Opens a qg:dialogue of the scene: its lines one at a time, select for the next. The scene is paused '
        'while it is open (`talking()` says so); after the last line, its qg:on-end runs.',
        {'dialogue': Attr('ident', required=True)},
        parents=('handler',)),
    'goto-scene': Tag(
        'Leaves this scene for another, at the end of the tick. Scene state is lost; game state stays.',
        {'name': Attr('ident', required=True),
         'fade': Attr('float', 0.0, doc='seconds the new scene takes to come out of black (0: a cut); '
                      'only the picture fades, the game runs from its first tick as without it')},
        parents=('handler',)),
    'save': Tag(
        'Saves the game to continue it later: the game state (every q:set of q:application) and a scene to '
        'come back to. Kept between runs (in a browser, by the browser); a new qg:save replaces it. '
        '`has_save()` says whether there is one. A networked game is not saved.',
        {'scene': Attr('ident', None, doc='the scene to continue in (none: this one); it starts over, '
                       'what was in it is not saved'),
         'slot': Attr('expr', None, doc='which of several saves (1, 2, 3...: a game each); the scenes with '
                                        'save="true" save into it from then on. None: the one save')},
        parents=('handler',)),
    'next-language': Tag(
        'Shows the game in its next language (qg:language), after its own: a button for it is '
        '`<qg:button label="{tr(\'Language\') + \': \' + language()}">`. The choice is kept for the next run. '
        'Only what is shown changes.',
        {},
        parents=('handler',)),
    'continue': Tag(
        'Continues the saved game (qg:save): its game state back, and on to its scene. Nothing when there '
        'is no save.',
        {'slot': Attr('expr', None, doc='which save (qg:save slot=); the scenes with save="true" save into it '
                                        'from then on. None: the one save')},
        parents=('handler',)),
    'volume': Tag(
        'How loud a bus of the game\'s sounds is, from 0 (silent) to 100; kept between runs. `volume(\'music\')` '
        'reads it. Only heard.',
        {'bus': Attr('ident', required=True, doc='a bus of the game\'s sounds (qg:sound bus=)'),
         'value': Attr('expr', required=True, doc='0 to 100')},
        parents=('handler',)),
    'fullscreen': Tag(
        'The game fills the screen, or goes back to a window; kept between runs. `fullscreen()` reads it. In a '
        'browser, the page goes full screen.',
        {'on': Attr('expr', None, doc='true or false; none: the other of what it is')},
        parents=('handler',)),
    'touch-button': Tag(
        'A button on a touch screen that presses one of the game\'s actions while it is touched, as a key '
        'would (a replay and the lockstep see the action). In the application, every scene has it.',
        {'action': Attr('ident', required=True, doc='an action of the game'),
         'x': Attr('float', required=True), 'y': Attr('float', required=True, doc='its middle, on the screen'),
         'size': Attr('float', 32.0, doc='its width across, in pixels'),
         'label': Attr('str', '', doc='a letter or a word on it'),
         'player': Attr('int', 1, doc='whose action'),
         'show': Attr('enum:touch|always', 'touch', doc='touch: only on a device with a touch screen')},
        parents=('application', 'scene')),
    'touch-stick': Tag(
        'A stick on a touch screen: dragged from its middle, it presses left, right, up and down as far as it '
        'is pushed (strength()). In the application, every scene has it.',
        {'x': Attr('float', required=True), 'y': Attr('float', required=True, doc='its middle, on the screen'),
         'size': Attr('float', 56.0, doc='its width across, in pixels'),
         'player': Attr('int', 1, doc='whose directions'),
         'show': Attr('enum:touch|always', 'touch', doc='touch: only on a device with a touch screen')},
        parents=('application', 'scene')),
}

# q: statements the compiler reads itself (see model.py).
STATEMENTS = ('set', 'if', 'else', 'elseif', 'loop', 'function', 'return', 'call')
