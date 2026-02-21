"""
Game Engine 2D Parser - Parse qg: namespace elements into Game AST nodes.

This module provides parse functions for all game-specific tags.
It is called from the main QuantumParser when a qg: prefixed tag is encountered.
"""

from xml.etree import ElementTree as ET
from typing import Optional, List

from .ast_nodes import (
    SceneNode, SpriteNode, PhysicsNode, ColliderNode, AnimationNode,
    CameraNode, InputNode, SoundNode, ParticleNode, TimerNode,
    SpawnNode, HudNode, TweenNode, TilemapNode, TilemapLayerNode,
    TileAnimationNode, BehaviorNode, UseNode, PrefabNode, InstanceNode,
    GroupNode, StateMachineNode, StateNode, TransitionNode, RawCodeNode,
    ClickableNode, EventNode, OnCollisionNode,
)


class GameParseError(Exception):
    """Game-specific parse error."""
    pass


class GameParser:
    """Parser for qg: namespace game elements."""

    def __init__(self, parent_parser):
        """
        Args:
            parent_parser: The main QuantumParser instance, used to parse
                           q: namespace children (q:set, q:function, q:if, etc.)
        """
        self.parent = parent_parser

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    GAME_TAG_MAP = {
        'scene': '_parse_game_scene',
        'sprite': '_parse_game_sprite',
        'physics': '_parse_game_physics',
        'collider': '_parse_game_collider',
        'animation': '_parse_game_animation',
        'camera': '_parse_game_camera',
        'input': '_parse_game_input',
        'sound': '_parse_game_sound',
        'particle': '_parse_game_particle',
        'timer': '_parse_game_timer',
        'spawn': '_parse_game_spawn',
        'hud': '_parse_game_hud',
        'tween': '_parse_game_tween',
        'tilemap': '_parse_game_tilemap',
        'layer': '_parse_game_layer',
        'behavior': '_parse_game_behavior',
        'use': '_parse_game_use',
        'prefab': '_parse_game_prefab',
        'instance': '_parse_game_instance',
        'group': '_parse_game_group',
        'state-machine': '_parse_game_state_machine',
        'state': '_parse_game_state',
        'on': '_parse_game_transition',
        'clickable': '_parse_game_clickable',
        'event': '_parse_game_event',
        'on-collision': '_parse_game_on_collision',
    }

    def parse_game_element(self, local_name: str, element: ET.Element):
        """Dispatch a qg: element to the correct parse method."""
        method_name = self.GAME_TAG_MAP.get(local_name)
        if method_name is None:
            raise GameParseError(f"Unknown game tag: qg:{local_name}")
        method = getattr(self, method_name)
        return method(element)

    # ------------------------------------------------------------------
    # Helper: get local name from element
    # ------------------------------------------------------------------

    def _get_local_name(self, element: ET.Element) -> str:
        tag = element.tag
        if '}' in tag:
            return tag.split('}')[-1]
        if ':' in tag:
            return tag.split(':')[-1]
        return tag

    def _get_namespace(self, element: ET.Element) -> Optional[str]:
        tag = element.tag
        if '{https://quantum.lang/game}' in tag:
            return 'game'
        if '{https://quantum.lang/ns}' in tag:
            return 'quantum'
        if tag.startswith('qg:'):
            return 'game'
        if tag.startswith('q:'):
            return 'quantum'
        return None

    def _parse_float(self, value: Optional[str], default: float = 0) -> float:
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            return default

    def _parse_int(self, value: Optional[str], default: int = 0) -> int:
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    def _parse_bool(self, value: Optional[str], default: bool = False) -> bool:
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes')

    # ------------------------------------------------------------------
    # Parse children – dispatches both qg: and q: tags
    # ------------------------------------------------------------------

    def _parse_child(self, child: ET.Element):
        """Parse a child element that can be either qg: or q: namespace."""
        ns = self._get_namespace(child)
        local = self._get_local_name(child)

        if ns == 'game':
            return self.parse_game_element(local, child)
        elif ns == 'quantum':
            if local == 'function':
                return self._parse_game_function(child)
            return self.parent._parse_statement(child)
        else:
            # Could be HTML inside HUD
            if hasattr(self.parent, '_parse_html_element'):
                return self.parent._parse_html_element(child)
            return None

    def _parse_game_function(self, element: ET.Element):
        """Parse q:function with mixed raw code text and XML statement children.

        Captures element.text and child.tail as RawCodeNode, alongside
        regular q:set / q:if / etc children parsed normally.
        """
        # Use the parent parser to get the FunctionNode shell (name, params)
        func_node = self.parent._parse_function(element)

        # Now re-parse the body to capture raw text
        mixed_body = []

        # Leading text before first child
        if element.text and element.text.strip():
            for line in element.text.strip().splitlines():
                line = line.strip()
                if line:
                    mixed_body.append(RawCodeNode(line))

        # Process children: XML elements + their tail text
        for child in element:
            parsed = self._parse_child(child)
            if parsed:
                mixed_body.append(parsed)
            # Tail text after each child
            if child.tail and child.tail.strip():
                for line in child.tail.strip().splitlines():
                    line = line.strip()
                    if line:
                        mixed_body.append(RawCodeNode(line))

        # Only replace body if we found raw code nodes
        has_raw = any(isinstance(n, RawCodeNode) for n in mixed_body)
        if has_raw:
            func_node.body = mixed_body

        return func_node

    # ------------------------------------------------------------------
    # Core game nodes
    # ------------------------------------------------------------------

    def _parse_game_scene(self, element: ET.Element) -> SceneNode:
        name = element.get('name', 'main')
        node = SceneNode(name)
        node.width = self._parse_int(element.get('width'), 800)
        node.height = self._parse_int(element.get('height'), 600)
        # Viewport size (canvas size) - defaults to scene size if not specified
        node.viewport_width = self._parse_int(element.get('viewport-width')) if element.get('viewport-width') else None
        node.viewport_height = self._parse_int(element.get('viewport-height')) if element.get('viewport-height') else None
        node.background = element.get('background', '#000000')
        node.active = self._parse_bool(element.get('active'), True)

        for child in element:
            parsed = self._parse_child(child)
            if parsed:
                node.add_child(parsed)
        return node

    def _parse_game_sprite(self, element: ET.Element) -> SpriteNode:
        sprite_id = element.get('id', '')
        node = SpriteNode(sprite_id)
        node.src = element.get('src', '')
        node.x = self._parse_float(element.get('x'))
        node.y = self._parse_float(element.get('y'))
        node.width = self._parse_float(element.get('width')) if element.get('width') else None
        node.height = self._parse_float(element.get('height')) if element.get('height') else None
        node.anchor_x = self._parse_float(element.get('anchor-x'), 0.5)
        node.anchor_y = self._parse_float(element.get('anchor-y'), 0.5)
        node.rotation = self._parse_float(element.get('rotation'))
        node.scale_x = self._parse_float(element.get('scale-x'), 1)
        node.scale_y = self._parse_float(element.get('scale-y'), 1)
        node.alpha = self._parse_float(element.get('alpha'), 1.0)
        node.visible = self._parse_bool(element.get('visible'), True)
        node.color = element.get('color')  # Hex color for sprites without images
        node.tag = element.get('tag')
        node.layer = self._parse_int(element.get('layer'))

        # Spritesheet
        node.frame_width = self._parse_int(element.get('frame-width')) if element.get('frame-width') else None
        node.frame_height = self._parse_int(element.get('frame-height')) if element.get('frame-height') else None

        # Physics
        node.body = element.get('body')
        node.bounce = self._parse_float(element.get('bounce'), 0.1)
        node.friction = self._parse_float(element.get('friction'), 0.1)
        node.mass = self._parse_float(element.get('mass')) if element.get('mass') else None
        node.sensor = self._parse_bool(element.get('sensor'))

        # Controls
        node.controls = element.get('controls')
        node.speed = self._parse_float(element.get('speed'), 5.0)
        node.jump_force = self._parse_float(element.get('jump-force'), 10.0)

        # SMW-style jump physics
        node.gravity_up = self._parse_float(element.get('gravity-up')) if element.get('gravity-up') else None
        node.gravity_down = self._parse_float(element.get('gravity-down')) if element.get('gravity-down') else None
        node.jump_hold_boost = self._parse_float(element.get('jump-hold-boost'), 0.4)
        node.coyote_frames = self._parse_int(element.get('coyote-frames'), 6)
        node.max_fall_speed = self._parse_float(element.get('max-fall-speed'), 15.0)

        for child in element:
            parsed = self._parse_child(child)
            if parsed:
                node.add_child(parsed)
        return node

    def _parse_game_physics(self, element: ET.Element) -> PhysicsNode:
        node = PhysicsNode()
        node.gravity_x = self._parse_float(element.get('gravity-x'))
        node.gravity_y = self._parse_float(element.get('gravity-y'), 9.8)
        node.bounds = element.get('bounds')
        node.debug = self._parse_bool(element.get('debug'))
        return node

    def _parse_game_collider(self, element: ET.Element) -> ColliderNode:
        node = ColliderNode()
        node.shape = element.get('shape', 'box')
        node.width = self._parse_float(element.get('width')) if element.get('width') else None
        node.height = self._parse_float(element.get('height')) if element.get('height') else None
        node.radius = self._parse_float(element.get('radius')) if element.get('radius') else None
        node.vertices = element.get('vertices')
        node.offset_x = self._parse_float(element.get('offset-x'))
        node.offset_y = self._parse_float(element.get('offset-y'))
        return node

    def _parse_game_animation(self, element: ET.Element) -> AnimationNode:
        name = element.get('name', '')
        node = AnimationNode(name)
        node.frames = element.get('frames', '')
        node.speed = self._parse_float(element.get('speed'), 0.1)
        node.loop = self._parse_bool(element.get('loop'), True)
        node.auto_play = self._parse_bool(element.get('auto-play'))
        return node

    def _parse_game_camera(self, element: ET.Element) -> CameraNode:
        node = CameraNode()
        node.follow = element.get('follow')
        node.lerp = self._parse_float(element.get('lerp'), 0.1)
        node.bounds = element.get('bounds')
        node.zoom = self._parse_float(element.get('zoom'), 1.0)
        node.offset_x = self._parse_float(element.get('offset-x'))
        node.offset_y = self._parse_float(element.get('offset-y'))
        return node

    def _parse_game_input(self, element: ET.Element) -> InputNode:
        node = InputNode()
        node.key = element.get('key', '')
        node.action = element.get('action', '')
        node.input_type = element.get('type', 'press')
        return node

    def _parse_game_sound(self, element: ET.Element) -> SoundNode:
        sound_id = element.get('id', '')
        node = SoundNode(sound_id)
        node.src = element.get('src', '')
        node.volume = self._parse_float(element.get('volume'), 1.0)
        node.loop = self._parse_bool(element.get('loop'))
        node.trigger = element.get('trigger')
        node.channel = element.get('channel', 'sfx')
        return node

    def _parse_game_particle(self, element: ET.Element) -> ParticleNode:
        pid = element.get('id', '')
        node = ParticleNode(pid)
        node.src = element.get('src', '')
        node.follow = element.get('follow')
        node.trigger = element.get('trigger')
        node.count = self._parse_int(element.get('count'), 20)
        node.emit_rate = self._parse_int(element.get('emit-rate'), 10)
        node.lifetime = self._parse_float(element.get('lifetime'), 1.0)
        node.speed_min = self._parse_float(element.get('speed-min'), 1.0)
        node.speed_max = self._parse_float(element.get('speed-max'), 3.0)
        node.angle_min = self._parse_float(element.get('angle-min'), 0)
        node.angle_max = self._parse_float(element.get('angle-max'), 360)
        node.alpha_start = self._parse_float(element.get('alpha-start'), 1.0)
        node.alpha_end = self._parse_float(element.get('alpha-end'), 0.0)
        return node

    def _parse_game_timer(self, element: ET.Element) -> TimerNode:
        tid = element.get('id', '')
        node = TimerNode(tid)
        node.interval = self._parse_float(element.get('interval'), 1.0)
        node.repeat = self._parse_int(element.get('repeat'), -1)
        node.auto_start = self._parse_bool(element.get('auto-start'), True)
        node.action = element.get('action', '')
        return node

    def _parse_game_spawn(self, element: ET.Element) -> SpawnNode:
        sid = element.get('id', '')
        node = SpawnNode(sid)
        node.prefab = element.get('prefab', '')
        node.count = self._parse_int(element.get('count'), 1)
        node.interval = self._parse_float(element.get('interval')) if element.get('interval') else None
        node.x = element.get('x')
        node.y = element.get('y')
        node.pool_size = self._parse_int(element.get('pool-size'), 10)
        return node

    def _parse_game_hud(self, element: ET.Element) -> HudNode:
        node = HudNode()
        node.position = element.get('position', 'top-left')

        for child in element:
            parsed = self._parse_child(child)
            if parsed:
                node.add_child(parsed)
            else:
                # Fallback: parse as HTML
                if hasattr(self.parent, '_parse_html_element'):
                    html_node = self.parent._parse_html_element(child)
                    if html_node:
                        node.add_child(html_node)
        return node

    def _parse_game_tween(self, element: ET.Element) -> TweenNode:
        tid = element.get('id', '')
        node = TweenNode(tid)
        node.target = element.get('target', '')
        node.property = element.get('property', '')
        node.to_value = self._parse_float(element.get('to'))
        node.duration = self._parse_float(element.get('duration'), 1.0)
        node.easing = element.get('easing', 'linear')
        node.loop = self._parse_bool(element.get('loop'))
        node.yoyo = self._parse_bool(element.get('yoyo'))
        node.delay = self._parse_float(element.get('delay'))
        node.auto_start = self._parse_bool(element.get('auto-start'), True)
        return node

    def _parse_game_tilemap(self, element: ET.Element) -> TilemapNode:
        tid = element.get('id', '')
        node = TilemapNode(tid)
        node.src = element.get('src', '')
        node.tile_width = self._parse_int(element.get('tile-width'), 32)
        node.tile_height = self._parse_int(element.get('tile-height'), 32)

        for child in element:
            local = self._get_local_name(child)
            if local == 'layer':
                layer = self._parse_game_layer(child)
                node.add_layer(layer)
            elif local == 'tile-animation':
                anim = self._parse_game_tile_animation(child)
                node.add_tile_animation(anim)
        return node

    def _parse_game_tile_animation(self, element: ET.Element) -> TileAnimationNode:
        """Parse <qg:tile-animation tile-id="5" frames="5,6,7,8" speed="0.15" />"""
        tile_id = self._parse_int(element.get('tile-id'), 0)
        node = TileAnimationNode(tile_id)
        node.speed = self._parse_float(element.get('speed'), 0.15)

        # Parse frames as comma-separated list of integers
        frames_str = element.get('frames', '')
        if frames_str:
            node.frames = [int(f.strip()) for f in frames_str.split(',') if f.strip()]

        return node

    def _parse_game_layer(self, element: ET.Element) -> TilemapLayerNode:
        name = element.get('name', '')
        node = TilemapLayerNode(name)
        node.collision = self._parse_bool(element.get('collision'))
        node.data = (element.text or '').strip()
        return node

    # ------------------------------------------------------------------
    # Behavior abstractions
    # ------------------------------------------------------------------

    def _parse_game_behavior(self, element: ET.Element) -> BehaviorNode:
        name = element.get('name', '')
        node = BehaviorNode(name)

        for child in element:
            parsed = self._parse_child(child)
            if parsed:
                node.add_child(parsed)
        return node

    def _parse_game_use(self, element: ET.Element) -> UseNode:
        behavior = element.get('behavior', '')
        node = UseNode(behavior)
        node.on_collision = element.get('on-collision')
        node.collision_tag = element.get('collision-tag')

        # All other attributes are overrides
        reserved = {'behavior', 'on-collision', 'collision-tag'}
        for attr_name, attr_val in element.attrib.items():
            if attr_name not in reserved:
                node.overrides[attr_name] = attr_val
        return node

    def _parse_game_prefab(self, element: ET.Element) -> PrefabNode:
        name = element.get('name', '')
        node = PrefabNode(name)

        for child in element:
            parsed = self._parse_child(child)
            if parsed:
                node.add_child(parsed)
        return node

    def _parse_game_instance(self, element: ET.Element) -> InstanceNode:
        prefab = element.get('prefab', '')
        node = InstanceNode(prefab)
        node.instance_id = element.get('id')
        node.x = self._parse_float(element.get('x'))
        node.y = self._parse_float(element.get('y'))

        reserved = {'prefab', 'id', 'x', 'y'}
        for attr_name, attr_val in element.attrib.items():
            if attr_name not in reserved:
                node.overrides[attr_name] = attr_val
        return node

    def _parse_game_group(self, element: ET.Element) -> GroupNode:
        name = element.get('name', '')
        node = GroupNode(name)
        node.tag = element.get('tag')

        for child in element:
            parsed = self._parse_child(child)
            if parsed:
                node.add_child(parsed)
        return node

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------

    def _parse_game_state_machine(self, element: ET.Element) -> StateMachineNode:
        initial = element.get('initial', '')
        node = StateMachineNode(initial)

        for child in element:
            local = self._get_local_name(child)
            if local == 'state':
                state = self._parse_game_state(child)
                node.add_state(state)
        return node

    def _parse_game_state(self, element: ET.Element) -> StateNode:
        name = element.get('name', '')
        node = StateNode(name)

        for child in element:
            ns = self._get_namespace(child)
            local = self._get_local_name(child)

            if ns == 'game' and local == 'on':
                transition = self._parse_game_transition(child)
                node.add_transition(transition)
            else:
                parsed = self._parse_child(child)
                if parsed:
                    node.add_child(parsed)
        return node

    def _parse_game_clickable(self, element: ET.Element) -> ClickableNode:
        node = ClickableNode()
        node.action = element.get('action', '')
        node.cursor = element.get('cursor', 'pointer')
        return node

    def _parse_game_transition(self, element: ET.Element) -> TransitionNode:
        event = element.get('event', '')
        transition = element.get('transition', '')
        return TransitionNode(event, transition)

    def _parse_game_event(self, element: ET.Element) -> EventNode:
        """Parse <qg:event> - Declarative event listener.

        Attributes:
            name: Event name to listen for
            handler or action: Function to call when event fires
            filter-tag: Optional tag filter
            filter-id: Optional sprite ID filter
            scope: Event scope (scene, sprite, global)
        """
        name = element.get('name', '')
        handler = element.get('handler') or element.get('action', '')
        node = EventNode(name, handler)
        node.filter_tag = element.get('filter-tag')
        node.filter_id = element.get('filter-id')
        node.scope = element.get('scope', 'scene')
        return node

    def _parse_game_on_collision(self, element: ET.Element) -> OnCollisionNode:
        """Parse <qg:on-collision> - Inline collision handler for sprites.

        Attributes:
            with-tag: Tag of target sprites to collide with
            with-id: Specific sprite ID to collide with
            action: Action to perform (destroy-self, destroy-other, emit:eventName, call:funcName)

        Example:
            <qg:sprite id="mario" tag="player">
              <qg:on-collision with-tag="coin" action="destroy-other" />
              <qg:on-collision with-tag="enemy" action="emit:player-hit" />
            </qg:sprite>
        """
        node = OnCollisionNode()
        node.with_tag = element.get('with-tag')
        node.with_id = element.get('with-id')
        node.action = element.get('action', '')
        return node
