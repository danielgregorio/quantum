"""Statements and actions, compiled to GDScript.

A scene's logic becomes one script, `extends` the runtime's QuantumScene:
its `q:set`s are properties, its `q:function`s are methods, and every
handler (a `qg:on-collision`) is a method the runtime calls by name with
`(me, other)`. The scene script also reports its state for the replay
harness (`_q_state`).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from quantum.runtime.godot.errors import GameCompileError
from quantum.runtime.godot.expressions import (
    GD_TYPES, Scope, compile_expression, gdscript_literal, strip_braces,
)
from quantum.runtime.godot.model import Element, Node, Statement

_INDENT = '\t'


@dataclass
class StateVar:
    name: str
    type: str
    initial: str   # GDScript literal
    line: Optional[int]
    persist: bool = False   # game state kept between runs (q:set saved="true")


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

    def scope(self) -> Scope:
        return Scope(self.state.keys(), functions=self.function_names, game_names=self.game_state.keys())

    enter: List[Node] = field(default_factory=list)   # statements directly in the scene: run on enter

    def source(self) -> str:
        lines = ['extends "res://addons/quantum/quantum_scene.gd"',
                 '# Compiled by Quantum from the scene; do not edit.', '']
        for var in self.state.values():
            lines.append(f'var {var.name}: {GD_TYPES.get(var.type, "Variant")} = {var.initial}')
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
    script.state[name] = StateVar(name, type_name, initial, st.line, persist)


def compile_function(script: SceneScript, st: Statement) -> None:
    name = st.attrs['name']
    params = [p.strip() for p in st.attrs.get('params', '').split(',') if p.strip()]
    scope = script.scope().child(params)
    body = compile_block(st.body, scope, script, 1)
    script.functions.append(f'func {name}({", ".join(params)}):\n' + body)


def game_state_source(state: Dict[str, StateVar]) -> str:
    """The autoload G: the q:sets of <q:application>, kept across scenes."""
    lines = ['extends Node', '# Compiled by Quantum from the q:sets of <q:application>; do not edit.', '',
             '# Where the character arrives after a qg:exit (the runtime\'s, not the game\'s).',
             'var _q_arrive_at: String = ""', '']
    for var in state.values():
        lines.append(f'var {var.name}: {GD_TYPES.get(var.type, "Variant")} = {var.initial}')
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


def compile_handler(script: SceneScript, name: str, body: List[Node], line: Optional[int]) -> str:
    """A handler method `(me, other)`; returns its name."""
    scope = script.scope().child(['me', 'other'])
    code = compile_block(body, scope, script, 1)
    script.handlers.append(f'func {name}(me, other) -> void:\n' + code)
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
        if is_expression(value):
            rhs = compile_expression(value, scope, st.line)
        else:
            var = script.state.get(name) or script.game_state.get(name)
            rhs = gdscript_literal(value, var.type if var else 'string')
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
        raise GameCompileError(f'<qg:{el.tag} target="{target}"> outside a handler that has {target!r}', el.line)
    if el.tag == 'destroy':
        return f'Q.destroy({target})'
    if el.tag == 'bounce':
        return f'Q.bounce({target}, {float(el.get("height"))!r})'
    if el.tag == 'respawn':
        return f'Q.respawn({target})'
    if el.tag == 'play':
        script.sounds_played.append(el.get('sound'))
        return f'Q.play({json.dumps(el.get("sound"))})'
    if el.tag == 'become':
        script.states_used.append((el.get('state'), el.line))
        return f'Q.become({target}, {json.dumps(el.get("state"))})'
    if el.tag == 'spawn':
        at = el.get('at')
        if not scope.has(at):
            raise GameCompileError(f'<qg:spawn at="{at}"> outside a handler that has {at!r}', el.line)
        script.prefabs_used.append((el.get('prefab'), el.line))
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
