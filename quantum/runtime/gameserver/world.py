"""A world's state, a tick at a time.

`World.step(inputs)` is one tick: the players who came and went and the commands they sent, in the order they
arrived, then the rules whose interval the tick falls on. It touches nothing but its own state and its seeded
random, so the same snapshot and the same inputs give the same world: the log replays it, and a test is a list of
inputs. What a player sees of it (`public`, and the views: `members`, `sees`) is the server's to send; the index
of the world's cells (16 tiles a side) is how a view near a player reads only the entities around them.
"""

from __future__ import annotations

import copy
import hashlib
import json
import random
from collections import ChainMap
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from quantum.core.expressions import ExpressionError
from quantum.runtime.gameserver.errors import Refused, RuleError
from quantum.runtime.gameserver.life import MISSING, Life
from quantum.runtime.gameserver.model import EntityDef, ViewDef, WorldDef
from quantum.runtime.gameserver.rules import Interpreter, chebyshev, facing_of

_MISSING = MISSING
MAX_ARGS = 2048          # the size of a command's arguments, as JSON
MAX_ERRORS = 100
MAX_EVENTS = 10_000      # q:emit in a tick
CELL = 16                # the side of a cell of the index, in tiles


@dataclass
class Event:
    """What a q:emit said: the event as it is sent, where it happened, and to whom it goes."""
    message: dict
    tile: Optional[Tuple[int, int]]
    to: Optional[str]                    # an account: theirs alone
    everyone: bool                       # neither at= nor to=


@dataclass
class TickOut:
    tick: int
    entries: List[dict] = field(default_factory=list)                       # what the log keeps, in order
    acks: Dict[str, List[int]] = field(default_factory=dict)                 # account: the seqs that ran
    refused: Dict[str, List[dict]] = field(default_factory=dict)             # account: {seq, name, reason}
    joined: Dict[str, str] = field(default_factory=dict)                     # account: its entity's id
    left: List[str] = field(default_factory=list)
    full: List[str] = field(default_factory=list)                            # who found the world full


def plain(value: Any, depth: int = 0) -> Any:
    """A value as the world keeps it: numbers, texts, true, false, null, lists and records of them (a tuple is a
    list); anything else is not a world's."""
    if depth > 16:
        raise RuleError('a value nested more than 16 deep')
    if value is None or isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, float):
        if value != value or value in (float('inf'), float('-inf')):
            raise RuleError(f'{value} is not a number a world keeps')
        return value
    if isinstance(value, (list, tuple)):
        return [plain(v, depth + 1) for v in value]
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if not isinstance(k, str):
                raise RuleError(f'a record\'s keys are texts, not {type(k).__name__}')
            out[k] = plain(v, depth + 1)
        return out
    raise RuleError(f'a {type(value).__name__} is not a value a world keeps')


def _args_ok(value: Any, depth: int = 0) -> bool:
    if value is None or isinstance(value, (bool, int, float, str)):
        return not (isinstance(value, float) and (value != value or value in (float('inf'), float('-inf'))))
    if depth >= 2:
        return False
    if isinstance(value, list):
        return all(_args_ok(v, depth + 1) for v in value)
    if isinstance(value, dict):
        return all(isinstance(k, str) and _args_ok(v, depth + 1) for k, v in value.items())
    return False


class World(Life):
    def __init__(self, definition: WorldDef, seed: int = 0):
        self.definition = definition
        self.tick = 0
        self.vars: Dict[str, Any] = {}
        self.entities: Dict[str, dict] = {}
        self.stored: Dict[str, dict] = {}          # account: its entity while the player is away (persist)
        self.players: Dict[str, str] = {}          # account: its entity's id, while in the world
        self.rng = random.Random(seed)
        self.rates: Dict[str, List[int]] = {}      # account and command: the ticks it ran on, lately
        self.counters: Dict[str, int] = {}
        self.errors: List[dict] = []
        self.journal: Optional[List[Tuple[dict, str, Any]]] = None
        self.dirty: set = set()                    # entities changed this tick
        self.gone: set = set()                     # entities that left the world this tick
        self.events: List[Event] = []              # what q:emit said this tick
        self.vars_changed = False                  # a variable of the world was written this tick
        self.cells: Dict[Tuple[int, int], Set[str]] = {}       # the index: a cell, the entities on its tiles
        self.cell_of: Dict[str, Tuple[int, int]] = {}
        self._events_mark = 0
        # Phase 3: what each q:spawn keeps (its living, and the ticks when the next are due), the entities made for
        # a while (q:spawn for=) and those on their way (q:travel)
        self.spawned: Dict[str, Dict[str, list]] = {str(i): {'alive': [], 'due': []}
                                                    for i in range(len(definition.spawns))}
        self.expiring: Set[str] = set()
        self.travelers: Set[str] = set()
        self.dying: Set[str] = set()
        self.rules = Interpreter(self)
        self._private = {name: {f.name for f in e.fields if f.private} for name, e in definition.entities.items()}
        for name, value, line in definition.variables:
            self.vars[name] = plain(self.rules.value(value, {}, line))

    # -- reading -----------------------------------------------------------------------------------------------

    def is_entity(self, x: Any) -> bool:
        return isinstance(x, dict) and isinstance(x.get('id'), str) and self.entities.get(x['id']) is x

    def entity_of(self, x: Any, line: Optional[int]) -> dict:
        if isinstance(x, str) and x in self.entities:
            return self.entities[x]
        if not self.is_entity(x):
            raise RuleError('q:move entity= is not an entity of the world', line)
        return x

    def tile_of(self, x: Any) -> Optional[Tuple[int, int]]:
        """A tile ({x, y}, or [x, y]), an entity's tile, or the tile of the entity of that id."""
        if isinstance(x, str):
            x = self.entities.get(x)
        if isinstance(x, dict):
            if 'id' in x and 'at' in x:
                x = x['at']
            if isinstance(x, dict) and isinstance(x.get('x'), (int, float)) and isinstance(x.get('y'), (int, float)):
                return int(x['x']), int(x['y'])
            return None
        if isinstance(x, (list, tuple)) and len(x) == 2 and all(isinstance(v, (int, float)) for v in x):
            return int(x[0]), int(x[1])
        return None

    def walkable(self, tile: Tuple[int, int]) -> bool:
        m = self.definition.map
        return 0 <= tile[0] < m.width and 0 <= tile[1] < m.height and tile not in m.walls

    def area_tile(self, name: str, line: Optional[int]) -> Tuple[int, int]:
        """An area's middle, or the walkable tile of it nearest the middle."""
        x0, y0, x1, y1 = self.definition.map.areas[name]
        middle = ((x0 + x1) // 2, (y0 + y1) // 2)
        tiles = sorted(((x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)),
                       key=lambda t: (chebyshev(t, middle), t[1], t[0]))
        for t in tiles:
            if self.walkable(t):
                return t
        raise RuleError(f'the area {name!r} has no tile one can stand on', line)

    def public(self, entity: dict, viewer: Optional[str]) -> dict:
        """What a player sees of an entity: none of the world's own fields (_...), and its private ones only if it
        is the player's."""
        private = () if entity.get('_player') == viewer else self._private.get(entity.get('_type'), ())
        return {k: v for k, v in entity.items() if not k.startswith('_') and k not in private}

    # -- the index, and the views ------------------------------------------------------------------------------

    def reindex(self, ids: Iterable[str]) -> None:
        """The cells of these entities, as they are now (one that left the world, or is nowhere, is in none)."""
        for eid in ids:
            entity = self.entities.get(eid)
            tile = self.tile_of(entity) if entity is not None else None
            cell = (tile[0] // CELL, tile[1] // CELL) if tile else None
            old = self.cell_of.get(eid)
            if old == cell:
                continue
            if old is not None:
                members = self.cells[old]
                members.discard(eid)
                if not members:
                    del self.cells[old]
                del self.cell_of[eid]
            if cell is not None:
                self.cells.setdefault(cell, set()).add(eid)
                self.cell_of[eid] = cell

    @staticmethod
    def cells_near(tile: Tuple[int, int], n: int) -> List[Tuple[int, int]]:
        """The cells that a square of n tiles around the tile touches."""
        return [(cx, cy) for cx in range((tile[0] - n) // CELL, (tile[0] + n) // CELL + 1)
                for cy in range((tile[1] - n) // CELL, (tile[1] + n) // CELL + 1)]

    def near_ids(self, tile: Tuple[int, int], n: int) -> List[str]:
        """The entities of the cells that a square of n tiles around the tile touches (some farther than n)."""
        out: List[str] = []
        for cell in self.cells_near(tile, n):
            members = self.cells.get(cell)
            if members:
                out.extend(members)
        return out

    def sees(self, view: ViewDef, entity: dict, me: dict) -> bool:
        """The entity is in the player's view. A where= that fails is kept in the errors, and sees nothing."""
        if view.radius is not None:
            a, b = self.tile_of(entity), self.tile_of(me)
            if a is None or b is None or chebyshev(a, b) > view.radius:
                return False
            if not view.rest:
                return True
        if view.where is None:
            return True
        try:
            return bool(self.rules.reader.evaluate(view.where, ChainMap({'it': entity, 'me': me}, self.vars)))
        except ExpressionError as e:
            self._error(f'q:view {view.name}', RuleError(str(e), view.line))
            return False

    def members(self, view: ViewDef, me: dict) -> Set[str]:
        """The ids of what the player sees in the view."""
        if view.radius is not None:
            tile = self.tile_of(me)
            ids: Iterable[str] = self.near_ids(tile, view.radius) if tile else ()
        else:
            ids = self.entities
        return {eid for eid in ids if self.sees(view, self.entities[eid], me)}

    # -- writing, as a transaction -----------------------------------------------------------------------------

    def write(self, target: dict, key: str, value: Any, root: Optional[dict], line: Optional[int]) -> None:
        try:
            value = plain(value)
        except RuleError as e:
            raise RuleError(e.message, line)
        if self.journal is not None:
            self.journal.append((target, key, target.get(key, _MISSING)))
        target[key] = value
        owner = root if root is not None else target
        if self.is_entity(owner):
            self.dirty.add(owner['id'])
        elif owner is self.vars or any(owner is v for v in self.vars.values()):
            self.vars_changed = True

    def emit(self, name: str, value: Any, tile: Optional[Tuple[int, int]], of: Optional[str], to: Optional[str],
             everyone: bool, line: Optional[int]) -> None:
        if len(self.events) >= MAX_EVENTS:
            raise RuleError(f'q:emit: more than {MAX_EVENTS} events in a tick', line)
        try:
            message = {'name': name, 'value': plain(value)}
        except RuleError as e:
            raise RuleError(e.message, line)
        if tile is not None:
            message['at'] = {'x': tile[0], 'y': tile[1]}
        if of is not None:
            message['of'] = of
        self.events.append(Event(message, tile, to, everyone))

    def _begin(self) -> None:
        self.journal = []
        self._events_mark = len(self.events)

    def _commit(self) -> None:
        self.journal = None

    def _rollback(self) -> None:
        touched = set()
        for target, key, old in reversed(self.journal or []):
            if old is _MISSING:
                target.pop(key, None)
            else:
                target[key] = old
            if target is self.entities:
                touched.add(key)
            elif isinstance(target, dict) and isinstance(target.get('id'), str):
                touched.add(target['id'])
        self.journal = None
        del self.events[self._events_mark:]
        self.gone = {g for g in self.gone if g not in self.entities}
        self.reindex(touched)                  # an entity undone where it was, made or gone again
        for eid in touched:
            entity = self.entities.get(eid)
            for kept, key in ((self.travelers, '_path'), (self.expiring, '_expires')):
                if entity is not None and entity.get(key):
                    kept.add(eid)
                else:
                    kept.discard(eid)

    def put(self, container: dict, key: str, value: Any) -> None:
        """A key of a container of the world set (or, with _MISSING, taken out), as a transaction's: undone with it."""
        if self.journal is not None:
            self.journal.append((container, key, container.get(key, _MISSING)))
        if value is _MISSING:
            container.pop(key, None)
        else:
            container[key] = value

    def _error(self, where: str, e: RuleError) -> None:
        self.errors.append({'tick': self.tick, 'where': where, 'line': e.line, 'message': e.message})
        del self.errors[:-MAX_ERRORS]

    # -- what the world does -----------------------------------------------------------------------------------

    def move(self, entity: dict, to: Tuple[int, int], line: Optional[int]) -> None:
        """An entity to a tile: never into a wall; a step (to a tile next to it) faces that way, takes the entity's
        speed, and waits for the last one to end."""
        if not self.walkable(to):
            raise Refused('Blocked.')
        here = self.tile_of(entity)
        if here is not None and chebyshev(here, to) == 1:
            if entity.get('_until', 0) > self.tick:
                raise Refused('Still moving.')
            spec = self.definition.entities[entity['_type']]
            self.write(entity, '_until', self.tick + spec.step_ticks, None, line)
            self.write(entity, 'facing', facing_of(here, to), None, line)
        self.write(entity, 'at', {'x': to[0], 'y': to[1]}, None, line)
        self.reindex([entity['id']])           # the index follows at once: a brain moving next sees it

    def make(self, spec: EntityDef, account: Optional[str] = None) -> dict:
        if spec.per_player:
            eid = f'{spec.name}:{account}'
        else:
            self.counters[spec.name] = self.counters.get(spec.name, 0) + 1
            eid = f'{spec.name}-{self.counters[spec.name]}'
        entity = {'id': eid, 'kind': spec.kind, 'at': None, 'facing': 'south',
                  '_type': spec.name, '_player': account, '_until': 0}
        scope = {'account': {'name': account, 'id': account}}
        for f in spec.fields:
            entity[f.name] = plain(self.rules.value(f.value, scope, f.line))
        if spec.states:
            entity['state'] = spec.initial
            entity['_since'] = self.tick
        return entity

    def _join(self, account: str, out: TickOut) -> None:
        if account in self.players:
            return
        if len(self.players) >= self.definition.players:
            out.full.append(account)
            return
        spec = self.definition.hero
        hero = self.stored.pop(account, None) if spec.persist else None
        if hero is None:
            hero = self.make(spec, account)
        self.entities[hero['id']] = hero
        self.players[account] = hero['id']
        self.dirty.add(hero['id'])
        self.gone.discard(hero['id'])
        out.joined[account] = hero['id']
        for block in self.definition.on_join:
            self._run(block, {'me': hero}, 'q:on-join')

    def _leave(self, account: str, out: TickOut) -> None:
        eid = self.players.get(account)
        if eid is None:
            return
        hero = self.entities[eid]
        for block in self.definition.on_leave:
            self._run(block, {'me': hero}, 'q:on-leave')
        del self.entities[eid]
        del self.players[account]
        if self.definition.hero.persist:
            self.stored[account] = hero
        self.gone.add(eid)
        self.dirty.discard(eid)
        out.left.append(account)

    def _run(self, block, local: Dict[str, Any], where: str) -> bool:
        """A rule's run, as a transaction: what fails is undone and kept in the errors."""
        self._begin()
        try:
            self.rules.run(block, local)
        except (RuleError, Refused) as e:
            self._rollback()
            self._error(where, e if isinstance(e, RuleError) else RuleError(f'refused: {e.reason}'))
            return False
        self._commit()
        return True

    def _command(self, account: str, seq: Any, name: Any, args: Any, out: TickOut) -> Tuple[bool, str]:
        def no(reason: str) -> Tuple[bool, str]:
            out.refused.setdefault(account, []).append({'seq': seq, 'name': name, 'reason': reason})
            return False, reason

        eid = self.players.get(account)
        if eid is None:
            return no('Not in the world.')
        command = self.definition.commands.get(name) if isinstance(name, str) else None
        if command is None:
            return no(f'There is no command {name!r}.')
        if not isinstance(args, dict) or set(args) != set(command.params):
            wanted = ', '.join(command.params) or 'nothing'
            return no(f'{name} takes {wanted}.')
        if not _args_ok(args) or len(json.dumps(args)) > MAX_ARGS:
            return no(f'{name}: an argument is not a plain value.')
        if command.limit:
            count, window = command.limit
            key = f'{account}\x00{name}'
            recent = [t for t in self.rates.get(key, []) if t > self.tick - window]
            if len(recent) >= count:
                self.rates[key] = recent
                return no('Too fast.')
            self.rates[key] = recent + [self.tick]
        self._begin()
        try:
            self.rules.run(command.body, {'me': self.entities[eid], **args})
        except Refused as r:
            self._rollback()
            return no(r.reason)
        except RuleError as e:
            self._rollback()
            self._error(f'q:command {name}', e)
            return no('The world could not run it.')
        self._commit()
        out.acks.setdefault(account, []).append(seq)
        return True, 'ok'

    def step(self, inputs: List[tuple]) -> TickOut:
        """One tick: the inputs in the order they came (('join', account), ('leave', account), ('cmd', account,
        seq, name, args)), then the rules due."""
        self.tick += 1
        out = TickOut(self.tick)
        self.dirty, self.gone, self.events, self.vars_changed = set(), set(), [], False
        for item in inputs:
            kind, account = item[0], item[1]
            if kind == 'join':
                self._join(account, out)
                out.entries.append({'t': self.tick, 'k': 'join', 'a': account})
            elif kind == 'leave':
                self._leave(account, out)
                out.entries.append({'t': self.tick, 'k': 'leave', 'a': account})
            elif kind == 'cmd':
                _, _, seq, name, args = item
                ok, result = self._command(account, seq, name, args, out)
                out.entries.append({'t': self.tick, 'k': 'cmd', 'a': account, 's': seq, 'n': name, 'x': args,
                                    'r': 'ok' if ok else result})
        self.live()                            # spawns, the ones made for a while, the travellers, the brains
        for ticks, rule in self.definition.every:
            if self.tick % ticks == 0:
                self._run(rule, {}, 'q:every')
        self.reindex(self.dirty | self.gone)
        return out

    # -- kept, and brought back ------------------------------------------------------------------------------

    def snapshot(self) -> dict:
        version, state, gauss = self.rng.getstate()
        return copy.deepcopy({
            'world': self.definition.name, 'tick': self.tick, 'vars': self.vars, 'entities': self.entities,
            'stored': self.stored, 'players': self.players, 'rates': self.rates, 'counters': self.counters,
            'spawned': self.spawned,
            'rng': [version, list(state), gauss],
        })

    @classmethod
    def from_snapshot(cls, definition: WorldDef, snap: dict) -> 'World':
        world = cls(definition)
        world.tick = snap['tick']
        world.vars = copy.deepcopy(snap['vars'])
        world.entities = copy.deepcopy(snap['entities'])
        world.stored = copy.deepcopy(snap['stored'])
        world.players = dict(snap['players'])
        world.rates = {k: list(v) for k, v in snap['rates'].items()}
        world.counters = dict(snap['counters'])
        version, state, gauss = snap['rng']
        world.rng.setstate((version, tuple(state), gauss))
        world.spawned = copy.deepcopy(snap.get('spawned', world.spawned))
        world.expiring = {eid for eid, e in world.entities.items() if '_expires' in e}
        world.travelers = {eid for eid, e in world.entities.items() if e.get('_path')}
        world.reindex(world.entities)
        return world

    def digest(self) -> str:
        """The world's state as one hash: two worlds with the same are the same world."""
        return hashlib.sha256(json.dumps(self.snapshot(), sort_keys=True).encode()).hexdigest()
