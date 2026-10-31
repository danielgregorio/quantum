"""A world's expressions as bytecode (PLAN_WORLD_ENGINE.md, E2): what the Rust engine's machine runs.

Python is the compiler. It reads an expression as the Core reads it (quantum/core/expressions.py: the same parse, the
same checks, the same refusals) and writes it as a list of instructions for a stack machine: each an opcode and two
numbers. The machine (native/world/src/vm.rs) runs them with the Core's meaning, to the value: a numeric text is a
number in arithmetic and comparison, `/` is a float, `//` and `%` floor as Python's do, `round` goes half away from
zero, `and` and `or` give an operand, a chain of comparisons stops at the first that fails.

    code = compile_expression("me.hp - 1 if near(me, it) else 0")
    print(code.disassemble())

A world's own functions (near, nearest, random...) are the host's: the engine asks the world. Its q:functions too,
in E2's first part; E2's blocks bring them into the machine. What the machine does not hold (a set, a bytes or a
complex constant, the stdlib's dates and passwords) is refused here, by name, and the expression stays the
interpreter's.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from quantum.core.expressions import ExpressionError
from quantum.runtime.gameserver.expressions import WorldEvaluator

# the instructions: (name, what its first number is). Their numbers are their places here, and the machine's enum
# is in the same order (tests/gameserver/test_gameserver_bytecode.py holds the two together).
OPCODES: List[Tuple[str, str]] = [
    ('CONST', 'const'),          # push a constant
    ('NAME', 'name'),            # push a variable: the block's, then the world's; true, false, null
    ('ATTR', 'name'),            # pop x, push x.name (a record's key, an entity's field, a list's or text's length)
    ('INDEX', ''),               # pop key, x; push x[key]
    ('SLICE', 'flags'),          # pop upper (flags & 2), lower (flags & 1), x; push x[lower:upper]
    ('BINOP', 'op'),             # pop right, left; push left op right
    ('UNARY', 'op'),             # pop x; push op x
    ('COMPARE', 'op'),           # pop right, left; push left op right (a bool)
    ('JUMP', 'to'),
    ('JUMP_IF_FALSE', 'to'),     # pop x; jump if it is false
    ('JUMP_IF_FALSE_OR_POP', 'to'),   # `and`: jump keeping x if it is false, else pop it
    ('JUMP_IF_TRUE_OR_POP', 'to'),    # `or`: jump keeping x if it is true, else pop it
    ('DUP', ''),
    ('ROT2', ''),
    ('ROT3', ''),                # a b c -> c a b
    ('POP', ''),
    ('LIST', 'count'),
    ('TUPLE', 'count'),
    ('DICT', 'count'),           # pop count key-value pairs, in order
    ('CALL', 'name'),            # second number: the arguments; a stdlib function, the machine's own
    ('CALL_HOST', 'name'),       # a world's function, or its q:function: the host runs it
    ('CALL_KW', 'name'),         # second number: a constant, [positional count, [keyword names]]; machine's own
    ('CALL_HOST_KW', 'name'),
    # blocks (q:command, q:every, a q:function...): the statements
    ('STORE_NAME', 'name'),      # pop x; q:set of a name: the block's, else the world's variable, else the block's
    ('STORE_PATH', 'const'),     # pop x; q:set of a.b.c (second number: the name as written)
    ('FORMAT', 'count'),         # pop count values; push them as one text (text_of each)
    ('LOOP_ITEMS', 'name'),      # pop items; a loop over them (second number: the index's name, or none)
    ('LOOP_RANGE', 'name'),      # pop to, from; a loop over from..to
    ('FOR_NEXT', 'to'),          # the loop's next turn, or jump when it is over
    ('CALL_USER', 'name'),       # a q:function, in an expression (second number: the arguments)
    ('CALL_STATEMENT', 'name'),  # a q:call (second number: the arguments)
    ('RETURN', ''),              # pop x; the q:function gives it
    ('REFUSE', ''),              # pop a text: the command is refused with it (q:require)
    ('EFFECT', 'const'),         # second number: the arguments; what only the world does (q:move, q:emit...)
    ('LINE', 'to'),              # the line of the statement that runs (for its errors)
    ('LOCAL_OR_NULL', 'name'),   # the block's own variable, or null
    ('FAIL', 'const'),           # a statement that cannot run: the world's error
]
NO_INDEX = 0xFFFF_FFFF
OP = {name: number for number, (name, _) in enumerate(OPCODES)}
BINOPS = [ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow]
BINOP_TEXT = ['+', '-', '*', '/', '//', '%', '**']
UNARYOPS = [ast.USub, ast.UAdd, ast.Not]
UNARY_TEXT = ['-', '+', 'not']
COMPAREOPS = [ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn]
COMPARE_TEXT = ['==', '!=', '<', '<=', '>', '>=', 'in', 'not in']

# the stdlib functions the machine holds (quantum/core/expression_stdlib.py). The rest (dates, passwords, the URL's
# and base64's) a world has no use for: an expression that calls one stays the interpreter's.
NATIVE = frozenset({'len', 'first', 'last', 'join', 'sort', 'get', 'round', 'ceil', 'floor', 'abs', 'min', 'max',
                    'int', 'float', 'str', 'upper', 'lower', 'trim', 'replace', 'split', 'contains', 'sqrt'})


class CompileError(Exception):
    """What the machine does not hold: the expression stays the interpreter's."""


@dataclass
class Code:
    """An expression or a block compiled: its instructions (opcode, a, b), its constants and its names."""
    source: str
    ops: List[Tuple[int, int, int]] = field(default_factory=list)
    consts: List[Any] = field(default_factory=list)
    names: List[str] = field(default_factory=list)

    def const(self, value: Any) -> int:
        for i, c in enumerate(self.consts):          # the same constant, the same place (1 and True are not)
            if type(c) is type(value) and c == value:
                return i
        self.consts.append(value)
        return len(self.consts) - 1

    def name(self, text: str) -> int:
        if text not in self.names:
            self.names.append(text)
        return self.names.index(text)

    def emit(self, op: str, a: int = 0, b: int = 0) -> int:
        self.ops.append((OP[op], a, b))
        return len(self.ops) - 1

    def patch(self, at: int, to: int) -> None:
        op, _, b = self.ops[at]
        self.ops[at] = (op, to, b)

    def disassemble(self) -> str:
        """The instructions as they read: `3  BINOP  +`."""
        lines = [f'; {self.source}']
        for i, (op, a, b) in enumerate(self.ops):
            name, kind = OPCODES[op]
            if name == 'EFFECT':
                arg = f'{self.consts[a]}  ({b} args)'
            elif name == 'STORE_PATH':
                arg = self.consts[b]
            elif kind == 'const':
                arg = repr(self.consts[a])
            elif kind == 'name':
                arg = self.names[a] + (f'  ({b} args)' if name in ('CALL', 'CALL_HOST', 'CALL_USER',
                                                                   'CALL_STATEMENT') else '')
                if name.startswith('LOOP_') and b != NO_INDEX:
                    arg += f'  (index {self.names[b]})'
            elif name == 'EFFECT':
                arg = f'{self.consts[a]}  ({b} args)'
                if name.endswith('_KW'):
                    count, keywords = self.consts[b]
                    arg += f'  ({count} args, {", ".join(keywords)}=)'
            elif kind == 'op':
                arg = {'BINOP': BINOP_TEXT, 'UNARY': UNARY_TEXT, 'COMPARE': COMPARE_TEXT}[name][a]
            elif kind in ('to', 'count', 'flags'):
                arg = str(a)
            else:
                arg = ''
            lines.append(f'{i:>4}  {name:<22}{arg}')
        return '\n'.join(lines)


_PARSER = WorldEvaluator()


def compile_expression(expression: str, host: Optional[frozenset] = None, users: frozenset = frozenset()) -> Code:
    """An expression (out of its braces) as bytecode. host: the names the host runs (a world's functions, and its
    q:functions when the machine does not run them); users: the q:functions the machine runs (compile_block). A
    name in none of them is an error when it runs, as in the interpreter."""
    try:
        tree = _PARSER.compile(expression)
    except ExpressionError as e:
        raise CompileError(str(e)) from e
    code = Code(expression)
    _Compiler(code, host or frozenset(), users).node(tree.body)
    return code


class _Compiler:
    def __init__(self, code: Code, host: frozenset, users: frozenset = frozenset()):
        self.code = code
        self.host = host
        self.users = users

    def node(self, n: ast.AST) -> None:
        c = self.code
        if isinstance(n, ast.Constant):
            if not (n.value is None or isinstance(n.value, (bool, int, float, str))):
                raise CompileError(f'a constant of {type(n.value).__name__} is not a world\'s value')
            c.emit('CONST', c.const(n.value))
        elif isinstance(n, ast.Name):
            c.emit('NAME', c.name(n.id))
        elif isinstance(n, ast.Attribute):
            self.node(n.value)
            c.emit('ATTR', c.name(n.attr))
        elif isinstance(n, ast.Subscript):
            if isinstance(n.slice, ast.Slice):
                if n.slice.step is not None:
                    raise CompileError('a slice with a step is refused by the Core')
                self.node(n.value)
                flags = 0
                if n.slice.lower is not None:
                    self.node(n.slice.lower)
                    flags |= 1
                if n.slice.upper is not None:
                    self.node(n.slice.upper)
                    flags |= 2
                c.emit('SLICE', flags)
            else:
                self.node(n.value)
                self.node(n.slice)
                c.emit('INDEX')
        elif isinstance(n, ast.BinOp):
            self.node(n.left)
            self.node(n.right)
            c.emit('BINOP', BINOPS.index(type(n.op)))
        elif isinstance(n, ast.UnaryOp):
            self.node(n.operand)
            c.emit('UNARY', UNARYOPS.index(type(n.op)))
        elif isinstance(n, ast.BoolOp):
            jump = 'JUMP_IF_FALSE_OR_POP' if isinstance(n.op, ast.And) else 'JUMP_IF_TRUE_OR_POP'
            exits = []
            for value in n.values[:-1]:
                self.node(value)
                exits.append(c.emit(jump))
            self.node(n.values[-1])
            for at in exits:
                c.patch(at, len(c.ops))
        elif isinstance(n, ast.Compare):
            self.compare(n)
        elif isinstance(n, ast.IfExp):
            self.node(n.test)
            otherwise = c.emit('JUMP_IF_FALSE')
            self.node(n.body)
            end = c.emit('JUMP')
            c.patch(otherwise, len(c.ops))
            self.node(n.orelse)
            c.patch(end, len(c.ops))
        elif isinstance(n, (ast.List, ast.Tuple)):
            for e in n.elts:
                self.node(e)
            c.emit('LIST' if isinstance(n, ast.List) else 'TUPLE', len(n.elts))
        elif isinstance(n, ast.Dict):
            for k, v in zip(n.keys, n.values):
                if k is None:
                    raise CompileError('a record spread (**x) is not a world\'s')
                self.node(k)
                self.node(v)
            c.emit('DICT', len(n.keys))
        elif isinstance(n, ast.Set):
            raise CompileError('a set is not a world\'s value')
        elif isinstance(n, ast.Call):
            self.call(n)
        else:
            raise CompileError(f'{type(n).__name__} is not compiled')

    def compare(self, n: ast.Compare) -> None:
        """A chain stops at the first comparison that fails, and is False; each operand is read once."""
        c = self.code
        self.node(n.left)
        fails = []
        pairs = list(zip(n.ops, n.comparators))
        for i, (op, right) in enumerate(pairs):
            self.node(right)
            if i < len(pairs) - 1:
                c.emit('DUP')
                c.emit('ROT3')
                c.emit('COMPARE', COMPAREOPS.index(type(op)))
                fails.append(c.emit('JUMP_IF_FALSE'))
            else:
                c.emit('COMPARE', COMPAREOPS.index(type(op)))
        if fails:
            end = c.emit('JUMP')
            for at in fails:
                c.patch(at, len(c.ops))
            c.emit('POP')
            c.emit('CONST', c.const(False))
            c.patch(end, len(c.ops))

    def call(self, n: ast.Call) -> None:
        c = self.code
        if not isinstance(n.func, ast.Name):
            raise CompileError('only named function calls are allowed')
        name = n.func.id
        if name in self.users and name not in self.host and name not in _PARSER.functions:
            for a in n.args:
                if isinstance(a, ast.Starred):
                    raise CompileError('a call with *args is not compiled')
                self.node(a)
            if n.keywords:
                raise CompileError(f'{name}(): a q:function takes no keywords')
            c.emit('CALL_USER', c.name(name), len(n.args))
            return
        if name in self.host:
            hosted = True
        elif name in NATIVE:
            hosted = False
        elif name in _PARSER.functions:
            raise CompileError(f'{name}() is not the machine\'s (the stdlib\'s {name} has no use in a world)')
        else:
            hosted = True                 # not a function anywhere: the host says so when it runs, as the interpreter
        for a in n.args:
            if isinstance(a, ast.Starred):
                raise CompileError('a call with *args is not compiled')
            self.node(a)
        if n.keywords:
            for kw in n.keywords:
                if kw.arg is None:
                    raise CompileError('a call with **kwargs is not compiled')
                self.node(kw.value)
            spec = c.const([len(n.args), [kw.arg for kw in n.keywords]])
            c.emit('CALL_HOST_KW' if hosted else 'CALL_KW', c.name(name), spec)
        else:
            c.emit('CALL_HOST' if hosted else 'CALL', c.name(name), len(n.args))


def world_function_names(interpreter) -> frozenset:
    """A world's own functions (rules.py's): the host runs them."""
    from quantum.core.expression_stdlib import STDLIB
    return frozenset(k for k, f in interpreter.evaluator.functions.items() if k not in STDLIB or STDLIB[k] is not f)


def world_host_names(interpreter) -> frozenset:
    """The names the host runs for a world when the machine runs its expressions alone: its functions and its
    q:functions."""
    return world_function_names(interpreter) | frozenset(interpreter.world.definition.functions)


# -- blocks ----------------------------------------------------------------------------------------------------

def _tag(element) -> str:
    tag = element.tag
    return tag.split('}')[-1] if isinstance(tag, str) else str(tag).split('}')[-1]


def _line_of(element) -> int:
    return getattr(element, 'sourceline', None) or 0


EFFECTS = ('move', 'travel', 'emit', 'kill', 'loot', 'give', 'take', 'pay', 'say', 'ask', 'reward', 'spawn')


def compile_block(block, definition, host: frozenset, users: frozenset, source: str = '') -> Code:
    """A block of statements (a q:command's, a rule's, a q:function's) as bytecode: rules.py's Interpreter.run, to
    the statement. What only the world does (a move, an emit, the ledger's) is an EFFECT the host runs, with its
    attributes evaluated by the machine first, in the interpreter's order."""
    code = Code(source or _tag(block))
    _BlockCompiler(code, host, users, definition).block(block)
    return code


def compile_value(raw: str, definition, host: frozenset, users: frozenset, line: int = 0, source: str = '') -> Code:
    """A value= as written (rules.py's value: one {...} its value; no braces, a literal; else a text), its line first
    (a field's, a variable's: what its error says)."""
    code = Code(source or 'value')
    code.emit('LINE', line)
    _BlockCompiler(code, host, users, definition).value(raw)
    return code


class _BlockCompiler(_Compiler):
    def __init__(self, code: Code, host: frozenset, users: frozenset, definition):
        super().__init__(code, host, users)
        self.definition = definition

    # -- what a statement's attributes are -------------------------------------------------------------------

    def expression(self, text: str) -> None:
        """An expression out of its braces; one that does not parse fails when it runs, as in the interpreter."""
        try:
            tree = _PARSER.compile(text)
        except ExpressionError as e:
            self.code.emit('FAIL', self.code.const(str(e)))
            return
        self.node(tree.body)

    def evaluate(self, raw: str) -> None:
        from quantum.runtime.gameserver.expressions import unbraced
        self.expression(unbraced(raw))

    def value(self, raw: str) -> None:
        """rules.py's value: one {...} is its value; no braces, a literal; else a text."""
        from quantum.runtime.gameserver.expressions import literal, parts_of
        parts = parts_of(raw)
        if len(parts) == 1 and parts[0][1] is not None and parts[0][0] == '':
            self.expression(parts[0][1])
        elif all(e is None for _, e in parts):
            self.code.emit('CONST', self.code.const(literal(raw)))
        else:
            self.text(raw)

    def text(self, raw: str) -> None:
        from quantum.runtime.gameserver.expressions import parts_of
        parts = parts_of(raw)
        for lit, expression in parts:
            if expression is None:
                self.code.emit('CONST', self.code.const(lit))
            else:
                self.expression(expression)
        self.code.emit('FORMAT', len(parts))

    def place(self, raw: str) -> None:
        """q:move to= (and q:emit at=): an area's name as written is the area; else the expression's value. Pushes
        two: the kind ('area' or 'value') and it."""
        text = raw.strip()
        c = self.code
        if text in self.definition.map.areas:
            c.emit('CONST', c.const('area'))
            c.emit('CONST', c.const(text))
        else:
            c.emit('CONST', c.const('value'))
            self.evaluate(text)

    def const(self, value: Any) -> None:
        self.code.emit('CONST', self.code.const(value))

    # -- the statements --------------------------------------------------------------------------------------

    def block(self, block) -> None:
        for child in block:
            if _tag(child) in ('elseif', 'else'):
                continue                       # a q:if's own, read by the q:if
            self.statement(child)

    def statement(self, el) -> None:
        c, name, line = self.code, _tag(el), _line_of(el)
        c.emit('LINE', line)
        if name == 'set':
            self.value(el.get('value', ''))
            target = el.get('name') or ''
            if '.' in target:
                c.emit('STORE_PATH', c.const(target.split('.')), c.const(target))
            else:
                c.emit('STORE_NAME', c.name(target))
        elif name == 'if':
            ends = []
            self.evaluate(el.get('condition'))
            otherwise = c.emit('JUMP_IF_FALSE')
            self.block(el)
            ends.append(c.emit('JUMP'))
            c.patch(otherwise, len(c.ops))
            for branch in el:
                kind = _tag(branch)
                if kind == 'elseif':
                    c.emit('LINE', _line_of(branch))
                    self.evaluate(branch.get('condition'))
                    otherwise = c.emit('JUMP_IF_FALSE')
                    self.block(branch)
                    ends.append(c.emit('JUMP'))
                    c.patch(otherwise, len(c.ops))
                elif kind == 'else':
                    self.block(branch)
                    break
            for at in ends:
                c.patch(at, len(c.ops))
        elif name == 'loop':
            var, index = el.get('var'), el.get('index')
            names = (c.name(var or ''), c.name(index) if index else NO_INDEX)
            if el.get('items') is not None:
                self.evaluate(el.get('items'))
                c.emit('LOOP_ITEMS', *names)
            elif el.get('from') is not None and el.get('to') is not None:
                self.evaluate(el.get('from'))
                self.evaluate(el.get('to'))
                c.emit('LOOP_RANGE', *names)
            else:
                c.emit('FAIL', c.const('q:loop needs items=, or from= and to='))
                return
            top = c.emit('FOR_NEXT')
            self.block(el)
            c.emit('JUMP', top)
            c.patch(top, len(c.ops))
        elif name == 'call':
            function = el.get('function')
            if function not in self.definition.functions:
                c.emit('FAIL', c.const(f'q:call: there is no q:function {function!r}'))
                return
            if function not in self.users:
                raise CompileError(f'q:call {function}: that q:function stays the interpreter\'s')
            args = self.arguments(el.get('args', ''))
            c.emit('CALL_STATEMENT', c.name(function), args)
            c.emit('POP')
        elif name == 'return':
            self.value(el.get('value', ''))
            c.emit('RETURN')
        elif name == 'require':
            self.evaluate(el.get('condition'))
            refuse = c.emit('JUMP_IF_FALSE')
            done = c.emit('JUMP')
            c.patch(refuse, len(c.ops))
            self.text(el.get('else', 'Not allowed.'))
            c.emit('REFUSE')
            c.patch(done, len(c.ops))
        elif name in EFFECTS:
            self.effect(name, el, line)
        else:                                # the schema has let nothing else through
            c.emit('FAIL', c.const(f'<q:{name}> does not run in a block'))

    def arguments(self, raw: str) -> int:
        """q:call args=: each {...} an argument; with no braces, expressions separated by commas."""
        from quantum.runtime.gameserver.expressions import parts_of
        expressions = [e for _, e in parts_of(raw) if e is not None]
        if expressions:
            for e in expressions:
                self.expression(e)
            return len(expressions)
        out, depth, current = [], 0, []
        for ch in raw:
            if ch == ',' and depth == 0:
                out.append(''.join(current))
                current = []
                continue
            if ch in '([':
                depth += 1
            elif ch in ')]':
                depth -= 1
            current.append(ch)
        out.append(''.join(current))
        args = [a for a in out if a.strip()]
        for a in args:
            self.evaluate(a)
        return len(args)

    def effect(self, name: str, el, line: int) -> None:
        """What only the world does: its attributes evaluated here, in the interpreter's order, then the host."""
        c = self.code
        count = 0

        def push(value=None, raw=None, how='const'):
            nonlocal count
            if how == 'const':
                self.const(value)
            elif how == 'evaluate':
                self.evaluate(raw)
            elif how == 'value':
                self.value(raw)
            elif how == 'text':
                self.text(raw)
            elif how == 'place':
                self.place(raw)
                count += 1
            count += 1

        push(line)
        if name in ('move', 'travel'):
            push(raw=el.get('entity'), how='evaluate')
            push(raw=el.get('to'), how='place')
            push(el.get('to'))
        elif name == 'emit':
            push(el.get('event'))
            has_value = el.get('value') is not None
            push(has_value)
            push(raw=el.get('value'), how='value') if has_value else push(None)
            if el.get('at') is not None:
                push(raw=el.get('at'), how='place')
            else:
                push(None)
                push(None)
            push(el.get('at'))
            has_to = el.get('to') is not None
            push(has_to)
            push(raw=el.get('to'), how='evaluate') if has_to else push(None)
        elif name == 'kill':
            push(raw=el.get('entity'), how='evaluate')
            has_by = bool(el.get('by'))
            push(has_by)
            push(raw=el.get('by'), how='evaluate') if has_by else push(None)
        elif name == 'loot':
            if el.get('of') is None or el.get('to') is None:
                c.emit('FAIL', c.const('q:loot in a block takes of= and to='))
                return
            push(raw=el.get('of'), how='evaluate')
            push(raw=el.get('to'), how='evaluate')
        elif name in ('give', 'take'):
            push(raw=el.get('to' if name == 'give' else 'from'), how='evaluate')
            if el.get('item') is not None:
                self.evaluate(el.get('item'))                 # the count, only when there is an item
                c.emit('DUP')
                c.emit('CONST', c.const(None))
                c.emit('COMPARE', COMPAREOPS.index(ast.NotEq))
                skip = c.emit('JUMP_IF_FALSE')
                self.evaluate(el.get('count', '1'))
                done = c.emit('JUMP')
                c.patch(skip, len(c.ops))
                c.emit('CONST', c.const(None))
                c.patch(done, len(c.ops))
                count += 2
            else:
                push(None)
                push(None)
            push(raw=el.get('amount'), how='evaluate') if el.get('amount') is not None else push(None)
            push(el.get('currency'))
        elif name == 'pay':
            push(raw=el.get('from'), how='evaluate')
            push(raw=el.get('to'), how='evaluate')
            push(raw=el.get('amount'), how='evaluate')
            push(el.get('currency'))
        elif name == 'say':
            push(el.get('channel', 'system'))
            to = el.get('to', 'all')
            push('all') if to.strip() == 'all' else push(raw=to, how='evaluate')
            push(raw=el.get('text'), how='text')
        elif name == 'ask':
            push(raw=el.get('npc'), how='evaluate')
            c.emit('LOCAL_OR_NULL', c.name('me'))
            count += 1
            push(raw=el.get('text'), how='evaluate')
        elif name == 'reward':
            push(raw=el.get('to'), how='evaluate')
            push(raw=el.get('quest'), how='evaluate')
        elif name == 'spawn':
            from quantum.runtime.gameserver.model import seconds_of
            try:
                ticks = (max(1, round(seconds_of(el.get('for')) * self.definition.tick_rate))
                         if el.get('for') else None)
                many = int(el.get('count', 1))
            except (TypeError, ValueError) as e:      # what the interpreter raises when it runs: it stays its own
                raise CompileError(f'q:spawn: {e}') from None
            push(el.get('entity'))
            push(el.get('area'))
            push(many)
            push(ticks)
        c.emit('EFFECT', c.const(name), count)


def world_expressions(path) -> Dict[str, Optional[int]]:
    """Every expression a world's .q holds, with the line of its first: each attribute's {...}, and the attributes
    the schema reads as an expression (a condition, a loop's items, an entity...). What `quantum gameserver
    bytecode` compiles."""
    from quantum.core.parser import QuantumParser
    from quantum.runtime.gameserver.expressions import parts_of, unbraced
    from quantum.runtime.gameserver.schema import TAGS

    found: Dict[str, Optional[int]] = {}
    for element in QuantumParser(use_cache=False).parse_file(str(path)).xml_root.iter():
        tag = element.tag.split('}')[-1] if isinstance(element.tag, str) else ''
        spec = TAGS.get(tag)
        for attr, raw in element.attrib.items():
            kind = spec.attrs[attr].type if spec is not None and attr in spec.attrs else 'text'
            if kind in ('ident', 'names', 'int', 'bool', 'rate', 'duration') or kind.startswith('enum:'):
                continue
            pieces = [e for _, e in parts_of(raw) if e is not None]
            if kind == 'expr' and not pieces and raw.strip() and raw.strip() != 'all':
                pieces = [unbraced(raw)]
            for e in pieces:
                found.setdefault(e, getattr(element, 'sourceline', None))
    return found


def world_blocks(definition) -> List[Tuple[str, Any]]:
    """Every block of a world, named as a reader finds it: its q:commands, q:functions, q:every, q:on-join,
    q:on-leave and q:on-death."""
    blocks: List[Tuple[str, Any]] = []
    blocks += [(f'q:command {name}', c.body) for name, c in definition.commands.items() if c.body is not None]
    blocks += [(f'q:function {name}', f.body) for name, f in definition.functions.items()]
    blocks += [(f'q:every {ticks} ticks', body) for ticks, body in definition.every]
    blocks += [('q:on-join', body) for body in definition.on_join]
    blocks += [('q:on-leave', body) for body in definition.on_leave]
    blocks += [(f'q:on-death {" ".join(d.kinds)}', d.body) for d in definition.deaths]
    return blocks


def main(args) -> int:
    """`quantum gameserver bytecode FILE`: each expression of the world as the machine runs it; with --blocks, each
    block (a q:command's, a q:function's, a rule's) whole."""
    from quantum.runtime.gameserver.errors import GameServerError
    from quantum.runtime.gameserver.server import load
    from quantum.runtime.gameserver.world import World

    try:
        definition = load(args.file)
    except GameServerError as e:
        print(f'[ERROR] {e}')
        return 1
    rules = World(definition).rules
    if getattr(args, 'blocks', False):
        own, users = world_function_names(rules), frozenset(definition.functions)
        blocks = world_blocks(definition)
        refused = 0
        for where, block in blocks:
            try:
                code = compile_block(block, definition, own, users, where)
            except CompileError as e:
                refused += 1
                print(f'; {where}\n  stays the interpreter\'s: {e}\n')
                continue
            if not args.summary:
                print(code.disassemble() + '\n')
        print(f'[OK] {definition.name}: {len(blocks) - refused} of {len(blocks)} blocks compiled to bytecode'
              + (f'; {refused} stay the interpreter\'s' if refused else ''))
        return 0
    hosted = world_host_names(rules)
    expressions = [args.expression] if args.expression else list(world_expressions(args.file))
    refused = 0
    for expression in expressions:
        try:
            code = compile_expression(expression, hosted)
        except CompileError as e:
            refused += 1
            print(f'; {expression}\n  stays the interpreter\'s: {e}\n')
            continue
        if not args.summary:
            print(code.disassemble() + '\n')
    print(f'[OK] {definition.name}: {len(expressions) - refused} of {len(expressions)} expressions compiled to '
          f'bytecode' + (f'; {refused} stay the interpreter\'s' if refused else ''))
    return 0
