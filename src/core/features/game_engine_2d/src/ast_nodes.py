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
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.ast_nodes import QuantumNode


# ============================================
# CORE GAME NODES
# ============================================

class SceneNode(QuantumNode):
    """Represents <qg:scene> - A game scene with auto game loop."""

    def __init__(self, name: str):
        self.name = name
        self.width: int = 800
        self.height: int = 600
        self.background: str = "#000000"
        self.active: bool = True
        self.children: List[QuantumNode] = []

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_scene",
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "background": self.background,
            "active": self.active,
            "children_count": len(self.children),
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Scene name is required")
        if self.width <= 0:
            errors.append("Scene width must be positive")
        if self.height <= 0:
            errors.append("Scene height must be positive")
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
        self.tag: Optional[str] = None
        self.layer: int = 0

        # Spritesheet
        self.frame_width: Optional[int] = None
        self.frame_height: Optional[int] = None

        # Physics (Matter.js)
        self.body: Optional[str] = None  # static, dynamic, kinematic
        self.bounce: float = 0.1
        self.friction: float = 0.1
        self.mass: Optional[float] = None
        self.sensor: bool = False

        # Magic controls
        self.controls: Optional[str] = None  # wasd, arrows, custom
        self.speed: float = 5.0
        self.jump_force: float = 10.0

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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_physics",
            "gravity_x": self.gravity_x,
            "gravity_y": self.gravity_y,
            "bounds": self.bounds,
            "debug": self.debug,
        }

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
        self.input_type: str = "press"  # press, hold, release

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
    """Represents <qg:hud> - Fixed overlay on camera."""

    def __init__(self):
        self.position: str = "top-left"
        self.children: List[QuantumNode] = []

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_hud",
            "position": self.position,
            "children_count": len(self.children),
        }

    def validate(self) -> List[str]:
        errors = []
        valid = ('top-left', 'top-right', 'top-center',
                 'bottom-left', 'bottom-right', 'bottom-center', 'center')
        if self.position not in valid:
            errors.append(f"Invalid HUD position: {self.position}")
        for child in self.children:
            if hasattr(child, 'validate'):
                errors.extend(child.validate())
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


class TilemapNode(QuantumNode):
    """Represents <qg:tilemap> - Tile-based map."""

    def __init__(self, tilemap_id: str):
        self.tilemap_id = tilemap_id
        self.src: str = ""  # tileset image
        self.tile_width: int = 32
        self.tile_height: int = 32
        self.layers: List['TilemapLayerNode'] = []

    def add_layer(self, layer: 'TilemapLayerNode'):
        self.layers.append(layer)

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
        self.data: str = ""  # CSV tile data
        self.collision: bool = False

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
        if not self.data:
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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_use",
            "behavior": self.behavior,
            "overrides": self.overrides,
            "on_collision": self.on_collision,
            "collision_tag": self.collision_tag,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.behavior:
            errors.append("Use behavior name is required")
        return errors


class PrefabNode(QuantumNode):
    """Represents <qg:prefab> - Reusable game object template."""

    def __init__(self, name: str):
        self.name = name
        self.children: List[QuantumNode] = []  # Typically one sprite with children

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "game_prefab",
            "name": self.name,
            "children_count": len(self.children),
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Prefab name is required")
        if not self.children:
            errors.append("Prefab must contain at least one child")
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
