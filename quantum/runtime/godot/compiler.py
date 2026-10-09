"""Writes the Godot project: game.json, the scene scripts, the runtime, the assets."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from quantum.runtime.godot.errors import GameCompileError
from quantum.runtime.godot.model import Element, Game, Statement, read_game
from quantum.runtime.godot.statements import (
    SceneScript, compile_function, compile_handler, declare_state,
)

ADDON_SRC = Path(__file__).with_name('addons') / 'quantum'

# The keys a platformer controller reads, until a qg:input says otherwise.
DEFAULT_INPUTS = {
    'left': ['Left', 'A'],
    'right': ['Right', 'D'],
    'jump': ['Space', 'Z', 'Up', 'W'],
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

    data = _Compiler(game, base_dir).build()

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
    def __init__(self, game: Game, base_dir: Path):
        self.game = game
        self.base_dir = base_dir
        self.assets: Dict[str, Path] = {}
        self.scripts: Dict[str, str] = {}

    def build(self) -> dict:
        g = self.game
        sheets = {}
        for name, el in list(g.tilesets.items()) + list(g.sheets.items()):
            sheets[name] = {'src': self._asset(el.get('src'), el.line), 'tile': el.get('tile'),
                            'kind': el.tag}
        prefabs = {}
        for name, el in g.prefabs.items():
            self._sheet_exists(el.get('sheet'), sheets, el.line)
            prefabs[name] = {'tag': el.get('tag') or name.lower(), 'sheet': el.get('sheet'),
                             'frame': el.get('frame'), 'hitbox': list(el.get('hitbox'))}
        scenes = {}
        for scene in g.scenes:
            scenes[scene.get('name')] = self._scene(scene, sheets, prefabs)
        return {
            'game': {
                'id': g.id,
                'initial': g.scenes[0].get('name'),
                'inputs': DEFAULT_INPUTS,
                'sheets': sheets,
                'prefabs': prefabs,
                'scenes': scenes,
            },
            'scripts': self.scripts,
            'assets': self.assets,
        }

    def _asset(self, rel: str, line: Optional[int]) -> str:
        rel = rel.replace('\\', '/').lstrip('/')
        d = self.base_dir
        for _ in range(6):
            candidate = d / rel
            if candidate.is_file():
                self.assets[rel] = candidate
                return rel
            if d.parent == d:
                break
            d = d.parent
        raise GameCompileError(f'asset not found: {rel} (looked in {self.base_dir} and the folders above it)', line)

    @staticmethod
    def _sheet_exists(name: str, sheets: dict, line: Optional[int]) -> None:
        if name not in sheets:
            known = ', '.join(sorted(sheets)) or 'none'
            raise GameCompileError(f'no qg:spritesheet or qg:tileset named {name!r} (declared: {known})', line)

    def _scene(self, scene: Element, sheets: dict, prefabs: dict) -> dict:
        name = scene.get('name')
        script = SceneScript(name)
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
        for node in scene.children:
            if isinstance(node, Statement):
                continue
            el = node
            if el.tag == 'tilemap':
                if tilemap is not None:
                    raise GameCompileError('a scene has one <qg:tilemap>', el.line)
                self._sheet_exists(el.get('tileset'), sheets, el.line)
                tilemap = {'kind': 'tilemap', 'tileset': el.get('tileset'),
                           'collision': el.get('collision'), 'rows': _csv_rows(el)}
                nodes.append(tilemap)
            elif el.tag == 'character':
                cid = el.get('id')
                if cid in ids:
                    raise GameCompileError(f'two nodes with id {cid!r}', el.line)
                ids[cid] = el.line
                self._sheet_exists(el.get('sheet'), sheets, el.line)
                handlers = []
                for i, h in enumerate(el.find_all('on-collision')):
                    hname = compile_handler(script, f'_on_{_ident(cid)}_collision_{i}', h.children, h.line)
                    handlers.append({'with': h.get('with'), 'handler': hname})
                nodes.append({
                    'kind': 'character', 'id': cid, 'controller': el.get('controller'),
                    'sheet': el.get('sheet'), 'frame': el.get('frame'),
                    'x': el.get('x'), 'y': el.get('y'), 'hitbox': list(el.get('hitbox')),
                    'run_speed': el.get('run-speed'), 'jump_height': el.get('jump-height'),
                    'variable_jump': el.get('variable-jump'), 'coyote_frames': el.get('coyote-frames'),
                    'gravity': el.get('gravity'), 'max_fall': el.get('max-fall'),
                    'on_collision': handlers,
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
                    if isinstance(c, Element) and c.tag == 'counter':
                        if c.get('bind') not in script.state:
                            raise GameCompileError(
                                f'<qg:counter bind="{c.get("bind")}">: no q:set of that name in the scene', c.line)
                        items.append({'kind': 'counter', 'bind': c.get('bind'), 'label': c.get('label')})
                    else:
                        raise GameCompileError('<qg:hud> holds qg:counter', getattr(c, 'line', el.line))
                nodes.append({'kind': 'hud', 'position': el.get('position'), 'items': items})
            else:
                raise GameCompileError(f'<qg:{el.tag}> cannot go directly inside a scene', el.line)
        # 3. references between nodes
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
        script_file = _script_name(name)
        self.scripts[script_file] = script.source()
        return {
            'name': name, 'script': f'res://scripts/{script_file}',
            'width': scene.get('width'), 'height': scene.get('height'),
            'background': scene.get('background'), 'seed': scene.get('seed'),
            'nodes': nodes,
        }


def _ident(text: str) -> str:
    return re.sub(r'[^A-Za-z0-9_]+', '_', text)


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
