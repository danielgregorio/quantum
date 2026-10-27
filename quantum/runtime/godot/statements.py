"""Statements and actions, compiled to GDScript.

A scene's logic becomes one script, `extends` the runtime's QuantumScene:
its `q:set`s are properties, its `q:function`s are methods, and every
handler (a `qg:on-collision`) is a method the runtime calls by name with
`(me, other)`. The scene script also reports its state for the replay
harness (`_q_state`).
"""

from __future__ import annotations

import ast
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

# What every Godot object has, from Object itself (the class table starts at Node): a state named `free` was
# Object.free() to the scripts that read it, and PandaFoot's free agents a number.
OBJECT_MEMBERS = frozenset((
    'add_user_signal', 'call', 'call_deferred', 'callv', 'can_translate_messages', 'cancel_free', 'connect',
    'disconnect', 'emit_signal', 'free', 'get', 'get_class', 'get_incoming_connections', 'get_indexed',
    'get_instance_id', 'get_meta', 'get_meta_list', 'get_method_argument_count', 'get_method_list',
    'get_property_list', 'get_script', 'get_signal_connection_list', 'get_signal_list', 'get_translation_domain',
    'has_connections', 'has_meta', 'has_method', 'has_signal', 'has_user_signal', 'is_blocking_signals', 'is_class',
    'is_connected', 'is_queued_for_deletion', 'notification', 'notify_property_list_changed', 'property_can_revert',
    'property_get_revert', 'remove_meta', 'remove_user_signal', 'set', 'set_block_signals', 'set_deferred',
    'set_indexed', 'set_message_translation', 'set_meta', 'set_script', 'set_translation_domain', 'to_string',
    'property_list_changed', 'script_changed',
))

# Names a scene script may not declare: what every Node2D already has (its
# properties, methods and signals, from Godot's own reference — a variable
# named like one is a GDScript error), and what the runtime's scripts use.
RESERVED_NAMES = frozenset((
    'self', 'rng', 'state', 'health', 'tag', 'speed', 'velocity', 'heading', 'player',
)) | gdprops.members_of('Node2D') | OBJECT_MEMBERS


def _member_kind(name: str) -> str:
    return 'a method of every Godot object' if name in OBJECT_MEMBERS else 'a property of every Godot node'


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
    music_set: List[tuple] = field(default_factory=list)   # (sound, line) of a qg:music in a handler: it must loop
    prefabs_used: List[tuple] = field(default_factory=list)   # (name, line) from spawn/swap
    particles_used: List[tuple] = field(default_factory=list)  # (name, line) from qg:emit
    animations_played: List[tuple] = field(default_factory=list)  # (name, line) from qg:play-animation
    items_used: List[tuple] = field(default_factory=list)  # (item, line) from qg:give and qg:take
    states_used: List[tuple] = field(default_factory=list)    # (name, line) from become
    scenes_used: List[tuple] = field(default_factory=list)    # (name, line) from goto-scene
    buses: Optional[set] = None   # the buses of the game's sounds (qg:sound bus=), for qg:volume
    paths_used: List[tuple] = field(default_factory=list)     # (name, line) from spawn at="path"
    dialogues_used: List[tuple] = field(default_factory=list)  # (name, line) from qg:say
    net_used: List[Optional[int]] = field(default_factory=list)   # lines of qg:host, qg:join, qg:leave
    tween_ends: int = 0   # the qg:on-end handlers of tweens so far: each its own method, nested ones too
    travels_used: list = field(default_factory=list)   # the lines of its qg:travels: the scene needs a tilemap
    afters: int = 0       # the qg:afters so far: what each puts off is its own method
    headed: List[tuple] = field(default_factory=list)   # (prefab, line) of a qg:spawn heading=: an ai="fly" one
    cameras_moved: List[Optional[int]] = field(default_factory=list)   # lines of qg:camera-to: the scene needs a camera
    overlays_used: List[tuple] = field(default_factory=list)   # (name, line) from qg:open-overlay
    posts_used: List[Optional[int]] = field(default_factory=list)   # lines of qg:post: each its answers' methods
    game_posts: int = 0   # the qg:posts of the application's q:functions: the same numbers in every script

    node_ids: List[str] = field(default_factory=list)   # the scene's characters, by id
    game_functions: List[str] = field(default_factory=list)   # the q:functions of <q:application>, every scene's
    game_wide: bool = False   # compiling one of those: it sees the game's state and functions, not the scene's
    node_fields: Dict[str, frozenset] = field(default_factory=dict)   # a character id -> its controller's fields
    actions: Optional[List[str]] = None   # the game's actions, for pressing('run') and the like
    tiled_props: Optional[dict] = None   # the scene's Tiled map's properties, for tiled('par')
    world: Optional[object] = None   # the world of qg:connect (world.WorldInfo): what qg:send may ask
    world_scene: bool = False        # a scene with world="true"

    def scope(self) -> Scope:
        fields = self.world.fields if self.world is not None else None
        if self.game_wide:
            return Scope((), functions=self.game_functions, game_names=self.game_state.keys(),
                         actions=self.actions, world_fields=fields)
        return Scope(self.state.keys(), functions=self.function_names, game_names=self.game_state.keys(),
                     node_ids=self.node_ids, node_fields=self.node_fields, actions=self.actions,
                     tiled=self.tiled_props, world_fields=fields)

    enter: List[Node] = field(default_factory=list)   # statements directly in the scene: run on enter
    # a scene's q:sets whose value= is computed (a function, the game's state, random()): (name, GDScript),
    # set in order as the scene is entered, after its random source is seeded and before what it runs
    computed: List[tuple] = field(default_factory=list)

    def source(self) -> str:
        lines = ['extends "res://addons/quantum/quantum_scene.gd"',
                 '# Compiled by Quantum from the scene; do not edit.', '']
        for var in self.state.values():
            lines.append(f'var {var.name}: {var.gd_type} = {var.initial}')
        lines.append('')
        if self.enter or self.computed:
            lines.append('func _q_enter() -> void:')
            for name, code in self.computed:
                lines.append(f'{_INDENT}{name} = {code}')
            if self.enter:
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
        raise GameCompileError(f'{name!r} is {_member_kind(name)}; a game state needs another name', st.line)
    type_name = st.attrs.get('type', 'string')
    if type_name not in GD_TYPES:
        raise GameCompileError(
            f'type="{type_name}": a game state is number, string, boolean or array', st.line)
    value = st.attrs.get('value', st.attrs.get('default'))
    if value is not None and is_expression(value):
        initial = compile_expression(value, script.scope(), st.line)
        if script.name != 'game' and not _constant(value):
            # computed as the scene is entered: seeded, and with the game's state as it is then
            script.computed.append((name, initial))
            initial = gdscript_literal({'number': '0', 'boolean': 'false', 'array': '[]'}.get(type_name, ''), type_name) \
                if 'type' in st.attrs else 'null'
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


def _constant(value: str) -> bool:
    """{3}, {[]}, {'text'}, {null}: an expression that is a value already, the same whenever it is read."""
    inner = value.strip()[1:-1].strip()
    if inner in ('null', 'true', 'false'):
        return True
    try:
        ast.literal_eval(inner)
        return True
    except (ValueError, SyntaxError):
        return False


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


_NAME_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')


def local_names(body: List[Node], scope: Scope, home: str = 'the scene') -> List[str]:
    """The names a q:set in the body gives that no q:set of the scene or the game declared: the
    function's (or the handler's) own variables, local to the call — they never clash with another
    function's, nor with the same function called from within a loop of itself."""
    out: List[str] = []

    def walk(nodes: List[Node]) -> None:
        for n in nodes:
            if isinstance(n, Statement):
                if n.kind == 'set' and n.attrs.get('index') is None and '.' not in n.attrs['name']:
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
            line = next((n.line for n in _sets(body) if n.attrs['name'] == name), None)
            raise GameCompileError(f'{name!r} is {_member_kind(name)}; a variable needs another name', line)
    # a variable set and never read is a misspelt state, not a variable
    read = _texts_read(body)
    for name in out:
        # the name itself, not a field of that name (m.luck is not luck)
        mentioned = re.compile(rf'(?<![A-Za-z0-9_.]){re.escape(name)}(?![A-Za-z0-9_])')
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
                # a q:set's name is what it sets, not what it reads; but setting a field or an item reads the record
                if not (n.kind == 'set' and key == 'name' and '.' not in str(value) and 'index' not in n.attrs):
                    out.append(str(value))
            out.extend(_texts_read(n.body))
            for b in n.branches:
                out.extend([str(v) for v in b.attrs.values()])
                out.extend(_texts_read(b.body))
        else:
            out.extend(str(v) for v in n.attrs.values())
            out.extend(_texts_read(n.children))
    return out


# The signals among the members (a function may share a signal's name: PandaFoot's ready() and Node's ready)
NODE2D_SIGNALS = frozenset((
    'ready', 'renamed', 'tree_entered', 'tree_exiting', 'tree_exited', 'child_entered_tree', 'child_exiting_tree',
    'child_order_changed', 'replacing_by', 'editor_description_changed', 'editor_state_changed', 'draw',
    'visibility_changed', 'hidden', 'item_rect_changed', 'script_changed', 'property_list_changed',
))


def compile_function(script: SceneScript, st: Statement) -> None:
    name = st.attrs['name']
    if name in RESERVED_NAMES and name not in NODE2D_SIGNALS:
        # a function named like a member every node has overrides it (draw_line is CanvasItem's): a parse error
        # when the scene loads, the whole scene gone
        raise GameCompileError(f'<q:function name="{name}">: {name!r} is {_member_kind(name)}; '
                               f'the function needs another name', st.line)
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
        path = name.split('.')   # name="team.points": a field of a record, set in place
        if not all(_NAME_RE.match(part) for part in path):
            raise GameCompileError(f'<q:set name="{name}">: a name, or a field of one (team.points)', st.line)
        if not scope.has(path[0]):
            raise GameCompileError(
                f'{path[0]!r} is not declared: declare it with <q:set name="{path[0]}" .../> in the scene', st.line)
        if len(path) > 1 and (path[0] in scope.things or scope.is_node(path[0])):
            raise GameCompileError(f'<q:set name="{name}">: {path[0]} is a thing or a character; what it has is '
                                   f'changed by its actions (qg:put, qg:velocity, qg:damage...)', st.line)
        target = '.'.join([scope.reference(path[0])] + path[1:])
        value = st.attrs.get('value')
        if value is None:
            raise GameCompileError('<q:set> in a handler needs value=', st.line)
        if is_expression(value):
            rhs = compile_expression(value, scope, st.line)
        elif st.attrs.get('index') is not None:
            rhs = gdscript_literal(value, 'string')   # an element, written as text
        else:
            var = script.state.get(name) or script.game_state.get(name)
            rhs = gdscript_literal(value, var.type if var else _literal_type(value))
        if st.attrs.get('index') is not None:
            # an item of a list, <q:set name="board" index="{i}" .../>, or a key of a dictionary (index="{name}")
            return [f'{ind}Q.set_at({target}, {compile_expression(st.attrs["index"], scope, st.line)}, {rhs})']
        return [f'{ind}{target} = {rhs}']
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
        if scope.has_local(var):
            raise GameCompileError(f'<q:loop var="{var}">: {var!r} is a parameter or a variable here already; '
                                   f'the loop\'s needs another name', st.line)
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


def _send(el: Element, scope: Scope, script: SceneScript) -> str:
    """qg:send command="step" dir="north": a command of the world, its arguments the other attributes (a text as
    written, or an expression in braces), all of its params and no other."""
    world = script.world
    command = el.get('command')
    if world is None:
        raise GameCompileError(f'<qg:send command="{command}">: the game is no world\'s client (qg:connect)', el.line)
    if command not in world.commands:
        raise GameCompileError(f'<qg:send command="{command}">: the world {world.name!r} has no such command '
                               f'(it has: {", ".join(sorted(world.commands)) or "none"})', el.line)
    args = dict(el.get('_extra') or {})
    params = world.commands[command]
    if set(args) != set(params):
        missing, extra = sorted(set(params) - set(args)), sorted(set(args) - set(params))
        said = '; '.join(([f'it needs {", ".join(f"{m}=" for m in missing)}'] if missing else [])
                         + ([f'it takes no {", ".join(f"{x}=" for x in extra)}'] if extra else []))
        raise GameCompileError(f'<qg:send command="{command}">: {said} (its params: '
                               f'{", ".join(params) or "none"})', el.line)
    items = []
    for name in params:
        raw = args[name].strip()
        if raw.startswith('{') and raw.endswith('}'):
            code = compile_expression(raw, scope, el.line)
        else:
            code = json.dumps(args[name], ensure_ascii=False)
        items.append(f'{json.dumps(name)}: {code}')
    return f'Q.world_send({json.dumps(command)}, {{{", ".join(items)}}})'


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
        volume, pitch, vary = float(el.get('volume')), float(el.get('pitch')), float(el.get('vary'))
        if pitch <= 0 or vary < 0 or vary >= pitch:
            raise GameCompileError('<qg:play>: pitch= more than 0, vary= 0 or more and less than pitch=', el.line)
        if (el.get('sound') is None) == (el.get('sounds') is None):
            raise GameCompileError('<qg:play> takes sound= or sounds=, one of them', el.line)
        at = el.get('at')
        if at is not None and not scope.has(at):
            raise GameCompileError(f'<qg:play at="{at}"> outside a handler that has {at!r} (me, other, a character '
                                   f'id, or a parameter holding a thing)', el.line)
        where = f', {scope.reference(at)}' if at is not None else ''
        if el.get('sounds') is not None:   # one of several, drawn each time
            names = [n.strip() for n in str(el.get('sounds')).split(',') if n.strip()]
            if len(names) < 2:
                raise GameCompileError('<qg:play sounds=>: two sounds or more, separated by commas', el.line)
            script.sounds_played.extend(names)
            return f'Q.play_one({json.dumps(names)}, {volume!r}, {pitch!r}, {vary!r}{where})'
        script.sounds_played.append(el.get('sound'))
        if where:
            return f'Q.play({json.dumps(el.get("sound"))}, {volume!r}, {pitch!r}, {vary!r}{where})'
        if (volume, pitch, vary) == (0.0, 1.0, 0.0):
            return f'Q.play({json.dumps(el.get("sound"))})'
        return f'Q.play({json.dumps(el.get("sound"))}, {volume!r}, {pitch!r}, {vary!r})'
    if el.tag == 'music':   # in a handler: the music changes there and then
        if el.get('fade') < 0:
            raise GameCompileError('<qg:music fade=>: the seconds of a fade cannot be negative', el.line)
        script.sounds_played.append(el.get('sound'))
        script.music_set.append((el.get('sound'), el.line))
        spec = {'sound': el.get('sound'), 'fade': el.get('fade'), 'volume': el.get('volume')}
        return f'Q.music({json.dumps(spec)})'
    if el.tag == 'stop':
        script.sounds_played.append(el.get('sound'))
        return f'Q.stop({json.dumps(el.get("sound"))})'
    if el.tag == 'become':
        if el.get('target') == 'me':   # its own state: checked against its qg:states (another's is its own business)
            script.states_used.append((el.get('state'), el.line))
        return f'Q.become({target}, {json.dumps(el.get("state"))})'
    if el.tag == 'spawn' and el.get('heading') is not None:
        # the way an ai="fly" prefab goes, from expressions: set on the thing as it is placed
        parts = split_args(el.get('heading'))
        if len(parts) != 2:
            raise GameCompileError(f'<qg:spawn heading="{el.get("heading")}">: x,y (each a number or an '
                                   f'expression)', el.line)
        script.headed.append((el.get('prefab'), el.line))
        hx, hy = (compile_expression(v, scope, el.line) for v in parts)
        bare = Element(el.tag, {k: v for k, v in el.attrs.items() if k != 'heading'}, el.line, el.children)
        return f'Q.headed({_compile_action(bare, scope, script)}, float({hx}), float({hy}))'
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
        amount = str(el.get('amount'))
        if re.fullmatch(r'\d+', strip_braces(amount)):
            return f'Q.damage({target}, {int(strip_braces(amount))})'
        return f'Q.damage({target}, int({compile_expression(amount, scope, el.line)}))'
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
        if (el.get('particles') is None) == (el.get('text') is None):
            raise GameCompileError('<qg:emit> plays particles= or shows text=, one of them', el.line)
        if el.get('text') is not None:
            text = el.get('text')
            value = (compile_expression(text, scope, el.line) if is_expression(text)
                     else json.dumps(str(text), ensure_ascii=False))
            return (f'Q.emit_text({scope.reference(at)}, Q.to_str({value}), {json.dumps(el.get("color"))}, '
                    f'{int(el.get("size"))}, {float(el.get("dx"))!r}, {float(el.get("dy"))!r})')
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
    if el.tag == 'travel':
        ends = [c for c in el.children if isinstance(c, Element) and c.tag == 'on-end']
        if len(ends) != len(el.children) or len(ends) > 1:
            raise GameCompileError('<qg:travel> holds one <qg:on-end> at most, and nothing else', el.line)
        if el.get('step') < 1:
            raise GameCompileError('<qg:travel step=>: 1 tick a cell or more', el.line)
        script.travels_used.append(el.line)
        to = str(el.get('to')).strip()
        to = scope.reference(to) if scope.has(to) else compile_expression(to, scope, el.line)
        budget = compile_expression(el.get('budget'), scope, el.line) if el.get('budget') is not None else '-1'
        args = [target or scope.reference('me'), to, budget, str(int(el.get('step')))]
        if ends:   # what runs as it arrives: a handler of this script, `me` the traveller
            script.tween_ends += 1
            name = compile_handler(script, f'_on_travel_end_{script.tween_ends}', ends[0].children, ends[0].line)
            args += ['self', json.dumps(name)]
        return f'Q.travel({", ".join(args)})'
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
    if el.tag == 'camera-to':
        if not script.game_wide:   # in a q:function of the game, a scene without a camera has none to move
            script.cameras_moved.append(el.line)
        if (el.get('target') is None) == (el.get('x') is None or el.get('y') is None):
            raise GameCompileError('<qg:camera-to> goes to target=, or to x= and y=, one of them', el.line)
        if el.get('target') is not None:
            if not scope.has(el.get('target')):
                raise GameCompileError(f'<qg:camera-to target="{el.get("target")}">: not me/other of this handler, a '
                                       f'character or cursor of the scene, nor a parameter, loop variable or q:set',
                                       el.line)
            to = scope.reference(el.get('target'))
        else:
            to = (f'Vector2(float({compile_expression(el.get("x"), scope, el.line)}), '
                  f'float({compile_expression(el.get("y"), scope, el.line)}))')
        if el.get('seconds') < 0 or el.get('hold') < 0 or (el.get('zoom') is not None and el.get('zoom') <= 0):
            raise GameCompileError('<qg:camera-to>: seconds= and hold= 0 or more, zoom= more than 0', el.line)
        zoom = repr(float(el.get('zoom'))) if el.get('zoom') is not None else '0.0'
        return (f'Q.camera_to(self, {to}, {zoom}, {float(el.get("seconds"))!r}, {float(el.get("hold"))!r}, '
                f'{"true" if el.get("pause") else "false"})')
    if el.tag == 'attach':
        ends = []
        for attr in ('target', 'to'):
            name = el.get(attr)
            if not scope.has(name):
                raise GameCompileError(f'<qg:attach {attr}="{name}">: not me/other of this handler, a character of '
                                       f'the scene, nor a parameter, loop variable or q:set', el.line)
            ends.append(scope.reference(name))
        return f'Q.attach({ends[0]}, {ends[1]}, {float(el.get("dx"))!r}, {float(el.get("dy"))!r})'
    if el.tag == 'detach':
        if (el.get('target') is None) == (el.get('from') is None or el.get('tag') is None):
            raise GameCompileError('<qg:detach> puts down target=, or from= and tag= (what of a tag it carries), '
                                   'one of them', el.line)
        name = el.get('target') or el.get('from')
        if not scope.has(name):
            raise GameCompileError(f'<qg:detach>: {name!r} is not me/other of this handler, a character of the '
                                   f'scene, nor a parameter, loop variable or q:set', el.line)
        if el.get('target') is not None:
            return f'Q.detach({scope.reference(name)})'
        return f'Q.detach_all({scope.reference(name)}, {json.dumps(el.get("tag"))})'
    if el.tag == 'beam':
        ends = []
        for attr in ('from', 'to'):
            name = el.get(attr)
            if not scope.has(name):
                raise GameCompileError(f'<qg:beam {attr}="{name}">: not me/other of this handler, a character or '
                                       f'cursor of the scene, nor a parameter, loop variable or q:set', el.line)
            ends.append(scope.reference(name))
        if el.get('seconds') <= 0 or el.get('width') <= 0:
            raise GameCompileError('<qg:beam>: seconds= and width= more than 0', el.line)
        return (f'Q.beam(self, {ends[0]}, {ends[1]}, {float(el.get("seconds"))!r}, {json.dumps(el.get("color"))}, '
                f'{float(el.get("width"))!r})')
    if el.tag == 'goto-scene':
        script.scenes_used.append((el.get('name'), el.line))
        fade = el.get('fade') or 0.0
        if fade < 0:
            raise GameCompileError(f'<qg:goto-scene fade="{fade}">: the seconds of a fade cannot be negative', el.line)
        if fade:
            return f'Q.goto_scene(self, {json.dumps(el.get("name"))}, {float(fade)!r})'
        return f'Q.goto_scene(self, {json.dumps(el.get("name"))})'
    if el.tag == 'save':
        slot = compile_expression(el.get('slot'), scope, el.line) if el.get('slot') is not None else 'null'
        if el.get('scene'):
            script.scenes_used.append((el.get('scene'), el.line))
        if el.get('slot') is not None:
            return f'Q.save_game(self, {json.dumps(el.get("scene") or "")}, {slot})'
        if el.get('scene'):
            return f'Q.save_game(self, {json.dumps(el.get("scene"))})'
        return 'Q.save_game(self)'
    if el.tag == 'continue':
        if el.get('slot') is not None:
            return f'Q.continue_game(self, {compile_expression(el.get("slot"), scope, el.line)})'
        return 'Q.continue_game(self)'
    if el.tag == 'volume':
        if script.buses is not None and el.get('bus') not in script.buses:
            raise GameCompileError(f'<qg:volume bus="{el.get("bus")}">: no qg:sound is heard on that bus (buses: '
                                   f'{", ".join(sorted(script.buses)) or "none: give a qg:sound bus="})', el.line)
        return f'Q.set_volume({json.dumps(el.get("bus"))}, float({compile_expression(el.get("value"), scope, el.line)}))'
    if el.tag == 'rumble':
        if not 0.0 <= el.get('strength') <= 1.0 or el.get('seconds') <= 0:
            raise GameCompileError('<qg:rumble>: strength= 0 to 1, seconds= more than 0', el.line)
        player = str(el.get('player'))
        who = player if player.isdigit() else f'int({compile_expression(player, scope, el.line)})'
        return f'Q.rumble({who}, {float(el.get("strength"))!r}, {float(el.get("seconds"))!r})'
    if el.tag == 'fullscreen':
        if el.get('on') is None:
            return 'Q.set_fullscreen(not Q.fullscreen())'
        return f'Q.set_fullscreen(bool({compile_expression(el.get("on"), scope, el.line)}))'
    if el.tag == 'next-language':
        return 'Q.next_language()'
    if el.tag == 'open-url':
        href = str(el.get('href')).strip()
        if is_expression(href):
            return f'Q.open_url({compile_expression(href, scope, el.line)})'
        if not re.match(r'https?://\S+$', href):
            raise GameCompileError(f'<qg:open-url href="{href}">: an http:// or https:// address', el.line)
        return f'Q.open_url({json.dumps(href)})'
    if el.tag == 'open-overlay':
        script.overlays_used.append((el.get('name'), el.line))
        return f'Q.open_overlay({json.dumps(el.get("name"))})'
    if el.tag == 'close-overlay':
        return 'Q.close_overlay()'
    if el.tag == 'post':
        return _post(el, scope, script)
    if el.tag == 'send':
        return _send(el, scope, script)
    if el.tag == 'checkpoint':
        at = el.get('at')
        if not scope.has(at):
            raise GameCompileError(f'<qg:checkpoint at="{at}"> outside a handler that has {at!r}', el.line)
        return f'Q.checkpoint({target}, {at})'
    raise GameCompileError(f'<qg:{el.tag}> is not an action; it cannot go inside a handler', el.line)


def _post(el: Element, scope: Scope, script: SceneScript) -> str:
    """qg:post: Q.post with the data, and its qg:on-done and qg:on-fail as methods of this script that take the
    names of the handler as they are now (as qg:after's do) and then `reply` or `reason`."""
    to = str(el.get('to')).strip()
    if is_expression(to):
        address = compile_expression(to, scope, el.line)
    elif re.match(r'https?://\S+$', to):
        address = json.dumps(to)
    else:
        raise GameCompileError(f'<qg:post to="{to}">: an http:// or https:// address', el.line)
    if el.get('timeout') <= 0:
        raise GameCompileError('<qg:post timeout=>: seconds, more than 0', el.line)
    answers = {c.tag: c for c in el.children if isinstance(c, Element) and c.tag in ('on-done', 'on-fail')}
    if len(answers) != len(el.children):
        raise GameCompileError('<qg:post> holds one <qg:on-done> and one <qg:on-fail> at most, and nothing else',
                               el.line)
    script.posts_used.append(el.line)
    # a post in its own qg:on-done is the next number. One in a q:function of the application is numbered among
    # those alone: every script compiles them in the same order, so a scene played later has the same method
    if script.game_wide:
        script.game_posts += 1
        prefix = f'_on_game_post_{script.game_posts}'
    else:
        prefix = f'_on_post_{len(script.posts_used)}'
    names = scope.locals()
    methods = []
    for tag, answer in (('on-done', 'reply'), ('on-fail', 'reason')):
        handler = answers.get(tag)
        if handler is None:
            methods.append('""')
            continue
        if answer in names:
            raise GameCompileError(f'<qg:{tag}>: its answer is `{answer}`, a name this handler has already; '
                                   f'give that one another name', handler.line)
        method = compile_handler(script, f'{prefix}_{tag[3:]}', handler.children,
                                 handler.line, params=tuple(names) + (answer,))
        methods.append(json.dumps(method))
    data = compile_expression(el.get('data'), scope, el.line)
    return (f'Q.post(self, {address}, {data}, {methods[0]}, {methods[1]}, [{", ".join(names)}], '
            f'{float(el.get("timeout"))!r})')


def _tween_value(value: str, scope: Scope, line: Optional[int]) -> str:
    """A tint's colour: #rrggbb as written, or an expression that gives one."""
    if re.fullmatch(r'#[0-9a-fA-F]{6}', str(value).strip()):
        return f'Color({json.dumps(str(value).strip())})'
    return f'Color({compile_expression(value, scope, line)})'


def expression_or_literal(value: str, scope: Scope, line: Optional[int]) -> str:
    return compile_expression(value, scope, line) if is_expression(value) else gdscript_literal(strip_braces(value))
