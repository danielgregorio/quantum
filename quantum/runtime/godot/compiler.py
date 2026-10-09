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
from quantum.runtime.godot.statements import (
    SceneScript, StateVar, compile_function, compile_handler, declare_state, game_state_source,
    is_expression,
)

ADDON_SRC = Path(__file__).with_name('addons') / 'quantum'

# The keys a platformer controller reads, until a qg:input says otherwise.
DEFAULT_INPUTS = {
    'left': ['Left', 'A'],
    'right': ['Right', 'D'],
    'up': ['Up', 'W'],
    'down': ['Down', 'S'],
    'jump': ['Space', 'Z', 'X'],
}

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
        sheets = {}
        for name, el in list(g.tilesets.items()) + list(g.sheets.items()):
            sheets[name] = {'src': self._asset(el.get('src'), el.line), 'tile': el.get('tile'),
                            'kind': el.tag}
        sounds = {}
        for name, el in g.sounds.items():
            sounds[name] = {'src': self._asset(el.get('src'), el.line)}
        self.sounds = sounds
        prefabs = {}
        for name, el in g.prefabs.items():
            self._sheet_exists(el.get('sheet'), sheets, el.line)
            prefabs[name] = {'tag': el.get('tag') or name.lower(), 'sheet': el.get('sheet'),
                             'frame': el.get('frame'), 'hitbox': list(el.get('hitbox')),
                             'ai': el.get('ai'), 'speed': el.get('speed'),
                             'direction': el.get('direction'), 'turns_at': el.get('turns-at'),
                             'gravity': el.get('gravity'), 'solid': el.get('solid'),
                             'animations': _animations(el)}
            if el.get('solid') and el.get('ai'):
                raise GameCompileError('a prefab is solid or has ai=, not both', el.line)
        scenes = {}
        self._scenes_used: List[tuple] = []
        for scene in g.scenes:
            scenes[scene.get('name')] = self._scene(scene, sheets, prefabs)
        for sname, line in self._scenes_used:
            if sname not in scenes:
                raise GameCompileError(
                    f'no qg:scene named {sname!r} (declared: {", ".join(scenes)})', line)
        return {
            'game': {
                'id': g.id,
                'initial': g.scenes[0].get('name'),
                'inputs': DEFAULT_INPUTS,
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
                declare_state(script, node)
        for node in scene.children:
            if isinstance(node, Statement) and node.kind == 'function':
                script.function_names.append(node.attrs['name'])
        for node in scene.children:
            if isinstance(node, Statement) and node.kind == 'function':
                compile_function(script, node)
            elif isinstance(node, Statement) and node.kind != 'set':
                raise GameCompileError(
                    f'<q:{node.kind}> directly in a scene: only q:set and q:function go there; '
                    f'logic goes inside a handler', node.line)
        # 2. the nodes
        nodes: List[dict] = []
        ids: Dict[str, int] = {}
        tilemap: Optional[dict] = None
        map_nodes: Dict[str, dict] = {}
        map_paths: List[dict] = []
        on_input: Dict[str, str] = {}
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
            elif el.tag == 'map-path':
                if el.get('requires') is not None:
                    self._scenes_used.append((el.get('requires'), el.line))
                    if 'cleared' not in self.game_state:
                        raise GameCompileError(
                            '<qg:map-path requires=> reads the game state `cleared`: declare '
                            '<q:set name="cleared" type="array" /> in <q:application>', el.line)
                map_paths.append({'from': el.get('from'), 'to': el.get('to'), 'requires': el.get('requires'),
                                  'line': el.line})
            elif el.tag == 'on-input':
                action = el.get('action')
                if action in on_input:
                    raise GameCompileError(f'two <qg:on-input action="{action}">', el.line)
                on_input[action] = compile_handler(script, f'_on_input_{action}', el.children, el.line)
            elif el.tag == 'tilemap':
                if tilemap is not None:
                    raise GameCompileError('a scene has one <qg:tilemap>', el.line)
                self._sheet_exists(el.get('tileset'), sheets, el.line)
                if el.get('src'):
                    tmx = read_tmx(self._find(el.get('src'), el.line), el.line)
                    tile = sheets[el.get('tileset')]['tile']
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
                else:
                    layers = [{'name': 'tiles', 'rows': _csv_rows(el), 'collision': el.get('collision')}]
                tilemap = {'kind': 'tilemap', 'tileset': el.get('tileset'), 'layers': layers}
                nodes.insert(0, tilemap)
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
                on_fall = None
                falls = el.find_all('on-fall')
                if len(falls) > 1:
                    raise GameCompileError('a character has one <qg:on-fall>', falls[1].line)
                if falls:
                    on_fall = compile_handler(script, f'_on_{_ident(cid)}_fall', falls[0].children, falls[0].line)
                if el.get('jump-sound') and el.get('jump-sound') not in self.sounds:
                    raise GameCompileError(
                        f'jump-sound="{el.get("jump-sound")}": no qg:sound of that name', el.line)
                states = {}
                initial_state = None
                for st in el.find_all('state'):
                    sname = st.get('name')
                    if sname in states:
                        raise GameCompileError(f'two states named {sname!r}', st.line)
                    states[sname] = {'hitbox': list(st.get('hitbox')), 'frame': st.get('frame'),
                                     'animations': _animations(st)}
                    if st.get('initial'):
                        if initial_state is not None:
                            raise GameCompileError('two states marked initial', st.line)
                        initial_state = sname
                if states and initial_state is None:
                    initial_state = next(iter(states))
                for sname, line in script.states_used[len(self._states_checked):]:
                    if sname not in states:
                        raise GameCompileError(
                            f'<qg:become state="{sname}">: {cid!r} has no qg:state of that name '
                            f'(it has: {", ".join(states) or "none"})', line)
                self._states_checked = list(script.states_used)
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
                nodes.append({
                    'kind': 'character', 'id': cid, 'controller': el.get('controller'),
                    'at_method': at_method, 'speed': el.get('speed'),
                    'sheet': el.get('sheet'), 'frame': el.get('frame'),
                    'x': el.get('x'), 'y': el.get('y'), 'hitbox': list(el.get('hitbox')),
                    'run_speed': el.get('run-speed'), 'jump_height': el.get('jump-height'),
                    'variable_jump': el.get('variable-jump'), 'coyote_frames': el.get('coyote-frames'),
                    'gravity': el.get('gravity'), 'max_fall': el.get('max-fall'),
                    'jump_sound': el.get('jump-sound'),
                    'animations': _animations(el),
                    'states': states, 'initial_state': initial_state,
                    'on_collision': handlers, 'on_fall': on_fall,
                })
            elif el.tag == 'instance':
                if el.get('prefab') not in prefabs:
                    known = ', '.join(sorted(prefabs)) or 'none'
                    raise GameCompileError(f'no qg:prefab named {el.get("prefab")!r} (declared: {known})', el.line)
                nodes.append({'kind': 'instance', 'prefab': el.get('prefab'), 'x': el.get('x'), 'y': el.get('y')})
            elif el.tag == 'camera':
                nodes.append({'kind': 'camera', 'follow': el.get('follow'), 'bounds': el.get('bounds')})
            elif el.tag == 'hud':
                items = []
                for c in el.children:
                    if isinstance(c, Element) and c.tag in ('counter', 'text'):
                        if c.get('bind') not in script.state and c.get('bind') not in self.game_state:
                            raise GameCompileError(
                                f'<qg:{c.tag} bind="{c.get("bind")}">: no q:set of that name in the scene '
                                f'or the game', c.line)
                        items.append({'kind': c.tag, 'bind': c.get('bind'), 'label': c.get('label', '')})
                    else:
                        raise GameCompileError('<qg:hud> holds qg:counter and qg:text', getattr(c, 'line', el.line))
                nodes.append({'kind': 'hud', 'position': el.get('position'), 'items': items})
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
        for n in nodes:
            for h in n.get('on_collision', []):
                if h['with'] not in tags:
                    raise GameCompileError(
                        f'<qg:on-collision with="{h["with"]}">: no prefab has that tag '
                        f'(tags: {", ".join(sorted(tags)) or "none"})', scene.line)
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
        script_file = _script_name(name)
        self.scripts[script_file] = script.source()
        return {
            'name': name, 'script': f'res://scripts/{script_file}',
            'width': scene.get('width'), 'height': scene.get('height'),
            'background': scene.get('background'), 'seed': scene.get('seed'),
            'nodes': nodes, 'map_paths': map_paths, 'on_input': on_input,
        }


def _ident(text: str) -> str:
    return re.sub(r'[^A-Za-z0-9_]+', '_', text)


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
