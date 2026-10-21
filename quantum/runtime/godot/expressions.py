"""A Quantum expression, compiled to GDScript.

The grammar is the Core evaluator's (`quantum/core/expressions.py`: Python's
`ast`, a node whitelist, `&&`/`||`/`!` normalised) so a game's `{coins + 1}`
reads like a page's. Where GDScript's operators differ from the evaluator's
semantics, a runtime helper (`Q.*`, addons/quantum/q.gd) closes the gap:
`/` is always a float division, `%` follows the divisor's sign, `len`
works on strings, arrays and dictionaries.

Every name must be declared (`Scope`): a typo is a compile error here, not
a null in Godot.
"""

from __future__ import annotations

import ast
import json
from typing import Dict, Iterable, List, Optional, Set

from quantum.core.expressions import _normalise_js_operators
from quantum.runtime.godot.errors import GameCompileError

_LITERALS = {'true': 'true', 'false': 'false', 'null': 'null',
             'True': 'true', 'False': 'false', 'None': 'null'}

# Quantum built-in function -> GDScript
_FUNCTIONS = {
    'len': 'Q.len({0})',
    'str': 'Q.to_str({0})',
    'int': 'int({0})',
    'float': 'float({0})',
    'abs': 'abs({0})',
    'min': 'min({0}, {1})',
    'max': 'max({0}, {1})',
    'round': 'roundi({0})',
    'floor': 'floori({0})',
    'ceil': 'ceili({0})',
    'sqrt': 'sqrt({0})',
    'random': 'Q.random(self, {0}, {1})',   # a float in [a, b] from the scene's seeded source
    'count': 'Q.count(self, {0})',           # how many things of a tag are in the scene
    'thing_at': 'Q.thing_at(self, {0}, {1}, {2})',   # the thing of a tag at (x, y), or null
    'tile_at': 'Q.tile_at(self, {0}, {1})',  # the tile in a cell of the tilemap (0: none)
    'net_status': 'Q.net_status()',          # offline, hosting, joining, connected, playing, waiting, catching up, failed, ended
    'net_players': 'Q.net_players()',        # how many are connected
    'net_player': 'Q.net_player()',          # this machine's player number (0: none yet)
    'url_param': 'Q.url_param({0}, {1})',    # the web page's ?name=, or the default (a link that joins a room)
    'paused': 'Q.paused(self)',              # the scene is paused (qg:pause)
    'talking': 'Q.talking(self)',            # a qg:dialogue is open (qg:say)
    'tr': 'Q.translate({0})',                # a text in the player's language (qg:language)
    'language': 'Q.language_name()',         # the name of the language shown, in it (English: the game's own)
    'has_save': 'Q.has_save()',              # a qg:save is there to continue
    'distance': 'Q.distance({0}, {1})',      # pixels between two things or characters (INF when one is gone)
    'nearest': 'Q.nearest({0}, {1})',        # the character of that id, or thing of that tag, nearest the first
    'sees': 'Q.sees({0}, {1})',              # no solid tile of the tilemap between the two
    'held': 'Q.items_held({0})',             # how many of a qg:item the players hold
    'can_quit': 'Q.can_quit()',              # qg:quit would close the game (not in a browser)
    'ticks': 'Q.ticks(self)',                # the ticks the scene has played (not while paused)
    'sin': 'sin(deg_to_rad({0}))',           # of an angle in degrees
    'cos': 'cos(deg_to_rad({0}))',
    'atan2': 'Q.atan2_deg({0}, {1})',        # the angle of (x, y) in degrees: 0 right, 90 down
    'sort': {1: 'Q.sort({0})', 2: 'Q.sort({0}, {1})'},   # a sorted copy (descending with true), the Core's sort
}

# The built-ins that read a player's action: the action's name, and the player (1 when not given).
# What an action is held with travels in the lockstep as pressed or not, so strength() is 0 or 1 there.
_ACTION_FUNCTIONS = {
    'pressing': 'Q.held({0})',               # held now
    'pressed_for': 'Q.held_ticks({0})',      # the ticks it has been held; on the tick it is let go, how long it was
    'strength': 'Q.strength({0})',           # how far it is pressed, 0 to 1 (a stick, a trigger)
}

# What an expression may read of a thing (`hero.x`, `other.state`); anything else is a compile error, not a
# game stopped in Godot. A character's controller says which of these it has.
_BODY = ('x', 'y', 'name', 'state', 'player', 'on_floor', 'on_wall', 'on_ceiling')
CONTROLLER_FIELDS: Dict[str, frozenset] = {
    'platformer': frozenset(_BODY + ('facing',)),
    'topdown': frozenset(_BODY + ('facing',)),
    'ship': frozenset(_BODY),
    'fighter': frozenset(_BODY + ('facing', 'health')),
    'grid': frozenset(_BODY + ('facing', 'col', 'row')),
    'behavior': frozenset(_BODY + ('facing', 'vx', 'vy')),
    'map': frozenset(('x', 'y', 'name')),
}
# ...and a thing that may be any of them, or a prefab's instance (`me` and `other` of a handler, a loop's thing)
THING_FIELDS = frozenset().union(*CONTROLLER_FIELDS.values(), ('tag', 'health', 'doing'))

_BIN = {ast.Add: '+', ast.Sub: '-', ast.Mult: '*'}
_CMP = {ast.Eq: '==', ast.NotEq: '!=', ast.Lt: '<', ast.LtE: '<=', ast.Gt: '>', ast.GtE: '>='}


class Scope:
    """The names an expression may use, with the enclosing scopes.

    Game-wide names (the q:sets at the application level) live on the
    autoload `G` and compile to `G.name`.
    """

    def __init__(self, names: Iterable[str] = (), parent: Optional['Scope'] = None,
                 functions: Iterable[str] = (), game_names: Iterable[str] = (), node_ids: Iterable[str] = (),
                 things: Iterable[str] = (), node_fields: Optional[Dict[str, frozenset]] = None,
                 actions: Optional[Iterable[str]] = None):
        self.names: Set[str] = set(names)
        self.functions: Set[str] = set(functions)
        self.game_names: Set[str] = set(game_names)
        self.node_ids: Set[str] = set(node_ids)   # the scene's characters, by id: `p1.health`
        self.things: Set[str] = set(things)       # names that always hold a thing: me, other, a qg:for-each's
        self.node_fields = node_fields or {}      # a character id -> what its controller has
        self.actions = set(actions) if actions is not None else None   # the game's actions (None: unchecked)
        self.parent = parent

    def has(self, name: str) -> bool:
        return (name in self.names or name in self.game_names or name in self.node_ids
                or (self.parent is not None and self.parent.has(name)))

    def is_node(self, name: str) -> bool:
        if name in self.names:
            return False
        return name in self.node_ids or (self.parent is not None and self.parent.is_node(name))

    def is_game(self, name: str) -> bool:
        if name in self.names:
            return False
        if name in self.game_names:
            return True
        return self.parent is not None and self.parent.is_game(name)

    def reference(self, name: str) -> str:
        if self.is_node(name):
            return f'get_node("{name}")'
        return f'G.{name}' if self.is_game(name) else name

    def has_function(self, name: str) -> bool:
        return name in self.functions or (self.parent is not None and self.parent.has_function(name))

    def child(self, names: Iterable[str] = (), things: Iterable[str] = ()) -> 'Scope':
        return Scope(names, parent=self, things=things)

    def fields_of(self, name: str) -> Optional[frozenset]:
        """What `name.field` may read, or None when the name may hold anything (a q:set, a parameter)."""
        if name in self.names:
            return THING_FIELDS if name in self.things else None
        if name in self.node_ids:
            return self.node_fields.get(name, THING_FIELDS)
        return self.parent.fields_of(name) if self.parent is not None else None

    def game_actions(self) -> Optional[Set[str]]:
        if self.actions is not None:
            return self.actions
        return self.parent.game_actions() if self.parent is not None else None

    def locals(self) -> List[str]:
        """The names of the scopes inside the script's own: parameters, loop variables, a function's or a
        handler's variables (outermost first)."""
        if self.parent is None:
            return []
        out = self.parent.locals()
        return out + sorted(n for n in self.names if n not in out)


def strip_braces(text: str) -> str:
    text = text.strip()
    if text.startswith('{') and text.endswith('}'):
        return text[1:-1].strip()
    return text


def compile_expression(source: str, scope: Scope, line: Optional[int] = None) -> str:
    """`{coins + 1}` or `coins + 1` -> GDScript source."""
    text = strip_braces(source)
    if not text:
        raise GameCompileError('empty expression', line)
    try:
        tree = ast.parse(_normalise_js_operators(text), mode='eval')
    except SyntaxError as e:
        raise GameCompileError(f'cannot read the expression {text!r}: {e.msg}', line)
    return _Emitter(scope, line, text).emit(tree.body)


class _Emitter:
    def __init__(self, scope: Scope, line: Optional[int], source: str):
        self.scope = scope
        self.line = line
        self.source = source

    def fail(self, message: str) -> GameCompileError:
        return GameCompileError(f'in {{{self.source}}}: {message}', self.line)

    def emit(self, node: ast.AST) -> str:
        method = getattr(self, '_' + type(node).__name__, None)
        if method is None:
            raise self.fail(f'{type(node).__name__} is not part of the language')
        return method(node)

    def _Constant(self, node: ast.Constant) -> str:
        v = node.value
        if isinstance(v, bool):
            return 'true' if v else 'false'
        if v is None:
            return 'null'
        if isinstance(v, (int, float)):
            return repr(v)
        if isinstance(v, str):
            return json.dumps(v, ensure_ascii=False)
        raise self.fail(f'literal {v!r} is not part of the language')

    def _Name(self, node: ast.Name) -> str:
        if node.id in _LITERALS:
            return _LITERALS[node.id]
        if not self.scope.has(node.id):
            raise self.fail(f'{node.id!r} is not declared (a q:set of the scene or the game, a parameter or a loop variable)')
        return self.scope.reference(node.id)

    def _BinOp(self, node: ast.BinOp) -> str:
        left, right = self.emit(node.left), self.emit(node.right)
        op = type(node.op)
        if op in _BIN:
            return f'({left} {_BIN[op]} {right})'
        if op is ast.Div:
            return f'Q.div({left}, {right})'
        if op is ast.FloorDiv:
            return f'Q.floordiv({left}, {right})'
        if op is ast.Mod:
            return f'Q.mod({left}, {right})'
        if op is ast.Pow:
            return f'pow({left}, {right})'
        raise self.fail(f'operator {op.__name__} is not part of the language')

    def _UnaryOp(self, node: ast.UnaryOp) -> str:
        operand = self.emit(node.operand)
        if isinstance(node.op, ast.Not):
            return f'(not {operand})'
        if isinstance(node.op, ast.USub):
            return f'(-{operand})'
        if isinstance(node.op, ast.UAdd):
            return operand
        raise self.fail('operator is not part of the language')

    def _BoolOp(self, node: ast.BoolOp) -> str:
        word = ' and ' if isinstance(node.op, ast.And) else ' or '
        return '(' + word.join(self.emit(v) for v in node.values) + ')'

    def _Compare(self, node: ast.Compare) -> str:
        parts = []
        left = self.emit(node.left)
        for op, comparator in zip(node.ops, node.comparators):
            right = self.emit(comparator)
            kind = type(op)
            if kind in _CMP:
                parts.append(f'{left} {_CMP[kind]} {right}')
            elif kind is ast.In:
                parts.append(f'{left} in {right}')
            elif kind is ast.NotIn:
                parts.append(f'{left} not in {right}')
            else:
                raise self.fail('comparison is not part of the language')
            left = right
        if len(parts) == 1:
            return f'({parts[0]})'
        return '(' + ' and '.join(f'({p})' for p in parts) + ')'

    def _IfExp(self, node: ast.IfExp) -> str:
        return f'({self.emit(node.body)} if {self.emit(node.test)} else {self.emit(node.orelse)})'

    def _Attribute(self, node: ast.Attribute) -> str:
        if isinstance(node.value, ast.Name):
            fields = self.scope.fields_of(node.value.id)
            if fields is not None and node.attr not in fields:
                raise self.fail(f'{node.value.id}.{node.attr}: no such field; {node.value.id} has '
                                + ', '.join(sorted(fields)))
        if node.attr in ('x', 'y'):   # where a thing or a character is (or a cursor's point)
            return f'Q.pos_{node.attr}({self.emit(node.value)})'
        if node.attr in ('on_floor', 'on_wall', 'on_ceiling'):   # what a body touched as it last moved
            return f'Q.touching({self.emit(node.value)}, "{node.attr[3:]}")'
        return f'{self.emit(node.value)}.{node.attr}'

    def _Subscript(self, node: ast.Subscript) -> str:
        if isinstance(node.slice, ast.Slice):
            sl = node.slice
            if sl.step is not None:
                raise self.fail('a slice with a step is not part of the game language')
            start = self.emit(sl.lower) if sl.lower is not None else 'null'
            end = self.emit(sl.upper) if sl.upper is not None else 'null'
            return f'Q.slice({self.emit(node.value)}, {start}, {end})'
        return f'{self.emit(node.value)}[{self.emit(node.slice)}]'

    def _List(self, node: ast.List) -> str:
        return '[' + ', '.join(self.emit(e) for e in node.elts) + ']'

    def _Tuple(self, node: ast.Tuple) -> str:
        return self._List(node)  # type: ignore[arg-type]

    def _Dict(self, node: ast.Dict) -> str:
        items = []
        for k, v in zip(node.keys, node.values):
            if k is None:
                raise self.fail('** in a dictionary is not part of the language')
            items.append(f'{self.emit(k)}: {self.emit(v)}')
        return '{' + ', '.join(items) + '}'

    def _Call(self, node: ast.Call) -> str:
        if node.keywords:
            raise self.fail('keyword arguments are not part of the game language')
        args = [self.emit(a) for a in node.args]
        if isinstance(node.func, ast.Name):
            name = node.func.id
            if name in _FUNCTIONS:
                templates = _FUNCTIONS[name]
                if isinstance(templates, str):
                    templates = {templates.count('{'): templates}
                if len(args) not in templates:
                    wanted = ' or '.join(str(n) for n in sorted(templates))
                    raise self.fail(f'{name}() takes {wanted} argument(s), {len(args)} given')
                return templates[len(args)].format(*args)
            if name in _ACTION_FUNCTIONS:
                return _ACTION_FUNCTIONS[name].format(self._action(name, node.args, args))
            if self.scope.has_function(name):
                return f'{name}({", ".join(args)})'
            raise self.fail(f'{name}() is not a built-in nor a q:function of this scene')
        if isinstance(node.func, ast.Attribute):
            raise self.fail('method calls are not part of the game language yet')
        raise self.fail('call is not part of the language')


    def _action(self, name: str, nodes: list, args: list) -> str:
        """pressing('run'), pressing('run', 2): the Godot action of that player's action (p2_run)."""
        if len(args) not in (1, 2):
            raise self.fail(f'{name}() takes an action and, for another player, its number')
        actions = self.scope.game_actions()
        if isinstance(nodes[0], ast.Constant) and isinstance(nodes[0].value, str):
            action = nodes[0].value
            if actions is not None and action not in actions:
                raise self.fail(f'{name}({action!r}): no such action (the game has {", ".join(sorted(actions))})')
            if len(args) == 1:
                return json.dumps(action)
            if isinstance(nodes[1], ast.Constant):
                player = int(nodes[1].value)
                if player < 1:
                    raise self.fail(f'{name}(): the player is 1 or more')
                return json.dumps(action if player == 1 else f'p{player}_{action}')
        if len(args) == 1:
            return args[0]
        return f'Q.action_of({args[0]}, {args[1]})'


def gdscript_literal(value: object, type_name: str = 'string') -> str:
    """A q:set literal value in GDScript, by its declared type."""
    if type_name == 'number':
        try:
            return repr(float(value))
        except (TypeError, ValueError):
            raise GameCompileError(f'{value!r} is not a number')
    if type_name == 'boolean':
        return 'true' if str(value).strip().lower() in ('true', '1', 'yes') else 'false'
    if type_name in ('array', 'list'):
        try:
            return json.dumps(json.loads(value) if isinstance(value, str) else value)
        except (TypeError, ValueError):
            raise GameCompileError(f'{value!r} is not an array')
    return json.dumps('' if value is None else str(value), ensure_ascii=False)


GD_TYPES: Dict[str, str] = {'number': 'float', 'string': 'String', 'boolean': 'bool', 'array': 'Array'}
