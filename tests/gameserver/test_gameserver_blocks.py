"""The world's blocks as bytecode (PLAN_WORLD_ENGINE.md, E2): a q:command's, a q:every's, a q:function's statements
compiled by bytecode.py and run whole on the Rust engine's machine (machine.py's MachineWorld), the world its host.

Held two ways. A session of each world (meadow, den, Outpost: players who send every command, beasts that live and
die, the ledger, chat, quests) run on the machine and on the interpreter gives the same world on every tick: its
digest, acks, refusals, frames, and the errors it keeps, word for word. And a world of cases, a command each, sends
each statement what it is hardest to run: loops over every kind of value and of every length, q:set into names,
fields, records and the world's variables (and where it may not), q:if chains that fail in an elseif, q:require's
texts, q:call with too few arguments and too deep, a q:function failing inside an expression, Python's own
TypeError and ValueError: the same outcome on both.
"""

import shutil
from pathlib import Path

import pytest
from test_gameserver_conform import WORLDS, definition_of, session

from quantum.core.parser import QuantumParser
from quantum.runtime.gameserver import World, read_world
from quantum.runtime.gameserver.bytecode import compile_block
from quantum.runtime.gameserver.conform import ENGINES, conform
from quantum.runtime.gameserver.machine import MachineWorld, quantum_world

pytestmark = pytest.mark.skipif(quantum_world is None, reason='the Rust engine is not built here (pip install ./native/world)')
YARD = Path(__file__).resolve().parent / 'worlds' / 'yard'

# a command each: its body, and what x is sent as, one tick each
CASES = {
    'loop_items': ('<q:set name="out" value="" />'
                   '<q:loop items="{x}" var="v" index="i"><q:set name="out" value="{out}{i}={v};" /></q:loop>'
                   '<q:set name="me.name" value="{out}" />',
                   [[1, 2.0, 'a', None, True, [3]], {'a': 1, 'b': [2]}, 'héllo', '', 5, None, True, [], 2.5]),
    'loop_entity': ('<q:set name="n" value="0" />'
                    '<q:loop items="{me}" var="v"><q:set name="n" value="{n + 1}" /></q:loop>'
                    '<q:set name="me.steps" value="{n}" />', [0]),
    'loop_range': ('<q:set name="t" value="0" />'
                   '<q:loop var="k" from="{x[0]}" to="{x[1]}" index="i"><q:set name="t" value="{t + k * 10 + i}" />'
                   '</q:loop><q:set name="me.steps" value="{t}" />',
                   [[1, 3], [3, 1], [1.9, 3.7], ['2', ' 4 '], [-2, 1], [True, 3], [1, 100001], [0, 99999],
                    ['x', 3], [None, 1], [1, [2]]]),
    'loop_nested': ('<q:set name="out" value="" />'
                    '<q:loop var="i" from="1" to="2"><q:loop items="{x}" var="v">'
                    '<q:set name="out" value="{out}{i}{v}" /></q:loop></q:loop><q:set name="me.name" value="{out}" />',
                    [['a', 'b'], []]),
    'loop_shadow': ('<q:loop items="{x}" var="visits"><q:set name="visits" value="{visits + 1}" /></q:loop>'
                    '<q:set name="visits" value="{visits + 100}" />', [[1, 2], []]),
    'set_world': ('<q:set name="visits" value="{visits + x}" /><q:set name="tmp" value="{x}" />'
                  '<q:set name="me.name" value="{tmp}" />', [1, 'a', 2.5]),
    'set_field': ('<q:set name="me.steps" value="{x}" /><q:set name="me.mood" value="{x}" />',
                  [3, [1, 2.0], {'a': {'b': None}}, 'loud']),
    'set_infinite': ('<q:set name="me.steps" value="{float(x)}" />', ['inf', '1.5']),
    'set_read_only': ('<q:set name="me.id" value="{x}" />', [1]),
    'set_private': ('<q:set name="me._at" value="{x}" />', [1]),
    'set_record': ('<q:set name="r" value="{ {\'a\': {\'b\': 1}} }" /><q:set name="r.a.b" value="{x}" />'
                   '<q:set name="r.c" value="{x}" /><q:set name="me.name" value="{r}" />', [7, 'z']),
    'set_not_record': ('<q:set name="n" value="{x}" /><q:set name="n.a" value="1" />', [1, 'a', [1], {'b': 2}]),
    'set_deeper': ('<q:set name="r" value="{ {\'a\': x} }" /><q:set name="r.a.b" value="1" />', [1, {'c': 0}]),
    'set_world_record': ('<q:set name="book.page" value="{x}" /><q:set name="book.notes.a" value="{x}" />',
                         [2, 'ten']),
    'set_nowhere': ('<q:set name="nothing.a" value="{x}" />', [1]),
    'if_chain': ('<q:if condition="{x == 0}"><q:set name="me.name" value="zero" />'
                 '<q:elseif condition="{x.k > 1}"><q:set name="me.name" value="big" /></q:elseif>'
                 '<q:elseif condition="{x.k == 1}"><q:set name="me.name" value="one" /></q:elseif>'
                 '<q:else><q:set name="me.name" value="small" /></q:else></q:if>',
                 [0, {'k': 2}, {'k': 1}, {'k': 0}, 5, {'j': 1}, {'kk': 1}, None]),
    'require': ('<q:require condition="{x}" else="No {x} here, {me.name}." /><q:set name="me.steps" value="1" />',
                [0, '', [], 1, None, 2.0]),
    'require_plain': ('<q:require condition="{x}" />', [0, 1]),
    'call_short': ('<q:call function="pair" args="{x}" />', [1]),
    'call_commas': ('<q:call function="pair" args="x, x + 1" />', [1, 'a']),
    'call_deep': ('<q:call function="deep" args="{x}" />', [3, 63, 64, 70]),
    'expression_deep': ('<q:set name="me.steps" value="{depth_of(x)}" />', [5, 63, 64, 70]),
    'expression_refused': ('<q:set name="me.steps" value="{boom(x)}" />', [0, 1]),
    'expression_short': ('<q:set name="me.steps" value="{pair(x)}" />', [1]),
    'return_in_loop': ('<q:set name="me.steps" value="{first_big(x)}" />', [[1, 5, 9], [1], 'abc', 7]),
    'no_return': ('<q:set name="me.name" value="{nothing_back(x)}" />', [1]),
    'text': ('<q:set name="me.name" value="{x}|{me.steps}|{1.0}|{true}|{null}|{[1.0, true]}|{1e20}|{2.5}|{-0.0}" />',
             [1, 2.0, 'a', None, True, [1, 2.0], 1e300, {'k': [None]}]),
    'text_entity': ('<q:emit event="seen" value="I am {me}" />', [0]),
    'literal': ('<q:set name="me.name" value="42" /><q:set name="me.mood" value="true" />'
                '<q:set name="me.steps" value=" 7 " />', [0]),
    'emit': ('<q:emit event="spot" value="{ {\'x\': x} }" at="{me}" /><q:emit event="all" value="{x}" />',
             [1, 'two']),
    'emit_to': ('<q:emit event="note" value="{x}" to="{x}" />', ['hero:p1', 'nobody', 3]),
    'emit_at': ('<q:emit event="here" at="{x}" />', ['pen', 'hero:p1', [3, 3], 'nowhere']),
    'move': ('<q:move entity="{me}" to="{x}" />', ['pen', 'gate', [3, 3], {'x': 2, 'y': 2}, 'nowhere', 5]),
    'move_named': ('<q:move entity="{me}" to="pen" /><q:move entity="{x}" to="gate" />', ['hero:p1', 'nobody']),
    'say': ('<q:say channel="news" text="{x} and {me.name}" /><q:say to="{me}" text="you {x}" />', [1, None]),
    'unary': ('<q:set name="me.steps" value="{-x}" />', ['5', [1]]),
    'suggest_field': ('<q:set name="me.steps" value="{me.step + x}" />', [1]),
    'suggest_variable': ('<q:set name="me.steps" value="{visit + x}" />', [1]),
    'suggest_record': ('<q:set name="me.steps" value="{book.pag + x}" />', [1]),
    'method': ('<q:set name="me.steps" value="{x.bit_length}" />', [3]),
}

FUNCTIONS = '''
    <q:function name="pair" params="a, b"><q:set name="visits" value="{visits + 1}" /></q:function>
    <q:function name="deep" params="n">
      <q:set name="visits" value="{visits + 1}" />
      <q:if condition="{n > 0}"><q:call function="deep" args="{n - 1}" /></q:if>
    </q:function>
    <q:function name="depth_of" params="n">
      <q:if condition="{n &lt;= 0}"><q:return value="0" /></q:if>
      <q:return value="{depth_of(n - 1) + 1}" />
    </q:function>
    <q:function name="boom" params="n">
      <q:require condition="{n > 0}" else="no {n}" />
      <q:return value="{n * missing}" />
    </q:function>
    <q:function name="first_big" params="items">
      <q:loop items="{items}" var="v"><q:if condition="{v > 2}"><q:return value="{v}" /></q:if></q:loop>
      <q:return value="-1" />
    </q:function>
    <q:function name="nothing_back" params="n"><q:set name="visits" value="{visits + n}" /></q:function>
'''


@pytest.fixture(scope='module')
def cases(tmp_path_factory):
    """The world of cases: the yard's map, a command each."""
    folder = tmp_path_factory.mktemp('cases')
    shutil.copy(YARD / 'yard.tmx', folder / 'yard.tmx')
    commands = '\n'.join(f'    <q:command name="{name}" params="x">{body}</q:command>'
                         for name, (body, _) in CASES.items())
    source = f'''<q:application id="cases-server" type="gameserver">
  <q:gameserver name="cases" tick="10" players="4">
    <q:map name="yard" tiled="yard.tmx" />
    <q:set name="visits" value="0" />
    <q:set name="book" value="{{ {{'page': 1, 'notes': {{'a': 0}}}} }}" />
    <q:entity name="hero" kind="Hero" per-player="true">
      <q:field name="name" value="{{account.name}}" />
      <q:field name="steps" value="0" />
    </q:entity>
{commands}
{FUNCTIONS}
    <q:on-join><q:move entity="{{me}}" to="gate" /></q:on-join>
  </q:gameserver>
</q:application>
'''
    path = folder / 'cases.server.q'
    path.write_text(source, encoding='utf-8')
    return read_world(QuantumParser(use_cache=False).parse_file(str(path)), str(path))


def outcome(run, inputs):
    """What a tick gives on an engine: what came out of it, the errors the world kept, its digest; or what it
    raised (Python's own error, which the world does not catch)."""
    try:
        out = run.step(inputs)
    except Exception as e:  # noqa: BLE001 - the same on both is the point
        return 'raised', type(e).__name__, str(e)
    return out, run.world.errors[-3:], run.digest()


@pytest.mark.parametrize('name', sorted(CASES))
def test_each_statement_gives_the_same_on_the_machine(cases, name):
    python, machine = ENGINES['python'](cases), ENGINES['machine'](cases)
    assert isinstance(machine.world, MachineWorld)
    command = cases.commands[name].body
    assert machine.world.rules.block(command) is not None, machine.world.rules.refused    # on the machine
    for run in (python, machine):
        run.step([('join', 'p1')])
    for seq, x in enumerate(CASES[name][1], 1):
        theirs = outcome(python, [('cmd', 'p1', seq, name, {'x': x})])
        mine = outcome(machine, [('cmd', 'p1', seq, name, {'x': x})])
        assert mine == theirs, f'{name}({x!r})'
        if theirs[0] == 'raised':
            break


def test_the_cases_say_what_went_wrong_as_the_interpreter_says_it(cases):
    """A few of the cases' errors, as the world keeps them: the line, and the Core's words."""
    run = ENGINES['machine'](cases)
    run.step([('join', 'p1')])
    said = {}
    for seq, (name, x) in enumerate([('call_deep', 70), ('expression_refused', 0), ('suggest_field', 1),
                                     ('loop_range', [1, 100001]), ('set_read_only', 1), ('if_chain', 5)], 1):
        run.step([('cmd', 'p1', seq, name, {'x': x})])
        said[name] = run.world.errors[-1]['message']
    assert said['call_deep'] == 'deep(): calls nested 64 deep'
    assert said['expression_refused'] == 'boom() failed: no 0'
    assert said['suggest_field'] == "key 'step' not found, did you mean 'steps'?"
    assert said['loop_range'] == 'q:loop of 100001 turns: a tick holds 100000 at most'
    assert said['set_read_only'] == 'q:set name="me.id": an entity\'s id is the world\'s'
    assert said['if_chain'] == "attribute 'k' not found on int"


@pytest.mark.parametrize('name', sorted(WORLDS))
def test_a_worlds_sessions_run_the_same_on_the_machine(name, monkeypatch):
    """A session of each world on both engines, its digest compared on every tick; then the same session played on
    each, the errors each world kept the same, word for word."""
    definition = definition_of(name)
    entries, world = session(definition, ticks=300, players=8, seed=7)
    report = conform(definition, None, entries, ['python', 'machine'], digest_every=1)
    assert report.same, '\n'.join(map(str, report.differences[:3]))
    import test_gameserver_conform
    monkeypatch.setattr(test_gameserver_conform, 'World', MachineWorld)
    again, on_machine = session(definition, ticks=300, players=8, seed=7)
    assert again == entries
    assert on_machine.errors == world.errors and on_machine.digest() == world.digest()
    rules = on_machine.rules
    blocks = [c.body for c in definition.commands.values() if c.body is not None]
    assert blocks and all(rules.block(b) is not None for b in blocks), rules.refused
    assert rules.users == frozenset(definition.functions)                    # every q:function on the machine


def test_an_entity_killed_in_a_loop_is_still_what_it_was():
    """The den's blow a second: a q:loop over those fighting, where a rat struck dead earlier in the loop is still
    its dict to the rest of it (`entity(a.id)` null: it strikes no one), as it is to Python. Held by id alone, it
    was not there to read, and the rat never died."""
    definition = definition_of('den')
    ends = []
    for kind in (World, MachineWorld):
        world = kind(definition)
        world.step([('join', 'ana')])
        world.step([('cmd', 'ana', 1, 'go', {'to': {'x': 19, 'y': 21}})])
        for _ in range(60):
            world.step([])
        rat = next(e['id'] for e in world.entities.values() if e.get('kind') == 'Rat')
        for seq in range(2, 200):
            world.step([('cmd', 'ana', seq, 'attack', {'who': rat})])
            if rat not in world.entities:
                break
        hero = world.entities['hero:ana']
        ends.append((world.tick, hero['bag'], hero['kills'], world.errors, world.digest()))
    assert ends[0] == ends[1]
    assert ends[0][1] == {'cheese': 1} and ends[0][2] == 1 and not ends[0][3]


def test_a_block_the_compiler_refuses_stays_the_interpreters(cases, monkeypatch):
    """A block with what the machine does not hold (here: a set) runs on the interpreter, and what it calls with it;
    the world is the same."""
    from quantum.runtime.gameserver import bytecode

    real = bytecode.compile_block

    def refusing(block, *args, **kwargs):
        if block is cases.commands['loop_items'].body:
            raise bytecode.CompileError('a set (for this test)')
        return real(block, *args, **kwargs)

    monkeypatch.setattr('quantum.runtime.gameserver.machine.compile_block', refusing)
    python, machine = ENGINES['python'](cases), ENGINES['machine'](cases)
    for run in (python, machine):
        run.step([('join', 'p1')])
    assert machine.world.rules.block(cases.commands['loop_items'].body) is None
    for seq, x in enumerate([[1, 'b'], 3], 1):
        assert outcome(machine, [('cmd', 'p1', seq, 'loop_items', {'x': x})]) == \
            outcome(python, [('cmd', 'p1', seq, 'loop_items', {'x': x})])


def test_a_blocks_code_reads_as_its_statements(cases):
    code = compile_block(cases.commands['require'].body, cases, frozenset(), frozenset())
    text = code.disassemble()
    for op in ('LINE', 'JUMP_IF_FALSE', 'FORMAT', 'REFUSE', 'STORE_PATH'):
        assert op in text
    assert World(cases).rules.__class__.__name__ == 'Interpreter'                    # the default stays Python's
