"""The rules as bytecode (PLAN_WORLD_ENGINE.md, E2): bytecode.py compiles a world's expressions, the Rust engine's
machine runs them, and they give what the interpreter gives.

Held three ways: every expression of the test worlds and of Outpost compiles; a session of each world, every
expression it evaluates run again on the machine (the world's random put back between the two, so both draw the same
numbers), gives the same value or the same error, word for word; and expressions drawn from the grammar (the Core's
operators and stdlib over numbers, texts, numeric texts, lists, records and null) agree, to the error's text and
type, twenty thousand here and a million by `python scripts/bytecode-fuzz.py`. The machine's random is Python's,
word for word. The blocks (tests/gameserver/test_gameserver_blocks.py) are held to the interpreter tick by tick.
"""

import math
import random
from collections import ChainMap

import pytest
from test_gameserver_conform import WORLDS, definition_of, session

from quantum.core.expressions import ExpressionError, UndefinedError
from quantum.runtime.gameserver import World
from quantum.runtime.gameserver import bytecode
from quantum.runtime.gameserver.expressions import WorldEvaluator
from quantum.runtime.gameserver.machine import WorldMachine, quantum_world

needs_rust = pytest.mark.skipif(quantum_world is None, reason='the Rust engine is not built here (pip install ./native/world)')
ALL_WORLDS = {**WORLDS, 'yard': WORLDS['meadow'].parents[1] / 'yard' / 'yard.server.q'}


def same(a, b) -> bool:
    """Equal as values and as types: 1, 1.0 and True are three; a float by its repr; a record's keys in order; an
    entity is the world's own dict."""
    if type(a) is not type(b):
        return False
    if isinstance(a, float):
        return repr(a) == repr(b)
    if isinstance(a, (list, tuple)):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    if isinstance(a, dict):
        if 'id' in a and isinstance(a.get('_type'), str):
            return a is b
        return list(a) == list(b) and all(same(a[k], b[k]) for k in a)
    return a == b


def outcome(run):
    """What an evaluation gives: its value, or its error word for word (an UndefinedError, an ExpressionError, or
    what Python raises past the Core: a TypeError of `-[1]`)."""
    try:
        return 'value', run()
    except UndefinedError as e:
        return 'undefined', str(e)
    except ExpressionError as e:
        return 'error', str(e)
    except (TypeError, ValueError, ArithmeticError) as e:
        return 'raised', f'{type(e).__name__}: {e}'


def test_the_machine_knows_the_compilers_instructions():
    if quantum_world is not None:
        assert quantum_world.OPCODES == [name for name, _ in bytecode.OPCODES]
    code = bytecode.compile_expression('1 < x <= 3')
    assert code.disassemble().splitlines()[1:6] == [
        '   0  CONST                 1', '   1  NAME                  x', '   2  DUP                   ',
        '   3  ROT3                  ', '   4  COMPARE               <']


@pytest.mark.parametrize('name', sorted(ALL_WORLDS))
def test_every_expression_of_a_world_compiles(name):
    definition = definition_of(name) if name in WORLDS else _definition(ALL_WORLDS[name])
    hosted = bytecode.world_host_names(World(definition).rules)
    found = bytecode.world_expressions(ALL_WORLDS[name])
    assert len(found) >= 15
    refused = {}
    for expression in found:
        try:
            bytecode.compile_expression(expression, hosted)
        except bytecode.CompileError as e:
            refused[expression] = str(e)
    assert not refused, refused


def _definition(path):
    from quantum.core.parser import QuantumParser
    from quantum.runtime.gameserver import read_world
    return read_world(QuantumParser(use_cache=False).parse_file(str(path)), str(path))


@needs_rust
@pytest.mark.parametrize('name', sorted(WORLDS))
def test_a_worlds_expressions_give_the_same_on_the_machine(name, monkeypatch):
    """A session that sends every kind of command: each expression the world evaluates (a command's, a rule's, a
    brain's, a view's) run on the machine as well, from the same random, gives the same value or the same refusal,
    and leaves the random where the interpreter left it. A q:function runs blocks (and writes): those wait for E2's
    blocks."""
    definition = definition_of(name)
    held = {'world': None, 'machine': None}
    checked, values, differences, users = set(), [0], [], set(definition.functions)
    original = WorldEvaluator.evaluate

    def both(self, expression, context, absent_scope_key_is_none=False):
        world, machine = held['world'], held['machine']
        if world is None or machine is None:                   # the world being made: its first variables
            return original(self, expression, context, absent_scope_key_is_none)
        before = world.rng.getstate()
        try:
            result = original(self, expression, context, absent_scope_key_is_none)
            failure = None
        except ExpressionError as e:
            result, failure = None, e
        after = world.rng.getstate()
        if (isinstance(context, ChainMap) and context.maps[-1] is world.vars and machine.code(expression) is not None
                and not (users & set(bytecode.compile_expression(expression, machine.names).names))):
            world.rng.setstate(before)
            local = context.maps[0]
            mine = outcome(lambda: machine.evaluate(expression, local))
            theirs = ('undefined' if isinstance(failure, UndefinedError) else 'error', str(failure)) if failure \
                else ('value', result)
            if mine[0] != theirs[0] or not same(mine[1], theirs[1]) or world.rng.getstate() != after:
                differences.append((expression, theirs, mine))
            checked.add(expression)
            values[0] += 1
            world.rng.setstate(after)
        if failure is not None:
            raise failure
        return result

    monkeypatch.setattr(WorldEvaluator, 'evaluate', both)

    class Held(World):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            held['world'] = self
            held['machine'] = WorldMachine(self)

    import test_gameserver_conform
    monkeypatch.setattr(test_gameserver_conform, 'World', Held)
    session(definition, ticks=200, players=8, seed=31)
    assert not differences, differences[:5]
    assert len(checked) >= 10 and values[0] >= 500


# -- expressions drawn from the grammar --------------------------------------------------------------------------

TEXTS = ['', 'a', 'ab', '5', ' 3 ', '2.5', '-7', '1_000', 'x y', "it's", 'é', '10', '9', 'True', 'none']
FUNCTIONS = {'len': 1, 'first': 1, 'last': 1, 'join': 2, 'sort': 1, 'get': 3, 'round': 2, 'ceil': 1, 'floor': 1,
             'abs': 1, 'min': 2, 'max': 2, 'int': 1, 'float': 1, 'str': 1, 'upper': 1, 'lower': 1, 'trim': 1,
             'replace': 3, 'split': 2, 'contains': 2, 'sqrt': 1}


class Drawer:
    """Random expressions over a random context: what the Core's grammar allows, small enough to stay in 64 bits."""

    def __init__(self, rng: random.Random):
        self.rng = rng

    def value(self, depth=0):
        r = self.rng.random()
        if r < 0.25:
            return self.rng.choice([0, 1, 2, 3, -1, 7, 10, 255, -40])
        if r < 0.4:
            return self.rng.choice([0.0, 0.5, -2.25, 1.5, 3.0, 1e3, 0.1, -0.0])
        if r < 0.6:
            return self.rng.choice(TEXTS)
        if r < 0.67:
            return self.rng.choice([True, False, None])
        if depth > 1:
            return 1
        if r < 0.85:
            return [self.value(depth + 1) for _ in range(self.rng.randint(0, 4))]
        return {self.rng.choice(['a', 'b', 'k', '5']): self.value(depth + 1) for _ in range(self.rng.randint(0, 3))}

    def context(self):
        return {name: self.value() for name in ('a', 'b', 'c', 's', 'l', 'd')}

    def literal(self):
        v = self.rng.choice([0, 1, 2, 3, -1, 10, 0.5, -2.25, 1.5, 'a', '5', ' 2 ', 'x', True, False, None])
        if v is True:
            return self.rng.choice(['true', 'True'])
        if v is False:
            return self.rng.choice(['false', 'False'])
        if v is None:
            return self.rng.choice(['null', 'None'])
        return repr(v)

    def expr(self, depth=0):
        if depth > 3 or self.rng.random() < 0.3:
            return self.rng.choice([self.literal(), self.rng.choice(['a', 'b', 'c', 's', 'l', 'd'])])
        e = lambda: self.expr(depth + 1)  # noqa: E731
        kind = self.rng.random()
        if kind < 0.25:
            return f'({e()} {self.rng.choice(["+", "-", "*", "/", "//", "%", "+", "+"])} {e()})'
        if kind < 0.3:
            return f'({e()} ** {self.rng.choice(["0", "1", "2", "3", "-1", "0.5"])})'
        if kind < 0.45:
            ops = ['<', '<=', '==', '!=', '>', '>=', 'in', 'not in']
            chain = e()
            for _ in range(self.rng.randint(1, 2)):
                chain += f' {self.rng.choice(ops)} {e()}'
            return f'({chain})'
        if kind < 0.53:
            return f'({e()} {self.rng.choice(["and", "or", "&&", "||"])} {e()})'
        if kind < 0.58:
            return f'({self.rng.choice(["-", "+", "not ", "!"])}{e()})'
        if kind < 0.62:
            return f'({e()} if {e()} else {e()})'
        if kind < 0.68:
            return self.rng.choice([f'{e()}[{e()}]', f"d[{self.rng.choice(['a', 'k', '5'])!r}]",
                                    f'l[{self.rng.randint(-3, 3)}]', f'{e()}[{self.rng.randint(-2, 2)}:]',
                                    f'l[:{self.rng.randint(-2, 3)}]', f's[{self.rng.randint(0, 2)}:{e()}]'])
        if kind < 0.72:
            return self.rng.choice([f'{e()}.length', 'd.a', 'd.k', 'l.length', 's.length'])
        if kind < 0.78:
            return self.rng.choice([f'[{e()}, {e()}]', f'({e()}, {e()})', '[]', f"{{'a': {e()}, 'b': {e()}}}",
                                    f'({e()},)'])
        name = self.rng.choice(list(FUNCTIONS))
        n = self.rng.randint(1, FUNCTIONS[name])
        args = ', '.join(e() for _ in range(n))
        if name == 'sort' and self.rng.random() < 0.3:
            args += f', reverse={self.rng.choice(["true", "false"])}'
        if name in ('min', 'max') and self.rng.random() < 0.2:
            args = f'[{args}], default=0'
        return f'{name}({args})'


class _Plain:
    """A host with no world: what the drawn expressions have."""

    def variable(self, name):
        return False, None

    def field(self, eid, key):
        return False, None

    def keys(self, eid):
        return []

    def call(self, name, args, kwargs):
        raise ExpressionError(f'function {name!r} is not defined')


def draw(count: int, seed: int):
    """Draws count expressions and contexts; the ones that differ, and how many each way."""
    interpreter = WorldEvaluator(functions={'sqrt': math.sqrt})
    machine = quantum_world.Machine()
    host, codes = _Plain(), {}
    rng = random.Random(seed)
    drawer = Drawer(rng)
    differences, tally = [], {'value': 0, 'undefined': 0, 'error': 0, 'raised': 0, 'past 64 bits': 0, 'complex': 0,
                              'refused': 0}
    for _ in range(count):
        expression, context = drawer.expr(), drawer.context()
        theirs = outcome(lambda: interpreter.evaluate(expression, context))
        if expression not in codes:
            try:
                code = bytecode.compile_expression(expression)
                codes[expression] = machine.load(code.ops, code.consts, code.names)
            except bytecode.CompileError:
                codes[expression] = None
        if codes[expression] is None:
            tally['refused'] += 1
            continue
        try:
            mine = ('value', machine.run(codes[expression], context, host, {}))
        except quantum_world.MachineError as e:
            if 'past 64 bits' in e.args[1]:
                tally['past 64 bits'] += 1               # Python's whole numbers have no end; the engine's 64 bits
                continue
            if 'complex number' in e.args[1]:
                tally['complex'] += 1                    # (-8) ** 0.5 is a complex to Python: no world keeps one
                continue
            mine = ('undefined' if e.args[0] == 'undefined' else 'error', e.args[1])
        except (TypeError, ValueError, ArithmeticError) as e:
            mine = ('raised', f'{type(e).__name__}: {e}')
        if mine[0] != theirs[0] or not same(mine[1], theirs[1]):
            differences.append((expression, context, theirs, mine))
        tally[theirs[0]] += 1
    return differences, tally


@needs_rust
def test_expressions_drawn_from_the_grammar_agree():
    differences, tally = draw(20_000, seed=5)
    assert not differences, differences[:5]
    assert tally['value'] > 6000 and tally['error'] > 2000, tally
    assert tally['past 64 bits'] + tally['complex'] < 0.01 * sum(tally.values()), tally


@needs_rust
def test_the_machines_random_is_pythons():
    for seed in (0, 1, 7, 2 ** 31 - 1, 2 ** 40):
        mine, theirs = quantum_world.Rng(seed), random.Random(seed)
        for k in range(3000):
            if k % 3 == 0:
                assert mine.random() == theirs.random()
            elif k % 3 == 1:
                assert mine.randint(-3, 10 ** 9) == theirs.randint(-3, 10 ** 9)
            else:
                n = 1 + k % 977
                assert mine.randrange(n) == theirs.randrange(n)
        assert mine.state() == list(theirs.getstate()[1])
    theirs = random.Random(12)
    theirs.random()
    mine = quantum_world.Rng.from_state(list(theirs.getstate()[1]))       # a world's state, from its snapshot
    assert [mine.random() for _ in range(700)] == [theirs.random() for _ in range(700)]
    with pytest.raises(ValueError):
        mine.randint(5, 4)
