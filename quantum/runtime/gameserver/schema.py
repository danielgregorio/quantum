"""What a world's language is: every tag of a `q:application type="gameserver"`, its attributes, where it goes.

This table is the single source: the model validates a world against it, the reference page is generated from it,
and a tag with no entry does not exist (the Core used to drop a gameserver's children without a word). It holds
what has been built (PLAN_GAME_SERVER.md, Phase 1); the tags of the later phases come in with them. Attribute types:

- `ident`: a name (`[A-Za-z_][A-Za-z0-9_-]*`)
- `names`: names separated by commas (`dir, speed`)
- `text`: a string; `{...}` in it is an expression, read when it runs ("Welcome, {me.name}.")
- `value`: a number, true or false, or a text as written; or, all of it in braces, an expression (`{[]}`)
- `expr`: an expression, with or without its braces
- `place`: an area of the map by its name (`temple`), or an expression giving a tile or an entity
- `int`, `bool`
- `rate`: so many in so long: `8/s`, `1/3s`, `30/m`
- `duration`: `500ms`, `2s`, `5m`, `1h`
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
    # Which tags may hold it: 'application' is the q:application, 'handler' any block of statements (a command,
    # q:every, q:on-join, q:on-leave, a q:function, and q:if, q:elseif, q:else and q:loop inside them).
    parents: Tuple[str, ...] = ()
    text: Optional[str] = None


HANDLERS = ('command', 'every', 'on-join', 'on-leave', 'function', 'if', 'elseif', 'else', 'loop')

TAGS: Dict[str, Tag] = {
    'gameserver': Tag(
        'A world, run by `quantum gameserver run`: its map, its entities, what each player may ask (q:command) '
        'and its rules (q:every, q:on-join). One in a q:application type="gameserver".',
        {'name': Attr('ident', required=True, doc='the world\'s name: its data directory, and what a client asks for'),
         'client': Attr('text', doc='the game the players run (its .q, next to this file)'),
         'tick': Attr('int', 10, doc='ticks a second: every command, every rule and every view runs on one'),
         'players': Attr('int', 500, doc='how many may be in the world at once; one more is told it is full'),
         'accounts': Attr('enum:guest', 'guest',
                          doc='who may come in: guest, anyone with a name (the site\'s accounts are Phase 4)')},
        ('application',)),
    'map': Tag(
        'The world\'s map: a Tiled file the game draws too, so the walls the player sees are the walls the server '
        'keeps. Its walls are the tiles of its layers with the collision property (or of the layer walls= names); '
        'its areas are its zones (a rectangle of class zone), by their names: where q:move sends an entity.',
        {'name': Attr('ident', required=True),
         'tiled': Attr('text', required=True, doc='the .tmx, next to this file'),
         'walls': Attr('text', '', doc='the tile layer of the walls (else every layer with collision)')},
        ('gameserver',)),
    'entity': Tag(
        'A kind of thing in the world. Each one has an `id`, its `kind` (the prefab the game draws it as), its '
        'tile `at` ({x, y}; null until it is put somewhere) and `facing`, and the fields declared in it. With '
        'per-player="true" it is a player\'s: one is made for each player that comes in (`me` in the player\'s '
        'commands), and with persist="true" it is kept while the player is away and comes back with them.',
        {'name': Attr('ident', required=True),
         'kind': Attr('text', required=True, doc='what the game draws it as: a qg:prefab of the client'),
         'per-player': Attr('bool', False),
         'persist': Attr('bool', False, doc='kept between a player\'s sessions (with per-player)'),
         'speed': Attr('rate', '4/s', doc='steps a second: a step (a q:move to a tile next to it) takes so long, '
                                          'and another waits for it')},
        ('gameserver',)),
    'field': Tag(
        'A field of an entity: what it starts as, and who sees it. A private field goes only to the player whose '
        'entity it is; the others go to whoever sees the entity.',
        {'name': Attr('ident', required=True),
         'value': Attr('value', '', doc='its first value; `account` is the player\'s ({account.name})'),
         'private': Attr('bool', False)},
        ('entity',)),
    'command': Tag(
        'What a player may ask the world, by its name and with its params (the client\'s qg:send). It runs whole or '
        'not at all, as the player who sent it (`me`, their entity): a q:require that does not hold, an argument '
        'that is not one of params=, a command sent faster than limit=, or an expression that fails, and nothing '
        'it did stays; the player is told why.',
        {'name': Attr('ident', required=True),
         'params': Attr('names', '', doc='the arguments it takes: no other, none missing'),
         'limit': Attr('rate', doc='at most so many a player (8/s, 1/3s): one more is refused')},
        ('gameserver',)),
    'require': Tag(
        'A condition the command needs: if it does not hold, the command is refused, with else= as the reason.',
        {'condition': Attr('expr', required=True),
         'else': Attr('text', 'Not allowed.', doc='what the player is told')},
        ('handler',)),
    'move': Tag(
        'An entity to a tile, to another entity\'s tile or to an area of the map (to its middle, or the walkable tile '
        'nearest it). A move to a tile next to it is a step: it faces that way, it takes its speed=, and a step '
        'before the last one ended is refused.',
        {'entity': Attr('expr', required=True),
         'to': Attr('place', required=True)},
        ('handler',)),
    'every': Tag(
        'A rule that runs every so often, for the whole world (on the ticks the interval divides). An expression that '
        'fails undoes the rule\'s run and is kept in the world\'s errors; the world goes on.',
        {'interval': Attr('duration', required=True)},
        ('gameserver',)),
    'on-join': Tag('What happens when a player comes into the world: `me` is their entity (made, or brought back).',
                   {}, ('gameserver',)),
    'on-leave': Tag('What happens when a player leaves (or loses the connection), before their entity goes.',
                    {}, ('gameserver',)),
    'set': Tag(
        'Directly in q:gameserver, a variable of the world, kept with it. In a block, a value to a name: a field of '
        'an entity (`me.level`), a variable of the world, or else a variable of the block.',
        {'name': Attr('text', required=True),
         'value': Attr('value', '')},
        ('gameserver', 'handler')),
    'if': Tag('Runs what it holds when the condition holds; else its first q:elseif that does, or its q:else.',
              {'condition': Attr('expr', required=True)}, ('handler',)),
    'elseif': Tag('Inside a q:if: what runs when the q:if\'s condition does not hold and this one does.',
                  {'condition': Attr('expr', required=True)}, ('if',)),
    'else': Tag('Inside a q:if: what runs when no condition held.', {}, ('if',)),
    'loop': Tag(
        'Runs what it holds for each item of a list (items=, as var=), or for each number from from= to to=.',
        {'var': Attr('ident', required=True),
         'items': Attr('expr'),
         'from': Attr('expr'),
         'to': Attr('expr'),
         'index': Attr('ident', doc='the position, from 0, of a list\'s item')},
        ('handler',)),
    'function': Tag(
        'A function of the world: called by q:call or from an expression (`{level_of(me)}`), with what q:return '
        'gives. It runs inside whatever called it, so a command\'s function is undone with the command.',
        {'name': Attr('ident', required=True),
         'params': Attr('names', '')},
        ('gameserver',)),
    'call': Tag('Runs a q:function: args= are its arguments, expressions separated by commas.',
                {'function': Attr('ident', required=True),
                 'args': Attr('text', '')},
                ('handler',)),
    'return': Tag('Ends a q:function with its value.', {'value': Attr('value', '')}, ('handler',)),
}
