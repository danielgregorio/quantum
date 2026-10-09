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
    states_used: List[tuple] = field(default_factory=list)    # (name, line) from become
    scenes_used: List[tuple] = field(default_factory=list)    # (name, line) from goto-scene
    paths_used: List[tuple] = field(default_factory=list)     # (name, line) from spawn at="path"
    net_used: List[Optional[int]] = field(default_factory=list)   # lines of qg:host, qg:join, qg:leave

    node_ids: List[str] = field(default_factory=list)   # the scene's characters, by id

    def scope(self) -> Scope:
        return Scope(self.state.keys(), functions=self.function_names, game_names=self.game_state.keys(),
                     node_ids=self.node_ids)

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


def local_names(body: List[Node], scope: Scope) -> List[str]:
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
    walk(body)
    for name in out:
        if name in RESERVED_NAMES:
            raise GameCompileError(f'{name!r} is a property of every Godot node; a variable needs another name', None)
    # a variable set and never read is a misspelt state, not a variable
    read = _texts_read(body)
    for name in out:
        if not any(re.search(rf'(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])', text) for text in read):
            line = next((n.line for n in _sets(body) if n.attrs['name'] == name), None)
            raise GameCompileError(
                f'{name!r} is set and never read: a state of the scene is declared with <q:set name="{name}" .../> '
                f'in the scene; a variable of the function or handler is read somewhere in it', line)
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
    locals_ = local_names(st.body, scope)
    scope = scope.child(locals_)
    head = ''.join(f'{_INDENT}var {v} = null\n' for v in locals_)
    body = compile_block(st.body, scope, script, 1)
    script.functions.append(f'func {name}({", ".join(params)}):\n' + head + body)


def game_state_source(state: Dict[str, StateVar]) -> str:
    """The autoload G: the q:sets of <q:application>, kept across scenes."""
    lines = ['extends Node', '# Compiled by Quantum from the q:sets of <q:application>; do not edit.', '',
             '# Where the character arrives after a qg:exit (the runtime\'s, not the game\'s).',
             'var _q_arrive_at: String = ""', '']
    for var in state.values():
        lines.append(f'var {var.name}: {var.gd_type} = {var.initial}')
    lines.append('')
    lines.append('func quantum_state() -> Dictionary:')
    if state:
        items = ', '.join(f'"{v.name}": {v.name}' for v in state.values())
        lines.append(f'{_INDENT}return {{{items}}}')
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
    for block in script.handlers:
        lines.append(block)
        lines.append('')
    return '\n'.join(lines).rstrip('\n') + '\n'


def compile_handler(script: SceneScript, name: str, body: List[Node], line: Optional[int],
                    params: tuple = ('me', 'other')) -> str:
    """A handler method `(me, other)` (or `(cursor, other)` for qg:on-select); returns its name."""
    scope = script.scope().child(params)
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
            raise GameCompileError(f'<q:call function="{fname}">: no q:function of that name in the scene', st.line)
        args = [compile_expression(a.strip(), scope, st.line)
                for a in st.attrs.get('args', '').split(',') if a.strip()]
        return [f'{ind}{fname}({", ".join(args)})']
    if st.kind == 'function':
        raise GameCompileError('<q:function> goes directly inside <qg:scene>', st.line)
    raise GameCompileError(f'<q:{st.kind}> cannot go here', st.line)


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
        return f'Q.play({json.dumps(el.get("sound"))})'
    if el.tag == 'stop':
        script.sounds_played.append(el.get('sound'))
        return f'Q.stop({json.dumps(el.get("sound"))})'
    if el.tag == 'become':
        script.states_used.append((el.get('state'), el.line))
        return f'Q.become({target}, {json.dumps(el.get("state"))})'
    if el.tag == 'spawn':
        at = el.get('at')
        script.prefabs_used.append((el.get('prefab'), el.line))
        if at == 'path':
            if not el.get('path'):
                raise GameCompileError('<qg:spawn at="path"> needs path= (a qg:path of the scene)', el.line)
            script.paths_used.append((el.get('path'), el.line))
            return f'Q.spawn_on_path(self, {json.dumps(el.get("prefab"))}, {json.dumps(el.get("path"))})'
        if el.get('path'):
            raise GameCompileError('path= goes with at="path"', el.line)
        if not scope.has(at):
            raise GameCompileError(f'<qg:spawn at="{at}"> outside a handler that has {at!r}', el.line)
        if at == 'cursor':
            return (f'Q.spawn_at(self, {json.dumps(el.get("prefab"))}, '
                    f'Vector2(cursor.x + {float(el.get("dx"))!r}, cursor.y + {float(el.get("dy"))!r}))')
        return (f'Q.spawn(self, {json.dumps(el.get("prefab"))}, {at}, '
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
        return f'Q.burst({at}, {json.dumps(el.get("color"))}, {int(el.get("count"))})'
    if el.tag == 'shake':
        at = el.get('at')
        if not scope.has(at):
            raise GameCompileError(f'<qg:shake at="{at}"> outside a handler that has {at!r}', el.line)
        return f'Q.shake({at}, {int(el.get("frames"))}, {float(el.get("strength"))!r})'
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
    if el.tag == 'pause':
        return 'Q.pause(self, true)'
    if el.tag == 'resume':
        return 'Q.pause(self, false)'
    if el.tag == 'put':
        return (f'Q.put({target}, {compile_expression(el.get("x"), scope, el.line)}, '
                f'{compile_expression(el.get("y"), scope, el.line)})')
    if el.tag == 'goto-scene':
        script.scenes_used.append((el.get('name'), el.line))
        return f'Q.goto_scene(self, {json.dumps(el.get("name"))})'
    if el.tag == 'checkpoint':
        at = el.get('at')
        if not scope.has(at):
            raise GameCompileError(f'<qg:checkpoint at="{at}"> outside a handler that has {at!r}', el.line)
        return f'Q.checkpoint({target}, {at})'
    raise GameCompileError(f'<qg:{el.tag}> is not an action; it cannot go inside a handler', el.line)


def expression_or_literal(value: str, scope: Scope, line: Optional[int]) -> str:
    return compile_expression(value, scope, line) if is_expression(value) else gdscript_literal(strip_braces(value))
