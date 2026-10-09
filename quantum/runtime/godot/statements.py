"""Statements and actions, compiled to GDScript.

A scene's logic becomes one script, `extends` the runtime's QuantumScene:
its `q:set`s are properties, its `q:function`s are methods, and every
handler (a `qg:on-collision`) is a method the runtime calls by name with
`(me, other)`. The scene script also reports its state for the replay
harness (`_q_state`).
"""

from __future__ import annotations

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


@dataclass
class SceneScript:
    """The GDScript of one scene, built up by the compiler."""
    name: str
    state: Dict[str, StateVar] = field(default_factory=dict)
    functions: List[str] = field(default_factory=list)   # compiled func blocks
    handlers: List[str] = field(default_factory=list)
    function_names: List[str] = field(default_factory=list)

    def scope(self) -> Scope:
        return Scope(self.state.keys(), functions=self.function_names)

    def source(self) -> str:
        lines = ['extends "res://addons/quantum/quantum_scene.gd"',
                 '# Compiled by Quantum from the scene; do not edit.', '']
        for var in self.state.values():
            lines.append(f'var {var.name}: {GD_TYPES.get(var.type, "Variant")} = {var.initial}')
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
    script.state[name] = StateVar(name, type_name, initial, st.line)


def compile_function(script: SceneScript, st: Statement) -> None:
    name = st.attrs['name']
    params = [p.strip() for p in st.attrs.get('params', '').split(',') if p.strip()]
    scope = script.scope().child(params)
    body = compile_block(st.body, scope, script, 1)
    script.functions.append(f'func {name}({", ".join(params)}):\n' + body)


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
        return [ind + _compile_action(node, scope)]
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
            var = script.state.get(name)
            rhs = gdscript_literal(value, var.type if var else 'string')
        return [f'{ind}{name} = {rhs}']
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
    if st.kind == 'function':
        raise GameCompileError('<q:function> goes directly inside <qg:scene>', st.line)
    raise GameCompileError(f'<q:{st.kind}> cannot go here', st.line)


def _compile_action(el: Element, scope: Scope) -> str:
    if el.tag == 'destroy':
        target = el.get('target', 'other')
        if not scope.has(target):
            raise GameCompileError(f'<qg:destroy target="{target}"> outside a collision handler', el.line)
        return f'Q.destroy({target})'
    raise GameCompileError(f'<qg:{el.tag}> is not an action; it cannot go inside a handler', el.line)


def expression_or_literal(value: str, scope: Scope, line: Optional[int]) -> str:
    return compile_expression(value, scope, line) if is_expression(value) else gdscript_literal(strip_braces(value))
