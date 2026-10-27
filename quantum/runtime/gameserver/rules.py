"""A world's statements run: q:set, q:if, q:loop, q:call and q:return, as the Core's, and the world's own q:require,
q:move and q:emit; and the functions a world's expressions call.

Every write to the world goes through World.write, so a command that is refused (or fails) is undone whole: the
world keeps a journal of what each write replaced while a command runs, and plays it back.
"""

from __future__ import annotations

import math
from collections import ChainMap
from typing import Any, Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET

from quantum.core.expressions import ExpressionError
from quantum.runtime.gameserver.errors import Refused, RuleError
from quantum.runtime.gameserver.expressions import WorldEvaluator, literal, parts_of, text_of, unbraced
from quantum.runtime.gameserver.model import NOT_IN_A_VIEW, Q_NS

# the eight ways a step goes, as the game says them
DIRECTIONS: Dict[str, Tuple[int, int]] = {
    'north': (0, -1), 'south': (0, 1), 'east': (1, 0), 'west': (-1, 0),
    'northeast': (1, -1), 'northwest': (-1, -1), 'southeast': (1, 1), 'southwest': (-1, 1),
}
_FACING = {v: k for k, v in DIRECTIONS.items()}
READ_ONLY = ('id', 'kind')

# What a world's expressions may call besides the Core's stdlib (len, round, min, join...): the reference page is
# written from this, and a test checks it names every function the interpreter has.
FUNCTION_DOCS: Dict[str, str] = {
    'tile(x)': 'the tile of an entity (or of the entity of that id, or a tile itself), as {x, y}; null if none',
    'walkable(x)': 'the tile is on the map and not a wall',
    'ahead(x, dir)': 'the tile next to it the way dir says (north, south, east, west, northeast...); null for a '
                     'way that is not one',
    'distance(a, b)': 'tiles between two (the most of across and down: a diagonal is one); null if either is '
                      'nowhere',
    'near(a, b, n)': 'within n tiles of each other (n is 1 if not given)',
    'in_area(x, name)': "on a tile of the map's area of that name",
    'area(name)': "the area's tile where q:move puts an entity: its middle, or the walkable tile nearest it",
    'heroes()': "the players' entities in the world, by id",
    'entities(kind)': 'every entity of the world, by id; of that kind only, if given',
    'entity(id)': 'the entity of that id, or null',
    'tick()': "the world's tick, from 0 when it was made",
    'seconds()': "the world's time: its ticks over its tick rate",
    'random(a, b)': "a whole number from a to b; random() a number from 0 to 1. The world's own seeded source: "
                    'a replay draws the same',
    'chance(p)': 'true with the probability p (0 to 1), from the same source',
    'pick(list)': 'one of a list, from the same source',
    'sqrt(x)': 'its square root',
    'now()': "refused: it is the machine's clock, and a world is replayed; its time is tick() and seconds()",
}
MAX_LOOP = 100_000
MAX_DEPTH = 64


class _Return(Exception):
    def __init__(self, value: Any):
        self.value = value


def _name(element: ET.Element) -> str:
    tag = element.tag
    return tag[len(Q_NS):] if isinstance(tag, str) and tag.startswith(Q_NS) else str(tag).split('}')[-1]


def _line(element: ET.Element) -> Optional[int]:
    return getattr(element, 'sourceline', None)


def truthy(value: Any) -> bool:
    return bool(value)


def chebyshev(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


class Interpreter:
    """Runs a world's blocks against its World."""

    def __init__(self, world):
        self.world = world
        self.depth = 0
        self.evaluator = WorldEvaluator(functions=self._functions(), function_resolver=self._resolve)
        # a view's where=: the functions that read, and none of the q:functions (which could write)
        self.reader = WorldEvaluator(functions={k: f for k, f in self._functions().items() if k not in NOT_IN_A_VIEW})

    # -- expressions -------------------------------------------------------------------------------------------

    def scope(self, local: Dict[str, Any]) -> ChainMap:
        return ChainMap(local, self.world.vars)

    def evaluate(self, raw: str, local: Dict[str, Any], line: Optional[int]) -> Any:
        """An expression attribute, with or without its braces."""
        return self.expression(unbraced(raw), local, line)

    def expression(self, expression: str, local: Dict[str, Any], line: Optional[int]) -> Any:
        """An expression out of its braces (a { in it is a record's)."""
        try:
            return self.evaluator.evaluate(expression, self.scope(local))
        except ExpressionError as e:
            raise RuleError(str(e), line)

    def value(self, raw: str, local: Dict[str, Any], line: Optional[int]) -> Any:
        """A value= as written: one expression in braces is its value; a text with expressions in it, a text; else
        a number, true, false, null or the text."""
        parts = parts_of(raw)
        if len(parts) == 1 and parts[0][1] is not None and parts[0][0] == '':
            return self.expression(parts[0][1], local, line)
        if all(e is None for _, e in parts):
            return literal(raw)
        return self.text(raw, local, line)

    def text(self, raw: str, local: Dict[str, Any], line: Optional[int]) -> str:
        out = []
        for lit, expression in parts_of(raw):
            out.append(lit if expression is None else text_of(self.expression(expression, local, line)))
        return ''.join(out)

    # -- blocks ------------------------------------------------------------------------------------------------

    def run(self, block: ET.Element, local: Dict[str, Any]) -> None:
        for child in block:
            if _name(child) in ('elseif', 'else'):
                continue                     # a q:if's own, read by the q:if
            self.statement(child, local)

    def statement(self, el: ET.Element, local: Dict[str, Any]) -> None:
        name = _name(el)
        line = _line(el)
        if name == 'set':
            self.assign(el.get('name'), self.value(el.get('value', ''), local, line), local, line)
        elif name == 'if':
            if truthy(self.evaluate(el.get('condition'), local, line)):
                self.run(el, local)
                return
            for branch in el:
                kind = _name(branch)
                if kind == 'elseif' and truthy(self.evaluate(branch.get('condition'), local, _line(branch))):
                    self.run(branch, local)
                    return
                if kind == 'else':
                    self.run(branch, local)
                    return
        elif name == 'loop':
            self.loop(el, local, line)
        elif name == 'call':
            function = self.world.definition.functions.get(el.get('function'))
            if function is None:
                raise RuleError(f'q:call: there is no q:function {el.get("function")!r}', line)
            self.call(function, self.arguments(el.get('args', ''), local, line), line)
        elif name == 'return':
            raise _Return(self.value(el.get('value', ''), local, line))
        elif name == 'require':
            if not truthy(self.evaluate(el.get('condition'), local, line)):
                raise Refused(self.text(el.get('else', 'Not allowed.'), local, line))
        elif name == 'move':
            entity = self.evaluate(el.get('entity'), local, line)
            self.world.move(self.world.entity_of(entity, line), self.place(el.get('to'), local, line), line)
        elif name == 'emit':
            self.emit(el, local, line)
        else:                                # the schema has let nothing else through
            raise RuleError(f'<q:{name}> does not run in a block', line)

    def loop(self, el: ET.Element, local: Dict[str, Any], line: Optional[int]) -> None:
        var, index = el.get('var'), el.get('index')
        if el.get('items') is not None:
            items = self.evaluate(el.get('items'), local, line)
            if isinstance(items, dict):
                items = list(items.values())
            if not isinstance(items, (list, tuple, str)):
                raise RuleError(f'q:loop items= is not a list ({type(items).__name__})', line)
            seq = list(items)
        elif el.get('from') is not None and el.get('to') is not None:
            first = self.evaluate(el.get('from'), local, line)
            last = self.evaluate(el.get('to'), local, line)
            seq = list(range(int(first), int(last) + 1))
        else:
            raise RuleError('q:loop needs items=, or from= and to=', line)
        if len(seq) > MAX_LOOP:
            raise RuleError(f'q:loop of {len(seq)} turns: a tick holds {MAX_LOOP} at most', line)
        for i, item in enumerate(seq):
            local[var] = item
            if index:
                local[index] = i
            self.run(el, local)

    def arguments(self, raw: str, local: Dict[str, Any], line: Optional[int]) -> List[Any]:
        """q:call args=: each {...} an argument; with no braces, expressions separated by commas."""
        parts = parts_of(raw)
        expressions = [e for _, e in parts if e is not None]
        if expressions:
            return [self.expression(e, local, line) for e in expressions]
        out, depth, current = [], 0, []
        for c in raw:
            if c == ',' and depth == 0:
                out.append(''.join(current))
                current = []
                continue
            if c in '([':
                depth += 1
            elif c in ')]':
                depth -= 1
            current.append(c)
        out.append(''.join(current))
        return [self.evaluate(a, local, line) for a in out if a.strip()]

    def call(self, function, args: List[Any], line: Optional[int]) -> Any:
        if len(args) != len(function.params):
            raise RuleError(f'{function.name}() takes {len(function.params)} arguments '
                            f'({", ".join(function.params) or "none"}), not {len(args)}', line)
        if self.depth >= MAX_DEPTH:
            raise RuleError(f'{function.name}(): calls nested {MAX_DEPTH} deep', line)
        self.depth += 1
        try:
            self.run(function.body, dict(zip(function.params, args)))
        except _Return as r:
            return r.value
        finally:
            self.depth -= 1
        return None

    def _resolve(self, name: str):
        function = self.world.definition.functions.get(name)
        if function is None:
            return None
        return lambda *args: self.call(function, list(args), function.line)

    def assign(self, name: str, value: Any, local: Dict[str, Any], line: Optional[int]) -> None:
        parts = name.split('.')
        if len(parts) == 1:
            if name in local:
                local[name] = value
            elif name in self.world.vars:
                self.world.write(self.world.vars, name, value, None, line)
            else:
                local[name] = value
            return
        root = local[parts[0]] if parts[0] in local else self.world.vars.get(parts[0])
        if not isinstance(root, dict):
            raise RuleError(f'q:set name="{name}": {parts[0]} is not an entity or a record', line)
        target = root
        for part in parts[1:-1]:
            target = target.get(part) if isinstance(target, dict) else None
            if not isinstance(target, dict):
                raise RuleError(f'q:set name="{name}": {part} is not a record', line)
        key = parts[-1]
        if target is root and self.world.is_entity(root) and (key in READ_ONLY or key.startswith('_')):
            raise RuleError(f'q:set name="{name}": an entity\'s {key} is the world\'s', line)
        self.world.write(target, key, value, root, line)

    def place(self, raw: str, local: Dict[str, Any], line: Optional[int]) -> Tuple[int, int]:
        """q:move to=: an area by its name, or an expression giving a tile, an entity, or an area's name."""
        text = raw.strip()
        areas = self.world.definition.map.areas
        if text in areas:
            return self.world.area_tile(text, line)
        value = self.evaluate(text, local, line)
        if isinstance(value, str) and value in areas:
            return self.world.area_tile(value, line)
        tile = self.world.tile_of(value)
        if tile is None:
            raise RuleError(f'q:move to="{raw}": not a tile, an entity or an area of the map', line)
        return tile

    def emit(self, el: ET.Element, local: Dict[str, Any], line: Optional[int]) -> None:
        value = self.value(el.get('value'), local, line) if el.get('value') is not None else None
        tile, of, to = None, None, None
        if el.get('at') is not None:
            tile, of = self.spot(el.get('at'), local, line)
        if el.get('to') is not None:
            target = self.evaluate(el.get('to'), local, line)
            entity = self.world.entities.get(target) if isinstance(target, str) else target
            if not self.world.is_entity(entity) or entity.get('_player') is None:
                raise RuleError('q:emit to= is not a player\'s entity in the world', line)
            to = entity['_player']
        everyone = el.get('at') is None and el.get('to') is None
        self.world.emit(el.get('event'), value, tile, of, to, everyone, line)

    def spot(self, raw: str, local: Dict[str, Any], line: Optional[int]) -> Tuple[Optional[Tuple[int, int]],
                                                                                    Optional[str]]:
        """q:emit at=: the tile, and the entity's id if it is an entity's (an entity nowhere: no tile)."""
        text = raw.strip()
        areas = self.world.definition.map.areas
        if text in areas:
            return self.world.area_tile(text, line), None
        value = self.evaluate(text, local, line)
        if isinstance(value, str) and value in areas:
            return self.world.area_tile(value, line), None
        if isinstance(value, str) and value in self.world.entities:
            value = self.world.entities[value]
        if self.world.is_entity(value):
            return self.world.tile_of(value), value['id']
        tile = self.world.tile_of(value)
        if tile is None:
            raise RuleError(f'q:emit at="{raw}": not a tile, an entity or an area of the map', line)
        return tile, None

    # -- the world's functions ---------------------------------------------------------------------------------

    def _functions(self) -> Dict[str, Any]:
        world = self.world

        def tile(x: Any) -> Optional[Dict[str, int]]:
            t = world.tile_of(x)
            return {'x': t[0], 'y': t[1]} if t else None

        def walkable(x: Any) -> bool:
            t = world.tile_of(x)
            return t is not None and world.walkable(t)

        def ahead(x: Any, direction: Any) -> Optional[Dict[str, int]]:
            t = world.tile_of(x)
            step = DIRECTIONS.get(direction) if isinstance(direction, str) else None
            if t is None or step is None:
                return None
            return {'x': t[0] + step[0], 'y': t[1] + step[1]}

        def distance(a: Any, b: Any) -> Optional[int]:
            ta, tb = world.tile_of(a), world.tile_of(b)
            return chebyshev(ta, tb) if ta and tb else None

        def near(a: Any, b: Any, n: Any = 1) -> bool:
            d = distance(a, b)
            return d is not None and d <= n

        def in_area(x: Any, name: Any) -> bool:
            t = world.tile_of(x)
            box = world.definition.map.areas.get(name) if isinstance(name, str) else None
            return bool(t and box and box[0] <= t[0] <= box[2] and box[1] <= t[1] <= box[3])

        def area(name: Any) -> Optional[Dict[str, int]]:
            if not isinstance(name, str) or name not in world.definition.map.areas:
                return None
            t = world.area_tile(name, None)
            return {'x': t[0], 'y': t[1]}

        def heroes() -> List[dict]:
            return [world.entities[i] for i in sorted(world.players.values())]

        def entities(kind: Any = None) -> List[dict]:
            return [e for _, e in sorted(world.entities.items()) if kind is None or e.get('kind') == kind]

        def entity(x: Any) -> Optional[dict]:
            return world.entities.get(x) if isinstance(x, str) else (x if world.is_entity(x) else None)

        def random(low: Any = None, high: Any = None) -> Any:
            if low is None and high is None:
                return world.rng.random()
            if low is None or high is None:
                raise ValueError('random() takes no arguments, or two: random(a, b)')
            return world.rng.randint(int(low), int(high))

        def chance(p: Any) -> bool:
            p = float(p)
            if not 0 <= p <= 1:
                raise ValueError(f'chance({p}): the probability is between 0 and 1')
            return world.rng.random() < p

        def pick(items: Any) -> Any:
            items = list(items)
            if not items:
                raise ValueError('pick() of an empty list')
            return items[world.rng.randrange(len(items))]

        def now() -> Any:
            raise ValueError('now() is the machine\'s clock; a world\'s time is tick() (and seconds())')

        return {
            'tile': tile, 'walkable': walkable, 'ahead': ahead, 'distance': distance, 'near': near,
            'in_area': in_area, 'area': area, 'heroes': heroes, 'entities': entities, 'entity': entity,
            'tick': lambda: world.tick, 'seconds': lambda: world.tick / world.definition.tick_rate,
            'random': random, 'chance': chance, 'pick': pick, 'now': now, 'sqrt': math.sqrt,
        }


def facing_of(a: Tuple[int, int], b: Tuple[int, int]) -> Optional[str]:
    step = (max(-1, min(1, b[0] - a[0])), max(-1, min(1, b[1] - a[1])))
    return _FACING.get(step)
