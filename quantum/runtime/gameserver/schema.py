"""What a world's language is: every tag of a `q:application type="gameserver"`, its attributes, where it goes.

This table is the single source: the model validates a world against it, the reference page is generated from it,
and a tag with no entry does not exist (the Core used to drop a gameserver's children without a word). It holds
what has been built (PLAN_GAME_SERVER.md, Phases 1 to 4); the tags of the later phases come in with them. Attribute types:

- `ident`: a name (`[A-Za-z_][A-Za-z0-9_-]*`)
- `names`: names separated by commas (`dir, speed`)
- `text`: a string; `{...}` in it is an expression, read when it runs ("Welcome, {me.name}.")
- `value`: a number, true or false, or a text as written; or, all of it in braces, an expression (`{[]}`)
- `expr`: an expression, with or without its braces
- `place`: an area of the map by its name (`temple`), or an expression giving a tile or an entity
- `int`, `bool`, `number` (a whole number or not: 0.5)
- `range`: a whole number, or two with a dash between: `3`, `0-3`
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
    extra: Optional[str] = None      # what its other attributes are, when it takes any (q:entity: its fields)


HANDLERS = ('command', 'every', 'on-join', 'on-leave', 'on-death', 'function', 'if', 'elseif', 'else', 'loop')

TAGS: Dict[str, Tag] = {
    'gameserver': Tag(
        'A world, run by `quantum gameserver run`: its map, its entities, what each player may ask (q:command) '
        'and its rules (q:every, q:on-join). One in a q:application type="gameserver".',
        {'name': Attr('ident', required=True, doc='the world\'s name: its data directory, and what a client asks for'),
         'client': Attr('text', doc='the game the players run (its .q, next to this file)'),
         'tick': Attr('int', 10, doc='ticks a second: every command, every rule and every view runs on one'),
         'players': Attr('int', 500, doc='how many may be in the world at once; one more is told it is full'),
         'accounts': Attr('enum:guest|site', 'guest',
                          doc='who may come in: guest, anyone with a name; site, a site\'s account with its ticket '
                              '(signed with QUANTUM_WORLD_SECRET, from the environment: `quantum gameserver ticket`)')},
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
        ('gameserver',),
        extra='its fields, public, with their first values (hp="20" attack="3"): one that fights has hp, and with '
              'it max_hp (as hp, unless given) and target (none, \'\')'),
    'field': Tag(
        'A field of an entity: what it starts as, and who sees it. A private field goes only to the player whose '
        'entity it is; the others go to whoever sees the entity.',
        {'name': Attr('ident', required=True),
         'value': Attr('value', '', doc='its first value; `account` is the player\'s ({account.name})'),
         'private': Attr('bool', False)},
        ('entity', 'npc')),
    'brain': Tag(
        'What an entity of the world does by itself, as states (q:state): in each, a way to move (do=) and the '
        'conditions that change it (q:when). The world runs a brain a tick at a time, for the entities with a '
        'hero near (within 32 tiles); one with no hero near sleeps. Its entity has a public field `state`.',
        {}, ('entity',)),
    'state': Tag(
        'A state of a brain: what the entity does in it, read every tick (`it` is the entity). stand stays; '
        'wander steps now and then within within= tiles of where it was made; chase steps towards target= (and '
        'stops next to it); flee steps away from from=, for for= and then becomes then=. target= is kept in the '
        'entity\'s `target` (its id, or \'\' for none) every tick.',
        {'name': Attr('ident', required=True),
         'initial': Attr('bool', False, doc='the state it is made in (else the first)'),
         'do': Attr('enum:stand|wander|chase|flee', 'stand'),
         'within': Attr('int', 5, doc='wander: how far from home, in tiles'),
         'target': Attr('expr', doc='chase: an entity (or its id), or null'),
         'from': Attr('expr', doc='flee: an entity (or its id)'),
         'for': Attr('duration', doc='flee: how long, before then='),
         'then': Attr('ident', doc='flee: the state after for=')},
        ('brain',)),
    'when': Tag(
        'In a state: when the condition holds, the entity becomes another state (the first q:when that holds, '
        'each tick, before it moves).',
        {'condition': Attr('expr', required=True),
         'become': Attr('ident', required=True)},
        ('state',)),
    'loot': Tag(
        'In a q:entity: what it leaves when it is killed, its q:drops. In a block (of= and to=): the drops of an '
        'entity rolled, from the world\'s random, and given: an item to the receiver\'s `bag` (a record of counts), '
        'gold to its `gold` (the ledger of Phase 4 will keep them instead).',
        {'of': Attr('expr', doc='in a block: the entity whose loot it is'),
         'to': Attr('expr', doc='in a block: who gets it')},
        ('entity', 'handler')),
    'drop': Tag(
        'One thing of a loot: an item (so many, with a chance) or gold (so much).',
        {'item': Attr('ident', doc='its name'),
         'gold': Attr('range', doc='how much gold: 3, or 0-3'),
         'count': Attr('range', '1', doc='how many of the item: 1, or 1-3'),
         'chance': Attr('number', 1, doc='0 to 1')},
        ('loot',)),
    'spawn': Tag(
        'Entities of a kind kept in an area: made at the first tick, at walkable tiles of it no entity stands on, '
        'and each one killed made again respawn= later. In q:gameserver it lasts; in a block (a command), it makes '
        'count= more now, for for= if given.',
        {'entity': Attr('ident', required=True, doc='a q:entity of the world (not the players\')'),
         'area': Attr('ident', required=True, doc='an area of the map'),
         'count': Attr('int', 1),
         'night-count': Attr('int', doc='how many at night (q:clock)'),
         'respawn': Attr('duration', '60s', doc='how long after one is killed another is made'),
         'for': Attr('duration', doc='in a block: they go after so long')},
        ('gameserver', 'handler')),
    'kill': Tag(
        'An entity\'s end: the world\'s q:on-death for its kind run, then it goes (a player\'s stays: its '
        'q:on-death brings it back), and its q:spawn makes another respawn= later.',
        {'entity': Attr('expr', required=True),
         'by': Attr('expr', doc='who killed it: the on-death\'s by=')},
        ('handler',)),
    'on-death': Tag(
        'What happens when an entity of these kinds is killed (q:kill), before it goes: as= names it, by= its '
        'killer (null if none).',
        {'kind': Attr('names', required=True, doc='the kinds: Rat, Wolf'),
         'as': Attr('ident', 'it', doc='the name the block gives the killed one'),
         'by': Attr('ident', 'killer', doc='the name it gives the killer')},
        ('gameserver',)),
    'clock': Tag(
        'The world\'s day: so long a day, the last part of it night. `is_night()` and `daytime()` (0 to 1) read '
        'it, and a q:spawn\'s night-count= follows it.',
        {'day': Attr('duration', '60m'),
         'night': Attr('number', 0.25, doc='how much of a day is night: 0 to 1')},
        ('gameserver',)),
    'travel': Tag(
        'An entity on its way to a place, a step at a time at its speed, around the walls (the shortest way, '
        'within 40 tiles); a q:move or another q:travel of it ends the way.',
        {'entity': Attr('expr', required=True),
         'to': Attr('place', required=True)},
        ('handler',)),
    'currency': Tag(
        'A money of the world, kept by its ledger: a hero has it in a private field of its name (gold), which only '
        'q:give, q:take, q:pay and q:loot change (a q:set of it is refused), and the world counts what was made and '
        'spent of it, by where. The first currency is the one q:pay and q:give amount= pay in when none is named.',
        {'name': Attr('ident', required=True),
         'start': Attr('int', 0, doc='what a hero has of it when it is made')},
        ('gameserver',)),
    'item': Tag(
        'A thing of the world: a hero holds items in its private `bag` (a record of counts), which only the ledger '
        'changes. Its other attributes are what it is (price="40" heals="50" slot="weapon" attack="7"), read by '
        'price(), heals(), slot(), bonus() and item(). With one q:item, every item given, taken or dropped is one.',
        {'name': Attr('ident', required=True)},
        ('gameserver',),
        extra='what it is: numbers or texts, read by price(), heals(), slot(), bonus(item, name) and item(name)'),
    'give': Tag(
        'Something made for an entity: an item (count= of it) or an amount of a currency, counted by the ledger as '
        'made here.',
        {'to': Attr('expr', required=True),
         'item': Attr('expr', doc='the item\'s name (or amount=)'),
         'count': Attr('expr', '1'),
         'amount': Attr('expr', doc='of the currency (or item=)'),
         'currency': Attr('ident', doc='which (the first, if not given)')},
        ('handler',)),
    'take': Tag(
        'Something an entity has, taken and spent: an item (count=) or an amount. Not enough, and the command is '
        'refused (Not enough gold.).',
        {'from': Attr('expr', required=True),
         'item': Attr('expr'),
         'count': Attr('expr', '1'),
         'amount': Attr('expr'),
         'currency': Attr('ident')},
        ('handler',)),
    'pay': Tag(
        'An amount from one entity to another: nothing is made or spent. Not enough, and the command is refused.',
        {'from': Attr('expr', required=True),
         'to': Attr('expr', required=True),
         'amount': Attr('expr', required=True),
         'currency': Attr('ident')},
        ('handler',)),
    'chat': Tag(
        'The world\'s chat: commands `chat` (channel, text) and, with whisper=, `whisper` (to, text) every player may '
        'send, heard as the event `chat` ({channel, who, text}: who said it) by whom the channel reaches: say:7 is '
        'the players within 7 tiles, a channel with no number all of them, `party` the speaker\'s party. A line is cut at 200 '
        'characters and its words in the filter are starred; more than limit= of them and it is refused.',
        {'channels': Attr('text', 'say:7', doc='name:tiles, or name for the whole world, separated by commas'),
         'whisper': Attr('bool', False, doc='a line to one player, wherever they are'),
         'limit': Attr('rate', '3/5s', doc='lines a player may say'),
         'filter': Attr('text', 'moderate', doc='moderate (a short list of the worst words), none, or a file of '
                                                'words, one a line, next to the world')},
        ('gameserver',)),
    'say': Tag(
        'A line of the world itself in its chat (its who is "world"): to= one player\'s entity, or all.',
        {'channel': Attr('ident', 'system'),
         'to': Attr('expr', 'all', doc='an entity of a player, or all'),
         'text': Attr('text', required=True)},
        ('handler',)),
    'party': Tag(
        'Players who go together: commands `party-invite` (who), `party-accept` (who: the one who invited) and '
        '`party-leave`. A player\'s entity has a public field `party` (the party\'s id, \'\' for none); '
        'party_of(x) and party_near(x, n) read it, and a party\'s channel of the chat is its own.',
        {'size': Attr('int', 5, doc='how many at most')},
        ('gameserver',)),
    'trade': Tag(
        'A trade between two players, done whole or not at all: commands `trade-offer` (who, gold, items: a record '
        'of counts), `trade-accept` (who) and `trade-cancel` (who). When both accept the same offers, both sides '
        'move at once, on the ledger; a new offer takes back both acceptances. Each change is the event `trade` to '
        'both.',
        {}, ('gameserver',)),
    'quest': Tag(
        'A quest the world may give: what to do (goal= kill:Kind:n, or bring:item:n), from which level, and its '
        'reward (gold:60, xp:100, item:sword). A hero\'s quest is a field it has (quest: {name, done}); '
        'quest_goal(), quest_done(), quest_level() and quest_title() read it, and q:reward gives the reward.',
        {'name': Attr('ident', required=True),
         'title': Attr('text', required=True),
         'goal': Attr('text', required=True, doc='kill:Kind:n or bring:item:n'),
         'level': Attr('int', 1),
         'reward': Attr('text', '', doc='what it gives, separated by commas: a currency, item, or a field of the '
                                        'hero (xp) with its amount')},
        ('gameserver',)),
    'npc': Tag(
        'A character of the world with a mind: an entity (kind=, its fields as attributes or q:fields) made at '
        'the area at= when the world begins, whose words come from its q:agent. A player\'s q:ask gives it their '
        'words; the world goes on, the NPC is seen thinking (the event npc-thinking), and its answer comes some '
        'ticks later as the event npc-says ({npc, who, text}) to the asker and those near. What it does is its '
        'tools\' commands (by="npc"), whose q:requires hold whatever it was told. Without a mind, out of budget '
        'or too slow, it says a line of its q:fallback. The answer is kept in the log: a replay asks no model.',
        {'name': Attr('ident', required=True),
         'kind': Attr('text', required=True, doc='what the game draws it as: a qg:prefab of the client'),
         'at': Attr('text', required=True, doc='the area of the map where it stands')},
        ('gameserver',),
        extra='its fields, as q:entity\'s (title="Old Marta")'),
    'agent': Tag(
        'An NPC\'s mind: its q:instruction (who it is), its q:tools (the commands it may run), what it knows '
        '(knowledge=, a q:knowledge of the world) and remembers of each player (memory=), and how many questions a '
        'player may ask it a day (budget=, the world\'s day with a q:clock, else 24 hours).',
        {'model': Attr('text', 'small', doc='the model: small is the environment\'s QUANTUM_NPC_MODEL, else the '
                                            'Core\'s default; any other is a model\'s name'),
         'knowledge': Attr('ident', None, doc='a q:knowledge of the world: the texts it may read'),
         'memory': Attr('enum:per-player|none', 'per-player', doc='per-player: a short note of each player, kept '
                                                                   'with the hero (persist="true": the next day too)'),
         'budget': Attr('text', '40/day', doc='questions a player may ask it a day; one more is a fallback line'),
         'maxIterations': Attr('int', 3, doc='tools it may run in one answer')},
        ('npc',)),
    'instruction': Tag(
        'Who the NPC is and how it speaks: the text of its agent\'s instruction.',
        {}, ('agent',), text='the instruction'),
    'tool': Tag(
        'A tool of an NPC\'s agent: a command of the world with by="npc", which the agent may run as the player '
        'it talks to, with the arguments it chooses; the command\'s q:requires decide, not the model.',
        {'command': Attr('ident', required=True),
         'description': Attr('text', '', doc='what the agent is told it does')},
        ('agent',)),
    'fallback': Tag(
        'What an NPC says with no mind to answer: no model, out of budget, or too slow. Its q:lines, one at '
        'random (the world\'s random).',
        {}, ('npc',)),
    'line': Tag(
        'A line of an NPC\'s q:fallback.',
        {'text': Attr('text', required=True)},
        ('fallback',)),
    'knowledge': Tag(
        'Texts the world\'s NPCs may read (the town\'s story): its q:sources, read as the world is loaded.',
        {'name': Attr('ident', required=True)},
        ('gameserver',)),
    'source': Tag(
        'Where a q:knowledge\'s texts are: a directory (its files of pattern=) or a file, next to the world.',
        {'type': Attr('enum:directory|file', 'directory'),
         'path': Attr('text', required=True),
         'pattern': Attr('text', '*.md')},
        ('knowledge',)),
    'ask': Tag(
        'A player\'s words to an NPC (in a command): it is seen thinking, and answers some ticks later, off the '
        'tick (q:npc). Refused when the command is.',
        {'npc': Attr('expr', required=True, doc='the NPC (an entity, or its id)'),
         'text': Attr('expr', required=True, doc='what the player says')},
        ('handler',)),
    'reward': Tag(
        'A quest\'s reward, given: its currency and items by the ledger, its other parts added to the hero\'s fields '
        '(xp:100 to its xp). A quest to bring things takes them: the five furs go, spent where the reward is given.',
        {'to': Attr('expr', required=True),
         'quest': Attr('expr', required=True)},
        ('handler',)),
    'command': Tag(
        'What a player may ask the world, by its name and with its params (the client\'s qg:send). It runs whole or '
        'not at all, as the player who sent it (`me`, their entity): a q:require that does not hold, an argument '
        'that is not one of params=, a command sent faster than limit=, or an expression that fails, and nothing '
        'it did stays; the player is told why.',
        {'name': Attr('ident', required=True),
         'params': Attr('names', '', doc='the arguments it takes: no other, none missing'),
         'limit': Attr('rate', doc='at most so many a player (8/s, 1/3s): one more is refused'),
         'predict': Attr('bool', False, doc='the game shows it at once, before the world says yes: a command '
                                            'whose body is q:requires and one q:move of me to ahead(me, a '
                                            'param); a refusal walks the hero back'),
         'by': Attr('enum:npc', None, doc='npc: only an NPC\'s agent runs it (a q:tool), as the player it talks to '
                                          '(`me`), the NPC being `npc`; a player who sends it is refused')},
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
    'view': Tag(
        'What each player sees of the world, by its name (the game\'s qg:mirror view=): the entities for which '
        'where= holds, with `it` the entity and `me` the player\'s. Only what changes in it goes to the player: what '
        'came into it, the fields that changed (the public ones, and its own entity\'s private ones) and what left. '
        'A where= of near(it, me, n), alone or with `and` more, reads only the cells of the world\'s index around '
        'the player; any other reads every entity, for a small world. A world with no q:view has one, `world`: '
        'everything.',
        {'name': Attr('ident', required=True),
         'where': Attr('expr', doc='which entities it holds (all of them if not given); read again when the entity '
                                   'or the player\'s changes')},
        ('gameserver',)),
    'emit': Tag(
        'An event: something that happened, sent with the tick to whoever sees where it happened (the game\'s '
        'qg:on-event name=), and kept nowhere. At a tile or an entity (at=), it goes to the players within reach of '
        'their views (a near() view\'s n; a view of the whole world reaches everywhere); to= one player\'s entity, to '
        'that player; neither, to everyone. It is the command\'s: a command refused emits nothing.',
        {'event': Attr('ident', required=True, doc='its name'),
         'value': Attr('value', '', doc='what it carries: a number, a text, a record'),
         'at': Attr('place', doc='where: an area, a tile or an entity (the event says its id: `of`)'),
         'to': Attr('expr', doc='a player\'s entity: the event is theirs alone')},
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
