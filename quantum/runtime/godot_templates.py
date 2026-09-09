"""
Godot 4 - GDScript/TSCN Templates and Builders

Provides:
  - GdScriptBuilder: Structured GDScript code emitter with proper indentation
  - TscnBuilder: Godot .tscn scene file builder (text-based format)
  - GDScript templates for runtime scripts (bridge, event bus, player controller, etc.)
  - Scale constants for Quantum → Godot unit conversion
"""

import json
import re
from typing import List, Dict, Any, Optional, Tuple


# ==========================================================================
# SNES Hardware Constants (Super Nintendo Entertainment System)
# ==========================================================================
# Source: SNES dev wiki, SMW disassembly, TASVideos
#   Resolution: 256×224 (Mode 1, NTSC)
#   Tile size: 16×16 px (BG), sprites 8/16/32/64
#   Framerate: 60 fps (NTSC)
#   Subpixel resolution: 1/16 pixel (4-bit fractional)

SNES_WIDTH = 256
SNES_HEIGHT = 224
SNES_TILE = 16
SNES_FPS = 60
SNES_WINDOW_SCALE = 3  # 3x upscale → 768×672 window

# ==========================================================================
# SMW Physics Constants (for Godot: px/s and px/s² at 60fps)
# ==========================================================================
# Derived from SMW disassembly + frame analysis:
#   Walk max: ~21 subpx/frame = 1.3 px/frame → 78.75 px/s
#   Run max:  ~37 subpx/frame = 2.3 px/frame → 138.75 px/s
#   Sprint:   ~49 subpx/frame = 3.1 px/frame → 183.75 px/s
#   Max fall: ~64 subpx/frame = 4.0 px/frame → 240 px/s
#   Jump initial: ~-5 px/frame → -300 px/s
#   Gravity rise (A held): ~0.19 px/frame² → 675 px/s²
#   Gravity fall: ~0.44 px/frame² → 1575 px/s²
#
# Tuned values (balanced for playability in Godot):

SMW_WALK_SPEED = 90.0       # px/s (1.5 px/frame)
SMW_JUMP_VELOCITY = -280.0  # px/s (initial upward, negative = up)
SMW_GRAVITY = 750.0         # px/s² (project default)
SMW_GRAVITY_RISING = 600.0  # px/s² (holding jump, lighter feel)
SMW_GRAVITY_FALLING = 1050.0  # px/s² (falling, snappy)
SMW_MAX_FALL = 240.0        # px/s (4 px/frame terminal velocity)
SMW_JUMP_HOLD_BOOST = 50.0  # px/s² (extra lift while holding jump)
SMW_COYOTE_FRAMES = 6       # frames of grace after leaving edge

# Validation: jump height = v² / (2 * g_rise) = 280² / (2*600) = 65px ≈ 4 tiles ✓
# With hold boost over 0.4s rise: ~80px ≈ 5 tiles ✓ (SMW standard)

# ==========================================================================
# Legacy scale helpers (kept for backward compat with tests)
# ==========================================================================

QUANTUM_SCALE = 100  # Legacy — NOT used for positions or SNES physics


def q2g(value: float) -> float:
    """Convert Quantum abstract unit to Godot value (legacy)."""
    return value * QUANTUM_SCALE


def q2g_int(value: float) -> int:
    """Convert Quantum abstract unit to integer (legacy)."""
    return int(value * QUANTUM_SCALE)


def q2g_gravity(value: float) -> float:
    """Convert Quantum gravity to Godot gravity (legacy)."""
    return value * QUANTUM_SCALE


def q2g_speed(value: float) -> float:
    """Convert Quantum speed to Godot speed (legacy)."""
    return value * QUANTUM_SCALE


def q2g_jump(value: float) -> float:
    """Convert Quantum jump force to Godot velocity (legacy)."""
    return -(value * QUANTUM_SCALE * 0.6)


# ==========================================================================
# GdScriptBuilder - Structured GDScript code emitter
# ==========================================================================

class GdScriptBuilder:
    """Builds syntactically valid GDScript code with proper indentation.

    Every append method returns self for chaining.
    """

    def __init__(self, indent_char: str = '\t'):
        self._lines: list[str] = []
        self._indent: int = 0
        self._indent_char: str = indent_char

    # -- core --

    @property
    def _pad(self) -> str:
        return self._indent_char * self._indent

    def line(self, code: str = '') -> 'GdScriptBuilder':
        """Emit a single line at current indent."""
        self._lines.append(f"{self._pad}{code}" if code else '')
        return self

    def raw(self, code: str) -> 'GdScriptBuilder':
        """Emit raw code preserving its own indentation at current base indent."""
        for ln in code.split('\n'):
            self._lines.append(f"{self._pad}{ln}")
        return self

    def raw_unindented(self, code: str) -> 'GdScriptBuilder':
        """Emit raw code without adding base indentation."""
        for ln in code.split('\n'):
            self._lines.append(ln)
        return self

    def blank(self) -> 'GdScriptBuilder':
        self._lines.append('')
        return self

    def comment(self, text: str) -> 'GdScriptBuilder':
        return self.line(f"# {text}")

    def section(self, title: str) -> 'GdScriptBuilder':
        return self.blank().line(f"# === {title} ===")

    def indent(self) -> 'GdScriptBuilder':
        self._indent += 1
        return self

    def dedent(self) -> 'GdScriptBuilder':
        self._indent = max(0, self._indent - 1)
        return self

    # -- GDScript specific --

    def extends(self, base_class: str) -> 'GdScriptBuilder':
        return self.line(f"extends {base_class}")

    def class_name(self, name: str) -> 'GdScriptBuilder':
        return self.line(f"class_name {name}")

    def var(self, name: str, value: str = '', type_hint: str = '') -> 'GdScriptBuilder':
        if type_hint and value:
            return self.line(f"var {name}: {type_hint} = {value}")
        elif type_hint:
            return self.line(f"var {name}: {type_hint}")
        elif value:
            return self.line(f"var {name} = {value}")
        else:
            return self.line(f"var {name}")

    def const(self, name: str, value: str) -> 'GdScriptBuilder':
        return self.line(f"const {name} = {value}")

    def assign(self, target: str, value: str) -> 'GdScriptBuilder':
        return self.line(f"{target} = {value}")

    def export_var(self, name: str, type_hint: str, value: str = '') -> 'GdScriptBuilder':
        if value:
            return self.line(f"@export var {name}: {type_hint} = {value}")
        return self.line(f"@export var {name}: {type_hint}")

    def onready_var(self, name: str, path: str) -> 'GdScriptBuilder':
        return self.line(f'@onready var {name} = ${path}')

    def signal_decl(self, name: str, params: str = '') -> 'GdScriptBuilder':
        if params:
            return self.line(f"signal {name}({params})")
        return self.line(f"signal {name}")

    def preload(self, name: str, path: str) -> 'GdScriptBuilder':
        return self.line(f'var {name} = preload("{path}")')

    # -- blocks --

    def func(self, name: str, params: str = '', return_type: str = '') -> 'GdScriptBuilder':
        """Open a function block."""
        sig = f"func {name}({params})"
        if return_type:
            sig += f" -> {return_type}"
        sig += ":"
        self.line(sig)
        self._indent += 1
        return self

    def func_close(self) -> 'GdScriptBuilder':
        """Close a function block (just dedent in GDScript)."""
        self._indent = max(0, self._indent - 1)
        return self

    def if_block(self, condition: str) -> 'GdScriptBuilder':
        self.line(f"if {condition}:")
        self._indent += 1
        return self

    def elif_block(self, condition: str) -> 'GdScriptBuilder':
        self._indent = max(0, self._indent - 1)
        self.line(f"elif {condition}:")
        self._indent += 1
        return self

    def else_block(self) -> 'GdScriptBuilder':
        self._indent = max(0, self._indent - 1)
        self.line("else:")
        self._indent += 1
        return self

    def for_block(self, var: str, iterable: str) -> 'GdScriptBuilder':
        self.line(f"for {var} in {iterable}:")
        self._indent += 1
        return self

    def while_block(self, condition: str) -> 'GdScriptBuilder':
        self.line(f"while {condition}:")
        self._indent += 1
        return self

    def match_block(self, value: str) -> 'GdScriptBuilder':
        self.line(f"match {value}:")
        self._indent += 1
        return self

    def match_case(self, pattern: str) -> 'GdScriptBuilder':
        self.line(f"{pattern}:")
        self._indent += 1
        return self

    def block_close(self) -> 'GdScriptBuilder':
        """Generic block close (dedent)."""
        self._indent = max(0, self._indent - 1)
        return self

    def pass_stmt(self) -> 'GdScriptBuilder':
        return self.line("pass")

    def return_stmt(self, value: str = '') -> 'GdScriptBuilder':
        if value:
            return self.line(f"return {value}")
        return self.line("return")

    def build(self) -> str:
        """Return the complete GDScript source."""
        return '\n'.join(self._lines) + '\n'


# ==========================================================================
# TscnBuilder - Godot .tscn scene file builder
# ==========================================================================

class TscnBuilder:
    """Builds Godot .tscn (text scene) files programmatically.

    TSCN format:
      [gd_scene load_steps=N format=3 uid="uid://..."]
      [ext_resource type="..." path="..." id="1"]
      [sub_resource type="..." id="sub_1"]
      [node name="Root" type="Node2D"]
      [node name="Child" type="Sprite2D" parent="."]
    """

    def __init__(self):
        self._ext_resources: List[Dict[str, str]] = []
        self._sub_resources: List[Dict[str, Any]] = []
        self._nodes: List[Dict[str, Any]] = []
        self._ext_id_counter: int = 0
        self._sub_id_counter: int = 0
        self._ext_resource_cache: Dict[str, str] = {}  # path → id

    def add_ext_resource(self, res_type: str, path: str) -> str:
        """Add an external resource. Returns the resource ID string."""
        if path in self._ext_resource_cache:
            return self._ext_resource_cache[path]
        self._ext_id_counter += 1
        rid = str(self._ext_id_counter)
        self._ext_resources.append({
            'type': res_type,
            'path': path,
            'id': rid,
        })
        self._ext_resource_cache[path] = rid
        return rid

    def add_sub_resource(self, res_type: str, properties: Dict[str, Any] = None) -> str:
        """Add a sub-resource. Returns the sub-resource ID string."""
        self._sub_id_counter += 1
        sid = f"SubResource(\"{self._sub_id_counter}\")"
        self._sub_resources.append({
            'type': res_type,
            'id': str(self._sub_id_counter),
            'properties': properties or {},
        })
        return sid

    def add_node(self, name: str, node_type: str, parent: Optional[str] = None,
                 properties: Dict[str, Any] = None, groups: List[str] = None,
                 instance: Optional[str] = None) -> 'TscnBuilder':
        """Add a scene node."""
        self._nodes.append({
            'name': name,
            'type': node_type,
            'parent': parent,
            'properties': properties or {},
            'groups': groups or [],
            'instance': instance,
        })
        return self

    def add_node_with_script(self, name: str, node_type: str, script_path: str,
                             parent: Optional[str] = None,
                             properties: Dict[str, Any] = None,
                             groups: List[str] = None) -> 'TscnBuilder':
        """Add a scene node with an attached script."""
        script_id = self.add_ext_resource('Script', script_path)
        props = properties or {}
        props['script'] = f'ExtResource("{script_id}")'
        return self.add_node(name, node_type, parent, props, groups)

    def build(self) -> str:
        """Return the complete .tscn file content."""
        lines = []
        load_steps = 1 + len(self._ext_resources) + len(self._sub_resources)

        # Header
        lines.append(f'[gd_scene load_steps={load_steps} format=3]')
        lines.append('')

        # External resources
        for res in self._ext_resources:
            lines.append(
                f'[ext_resource type="{res["type"]}" path="res://{res["path"]}" id="{res["id"]}"]'
            )
        if self._ext_resources:
            lines.append('')

        # Sub-resources
        for sub in self._sub_resources:
            props_str = self._format_sub_resource_props(sub['properties'])
            lines.append(f'[sub_resource type="{sub["type"]}" id="{sub["id"]}"]')
            if props_str:
                lines.append(props_str)
            lines.append('')

        # Nodes
        for node in self._nodes:
            lines.append(self._format_node(node))
            props_lines = self._format_node_props(node['properties'])
            if props_lines:
                lines.append(props_lines)
            lines.append('')

        return '\n'.join(lines)

    def _format_node(self, node: Dict[str, Any]) -> str:
        """Format a [node ...] header line."""
        parts = [f'name="{node["name"]}"']

        if node.get('instance'):
            parts.append(f'instance={node["instance"]}')
        elif node['type']:
            parts.append(f'type="{node["type"]}"')

        if node['parent'] is not None:
            parts.append(f'parent="{node["parent"]}"')

        if node.get('groups'):
            groups_str = ', '.join(f'"{g}"' for g in node['groups'])
            parts.append(f'groups=[{groups_str}]')

        return '[node ' + ' '.join(parts) + ']'

    def _format_node_props(self, props: Dict[str, Any]) -> str:
        """Format node properties as key = value lines."""
        lines = []
        for key, value in props.items():
            lines.append(f'{key} = {self._format_value(value)}')
        return '\n'.join(lines)

    def _format_sub_resource_props(self, props: Dict[str, Any]) -> str:
        """Format sub-resource properties."""
        lines = []
        for key, value in props.items():
            lines.append(f'{key} = {self._format_value(value)}')
        return '\n'.join(lines)

    def _format_value(self, value: Any) -> str:
        """Format a value for .tscn file."""
        if isinstance(value, bool):
            return 'true' if value else 'false'
        elif isinstance(value, int):
            return str(value)
        elif isinstance(value, float):
            return f'{value:.6g}'
        elif isinstance(value, str):
            # Check for special Godot references
            if value.startswith('ExtResource(') or value.startswith('SubResource('):
                return value
            if value.startswith('Vector2(') or value.startswith('Vector2i('):
                return value
            if value.startswith('Rect2(') or value.startswith('Color('):
                return value
            if value.startswith('PackedScene('):
                return value
            return f'"{value}"'
        elif isinstance(value, list):
            items = ', '.join(self._format_value(v) for v in value)
            return f'[{items}]'
        elif isinstance(value, dict):
            items = ', '.join(
                f'{self._format_value(k)}: {self._format_value(v)}'
                for k, v in value.items()
            )
            return f'{{{items}}}'
        else:
            return str(value)


# ==========================================================================
# GDScript helper functions
# ==========================================================================

def gd_string(s: str) -> str:
    """Escape a string for GDScript."""
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n') + '"'


def gd_bool(b: bool) -> str:
    """Convert Python bool to GDScript bool literal."""
    return 'true' if b else 'false'


def gd_vector2(x: float, y: float) -> str:
    """Format a Vector2."""
    return f'Vector2({x:.6g}, {y:.6g})'


def gd_vector2i(x: int, y: int) -> str:
    """Format a Vector2i."""
    return f'Vector2i({x}, {y})'


def gd_color(hex_color: str) -> str:
    """Convert hex color to Godot Color."""
    c = hex_color.lstrip('#')
    if len(c) == 3:
        c = ''.join(ch * 2 for ch in c)
    if len(c) == 6:
        r = int(c[0:2], 16) / 255.0
        g = int(c[2:4], 16) / 255.0
        b = int(c[4:6], 16) / 255.0
        return f'Color({r:.3f}, {g:.3f}, {b:.3f}, 1.0)'
    return f'Color("{hex_color}")'


# ==========================================================================
# Easing name mapping: Quantum → Godot
# ==========================================================================

EASING_MAP = {
    'linear': 'Tween.EASE_IN',  # Godot TRANS_LINEAR
    'ease-in': 'Tween.EASE_IN',
    'ease-out': 'Tween.EASE_OUT',
    'ease-in-out': 'Tween.EASE_IN_OUT',
    'bounce': 'Tween.EASE_OUT',  # with TRANS_BOUNCE
}

TRANS_MAP = {
    'linear': 'Tween.TRANS_LINEAR',
    'ease-in': 'Tween.TRANS_QUAD',
    'ease-out': 'Tween.TRANS_QUAD',
    'ease-in-out': 'Tween.TRANS_QUAD',
    'bounce': 'Tween.TRANS_BOUNCE',
}


# ==========================================================================
# project.godot template
# ==========================================================================

def build_project_godot(config: Dict[str, Any]) -> str:
    """Generate project.godot file content."""
    lines = []
    lines.append('; Engine configuration file.')
    lines.append('; Generated by Quantum Framework - Godot Backend')
    lines.append('')
    lines.append('config_version=5')
    lines.append('')

    # [application]
    lines.append('[application]')
    lines.append('')
    lines.append(f'config/name="{config.get("name", "Quantum Game")}"')
    lines.append(f'run/main_scene="res://{config.get("main_scene", "main.tscn")}"')
    lines.append('config/features=PackedStringArray("4.4")')
    lines.append('')

    # [autoload]
    autoloads = config.get('autoloads', {})
    if autoloads:
        lines.append('[autoload]')
        lines.append('')
        for name, path in autoloads.items():
            lines.append(f'{name}="*res://{path}"')
        lines.append('')

    # [display]
    lines.append('[display]')
    lines.append('')
    vp_width = config.get('viewport_width', SNES_WIDTH)
    vp_height = config.get('viewport_height', SNES_HEIGHT)
    lines.append(f'window/size/viewport_width={vp_width}')
    lines.append(f'window/size/viewport_height={vp_height}')

    # Window override: scale up for modern monitors
    scale = config.get('window_scale', SNES_WINDOW_SCALE)
    win_width = vp_width * scale
    win_height = vp_height * scale
    lines.append(f'window/size/window_width_override={win_width}')
    lines.append(f'window/size/window_height_override={win_height}')

    # Stretch: "viewport" = pixel-perfect upscale (no subpixel blending)
    stretch_mode = config.get('stretch_mode', 'viewport')
    lines.append(f'window/stretch/mode="{stretch_mode}"')
    stretch_aspect = config.get('stretch_aspect', 'keep')
    lines.append(f'window/stretch/aspect="{stretch_aspect}"')
    lines.append('')

    # [physics]
    lines.append('[physics]')
    lines.append('')
    gravity = config.get('gravity', 980.0)
    lines.append(f'2d/default_gravity={gravity:.1f}')
    lines.append('')

    # [input] - input map
    input_map = config.get('input_map', {})
    if input_map:
        lines.append('[input]')
        lines.append('')
        for action_name, keys in input_map.items():
            events = []
            for key in keys:
                events.append(_input_event_for_key(key))
            events_str = ', '.join(events)
            lines.append(f'{action_name}={{"deadzone": 0.5, "events": [{events_str}]}}')
        lines.append('')

    # [layer_names]
    collision_layer_names = config.get('collision_layer_names', {})
    if collision_layer_names:
        lines.append('[layer_names]')
        lines.append('')
        # Sort by layer id value, map name->id to id->name
        id_to_name = {}
        for name, layer_id in collision_layer_names.items():
            # Convert bitmask to layer number (1-based)
            bit = 1
            while (1 << (bit - 1)) < layer_id:
                bit += 1
            if (1 << (bit - 1)) == layer_id:
                id_to_name[bit] = name
            else:
                # Not a power of 2, use as direct layer number
                id_to_name[layer_id] = name
        for layer_num in sorted(id_to_name.keys()):
            lines.append(f'2d_physics/layer_{layer_num}="{id_to_name[layer_num]}"')
        lines.append('')
    else:
        # Default SMW layer names
        lines.append('[layer_names]')
        lines.append('')
        lines.append('2d_physics/layer_1="world"')
        lines.append('2d_physics/layer_2="player"')
        lines.append('2d_physics/layer_3="enemies"')
        lines.append('2d_physics/layer_4="collectibles"')
        lines.append('2d_physics/layer_5="sensors"')
        lines.append('')

    # [rendering]
    lines.append('[rendering]')
    lines.append('')
    lines.append('textures/canvas_textures/default_texture_filter=0')
    lines.append('')

    return '\n'.join(lines)


def _input_event_for_key(key: str) -> str:
    """Convert a key name to a Godot InputEvent resource string.

    Godot 4 project.godot uses integer physical keycodes, not symbolic names.
    """
    # Godot 4 physical keycode integer values
    key_map = {
        'ArrowLeft': 4194319, 'ArrowRight': 4194321,
        'ArrowUp': 4194320, 'ArrowDown': 4194322,
        'a': 65, 'd': 68, 'w': 87, 's': 83,
        'Space': 32, ' ': 32,
        'Enter': 4194309, 'Escape': 4194305,
        'Shift': 4194325, 'Control': 4194326,
        'z': 90, 'x': 88, 'c': 67,
    }
    godot_key = key_map.get(key, ord(key.upper()) if len(key) == 1 else 0)
    return f'Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":0,"physical_keycode":{godot_key},"key_label":0,"unicode":0,"location":0,"echo":false,"script":null)'


# ==========================================================================
# export_presets.cfg template
# ==========================================================================

def build_export_presets() -> str:
    """Generate export_presets.cfg for HTML5 web export."""
    return """[preset.0]

name="Web"
platform="Web"
runnable=true
dedicated_server=false
custom_features=""
export_filter="all_resources"
include_filter=""
exclude_filter=""
export_path="dist/index.html"
encryption_include_filters=""
encryption_exclude_filters=""
encrypt_pck=false
encrypt_directory=false

[preset.0.options]

custom_template/debug=""
custom_template/release=""
variant/extensions_support=false
vram_texture_compression/for_desktop=true
vram_texture_compression/for_mobile=false
html/export_icon=true
html/custom_html_shell=""
html/head_include=""
html/canvas_resize_policy=2
html/focus_canvas_on_start=true
html/experimental_virtual_keyboard=false
progressive_web_app/enabled=false
"""


# ==========================================================================
# GDScript templates for runtime scripts
# ==========================================================================

QUANTUM_BRIDGE_GD = '''\
extends Node
## Quantum Bridge - Game API autoload
## Provides centralized game object management and utility functions.

var sprites: Dictionary = {}
var event_bus: Node
var game_state: Dictionary = {}

func save_game_state(data: Dictionary):
\tgame_state = data.duplicate()

func get_game_state() -> Dictionary:
\treturn game_state

func clear_game_state():
\tgame_state = {}

func _ready():
\tevent_bus = get_node("/root/QuantumEventBus")

func register_sprite(id: String, node: Node):
\tsprites[id] = node

func destroy_sprite(id: String):
\tif id in sprites:
\t\tsprites[id].queue_free()
\t\tsprites.erase(id)

func respawn(id: String, x: float, y: float):
\tif id in sprites:
\t\tsprites[id].position = Vector2(x, y)
\t\tif sprites[id] is CharacterBody2D:
\t\t\tsprites[id].velocity = Vector2.ZERO

func get_sprite(id: String) -> Node:
\tif id in sprites:
\t\treturn sprites[id]
\treturn null

func emit_event(event_name: String, data: Dictionary = {}):
\tif event_bus:
\t\tevent_bus.emit_event(event_name, data)

func camera_shake(intensity: float = 5.0, duration: float = 0.3):
\tvar cam = get_viewport().get_camera_2d()
\tif cam and cam.has_method("shake"):
\t\tcam.shake(intensity, duration)

func set_patrol_ai(id: String, speed: float):
\tif id in sprites and sprites[id].has_method("set_patrol"):
\t\tsprites[id].set_patrol(speed)

func kill_player(id: String):
\tif id in sprites and sprites[id].has_method("die"):
\t\tsprites[id].die()

func play_sound(id: String, opts: Dictionary = {}):
\tvar player = get_node_or_null("/root/Main/Sounds/" + id)
\tif player and player is AudioStreamPlayer:
\t\tif opts.has("volume"):
\t\t\tplayer.volume_db = linear_to_db(opts["volume"])
\t\tplayer.play()

func pause():
\tget_tree().paused = true

func resume():
\tget_tree().paused = false

func load_scene(scene_name: String):
\tvar path = "res://scenes/" + scene_name + ".tscn"
\tget_tree().change_scene_to_file(path)

func iris_in(duration: float = 0.5):
\temit_event("iris_in", {"duration": duration})

func iris_out(duration: float = 0.5):
\temit_event("iris_out", {"duration": duration})

func save_state(key: String, value) -> void:
\tvar save_data: Dictionary = {}
\tvar path = "user://quantum_save.json"
\tif FileAccess.file_exists(path):
\t\tvar f = FileAccess.open(path, FileAccess.READ)
\t\tsave_data = JSON.parse_string(f.get_as_text()) if f else {}
\t\tif f: f.close()
\tif save_data == null:
\t\tsave_data = {}
\tsave_data[key] = value
\tvar f = FileAccess.open(path, FileAccess.WRITE)
\tif f:
\t\tf.store_string(JSON.stringify(save_data))
\t\tf.close()

func load_state(key: String, default_value = null):
\tvar path = "user://quantum_save.json"
\tif not FileAccess.file_exists(path):
\t\treturn default_value
\tvar f = FileAccess.open(path, FileAccess.READ)
\tif not f:
\t\treturn default_value
\tvar data = JSON.parse_string(f.get_as_text())
\tf.close()
\tif data is Dictionary and data.has(key):
\t\treturn data[key]
\treturn default_value
'''


QUANTUM_EVENT_BUS_GD = '''\
extends Node
## Quantum Event Bus - Global event system autoload
## Allows decoupled communication between game objects.

var _listeners: Dictionary = {}

func emit_event(event_name: String, data: Dictionary = {}):
\tif event_name in _listeners:
\t\tfor callback in _listeners[event_name]:
\t\t\tif callback.is_valid():
\t\t\t\tcallback.call(data)

func listen(event_name: String, callback: Callable):
\tif event_name not in _listeners:
\t\t_listeners[event_name] = []
\t_listeners[event_name].append(callback)

func remove_listener(event_name: String, callback: Callable):
\tif event_name in _listeners:
\t\t_listeners[event_name].erase(callback)

func clear(event_name: String = ""):
\tif event_name:
\t\t_listeners.erase(event_name)
\telse:
\t\t_listeners.clear()
'''


PLAYER_CONTROLLER_GD = '''\
extends CharacterBody2D
## Player Controller - SMW-style platformer physics
## Generated by Quantum Framework

@export var move_speed: float = {speed}
@export var jump_velocity: float = {jump_velocity}
@export var gravity_up: float = {gravity_up}
@export var gravity_down: float = {gravity_down}
@export var jump_hold_boost: float = {jump_hold_boost}
@export var coyote_frames: int = {coyote_frames}
@export var max_fall_speed: float = {max_fall_speed}

var _coyote_counter: int = 0
var _jump_held: bool = false
var _facing_right: bool = true
var _stomp_bouncing: bool = false

# Death state
var is_dead: bool = false
var _death_texture: Texture2D = null
var _normal_texture: Texture2D = null

# Animation
var _anim_timer: float = 0.0
var _walk_frames: Array = {walk_frames}
var _walk_frame_idx: int = 0
var _walk_speed: float = {walk_anim_speed}
var _idle_frame: int = {idle_frame}
var _jump_frame: int = {jump_frame}

func _ready():
\tcollision_layer = {collision_layer}
\tcollision_mask = {collision_mask}
\tfloor_max_angle = deg_to_rad({floor_max_angle})
\tfloor_snap_length = 4.0
\tfloor_block_on_wall = true
\tmax_slides = 6

func _physics_process(delta: float):
\t# Death: only apply gravity and slide
\tif is_dead:
\t\tvelocity.y += gravity_down * delta
\t\tmove_and_slide()
\t\treturn

\t# Enemy hit cooldown
\tif _enemy_hit_cooldown > 0:
\t\t_enemy_hit_cooldown -= delta

\t# Gravity
\tif not is_on_floor():
\t\tvar grav = gravity_down if velocity.y > 0 else gravity_up
\t\tvelocity.y += grav * delta
\t\tvelocity.y = min(velocity.y, max_fall_speed)
\t\t_coyote_counter -= 1
\telse:
\t\tif _stomp_bouncing:
\t\t\t_stomp_bouncing = false
\t\telse:
\t\t\tvelocity.y = 0
\t\t\t_coyote_counter = coyote_frames

\t# Jump
\tif Input.is_action_just_pressed("jump") and _coyote_counter > 0:
\t\tvelocity.y = jump_velocity
\t\t_jump_held = true
\t\t_coyote_counter = 0
\t\tprint("[JUMP] vel_y=", velocity.y, " pos_y=", global_position.y)

\t# Variable jump height
\tif Input.is_action_just_released("jump") and velocity.y < 0:
\t\tvelocity.y *= 0.5
\t\t_jump_held = false

\t# Jump hold boost
\tif _jump_held and Input.is_action_pressed("jump") and velocity.y < 0:
\t\tvelocity.y -= jump_hold_boost * delta

\t# Horizontal movement
\tvar direction = Input.get_axis("move_left", "move_right")
\tif direction:
\t\tvelocity.x = direction * move_speed
\t\t_facing_right = direction > 0
\telse:
\t\tvelocity.x = move_toward(velocity.x, 0, move_speed * 0.2)

\tmove_and_slide()
\t_check_enemy_collisions()
\t_update_animation(delta)

var _enemy_hit_cooldown: float = 0.0

func _check_enemy_collisions():
\tif _enemy_hit_cooldown > 0:
\t\treturn
\tfor i in range(get_slide_collision_count()):
\t\tvar col = get_slide_collision(i)
\t\tvar collider = col.get_collider()
\t\tif not collider or not collider.has_meta("tag"):
\t\t\tcontinue
\t\tvar tag = collider.get_meta("tag")
\t\tvar normal = col.get_normal()
\t\tif tag == "enemy":
\t\t\t_enemy_hit_cooldown = 0.3
\t\t\tQuantumEventBus.emit_event("enemy-collision", {{
\t\t\t\t"other": collider,
\t\t\t\t"normal_y": normal.y
\t\t\t}})
\t\t\tbreak
\t\telif tag == "qblock" and normal.y > 0.5:
\t\t\tif collider.has_method("hit"):
\t\t\t\tcollider.hit()
\t\t\tQuantumEventBus.emit_event("qblock-hit", {{
\t\t\t\t"other": collider,
\t\t\t\t"normal_y": normal.y
\t\t\t}})
\t\telif tag == "rotating_block" and normal.y > 0.5:
\t\t\tif collider.has_method("hit"):
\t\t\t\tcollider.hit()
\t\t\tQuantumEventBus.emit_event("rotating-block-hit", {{
\t\t\t\t"other": collider,
\t\t\t\t"normal_y": normal.y
\t\t\t}})

func die():
\tif is_dead:
\t\treturn
\tis_dead = true
\tprocess_mode = Node.PROCESS_MODE_ALWAYS
\tvar sprite = get_node_or_null("Sprite2D")
\tif sprite and _death_texture:
\t\t_normal_texture = sprite.texture
\t\tsprite.texture = _death_texture
\t\tsprite.hframes = 1
\t\tsprite.vframes = 1
\t\tsprite.frame = 0
\t\tsprite.flip_h = false
\tvelocity = Vector2(0, -200)
\tset_deferred("collision_layer", 0)
\tset_deferred("collision_mask", 0)

func set_death_texture(tex: Texture2D):
\t_death_texture = tex

func stomp_bounce(vel: float):
\tprint("[STOMP_BOUNCE] before_vel_y=", velocity.y, " bounce_vel=", vel, " pos_y=", global_position.y)
\tvelocity.y = vel
\t_jump_held = false
\t_coyote_counter = 0
\t_stomp_bouncing = true

func _update_animation(delta: float):
\tvar sprite = get_node_or_null("Sprite2D")
\tif not sprite:
\t\treturn

\t# Flip sprite based on facing direction
\t# SMW spritesheets face LEFT by default, flip when facing right
\tsprite.flip_h = _facing_right

\t# Frame selection
\tif not is_on_floor():
\t\t# Airborne: jump frame
\t\tsprite.frame = _jump_frame
\t\t_anim_timer = 0.0
\t\t_walk_frame_idx = 0
\telif abs(velocity.x) > 5:
\t\t# Walking: cycle through walk frames
\t\t_anim_timer += delta
\t\tif _anim_timer >= _walk_speed:
\t\t\t_anim_timer = 0.0
\t\t\t_walk_frame_idx = (_walk_frame_idx + 1) % _walk_frames.size()
\t\tsprite.frame = _walk_frames[_walk_frame_idx]
\telse:
\t\t# Idle
\t\tsprite.frame = _idle_frame
\t\t_anim_timer = 0.0
\t\t_walk_frame_idx = 0
'''


# Spin jump section — appended to player controller when spin_jump=true
SPIN_JUMP_SECTION = '''

# --- Spin Jump (SMW-style) ---
var _is_spin_jumping: bool = false
var _spin_jump_velocity_mult: float = 0.85

func _unhandled_input(event):
\tif event.is_action_pressed("spin_jump") and is_on_floor() and not is_dead:
\t\tvelocity.y = jump_velocity * _spin_jump_velocity_mult
\t\t_is_spin_jumping = true
\t\t_jump_held = true
\t\t_coyote_counter = 0
\t\tQuantumBridge.play_sound("sfx-spin")

func _check_spin_landing():
\tif _is_spin_jumping and is_on_floor():
\t\t_is_spin_jumping = false
\t\tvar sprite = get_node_or_null("Sprite2D")
\t\tif sprite:
\t\t\tsprite.rotation = 0.0

func _spin_visual(delta: float):
\tif _is_spin_jumping:
\t\tvar sprite = get_node_or_null("Sprite2D")
\t\tif sprite:
\t\t\tsprite.rotation += delta * 20.0
'''


CAMERA_FOLLOW_GD = '''\
extends Camera2D
## Camera Follow - Smooth follow with bounds
## Generated by Quantum Framework

@export var follow_target: NodePath
@export var smoothing_speed: float = {lerp_speed}
@export var use_bounds: bool = {use_bounds}
@export var bound_left: float = 0.0
@export var bound_top: float = 0.0
@export var bound_right: float = {bound_right}
@export var bound_bottom: float = {bound_bottom}

var _shake_intensity: float = 0.0
var _shake_timer: float = 0.0
var _base_offset: Vector2

func _ready():
\t_base_offset = offset
\tposition_smoothing_enabled = true
\tposition_smoothing_speed = smoothing_speed

\tif use_bounds:
\t\tlimit_left = int(bound_left)
\t\tlimit_top = int(bound_top)
\t\tlimit_right = int(bound_right)
\t\tlimit_bottom = int(bound_bottom)

func _process(delta: float):
\tif _shake_timer > 0:
\t\t_shake_timer -= delta
\t\toffset = _base_offset + Vector2(
\t\t\trandf_range(-_shake_intensity, _shake_intensity),
\t\t\trandf_range(-_shake_intensity, _shake_intensity)
\t\t)
\telse:
\t\toffset = _base_offset

func shake(intensity: float = 5.0, duration: float = 0.3):
\t_shake_intensity = intensity
\t_shake_timer = duration
'''


PATROL_AI_GD = '''\
extends CharacterBody2D
## Patrol AI - Simple back-and-forth movement
## Generated by Quantum Framework

@export var patrol_speed: float = {speed}
@export var turn_on_edge: bool = {turn_on_edge}
@export var gravity: float = {gravity}

var _direction: float = {initial_direction}

func _physics_process(delta: float):
\tif not is_on_floor():
\t\tvelocity.y += gravity * delta
\telse:
\t\tvelocity.y = 0

\tvelocity.x = _direction * patrol_speed

\tif is_on_wall():
\t\t_direction *= -1

\tif turn_on_edge and is_on_floor():
\t\tvar ray_pos = Vector2(_direction * 16, 2)
\t\tvar space = get_world_2d().direct_space_state
\t\tvar query = PhysicsRayQueryParameters2D.create(
\t\t\tglobal_position + ray_pos,
\t\t\tglobal_position + ray_pos + Vector2(0, 32)
\t\t)
\t\tvar result = space.intersect_ray(query)
\t\tif not result:
\t\t\t_direction *= -1

\tmove_and_slide()

func set_patrol(speed: float):
\tpatrol_speed = speed

func die():
\tqueue_free()
'''


HUD_MANAGER_GD = '''\
extends CanvasLayer
## HUD Manager - UI overlay
## Generated by Quantum Framework

{label_vars}

func _ready():
{label_ready}

func update_label(label_name: String, value):
\tvar label = get_node_or_null(label_name)
\tif label and label is Label:
\t\tlabel.text = str(value)
'''


SPRITE_ANIMATOR_GD = '''\
extends {base_class}
## Sprite Animator - Auto-cycling sprite frames
## Generated by Quantum Framework

var _anim_timer: float = 0.0
var _anim_frames: Array = {frames}
var _anim_idx: int = 0
var _anim_speed: float = {speed}
var _sprite: Sprite2D

func _ready():
\t_sprite = find_child("Sprite2D", true, false)

func _process(delta: float):
\tif not _sprite or _anim_frames.size() <= 1:
\t\treturn
\t_anim_timer += delta
\tif _anim_timer >= _anim_speed:
\t\t_anim_timer = 0.0
\t\t_anim_idx = (_anim_idx + 1) % _anim_frames.size()
\t\t_sprite.frame = _anim_frames[_anim_idx]
'''


# ==========================================================================
# SceneManager autoload — handles multi-scene transitions & persistent state
# ==========================================================================

SCENE_MANAGER_GD = '''extends Node
## SceneManager — handles scene transitions and persistent state.
## Generated by Quantum Framework - Godot Backend

var persistent_state: Dictionary = {}
var current_scene_name: String = ""

var _transition_layer: CanvasLayer
var _color_rect: ColorRect
var _transitioning: bool = false

func _ready():
\t_setup_transition_layer()

func _setup_transition_layer():
\t_transition_layer = CanvasLayer.new()
\t_transition_layer.layer = 100
\tadd_child(_transition_layer)
\t_color_rect = ColorRect.new()
\t_color_rect.color = Color.BLACK
\t_color_rect.anchors_preset = Control.PRESET_FULL_RECT
\t_color_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
\t_color_rect.modulate.a = 0.0
\t_transition_layer.add_child(_color_rect)

func transition_to(scene_name: String, effect: String = "fade", duration: float = 0.5, data: Dictionary = {}):
\tif _transitioning:
\t\treturn
\t_transitioning = true
\tfor key in data:
\t\tpersistent_state[key] = data[key]
\tvar scene_path = "res://scenes/" + scene_name + ".tscn"
\tmatch effect:
\t\t"fade":
\t\t\tawait _fade_out(duration / 2.0)
\t\t\tget_tree().change_scene_to_file(scene_path)
\t\t\tawait get_tree().process_frame
\t\t\tcurrent_scene_name = scene_name
\t\t\tawait _fade_in(duration / 2.0)
\t\t"iris-out":
\t\t\tawait _fade_out(duration)
\t\t\tget_tree().change_scene_to_file(scene_path)
\t\t\tawait get_tree().process_frame
\t\t\tcurrent_scene_name = scene_name
\t\t\t_color_rect.modulate.a = 0.0
\t\t"iris-in":
\t\t\t_color_rect.modulate.a = 1.0
\t\t\tget_tree().change_scene_to_file(scene_path)
\t\t\tawait get_tree().process_frame
\t\t\tcurrent_scene_name = scene_name
\t\t\tawait _fade_in(duration)
\t\t"cut":
\t\t\tget_tree().change_scene_to_file(scene_path)
\t\t\tawait get_tree().process_frame
\t\t\tcurrent_scene_name = scene_name
\t_transitioning = false

func _fade_out(duration: float):
\tvar tween = create_tween()
\ttween.tween_property(_color_rect, "modulate:a", 1.0, duration)
\tawait tween.finished

func _fade_in(duration: float):
\tvar tween = create_tween()
\ttween.tween_property(_color_rect, "modulate:a", 0.0, duration)
\tawait tween.finished

func set_state(key: String, value):
\tpersistent_state[key] = value

func get_state(key: String, default = null):
\treturn persistent_state.get(key, default)
'''


MAP_CONTROLLER_GD = '''extends Node2D
## MapController — handles world map navigation between nodes.
## Generated by Quantum Framework - Godot Backend

@export var map_data: Dictionary = {}
@export var path_data: Array = []

var current_node: String = ""
var _mario_sprite: Sprite2D
var _moving: bool = false

func _ready():
\t_mario_sprite = $Mario if has_node("Mario") else null
\tif map_data.has("start_node"):
\t\tcurrent_node = map_data["start_node"]
\tif _mario_sprite and map_data.has("nodes") and map_data["nodes"].has(current_node):
\t\tvar node_info = map_data["nodes"][current_node]
\t\t_mario_sprite.position = Vector2(node_info["x"], node_info["y"])

func _input(event: InputEvent):
\tif _moving:
\t\treturn
\tif event.is_action_pressed("ui_accept"):
\t\t_enter_node()
\telif event.is_action_pressed("ui_right"):
\t\t_try_move("right")
\telif event.is_action_pressed("ui_left"):
\t\t_try_move("left")
\telif event.is_action_pressed("ui_up"):
\t\t_try_move("up")
\telif event.is_action_pressed("ui_down"):
\t\t_try_move("down")

func _enter_node():
\tif not map_data.has("nodes"):
\t\treturn
\tvar node_info = map_data["nodes"].get(current_node, {})
\tvar scene_name = node_info.get("scene", "")
\tif scene_name != "" and not node_info.get("locked", false):
\t\tSceneManager.transition_to(scene_name, "iris-in", 0.5)

func _try_move(direction: String):
\tvar neighbors = _get_neighbors(current_node)
\tvar best_node = ""
\tvar best_dist = INF
\tvar current_pos = _get_node_pos(current_node)
\tfor neighbor in neighbors:
\t\tvar neighbor_pos = _get_node_pos(neighbor)
\t\tvar delta = neighbor_pos - current_pos
\t\tvar valid = false
\t\tmatch direction:
\t\t\t"right": valid = delta.x > 0 and abs(delta.x) >= abs(delta.y)
\t\t\t"left": valid = delta.x < 0 and abs(delta.x) >= abs(delta.y)
\t\t\t"up": valid = delta.y < 0 and abs(delta.y) >= abs(delta.x)
\t\t\t"down": valid = delta.y > 0 and abs(delta.y) >= abs(delta.x)
\t\tif valid:
\t\t\tvar dist = delta.length()
\t\t\tif dist < best_dist:
\t\t\t\tbest_dist = dist
\t\t\t\tbest_node = neighbor
\tif best_node != "":
\t\t_move_to(best_node)

func _move_to(target_node: String):
\t_moving = true
\tvar target_pos = _get_node_pos(target_node)
\tif _mario_sprite:
\t\tvar tween = create_tween()
\t\ttween.tween_property(_mario_sprite, "position", target_pos, 0.2)
\t\tawait tween.finished
\tcurrent_node = target_node
\t_moving = false

func _get_neighbors(node_id: String) -> Array:
\tvar neighbors = []
\tfor path in path_data:
\t\tvar unlocked = true
\t\tif path.has("unlock") and path["unlock"] != "":
\t\t\tunlocked = SceneManager.get_state(path["unlock"], false)
\t\tif not unlocked:
\t\t\tcontinue
\t\tif path["from"] == node_id:
\t\t\tneighbors.append(path["to"])
\t\telif path["to"] == node_id:
\t\t\tneighbors.append(path["from"])
\treturn neighbors

func _get_node_pos(node_id: String) -> Vector2:
\tif map_data.has("nodes") and map_data["nodes"].has(node_id):
\t\tvar info = map_data["nodes"][node_id]
\t\treturn Vector2(info["x"], info["y"])
\treturn Vector2.ZERO
'''


# ==========================================================================
# Tilemap Loader — loads tile data from external JSON at runtime
# ==========================================================================

TILEMAP_LOADER_GD = '''\
extends TileMapLayer
## Loads tile data from {json_path} and populates the TileMapLayer at runtime.

func _ready():
\tvar file = FileAccess.open("{json_path}", FileAccess.READ)
\tif not file:
\t\tpush_error("tilemap_loader: Could not open {json_path}")
\t\treturn
\tvar json_text = file.get_as_text()
\tfile.close()

\tvar json = JSON.parse_string(json_text)
\tif json == null:
\t\tpush_error("tilemap_loader: Failed to parse {json_path}")
\t\treturn

\tvar grid = json["grid"]
\tvar count = 0
\tfor row_idx in grid.size():
\t\tvar row = grid[row_idx]
\t\tfor col_idx in row.size():
\t\t\tvar cell = row[col_idx]
\t\t\tif cell != null:
\t\t\t\tvar atlas_x = int(cell[0])
\t\t\t\tvar atlas_y = int(cell[1])
\t\t\t\tset_cell(Vector2i(col_idx, row_idx), {source_id}, Vector2i(atlas_x, atlas_y))
\t\t\t\tcount += 1

\tprint("TileMapLayer: loaded ", count, " tiles")
'''


# ==========================================================================
# Game Over Screen
# ==========================================================================

GAME_OVER_SCREEN_GD = '''\
extends CanvasLayer
## Game Over Screen - SMW-style slide-in animation
## "GAME" slides from left, "OVER" from right, meet at center
## Generated by Quantum Framework

var _alphabet_tex: Texture2D
var _canvas: Control
var _game_x: float = -64.0
var _over_x: float = 320.0
var _target_game_x: float
var _target_over_x: float
var _black_alpha: float = 0.0
var _phase: int = 0  # 0=fade-in, 1=slide, 2=hold
var _timer: float = 0.0
var _sfx: AudioStreamPlayer

const CHAR_W: int = 8
const CHAR_H: int = 8
const SCALE: float = 2.0

signal game_over_finished

func _ready():
\tlayer = 100
\tprocess_mode = Node.PROCESS_MODE_ALWAYS

\t_alphabet_tex = load("res://{alphabet_path}")

\t_canvas = Control.new()
\t_canvas.set_anchors_preset(Control.PRESET_FULL_RECT)
\t_canvas.connect("draw", _on_draw)
\tadd_child(_canvas)

\t# "GAME OVER" layout
\tvar vp_w: float = {viewport_width}.0
\tvar game_width = 4 * CHAR_W * SCALE
\tvar over_width = 4 * CHAR_W * SCALE
\tvar space_w = CHAR_W * SCALE
\tvar total_width = game_width + space_w + over_width
\tvar center_x = vp_w / 2.0

\t_target_game_x = center_x - total_width / 2.0
\t_target_over_x = _target_game_x + game_width + space_w

\t_game_x = -game_width
\t_over_x = vp_w + over_width

func _process(delta: float):
\tmatch _phase:
\t\t0:  # Fade to black
\t\t\t_black_alpha = min(1.0, _black_alpha + delta * 2.0)
\t\t\tif _black_alpha >= 1.0:
\t\t\t\t_phase = 1
\t\t\t\t_timer = 0.0
\t\t\t\t_sfx = AudioStreamPlayer.new()
\t\t\t\t_sfx.stream = load("res://{jingle_path}")
\t\t\t\t_sfx.process_mode = Node.PROCESS_MODE_ALWAYS
\t\t\t\tadd_child(_sfx)
\t\t\t\t_sfx.play()
\t\t1:  # Slide in
\t\t\t_timer += delta
\t\t\tvar t = clamp(_timer / 0.8, 0.0, 1.0)
\t\t\tvar ease_t = 1.0 - pow(1.0 - t, 3.0)
\t\t\t_game_x = lerp(-64.0, _target_game_x, ease_t)
\t\t\t_over_x = lerp({viewport_width}.0 + 64.0, _target_over_x, ease_t)
\t\t\tif t >= 1.0:
\t\t\t\t_phase = 2
\t\t\t\t_timer = 0.0
\t\t2:  # Hold until jingle ends
\t\t\t_timer += delta
\t\t\tif _timer >= 6.0:
\t\t\t\temit_signal("game_over_finished")
\t\t\t\tset_process(false)
\t_canvas.queue_redraw()

func _on_draw():
\tvar size = _canvas.size
\t_canvas.draw_rect(Rect2(0, 0, size.x, size.y), Color(0, 0, 0, _black_alpha))
\tif _phase >= 1:
\t\tvar center_y = size.y / 2.0 - CHAR_H * SCALE / 2.0
\t\t_draw_word("GAME", _game_x, center_y)
\t\t_draw_word("OVER", _over_x, center_y)

func _draw_word(word: String, x: float, y: float):
\tfor i in range(word.length()):
\t\tvar ch = word[i]
\t\tvar idx = ch.unicode_at(0) - "A".unicode_at(0)
\t\tif idx < 0 or idx > 25:
\t\t\tcontinue
\t\tvar src = Rect2(idx * CHAR_W, 0, CHAR_W, CHAR_H)
\t\tvar dst = Rect2(x + i * CHAR_W * SCALE, y, CHAR_W * SCALE, CHAR_H * SCALE)
\t\t_canvas.draw_texture_rect_region(_alphabet_tex, dst, src)
'''
