"""A world's rules on the Rust engine's machine (PLAN_WORLD_ENGINE.md, E2): bytecode.py compiles them, the machine
(native/world/src/vm.rs) runs them, and the world is its host.

E2 holds the machine to the interpreter (rules.py): every expression of a world, and every block (a q:command's, a
q:every's, a q:function's), run both ways, gives the same world, tick by tick. The world's state is still Python's
(E3 moves it), so the machine asks the world for what it does not hold: a variable, an entity's field, a world's
function (`near`, `nearest`, `random`...), and what only the world does (a q:move, a q:emit, the ledger's). An entity
reaches the machine as its id, and comes back as the world's own dict.

    machine = WorldMachine(world)
    machine.evaluate("me.hp - 1 if near(me, it) else 0", {'me': hero, 'it': rat})

    world = MachineWorld(definition)       # a World whose blocks run on the machine
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from quantum.core.expressions import ExpressionError, UndefinedError, _names_of
from quantum.runtime.gameserver.bytecode import (CompileError, Code, compile_block, compile_expression,
                                                 world_function_names, world_host_names)
from quantum.runtime.gameserver.errors import Refused, RuleError
from quantum.runtime.gameserver.rules import Interpreter
from quantum.runtime.gameserver.world import World

try:
    import quantum_world
except ImportError:  # not built here
    quantum_world = None


def _built() -> None:
    if quantum_world is None:
        raise RuntimeError('the Rust engine is not built here (pip install ./native/world)')


class WorldHost:
    """What the machine asks a world (vm.rs's Host): its variables, its functions, and what only it does. An
    entity's fields it reads itself, from the dict (python.rs). A statement's line comes as 0 when it has none."""

    def __init__(self, interpreter):
        self.interpreter = interpreter
        self.world = interpreter.world

    def variable(self, name: str):
        vars_ = self.world.vars
        return (True, vars_[name]) if name in vars_ else (False, None)

    def scope_names(self, local):
        """What the Core suggests for a variable that is not there: the interpreter's scope is a ChainMap."""
        return _names_of(self.interpreter.scope(local))

    def call(self, name: str, args, kwargs):
        """A function as the interpreter calls it: its own failures said as the Core says them."""
        evaluator = self.interpreter.evaluator
        fn = evaluator.functions.get(name)
        if fn is None and evaluator.function_resolver is not None:
            fn = evaluator.function_resolver(name)
        if fn is None:
            raise ExpressionError(f'function {name!r} is not defined')
        try:
            return fn(*args, **kwargs)
        except ExpressionError:
            raise
        except Exception as exc:  # noqa: BLE001 - the Core's own wording
            raise ExpressionError(f'{name}() failed: {exc}') from exc

    # -- what a block writes and does --------------------------------------------------------------------------

    def write_var(self, name: str, value: Any, line: int) -> bool:
        """q:set of a world's variable (rules.py's assign): False when there is none of that name."""
        world = self.world
        if name not in world.vars:
            return False
        world.write(world.vars, name, value, None, line or None)
        return True

    def assign_path(self, name: str, local: bool, root: Any, value: Any, line: int):
        """q:set of a.b.c: into the block's own a (local), or the world's variable a. A record of the block's comes
        back changed, for the machine to keep."""
        if not local:
            root = self.world.vars.get(name.split('.')[0])
        self.interpreter.assign_into(name, root, value, line or None)
        if local and not self.world.is_entity(root):
            return True, root
        return False, None

    def effect(self, name: str, args) -> None:
        """A statement only the world does, its attributes evaluated (bytecode.py's effect() lays them out): what
        rules.py's statement() does with them, to the call."""
        world = self.world
        line, *a = args
        line = line or None
        if name in ('move', 'travel'):
            entity, kind, to, raw = a
            entity = world.entity_of(entity, line)
            world.stop_travel(entity, line)
            (world.move if name == 'move' else world.travel)(entity, self.place(kind, to, raw, line), line)
        elif name == 'emit':
            event, has_value, value, kind, spot, at, has_to, to = a
            tile, of, player = None, None, None
            if at is not None:
                tile, of = self.spot(kind, spot, at, line)
            if has_to:
                entity = world.entities.get(to) if isinstance(to, str) else to
                if not world.is_entity(entity) or entity.get('_player') is None:
                    raise RuleError('q:emit to= is not a player\'s entity in the world', line)
                player = entity['_player']
            world.emit(event, value if has_value else None, tile, of, player, at is None and not has_to, line)
        elif name == 'kill':
            entity, has_by, by = a
            entity = world.entity_of(entity, line)
            world.kill(entity, world._entity(by) if has_by else None, line)
        elif name == 'loot':
            of, to = a
            of = world.entity_of(of, line)
            world.loot(of, world.entity_of(to, line), line)
        elif name in ('give', 'take'):
            holder, item, count, amount, currency = a
            holder = world.entity_of(holder, line)
            (world.give if name == 'give' else world.take)(holder, item, count, amount, currency, line)
        elif name == 'pay':
            payer, to, amount, currency = a
            payer = world.entity_of(payer, line)
            world.pay(payer, world.entity_of(to, line), amount, currency, line)
        elif name == 'say':
            channel, target, text = a
            world.say(channel, target, text, line)
        elif name == 'ask':
            npc, me, text = a
            world.ask(me, npc, text, line)
        elif name == 'reward':
            to, quest = a
            world.reward(world.entity_of(to, line), quest, line)
        elif name == 'spawn':
            entity, area, count, ticks = a
            world.spawn_now(entity, area, count, ticks, line)
        else:
            raise RuleError(f'<q:{name}> does not run in a block', line)

    def place(self, kind: str, value: Any, raw: str, line: Optional[int]):
        """rules.py's place, its expression evaluated: an area's name as written, else the value."""
        world = self.world
        if kind == 'area' or (isinstance(value, str) and value in world.definition.map.areas):
            return world.area_tile(value, line)
        tile = world.tile_of(value)
        if tile is None:
            raise RuleError(f'q:move to="{raw}": not a tile, an entity or an area of the map', line)
        return tile

    def spot(self, kind: str, value: Any, raw: str, line: Optional[int]):
        """rules.py's spot, its expression evaluated."""
        world = self.world
        if kind == 'area' or (isinstance(value, str) and value in world.definition.map.areas):
            return world.area_tile(value, line), None
        if isinstance(value, str) and value in world.entities:
            value = world.entities[value]
        if world.is_entity(value):
            return world.tile_of(value), value['id']
        tile = world.tile_of(value)
        if tile is None:
            raise RuleError(f'q:emit at="{raw}": not a tile, an entity or an area of the map', line)
        return tile, None


class WorldMachine:
    """A world's expressions, compiled once each and run on the machine. names: what the host runs (a world's
    functions, and its q:functions when the machine does not hold them); users: the q:functions it holds."""

    def __init__(self, world, interpreter=None, machine=None, names: Optional[frozenset] = None,
                 users: frozenset = frozenset()):
        _built()
        self.world = world
        self.interpreter = interpreter or world.rules
        self.host = WorldHost(self.interpreter)
        self.names = names if names is not None else world_host_names(self.interpreter)
        self.users = users
        self.machine = machine or quantum_world.Machine()
        self._codes: Dict[str, Optional[int]] = {}
        self.refused: Dict[str, str] = {}               # what stays the interpreter's, and why

    def code(self, expression: str) -> Optional[int]:
        """The expression's code on the machine, or None when the machine does not hold it."""
        if expression in self._codes:
            return self._codes[expression]
        try:
            code: Code = compile_expression(expression, self.names, self.users)
        except CompileError as e:
            self.refused[expression] = str(e)
            self._codes[expression] = None
            return None
        number = self.machine.load(code.ops, code.consts, code.names)
        self._codes[expression] = number
        return number

    def evaluate(self, expression: str, local: Dict[str, Any]) -> Any:
        """As the interpreter's evaluate: the value, or an ExpressionError (UndefinedError for what is not
        there)."""
        number = self.code(expression)
        if number is None:
            raise CompileError(self.refused[expression])
        try:
            return self.machine.run(number, local, self.host, self.world.entities)
        except quantum_world.MachineError as e:
            kind, message, _ = e.args
            raise (UndefinedError if kind == 'undefined' else ExpressionError)(message) from None


class MachineInterpreter(Interpreter):
    """rules.py's Interpreter with the world's blocks on the machine: each compiled once (bytecode.py's
    compile_block), its q:functions too, and run there whole. A block the compiler refuses, and what it runs,
    stays the interpreter's, as a q:function the compiler refuses does."""

    def __init__(self, world):
        _built()
        self.native = quantum_world.Machine()        # first: Interpreter's __init__ sets the depth, kept on it
        self._python = False                         # while a block of the interpreter's runs, what it runs stays so
        super().__init__(world)
        self.host = WorldHost(self)
        self.refused: Dict[str, str] = {}
        self._blocks: Dict[int, Optional[int]] = {}
        self._machine: Optional[WorldMachine] = None

    @property
    def depth(self) -> int:
        return self.native.depth()

    @depth.setter
    def depth(self, depth: int) -> None:
        self.native.set_depth(depth)

    @property
    def machine(self) -> WorldMachine:
        """The expressions' machine, with the world's q:functions defined on it (once: the world is built by
        then)."""
        if self._machine is None:
            definition = self.world.definition
            own = world_function_names(self)
            users = set(definition.functions)
            while True:                              # a q:function the compiler refuses, and those that q:call it
                codes = {}
                for name, function in definition.functions.items():
                    if name not in users:
                        continue
                    try:
                        codes[name] = compile_block(function.body, definition,
                                                    own | (frozenset(definition.functions) - users),
                                                    frozenset(users), f'q:function {name}')
                    except CompileError as e:
                        self.refused[f'q:function {name}'] = str(e)
                        users.discard(name)
                        break
                else:
                    break
            for name, code in codes.items():
                function = definition.functions[name]
                number = self.native.load(code.ops, code.consts, code.names)
                self.native.define(name, number, list(function.params), function.line or 0)
            self.users = frozenset(users)
            self.names = own | (frozenset(definition.functions) - self.users)
            self._machine = WorldMachine(self.world, self, self.native, self.names, self.users)
        return self._machine

    def block(self, block) -> Optional[int]:
        """A block's code on the machine, or None when it stays the interpreter's."""
        key = id(block)
        if key not in self._blocks:
            machine = self.machine
            try:
                code = compile_block(block, self.world.definition, machine.names, machine.users)
            except CompileError as e:
                self.refused[f'line {getattr(block, "sourceline", None)}'] = str(e)
                self._blocks[key] = None
            else:
                self._blocks[key] = self.native.load(code.ops, code.consts, code.names)
        return self._blocks[key]

    def run(self, block, local: Dict[str, Any]) -> None:
        number = None if self._python else self.block(block)
        if number is None:
            was, self._python = self._python, True
            try:
                return super().run(block, local)
            finally:
                self._python = was
        try:
            self.native.run_block(number, local, self.host, self.world.entities)
        except quantum_world.MachineError as e:
            kind, message, line = e.args
            if kind == 'refused':
                raise Refused(message) from None
            raise RuleError(message, line or None) from None

    def call(self, function, args, line):
        """A q:function called by the interpreter (a block or an expression it kept): its body is the
        interpreter's too, for its q:return."""
        was, self._python = self._python, True
        try:
            return super().call(function, args, line)
        finally:
            self._python = was

    def expression(self, expression: str, local: Dict[str, Any], line: Optional[int]) -> Any:
        try:
            return self.machine.evaluate(expression, local)
        except CompileError:
            return super().expression(expression, local, line)
        except ExpressionError as e:
            raise RuleError(str(e), line) from None


class MachineWorld(World):
    """A World whose rules run on the machine: conform.py's 'machine' engine."""
    rules_class = MachineInterpreter
