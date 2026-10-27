"""Writes the Godot project: game.json, the scene scripts, the runtime, the assets."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from quantum.runtime.godot.errors import GameCompileError
from quantum.runtime.godot.model import Element, Game, Statement, read_game
from quantum.runtime.godot.expressions import (
    CONTROLLER_FIELDS, CURSOR_FIELDS, THING_FIELDS, compile_expression, strip_braces,
)
from quantum.runtime.godot.schema import TAGS
from quantum.runtime.godot.tiled import read_tmx
from quantum.runtime.godot import gd as gdprops
from quantum.runtime.godot.statements import (
    SceneScript, StateVar, compile_function, compile_game_functions, compile_handler, declare_state,
    game_state_source, is_expression, prefabs_source,
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
    # the mouse button alone: a menu tells a click (what is under the pointer) from Enter (what has the focus)
    'click': ['MouseLeft'],
}
MOUSE_BUTTONS = {'MouseLeft': 1, 'MouseRight': 2, 'MouseMiddle': 3, 'WheelUp': 4, 'WheelDown': 5}

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

[editor]
; One file at a time: Godot 4.4 imports the files of an importer on several threads, and two fonts
; imported together sometimes crash the import, or hang it. One at a time is as quick here.
import/use_multiple_threads=false

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
                                'check_every': mp.get('check-every'), 'transport': mp.get('transport')}
            if mp.get('min-players') is not None:
                if not 2 <= mp.get('min-players') < mp.get('players'):
                    raise GameCompileError('<qg:multiplayer min-players=>: 2 or more, and fewer than players=', mp.line)
                if mp.get('rollback'):
                    raise GameCompileError('<qg:multiplayer min-players=> goes with the plain lockstep, not rollback=',
                                           mp.line)
                self.multiplayer['min_players'] = mp.get('min-players')
            if mp.get('rollback'):
                if mp.get('rollback') < 1:
                    raise GameCompileError('<qg:multiplayer rollback=>: 1 or more ticks (0 is off)', mp.line)
                self.multiplayer['rollback'] = mp.get('rollback')
            if mp.get('start'):
                if not any(sc.get('name') == mp.get('start') for sc in g.scenes):
                    raise GameCompileError(f'<qg:multiplayer start="{mp.get("start")}">: no scene of that name', mp.line)
                self.multiplayer['start'] = mp.get('start')
            # every player's actions exist; under lockstep they are pressed by the runtime, not by keys
            for p in range(2, mp.get('players') + 1):
                for action in self.actions:
                    inputs.setdefault(action_name(p, action), [])
        self.inputs = inputs
        # qg:connect: the game is a world's client; the world's file says what it may ask and will see
        self.world = None
        self.world_spec = None
        if g.connect is not None:
            self._connect(g)
        # the tags of the zones of every scene: handlers may name them like a prefab's
        self._zone_tags = {z.get('tag') for sc in g.scenes for z in sc.find_all('zone')}
        sheets = {}
        for name, el in list(g.tilesets.items()) + list(g.sheets.items()):
            if el.gd:
                raise GameCompileError(f'<qg:{el.tag}> becomes no Godot node: gd: attributes go on what is placed', el.line)
            tile = el.get('tile')
            if isinstance(tile, int):
                tile = (tile, tile)
            shaped = el.tag == 'tileset' and el.get('shape') != 'square'
            if el.tag == 'tileset' and not shaped and tile[0] != tile[1]:
                raise GameCompileError(f'<qg:tileset name="{name}" tile="{tile[0]}x{tile[1]}">: square tiles are '
                                       f'square (tile="{tile[0]}"); WxH is for shape="hex" or "iso"', el.line)
            sheets[name] = {'src': self._asset(el.get('src'), el.line), 'tile': list(tile),
                            'kind': el.tag}
            if shaped:
                sheets[name]['shape'] = el.get('shape')
            if el.get('slice') is not None:
                sheets[name]['slice'] = _slice(el.get('slice'), tile, name, el.line)
            tiles = {}
            for t in el.find_all('tile'):
                if str(t.get('frame')) in tiles:
                    raise GameCompileError(f'two <qg:tile frame="{t.get("frame")}"> in tileset {name!r}', t.line)
                if t.get('frame') < 0:
                    raise GameCompileError('<qg:tile frame=>: 0 or more', t.line)
                shape = t.get('shape')
                if t.get('kind') in ('ladder', 'water'):
                    if shape is not None and str(shape).strip() != 'none' or t.get('one-way'):
                        raise GameCompileError(f'<qg:tile kind="{t.get("kind")}"> is passed through: no shape= '
                                               f'or one-way=', t.line)
                    shape = 'none'
                if shape is not None and str(shape).strip() == 'none':
                    if t.get('one-way'):
                        raise GameCompileError('<qg:tile shape="none"> is not solid: one-way= means nothing', t.line)
                    points = None
                elif shape is None and shaped:
                    points = 'cell'   # the whole hex (or diamond)
                elif shape is None:
                    size = float(tile[0])
                    points = [[0.0, 0.0], [size, 0.0], [size, size], [0.0, size]]
                else:
                    points = _points(shape, t.line)
                    if len(points) < 3:
                        raise GameCompileError('<qg:tile shape=>: at least three points', t.line)
                tiles[str(t.get('frame'))] = {'shape': points, 'one_way': t.get('one-way')}
                if t.get('kind'):
                    tiles[str(t.get('frame'))]['kind'] = t.get('kind')
                if t.get('cost') != 1:
                    if t.get('cost') < 1:
                        raise GameCompileError('<qg:tile cost=>: what a step onto it costs, 1 or more', t.line)
                    tiles[str(t.get('frame'))]['cost'] = t.get('cost')
                if t.get('frames') != 1:
                    if t.get('frames') < 1 or t.get('fps') <= 0:
                        raise GameCompileError('<qg:tile frames=>: 1 or more, and fps= more than 0', t.line)
                    tiles[str(t.get('frame'))].update({'frames': t.get('frames'), 'fps': t.get('fps')})
            if tiles:
                sheets[name]['tiles'] = tiles
        sounds = {}
        for name, el in g.sounds.items():
            sounds[name] = {'src': self._asset(el.get('src'), el.line), 'loop': el.get('loop')}
            if el.get('bus'):
                if el.get('bus') == 'Master':
                    raise GameCompileError('<qg:sound bus="Master">: Master is every bus together; name a bus of '
                                           'your own (music, effects)', el.line)
                sounds[name]['bus'] = el.get('bus')
            gdprops.attach(sounds[name], 'AudioStreamPlayer', el.gd, f'<qg:sound name="{name}">', el.line)
        self.sounds = sounds
        self.buses = sorted({s_['bus'] for s_ in sounds.values() if s_.get('bus')})
        particles = {}
        for name, el in g.particles.items():
            particles[name] = {'preset': el.get('preset')}
            for k in ('color', 'amount', 'lifetime', 'speed', 'size'):
                if el.get(k) is not None:
                    particles[name][k] = el.get(k)
        self.particles = particles
        self.items = self._items(sheets)
        self.scripts['game_state.gd'] = game_state_source(self.game_state, self.items)
        languages = {}
        for lang_el in g.languages:
            code = str(lang_el.get('lang'))
            if not re.match(r'^[a-z]{2,3}(_[A-Z]{2})?$', code):
                raise GameCompileError(f'<qg:language lang="{code}">: a language code, as pt, es or pt_BR', lang_el.line)
            forms = PLURAL_FORMS.get(code.split('_')[0], ('one',))
            phrases, plurals = {}, {}
            for ph in lang_el.children:
                if not (isinstance(ph, Element) and ph.tag in ('phrase', 'asset')):
                    raise GameCompileError('<qg:language> holds qg:phrase and qg:asset',
                                           getattr(ph, 'line', lang_el.line))
                if ph.tag == 'asset':
                    self._language_asset(ph, code, sheets, sounds)
                    continue
                if ph.get('text') in phrases:
                    raise GameCompileError(f'<qg:phrase text="{ph.get("text")}">: twice in lang="{code}"', ph.line)
                phrases[ph.get('text')] = ph.get('as')
                kinds = {k: ph.get(k) for k in ('one', 'few', 'many') if ph.get(k) is not None}
                for k in kinds:
                    if k not in forms:
                        has = ', '.join(f'{f}=' for f in forms) or 'none: a count\'s word is the same for any number'
                        raise GameCompileError(f'<qg:phrase {k}=>: a count\'s word in {code} has no such form (its '
                                               f'forms besides as=: {has})', ph.line)
                if kinds:
                    plurals[ph.get('text')] = kinds
            if self.multiplayer is not None:
                phrases = {**LOBBY_PHRASES.get(code.split('_')[0], {}), **phrases}
            languages[code] = {'name': lang_el.get('name') or code, 'phrases': phrases}
            if plurals:
                languages[code]['plurals'] = plurals
            if lang_el.get('font'):
                languages[code]['font'] = self._asset(lang_el.get('font'), lang_el.line)
        self.languages = languages
        prefabs = {}
        self._part_targets: List[tuple] = []
        pscript = SceneScript('prefabs', game_state=self.game_state, actions=self.actions, world=self.world)
        pscript.buses = set(self.buses)
        compile_game_functions(pscript, g.functions)   # a prefab's handlers call the game's q:functions too
        for name, el in g.prefabs.items():
            self._sheet_exists(el.get('sheet'), sheets, el.line)
            if el.get('solid') and el.get('ai') and el.get('ai') != 'shuttle':
                raise GameCompileError('a prefab is solid or has ai=, not both (a shuttle is both)', el.line)
            if el.get('ai') == 'shuttle' and not el.get('solid'):
                raise GameCompileError('ai="shuttle" is a solid: add solid="true"', el.line)
            if el.get('one-way') and not el.get('solid'):
                raise GameCompileError('one-way="true" is for a solid prefab', el.line)
            shape = None
            if el.get('shape') is not None:
                if not el.get('solid'):
                    raise GameCompileError('shape= is for a solid prefab', el.line)
                shape = _points(el.get('shape'), el.line)
                if len(shape) < 3:
                    raise GameCompileError('<qg:prefab shape=>: at least three points', el.line)
            if el.get('walls') != 'pass' and el.get('ai') != 'fly':
                raise GameCompileError('walls= is for ai="fly"', el.line)
            if el.get('pushable') and not el.get('solid'):
                raise GameCompileError('pushable="true" is for a solid prefab (solid="true"): what a step pushes '
                                       'is what a step is stopped by', el.line)
            if el.get('spacing') < 0:
                raise GameCompileError('<qg:prefab spacing=>: 0 or more (pixels)', el.line)
            if el.get('spacing') and (el.get('solid') or el.get('ai') in (None, 'fly', 'shuttle', 'turret', 'path')):
                raise GameCompileError('spacing= is for a prefab that walks: ai="patrol", "wander", "chase", '
                                       '"pathfind", "sway" or "behavior"', el.line)
            if el.get('scale') <= 0:
                raise GameCompileError('<qg:prefab scale=>: more than 0', el.line)
            for attr in ('fire-sound',):
                if el.get(attr) and el.get(attr) not in sounds:
                    raise GameCompileError(f'{attr}="{el.get(attr)}": no qg:sound of that name', el.line)
            mark = len(pscript.states_used)   # the become target="me" of this prefab's own handlers, below
            states, initial_state = _states(el, pscript, name, for_prefab=True, already=mark)
            handlers = []
            touches = el.find_all('on-collision')
            if touches and el.get('ai') in (None, 'shuttle'):
                raise GameCompileError(f'<qg:on-collision> on {name!r}, a prefab that does not move: it would never '
                                       f'run — put it on what moves into it, `with="{el.get("tag") or name.lower()}"`',
                                       touches[0].line)
            for i, h in enumerate(touches):
                hname = compile_handler(pscript, f'_{_ident(name)}_on_collision_{i}', h.children, h.line)
                handlers.append({'with': h.get('with'), 'side': h.get('side'), 'cooldown': h.get('cooldown'),
                                 'handler': hname})
            on_damage = on_death = None
            for h in el.find_all('on-damage'):
                on_damage = compile_handler(pscript, f'_{_ident(name)}_on_damage', h.children, h.line)
            for h in el.find_all('on-death'):
                if h.get('of'):
                    raise GameCompileError('of= is for a <qg:on-death> in a scene', h.line)
                on_death = compile_handler(pscript, f'_{_ident(name)}_on_death', h.children, h.line)
            parts = self._prefab_parts(el, name, pscript)
            carry = self._prefab_items(el, name, pscript)
            prefab_contacts = _contact_handlers(el, pscript, f'_{_ident(name)}')
            for sname, line in pscript.states_used[mark:]:
                if sname not in states:
                    raise GameCompileError(f'<qg:become state="{sname}">: {name!r} has no qg:state of that name '
                                           f'(it has: {", ".join(states) or "none"})', line)
            prefabs[name] = {'tag': el.get('tag') or name.lower(), 'sheet': el.get('sheet'),
                             'frame': el.get('frame'), 'hitbox': list(el.get('hitbox')),
                             'ai': el.get('ai'), 'speed': _speed(el.get('speed'), el.line), 'sight': el.get('sight'),
                             'rotate': el.get('rotate'), 'range': el.get('range'), 'targets': el.get('targets'),
                             'attack': el.get('attack'), 'damage': el.get('damage'),
                             'direction': el.get('direction'), 'turns_at': el.get('turns-at'),
                             'gravity': el.get('gravity'), 'solid': el.get('solid'),
                             'one_way': el.get('one-way'), 'dx': el.get('dx'), 'dy': el.get('dy'),
                             'shape': shape, 'scale': el.get('scale'), 'walls': el.get('walls'),
                             'period': el.get('period'),
                             'heading': _heading(el.get('heading'), el.line), 'accel': el.get('accel'),
                             'lifetime': el.get('lifetime'),
                             'health': el.get('health'),
                             'fire_prefab': el.get('fire-prefab'), 'fire_every': el.get('fire-every'),
                             'fire_sound': el.get('fire-sound'),
                             'states': states, 'initial_state': initial_state,
                             'on_collision': handlers, 'on_damage': on_damage, 'on_death': on_death,
                             'animations': _animations(el),
                             'on_animation_end': _animation_ends(el, pscript, f'_{_ident(name)}_on')}
            prefabs[name].update(prefab_contacts)
            prefabs[name].update(_looks(el, pscript, f'_{_ident(name)}', self.particles))
            if el.get('trail') is not None:
                prefabs[name]['trail'] = el.get('trail')
            if el.get('spacing'):
                prefabs[name]['spacing'] = el.get('spacing')
            if el.get('pushable'):
                prefabs[name]['pushable'] = True
            if parts:
                prefabs[name]['parts'] = parts
            prefabs[name].update(carry)
            gdprops.attach(prefabs[name], gdprops.PREFAB_CLASS[gdprops.prefab_kind(prefabs[name])], el.gd,
                           f'<qg:prefab name="{name}">', el.line)
        for pname, line in pscript.prefabs_used + [(p['fire_prefab'], el.line) for p in prefabs.values()
                                                   if p['fire_prefab']]:
            if pname not in prefabs:
                raise GameCompileError(
                    f'no qg:prefab named {pname!r} (declared: {", ".join(sorted(prefabs)) or "none"})', line)
        _heading_is_flown(pscript.headed, prefabs)
        for played in pscript.sounds_played:
            if played not in sounds:
                raise GameCompileError(f'<qg:play sound="{played}">: no qg:sound of that name', None)
        for pname, line in pscript.particles_used:
            if pname not in self.particles:
                raise GameCompileError(f'<qg:emit particles="{pname}">: no qg:particles of that name', line)
        self._animations_known(pscript.animations_played)
        self._items_known(pscript.items_used)
        tags = {p['tag'] for p in prefabs.values()} | self._zone_tags
        for p_ in prefabs.values():
            for h in p_['on_collision'] + p_.get('on_separate', []):
                if h['with'] not in tags:
                    raise GameCompileError(
                        f'<qg:on-collision with="{h["with"]}">: no prefab or zone has that tag '
                        f'(tags: {", ".join(sorted(tags))})', None)
        self.scripts['prefabs.gd'] = prefabs_source(pscript)
        self._prefab_scenes_used = pscript.scenes_used
        self._overlays_used: List[tuple] = list(pscript.overlays_used)
        self._posts_used: List[Optional[int]] = list(pscript.posts_used)
        self._signs_in = pscript.signs_in
        scenes = {}
        self._scenes_used: List[tuple] = []
        self._exits_used: List[tuple] = []
        self._scene_exits: Dict[str, set] = {}
        self._scenes_used.extend(self._prefab_scenes_used)
        self._scene_goes: Dict[str, List[str]] = {}
        self._scene_spawns: Dict[str, Optional[int]] = {}
        for scene in g.scenes:
            scenes[scene.get('name')] = self._scene(scene, sheets, prefabs)
        overlays = {name: self._overlay(el, sheets, prefabs) for name, el in g.overlays.items()}
        for oname, line in self._overlays_used:
            if oname not in overlays:
                raise GameCompileError(f'<qg:open-overlay name="{oname}">: no qg:overlay of that name (declared: '
                                       f'{", ".join(sorted(overlays)) or "none"})', line)
        if self.multiplayer is not None and self._posts_used:
            raise GameCompileError('<qg:post> is not for a qg:multiplayer game: its answer would come to each peer '
                                   'at another tick', self._posts_used[0])
        if self.world is not None and self.world.accounts == 'site' and not self._signs_in:
            raise GameCompileError(f'<qg:connect world="{g.connect.get("world")}">: the world\'s players sign in '
                                   f'(accounts="site"): the game has a <qg:sign-in> to the site before a scene of '
                                   f'the world', g.connect.line)
        if self.multiplayer is not None and self.multiplayer.get('rollback'):
            _check_rollback(self.multiplayer.get('start') or g.scenes[0].get('name'), scenes,
                            self._scene_goes, self._scene_spawns, g.multiplayer.line)
        characters = {n['id'] for sc in scenes.values() for n in sc['nodes'] if n['kind'] == 'character'}
        tags = {p['tag'] for p in prefabs.values()}
        for who, tag, attr, line in self._part_targets:
            if who not in characters and who not in tags:
                raise GameCompileError(f'<qg:{tag} {attr}="{who}">: no character has that id, nor a prefab that tag '
                                       f'(characters: {", ".join(sorted(characters)) or "none"}; tags: '
                                       f'{", ".join(sorted(tags))})', line)
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
                **({'world': self.world_spec} if self.world_spec else {}),
                'sheets': sheets,
                'sounds': sounds,
                'buses': self.buses,
                'touch': self._touch(g.touch, None),
                'particles': particles,
                'items': self.items,
                'languages': languages,
                'prefabs': prefabs,
                'scenes': scenes,
                **({'overlays': overlays} if overlays else {}),
            },
            'scripts': self.scripts,
            'assets': self.assets,
        }

    def _connect(self, g: Game) -> None:
        from quantum.runtime.godot.world import read_world
        el = g.connect
        if g.multiplayer is not None:
            raise GameCompileError('<qg:connect>: a game is a world\'s client or a qg:multiplayer one, not both (the '
                                   'world is the server\'s; the lockstep has no server)', el.line)
        self.world = read_world(self._find(el.get('world'), el.line), el.line)
        for kind in sorted(self.world.kinds):
            prefab = g.prefabs.get(kind)
            if prefab is None:
                raise GameCompileError(f'<qg:connect world="{el.get("world")}">: the world has entities of kind '
                                       f'{kind!r}; the game draws each as the qg:prefab of its kind\'s name: declare '
                                       f'<qg:prefab name="{kind}">', el.line)
            if prefab.get('ai'):
                raise GameCompileError(f'<qg:prefab name="{kind}" ai="{prefab.get("ai")}">: an entity of the world '
                                       f'moves as the world says; its prefab has no ai=', prefab.line)
        self.world_spec = {'name': self.world.name, 'local': el.get('local'), 'server': el.get('server'),
                           'kinds': self.world.kinds, 'views': self.world.views, 'hero': self.world.hero_kind,
                           **({'predict': self.world.predict, 'walls': self.world.walls} if self.world.predict
                              else {})}

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

    def _tmx(self, src: str, line: Optional[int]):
        """A Tiled map, read once."""
        cache = self.__dict__.setdefault('_tmx_read', {})
        if src not in cache:
            cache[src] = read_tmx(self._find(src, line), line)
        return cache[src]

    @staticmethod
    def _tiled_kinds(sheet: dict, name: str, kinds: dict, line: Optional[int]) -> None:
        """A Tiled tileset's tile kinds, onto the qg:tileset's tiles: a ladder or water tile is passed through."""
        size = float(sheet['tile'][0])
        tiles = sheet.setdefault('tiles', {})
        for frame, kind in kinds.items():
            have = tiles.get(str(frame))
            if have is not None and have.get('kind') not in (None, kind):
                raise GameCompileError(f'tile {frame} of {name!r} is of kind {have["kind"]!r} in the .q and {kind!r} '
                                       f'in the Tiled map', line)
            if have is None:
                square = [[0.0, 0.0], [size, 0.0], [size, size], [0.0, size]]
                have = tiles[str(frame)] = {'shape': None if kind in ('ladder', 'water') else square, 'one_way': False}
            elif kind in ('ladder', 'water'):
                have['shape'] = None
            have['kind'] = kind

    def _animations_known(self, played: list) -> None:
        """qg:play-animation names an animation some character or prefab of the game has."""
        if not played:
            return
        if getattr(self, '_animation_names', None) is None:
            names, todo = set(), list(self.game.prefabs.values()) + list(self.game.scenes)
            while todo:
                el = todo.pop()
                for c in el.children:
                    if isinstance(c, Element):
                        if c.tag == 'animation':
                            names.add(c.get('name'))
                        todo.append(c)
            self._animation_names = names
        for name, line in played:
            if name and name not in self._animation_names:
                raise GameCompileError(f'<qg:play-animation name="{name}">: no qg:animation of that name in the game '
                                       f'(it has: {", ".join(sorted(self._animation_names)) or "none"})', line)

    def _prefab_parts(self, el: Element, name: str, script: SceneScript) -> list:
        """The parts of an enemy, a prefab ai="behavior" (its qg:behavior), checked; their when= go into P."""
        found = el.find_all('behavior')
        if el.get('ai') != 'behavior':
            if found:
                raise GameCompileError('<qg:behavior> in a prefab is for ai="behavior"', found[0].line)
            return []
        if len(found) != 1:
            raise GameCompileError('<qg:prefab ai="behavior"> holds one <qg:behavior> (its parts)',
                                   found[1].line if found else el.line)
        parts = []
        for i, p in enumerate(found[0].children):
            if not isinstance(p, Element):
                raise GameCompileError('<qg:behavior> holds parts (qg:seek, qg:wander...), not statements', p.line)
            if p.tag not in _ENEMY_PARTS + ('gravity',):
                raise GameCompileError(f'<qg:{p.tag}> is a part of a character controller="behavior"; an enemy\'s '
                                       f'parts are qg:gravity, {", ".join("qg:" + t for t in _ENEMY_PARTS)}',
                                       p.line)
            part = {'kind': p.tag}
            for attr in TAGS[p.tag].attrs:
                if attr != 'when':
                    part[attr.replace('-', '_')] = p.get(attr)
            for attr in ('sight', 'range'):
                if part.get(attr) is not None and part[attr] <= 0:
                    raise GameCompileError(f'<qg:{p.tag} {attr}=>: more than 0', p.line)
            for attr in ('speed', 'distance', 'min'):
                if part.get(attr) is not None and part[attr] < 0:
                    raise GameCompileError(f'<qg:{p.tag} {attr}=>: 0 or more', p.line)
            if p.tag == 'keep-distance' and part['max'] <= part['min']:
                raise GameCompileError('<qg:keep-distance>: max= more than min=', p.line)
            if p.tag == 'gravity' and (part['strength'] < 0 or part['max_fall'] <= 0):
                raise GameCompileError('<qg:gravity>: strength= 0 or more, max-fall= more than 0', p.line)
            if p.tag == 'leap':
                if part['height'] <= 0 or part['every'] < 1:
                    raise GameCompileError('<qg:leap>: height= more than 0, every= 1 or more', p.line)
                if part['sound'] and part['sound'] not in self.sounds:
                    raise GameCompileError(f'<qg:leap sound="{part["sound"]}">: no qg:sound of that name', p.line)
            if p.tag == 'shoot':
                if part['every'] < 1:
                    raise GameCompileError('<qg:shoot every=>: 1 or more ticks', p.line)
                script.prefabs_used.append((part['prefab'], p.line))
                if part['sound'] and part['sound'] not in self.sounds:
                    raise GameCompileError(f'<qg:shoot sound="{part["sound"]}">: no qg:sound of that name', p.line)
            for attr in ('target', 'from', 'at'):
                if part.get(attr):
                    self._part_targets.append((part[attr], p.tag, attr, p.line))
            part['when'] = None
            if p.get('when') is not None:
                part['when'] = f'_{_ident(name)}_when_{i}'
                expr = compile_expression(p.get('when'), script.scope().child(('me',)), p.line)
                script.handlers.append(f'func {part["when"]}(me) -> bool:\n\treturn true if {expr} else false\n')
            parts.append(part)
        if not parts:
            raise GameCompileError('<qg:behavior> is empty: give it parts (qg:seek, qg:wander...)', found[0].line)
        kinds = [p['kind'] for p in parts]
        if kinds.count('gravity') > 1 or kinds.count('leap') > 1:
            raise GameCompileError('a qg:behavior has one qg:gravity and one qg:leap at most', found[0].line)
        if 'gravity' in kinds:
            for p in parts:
                if p['kind'] == 'patrol' and p['heading'] in ('up', 'down'):
                    raise GameCompileError('<qg:patrol heading=>: an enemy with qg:gravity walks left and right',
                                           found[0].line)
        elif 'leap' in kinds:
            raise GameCompileError('<qg:leap> needs qg:gravity in the same qg:behavior (what brings it down)',
                                   found[0].line)
        return parts

    def _items(self, sheets: dict) -> dict:
        """The qg:items the players carry, checked."""
        items = {}
        for name, el in self.game.items.items():
            if el.get('sheet') is not None:
                self._sheet_exists(el.get('sheet'), sheets, el.line)
            if el.get('sound') is not None and el.get('sound') not in self.sounds:
                raise GameCompileError(f'<qg:item sound="{el.get("sound")}">: no qg:sound of that name', el.line)
            if el.get('particles') is not None and el.get('particles') not in self.particles:
                raise GameCompileError(f'<qg:item particles="{el.get("particles")}">: no qg:particles of that name',
                                       el.line)
            if el.get('max') < 0 or el.get('start') < 0 or (el.get('max') and el.get('start') > el.get('max')):
                raise GameCompileError('<qg:item>: max= and start= 0 or more, start= not over max=', el.line)
            items[name] = {'label': el.get('label') or name, 'sheet': el.get('sheet'), 'frame': el.get('frame'),
                           'max': el.get('max'), 'start': el.get('start'), 'sound': el.get('sound'),
                           'particles': el.get('particles')}
        for reserved in ('q_items', 'q_gone'):
            if items and reserved in self.game_state:
                raise GameCompileError(f'{reserved!r} is the runtime\'s name for what the players carry: '
                                       f'name the q:set otherwise', None)
        return items

    def _items_known(self, used: list) -> None:
        for item, line in used:
            if item is None:   # qg:reset-items
                if not self.items:
                    raise GameCompileError('<qg:reset-items>: the game declares no qg:item', line)
            elif item not in self.items:
                raise GameCompileError(f'no qg:item named {item!r} (declared: {", ".join(sorted(self.items)) or "none"})',
                                       line)

    def _prefab_items(self, el: Element, name: str, script: SceneScript) -> dict:
        """A prefab picked up as an item (gives=) or opened by one (opens-with=), checked."""
        out = {}
        if el.get('gives') is not None:
            if el.get('ai') or el.get('solid'):
                raise GameCompileError('gives= is for a prefab that is picked up: no ai=, not solid', el.line)
            if el.get('amount') < 1:
                raise GameCompileError('<qg:prefab amount=>: 1 or more', el.line)
            self._items_known([(el.get('gives'), el.line)])
            out.update(gives=el.get('gives'), amount=el.get('amount'))
        elif el.get('amount') != 1:
            raise GameCompileError('amount= is for gives=', el.line)
        locked = el.find_all('on-locked')
        if el.get('opens-with') is not None:
            if not el.get('solid') or el.get('ai'):
                raise GameCompileError('opens-with= is for a solid prefab without ai= (a door)', el.line)
            self._items_known([(el.get('opens-with'), el.line)])
            out.update(opens_with=el.get('opens-with'), keeps=el.get('keeps'))
            if len(locked) > 1:
                raise GameCompileError('a qg:prefab has one <qg:on-locked>', locked[1].line)
            if locked:
                out['on_locked'] = compile_handler(script, f'_{_ident(name)}_on_locked', locked[0].children,
                                                   locked[0].line)
        else:
            if el.get('keeps'):
                raise GameCompileError('keeps= is for opens-with=', el.line)
            if locked:
                raise GameCompileError('<qg:on-locked> is for a prefab with opens-with=', locked[0].line)
        return out

    def _behavior(self, el: Element) -> list:
        """The parts of a character controller="behavior" (its qg:behavior), checked."""
        found = el.find_all('behavior')
        if el.get('controller') != 'behavior':
            if found:
                raise GameCompileError('<qg:behavior> is for controller="behavior"', found[0].line)
            return []
        if len(found) != 1:
            raise GameCompileError('<qg:character controller="behavior"> holds one <qg:behavior> (its parts)',
                                   found[1].line if found else el.line)
        parts, seen = [], {}
        for p in found[0].children:
            if not isinstance(p, Element):
                raise GameCompileError('<qg:behavior> holds parts (qg:gravity, qg:walk...), not statements', p.line)
            if p.tag in _ENEMY_PARTS:
                raise GameCompileError(f'<qg:{p.tag}> is a part of an enemy (a qg:prefab ai="behavior"), not of a '
                                       f'character', p.line)
            if p.tag in seen:
                raise GameCompileError(f'two <qg:{p.tag}> in one qg:behavior', p.line)
            seen[p.tag] = p.line
            part = {'part': p.tag}
            for name in TAGS[p.tag].attrs:
                part[name.replace('-', '_')] = p.get(name)
            parts.append(part)
        if not parts:
            raise GameCompileError('<qg:behavior> is empty: give it parts (qg:gravity, qg:walk, qg:jump...)',
                                   found[0].line)
        by = {p['part']: p for p in parts}
        if 'keep-inside' in by and 'wrap' in by:
            raise GameCompileError('a qg:behavior has qg:keep-inside or qg:wrap, not both', seen['wrap'])
        if 'gravity' in by and (by['gravity']['strength'] < 0 or by['gravity']['max_fall'] <= 0):
            raise GameCompileError('<qg:gravity>: strength= 0 or more, max-fall= more than 0', seen['gravity'])
        if 'walk' in by and (by['walk']['speed'] < 0 or by['walk']['accel'] < 0):
            raise GameCompileError('<qg:walk>: speed= and accel= 0 or more', seen['walk'])
        if 'jump' in by:
            j, line = by['jump'], seen['jump']
            if 'gravity' not in by:
                raise GameCompileError('<qg:jump> needs <qg:gravity> in the same qg:behavior (what brings it down)',
                                       line)
            if j['action'] not in self.actions:
                raise GameCompileError(
                    f'<qg:jump action="{j["action"]}">: no such action — declare it with '
                    f'<qg:input action="{j["action"]}" keys="..." />', line)
            if j['sound'] and j['sound'] not in self.sounds:
                raise GameCompileError(f'<qg:jump sound="{j["sound"]}">: no qg:sound of that name', line)
            if j['height'] <= 0 or (j['speed'] is not None and j['speed'] <= 0):
                raise GameCompileError('<qg:jump>: height= and speed= more than 0', line)
            if j['coyote'] < 0 or j['air'] < 0 or j['buffer'] < 0:
                raise GameCompileError('<qg:jump>: coyote=, air= and buffer= 0 or more', line)
            if not 0 <= j['cut'] <= 1:
                raise GameCompileError('<qg:jump cut=>: between 0 and 1', line)
        if 'steer' in by:
            st, line = by['steer'], seen['steer']
            for other in ('walk', 'gravity', 'jump'):
                if other in by:
                    raise GameCompileError(f'<qg:steer> and <qg:{other}> in one qg:behavior: steer turns and pushes '
                                           f'the body itself, seen from above', line)
            if st['turn'] < 0 or st['thrust'] < 0 or st['drag'] < 0 or st['max'] <= 0:
                raise GameCompileError('<qg:steer>: turn=, thrust= and drag= 0 or more, max= more than 0', line)
        return parts

    def _touch(self, elements: list, scene: Optional[str]) -> List[dict]:
        """qg:touch-button and qg:touch-stick: on a touch screen, what presses the game's actions."""
        out = []
        for el in elements:
            if el.get('player') < 1:
                raise GameCompileError(f'<qg:{el.tag} player=>: 1 or more', el.line)
            if el.get('size') <= 0:
                raise GameCompileError(f'<qg:{el.tag} size=>: more than 0', el.line)
            spec = {'kind': 'stick' if el.tag == 'touch-stick' else 'button', 'x': el.get('x'), 'y': el.get('y'),
                    'size': el.get('size'), 'player': el.get('player'), 'show': el.get('show')}
            if el.tag == 'touch-button':
                if el.get('action') not in self.actions:
                    raise GameCompileError(f'<qg:touch-button action="{el.get("action")}">: no such action (the game '
                                           f'has {", ".join(sorted(self.actions))})', el.line)
                spec.update({'action': el.get('action'), 'label': el.get('label')})
            out.append(spec)
        return out

    def _language_asset(self, el: Element, code: str, sheets: dict, sounds: dict) -> None:
        """A qg:asset: a picture or a sound of the game as it is in a language, beside its own src."""
        name = el.get('name')
        target = sheets.get(name) or sounds.get(name)
        if target is None:
            known = ', '.join(sorted({**sheets, **sounds})) or 'none'
            raise GameCompileError(f'<qg:asset name="{name}">: no qg:spritesheet, qg:tileset or qg:sound of that '
                                   f'name (declared: {known})', el.line)
        srcs = target.setdefault('srcs', {})
        if code in srcs:
            raise GameCompileError(f'<qg:asset name="{name}">: twice in lang="{code}"', el.line)
        srcs[code] = self._asset(el.get('src'), el.line)

    @staticmethod
    def _box(name: str, sheets: dict, where: str, line: Optional[int]) -> None:
        """box=: a qg:spritesheet with slice=, the frame a box is drawn with."""
        _Compiler._sheet_exists(name, sheets, line)
        if 'slice' not in sheets[name]:
            raise GameCompileError(f'{where} box="{name}">: a qg:spritesheet with slice= (how wide its edges are, '
                                   f'which do not stretch)', line)

    @staticmethod
    def _place(el: Element, what: str) -> dict:
        """x= and y=: a HUD's or a menu's top-left corner, in pixels, in place of position=."""
        x, y = el.get('x'), el.get('y')
        if (x is None) != (y is None):
            raise GameCompileError(f'<qg:{what}>: x= and y= go together (its top-left corner)', el.line)
        return {} if x is None else {'xy': [x, y]}

    def _table(self, el: Element, script: SceneScript, n: int) -> dict:
        """A qg:table of a HUD: a method for its rows, and one for each column's value (and colour) of a row."""
        name = f'_q_table_{n}'
        row = el.get('as')
        scope = script.scope().child([row])
        script.functions.append(f'func {name}():\n\treturn Q.rows('
                                f'{compile_expression(el.get("source"), script.scope(), el.line)})\n')
        columns = []
        for k, c in enumerate(el.children):
            if not (isinstance(c, Element) and c.tag == 'column'):
                raise GameCompileError('<qg:table> holds qg:column', getattr(c, 'line', el.line))
            if c.get('width') < 1:
                raise GameCompileError('<qg:column width=>: 1 character or more', c.line)
            column = {'label': c.get('label'), 'width': c.get('width'), 'align': c.get('align'),
                      'value': f'{name}_{k}'}
            script.functions.append(f'func {name}_{k}({row}):\n\treturn Q.to_str('
                                    f'{compile_expression(c.get("value"), scope, c.line)})\n')
            color = c.get('color')
            if color:
                if is_expression(str(color)):
                    column['color_method'] = f'{name}_{k}_color'
                    script.functions.append(f'func {name}_{k}_color({row}):\n\treturn Q.to_str('
                                            f'{compile_expression(color, scope, c.line)})\n')
                else:
                    column['color'] = _color(color, '<qg:column color=', c.line)
            columns.append(column)
        if not columns:
            raise GameCompileError('<qg:table> needs at least one qg:column', el.line)
        if el.get('rows') < 0:
            raise GameCompileError('<qg:table rows=>: 0 (all of them) or more', el.line)
        return {'kind': 'table', 'source': name, 'columns': columns,
                **({'rows': el.get('rows')} if el.get('rows') else {})}

    @staticmethod
    def _sheet_exists(name: str, sheets: dict, line: Optional[int]) -> None:
        if name not in sheets:
            known = ', '.join(sorted(sheets)) or 'none'
            raise GameCompileError(f'no qg:spritesheet or qg:tileset named {name!r} (declared: {known})', line)

    def _overlay(self, el: Element, sheets: dict, prefabs: dict) -> dict:
        """A qg:overlay: a screen of its own (its HUD, menus and handlers, compiled as a scene's are), built over
        the scene shown when it opens."""
        name = el.get('name')
        if self.multiplayer is not None:
            raise GameCompileError(f'<qg:overlay name="{name}">: not in a qg:multiplayer game (the scene under it '
                                   f'would stand still on one machine only)', el.line)
        action = el.get('action')
        if action is not None and action not in self.actions:
            raise GameCompileError(f'<qg:overlay action="{action}">: no such action (the game has '
                                   f'{", ".join(sorted(self.actions))}; a qg:input declares one)', el.line)
        if not 0.0 <= el.get('shade') <= 1.0:
            raise GameCompileError(f'<qg:overlay shade="{el.get("shade")}">: 0 (the scene as it is) to 1 (hidden)',
                                   el.line)
        first = self.game.scenes[0]
        screen = Element('scene', {'name': name, 'width': first.get('width'), 'height': first.get('height'),
                                   'background': el.get('background'), 'seed': '0', 'save': False, 'y-sort': False,
                                   'ambient': None}, el.line, children=el.children, gd=el.gd)
        spec = self._scene(screen, sheets, prefabs)
        spec['overlay'] = {'shade': el.get('shade'), **({'action': action} if action else {}),
                           **({} if el.get('freeze') else {'freeze': False})}
        return spec

    def _scene(self, scene: Element, sheets: dict, prefabs: dict) -> dict:
        name = scene.get('name')
        scene.children = _expand_lobbies(scene.children, self.multiplayer, bool(self.languages))
        script = SceneScript(name, game_state=self.game_state, world=self.world,
                             world_scene=bool(scene.get('world')))
        if scene.get('world') and self.world is None:
            raise GameCompileError(f'<qg:scene name="{name}" world="true">: the game is no world\'s client '
                                   f'(qg:connect)', scene.line)
        script.buses = set(self.buses)
        self._states_checked: list = []
        # the characters, by id: names in the scene's expressions, targets of its actions
        script.node_ids = ([c.get('id') for c in scene.find_all('character')]
                           + [i.get('name') for i in scene.find_all('instance') if i.get('name')]
                           + [c.get('id') for c in scene.find_all('cursor') if c.get('id')])
        script.node_fields = {c.get('id'): CONTROLLER_FIELDS.get(c.get('controller'), THING_FIELDS)
                              for c in scene.find_all('character')}
        script.node_fields.update({c.get('id'): CURSOR_FIELDS for c in scene.find_all('cursor') if c.get('id')})
        script.actions = self.actions
        script.tiled_props = {}
        for tm in scene.find_all('tilemap'):
            if tm.get('src'):
                script.tiled_props.update(self._tmx(tm.get('src'), tm.line).properties)
        # 1. state and functions first: handlers refer to them (and a state's first value may call a function)
        for node in scene.children:
            if isinstance(node, Statement) and node.kind == 'function':
                if any(f.attrs['name'] == node.attrs['name'] for f in self.game.functions):
                    raise GameCompileError(f'{node.attrs["name"]!r} is a q:function of the game already (in '
                                           f'<q:application>); a scene\'s needs another name', node.line)
                script.function_names.append(node.attrs['name'])
        script.function_names.extend(f.attrs['name'] for f in self.game.functions)
        for node in scene.children:
            if isinstance(node, Statement) and node.kind == 'set':
                if node.attrs['name'] in self.game_state and 'type' not in node.attrs and 'saved' not in node.attrs:
                    script.enter.append(node)   # the game's state, set as the scene is entered
                else:
                    declare_state(script, node)
        compile_game_functions(script, self.game.functions)
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
        music: Optional[dict] = None
        map_nodes: Dict[str, dict] = {}
        map_paths: List[dict] = []
        on_input: Dict[str, str] = {}
        on_event: Dict[str, List[str]] = {}       # a world's event -> its handlers (world="true")
        on_refused: List[dict] = []
        sequences: List[dict] = []
        on_release: Dict[str, str] = {}
        on_screen: List[dict] = []
        exits: Dict[str, dict] = {}
        zones: set = set()
        on_select: Dict[str, str] = {}
        cursors: set = set()
        menus = 0
        texts = 0
        paths: Dict[str, list] = {}
        conditions = 0
        on_death: Dict[str, str] = {}
        whens: List[list] = []
        touch: list = []
        tiled: dict = {}
        pointers: List[tuple] = []   # (player, line) of the characters controller="pointer": they need a cursor
        cameras_here = any(isinstance(n, Element) and n.tag == 'camera' for n in scene.children)
        dialogues: Dict[str, dict] = {}
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
            elif el.tag == 'parallax':
                self._sheet_exists(el.get('sheet'), sheets, el.line)
                if not 0 <= el.get('scroll') <= 1:
                    raise GameCompileError('<qg:parallax scroll=>: between 0 (still) and 1 (with the level)', el.line)
                nodes.append({'kind': 'parallax', 'sheet': el.get('sheet'), 'frame': el.get('frame'),
                              'y': el.get('y'), 'scroll': el.get('scroll'), 'repeat': el.get('repeat')})
                self._node_elements.append(el)
            elif el.tag == 'sprite':
                self._sheet_exists(el.get('sheet'), sheets, el.line)
                frame = str(el.get('frame')).strip()
                nodes.append({'kind': 'sprite', 'sheet': el.get('sheet'), 'frame': int(frame) if frame.isdigit() else 0,
                              'x': el.get('x'), 'y': el.get('y')})
                if not frame.isdigit():
                    # frame="{...}": the picture shows what the expression says, tick by tick
                    nodes[-1]['frame_method'] = f'_q_sprite_{len(nodes) - 1}_frame'
                    script.functions.append(f'func {nodes[-1]["frame_method"]}():\n'
                                            f'\treturn int({compile_expression(frame, script.scope(), el.line)})\n')
                self._node_elements.append(el)
            elif el.tag == 'emitter':
                if el.get('particles') not in self.particles:
                    raise GameCompileError(f'<qg:emitter particles="{el.get("particles")}">: no qg:particles of that name',
                                           el.line)
                nodes.append({'kind': 'emitter', 'particles': el.get('particles'), 'x': el.get('x'), 'y': el.get('y'),
                              'width': el.get('width')})
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
            elif el.tag == 'light':
                if el.get('x') is None or el.get('y') is None:
                    raise GameCompileError('<qg:light> in a scene needs x= and y= (where it is)', el.line)
                if el.get('dx') or el.get('dy'):
                    raise GameCompileError('<qg:light> in a scene takes x= and y=; dx= and dy= are for one on a '
                                           'character or a prefab', el.line)
                nodes.append({'kind': 'light', 'x': el.get('x'), 'y': el.get('y'), **_light(el)})
                self._node_elements.append(el)
            elif el.tag == 'label':
                # text at a place of the scene, read every tick
                if el.get('x') is None or el.get('y') is None:
                    raise GameCompileError('<qg:label> in a scene needs x= and y= (where its middle is)', el.line)
                n = sum(1 for nd in nodes if nd['kind'] == 'label') + 1
                method = f'_q_label_{n}'
                script.functions.append(f'func {method}() -> String:\n\treturn Q.to_str('
                                        f'{compile_expression(el.get("value"), script.scope(), el.line)})\n')
                condition = None
                if el.get('if') is not None:
                    conditions += 1
                    condition = f'_q_if_{conditions}'
                    expr = compile_expression(el.get('if'), script.scope(), el.line)
                    script.functions.append(f'func {condition}() -> bool:\n\treturn {expr}\n')
                nodes.append({'kind': 'label', 'method': method, 'x': el.get('x'), 'y': el.get('y'),
                              'size': el.get('size'), 'color': el.get('color'), 'if': condition})
                self._node_elements.append(el)
            elif el.tag == 'when':
                # the condition, a method the scene's clock reads before every tick; the handler, run as it turns true
                n = len(whens) + 1
                cond = compile_expression(el.get('condition'), script.scope(), el.line)
                script.functions.append(f'func _when_{n}() -> bool:\n\treturn bool({cond})')
                whens.append([f'_when_{n}', compile_handler(script, f'_on_when_{n}', el.children, el.line, params=())])
            elif el.tag == 'timer':
                if (el.get('after') is None) == (el.get('every') is None):
                    raise GameCompileError('<qg:timer> takes after= or every=, one of them', el.line)
                timers = sum(1 for n in nodes if n['kind'] == 'timer')
                handler = compile_handler(script, f'_on_timer_{timers}', el.children, el.line)
                nodes.append({'kind': 'timer', 'after': el.get('after'), 'every': el.get('every'),
                              'from': el.get('from'), 'count': el.get('count'), 'handler': handler})
                self._node_elements.append(el)
            elif el.tag == 'on-input' and el.get('sequence') is not None:
                # a special move: presses in order, in time (quantum_scene.gd, Q.sequence)
                steps = [s.strip() for s in str(el.get('sequence')).split(',') if s.strip()]
                if el.get('action') is not None or el.get('on') != 'press':
                    raise GameCompileError('<qg:on-input sequence=>: the sequence names its actions; no action= '
                                           'or on=', el.line)
                if len(steps) < 2:
                    raise GameCompileError('<qg:on-input sequence=>: two actions or more, separated by commas',
                                           el.line)
                for step in steps:
                    if step not in self.actions and step not in ('forward', 'back'):
                        raise GameCompileError(f'<qg:on-input sequence=>: no such action {step!r} (forward and '
                                               f'back are the way the character faces)', el.line)
                if el.get('within') < len(steps) - 1 or not 1 <= el.get('player') <= 4:
                    raise GameCompileError('<qg:on-input sequence=>: within= at least a tick a step; player= 1 to 4',
                                           el.line)
                sequences.append({'steps': steps, 'within': el.get('within'), 'player': el.get('player'),
                                  'handler': compile_handler(script, f'_on_sequence_{len(sequences)}', el.children,
                                                             el.line)})
            elif el.tag == 'on-input':
                action = el.get('action')
                if action is None:
                    raise GameCompileError('<qg:on-input> takes action= (or sequence=)', el.line)
                if action not in self.actions:
                    raise GameCompileError(
                        f'<qg:on-input action="{action}">: no such action (the defaults are '
                        f'{", ".join(DEFAULT_INPUTS)}; a qg:input declares another)', el.line)
                pressing = el.get('on') == 'press'
                table = on_input if pressing else on_release
                if action in table:
                    raise GameCompileError(f'two <qg:on-input action="{action}"'
                                           f'{"" if pressing else " on=" + chr(34) + "release" + chr(34)}>', el.line)
                table[action] = compile_handler(script, f'_on_{"input" if pressing else "release"}_{_ident(action)}',
                                                el.children, el.line)
            elif el.tag in ('on-screen-exit', 'on-screen-enter'):
                if not el.get('of'):
                    raise GameCompileError(f'<qg:{el.tag}> in a scene needs of= (a tag)', el.line)
                on_screen.append({'of': el.get('of'), 'on': el.tag[len('on-screen-'):], 'side': el.get('side'),
                                  'handler': compile_handler(script, f'_on_screen_{len(on_screen)}', el.children,
                                                             el.line)})
            elif el.tag == 'on-select':
                action = el.get('action')
                if action not in self.actions:
                    raise GameCompileError(f'<qg:on-select action="{action}">: no such action (the defaults are '
                                           f'{", ".join(DEFAULT_INPUTS)}; a qg:input declares another)', el.line)
                # "2": player 2's select; "0:sell": anyone's sell (a right click on a thing)
                key = str(el.get('player') or 0) + ('' if action == 'select' else ':' + action)
                if key in on_select:
                    raise GameCompileError('two <qg:on-select> for the same player and action', el.line)
                on_select[key] = compile_handler(script, f'_on_select_{_ident(key.replace(":", "_"))}', el.children, el.line,
                                                 params=('cursor', 'other'))
            elif el.tag == 'cursor':
                if el.get('sheet'):
                    self._sheet_exists(el.get('sheet'), sheets, el.line)
                if el.get('player') in cursors:
                    raise GameCompileError(f'two <qg:cursor player="{el.get("player")}">', el.line)
                cursors.add(el.get('player'))
                if el.get('id') is not None:
                    if el.get('id') in ids:
                        raise GameCompileError(f'two nodes with id {el.get("id")!r}', el.line)
                    ids[el.get('id')] = el.line
                if el.get('cells') and el.get('grid') is not None:
                    raise GameCompileError('<qg:cursor> snaps to grid= or to the cells of the tilemap (cells="true"), '
                                           'one of them', el.line)
                nodes.append({'kind': 'cursor', 'player': el.get('player'), 'step': el.get('step'),
                              'grid': el.get('grid'), 'sheet': el.get('sheet'), 'frame': el.get('frame'),
                              **({'cells': True} if el.get('cells') else {}),
                              **({'id': el.get('id')} if el.get('id') else {})})
                self._node_elements.append(el)
            elif el.tag == 'path':
                pname = el.get('name')
                if pname in paths:
                    raise GameCompileError(f'two paths named {pname!r}', el.line)
                paths[pname] = _points(el.get('points'), el.line)
                nodes.append({'kind': 'path', 'name': pname, 'points': paths[pname]})
                self._node_elements.append(el)
            elif el.tag == 'tilemap':
                if tilemap is not None and el.get('tileset') != tilemap['tileset']:
                    raise GameCompileError(
                        f'<qg:tilemap tileset="{el.get("tileset")}">: the layers of a scene share one tileset, '
                        f'{tilemap["tileset"]!r}', el.line)
                self._sheet_exists(el.get('tileset'), sheets, el.line)
                if el.get('src') and sheets[el.get('tileset')].get('shape'):
                    raise GameCompileError(f'<qg:tilemap src="{el.get("src")}">: a Tiled map of hexes or diamonds is '
                                           f'not read yet; give its rows in the .q', el.line)
                if el.get('src'):
                    tmx = self._tmx(el.get('src'), el.line)
                    tile = sheets[el.get('tileset')]['tile'][0]
                    if (tmx.tile_width, tmx.tile_height) != (tile, tile):
                        raise GameCompileError(
                            f'{el.get("src")}: tiles are {tmx.tile_width}x{tmx.tile_height}, the tileset '
                            f'{el.get("tileset")!r} has {tile}x{tile}', el.line)
                    # each tileset of the map is a qg:tileset of the game with the same image (a map of
                    # one tileset draws with the scene's, whatever its image)
                    used = []
                    for ts in tmx.tilesets:
                        same = [n for n, sh in sheets.items() if sh['kind'] == 'tileset' and Path(sh['src']).name == ts.image]
                        if len(tmx.tilesets) == 1:
                            same = [el.get('tileset')]
                        if not same:
                            raise GameCompileError(f'{el.get("src")}: its tileset {ts.image!r} is no qg:tileset of the '
                                                   f'game (a qg:tileset with src= that image)', el.line)
                        tname = el.get('tileset') if el.get('tileset') in same else same[0]
                        if sheets[tname]['tile'][0] != tile:
                            raise GameCompileError(f'{el.get("src")}: the tilesets of a map have one tile size; '
                                                   f'{tname!r} has {sheets[tname]["tile"][0]}', el.line)
                        self._tiled_kinds(sheets[tname], tname, ts.kinds, el.line)
                        used.append(tname)
                    layers = [{'name': ly.name, 'rows': ly.rows, 'collision': ly.collision or el.get('collision'),
                               **({'tileset': used[ly.tileset]} if used[ly.tileset] != el.get('tileset') else {})}
                              for ly in tmx.layers]
                    for obj in tmx.objects:
                        if obj.prefab not in prefabs:
                            raise GameCompileError(
                                f'{el.get("src")}: object {obj.name or obj.prefab!r} has class {obj.prefab!r}, '
                                f'no qg:prefab of that name (declared: {", ".join(sorted(prefabs)) or "none"})',
                                el.line)
                        if obj.state is not None and obj.state not in (prefabs[obj.prefab].get('states') or {}):
                            raise GameCompileError(f'{el.get("src")}: object {obj.name or obj.prefab!r} starts in '
                                                   f'state {obj.state!r}, which {obj.prefab!r} has not', el.line)
                        nodes.append({'kind': 'instance', 'prefab': obj.prefab, 'x': obj.x, 'y': obj.y,
                                      'name': obj.name or None, 'if': None,
                                      **({'state': obj.state} if obj.state else {})})
                        self._node_elements.append(None)
                    for z in tmx.zones:
                        if z.name in zones:
                            raise GameCompileError(f'{el.get("src")}: two zones named {z.name!r}', el.line)
                        zones.add(z.name)
                        self._zone_tags.add(z.tag)
                        nodes.append({'kind': 'zone', 'name': z.name, 'tag': z.tag, 'x': z.x, 'y': z.y,
                                      'width': z.width, 'height': z.height})
                        self._node_elements.append(None)
                    for x in tmx.exits:
                        if x.name in exits:
                            raise GameCompileError(f'{el.get("src")}: two exits named {x.name!r}', el.line)
                        self._scenes_used.append((x.to, el.line))
                        self._exits_used.append((name, x.to, x.at, el.line))
                        exits[x.name] = {'kind': 'exit', 'name': x.name, 'x': x.x, 'y': x.y, 'width': x.width,
                                         'height': x.height, 'to': x.to, 'at': x.at}
                        nodes.append(exits[x.name])
                        self._node_elements.append(None)
                    for pth in tmx.paths:
                        if pth.name in paths:
                            raise GameCompileError(f'{el.get("src")}: two paths named {pth.name!r}', el.line)
                        paths[pth.name] = pth.points
                        nodes.append({'kind': 'path', 'name': pth.name, 'points': pth.points})
                        self._node_elements.append(None)
                    tiled = dict(tmx.properties)
                else:
                    layers = [{'name': 'tiles', 'rows': _csv_rows(el), 'collision': el.get('collision')}]
                if tilemap is not None:
                    # another layer of the same map, drawn over the ones before
                    for ly in layers:
                        ly['name'] = f'{ly["name"]}-{len(tilemap["layers"])}'
                    tilemap['layers'].extend(layers)
                    continue
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
                moves = []
                for m in el.find_all('move'):
                    if el.get('controller') != 'fighter':
                        raise GameCompileError('<qg:move> is for controller="fighter"', m.line)
                    if m.get('action') not in self.actions:
                        raise GameCompileError(
                            f'<qg:move action="{m.get("action")}">: no such action (a qg:input declares it)', m.line)
                    try:
                        frames = [int(f.strip()) for f in str(m.get('frames')).split(',') if f.strip()]
                        at = [float(v) for v in str(m.get('at')).split(',')]
                        if len(at) != 2:
                            raise ValueError
                    except ValueError:
                        raise GameCompileError('<qg:move>: frames= are frame numbers, at= is dx,dy', m.line)
                    if not frames or not 0 <= m.get('active') < len(frames):
                        raise GameCompileError(f'<qg:move active="{m.get("active")}">: a frame index of frames=', m.line)
                    if any(mv['name'] == m.get('name') for mv in moves):
                        raise GameCompileError(f'two moves named {m.get("name")!r}', m.line)
                    moves.append({'name': m.get('name'), 'action': m.get('action'), 'frames': frames,
                                  'fps': m.get('fps'), 'active': m.get('active'), 'reach': list(m.get('reach')),
                                  'at': at, 'damage': m.get('damage'), 'stun': m.get('stun'), 'push': m.get('push')})
                on_ko = None
                kos = el.find_all('on-ko')
                if kos and el.get('controller') != 'fighter':
                    raise GameCompileError('<qg:on-ko> is for controller="fighter"', kos[0].line)
                if len(kos) > 1:
                    raise GameCompileError('a fighter has one <qg:on-ko>', kos[1].line)
                if kos:
                    on_ko = compile_handler(script, f'_on_{_ident(cid)}_ko', kos[0].children, kos[0].line)
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
                controller = el.get('controller')
                if el.get('fire-action') is not None:
                    if controller not in ('ship', 'platformer'):
                        raise GameCompileError('fire-action= is for controller="ship" or "platformer"', el.line)
                    if el.get('fire-action') not in self.actions:
                        raise GameCompileError(
                            f'fire-action="{el.get("fire-action")}": no such action — declare it with '
                            f'<qg:input action="{el.get("fire-action")}" keys="..." />', el.line)
                    if not el.get('fire-prefab'):
                        raise GameCompileError('fire-action= needs fire-prefab= (what it shoots)', el.line)
                    if controller == 'platformer' and prefabs[el.get('fire-prefab')]['ai'] != 'fly':
                        raise GameCompileError(
                            f'fire-prefab="{el.get("fire-prefab")}": a platformer shoots a prefab with ai="fly"', el.line)
                for attr, default in (('jump-speed', None), ('accel', 0.0), ('air-jumps', 0),
                                      ('air-jump-boost', 1.0), ('jump-cut', 0.0), ('buffer-frames', 0)):
                    if el.get(attr) != default and controller != 'platformer':
                        raise GameCompileError(f'{attr}= is for controller="platformer"', el.line)
                if el.get('jump-speed') is not None and el.get('jump-speed') <= 0:
                    raise GameCompileError('jump-speed=: more than 0 (pixels per second, upwards)', el.line)
                if el.get('air-jumps') < 0 or el.get('accel') < 0 or el.get('buffer-frames') < 0:
                    raise GameCompileError('air-jumps=, accel= and buffer-frames=: 0 or more', el.line)
                if not 0 <= el.get('jump-cut') <= 1:
                    raise GameCompileError('jump-cut=: between 0 and 1', el.line)
                if el.get('scale') <= 0:
                    raise GameCompileError('<qg:character scale=>: more than 0', el.line)
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
                for attr, default in (('step-frames', 15), ('diagonal', False)):
                    if el.get(attr) != default and controller not in ('grid', 'pointer'):
                        raise GameCompileError(f'{attr}= is for controller="grid" or "pointer"', el.line)
                if controller == 'pointer':
                    pointers.append((player, el.line))
                if el.get('step-frames') < 1:
                    raise GameCompileError('step-frames=: 1 or more', el.line)
                if el.get('bounds') is not None and el.get('controller') not in ('ship', 'topdown'):
                    raise GameCompileError('bounds= is for controller="ship" or "topdown"', el.line)
                behavior = self._behavior(el)
                for h in el.find_all('on-tile'):
                    if controller not in ('platformer', 'topdown', 'behavior'):
                        raise GameCompileError('<qg:on-tile> is for controller="platformer", "topdown" or '
                                               '"behavior"', h.line)
                    if h.get('cooldown') < 0:
                        raise GameCompileError('<qg:on-tile cooldown=>: 0 or more', h.line)
                condition = None
                if el.get('if') is not None:
                    if controller == 'map':
                        raise GameCompileError('if= is not for controller="map"', el.line)
                    conditions += 1
                    condition = f'_q_if_{conditions}'
                    expr = compile_expression(el.get('if'), script.scope(), el.line)
                    script.functions.append(f'func {condition}() -> bool:\n\treturn {expr}\n')
                nodes.append({
                    'kind': 'character', 'id': cid, 'controller': el.get('controller'),
                    'player': player, 'axis': el.get('axis'),
                    'at_method': at_method, 'speed': el.get('speed'),
                    'sheet': el.get('sheet'), 'frame': el.get('frame'),
                    'x': el.get('x'), 'y': el.get('y'), 'hitbox': list(el.get('hitbox')),
                    'run_speed': el.get('run-speed'), 'jump_height': el.get('jump-height'),
                    'variable_jump': el.get('variable-jump'), 'coyote_frames': el.get('coyote-frames'),
                    'gravity': el.get('gravity'), 'max_fall': el.get('max-fall'),
                    'jump_sound': el.get('jump-sound'), 'jump_speed': el.get('jump-speed'),
                    'accel': el.get('accel'), 'air_jumps': el.get('air-jumps'),
                    'air_jump_boost': el.get('air-jump-boost'), 'jump_cut': el.get('jump-cut'),
                    'scale': el.get('scale'),
                    'bounds': el.get('bounds'), 'fire_action': el.get('fire-action'),
                    'fire_prefab': el.get('fire-prefab'), 'fire_every': el.get('fire-every'),
                    'fire_sound': el.get('fire-sound'),
                    'attack_action': el.get('attack-action'), 'attack_reach': el.get('attack-reach'),
                    'attack_frames': el.get('attack-frames'), 'attack_sound': el.get('attack-sound'),
                    'animations': _animations(el),
                    'states': states, 'initial_state': initial_state,
                    'on_collision': handlers, 'on_hit': hits, 'on_fall': on_fall,
                    'health': el.get('health'), 'facing': el.get('facing'), 'moves': moves, 'on_ko': on_ko,
                    'step_frames': el.get('step-frames'), 'diagonal': el.get('diagonal'),
                    'behavior': behavior, 'if': condition,
                    'on_tile': [{'kind': h.get('kind'), 'cooldown': h.get('cooldown'),
                                 'handler': compile_handler(script, f'_on_{_ident(cid)}_tile_{i}', h.children,
                                                            h.line)}
                                for i, h in enumerate(el.find_all('on-tile'))],
                    'on_animation_end': _animation_ends(el, script, f'_on_{_ident(cid)}'),
                    **_contact_handlers(el, script, f'_on_{_ident(cid)}'),
                    **_looks(el, script, f'_q_{_ident(cid)}', self.particles),
                    **({'buffer_frames': el.get('buffer-frames')} if el.get('buffer-frames') else {}),
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
                follow = [f.strip() for f in str(el.get('follow')).split(',') if f.strip()]
                if not follow:
                    raise GameCompileError('<qg:camera follow=>: a character id, or several', el.line)
                if el.get('zoom') <= 0 or el.get('zoom-min') <= 0 or el.get('lead') < 0 or el.get('smooth') < 0:
                    raise GameCompileError('<qg:camera>: zoom= and zoom-min= more than 0; lead= and smooth= 0 or more',
                                           el.line)
                if el.get('fit') and len(follow) < 2:
                    raise GameCompileError('<qg:camera fit="true">: for a camera that follows several', el.line)
                players = [c.get('player') for c in scene.find_all('camera')]
                if any(p is not None for p in players) and (None in players or len(set(players)) < len(players)):
                    raise GameCompileError('<qg:camera>: one camera for everyone, or one a player (player=, each '
                                           'player once)', el.line)
                if el.get('player') is not None and not 1 <= el.get('player') <= 4:
                    raise GameCompileError('<qg:camera player=>: 1 to 4', el.line)
                nodes.append({'kind': 'camera', 'follow': follow, 'bounds': el.get('bounds'), 'zoom': el.get('zoom'),
                              'dead_zone': list(el.get('dead-zone')) if el.get('dead-zone') else None,
                              'lead': el.get('lead'), 'smooth': el.get('smooth'), 'fit': el.get('fit'),
                              'zoom_min': el.get('zoom-min'),
                              **({'player': el.get('player')} if el.get('player') is not None else {})})
                self._node_elements.append(el)
            elif el.tag == 'menu':
                menus += 1
                items = []
                rows = None   # source=: the method that reads the rows, and the button shown for each
                if (el.get('source') is None) != (el.get('as') is None):
                    raise GameCompileError('<qg:menu>: source= and as= go together (the rows, and the name of one)',
                                           el.line)
                if el.get('source') is not None:
                    buttons = [c for c in el.children if isinstance(c, Element)]
                    if len(buttons) != 1 or buttons[0].tag != 'button':
                        raise GameCompileError('<qg:menu source=> holds one qg:button, shown once for each row',
                                               el.line)
                    rows = f'_q_menu_{menus}_rows'
                    script.functions.append(f'func {rows}():\n\treturn Q.rows('
                                            f'{compile_expression(el.get("source"), script.scope(), el.line)})\n')
                    c, row = buttons[0], el.get('as')
                    item = {'kind': 'button', 'handler': compile_handler(script, f'_on_menu_{menus}_button_0', c.children,
                                                                         c.line, params=(row,))}
                    label = str(c.get('label'))
                    lscope = script.scope().child([row])
                    item['label_method'] = f'_q_menu_{menus}_label_0'
                    script.functions.append(
                        f'func {item["label_method"]}({row}):\n\treturn Q.to_str('
                        f'{compile_expression(label, lscope, c.line) if is_expression(label) else json.dumps(label)})\n')
                    if c.get('if') is not None:
                        item['if_method'] = f'_q_menu_{menus}_if_0'
                        script.functions.append(
                            f'func {item["if_method"]}({row}):\n\treturn {compile_expression(c.get("if"), lscope, c.line)}\n')
                    gdprops.attach(item, 'Button', c.gd, '<qg:button>', c.line)
                    items.append(item)
                for c in el.children if rows is None else []:
                    if isinstance(c, Element) and c.tag == 'button':
                        n = len(items)
                        item = {'kind': 'button',
                                'handler': compile_handler(script, f'_on_menu_{menus}_button_{n}', c.children, c.line)}
                        label = str(c.get('label'))
                        if is_expression(label):
                            item['label_method'] = f'_q_menu_{menus}_label_{n}'
                            script.functions.append(
                                f'func {item["label_method"]}():\n\treturn Q.to_str({compile_expression(label, script.scope(), c.line)})\n')
                        else:
                            item['label'] = label
                        if c.get('if') is not None:
                            item['if_method'] = f'_q_menu_{menus}_if_{n}'
                            script.functions.append(
                                f'func {item["if_method"]}():\n\treturn {compile_expression(c.get("if"), script.scope(), c.line)}\n')
                        gdprops.attach(item, 'Button', c.gd, '<qg:button>', c.line)
                        items.append(item)
                    elif isinstance(c, Element) and c.tag == 'field':
                        bind = c.get('bind')
                        var = script.state.get(bind) or self.game_state.get(bind)
                        if var is None:
                            raise GameCompileError(f'<qg:field bind="{bind}">: no q:set of that name in the scene or the game', c.line)
                        if var.typed and var.type != 'string':
                            raise GameCompileError(f'<qg:field bind="{bind}">: a field holds text; {bind!r} is a {var.type}', c.line)
                        item = {'kind': 'field', 'bind': bind, 'label': c.get('label'), 'max_length': c.get('max-length'),
                                'game': bind not in script.state}
                        body = [b for b in c.children if isinstance(b, (Element, Statement))]
                        if c.get('shared'):
                            # the field a text was sent from, on every machine: the scene, the menu, its place
                            item.update({'shared': True, 'key': f'{scene.get("name")}:{menus}:{len(items)}'})
                            if body:
                                item['handler'] = compile_handler(script, f'_on_menu_{menus}_field_{len(items)}',
                                                                  c.children, c.line, params=('sender', 'text'))
                        elif body:
                            raise GameCompileError(f'<qg:field bind="{bind}">: only a shared field (shared="true") '
                                                   'runs what it holds, when a text is sent', c.line)
                        items.append(item)
                    elif isinstance(c, Element) and c.tag == 'slider':
                        if (c.get('bus') is None) == (c.get('bind') is None):
                            raise GameCompileError('<qg:slider> takes bus= or bind=, one of them', c.line)
                        if c.get('min') >= c.get('max') or c.get('step') <= 0:
                            raise GameCompileError('<qg:slider>: min= below max=, and a step= more than 0', c.line)
                        item = {'kind': 'slider', 'label': c.get('label'), 'min': c.get('min'), 'max': c.get('max'),
                                'step': c.get('step')}
                        if c.get('bus') is not None:
                            if c.get('bus') not in self.buses:
                                raise GameCompileError(f'<qg:slider bus="{c.get("bus")}">: no qg:sound is heard on that '
                                                       f'bus (buses: {", ".join(self.buses) or "none: give a qg:sound bus="})',
                                                       c.line)
                            item['bus'] = c.get('bus')
                        else:
                            bind = c.get('bind')
                            var = script.state.get(bind) or self.game_state.get(bind)
                            if var is None:
                                raise GameCompileError(f'<qg:slider bind="{bind}">: no q:set of that name in the scene or '
                                                       f'the game', c.line)
                            if var.typed and var.type != 'number':
                                raise GameCompileError(f'<qg:slider bind="{bind}">: a slider holds a number; {bind!r} is '
                                                       f'a {var.type}', c.line)
                            item.update({'bind': bind, 'game': bind not in script.state})
                        items.append(item)
                    elif isinstance(c, Element) and c.tag == 'rebind':
                        if c.get('action') not in self.actions:
                            raise GameCompileError(f'<qg:rebind action="{c.get("action")}">: no such action (the game has '
                                                   f'{", ".join(sorted(self.actions))})', c.line)
                        if c.get('player') < 1:
                            raise GameCompileError('<qg:rebind player=>: 1 or more', c.line)
                        action = c.get('action') if c.get('player') == 1 else f'p{c.get("player")}_{c.get("action")}'
                        items.append({'kind': 'rebind', 'action': action, 'label': c.get('label') or c.get('action')})
                    else:
                        raise GameCompileError('<qg:menu> holds qg:button, qg:field, qg:slider and qg:rebind',
                                               getattr(c, 'line', el.line))
                    if isinstance(c, Element) and c.tag in ('slider', 'rebind') and c.get('if') is not None:
                        n = len(items) - 1
                        items[-1]['if_method'] = f'_q_menu_{menus}_if_{n}'
                        script.functions.append(
                            f'func {items[-1]["if_method"]}():\n\treturn {compile_expression(c.get("if"), script.scope(), c.line)}\n')
                if not items:
                    raise GameCompileError('<qg:menu> needs at least one qg:button', el.line)
                font = self._asset(el.get('font'), el.line) if el.get('font') else None
                if el.get('columns') < 1 or el.get('rows') < 0:
                    raise GameCompileError('<qg:menu>: columns= 1 or more, rows= 0 or more', el.line)
                if el.get('local'):
                    # what it does happens on one machine: only a text sent reaches the others
                    if el.get('player') != 1:
                        raise GameCompileError('<qg:menu local="true">: the seat of the machine it is on; no player=',
                                               el.line)
                    if any(not i.get('shared') for i in items):
                        raise GameCompileError('<qg:menu local="true"> holds only shared fields (qg:field '
                                               'shared="true"): anything else it did would happen on one machine '
                                               'and not the others', el.line)
                if el.get('box') is not None:
                    self._box(el.get('box'), sheets, '<qg:menu', el.line)
                nodes.append({'kind': 'menu', 'player': el.get('player'), 'position': el.get('position'),
                              'size': el.get('size'), 'font': font, 'items': items, **self._place(el, 'menu'),
                              **({'rows_method': rows} if rows else {}),
                              **({'local': True} if el.get('local') else {}),
                              **({'box': el.get('box')} if el.get('box') else {}),
                              **({'columns': el.get('columns')} if el.get('columns') > 1 else {}),
                              **({'rows': el.get('rows')} if el.get('rows') else {})})
                if el.get('if') is not None:
                    nodes[-1]['if_method'] = f'_q_menu_{menus}_if'
                    script.functions.append(
                        f'func {nodes[-1]["if_method"]}():\n\treturn {compile_expression(el.get("if"), script.scope(), el.line)}\n')
                self._node_elements.append(el)
            elif el.tag == 'hud':
                items = []
                for c in el.children:
                    if isinstance(c, Element) and c.tag == 'bar':
                        if (c.get('bind') is None) == (c.get('value') is None):
                            raise GameCompileError('<qg:bar> takes bind= or value=, one of them', c.line)
                        bars = sum(1 for n in nodes if n['kind'] == 'hud' for i in n['items'] if i['kind'] == 'bar')
                        bars += sum(1 for i in items if i['kind'] == 'bar')
                        bar = {'kind': 'bar', 'width': c.get('width'), 'height': c.get('height'),
                               'color': c.get('color')}
                        if c.get('bind') is not None:
                            bind = str(c.get('bind'))
                            if '.' in bind:
                                node, prop = bind.split('.', 1)
                                if node not in ids or prop != 'health':
                                    raise GameCompileError(
                                        f'<qg:bar bind="{bind}">: a fighter of this scene and .health (p1.health)',
                                        c.line)
                            elif bind not in script.state and bind not in self.game_state:
                                raise GameCompileError(f'<qg:bar bind="{bind}">: no q:set of that name', c.line)
                            bar['bind'] = bind
                        else:
                            bar['value_method'] = f'_q_bar_{bars}'
                            script.functions.append(f'func _q_bar_{bars}() -> float:\n\treturn float(Q.number('
                                                    f'{compile_expression(c.get("value"), script.scope(), c.line)}))\n')
                        try:
                            bar['max'] = float(str(c.get('max')).strip().strip('{}'))
                        except ValueError:
                            bar['max'] = 100.0
                            bar['max_method'] = f'_q_bar_{bars}_max'
                            script.functions.append(f'func _q_bar_{bars}_max() -> float:\n\treturn float(Q.number('
                                                    f'{compile_expression(c.get("max"), script.scope(), c.line)}))\n')
                        items.append(bar)
                        gdprops.attach(items[-1], 'ProgressBar', c.gd, '<qg:bar>', c.line)
                        continue
                    if isinstance(c, Element) and c.tag == 'inventory':
                        if not any(i['sheet'] for i in self.items.values()):
                            raise GameCompileError('<qg:inventory> shows the qg:items by their pictures: give one '
                                                   'a sheet=', c.line)
                        items.append({'kind': 'inventory', 'size': c.get('size')})
                        gdprops.attach(items[-1], 'HBoxContainer', c.gd, '<qg:inventory>', c.line)
                        continue
                    if isinstance(c, Element) and c.tag in ('counter', 'text'):
                        if c.tag == 'text' and (c.get('bind') is None) == (c.get('value') is None):
                            raise GameCompileError('<qg:text> takes bind= or value=, one of them', c.line)
                        if c.tag == 'counter' and (c.get('bind') is None) == (c.get('item') is None):
                            raise GameCompileError('<qg:counter> takes bind= or item=, one of them', c.line)
                        if c.tag == 'counter' and c.get('item') is not None:
                            self._items_known([(c.get('item'), c.line)])
                            items.append({'kind': 'counter', 'item': c.get('item'), 'label': c.get('label', ''),
                                          'size': c.get('size'), **({'color': c.get('color')} if c.get('color') else {})})
                            gdprops.attach(items[-1], 'Label', c.gd, '<qg:counter>', c.line)
                            continue
                        if c.get('bind') is not None and c.get('bind') not in script.state and c.get('bind') not in self.game_state:
                            raise GameCompileError(
                                f'<qg:{c.tag} bind="{c.get("bind")}">: no q:set of that name in the scene '
                                f'or the game', c.line)
                        items.append({'kind': c.tag, 'bind': c.get('bind'), 'label': c.get('label', ''),
                                      'size': c.get('size')})
                        if c.get('color'):
                            if c.tag == 'text' and is_expression(str(c.get('color'))):
                                texts += 1
                                items[-1]['color_method'] = f'_q_text_{texts}'
                                script.functions.append(
                                    f'func _q_text_{texts}():\n\treturn Q.to_str('
                                    f'{compile_expression(c.get("color"), script.scope(), c.line)})\n')
                            else:
                                items[-1]['color'] = _color(c.get('color'), f'<qg:{c.tag} color=', c.line)
                        if c.tag == 'text' and c.get('value') is not None:
                            texts += 1
                            items[-1]['value_method'] = f'_q_text_{texts}'
                            script.functions.append(
                                f'func _q_text_{texts}():\n\treturn Q.to_str({compile_expression(c.get("value"), script.scope(), c.line)})\n')
                        gdprops.attach(items[-1], 'Label', c.gd, f'<qg:{c.tag}>', c.line)
                    elif isinstance(c, Element) and c.tag == 'table':
                        texts += 1
                        items.append(self._table(c, script, texts))
                    elif isinstance(c, Element) and c.tag == 'icon':
                        self._sheet_exists(c.get('sheet'), sheets, c.line)
                        if c.get('scale') <= 0:
                            raise GameCompileError('<qg:icon scale=>: more than 0', c.line)
                        icon = {'kind': 'icon', 'sheet': c.get('sheet'), 'scale': c.get('scale')}
                        frame = str(c.get('frame'))
                        if is_expression(frame):
                            texts += 1
                            icon['frame_method'] = f'_q_text_{texts}'
                            script.functions.append(f'func _q_text_{texts}():\n\treturn int('
                                                    f'{compile_expression(frame, script.scope(), c.line)})\n')
                        else:
                            try:
                                icon['frame'] = int(frame)
                            except ValueError:
                                raise GameCompileError(f'<qg:icon frame="{frame}">: a frame number, or an expression '
                                                       f'({{...}})', c.line) from None
                        gdprops.attach(icon, 'TextureRect', c.gd, '<qg:icon>', c.line)
                        items.append(icon)
                    else:
                        raise GameCompileError('<qg:hud> holds qg:counter, qg:text, qg:icon, qg:bar, qg:inventory '
                                               'and qg:table', getattr(c, 'line', el.line))
                font = self._asset(el.get('font'), el.line) if el.get('font') else None
                if el.get('box') is not None:
                    self._box(el.get('box'), sheets, '<qg:hud', el.line)
                nodes.append({'kind': 'hud', 'position': el.get('position'), 'items': items,
                              'font': font, 'size': el.get('size'), **self._place(el, 'hud'),
                              **({'box': el.get('box')} if el.get('box') else {})})
                if el.get('if') is not None:
                    texts += 1
                    nodes[-1]['if_method'] = f'_q_text_{texts}'
                    script.functions.append(f'func _q_text_{texts}():\n\treturn bool('
                                            f'{compile_expression(el.get("if"), script.scope(), el.line)})\n')
                self._node_elements.append(el)
            elif el.tag == 'dialogue':
                dname = el.get('name')
                if dname in dialogues:
                    raise GameCompileError(f'two dialogues named {dname!r}', el.line)
                lines, on_end = [], None
                for c in el.children:
                    if isinstance(c, Element) and c.tag == 'line':
                        line_spec = {}
                        for attr in ('who', 'text'):
                            value = str(c.get(attr) or '')
                            if is_expression(value):
                                method = f'_q_dialogue_{_ident(dname)}_{len(lines)}_{attr}'
                                script.functions.append(
                                    f'func {method}():\n\treturn Q.to_str({compile_expression(value, script.scope(), c.line)})\n')
                                line_spec[f'{attr}_method'] = method
                            else:
                                line_spec[attr] = value
                        if c.get('portrait') is not None:
                            if el.get('sheet') is None:
                                raise GameCompileError('<qg:line portrait=>: a frame of the dialogue\'s sheet= (a '
                                                       'qg:spritesheet of faces), which it has not', c.line)
                            line_spec['portrait'] = c.get('portrait')
                        choices = []
                        for k, ch in enumerate(c.children):
                            if not (isinstance(ch, Element) and ch.tag == 'choice'):
                                raise GameCompileError('<qg:line> holds qg:choice, nothing else', getattr(ch, 'line', c.line))
                            prefix = f'_q_dialogue_{_ident(dname)}_{len(lines)}_choice_{k}'
                            choice = {'handler': compile_handler(script, prefix, ch.children, ch.line)}
                            label = str(ch.get('label'))
                            if is_expression(label):
                                script.functions.append(f'func {prefix}_label():\n\treturn Q.to_str('
                                                        f'{compile_expression(label, script.scope(), ch.line)})\n')
                                choice['label_method'] = f'{prefix}_label'
                            else:
                                choice['label'] = label
                            if ch.get('if') is not None:
                                script.functions.append(f'func {prefix}_if() -> bool:\n\treturn bool('
                                                        f'{compile_expression(ch.get("if"), script.scope(), ch.line)})\n')
                                choice['if'] = f'{prefix}_if'
                            choices.append(choice)
                        if choices:
                            line_spec['choices'] = choices
                        lines.append(line_spec)
                    elif isinstance(c, Element) and c.tag == 'on-end':
                        if on_end is not None:
                            raise GameCompileError('a qg:dialogue has one <qg:on-end>', c.line)
                        on_end = compile_handler(script, f'_on_dialogue_{_ident(dname)}_end', c.children, c.line)
                    else:
                        raise GameCompileError('<qg:dialogue> holds qg:line and qg:on-end',
                                               getattr(c, 'line', el.line))
                if not lines:
                    raise GameCompileError(f'<qg:dialogue name="{dname}"> needs at least one qg:line', el.line)
                font = self._asset(el.get('font'), el.line) if el.get('font') else None
                if el.get('sheet') is not None:
                    self._sheet_exists(el.get('sheet'), sheets, el.line)
                if el.get('speed') < 0:
                    raise GameCompileError('<qg:dialogue speed=>: letters a second, 0 or more', el.line)
                if el.get('box') is not None:
                    self._box(el.get('box'), sheets, f'<qg:dialogue name="{dname}"', el.line)
                dialogues[dname] = {'kind': 'dialogue', 'name': dname, 'lines': lines, 'on_end': on_end,
                                    'font': font, 'size': el.get('size'),
                                    **({'speed': el.get('speed')} if el.get('speed') else {}),
                                    **({'box': el.get('box')} if el.get('box') else {}),
                                    **({'sheet': el.get('sheet')} if el.get('sheet') else {})}
                nodes.append(dialogues[dname])
                self._node_elements.append(el)
            elif el.tag in ('touch-button', 'touch-stick'):
                touch.append(el)
            elif el.tag in ('play', 'stop'):
                pass   # an enter statement, read above
            elif el.tag == 'music':
                if music is not None:
                    raise GameCompileError('<qg:music>: one per scene', el.line)
                sound = el.get('sound')
                if sound not in self.sounds:
                    raise GameCompileError(
                        f'<qg:music sound="{sound}">: no qg:sound of that name '
                        f'(declared: {", ".join(sorted(self.sounds)) or "none"})', el.line)
                if not self.sounds[sound].get('loop'):
                    raise GameCompileError(f'<qg:music sound="{sound}">: music loops; give the qg:sound loop="true"',
                                           el.line)
                if el.get('fade') < 0:
                    raise GameCompileError('<qg:music fade=>: the seconds of a fade cannot be negative', el.line)
                music = {'sound': sound, 'fade': el.get('fade'), 'volume': el.get('volume')}
            elif el.tag in ('mirror', 'on-event', 'on-refused'):
                if not script.world_scene:
                    raise GameCompileError(f'<qg:{el.tag}> is in a scene of the world: <qg:scene name="{name}" '
                                           f'world="true">', el.line)
                if el.tag == 'mirror':
                    if el.get('view') not in self.world.views:
                        raise GameCompileError(f'<qg:mirror view="{el.get("view")}">: the world {self.world.name!r} '
                                               f'has no such view (it has: {", ".join(self.world.views)})', el.line)
                    if any(n['kind'] == 'mirror' and n['view'] == el.get('view') for n in nodes):
                        raise GameCompileError(f'two <qg:mirror view="{el.get("view")}"> in a scene', el.line)
                    nodes.append({'kind': 'mirror', 'view': el.get('view')})
                    self._node_elements.append(el)
                elif el.tag == 'on-event':
                    event = el.get('name')
                    if event not in self.world.events:
                        raise GameCompileError(f'<qg:on-event name="{event}">: the world {self.world.name!r} emits no '
                                               f'such event (its q:emit say: '
                                               f'{", ".join(sorted(self.world.events)) or "none"})', el.line)
                    handlers = on_event.setdefault(event, [])
                    handlers.append(compile_handler(script, f'_on_event_{_ident(event)}_{len(handlers)}',
                                                    el.children, el.line, params=('me', 'other', 'value', 'at')))
                else:
                    command = el.get('command')
                    if command is not None and command not in self.world.commands:
                        raise GameCompileError(f'<qg:on-refused command="{command}">: the world {self.world.name!r} '
                                               f'has no such command (it has: '
                                               f'{", ".join(sorted(self.world.commands))})', el.line)
                    on_refused.append({'command': command, 'handler': compile_handler(
                        script, f'_on_refused_{len(on_refused)}', el.children, el.line,
                        params=('me', 'other', 'reason', 'command'))})
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
            for f in (n['follow'] if n['kind'] == 'camera' else []):
                if f == 'me' and script.world_scene:
                    continue                 # the player's own entity, mirrored
                if f not in ids:
                    raise GameCompileError(f'<qg:camera follow="{f}">: no character with that id'
                                           + (' (follow="me" is a scene of the world\'s: world="true")'
                                              if f == 'me' else ''), scene.line)
            if n['kind'] == 'camera' and n['bounds'] == 'tilemap' and tilemap is None:
                raise GameCompileError('<qg:camera bounds="tilemap"> in a scene without a tilemap', scene.line)
        tags = {p['tag'] for p in prefabs.values()}
        for tag in on_death:
            if tag not in tags:
                raise GameCompileError(f'<qg:on-death of="{tag}">: no prefab has that tag', scene.line)
        for h in on_screen:
            if h['of'] not in tags:
                raise GameCompileError(f'<qg:on-screen-{h["on"]} of="{h["of"]}">: no prefab has that tag '
                                       f'(tags: {", ".join(sorted(tags)) or "none"})', scene.line)
        tags |= self._zone_tags
        for n in nodes:
            for kind in ('on_collision', 'on_hit', 'on_separate'):
                for h in n.get(kind, []):
                    if h['with'] not in tags:
                        raise GameCompileError(
                            f'<qg:{kind.replace("_", "-")} with="{h["with"]}">: no prefab or zone has that tag '
                            f'(tags: {", ".join(sorted(tags)) or "none"})', scene.line)
        for dname, line in script.dialogues_used:
            if dname not in dialogues:
                raise GameCompileError(f'<qg:say dialogue="{dname}">: no qg:dialogue of that name in the scene '
                                       f'(dialogues: {", ".join(sorted(dialogues)) or "none"})', line)
        for n in nodes:
            if n['kind'] == 'character' and n['controller'] == 'grid' and tilemap is None:
                raise GameCompileError('<qg:character controller="grid"> walks the cells of a tilemap: '
                                       'the scene has none', scene.line)
        if on_select and not cursors:
            raise GameCompileError('<qg:on-select> in a scene without a <qg:cursor>', scene.line)
        for pname, line in script.paths_used:
            if pname not in paths:
                raise GameCompileError(f'<qg:spawn path="{pname}">: no qg:path of that name in the scene '
                                       f'(paths: {", ".join(sorted(paths)) or "none"})', line)
        if script.net_used and self.multiplayer is None:
            raise GameCompileError('qg:host, qg:join, qg:watch, qg:leave and qg:start-now need a <qg:multiplayer> in q:application', script.net_used[0])
        self._scene_exits[name] = set(exits)
        self._scenes_used.extend(script.scenes_used)
        self._overlays_used.extend(script.overlays_used)
        self._posts_used.extend(script.posts_used)
        self._signs_in = self._signs_in or script.signs_in
        self._scene_goes[name] = [s for s, _ in script.scenes_used]
        self._scene_spawns[name] = script.prefabs_used[0][1] if script.prefabs_used else None
        for pname, line in script.prefabs_used:
            if pname not in prefabs:
                raise GameCompileError(
                    f'no qg:prefab named {pname!r} (declared: {", ".join(sorted(prefabs)) or "none"})', line)
        _heading_is_flown(script.headed, prefabs)
        for pname, line in script.particles_used:
            if pname not in self.particles:
                raise GameCompileError(
                    f'<qg:emit particles="{pname}">: no qg:particles of that name '
                    f'(declared: {", ".join(sorted(self.particles)) or "none"})', line)
        self._animations_known(script.animations_played)
        self._items_known(script.items_used)
        for played in script.sounds_played:
            if played not in self.sounds:
                raise GameCompileError(
                    f'<qg:play sound="{played}">: no qg:sound of that name '
                    f'(declared: {", ".join(sorted(self.sounds)) or "none"})', scene.line)
        for sound, line in script.music_set:
            if not self.sounds[sound].get('loop'):
                raise GameCompileError(f'<qg:music sound="{sound}">: music loops; give the qg:sound loop="true"',
                                       line)
        # gd: attributes, checked against the Godot class each node becomes
        for n, el in zip(nodes, self._node_elements):
            if el is None:
                continue
            if n['kind'] == 'instance':
                cls = gdprops.PREFAB_CLASS[gdprops.prefab_kind(prefabs[n['prefab']])]
            else:
                cls = gdprops.NODE_CLASS.get(n['kind'], 'Node')
            gdprops.attach(n, cls, el.gd, f'<qg:{el.tag}>', el.line)
        seed = str(scene.get('seed')).strip()
        if is_expression(seed):
            # a world's number: read as the scene is entered
            script.functions.append(f'func _q_seed():\n\treturn int({compile_expression(seed, script.scope(), scene.line)})\n')
            seed_spec = {'seed': 0, 'seed_method': '_q_seed'}
        else:
            try:
                seed_spec = {'seed': int(seed)}
            except ValueError:
                raise GameCompileError(f'<qg:scene seed="{seed}">: a whole number, or an expression ({{...}}) giving one',
                                       scene.line) from None
        world_spec = {}
        if script.world_scene:
            world_spec['world'] = True
            if on_event:
                world_spec['on_event'] = on_event
            if on_refused:
                world_spec['on_refused'] = on_refused
            if self.game.connect.get('name') is not None:
                code = compile_expression(self.game.connect.get('name'), script.scope(), self.game.connect.line)
                script.functions.append(f'func _q_world_name() -> String:\n\treturn Q.to_str({code})\n')
                world_spec['world_name'] = '_q_world_name'
        script_file = _script_name(name)
        self.scripts[script_file] = script.source()
        spec = {
            'name': name, 'script': f'res://scripts/{script_file}',
            'width': scene.get('width'), 'height': scene.get('height'),
            'background': scene.get('background'), **seed_spec,
            'nodes': nodes, 'map_paths': map_paths, 'on_input': on_input, 'on_release': on_release,
            'on_screen': on_screen, 'on_death': on_death,
            'on_select': on_select, 'music': music,
            **({'sequences': sequences} if sequences else {}),
            **world_spec,
        }
        has_map = any(n['kind'] == 'tilemap' for n in nodes)
        if script.travels_used and not has_map:
            raise GameCompileError('<qg:travel> goes over the scene\'s qg:tilemap, which it has not',
                                   script.travels_used[0])
        if any(n['kind'] == 'cursor' and n.get('cells') for n in nodes) and not has_map:
            raise GameCompileError('<qg:cursor cells="true">: the cells of the scene\'s qg:tilemap, which it has not',
                                   scene.line)
        if scene.get('ambient') is not None:
            # a dark scene: its solid tiles stop the lights that cast shadows
            spec['ambient'] = scene.get('ambient')
            for n in nodes:
                if n['kind'] == 'tilemap':
                    n['shadows'] = True
        if script.cameras_moved and not cameras_here:
            raise GameCompileError('<qg:camera-to> moves the scene\'s qg:camera, which it has not', script.cameras_moved[0])
        for player, line in pointers:
            if player not in cursors:
                raise GameCompileError(f'<qg:character controller="pointer" player="{player}">: a click walks it to '
                                       f'where its player\'s qg:cursor is; the scene needs <qg:cursor player='
                                       f'"{player}" />', line)
        if whens:
            spec['when'] = whens
        if touch:
            spec['touch'] = self._touch(touch, name)
        if tiled:
            spec['tiled'] = tiled   # the Tiled map's own properties: tiled('par')
        if scene.get('y-sort'):
            spec['y_sort'] = True
        if scene.get('save'):
            spec['save'] = True
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


_COLOR_RE = re.compile(r'^#[0-9a-fA-F]{6}$')


def _color(raw, where: str, line: Optional[int]) -> str:
    """A colour given as it is (#rrggbb), where an expression giving one could have been."""
    raw = str(raw).strip()
    if not _COLOR_RE.match(raw):
        raise GameCompileError(f'{where}"{raw}">: a colour #rrggbb, or an expression ({{...}}) giving one', line)
    return raw.lower()


def action_name(player: int, action: str) -> str:
    """The Godot input action of a player's action: `up` for player 1, `p2_up` for player 2."""
    return action if player == 1 else f'p{player}_{action}'


_HEADINGS = {'up': (0.0, -1.0), 'down': (0.0, 1.0), 'left': (-1.0, 0.0), 'right': (1.0, 0.0)}

# The parts an enemy (a qg:prefab ai="behavior") is made of; a character's are the others.
_ENEMY_PARTS = ('seek', 'flee', 'keep-distance', 'patrol', 'wander', 'stand', 'shoot', 'leap')


# What a scene the rollback reaches may hold: nodes that save and load their whole state
# and never go through Godot's physics, which cannot be run again inside one frame. A tilemap
# saves the cells qg:set-tile changed (a fighter stands on its own floor, not on its tiles), and
# the scene's tweens are records the rollback saves and runs again (tween.gd).
_ROLLBACK_KINDS = {'character', 'timer', 'hud', 'sprite', 'menu', 'camera', 'tilemap', 'label'}


def _check_rollback(start: str, scenes: dict, goes: Dict[str, List[str]], spawns: Dict[str, Optional[int]],
                    line: Optional[int]) -> None:
    reach, todo = set(), [start]
    while todo:
        s = todo.pop()
        if s in reach or s not in scenes:
            continue
        reach.add(s)
        todo.extend(goes.get(s, []))
    for s in sorted(reach):
        for n in scenes[s]['nodes']:
            what = n['kind'] if n['kind'] != 'character' else f'controller="{n["controller"]}"'
            if n['kind'] not in _ROLLBACK_KINDS or (n['kind'] == 'character' and n['controller'] != 'fighter'):
                raise GameCompileError(
                    f'<qg:multiplayer rollback=>: the scene {s!r} holds {what}, which goes through physics or '
                    f'keeps no state to roll back — rollback takes fighters, timers, menus, the HUD, pictures '
                    f'a tilemap and a camera (rollback="0" is the plain lockstep)', line)
        if spawns.get(s) is not None:
            raise GameCompileError(f'<qg:multiplayer rollback=>: the scene {s!r} places prefabs (qg:spawn, qg:swap), '
                                   f'which rollback cannot take back', spawns[s])


def _el(tag: str, line: Optional[int], children=(), **attrs) -> Element:
    """An element the compiler writes itself, with the schema's defaults (attribute names use _ for -)."""
    values = {name: spec.default for name, spec in TAGS[tag].attrs.items()}
    values.update({k.replace('_', '-'): v for k, v in attrs.items()})
    return Element(tag, values, line, list(children))


# What a qg:lobby shows, and the notices of a networked game (lockstep.gd), in
# The forms a count's word takes in a language besides as= (the rest), as Q.plural_form picks them for whole
# numbers (after CLDR): one, few and many in Russian; none where a word is the same for any number.
PLURAL_FORMS = {**{code: ('one', 'few', 'many') for code in ('ru', 'uk', 'be', 'pl')},
                **{code: ('one', 'few') for code in ('cs', 'sk')},
                **{code: () for code in ('ja', 'zh', 'ko', 'vi', 'th', 'id')}}


# the languages the repository's games speak: a game declaring one of them has
# these phrases too (its own qg:phrase wins).
LOBBY_PHRASES = {
    'pt': {'Language': 'Idioma', 'Host a game': 'Criar uma partida', 'Address': 'Endereço', 'Join': 'Entrar', 'Cancel': 'Cancelar',
           'Waiting for the other players on port': 'Esperando os outros jogadores na porta',
           'Joining': 'Entrando em', 'Connected, starting...': 'Conectado, começando...',
           'Could not connect': 'Não foi possível conectar',
           'Waiting for the other player to come back': 'Esperando o outro jogador voltar',
           'Catching up': 'Alcançando a partida', 'The other player left': 'O outro jogador saiu',
           'The games differ: the match stopped': 'Os jogos divergiram: a partida parou',
           'Start now': 'Começar agora', 'here': 'aqui', 'Watch': 'Assistir', 'Watching': 'Assistindo',
           'Options': 'Opções'},
    'es': {'Language': 'Idioma', 'Host a game': 'Crear una partida', 'Address': 'Dirección', 'Join': 'Unirse', 'Cancel': 'Cancelar',
           'Waiting for the other players on port': 'Esperando a los demás jugadores en el puerto',
           'Joining': 'Uniéndose a', 'Connected, starting...': 'Conectado, empezando...',
           'Could not connect': 'No se pudo conectar',
           'Waiting for the other player to come back': 'Esperando a que el otro jugador vuelva',
           'Catching up': 'Poniéndose al día', 'The other player left': 'El otro jugador se fue',
           'The games differ: the match stopped': 'Las partidas difieren: el juego se detuvo',
           'Start now': 'Empezar ya', 'here': 'aquí', 'Watch': 'Mirar', 'Watching': 'Mirando',
           'Options': 'Opciones'},
}

# The label of a button for qg:next-language: "Language: English".
LANGUAGE_LABEL = "{tr('Language') + ': ' + language()}"

_BUSY = "net_status() == 'hosting' or net_status() == 'joining' or net_status() == 'connected'"
_IDLE = "net_status() == 'offline' or net_status() == 'failed'"


def _expand_lobbies(children: list, multiplayer: Optional[dict], languages: bool = False) -> list:
    """qg:lobby, written out: a q:set for the address, a qg:menu, a qg:hud with the status line."""
    out: list = []
    for node in children:
        if not (isinstance(node, Element) and node.tag == 'lobby'):
            out.append(node)
            continue
        el, line = node, node.line
        if multiplayer is None:
            raise GameCompileError('<qg:lobby> needs a <qg:multiplayer> in q:application', line)
        if el.children:
            raise GameCompileError('<qg:lobby> holds nothing; write a qg:menu to have other buttons', line)
        port = el.get('port')
        buttons = []
        if el.get('local'):
            buttons.append(_el('button', line, [_el('goto-scene', line, name=el.get('local'))], label=el.get('local-label')))
        buttons += [
            _el('button', line, [_el('host', line, port=port)], label='Host a game', **{'if': '{' + _IDLE + '}'}),
            _el('field', line, bind='lobby_address', label='Address'),
            _el('button', line, [_el('join', line, address='{lobby_address}')], label='Join', **{'if': '{' + _IDLE + '}'}),
            *([] if multiplayer.get('rollback') else [   # one who only watches: not under the rollback
                _el('button', line, [_el('watch', line, address='{lobby_address}')], label='Watch',
                    **{'if': '{' + _IDLE + '}'})]),
            _el('button', line, [_el('leave', line)], label='Cancel', **{'if': '{' + _BUSY + '}'}),
        ]
        least = multiplayer.get('min_players')
        if least:   # fewer may play: the host starts with those who are there
            buttons.insert(-1, _el('button', line, [_el('start-now', line)], label='Start now',
                                   **{'if': '{' + f"(net_status() == 'hosting' or (net_status() == 'connected' and net_player() == 1)) "
                                         f"and net_players() >= {least}" + '}'}))
        if el.get('options'):   # the game's options screen
            buttons.append(_el('button', line, [_el('goto-scene', line, name=el.get('options'))], label='Options',
                               **{'if': '{' + _IDLE + '}'}))
        if languages:   # a game in several languages: a button to show the next one
            buttons.append(_el('button', line, [_el('next-language', line)], label=LANGUAGE_LABEL))
        # each part through tr(), in the player's language (LOBBY_PHRASES); the same text in English
        here = " + ' (' + str(net_players()) + ' ' + tr('here') + ')'" if least else ''   # how many are there
        status = ("{" + f"tr('Waiting for the other players on port') + ' {port}'{here} if net_status() == 'hosting' else "
                  "(tr('Joining') + ' ' + lobby_address + '...' if net_status() == 'joining' else "
                  "(tr('Connected, starting...') if net_status() == 'connected' else "
                  "(tr('Could not connect') if net_status() == 'failed' else '')))" + "}")
        # the address field starts with the page's ?join= (a link to a relay's room), else address=
        out.append(Statement('set', {'name': 'lobby_address',
                                     'value': '{url_param(' + json.dumps('join') + ', ' + json.dumps(str(el.get('address'))) + ')}'},
                             line))
        out.append(_el('menu', line, buttons, font=el.get('font'), size=el.get('size')))
        out.append(_el('hud', line, [_el('text', line, value=status)], position='bottom-center', size=el.get('size')))
    return out


def _slice(raw: str, tile: tuple, name: str, line: Optional[int]) -> list:
    """slice=: the edges of a frame that do not stretch, left, top, right, bottom."""
    try:
        edges = [int(p) for p in str(raw).split(',')]
    except ValueError:
        edges = []
    if len(edges) == 1:
        edges *= 4
    if len(edges) != 4 or min(edges) < 0:
        raise GameCompileError('<qg:spritesheet slice=>: its edges in pixels, 16, or left, top, right, bottom '
                               '(16, 8, 16, 8)', line)
    if edges[0] + edges[2] >= tile[0] or edges[1] + edges[3] >= tile[1]:
        raise GameCompileError(f'<qg:spritesheet name="{name}" slice=>: edges of {", ".join(map(str, edges))} leave '
                               f'nothing to stretch in a {tile[0]}x{tile[1]} frame', line)
    return edges


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
        if not a.get('loop'):
            out[name]['loop'] = False
    return out


def _heading_is_flown(headed: List[tuple], prefabs: dict) -> None:
    for pname, line in headed:
        if pname in prefabs and prefabs[pname]['ai'] != 'fly':
            raise GameCompileError(f'<qg:spawn prefab="{pname}" heading=>: heading= is for a prefab with ai="fly"',
                                   line)


def _looks(el: Element, script: SceneScript, prefix: str, particles: dict) -> dict:
    """How a character or a prefab looks besides its frame: an effect kept going on it (particles=), when it
    is shown (visible=, a method with `me`), upside down, its draw layer, and the qg:labels over it (each a
    method with `me` giving the text). Only seen."""
    out: dict = {}
    scope = script.scope().child(('me',), things=('me',))
    if el.get('particles') is not None:
        if el.get('particles') not in particles:
            raise GameCompileError(f'particles="{el.get("particles")}": no qg:particles of that name', el.line)
        out['particles'] = el.get('particles')
    if el.get('visible') is not None:
        out['visible'] = f'{prefix}_visible'
        script.functions.append(f'func {prefix}_visible(me) -> bool:\n\treturn bool('
                                f'{compile_expression(el.get("visible"), scope, el.line)})\n')
    if el.get('flip-v'):
        out['flip_v'] = True
    if el.get('layer'):
        out['layer'] = el.get('layer')
    labels = []
    for i, lb in enumerate(el.find_all('label')):
        if lb.get('x') is not None or lb.get('y') is not None:
            raise GameCompileError('<qg:label> on a character or a prefab takes dx= and dy= (from its middle), '
                                   'not x= and y=', lb.line)
        method = f'{prefix}_label_{i}'
        script.functions.append(f'func {method}(me) -> String:\n\treturn Q.to_str('
                                f'{compile_expression(lb.get("value"), scope, lb.line)})\n')
        label = {'method': method, 'dx': lb.get('dx'), 'dy': lb.get('dy'), 'size': lb.get('size'),
                 'color': lb.get('color')}
        if lb.get('if') is not None:
            label['if'] = f'{method}_if'
            script.functions.append(f'func {method}_if(me) -> bool:\n\treturn bool('
                                    f'{compile_expression(lb.get("if"), scope, lb.line)})\n')
        labels.append(label)
    if labels:
        out['labels'] = labels
    bars = []
    for i, hb in enumerate(el.find_all('health-bar')):
        method = f'{prefix}_bar_{i}'
        script.functions.append(f'func {method}(me) -> float:\n\treturn float(Q.number('
                                f'{compile_expression(hb.get("value"), scope, hb.line)}))\n')
        script.functions.append(f'func {method}_max(me) -> float:\n\treturn float(Q.number('
                                f'{compile_expression(hb.get("max"), scope, hb.line)}))\n')
        if hb.get('width') < 1 or hb.get('height') < 1:
            raise GameCompileError('<qg:health-bar>: width= and height= 1 or more', hb.line)
        bars.append({'method': method, 'dx': hb.get('dx'), 'dy': hb.get('dy'), 'width': hb.get('width'),
                     'height': hb.get('height'), 'color': hb.get('color')})
    if bars:
        out['bars'] = bars
    lights = []
    for lt in el.find_all('light'):
        if lt.get('x') is not None or lt.get('y') is not None:
            raise GameCompileError('<qg:light> on a character or a prefab takes dx= and dy= (from its middle), '
                                   'not x= and y=', lt.line)
        lights.append({'dx': lt.get('dx'), 'dy': lt.get('dy'), **_light(lt)})
    if lights:
        out['lights'] = lights
    return out


def _light(el: Element) -> dict:
    """A qg:light's own look, wherever it is."""
    if el.get('radius') <= 0 or el.get('energy') < 0 or not 0 <= el.get('flicker') <= 1:
        raise GameCompileError('<qg:light>: radius= more than 0, energy= 0 or more, flicker= from 0 to 1', el.line)
    return {'radius': el.get('radius'), 'color': el.get('color'), 'energy': el.get('energy'),
            **({'flicker': el.get('flicker')} if el.get('flicker') else {}),
            **({'shadows': True} if el.get('shadows') else {})}


def _contact_handlers(el: Element, script: SceneScript, prefix: str) -> dict:
    """A character's or a prefab's qg:on-separate and qg:on-screen-exit/-enter handlers (`me` is itself)."""
    out: dict = {}
    separate = [{'with': h.get('with'),
                 'handler': compile_handler(script, f'{prefix}_separate_{i}', h.children, h.line)}
                for i, h in enumerate(el.find_all('on-separate'))]
    screen = []
    for tag in ('on-screen-exit', 'on-screen-enter'):
        for i, h in enumerate(el.find_all(tag)):
            if h.get('of'):
                raise GameCompileError(f'of= is for a <qg:{tag}> in a scene; here it is about this one', h.line)
            on = tag[len('on-screen-'):]
            screen.append({'on': on, 'side': h.get('side'),
                           'handler': compile_handler(script, f'{prefix}_screen_{on}_{i}', h.children, h.line)})
    if separate:
        out['on_separate'] = separate
    if screen:
        out['on_screen'] = screen
    return out


def _animation_ends(el: Element, script: SceneScript, prefix: str) -> List[dict]:
    """The qg:on-animation-end handlers of a character or a prefab, each naming one of its animations."""
    names = set(_animations(el)) | {a for st in el.find_all('state') for a in _animations(st)}
    out = []
    for i, h in enumerate(el.find_all('on-animation-end')):
        if h.get('name') not in names:
            raise GameCompileError(f'<qg:on-animation-end name="{h.get("name")}">: no qg:animation of that name here '
                                   f'(it has: {", ".join(sorted(names)) or "none"})', h.line)
        out.append({'name': h.get('name'),
                    'handler': compile_handler(script, f'{prefix}_animation_end_{i}', h.children, h.line)})
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
