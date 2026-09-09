"""
AST Nodes for Game Engine 2D (qg: namespace)

All game-specific AST nodes for the Quantum 2D game engine.
These represent game objects, systems, behaviors, and abstractions
that compile to PixiJS + Matter.js JavaScript.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import sys
from pathlib import Path
from quantum.core.ast_nodes import QuantumNode


# ============================================
# CORE GAME NODES
# ============================================

class SceneNode(QuantumNode):
    """Represents <qg:scene> - A game scene with auto game loop."""

    VALID_SCENE_TYPES = ('level', 'title', 'map', 'overlay')

    VALID_DEATH_SEQUENCES = ('smw', 'instant', 'respawn')

    def __init__(self, name: str):
        self.name = name
        self.width: int = 800
        self.height: int = 600
        self.viewport_width: Optional[int] = None  # Canvas width (defaults to width)
        self.viewport_height: Optional[int] = None  # Canvas height (defaults to height)
        self.background: str = "#000000"
        self.active: bool = True
        self.scene_type: str = "level"   # level, title, map, overlay
        self.initial: bool = False        # marks as entry scene
        self.children: List[QuantumNode] = []

        # Death / game over
        self.death_sequence: Optional[str] = None  # "smw", "instant", "respawn"
        self.death_timer: float = 3.0               # Seconds before reload after death
        self.game_over_jingle: Optional[str] = None  # Audio path for game over jingle
        self.game_over_alphabet: Optional[str] = None  # Sprite path for alphabet tileset

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "type": "game_scene",
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "background": self.background,
            "active": self.active,
            "scene_type": self.scene_type,
            "initial": self.initial,
            "children_count": len(self.children),
        }
        if self.death_sequence is not None:
            result["death_sequence"] = self.death_sequence
        if self.game_over_jingle is not None:
            result["game_over_jingle"] = self.game_over_jingle
        if self.game_over_alphabet is not None:
            result["game_over_alphabet"] = self.game_over_alphabet
        return result

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Scene name is required")
        if self.width <= 0:
            errors.append("Scene width must be positive")
        if self.height <= 0:
            errors.append("Scene height must be positive")
        if self.scene_type not in self.VALID_SCENE_TYPES:
            errors.append(f"Invalid scene type: {self.scene_type}. Must be one of {', '.join(self.VALID_SCENE_TYPES)}")
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class SpriteNode(QuantumNode):
    """Represents <qg:sprite> - A game sprite with optional physics."""

    def __init__(self, sprite_id: str):
        self.sprite_id = sprite_id
        self.src: str = ""
        self.x: float = 0
        self.y: float = 0
        self.width: Optional[float] = None
        self.height: Optional[float] = None
        self.anchor_x: float = 0.5
        self.anchor_y: float = 0.5
        self.rotation: float = 0
        self.scale_x: float = 1
        self.scale_y: float = 1
        self.alpha: float = 1.0
        self.visible: bool = True
        self.color: Optional[str] = None  # Hex color for sprites without images
        self.tag: Optional[str] = None
        self.layer: int = 0

        # Spritesheet
        self.frame_width: Optional[int] = None
        self.frame_height: Optional[int] = None

        # Physics (Matter.js)
        self.body: Optional[str] = None  # static, dynamic, kinematic
        self.shape: str = 'box'  # box, circle, slope-left, slope-right
        self.bounce: float = 0.1
        self.friction: float = 0.1
        self.mass: Optional[float] = None
        self.sensor: bool = False

        # Magic controls
        self.controls: Optional[str] = None  # wasd, arrows, custom
        self.speed: float = 5.0
        self.jump_force: float = 10.0

        # SMW-style jump physics
        self.gravity_up: Optional[float] = None  # Gravity while ascending (lower = floatier)
        self.gravity_down: Optional[float] = None  # Gravity while descending (higher = snappier)
        self.jump_hold_boost: float = 0.4  # Extra upward force while holding jump
        self.coyote_frames: int = 6  # Frames allowed to jump after leaving platform
        self.max_fall_speed: float = 15.0  # Terminal velocity

        # Collision layers (int bitmask or str named layer)
        self.collision_layer = None  # int bitmask or str layer name
        self.collision_mask = None   # int bitmask or str comma-separated layer names
        self.floor_max_angle: Optional[float] = None  # Max floor angle in degrees (default 45)

        # Special abilities
        self.spin_jump: bool = False  # SMW spin jump (kills enemies instantly, rotates sprite)

        # Children (animations, colliders, behaviors)
        self.children: List[QuantumNode] = []

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_sprite",
            "id": self.sprite_id,
            "src": self.src,
            "x": self.x,
            "y": self.y,
            "body": self.body,
            "controls": self.controls,
            "tag": self.tag,
            "children_count": len(self.children),
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.sprite_id:
            errors.append("Sprite id is required")
        if self.body and self.body not in ('static', 'dynamic', 'kinematic'):
            errors.append(f"Invalid body type: {self.body}. Must be static, dynamic, or kinematic")
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class PhysicsNode(QuantumNode):
    """Represents <qg:physics> - Scene-level physics configuration."""

    def __init__(self):
        self.gravity_x: float = 0
        self.gravity_y: float = 9.8
        self.bounds: Optional[str] = None  # canvas, scene, none
        self.debug: bool = False
        self.collision_layers: Dict[str, int] = {}  # name -> bitmask value
        self.children: List[QuantumNode] = []

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "type": "game_physics",
            "gravity_x": self.gravity_x,
            "gravity_y": self.gravity_y,
            "bounds": self.bounds,
            "debug": self.debug,
        }
        if self.collision_layers:
            result["collision_layers"] = self.collision_layers
        return result

    def validate(self) -> List[str]:
        return []


class ColliderNode(QuantumNode):
    """Represents <qg:collider> - Override collision shape for a sprite."""

    def __init__(self):
        self.shape: str = "box"  # box, circle, polygon
        self.width: Optional[float] = None
        self.height: Optional[float] = None
        self.radius: Optional[float] = None
        self.vertices: Optional[str] = None  # JSON array of points
        self.offset_x: float = 0
        self.offset_y: float = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_collider",
            "shape": self.shape,
        }

    def validate(self) -> List[str]:
        errors = []
        if self.shape not in ('box', 'circle', 'polygon'):
            errors.append(f"Invalid collider shape: {self.shape}")
        return errors


class AnimationNode(QuantumNode):
    """Represents <qg:animation> - Sprite animation from spritesheet."""

    def __init__(self, name: str):
        self.name = name
        self.frames: str = ""  # e.g. "0-3", "0,1,2,3"
        self.speed: float = 0.1
        self.loop: bool = True
        self.auto_play: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_animation",
            "name": self.name,
            "frames": self.frames,
            "speed": self.speed,
            "loop": self.loop,
            "auto_play": self.auto_play,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Animation name is required")
        if not self.frames:
            errors.append("Animation frames are required")
        return errors


class OnCollisionNode(QuantumNode):
    """Represents <qg:on-collision> - Inline collision handler for sprites.

    Allows simple collision responses without creating behaviors:
        <qg:sprite id="mario" tag="player">
            <qg:on-collision with-tag="coin" action="destroy-other" />
            <qg:on-collision with-tag="enemy" action="emit:player-hit" />
        </qg:sprite>

    Supported actions:
        - destroy-self: Remove this sprite
        - destroy-other: Remove the colliding sprite
        - emit:eventName: Emit a custom event
    """

    def __init__(self):
        self.with_tag: Optional[str] = None  # Tag to collide with
        self.with_id: Optional[str] = None   # Specific sprite ID to collide with
        self.action: str = ""                # Action to perform

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_on_collision",
            "with_tag": self.with_tag,
            "with_id": self.with_id,
            "action": self.action,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.with_tag and not self.with_id:
            errors.append("on-collision requires with-tag or with-id")
        if not self.action:
            errors.append("on-collision requires an action")
        return errors


class CameraNode(QuantumNode):
    """Represents <qg:camera> - Camera system with follow and bounds."""

    def __init__(self):
        self.follow: Optional[str] = None  # sprite id to follow
        self.lerp: float = 0.1
        self.bounds: Optional[str] = None  # scene, none
        self.zoom: float = 1.0
        self.offset_x: float = 0
        self.offset_y: float = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_camera",
            "follow": self.follow,
            "lerp": self.lerp,
            "bounds": self.bounds,
        }

    def validate(self) -> List[str]:
        return []


class InputNode(QuantumNode):
    """Represents <qg:input> - Custom input mapping."""

    def __init__(self):
        self.key: str = ""
        self.action: str = ""
        self.input_type: str = "press"  # press, hold, release, click, mousedown, mouseup, mousemove

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_input",
            "key": self.key,
            "action": self.action,
            "input_type": self.input_type,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.key:
            errors.append("Input key is required")
        if not self.action:
            errors.append("Input action is required")
        return errors


class SoundNode(QuantumNode):
    """Represents <qg:sound> - Audio with trigger-based playback."""

    def __init__(self, sound_id: str):
        self.sound_id = sound_id
        self.src: str = ""
        self.volume: float = 1.0
        self.loop: bool = False
        self.trigger: Optional[str] = None  # e.g. "player.jump", "scene.start"
        self.channel: str = "sfx"  # sfx, music

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_sound",
            "id": self.sound_id,
            "src": self.src,
            "trigger": self.trigger,
            "channel": self.channel,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.sound_id:
            errors.append("Sound id is required")
        if not self.src:
            errors.append("Sound src is required")
        return errors


class ParticleNode(QuantumNode):
    """Represents <qg:particle> - Particle emitter."""

    def __init__(self, particle_id: str):
        self.particle_id = particle_id
        self.src: str = ""
        self.follow: Optional[str] = None
        self.trigger: Optional[str] = None
        self.count: int = 20
        self.emit_rate: int = 10
        self.lifetime: float = 1.0
        self.speed_min: float = 1.0
        self.speed_max: float = 3.0
        self.angle_min: float = 0
        self.angle_max: float = 360
        self.alpha_start: float = 1.0
        self.alpha_end: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_particle",
            "id": self.particle_id,
            "follow": self.follow,
            "trigger": self.trigger,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.particle_id:
            errors.append("Particle id is required")
        return errors


class TimerNode(QuantumNode):
    """Represents <qg:timer> - Declarative game timer."""

    def __init__(self, timer_id: str):
        self.timer_id = timer_id
        self.interval: float = 1.0
        self.repeat: int = -1  # -1 = infinite
        self.auto_start: bool = True
        self.action: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_timer",
            "id": self.timer_id,
            "interval": self.interval,
            "action": self.action,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.timer_id:
            errors.append("Timer id is required")
        if not self.action:
            errors.append("Timer action is required")
        return errors


class SpawnNode(QuantumNode):
    """Represents <qg:spawn> - Object spawner with pooling."""

    def __init__(self, spawn_id: str):
        self.spawn_id = spawn_id
        self.prefab: str = ""
        self.count: int = 1
        self.interval: Optional[float] = None
        self.x: Optional[str] = None
        self.y: Optional[str] = None
        self.pool_size: int = 10

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_spawn",
            "id": self.spawn_id,
            "prefab": self.prefab,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.spawn_id:
            errors.append("Spawn id is required")
        if not self.prefab:
            errors.append("Spawn prefab is required")
        return errors


class HudNode(QuantumNode):
    """Represents <qg:hud> - Fixed overlay on camera.

    Supports two modes:
    1. HTML mode (legacy): children are HTMLNode/TextNode elements
    2. Tile-based mode: children are HudTileNode, HudCounterNode, etc.

    Tile-based mode is detected by presence of background/sprite-prefix attrs
    or HudTile*/HudCounter*/HudCollection* children.
    """

    def __init__(self):
        self.position: str = "top-left"
        self.background: Optional[str] = None  # e.g. "rgba(0,0,0,0.55)"
        self.background_height: Optional[int] = None  # px height of bg bar
        self.sprite_prefix: Optional[str] = None  # e.g. "assets/smw/sprites/hud_"
        self.children: List[QuantumNode] = []

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "type": "game_hud",
            "position": self.position,
            "children_count": len(self.children),
        }
        if self.background is not None:
            result["background"] = self.background
        if self.background_height is not None:
            result["background_height"] = self.background_height
        if self.sprite_prefix is not None:
            result["sprite_prefix"] = self.sprite_prefix
        return result

    def validate(self) -> List[str]:
        errors = []
        valid = ('top-left', 'top-right', 'top-center',
                 'bottom-left', 'bottom-right', 'bottom-center', 'center')
        # Only validate position for HTML-mode HUDs (no background = legacy)
        if self.background is None and self.position not in valid:
            errors.append(f"Invalid HUD position: {self.position}")
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class HudTileNode(QuantumNode):
    """Represents <qg:tile> inside <qg:hud> - Static sprite tile."""

    def __init__(self):
        self.sprite: str = ""  # Sprite filename (resolved with prefix)
        self.x: int = 0
        self.y: int = 0
        self.width: Optional[int] = None
        self.height: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "hud_tile",
            "sprite": self.sprite,
            "x": self.x,
            "y": self.y,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.sprite:
            errors.append("HUD tile sprite is required")
        return errors


class HudCounterNode(QuantumNode):
    """Represents <qg:counter> inside <qg:hud> - Numeric counter from digit strip."""

    def __init__(self):
        self.strip: str = ""  # Digit strip image (0-9 horizontally)
        self.x: int = 0
        self.y: int = 0
        self.digits: int = 2
        self.bind: str = ""  # e.g. "{coins}"
        self.digit_width: int = 8
        self.digit_height: int = 8
        self.countdown: bool = False
        self.hurry_at: Optional[int] = None  # Flash when value reaches this
        self.flash: Optional[str] = None  # Flash color name (e.g. "red")
        self.align: str = "left"  # "left" or "right"
        self.right_edge: Optional[int] = None  # Right edge x for align="right"
        self.tint: Optional[str] = None  # Constant tint color name (e.g. "yellow")
        self.intelligent: bool = False  # No zero-padding, show only needed digits
        self.icon: Optional[str] = None  # Prefix icon sprite (e.g. "coin_icon.png")
        self.symbol: Optional[str] = None  # Prefix symbol sprite (e.g. "x_symbol.png")
        self.extra_life_at: Optional[int] = None  # Add life and reset at this value

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "type": "hud_counter",
            "strip": self.strip,
            "x": self.x,
            "y": self.y,
            "digits": self.digits,
            "bind": self.bind,
        }
        if self.countdown:
            result["countdown"] = True
        if self.hurry_at is not None:
            result["hurry_at"] = self.hurry_at
        if self.flash is not None:
            result["flash"] = self.flash
        if self.align != "left":
            result["align"] = self.align
        if self.right_edge is not None:
            result["right_edge"] = self.right_edge
        if self.tint is not None:
            result["tint"] = self.tint
        if self.intelligent:
            result["intelligent"] = True
        if self.icon is not None:
            result["icon"] = self.icon
        if self.symbol is not None:
            result["symbol"] = self.symbol
        if self.extra_life_at is not None:
            result["extra_life_at"] = self.extra_life_at
        return result

    def validate(self) -> List[str]:
        errors = []
        if not self.strip:
            errors.append("HUD counter strip is required")
        if not self.bind:
            errors.append("HUD counter bind is required")
        if self.digits < 1:
            errors.append("HUD counter digits must be >= 1")
        return errors


class HudCollectionNode(QuantumNode):
    """Represents <qg:collection> inside <qg:hud> - Repeated sprites (e.g. dragon coins)."""

    def __init__(self):
        self.sprite: str = ""
        self.x: int = 0
        self.y: int = 0
        self.spacing: int = 8
        self.max: int = 5
        self.bind: str = ""  # e.g. "{yoshi_coins}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "hud_collection",
            "sprite": self.sprite,
            "x": self.x,
            "y": self.y,
            "spacing": self.spacing,
            "max": self.max,
            "bind": self.bind,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.sprite:
            errors.append("HUD collection sprite is required")
        if not self.bind:
            errors.append("HUD collection bind is required")
        if self.max < 1:
            errors.append("HUD collection max must be >= 1")
        return errors


class HudSlotNode(QuantumNode):
    """Represents <qg:slot> inside <qg:hud> - Switchable sprite based on variable."""

    def __init__(self):
        self.x: int = 0
        self.y: int = 0
        self.bind: str = ""  # e.g. "{powerup_state}"
        self.options: List['HudOptionNode'] = []

    def add_option(self, option: 'HudOptionNode'):
        self.options.append(option)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "hud_slot",
            "x": self.x,
            "y": self.y,
            "bind": self.bind,
            "options_count": len(self.options),
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.bind:
            errors.append("HUD slot bind is required")
        if not self.options:
            errors.append("HUD slot must have at least one option")
        for opt in self.options:
            if hasattr(opt, 'validate'):
                errors.extend(opt.validate())
        return errors


class HudOptionNode(QuantumNode):
    """Represents <qg:option> inside <qg:slot> - One sprite option."""

    def __init__(self):
        self.value: str = ""
        self.sprite: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "hud_option",
            "value": self.value,
            "sprite": self.sprite,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.value:
            errors.append("HUD option value is required")
        if not self.sprite:
            errors.append("HUD option sprite is required")
        return errors


class HudBehaviorNode(QuantumNode):
    """Represents <qg:hud-behavior> - Event trigger based on HUD variable state."""

    def __init__(self):
        self.target: str = ""  # Variable name (e.g. "time_left")
        self.event: str = ""  # Event type (e.g. "reach")
        self.value: Optional[int] = None  # Threshold value
        self.actions: List['HudActionNode'] = []

    def add_action(self, action: 'HudActionNode'):
        self.actions.append(action)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "type": "hud_behavior",
            "target": self.target,
            "event": self.event,
        }
        if self.value is not None:
            result["value"] = self.value
        result["actions_count"] = len(self.actions)
        return result

    def validate(self) -> List[str]:
        errors = []
        if not self.target:
            errors.append("HUD behavior target is required")
        if not self.event:
            errors.append("HUD behavior event is required")
        if not self.actions:
            errors.append("HUD behavior must have at least one action")
        for action in self.actions:
            if hasattr(action, 'validate'):
                errors.extend(action.validate())
        return errors


class HudActionNode(QuantumNode):
    """Represents <qg:action> inside <qg:hud-behavior> - Action to perform."""

    def __init__(self):
        self.action_type: str = ""  # "emit", "set", etc.
        self.event: Optional[str] = None  # For emit type
        self.rate: Optional[float] = None  # For countdown rate

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "type": "hud_action",
            "action_type": self.action_type,
        }
        if self.event is not None:
            result["event"] = self.event
        if self.rate is not None:
            result["rate"] = self.rate
        return result

    def validate(self) -> List[str]:
        errors = []
        if not self.action_type:
            errors.append("HUD action type is required")
        return errors


class TweenNode(QuantumNode):
    """Represents <qg:tween> - Declarative animation tween."""

    def __init__(self, tween_id: str):
        self.tween_id = tween_id
        self.target: str = ""
        self.property: str = ""  # x, y, alpha, rotation, scale
        self.to_value: float = 0
        self.duration: float = 1.0
        self.easing: str = "linear"
        self.loop: bool = False
        self.yoyo: bool = False
        self.delay: float = 0
        self.auto_start: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_tween",
            "id": self.tween_id,
            "target": self.target,
            "property": self.property,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.tween_id:
            errors.append("Tween id is required")
        if not self.target:
            errors.append("Tween target is required")
        if not self.property:
            errors.append("Tween property is required")
        return errors


class TileAnimationNode(QuantumNode):
    """Represents <qg:tile-animation> - Animated tile definition."""

    def __init__(self, tile_id: int):
        self.tile_id = tile_id  # Which tile ID to animate
        self.frames: List[int] = []  # List of tile IDs for animation frames
        self.speed: float = 0.15  # Seconds per frame

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_tile_animation",
            "tile_id": self.tile_id,
            "frames": self.frames,
            "speed": self.speed,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.frames:
            errors.append("Tile animation must have at least one frame")
        return errors


class TilemapNode(QuantumNode):
    """Represents <qg:tilemap> - Tile-based map."""

    def __init__(self, tilemap_id: str):
        self.tilemap_id = tilemap_id
        self.src: str = ""  # tileset image or .tres resource
        self.data_src: Optional[str] = None  # External JSON file with grid data
        self.tile_width: int = 32
        self.tile_height: int = 32
        self.layers: List['TilemapLayerNode'] = []
        self.tile_animations: List['TileAnimationNode'] = []  # Animated tile definitions

    def add_layer(self, layer: 'TilemapLayerNode'):
        self.layers.append(layer)

    def add_tile_animation(self, anim: 'TileAnimationNode'):
        self.tile_animations.append(anim)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_tilemap",
            "id": self.tilemap_id,
            "tile_width": self.tile_width,
            "tile_height": self.tile_height,
            "layers_count": len(self.layers),
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.tilemap_id:
            errors.append("Tilemap id is required")
        for layer in self.layers:
            errors.extend(layer.validate())
        return errors


class TilemapLayerNode(QuantumNode):
    """Represents <qg:layer> - A layer within a tilemap."""

    def __init__(self, name: str):
        self.name = name
        self.data: str = ""  # CSV tile data (empty when using data-src on parent)
        self.collision: bool = False
        self.external_data: bool = False  # True when parent tilemap uses data-src

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_tilemap_layer",
            "name": self.name,
            "collision": self.collision,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Tilemap layer name is required")
        if not self.data and not self.external_data:
            errors.append("Tilemap layer data is required")
        return errors


# ============================================
# BEHAVIOR & ABSTRACTION NODES
# ============================================

class BehaviorNode(QuantumNode):
    """Represents <qg:behavior> - Reusable behavior encapsulating state + functions."""

    def __init__(self, name: str):
        self.name = name
        self.children: List[QuantumNode] = []  # q:set, q:function, qg:state-machine

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_behavior",
            "name": self.name,
            "children_count": len(self.children),
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Behavior name is required")
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class UseNode(QuantumNode):
    """Represents <qg:use> - Attach a behavior to a sprite/group."""

    def __init__(self, behavior: str):
        self.behavior = behavior
        self.overrides: Dict[str, str] = {}
        self.on_collision: Optional[str] = None
        self.collision_tag: Optional[str] = None
        # Handlers past the first, from <qg:on-collision> children: a patrol
        # that turns at a wall AND at a ledge needs two, and one attribute
        # holds one.
        self.extra_collisions: List[Dict[str, Optional[str]]] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_use",
            "behavior": self.behavior,
            "overrides": self.overrides,
            "on_collision": self.on_collision,
            "collision_tag": self.collision_tag,
            "extra_collisions": self.extra_collisions,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.behavior:
            errors.append("Use behavior name is required")
        return errors


class PrefabNode(QuantumNode):
    """Represents <qg:prefab> - Reusable game object template with semantic attributes.

    Semantic attributes allow declarative specification of game entity behavior
    (combat, movement, rewards, etc.) without manual JavaScript. These attributes
    are optional and default to None/False/0 for backward compatibility.
    """

    # Valid values for validated fields
    VALID_ENTITY_TYPES = ('enemy', 'item', 'block', 'hazard', 'goal', 'projectile')
    VALID_DEFEATED_BY = ('stomp', 'fire', 'star', 'shell', 'any')
    VALID_MOVEMENTS = ('patrol', 'chase', 'fly-patrol', 'hop', 'path', 'none')
    VALID_EFFECTS = ('grow', 'fire-power', 'invincible', 'extra-life', 'speed-up')
    VALID_FACINGS = ('left', 'right')

    def __init__(self, name: str):
        self.name = name
        self.children: List[QuantumNode] = []  # Typically one sprite with children

        # --- Classification ---
        self.entity_type: Optional[str] = None  # enemy, item, block, hazard, goal, projectile

        # --- Combat ---
        self.health: Optional[int] = None       # Hit points (e.g. 2 = dies after 2 stomps)
        self.defeated_by: Optional[str] = None   # stomp, fire, star, shell, any
        self.on_defeat: Optional[str] = None     # Event/action on defeat (e.g. "emit:enemy-killed")
        self.contact_damage: Optional[int] = None # Damage dealt on contact
        self.knockback: Optional[float] = None    # Knockback force applied to player
        self.i_frames: Optional[int] = None       # Invincibility frames after hit
        self.stomp_bounce: Optional[float] = None  # Bounce force when stomped

        # --- Movement ---
        self.movement: Optional[str] = None      # patrol, chase, fly-patrol, hop, path, none
        self.move_speed: Optional[float] = None   # Movement speed
        self.turn_on_edge: Optional[bool] = None  # Turn around at platform edges
        self.facing: Optional[str] = None          # Initial facing direction: left, right
        self.turn_cooldown: Optional[float] = None  # Delay before allowing next turn (anti-oscillation)

        # --- Reward ---
        self.reward: Optional[str] = None         # Reward on collect/interact (e.g. "score:100")
        self.reward_kill: Optional[str] = None     # Reward on kill (e.g. "score:200")

        # --- Respawn ---
        self.respawns: Optional[bool] = None       # Whether entity respawns after defeat
        self.respawn_delay: Optional[float] = None  # Seconds before respawn

        # --- Item ---
        self.effect: Optional[str] = None          # grow, fire-power, invincible, extra-life, speed-up
        self.duration: Optional[float] = None       # Effect duration in seconds
        self.auto_move: Optional[bool] = None       # Item moves after spawning (e.g. mushroom)
        self.collectible: Optional[bool] = None     # Can be collected on contact
        self.carryable: Optional[bool] = None       # Can be picked up and carried

        # --- Block ---
        self.content: Optional[str] = None          # What's inside: coin, mushroom, star, etc.
        self.hits: Optional[int] = None             # Hits before empty (e.g. 1 for ? block)
        self.breakable: Optional[bool] = None       # Can be broken (e.g. brick block)
        self.invisible: Optional[bool] = None       # Hidden until hit from below

        # --- Checkpoint ---
        self.checkpoint: Optional[bool] = None      # Acts as a checkpoint (one-time activation)

        # --- Flying ---
        self.flying: Optional[bool] = None          # Block with wings (oscillating movement)

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "type": "game_prefab",
            "name": self.name,
            "children_count": len(self.children),
        }
        # Include semantic attributes only when set (non-None)
        if self.entity_type is not None:
            result["entity_type"] = self.entity_type
        if self.health is not None:
            result["health"] = self.health
        if self.defeated_by is not None:
            result["defeated_by"] = self.defeated_by
        if self.on_defeat is not None:
            result["on_defeat"] = self.on_defeat
        if self.contact_damage is not None:
            result["contact_damage"] = self.contact_damage
        if self.knockback is not None:
            result["knockback"] = self.knockback
        if self.i_frames is not None:
            result["i_frames"] = self.i_frames
        if self.stomp_bounce is not None:
            result["stomp_bounce"] = self.stomp_bounce
        if self.movement is not None:
            result["movement"] = self.movement
        if self.move_speed is not None:
            result["move_speed"] = self.move_speed
        if self.turn_on_edge is not None:
            result["turn_on_edge"] = self.turn_on_edge
        if self.facing is not None:
            result["facing"] = self.facing
        if self.turn_cooldown is not None:
            result["turn_cooldown"] = self.turn_cooldown
        if self.reward is not None:
            result["reward"] = self.reward
        if self.reward_kill is not None:
            result["reward_kill"] = self.reward_kill
        if self.respawns is not None:
            result["respawns"] = self.respawns
        if self.respawn_delay is not None:
            result["respawn_delay"] = self.respawn_delay
        if self.effect is not None:
            result["effect"] = self.effect
        if self.duration is not None:
            result["duration"] = self.duration
        if self.auto_move is not None:
            result["auto_move"] = self.auto_move
        if self.collectible is not None:
            result["collectible"] = self.collectible
        if self.carryable is not None:
            result["carryable"] = self.carryable
        if self.content is not None:
            result["content"] = self.content
        if self.hits is not None:
            result["hits"] = self.hits
        if self.breakable is not None:
            result["breakable"] = self.breakable
        if self.invisible is not None:
            result["invisible"] = self.invisible
        if self.checkpoint is not None:
            result["checkpoint"] = self.checkpoint
        if self.flying is not None:
            result["flying"] = self.flying
        return result

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Prefab name is required")
        if not self.children:
            errors.append("Prefab must contain at least one child")

        # Validate semantic attribute values
        if self.entity_type is not None and self.entity_type not in self.VALID_ENTITY_TYPES:
            errors.append(f"Invalid entity type: {self.entity_type}. Must be one of {', '.join(self.VALID_ENTITY_TYPES)}")
        if self.defeated_by is not None and self.defeated_by not in self.VALID_DEFEATED_BY:
            errors.append(f"Invalid defeated-by: {self.defeated_by}. Must be one of {', '.join(self.VALID_DEFEATED_BY)}")
        if self.movement is not None and self.movement not in self.VALID_MOVEMENTS:
            errors.append(f"Invalid movement: {self.movement}. Must be one of {', '.join(self.VALID_MOVEMENTS)}")
        if self.effect is not None and self.effect not in self.VALID_EFFECTS:
            errors.append(f"Invalid effect: {self.effect}. Must be one of {', '.join(self.VALID_EFFECTS)}")
        if self.facing is not None and self.facing not in self.VALID_FACINGS:
            errors.append(f"Invalid facing: {self.facing}. Must be one of {', '.join(self.VALID_FACINGS)}")
        if self.health is not None and self.health < 0:
            errors.append("Health must be non-negative")
        if self.hits is not None and self.hits < 0:
            errors.append("Hits must be non-negative")

        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class InstanceNode(QuantumNode):
    """Represents <qg:instance> - Instantiate a prefab."""

    def __init__(self, prefab: str):
        self.prefab = prefab
        self.instance_id: Optional[str] = None
        self.x: float = 0
        self.y: float = 0
        self.overrides: Dict[str, str] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_instance",
            "prefab": self.prefab,
            "id": self.instance_id,
            "x": self.x,
            "y": self.y,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.prefab:
            errors.append("Instance prefab name is required")
        return errors


# ============================================
# ENEMY SYSTEM NODES
# ============================================

VALID_AI_TYPES = ('patrol', 'chase', 'fly-patrol', 'hop', 'path', 'charge', 'emerge')
VALID_DEFEAT_BY = ('stomp', 'fire', 'star', 'shell')
VALID_HIT_EFFECTS = ('squish', 'shrink', 'flash')
VALID_KILL_EFFECTS = ('puff', 'explode', 'fade')


class EnemyOnHitNode(QuantumNode):
    """Represents <qg:on-hit> - What happens when enemy is hit (not killed)."""

    def __init__(self):
        self.score: int = 0
        self.effect: Optional[str] = None
        self.speed_multiply: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_enemy_on_hit",
            "score": self.score,
            "effect": self.effect,
            "speed_multiply": self.speed_multiply,
        }

    def validate(self) -> List[str]:
        errors = []
        if self.effect is not None and self.effect not in VALID_HIT_EFFECTS:
            errors.append(f"Invalid hit effect: {self.effect}. Must be one of {', '.join(VALID_HIT_EFFECTS)}")
        return errors


class EnemyOnKillNode(QuantumNode):
    """Represents <qg:on-kill> - What happens when enemy is killed."""

    def __init__(self):
        self.score: int = 0
        self.effect: Optional[str] = None
        self.drop: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_enemy_on_kill",
            "score": self.score,
            "effect": self.effect,
            "drop": self.drop,
        }

    def validate(self) -> List[str]:
        errors = []
        if self.effect is not None and self.effect not in VALID_KILL_EFFECTS:
            errors.append(f"Invalid kill effect: {self.effect}. Must be one of {', '.join(VALID_KILL_EFFECTS)}")
        return errors


class EnemyDefeatNode(QuantumNode):
    """Represents <qg:defeat> - How enemy can be defeated."""

    def __init__(self):
        self.by: str = 'stomp'
        self.health: int = 1
        self.bounce: Optional[float] = None
        self.on_hit: Optional[EnemyOnHitNode] = None
        self.on_kill: Optional[EnemyOnKillNode] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_enemy_defeat",
            "by": self.by,
            "health": self.health,
            "bounce": self.bounce,
            "on_hit": self.on_hit.to_dict() if self.on_hit else None,
            "on_kill": self.on_kill.to_dict() if self.on_kill else None,
        }

    def validate(self) -> List[str]:
        errors = []
        if self.by not in VALID_DEFEAT_BY:
            errors.append(f"Invalid defeat by: {self.by}. Must be one of {', '.join(VALID_DEFEAT_BY)}")
        if self.health < 1:
            errors.append("Defeat health must be >= 1")
        if self.on_hit:
            errors.extend(self.on_hit.validate())
        if self.on_kill:
            errors.extend(self.on_kill.validate())
        return errors


class EnemyAiNode(QuantumNode):
    """Represents <qg:ai> - Enemy AI behavior."""

    def __init__(self):
        self.ai_type: str = 'patrol'
        self.speed: float = 30.0
        self.turn_cooldown: Optional[float] = None
        self.turn_on_edge: bool = False
        self.facing: str = 'left'

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_enemy_ai",
            "ai_type": self.ai_type,
            "speed": self.speed,
            "turn_cooldown": self.turn_cooldown,
            "turn_on_edge": self.turn_on_edge,
            "facing": self.facing,
        }

    def validate(self) -> List[str]:
        errors = []
        if self.ai_type not in VALID_AI_TYPES:
            errors.append(f"Invalid AI type: {self.ai_type}. Must be one of {', '.join(VALID_AI_TYPES)}")
        if self.speed < 0:
            errors.append("AI speed must be non-negative")
        if self.facing not in ('left', 'right'):
            errors.append(f"Invalid facing: {self.facing}. Must be 'left' or 'right'")
        return errors


class EnemyNode(QuantumNode):
    """Represents <qg:enemy> - Enemy behavior definition (AI + defeat + rewards).

    Separates behavior from visual (prefab) and placement (instance).
    """

    def __init__(self, prefab: str):
        self.prefab = prefab
        self.ai: Optional[EnemyAiNode] = None
        self.defeat: Optional[EnemyDefeatNode] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_enemy",
            "prefab": self.prefab,
            "ai": self.ai.to_dict() if self.ai else None,
            "defeat": self.defeat.to_dict() if self.defeat else None,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.prefab:
            errors.append("Enemy prefab name is required")
        if self.ai:
            errors.extend(self.ai.validate())
        if self.defeat:
            errors.extend(self.defeat.validate())
        return errors


class GroupNode(QuantumNode):
    """Represents <qg:group> - Group sprites with shared behavior."""

    def __init__(self, name: str):
        self.name = name
        self.tag: Optional[str] = None
        self.children: List[QuantumNode] = []

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_group",
            "name": self.name,
            "tag": self.tag,
            "children_count": len(self.children),
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Group name is required")
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


# ============================================
# STATE MACHINE NODES
# ============================================

class StateMachineNode(QuantumNode):
    """Represents <qg:state-machine> - Declarative FSM."""

    def __init__(self, initial: str):
        self.initial = initial
        self.states: List['StateNode'] = []

    def add_state(self, state: 'StateNode'):
        self.states.append(state)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_state_machine",
            "initial": self.initial,
            "states_count": len(self.states),
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.initial:
            errors.append("State machine initial state is required")
        if not self.states:
            errors.append("State machine must have at least one state")
        state_names = [s.name for s in self.states]
        if self.initial not in state_names:
            errors.append(f"Initial state '{self.initial}' not found in states")
        for state in self.states:
            errors.extend(state.validate())
        return errors


class StateNode(QuantumNode):
    """Represents <qg:state> - Individual state in a state machine."""

    def __init__(self, name: str):
        self.name = name
        self.transitions: List['TransitionNode'] = []
        self.children: List[QuantumNode] = []  # q:function nodes (enter, update, exit)

    def add_transition(self, transition: 'TransitionNode'):
        self.transitions.append(transition)

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_state",
            "name": self.name,
            "transitions_count": len(self.transitions),
            "children_count": len(self.children),
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("State name is required")
        for t in self.transitions:
            errors.extend(t.validate())
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class RawCodeNode(QuantumNode):
    """Represents raw JavaScript code inside a q:function in game context.

    Allows free-form JS text (e.g. game.destroy(self)) alongside XML-parsed nodes.
    """

    def __init__(self, code: str):
        self.code = code

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "raw_code",
            "code": self.code,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.code or not self.code.strip():
            errors.append("RawCodeNode code is empty")
        return errors


class ClickableNode(QuantumNode):
    """Represents <qg:clickable> - Makes a sprite respond to mouse/pointer events."""

    def __init__(self):
        self.action: str = ""
        self.cursor: str = "pointer"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_clickable",
            "action": self.action,
            "cursor": self.cursor,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.action:
            errors.append("Clickable action is required")
        return errors


class TransitionNode(QuantumNode):
    """Represents <qg:on> - State transition triggered by event."""

    def __init__(self, event: str, transition: str):
        self.event = event
        self.transition = transition

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_transition",
            "event": self.event,
            "transition": self.transition,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.event:
            errors.append("Transition event is required")
        if not self.transition:
            errors.append("Transition target state is required")
        return errors


class EventNode(QuantumNode):
    """Represents <qg:event> - Declarative event listener.

    Allows registering event handlers at scene level:
        <qg:event name="coinCollected" handler="onCoinCollected" />
        <qg:event name="playerDied" handler="onPlayerDied" filter-tag="player" />

    Attributes:
        name: Event name to listen for (e.g., "coinCollected", "player.jump")
        handler: Function name to call when event fires
        filter_tag: Optional tag filter - only handle events from sprites with this tag
        filter_id: Optional sprite ID filter - only handle events from this specific sprite
        scope: Event scope - "scene" (default), "sprite", or "global"
    """

    def __init__(self, name: str, handler: str):
        self.name = name
        self.handler = handler
        self.filter_tag: Optional[str] = None
        self.filter_id: Optional[str] = None
        self.scope: str = "scene"
        self.children: List[QuantumNode] = []  # inline children (e.g., SceneTransitionNode)

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_event",
            "name": self.name,
            "handler": self.handler,
            "filter_tag": self.filter_tag,
            "filter_id": self.filter_id,
            "scope": self.scope,
            "children_count": len(self.children),
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Event name is required")
        if not self.handler and not self.children:
            errors.append("Event must have a handler or inline children")
        if self.scope not in ("scene", "sprite", "global"):
            errors.append(f"Invalid event scope: {self.scope}. Must be scene, sprite, or global")
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


# ============================================
# MULTI-SCENE NODES
# ============================================

class SceneTransitionNode(QuantumNode):
    """Represents <qg:transition> - Transition between game scenes.

    Used inside <qg:event>, <q:function>, or <qg:hud-behavior> to trigger
    a scene change with an optional visual effect.

    Attributes:
        to: Target scene name
        effect: Transition effect (fade, iris-out, iris-in, cut)
        duration: Effect duration in seconds
        data: Optional dictionary of data to pass to target scene
    """

    VALID_EFFECTS = ('fade', 'iris-out', 'iris-in', 'cut')

    def __init__(self, to: str):
        self.to = to
        self.effect: str = "fade"
        self.duration: float = 0.5
        self.data: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "type": "game_scene_transition",
            "to": self.to,
            "effect": self.effect,
            "duration": self.duration,
        }
        if self.data:
            result["data"] = self.data
        return result

    def validate(self) -> List[str]:
        errors = []
        if not self.to:
            errors.append("Scene transition target (to) is required")
        if self.effect not in self.VALID_EFFECTS:
            errors.append(f"Invalid transition effect: {self.effect}. Must be one of {', '.join(self.VALID_EFFECTS)}")
        if self.duration < 0:
            errors.append("Transition duration must be non-negative")
        return errors


class PersistentNode(QuantumNode):
    """Represents <qg:persistent> - State that survives scene changes.

    Wraps SetNode children that should persist across scene transitions.
    These become part of SceneManager's persistent_state dictionary.

    Example:
        <qg:persistent>
            <q:set name="lives" value="5" />
            <q:set name="score" value="0" />
        </qg:persistent>
    """

    def __init__(self):
        self.children: List[QuantumNode] = []

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_persistent",
            "children_count": len(self.children),
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.children:
            errors.append("Persistent block must contain at least one child")
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
        return errors


class MapNodeDef(QuantumNode):
    """Represents <qg:map-node> - A point on the world map.

    Used inside <qg:scene type="map"> to define navigable nodes
    that the player can move between (SMW-style world map).

    Attributes:
        id: Unique identifier for this map node
        x: X position on the map
        y: Y position on the map
        scene: Scene name to load when entering this node (None = decorative)
        locked: Whether this node starts locked
        icon: Optional sprite for the node marker
    """

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.x: float = 0
        self.y: float = 0
        self.scene: Optional[str] = None
        self.locked: bool = False
        self.icon: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "type": "game_map_node",
            "id": self.node_id,
            "x": self.x,
            "y": self.y,
        }
        if self.scene:
            result["scene"] = self.scene
        if self.locked:
            result["locked"] = True
        if self.icon:
            result["icon"] = self.icon
        return result

    def validate(self) -> List[str]:
        errors = []
        if not self.node_id:
            errors.append("Map node id is required")
        return errors


class MapPathNode(QuantumNode):
    """Represents <qg:map-path> - A path between two map nodes.

    Defines connectivity in the world map graph. Mario can only
    move between connected nodes via defined paths.

    Attributes:
        from_node: Source node ID
        to_node: Destination node ID
        unlock: Condition to unlock this path (e.g., "level-1-cleared")
        direction: Visual hint for path direction (right, up, etc.)
    """

    def __init__(self, from_node: str, to_node: str):
        self.from_node = from_node
        self.to_node = to_node
        self.unlock: Optional[str] = None
        self.direction: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "type": "game_map_path",
            "from": self.from_node,
            "to": self.to_node,
        }
        if self.unlock:
            result["unlock"] = self.unlock
        if self.direction:
            result["direction"] = self.direction
        return result

    def validate(self) -> List[str]:
        errors = []
        if not self.from_node:
            errors.append("Map path from_node is required")
        if not self.to_node:
            errors.append("Map path to_node is required")
        return errors


# ============================================
# EVENT ACTION NODES
# ============================================

class EventActionNode(QuantumNode):
    """Represents <qg:action> inside <qg:event> - Inline event action.

    Generates a single line of GDScript inside an event handler:
        type="score" amount="10"     -> score += 10
        type="destroy" target="{data.other}" -> data.other.queue_free()
        type="sound" target="sfx-coin"       -> QuantumBridge.play_sound("sfx-coin")
        type="camera-shake" value="3,0.15"   -> camera.shake(3.0, 0.15)
        type="set" target="coins" value="{coins+1}" -> coins += 1
        type="emit" value="coin-collected"   -> QuantumEventBus.emit_event("coin-collected", {})
        type="spawn" target="puff" value="x,y" -> spawn puff particle
    """

    VALID_ACTION_TYPES = ('score', 'destroy', 'sound', 'set', 'camera-shake', 'emit', 'spawn')

    def __init__(self):
        self.action_type: str = ""    # score, destroy, sound, set, camera-shake, emit, spawn
        self.target: Optional[str] = None
        self.value: Optional[str] = None
        self.amount: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "type": "event_action",
            "action_type": self.action_type,
        }
        if self.target is not None:
            result["target"] = self.target
        if self.value is not None:
            result["value"] = self.value
        if self.amount is not None:
            result["amount"] = self.amount
        return result

    def validate(self) -> List[str]:
        errors = []
        if not self.action_type:
            errors.append("Event action type is required")
        if self.action_type and self.action_type not in self.VALID_ACTION_TYPES:
            errors.append(f"Invalid event action type: {self.action_type}. Must be one of {', '.join(self.VALID_ACTION_TYPES)}")
        return errors


# ============================================
# COLLISION LAYER DEFINITIONS
# ============================================

class CollisionLayerDef(QuantumNode):
    """Represents <qg:collision-layer> inside <qg:physics> - Named collision layer.

    Maps a human-readable name to a Godot collision layer bitmask value.
    Example:
        <qg:collision-layer id="1" name="world" />
        <qg:collision-layer id="2" name="player" />
    """

    def __init__(self, layer_id: int, name: str):
        self.layer_id = layer_id
        self.name = name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "collision_layer_def",
            "layer_id": self.layer_id,
            "name": self.name,
        }

    def validate(self) -> List[str]:
        errors = []
        if self.layer_id < 1 or self.layer_id > 32:
            errors.append(f"Collision layer id must be between 1 and 32, got {self.layer_id}")
        if not self.name:
            errors.append("Collision layer name is required")
        return errors
