"""Statements and actions, compiled to GDScript.

A scene's logic becomes one script, `extends` the runtime's QuantumScene:
its `q:set`s are properties, its `q:function`s are methods, and every
handler (a `qg:on-collision`) is a method the runtime calls by name with
`(me, other)`. The scene script also reports its state for the replay
harness (`_q_state`).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from quantum.runtime.godot import gd as gdprops
from quantum.runtime.godot.errors import GameCompileError
from quantum.runtime.godot.expressions import (
    GD_TYPES, Scope, compile_expression, gdscript_literal, strip_braces,
)
from quantum.runtime.godot.model import Element, Node, Statement

_INDENT = '\t'

# Names a scene script may not declare: what every Node2D already has (its
# properties, methods and signals, from Godot's own reference — a variable
# named like one is a GDScript error), and what the runtime's scripts use.
RESERVED_NAMES = frozenset((
    'self', 'rng', 'state', 'health', 'tag', 'speed', 'velocity', 'heading', 'player',
)) | gdprops.members_of('Node2D')


@dataclass
class StateVar:
    name: str
    type: str
    initial: str   # GDScript literal
    line: Optional[int]
    persist: bool = False   # game state kept between runs (q:set saved="true")
    typed: bool = True      # type= written: the GDScript variable is typed; else Variant

    @property
    def gd_type(self) -> str:
        return GD_TYPES.get(self.type, 'Variant') if self.typed else 'Variant'


@dataclass
class SceneScript:
    """The GDScript of one scene, built up by the compiler."""
    name: str
    game_state: Dict[str, 'StateVar'] = field(default_factory=dict)
    state: Dict[str, StateVar] = field(default_factory=dict)
    functions: List[str] = field(default_factory=list)   # compiled func blocks
    handlers: List[str] = field(default_factory=list)
    function_names: List[str] = field(default_factory=list)
    sounds_played: List[str] = field(default_factory=list)
    prefabs_used: List[tuple] = field(default_factory=list)   # (name, line) from spawn/swap
    particles_used: List[tuple] = field(default_factory=list)  # (name, line) from qg:emit
    animations_played: List[tuple] = field(default_factory=list)  # (name, line) from qg:play-animation
    items_used: List[tuple] = field(default_factory=list)  # (item, line) from qg:give and qg:take
    states_used: List[tuple] = field(default_factory=list)    # (name, line) from become
    scenes_used: List[tuple] = field(default_factory=list)    # (name, line) from goto-scene
    paths_used: List[tuple] = field(default_factory=list)     # (name, line) from spawn at="path"
    dialogues_used: List[tuple] = field(default_factory=list)  # (name, line) from qg:say
    net_used: List[Optional[int]] = field(default_factory=list)   # lines of qg:host, qg:join, qg:leave
    tween_ends: int = 0   # the qg:on-end handlers of tweens so far: each its own method, nested ones too
    afters: int = 0       # the qg:afters so far: what each puts off is its own method

    node_ids: List[str] = field(default_factory=list)   # the scene's characters, by id
    game_functions: List[str] = field(default_factory=list)   # the q:functions of <q:application>, every scene's
    game_wide: bool = False   # compiling one of those: it sees the game's state and functions, not the scene's
    node_fields: Dict[str, frozenset] = field(default_factory=dict)   # a character id -> its controller's fields
    actions: Optional[List[str]] = None   # the game's actions, for pressing('run') and the like

    def scope(self) -> Scope:
        if self.game_wide:
            return Scope((), functions=self.game_functions, game_names=self.game_state.keys(),
                         actions=self.actions)
        return Scope(self.state.keys(), functions=self.function_names, game_names=self.game_state.keys(),
                     node_ids=self.node_ids, node_fields=self.node_fields, actions=self.actions)

    enter: List[Node] = field(default_factory=list)   # statements directly in the scene: run on enter

    def source(self) -> str:
        lines = ['extends "res://addons/quantum/quantum_scene.gd"',
                 '# Compiled by Quantum from the scene; do not edit.', '']
        for var in self.state.values():
            lines.append(f'var {var.name}: {var.gd_type} = {var.initial}')
        lines.append('')
        if self.enter:
            lines.append('func _q_enter() -> void:')
            lines.append(compile_block(self.enter, self.scope(), self, 1).rstrip('\n'))
            lines.append('')
        lines.append('func _q_state() -> Dictionary:')
        if self.state:
            items = ', '.join(f'"{v.name}": {v.name}' for v in self.state.values())
            lines.append(f'{_INDENT}return {{{items}}}')
        else:
            lines.append(f'{_INDENT}return {{}}')
        lines.append('')
        for block in self.functions + self.handlers:
            lines.append(block)
            lines.append('')
        return '\n'.join(lines).rstrip('\n') + '\n'


def is_expression(value: str) -> bool:
    v = value.strip()
    return v.startswith('{') and v.endswith('}')


def declare_state(script: SceneScript, st: Statement) -> None:
    """A q:set directly in the scene declares a state variable."""
    name = st.attrs['name']
    if name in script.state:
        raise GameCompileError(f'{name!r} is declared twice', st.line)
    if name in script.game_state:
        raise GameCompileError(f'{name!r} is already the game\'s state (a q:set in <q:application>)', st.line)
    if name in RESERVED_NAMES:
        raise GameCompileError(
            f'{name!r} is a property of every Godot node; a game state needs another name', st.line)
    type_name = st.attrs.get('type', 'string')
    if type_name not in GD_TYPES:
        raise GameCompileError(
            f'type="{type_name}": a game state is number, string, boolean or array', st.line)
    value = st.attrs.get('value', st.attrs.get('default'))
    if value is not None and is_expression(value):
        initial = compile_expression(value, script.scope(), st.line)
    else:
        if value is None:
            value = {'number': '0', 'boolean': 'false', 'array': '[]'}.get(type_name, '')
        try:
            initial = gdscript_literal(value, type_name)
        except GameCompileError as e:
            raise GameCompileError(e.message, st.line)
    persist = str(st.attrs.get('saved', 'false')).lower() in ('true', '1', 'yes')
    if persist and script.name != 'game':
        raise GameCompileError('saved= is for the game state (a q:set in <q:application>)', st.line)
    script.state[name] = StateVar(name, type_name, initial, st.line, persist, typed='type' in st.attrs)


def _literal_type(value: str) -> str:
    """What a bare literal is, for a variable no q:set typed: true/false, a number, else text."""
    low = value.strip().lower()
    if low in ('true', 'false'):
        return 'boolean'
    try:
        float(low)
        return 'number'
    except ValueError:
        return 'string'


def local_names(body: List[Node], scope: Scope, home: str = 'the scene') -> List[str]:
    """The names a q:set in the body gives that no q:set of the scene or the game declared: the
    function's (or the handler's) own variables, local to the call — they never clash with another
    function's, nor with the same function called from within a loop of itself."""
    out: List[str] = []

    def walk(nodes: List[Node]) -> None:
        for n in nodes:
            if isinstance(n, Statement):
                if n.kind == 'set' and n.attrs.get('index') is None:
                    name = n.attrs['name']
                    if not scope.has(name) and name not in out:
                        out.append(name)
                walk(n.body)
                for b in n.branches:
                    walk(b.body)
            elif n.tag == 'for-each':
                walk(n.children)
    walk(body)
    for name in out:
        if name in RESERVED_NAMES:
            raise GameCompileError(f'{name!r} is a property of every Godot node; a variable needs another name', None)
    # a variable set and never read is a misspelt state, not a variable
    read = _texts_read(body)
    for name in out:
        mentioned = re.compile(rf'(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])')
        if not any(mentioned.search(text) for text in read):
            line = next((n.line for n in _sets(body) if n.attrs['name'] == name), None)
            raise GameCompileError(
                f'{name!r} is set and never read: a state of {"the game" if home != "the scene" else "the scene"} '
                f'is declared with <q:set name="{name}" .../> in {home}; a variable of the function or handler is '
                f'read somewhere in it', line)
        # ...and one whose first q:set reads it (score + 1) is a state never declared: it would start as null
        first = next(n for n in _sets(body) if n.attrs['name'] == name)
        if mentioned.search(str(first.attrs.get('value', ''))):
            raise GameCompileError(
                f'{name!r} is not declared: its first <q:set> reads it before it has a value; a state of the '
                f'scene or the game is declared with <q:set name="{name}" .../> there', first.line)
    return out


def _sets(body: List[Node]) -> List[Statement]:
    out: List[Statement] = []
    for n in body:
        if isinstance(n, Statement):
            if n.kind == 'set':
                out.append(n)
            out.extend(_sets(n.body))
            for b in n.branches:
                out.extend(_sets(b.body))
        elif n.tag == 'for-each':
            out.extend(_sets(n.children))
    return out


def _texts_read(body: List[Node]) -> List[str]:
    """Every attribute value in the body that an expression or a name may sit in (q:set's own name aside)."""
    out: List[str] = []
    for n in body:
        if isinstance(n, Statement):
            for key, value in n.attrs.items():
                if not (n.kind == 'set' and key == 'name'):
                    out.append(str(value))
            out.extend(_texts_read(n.body))
            for b in n.branches:
                out.extend([str(v) for v in b.attrs.values()])
                out.extend(_texts_read(b.body))
        else:
            out.extend(str(v) for v in n.attrs.values())
            out.extend(_texts_read(n.children))
    return out


def compile_function(script: SceneScript, st: Statement) -> None:
    name = st.attrs['name']
    params = [p.strip() for p in st.attrs.get('params', '').split(',') if p.strip()]
    scope = script.scope().child(params)
    locals_ = local_names(st.body, scope, '<q:application>' if script.game_wide else 'the scene')
    scope = scope.child(locals_)
    head = ''.join(f'{_INDENT}var {v} = null\n' for v in locals_)
    body = compile_block(st.body, scope, script, 1)
    script.functions.append(f'func {name}({", ".join(params)}):\n' + head + body)


def compile_game_functions(script: SceneScript, functions: List[Statement]) -> None:
    """The q:functions of <q:application>, compiled into a scene's script (or P): each scene has them, and
    they read only the game's state, their parameters and their own variables."""
    script.game_functions = [f.attrs['name'] for f in functions]
    for name in script.game_functions:
        if name not in script.function_names:
            script.function_names.append(name)
    script.game_wide = True
    try:
        for st in functions:
            compile_function(script, st)
    finally:
        script.game_wide = False


def game_state_source(state: Dict[str, StateVar], items: Optional[dict] = None) -> str:
    """The autoload G: the q:sets of <q:application>, kept across scenes; and what the players carry."""
    lines = ['extends Node', '# Compiled by Quantum from the q:sets of <q:application>; do not edit.', '',
             '# Where the character arrives after a qg:exit (the runtime\'s, not the game\'s).',
             'var _q_arrive_at: String = ""', '']
    for var in state.values():
        lines.append(f'var {var.name}: {var.gd_type} = {var.initial}')
    names = [v.name for v in state.values()]
    if items:
        lines.append('')
        lines.append('# What the players carry (qg:item): how many of each; and the named things picked up or')
        lines.append('# opened, as "scene/name", which do not come back. Part of the state: saved, replayed.')
        lines.append(f'const Q_ITEMS := {json.dumps(items)}')
        lines.append(f'var q_items: Dictionary = {json.dumps({k: v["start"] for k, v in items.items()})}')
        lines.append('var q_gone: Array = []')
        names += ['q_items', 'q_gone']
    lines.append('')
    lines.append('func quantum_state() -> Dictionary:')
    if names:
        listed = ', '.join(f'"{n}": {n}' for n in names)
        lines.append(f'{_INDENT}return {{{listed}}}')
    else:
        lines.append(f'{_INDENT}return {{}}')
    persisted = [v.name for v in state.values() if v.persist]
    lines.append('')
    lines.append('# The q:sets with saved=\"true\": read at start, written on every scene change.')
    lines.append(f'const PERSISTED := {json.dumps(persisted)}')
    lines.append('')
    lines.append('func _ready() -> void:')
    lines.append(f'{_INDENT}Q.load_persisted(self, PERSISTED)')
    lines.append('')
    lines.append('func _q_save() -> void:')
    lines.append(f'{_INDENT}Q.save_persisted(self, PERSISTED)')
    return '\n'.join(lines) + '\n'


def prefabs_source(script: 'SceneScript') -> str:
    """The autoload P: the handlers of the prefabs (qg:on-collision, qg:on-damage, qg:on-death)."""
    lines = ['extends Node', '# Compiled by Quantum from the handlers of the qg:prefabs; do not edit.', '']
    for block in script.functions + script.handlers:
        lines.append(block)
        lines.append('')
    return '\n'.join(lines).rstrip('\n') + '\n'


def compile_handler(script: SceneScript, name: str, body: List[Node], line: Optional[int],
                    params: tuple = ('me', 'other')) -> str:
    """A handler method `(me, other)` (or `(cursor, other)` for qg:on-select); returns its name."""
    scope = script.scope().child(params, things=[p for p in params if p in ('me', 'other')])
    locals_ = local_names(body, scope)
    scope = scope.child(locals_)
    head = ''.join(f'{_INDENT}var {v} = null\n' for v in locals_)
    code = compile_block(body, scope, script, 1)
    script.handlers.append(f'func {name}({", ".join(params)}) -> void:\n' + head + code)
    return name


def compile_block(nodes: List[Node], scope: Scope, script: SceneScript, depth: int) -> str:
    lines: List[str] = []
    for node in nodes:
        lines.extend(_compile_node(node, scope, script, depth))
    if not lines:
        lines.append(_INDENT * depth + 'pass')
    return '\n'.join(lines) + '\n'


def _compile_node(node: Node, scope: Scope, script: SceneScript, depth: int) -> List[str]:
    ind = _INDENT * depth
    if isinstance(node, Element) and node.tag == 'for-each':
        var = node.get('var')
        if scope.has(var):
            raise GameCompileError(f'<qg:for-each var="{var}">: the name is taken here; choose another', node.line)
        inner = scope.child([var], things=[var])
        # the things there as it starts; one destroyed meanwhile (by the loop itself) is skipped
        return [f'{ind}for {var} in Q.things(self, {json.dumps(node.get("tag"))}):',
                f'{ind}{_INDENT}if not Q.alive({var}):',
                f'{ind}{_INDENT}{_INDENT}continue',
                compile_block(node.children, inner, script, depth + 1).rstrip('\n')]
    if isinstance(node, Element):
        return [ind + _compile_action(node, scope, script)]
    st = node
    if st.kind == 'set':
        name = st.attrs['name']
        if not scope.has(name):
            raise GameCompileError(
                f'{name!r} is not declared: declare it with <q:set name="{name}" .../> in the scene', st.line)
        value = st.attrs.get('value')
        if value is None:
            raise GameCompileError('<q:set> in a handler needs value=', st.line)
        if st.attrs.get('index') is not None and not scope.has(name):
            raise GameCompileError(f'<q:set name="{name}" index=>: {name!r} is not an array of the scene', st.line)
        if is_expression(value):
            rhs = compile_expression(value, scope, st.line)
        elif st.attrs.get('index') is not None:
            rhs = gdscript_literal(value, 'string')   # an element, written as text
        else:
            var = script.state.get(name) or script.game_state.get(name)
            rhs = gdscript_literal(value, var.type if var else _literal_type(value))
        if st.attrs.get('index') is not None:   # one element of an array: <q:set name="board" index="{i}" .../>
            return [f'{ind}{scope.reference(name)}[int({compile_expression(st.attrs["index"], scope, st.line)})] = {rhs}']
        return [f'{ind}{scope.reference(name)} = {rhs}']
    if st.kind == 'if':
        out = [f'{ind}if {compile_expression(st.attrs["condition"], scope, st.line)}:']
        out.append(compile_block(st.body, scope, script, depth + 1).rstrip('\n'))
        for branch in st.branches:
            if branch.kind == 'elseif':
                out.append(f'{ind}elif {compile_expression(branch.attrs["condition"], scope, branch.line)}:')
            else:
                out.append(f'{ind}else:')
            out.append(compile_block(branch.body, scope, script, depth + 1).rstrip('\n'))
        return out
    if st.kind == 'loop':
        var = st.attrs['var']
        inner = scope.child([var])
        if 'items' in st.attrs:
            head = f'{ind}for {var} in {compile_expression(st.attrs["items"], scope, st.line)}:'
        else:
            start = compile_expression(st.attrs['from'], scope, st.line)
            if 'to' not in st.attrs:
                raise GameCompileError('<q:loop from=> needs to=', st.line)
            end = compile_expression(st.attrs['to'], scope, st.line)
            head = f'{ind}for {var} in range(int({start}), int({end}) + 1):'
        return [head, compile_block(st.body, inner, script, depth + 1).rstrip('\n')]
    if st.kind == 'return':
        value = st.attrs.get('value')
        if value is None:
            return [f'{ind}return']
        return [f'{ind}return {compile_expression(value, scope, st.line)}']
    if st.kind == 'call':
        fname = st.attrs['function']
        if not scope.has_function(fname):
            raise GameCompileError(f'<q:call function="{fname}">: no q:function of that name in the scene or the '
                                   f'game', st.line)
        args = [compile_expression(a, scope, st.line) for a in split_args(st.attrs.get('args', ''))]
        return [f'{ind}{fname}({", ".join(args)})']
    if st.kind == 'function':
        raise GameCompileError('<q:function> goes directly inside <qg:scene>', st.line)
    raise GameCompileError(f'<q:{st.kind}> cannot go here', st.line)


def split_args(text: str) -> List[str]:
    """q:call's args=: the arguments, split at the commas between them — not one inside a text, a list,
    a dictionary or a call (`{'a, b'}, {[1, 2]}, {max(x, 3)}` is three)."""
    out, depth, quote, start = [], 0, '', 0
    for i, ch in enumerate(text):
        if quote:
            if ch == quote and text[i - 1] != '\\':
                quote = ''
        elif ch in '\'"':
            quote = ch
        elif ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
        elif ch == ',' and depth == 0:
            out.append(text[start:i])
            start = i + 1
    out.append(text[start:])
    return [a.strip() for a in out if a.strip()]


def _compile_action(el: Element, scope: Scope, script: SceneScript) -> str:
    target = el.get('target')
    if target is not None and not scope.has(target):
        raise GameCompileError(
            f'<qg:{el.tag} target="{target}">: not me/other of this handler nor a character of the scene', el.line)
    if target is not None:
        target = scope.reference(target)
    if el.tag == 'destroy':
        return f'Q.destroy({target})'
    if el.tag == 'bounce':
        return f'Q.bounce({target}, {float(el.get("height"))!r})'
    if el.tag == 'respawn':
        return f'Q.respawn({target})'
    if el.tag == 'play':
        script.sounds_played.append(el.get('sound'))
        volume, pitch, vary = float(el.get('volume')), float(el.get('pitch')), float(el.get('vary'))
        if pitch <= 0 or vary < 0 or vary >= pitch:
            raise GameCompileError('<qg:play>: pitch= more than 0, vary= 0 or more and less than pitch=', el.line)
        if (volume, pitch, vary) == (0.0, 1.0, 0.0):
            return f'Q.play({json.dumps(el.get("sound"))})'
        return f'Q.play({json.dumps(el.get("sound"))}, {volume!r}, {pitch!r}, {vary!r})'
    if el.tag == 'stop':
        script.sounds_played.append(el.get('sound'))
        return f'Q.stop({json.dumps(el.get("sound"))})'
    if el.tag == 'become':
        if el.get('target') == 'me':   # its own state: checked against its qg:states (another's is its own business)
            script.states_used.append((el.get('state'), el.line))
        return f'Q.become({target}, {json.dumps(el.get("state"))})'
    if el.tag == 'spawn':
        at = el.get('at')
        script.prefabs_used.append((el.get('prefab'), el.line))
        if (el.get('x') is None) != (el.get('y') is None):
            raise GameCompileError('<qg:spawn> takes x= and y= together', el.line)
        if el.get('x') is not None:
            if at != 'other' or el.get('path'):
                raise GameCompileError('<qg:spawn>: x= and y=, or at=, not both', el.line)
            return (f'Q.spawn_at(self, {json.dumps(el.get("prefab"))}, '
                    f'Vector2(float({compile_expression(el.get("x"), scope, el.line)}) + {float(el.get("dx"))!r}, '
                    f'float({compile_expression(el.get("y"), scope, el.line)}) + {float(el.get("dy"))!r}))')
        if at == 'path':
            if not el.get('path'):
                raise GameCompileError('<qg:spawn at="path"> needs path= (a qg:path of the scene)', el.line)
            script.paths_used.append((el.get('path'), el.line))
            return f'Q.spawn_on_path(self, {json.dumps(el.get("prefab"))}, {json.dumps(el.get("path"))})'
        if el.get('path'):
            raise GameCompileError('path= goes with at="path"', el.line)
        if not scope.has(at):
            raise GameCompileError(f'<qg:spawn at="{at}">: not me/other of this handler, a character of the scene, '
                                   f'nor a parameter, loop variable or q:set', el.line)
        if at == 'cursor':
            return (f'Q.spawn_at(self, {json.dumps(el.get("prefab"))}, '
                    f'Vector2(cursor.x + {float(el.get("dx"))!r}, cursor.y + {float(el.get("dy"))!r}))')
        return (f'Q.spawn(self, {json.dumps(el.get("prefab"))}, {scope.reference(at)}, '
                f'{float(el.get("dx"))!r}, {float(el.get("dy"))!r})')
    if el.tag == 'swap':
        script.prefabs_used.append((el.get('prefab'), el.line))
        return f'Q.swap(self, {target}, {json.dumps(el.get("prefab"))})'
    if el.tag == 'damage':
        return f'Q.damage({target}, {int(el.get("amount"))})'
    if el.tag == 'burst':
        at = el.get('at')
        if not scope.has(at):
            raise GameCompileError(f'<qg:burst at="{at}"> outside a handler that has {at!r}', el.line)
        return f'Q.burst({scope.reference(at)}, {json.dumps(el.get("color"))}, {int(el.get("count"))})'
    if el.tag == 'shake':
        at = el.get('at')
        if not scope.has(at):
            raise GameCompileError(f'<qg:shake at="{at}"> outside a handler that has {at!r}', el.line)
        return f'Q.shake({scope.reference(at)}, {int(el.get("frames"))}, {float(el.get("strength"))!r})'
    if el.tag == 'deflect':
        axis, dx, dy = el.get('axis'), el.get('dx'), el.get('dy')
        if axis is not None and (dx is not None or dy is not None):
            raise GameCompileError('<qg:deflect>: axis=, or dx= and dy=, not both', el.line)
        if axis is not None:
            return f'Q.deflect_axis({target}, {json.dumps(axis)})'
        if dx is None or dy is None:
            raise GameCompileError('<qg:deflect> needs axis="x|y", or dx= and dy=', el.line)
        return (f'Q.deflect_to({target}, {compile_expression(dx, scope, el.line)}, '
                f'{compile_expression(dy, scope, el.line)})')
    if el.tag == 'host':
        script.net_used.append(el.line)
        return f'Q.net_host({int(el.get("port"))})'
    if el.tag == 'join':
        script.net_used.append(el.line)
        return f'Q.net_join({compile_expression(el.get("address"), scope, el.line)})'
    if el.tag == 'leave':
        script.net_used.append(el.line)
        return 'Q.net_leave()'
    if el.tag == 'watch':
        script.net_used.append(el.line)
        return f'Q.net_watch({compile_expression(el.get("address"), scope, el.line)})'
    if el.tag == 'time-scale':
        if not 0 < el.get('scale') <= 4 or el.get('seconds') < 0:
            raise GameCompileError('<qg:time-scale>: scale= more than 0 and up to 4, seconds= 0 or more', el.line)
        return f'Q.time_scale({float(el.get("scale"))!r}, {float(el.get("seconds"))!r})'
    if el.tag == 'quit':
        return 'Q.quit()'
    if el.tag == 'start-now':
        script.net_used.append(el.line)
        return 'Q.net_start_now()'
    if el.tag == 'pause':
        return 'Q.pause(self, true)'
    if el.tag == 'resume':
        return 'Q.pause(self, false)'
    if el.tag == 'say':
        script.dialogues_used.append((el.get('dialogue'), el.line))
        return f'Q.say(self, {json.dumps(el.get("dialogue"))})'
    if el.tag == 'put':
        return (f'Q.put({target}, {compile_expression(el.get("x"), scope, el.line)}, '
                f'{compile_expression(el.get("y"), scope, el.line)})')
    if el.tag == 'velocity':
        if el.get('x') is None and el.get('y') is None:
            raise GameCompileError('<qg:velocity> needs x=, y= or both (pixels per second)', el.line)
        x, y = (compile_expression(el.get(a), scope, el.line) if el.get(a) is not None else 'null'
                for a in ('x', 'y'))
        return f'Q.velocity({target}, {x}, {y})'
    if el.tag == 'set-tile':
        args = [compile_expression(el.get('col'), scope, el.line), compile_expression(el.get('row'), scope, el.line),
                compile_expression(el.get('tile'), scope, el.line)]
        if el.get('layer'):
            args.append(json.dumps(el.get('layer')))
        return f'Q.set_tile(self, {", ".join(args)})'
    if el.tag == 'emit':
        at = el.get('at')
        if not scope.has(at):
            raise GameCompileError(f'<qg:emit at="{at}">: not me/other of this handler nor a character of the scene',
                                   el.line)
        script.particles_used.append((el.get('particles'), el.line))
        return (f'Q.emit({scope.reference(at)}, {json.dumps(el.get("particles"))}, '
                f'{float(el.get("dx"))!r}, {float(el.get("dy"))!r})')
    if el.tag == 'reset-items':
        script.items_used.append((None, el.line))
        return 'Q.reset_items()'
    if el.tag in ('give', 'take'):
        if el.get('amount') < 1:
            raise GameCompileError(f'<qg:{el.tag} amount=>: 1 or more', el.line)
        script.items_used.append((el.get('item'), el.line))
        return f'Q.{el.tag}_item({json.dumps(el.get("item"))}, {el.get("amount")})'
    if el.tag == 'play-animation':
        script.animations_played.append((el.get('name'), el.line))
        return f'Q.play_animation({target}, {json.dumps(el.get("name"))})'
    if el.tag == 'tween':
        if el.get('seconds') <= 0:
            raise GameCompileError(f'<qg:tween seconds="{el.get("seconds")}">: more than 0', el.line)
        frm, ends = el.get('from'), [c for c in el.children if isinstance(c, Element) and c.tag == 'on-end']
        if len(ends) != len(el.children) or len(ends) > 1:
            raise GameCompileError('<qg:tween> holds one <qg:on-end> at most, and nothing else', el.line)
        value = _tween_value if el.get('property') == 'tint' else compile_expression
        args = [target, json.dumps(el.get('property')), value(el.get('to'), scope, el.line),
                repr(float(el.get('seconds'))), json.dumps(el.get('trans')), json.dumps(el.get('ease')),
                str(int(el.get('repeat'))), 'true' if el.get('yoyo') else 'false',
                value(frm, scope, el.line) if frm is not None else 'null']
        if ends:   # what runs when it is done: a handler of this script, `me` the thing it moved
            script.tween_ends += 1
            name = compile_handler(script, f'_on_tween_end_{script.tween_ends}', ends[0].children, ends[0].line)
            args += ['self', json.dumps(name)]
        while args[-1] == 'null':
            args.pop()
        return f'Q.tween({", ".join(args)})'
    if el.tag == 'after':
        ticks, seconds = el.get('ticks'), el.get('seconds')
        if (ticks is None) == (seconds is None):
            raise GameCompileError('<qg:after> takes ticks= or seconds=, one of them', el.line)
        given = ticks if ticks is not None else seconds
        try:
            if float(strip_braces(str(given))) <= 0:
                raise GameCompileError(f'<qg:after {"ticks" if ticks is not None else "seconds"}="{given}">: '
                                       f'more than 0', el.line)
        except ValueError:
            pass   # an expression: rounded at run time, and at least one tick
        count = compile_expression(str(given), scope, el.line)
        if seconds is not None:
            count = f'{count} * Q.TICK_RATE'
        # the names of this handler are passed on as they are now: the method runs later, with them
        names = scope.locals()
        script.afters += 1
        method = compile_handler(script, f'_after_{script.afters}', el.children, el.line, params=tuple(names))
        args = ['self', count, json.dumps(method), '[' + ', '.join(names) + ']']
        if el.get('name'):
            args.append(json.dumps(el.get('name')))
        return f'Q.after({", ".join(args)})'
    if el.tag == 'goto-scene':
        script.scenes_used.append((el.get('name'), el.line))
        fade = el.get('fade') or 0.0
        if fade < 0:
            raise GameCompileError(f'<qg:goto-scene fade="{fade}">: the seconds of a fade cannot be negative', el.line)
        if fade:
            return f'Q.goto_scene(self, {json.dumps(el.get("name"))}, {float(fade)!r})'
        return f'Q.goto_scene(self, {json.dumps(el.get("name"))})'
    if el.tag == 'save':
        if el.get('scene'):
            script.scenes_used.append((el.get('scene'), el.line))
            return f'Q.save_game(self, {json.dumps(el.get("scene"))})'
        return 'Q.save_game(self)'
    if el.tag == 'continue':
        return 'Q.continue_game(self)'
    if el.tag == 'next-language':
        return 'Q.next_language()'
    if el.tag == 'checkpoint':
        at = el.get('at')
        if not scope.has(at):
            raise GameCompileError(f'<qg:checkpoint at="{at}"> outside a handler that has {at!r}', el.line)
        return f'Q.checkpoint({target}, {at})'
    raise GameCompileError(f'<qg:{el.tag}> is not an action; it cannot go inside a handler', el.line)


def _tween_value(value: str, scope: Scope, line: Optional[int]) -> str:
    """A tint's colour: #rrggbb as written, or an expression that gives one."""
    if re.fullmatch(r'#[0-9a-fA-F]{6}', str(value).strip()):
        return f'Color({json.dumps(str(value).strip())})'
    return f'Color({compile_expression(value, scope, line)})'


def expression_or_literal(value: str, scope: Scope, line: Optional[int]) -> str:
    return compile_expression(value, scope, line) if is_expression(value) else gdscript_literal(strip_braces(value))
