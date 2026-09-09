"""
Godot 4 - Code Generator

Transforms Game AST nodes into Godot 4 project files (.tscn, .gd, project.godot).
This is the Godot backend equivalent of game_code_generator.py (PIXI+Matter.js).

AST and Parser are unchanged — only the code generation backend differs.

Pipeline:
  .q → Parser → AST → GodotCodeGenerator → .tscn + .gd files → Godot project directory
"""

import os
import json
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from quantum.core.features.game_engine_2d.src.ast_nodes import (
    SceneNode, SpriteNode, PhysicsNode, ColliderNode, AnimationNode,
    CameraNode, InputNode, SoundNode, ParticleNode, TimerNode,
    SpawnNode, HudNode, TweenNode, TilemapNode, TilemapLayerNode,
    BehaviorNode, UseNode, PrefabNode, InstanceNode, GroupNode,
    StateMachineNode, StateNode, TransitionNode, RawCodeNode,
    ClickableNode, EventNode, OnCollisionNode, TileAnimationNode,
    HudTileNode, HudCounterNode, HudCollectionNode,
    HudSlotNode, HudOptionNode, HudBehaviorNode, HudActionNode,
    SceneTransitionNode, PersistentNode, MapNodeDef, MapPathNode,
    EventActionNode, CollisionLayerDef,
    EnemyNode, EnemyAiNode, EnemyDefeatNode, EnemyOnHitNode, EnemyOnKillNode,
)
from quantum.core.ast_nodes import QuantumNode, HTMLNode, TextNode
from quantum.core.features.conditionals.src.ast_node import IfNode
from quantum.core.features.loops.src.ast_node import LoopNode
from quantum.core.features.state_management.src.ast_node import SetNode
from quantum.core.features.functions.src.ast_node import FunctionNode

from quantum.runtime.godot_templates import (
    GdScriptBuilder, TscnBuilder,
    QUANTUM_SCALE, q2g, q2g_int, q2g_gravity, q2g_speed, q2g_jump,
    gd_string, gd_bool, gd_vector2, gd_vector2i, gd_color,
    EASING_MAP, TRANS_MAP,
    build_project_godot, build_export_presets,
    QUANTUM_BRIDGE_GD, QUANTUM_EVENT_BUS_GD,
    PLAYER_CONTROLLER_GD, SPIN_JUMP_SECTION, CAMERA_FOLLOW_GD, PATROL_AI_GD, HUD_MANAGER_GD, SPRITE_ANIMATOR_GD,
    SCENE_MANAGER_GD, MAP_CONTROLLER_GD, GAME_OVER_SCREEN_GD, TILEMAP_LOADER_GD,
    # SNES constants
    SNES_WIDTH, SNES_HEIGHT, SNES_WINDOW_SCALE,
    SMW_GRAVITY, SMW_GRAVITY_RISING, SMW_GRAVITY_FALLING,
    SMW_WALK_SPEED, SMW_JUMP_VELOCITY, SMW_MAX_FALL,
    SMW_JUMP_HOLD_BOOST, SMW_COYOTE_FRAMES,
)


class GodotCodeGenerator:
    """Generates a Godot 4 project directory from a game AST."""

    def __init__(self, source_dir: str = None):
        self._source_dir = source_dir
        self._sprites: List[Dict] = []
        self._behaviors: Dict[str, BehaviorNode] = {}
        self._prefabs: Dict[str, PrefabNode] = {}
        self._state_vars: List[Dict] = []
        self._functions: List[FunctionNode] = []
        self._sounds: List[Dict] = []
        self._particles: List[Dict] = []
        self._timers: List[Dict] = []
        self._tweens: List[Dict] = []
        self._huds: List[Dict] = []
        self._custom_inputs: List[Dict] = []
        self._events: List[Dict] = []
        self._camera: Optional[Dict] = None
        self._physics: Optional[Dict] = None
        self._assets: set = set()
        self._sprite_counter: int = 0
        self._scene_width: int = 800
        self._scene_height: int = 600
        self._viewport_width: int = SNES_WIDTH
        self._viewport_height: int = SNES_HEIGHT
        self._spawners: List[Dict] = []
        self._tilemaps: List[Dict] = []
        self._instances: List[Dict] = []
        self._groups: List[Dict] = []
        self._map_nodes: List[Dict] = []
        self._map_paths: List[Dict] = []
        self._enemies: List[EnemyNode] = []
        self._output_dir: Optional[Path] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, scene: SceneNode, behaviors: List[BehaviorNode] = None,
                 prefabs: List[PrefabNode] = None,
                 enemies: List[EnemyNode] = None,
                 output_dir: str = 'output',
                 project_name: str = 'QuantumGame') -> str:
        """Generate a complete Godot 4 project directory from a SceneNode.

        Returns the output directory path.
        """
        self._scene_width = scene.width
        self._scene_height = scene.height
        self._viewport_width = scene.viewport_width or SNES_WIDTH
        self._viewport_height = scene.viewport_height or SNES_HEIGHT

        for b in (behaviors or []):
            self._behaviors[b.name] = b
        for p in (prefabs or []):
            self._prefabs[p.name] = p
        for e in (enemies or []):
            self._enemies.append(e)

        # Walk the AST
        self._process_scene_children(scene.children)

        # Build output directory
        out = Path(output_dir)
        self._output_dir = out
        out.mkdir(parents=True, exist_ok=True)
        scripts_dir = out / 'scripts'
        scripts_dir.mkdir(exist_ok=True)
        prefabs_dir = out / 'prefabs'
        prefabs_dir.mkdir(exist_ok=True)
        assets_dir = out / 'assets'
        assets_dir.mkdir(exist_ok=True)

        # 1. project.godot
        self._write_project_godot(out, scene, project_name)

        # 2. Autoload scripts
        self._write_autoload_scripts(scripts_dir)

        # 3. Main scene .tscn + script
        self._write_main_scene(out, scripts_dir, scene)

        # 4. Prefab scenes
        self._write_prefab_scenes(prefabs_dir, scripts_dir)

        # 5. Player controller (if needed)
        self._write_player_controller(scripts_dir)

        # 6. Camera script (if needed)
        self._write_camera_script(scripts_dir)

        # 7. Enemy/AI scripts
        self._write_ai_scripts(scripts_dir)

        # 8. HUD script (if needed)
        self._write_hud_script(scripts_dir)

        # 9. Game over screen (if death_sequence="smw")
        self._write_game_over_screen(scripts_dir, scene)

        # 10. Tilemap assets + loader (if data-src)
        self._write_tilemap_assets(out)
        self._write_tilemap_loader(scripts_dir)

        # 11. Export presets
        self._write_export_presets(out)

        return str(out.resolve())

    def generate_multi(self, scenes: List[SceneNode], initial: str,
                       behaviors: List[BehaviorNode] = None,
                       prefabs: List[PrefabNode] = None,
                       enemies: List[EnemyNode] = None,
                       persistent: List = None,
                       output_dir: str = 'output',
                       project_name: str = 'QuantumGame') -> str:
        """Generate Godot project with multiple scenes.

        Each scene becomes a separate .tscn + .gd pair in the scenes/ directory.
        SceneManager autoload handles transitions and persistent state.
        """
        if not scenes:
            return self.generate(SceneNode('empty'), behaviors, prefabs, enemies, output_dir, project_name)

        # If only one scene, use single-scene generation (backward compat)
        if len(scenes) == 1:
            return self.generate(scenes[0], behaviors, prefabs, enemies, output_dir, project_name)

        # Find initial scene
        initial_scene = scenes[0]
        for sc in scenes:
            if getattr(sc, 'initial', False):
                initial_scene = sc
                break
            if sc.name == initial:
                initial_scene = sc

        # Set up shared state
        for b in (behaviors or []):
            self._behaviors[b.name] = b
        for p in (prefabs or []):
            self._prefabs[p.name] = p
        for e in (enemies or []):
            self._enemies.append(e)

        # Build output directory structure
        out = Path(output_dir)
        self._output_dir = out
        out.mkdir(parents=True, exist_ok=True)
        scenes_dir = out / 'scenes'
        scenes_dir.mkdir(exist_ok=True)
        scripts_dir = out / 'scripts'
        scripts_dir.mkdir(exist_ok=True)
        prefabs_dir = out / 'prefabs'
        prefabs_dir.mkdir(exist_ok=True)
        assets_dir = out / 'assets'
        assets_dir.mkdir(exist_ok=True)

        # 1. project.godot — main_scene points to initial scene in scenes/
        self._write_multi_project_godot(out, initial_scene, scenes, project_name)

        # 2. Autoload scripts (bridge + event bus + scene manager)
        self._write_autoload_scripts(scripts_dir)
        (scripts_dir / 'scene_manager.gd').write_text(
            self._build_scene_manager_script(persistent or []),
            encoding='utf-8'
        )

        # 3. Generate each scene as scenes/{name}.tscn + scripts/scene_{name}.gd
        all_has_player = False
        all_has_camera = False
        all_has_patrol = False
        for scene in scenes:
            self._reset_scene_state()
            self._scene_width = scene.width
            self._scene_height = scene.height
            self._viewport_width = scene.viewport_width or SNES_WIDTH
            self._viewport_height = scene.viewport_height or SNES_HEIGHT

            self._process_scene_children(scene.children)

            # Generate .tscn + .gd for this scene
            self._write_scene_file(scenes_dir, scripts_dir, scene)

            if any(s.get('controls') for s in self._sprites):
                all_has_player = True
            if self._camera:
                all_has_camera = True
            if any(s.get('tag') in ('enemy',) for s in self._sprites):
                all_has_patrol = True

        # 4. Shared scripts
        if all_has_player:
            self._write_player_controller(scripts_dir)
        if all_has_camera:
            self._write_camera_script(scripts_dir)
        if all_has_patrol:
            self._write_ai_scripts(scripts_dir)

        # 5. Shared prefab scenes
        self._write_prefab_scenes(prefabs_dir, scripts_dir)

        # 6. Tilemap assets + loader (if any scene uses data-src)
        self._write_tilemap_assets(out)
        self._write_tilemap_loader(scripts_dir)

        # 7. Export presets
        self._write_export_presets(out)

        # 8. Copy referenced assets (sprites, sounds) to output
        self._copy_assets(out)

        return str(out.resolve())

    def _reset_scene_state(self):
        """Reset per-scene state for multi-scene generation."""
        self._sprites = []
        self._state_vars = []
        self._functions = []
        self._sounds = []
        self._particles = []
        self._timers = []
        self._tweens = []
        self._huds = []
        self._custom_inputs = []
        self._events = []
        self._camera = None
        self._physics = None
        self._spawners = []
        self._tilemaps = []
        self._instances = []
        self._groups = []
        self._map_nodes = []
        self._map_paths = []
        self._sprite_counter = 0

    def _write_multi_project_godot(self, out: Path, initial_scene: SceneNode,
                                    scenes: List[SceneNode], project_name: str):
        """Generate project.godot for multi-scene project."""
        gravity_y = SMW_GRAVITY

        # Collect input maps from all scenes
        # Reset + process all scenes to build comprehensive input map
        saved_sprites = self._sprites
        all_inputs = {}
        for scene in scenes:
            self._sprites = []
            self._custom_inputs = []
            self._process_scene_children(scene.children)
            scene_map = self._build_input_map()
            all_inputs.update(scene_map)
        self._sprites = saved_sprites

        scene_name = _sanitize_name(initial_scene.name)
        config = {
            'name': project_name,
            'main_scene': f'scenes/{scene_name}.tscn',
            'viewport_width': initial_scene.viewport_width or SNES_WIDTH,
            'viewport_height': initial_scene.viewport_height or SNES_HEIGHT,
            'gravity': gravity_y,
            'input_map': all_inputs,
            'autoloads': {
                'QuantumBridge': 'scripts/quantum_bridge.gd',
                'QuantumEventBus': 'scripts/quantum_event_bus.gd',
                'SceneManager': 'scripts/scene_manager.gd',
            },
        }
        content = build_project_godot(config)
        (out / 'project.godot').write_text(content, encoding='utf-8')

    def _build_scene_manager_script(self, persistent_nodes: List) -> str:
        """Build SceneManager script with persistent state initialization."""
        script = SCENE_MANAGER_GD

        # If there are persistent nodes, add initial state setup
        if persistent_nodes:
            init_lines = []
            for pnode in persistent_nodes:
                if isinstance(pnode, PersistentNode):
                    for child in pnode.children:
                        if isinstance(child, SetNode):
                            name = child.name
                            value = child.value
                            var_type = getattr(child, 'type', 'string')
                            if var_type == 'integer':
                                init_lines.append(f'\tpersistent_state["{name}"] = {value}')
                            elif var_type == 'float':
                                init_lines.append(f'\tpersistent_state["{name}"] = {value}')
                            elif var_type == 'boolean':
                                gd_val = 'true' if value.lower() in ('true', '1', 'yes') else 'false'
                                init_lines.append(f'\tpersistent_state["{name}"] = {gd_val}')
                            else:
                                init_lines.append(f'\tpersistent_state["{name}"] = "{value}"')

            if init_lines:
                # Insert initialization into _ready()
                init_block = '\n'.join(init_lines)
                script = script.replace(
                    '\t_setup_transition_layer()',
                    f'\t_setup_transition_layer()\n\t_init_persistent_state()\n'
                )
                script = script.rstrip()
                script += f'\n\nfunc _init_persistent_state():\n{init_block}\n'

        return script

    def _write_scene_file(self, scenes_dir: Path, scripts_dir: Path, scene: SceneNode):
        """Generate a single scene .tscn + .gd for multi-scene mode."""
        scene_name = _sanitize_name(scene.name)
        script_path = f'scripts/scene_{scene_name}.gd'

        tscn = TscnBuilder()

        # Determine root node type based on scene type
        root_type = 'Node2D'

        # Root node with script
        tscn.add_node_with_script(
            _pascal_case(scene_name), root_type,
            # Script path is relative to res:// (project root)
            script_path=f'scripts/scene_{scene_name}.gd'
        )

        # Background color
        bg = scene.background or '#000000'
        tscn.add_node('Background', 'ColorRect', parent='.', properties={
            'offset_right': float(scene.width),
            'offset_bottom': float(scene.height),
            'color': gd_color(bg),
        })

        # Sprites
        for sprite in self._sprites:
            self._add_sprite_to_tscn(tscn, sprite, parent='.')

        # Tilemaps
        for tilemap in self._tilemaps:
            self._add_tilemap_to_tscn(tscn, tilemap, parent='.')

        # Camera
        if self._camera:
            self._add_camera_to_tscn(tscn)

        # Sounds
        if self._sounds:
            tscn.add_node('Sounds', 'Node', parent='.')
            for sound in self._sounds:
                props = {}
                if sound['volume'] != 1.0:
                    import math
                    props['volume_db'] = 20 * math.log10(max(sound['volume'], 0.001))
                src = sound['src']
                if src:
                    res_id = tscn.add_ext_resource('AudioStream', _asset_path(src))
                    props['stream'] = f'ExtResource("{res_id}")'
                tscn.add_node(sound['id'], 'AudioStreamPlayer', parent='Sounds', properties=props)

        # Particles
        for particle in self._particles:
            self._add_particle_to_tscn(tscn, particle, parent='.')

        # Timers
        for timer in self._timers:
            props = {
                'wait_time': timer['interval'],
                'one_shot': timer['repeat'] == 1,
                'autostart': timer['auto_start'],
            }
            tscn.add_node(timer['id'], 'Timer', parent='.', properties=props)

        # HUD
        if self._huds:
            self._add_hud_to_tscn(tscn)

        # Instances
        for inst in self._instances:
            self._add_instance_to_tscn(tscn, inst, parent='.')

        # Write .tscn
        tscn_content = tscn.build()
        (scenes_dir / f'{scene_name}.tscn').write_text(tscn_content, encoding='utf-8')

        # Write scene script — map scenes get map_controller logic
        if getattr(scene, 'scene_type', 'level') == 'map' and self._map_nodes:
            script = self._build_map_scene_script(scene)
        else:
            script = self._build_multi_scene_script(scene)
        (scripts_dir / f'scene_{scene_name}.gd').write_text(script, encoding='utf-8')

        # Write HUD script if needed (per-scene)
        if self._huds:
            self._write_hud_script(scripts_dir)

    def _build_multi_scene_script(self, scene: SceneNode) -> str:
        """Generate a scene GDScript with SceneManager transition support."""
        gd = GdScriptBuilder()
        gd.extends('Node2D')
        gd.blank()

        # State variables
        if self._state_vars:
            gd.comment('State variables')
            for sv in self._state_vars:
                gd.var(sv['name'], sv['value'])
            gd.blank()

        # Identify player sprite
        player_id = None
        for sprite in self._sprites:
            if sprite.get('tag') == 'player' or sprite.get('controls'):
                player_id = sprite['id']
                break

        # Death sequence config from scene attrs
        death_sequence = getattr(scene, 'death_sequence', None) or 'smw'
        death_timer = float(getattr(scene, 'death_timer', 3.0) or 3.0)

        # Build sound trigger map: event_name -> [sound_id, ...]
        sound_triggers = {}
        bgm_sounds = []
        for sound in self._sounds:
            trigger = sound.get('trigger', '')
            if trigger == 'scene.start':
                bgm_sounds.append(sound['id'])
            elif trigger:
                sound_triggers.setdefault(trigger, []).append(sound['id'])

        # Build event action map and transition map
        event_actions = {}  # event_name -> [actions]
        event_transitions = {}  # event_name -> [transitions]
        event_handlers = {}  # event_name -> handler_name (custom)
        for evt in self._events:
            if evt.get('actions'):
                event_actions[evt['name']] = evt['actions']
            if evt.get('transitions'):
                event_transitions[evt['name']] = evt['transitions']
            if evt.get('handler'):
                event_handlers[evt['name']] = evt['handler']

        # _ready
        gd.func('_ready')
        gd.line(f'SceneManager.current_scene_name = "{scene.name}"')

        # Register sprites with bridge
        for sprite in self._sprites:
            sid = sprite['id']
            gd.line(f'QuantumBridge.register_sprite("{sid}", {_gd_node_ref(sid)})')
        gd.blank()

        # Set death texture on player
        if player_id:
            death_sprites = [s for s in self._sprites if s['id'] == '_preload_death']
            if death_sprites:
                gd.comment('Death texture')
                gd.line(f'{_gd_node_ref(player_id)}.set_death_texture({_gd_node_ref("_preload_death")}.texture)')
                gd.blank()

        # Initialize HUD from persistent state
        if self._huds:
            gd.comment('Initialize HUD')
            gd.line('$HUD.update_label("lives", SceneManager.get_state("lives", 5))')
            gd.line('$HUD.update_label("coins", SceneManager.get_state("coins", 0))')
            gd.line('$HUD.update_label("score", SceneManager.get_state("score", 0))')
            gd.line('$HUD.update_label("yoshi_coins", SceneManager.get_state("yoshi_coins", 0))')
            # Find time_left state var
            time_val = 300
            for sv in self._state_vars:
                if sv['name'] == 'time_left':
                    time_val = sv['value']
                    break
            gd.line(f'$HUD.set_time({time_val})')
            gd.blank()

        # Event listeners — register all handlers
        all_events = set()
        gd.comment('Event listeners')
        for evt in self._events:
            evt_name = evt['name']
            all_events.add(evt_name)
            func_name = f'_on_{_sanitize_name(evt_name)}'
            gd.line(f'QuantumEventBus.listen("{evt_name}", Callable(self, "{func_name}"))')

        # Register sound-only triggers (events not already registered)
        for trigger_event in sound_triggers:
            if trigger_event not in all_events and trigger_event != 'player.jump':
                func_name = f'_on_{_sanitize_name(trigger_event)}'
                gd.line(f'QuantumEventBus.listen("{trigger_event}", Callable(self, "{func_name}"))')
                all_events.add(trigger_event)
        gd.blank()

        # Timer connections
        for timer in self._timers:
            gd.line(f'${timer["id"]}.timeout.connect(Callable(self, "{timer["action"]}"))')

        # Tweens
        if self._tweens:
            gd.blank()
            gd.comment('Tweens')
            for tw in self._tweens:
                if tw['auto_start']:
                    target = tw['target']
                    prop = _quantum_prop_to_godot(tw['property'])
                    to_val = tw['to_value']
                    dur = tw['duration']
                    ease = EASING_MAP.get(tw['easing'], 'Tween.EASE_IN_OUT')
                    trans = TRANS_MAP.get(tw['easing'], 'Tween.TRANS_LINEAR')
                    gd.line(f'var tween_{tw["id"]} = create_tween()')
                    gd.line(f'tween_{tw["id"]}.tween_property(${target}, "{prop}", {to_val}, {dur}).set_ease({ease}).set_trans({trans})')
                    if tw['loop']:
                        gd.line(f'tween_{tw["id"]}.set_loops()')

        # Start BGM
        if bgm_sounds:
            gd.blank()
            gd.comment('Start background music')
            for bgm_id in bgm_sounds:
                gd.line(f'_play_sound("{bgm_id}")')

        gd.func_close()

        # User functions
        for func in self._functions:
            gd.blank()
            self._emit_function(gd, func)

        # ---- Auto-generated event handler functions ----

        for evt in self._events:
            evt_name = evt['name']
            func_name = f'_on_{_sanitize_name(evt_name)}'
            handler_name = evt.get('handler', '')
            actions = evt.get('actions', [])
            transitions = evt.get('transitions', [])
            trigger_sounds = sound_triggers.get(evt_name, [])

            gd.blank()
            gd.func(func_name, '_data = null')

            # --- Special handler: enemy-collision ---
            if handler_name == 'onEnemyCollision' or evt_name == 'enemy-collision':
                gd.line('if isDead: return')
                gd.line('var normal_y = _data.get("normal_y", 0) if _data else 0')
                gd.line('var other = _data.get("other") if _data else null')
                gd.if_block('normal_y < -0.5 and other and other.has_method("stomp")')
                gd.line('other.stomp()')
                if player_id:
                    gd.line(f'if {_gd_node_ref(player_id)}.has_method("stomp_bounce"):')
                    gd.line(f'\t{_gd_node_ref(player_id)}.stomp_bounce(-200)')
                    gd.line(f'else:')
                    gd.line(f'\t{_gd_node_ref(player_id)}.velocity.y = -200')
                for sid in sound_triggers.get('enemy-stomped', []):
                    gd.line(f'_play_sound("{sid}")')
                gd.else_block()
                gd.line('_die()')
                gd.block_close()

            # --- Special handler: fell-in-pit ---
            elif handler_name == 'onFellInPit' or evt_name == 'fell-in-pit':
                gd.line('_die()')

            # --- Special handler: block-hit ---
            elif handler_name == 'onBlockHit' or evt_name == 'block-hit':
                for sid in trigger_sounds:
                    gd.line(f'_play_sound("{sid}")')
                if not trigger_sounds:
                    gd.line('pass')

            # --- Generic event with actions/transitions ---
            else:
                # Play associated sounds
                for sid in trigger_sounds:
                    gd.line(f'_play_sound("{sid}")')

                # Execute inline actions
                for action in actions:
                    atype = action.get('action_type', '')
                    if atype == 'score':
                        amount = action.get('amount', 0)
                        gd.line(f'SceneManager.set_state("score", SceneManager.get_state("score", 0) + {amount})')
                        if self._huds:
                            gd.line('$HUD.update_label("score", SceneManager.get_state("score", 0))')
                    elif atype == 'set':
                        target = action.get('target', '')
                        value = action.get('value', '')
                        # Handle {var+1} expressions
                        if value and '{' in str(value):
                            inner = str(value).strip('{}')
                            if '+' in inner:
                                parts = inner.split('+')
                                var_name = parts[0].strip()
                                increment = parts[1].strip()
                                gd.line(f'SceneManager.set_state("{target}", SceneManager.get_state("{var_name}", 0) + {increment})')
                            else:
                                gd.line(f'SceneManager.set_state("{target}", {inner})')
                        else:
                            gd.line(f'SceneManager.set_state("{target}", {value})')
                        if self._huds and target in ('coins', 'lives', 'score', 'yoshi_coins', 'time_left'):
                            gd.line(f'$HUD.update_label("{target}", SceneManager.get_state("{target}", 0))')

                # Execute transitions
                for tr in transitions:
                    data_str = '{}'
                    if tr.get('data'):
                        pairs = ', '.join(f'"{k}": "{v}"' for k, v in tr['data'].items())
                        data_str = '{' + pairs + '}'
                    # Stop timer and music before transition
                    if self._huds:
                        gd.line('$HUD.stop_timer()')
                    for bgm_id in bgm_sounds:
                        gd.line(f'_stop_sound("{bgm_id}")')
                    gd.line(f'SceneManager.transition_to("{tr["to"]}", "{tr["effect"]}", {tr["duration"]}, {data_str})')

                if not trigger_sounds and not actions and not transitions:
                    gd.line('pass')

            gd.func_close()

        # Sound-only event handlers (for triggers not covered by events)
        for trigger_event, sound_ids in sound_triggers.items():
            if trigger_event not in {e['name'] for e in self._events} and trigger_event != 'player.jump':
                func_name = f'_on_{_sanitize_name(trigger_event)}'
                gd.blank()
                gd.func(func_name, '_data = null')
                for sid in sound_ids:
                    gd.line(f'_play_sound("{sid}")')
                gd.func_close()

        # _die() function
        if player_id:
            gd.blank()
            gd.func('_die')
            gd.line('if isDead: return')
            gd.assign('isDead', '1')
            if player_id:
                gd.line(f'{_gd_node_ref(player_id)}.die()')
            if self._huds:
                gd.line('$HUD.stop_timer()')
            # Play death sound
            for sid in sound_triggers.get('mario-died', []):
                gd.line(f'_play_sound("{sid}")')
            # Stop BGM
            for bgm_id in bgm_sounds:
                gd.line(f'_stop_sound("{bgm_id}")')
            # Wait and respawn
            gd.line(f'await get_tree().create_timer({death_timer}).timeout')
            gd.line('var lives = SceneManager.get_state("lives", 5) - 1')
            gd.line('SceneManager.set_state("lives", lives)')
            gd.if_block('lives <= 0')
            gd.line('QuantumEventBus.emit_event("game-over", {})')
            gd.else_block()
            gd.line('get_tree().reload_current_scene()')
            gd.block_close()
            gd.func_close()

        # _play_sound / _stop_sound helpers (use relative path within scene)
        gd.blank()
        gd.func('_play_sound', 'id: String')
        gd.line('var player = get_node_or_null("Sounds/" + id)')
        gd.line('if player: player.play()')
        gd.func_close()
        gd.blank()
        gd.func('_stop_sound', 'id: String')
        gd.line('var player = get_node_or_null("Sounds/" + id)')
        gd.line('if player: player.stop()')
        gd.func_close()

        return gd.build()

    def _build_map_scene_script(self, scene: SceneNode) -> str:
        """Generate a map scene GDScript with path-based navigation."""
        gd = GdScriptBuilder()
        gd.extends('Node2D')
        gd.blank()

        # Build map data dictionary
        gd.comment('Map data')
        nodes_dict_parts = []
        start_node = ''
        for mn in self._map_nodes:
            node_id = mn['id']
            if not start_node:
                start_node = node_id
            locked = 'true' if mn.get('locked') else 'false'
            scene_str = f'"{mn["scene"]}"' if mn.get('scene') else '""'
            nodes_dict_parts.append(
                f'"{node_id}": {{"x": {mn["x"]}, "y": {mn["y"]}, "scene": {scene_str}, "locked": {locked}}}'
            )
        nodes_str = ', '.join(nodes_dict_parts)
        gd.line(f'var map_nodes: Dictionary = {{{nodes_str}}}')
        gd.blank()

        paths_parts = []
        for mp in self._map_paths:
            unlock_str = f'"{mp["unlock"]}"' if mp.get('unlock') else '""'
            paths_parts.append(f'{{"from": "{mp["from"]}", "to": "{mp["to"]}", "unlock": {unlock_str}}}')
        paths_str = ', '.join(paths_parts)
        gd.line(f'var map_paths: Array = [{paths_str}]')
        gd.blank()

        gd.line(f'var current_node: String = "{start_node}"')
        gd.line('var _mario_sprite: Sprite2D')
        gd.line('var _moving: bool = false')
        gd.blank()

        # _ready
        gd.func('_ready')
        gd.line(f'SceneManager.current_scene_name = "{scene.name}"')
        # Register sprites
        for sprite in self._sprites:
            sid = sprite['id']
            gd.line(f'QuantumBridge.register_sprite("{sid}", {_gd_node_ref(sid)})')
        gd.blank()
        gd.line('_mario_sprite = $Mario if has_node("Mario") else null')
        gd.line('if _mario_sprite and map_nodes.has(current_node):')
        gd.indent()
        gd.line('var node_info = map_nodes[current_node]')
        gd.line('_mario_sprite.position = Vector2(node_info["x"], node_info["y"])')
        gd.dedent()

        # Event listeners
        if self._events:
            gd.blank()
            for evt in self._events:
                handler = evt['handler']
                if handler:
                    gd.line(f'QuantumEventBus.listen("{evt["name"]}", Callable(self, "{handler}"))')
        gd.func_close()
        gd.blank()

        # _input for map navigation
        gd.func('_input', 'event: InputEvent')
        gd.line('if _moving:')
        gd.indent()
        gd.line('return')
        gd.dedent()
        gd.line('if event.is_action_pressed("ui_accept"):')
        gd.indent()
        gd.line('_enter_node()')
        gd.dedent()
        gd.line('elif event.is_action_pressed("ui_right"):')
        gd.indent()
        gd.line('_try_move("right")')
        gd.dedent()
        gd.line('elif event.is_action_pressed("ui_left"):')
        gd.indent()
        gd.line('_try_move("left")')
        gd.dedent()
        gd.line('elif event.is_action_pressed("ui_up"):')
        gd.indent()
        gd.line('_try_move("up")')
        gd.dedent()
        gd.line('elif event.is_action_pressed("ui_down"):')
        gd.indent()
        gd.line('_try_move("down")')
        gd.dedent()
        gd.func_close()
        gd.blank()

        # _enter_node
        gd.func('_enter_node')
        gd.line('var node_info = map_nodes.get(current_node, {})')
        gd.line('var scene_name = node_info.get("scene", "")')
        gd.line('if scene_name != "" and not node_info.get("locked", false):')
        gd.indent()
        gd.line('SceneManager.transition_to(scene_name, "iris-in", 0.5)')
        gd.dedent()
        gd.func_close()
        gd.blank()

        # _try_move
        gd.func('_try_move', 'direction: String')
        gd.line('var neighbors = _get_neighbors(current_node)')
        gd.line('var best_node = ""')
        gd.line('var best_dist = INF')
        gd.line('var current_pos = _get_node_pos(current_node)')
        gd.line('for neighbor in neighbors:')
        gd.indent()
        gd.line('var neighbor_pos = _get_node_pos(neighbor)')
        gd.line('var delta = neighbor_pos - current_pos')
        gd.line('var valid = false')
        gd.line('match direction:')
        gd.indent()
        gd.line('"right": valid = delta.x > 0 and abs(delta.x) >= abs(delta.y)')
        gd.line('"left": valid = delta.x < 0 and abs(delta.x) >= abs(delta.y)')
        gd.line('"up": valid = delta.y < 0 and abs(delta.y) >= abs(delta.x)')
        gd.line('"down": valid = delta.y > 0 and abs(delta.y) >= abs(delta.x)')
        gd.dedent()
        gd.line('if valid:')
        gd.indent()
        gd.line('var dist = delta.length()')
        gd.line('if dist < best_dist:')
        gd.indent()
        gd.line('best_dist = dist')
        gd.line('best_node = neighbor')
        gd.dedent()
        gd.dedent()
        gd.dedent()
        gd.line('if best_node != "":')
        gd.indent()
        gd.line('_move_to(best_node)')
        gd.dedent()
        gd.func_close()
        gd.blank()

        # _move_to
        gd.func('_move_to', 'target_node: String')
        gd.line('_moving = true')
        gd.line('var target_pos = _get_node_pos(target_node)')
        gd.line('if _mario_sprite:')
        gd.indent()
        gd.line('var tween = create_tween()')
        gd.line('tween.tween_property(_mario_sprite, "position", target_pos, 0.2)')
        gd.line('await tween.finished')
        gd.dedent()
        gd.line('current_node = target_node')
        gd.line('_moving = false')
        gd.func_close()
        gd.blank()

        # _get_neighbors
        gd.func('_get_neighbors', 'node_id: String')
        gd.line('var neighbors = []')
        gd.line('for path in map_paths:')
        gd.indent()
        gd.line('var unlocked = true')
        gd.line('if path.has("unlock") and path["unlock"] != "":')
        gd.indent()
        gd.line('unlocked = SceneManager.get_state(path["unlock"], false)')
        gd.dedent()
        gd.line('if not unlocked:')
        gd.indent()
        gd.line('continue')
        gd.dedent()
        gd.line('if path["from"] == node_id:')
        gd.indent()
        gd.line('neighbors.append(path["to"])')
        gd.dedent()
        gd.line('elif path["to"] == node_id:')
        gd.indent()
        gd.line('neighbors.append(path["from"])')
        gd.dedent()
        gd.dedent()
        gd.line('return neighbors')
        gd.func_close()
        gd.blank()

        # _get_node_pos
        gd.func('_get_node_pos', 'node_id: String')
        gd.line('if map_nodes.has(node_id):')
        gd.indent()
        gd.line('var info = map_nodes[node_id]')
        gd.line('return Vector2(info["x"], info["y"])')
        gd.dedent()
        gd.line('return Vector2.ZERO')
        gd.func_close()

        # User functions
        for func in self._functions:
            gd.blank()
            self._emit_function(gd, func)

        return gd.build()

    # ------------------------------------------------------------------
    # AST Walking
    # ------------------------------------------------------------------

    def _process_scene_children(self, children: List[QuantumNode]):
        """Walk scene children and collect data for generation."""
        for child in children:
            self._process_node(child)

    def _process_node(self, node: QuantumNode):
        """Process a single AST node."""
        if isinstance(node, SpriteNode):
            self._process_sprite(node)
        elif isinstance(node, PhysicsNode):
            self._process_physics(node)
        elif isinstance(node, CameraNode):
            self._process_camera(node)
        elif isinstance(node, InputNode):
            self._process_input(node)
        elif isinstance(node, SoundNode):
            self._process_sound(node)
        elif isinstance(node, ParticleNode):
            self._process_particle(node)
        elif isinstance(node, TimerNode):
            self._process_timer(node)
        elif isinstance(node, TweenNode):
            self._process_tween(node)
        elif isinstance(node, HudNode):
            self._process_hud(node)
        elif isinstance(node, TilemapNode):
            self._process_tilemap(node)
        elif isinstance(node, SpawnNode):
            self._process_spawn(node)
        elif isinstance(node, PrefabNode):
            self._prefabs[node.name] = node
        elif isinstance(node, EnemyNode):
            self._enemies.append(node)
        elif isinstance(node, InstanceNode):
            self._process_instance(node)
        elif isinstance(node, GroupNode):
            self._process_group(node)
        elif isinstance(node, SetNode):
            self._process_set(node)
        elif isinstance(node, FunctionNode):
            self._functions.append(node)
        elif isinstance(node, EventNode):
            self._process_event(node)
        elif isinstance(node, BehaviorNode):
            self._behaviors[node.name] = node
        elif isinstance(node, MapNodeDef):
            self._map_nodes.append({
                'id': node.node_id,
                'x': node.x,
                'y': node.y,
                'scene': node.scene,
                'locked': node.locked,
                'icon': node.icon,
            })
            if node.icon:
                self._assets.add(node.icon)
        elif isinstance(node, MapPathNode):
            self._map_paths.append({
                'from': node.from_node,
                'to': node.to_node,
                'unlock': node.unlock,
                'direction': node.direction,
            })

    def _process_sprite(self, node: SpriteNode):
        """Collect sprite data."""
        sprite_data = {
            'id': node.sprite_id,
            'src': node.src,
            'x': node.x,
            'y': node.y,
            'width': node.width,
            'height': node.height,
            'anchor_x': node.anchor_x,
            'anchor_y': node.anchor_y,
            'rotation': node.rotation,
            'scale_x': node.scale_x,
            'scale_y': node.scale_y,
            'alpha': node.alpha,
            'visible': node.visible,
            'color': node.color,
            'tag': node.tag,
            'layer': node.layer,
            'frame_width': node.frame_width,
            'frame_height': node.frame_height,
            'body': node.body,
            'shape': node.shape,
            'bounce': node.bounce,
            'friction': node.friction,
            'mass': node.mass,
            'sensor': node.sensor,
            'controls': node.controls,
            'speed': node.speed,
            'jump_force': node.jump_force,
            'gravity_up': node.gravity_up,
            'gravity_down': node.gravity_down,
            'jump_hold_boost': node.jump_hold_boost,
            'coyote_frames': node.coyote_frames,
            'max_fall_speed': node.max_fall_speed,
            'collision_layer': node.collision_layer,
            'collision_mask': node.collision_mask,
            'floor_max_angle': node.floor_max_angle,
            'spin_jump': getattr(node, 'spin_jump', False),
            'animations': [],
            'colliders': [],
            'on_collisions': [],
            'behaviors': [],
            'children': [],
        }

        if node.src:
            self._assets.add(node.src)

        # Process sprite children
        for child in node.children:
            if isinstance(child, AnimationNode):
                sprite_data['animations'].append({
                    'name': child.name,
                    'frames': child.frames,
                    'speed': child.speed,
                    'loop': child.loop,
                    'auto_play': child.auto_play,
                })
            elif isinstance(child, ColliderNode):
                sprite_data['colliders'].append({
                    'shape': child.shape,
                    'width': child.width,
                    'height': child.height,
                    'radius': child.radius,
                    'offset_x': child.offset_x,
                    'offset_y': child.offset_y,
                })
            elif isinstance(child, OnCollisionNode):
                sprite_data['on_collisions'].append({
                    'with_tag': child.with_tag,
                    'with_id': child.with_id,
                    'action': child.action,
                })
            elif isinstance(child, UseNode):
                sprite_data['behaviors'].append({
                    'behavior': child.behavior,
                    'overrides': child.overrides,
                })
            elif isinstance(child, ClickableNode):
                sprite_data['children'].append({'type': 'clickable', 'action': child.action})
            else:
                sprite_data['children'].append(child)

        self._sprites.append(sprite_data)

    def _process_physics(self, node: PhysicsNode):
        self._physics = {
            'gravity_x': node.gravity_x,
            'gravity_y': node.gravity_y,
            'bounds': node.bounds,
            'debug': node.debug,
            'collision_layers': node.collision_layers,
        }

    def _process_camera(self, node: CameraNode):
        self._camera = {
            'follow': node.follow,
            'lerp': node.lerp,
            'bounds': node.bounds,
            'zoom': node.zoom,
            'offset_x': node.offset_x,
            'offset_y': node.offset_y,
        }

    def _process_input(self, node: InputNode):
        self._custom_inputs.append({
            'key': node.key,
            'action': node.action,
            'type': node.input_type,
        })

    def _process_sound(self, node: SoundNode):
        self._sounds.append({
            'id': node.sound_id,
            'src': node.src,
            'volume': node.volume,
            'loop': node.loop,
            'trigger': node.trigger,
            'channel': node.channel,
        })
        if node.src:
            self._assets.add(node.src)

    def _process_particle(self, node: ParticleNode):
        self._particles.append({
            'id': node.particle_id,
            'src': node.src,
            'follow': node.follow,
            'trigger': node.trigger,
            'count': node.count,
            'emit_rate': node.emit_rate,
            'lifetime': node.lifetime,
            'speed_min': node.speed_min,
            'speed_max': node.speed_max,
            'angle_min': node.angle_min,
            'angle_max': node.angle_max,
            'alpha_start': node.alpha_start,
            'alpha_end': node.alpha_end,
        })

    def _process_timer(self, node: TimerNode):
        self._timers.append({
            'id': node.timer_id,
            'interval': node.interval,
            'repeat': node.repeat,
            'auto_start': node.auto_start,
            'action': node.action,
        })

    def _process_tween(self, node: TweenNode):
        self._tweens.append({
            'id': node.tween_id,
            'target': node.target,
            'property': node.property,
            'to_value': node.to_value,
            'duration': node.duration,
            'easing': node.easing,
            'loop': node.loop,
            'yoyo': node.yoyo,
            'delay': node.delay,
            'auto_start': node.auto_start,
        })

    def _process_hud(self, node: HudNode):
        hud_data = {
            'position': node.position,
            'background': node.background,
            'background_height': node.background_height,
            'sprite_prefix': node.sprite_prefix,
            'children': [],
            'tiles': [],
            'counters': [],
            'collections': [],
            'slots': [],
            'behaviors': [],
        }
        for child in node.children:
            if isinstance(child, HudTileNode):
                sprite_path = self._resolve_hud_sprite(child.sprite, node.sprite_prefix)
                self._assets.add(sprite_path)
                hud_data['tiles'].append({
                    'sprite': sprite_path,
                    'x': child.x,
                    'y': child.y,
                    'width': child.width,
                    'height': child.height,
                })
            elif isinstance(child, HudCounterNode):
                strip_path = self._resolve_hud_sprite(child.strip, node.sprite_prefix)
                self._assets.add(strip_path)
                counter_data = {
                    'strip': strip_path,
                    'x': child.x,
                    'y': child.y,
                    'digits': child.digits,
                    'bind': self._strip_bind(child.bind),
                    'digit_width': child.digit_width,
                    'digit_height': child.digit_height,
                    'countdown': child.countdown,
                    'hurry_at': child.hurry_at,
                    'flash': child.flash,
                    'align': child.align,
                    'right_edge': child.right_edge,
                    'tint': child.tint,
                    'intelligent': child.intelligent,
                    'extra_life_at': child.extra_life_at,
                }
                if child.icon:
                    icon_path = self._resolve_hud_sprite(child.icon, node.sprite_prefix)
                    self._assets.add(icon_path)
                    counter_data['icon'] = icon_path
                if child.symbol:
                    symbol_path = self._resolve_hud_sprite(child.symbol, node.sprite_prefix)
                    self._assets.add(symbol_path)
                    counter_data['symbol'] = symbol_path
                hud_data['counters'].append(counter_data)
            elif isinstance(child, HudCollectionNode):
                sprite_path = self._resolve_hud_sprite(child.sprite, node.sprite_prefix)
                self._assets.add(sprite_path)
                hud_data['collections'].append({
                    'sprite': sprite_path,
                    'x': child.x,
                    'y': child.y,
                    'spacing': child.spacing,
                    'max': child.max,
                    'bind': self._strip_bind(child.bind),
                })
            elif isinstance(child, HudSlotNode):
                slot_data = {
                    'x': child.x,
                    'y': child.y,
                    'bind': self._strip_bind(child.bind),
                    'options': [],
                }
                for opt in child.options:
                    opt_sprite = self._resolve_hud_sprite(opt.sprite, node.sprite_prefix)
                    self._assets.add(opt_sprite)
                    slot_data['options'].append({
                        'value': opt.value,
                        'sprite': opt_sprite,
                    })
                hud_data['slots'].append(slot_data)
            elif isinstance(child, HudBehaviorNode):
                behavior_data = {
                    'target': child.target,
                    'event': child.event,
                    'value': child.value,
                    'actions': [],
                }
                for action in child.actions:
                    behavior_data['actions'].append({
                        'action_type': action.action_type,
                        'event': action.event,
                        'rate': action.rate,
                    })
                hud_data['behaviors'].append(behavior_data)
            elif isinstance(child, HTMLNode):
                hud_data['children'].append({
                    'type': 'html',
                    'tag': child.tag,
                    'attrs': child.attributes,
                    'children': child.children,
                })
            elif isinstance(child, TextNode):
                hud_data['children'].append({
                    'type': 'text',
                    'content': child.content,
                })
        self._huds.append(hud_data)

    def _has_tile_hud(self) -> bool:
        """Check if any HUD uses tile-based mode."""
        for hud in self._huds:
            if hud.get('tiles') or hud.get('counters') or hud.get('collections') or hud.get('slots'):
                return True
        return False

    def _resolve_hud_sprite(self, sprite: str, prefix: Optional[str]) -> str:
        """Resolve sprite name with prefix. Paths with '/' are used literally."""
        if not sprite:
            return sprite
        if '/' in sprite:
            return sprite
        if prefix:
            return prefix + sprite
        return sprite

    def _strip_bind(self, bind: str) -> str:
        """Strip curly braces from bind expression: '{coins}' -> 'coins'."""
        if bind.startswith('{') and bind.endswith('}'):
            return bind[1:-1]
        return bind

    def _sprite_var_name(self, path: str) -> str:
        """Convert sprite path to a GDScript variable name."""
        name = path.replace('/', '_').replace('.', '_').replace('-', '_')
        if name.startswith('_'):
            name = 'tex' + name
        return name

    def _parse_rgba(self, rgba_str: str) -> str:
        """Parse 'rgba(r,g,b,a)' to Godot Color(r,g,b,a) format."""
        if not rgba_str:
            return 'Color(0, 0, 0, 0.5)'
        s = rgba_str.strip()
        if s.startswith('rgba(') and s.endswith(')'):
            parts = s[5:-1].split(',')
            if len(parts) == 4:
                r = float(parts[0].strip()) / 255.0
                g = float(parts[1].strip()) / 255.0
                b = float(parts[2].strip()) / 255.0
                a = float(parts[3].strip())
                return f'Color({r:.3f}, {g:.3f}, {b:.3f}, {a})'
        if s.startswith('rgb(') and s.endswith(')'):
            parts = s[4:-1].split(',')
            if len(parts) == 3:
                r = float(parts[0].strip()) / 255.0
                g = float(parts[1].strip()) / 255.0
                b = float(parts[2].strip()) / 255.0
                return f'Color({r:.3f}, {g:.3f}, {b:.3f}, 1.0)'
        return 'Color(0, 0, 0, 0.5)'

    def _flash_color(self, color_name: Optional[str]) -> str:
        """Convert flash color name to Godot Color."""
        colors = {
            'red': 'Color(1, 0.2, 0.2, 1)',
            'yellow': 'Color(1, 1, 0, 1)',
            'white': 'Color(1, 1, 1, 1)',
            'blue': 'Color(0.2, 0.4, 1, 1)',
        }
        return colors.get(color_name, 'Color(1, 0.2, 0.2, 1)')

    def _process_tilemap(self, node: TilemapNode):
        tilemap_data = {
            'id': node.tilemap_id,
            'src': node.src,
            'data_src': node.data_src,
            'tile_width': node.tile_width,
            'tile_height': node.tile_height,
            'layers': [],
            'tile_animations': [],
        }
        if node.src:
            self._assets.add(node.src)
        if node.data_src:
            self._assets.add(node.data_src)

        for layer in node.layers:
            tilemap_data['layers'].append({
                'name': layer.name,
                'data': layer.data,
                'collision': layer.collision,
            })

        for anim in node.tile_animations:
            tilemap_data['tile_animations'].append({
                'tile_id': anim.tile_id,
                'frames': anim.frames,
                'speed': anim.speed,
            })

        self._tilemaps.append(tilemap_data)

    def _process_spawn(self, node: SpawnNode):
        self._spawners.append({
            'id': node.spawn_id,
            'prefab': node.prefab,
            'count': node.count,
            'interval': node.interval,
            'x': node.x,
            'y': node.y,
            'pool_size': node.pool_size,
        })

    def _process_instance(self, node: InstanceNode):
        self._instances.append({
            'prefab': node.prefab,
            'id': node.instance_id,
            'x': node.x,
            'y': node.y,
            'overrides': node.overrides,
        })

    def _process_group(self, node: GroupNode):
        group_data = {
            'name': node.name,
            'tag': node.tag,
            'children': [],
        }
        for child in node.children:
            if isinstance(child, SpriteNode):
                self._process_sprite(child)
                group_data['children'].append(child.sprite_id)
            elif isinstance(child, InstanceNode):
                self._process_instance(child)
                group_data['children'].append(child.instance_id or child.prefab)
            else:
                self._process_node(child)
        self._groups.append(group_data)

    def _process_set(self, node: SetNode):
        val = node.value
        val_type = 'String'
        if val is None or val == '':
            val_type = 'Variant'
            val = 'null'
        elif isinstance(val, bool):
            val_type = 'bool'
            val = gd_bool(val)
        elif isinstance(val, int):
            val_type = 'int'
            val = str(val)
        elif isinstance(val, float):
            val_type = 'float'
            val = str(val)
        elif isinstance(val, str):
            # Try to detect numbers
            try:
                int(val)
                val_type = 'int'
            except ValueError:
                try:
                    float(val)
                    val_type = 'float'
                except ValueError:
                    if val.lower() in ('true', 'false'):
                        val_type = 'bool'
                        val = val.lower()
                    else:
                        val_type = 'String'
                        val = gd_string(val)

        self._state_vars.append({
            'name': node.name,
            'value': val,
            'type': val_type,
        })

    def _process_event(self, node: EventNode):
        # Extract scene transitions and event actions from inline children
        transitions = []
        actions = []
        for child in getattr(node, 'children', []):
            if isinstance(child, SceneTransitionNode):
                transitions.append({
                    'to': child.to,
                    'effect': child.effect,
                    'duration': child.duration,
                    'data': child.data,
                })
            elif isinstance(child, EventActionNode):
                actions.append({
                    'action_type': child.action_type,
                    'target': child.target,
                    'value': child.value,
                    'amount': child.amount,
                })
        self._events.append({
            'name': node.name,
            'handler': node.handler,
            'filter_tag': node.filter_tag,
            'filter_id': node.filter_id,
            'scope': node.scope,
            'transitions': transitions,
            'actions': actions,
        })

    def _resolve_collision_value(self, raw_value) -> int:
        """Resolve a collision layer/mask value.

        Supports:
        - int: direct bitmask value
        - str: single named layer or comma-separated names
        Returns an int bitmask.
        """
        if raw_value is None:
            return 1
        if isinstance(raw_value, int):
            return raw_value
        if isinstance(raw_value, str):
            collision_layers = {}
            if self._physics and self._physics.get('collision_layers'):
                collision_layers = self._physics['collision_layers']
            # Could be comma-separated names like "world,enemies"
            result = 0
            for part in raw_value.split(','):
                name = part.strip()
                if name in collision_layers:
                    result |= collision_layers[name]
                else:
                    # Try parsing as int
                    try:
                        result |= int(name)
                    except ValueError:
                        pass  # Unknown layer name, skip
            return result if result > 0 else 1
        return 1

    # ------------------------------------------------------------------
    # File Generation
    # ------------------------------------------------------------------

    def _write_project_godot(self, out: Path, scene: SceneNode, project_name: str):
        """Generate and write project.godot."""
        gravity_y = SMW_GRAVITY
        if self._physics:
            # Use SNES gravity as default, ignore Quantum abstract gravity
            pass

        # Build input map
        input_map = self._build_input_map()

        # Build collision layer names
        collision_layer_names = {}
        if self._physics and self._physics.get('collision_layers'):
            collision_layer_names = self._physics['collision_layers']

        config = {
            'name': project_name,
            'main_scene': 'main.tscn',
            'viewport_width': scene.viewport_width or SNES_WIDTH,
            'viewport_height': scene.viewport_height or SNES_HEIGHT,
            'gravity': gravity_y,
            'input_map': input_map,
            'autoloads': {
                'QuantumBridge': 'scripts/quantum_bridge.gd',
                'QuantumEventBus': 'scripts/quantum_event_bus.gd',
            },
            'collision_layer_names': collision_layer_names,
        }
        content = build_project_godot(config)
        (out / 'project.godot').write_text(content, encoding='utf-8')

    def _build_input_map(self) -> Dict[str, List[str]]:
        """Build input action map from sprites with controls + custom inputs."""
        input_map = {}

        # Check if any sprite has controls
        has_controls = any(s.get('controls') for s in self._sprites)
        if has_controls:
            input_map['move_left'] = ['ArrowLeft', 'a']
            input_map['move_right'] = ['ArrowRight', 'd']
            input_map['jump'] = ['Space', 'ArrowUp', 'w']
            input_map['move_down'] = ['ArrowDown', 's']

        # Custom inputs
        for inp in self._custom_inputs:
            action = inp['action']
            key = inp['key']
            if action not in input_map:
                input_map[action] = []
            input_map[action].append(key)

        return input_map

    def _write_autoload_scripts(self, scripts_dir: Path):
        """Write autoload scripts (bridge, event bus)."""
        (scripts_dir / 'quantum_bridge.gd').write_text(
            QUANTUM_BRIDGE_GD, encoding='utf-8'
        )
        (scripts_dir / 'quantum_event_bus.gd').write_text(
            QUANTUM_EVENT_BUS_GD, encoding='utf-8'
        )

    def _write_main_scene(self, out: Path, scripts_dir: Path, scene: SceneNode):
        """Generate the main .tscn scene and its script."""
        tscn = TscnBuilder()
        script_path = 'scripts/scene_main.gd'

        # Root node: Node2D with script
        tscn.add_node_with_script('Main', 'Node2D', script_path=script_path)

        # Background color (ColorRect) — sized to world, not viewport
        bg = scene.background or '#000000'
        tscn.add_node('Background', 'ColorRect', parent='.', properties={
            'offset_right': float(scene.width),
            'offset_bottom': float(scene.height),
            'color': gd_color(bg),
        })

        # Sprites
        node_index = 0
        for sprite in self._sprites:
            self._add_sprite_to_tscn(tscn, sprite, parent='.')
            node_index += 1

        # Tilemaps
        for tilemap in self._tilemaps:
            self._add_tilemap_to_tscn(tscn, tilemap, parent='.')

        # Camera
        if self._camera:
            self._add_camera_to_tscn(tscn)

        # Sounds container
        if self._sounds:
            tscn.add_node('Sounds', 'Node', parent='.')
            for sound in self._sounds:
                props = {}
                if sound['volume'] != 1.0:
                    import math
                    props['volume_db'] = 20 * math.log10(max(sound['volume'], 0.001))
                if sound['loop']:
                    pass  # Loop is set on the AudioStream, not the player
                src = sound['src']
                if src:
                    res_id = tscn.add_ext_resource('AudioStream', _asset_path(src))
                    props['stream'] = f'ExtResource("{res_id}")'
                tscn.add_node(sound['id'], 'AudioStreamPlayer', parent='Sounds', properties=props)

        # Particles
        for particle in self._particles:
            self._add_particle_to_tscn(tscn, particle, parent='.')

        # Timers
        for timer in self._timers:
            props = {
                'wait_time': timer['interval'],
                'one_shot': timer['repeat'] == 1,
                'autostart': timer['auto_start'],
            }
            tscn.add_node(timer['id'], 'Timer', parent='.', properties=props)

        # HUD
        if self._huds:
            self._add_hud_to_tscn(tscn)

        # Instances (of prefabs)
        for inst in self._instances:
            self._add_instance_to_tscn(tscn, inst, parent='.')

        # Write .tscn
        tscn_content = tscn.build()
        (out / 'main.tscn').write_text(tscn_content, encoding='utf-8')

        # Write scene script
        script = self._build_scene_script(scene)
        (scripts_dir / 'scene_main.gd').write_text(script, encoding='utf-8')

    def _add_sprite_to_tscn(self, tscn: TscnBuilder, sprite: Dict, parent: str):
        """Add a sprite node to the TSCN."""
        sid = sprite['id'] or 'Sprite'
        body = sprite.get('body')
        sensor = sprite.get('sensor', False)
        controls = sprite.get('controls')
        has_animations = bool(sprite.get('animations'))
        tag = sprite.get('tag')

        x = float(sprite['x'])
        y = float(sprite['y'])

        # Base metadata — tag for collision dispatch
        meta = {}
        if tag:
            meta['metadata/tag'] = tag  # TscnBuilder auto-quotes strings

        if sensor:
            # Area2D for sensors
            node_type = 'Area2D'
            props = {'position': gd_vector2(x, y), **meta}
            tscn.add_node(sid, node_type, parent=parent, properties=props)
            self._add_collision_shape(tscn, sprite, parent=_node_path(parent, sid))
            self._add_sprite_visual(tscn, sprite, parent=_node_path(parent, sid))

        elif body == 'dynamic' and controls:
            # CharacterBody2D with player controller
            node_type = 'CharacterBody2D'
            props = {'position': gd_vector2(x, y), **meta}
            tscn.add_node_with_script(
                sid, node_type, script_path='scripts/player_controller.gd',
                parent=parent, properties=props
            )
            self._add_collision_shape(tscn, sprite, parent=_node_path(parent, sid))
            self._add_sprite_visual(tscn, sprite, parent=_node_path(parent, sid),
                                    has_animations=has_animations)

        elif body == 'dynamic':
            # CharacterBody2D without controls
            node_type = 'CharacterBody2D'
            props = {'position': gd_vector2(x, y), **meta}
            # Check if it has patrol/AI behavior
            has_patrol = False
            for beh in sprite.get('behaviors', []):
                bname = beh['behavior']
                if bname in self._behaviors:
                    # Check for patrol-like behavior
                    has_patrol = True
            if has_patrol or sprite.get('tag') in ('enemy',):
                tscn.add_node_with_script(
                    sid, node_type, script_path=f'scripts/patrol_ai.gd',
                    parent=parent, properties=props
                )
            else:
                tscn.add_node(sid, node_type, parent=parent, properties=props)
            self._add_collision_shape(tscn, sprite, parent=_node_path(parent, sid))
            self._add_sprite_visual(tscn, sprite, parent=_node_path(parent, sid),
                                    has_animations=has_animations)

        elif body == 'static':
            # StaticBody2D
            node_type = 'StaticBody2D'
            props = {'position': gd_vector2(x, y), **meta}
            tscn.add_node(sid, node_type, parent=parent, properties=props)
            self._add_collision_shape(tscn, sprite, parent=_node_path(parent, sid))
            self._add_sprite_visual(tscn, sprite, parent=_node_path(parent, sid))

        else:
            # Pure visual: Sprite2D or AnimatedSprite2D
            if has_animations:
                props = {'position': gd_vector2(x, y)}
                tscn.add_node(sid, 'AnimatedSprite2D', parent=parent, properties=props)
            else:
                props = {'position': gd_vector2(x, y)}
                if sprite['src']:
                    res_id = tscn.add_ext_resource('Texture2D', _asset_path(sprite['src']))
                    props['texture'] = f'ExtResource("{res_id}")'
                if sprite['alpha'] != 1.0:
                    props['modulate'] = f'Color(1, 1, 1, {sprite["alpha"]})'
                if not sprite['visible']:
                    props['visible'] = False
                if sprite['scale_x'] != 1.0 or sprite['scale_y'] != 1.0:
                    props['scale'] = gd_vector2(sprite['scale_x'], sprite['scale_y'])
                if sprite['rotation'] != 0:
                    import math
                    props['rotation'] = sprite['rotation'] * math.pi / 180
                tscn.add_node(sid, 'Sprite2D', parent=parent, properties=props)

        # Add collision handlers as Area2D children if needed
        if sprite.get('on_collisions') and not sensor:
            area_parent = _node_path(parent, sid)
            tscn.add_node(f'{sid}_area', 'Area2D', parent=area_parent)
            # Add collision shape to the area (slightly larger for generous detection)
            area_path = _node_path(area_parent, f'{sid}_area')
            w = sprite.get('width') or sprite.get('frame_width') or 32
            h = sprite.get('height') or sprite.get('frame_height') or 32
            shape_id = tscn.add_sub_resource('RectangleShape2D', {
                'size': gd_vector2(w, h),
            })
            tscn.add_node('CollisionShape2D', 'CollisionShape2D', parent=area_path, properties={
                'shape': shape_id,
            })

    def _add_collision_shape(self, tscn: TscnBuilder, sprite: Dict, parent: str):
        """Add a CollisionShape2D to a physics body."""
        colliders = sprite.get('colliders', [])
        if colliders:
            for i, col in enumerate(colliders):
                name = f'CollisionShape2D{"" if i == 0 else str(i)}'
                shape = col['shape']
                if shape == 'circle':
                    radius = col.get('radius') or (sprite.get('width') or 32) / 2
                    shape_id = tscn.add_sub_resource('CircleShape2D', {
                        'radius': float(radius),
                    })
                else:
                    w = col.get('width') or sprite.get('width') or 32
                    h = col.get('height') or sprite.get('height') or 32
                    shape_id = tscn.add_sub_resource('RectangleShape2D', {
                        'size': gd_vector2(w, h),
                    })
                props = {'shape': shape_id}
                if col.get('offset_x') or col.get('offset_y'):
                    props['position'] = gd_vector2(
                        col.get('offset_x', 0), col.get('offset_y', 0)
                    )
                tscn.add_node(name, 'CollisionShape2D', parent=parent, properties=props)
        else:
            # Default collision shape from sprite dimensions
            # Prefer frame_width/frame_height (actual sprite size) over width/height
            w = sprite.get('width') or sprite.get('frame_width') or 32
            h = sprite.get('height') or sprite.get('frame_height') or 32
            shape_type = sprite.get('shape', 'box')
            if shape_type == 'circle':
                shape_id = tscn.add_sub_resource('CircleShape2D', {
                    'radius': float(max(w, h)) / 2,
                })
            else:
                shape_id = tscn.add_sub_resource('RectangleShape2D', {
                    'size': gd_vector2(w, h),
                })
            tscn.add_node('CollisionShape2D', 'CollisionShape2D', parent=parent, properties={
                'shape': shape_id,
            })

    def _add_sprite_visual(self, tscn: TscnBuilder, sprite: Dict, parent: str,
                           has_animations: bool = False):
        """Add the visual representation (Sprite2D) inside a physics body."""
        if not sprite['src']:
            return

        res_id = tscn.add_ext_resource('Texture2D', _asset_path(sprite['src']))
        props = {'texture': f'ExtResource("{res_id}")'}

        if sprite['alpha'] != 1.0:
            props['modulate'] = f'Color(1, 1, 1, {sprite["alpha"]})'
        if sprite['scale_x'] != 1.0 or sprite['scale_y'] != 1.0:
            props['scale'] = gd_vector2(sprite['scale_x'], sprite['scale_y'])

        # Spritesheet slicing: compute hframes from actual texture size
        fw = sprite.get('frame_width')
        fh = sprite.get('frame_height')
        if fw and fh and fw > 0 and fh > 0:
            src_path = _asset_path(sprite['src'])
            tex_size = self._get_texture_size(src_path)
            if tex_size:
                tw, th = tex_size
                hf = max(1, tw // fw)
                vf = max(1, th // fh)
                props['hframes'] = hf
                props['vframes'] = vf

        tscn.add_node('Sprite2D', 'Sprite2D', parent=parent, properties=props)

    def _get_texture_size(self, asset_path: str) -> Optional[Tuple[int, int]]:
        """Get texture dimensions from actual image file on disk."""
        if not self._output_dir:
            return None
        full_path = self._output_dir / asset_path
        if not full_path.exists():
            return None
        try:
            from PIL import Image
            with Image.open(full_path) as img:
                return img.size
        except Exception:
            return None

    def _add_tilemap_to_tscn(self, tscn: TscnBuilder, tilemap: Dict, parent: str):
        """Add tilemap nodes to the TSCN."""
        tid = tilemap['id']
        tile_w = tilemap['tile_width']
        tile_h = tilemap['tile_height']

        if tilemap.get('data_src'):
            # External data mode: reference .tres tileset + loader script
            tileset_rid = None
            if tilemap['src']:
                tileset_rid = tscn.add_ext_resource('TileSet', _asset_path(tilemap['src']))
            for layer in tilemap['layers']:
                layer_name = f'{tid}_{layer["name"]}'
                props = {
                    'collision_enabled': layer.get('collision', False),
                    'z_index': -1,  # Render behind player/entities
                }
                if tileset_rid:
                    props['tile_set'] = f'ExtResource("{tileset_rid}")'
                tscn.add_node_with_script(
                    layer_name, 'TileMapLayer',
                    script_path='scripts/tilemap_loader.gd',
                    parent=parent, properties=props
                )
        else:
            # Inline CSV data mode (original behavior)
            if tilemap['src']:
                tscn.add_ext_resource('Texture2D', _asset_path(tilemap['src']))
            for layer in tilemap['layers']:
                layer_name = f'{tid}_{layer["name"]}'
                props = {}
                tscn.add_node(layer_name, 'TileMapLayer', parent=parent, properties=props)

    def _add_camera_to_tscn(self, tscn: TscnBuilder):
        """Add Camera2D node."""
        cam = self._camera
        props = {
            'zoom': gd_vector2(cam.get('zoom', 1.0), cam.get('zoom', 1.0)),
        }
        if cam.get('offset_x') or cam.get('offset_y'):
            # Scale camera offset proportionally to viewport height.
            # .q offset values were calibrated for ~480px PIXI viewport.
            # For SNES 224px viewport, scale down to avoid hiding ground.
            default_vp = 480.0  # PIXI default viewport height
            scale_factor = min(1.0, self._viewport_height / default_vp)
            offset_x = float(cam.get('offset_x', 0)) * scale_factor
            offset_y = float(cam.get('offset_y', 0)) * scale_factor
            props['offset'] = gd_vector2(offset_x, offset_y)

        follow_target = cam.get('follow')
        if follow_target:
            # Camera follows a sprite — attach as child of that sprite
            # Godot Camera2D inherits parent transform, so it auto-follows
            tscn.add_node_with_script(
                'Camera2D', 'Camera2D',
                script_path='scripts/camera_follow.gd',
                parent=follow_target, properties=props
            )
        else:
            tscn.add_node('Camera2D', 'Camera2D', parent='.', properties=props)

    def _add_particle_to_tscn(self, tscn: TscnBuilder, particle: Dict, parent: str):
        """Add GPUParticles2D node."""
        pid = particle['id']
        props = {
            'amount': particle.get('count', 20),
            'lifetime': particle.get('lifetime', 1.0),
            'emitting': False,  # Triggered by events
        }
        tscn.add_node(pid, 'GPUParticles2D', parent=parent, properties=props)

    def _add_hud_to_tscn(self, tscn: TscnBuilder):
        """Add HUD (CanvasLayer + Controls)."""
        tscn.add_node_with_script(
            'HUD', 'CanvasLayer',
            script_path='scripts/hud_manager.gd',
            parent='.'
        )

        if self._has_tile_hud():
            # Tile-based HUD: script handles all drawing, no Label children needed
            return

        # Legacy HTML-based HUD: create Label children
        label_index = 0
        for hud in self._huds:
            for child in hud.get('children', []):
                if child.get('type') == 'html':
                    tag = child.get('tag', 'div')
                    attrs = child.get('attrs', {})
                    label_name = attrs.get('id', f'label_{label_index}')
                    text = ''
                    for sub in child.get('children', []):
                        if isinstance(sub, TextNode):
                            text = sub.content
                        elif hasattr(sub, 'content'):
                            text = sub.content

                    props = {
                        'text': f'"{text}"' if text else '""',
                    }

                    # Position based on hud position
                    pos = hud.get('position', 'top-left')
                    margin = 10
                    if 'right' in pos:
                        props['offset_left'] = -200.0
                        props['offset_right'] = float(-margin)
                    else:
                        props['offset_left'] = float(margin)
                        props['offset_right'] = 200.0
                    if 'bottom' in pos:
                        props['offset_top'] = -40.0
                        props['offset_bottom'] = 0.0
                    else:
                        props['offset_top'] = float(margin)
                        props['offset_bottom'] = 40.0

                    tscn.add_node(label_name, 'Label', parent='HUD', properties=props)
                    label_index += 1

    def _add_instance_to_tscn(self, tscn: TscnBuilder, inst: Dict, parent: str):
        """Add an instantiated prefab to the TSCN."""
        prefab_name = inst['prefab']
        inst_id = inst.get('id') or f'{prefab_name}_{id(inst)}'
        x = float(inst['x'])
        y = float(inst['y'])

        # Reference the prefab scene
        res_id = tscn.add_ext_resource('PackedScene', f'prefabs/{prefab_name}.tscn')
        tscn.add_node(inst_id, '', parent=parent, properties={
            'position': gd_vector2(x, y),
        }, instance=f'ExtResource("{res_id}")')

    def _write_prefab_scenes(self, prefabs_dir: Path, scripts_dir: Path):
        """Generate .tscn files for each prefab."""
        for name, prefab in self._prefabs.items():
            tscn = TscnBuilder()

            # Determine root node type based on prefab semantics
            entity_type = prefab.entity_type
            movement = prefab.movement
            collectible = prefab.collectible
            body_type = self._get_prefab_body_type(prefab)

            # Get tag and animations from prefab's sprite child
            prefab_tag = None
            prefab_anims = []
            for child in prefab.children:
                if isinstance(child, SpriteNode):
                    if child.tag:
                        prefab_tag = child.tag
                    # Collect animations from sprite children
                    for anim_child in child.children:
                        if isinstance(anim_child, AnimationNode):
                            prefab_anims.append(anim_child)
            root_props = {}
            if prefab_tag:
                root_props['metadata/tag'] = prefab_tag  # TscnBuilder auto-quotes

            # Determine if this prefab needs a script
            has_enemy_ai = False
            has_animation = len(prefab_anims) > 0

            # Check if there's an EnemyNode for this prefab
            enemy_def = self._get_enemy_for_prefab(name)

            if body_type == 'dynamic':
                # Detect if entity needs patrol AI: explicit movement, enemy tag, or EnemyNode
                has_movement = movement and movement != 'none'
                has_enemy_tag = prefab_tag == 'enemy' or entity_type == 'enemy'
                has_enemy_ai = has_movement or has_enemy_tag or enemy_def is not None
                if has_enemy_ai:
                    # Enemy/moving entity — attach patrol script (includes animation)
                    script_name = f'prefab_{name}.gd'
                    tscn.add_node_with_script(
                        name, 'CharacterBody2D',
                        script_path=f'scripts/{script_name}',
                        properties=root_props
                    )
                    if enemy_def:
                        self._write_enemy_script(scripts_dir, name, prefab, enemy_def, prefab_anims)
                    else:
                        self._write_prefab_script(scripts_dir, name, prefab, prefab_anims)
                else:
                    tscn.add_node(name, 'CharacterBody2D', properties=root_props)
            elif body_type == 'static':
                # Detect qblock by tag even without explicit content/hits attrs
                is_qblock = prefab_tag == 'qblock'
                has_block_content = (prefab.content is not None or
                                    (prefab.hits is not None and prefab.hits > 0) or
                                    is_qblock)
                has_breakable = prefab.breakable

                is_flying = getattr(prefab, 'flying', False) or False
                if has_block_content and is_flying:
                    script_name = f'prefab_{name}.gd'
                    tscn.add_node_with_script(
                        name, 'StaticBody2D',
                        script_path=f'scripts/{script_name}',
                        properties=root_props
                    )
                    self._write_flying_block_script(scripts_dir, name, prefab, prefab_anims)
                elif has_block_content:
                    script_name = f'prefab_{name}.gd'
                    tscn.add_node_with_script(
                        name, 'StaticBody2D',
                        script_path=f'scripts/{script_name}',
                        properties=root_props
                    )
                    self._write_block_script(scripts_dir, name, prefab, prefab_anims)
                elif has_breakable:
                    script_name = f'prefab_{name}.gd'
                    tscn.add_node_with_script(
                        name, 'StaticBody2D',
                        script_path=f'scripts/{script_name}',
                        properties=root_props
                    )
                    self._write_breakable_block_script(scripts_dir, name, prefab, prefab_anims)
                elif has_animation:
                    script_name = f'prefab_{name}.gd'
                    tscn.add_node_with_script(
                        name, 'StaticBody2D',
                        script_path=f'scripts/{script_name}',
                        properties=root_props
                    )
                    self._write_animator_script(scripts_dir, name, 'StaticBody2D', prefab_anims)
                else:
                    tscn.add_node(name, 'StaticBody2D', properties=root_props)
            elif collectible or (entity_type in ('item', 'goal')) or prefab.checkpoint:
                has_collectible = prefab.collectible
                has_checkpoint = prefab.checkpoint

                if has_collectible:
                    script_name = f'prefab_{name}.gd'
                    tscn.add_node_with_script(
                        name, 'Area2D',
                        script_path=f'scripts/{script_name}',
                        properties=root_props
                    )
                    self._write_collectible_script(scripts_dir, name, prefab, prefab_tag, prefab_anims)
                elif has_checkpoint:
                    script_name = f'prefab_{name}.gd'
                    tscn.add_node_with_script(
                        name, 'Area2D',
                        script_path=f'scripts/{script_name}',
                        properties=root_props
                    )
                    self._write_checkpoint_script(scripts_dir, name, prefab, prefab_anims)
                elif has_animation:
                    script_name = f'prefab_{name}.gd'
                    tscn.add_node_with_script(
                        name, 'Area2D',
                        script_path=f'scripts/{script_name}',
                        properties=root_props
                    )
                    self._write_animator_script(scripts_dir, name, 'Area2D', prefab_anims)
                else:
                    tscn.add_node(name, 'Area2D', properties=root_props)
            else:
                if enemy_def is not None:
                    # Sensor/hazard enemy (e.g., piranha plant with emerge AI)
                    script_name = f'prefab_{name}.gd'
                    tscn.add_node_with_script(
                        name, 'Node2D',
                        script_path=f'scripts/{script_name}',
                        properties=root_props
                    )
                    self._write_enemy_script(scripts_dir, name, prefab, enemy_def, prefab_anims)
                elif has_animation:
                    script_name = f'prefab_{name}.gd'
                    tscn.add_node_with_script(
                        name, 'Node2D',
                        script_path=f'scripts/{script_name}',
                        properties=root_props
                    )
                    self._write_animator_script(scripts_dir, name, 'Node2D', prefab_anims)
                else:
                    tscn.add_node(name, 'Node2D', properties=root_props)

            # Process prefab children (usually a sprite)
            child_idx = 0
            for child in prefab.children:
                if isinstance(child, SpriteNode):
                    sprite_data = self._sprite_to_dict(child)
                    # Ensure child has a valid node name (empty names crash Godot)
                    if not sprite_data['id']:
                        suffix = f'_{child_idx}' if child_idx > 0 else ''
                        sprite_data['id'] = f'{name}_body{suffix}'
                        child_idx += 1
                    if body_type in ('dynamic', 'static'):
                        # Add visual + collision as children
                        self._add_sprite_visual(tscn, sprite_data, parent='.')
                        self._add_collision_shape(tscn, sprite_data, parent='.')
                    elif body_type is None and sprite_data.get('sensor'):
                        # Root is already Area2D — add visual + collision directly (no nested Area2D)
                        self._add_collision_shape(tscn, sprite_data, parent='.')
                        self._add_sprite_visual(tscn, sprite_data, parent='.')
                    else:
                        self._add_sprite_to_tscn(tscn, sprite_data, parent='.')

            content = tscn.build()
            (prefabs_dir / f'{name}.tscn').write_text(content, encoding='utf-8')

    def _get_prefab_body_type(self, prefab: PrefabNode) -> Optional[str]:
        """Determine the physics body type for a prefab."""
        # Check entity type
        if prefab.entity_type == 'enemy':
            return 'dynamic'
        if prefab.entity_type == 'block':
            return 'static'
        if prefab.entity_type in ('item', 'goal'):
            return None  # Area2D

        # Check children for body hints
        for child in prefab.children:
            if isinstance(child, SpriteNode):
                # Sensors should be Area2D, not StaticBody2D
                if child.sensor:
                    return None  # Area2D
                if child.body:
                    return child.body
        return None

    def _sprite_to_dict(self, node: SpriteNode) -> Dict:
        """Convert a SpriteNode to a dict (reuse _process_sprite format)."""
        if node.src:
            self._assets.add(node.src)
        return {
            'id': node.sprite_id,
            'src': node.src,
            'x': node.x, 'y': node.y,
            'width': node.width, 'height': node.height,
            'anchor_x': node.anchor_x, 'anchor_y': node.anchor_y,
            'rotation': node.rotation,
            'scale_x': node.scale_x, 'scale_y': node.scale_y,
            'alpha': node.alpha, 'visible': node.visible,
            'color': node.color, 'tag': node.tag, 'layer': node.layer,
            'frame_width': node.frame_width, 'frame_height': node.frame_height,
            'body': node.body, 'shape': node.shape,
            'bounce': node.bounce, 'friction': node.friction,
            'mass': node.mass, 'sensor': node.sensor,
            'controls': node.controls, 'speed': node.speed,
            'jump_force': node.jump_force,
            'gravity_up': node.gravity_up, 'gravity_down': node.gravity_down,
            'jump_hold_boost': node.jump_hold_boost,
            'coyote_frames': node.coyote_frames,
            'max_fall_speed': node.max_fall_speed,
            'animations': [], 'colliders': [], 'on_collisions': [],
            'behaviors': [], 'children': [],
        }

    def _write_animator_script(self, scripts_dir: Path, name: str,
                               base_class: str, anims: list):
        """Generate a simple sprite animator script for a prefab."""
        # Get the first auto-play animation's frames and speed
        frames = [0, 1, 2, 3]
        anim_speed = 0.15
        for anim in anims:
            if getattr(anim, 'auto_play', False) or True:  # Use first anim
                parsed = self._parse_frame_range(getattr(anim, 'frames', '0'))
                if parsed:
                    frames = parsed
                anim_speed = float(getattr(anim, 'speed', 0.15) or 0.15)
                break

        content = SPRITE_ANIMATOR_GD.format(
            base_class=base_class,
            frames=str(frames),
            speed=f'{anim_speed:.2f}',
        )
        (scripts_dir / f'prefab_{name}.gd').write_text(content, encoding='utf-8')

    def _write_prefab_script(self, scripts_dir: Path, name: str,
                             prefab: PrefabNode, anims: list = None):
        """Generate a GDScript for a prefab with AI/behavior."""
        gd = GdScriptBuilder()
        gd.extends('CharacterBody2D')
        gd.blank()

        # Use move_speed directly as px/s (no conversion if >= 10)
        speed = float(prefab.move_speed or 50.0)
        if speed < 10:
            speed = speed * 60.0  # Convert frame-based speed to px/s
        gravity = SMW_GRAVITY

        # Get collision settings from child sprite
        child_collision_layer = None
        child_collision_mask = None
        for child in prefab.children:
            if isinstance(child, SpriteNode):
                if child.collision_layer is not None:
                    child_collision_layer = child.collision_layer
                if child.collision_mask is not None:
                    child_collision_mask = child.collision_mask
                break

        gd.export_var('patrol_speed', 'float', f'{speed:.1f}')
        gd.export_var('turn_on_edge', 'bool', gd_bool(prefab.turn_on_edge or False))
        gd.var('_direction', '-1.0' if (getattr(prefab, 'facing', None) or 'left') == 'left' else '1.0')
        gd.blank()

        # Turn cooldown (anti-oscillation)
        has_turn_cooldown = prefab.turn_cooldown is not None and prefab.turn_cooldown > 0
        if has_turn_cooldown:
            gd.var('_turn_cooldown', f'{prefab.turn_cooldown:.2f}', 'float')
            gd.var('_turn_timer', '0.0', 'float')
            gd.blank()

        # Squish mechanic: health >= 2 + defeated_by == "stomp"
        has_squish = (prefab.health is not None and prefab.health >= 2
                      and prefab.defeated_by == 'stomp')
        # Get frame_height from child sprite for squish offset calculation
        prefab_frame_h = 32  # default
        for child in prefab.children:
            if isinstance(child, SpriteNode):
                prefab_frame_h = child.frame_height or child.height or 32
                break
        if has_squish:
            gd.var('_health', str(prefab.health), 'int')
            gd.var('_is_squished', 'false', 'bool')
            gd.var('_squish_speed_mult', '1.5', 'float')
            gd.var('frame_h', str(prefab_frame_h), 'float')
            gd.blank()

        # Animation variables
        anim_frames = [0]  # Default to single frame (no animation)
        anim_speed = 0.15
        if anims:
            for anim in anims:
                parsed = self._parse_frame_range(getattr(anim, 'frames', '0'))
                if parsed:
                    anim_frames = parsed
                anim_speed = float(getattr(anim, 'speed', 0.15) or 0.15)
                break
        gd.var('_anim_timer', '0.0', 'float')
        gd.var('_anim_frames', str(anim_frames), 'Array')
        gd.var('_anim_idx', '0', 'int')
        gd.var('_anim_speed', f'{anim_speed:.2f}', 'float')
        gd.blank()

        # _ready: set collision layers
        if child_collision_layer is not None or child_collision_mask is not None:
            gd.func('_ready')
            if child_collision_layer is not None:
                gd.assign('collision_layer', str(self._resolve_collision_value(child_collision_layer)))
            if child_collision_mask is not None:
                gd.assign('collision_mask', str(self._resolve_collision_value(child_collision_mask)))
            gd.func_close()
            gd.blank()

        # _physics_process
        gd.func('_physics_process', 'delta: float')
        gd.if_block('not is_on_floor()')
        gd.line(f'velocity.y += {gravity} * delta')
        gd.else_block()
        gd.assign('velocity.y', '0')
        gd.block_close()
        gd.blank()

        # Turn cooldown timer
        if has_turn_cooldown:
            gd.if_block('_turn_timer > 0')
            gd.line('_turn_timer -= delta')
            gd.block_close()
            gd.blank()

        # Velocity
        gd.assign('velocity.x', '_direction * patrol_speed')
        gd.blank()

        # Wall turn with cooldown
        if has_turn_cooldown:
            gd.if_block('is_on_wall() and _turn_timer <= 0')
            gd.line('_direction *= -1')
            gd.assign('_turn_timer', '_turn_cooldown')
            gd.block_close()
        else:
            gd.if_block('is_on_wall()')
            gd.line('_direction *= -1')
            gd.block_close()
        gd.blank()

        gd.line('move_and_slide()')
        gd.blank()
        gd.comment('Flip sprite to face movement direction')
        gd.if_block('has_node("Sprite2D")')
        gd.line('$Sprite2D.flip_h = _direction > 0')
        gd.block_close()
        gd.blank()
        gd.comment('Animate sprite')
        gd.line('_anim_timer += delta')
        gd.if_block('_anim_timer >= _anim_speed')
        gd.assign('_anim_timer', '0.0')
        gd.line('_anim_idx = (_anim_idx + 1) % _anim_frames.size()')
        gd.if_block('has_node("Sprite2D")')
        gd.line('$Sprite2D.frame = _anim_frames[_anim_idx]')
        gd.block_close()
        gd.block_close()
        gd.func_close()
        gd.blank()

        # Stomp handler (squish mechanic)
        if has_squish:
            stomp_bounce = prefab.stomp_bounce or -200
            reward_str = prefab.reward or ''
            reward_kill_str = prefab.reward_kill or ''
            gd.func('stomp')
            gd.line('_health -= 1')
            gd.if_block('_health <= 0')
            # Final kill
            if reward_kill_str:
                parts = reward_kill_str.split(':')
                if len(parts) == 2:
                    gd.line(f'QuantumEventBus.emit_event("enemy-killed", {{"score": {parts[1]}, "other": self}})')
            gd.line('queue_free()')
            gd.else_block()
            # Squish (half height, speed up)
            gd.assign('_is_squished', 'true')
            gd.comment('Squish visual + reposition body')
            gd.if_block('has_node("Sprite2D")')
            gd.line('$Sprite2D.scale.y = 0.5')
            gd.line('$Sprite2D.position.y += frame_h * 0.25')
            gd.block_close()
            gd.line('global_position.y += frame_h * 0.25')
            gd.comment('Shrink collision to match squished sprite')
            gd.if_block('has_node("CollisionShape2D")')
            gd.line('var shape = $CollisionShape2D.shape.duplicate()')
            gd.line('$CollisionShape2D.shape = shape')
            gd.if_block('shape is RectangleShape2D')
            gd.line('shape.size.y *= 0.5')
            gd.block_close()
            gd.block_close()
            gd.comment('Speed up after hit')
            gd.line('patrol_speed *= _squish_speed_mult')
            if reward_str:
                parts = reward_str.split(':')
                if len(parts) == 2:
                    gd.line(f'QuantumEventBus.emit_event("enemy-stomped", {{"score": {parts[1]}, "other": self}})')
            gd.block_close()
            gd.func_close()
            gd.blank()

        # die()
        gd.func('die')
        gd.line('QuantumEventBus.emit_event("enemy-killed", {"other": self})')
        gd.line('queue_free()')
        gd.func_close()
        gd.blank()

        # set_patrol()
        gd.func('set_patrol', 'speed: float')
        gd.assign('patrol_speed', 'speed')
        gd.func_close()

        (scripts_dir / f'prefab_{name}.gd').write_text(gd.build(), encoding='utf-8')

    def _get_enemy_for_prefab(self, name: str) -> Optional[EnemyNode]:
        """Find EnemyNode definition for a given prefab name."""
        for enemy in self._enemies:
            if enemy.prefab == name:
                return enemy
        return None

    def _write_enemy_script(self, scripts_dir: Path, name: str,
                            prefab: PrefabNode, enemy: EnemyNode,
                            anims: list = None):
        """Generate a GDScript for an enemy prefab using EnemyNode data."""
        ai = enemy.ai
        ai_type = ai.ai_type if ai else 'patrol'

        # Dispatch to specialized generators for non-patrol AI types
        if ai_type == 'charge':
            self._write_charge_enemy_script(scripts_dir, name, prefab, enemy, anims)
            return
        if ai_type == 'emerge':
            self._write_emerge_enemy_script(scripts_dir, name, prefab, enemy, anims)
            return

        gd = GdScriptBuilder()
        gd.extends('CharacterBody2D')
        gd.blank()

        # AI data
        speed = ai.speed if ai else 30.0
        if speed < 10:
            speed = speed * 60.0
        facing = (ai.facing if ai else 'left') or 'left'
        turn_on_edge = ai.turn_on_edge if ai else False
        gravity = SMW_GRAVITY

        # Get collision settings from child sprite
        child_collision_layer = None
        child_collision_mask = None
        for child in prefab.children:
            if isinstance(child, SpriteNode):
                if child.collision_layer is not None:
                    child_collision_layer = child.collision_layer
                if child.collision_mask is not None:
                    child_collision_mask = child.collision_mask
                break

        gd.export_var('patrol_speed', 'float', f'{speed:.1f}')
        gd.export_var('turn_on_edge', 'bool', gd_bool(turn_on_edge))
        gd.var('_direction', '-1.0' if facing == 'left' else '1.0')
        gd.blank()

        # Turn cooldown
        turn_cooldown = ai.turn_cooldown if ai else None
        has_turn_cooldown = turn_cooldown is not None and turn_cooldown > 0
        if has_turn_cooldown:
            gd.var('_turn_cooldown', f'{turn_cooldown:.2f}', 'float')
            gd.var('_turn_timer', '0.0', 'float')
            gd.blank()

        # Squish mechanic from defeat data
        defeat = enemy.defeat
        has_squish = (defeat is not None and defeat.health >= 2
                      and defeat.by == 'stomp')
        squish_speed_mult = 1.5
        # Get frame_height from child sprite for squish offset calculation
        enemy_frame_h = 32  # default
        for child in prefab.children:
            if isinstance(child, SpriteNode):
                enemy_frame_h = child.frame_height or child.height or 32
                break
        if has_squish:
            if defeat.on_hit and defeat.on_hit.speed_multiply:
                squish_speed_mult = defeat.on_hit.speed_multiply
            gd.var('_health', str(defeat.health), 'int')
            gd.var('_is_squished', 'false', 'bool')
            gd.var('_squish_speed_mult', f'{squish_speed_mult}', 'float')
            gd.var('frame_h', str(enemy_frame_h), 'float')
            gd.blank()

        # Animation variables
        anim_frames = [0]  # Default to single frame (no animation)
        anim_speed = 0.15
        if anims:
            for anim in anims:
                parsed = self._parse_frame_range(getattr(anim, 'frames', '0'))
                if parsed:
                    anim_frames = parsed
                anim_speed = float(getattr(anim, 'speed', 0.15) or 0.15)
                break
        gd.var('_anim_timer', '0.0', 'float')
        gd.var('_anim_frames', str(anim_frames), 'Array')
        gd.var('_anim_idx', '0', 'int')
        gd.var('_anim_speed', f'{anim_speed:.2f}', 'float')
        gd.blank()

        # _ready: set collision layers
        if child_collision_layer is not None or child_collision_mask is not None:
            gd.func('_ready')
            if child_collision_layer is not None:
                gd.assign('collision_layer', str(self._resolve_collision_value(child_collision_layer)))
            if child_collision_mask is not None:
                gd.assign('collision_mask', str(self._resolve_collision_value(child_collision_mask)))
            gd.func_close()
            gd.blank()

        # _physics_process
        gd.func('_physics_process', 'delta: float')
        gd.if_block('not is_on_floor()')
        gd.line(f'velocity.y += {gravity} * delta')
        gd.else_block()
        gd.assign('velocity.y', '0')
        gd.block_close()
        gd.blank()

        if has_turn_cooldown:
            gd.if_block('_turn_timer > 0')
            gd.line('_turn_timer -= delta')
            gd.block_close()
            gd.blank()

        gd.assign('velocity.x', '_direction * patrol_speed')
        gd.blank()

        if has_turn_cooldown:
            gd.if_block('is_on_wall() and _turn_timer <= 0')
            gd.line('_direction *= -1')
            gd.assign('_turn_timer', '_turn_cooldown')
            gd.block_close()
        else:
            gd.if_block('is_on_wall()')
            gd.line('_direction *= -1')
            gd.block_close()
        gd.blank()

        gd.line('move_and_slide()')
        gd.blank()
        gd.comment('Flip sprite to face movement direction')
        gd.if_block('has_node("Sprite2D")')
        gd.line('$Sprite2D.flip_h = _direction > 0')
        gd.block_close()
        gd.blank()
        gd.comment('Animate sprite')
        gd.line('_anim_timer += delta')
        gd.if_block('_anim_timer >= _anim_speed')
        gd.assign('_anim_timer', '0.0')
        gd.line('_anim_idx = (_anim_idx + 1) % _anim_frames.size()')
        gd.if_block('has_node("Sprite2D")')
        gd.line('$Sprite2D.frame = _anim_frames[_anim_idx]')
        gd.block_close()
        gd.block_close()
        gd.func_close()
        gd.blank()

        # Stomp handler (squish mechanic) - data-driven from EnemyNode
        if has_squish:
            stomp_bounce = defeat.bounce or -200
            hit_score = defeat.on_hit.score if defeat.on_hit else 0
            kill_score = defeat.on_kill.score if defeat.on_kill else 0
            gd.func('stomp')
            gd.line('_health -= 1')
            gd.if_block('_health <= 0')
            if kill_score:
                gd.line(f'QuantumEventBus.emit_event("enemy-killed", {{"score": {kill_score}, "other": self}})')
            else:
                gd.line('QuantumEventBus.emit_event("enemy-killed", {"other": self})')
            gd.line('queue_free()')
            gd.else_block()
            gd.assign('_is_squished', 'true')
            gd.comment('Squish visual + reposition body')
            gd.if_block('has_node("Sprite2D")')
            gd.line('$Sprite2D.scale.y = 0.5')
            gd.line('$Sprite2D.position.y += frame_h * 0.25')
            gd.block_close()
            gd.line('global_position.y += frame_h * 0.25')
            gd.comment('Shrink collision to match squished sprite')
            gd.if_block('has_node("CollisionShape2D")')
            gd.line('var shape = $CollisionShape2D.shape.duplicate()')
            gd.line('$CollisionShape2D.shape = shape')
            gd.if_block('shape is RectangleShape2D')
            gd.line('shape.size.y *= 0.5')
            gd.block_close()
            gd.block_close()
            gd.comment('Speed up after hit')
            gd.line('patrol_speed *= _squish_speed_mult')
            if hit_score:
                gd.line(f'QuantumEventBus.emit_event("enemy-stomped", {{"score": {hit_score}, "other": self}})')
            gd.block_close()
            gd.func_close()
            gd.blank()

        # die()
        gd.func('die')
        gd.line('QuantumEventBus.emit_event("enemy-killed", {"other": self})')
        gd.line('queue_free()')
        gd.func_close()
        gd.blank()

        # set_patrol()
        gd.func('set_patrol', 'speed: float')
        gd.assign('patrol_speed', 'speed')
        gd.func_close()

        (scripts_dir / f'prefab_{name}.gd').write_text(gd.build(), encoding='utf-8')

    def _write_charge_enemy_script(self, scripts_dir: Path, name: str,
                                    prefab: PrefabNode, enemy: EnemyNode,
                                    anims: list = None):
        """Generate GDScript for charge AI enemy (Banzai Bill - horizontal flight, no gravity)."""
        gd = GdScriptBuilder()
        gd.extends('CharacterBody2D')
        gd.blank()

        ai = enemy.ai
        speed = ai.speed if ai else 90.0
        if speed < 10:
            speed = speed * 60.0
        facing = (ai.facing if ai else 'left') or 'left'

        # Get collision settings
        child_collision_layer = None
        child_collision_mask = None
        for child in prefab.children:
            if isinstance(child, SpriteNode):
                if child.collision_layer is not None:
                    child_collision_layer = child.collision_layer
                if child.collision_mask is not None:
                    child_collision_mask = child.collision_mask
                break

        gd.export_var('charge_speed', 'float', f'{speed:.1f}')
        gd.var('_direction', '-1.0' if facing == 'left' else '1.0')
        gd.blank()

        # Defeat data
        defeat = enemy.defeat
        has_stomp = defeat is not None and defeat.by == 'stomp'
        if has_stomp:
            gd.var('_health', str(defeat.health), 'int')
            gd.blank()

        # Animation variables
        anim_frames = [0]  # Default to single frame (no animation)
        anim_speed = 0.15
        if anims:
            for anim in anims:
                parsed = self._parse_frame_range(getattr(anim, 'frames', '0'))
                if parsed:
                    anim_frames = parsed
                anim_speed = float(getattr(anim, 'speed', 0.15) or 0.15)
                break
        gd.var('_anim_timer', '0.0', 'float')
        gd.var('_anim_frames', str(anim_frames), 'Array')
        gd.var('_anim_idx', '0', 'int')
        gd.var('_anim_speed', f'{anim_speed:.2f}', 'float')
        gd.var('_launch_sound_played', 'false', 'bool')
        gd.blank()

        # _ready
        gd.func('_ready')
        if child_collision_layer is not None:
            gd.assign('collision_layer', str(self._resolve_collision_value(child_collision_layer)))
        if child_collision_mask is not None:
            gd.assign('collision_mask', str(self._resolve_collision_value(child_collision_mask)))
        gd.func_close()
        gd.blank()

        # _physics_process: NO gravity, horizontal flight only
        gd.func('_physics_process', 'delta: float')
        gd.comment('Launch sound when entering viewport')
        gd.if_block('not _launch_sound_played')
        gd.line('var camera = get_viewport().get_camera_2d()')
        gd.if_block('camera')
        gd.line('var vp_w = get_viewport_rect().size.x')
        gd.if_block('global_position.x < camera.global_position.x + vp_w + 100')
        gd.assign('_launch_sound_played', 'true')
        gd.line('QuantumEventBus.emit_event("banzai-launch", {"other": self})')
        gd.block_close()
        gd.block_close()
        gd.block_close()
        gd.blank()
        gd.comment('Charge AI: horizontal flight, no gravity')
        gd.assign('velocity.x', '_direction * charge_speed')
        gd.assign('velocity.y', '0')
        gd.line('move_and_slide()')
        gd.blank()
        gd.comment('Flip sprite to face movement direction')
        gd.if_block('has_node("Sprite2D")')
        gd.line('$Sprite2D.flip_h = _direction > 0')
        gd.block_close()
        gd.blank()
        gd.comment('Animate sprite')
        gd.line('_anim_timer += delta')
        gd.if_block('_anim_timer >= _anim_speed')
        gd.assign('_anim_timer', '0.0')
        gd.line('_anim_idx = (_anim_idx + 1) % _anim_frames.size()')
        gd.if_block('has_node("Sprite2D")')
        gd.line('$Sprite2D.frame = _anim_frames[_anim_idx]')
        gd.block_close()
        gd.block_close()
        gd.blank()
        gd.comment('Destroy if off-screen (far left)')
        gd.if_block('global_position.x < -200')
        gd.line('queue_free()')
        gd.block_close()
        gd.func_close()
        gd.blank()

        # stomp handler
        if has_stomp:
            kill_score = defeat.on_kill.score if defeat.on_kill else 0
            gd.func('stomp')
            gd.line('_health -= 1')
            gd.if_block('_health <= 0')
            if kill_score:
                gd.line(f'QuantumEventBus.emit_event("enemy-killed", {{"score": {kill_score}, "other": self}})')
            else:
                gd.line('QuantumEventBus.emit_event("enemy-killed", {"other": self})')
            gd.line('queue_free()')
            gd.block_close()
            gd.func_close()
            gd.blank()

        # die()
        gd.func('die')
        gd.line('QuantumEventBus.emit_event("enemy-killed", {"other": self})')
        gd.line('queue_free()')
        gd.func_close()

        (scripts_dir / f'prefab_{name}.gd').write_text(gd.build(), encoding='utf-8')

    def _write_emerge_enemy_script(self, scripts_dir: Path, name: str,
                                    prefab: PrefabNode, enemy: EnemyNode,
                                    anims: list = None):
        """Generate GDScript for emerge AI enemy (Piranha Plant - timer-based emerge/retract)."""
        gd = GdScriptBuilder()
        gd.extends('Node2D')
        gd.blank()

        ai = enemy.ai
        emerge_speed = ai.speed if ai else 1.5

        gd.export_var('emerge_height', 'float', '24.0')
        gd.export_var('wait_time', 'float', '2.0')
        gd.export_var('emerge_speed', 'float', f'{emerge_speed:.1f}')
        gd.export_var('safe_distance', 'float', '32.0')
        gd.blank()

        gd.var('_emerged', 'false', 'bool')
        gd.var('_emerging', 'false', 'bool')
        gd.var('_retracting', 'false', 'bool')
        gd.var('_timer', '0.0', 'float')
        gd.var('_base_y', '0.0', 'float')
        gd.var('_current_offset', '0.0', 'float')
        gd.var('_player_near', 'false', 'bool')
        gd.blank()

        # Animation variables
        anim_frames = [0, 1]
        anim_speed = 0.2
        if anims:
            for anim in anims:
                parsed = self._parse_frame_range(getattr(anim, 'frames', '0-1'))
                if parsed:
                    anim_frames = parsed
                anim_speed = float(getattr(anim, 'speed', 0.2) or 0.2)
                break
        gd.var('_anim_timer', '0.0', 'float')
        gd.var('_anim_frames', str(anim_frames), 'Array')
        gd.var('_anim_idx', '0', 'int')
        gd.var('_anim_speed', f'{anim_speed:.2f}', 'float')
        gd.blank()

        # _ready
        gd.func('_ready')
        gd.assign('_base_y', 'position.y')
        gd.func_close()
        gd.blank()

        # _process: emerge/retract cycle
        gd.func('_process', 'delta: float')
        gd.comment('Check player proximity (safe zone)')
        gd.line('_check_player_proximity()')
        gd.blank()

        gd.comment('Timer-based emerge/retract cycle')
        gd.line('_timer += delta')
        gd.blank()

        gd.if_block('not _emerged and not _emerging')
        gd.comment('Waiting to emerge')
        gd.if_block('_timer >= wait_time and not _player_near')
        gd.assign('_emerging', 'true')
        gd.assign('_timer', '0.0')
        gd.block_close()
        gd.block_close()
        gd.blank()

        gd.if_block('_emerging')
        gd.line('_current_offset = min(_current_offset + emerge_speed * delta * 60.0, emerge_height)')
        gd.assign('position.y', '_base_y - _current_offset')
        gd.if_block('_current_offset >= emerge_height')
        gd.assign('_emerged', 'true')
        gd.assign('_emerging', 'false')
        gd.assign('_timer', '0.0')
        gd.block_close()
        gd.block_close()
        gd.blank()

        gd.if_block('_emerged and not _retracting')
        gd.if_block('_timer >= wait_time')
        gd.assign('_retracting', 'true')
        gd.assign('_timer', '0.0')
        gd.block_close()
        gd.block_close()
        gd.blank()

        gd.if_block('_retracting')
        gd.line('_current_offset = max(_current_offset - emerge_speed * delta * 60.0, 0.0)')
        gd.assign('position.y', '_base_y - _current_offset')
        gd.if_block('_current_offset <= 0.0')
        gd.assign('_emerged', 'false')
        gd.assign('_retracting', 'false')
        gd.assign('_timer', '0.0')
        gd.block_close()
        gd.block_close()
        gd.blank()

        gd.comment('Animate sprite')
        gd.line('_anim_timer += delta')
        gd.if_block('_anim_timer >= _anim_speed')
        gd.assign('_anim_timer', '0.0')
        gd.line('_anim_idx = (_anim_idx + 1) % _anim_frames.size()')
        gd.if_block('has_node("Sprite2D")')
        gd.line('$Sprite2D.frame = _anim_frames[_anim_idx]')
        gd.block_close()
        gd.block_close()
        gd.func_close()
        gd.blank()

        # _check_player_proximity
        gd.func('_check_player_proximity')
        gd.assign('_player_near', 'false')
        gd.line('var players = get_tree().get_nodes_in_group("player")')
        gd.if_block('players.size() > 0')
        gd.line('var dist = abs(players[0].global_position.x - global_position.x)')
        gd.assign('_player_near', 'dist < safe_distance')
        gd.block_close()
        gd.func_close()
        gd.blank()

        # die()
        gd.func('die')
        gd.line('QuantumEventBus.emit_event("enemy-killed", {"other": self})')
        gd.line('queue_free()')
        gd.func_close()

        (scripts_dir / f'prefab_{name}.gd').write_text(gd.build(), encoding='utf-8')

    def _write_block_script(self, scripts_dir: Path, name: str,
                            prefab: PrefabNode, anims: list = None):
        """Generate GDScript for a question block (content + hits countdown)."""
        gd = GdScriptBuilder()
        gd.extends('StaticBody2D')
        gd.blank()

        hits = prefab.hits if prefab.hits is not None else 1
        content = prefab.content or 'coin'

        gd.var('_hits_remaining', str(hits), 'int')
        gd.var('_content', f'"{content}"', 'String')
        gd.var('_is_used', 'false', 'bool')
        gd.blank()

        # Animation variables
        anim_frames = [0, 1, 2, 3]
        anim_speed = 0.15
        if anims:
            for anim in anims:
                parsed = self._parse_frame_range(getattr(anim, 'frames', '0-3'))
                if parsed:
                    anim_frames = parsed
                anim_speed = float(getattr(anim, 'speed', 0.15) or 0.15)
                break
        gd.var('_anim_timer', '0.0', 'float')
        gd.var('_anim_frames', str(anim_frames), 'Array')
        gd.var('_anim_idx', '0', 'int')
        gd.var('_anim_speed', f'{anim_speed:.2f}', 'float')
        gd.blank()

        # _process: animate while not used
        gd.func('_process', 'delta: float')
        gd.if_block('_is_used')
        gd.line('return')
        gd.block_close()
        gd.line('_anim_timer += delta')
        gd.if_block('_anim_timer >= _anim_speed')
        gd.assign('_anim_timer', '0.0')
        gd.line('_anim_idx = (_anim_idx + 1) % _anim_frames.size()')
        gd.if_block('has_node("Sprite2D")')
        gd.line('$Sprite2D.frame = _anim_frames[_anim_idx]')
        gd.block_close()
        gd.block_close()
        gd.func_close()
        gd.blank()

        # hit(): countdown hits, switch to used
        gd.func('hit')
        gd.if_block('_is_used')
        gd.line('return')
        gd.block_close()
        gd.line('_hits_remaining -= 1')
        gd.line(f'QuantumEventBus.emit_event("block-hit", {{"content": _content, "other": self}})')
        gd.if_block('_hits_remaining <= 0')
        gd.assign('_is_used', 'true')
        gd.if_block('has_node("Sprite2D")')
        gd.line('$Sprite2D.frame = _anim_frames[-1]')
        gd.block_close()
        gd.block_close()
        gd.func_close()

        (scripts_dir / f'prefab_{name}.gd').write_text(gd.build(), encoding='utf-8')

    def _write_breakable_block_script(self, scripts_dir: Path, name: str,
                                      prefab: PrefabNode, anims: list = None):
        """Generate GDScript for a breakable block (tween rotation, toggle collision)."""
        gd = GdScriptBuilder()
        gd.extends('StaticBody2D')
        gd.blank()

        gd.var('_is_breaking', 'false', 'bool')
        gd.blank()

        # hit(): tween rotation + toggle collision
        gd.func('hit')
        gd.if_block('_is_breaking')
        gd.line('return')
        gd.block_close()
        gd.assign('_is_breaking', 'true')
        gd.line('var tween = create_tween()')
        gd.line('tween.tween_property(self, "rotation_degrees", 360.0, 0.25)')
        gd.line('tween.set_loops(4)')
        gd.line('tween.tween_callback(_on_break_complete)')
        gd.func_close()
        gd.blank()

        # _on_break_complete(): disable collision temporarily
        gd.func('_on_break_complete')
        gd.if_block('has_node("CollisionShape2D")')
        gd.line('$CollisionShape2D.disabled = true')
        gd.block_close()
        gd.line('QuantumEventBus.emit_event("block-broken", {"other": self})')
        gd.line('var timer = get_tree().create_timer(2.0)')
        gd.line('timer.timeout.connect(_restore)')
        gd.func_close()
        gd.blank()

        # _restore(): re-enable collision
        gd.func('_restore')
        gd.assign('rotation_degrees', '0.0')
        gd.assign('_is_breaking', 'false')
        gd.if_block('has_node("CollisionShape2D")')
        gd.line('$CollisionShape2D.disabled = false')
        gd.block_close()
        gd.func_close()

        (scripts_dir / f'prefab_{name}.gd').write_text(gd.build(), encoding='utf-8')

    def _write_flying_block_script(self, scripts_dir: Path, name: str,
                                    prefab: PrefabNode, anims: list = None):
        """Generate GDScript for a flying block (oscillating movement + hit drops + wings)."""
        gd = GdScriptBuilder()
        gd.extends('StaticBody2D')
        gd.blank()

        hits = prefab.hits if prefab.hits is not None else 1
        content = prefab.content or 'coin'

        gd.var('_hits_remaining', str(hits), 'int')
        gd.var('_content', f'"{content}"', 'String')
        gd.var('_is_used', 'false', 'bool')
        gd.var('_is_flying', 'true', 'bool')
        gd.var('_fly_time', '0.0', 'float')
        gd.export_var('fly_speed', 'float', '30.0')
        gd.export_var('fly_amplitude', 'float', '40.0')
        gd.var('_base_x', '0.0', 'float')
        gd.blank()

        # Animation variables
        anim_frames = [0, 1, 2, 3]
        anim_speed = 0.15
        if anims:
            for anim in anims:
                parsed = self._parse_frame_range(getattr(anim, 'frames', '0-3'))
                if parsed:
                    anim_frames = parsed
                anim_speed = float(getattr(anim, 'speed', 0.15) or 0.15)
                break
        gd.var('_anim_timer', '0.0', 'float')
        gd.var('_anim_frames', str(anim_frames), 'Array')
        gd.var('_anim_idx', '0', 'int')
        gd.var('_anim_speed', f'{anim_speed:.2f}', 'float')
        gd.blank()

        # _ready
        gd.func('_ready')
        gd.assign('_base_x', 'position.x')
        gd.func_close()
        gd.blank()

        # _process: oscillate while flying, animate
        gd.func('_process', 'delta: float')
        gd.if_block('_is_flying')
        gd.line('_fly_time += delta')
        gd.assign('position.x', '_base_x + sin(_fly_time * 2.0) * fly_amplitude')
        gd.block_close()
        gd.blank()
        gd.if_block('_is_used')
        gd.line('return')
        gd.block_close()
        gd.line('_anim_timer += delta')
        gd.if_block('_anim_timer >= _anim_speed')
        gd.assign('_anim_timer', '0.0')
        gd.line('_anim_idx = (_anim_idx + 1) % _anim_frames.size()')
        gd.if_block('has_node("Sprite2D")')
        gd.line('$Sprite2D.frame = _anim_frames[_anim_idx]')
        gd.block_close()
        gd.block_close()
        gd.func_close()
        gd.blank()

        # hit(): stop flying, remove wings, release content
        gd.func('hit')
        gd.if_block('_is_used')
        gd.line('return')
        gd.block_close()
        gd.line('_hits_remaining -= 1')
        gd.blank()
        gd.comment('Stop flying and remove wings')
        gd.assign('_is_flying', 'false')
        gd.if_block('has_node("Wings")')
        gd.line('$Wings.queue_free()')
        gd.block_close()
        gd.blank()
        gd.line(f'QuantumEventBus.emit_event("block-hit", {{"content": _content, "other": self}})')
        gd.if_block('_hits_remaining <= 0')
        gd.assign('_is_used', 'true')
        gd.if_block('has_node("Sprite2D")')
        gd.line('$Sprite2D.frame = _anim_frames[-1]')
        gd.block_close()
        gd.block_close()
        gd.func_close()

        (scripts_dir / f'prefab_{name}.gd').write_text(gd.build(), encoding='utf-8')

    def _write_collectible_script(self, scripts_dir: Path, name: str,
                                  prefab: PrefabNode, prefab_tag: str = None,
                                  anims: list = None):
        """Generate GDScript for a collectible item (Area2D body_entered, emit, queue_free)."""
        gd = GdScriptBuilder()
        gd.extends('Area2D')
        gd.blank()

        gd.var('_collected', 'false', 'bool')

        # Yoshi coin shimmer effect (palette shimmer instead of fake 3D spin)
        is_yoshi_coin = (prefab_tag == 'yoshi_coin')
        if is_yoshi_coin:
            gd.var('_shimmer_time', 'randf() * TAU', 'float')
        gd.blank()

        # Animation variables
        has_anim = anims and len(anims) > 0
        if has_anim:
            anim_frames = [0, 1, 2, 3]
            anim_speed = 0.15
            for anim in anims:
                parsed = self._parse_frame_range(getattr(anim, 'frames', '0-3'))
                if parsed:
                    anim_frames = parsed
                anim_speed = float(getattr(anim, 'speed', 0.15) or 0.15)
                break
            gd.var('_anim_timer', '0.0', 'float')
            gd.var('_anim_frames', str(anim_frames), 'Array')
            gd.var('_anim_idx', '0', 'int')
            gd.var('_anim_speed', f'{anim_speed:.2f}', 'float')
            gd.blank()

        # _ready: connect body_entered signal
        gd.func('_ready')
        gd.line('body_entered.connect(_on_body_entered)')
        gd.func_close()
        gd.blank()

        # _process: animation + yoshi coin spin
        if has_anim or is_yoshi_coin:
            gd.func('_process', 'delta: float')
            if is_yoshi_coin:
                gd.line('_shimmer_time += delta * 3.0')
                gd.line('var shimmer = 0.15 * sin(_shimmer_time)')
                gd.if_block('has_node("Sprite2D")')
                gd.line('$Sprite2D.modulate = Color(1.0 + shimmer, 1.0 + shimmer * 0.5, 0.7, 1.0)')
                gd.block_close()
            if has_anim:
                gd.line('_anim_timer += delta')
                gd.if_block('_anim_timer >= _anim_speed')
                gd.assign('_anim_timer', '0.0')
                gd.line('_anim_idx = (_anim_idx + 1) % _anim_frames.size()')
                gd.if_block('has_node("Sprite2D")')
                gd.line('$Sprite2D.frame = _anim_frames[_anim_idx]')
                gd.block_close()
                gd.block_close()
            gd.func_close()
            gd.blank()

        # Determine event name from reward or tag
        event_name = 'item-collected'
        if prefab.reward:
            parts = prefab.reward.split(':')
            if len(parts) == 2:
                event_name = f'{prefab_tag or name}-collected'

        # _on_body_entered: collect item
        gd.func('_on_body_entered', 'body: Node')
        gd.if_block('_collected')
        gd.line('return')
        gd.block_close()
        gd.if_block('body is CharacterBody2D')
        gd.assign('_collected', 'true')
        # Emit event with score if reward specified
        if prefab.reward:
            parts = prefab.reward.split(':')
            if len(parts) == 2:
                gd.line(f'QuantumEventBus.emit_event("{event_name}", {{"score": {parts[1]}, "other": self}})')
            else:
                gd.line(f'QuantumEventBus.emit_event("{event_name}", {{"other": self}})')
        else:
            gd.line(f'QuantumEventBus.emit_event("{event_name}", {{"other": self}})')
        gd.line('queue_free()')
        gd.block_close()
        gd.func_close()

        (scripts_dir / f'prefab_{name}.gd').write_text(gd.build(), encoding='utf-8')

    def _write_checkpoint_script(self, scripts_dir: Path, name: str,
                                 prefab: PrefabNode, anims: list = None):
        """Generate GDScript for a checkpoint (one-time activation, bar disappear, SFX)."""
        gd = GdScriptBuilder()
        gd.extends('Area2D')
        gd.blank()

        gd.line('signal checkpoint_activated(pos: Vector2)')
        gd.blank()
        gd.var('_activated', 'false', 'bool')
        gd.blank()

        # _ready: connect body_entered, ensure collision_mask targets player
        gd.func('_ready')
        gd.line('body_entered.connect(_on_body_entered)')
        gd.comment('Ensure collision_mask detects player layer (2)')
        gd.assign('collision_layer', '0')
        gd.assign('collision_mask', '2')
        gd.func_close()
        gd.blank()

        # _on_body_entered: activate checkpoint with SMW-style feedback
        gd.func('_on_body_entered', 'body: Node')
        gd.if_block('_activated')
        gd.line('return')
        gd.block_close()
        gd.if_block('body is CharacterBody2D')
        gd.assign('_activated', 'true')
        gd.line('checkpoint_activated.emit(global_position)')
        gd.line('QuantumEventBus.emit_event("checkpoint-activated", {"position": global_position, "other": self})')
        gd.blank()
        gd.comment('Visual feedback: flash green then fade to semi-transparent')
        gd.line('var tween = create_tween()')
        gd.line('tween.tween_property(self, "modulate", Color(0.0, 1.0, 0.0, 1.0), 0.1)')
        gd.line('tween.tween_property(self, "modulate", Color(0.5, 1.0, 0.5, 0.6), 0.3)')
        gd.blank()
        gd.comment('Hide bar/cordao child if present')
        gd.if_block('has_node("Bar")')
        gd.line('var bar_tween = create_tween()')
        gd.line('bar_tween.tween_property($Bar, "scale", Vector2(0, 1), 0.2)')
        gd.line('bar_tween.tween_callback($Bar.queue_free)')
        gd.block_close()
        gd.block_close()
        gd.func_close()

        (scripts_dir / f'prefab_{name}.gd').write_text(gd.build(), encoding='utf-8')

    def _write_player_controller(self, scripts_dir: Path):
        """Write player_controller.gd if any sprite has controls."""
        player = None
        for s in self._sprites:
            if s.get('controls'):
                player = s
                break

        if not player:
            return

        # Use sprite-level physics attrs if specified, fallback to SMW constants
        speed = float(player.get('speed') or 0) or SMW_WALK_SPEED
        # Convert abstract speed to Godot px/s: if small value (< 10), scale by 60
        if speed < 10:
            speed = speed * 60.0
        jump_vel = SMW_JUMP_VELOCITY
        jump_force = player.get('jump_force')
        if jump_force and float(jump_force) > 0:
            # Convert abstract jump force to Godot velocity
            jf = float(jump_force)
            if jf < 50:
                jump_vel = -jf * 53.0  # Scale: 5.3 -> ~-280
            else:
                jump_vel = -jf
        gravity_up = float(player.get('gravity_up') or 0) or SMW_GRAVITY_RISING
        gravity_down = float(player.get('gravity_down') or 0) or SMW_GRAVITY_FALLING
        jump_hold_boost = float(player.get('jump_hold_boost') or 0) or SMW_JUMP_HOLD_BOOST
        max_fall = float(player.get('max_fall_speed') or 0) or SMW_MAX_FALL
        coyote_frames = int(player.get('coyote_frames') or 6)
        collision_layer = player.get('collision_layer')
        collision_mask = player.get('collision_mask')
        floor_max_angle = player.get('floor_max_angle')

        # Extract animation data from sprite
        idle_frame = 0
        walk_frames = [1, 2, 3]
        jump_frame = 4
        walk_anim_speed = 0.12

        for anim in player.get('animations', []):
            anim_name = anim.get('name', '')
            frames_str = anim.get('frames', '')
            anim_speed = anim.get('speed', 0.12)

            if anim_name == 'idle':
                idle_frame = self._parse_frame_range(frames_str)[0] if frames_str else 0
            elif anim_name == 'walk':
                walk_frames = self._parse_frame_range(frames_str) if frames_str else [1, 2, 3]
                walk_anim_speed = float(anim_speed) if anim_speed else 0.12
            elif anim_name == 'jump':
                jump_frame = self._parse_frame_range(frames_str)[0] if frames_str else 4

        content = PLAYER_CONTROLLER_GD.format(
            speed=f'{speed:.1f}',
            jump_velocity=f'{jump_vel:.1f}',
            gravity_up=f'{gravity_up:.1f}',
            gravity_down=f'{gravity_down:.1f}',
            jump_hold_boost=f'{jump_hold_boost:.1f}',
            coyote_frames=coyote_frames,
            max_fall_speed=f'{max_fall:.1f}',
            idle_frame=idle_frame,
            walk_frames=str(walk_frames),
            walk_anim_speed=f'{walk_anim_speed:.2f}',
            jump_frame=jump_frame,
            collision_layer=self._resolve_collision_value(collision_layer),
            collision_mask=self._resolve_collision_value(collision_mask),
            floor_max_angle=f'{float(floor_max_angle) if floor_max_angle is not None else 45.0:.1f}',
        )

        # Add spin jump support if enabled
        has_spin_jump = player.get('spin_jump', False)
        if has_spin_jump:
            content += SPIN_JUMP_SECTION

        (scripts_dir / 'player_controller.gd').write_text(content, encoding='utf-8')

    @staticmethod
    def _parse_frame_range(frames_str: str) -> list:
        """Parse frame range string like '0', '1-3', '0,1,2,3' into list of ints."""
        frames = []
        for part in str(frames_str).split(','):
            part = part.strip()
            if '-' in part:
                start, end = part.split('-', 1)
                frames.extend(range(int(start), int(end) + 1))
            else:
                try:
                    frames.append(int(part))
                except ValueError:
                    pass
        return frames or [0]

    def _write_camera_script(self, scripts_dir: Path):
        """Write camera_follow.gd if camera exists."""
        if not self._camera:
            return

        cam = self._camera
        lerp_speed = cam.get('lerp', 0.1) * 60  # Convert to Godot smoothing speed
        use_bounds = cam.get('bounds') == 'scene'

        content = CAMERA_FOLLOW_GD.format(
            lerp_speed=f'{lerp_speed:.1f}',
            use_bounds=gd_bool(use_bounds),
            bound_right=f'{float(self._scene_width):.1f}',
            bound_bottom=f'{float(self._scene_height):.1f}',
        )
        (scripts_dir / 'camera_follow.gd').write_text(content, encoding='utf-8')

    def _write_ai_scripts(self, scripts_dir: Path):
        """Write patrol_ai.gd if any sprite needs it."""
        needs_patrol = False
        for s in self._sprites:
            if s.get('body') == 'dynamic' and not s.get('controls'):
                if s.get('tag') in ('enemy',) or s.get('behaviors'):
                    needs_patrol = True
                    break

        if not needs_patrol:
            return

        gravity_y = 980.0
        if self._physics:
            gravity_y = q2g_gravity(self._physics['gravity_y'])

        content = PATROL_AI_GD.format(
            speed=f'{q2g_speed(0.5):.1f}',
            turn_on_edge=gd_bool(True),
            gravity=f'{gravity_y:.1f}',
            initial_direction='-1.0',
        )
        (scripts_dir / 'patrol_ai.gd').write_text(content, encoding='utf-8')

    def _write_hud_script(self, scripts_dir: Path):
        """Write hud_manager.gd if HUD exists."""
        if not self._huds:
            return

        if self._has_tile_hud():
            self._write_tile_hud_script(scripts_dir)
            return

        # Legacy HTML-based HUD
        label_names = []
        label_index = 0
        for hud in self._huds:
            for child in hud.get('children', []):
                if child.get('type') == 'html':
                    attrs = child.get('attrs', {})
                    name = attrs.get('id', f'label_{label_index}')
                    label_names.append(name)
                    label_index += 1

        label_vars = '\n'.join(
            f'@onready var {name}_label: Label = ${name}'
            for name in label_names
        )
        label_ready = '\n'.join(
            f'\tpass  # Labels auto-connected via @onready'
            for _ in label_names
        ) or '\tpass'

        content = HUD_MANAGER_GD.format(
            label_vars=label_vars,
            label_ready=label_ready,
        )
        (scripts_dir / 'hud_manager.gd').write_text(content, encoding='utf-8')

    def _write_tile_hud_script(self, scripts_dir: Path):
        """Generate tile-based hud_manager.gd using GdScriptBuilder."""
        gd = GdScriptBuilder()
        gd.extends('CanvasLayer')
        gd.comment('HUD Manager - Tile-based SNES-style overlay')
        gd.comment('Generated by Quantum Framework')
        gd.blank()

        # Collect all tile-based HUD data
        all_tiles = []
        all_counters = []
        all_collections = []
        all_slots = []
        all_behaviors = []
        bg_color = None
        bg_height = 26

        for hud in self._huds:
            if hud.get('background'):
                bg_color = hud['background']
            if hud.get('background_height'):
                bg_height = hud['background_height']
            all_tiles.extend(hud.get('tiles', []))
            all_counters.extend(hud.get('counters', []))
            all_collections.extend(hud.get('collections', []))
            all_slots.extend(hud.get('slots', []))
            all_behaviors.extend(hud.get('behaviors', []))

        # Collect all unique textures
        all_sprites = set()
        for t in all_tiles:
            all_sprites.add(t['sprite'])
        for c in all_counters:
            all_sprites.add(c['strip'])
            if c.get('icon'):
                all_sprites.add(c['icon'])
            if c.get('symbol'):
                all_sprites.add(c['symbol'])
        for col in all_collections:
            all_sprites.add(col['sprite'])
        for slot in all_slots:
            for opt in slot.get('options', []):
                all_sprites.add(opt['sprite'])

        # Texture variables
        for sprite_path in sorted(all_sprites):
            var_name = self._sprite_var_name(sprite_path)
            gd.raw(f'var {var_name}: Texture2D')
        gd.blank()

        # State variables for counters
        for counter in all_counters:
            bind = counter['bind']
            gd.raw(f'var {bind}: int = 0')
        for col in all_collections:
            bind = col['bind']
            gd.raw(f'var {bind}: int = 0')
        for slot in all_slots:
            bind = slot['bind']
            gd.raw(f'var {bind}: String = ""')
        gd.blank()

        # Countdown variables
        has_countdown = any(c.get('countdown') for c in all_counters)
        has_hurry = any(c.get('hurry_at') is not None for c in all_counters)
        if has_countdown:
            gd.raw('var _countdown_timer: float = 0.0')
            gd.raw('var _countdown_active: bool = true')
        if has_hurry:
            gd.raw('var _hurry_mode: bool = false')
            gd.raw('var _hurry_flash_timer: float = 0.0')
        gd.raw('var _bonus_countdown_active: bool = false')
        gd.raw('var _bonus_countdown_timer: float = 0.0')
        gd.raw('var _course_clear: bool = false')
        gd.raw('var _canvas: Control')
        # Tint color variables
        tint_colors = set()
        for c in all_counters:
            if c.get('tint'):
                tint_colors.add(c['tint'])
        for color_name in sorted(tint_colors):
            gd.raw(f'var _tint_{color_name}: Color = {self._flash_color(color_name)}')
        gd.blank()

        # _ready()
        gd.func('_ready')
        for sprite_path in sorted(all_sprites):
            var_name = self._sprite_var_name(sprite_path)
            asset = self._hud_res_path(sprite_path)
            gd.line(f'{var_name} = load("{asset}")')
        gd.line('_canvas = Control.new()')
        gd.line('_canvas.set_anchors_preset(Control.PRESET_FULL_RECT)')
        gd.line('_canvas.connect("draw", _on_draw)')
        gd.line('add_child(_canvas)')
        gd.func_close()
        gd.blank()

        # _process(delta)
        gd.func('_process', 'delta: float')
        if has_countdown:
            gd.if_block('_countdown_active')
            gd.line('_countdown_timer += delta')
            gd.if_block('_countdown_timer >= 1.0')
            gd.line('_countdown_timer -= 1.0')
            # Find countdown counters
            for counter in all_counters:
                if counter.get('countdown'):
                    bind = counter['bind']
                    gd.line(f'{bind} = max(0, {bind} - 1)')
                    if counter.get('hurry_at') is not None:
                        hurry_val = counter['hurry_at']
                        gd.if_block(f'{bind} == {hurry_val}')
                        gd.line('_hurry_mode = true')
                        gd.line('QuantumEventBus.emit_event("time-hurry", {})')
                        gd.block_close()
            gd.block_close()  # timer >= 1.0
            gd.block_close()  # countdown_active
        if has_hurry:
            gd.if_block('_hurry_mode')
            gd.line('_hurry_flash_timer += delta')
            gd.block_close()
        # Bonus countdown
        gd.if_block('_bonus_countdown_active')
        gd.line('_bonus_countdown_timer += delta')
        gd.if_block('_bonus_countdown_timer >= 0.02')
        gd.line('_bonus_countdown_timer -= 0.02')
        for counter in all_counters:
            if counter.get('countdown'):
                bind = counter['bind']
                gd.line(f'if {bind} > 0:')
                gd.raw(f'\t\t\t{bind} -= 1')
        gd.block_close()
        gd.block_close()
        # Behavior checks
        for behavior in all_behaviors:
            target = behavior['target']
            event_type = behavior['event']
            value = behavior.get('value')
            if event_type == 'reach' and value is not None:
                for action in behavior.get('actions', []):
                    if action['action_type'] == 'emit' and action.get('event'):
                        if value == 0:
                            gd.if_block(f'{target} <= 0')
                        else:
                            gd.if_block(f'{target} == {value}')
                        gd.line(f'QuantumEventBus.emit_event("{action["event"]}", {{}})')
                        gd.block_close()
        gd.line('_canvas.queue_redraw()')
        gd.func_close()
        gd.blank()

        # _on_draw()
        gd.func('_on_draw')
        # Background bar
        if bg_color:
            godot_color = self._parse_rgba(bg_color)
            gd.line(f'_canvas.draw_rect(Rect2(0, 0, _canvas.size.x, {bg_height}), {godot_color})')
        gd.blank()

        # Draw tiles
        for tile in all_tiles:
            var_name = self._sprite_var_name(tile['sprite'])
            x, y = tile['x'], tile['y']
            if tile.get('width') and tile.get('height'):
                gd.line(f'_canvas.draw_texture_rect({var_name}, Rect2({x}, {y}, {tile["width"]}, {tile["height"]}), false)')
            else:
                gd.line(f'_canvas.draw_texture({var_name}, Vector2({x}, {y}))')
        gd.blank()

        # Draw counters
        for counter in all_counters:
            bind = counter['bind']
            x, y = counter['x'], counter['y']
            digits = counter['digits']
            dw = counter['digit_width']
            dh = counter['digit_height']
            align = counter.get('align', 'left')
            tint = counter.get('tint')
            right_edge = counter.get('right_edge')
            icon = counter.get('icon')
            symbol = counter.get('symbol')
            tint_expr = f'_tint_{tint}' if tint else None

            if align == 'right' and right_edge is not None:
                # Right-aligned counter
                if icon and symbol:
                    icon_var = self._sprite_var_name(icon)
                    sym_var = self._sprite_var_name(symbol)
                    gd.line(f'_draw_counter_right({bind}, {right_edge}, {y}, {icon_var}, {sym_var}, {dw}, {dh}, {tint_expr or "Color(1,1,1,1)"})')
                else:
                    if counter.get('hurry_at') is not None and counter.get('flash'):
                        flash_color = self._flash_color(counter['flash'])
                        gd.if_block('_hurry_mode and int(_hurry_flash_timer * 4) % 2 == 0')
                        gd.line(f'_draw_number_right({bind}, {right_edge}, {y}, {dw}, {dh}, {flash_color})')
                        gd.else_block()
                        gd.line(f'_draw_number_right({bind}, {right_edge}, {y}, {dw}, {dh}, {tint_expr or "Color(1,1,1,1)"})')
                        gd.block_close()
                    else:
                        gd.line(f'_draw_number_right({bind}, {right_edge}, {y}, {dw}, {dh}, {tint_expr or "Color(1,1,1,1)"})')
            else:
                # Left-aligned counter
                if counter.get('hurry_at') is not None and counter.get('flash'):
                    flash_color = self._flash_color(counter['flash'])
                    gd.if_block('_hurry_mode and int(_hurry_flash_timer * 4) % 2 == 0')
                    gd.line(f'_draw_number_tinted({bind}, {x}, {y}, {digits}, {dw}, {dh}, {flash_color})')
                    gd.else_block()
                    if tint_expr:
                        gd.line(f'_draw_number_tinted({bind}, {x}, {y}, {digits}, {dw}, {dh}, {tint_expr})')
                    else:
                        gd.line(f'_draw_number({bind}, {x}, {y}, {digits}, {dw}, {dh})')
                    gd.block_close()
                elif tint_expr:
                    gd.line(f'_draw_number_tinted({bind}, {x}, {y}, {digits}, {dw}, {dh}, {tint_expr})')
                else:
                    gd.line(f'_draw_number({bind}, {x}, {y}, {digits}, {dw}, {dh})')
        gd.blank()

        # Draw collections
        for col in all_collections:
            bind = col['bind']
            var_name = self._sprite_var_name(col['sprite'])
            x, y = col['x'], col['y']
            spacing = col['spacing']
            max_count = col['max']
            gd.for_block('i', f'range({bind})')
            gd.line(f'_canvas.draw_texture({var_name}, Vector2({x} + i * {spacing}, {y}))')
            gd.block_close()
        gd.blank()

        # Draw slots
        for slot in all_slots:
            bind = slot['bind']
            x, y = slot['x'], slot['y']
            for opt in slot.get('options', []):
                opt_var = self._sprite_var_name(opt['sprite'])
                gd.if_block(f'{bind} == "{opt["value"]}"')
                gd.line(f'_canvas.draw_texture({opt_var}, Vector2({x}, {y}))')
                gd.block_close()

        # Course clear overlay
        gd.if_block('_course_clear')
        gd.line('_draw_course_clear()')
        gd.block_close()
        gd.func_close()
        gd.blank()

        # _draw_number() helper
        # Find the first counter's strip for the texture reference
        strip_var = self._sprite_var_name(all_counters[0]['strip']) if all_counters else 'null'
        gd.func('_draw_number', 'value: int, x: int, y: int, digits: int, dw: int, dh: int')
        gd.line('var s = str(value)')
        gd.line('while s.length() < digits:')
        gd.raw('\t\ts = "0" + s')
        gd.line('for i in range(s.length()):')
        gd.raw(f'\t\tvar digit = s[i].to_int()')
        gd.raw(f'\t\tvar src_rect = Rect2(digit * dw, 0, dw, dh)')
        gd.raw(f'\t\tvar dst_rect = Rect2(x + i * dw, y, dw, dh)')
        gd.raw(f'\t\t_canvas.draw_texture_rect_region({strip_var}, dst_rect, src_rect)')
        gd.func_close()
        gd.blank()

        # _draw_number_tinted() helper
        gd.func('_draw_number_tinted', 'value: int, x: int, y: int, digits: int, dw: int, dh: int, tint: Color')
        gd.line('var s = str(value)')
        gd.line('while s.length() < digits:')
        gd.raw('\t\ts = "0" + s')
        gd.line('for i in range(s.length()):')
        gd.raw(f'\t\tvar digit = s[i].to_int()')
        gd.raw(f'\t\tvar src_rect = Rect2(digit * dw, 0, dw, dh)')
        gd.raw(f'\t\tvar dst_rect = Rect2(x + i * dw, y, dw, dh)')
        gd.raw(f'\t\t_canvas.draw_texture_rect_region({strip_var}, dst_rect, src_rect, tint)')
        gd.func_close()
        gd.blank()

        # _draw_number_right() - right-aligned, intelligent display (no zero-padding)
        has_right_counter = any(c.get('align') == 'right' for c in all_counters)
        if has_right_counter:
            gd.func('_draw_number_right', 'value: int, right_x: int, y: int, dw: int, dh: int, tint: Color')
            gd.line('var s = str(value)')
            gd.line('var start_x = right_x - s.length() * dw')
            gd.line('for i in range(s.length()):')
            gd.raw(f'\t\tvar digit = s[i].to_int()')
            gd.raw(f'\t\tvar src_rect = Rect2(digit * dw, 0, dw, dh)')
            gd.raw(f'\t\tvar dst_rect = Rect2(start_x + i * dw, y, dw, dh)')
            gd.raw(f'\t\t_canvas.draw_texture_rect_region({strip_var}, dst_rect, src_rect, tint)')
            gd.func_close()
            gd.blank()

        # _draw_counter_right() - composite right-aligned (icon + symbol + digits)
        has_composite = any(c.get('icon') and c.get('align') == 'right' for c in all_counters)
        if has_composite:
            gd.func('_draw_counter_right', 'value: int, right_x: int, y: int, icon: Texture2D, sym: Texture2D, dw: int, dh: int, tint: Color')
            gd.line('var s = str(value)')
            gd.line('var digits_w = s.length() * dw')
            gd.line('var sym_x = right_x - digits_w - dw')
            gd.line('var icon_x = sym_x - dw')
            gd.line('_canvas.draw_texture(icon, Vector2(icon_x, y))')
            gd.line('_canvas.draw_texture(sym, Vector2(sym_x, y))')
            gd.line('var start_x = right_x - digits_w')
            gd.line('for i in range(s.length()):')
            gd.raw(f'\t\tvar digit = s[i].to_int()')
            gd.raw(f'\t\tvar src_rect = Rect2(digit * dw, 0, dw, dh)')
            gd.raw(f'\t\tvar dst_rect = Rect2(start_x + i * dw, y, dw, dh)')
            gd.raw(f'\t\t_canvas.draw_texture_rect_region({strip_var}, dst_rect, src_rect, tint)')
            gd.func_close()
            gd.blank()

        # _draw_course_clear()
        gd.func('_draw_course_clear')
        gd.line('var screen_size = _canvas.size')
        gd.line('_canvas.draw_rect(Rect2(0, 0, screen_size.x, screen_size.y), Color(0, 0, 0, 0.7))')
        gd.line('# Course clear text would use a sprite in production')
        gd.func_close()
        gd.blank()

        # Public API
        gd.func('update_label', 'label_name: String, value')
        gd.line('match label_name:')
        for counter in all_counters:
            bind = counter['bind']
            gd.raw(f'\t\t"{bind}":')
            gd.raw(f'\t\t\t{bind} = int(value)')
            if counter.get('extra_life_at'):
                threshold = counter['extra_life_at']
                gd.raw(f'\t\t\twhile {bind} >= {threshold}:')
                gd.raw(f'\t\t\t\t{bind} -= {threshold}')
                gd.raw(f'\t\t\t\tlives += 1')
        for col in all_collections:
            bind = col['bind']
            gd.raw(f'\t\t"{bind}":')
            gd.raw(f'\t\t\t{bind} = int(value)')
        for slot in all_slots:
            bind = slot['bind']
            gd.raw(f'\t\t"{bind}":')
            gd.raw(f'\t\t\t{bind} = str(value)')
        gd.func_close()
        gd.blank()

        gd.func('set_time', 'value: int')
        for counter in all_counters:
            if counter.get('countdown'):
                bind = counter['bind']
                gd.line(f'{bind} = value')
        gd.func_close()
        gd.blank()

        gd.func('stop_timer')
        gd.line('_countdown_active = false')
        gd.func_close()
        gd.blank()

        gd.func('start_bonus_countdown')
        gd.line('_countdown_active = false')
        gd.line('_bonus_countdown_active = true')
        gd.func_close()
        gd.blank()

        gd.func('show_course_clear')
        gd.line('_course_clear = true')
        gd.func_close()

        content = gd.build()
        (scripts_dir / 'hud_manager.gd').write_text(content, encoding='utf-8')

    def _hud_res_path(self, src: str) -> str:
        """Convert a source path to a Godot resource path for HUD assets."""
        return f'res://{src}'

    def _write_game_over_screen(self, scripts_dir: Path, scene: SceneNode):
        """Write game_over_screen.gd when death_sequence='smw'."""
        death_sequence = getattr(scene, 'death_sequence', None)
        if death_sequence != 'smw':
            return

        alphabet = getattr(scene, 'game_over_alphabet', None) or 'assets/smw/sprites/hud_alphabet.png'
        jingle = getattr(scene, 'game_over_jingle', None) or 'assets/smw/sounds/smw_game_over.wav'
        vp_width = getattr(scene, 'viewport_width', None) or SNES_WIDTH

        content = GAME_OVER_SCREEN_GD.format(
            alphabet_path=_asset_path(alphabet),
            jingle_path=_asset_path(jingle),
            viewport_width=vp_width,
        )
        (scripts_dir / 'game_over_screen.gd').write_text(content, encoding='utf-8')

    def _resolve_asset_path(self, rel_path: str) -> Optional[Path]:
        """Resolve a relative asset path by searching upward from source dir."""
        search_dirs = []
        if self._source_dir:
            d = Path(self._source_dir)
            for _ in range(5):
                search_dirs.append(d)
                if d.parent == d:
                    break
                d = d.parent
        search_dirs.append(Path.cwd())
        for base in search_dirs:
            candidate = base / rel_path
            if candidate.exists():
                return candidate
        return None

    def _write_tilemap_assets(self, out: Path):
        """Copy external tilemap assets (JSON data, .tres tileset) to output."""
        import re
        for tilemap in self._tilemaps:
            data_src = tilemap.get('data_src')
            if not data_src:
                continue
            # Copy JSON data file (search upward from source dir)
            src_json = self._resolve_asset_path(data_src)
            if src_json:
                dst_json = out / src_json.name
                if not dst_json.exists():
                    shutil.copy2(str(src_json), str(dst_json))
            # Copy .tres tileset file and its referenced textures
            if tilemap['src']:
                src_tres = self._resolve_asset_path(tilemap['src'])
                if src_tres:
                    dst_tres = out / src_tres.name
                    if not dst_tres.exists():
                        shutil.copy2(str(src_tres), str(dst_tres))
                    # Parse .tres for ext_resource texture paths and copy them
                    try:
                        tres_text = src_tres.read_text(encoding='utf-8')
                        for m in re.finditer(r'path="res://([^"]+)"', tres_text):
                            res_path = m.group(1)
                            dst_res = out / res_path
                            if not dst_res.exists():
                                src_res = self._resolve_asset_path(res_path)
                                if src_res:
                                    dst_res.parent.mkdir(parents=True, exist_ok=True)
                                    shutil.copy2(str(src_res), str(dst_res))
                    except Exception:
                        pass

    def _write_tilemap_loader(self, scripts_dir: Path):
        """Write tilemap_loader.gd script for external JSON data mode."""
        has_data_src = any(t.get('data_src') for t in self._tilemaps)
        if not has_data_src:
            return
        # Use the first tilemap with data_src to determine the JSON path
        for tilemap in self._tilemaps:
            if tilemap.get('data_src'):
                json_name = Path(tilemap['data_src']).name
                json_path = f'res://{json_name}'
                content = TILEMAP_LOADER_GD.format(
                    json_path=json_path,
                    source_id=0,
                )
                (scripts_dir / 'tilemap_loader.gd').write_text(content, encoding='utf-8')
                break

    def _write_export_presets(self, out: Path):
        """Write export_presets.cfg for web export."""
        content = build_export_presets()
        (out / 'export_presets.cfg').write_text(content, encoding='utf-8')

    def _copy_assets(self, out: Path):
        """Copy all referenced asset files (sprites, sounds) to the output directory.

        Assets are resolved by searching upward from the source .q file directory
        until the asset path is found. Falls back to CWD if source_dir is not set.
        The _assets set contains paths like 'assets/smw/sprites/rex_walk.png'.
        """
        search_dirs = []
        if self._source_dir:
            # Search from source dir, then parent, then grandparent, etc.
            d = Path(self._source_dir)
            for _ in range(5):
                search_dirs.append(d)
                if d.parent == d:
                    break
                d = d.parent
        search_dirs.append(Path.cwd())

        for asset_rel in self._assets:
            dst = out / asset_rel
            for base in search_dirs:
                src = base / asset_rel
                if src.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(str(src), str(dst))
                    break

    # ------------------------------------------------------------------
    # Scene Script Generation
    # ------------------------------------------------------------------

    def _build_scene_script(self, scene: SceneNode) -> str:
        """Generate the main scene GDScript."""
        gd = GdScriptBuilder()
        gd.extends('Node2D')
        gd.blank()

        # Death sequence support
        death_sequence = getattr(scene, 'death_sequence', None)
        death_timer = getattr(scene, 'death_timer', 3.0)
        has_death = death_sequence is not None

        # Countdown HUD counter detection (for time-up handler)
        has_countdown = any(
            counter.get('countdown')
            for hud in self._huds
            for counter in hud.get('counters', [])
        )

        if has_death:
            gd.var('_is_dead', 'false', 'bool')
            gd.var('_death_timer', f'{death_timer}', 'float')
            gd.blank()

        # Infer enemy stomp behavior from EnemyNodes first, then PrefabNode fallback
        has_stomp_enemies = False
        stomp_prefabs = []
        stomp_enemies = []  # EnemyNode-based stomp data
        for enemy in self._enemies:
            if enemy.defeat and enemy.defeat.by == 'stomp':
                has_stomp_enemies = True
                stomp_enemies.append(enemy)
        # Legacy fallback: PrefabNode attrs (no EnemyNode defined)
        if not stomp_enemies:
            for pname, prefab in self._prefabs.items():
                if prefab.defeated_by == 'stomp':
                    has_stomp_enemies = True
                    stomp_prefabs.append(prefab)

        # Collect implicit state variables from event actions and HUD bindings
        declared_vars = {sv['name'] for sv in self._state_vars}
        for evt in self._events:
            for action in evt.get('actions', []):
                if action['action_type'] == 'set' and action.get('target'):
                    varname = action['target']
                    if varname not in declared_vars:
                        self._state_vars.append({'name': varname, 'value': '0'})
                        declared_vars.add(varname)
                elif action['action_type'] == 'score':
                    if 'score' not in declared_vars:
                        self._state_vars.append({'name': 'score', 'value': '0'})
                        declared_vars.add('score')
        for hud in self._huds:
            for counter in hud.get('counters', []):
                bind = counter.get('bind', '')
                if bind and bind not in declared_vars:
                    default_val = '300' if counter.get('countdown') else '0'
                    self._state_vars.append({'name': bind, 'value': default_val})
                    declared_vars.add(bind)
            for collection in hud.get('collections', []):
                bind = collection.get('bind', '')
                if bind and bind not in declared_vars:
                    self._state_vars.append({'name': bind, 'value': '0'})
                    declared_vars.add(bind)

        # Collect HUD binds for later use in event action handlers
        self._hud_binds = set()
        for hud in self._huds:
            for counter in hud.get('counters', []):
                if counter.get('bind'):
                    self._hud_binds.add(counter['bind'])
            for collection in hud.get('collections', []):
                if collection.get('bind'):
                    self._hud_binds.add(collection['bind'])

        # Auto-declare 'score' if stomp enemies present (stomp awards score)
        if has_stomp_enemies and 'score' not in declared_vars:
            self._state_vars.append({'name': 'score', 'value': '0'})
            declared_vars.add('score')

        # Auto-declare 'lives' for SMW death sequence (default 3)
        if has_death and death_sequence == 'smw':
            if 'lives' not in declared_vars:
                self._state_vars.append({'name': 'lives', 'value': '3'})
                declared_vars.add('lives')
            else:
                # Fix: if lives was auto-declared from HUD bind with 0, override to 3
                for sv in self._state_vars:
                    if sv['name'] == 'lives' and sv['value'] == '0':
                        sv['value'] = '3'
                        break

        # State variables
        if self._state_vars:
            gd.comment('State variables')
            for sv in self._state_vars:
                gd.var(sv['name'], sv['value'])
            gd.blank()

        # Checkpoint support
        if has_death and death_sequence == 'smw':
            gd.var('has_checkpoint', 'false', 'bool')
            gd.var('checkpoint_position', 'Vector2.ZERO', 'Vector2')
            gd.blank()

        # _ready
        gd.func('_ready')
        # Register all game entities with bridge (sprites + prefab instances)
        has_prefab_instances = bool(self._instances)
        if has_prefab_instances:
            gd.comment('Register all game entities with the bridge')
            gd.for_block('child', 'get_children()')
            gd.if_block('child.has_meta("tag") or child is CharacterBody2D or child is StaticBody2D')
            gd.line('QuantumBridge.register_sprite(child.name, child)')
            gd.block_close()
            gd.block_close()
        else:
            # No prefab instances — register declared sprites individually
            for sprite in self._sprites:
                sid = sprite['id']
                gd.line(f'QuantumBridge.register_sprite("{sid}", {_gd_node_ref(sid)})')
        gd.blank()

        # Event listeners — both explicit handlers and auto-generated action handlers
        if self._events:
            gd.comment('Event listeners')
            for evt in self._events:
                handler = evt['handler']
                actions = evt.get('actions', [])
                if handler:
                    gd.line(f'QuantumEventBus.listen("{evt["name"]}", Callable(self, "{handler}"))')
                elif actions:
                    # Auto-generate handler name from event name
                    safe_name = evt['name'].replace('-', '_')
                    gd.line(f'QuantumEventBus.listen("{evt["name"]}", Callable(self, "_on_{safe_name}"))')
            gd.blank()

        # Auto-listen for enemy-collision if we have stomp enemies
        if has_stomp_enemies:
            gd.line('QuantumEventBus.listen("enemy-collision", Callable(self, "_on_enemy_collision"))')
            gd.blank()

        # Auto-listen for fell-in-pit if sprites have death collision and death sequence exists
        has_death_collision = any(
            col.get('with_tag') == 'death'
            for sprite in self._sprites
            for col in sprite.get('on_collisions', [])
        )
        if has_death_collision and has_death:
            gd.line('QuantumEventBus.listen("fell-in-pit", Callable(self, "_on_fell_in_pit"))')
            gd.blank()

        # Auto-listen for time-up if countdown HUD exists
        has_countdown = any(
            counter.get('countdown')
            for hud in self._huds
            for counter in hud.get('counters', [])
        )
        if has_countdown and has_death:
            gd.line('QuantumEventBus.listen("time-up", Callable(self, "_on_time_up"))')
            gd.blank()

        # Timer connections
        for timer in self._timers:
            gd.line(f'${timer["id"]}.timeout.connect(Callable(self, "{timer["action"]}"))')

        # Collision signal connections (one connect per sprite, not per on_collision)
        for sprite in self._sprites:
            if sprite.get('on_collisions'):
                sid = sprite['id']
                gd.line(f'{_gd_node_ref(sid + "_area")}.body_entered.connect(_on_{sid}_collision)')
                gd.line(f'{_gd_node_ref(sid + "_area")}.area_entered.connect(_on_{sid}_area_entered)')

        # Tweens (auto-start)
        if self._tweens:
            gd.blank()
            gd.comment('Tweens')
            for tw in self._tweens:
                if tw['auto_start']:
                    target = tw['target']
                    prop = _quantum_prop_to_godot(tw['property'])
                    to_val = tw['to_value']
                    dur = tw['duration']
                    ease = EASING_MAP.get(tw['easing'], 'Tween.EASE_IN_OUT')
                    trans = TRANS_MAP.get(tw['easing'], 'Tween.TRANS_LINEAR')
                    gd.line(f'var tween_{tw["id"]} = create_tween()')
                    gd.line(f'tween_{tw["id"]}.tween_property(${target}, "{prop}", {to_val}, {dur}).set_ease({ease}).set_trans({trans})')
                    if tw['loop']:
                        gd.line(f'tween_{tw["id"]}.set_loops()')

        # Tilemap setup (only for inline CSV tilemaps; data_src tilemaps use loader script)
        csv_tilemaps = [t for t in self._tilemaps if not t.get('data_src')]
        if csv_tilemaps:
            gd.blank()
            gd.comment('Tilemap setup')
            gd.line('_setup_tilemaps()')

        # Connect checkpoint signals
        has_checkpoint_prefab = any(
            p.checkpoint or p.name == 'checkpoint' or (hasattr(p, 'tag') and getattr(p, 'tag', None) == 'checkpoint')
            for p in self._prefabs.values()
        )
        if has_checkpoint_prefab and has_death and death_sequence == 'smw':
            gd.blank()
            gd.comment('Connect checkpoint signals')
            gd.for_block('child', 'get_children()')
            gd.if_block('child.has_signal("checkpoint_activated")')
            gd.line('child.checkpoint_activated.connect(_on_checkpoint_activated)')
            gd.block_close()
            gd.block_close()

        # Game init (state restore, iris_in, HUD update, BGM)
        if has_death and death_sequence == 'smw':
            gd.blank()
            gd.line('on_game_init()')

        if not self._sprites and not self._events and not self._timers and not self._tilemaps and not has_death:
            gd.pass_stmt()

        gd.func_close()
        gd.blank()

        # Tilemap setup function (only for inline CSV data)
        if csv_tilemaps:
            gd.func('_setup_tilemaps')
            for tilemap in csv_tilemaps:
                tid = tilemap['id']
                tw = tilemap['tile_width']
                th = tilemap['tile_height']

                for layer in tilemap['layers']:
                    layer_name = f'{tid}_{layer["name"]}'
                    gd.comment(f'Setup {layer_name}')
                    gd.line(f'var tileset_{layer_name} = TileSet.new()')
                    gd.line(f'tileset_{layer_name}.tile_size = {gd_vector2i(tw, th)}')

                    if layer['collision']:
                        gd.line(f'tileset_{layer_name}.add_physics_layer()')

                    if tilemap['src']:
                        gd.line(f'var source_{layer_name} = TileSetAtlasSource.new()')
                        gd.line(f'source_{layer_name}.texture = load("res://{_asset_path(tilemap["src"])}")')
                        gd.line(f'source_{layer_name}.texture_region_size = {gd_vector2i(tw, th)}')
                        gd.line(f'tileset_{layer_name}.add_source(source_{layer_name})')

                    gd.line(f'${layer_name}.tile_set = tileset_{layer_name}')
                    gd.blank()

                    # Parse CSV data and set cells
                    gd.comment(f'Populate {layer_name} from data')
                    gd.line(f'var data_{layer_name} = {_csv_to_gd_array(layer["data"])}')
                    gd.for_block('row', f'range(data_{layer_name}.size())')
                    gd.for_block('col', f'range(data_{layer_name}[row].size())')
                    gd.if_block(f'data_{layer_name}[row][col] > 0')
                    # tile_id = data[row][col] - 1 (convert from 1-based to 0-based)
                    gd.line(f'var tile_id = data_{layer_name}[row][col] - 1')
                    # Calculate atlas coords from tile_id
                    # This depends on tileset width; default to simple approach
                    gd.line(f'${layer_name}.set_cell(Vector2i(col, row), 0, Vector2i(tile_id, 0))')
                    gd.block_close()  # if
                    gd.block_close()  # for col
                    gd.block_close()  # for row
                    gd.blank()

            gd.func_close()
            gd.blank()

        # on_game_init: state restore, iris_in, HUD update, BGM
        if has_death and death_sequence == 'smw':
            gd.func('on_game_init')
            gd.comment('Restore state from previous life')
            gd.line('var saved = QuantumBridge.get_game_state()')
            gd.if_block('saved.size() > 0')
            for sv in self._state_vars:
                gd.line(f'if saved.has("{sv["name"]}"): {sv["name"]} = saved["{sv["name"]}"]')
            gd.line('QuantumBridge.clear_game_state()')
            gd.block_close()
            gd.blank()
            # Iris in
            gd.line('QuantumBridge.iris_in(0.75)')
            gd.blank()
            # Update all HUD labels
            hud_binds = getattr(self, '_hud_binds', set())
            if hud_binds:
                gd.comment('Update HUD')
                for bind in sorted(hud_binds):
                    gd.line(f'$HUD.update_label("{bind}", str({bind}))')
                # Set time for countdown counters
                for hud in self._huds:
                    for counter in hud.get('counters', []):
                        if counter.get('countdown') and counter.get('bind'):
                            gd.line(f'$HUD.set_time({counter["bind"]})')
                gd.blank()
            # BGM auto-play for scene.start triggers
            bgm_sounds = [s for s in self._sounds if s.get('trigger') == 'scene.start']
            for sound in bgm_sounds:
                gd.line(f'QuantumBridge.play_sound("{sound["id"]}")')
            gd.func_close()
            gd.blank()

        # User-defined functions
        for func in self._functions:
            self._emit_function(gd, func)

        # Collision handler functions
        for sprite in self._sprites:
            if sprite.get('on_collisions'):
                sid = sprite['id']
                gd.func(f'_on_{sid}_collision', 'body: Node')
                for col in sprite['on_collisions']:
                    with_tag = col.get('with_tag', '')
                    action = col['action']
                    if with_tag:
                        gd.if_block(f'body.is_in_group("{with_tag}")')
                    self._emit_collision_action(gd, action, sid)
                    if with_tag:
                        gd.block_close()
                gd.func_close()
                gd.blank()

                # Area2D area_entered handler (delegates to body collision via parent)
                gd.func(f'_on_{sid}_area_entered', 'area: Area2D')
                gd.comment('Area2D parents are the actual game objects')
                gd.line(f'_on_{sid}_collision(area.get_parent())')
                gd.func_close()
                gd.blank()

        # --- Semantic: fell-in-pit handler ---
        if has_death_collision and has_death:
            gd.func('_on_fell_in_pit', '_data: Dictionary = {}')
            gd.if_block('_is_dead')
            gd.return_stmt()
            gd.block_close()
            gd.line('_kill_player()')
            gd.func_close()
            gd.blank()

        # --- Semantic: time-up handler ---
        if has_countdown and has_death:
            gd.func('_on_time_up', '_data: Dictionary = {}')
            gd.if_block('_is_dead')
            gd.return_stmt()
            gd.block_close()
            gd.line('_kill_player()')
            gd.func_close()
            gd.blank()

        # --- Semantic: stomp detection ---
        if has_stomp_enemies:
            gd.func('_on_enemy_collision', 'data: Dictionary')
            # Death guard
            gd.if_block('_is_dead')
            gd.return_stmt()
            gd.block_close()
            gd.line('var enemy = data.get("other")')
            gd.line('var normal_y = data.get("normal_y", 0.0)')
            gd.if_block('enemy == null')
            gd.return_stmt()
            gd.block_close()
            gd.comment('Stomp detection: player falling onto enemy from above')
            gd.if_block('normal_y < -0.5')
            # Cooldown check (500ms)
            gd.comment('Stomp cooldown (500ms)')
            gd.line('var now = Time.get_ticks_msec()')
            gd.if_block('enemy.has_meta("last_stomp_time") and now - enemy.get_meta("last_stomp_time") < 500')
            gd.return_stmt()
            gd.block_close()
            gd.line('enemy.set_meta("last_stomp_time", now)')
            gd.blank()
            gd.comment('Sound + camera shake')
            gd.line('QuantumBridge.play_sound("sfx-stomp")')
            gd.line('QuantumBridge.camera_shake(3.0, 0.15)')
            gd.blank()

            hud_binds = getattr(self, '_hud_binds', set())

            if stomp_enemies:
                # Data-driven stomp from EnemyNode definitions
                gd.comment('Data-driven stomp (from <qg:enemy> definitions)')
                for enemy in stomp_enemies:
                    prefab_name = enemy.prefab
                    meta_key = f'{prefab_name}_squished'
                    defeat = enemy.defeat
                    hit_score = defeat.on_hit.score if defeat and defeat.on_hit else 100
                    kill_score = defeat.on_kill.score if defeat and defeat.on_kill else 200
                    hit_effect = defeat.on_hit.effect if defeat and defeat.on_hit else 'squish'
                    kill_effect = defeat.on_kill.effect if defeat and defeat.on_kill else 'puff'
                    speed_mult = defeat.on_hit.speed_multiply if defeat and defeat.on_hit and defeat.on_hit.speed_multiply else None
                    bounce_val = defeat.bounce if defeat and defeat.bounce else -200

                    gd.if_block(f'enemy.get_meta("{meta_key}", false)')
                    # Second stomp: kill
                    gd.line(f'score += {kill_score}')
                    if kill_effect == 'puff':
                        gd.line('_spawn_puff(enemy.global_position)')
                    gd.line('QuantumBridge.destroy_sprite(enemy.name)')
                    gd.else_block()
                    # First stomp: squish
                    gd.line(f'enemy.set_meta("{meta_key}", true)')
                    if hit_effect == 'squish':
                        gd.line('var fh = enemy.frame_h if "frame_h" in enemy else 32.0')
                        gd.if_block('enemy.has_node("Sprite2D")')
                        gd.line('enemy.get_node("Sprite2D").scale.y = 0.5')
                        gd.line('enemy.get_node("Sprite2D").position.y += fh * 0.25')
                        gd.block_close()
                        gd.if_block('enemy.has_node("CollisionShape2D")')
                        gd.line('var col_shape = enemy.get_node("CollisionShape2D").shape')
                        gd.if_block('col_shape is RectangleShape2D')
                        gd.line('col_shape.size.y *= 0.5')
                        gd.line('enemy.get_node("CollisionShape2D").position.y += fh * 0.25')
                        gd.block_close()
                        gd.block_close()
                    if speed_mult:
                        gd.if_block('enemy.has_method("set_patrol")')
                        gd.line(f'enemy.set_patrol(enemy.patrol_speed * {speed_mult})')
                        gd.block_close()
                    gd.line(f'score += {hit_score}')
                    gd.block_close()
                    if 'score' in hud_binds:
                        gd.line('$HUD.update_label("score", str(score))')

                    # Bounce player
                    gd.comment('Bounce player after stomp')
                    player_id = None
                    for s in self._sprites:
                        if s.get('controls'):
                            player_id = s['id']
                            break
                    if player_id:
                        gd.line(f'var player = QuantumBridge.get_sprite("{player_id}")')
                        gd.if_block('player')
                        gd.if_block('player.has_method("stomp_bounce")')
                        gd.line(f'player.stomp_bounce({bounce_val})')
                        gd.else_block()
                        gd.line(f'player.velocity.y = {bounce_val}')
                        gd.block_close()
                        gd.block_close()
            else:
                # Legacy fallback: PrefabNode attrs
                gd.comment('Two-stage stomp: squish first, kill on second stomp')
                gd.if_block('enemy.get_meta("rex_squished", false)')
                # Second stomp: kill + puff
                gd.line('score += 200')
                gd.line('_spawn_puff(enemy.global_position)')
                gd.line('QuantumBridge.destroy_sprite(enemy.name)')
                gd.else_block()
                # First stomp: squish
                gd.line('enemy.set_meta("rex_squished", true)')
                gd.line('var fh = enemy.frame_h if "frame_h" in enemy else 32.0')
                gd.if_block('enemy.has_node("Sprite2D")')
                gd.line('enemy.get_node("Sprite2D").scale.y = 0.5')
                gd.line('enemy.get_node("Sprite2D").position.y += fh * 0.25')
                gd.block_close()
                gd.if_block('enemy.has_node("CollisionShape2D")')
                gd.line('var col_shape = enemy.get_node("CollisionShape2D").shape')
                gd.if_block('col_shape is RectangleShape2D')
                gd.line('col_shape.size.y *= 0.5')
                gd.line('enemy.get_node("CollisionShape2D").position.y += fh * 0.25')
                gd.block_close()
                gd.block_close()
                gd.if_block('enemy.has_method("set_patrol")')
                gd.line('enemy.set_patrol(80.0)')
                gd.block_close()
                gd.line('score += 100')
                gd.block_close()
                if 'score' in hud_binds:
                    gd.line('$HUD.update_label("score", str(score))')
                # Bounce player
                any_bounce = False
                for p in stomp_prefabs:
                    if p.stomp_bounce:
                        any_bounce = True
                        break
                if any_bounce:
                    bounce_val = stomp_prefabs[0].stomp_bounce or -200
                    gd.comment('Bounce player after stomp')
                    player_id = None
                    for s in self._sprites:
                        if s.get('controls'):
                            player_id = s['id']
                            break
                    if player_id:
                        gd.line(f'var player = QuantumBridge.get_sprite("{player_id}")')
                        gd.if_block('player')
                        gd.if_block('player.has_method("stomp_bounce")')
                        gd.line(f'player.stomp_bounce({bounce_val})')
                        gd.else_block()
                        gd.line(f'player.velocity.y = {bounce_val}')
                        gd.block_close()
                        gd.block_close()

            gd.else_block()
            gd.comment('Enemy hit player from side/below')
            gd.line('_kill_player()')
            gd.block_close()
            gd.func_close()
            gd.blank()

            # _spawn_puff helper
            gd.func('_spawn_puff', 'pos: Vector2')
            gd.line('var puff = Sprite2D.new()')
            gd.line('puff.global_position = pos')
            gd.line('var img = Image.create(8, 8, false, Image.FORMAT_RGBA8)')
            gd.line('img.fill(Color.WHITE)')
            gd.line('puff.texture = ImageTexture.create_from_image(img)')
            gd.line('add_child(puff)')
            gd.line('var tween = create_tween()')
            gd.line('tween.set_parallel(true)')
            gd.line('tween.tween_property(puff, "scale", Vector2(4.0, 4.0), 0.3)')
            gd.line('tween.tween_property(puff, "modulate:a", 0.0, 0.3)')
            gd.line('tween.set_parallel(false)')
            gd.line('tween.tween_callback(puff.queue_free)')
            gd.func_close()
            gd.blank()

        # --- Semantic: death sequence ---
        if has_death:
            # Find player
            player_id = None
            for s in self._sprites:
                if s.get('controls'):
                    player_id = s['id']
                    break

            gd.func('_kill_player')
            gd.if_block('_is_dead')
            gd.return_stmt()
            gd.block_close()
            gd.assign('_is_dead', 'true')

            if death_sequence == 'smw':
                # Decrement lives + HUD update
                gd.line('lives -= 1')
                hud_binds = getattr(self, '_hud_binds', set())
                if 'lives' in hud_binds:
                    gd.line('$HUD.update_label("lives", str(lives))')
                gd.blank()
                # Force enemies to pausable so they freeze
                gd.comment('Freeze enemies')
                gd.for_block('child', 'get_children()')
                gd.if_block('child.has_meta("tag") and child.get_meta("tag") == "enemy"')
                gd.line('child.process_mode = Node.PROCESS_MODE_PAUSABLE')
                gd.block_close()
                gd.block_close()
                gd.blank()
                # Scene stays processing during pause
                gd.line('process_mode = Node.PROCESS_MODE_ALWAYS')
                gd.blank()
                # Death SFX (must keep playing during pause)
                gd.line('var sfx = get_node_or_null("Sounds/sfx-death")')
                gd.if_block('sfx')
                gd.line('sfx.process_mode = Node.PROCESS_MODE_ALWAYS')
                gd.line('sfx.play()')
                gd.block_close()
                # Stop BGM
                bgm_sounds = [s for s in self._sounds if s.get('trigger') == 'scene.start']
                if bgm_sounds:
                    bgm_id = bgm_sounds[0]['id']
                    gd.line(f'var bgm = get_node_or_null("Sounds/{bgm_id}")')
                    gd.if_block('bgm')
                    gd.line('bgm.stop()')
                    gd.block_close()
                gd.blank()
                # Kill player visual
                if player_id:
                    gd.line(f'QuantumBridge.kill_player("{player_id}")')
                gd.blank()
                # Pause tree
                gd.line('get_tree().paused = true')
                gd.blank()
                # Timer with PROCESS_MODE_ALWAYS (create_timer doesn't work in pause!)
                gd.comment('Manual Timer with PROCESS_MODE_ALWAYS (works during pause)')
                gd.line('var t = Timer.new()')
                gd.line('t.wait_time = _death_timer')
                gd.line('t.one_shot = true')
                gd.line('t.process_mode = Node.PROCESS_MODE_ALWAYS')
                gd.line('add_child(t)')
                gd.line('t.timeout.connect(_on_death_complete)')
                gd.line('t.start()')
            elif death_sequence == 'instant':
                gd.line('get_tree().reload_current_scene()')
            elif death_sequence == 'respawn':
                if player_id:
                    gd.line(f'QuantumBridge.respawn("{player_id}", 0, 0)')
                gd.assign('_is_dead', 'false')
            gd.func_close()
            gd.blank()

            if death_sequence == 'smw':
                gd.func('_on_death_complete')
                # Iris out
                gd.line('QuantumBridge.iris_out(0.6)')
                gd.line('var iris_timer = Timer.new()')
                gd.line('iris_timer.wait_time = 0.7')
                gd.line('iris_timer.one_shot = true')
                gd.line('iris_timer.process_mode = Node.PROCESS_MODE_ALWAYS')
                gd.line('add_child(iris_timer)')
                gd.line('iris_timer.start()')
                gd.line('await iris_timer.timeout')
                gd.blank()
                # Game over check
                gd.if_block('lives <= 0')
                gd.line('_show_game_over()')
                gd.return_stmt()
                gd.block_close()
                gd.blank()
                # Resume before checkpoint/reload
                gd.line('get_tree().paused = false')
                gd.if_block('has_checkpoint')
                gd.line('_respawn_at_checkpoint()')
                gd.else_block()
                # Save state + reload
                state_dict_parts = []
                for sv in self._state_vars:
                    state_dict_parts.append(f'"{sv["name"]}": {sv["name"]}')
                state_dict = '{' + ', '.join(state_dict_parts) + '}'
                gd.line(f'QuantumBridge.save_game_state({state_dict})')
                gd.line('get_tree().reload_current_scene()')
                gd.block_close()
                gd.func_close()
                gd.blank()

                # _show_game_over
                gd.func('_show_game_over')
                gd.comment('Stop HUD timer')
                gd.line('$HUD.stop_timer()')
                gd.blank()
                gd.line('var go_screen = load("res://scripts/game_over_screen.gd").new()')
                gd.line('go_screen.process_mode = Node.PROCESS_MODE_ALWAYS')
                gd.line('add_child(go_screen)')
                gd.line('await go_screen.game_over_finished')
                gd.line('go_screen.queue_free()')
                gd.blank()
                gd.comment('Fresh restart')
                gd.line('get_tree().paused = false')
                gd.line('QuantumBridge.clear_game_state()')
                gd.line('get_tree().reload_current_scene()')
                gd.func_close()
                gd.blank()

                # Checkpoint handlers
                gd.func('_on_checkpoint_activated', 'spawn_pos: Vector2')
                gd.assign('has_checkpoint', 'true')
                gd.assign('checkpoint_position', 'spawn_pos')
                gd.func_close()
                gd.blank()

                gd.func('_respawn_at_checkpoint')
                gd.assign('_is_dead', 'false')
                if player_id:
                    gd.line(f'var {player_id}_node = {_gd_node_ref(player_id)}')
                    gd.if_block(f'{player_id}_node')
                    gd.line(f'{player_id}_node.is_dead = false')
                    gd.line(f'{player_id}_node.position = checkpoint_position')
                    gd.line(f'{player_id}_node.velocity = Vector2.ZERO')
                    gd.line(f'{player_id}_node.collision_layer = 1')
                    gd.line(f'{player_id}_node.collision_mask = 1 | 2')
                    gd.line(f'{player_id}_node.process_mode = Node.PROCESS_MODE_INHERIT')
                    gd.comment('Restore sprite')
                    gd.line(f'var sprite = {player_id}_node.get_node_or_null("Sprite2D")')
                    gd.if_block(f'sprite and {player_id}_node._normal_texture')
                    gd.line(f'sprite.texture = {player_id}_node._normal_texture')
                    gd.line('sprite.hframes = 5')
                    gd.line('sprite.frame = 0')
                    gd.line('sprite.flip_h = false')
                    gd.block_close()
                    gd.block_close()
                gd.blank()
                # Resume BGM
                bgm_sounds = [s for s in self._sounds if s.get('trigger') == 'scene.start']
                if bgm_sounds:
                    bgm_id = bgm_sounds[0]['id']
                    gd.line(f'var bgm = get_node_or_null("Sounds/{bgm_id}")')
                    gd.if_block('bgm')
                    gd.line('bgm.play()')
                    gd.block_close()
                gd.blank()
                gd.line('QuantumBridge.iris_in(0.5)')
                hud_binds = getattr(self, '_hud_binds', set())
                if 'lives' in hud_binds:
                    gd.line('$HUD.update_label("lives", str(lives))')
                gd.func_close()
                gd.blank()

        # --- Semantic: event action handlers ---
        for evt in self._events:
            actions = evt.get('actions', [])
            if actions and not evt['handler']:
                safe_name = evt['name'].replace('-', '_')
                gd.func(f'_on_{safe_name}', 'data: Dictionary = {}')
                for action in actions:
                    self._emit_event_action(gd, action)
                gd.func_close()
                gd.blank()

        return gd.build()

    def _emit_event_action(self, gd: GdScriptBuilder, action: dict):
        """Emit GDScript code for a single event action."""
        atype = action['action_type']
        target = action.get('target')
        value = action.get('value')
        amount = action.get('amount')

        if atype == 'score':
            amt = amount or 0
            hud_binds = getattr(self, '_hud_binds', set())
            if 'score' in hud_binds:
                gd.line(f'score += {amt}')
                gd.line(f'$HUD.update_label("score", str(score))')
            else:
                gd.line(f'QuantumEventBus.emit_event("score-changed", {{"amount": {amt}}})')
        elif atype == 'destroy':
            if target and '{data' in target:
                # Dynamic target from event data
                key = target.replace('{', '').replace('}', '')
                gd.line(f'var target = {key}')
                gd.if_block('target and target.has_method("queue_free")')
                gd.line('target.queue_free()')
                gd.block_close()
            elif target:
                gd.line(f'QuantumBridge.destroy_sprite("{target}")')
        elif atype == 'sound':
            sound_id = target or ''
            gd.line(f'QuantumBridge.play_sound("{sound_id}")')
        elif atype == 'camera-shake':
            if value:
                parts = value.split(',')
                intensity = parts[0].strip() if len(parts) > 0 else '5.0'
                duration = parts[1].strip() if len(parts) > 1 else '0.3'
                gd.line(f'QuantumBridge.camera_shake({intensity}, {duration})')
            else:
                gd.line('QuantumBridge.camera_shake()')
        elif atype == 'set':
            if target and value:
                # Simple set: target is variable name
                gd.assign(target, str(value).replace('{', '').replace('}', ''))
            elif target:
                gd.assign(target, '0')
            # Update HUD if variable is bound
            hud_binds = getattr(self, '_hud_binds', set())
            if target and target in hud_binds:
                gd.line(f'$HUD.update_label("{target}", str({target}))')
        elif atype == 'emit':
            event_name = value or ''
            gd.line(f'QuantumEventBus.emit_event("{event_name}", data)')
        elif atype == 'spawn':
            gd.comment(f'spawn: {target} at {value}')

    def _emit_function(self, gd: GdScriptBuilder, func: FunctionNode):
        """Emit a user-defined function."""
        name = func.name
        params = ''
        # Check for lang attribute to determine if it's GDScript
        lang = getattr(func, 'lang', None)

        gd.func(name, 'data: Dictionary = {}')

        # Get function body
        body = getattr(func, 'body', [])
        if isinstance(body, str):
            # Raw code string
            for line in body.strip().split('\n'):
                gd.line(line.strip())
        elif isinstance(body, list):
            has_content = False
            for child in body:
                if isinstance(child, RawCodeNode):
                    for line in child.code.strip().split('\n'):
                        gd.line(line.strip())
                    has_content = True
                elif isinstance(child, SetNode):
                    gd.assign(child.name, str(child.value))
                    has_content = True
            if not has_content:
                gd.pass_stmt()
        else:
            gd.pass_stmt()

        gd.func_close()
        gd.blank()

    def _emit_collision_action(self, gd: GdScriptBuilder, action: str, sprite_id: str):
        """Emit code for a collision action. Supports compound actions separated by ';'."""
        parts = [a.strip() for a in action.split(';')]
        for part in parts:
            self._emit_single_collision_action(gd, part, sprite_id)

    def _emit_single_collision_action(self, gd: GdScriptBuilder, action: str, sprite_id: str):
        """Emit code for a single collision action."""
        if action == 'destroy-self':
            gd.line(f'QuantumBridge.destroy_sprite("{sprite_id}")')
        elif action == 'destroy-other' or action == 'destroy':
            gd.line('body.queue_free()')
        elif action.startswith('emit:'):
            event_name = action[5:]
            gd.line(f'QuantumBridge.emit_event("{event_name}", {{"self_id": "{sprite_id}", "other": body}})')
        elif action:
            gd.comment(f'Unknown action: {action}')


# ==========================================================================
# Utility functions
# ==========================================================================

def _gd_node_ref(node_id: str) -> str:
    """Build a safe GDScript node reference ($name or $"name-with-hyphens")."""
    if '-' in node_id or ' ' in node_id:
        return f'$"{node_id}"'
    return f'${node_id}'


def _node_path(parent: str, child: str) -> str:
    """Build a Godot scene tree path."""
    if parent == '.':
        return child
    return f'{parent}/{child}'


def _asset_path(src: str) -> str:
    """Normalize asset path — avoid double 'assets/' prefix.

    If src already starts with 'assets/', keep as-is.
    Otherwise prepend 'assets/'.
    """
    if src.startswith('assets/') or src.startswith('assets\\'):
        return src
    return f'assets/{src}'


def _csv_to_gd_array(csv_data: str) -> str:
    """Convert CSV tile data to GDScript 2D array literal."""
    rows = []
    for line in csv_data.strip().split('\n'):
        line = line.strip().rstrip(',')
        if not line:
            continue
        cells = [c.strip() for c in line.split(',') if c.strip()]
        rows.append('[' + ', '.join(cells) + ']')
    return '[' + ', '.join(rows) + ']'


def _quantum_prop_to_godot(prop: str) -> str:
    """Map Quantum property names to Godot property paths."""
    mapping = {
        'x': 'position:x',
        'y': 'position:y',
        'alpha': 'modulate:a',
        'rotation': 'rotation',
        'scale': 'scale:x',
        'scale_x': 'scale:x',
        'scale_y': 'scale:y',
    }
    return mapping.get(prop, prop)


def _sanitize_name(name: str) -> str:
    """Convert a scene name like 'world-map' to 'world_map' for filenames."""
    return name.replace('-', '_').replace(' ', '_').lower()


def _pascal_case(name: str) -> str:
    """Convert 'world-map' or 'world_map' to 'WorldMap' for Godot node names."""
    parts = name.replace('-', '_').split('_')
    return ''.join(p.capitalize() for p in parts)
