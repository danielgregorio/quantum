"""Writes the Godot project: game.json, the scene scripts, the runtime, the assets."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from quantum.runtime.godot.errors import GameCompileError
from quantum.runtime.godot.model import Element, Game, Statement, read_game
from quantum.runtime.godot.expressions import compile_expression, strip_braces
from quantum.runtime.godot.tiled import read_tmx
from quantum.runtime.godot import gd as gdprops
from quantum.runtime.godot.statements import (
    SceneScript, StateVar, compile_function, compile_handler, declare_state, game_state_source,
    is_expression, prefabs_source,
)

ADDON_SRC = Path(__file__).with_name('addons') / 'quantum'

# The keys a platformer controller reads, until a qg:input says otherwise.
DEFAULT_INPUTS = {
    'left': ['Left', 'A', 'JoyLeft', 'JoyLeftStickLeft'],
    'right': ['Right', 'D', 'JoyRight', 'JoyLeftStickRight'],
    'up': ['Up', 'W', 'JoyUp', 'JoyLeftStickUp'],
    'down': ['Down', 'S', 'JoyDown', 'JoyLeftStickDown'],
    'jump': ['Space', 'Z', 'X', 'JoyA'],
    'select': ['Enter', 'MouseLeft', 'JoyA'],
    'cancel': ['Escape', 'MouseRight', 'JoyB'],
}
MOUSE_BUTTONS = {'MouseLeft': 1, 'MouseRight': 2, 'MouseMiddle': 3}

# Joypad names a qg:input may use: Godot's button index, or an axis and its sign.
JOY_BUTTONS = {'JoyA': 0, 'JoyB': 1, 'JoyX': 2, 'JoyY': 3, 'JoySelect': 4, 'JoyStart': 6, 'JoyL': 9, 'JoyR': 10,
               'JoyUp': 11, 'JoyDown': 12, 'JoyLeft': 13, 'JoyRight': 14}
JOY_AXES = {'JoyLeftStickLeft': (0, -1.0), 'JoyLeftStickRight': (0, 1.0), 'JoyLeftStickUp': (1, -1.0),
            'JoyLeftStickDown': (1, 1.0), 'JoyRightStickLeft': (2, -1.0), 'JoyRightStickRight': (2, 1.0),
            'JoyRightStickUp': (3, -1.0), 'JoyRightStickDown': (3, 1.0), 'JoyL2': (4, 1.0), 'JoyR2': (5, 1.0)}

PROJECT_GODOT = '''; Engine configuration file.
; Written by Quantum from {source}; do not edit.
config_version=5

[application]
config/name="{name}"
run/main_scene="res://main.tscn"
config/features=PackedStringArray("4.4", "GL Compatibility")

[autoload]
Q="*res://addons/quantum/q.gd"
G="*res://scripts/game_state.gd"
P="*res://scripts/prefabs.gd"

[display]
window/size/viewport_width={width}
window/size/viewport_height={height}
window/size/window_width_override={window_width}
window/size/window_height_override={window_height}
window/stretch/mode="viewport"

[physics]
common/physics_ticks_per_second=60

[rendering]
renderer/rendering_method="gl_compatibility"
renderer/rendering_method.mobile="gl_compatibility"
textures/canvas_textures/default_texture_filter=0
'''

MAIN_TSCN = '''[gd_scene load_steps=2 format=3]

[ext_resource type="Script" path="res://addons/quantum/quantum_game.gd" id="1"]

[node name="Game" type="Node"]
script = ExtResource("1")
'''


def compile_game(app, output_dir: str, source_dir: Optional[str] = None) -> str:
    """Compile the game application into ``output_dir``; returns the path."""
    game = read_game(app)
    out = Path(output_dir)
    source = Path(game.source_path) if game.source_path else None
    base_dir = Path(source_dir) if source_dir else (source.parent if source else Path.cwd())

    try:
        data = _Compiler(game, base_dir, source.parent if source and source.parent.is_dir() else None).build()
    except GameCompileError as e:
        if e.file is None:
            e.file = game.source_path
        raise

    if out.exists():
        _clear(out)
    (out / 'scripts').mkdir(parents=True, exist_ok=True)
    shutil.copytree(ADDON_SRC, out / 'addons' / 'quantum')
    for name, text in data['scripts'].items():
        (out / 'scripts' / name).write_text(text, encoding='utf-8')
    for rel, src in data['assets'].items():
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    first = data['game']['scenes'][data['game']['initial']]
    (out / 'project.godot').write_text(PROJECT_GODOT.format(
        source=source.name if source else 'a .q', name=game.id,
        width=first['width'], height=first['height'],
        window_width=first['width'] * 3, window_height=first['height'] * 3), encoding='utf-8')
    (out / 'main.tscn').write_text(MAIN_TSCN, encoding='utf-8')
    (out / 'game.json').write_text(json.dumps(data['game'], indent=2), encoding='utf-8')
    return str(out)


def _clear(out: Path) -> None:
    """Empty a build directory we wrote before (never a directory with other files)."""
    if not (out / 'game.json').is_file() and any(out.iterdir()):
        raise GameCompileError(f'{out} exists and is not a Quantum build; not overwriting it')
    for child in out.iterdir():
        if child.name == '.godot':
            continue   # Godot's import cache, worth keeping
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def _script_name(scene: str) -> str:
    return 'scene_' + re.sub(r'[^A-Za-z0-9]+', '_', scene).strip('_').lower() + '.gd'


class _Compiler:
    def __init__(self, game: Game, base_dir: Path, source_dir: Optional[Path] = None):
        self.game = game
        self.base_dir = base_dir
        # Files are looked for next to the .q first, then from base_dir up.
        self.search_roots = [d for d in (source_dir, base_dir) if d is not None]
        self.assets: Dict[str, Path] = {}
        self.scripts: Dict[str, str] = {}

    def build(self) -> dict:
        g = self.game
        # the game-wide state: the q:sets of <q:application>, the autoload G
        game_script = SceneScript('game')
        for st in g.state:
            declare_state(game_script, st)
        self.game_state: Dict[str, StateVar] = game_script.state
        self.scripts['game_state.gd'] = game_state_source(self.game_state)
        inputs = {k: [_key(name, 1, None) for name in v] for k, v in DEFAULT_INPUTS.items()}
        for el in g.inputs:
            keys = [k.strip() for k in str(el.get('keys')).split(',') if k.strip()]
            if not keys:
                raise GameCompileError('<qg:input> needs at least one key', el.line)
            if el.get('player') < 1:
                raise GameCompileError('<qg:input player=>: 1 or more', el.line)
            inputs[action_name(el.get('player'), el.get('action'))] = [_key(k, el.get('player'), el.line)
                                                                       for k in keys]
        # every action the game has: the defaults and the names qg:input declares (the lockstep frame's bits)
        self.actions = list(DEFAULT_INPUTS) + sorted({
            el.get('action') for el in g.inputs if el.get('action') not in DEFAULT_INPUTS})
        self.multiplayer = None
        if g.multiplayer is not None:
            mp = g.multiplayer
            if mp.get('players') < 2:
                raise GameCompileError('<qg:multiplayer players=>: 2 or more', mp.line)
            if mp.get('delay') < 1:
                raise GameCompileError('<qg:multiplayer delay=>: 1 or more', mp.line)
            self.multiplayer = {'players': mp.get('players'), 'delay': mp.get('delay'),
                                'check_every': mp.get('check-every')}
            # every player's actions exist; under lockstep they are pressed by the runtime, not by keys
            for p in range(2, mp.get('players') + 1):
                for action in self.actions:
                    inputs.setdefault(action_name(p, action), [])
        self.inputs = inputs
        # the tags of the zones of every scene: handlers may name them like a prefab's
        self._zone_tags = {z.get('tag') for sc in g.scenes for z in sc.find_all('zone')}
        sheets = {}
        for name, el in list(g.tilesets.items()) + list(g.sheets.items()):
            if el.gd:
                raise GameCompileError(f'<qg:{el.tag}> becomes no Godot node: gd: attributes go on what is placed', el.line)
            tile = el.get('tile')
            if isinstance(tile, int):
                tile = (tile, tile)
            sheets[name] = {'src': self._asset(el.get('src'), el.line), 'tile': list(tile),
                            'kind': el.tag}
        sounds = {}
        for name, el in g.sounds.items():
            sounds[name] = {'src': self._asset(el.get('src'), el.line), 'loop': el.get('loop')}
            gdprops.attach(sounds[name], 'AudioStreamPlayer', el.gd, f'<qg:sound name="{name}">', el.line)
        self.sounds = sounds
        prefabs = {}
        pscript = SceneScript('prefabs', game_state=self.game_state)
        for name, el in g.prefabs.items():
            self._sheet_exists(el.get('sheet'), sheets, el.line)
            if el.get('solid') and el.get('ai') and el.get('ai') != 'shuttle':
                raise GameCompileError('a prefab is solid or has ai=, not both (a shuttle is both)', el.line)
            if el.get('ai') == 'shuttle' and not el.get('solid'):
                raise GameCompileError('ai="shuttle" is a solid: add solid="true"', el.line)
            if el.get('one-way') and not el.get('solid'):
                raise GameCompileError('one-way="true" is for a solid prefab', el.line)
            for attr in ('fire-sound',):
                if el.get(attr) and el.get(attr) not in sounds:
                    raise GameCompileError(f'{attr}="{el.get(attr)}": no qg:sound of that name', el.line)
            states, initial_state = _states(el, pscript, name, for_prefab=True)
            handlers = []
            for i, h in enumerate(el.find_all('on-collision')):
                hname = compile_handler(pscript, f'_{_ident(name)}_on_collision_{i}', h.children, h.line)
                handlers.append({'with': h.get('with'), 'cooldown': h.get('cooldown'), 'handler': hname})
            on_damage = on_death = None
            for h in el.find_all('on-damage'):
                on_damage = compile_handler(pscript, f'_{_ident(name)}_on_damage', h.children, h.line)
            for h in el.find_all('on-death'):
                if h.get('of'):
                    raise GameCompileError('of= is for a <qg:on-death> in a scene', h.line)
                on_death = compile_handler(pscript, f'_{_ident(name)}_on_death', h.children, h.line)
            prefabs[name] = {'tag': el.get('tag') or name.lower(), 'sheet': el.get('sheet'),
                             'frame': el.get('frame'), 'hitbox': list(el.get('hitbox')),
                             'ai': el.get('ai'), 'speed': _speed(el.get('speed'), el.line), 'sight': el.get('sight'),
                             'rotate': el.get('rotate'), 'range': el.get('range'), 'targets': el.get('targets'),
                             'attack': el.get('attack'), 'damage': el.get('damage'),
                             'direction': el.get('direction'), 'turns_at': el.get('turns-at'),
                             'gravity': el.get('gravity'), 'solid': el.get('solid'),
                             'one_way': el.get('one-way'), 'dx': el.get('dx'), 'dy': el.get('dy'),
                             'period': el.get('period'),
                             'heading': _heading(el.get('heading'), el.line), 'accel': el.get('accel'),
                             'lifetime': el.get('lifetime'),
                             'health': el.get('health'),
                             'fire_prefab': el.get('fire-prefab'), 'fire_every': el.get('fire-every'),
                             'fire_sound': el.get('fire-sound'),
                             'states': states, 'initial_state': initial_state,
                             'on_collision': handlers, 'on_damage': on_damage, 'on_death': on_death,
                             'animations': _animations(el)}
            gdprops.attach(prefabs[name], gdprops.PREFAB_CLASS[gdprops.prefab_kind(prefabs[name])], el.gd,
                           f'<qg:prefab name="{name}">', el.line)
        for pname, line in pscript.prefabs_used + [(p['fire_prefab'], el.line) for p in prefabs.values()
                                                   if p['fire_prefab']]:
            if pname not in prefabs:
                raise GameCompileError(
                    f'no qg:prefab named {pname!r} (declared: {", ".join(sorted(prefabs)) or "none"})', line)
        for played in pscript.sounds_played:
            if played not in sounds:
                raise GameCompileError(f'<qg:play sound="{played}">: no qg:sound of that name', None)
        tags = {p['tag'] for p in prefabs.values()} | self._zone_tags
        for p_ in prefabs.values():
            for h in p_['on_collision']:
                if h['with'] not in tags:
                    raise GameCompileError(
                        f'<qg:on-collision with="{h["with"]}">: no prefab or zone has that tag '
                        f'(tags: {", ".join(sorted(tags))})', None)
        self.scripts['prefabs.gd'] = prefabs_source(pscript)
        self._prefab_scenes_used = pscript.scenes_used
        scenes = {}
        self._scenes_used: List[tuple] = []
        self._exits_used: List[tuple] = []
        self._scene_exits: Dict[str, set] = {}
        self._scenes_used.extend(self._prefab_scenes_used)
        for scene in g.scenes:
            scenes[scene.get('name')] = self._scene(scene, sheets, prefabs)
        for sname, line in self._scenes_used:
            if sname not in scenes:
                raise GameCompileError(
                    f'no qg:scene named {sname!r} (declared: {", ".join(scenes)})', line)
        for here, to, at, line in self._exits_used:
            if at not in self._scene_exits.get(to, set()):
                raise GameCompileError(
                    f'<qg:exit to="{to}" at="{at}">: scene {to!r} has no exit named {at!r} '
                    f'(it has: {", ".join(sorted(self._scene_exits.get(to, set()))) or "none"})', line)
        return {
            'game': {
                'id': g.id,
                'initial': g.scenes[0].get('name'),
                'inputs': inputs,
                'actions': self.actions,
                'multiplayer': self.multiplayer,
                'sheets': sheets,
                'sounds': sounds,
                'prefabs': prefabs,
                'scenes': scenes,
            },
            'scripts': self.scripts,
            'assets': self.assets,
        }

    def _find(self, rel: str, line: Optional[int]) -> Path:
        """A file named in the .q: next to it, or in a folder above it."""
        rel = rel.replace('\\', '/').lstrip('/')
        for root in self.search_roots:
            d = root
            for _ in range(6):
                candidate = d / rel
                if candidate.is_file():
                    return candidate
                if d.parent == d:
                    break
                d = d.parent
        raise GameCompileError(f'file not found: {rel} (looked in {self.base_dir} and the folders above it)', line)

    def _asset(self, rel: str, line: Optional[int]) -> str:
        """A file copied into the build (an image, a sound); returns its path there."""
        rel = rel.replace('\\', '/').lstrip('/')
        self.assets[rel] = self._find(rel, line)
        return rel

    @staticmethod
    def _sheet_exists(name: str, sheets: dict, line: Optional[int]) -> None:
        if name not in sheets:
            known = ', '.join(sorted(sheets)) or 'none'
            raise GameCompileError(f'no qg:spritesheet or qg:tileset named {name!r} (declared: {known})', line)

    def _scene(self, scene: Element, sheets: dict, prefabs: dict) -> dict:
        name = scene.get('name')
        script = SceneScript(name, game_state=self.game_state)
        self._states_checked: list = []
        # 1. state and functions first: handlers refer to them
        for node in scene.children:
            if isinstance(node, Statement) and node.kind == 'set':
                if node.attrs['name'] in self.game_state and 'type' not in node.attrs and 'saved' not in node.attrs:
                    script.enter.append(node)   # the game's state, set as the scene is entered
                else:
                    declare_state(script, node)
        for node in scene.children:
            if isinstance(node, Statement) and node.kind == 'function':
                script.function_names.append(node.attrs['name'])
        for node in scene.children:
            if isinstance(node, Statement) and node.kind == 'function':
                compile_function(script, node)
            elif isinstance(node, Statement) and node.kind in ('if', 'loop', 'call'):
                script.enter.append(node)   # runs as the scene is entered
            elif isinstance(node, Element) and node.tag in ('play', 'stop'):
                script.enter.append(node)   # a sound as the scene is entered
            elif isinstance(node, Statement) and node.kind != 'set':
                raise GameCompileError(
                    f'<q:{node.kind}> directly in a scene: q:set, q:function, and q:if/q:loop/q:call '
                    f'(run as the scene is entered) go there', node.line)
        # 2. the nodes
        nodes: List[dict] = []
        ids: Dict[str, int] = {}
        tilemap: Optional[dict] = None
        map_nodes: Dict[str, dict] = {}
        map_paths: List[dict] = []
        on_input: Dict[str, str] = {}
        exits: Dict[str, dict] = {}
        zones: set = set()
        on_select: Dict[str, str] = {}
        cursors: set = set()
        paths: Dict[str, list] = {}
        conditions = 0
        on_death: Dict[str, str] = {}
        self._node_elements: List[Optional[Element]] = []
        for node in scene.children:
            if isinstance(node, Statement):
                continue
            el = node
            if el.tag == 'map-node':
                mname = el.get('name')
                if mname in map_nodes:
                    raise GameCompileError(f'two map nodes named {mname!r}', el.line)
                self._sheet_exists(el.get('sheet'), sheets, el.line)
                if el.get('scene'):
                    self._scenes_used.append((el.get('scene'), el.line))
                map_nodes[mname] = {'kind': 'map-node', 'name': mname, 'x': el.get('x'), 'y': el.get('y'),
                                    'sheet': el.get('sheet'), 'frame': el.get('frame'), 'scene': el.get('scene')}
                nodes.append(map_nodes[mname])
                self._node_elements.append(el)
            elif el.tag == 'map-path':
                if el.get('requires') is not None:
                    self._scenes_used.append((el.get('requires'), el.line))
                    if 'cleared' not in self.game_state:
                        raise GameCompileError(
                            '<qg:map-path requires=> reads the game state `cleared`: declare '
                            '<q:set name="cleared" type="array" /> in <q:application>', el.line)
                map_paths.append({'from': el.get('from'), 'to': el.get('to'), 'requires': el.get('requires'),
                                  'line': el.line})
            elif el.tag == 'zone':
                zname = el.get('name')
                if zname in zones:
                    raise GameCompileError(f'two zones named {zname!r}', el.line)
                zones.add(zname)
                nodes.append({'kind': 'zone', 'name': zname, 'tag': el.get('tag'), 'x': el.get('x'), 'y': el.get('y'),
                              'width': el.get('width'), 'height': el.get('height')})
                self._node_elements.append(el)
            elif el.tag == 'sprite':
                self._sheet_exists(el.get('sheet'), sheets, el.line)
                nodes.append({'kind': 'sprite', 'sheet': el.get('sheet'), 'frame': el.get('frame'),
                              'x': el.get('x'), 'y': el.get('y')})
                self._node_elements.append(el)
            elif el.tag == 'exit':
                ename = el.get('name')
                if ename in exits:
                    raise GameCompileError(f'two exits named {ename!r}', el.line)
                self._scenes_used.append((el.get('to'), el.line))
                self._exits_used.append((name, el.get('to'), el.get('at'), el.line))
                exits[ename] = {'kind': 'exit', 'name': ename, 'x': el.get('x'), 'y': el.get('y'),
                                'width': el.get('width'), 'height': el.get('height'),
                                'to': el.get('to'), 'at': el.get('at')}
                nodes.append(exits[ename])
                self._node_elements.append(el)
            elif el.tag == 'spawner':
                names = [p.strip() for p in str(el.get('prefab')).split(',') if p.strip()]
                for pname in names:
                    if pname not in prefabs:
                        raise GameCompileError(
                            f'no qg:prefab named {pname!r} (declared: {", ".join(sorted(prefabs)) or "none"})',
                            el.line)
                x = el.get('x')
                if x != 'random':
                    try:
                        x = float(x)
                    except ValueError:
                        raise GameCompileError(f'<qg:spawner x="{x}">: a number, or random', el.line)
                if el.get('heading') and not el.get('along'):
                    raise GameCompileError('<qg:spawner heading="inward"> goes with along="edges"', el.line)
                if el.get('heading') and any(not prefabs[p]['ai'] == 'fly' for p in names):
                    raise GameCompileError('<qg:spawner heading="inward">: every prefab must be ai="fly"', el.line)
                nodes.append({'kind': 'spawner', 'prefabs': names, 'from': el.get('from'),
                              'every': el.get('every'), 'count': el.get('count'), 'x': x, 'y': el.get('y'),
                              'along': el.get('along'), 'heading': el.get('heading'), 'spread': el.get('spread')})
                self._node_elements.append(el)
            elif el.tag == 'on-death':
                tag = el.get('of')
                if not tag:
                    raise GameCompileError('<qg:on-death> in a scene needs of= (a tag)', el.line)
                if tag in on_death:
                    raise GameCompileError(f'two <qg:on-death of="{tag}">', el.line)
                on_death[tag] = compile_handler(script, f'_on_death_of_{_ident(tag)}', el.children, el.line)
            elif el.tag == 'timer':
                if (el.get('after') is None) == (el.get('every') is None):
                    raise GameCompileError('<qg:timer> takes after= or every=, one of them', el.line)
                timers = sum(1 for n in nodes if n['kind'] == 'timer')
                handler = compile_handler(script, f'_on_timer_{timers}', el.children, el.line)
                nodes.append({'kind': 'timer', 'after': el.get('after'), 'every': el.get('every'),
                              'from': el.get('from'), 'count': el.get('count'), 'handler': handler})
                self._node_elements.append(el)
            elif el.tag == 'on-input':
                action = el.get('action')
                if action not in self.actions:
                    raise GameCompileError(
                        f'<qg:on-input action="{action}">: no such action (the defaults are '
                        f'{", ".join(DEFAULT_INPUTS)}; a qg:input declares another)', el.line)
                if action in on_input:
                    raise GameCompileError(f'two <qg:on-input action="{action}">', el.line)
                on_input[action] = compile_handler(script, f'_on_input_{_ident(action)}', el.children, el.line)
            elif el.tag == 'on-select':
                key = str(el.get('player') or 0)
                if key in on_select:
                    raise GameCompileError('two <qg:on-select> for the same player', el.line)
                on_select[key] = compile_handler(script, f'_on_select_{key}', el.children, el.line,
                                                 params=('cursor', 'other'))
            elif el.tag == 'cursor':
                if el.get('sheet'):
                    self._sheet_exists(el.get('sheet'), sheets, el.line)
                if el.get('player') in cursors:
                    raise GameCompileError(f'two <qg:cursor player="{el.get("player")}">', el.line)
                cursors.add(el.get('player'))
                nodes.append({'kind': 'cursor', 'player': el.get('player'), 'step': el.get('step'),
                              'grid': el.get('grid'), 'sheet': el.get('sheet'), 'frame': el.get('frame')})
                self._node_elements.append(el)
            elif el.tag == 'path':
                pname = el.get('name')
                if pname in paths:
                    raise GameCompileError(f'two paths named {pname!r}', el.line)
                paths[pname] = _points(el.get('points'), el.line)
                nodes.append({'kind': 'path', 'name': pname, 'points': paths[pname]})
                self._node_elements.append(el)
            elif el.tag == 'tilemap':
                if tilemap is not None:
                    raise GameCompileError('a scene has one <qg:tilemap>', el.line)
                self._sheet_exists(el.get('tileset'), sheets, el.line)
                if el.get('src'):
                    tmx = read_tmx(self._find(el.get('src'), el.line), el.line)
                    tile = sheets[el.get('tileset')]['tile'][0]
                    if (tmx.tile_width, tmx.tile_height) != (tile, tile):
                        raise GameCompileError(
                            f'{el.get("src")}: tiles are {tmx.tile_width}x{tmx.tile_height}, the tileset '
                            f'{el.get("tileset")!r} has {tile}x{tile}', el.line)
                    layers = [{'name': ly.name, 'rows': ly.rows, 'collision': ly.collision or el.get('collision')}
                              for ly in tmx.layers]
                    for obj in tmx.objects:
                        if obj.prefab not in prefabs:
                            raise GameCompileError(
                                f'{el.get("src")}: object {obj.name or obj.prefab!r} has class {obj.prefab!r}, '
                                f'no qg:prefab of that name (declared: {", ".join(sorted(prefabs)) or "none"})',
                                el.line)
                        nodes.append({'kind': 'instance', 'prefab': obj.prefab, 'x': obj.x, 'y': obj.y})
                        self._node_elements.append(None)
                else:
                    layers = [{'name': 'tiles', 'rows': _csv_rows(el), 'collision': el.get('collision')}]
                tilemap = {'kind': 'tilemap', 'tileset': el.get('tileset'), 'layers': layers}
                nodes.insert(0, tilemap)
                self._node_elements.insert(0, el)
            elif el.tag == 'character':
                cid = el.get('id')
                if cid in ids:
                    raise GameCompileError(f'two nodes with id {cid!r}', el.line)
                ids[cid] = el.line
                self._sheet_exists(el.get('sheet'), sheets, el.line)
                handlers = []
                for i, h in enumerate(el.find_all('on-collision')):
                    hname = compile_handler(script, f'_on_{_ident(cid)}_collision_{i}', h.children, h.line)
                    handlers.append({'with': h.get('with'), 'side': h.get('side'),
                                     'cooldown': h.get('cooldown'), 'handler': hname})
                hits = []
                for i, h in enumerate(el.find_all('on-hit')):
                    if not el.get('attack-action'):
                        raise GameCompileError('<qg:on-hit> needs attack-action= on the character', h.line)
                    hname = compile_handler(script, f'_on_{_ident(cid)}_hit_{i}', h.children, h.line)
                    hits.append({'with': h.get('with'), 'handler': hname})
                if el.get('attack-sound') and el.get('attack-sound') not in self.sounds:
                    raise GameCompileError(
                        f'attack-sound="{el.get("attack-sound")}": no qg:sound of that name', el.line)
                on_fall = None
                falls = el.find_all('on-fall')
                if len(falls) > 1:
                    raise GameCompileError('a character has one <qg:on-fall>', falls[1].line)
                if falls:
                    on_fall = compile_handler(script, f'_on_{_ident(cid)}_fall', falls[0].children, falls[0].line)
                if el.get('jump-sound') and el.get('jump-sound') not in self.sounds:
                    raise GameCompileError(
                        f'jump-sound="{el.get("jump-sound")}": no qg:sound of that name', el.line)
                states, initial_state = _states(el, script, cid, for_prefab=False,
                                                already=len(self._states_checked))
                self._states_checked = list(script.states_used)
                for attr in ('fire-sound',):
                    if el.get(attr) and el.get(attr) not in self.sounds:
                        raise GameCompileError(f'{attr}="{el.get(attr)}": no qg:sound of that name', el.line)
                if el.get('fire-prefab') and el.get('fire-prefab') not in prefabs:
                    raise GameCompileError(
                        f'fire-prefab="{el.get("fire-prefab")}": no qg:prefab of that name', el.line)
                at_method = None
                if el.get('controller') == 'map':
                    at = el.get('at')
                    if at is None:
                        raise GameCompileError('<qg:character controller="map"> needs at= (a map node)', el.line)
                    expr = compile_expression(at, script.scope(), el.line) if is_expression(at) \
                        else json.dumps(strip_braces(at))
                    at_method = f'_q_at_{_ident(cid)}'
                    script.functions.append(f'func {at_method}():\n\treturn {expr}\n')
                elif el.get('at') is not None:
                    raise GameCompileError('at= is for controller="map"', el.line)
                player = el.get('player')
                if player < 1:
                    raise GameCompileError('<qg:character player=>: 1 or more', el.line)
                if self.multiplayer is not None and player > self.multiplayer['players']:
                    raise GameCompileError(
                        f'<qg:character player="{player}">: the game has {self.multiplayer["players"]} players '
                        f'(qg:multiplayer)', el.line)
                if player > 1 and not any(k.startswith(f'p{player}_') for k in self.inputs):
                    raise GameCompileError(
                        f'<qg:character player="{player}">: no keys for that player — declare '
                        f'<qg:input player="{player}" action="up" keys="..." /> and so on in q:application', el.line)
                if el.get('axis') != 'both' and el.get('controller') != 'ship':
                    raise GameCompileError('axis= is for controller="ship"', el.line)
                if el.get('bounds') is not None and el.get('controller') not in ('ship', 'topdown'):
                    raise GameCompileError('bounds= is for controller="ship" or "topdown"', el.line)
                nodes.append({
                    'kind': 'character', 'id': cid, 'controller': el.get('controller'),
                    'player': player, 'axis': el.get('axis'),
                    'at_method': at_method, 'speed': el.get('speed'),
                    'sheet': el.get('sheet'), 'frame': el.get('frame'),
                    'x': el.get('x'), 'y': el.get('y'), 'hitbox': list(el.get('hitbox')),
                    'run_speed': el.get('run-speed'), 'jump_height': el.get('jump-height'),
                    'variable_jump': el.get('variable-jump'), 'coyote_frames': el.get('coyote-frames'),
                    'gravity': el.get('gravity'), 'max_fall': el.get('max-fall'),
                    'jump_sound': el.get('jump-sound'),
                    'bounds': el.get('bounds'), 'fire_action': el.get('fire-action'),
                    'fire_prefab': el.get('fire-prefab'), 'fire_every': el.get('fire-every'),
                    'fire_sound': el.get('fire-sound'),
                    'attack_action': el.get('attack-action'), 'attack_reach': el.get('attack-reach'),
                    'attack_frames': el.get('attack-frames'), 'attack_sound': el.get('attack-sound'),
                    'animations': _animations(el),
                    'states': states, 'initial_state': initial_state,
                    'on_collision': handlers, 'on_hit': hits, 'on_fall': on_fall,
                })
                self._node_elements.append(el)
            elif el.tag == 'instance':
                if el.get('prefab') not in prefabs:
                    known = ', '.join(sorted(prefabs)) or 'none'
                    raise GameCompileError(f'no qg:prefab named {el.get("prefab")!r} (declared: {known})', el.line)
                condition = None
                if el.get('if') is not None:
                    conditions += 1
                    condition = f'_q_if_{conditions}'
                    expr = compile_expression(el.get('if'), script.scope(), el.line)
                    script.functions.append(f'func {condition}() -> bool:\n\treturn {expr}\n')
                nodes.append({'kind': 'instance', 'prefab': el.get('prefab'), 'x': el.get('x'), 'y': el.get('y'),
                              'name': el.get('name'), 'if': condition})
                self._node_elements.append(el)
            elif el.tag == 'camera':
                nodes.append({'kind': 'camera', 'follow': el.get('follow'), 'bounds': el.get('bounds')})
                self._node_elements.append(el)
            elif el.tag == 'hud':
                items = []
                for c in el.children:
                    if isinstance(c, Element) and c.tag in ('counter', 'text'):
                        if c.get('bind') not in script.state and c.get('bind') not in self.game_state:
                            raise GameCompileError(
                                f'<qg:{c.tag} bind="{c.get("bind")}">: no q:set of that name in the scene '
                                f'or the game', c.line)
                        items.append({'kind': c.tag, 'bind': c.get('bind'), 'label': c.get('label', ''),
                                      'size': c.get('size')})
                        gdprops.attach(items[-1], 'Label', c.gd, f'<qg:{c.tag}>', c.line)
                    else:
                        raise GameCompileError('<qg:hud> holds qg:counter and qg:text', getattr(c, 'line', el.line))
                font = self._asset(el.get('font'), el.line) if el.get('font') else None
                nodes.append({'kind': 'hud', 'position': el.get('position'), 'items': items,
                              'font': font, 'size': el.get('size')})
                self._node_elements.append(el)
            elif el.tag in ('play', 'stop'):
                pass   # an enter statement, read above
            else:
                raise GameCompileError(f'<qg:{el.tag}> cannot go directly inside a scene', el.line)
        # 3. references between nodes
        for p in map_paths:
            for end in ('from', 'to'):
                if p[end] not in map_nodes:
                    raise GameCompileError(f'<qg:map-path {end}="{p[end]}">: no map node of that name', p['line'])
            del p['line']
        for n in nodes:
            if n['kind'] == 'character' and n['controller'] == 'map' and not map_nodes:
                raise GameCompileError('<qg:character controller="map"> in a scene without qg:map-node', scene.line)
        for n in nodes:
            if n['kind'] == 'camera' and n['follow'] not in ids:
                raise GameCompileError(f'<qg:camera follow="{n["follow"]}">: no character with that id', scene.line)
            if n['kind'] == 'camera' and n['bounds'] == 'tilemap' and tilemap is None:
                raise GameCompileError('<qg:camera bounds="tilemap"> in a scene without a tilemap', scene.line)
        tags = {p['tag'] for p in prefabs.values()}
        for tag in on_death:
            if tag not in tags:
                raise GameCompileError(f'<qg:on-death of="{tag}">: no prefab has that tag', scene.line)
        tags |= self._zone_tags
        for n in nodes:
            for kind in ('on_collision', 'on_hit'):
                for h in n.get(kind, []):
                    if h['with'] not in tags:
                        raise GameCompileError(
                            f'<qg:{kind.replace("_", "-")} with="{h["with"]}">: no prefab or zone has that tag '
                            f'(tags: {", ".join(sorted(tags)) or "none"})', scene.line)
        if on_select and not cursors:
            raise GameCompileError('<qg:on-select> in a scene without a <qg:cursor>', scene.line)
        for pname, line in script.paths_used:
            if pname not in paths:
                raise GameCompileError(f'<qg:spawn path="{pname}">: no qg:path of that name in the scene '
                                       f'(paths: {", ".join(sorted(paths)) or "none"})', line)
        self._scene_exits[name] = set(exits)
        self._scenes_used.extend(script.scenes_used)
        for pname, line in script.prefabs_used:
            if pname not in prefabs:
                raise GameCompileError(
                    f'no qg:prefab named {pname!r} (declared: {", ".join(sorted(prefabs)) or "none"})', line)
        for played in script.sounds_played:
            if played not in self.sounds:
                raise GameCompileError(
                    f'<qg:play sound="{played}">: no qg:sound of that name '
                    f'(declared: {", ".join(sorted(self.sounds)) or "none"})', scene.line)
        # gd: attributes, checked against the Godot class each node becomes
        for n, el in zip(nodes, self._node_elements):
            if el is None:
                continue
            if n['kind'] == 'instance':
                cls = gdprops.PREFAB_CLASS[gdprops.prefab_kind(prefabs[n['prefab']])]
            else:
                cls = gdprops.NODE_CLASS.get(n['kind'], 'Node')
            gdprops.attach(n, cls, el.gd, f'<qg:{el.tag}>', el.line)
        script_file = _script_name(name)
        self.scripts[script_file] = script.source()
        spec = {
            'name': name, 'script': f'res://scripts/{script_file}',
            'width': scene.get('width'), 'height': scene.get('height'),
            'background': scene.get('background'), 'seed': scene.get('seed'),
            'nodes': nodes, 'map_paths': map_paths, 'on_input': on_input, 'on_death': on_death,
            'on_select': on_select,
        }
        gdprops.attach(spec, 'Node2D', scene.gd, f'<qg:scene name="{name}">', scene.line)
        return spec


def _ident(text: str) -> str:
    return re.sub(r'[^A-Za-z0-9_]+', '_', text)


def _key(name: str, player: int, line: Optional[int]):
    """A qg:input key as game.json carries it: a key name, or a joypad button/axis of the player's pad."""
    if name in MOUSE_BUTTONS:
        return {'mouse_button': MOUSE_BUTTONS[name]}
    if name in JOY_BUTTONS:
        return {'joy_button': JOY_BUTTONS[name], 'device': player - 1}
    if name in JOY_AXES:
        axis, value = JOY_AXES[name]
        return {'joy_axis': axis, 'value': value, 'device': player - 1}
    if name.startswith('Joy'):
        raise GameCompileError(
            f'keys="{name}": not a joypad name (they are: {", ".join(list(JOY_BUTTONS) + list(JOY_AXES))})', line)
    return name


def _speed(raw, line: Optional[int]):
    """speed= as a number, or [min, max] for a range `a..b`."""
    raw = str(raw).strip()
    try:
        if '..' in raw:
            lo, hi = (float(v) for v in raw.split('..', 1))
            if hi < lo:
                raise ValueError
            return [lo, hi]
        return float(raw)
    except ValueError:
        raise GameCompileError(f'speed="{raw}": a number, or a range like 150..250', line)


def action_name(player: int, action: str) -> str:
    """The Godot input action of a player's action: `up` for player 1, `p2_up` for player 2."""
    return action if player == 1 else f'p{player}_{action}'


_HEADINGS = {'up': (0.0, -1.0), 'down': (0.0, 1.0), 'left': (-1.0, 0.0), 'right': (1.0, 0.0)}


def _points(raw: str, line: Optional[int]) -> list:
    """points= as [[x, y], ...]: `0,100; 200,100`."""
    out = []
    for part in str(raw).split(';'):
        if not part.strip():
            continue
        xy = part.split(',')
        try:
            if len(xy) != 2:
                raise ValueError
            out.append([float(xy[0]), float(xy[1])])
        except ValueError:
            raise GameCompileError(f'points="{raw}": x,y pairs separated by semicolons', line)
    if len(out) < 2:
        raise GameCompileError('points= needs at least two points', line)
    return out


def _heading(raw: str, line: Optional[int]) -> list:
    """heading= as a unit vector [x, y]: a word, or `x,y`."""
    raw = str(raw).strip()
    if raw in _HEADINGS:
        return list(_HEADINGS[raw])
    parts = raw.split(',')
    try:
        if len(parts) != 2:
            raise ValueError
        x, y = float(parts[0]), float(parts[1])
    except ValueError:
        raise GameCompileError(f'heading="{raw}": up, down, left, right, or x,y (e.g. -1,0.5)', line)
    length = (x * x + y * y) ** 0.5
    if length == 0:
        raise GameCompileError('heading="0,0" goes nowhere', line)
    return [x / length, y / length]


def _states(el: Element, script: SceneScript, owner: str, for_prefab: bool, already: int = 0):
    """The qg:states of a character or a prefab: (states, initial)."""
    states: Dict[str, dict] = {}
    initial_state = None
    for st in el.find_all('state'):
        sname = st.get('name')
        if sname in states:
            raise GameCompileError(f'two states named {sname!r}', st.line)
        if not for_prefab and st.get('hitbox') is None:
            raise GameCompileError('<qg:state> of a character needs hitbox=', st.line)
        states[sname] = {'hitbox': list(st.get('hitbox')) if st.get('hitbox') else None,
                         'frame': st.get('frame'), 'speed': st.get('speed'), 'fire_every': st.get('fire-every'),
                         'fire_prefab': st.get('fire-prefab'), 'range': st.get('range'),
                         'animations': _animations(st)}
        if st.get('initial'):
            if initial_state is not None:
                raise GameCompileError('two states marked initial', st.line)
            initial_state = sname
    if states and initial_state is None:
        initial_state = next(iter(states))
    for sname, line in script.states_used[already:]:
        if sname not in states:
            raise GameCompileError(
                f'<qg:become state="{sname}">: {owner!r} has no qg:state of that name '
                f'(it has: {", ".join(states) or "none"})', line)
    return states, initial_state


def _animations(el: Element) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for a in el.find_all('animation'):
        name = a.get('name')
        if name in out:
            raise GameCompileError(f'two animations named {name!r}', a.line)
        try:
            frames = [int(f.strip()) for f in str(a.get('frames')).split(',') if f.strip()]
        except ValueError:
            raise GameCompileError(f'frames="{a.get("frames")}": comma-separated frame numbers', a.line)
        if not frames:
            raise GameCompileError('<qg:animation> needs at least one frame', a.line)
        out[name] = {'frames': frames, 'fps': a.get('fps')}
    return out


def _csv_rows(el: Element) -> List[List[int]]:
    rows = []
    for raw in el.text.splitlines():
        raw = raw.strip().rstrip(',')
        if not raw:
            continue
        try:
            rows.append([int(v.strip()) for v in raw.split(',')])
        except ValueError:
            raise GameCompileError(f'<qg:tilemap>: a row is not numbers: {raw[:40]!r}', el.line)
    if not rows:
        raise GameCompileError('<qg:tilemap> is empty', el.line)
    width = len(rows[0])
    for i, r in enumerate(rows):
        if len(r) != width:
            raise GameCompileError(f'<qg:tilemap>: row {i + 1} has {len(r)} tiles, row 1 has {width}', el.line)
    return rows
