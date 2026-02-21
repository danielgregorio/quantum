"""
Game Engine 2D - Code Generator

Transforms Game AST nodes into JavaScript code that runs with PixiJS + Matter.js.
This is a compiler/transpiler: Python generates JS, the game runs 100% in the browser.

Uses JsBuilder for structured, safe JS generation - no fragile string concatenation.
"""

import json
import re
from typing import List, Dict, Any, Optional

from core.features.game_engine_2d.src.ast_nodes import (
    SceneNode, SpriteNode, PhysicsNode, ColliderNode, AnimationNode,
    CameraNode, InputNode, SoundNode, ParticleNode, TimerNode,
    SpawnNode, HudNode, TweenNode, TilemapNode, TilemapLayerNode,
    BehaviorNode, UseNode, PrefabNode, InstanceNode, GroupNode,
    StateMachineNode, StateNode, TransitionNode, RawCodeNode,
    ClickableNode, EventNode, OnCollisionNode,
)
from core.ast_nodes import QuantumNode, HTMLNode, TextNode
from core.features.conditionals.src.ast_node import IfNode
from core.features.loops.src.ast_node import LoopNode
from core.features.state_management.src.ast_node import SetNode
from core.features.functions.src.ast_node import FunctionNode

from runtime.game_templates import (
    HTML_TEMPLATE, PIXI_CDN, MATTER_CDN, HUD_DIV_TEMPLATE,
    JsBuilder, js_string, js_id, js_number, js_bool, js_safe_value,
    is_number, sanitize_hud_text, compile_binding_to_js,
    emit_physics_sync, emit_input_system, emit_animation_system,
    emit_easing_functions, emit_tween_system, emit_particle_system,
    emit_audio_system, emit_timer_system,
    emit_event_bus, emit_game_api, emit_spawn_system,
    emit_mouse_system,
)


class GameCodeGenerator:
    """Generates standalone HTML+JS from a game AST."""

    def __init__(self):
        self._sprites: List[Dict] = []
        self._behaviors: Dict[str, BehaviorNode] = {}
        self._prefabs: Dict[str, PrefabNode] = {}
        self._state_vars: List[Dict] = []  # {name, value, type}
        self._functions: List[FunctionNode] = []
        self._sounds: List[Dict] = []
        self._particles: List[Dict] = []
        self._timers: List[Dict] = []
        self._tweens: List[Dict] = []
        self._huds: List[Dict] = []
        self._custom_inputs: List[Dict] = []
        self._events: List[Dict] = []  # qg:event declarations
        self._camera: Optional[Dict] = None
        self._physics: Optional[Dict] = None
        self._assets: set = set()
        self._sprite_counter: int = 0
        self._scene_width: int = 800
        self._scene_height: int = 600
        self._spawners: List[Dict] = []
        self._visual_tile_layers: List[Dict] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, scene: SceneNode, behaviors: List[BehaviorNode] = None,
                 prefabs: List[PrefabNode] = None, title: str = "Quantum Game",
                 source_code: str = None) -> str:
        """Generate full HTML from a SceneNode."""
        self._scene_width = scene.width
        self._scene_height = scene.height

        for b in (behaviors or []):
            self._behaviors[b.name] = b
        for p in (prefabs or []):
            self._prefabs[p.name] = p

        self._process_scene_children(scene.children)

        js = JsBuilder()
        self._build_game_js(js, scene)
        game_js = js.build()

        hud_html = self._build_hud_html()

        # Format source code with syntax highlighting
        formatted_source = self._format_source_code(source_code) if source_code else "No source code available"

        return HTML_TEMPLATE.format(
            title=html_escape_title(title),
            pixi_cdn=PIXI_CDN,
            matter_cdn=MATTER_CDN,
            hud_html=hud_html,
            game_js=game_js,
            source_code=formatted_source,
        )

    def _format_source_code(self, source: str) -> str:
        """Format source code with HTML escaping only (clean display)."""
        import html
        # Just escape HTML entities - keep it simple and clean
        return html.escape(source)

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
        self._sprite_counter = 0
        self._spawners = []
        self._visual_tile_layers = []

    def generate_multi(self, scenes: List[SceneNode], initial: str,
                       behaviors: List[BehaviorNode] = None,
                       prefabs: List[PrefabNode] = None,
                       title: str = "Quantum Game",
                       source_code: str = None) -> str:
        """Generate HTML with multiple scenes and scene switching."""
        if not scenes:
            return self.generate(SceneNode('empty'), behaviors, prefabs, title, source_code)

        # Use initial/active scene dimensions for PIXI app
        first = scenes[0]
        for sc in scenes:
            if sc.name == initial:
                first = sc
                break
        self._scene_width = first.width
        self._scene_height = first.height

        for b in (behaviors or []):
            self._behaviors[b.name] = b
        for p in (prefabs or []):
            self._prefabs[p.name] = p

        # Collect all assets across all scenes
        for scene in scenes:
            self._reset_scene_state()
            self._process_scene_children(scene.children)

        # Now build the JS
        js = JsBuilder()
        js.line("(async function() {")
        js.indent()

        # PIXI App
        js.section("PIXI APP")
        js.const('app', 'new PIXI.Application()')
        js.line(f"await app.init({{ width: {first.width}, height: {first.height}, background: {js_string(first.background)} }});")
        js.line("document.body.appendChild(app.canvas);")

        # Matter.js Engine
        js.section("MATTER.JS ENGINE")
        js.const('mEngine', 'Matter.Engine.create()')
        js.assign('mEngine.gravity.x', '0')
        js.assign('mEngine.gravity.y', '0')
        js.const('mWorld', 'mEngine.world')

        # Event Bus
        js.section("EVENT BUS")
        emit_event_bus(js)

        # Shared state (merged from all scenes)
        js.section("GAME STATE")
        js.comment('State variables are initialized per-scene')

        # Asset Loading (collect from all scenes)
        all_assets = set()
        for scene in scenes:
            self._reset_scene_state()
            self._process_scene_children(scene.children)
            all_assets.update(self._assets)
        js.section("ASSET LOADING")
        if all_assets:
            urls = sorted(all_assets)
            asset_list = ', '.join(js_string(u) for u in urls)
            js.line(f"await PIXI.Assets.load([{asset_list}]);")
        else:
            js.comment('No assets to preload')

        # Animation System
        js.section("ANIMATION SYSTEM")
        emit_animation_system(js)

        # Behaviors (shared)
        js.section("BEHAVIORS")
        self._emit_behaviors(js)

        # Camera container
        js.section("CAMERA")
        js.const('_cameraContainer', 'new PIXI.Container()')
        js.line("app.stage.addChild(_cameraContainer);")
        js.func('updateCamera')
        js.block_close()

        # Shared sprite/body registries
        js.section("SPRITES & BODIES")
        js.const('_sprites', '{}')
        js.const('_bodyToSprite', '{}')
        emit_physics_sync(js)

        # Game API
        js.section("GAME API")
        emit_game_api(js)

        # Input
        js.section("INPUT")
        emit_input_system(js)
        js.const('_controlledSprites', '{}')

        # Particle system
        js.section("PARTICLES")
        emit_particle_system(js)

        # Timer system
        js.section("TIMERS")
        emit_timer_system(js)

        # Tween system
        js.section("TWEENS")
        emit_tween_system(js)

        # Sound system
        js.section("SOUNDS")
        emit_audio_system(js)

        # Teardown function
        js.section("MULTI-SCENE")
        js.func('_teardownScene')
        js.line('_cameraContainer.removeChildren();')
        js.line('Matter.Composite.clear(mWorld, false);')
        js.line("for (const id in _sprites) delete _sprites[id];")
        js.line("for (const id in _bodyToSprite) delete _bodyToSprite[id];")
        js.line("for (const id in _controlledSprites) delete _controlledSprites[id];")
        js.block_close()
        js.blank()

        js.const('_sceneInits', '{}')
        js.blank()

        # Generate init function per scene
        for scene in scenes:
            self._reset_scene_state()
            self._process_scene_children(scene.children)
            scene_name = js_id(scene.name)

            js.line(f"_sceneInits[{js_string(scene.name)}] = async function() {{")
            js.indent()

            # Physics config for this scene
            if self._physics:
                js.assign('mEngine.gravity.x', js_number(self._physics['gravity_x']))
                js.assign('mEngine.gravity.y', js_number(self._physics['gravity_y']))

            # State vars
            for sv in self._state_vars:
                name = js_id(sv['name'])
                val = js_safe_value(sv['value'], sv['type'])
                js.line(f"var {name} = {val};")

            # Sprites & Bodies
            body_vars = []
            for info in self._sprites:
                sid = js_id(info['id'])
                src = info['src']
                x, y = js_number(info['x']), js_number(info['y'])
                spr_var = f'_spr_{sid}'

                if src:
                    js.const(spr_var, f"PIXI.Sprite.from({js_string(src)})")
                else:
                    js.const(spr_var, 'new PIXI.Graphics()')
                    if info.get('width') and info.get('height'):
                        w, h = info['width'], info['height']
                        js.line(f"{spr_var}.rect(-{w/2}, -{h/2}, {w}, {h});")
                        # Use color if provided, otherwise default to a visible color
                        color = info.get('color')
                        if color:
                            hex_color = color.lstrip('#')
                            js.line(f"{spr_var}.fill({{ color: 0x{hex_color} }});")
                        else:
                            js.line(f"{spr_var}.fill({{ color: 0x4a9eff }});")

                js.assign(f'{spr_var}.x', x)
                js.assign(f'{spr_var}.y', y)
                if src:
                    js.line(f"{spr_var}.anchor.set({js_number(info['anchor_x'])}, {js_number(info['anchor_y'])});")
                # Only set width/height if NOT using frame-based animations
                # (animations will handle sizing via frame textures)
                has_frame_anims = info.get('frame_width') and info.get('frame_height')
                if info.get('width') and src and not has_frame_anims:
                    js.assign(f'{spr_var}.width', js_number(info['width']))
                if info.get('height') and src and not has_frame_anims:
                    js.assign(f'{spr_var}.height', js_number(info['height']))
                js.line(f"_cameraContainer.addChild({spr_var});")

                body_var = self._emit_body(js, info, sid)
                if body_var:
                    body_vars.append(body_var)
                    js.assign(f'_bodyToSprite[{body_var}.id]', js_string(info['id']))

                # Clickable setup (multi-scene)
                if info.get('clickable'):
                    cursor = info['clickable'].get('cursor', 'pointer')
                    action = js_id(info['clickable']['action'])
                    js.assign(f"{spr_var}.eventMode", "'static'")
                    js.assign(f"{spr_var}.cursor", js_string(cursor))
                    sid_str_click = js_string(info['id'])
                    js.line(f"{spr_var}.on('pointerdown', (e) => {{")
                    js.indent()
                    js.const('_info', f'_sprites[{sid_str_click}]')
                    js.let('_handled', 'false')
                    js.if_block('_info && _info.behaviors')
                    js.for_of('_b', '_info.behaviors')
                    js.if_block(f"typeof _b.{action} === 'function'")
                    js.line(f"_b.{action}(e);")
                    js.assign('_handled', 'true')
                    js.block_close()
                    js.block_close()
                    js.block_close()
                    js.if_block(f"!_handled && typeof {action} === 'function'")
                    js.line(f"{action}(_info, e);")
                    js.block_close()
                    js.dedent()
                    js.line("});")

                body_ref = f'_body_{sid}' if info.get('body') else 'null'
                tag_ref = js_string(info['tag']) if info.get('tag') else 'null'
                id_ref = js_string(info['id'])
                js.line(f"_sprites[{id_ref}] = {{ id: {id_ref}, sprite: {spr_var}, body: {body_ref}, tag: {tag_ref}, collisionHandlers: [], behaviors: [] }};")

            if body_vars:
                js.line(f"Matter.Composite.add(mWorld, [{', '.join(body_vars)}]);")

            # Behavior attachments for this scene
            self._emit_behavior_attachments(js)

            # Animations
            self._emit_animation_registration(js)

            # Controlled sprites
            for info in self._sprites:
                if info.get('controls'):
                    ctrl = info['controls']
                    sid_str = js_string(info['id'])
                    if ctrl == 'wasd':
                        js.assign(f'_controlledSprites[{sid_str}]',
                                  "{ left: 'a', right: 'd', up: 'w', jump: ' ' }")
                    elif ctrl == 'arrows':
                        js.assign(f'_controlledSprites[{sid_str}]',
                                  "{ left: 'ArrowLeft', right: 'ArrowRight', up: 'ArrowUp', jump: 'ArrowUp' }")

            # Camera
            if self._camera and self._camera.get('follow'):
                target = js_string(self._camera['follow'])
                lerp = js_number(self._camera['lerp'])
                js.assign('updateCamera', f"function() {{ const info = _sprites[{target}]; if (!info) return; const tx = app.screen.width / 2 - info.sprite.x; const ty = app.screen.height / 2 - info.sprite.y; _cameraContainer.x += (tx - _cameraContainer.x) * {lerp}; _cameraContainer.y += (ty - _cameraContainer.y) * {lerp}; }}")

            # Functions
            for fn in self._functions:
                params = ', '.join(js_id(p.name) for p in fn.params)
                js.func(js_id(fn.name), params)
                for stmt in fn.body:
                    self._emit_statement(js, stmt)
                js.block_close()

            # Collision handler
            self._emit_collision_handler(js)

            # Sounds
            for s in self._sounds:
                js.line(f"await _loadSound({js_string(s['id'])}, {js_string(s['src'])});")

            # Particle instances
            self._emit_particle_instances(js)

            # Timer instances
            self._emit_timer_instances(js)

            # Tween instances
            self._emit_tween_instances(js)

            # Scene start triggers
            self._emit_scene_start(js)

            js.dedent()
            js.line("};")
            js.blank()

        # Load scene function
        js.func('_loadScene', 'name')
        js.line('_teardownScene();')
        js.if_block('_sceneInits[name]')
        js.line('_sceneInits[name]();')
        js.block_close()
        js.block_close()
        js.blank()

        # HUD update placeholder
        js.section("HUD UPDATE")
        js.func('_updateHUD')
        js.block_close()

        # Game Loop
        js.section("GAME LOOP")
        self._emit_game_loop_multi(js)

        # Initial scene load
        js.line(f"_loadScene({js_string(initial)});")

        js.dedent()
        js.line("})();")

        game_js = js.build()

        # Collect all HUD HTML from all scenes
        all_hud_html_parts = []
        for scene in scenes:
            self._reset_scene_state()
            self._process_scene_children(scene.children)
            hud_html = self._build_hud_html()
            if hud_html:
                all_hud_html_parts.append(hud_html)

        # Format source code with syntax highlighting
        formatted_source = self._format_source_code(source_code) if source_code else "No source code available"

        return HTML_TEMPLATE.format(
            title=html_escape_title(title),
            pixi_cdn=PIXI_CDN,
            matter_cdn=MATTER_CDN,
            hud_html='\n'.join(all_hud_html_parts),
            game_js=game_js,
            source_code=formatted_source,
        )

    def _emit_game_loop_multi(self, js: JsBuilder):
        """Game loop for multi-scene mode."""
        js.line("app.ticker.add((ticker) => {")
        js.indent()
        js.const('dt', 'ticker.deltaTime')
        js.comment('Sub-step physics with velocity clamping to prevent tunneling')
        js.const('_fixedDt', '16.67')
        js.const('_maxSteps', '3')
        js.const('_maxVel', '12')
        js.const('_steps', 'Math.min(Math.ceil(dt), _maxSteps)')
        js.for_range('_i', '0', '_steps')
        js.for_entries('_sid', '_sinfo', '_sprites')
        js.if_block('_sinfo.body && !_sinfo.body.isStatic')
        js.const('_bv', '_sinfo.body.velocity')
        js.if_block('Math.abs(_bv.x) > _maxVel || Math.abs(_bv.y) > _maxVel')
        js.line('Matter.Body.setVelocity(_sinfo.body, { x: Math.max(-_maxVel, Math.min(_maxVel, _bv.x)), y: Math.max(-_maxVel, Math.min(_maxVel, _bv.y)) });')
        js.block_close()
        js.block_close()
        js.block_close()
        js.line('Matter.Engine.update(mEngine, _fixedDt);')
        js.block_close()
        js.line('syncPhysics();')
        js.comment('Input handling')
        js.for_entries('_sid', '_ctrl', '_controlledSprites')
        js.const('_body', '_sprites[_sid] && _sprites[_sid].body')
        js.if_block('!_body')
        js.line('continue;')
        js.block_close()
        js.if_block('_keys[_ctrl.left]')
        js.line("Matter.Body.setVelocity(_body, { x: -5, y: _body.velocity.y });")
        js.block_close()
        js.if_block('_keys[_ctrl.right]')
        js.line("Matter.Body.setVelocity(_body, { x: 5, y: _body.velocity.y });")
        js.block_close()
        js.if_block('_justPressed[_ctrl.jump]')
        js.line("Matter.Body.setVelocity(_body, { x: _body.velocity.x, y: -10 });")
        js.line("_gameEvents.emit('player.jump', _sprites[_sid]);")
        js.block_close()
        js.if_block('!_keys[_ctrl.left] && !_keys[_ctrl.right]')
        js.line("Matter.Body.setVelocity(_body, { x: _body.velocity.x * 0.8, y: _body.velocity.y });")
        js.block_close()
        js.block_close()
        js.line('_clearJustPressed();')
        js.line('updateCamera();')
        js.line('_updateControlAnimations();')
        js.line('_updateAnimatedSprites(ticker);')
        js.comment('Behaviors update')
        js.for_entries('_id', '_info', '_sprites')
        js.if_block('_info.behaviors')
        js.for_of('b', '_info.behaviors')
        js.if_block('b._smUpdate')
        js.line('b._smUpdate();')
        js.block_close()
        js.if_block('b.update')
        js.line('b.update();')
        js.block_close()
        js.block_close()
        js.block_close()
        js.block_close()
        js.line('_updateTimers(dt);')
        js.line('_updateTweens(dt);')
        js.line('_updateParticles(dt);')
        js.line('_updateHUD();')
        js.dedent()
        js.line("});")

    # ------------------------------------------------------------------
    # Scene children processing
    # ------------------------------------------------------------------

    def _process_scene_children(self, children: List[QuantumNode]):
        for child in children:
            if isinstance(child, PhysicsNode):
                self._physics = {
                    'gravity_x': child.gravity_x,
                    'gravity_y': child.gravity_y,
                    'bounds': child.bounds,
                    'debug': child.debug,
                }
            elif isinstance(child, CameraNode):
                self._camera = {
                    'follow': child.follow,
                    'lerp': child.lerp,
                    'bounds': child.bounds or 'none',
                }
            elif isinstance(child, SetNode):
                self._state_vars.append({
                    'name': child.name,
                    'value': child.value if child.value is not None else (child.default if child.default is not None else ''),
                    'type': child.type or 'string',
                })
            elif isinstance(child, FunctionNode):
                self._functions.append(child)
            elif isinstance(child, PrefabNode):
                # Register prefab for later instantiation
                self._prefabs[child.name] = child
            elif isinstance(child, SpriteNode):
                self._process_sprite(child)
            elif isinstance(child, InstanceNode):
                self._process_instance(child)
            elif isinstance(child, GroupNode):
                self._process_group(child)
            elif isinstance(child, SoundNode):
                self._sounds.append({
                    'id': child.sound_id, 'src': child.src,
                    'volume': child.volume, 'loop': child.loop,
                    'trigger': child.trigger, 'channel': child.channel,
                })
                if child.src:
                    self._assets.add(child.src)
            elif isinstance(child, ParticleNode):
                self._particles.append({
                    'id': child.particle_id, 'src': child.src,
                    'follow': child.follow, 'trigger': child.trigger,
                    'count': child.count, 'emit_rate': child.emit_rate,
                    'lifetime': child.lifetime,
                    'speed_min': child.speed_min, 'speed_max': child.speed_max,
                    'angle_min': child.angle_min, 'angle_max': child.angle_max,
                    'alpha_start': child.alpha_start, 'alpha_end': child.alpha_end,
                })
            elif isinstance(child, TimerNode):
                self._timers.append({
                    'id': child.timer_id, 'interval': child.interval,
                    'repeat': child.repeat, 'auto_start': child.auto_start,
                    'action': child.action,
                })
            elif isinstance(child, TweenNode):
                self._tweens.append({
                    'id': child.tween_id, 'target': child.target,
                    'property': child.property, 'to': child.to_value,
                    'duration': child.duration, 'easing': child.easing,
                    'loop': child.loop, 'yoyo': child.yoyo,
                    'delay': child.delay, 'auto_start': child.auto_start,
                })
            elif isinstance(child, HudNode):
                self._huds.append({
                    'position': child.position,
                    'children': child.children,
                })
            elif isinstance(child, InputNode):
                self._custom_inputs.append({
                    'key': child.key, 'action': child.action,
                    'type': child.input_type,
                })
            elif isinstance(child, SpawnNode):
                self._spawners.append({
                    'id': child.spawn_id,
                    'prefab': child.prefab,
                    'count': child.count,
                    'interval': child.interval,
                    'x': child.x,
                    'y': child.y,
                    'pool_size': child.pool_size,
                })
            elif isinstance(child, TilemapNode):
                self._process_tilemap(child)
            elif isinstance(child, EventNode):
                self._events.append({
                    'name': child.name,
                    'handler': child.handler,
                    'filter_tag': child.filter_tag,
                    'filter_id': child.filter_id,
                    'scope': child.scope,
                })

    # ------------------------------------------------------------------
    # Sprite processing (collect info, no JS emitted yet)
    # ------------------------------------------------------------------

    def _process_sprite(self, sprite: SpriteNode, group_name: str = None):
        info = self._extract_sprite_info(sprite)
        info['group'] = group_name
        if sprite.src:
            self._assets.add(sprite.src)
        self._sprites.append(info)

    def _extract_sprite_info(self, sprite: SpriteNode) -> Dict[str, Any]:
        info: Dict[str, Any] = {
            'id': sprite.sprite_id,
            'src': sprite.src,
            'x': sprite.x, 'y': sprite.y,
            'width': sprite.width, 'height': sprite.height,
            'anchor_x': sprite.anchor_x, 'anchor_y': sprite.anchor_y,
            'rotation': sprite.rotation,
            'scale_x': sprite.scale_x, 'scale_y': sprite.scale_y,
            'alpha': sprite.alpha,
            'visible': sprite.visible,
            'color': sprite.color,
            'tag': sprite.tag,
            'layer': sprite.layer,
            'body': sprite.body,
            'bounce': sprite.bounce, 'friction': sprite.friction,
            'mass': sprite.mass, 'sensor': sprite.sensor,
            'controls': sprite.controls,
            'speed': sprite.speed, 'jump_force': sprite.jump_force,
            # SMW-style jump physics
            'gravity_up': sprite.gravity_up,
            'gravity_down': sprite.gravity_down,
            'jump_hold_boost': sprite.jump_hold_boost,
            'coyote_frames': sprite.coyote_frames,
            'max_fall_speed': sprite.max_fall_speed,
            'frame_width': sprite.frame_width, 'frame_height': sprite.frame_height,
            'group': None,
            'animations': [],
            'collider': None,
            'behaviors': [],
            'clickable': None,
            'on_collisions': [],  # qg:on-collision handlers
        }
        for child in sprite.children:
            if isinstance(child, AnimationNode):
                info['animations'].append({
                    'name': child.name, 'frames': child.frames,
                    'speed': child.speed, 'loop': child.loop,
                    'auto_play': child.auto_play,
                })
            elif isinstance(child, ColliderNode):
                info['collider'] = {
                    'shape': child.shape,
                    'width': child.width, 'height': child.height,
                    'radius': child.radius,
                }
            elif isinstance(child, UseNode):
                info['behaviors'].append({
                    'name': child.behavior,
                    'overrides': child.overrides,
                    'on_collision': child.on_collision,
                    'collision_tag': child.collision_tag,
                })
            elif isinstance(child, ClickableNode):
                info['clickable'] = {
                    'action': child.action,
                    'cursor': child.cursor,
                }
            elif isinstance(child, OnCollisionNode):
                info['on_collisions'].append({
                    'with_tag': child.with_tag,
                    'with_id': child.with_id,
                    'action': child.action,
                })
        return info

    def _process_instance(self, instance: InstanceNode):
        prefab = self._prefabs.get(instance.prefab)
        if not prefab:
            return
        for child in prefab.children:
            if isinstance(child, SpriteNode):
                sid = instance.instance_id or f"{instance.prefab}_{self._sprite_counter}"
                self._sprite_counter += 1
                info = self._extract_sprite_info(child)
                info['id'] = sid
                info['x'] = instance.x
                info['y'] = instance.y
                # Apply instance overrides to behavior overrides
                for buse in info['behaviors']:
                    buse['overrides'] = dict(buse['overrides'])
                    buse['overrides'].update(instance.overrides)
                if child.src:
                    self._assets.add(child.src)
                self._sprites.append(info)

    def _process_group(self, group: GroupNode):
        group_uses = []
        for child in group.children:
            if isinstance(child, SpriteNode):
                self._process_sprite(child, group_name=group.name)
            elif isinstance(child, InstanceNode):
                self._process_instance(child)
            elif isinstance(child, UseNode):
                group_uses.append(child)
        if group_uses:
            for sprite_info in self._sprites:
                if sprite_info.get('group') == group.name:
                    for use in group_uses:
                        sprite_info['behaviors'].append({
                            'name': use.behavior,
                            'overrides': use.overrides,
                            'on_collision': use.on_collision,
                            'collision_tag': use.collision_tag,
                        })

    def _process_tilemap(self, tilemap: TilemapNode):
        if tilemap.src:
            self._assets.add(tilemap.src)

        # Convert tile animations to dict for easy lookup
        tile_anims = {}
        for anim in tilemap.tile_animations:
            tile_anims[anim.tile_id] = {
                'frames': anim.frames,
                'speed': anim.speed,
            }

        for layer in tilemap.layers:
            # Always render tiles visually (if tilemap has a src)
            if tilemap.src:
                self._visual_tile_layers.append({
                    'tilemap_id': tilemap.tilemap_id,
                    'layer_name': layer.name,
                    'data': layer.data,
                    'tile_width': tilemap.tile_width,
                    'tile_height': tilemap.tile_height,
                    'src': tilemap.src,
                    'tile_animations': tile_anims,  # Dict of tile_id -> {frames, speed}
                })

            # Additionally create collision bodies if collision=true
            if layer.collision:
                rows = layer.data.strip().split('\n')
                tw = tilemap.tile_width
                th = tilemap.tile_height
                # Merge adjacent horizontal tiles into single wide bodies
                # to prevent objects from sinking between tile gaps
                for ry, row_str in enumerate(rows):
                    cells = row_str.split(',')
                    cx = 0
                    while cx < len(cells):
                        cell = cells[cx].strip()
                        if cell and cell != '0':
                            # Find run of adjacent filled cells
                            run_start = cx
                            while cx < len(cells) and cells[cx].strip() and cells[cx].strip() != '0':
                                cx += 1
                            run_len = cx - run_start
                            # Create one merged body for the run
                            total_w = run_len * tw
                            center_x = run_start * tw + total_w / 2
                            center_y = ry * th + th / 2
                            tid = f"tile_{tilemap.tilemap_id}_{ry}_{run_start}"
                            self._sprites.append({
                                'id': tid, 'src': '', 'x': center_x, 'y': center_y,
                                'width': total_w, 'height': th,
                                'anchor_x': 0.5, 'anchor_y': 0.5,
                                'rotation': 0, 'scale_x': 1, 'scale_y': 1,
                                'alpha': 0, 'visible': False,
                                'tag': 'tilemap-collision', 'layer': -1,
                                'body': 'static', 'bounce': 0, 'friction': 1.0,
                                'mass': None, 'sensor': False,
                                'controls': None, 'speed': 0, 'jump_force': 0,
                                'frame_width': None, 'frame_height': None,
                                'group': None, 'animations': [], 'collider': None,
                                'behaviors': [],
                            })
                        else:
                            cx += 1

    # ------------------------------------------------------------------
    # Main JS builder
    # ------------------------------------------------------------------

    def _build_game_js(self, js: JsBuilder, scene: SceneNode):
        js.line("(async function() {")
        js.indent()

        # PIXI App - use viewport size for canvas, not world size
        js.section("PIXI APP")
        js.const('app', 'new PIXI.Application()')
        # Use explicit viewport size if specified, otherwise cap to reasonable size
        if scene.viewport_width and scene.viewport_height:
            viewport_w = scene.viewport_width
            viewport_h = scene.viewport_height
        else:
            viewport_w = min(scene.width, 800)
            viewport_h = min(scene.height, 600)
        self._viewport_width = viewport_w
        self._viewport_height = viewport_h
        js.line(f"await app.init({{ width: {viewport_w}, height: {viewport_h}, background: {js_string(scene.background)} }});")
        js.line("document.body.appendChild(app.canvas);")
        js.comment(f"World size: {scene.width}x{scene.height}, Viewport: {viewport_w}x{viewport_h}")

        # Matter.js Engine
        js.section("MATTER.JS ENGINE")
        self._emit_physics_init(js, scene)

        # Event Bus
        js.section("EVENT BUS")
        emit_event_bus(js)

        # Game State
        js.section("GAME STATE")
        self._emit_state_vars(js)

        # Asset Loading
        js.section("ASSET LOADING")
        self._emit_asset_loading(js)

        # Animation System
        js.section("ANIMATION SYSTEM")
        emit_animation_system(js)

        # Behaviors
        js.section("BEHAVIORS")
        self._emit_behaviors(js)

        # Camera container
        js.section("CAMERA")
        self._emit_camera_setup(js)

        # Visual Tilemaps (before sprites so sprites render on top)
        js.section("VISUAL TILEMAPS")
        self._emit_visual_tilemaps(js)

        # Sprites & Bodies
        js.section("SPRITES & BODIES")
        self._emit_sprites(js)

        # Game API
        js.section("GAME API")
        emit_game_api(js)

        # Behavior Attachments
        js.section("BEHAVIOR ATTACHMENTS")
        self._emit_behavior_attachments(js)

        # Animations registration (after sprites)
        js.section("ANIMATION REGISTRATION")
        self._emit_animation_registration(js)

        # Input
        js.section("INPUT")
        emit_input_system(js)
        self._emit_controlled_sprites(js)

        # Mouse
        js.section("MOUSE")
        emit_mouse_system(js)

        # Functions
        js.section("FUNCTIONS")
        self._emit_functions(js)

        # Collisions
        js.section("COLLISIONS")
        self._emit_collision_handler(js)

        # Sound
        js.section("SOUNDS")
        self._emit_sounds(js)

        # Particles
        js.section("PARTICLES")
        emit_particle_system(js)
        self._emit_particle_instances(js)

        # Timers
        js.section("TIMERS")
        emit_timer_system(js)
        self._emit_timer_instances(js)

        # Tweens
        js.section("TWEENS")
        emit_tween_system(js)
        self._emit_tween_instances(js)

        # Spawners
        js.section("SPAWNERS")
        self._emit_spawner_instances(js)

        # HUD Update
        js.section("HUD UPDATE")
        self._emit_hud_update(js)

        # Game Loop
        js.section("GAME LOOP")
        self._emit_game_loop(js)

        # Scene Start
        js.section("SCENE START")
        self._emit_scene_start(js)

        js.dedent()
        js.line("})();")

    # ------------------------------------------------------------------
    # Physics
    # ------------------------------------------------------------------

    def _emit_physics_init(self, js: JsBuilder, scene: SceneNode):
        js.const('mEngine', 'Matter.Engine.create()')
        if self._physics:
            js.assign('mEngine.gravity.x', js_number(self._physics['gravity_x']))
            js.assign('mEngine.gravity.y', js_number(self._physics['gravity_y']))
        else:
            js.assign('mEngine.gravity.x', '0')
            js.assign('mEngine.gravity.y', '0')
        js.comment('Increase solver iterations for tighter collision resolution')
        js.assign('mEngine.positionIterations', '10')
        js.assign('mEngine.velocityIterations', '8')
        js.const('mWorld', 'mEngine.world')

        if self._physics and self._physics.get('bounds') == 'canvas':
            w, h = scene.width, scene.height
            hw, hh = w / 2, h / 2
            js.comment('World bounds')
            js.const('_bT', f'Matter.Bodies.rectangle({hw}, -25, {w}, 50, {{ isStatic: true }})')
            js.const('_bB', f'Matter.Bodies.rectangle({hw}, {h}+25, {w}, 50, {{ isStatic: true }})')
            js.const('_bL', f'Matter.Bodies.rectangle(-25, {hh}, 50, {h}, {{ isStatic: true }})')
            js.const('_bR', f'Matter.Bodies.rectangle({w}+25, {hh}, 50, {h}, {{ isStatic: true }})')
            js.line("Matter.Composite.add(mWorld, [_bT, _bB, _bL, _bR]);")

    # ------------------------------------------------------------------
    # State Variables
    # ------------------------------------------------------------------

    def _emit_state_vars(self, js: JsBuilder):
        if not self._state_vars:
            js.comment('no state')
            return
        for sv in self._state_vars:
            name = js_id(sv['name'])
            val = js_safe_value(sv['value'], sv['type'])
            js.let(name, val)

    # ------------------------------------------------------------------
    # Assets
    # ------------------------------------------------------------------

    def _emit_asset_loading(self, js: JsBuilder):
        if not self._assets:
            js.comment('No assets to preload')
            return
        urls = sorted(self._assets)
        asset_list = ', '.join(js_string(u) for u in urls)
        js.line(f"await PIXI.Assets.load([{asset_list}]);")

    # ------------------------------------------------------------------
    # Behaviors
    # ------------------------------------------------------------------

    def _emit_behaviors(self, js: JsBuilder):
        if not self._behaviors:
            js.comment('no behaviors')
            return
        for name, bnode in self._behaviors.items():
            cls_name = js_id(name)
            js.class_open(cls_name)

            # constructor
            js.method('constructor', 'owner, overrides')
            js.assign('this.owner', 'owner')
            for child in bnode.children:
                if isinstance(child, SetNode):
                    prop = js_id(child.name)
                    val = js_safe_value(child.value if child.value is not None else (child.default if child.default is not None else ''), child.type or 'string')
                    js.assign(f'this.{prop}', val)
            js.line("if (overrides) Object.assign(this, overrides);")
            js.block_close()  # constructor

            # Sprite property proxies (x, y, rotation, alpha, visible)
            # These allow behaviors to access sprite properties directly via this.x, this.y etc.
            for prop in ['x', 'y', 'rotation', 'alpha', 'visible']:
                js.line(f"get {prop}() {{ return this.owner.sprite.{prop}; }}")
                js.line(f"set {prop}(v) {{ this.owner.sprite.{prop} = v; }}")

            # methods
            for child in bnode.children:
                if isinstance(child, FunctionNode):
                    self._emit_method(js, child)
                elif isinstance(child, StateMachineNode):
                    self._emit_state_machine(js, child)

            js.class_close()
            js.blank()

    def _emit_method(self, js: JsBuilder, fn: FunctionNode):
        params = ', '.join(js_id(p.name) for p in fn.params)
        js.method(js_id(fn.name), params)
        if fn.body:
            for stmt in fn.body:
                self._emit_statement(js, stmt)
        else:
            js.comment('empty')
        js.block_close()

    def _emit_state_machine(self, js: JsBuilder, sm: StateMachineNode):
        # _smInit
        js.method('_smInit')
        js.assign('this._state', js_string(sm.initial))
        js.assign('this._states', '{}')
        for state in sm.states:
            transitions = {t.event: t.transition for t in state.transitions}
            js.assign(f"this._states[{js_string(state.name)}]",
                      f"{{ transitions: {json.dumps(transitions)} }}")
        enter_fn = f'this._stateEnter_{js_id(sm.initial)}'
        js.if_block(enter_fn)
        js.line(f"{enter_fn}();")
        js.block_close()
        js.block_close()  # _smInit

        # _smUpdate
        js.method('_smUpdate')
        for state in sm.states:
            for child in state.children:
                if isinstance(child, FunctionNode) and child.name == 'update':
                    js.if_block(f"this._state === {js_string(state.name)}")
                    js.line(f"this._stateUpdate_{js_id(state.name)}();")
                    js.block_close()
        js.block_close()  # _smUpdate

        # Individual state functions
        for state in sm.states:
            for child in state.children:
                if isinstance(child, FunctionNode):
                    prefix = f"_state{child.name.capitalize()}_{js_id(state.name)}"
                    js.method(prefix)
                    for stmt in child.body:
                        self._emit_statement(js, stmt)
                    js.block_close()

        # _smEmit
        js.method('_smEmit', 'event')
        js.const('st', 'this._states[this._state]')
        js.if_block('st && st.transitions[event]')
        js.const('prev', 'this._state')
        js.assign('this._state', 'st.transitions[event]')
        js.const('exitFn', "'_stateExit_' + prev")
        js.if_block('this[exitFn]')
        js.line('this[exitFn]();')
        js.block_close()
        js.const('enterFn', "'_stateEnter_' + this._state")
        js.if_block('this[enterFn]')
        js.line('this[enterFn]();')
        js.block_close()
        js.block_close()  # if
        js.block_close()  # _smEmit

    # ------------------------------------------------------------------
    # Statement emission (q:set, q:if, q:loop, q:function inside bodies)
    # ------------------------------------------------------------------

    def _emit_statement(self, js: JsBuilder, node: QuantumNode):
        if isinstance(node, SetNode):
            self._emit_set_assignment(js, node)
        elif isinstance(node, IfNode):
            self._emit_if(js, node)
        elif isinstance(node, LoopNode):
            self._emit_loop(js, node)
        elif isinstance(node, FunctionNode):
            self._emit_nested_function(js, node)
        elif isinstance(node, RawCodeNode):
            # Convert self. to this. for JavaScript
            code = re.sub(r'\bself\.', 'this.', node.code)
            js.line(code)
        else:
            js.comment(f"unsupported node: {type(node).__name__}")

    def _emit_set_assignment(self, js: JsBuilder, node: SetNode):
        name = node.name
        val = self._compile_expression(node.value or '""')

        if name.startswith('self.'):
            prop = name[5:]
            # Sprite properties that should be proxied to owner.sprite
            sprite_props = {'x', 'y', 'rotation', 'alpha', 'visible', 'width', 'height'}
            if prop in sprite_props:
                js.assign(f'this.owner.sprite.{prop}', val)
            else:
                js.assign(f'this.{prop}', val)
        else:
            js.assign(js_id(name), val)

    def _emit_if(self, js: JsBuilder, node: IfNode):
        cond = self._compile_expression(node.condition)
        js.if_block(cond)
        for s in node.if_body:
            self._emit_statement(js, s)
        for eib in node.elseif_blocks:
            ec = self._compile_expression(eib['condition'])
            js.else_if_block(ec)
            for s in eib['body']:
                self._emit_statement(js, s)
        if node.else_body:
            js.else_block()
            for s in node.else_body:
                self._emit_statement(js, s)
        js.block_close()

    def _emit_loop(self, js: JsBuilder, node: LoopNode):
        var = js_id(node.var_name)
        if node.loop_type == 'range':
            frm = node.from_value or '0'
            to = node.to_value or '0'
            step = str(node.step_value or 1)
            js.for_range(var, frm, to, step)
            for s in node.body:
                self._emit_statement(js, s)
            js.block_close()
        else:
            js.comment(f"loop type {node.loop_type} not yet compiled")

    def _emit_nested_function(self, js: JsBuilder, node: FunctionNode):
        params = ', '.join(js_id(p.name) for p in node.params)
        js.func(js_id(node.name), params)
        for s in node.body:
            self._emit_statement(js, s)
        js.block_close()

    # ------------------------------------------------------------------
    # Camera
    # ------------------------------------------------------------------

    def _emit_camera_setup(self, js: JsBuilder):
        js.const('_cameraContainer', 'new PIXI.Container()')
        js.line("app.stage.addChild(_cameraContainer);")

        if self._camera and self._camera.get('follow'):
            target = js_string(self._camera['follow'])
            lerp = js_number(self._camera['lerp'])
            js.const('_camera', f'{{ targetId: {target}, lerp: {lerp} }}')
            js.blank()
            js.func('updateCamera')
            js.const('info', '_sprites[_camera.targetId]')
            js.if_block('!info')
            js.ret()
            js.block_close()
            js.const('tx', 'app.screen.width / 2 - info.sprite.x')
            js.const('ty', 'app.screen.height / 2 - info.sprite.y')
            js.line('_cameraContainer.x += (tx - _cameraContainer.x) * _camera.lerp;')
            js.line('_cameraContainer.y += (ty - _cameraContainer.y) * _camera.lerp;')
            if self._camera.get('bounds') == 'scene':
                js.assign('_cameraContainer.x',
                           f'Math.min(0, Math.max(app.screen.width - {self._scene_width}, _cameraContainer.x))')
                js.assign('_cameraContainer.y',
                           f'Math.min(0, Math.max(app.screen.height - {self._scene_height}, _cameraContainer.y))')
            js.block_close()  # updateCamera
        else:
            js.func('updateCamera')
            js.block_close()

    # ------------------------------------------------------------------
    # Sprites & Bodies
    # ------------------------------------------------------------------

    def _emit_sprites(self, js: JsBuilder):
        js.const('_sprites', '{}')
        js.const('_bodyToSprite', '{}')
        body_vars = []

        for info in self._sprites:
            sid = js_id(info['id'])
            src = info['src']
            x, y = js_number(info['x']), js_number(info['y'])
            spr_var = f'_spr_{sid}'

            if src:
                # Check if sprite has frame dimensions (spritesheet with frames)
                frame_w = info.get('frame_width')
                frame_h = info.get('frame_height')
                if frame_w and frame_h:
                    # Spritesheet with frames - cut first frame to avoid wrong initial size
                    js.const(f'_{sid}_baseTex', f"PIXI.Assets.get({js_string(src)})")
                    js.const(f'_{sid}_src', f'_{sid}_baseTex.source || _{sid}_baseTex.baseTexture || _{sid}_baseTex')
                    js.const(f'_{sid}_rect', f'new PIXI.Rectangle(0, 0, {js_number(frame_w)}, {js_number(frame_h)})')
                    js.const(f'_{sid}_frameTex', f'new PIXI.Texture({{ source: _{sid}_src, frame: _{sid}_rect }})')
                    js.const(spr_var, f"new PIXI.Sprite(_{sid}_frameTex)")
                else:
                    # Normal sprite - load entire image
                    js.const(spr_var, f"PIXI.Sprite.from({js_string(src)})")
            else:
                js.const(spr_var, 'new PIXI.Graphics()')
                if info.get('width') and info.get('height'):
                    w, h = info['width'], info['height']
                    js.line(f"{spr_var}.rect(-{w/2}, -{h/2}, {w}, {h});")
                    # Use color if provided, otherwise default to a visible color
                    color = info.get('color')
                    if color:
                        # Convert hex color like "#FF0000" to 0xFF0000
                        hex_color = color.lstrip('#')
                        js.line(f"{spr_var}.fill({{ color: 0x{hex_color} }});")
                    else:
                        # Default: visible gray rectangle for debugging
                        js.line(f"{spr_var}.fill({{ color: 0x4a9eff }});")

            js.assign(f'{spr_var}.x', x)
            js.assign(f'{spr_var}.y', y)

            if src:
                js.line(f"{spr_var}.anchor.set({js_number(info['anchor_x'])}, {js_number(info['anchor_y'])});")
            # Only set width/height if NOT using frame-based animations
            has_frame_anims = info.get('frame_width') and info.get('frame_height')
            if info.get('width') and src and not has_frame_anims:
                js.assign(f'{spr_var}.width', js_number(info['width']))
            if info.get('height') and src and not has_frame_anims:
                js.assign(f'{spr_var}.height', js_number(info['height']))
            if info['alpha'] != 1.0:
                js.assign(f'{spr_var}.alpha', js_number(info['alpha']))
            if not info['visible']:
                js.assign(f'{spr_var}.visible', 'false')

            js.line(f"_cameraContainer.addChild({spr_var});")

            # Physics body
            body_var = self._emit_body(js, info, sid)
            if body_var:
                body_vars.append(body_var)
                js.assign(f'_bodyToSprite[{body_var}.id]', js_string(info['id']))

            # Clickable setup
            if info.get('clickable'):
                cursor = info['clickable'].get('cursor', 'pointer')
                action = js_id(info['clickable']['action'])
                js.assign(f"{spr_var}.eventMode", "'static'")
                js.assign(f"{spr_var}.cursor", js_string(cursor))
                sid_str_click = js_string(info['id'])
                js.line(f"{spr_var}.on('pointerdown', (e) => {{")
                js.indent()
                js.const('_info', f'_sprites[{sid_str_click}]')
                js.comment('Try behavior method first, then global function')
                js.let('_handled', 'false')
                js.if_block('_info && _info.behaviors')
                js.for_of('_b', '_info.behaviors')
                js.if_block(f"typeof _b.{action} === 'function'")
                js.line(f"_b.{action}(e);")
                js.assign('_handled', 'true')
                js.block_close()
                js.block_close()
                js.block_close()
                js.if_block(f"!_handled && typeof {action} === 'function'")
                js.line(f"{action}(_info, e);")
                js.block_close()
                js.dedent()
                js.line("});")

            # Register in _sprites
            body_ref = f'_body_{sid}' if info.get('body') else 'null'
            tag_ref = js_string(info['tag']) if info.get('tag') else 'null'
            id_ref = js_string(info['id'])
            js.line(f"_sprites[{id_ref}] = {{ id: {id_ref}, sprite: {spr_var}, body: {body_ref}, tag: {tag_ref}, collisionHandlers: [], behaviors: [] }};")
            js.blank()

        if body_vars:
            js.line(f"Matter.Composite.add(mWorld, [{', '.join(body_vars)}]);")

        js.blank()
        emit_physics_sync(js)

    def _emit_body(self, js: JsBuilder, info: Dict, sid: str) -> Optional[str]:
        if not info.get('body'):
            return None
        btype = info['body']
        is_static = btype == 'static'
        # Use frame dimensions if available (for animated sprites), fallback to width/height or 32
        w = info.get('width') or info.get('frame_width') or 32
        h = info.get('height') or info.get('frame_height') or 32
        x, y = js_number(info['x']), js_number(info['y'])

        collider = info.get('collider')
        shape = collider['shape'] if collider else 'box'

        opts_parts = [f"isStatic: {js_bool(is_static)}"]
        opts_parts.append(f"restitution: {js_number(info['bounce'])}")
        opts_parts.append(f"friction: {js_number(info['friction'])}")
        opts_parts.append("slop: 0.01")
        if not is_static:
            opts_parts.append("inertia: Infinity")
            # Round corners on player to prevent edge-catching on pipes/platforms
            if info.get('tag') == 'player':
                opts_parts.append("chamfer: { radius: 3 }")
        if info.get('mass') is not None:
            opts_parts.append(f"mass: {js_number(info['mass'])}")
        if info.get('sensor'):
            opts_parts.append("isSensor: true")
        opts = ', '.join(opts_parts)

        body_var = f'_body_{sid}'
        if shape == 'circle':
            r = js_number((collider and collider.get('radius')) or w / 2)
            js.const(body_var, f"Matter.Bodies.circle({x}, {y}, {r}, {{ {opts} }})")
        else:
            js.const(body_var, f"Matter.Bodies.rectangle({x}, {y}, {js_number(w)}, {js_number(h)}, {{ {opts} }})")
        return body_var

    # ------------------------------------------------------------------
    # Behavior Attachments
    # ------------------------------------------------------------------

    def _emit_behavior_attachments(self, js: JsBuilder):
        has_any = False
        for info in self._sprites:
            sid_str = js_string(info['id'])
            for buse in info.get('behaviors', []):
                has_any = True
                bname = js_id(buse['name'])
                overrides = json.dumps(buse['overrides']) if buse.get('overrides') else '{}'
                js.line(f"_sprites[{sid_str}].behaviors.push(new {bname}(_sprites[{sid_str}], {overrides}));")
                if buse.get('on_collision'):
                    fn_name = js_id(buse['on_collision'])
                    js.line(f"_sprites[{sid_str}].collisionHandlers.push((self, other) => {{")
                    js.indent()
                    if buse.get('collision_tag'):
                        tag_val = js_string(buse['collision_tag'])
                        js.line(f"if (other.tag !== {tag_val}) return;")
                    js.line(f"const b = self.behaviors.find(b => b instanceof {bname});")
                    js.line(f"if (b && b.{fn_name}) {{ b._other = other; b.{fn_name}(other); }}")
                    js.dedent()
                    js.line("});")

            # Process inline on-collision handlers (qg:on-collision)
            for oc in info.get('on_collisions', []):
                has_any = True
                js.line(f"_sprites[{sid_str}].collisionHandlers.push((self, other) => {{")
                js.indent()
                # Tag filter
                if oc.get('with_tag'):
                    tag_val = js_string(oc['with_tag'])
                    js.line(f"if (other.tag !== {tag_val}) return;")
                # ID filter
                if oc.get('with_id'):
                    id_val = js_string(oc['with_id'])
                    js.line(f"if (other.sprite?.name !== {id_val}) return;")
                # Execute action
                action = oc.get('action', '')
                if action == 'destroy-self':
                    js.line('if (self._destroyed) return;')
                    js.line('self._destroyed = true;')
                    js.line('if (self.body) { delete _bodyToSprite[self.body.id]; Matter.Composite.remove(mEngine.world, self.body); }')
                    js.line('if (self.sprite) { if (self.sprite.stop) self.sprite.stop(); self.sprite.destroy(); }')
                    js.line('if (self.id) delete _sprites[self.id];')
                elif action == 'destroy-other':
                    js.line('if (other._destroyed) return;')
                    js.line('other._destroyed = true;')
                    js.line('if (other.body) { delete _bodyToSprite[other.body.id]; Matter.Composite.remove(mEngine.world, other.body); }')
                    js.line('if (other.sprite) { if (other.sprite.stop) other.sprite.stop(); other.sprite.destroy(); }')
                    js.line('if (other.id) delete _sprites[other.id];')
                elif action.startswith('emit:'):
                    event_name = action[5:]  # Remove 'emit:' prefix
                    js.line(f"_gameEvents.emit({js_string(event_name)}, {{ self, other }});")
                elif action.startswith('call:'):
                    fn_name = action[5:]  # Remove 'call:' prefix
                    js.line(f"if (typeof {js_id(fn_name)} === 'function') {js_id(fn_name)}(self, other);")
                js.dedent()
                js.line("});")

        if not has_any:
            js.comment('no behavior attachments')

        # Init state machines
        js.comment('Init state machines')
        js.for_entries('_id', '_info', '_sprites')
        js.for_of('b', '_info.behaviors')
        js.if_block('b._smInit')
        js.line('b._smInit();')
        js.block_close()
        js.block_close()
        js.block_close()

    # ------------------------------------------------------------------
    # Animation Registration
    # ------------------------------------------------------------------

    def _emit_animation_registration(self, js: JsBuilder):
        has_anims = False
        for info in self._sprites:
            if info.get('animations') and info.get('frame_width') and info.get('frame_height'):
                has_anims = True
                sid_str = js_string(info['id'])
                anims_obj_parts = []
                for anim in info['animations']:
                    a_name = js_string(anim['name'])
                    a_frames = js_string(anim['frames'])
                    a_speed = js_number(anim['speed'])
                    a_loop = js_bool(anim['loop'])
                    a_auto = js_bool(anim.get('auto_play', False))
                    anims_obj_parts.append(
                        f"{a_name}: {{ frames: {a_frames}, speed: {a_speed}, loop: {a_loop}, autoPlay: {a_auto} }}"
                    )
                anims_obj = '{ ' + ', '.join(anims_obj_parts) + ' }'
                fw = js_number(info['frame_width'])
                fh = js_number(info['frame_height'])
                js.line(f"_registerAnimation({sid_str}, PIXI.Assets.get({js_string(info['src'])}), {fw}, {fh}, {anims_obj});")
        if not has_anims:
            js.comment('no animations to register')

    # ------------------------------------------------------------------
    # Controlled Sprites (for input/animation auto-switch)
    # ------------------------------------------------------------------

    def _emit_controlled_sprites(self, js: JsBuilder):
        js.const('_controlledSprites', '{}')
        for info in self._sprites:
            if info.get('controls'):
                ctrl = info['controls']
                sid_str = js_string(info['id'])
                if ctrl == 'wasd':
                    js.assign(f'_controlledSprites[{sid_str}]',
                              "{ left: 'a', right: 'd', up: 'w', jump: ' ',"
                              " left2: null, right2: null, up2: null, jump2: null }")
                elif ctrl == 'arrows':
                    js.assign(f'_controlledSprites[{sid_str}]',
                              "{ left: 'ArrowLeft', right: 'ArrowRight', up: 'ArrowUp', jump: 'ArrowUp',"
                              " left2: 'a', right2: 'd', up2: 'w', jump2: 'w' }")

    # ------------------------------------------------------------------
    # Functions
    # ------------------------------------------------------------------

    def _emit_functions(self, js: JsBuilder):
        if not self._functions:
            js.comment('no functions')
            return

        # Collect event handler names to auto-add 'data' parameter
        event_handlers = {evt['handler'] for evt in self._events}

        for fn in self._functions:
            params = ', '.join(js_id(p.name) for p in fn.params)
            # Auto-add 'data' param for event handlers if not already declared
            if fn.name in event_handlers and not fn.params:
                params = 'data'
            js.func(js_id(fn.name), params)
            for stmt in fn.body:
                self._emit_statement(js, stmt)
            js.block_close()
            js.blank()

    # ------------------------------------------------------------------
    # Collision handler
    # ------------------------------------------------------------------

    def _emit_collision_handler(self, js: JsBuilder):
        has_behavior_collisions = any(
            buse.get('on_collision')
            for info in self._sprites
            for buse in info.get('behaviors', [])
        )
        has_inline_collisions = any(
            len(info.get('on_collisions', [])) > 0
            for info in self._sprites
        )
        if not has_behavior_collisions and not has_inline_collisions:
            js.comment('no collision handlers')
            return

        js.line("Matter.Events.on(mEngine, 'collisionStart', (event) => {")
        js.indent()
        js.for_of('pair', 'event.pairs')
        js.const('a', '_bodyToSprite[pair.bodyA.id]')
        js.const('b', '_bodyToSprite[pair.bodyB.id]')
        js.if_block('a && b')
        js.line('_handleCollision(a, b);')
        js.line('_handleCollision(b, a);')
        js.block_close()
        js.block_close()
        js.dedent()
        js.line("});")
        js.blank()

        js.func('_handleCollision', 'selfId, otherId')
        js.const('selfInfo', '_sprites[selfId]')
        js.const('otherInfo', '_sprites[otherId]')
        js.if_block('!selfInfo || !otherInfo')
        js.ret()
        js.block_close()
        js.if_block('selfInfo.collisionHandlers')
        js.for_of('handler', 'selfInfo.collisionHandlers')
        js.line('handler(selfInfo, otherInfo);')
        js.block_close()
        js.block_close()
        js.block_close()

    # ------------------------------------------------------------------
    # Sound
    # ------------------------------------------------------------------

    def _emit_sounds(self, js: JsBuilder):
        if not self._sounds:
            js.comment('No sounds')
            return
        emit_audio_system(js)
        for s in self._sounds:
            js.line(f"await _loadSound({js_string(s['id'])}, {js_string(s['src'])});")

    # ------------------------------------------------------------------
    # Particle instances
    # ------------------------------------------------------------------

    def _emit_particle_instances(self, js: JsBuilder):
        if not self._particles:
            js.comment('No particle instances')
            return
        for p in self._particles:
            config_parts = [
                f"id: {js_string(p['id'])}",
                f"follow: {js_string(p['follow']) if p.get('follow') else 'null'}",
                f"count: {js_number(p['count'])}",
                f"emitRate: {js_number(p['emit_rate'])}",
                f"lifetime: {js_number(p['lifetime'])}",
                f"speedMin: {js_number(p['speed_min'])}",
                f"speedMax: {js_number(p['speed_max'])}",
                f"angleMin: {js_number(p['angle_min'])}",
                f"angleMax: {js_number(p['angle_max'])}",
                f"alphaStart: {js_number(p['alpha_start'])}",
                f"alphaEnd: {js_number(p['alpha_end'])}",
            ]
            js.line(f"_createParticleSystem({{ {', '.join(config_parts)} }});")
            if p.get('trigger'):
                js.comment(f"trigger: {p['trigger']} (wired at scene start)")

    # ------------------------------------------------------------------
    # Timer instances
    # ------------------------------------------------------------------

    def _emit_timer_instances(self, js: JsBuilder):
        if not self._timers:
            js.comment('No timer instances')
            return
        for t in self._timers:
            action = js_id(t['action'])
            js.line(
                f"_createTimer({js_string(t['id'])}, {js_number(t['interval'])}, "
                f"{js_number(t['repeat'])}, {js_bool(t['auto_start'])}, "
                f"typeof {action} === 'function' ? {action} : function(){{}});"
            )

    # ------------------------------------------------------------------
    # Tween instances
    # ------------------------------------------------------------------

    def _emit_tween_instances(self, js: JsBuilder):
        if not self._tweens:
            js.comment('No tween instances')
            return
        for t in self._tweens:
            config_parts = [
                f"id: {js_string(t['id'])}",
                f"target: {js_string(t['target'])}",
                f"prop: {js_string(t['property'])}",
                f"to: {js_number(t['to'])}",
                f"duration: {js_number(t['duration'])}",
                f"easing: {js_string(t['easing'])}",
                f"loop: {js_bool(t['loop'])}",
                f"yoyo: {js_bool(t['yoyo'])}",
                f"delay: {js_number(t['delay'])}",
                f"active: {js_bool(t['auto_start'])}",
            ]
            js.line(f"_createTween({{ {', '.join(config_parts)} }});")

    # ------------------------------------------------------------------
    # HUD
    # ------------------------------------------------------------------

    def _build_hud_html(self) -> str:
        parts = []
        for i, hud in enumerate(self._huds):
            content = self._gen_hud_content_safe(hud['children'])
            div = HUD_DIV_TEMPLATE.format(
                position=hud['position'],
                index=i,
                content=content,
            )
            parts.append(f"  {div}")
        return '\n'.join(parts)

    def _gen_hud_content_safe(self, children: List) -> str:
        """Generate HUD HTML with sanitized content."""
        parts = []
        for child in children:
            if isinstance(child, HTMLNode):
                tag = re.sub(r'[^a-zA-Z0-9]', '', child.tag)  # sanitize tag name
                safe_attrs = []
                for k, v in child.attributes.items():
                    k_safe = re.sub(r'[^a-zA-Z0-9-]', '', k)
                    # Only allow safe attributes
                    if k_safe in ('style', 'class', 'id'):
                        v_safe = v.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
                        safe_attrs.append(f'{k_safe}="{v_safe}"')
                attrs_str = ' ' + ' '.join(safe_attrs) if safe_attrs else ''
                inner = self._gen_hud_content_safe(child.children)
                parts.append(f"<{tag}{attrs_str}>{inner}</{tag}>")
            elif isinstance(child, TextNode):
                parts.append(sanitize_hud_text(child.content))
            else:
                parts.append('')
        return ''.join(parts)

    def _emit_hud_update(self, js: JsBuilder):
        if not self._huds:
            js.comment('No HUD')
            return

        js.const('_hudElements', '[]')
        for i in range(len(self._huds)):
            js.line(f"_hudElements.push(document.getElementById('qg-hud-{i}'));")

        js.func('_updateHUD')
        for i, hud in enumerate(self._huds):
            raw_content = self._get_raw_hud_text(hud['children'])
            bindings = re.findall(r'\{([^}]+)\}', raw_content)
            if bindings:
                js_expr = compile_binding_to_js(raw_content)
                # Use textContent instead of innerHTML for safety
                js.if_block(f'_hudElements[{i}]')
                js.assign(f'_hudElements[{i}].textContent', js_expr)
                js.block_close()
        js.block_close()

    def _get_raw_hud_text(self, children: List) -> str:
        """Get raw text content from HUD children for binding extraction."""
        parts = []
        for child in children:
            if isinstance(child, HTMLNode):
                parts.append(self._get_raw_hud_text(child.children))
            elif isinstance(child, TextNode):
                parts.append(child.content)
        return ''.join(parts)

    # ------------------------------------------------------------------
    # Game Loop
    # ------------------------------------------------------------------

    def _emit_game_loop(self, js: JsBuilder):
        js.line("app.ticker.add((ticker) => {")
        js.indent()
        js.const('dt', 'ticker.deltaTime')

        # Physics update with fixed timestep sub-stepping to prevent tunneling
        js.comment('Sub-step physics with velocity clamping to prevent tunneling')
        js.const('_fixedDt', '16.67')  # ~60fps fixed step
        js.const('_maxSteps', '3')  # Cap to prevent spiral of death
        js.const('_maxVel', '12')  # Max velocity per step (must be < tile height)
        js.const('_steps', 'Math.min(Math.ceil(dt), _maxSteps)')
        js.for_range('_i', '0', '_steps')
        js.comment('Clamp velocities BEFORE physics step')
        js.for_entries('_sid', '_sinfo', '_sprites')
        js.if_block('_sinfo.body && !_sinfo.body.isStatic')
        js.const('_bv', '_sinfo.body.velocity')
        js.if_block('Math.abs(_bv.x) > _maxVel || Math.abs(_bv.y) > _maxVel')
        js.line('Matter.Body.setVelocity(_sinfo.body, {')
        js.line('  x: Math.max(-_maxVel, Math.min(_maxVel, _bv.x)),')
        js.line('  y: Math.max(-_maxVel, Math.min(_maxVel, _bv.y))')
        js.line('});')
        js.block_close()
        js.block_close()
        js.block_close()
        js.line('Matter.Engine.update(mEngine, _fixedDt);')
        js.block_close()
        js.line('syncPhysics();')

        # Input handling for controlled sprites
        js.comment('Input handling')
        self._emit_input_update_loop(js)

        # Camera
        js.line('updateCamera();')

        # Control-based animation switching
        js.line('_updateControlAnimations();')

        # Update animated sprites (PIXI v8 fix)
        js.line('_updateAnimatedSprites(ticker);')

        # Behaviors update
        js.comment('Behaviors update')
        js.for_entries('_id', '_info', '_sprites')
        js.if_block('_info.behaviors')
        js.for_of('b', '_info.behaviors')
        js.if_block('b._smUpdate')
        js.line('b._smUpdate();')
        js.block_close()
        js.if_block('b.update')
        js.line('b.update();')
        js.block_close()
        js.block_close()
        js.block_close()
        js.block_close()

        # Timers
        if self._timers:
            js.line('_updateTimers(dt);')

        # Tweens
        if self._tweens:
            js.line('_updateTweens(dt);')

        # Particles
        if self._particles:
            js.line('_updateParticles(dt);')

        # HUD
        if self._huds:
            js.line('_updateHUD();')

        js.dedent()
        js.line("});")

    def _emit_input_update_loop(self, js: JsBuilder):
        for info in self._sprites:
            if info.get('controls'):
                sid_str = js_string(info['id'])
                sid_js = js_id(info['id'])
                ctrl = info['controls']
                spd = js_number(info['speed'])
                jf = js_number(info['jump_force'])

                # SMW-style physics parameters
                gravity_up = info.get('gravity_up')
                gravity_down = info.get('gravity_down')
                jump_hold_boost = js_number(info.get('jump_hold_boost', 0.4))
                coyote_frames = js_number(info.get('coyote_frames', 6))
                max_fall_speed = js_number(info.get('max_fall_speed', 15.0))

                if ctrl in ('wasd', 'arrows'):
                    js.const(f'_ctrl_{sid_js}', f'_controlledSprites[{sid_str}]')
                    ctrl_var = f'_ctrl_{sid_js}'
                    body_ref = f'_sprites[{sid_str}].body'
                    sprite_ref = f'_sprites[{sid_str}]'

                    js.comment("Movement with dual key support (arrows + WASD)")
                    js.const(f'_leftPressed_{sid_js}',
                             f'_keys[{ctrl_var}.left] || (_keys[{ctrl_var}.left2] || false)')
                    js.const(f'_rightPressed_{sid_js}',
                             f'_keys[{ctrl_var}.right] || (_keys[{ctrl_var}.right2] || false)')
                    js.const(f'_jumpPressed_{sid_js}',
                             f'_keys[{ctrl_var}.jump] || (_keys[{ctrl_var}.jump2] || false)')
                    js.const(f'_jumpJust_{sid_js}',
                             f'_justPressed[{ctrl_var}.jump] || (_justPressed[{ctrl_var}.jump2] || false)')
                    left_var = f'_leftPressed_{sid_js}'
                    right_var = f'_rightPressed_{sid_js}'
                    jump_var = f'_jumpPressed_{sid_js}'
                    jump_just = f'_jumpJust_{sid_js}'

                    # Horizontal movement
                    js.if_block(f'{left_var} && {body_ref}')
                    js.line(f"Matter.Body.setVelocity({body_ref}, {{ x: -{spd}, y: {body_ref}.velocity.y }});")
                    js.line(f"{sprite_ref}.sprite.scale.x = Math.abs({sprite_ref}.sprite.scale.x);")
                    js.block_close()
                    js.if_block(f'{right_var} && {body_ref}')
                    js.line(f"Matter.Body.setVelocity({body_ref}, {{ x: {spd}, y: {body_ref}.velocity.y }});")
                    js.line(f"{sprite_ref}.sprite.scale.x = -Math.abs({sprite_ref}.sprite.scale.x);")
                    js.block_close()

                    # SMW-style jump physics
                    js.comment("SMW-style jump: coyote time, variable height, asymmetric gravity")

                    # Initialize tracking variables if not present
                    js.if_block(f'{sprite_ref}._coyoteFrames === undefined')
                    js.line(f'{sprite_ref}._coyoteFrames = 0;')
                    js.line(f'{sprite_ref}._jumpHeld = false;')
                    js.line(f'{sprite_ref}._wasGrounded = false;')
                    js.block_close()

                    # Check if grounded (very small vertical velocity)
                    js.const(f'_isGrounded_{sid_js}', f'{body_ref} && Math.abs({body_ref}.velocity.y) < 1.0')
                    grounded_var = f'_isGrounded_{sid_js}'

                    # Update coyote time
                    js.if_block(grounded_var)
                    js.line(f'{sprite_ref}._coyoteFrames = {coyote_frames};')
                    js.line(f'{sprite_ref}._wasGrounded = true;')
                    js.else_if_block(f'{sprite_ref}._coyoteFrames > 0')
                    js.line(f'{sprite_ref}._coyoteFrames--;')
                    js.block_close()

                    # Can jump if grounded OR within coyote time
                    js.const(f'_canJump_{sid_js}', f'{grounded_var} || {sprite_ref}._coyoteFrames > 0')
                    can_jump_var = f'_canJump_{sid_js}'

                    # Initiate jump
                    js.if_block(f'{jump_just} && {body_ref} && {can_jump_var}')
                    js.line(f"Matter.Body.setVelocity({body_ref}, {{ x: {body_ref}.velocity.x, y: -{jf} }});")
                    js.line(f"{sprite_ref}._jumpHeld = true;")
                    js.line(f"{sprite_ref}._coyoteFrames = 0;")  # Consume coyote time
                    js.line(f"_gameEvents.emit('player.jump', {sprite_ref});")
                    js.block_close()

                    # Hold jump for extra height (only while ascending)
                    js.if_block(f'{jump_var} && {body_ref} && {sprite_ref}._jumpHeld && {body_ref}.velocity.y < 0')
                    js.line(f"Matter.Body.setVelocity({body_ref}, {{ x: {body_ref}.velocity.x, y: {body_ref}.velocity.y - {jump_hold_boost} }});")
                    js.block_close()

                    # Release jump button cancels hold boost
                    js.if_block(f'!{jump_var}')
                    js.line(f"{sprite_ref}._jumpHeld = false;")
                    js.block_close()

                    # Asymmetric gravity: reduce gravity while ascending (floatier rise)
                    if gravity_up is not None:
                        gravity_up_val = js_number(gravity_up)
                        js.comment("Asymmetric gravity: lighter when rising")
                        js.if_block(f'{body_ref} && {body_ref}.velocity.y < 0')
                        # Apply upward force to counteract some gravity (making ascent floatier)
                        # The difference between normal gravity and gravity_up
                        js.line(f"Matter.Body.applyForce({body_ref}, {body_ref}.position, {{ x: 0, y: -{body_ref}.mass * (mEngine.gravity.y - {gravity_up_val}) * 0.001 }});")
                        js.block_close()

                    # Extra gravity when falling (snappier descent)
                    if gravity_down is not None:
                        gravity_down_val = js_number(gravity_down)
                        js.comment("Asymmetric gravity: heavier when falling")
                        js.if_block(f'{body_ref} && {body_ref}.velocity.y > 0')
                        js.line(f"Matter.Body.applyForce({body_ref}, {body_ref}.position, {{ x: 0, y: {body_ref}.mass * ({gravity_down_val} - mEngine.gravity.y) * 0.001 }});")
                        js.block_close()

                    # Cap fall speed (terminal velocity)
                    js.if_block(f'{body_ref} && {body_ref}.velocity.y > {max_fall_speed}')
                    js.line(f"Matter.Body.setVelocity({body_ref}, {{ x: {body_ref}.velocity.x, y: {max_fall_speed} }});")
                    js.block_close()

                    # Stop horizontal movement when no keys pressed
                    js.if_block(f'!{left_var} && !{right_var} && {body_ref}')
                    js.line(f"Matter.Body.setVelocity({body_ref}, {{ x: 0, y: {body_ref}.velocity.y }});")
                    js.line(f"_gameEvents.emit('player.stop', {sprite_ref});")
                    js.else_block()
                    js.line(f"_gameEvents.emit('player.walk', {sprite_ref});")
                    js.block_close()

        # Custom input actions (safe: reference by sanitized function name, no eval)
        for ci in self._custom_inputs:
            key = js_string(ci['key'])
            action = js_id(ci['action'])
            if ci['type'] == 'press':
                js.if_block(f"_justPressed[{key}] && typeof {action} === 'function'")
            else:
                js.if_block(f"_keys[{key}] && typeof {action} === 'function'")
            js.line(f"{action}();")
            js.block_close()

        js.line('_clearJustPressed();')

    # ------------------------------------------------------------------
    # Scene Start
    # ------------------------------------------------------------------

    def _emit_scene_start(self, js: JsBuilder):
        # Register qg:event handlers
        self._emit_event_handlers(js)

        # Play scene.start triggered sounds
        for s in self._sounds:
            if s.get('trigger') == 'scene.start':
                js.line(f"_playSound({js_string(s['id'])}, {{ volume: {js_number(s['volume'])}, loop: {js_bool(s['loop'])} }});")
            elif s.get('trigger'):
                # Wire to event bus
                trigger = js_string(s['trigger'])
                sid = js_string(s['id'])
                vol = js_number(s['volume'])
                loop = js_bool(s['loop'])
                js.line(f"_gameEvents.on({trigger}, () => _playSound({sid}, {{ volume: {vol}, loop: {loop} }}));")

        # Activate trigger-based particles
        for p in self._particles:
            if p.get('trigger') == 'scene.start':
                js.line(f"_activateParticles({js_string(p['id'])});")
            elif p.get('trigger'):
                trigger = js_string(p['trigger'])
                pid = js_string(p['id'])
                js.line(f"_gameEvents.on({trigger}, () => _activateParticles({pid}));")

        # Emit game-init event
        js.line("_gameEvents.emit('game-init', {});")

    def _emit_event_handlers(self, js: JsBuilder):
        """Emit qg:event registrations."""
        if not self._events:
            return

        js.comment('qg:event handlers')
        for evt in self._events:
            event_name = js_string(evt['name'])
            handler = js_id(evt['handler'])
            filter_tag = evt.get('filter_tag')
            filter_id = evt.get('filter_id')

            # Build callback body
            js.line(f"_gameEvents.on({event_name}, (data) => {{")
            js.indent()

            # Add filters if specified
            if filter_tag:
                js.if_block(f"data && data.tag !== {js_string(filter_tag)}")
                js.ret()
                js.block_close()
            if filter_id:
                # Check both sprite ID and object ID
                js.const('_evtId', "data && (data.id || (typeof data === 'object' && Object.keys(_sprites).find(k => _sprites[k] === data)))")
                js.if_block(f"_evtId !== {js_string(filter_id)}")
                js.ret()
                js.block_close()

            # Call the handler function
            js.if_block(f"typeof {handler} === 'function'")
            js.line(f"{handler}(data);")
            js.block_close()
            js.dedent()
            js.line("});")

    # ------------------------------------------------------------------
    # Spawner instances
    # ------------------------------------------------------------------

    def _emit_spawner_instances(self, js: JsBuilder):
        if not self._spawners:
            js.comment('No spawners')
            return
        emit_spawn_system(js)

        # Register prefabs used by spawners
        registered_prefabs = set()
        for sp in self._spawners:
            prefab_name = sp['prefab']
            if prefab_name not in registered_prefabs:
                registered_prefabs.add(prefab_name)
                prefab_node = self._prefabs.get(prefab_name)
                if prefab_node:
                    # Extract sprite info from prefab
                    for child in prefab_node.children:
                        if isinstance(child, SpriteNode):
                            config_parts = [
                                f"width: {js_number(child.width or 20)}",
                                f"height: {js_number(child.height or 20)}",
                            ]
                            if child.color:
                                config_parts.append(f"color: {js_string(child.color)}")
                            js.line(f"_registerPrefab({js_string(prefab_name)}, {{ {', '.join(config_parts)} }});")
                            break

        # Create spawners
        for sp in self._spawners:
            config_parts = [
                f"id: {js_string(sp['id'])}",
                f"prefab: {js_string(sp['prefab'])}",
                f"poolSize: {js_number(sp['pool_size'])}",
                f"x: {js_number(sp.get('x') or 0)}",
                f"y: {js_number(sp.get('y') or 0)}",
            ]
            if sp.get('interval') is not None:
                config_parts.append(f"interval: {js_number(sp['interval'])}")
            js.line(f"_createSpawner({{ {', '.join(config_parts)} }});")

    # ------------------------------------------------------------------
    # Visual tilemaps
    # ------------------------------------------------------------------

    def _emit_visual_tilemaps(self, js: JsBuilder):
        if not self._visual_tile_layers:
            js.comment('No visual tile layers')
            return
        _emitted_tilesets = set()
        for vt in self._visual_tile_layers:
            tilemap_id = js_id(vt['tilemap_id'])
            layer_name = js_id(vt['layer_name'])
            data_var = f'_tileData_{tilemap_id}_{layer_name}'
            tw = vt['tile_width']
            th = vt['tile_height']
            src = vt['src']
            tile_anims = vt.get('tile_animations', {})

            # Emit tile data as 2D array
            rows = vt['data'].strip().split('\n')
            data_2d = []
            for row in rows:
                cells = [c.strip() for c in row.split(',') if c.strip()]
                data_2d.append('[' + ','.join(cells) + ']')
            js.const(data_var, '[' + ','.join(data_2d) + ']')

            # Emit tile animations data if any
            if tile_anims:
                anims_js = {}
                for tile_id, anim_data in tile_anims.items():
                    anims_js[str(tile_id)] = {
                        'frames': anim_data['frames'],
                        'speed': anim_data['speed']
                    }
                js.const(f'_tileAnims_{tilemap_id}', json.dumps(anims_js))

            # Emit JS loop to create sprites from tileset
            if src:
                if tilemap_id not in _emitted_tilesets:
                    js.const(f'_tileset_{tilemap_id}', f"PIXI.Assets.get({js_string(src)})")
                    ts_var = f'_tileset_{tilemap_id}'
                    src_var = f'_tsSource_{tilemap_id}'
                    js.const(src_var, f'{ts_var}.source || {ts_var}.baseTexture || {ts_var}')
                    # Use source.width for PIXI 8 compatibility (texture.width may be 0)
                    js.const(f'_tsCols_{tilemap_id}', f'Math.floor(({src_var}.width || {ts_var}.width || 256) / {tw})')
                    _emitted_tilesets.add(tilemap_id)

            # Helper function to create texture for a tile ID
            js.comment(f'Create tiles for layer {layer_name}')
            js.line(f'function _getTileTex_{tilemap_id}(tileId) {{')
            js.indent()
            js.const('col', f'tileId % _tsCols_{tilemap_id}')
            js.const('row', f'Math.floor(tileId / _tsCols_{tilemap_id})')
            js.const('rect', f'new PIXI.Rectangle(col * {tw}, row * {th}, {tw}, {th})')
            js.line(f'return new PIXI.Texture({{ source: _tsSource_{tilemap_id}, frame: rect }});')
            js.dedent()
            js.line('}')

            js.for_range('_ty', '0', f'{data_var}.length - 1')
            js.for_range('_tx', '0', f'{data_var}[_ty].length - 1')
            js.const('_tileId', f'{data_var}[_ty][_tx]')
            js.if_block('_tileId > 0')

            if src:
                if tile_anims:
                    # Check if this tile has an animation (use String for key lookup)
                    js.const('_animData', f'_tileAnims_{tilemap_id}[String(_tileId)]')
                    js.line('let _tileSpr;')
                    js.if_block('_animData')
                    # Create AnimatedSprite for animated tiles
                    js.const('_animTextures', f'_animData.frames.map(fid => _getTileTex_{tilemap_id}(fid))')
                    js.assign('_tileSpr', 'new PIXI.AnimatedSprite(_animTextures)')
                    js.line('_tileSpr.animationSpeed = _animData.speed;')
                    js.line('_tileSpr.play();')
                    js.else_block()
                    # Regular static sprite
                    js.assign('_tileSpr', f'new PIXI.Sprite(_getTileTex_{tilemap_id}(_tileId))')
                    js.block_close()
                else:
                    # No animations defined - all static
                    js.const('_tileSpr', f'new PIXI.Sprite(_getTileTex_{tilemap_id}(_tileId))')
            else:
                js.const('_tileSpr', 'new PIXI.Graphics()')
                js.line(f"_tileSpr.rect(0, 0, {tw}, {th});")
                js.line("_tileSpr.fill({ color: 0x808080 });")

            js.assign('_tileSpr.x', f'_tx * {tw}')
            js.assign('_tileSpr.y', f'_ty * {th}')
            js.line('_cameraContainer.addChild(_tileSpr);')
            js.block_close()  # if tileId > 0
            js.block_close()  # for _tx
            js.block_close()  # for _ty
            js.blank()

    # ------------------------------------------------------------------
    # Expression compilation
    # ------------------------------------------------------------------

    def _compile_expression(self, expr: str) -> str:
        """Convert Quantum databinding expressions to JS safely."""
        if not expr:
            return '""'
        expr = expr.strip()
        # Handle {expr} databinding
        if expr.startswith('{') and expr.endswith('}'):
            inner = expr[1:-1]
            inner = inner.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
            # Convert self. to this. for JavaScript
            inner = re.sub(r'\bself\.', 'this.', inner)
            # Validate: only allow safe JS expressions (identifiers, math, dots, parens, arrays, ternary)
            if re.match(r'^[a-zA-Z_$0-9][a-zA-Z0-9_$.\s+\-*/()%<>=!&|,\[\]?:\'"]*$', inner):
                return inner
            return json.dumps(expr)  # escape unsafe expressions
        # Handle XML-escaped operators
        expr = expr.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        # Convert self. to this. for JavaScript
        expr = re.sub(r'\bself\.', 'this.', expr)
        if expr.startswith('"') or expr.startswith("'") or is_number(expr) or expr in ('true', 'false'):
            return expr
        return json.dumps(expr)


def html_escape_title(title: str) -> str:
    """Escape a title for safe HTML embedding."""
    return title.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
