"""
Tests for Godot 4 Code Generator

Verifies that Game AST nodes compile correctly to Godot 4 project files
(.tscn, .gd, project.godot).
"""

import pytest
import sys
import os
import shutil
import tempfile
from pathlib import Path


from quantum.core.features.game_engine_2d.src.ast_nodes import (
    SceneNode, SpriteNode, PhysicsNode, CameraNode, BehaviorNode,
    PrefabNode, InstanceNode, GroupNode, UseNode, HudNode,
    SoundNode, InputNode, AnimationNode, ColliderNode, TimerNode,
    TweenNode, StateMachineNode, StateNode, TransitionNode,
    ParticleNode, TilemapNode, TilemapLayerNode, SpawnNode,
    EventNode, OnCollisionNode, RawCodeNode, TileAnimationNode,
    HudTileNode, HudCounterNode, HudCollectionNode,
    HudSlotNode, HudOptionNode, HudBehaviorNode, HudActionNode,
    SceneTransitionNode, PersistentNode, MapNodeDef, MapPathNode,
    EventActionNode, CollisionLayerDef,
    EnemyNode, EnemyAiNode, EnemyDefeatNode, EnemyOnHitNode, EnemyOnKillNode,
)
from quantum.core.features.state_management.src.ast_node import SetNode
from quantum.core.features.functions.src.ast_node import FunctionNode
from quantum.core.ast_nodes import ApplicationNode, HTMLNode, TextNode
from quantum.runtime.godot_code_generator import GodotCodeGenerator
from quantum.runtime.godot_templates import (
    GdScriptBuilder, TscnBuilder,
    QUANTUM_SCALE, q2g, q2g_int, q2g_gravity, q2g_speed, q2g_jump,
    gd_string, gd_bool, gd_vector2, gd_vector2i, gd_color,
    build_project_godot, build_export_presets,
    TILEMAP_LOADER_GD,
)
from quantum.runtime.game_builder import GameBuilder, GameBuildError


@pytest.fixture
def codegen():
    return GodotCodeGenerator()


@pytest.fixture
def output_dir(tmp_path):
    """Provide a temporary output directory."""
    return str(tmp_path / 'godot_output')


@pytest.fixture
def basic_scene():
    """Create a basic scene with one sprite."""
    scene = SceneNode('main')
    scene.width = 800
    scene.height = 600
    scene.background = '#1a1a2e'
    sprite = SpriteNode('player')
    sprite.src = 'player.png'
    sprite.x = 100
    sprite.y = 200
    scene.add_child(sprite)
    return scene


# ==========================================================================
# GdScriptBuilder Tests
# ==========================================================================

class TestGdScriptBuilder:
    """Test the GDScript code builder."""

    def test_basic_script(self):
        gd = GdScriptBuilder()
        gd.extends('Node2D')
        gd.blank()
        gd.var('speed', '100.0', 'float')
        gd.blank()
        gd.func('_ready')
        gd.line('print("Hello")')
        gd.func_close()
        result = gd.build()
        assert 'extends Node2D' in result
        assert 'var speed: float = 100.0' in result
        assert 'func _ready():' in result
        assert '\tprint("Hello")' in result

    def test_indentation(self):
        gd = GdScriptBuilder()
        gd.func('test')
        gd.if_block('x > 0')
        gd.line('print("positive")')
        gd.else_block()
        gd.line('print("negative")')
        gd.block_close()
        gd.func_close()
        result = gd.build()
        assert '\tif x > 0:' in result
        assert '\t\tprint("positive")' in result
        assert '\telse:' in result
        assert '\t\tprint("negative")' in result

    def test_export_var(self):
        gd = GdScriptBuilder()
        gd.export_var('speed', 'float', '100.0')
        result = gd.build()
        assert '@export var speed: float = 100.0' in result

    def test_onready_var(self):
        gd = GdScriptBuilder()
        gd.onready_var('sprite', 'Sprite2D')
        result = gd.build()
        assert '@onready var sprite = $Sprite2D' in result

    def test_signal_decl(self):
        gd = GdScriptBuilder()
        gd.signal_decl('health_changed', 'new_value: int')
        result = gd.build()
        assert 'signal health_changed(new_value: int)' in result

    def test_for_loop(self):
        gd = GdScriptBuilder()
        gd.for_block('i', 'range(10)')
        gd.line('print(i)')
        gd.block_close()
        result = gd.build()
        assert 'for i in range(10):' in result
        assert '\tprint(i)' in result

    def test_const(self):
        gd = GdScriptBuilder()
        gd.const('MAX_SPEED', '500.0')
        result = gd.build()
        assert 'const MAX_SPEED = 500.0' in result

    def test_return_stmt(self):
        gd = GdScriptBuilder()
        gd.func('get_value', return_type='int')
        gd.return_stmt('42')
        gd.func_close()
        result = gd.build()
        assert 'func get_value() -> int:' in result
        assert '\treturn 42' in result

    def test_match_block(self):
        gd = GdScriptBuilder()
        gd.match_block('state')
        gd.match_case('"idle"')
        gd.line('do_idle()')
        gd.block_close()
        gd.match_case('"run"')
        gd.line('do_run()')
        gd.block_close()
        gd.block_close()
        result = gd.build()
        assert 'match state:' in result
        assert '"idle":' in result


# ==========================================================================
# TscnBuilder Tests
# ==========================================================================

class TestTscnBuilder:
    """Test the .tscn scene file builder."""

    def test_basic_scene(self):
        tscn = TscnBuilder()
        tscn.add_node('Root', 'Node2D')
        result = tscn.build()
        assert '[gd_scene' in result
        assert 'format=3' in result
        assert '[node name="Root" type="Node2D"]' in result

    def test_node_with_parent(self):
        tscn = TscnBuilder()
        tscn.add_node('Root', 'Node2D')
        tscn.add_node('Child', 'Sprite2D', parent='.')
        result = tscn.build()
        assert '[node name="Root" type="Node2D"]' in result
        assert '[node name="Child" type="Sprite2D" parent="."]' in result

    def test_ext_resource(self):
        tscn = TscnBuilder()
        rid = tscn.add_ext_resource('Texture2D', 'assets/player.png')
        tscn.add_node('Root', 'Node2D')
        tscn.add_node('Sprite', 'Sprite2D', parent='.', properties={
            'texture': f'ExtResource("{rid}")',
        })
        result = tscn.build()
        assert '[ext_resource type="Texture2D" path="res://assets/player.png"' in result
        assert 'texture = ExtResource("' in result

    def test_ext_resource_dedup(self):
        """Same path should return same resource ID."""
        tscn = TscnBuilder()
        rid1 = tscn.add_ext_resource('Texture2D', 'assets/player.png')
        rid2 = tscn.add_ext_resource('Texture2D', 'assets/player.png')
        assert rid1 == rid2
        assert len(tscn._ext_resources) == 1

    def test_sub_resource(self):
        tscn = TscnBuilder()
        shape_id = tscn.add_sub_resource('RectangleShape2D', {
            'size': 'Vector2(32, 32)',
        })
        tscn.add_node('Root', 'Node2D')
        result = tscn.build()
        assert '[sub_resource type="RectangleShape2D"' in result
        assert 'size = Vector2(32, 32)' in result

    def test_node_with_script(self):
        tscn = TscnBuilder()
        tscn.add_node_with_script('Root', 'Node2D', 'scripts/main.gd')
        result = tscn.build()
        assert '[ext_resource type="Script" path="res://scripts/main.gd"' in result
        assert 'script = ExtResource("' in result

    def test_node_groups(self):
        tscn = TscnBuilder()
        tscn.add_node('Enemy', 'CharacterBody2D', parent='.', groups=['enemies'])
        result = tscn.build()
        assert 'groups=["enemies"]' in result

    def test_node_properties(self):
        tscn = TscnBuilder()
        tscn.add_node('Sprite', 'Sprite2D', parent='.', properties={
            'position': 'Vector2(100, 200)',
            'visible': True,
            'scale': 'Vector2(2, 2)',
        })
        result = tscn.build()
        assert 'position = Vector2(100, 200)' in result
        assert 'visible = true' in result
        assert 'scale = Vector2(2, 2)' in result

    def test_instance_node(self):
        tscn = TscnBuilder()
        rid = tscn.add_ext_resource('PackedScene', 'prefabs/coin.tscn')
        tscn.add_node('Root', 'Node2D')
        tscn.add_node('coin_1', '', parent='.', instance=f'ExtResource("{rid}")')
        result = tscn.build()
        assert f'instance=ExtResource("{rid}")' in result


# ==========================================================================
# Scale Conversion Tests
# ==========================================================================

class TestScaleConversion:
    """Test Quantum → Godot scale conversion."""

    def test_q2g(self):
        assert q2g(1.0) == 100.0
        assert q2g(1.5) == 150.0
        assert q2g(0) == 0

    def test_q2g_int(self):
        assert q2g_int(1.5) == 150
        assert isinstance(q2g_int(1.0), int)

    def test_q2g_gravity(self):
        assert q2g_gravity(9.8) == pytest.approx(980.0)

    def test_q2g_speed(self):
        assert q2g_speed(1.5) == 150.0

    def test_q2g_jump(self):
        # Jump should be negative (up in Godot)
        result = q2g_jump(5.3)
        assert result < 0
        assert abs(result) == pytest.approx(5.3 * 100 * 0.6)


# ==========================================================================
# Helper Function Tests
# ==========================================================================

class TestHelpers:
    """Test GDScript helper functions."""

    def test_gd_string(self):
        assert gd_string('hello') == '"hello"'
        assert gd_string('it\'s a "test"') == '"it\'s a \\"test\\""'
        assert gd_string('line\nbreak') == '"line\\nbreak"'

    def test_gd_bool(self):
        assert gd_bool(True) == 'true'
        assert gd_bool(False) == 'false'

    def test_gd_vector2(self):
        assert 'Vector2(' in gd_vector2(10.0, 20.0)
        assert '10' in gd_vector2(10.0, 20.0)
        assert '20' in gd_vector2(10.0, 20.0)

    def test_gd_vector2i(self):
        result = gd_vector2i(16, 16)
        assert result == 'Vector2i(16, 16)'

    def test_gd_color(self):
        result = gd_color('#ff0000')
        assert 'Color(' in result
        assert '1.0' in result  # Red channel

    def test_gd_color_short(self):
        result = gd_color('#f00')
        assert 'Color(' in result


# ==========================================================================
# project.godot Generation Tests
# ==========================================================================

class TestProjectGodot:
    """Test project.godot file generation."""

    def test_basic_project(self):
        config = {
            'name': 'TestGame',
            'main_scene': 'main.tscn',
            'viewport_width': 256,
            'viewport_height': 224,
            'gravity': 750.0,
        }
        content = build_project_godot(config)
        assert 'config_version=5' in content
        assert 'config/name="TestGame"' in content
        assert 'run/main_scene="res://main.tscn"' in content
        # SNES native resolution
        assert 'window/size/viewport_width=256' in content
        assert 'window/size/viewport_height=224' in content
        # 3x upscale window
        assert 'window/size/window_width_override=768' in content
        assert 'window/size/window_height_override=672' in content
        # Pixel-perfect stretch
        assert 'window/stretch/mode="viewport"' in content
        assert 'window/stretch/aspect="keep"' in content
        assert '2d/default_gravity=750.0' in content

    def test_autoloads(self):
        config = {
            'name': 'Test',
            'autoloads': {
                'QuantumBridge': 'scripts/quantum_bridge.gd',
                'QuantumEventBus': 'scripts/quantum_event_bus.gd',
            },
        }
        content = build_project_godot(config)
        assert '[autoload]' in content
        assert 'QuantumBridge="*res://scripts/quantum_bridge.gd"' in content
        assert 'QuantumEventBus="*res://scripts/quantum_event_bus.gd"' in content

    def test_input_map(self):
        config = {
            'name': 'Test',
            'input_map': {
                'move_left': ['ArrowLeft', 'a'],
                'jump': ['Space'],
            },
        }
        content = build_project_godot(config)
        assert '[input]' in content
        assert 'move_left=' in content
        assert 'jump=' in content

    def test_physics_layers(self):
        config = {'name': 'Test'}
        content = build_project_godot(config)
        assert '[layer_names]' in content
        assert '2d_physics/layer_1="world"' in content
        assert '2d_physics/layer_2="player"' in content

    def test_pixel_art_rendering(self):
        config = {'name': 'Test'}
        content = build_project_godot(config)
        assert 'textures/canvas_textures/default_texture_filter=0' in content


# ==========================================================================
# Export Presets Tests
# ==========================================================================

class TestExportPresets:
    """Test export_presets.cfg generation."""

    def test_web_export(self):
        content = build_export_presets()
        assert 'name="Web"' in content
        assert 'platform="Web"' in content
        assert 'export_path="dist/index.html"' in content
        assert 'runnable=true' in content


# ==========================================================================
# GodotCodeGenerator Tests - Project Structure
# ==========================================================================

class TestProjectGeneration:
    """Test that GodotCodeGenerator produces correct project structure."""

    def test_generates_project_directory(self, codegen, basic_scene, output_dir):
        result = codegen.generate(basic_scene, output_dir=output_dir)
        out = Path(result)
        assert out.exists()
        assert (out / 'project.godot').exists()
        assert (out / 'main.tscn').exists()
        assert (out / 'export_presets.cfg').exists()

    def test_generates_scripts_directory(self, codegen, basic_scene, output_dir):
        result = codegen.generate(basic_scene, output_dir=output_dir)
        out = Path(result)
        assert (out / 'scripts').is_dir()
        assert (out / 'scripts' / 'quantum_bridge.gd').exists()
        assert (out / 'scripts' / 'quantum_event_bus.gd').exists()
        assert (out / 'scripts' / 'scene_main.gd').exists()

    def test_generates_prefabs_directory(self, codegen, basic_scene, output_dir):
        result = codegen.generate(basic_scene, output_dir=output_dir)
        out = Path(result)
        assert (out / 'prefabs').is_dir()

    def test_generates_assets_directory(self, codegen, basic_scene, output_dir):
        result = codegen.generate(basic_scene, output_dir=output_dir)
        out = Path(result)
        assert (out / 'assets').is_dir()


# ==========================================================================
# GodotCodeGenerator Tests - Sprites
# ==========================================================================

class TestSpriteGeneration:
    """Test sprite node generation."""

    def test_static_sprite(self, codegen, output_dir):
        scene = SceneNode('main')
        sprite = SpriteNode('bg')
        sprite.src = 'background.png'
        sprite.x = 0
        sprite.y = 0
        scene.add_child(sprite)

        codegen.generate(scene, output_dir=output_dir)
        tscn = Path(output_dir, 'main.tscn').read_text(encoding='utf-8')
        assert 'name="bg"' in tscn
        assert 'Sprite2D' in tscn
        assert 'background.png' in tscn

    def test_physics_static_body(self, codegen, output_dir):
        scene = SceneNode('main')
        sprite = SpriteNode('ground')
        sprite.src = 'ground.png'
        sprite.body = 'static'
        sprite.x = 400
        sprite.y = 550
        scene.add_child(sprite)

        codegen.generate(scene, output_dir=output_dir)
        tscn = Path(output_dir, 'main.tscn').read_text(encoding='utf-8')
        assert 'StaticBody2D' in tscn
        assert 'CollisionShape2D' in tscn

    def test_player_character_body(self, codegen, output_dir):
        scene = SceneNode('main')
        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.body = 'dynamic'
        player.controls = 'arrows'
        player.speed = 1.5
        player.jump_force = 5.3
        player.x = 100
        player.y = 400
        scene.add_child(player)

        codegen.generate(scene, output_dir=output_dir)
        tscn = Path(output_dir, 'main.tscn').read_text(encoding='utf-8')
        assert 'CharacterBody2D' in tscn
        assert 'player_controller.gd' in tscn

        # Player controller should exist
        controller = Path(output_dir, 'scripts', 'player_controller.gd').read_text(encoding='utf-8')
        assert 'extends CharacterBody2D' in controller
        assert 'move_speed' in controller
        assert 'jump_velocity' in controller
        assert 'move_and_slide()' in controller

    def test_sensor_sprite(self, codegen, output_dir):
        scene = SceneNode('main')
        sprite = SpriteNode('trigger')
        sprite.sensor = True
        sprite.x = 200
        sprite.y = 300
        scene.add_child(sprite)

        codegen.generate(scene, output_dir=output_dir)
        tscn = Path(output_dir, 'main.tscn').read_text(encoding='utf-8')
        assert 'Area2D' in tscn

    def test_sprite_with_animation(self, codegen, output_dir):
        scene = SceneNode('main')
        sprite = SpriteNode('player')
        sprite.src = 'player.png'
        sprite.body = 'dynamic'
        sprite.controls = 'arrows'
        anim = AnimationNode('walk')
        anim.frames = '0-3'
        anim.speed = 0.1
        sprite.add_child(anim)
        scene.add_child(sprite)

        codegen.generate(scene, output_dir=output_dir)
        tscn = Path(output_dir, 'main.tscn').read_text(encoding='utf-8')
        # Sprites with animations now use Sprite2D with hframes (AnimatedSprite2D deferred)
        assert 'Sprite2D' in tscn
        assert 'player.png' in tscn

    def test_sprite_position_passthrough(self, codegen, output_dir):
        """Verify Quantum pixel coordinates are passed through directly (no scaling)."""
        scene = SceneNode('main')
        sprite = SpriteNode('test')
        sprite.src = 'test.png'
        sprite.x = 80   # pixel coordinate — should stay 80
        sprite.y = 350  # pixel coordinate — should stay 350
        scene.add_child(sprite)

        codegen.generate(scene, output_dir=output_dir)
        tscn = Path(output_dir, 'main.tscn').read_text(encoding='utf-8')
        assert 'Vector2(80' in tscn
        assert '350' in tscn


# ==========================================================================
# GodotCodeGenerator Tests - Physics
# ==========================================================================

class TestPhysicsGeneration:
    """Test physics configuration generation."""

    def test_snes_gravity(self, codegen, output_dir):
        """Gravity uses SNES SMW constant regardless of .q value."""
        scene = SceneNode('main')
        physics = PhysicsNode()
        physics.gravity_y = 1.5  # Quantum abstract value — ignored for Godot
        scene.add_child(physics)
        sprite = SpriteNode('s1')
        sprite.src = 'a.png'
        scene.add_child(sprite)

        codegen.generate(scene, output_dir=output_dir)
        project = Path(output_dir, 'project.godot').read_text(encoding='utf-8')
        # SNES SMW default gravity: 750 px/s²
        assert '750.0' in project

    def test_input_map_generated(self, codegen, output_dir):
        scene = SceneNode('main')
        player = SpriteNode('player')
        player.body = 'dynamic'
        player.controls = 'arrows'
        player.src = 'p.png'
        scene.add_child(player)

        codegen.generate(scene, output_dir=output_dir)
        project = Path(output_dir, 'project.godot').read_text(encoding='utf-8')
        assert 'move_left=' in project
        assert 'move_right=' in project
        assert 'jump=' in project


# ==========================================================================
# GodotCodeGenerator Tests - Camera
# ==========================================================================

class TestCameraGeneration:
    """Test camera node generation."""

    def test_camera_with_follow(self, codegen, output_dir):
        scene = SceneNode('main')
        cam = CameraNode()
        cam.follow = 'player'
        cam.lerp = 0.1
        cam.bounds = 'scene'
        scene.add_child(cam)
        sprite = SpriteNode('player')
        sprite.src = 'p.png'
        scene.add_child(sprite)

        codegen.generate(scene, output_dir=output_dir)
        tscn = Path(output_dir, 'main.tscn').read_text(encoding='utf-8')
        assert 'Camera2D' in tscn
        assert 'camera_follow.gd' in tscn

        cam_script = Path(output_dir, 'scripts', 'camera_follow.gd').read_text(encoding='utf-8')
        assert 'extends Camera2D' in cam_script
        assert 'position_smoothing_enabled' in cam_script
        assert 'shake' in cam_script


# ==========================================================================
# GodotCodeGenerator Tests - Tilemap
# ==========================================================================

class TestTilemapGeneration:
    """Test tilemap generation."""

    def test_tilemap_basic(self, codegen, output_dir):
        scene = SceneNode('main')
        tilemap = TilemapNode('world')
        tilemap.src = 'tileset.png'
        tilemap.tile_width = 16
        tilemap.tile_height = 16

        layer = TilemapLayerNode('ground')
        layer.data = '0,0,1,1\n0,0,1,1'
        layer.collision = True
        tilemap.add_layer(layer)

        scene.add_child(tilemap)

        codegen.generate(scene, output_dir=output_dir)
        tscn = Path(output_dir, 'main.tscn').read_text(encoding='utf-8')
        assert 'TileMapLayer' in tscn

        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert '_setup_tilemaps' in script
        assert 'TileSet.new()' in script
        assert 'add_physics_layer' in script
        assert 'set_cell' in script

    def test_tilemap_multiple_layers(self, codegen, output_dir):
        scene = SceneNode('main')
        tilemap = TilemapNode('level')
        tilemap.src = 'tiles.png'
        tilemap.tile_width = 16
        tilemap.tile_height = 16

        bg_layer = TilemapLayerNode('background')
        bg_layer.data = '1,2\n3,4'
        tilemap.add_layer(bg_layer)

        col_layer = TilemapLayerNode('collision')
        col_layer.data = '0,1\n1,1'
        col_layer.collision = True
        tilemap.add_layer(col_layer)

        scene.add_child(tilemap)

        codegen.generate(scene, output_dir=output_dir)
        tscn = Path(output_dir, 'main.tscn').read_text(encoding='utf-8')
        assert 'level_background' in tscn
        assert 'level_collision' in tscn


# ==========================================================================
# GodotCodeGenerator Tests - Prefabs & Instances
# ==========================================================================

class TestPrefabGeneration:
    """Test prefab and instance generation."""

    def test_prefab_scene_generated(self, codegen, output_dir):
        scene = SceneNode('main')
        sprite = SpriteNode('s1')
        sprite.src = 'a.png'
        scene.add_child(sprite)

        # Create a prefab
        prefab = PrefabNode('coin')
        prefab.entity_type = 'item'
        prefab.collectible = True
        coin_sprite = SpriteNode('coin_sprite')
        coin_sprite.src = 'coin.png'
        prefab.add_child(coin_sprite)

        codegen.generate(scene, prefabs=[prefab], output_dir=output_dir)
        assert Path(output_dir, 'prefabs', 'coin.tscn').exists()

    def test_enemy_prefab_with_ai(self, codegen, output_dir):
        scene = SceneNode('main')
        sprite = SpriteNode('s1')
        sprite.src = 'a.png'
        scene.add_child(sprite)

        prefab = PrefabNode('rex')
        prefab.entity_type = 'enemy'
        prefab.movement = 'patrol'
        prefab.move_speed = 0.5
        prefab.turn_on_edge = True
        prefab.facing = 'left'
        rex_sprite = SpriteNode('rex_sprite')
        rex_sprite.src = 'rex.png'
        rex_sprite.body = 'dynamic'
        prefab.add_child(rex_sprite)

        codegen.generate(scene, prefabs=[prefab], output_dir=output_dir)
        prefab_tscn = Path(output_dir, 'prefabs', 'rex.tscn').read_text(encoding='utf-8')
        assert 'CharacterBody2D' in prefab_tscn

        # Check AI script was generated
        assert Path(output_dir, 'scripts', 'prefab_rex.gd').exists()
        ai_script = Path(output_dir, 'scripts', 'prefab_rex.gd').read_text(encoding='utf-8')
        assert 'patrol_speed' in ai_script
        assert 'move_and_slide()' in ai_script

    def test_instance_in_scene(self, codegen, output_dir):
        scene = SceneNode('main')

        inst = InstanceNode('coin')
        inst.instance_id = 'coin_1'
        inst.x = 5.0
        inst.y = 3.0
        scene.add_child(inst)

        prefab = PrefabNode('coin')
        coin_sprite = SpriteNode('cs')
        coin_sprite.src = 'coin.png'
        prefab.add_child(coin_sprite)

        codegen.generate(scene, prefabs=[prefab], output_dir=output_dir)
        tscn = Path(output_dir, 'main.tscn').read_text(encoding='utf-8')
        assert 'coin_1' in tscn
        assert 'PackedScene' in tscn


# ==========================================================================
# GodotCodeGenerator Tests - Events
# ==========================================================================

class TestEventGeneration:
    """Test event and collision generation."""

    def test_event_listener(self, codegen, output_dir):
        scene = SceneNode('main')
        event = EventNode('coinCollected', 'onCoinCollected')
        scene.add_child(event)
        sprite = SpriteNode('s1')
        sprite.src = 'a.png'
        scene.add_child(sprite)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'QuantumEventBus.listen("coinCollected"' in script
        assert 'onCoinCollected' in script

    def test_on_collision_generates_handler(self, codegen, output_dir):
        scene = SceneNode('main')
        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.body = 'dynamic'
        player.controls = 'arrows'

        collision = OnCollisionNode()
        collision.with_tag = 'coin'
        collision.action = 'destroy-other'
        player.add_child(collision)

        scene.add_child(player)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert '_on_mario_collision' in script
        assert 'body.queue_free()' in script

    def test_collision_emit_action(self, codegen, output_dir):
        scene = SceneNode('main')
        sprite = SpriteNode('player')
        sprite.src = 'p.png'
        sprite.body = 'dynamic'
        sprite.controls = 'arrows'

        col = OnCollisionNode()
        col.with_tag = 'enemy'
        col.action = 'emit:player-hit'
        sprite.add_child(col)
        scene.add_child(sprite)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'emit_event("player-hit"' in script


# ==========================================================================
# GodotCodeGenerator Tests - Audio
# ==========================================================================

class TestAudioGeneration:
    """Test sound node generation."""

    def test_sound_node(self, codegen, output_dir):
        scene = SceneNode('main')
        sound = SoundNode('sfx-jump')
        sound.src = 'jump.wav'
        sound.volume = 0.8
        scene.add_child(sound)
        sprite = SpriteNode('s1')
        sprite.src = 'a.png'
        scene.add_child(sprite)

        codegen.generate(scene, output_dir=output_dir)
        tscn = Path(output_dir, 'main.tscn').read_text(encoding='utf-8')
        assert 'AudioStreamPlayer' in tscn
        assert 'sfx-jump' in tscn
        assert 'Sounds' in tscn


# ==========================================================================
# GodotCodeGenerator Tests - HUD
# ==========================================================================

class TestHudGeneration:
    """Test HUD generation."""

    def test_hud_canvas_layer(self, codegen, output_dir):
        scene = SceneNode('main')
        hud = HudNode()
        hud.position = 'top-left'
        html = HTMLNode('span')
        html.attributes = {'id': 'score'}
        text = TextNode('Score: 0')
        html.children = [text]
        hud.add_child(html)
        scene.add_child(hud)
        sprite = SpriteNode('s1')
        sprite.src = 'a.png'
        scene.add_child(sprite)

        codegen.generate(scene, output_dir=output_dir)
        tscn = Path(output_dir, 'main.tscn').read_text(encoding='utf-8')
        assert 'CanvasLayer' in tscn
        assert 'Label' in tscn
        assert 'score' in tscn

        # HUD script should exist
        hud_script = Path(output_dir, 'scripts', 'hud_manager.gd').read_text(encoding='utf-8')
        assert 'extends CanvasLayer' in hud_script


# ==========================================================================
# GodotCodeGenerator Tests - Tweens & Timers
# ==========================================================================

class TestTweenTimerGeneration:
    """Test tween and timer generation."""

    def test_tween_auto_start(self, codegen, output_dir):
        scene = SceneNode('main')
        tween = TweenNode('bob')
        tween.target = 'player'
        tween.property = 'y'
        tween.to_value = 50
        tween.duration = 1.0
        tween.easing = 'ease-in-out'
        tween.auto_start = True
        scene.add_child(tween)
        sprite = SpriteNode('player')
        sprite.src = 'p.png'
        scene.add_child(sprite)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'create_tween()' in script
        assert 'tween_property' in script

    def test_timer_node(self, codegen, output_dir):
        scene = SceneNode('main')
        timer = TimerNode('spawn_timer')
        timer.interval = 2.0
        timer.action = 'on_spawn'
        scene.add_child(timer)
        sprite = SpriteNode('s1')
        sprite.src = 'a.png'
        scene.add_child(sprite)

        codegen.generate(scene, output_dir=output_dir)
        tscn = Path(output_dir, 'main.tscn').read_text(encoding='utf-8')
        assert 'Timer' in tscn
        assert 'spawn_timer' in tscn

        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'timeout.connect' in script
        assert 'on_spawn' in script


# ==========================================================================
# GodotCodeGenerator Tests - Particles
# ==========================================================================

class TestParticleGeneration:
    """Test particle generation."""

    def test_particle_node(self, codegen, output_dir):
        scene = SceneNode('main')
        particle = ParticleNode('dust')
        particle.count = 30
        particle.lifetime = 0.5
        scene.add_child(particle)
        sprite = SpriteNode('s1')
        sprite.src = 'a.png'
        scene.add_child(sprite)

        codegen.generate(scene, output_dir=output_dir)
        tscn = Path(output_dir, 'main.tscn').read_text(encoding='utf-8')
        assert 'GPUParticles2D' in tscn
        assert 'dust' in tscn


# ==========================================================================
# GodotCodeGenerator Tests - State Variables & Functions
# ==========================================================================

class TestStateAndFunctions:
    """Test state variable and function generation."""

    def test_state_variables(self, codegen, output_dir):
        scene = SceneNode('main')
        coins = SetNode('coins')
        coins.value = '0'
        scene.add_child(coins)
        lives = SetNode('lives')
        lives.value = '3'
        scene.add_child(lives)
        sprite = SpriteNode('s1')
        sprite.src = 'a.png'
        scene.add_child(sprite)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'var coins = 0' in script
        assert 'var lives = 3' in script

    def test_function_generation(self, codegen, output_dir):
        scene = SceneNode('main')
        func = FunctionNode('onCoinCollected')
        raw = RawCodeNode('coins += 1\nQuantumBridge.destroy_sprite(data.other_id)')
        func.body = [raw]
        scene.add_child(func)
        sprite = SpriteNode('s1')
        sprite.src = 'a.png'
        scene.add_child(sprite)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'func onCoinCollected' in script
        assert 'coins += 1' in script
        assert 'QuantumBridge.destroy_sprite' in script


# ==========================================================================
# GodotCodeGenerator Tests - Autoload Scripts
# ==========================================================================

class TestAutoloadScripts:
    """Test autoload script content."""

    def test_bridge_script_content(self, codegen, basic_scene, output_dir):
        codegen.generate(basic_scene, output_dir=output_dir)
        bridge = Path(output_dir, 'scripts', 'quantum_bridge.gd').read_text(encoding='utf-8')
        assert 'extends Node' in bridge
        assert 'var sprites: Dictionary' in bridge
        assert 'func destroy_sprite' in bridge
        assert 'func respawn' in bridge
        assert 'func emit_event' in bridge
        assert 'func play_sound' in bridge
        assert 'func pause' in bridge
        assert 'func resume' in bridge

    def test_event_bus_script_content(self, codegen, basic_scene, output_dir):
        codegen.generate(basic_scene, output_dir=output_dir)
        bus = Path(output_dir, 'scripts', 'quantum_event_bus.gd').read_text(encoding='utf-8')
        assert 'extends Node' in bus
        assert 'func emit_event' in bus
        assert 'func listen' in bus
        assert 'func remove_listener' in bus
        assert 'func clear' in bus


# ==========================================================================
# GodotCodeGenerator Tests - Scene Script
# ==========================================================================

class TestSceneScript:
    """Test scene_main.gd generation."""

    def test_registers_sprites_in_ready(self, codegen, output_dir):
        scene = SceneNode('main')
        sprite = SpriteNode('mario')
        sprite.src = 'mario.png'
        scene.add_child(sprite)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'QuantumBridge.register_sprite("mario"' in script


# ==========================================================================
# GameBuilder Engine Selection Tests
# ==========================================================================

class TestGameBuilderEngineSelection:
    """Test GameBuilder with engine parameter."""

    def test_default_engine_is_pixi(self):
        builder = GameBuilder()
        assert builder.engine == 'pixi'

    def test_godot_engine_selection(self):
        builder = GameBuilder(engine='godot')
        assert builder.engine == 'godot'

    def test_invalid_engine_raises(self):
        with pytest.raises(GameBuildError):
            GameBuilder(engine='unity')

    def test_valid_engines(self):
        assert 'pixi' in GameBuilder.VALID_ENGINES
        assert 'godot' in GameBuilder.VALID_ENGINES

    def test_godot_build_produces_directory(self, tmp_path):
        app = ApplicationNode('test_game', 'game')
        scene = SceneNode('main')
        sprite = SpriteNode('s1')
        sprite.src = 'test.png'
        scene.add_child(sprite)
        app.scenes = [scene]
        app.behaviors = []
        app.prefabs = []

        builder = GameBuilder(engine='godot')
        output = builder.build_to_file(app, str(tmp_path / 'godot_test'))
        assert Path(output).exists()
        assert (Path(output) / 'project.godot').exists()
        assert (Path(output) / 'main.tscn').exists()

    def test_pixi_build_produces_html(self, tmp_path):
        app = ApplicationNode('test_game', 'game')
        scene = SceneNode('main')
        sprite = SpriteNode('s1')
        sprite.src = 'test.png'
        scene.add_child(sprite)
        app.scenes = [scene]
        app.behaviors = []
        app.prefabs = []

        builder = GameBuilder(engine='pixi')
        output = builder.build_to_file(app, str(tmp_path / 'test.html'))
        assert Path(output).exists()
        assert output.endswith('.html')


# ==========================================================================
# GodotCodeGenerator Tests - Groups
# ==========================================================================

class TestGroupGeneration:
    """Test group node generation."""

    def test_group_with_children(self, codegen, output_dir):
        scene = SceneNode('main')
        group = GroupNode('enemies')
        group.tag = 'enemy'
        enemy1 = SpriteNode('rex1')
        enemy1.src = 'rex.png'
        enemy1.x = 100
        enemy1.y = 200
        group.add_child(enemy1)
        scene.add_child(group)

        codegen.generate(scene, output_dir=output_dir)
        tscn = Path(output_dir, 'main.tscn').read_text(encoding='utf-8')
        assert 'rex1' in tscn


# ==========================================================================
# GodotCodeGenerator Tests - Complete Scene
# ==========================================================================

class TestCompleteScene:
    """Test generation of a complete game scene with multiple features."""

    def test_mario_like_scene(self, codegen, output_dir):
        """Test a scene similar to a Mario game."""
        scene = SceneNode('yoshi_island_1')
        scene.width = 4096
        scene.height = 512
        scene.background = '#5c94fc'

        # Physics
        physics = PhysicsNode()
        physics.gravity_y = 1.5
        scene.add_child(physics)

        # State
        coins = SetNode('coins')
        coins.value = '0'
        scene.add_child(coins)

        # Player
        mario = SpriteNode('mario')
        mario.src = 'mario.png'
        mario.x = 50
        mario.y = 400
        mario.body = 'dynamic'
        mario.controls = 'arrows'
        mario.speed = 1.5
        mario.jump_force = 5.3
        mario.tag = 'player'
        mario.width = 16
        mario.height = 24
        scene.add_child(mario)

        # Camera
        camera = CameraNode()
        camera.follow = 'mario'
        camera.lerp = 0.1
        camera.bounds = 'scene'
        scene.add_child(camera)

        # Tilemap
        tilemap = TilemapNode('world')
        tilemap.src = 'smw_tileset.png'
        tilemap.tile_width = 16
        tilemap.tile_height = 16

        ground = TilemapLayerNode('ground')
        ground.data = '0,0,0,0\n1,1,1,1'
        ground.collision = True
        tilemap.add_layer(ground)
        scene.add_child(tilemap)

        # Sound
        jump_sfx = SoundNode('sfx-jump')
        jump_sfx.src = 'jump.wav'
        scene.add_child(jump_sfx)

        # Event
        event = EventNode('coinCollected', 'onCoinCollected')
        scene.add_child(event)

        # Function
        func = FunctionNode('onCoinCollected')
        func.body = [RawCodeNode('coins += 1')]
        scene.add_child(func)

        # HUD
        hud = HudNode()
        hud.position = 'top-left'
        label = HTMLNode('span')
        label.attributes = {'id': 'coin_counter'}
        label.children = [TextNode('Coins: 0')]
        hud.add_child(label)
        scene.add_child(hud)

        result = codegen.generate(scene, output_dir=output_dir, project_name='MarioSMW')
        out = Path(result)

        # Verify all files exist
        assert (out / 'project.godot').exists()
        assert (out / 'main.tscn').exists()
        assert (out / 'scripts' / 'quantum_bridge.gd').exists()
        assert (out / 'scripts' / 'quantum_event_bus.gd').exists()
        assert (out / 'scripts' / 'scene_main.gd').exists()
        assert (out / 'scripts' / 'player_controller.gd').exists()
        assert (out / 'scripts' / 'camera_follow.gd').exists()
        assert (out / 'scripts' / 'hud_manager.gd').exists()
        assert (out / 'export_presets.cfg').exists()

        # Verify project.godot
        project = (out / 'project.godot').read_text(encoding='utf-8')
        assert 'config/name="MarioSMW"' in project
        assert 'move_left=' in project
        assert 'jump=' in project
        assert 'QuantumBridge' in project
        assert 'QuantumEventBus' in project

        # Verify main.tscn
        tscn = (out / 'main.tscn').read_text(encoding='utf-8')
        assert 'CharacterBody2D' in tscn
        assert 'Camera2D' in tscn
        assert 'TileMapLayer' in tscn
        assert 'AudioStreamPlayer' in tscn
        assert 'CanvasLayer' in tscn

        # Verify scene_main.gd
        script = (out / 'scripts' / 'scene_main.gd').read_text(encoding='utf-8')
        assert 'var coins = 0' in script
        assert 'QuantumBridge.register_sprite' in script
        assert 'QuantumEventBus.listen("coinCollected"' in script
        assert 'func onCoinCollected' in script
        assert '_setup_tilemaps' in script


# ==========================================================================
# Edge Cases
# ==========================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_scene(self, codegen, output_dir):
        scene = SceneNode('empty')
        codegen.generate(scene, output_dir=output_dir)
        assert Path(output_dir, 'project.godot').exists()
        assert Path(output_dir, 'main.tscn').exists()

    def test_scene_with_only_physics(self, codegen, output_dir):
        scene = SceneNode('main')
        physics = PhysicsNode()
        physics.gravity_y = 2.0  # Quantum value — Godot uses SNES constant
        scene.add_child(physics)
        codegen.generate(scene, output_dir=output_dir)
        project = Path(output_dir, 'project.godot').read_text(encoding='utf-8')
        # Uses SNES SMW gravity regardless of .q value
        assert '750.0' in project

    def test_no_player_no_controller(self, codegen, output_dir):
        """If no sprite has controls, no player_controller.gd should be written."""
        scene = SceneNode('main')
        sprite = SpriteNode('bg')
        sprite.src = 'bg.png'
        scene.add_child(sprite)
        codegen.generate(scene, output_dir=output_dir)
        assert not Path(output_dir, 'scripts', 'player_controller.gd').exists()

    def test_no_camera_no_script(self, codegen, output_dir):
        scene = SceneNode('main')
        sprite = SpriteNode('s1')
        sprite.src = 'a.png'
        scene.add_child(sprite)
        codegen.generate(scene, output_dir=output_dir)
        assert not Path(output_dir, 'scripts', 'camera_follow.gd').exists()

    def test_multi_scene(self, codegen, output_dir):
        scene1 = SceneNode('level1')
        scene1.width = 800
        scene1.height = 600
        s1 = SpriteNode('s1')
        s1.src = 'a.png'
        scene1.add_child(s1)

        scene2 = SceneNode('level2')
        scene2.width = 1600
        scene2.height = 600

        result = codegen.generate_multi(
            [scene1, scene2], initial='level1', output_dir=output_dir
        )
        assert Path(result, 'project.godot').exists()


# ==========================================================================
# Tile-Based HUD Tests
# ==========================================================================

class TestTileBasedHud:
    """Test tile-based HUD code generation."""

    def _make_tile_hud_scene(self):
        """Helper: create a scene with tile-based HUD."""
        scene = SceneNode('main')
        scene.width = 256
        scene.height = 224
        scene.viewport_width = 256
        scene.viewport_height = 224

        hud = HudNode()
        hud.background = 'rgba(0,0,0,0.55)'
        hud.background_height = 26
        hud.sprite_prefix = 'assets/smw/sprites/hud_'

        tile = HudTileNode()
        tile.sprite = 'mario_text.png'
        tile.x = 24
        tile.y = 8
        hud.add_child(tile)

        counter = HudCounterNode()
        counter.strip = 'numbers_small.png'
        counter.x = 96
        counter.y = 8
        counter.digits = 2
        counter.bind = '{coins}'
        hud.add_child(counter)

        time_counter = HudCounterNode()
        time_counter.strip = 'numbers_small.png'
        time_counter.x = 192
        time_counter.y = 16
        time_counter.digits = 3
        time_counter.bind = '{time_left}'
        time_counter.countdown = True
        time_counter.hurry_at = 100
        time_counter.flash = 'red'
        hud.add_child(time_counter)

        col = HudCollectionNode()
        col.sprite = 'coin_icon.png'
        col.x = 148
        col.y = 8
        col.spacing = 8
        col.max = 5
        col.bind = '{yoshi_coins}'
        hud.add_child(col)

        scene.add_child(hud)

        # Need at least one sprite for scene to be valid
        s = SpriteNode('p')
        s.src = 'p.png'
        scene.add_child(s)
        return scene

    def test_tile_hud_generates_script(self, codegen, output_dir):
        """Test that tile-based HUD generates hud_manager.gd."""
        scene = self._make_tile_hud_scene()
        codegen.generate(scene, output_dir=output_dir)
        hud_path = Path(output_dir, 'scripts', 'hud_manager.gd')
        assert hud_path.exists()

    def test_tile_hud_script_has_textures(self, codegen, output_dir):
        """Test generated script loads textures."""
        scene = self._make_tile_hud_scene()
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'hud_manager.gd').read_text(encoding='utf-8')
        assert 'Texture2D' in script
        assert 'load("res://' in script

    def test_tile_hud_countdown_process(self, codegen, output_dir):
        """Test countdown logic in _process."""
        scene = self._make_tile_hud_scene()
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'hud_manager.gd').read_text(encoding='utf-8')
        assert '_countdown_active' in script
        assert '_countdown_timer += delta' in script
        assert 'time_left = max(0, time_left - 1)' in script

    def test_tile_hud_collection_for_loop(self, codegen, output_dir):
        """Test collection renders with for loop."""
        scene = self._make_tile_hud_scene()
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'hud_manager.gd').read_text(encoding='utf-8')
        assert 'for i in range(yoshi_coins)' in script

    def test_tile_hud_flash_tinted(self, codegen, output_dir):
        """Test hurry-mode flash uses tinted draw."""
        scene = self._make_tile_hud_scene()
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'hud_manager.gd').read_text(encoding='utf-8')
        assert '_draw_number_tinted' in script
        assert '_hurry_mode' in script
        assert 'Color(1, 0.2, 0.2, 1)' in script  # Red flash

    def test_tile_hud_sprite_prefix_resolution(self, codegen, output_dir):
        """Test sprite-prefix resolves short names."""
        scene = self._make_tile_hud_scene()
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'hud_manager.gd').read_text(encoding='utf-8')
        # Sprite prefix should be applied: mario_text.png -> assets/smw/sprites/hud_mario_text.png
        assert 'assets/smw/sprites/hud_mario_text.png' in script

    def test_tile_hud_course_clear(self, codegen, output_dir):
        """Test course clear overlay function exists."""
        scene = self._make_tile_hud_scene()
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'hud_manager.gd').read_text(encoding='utf-8')
        assert 'func _draw_course_clear' in script
        assert 'func show_course_clear' in script

    def test_html_hud_backward_compat(self, codegen, output_dir):
        """Test HTML-based HUD still works (backward compat)."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600
        hud = HudNode()
        hud.position = 'top-left'
        label = HTMLNode('span')
        label.attributes = {'id': 'score'}
        label.children = [TextNode('Score: 0')]
        hud.add_child(label)
        scene.add_child(hud)

        s = SpriteNode('p')
        s.src = 'p.png'
        scene.add_child(s)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'hud_manager.gd').read_text(encoding='utf-8')
        # Should use legacy template, not tile-based
        assert '@onready var score_label' in script

    def test_tile_hud_slot_match(self, codegen, output_dir):
        """Test slot generates match block."""
        scene = SceneNode('main')
        scene.width = 256
        scene.height = 224

        hud = HudNode()
        hud.background = 'rgba(0,0,0,0.5)'

        # Add a counter so _draw_number is generated
        counter = HudCounterNode()
        counter.strip = 'numbers.png'
        counter.x = 0
        counter.y = 0
        counter.digits = 1
        counter.bind = '{score}'
        hud.add_child(counter)

        slot = HudSlotNode()
        slot.x = 112
        slot.y = 0
        slot.bind = '{powerup}'
        opt1 = HudOptionNode()
        opt1.value = 'mushroom'
        opt1.sprite = 'assets/mushroom.png'
        slot.add_option(opt1)
        opt2 = HudOptionNode()
        opt2.value = 'flower'
        opt2.sprite = 'assets/flower.png'
        slot.add_option(opt2)
        hud.add_child(slot)
        scene.add_child(hud)

        s = SpriteNode('p')
        s.src = 'p.png'
        scene.add_child(s)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'hud_manager.gd').read_text(encoding='utf-8')
        assert 'powerup == "mushroom"' in script
        assert 'powerup == "flower"' in script


class TestMultiSceneCodegen:
    """Test multi-scene Godot code generation."""

    def test_generate_multi_creates_scenes_dir(self, output_dir, codegen):
        """Multi-scene generates scenes/ directory with per-scene files."""
        title = SceneNode('title')
        title.scene_type = 'title'
        title.initial = True
        title.width = 256
        title.height = 224
        s1 = SpriteNode('bg')
        s1.src = 'title.png'
        title.add_child(s1)

        level = SceneNode('level-1')
        level.scene_type = 'level'
        level.width = 5120
        level.height = 432
        s2 = SpriteNode('player')
        s2.src = 'mario.png'
        s2.body = 'dynamic'
        s2.controls = 'arrows'
        level.add_child(s2)

        codegen.generate_multi(
            scenes=[title, level],
            initial='title',
            output_dir=output_dir,
            project_name='TestGame',
        )

        scenes_dir = Path(output_dir, 'scenes')
        assert scenes_dir.exists()
        assert (scenes_dir / 'title.tscn').exists()
        assert (scenes_dir / 'level_1.tscn').exists()

    def test_generate_multi_creates_per_scene_scripts(self, output_dir, codegen):
        """Each scene gets its own script in scripts/."""
        title = SceneNode('title')
        title.initial = True
        s1 = SpriteNode('bg')
        s1.src = 'bg.png'
        title.add_child(s1)

        level = SceneNode('level-1')
        s2 = SpriteNode('p')
        s2.src = 'p.png'
        level.add_child(s2)

        codegen.generate_multi(
            scenes=[title, level],
            initial='title',
            output_dir=output_dir,
        )

        scripts_dir = Path(output_dir, 'scripts')
        assert (scripts_dir / 'scene_title.gd').exists()
        assert (scripts_dir / 'scene_level_1.gd').exists()

    def test_generate_multi_scene_manager_autoload(self, output_dir, codegen):
        """SceneManager autoload is generated and registered."""
        s1 = SceneNode('scene-a')
        s1.initial = True
        sp1 = SpriteNode('a')
        sp1.src = 'a.png'
        s1.add_child(sp1)

        s2 = SceneNode('scene-b')
        sp2 = SpriteNode('b')
        sp2.src = 'b.png'
        s2.add_child(sp2)

        codegen.generate_multi(
            scenes=[s1, s2],
            initial='scene-a',
            output_dir=output_dir,
        )

        # SceneManager script exists
        sm_path = Path(output_dir, 'scripts', 'scene_manager.gd')
        assert sm_path.exists()
        sm_content = sm_path.read_text(encoding='utf-8')
        assert 'func transition_to' in sm_content
        assert 'persistent_state' in sm_content
        assert 'func set_state' in sm_content
        assert 'func get_state' in sm_content

        # project.godot has SceneManager autoload
        proj = Path(output_dir, 'project.godot').read_text(encoding='utf-8')
        assert 'SceneManager' in proj
        assert 'scene_manager.gd' in proj

    def test_generate_multi_project_godot_main_scene(self, output_dir, codegen):
        """project.godot points to initial scene in scenes/ directory."""
        title = SceneNode('title')
        title.initial = True
        sp = SpriteNode('bg')
        sp.src = 'bg.png'
        title.add_child(sp)

        level = SceneNode('level')
        sp2 = SpriteNode('p')
        sp2.src = 'p.png'
        level.add_child(sp2)

        codegen.generate_multi(
            scenes=[title, level],
            initial='title',
            output_dir=output_dir,
        )

        proj = Path(output_dir, 'project.godot').read_text(encoding='utf-8')
        assert 'scenes/title.tscn' in proj

    def test_generate_multi_scene_script_sets_current_scene(self, output_dir, codegen):
        """Scene scripts set SceneManager.current_scene_name in _ready()."""
        s1 = SceneNode('title')
        s1.initial = True
        sp1 = SpriteNode('bg')
        sp1.src = 'bg.png'
        s1.add_child(sp1)

        s2 = SceneNode('level-1')
        sp2 = SpriteNode('p')
        sp2.src = 'p.png'
        s2.add_child(sp2)

        codegen.generate_multi(
            scenes=[s1, s2],
            initial='title',
            output_dir=output_dir,
        )

        title_script = Path(output_dir, 'scripts', 'scene_title.gd').read_text(encoding='utf-8')
        assert 'SceneManager.current_scene_name = "title"' in title_script

        level_script = Path(output_dir, 'scripts', 'scene_level_1.gd').read_text(encoding='utf-8')
        assert 'SceneManager.current_scene_name = "level-1"' in level_script

    def test_generate_multi_with_transitions(self, output_dir, codegen):
        """Events with SceneTransitionNode generate SceneManager.transition_to calls."""
        title = SceneNode('title')
        title.initial = True
        sp = SpriteNode('bg')
        sp.src = 'bg.png'
        title.add_child(sp)

        # Event with transition
        evt = EventNode('press-start', '')
        tr = SceneTransitionNode('level-1')
        tr.effect = 'fade'
        tr.duration = 0.5
        evt.children = [tr]
        title.add_child(evt)

        level = SceneNode('level-1')
        sp2 = SpriteNode('p')
        sp2.src = 'p.png'
        level.add_child(sp2)

        codegen.generate_multi(
            scenes=[title, level],
            initial='title',
            output_dir=output_dir,
        )

        script = Path(output_dir, 'scripts', 'scene_title.gd').read_text(encoding='utf-8')
        assert 'SceneManager.transition_to("level-1"' in script

    def test_generate_multi_with_persistent_state(self, output_dir, codegen):
        """Persistent state is initialized in SceneManager."""
        s1 = SceneNode('title')
        s1.initial = True
        sp = SpriteNode('bg')
        sp.src = 'bg.png'
        s1.add_child(sp)

        s2 = SceneNode('level')
        sp2 = SpriteNode('p')
        sp2.src = 'p.png'
        s2.add_child(sp2)

        # Create persistent nodes
        persistent = PersistentNode()
        lives = SetNode('lives')
        lives.value = '5'
        lives.type = 'integer'
        persistent.add_child(lives)
        score = SetNode('score')
        score.value = '0'
        score.type = 'integer'
        persistent.add_child(score)

        codegen.generate_multi(
            scenes=[s1, s2],
            initial='title',
            persistent=[persistent],
            output_dir=output_dir,
        )

        sm = Path(output_dir, 'scripts', 'scene_manager.gd').read_text(encoding='utf-8')
        assert 'persistent_state["lives"] = 5' in sm
        assert 'persistent_state["score"] = 0' in sm

    def test_generate_multi_single_scene_fallback(self, output_dir, codegen):
        """Single scene in generate_multi uses regular generate (backward compat)."""
        scene = SceneNode('main')
        sp = SpriteNode('p')
        sp.src = 'p.png'
        scene.add_child(sp)

        codegen.generate_multi(
            scenes=[scene],
            initial='main',
            output_dir=output_dir,
        )

        # Should use single-scene layout (main.tscn at root, not in scenes/)
        assert Path(output_dir, 'main.tscn').exists()
        assert not Path(output_dir, 'scenes').exists()

    def test_generate_multi_initial_scene_detection(self, output_dir, codegen):
        """Initial scene is detected from scene.initial attribute."""
        s1 = SceneNode('level')
        sp1 = SpriteNode('p')
        sp1.src = 'p.png'
        s1.add_child(sp1)

        s2 = SceneNode('title')
        s2.initial = True
        sp2 = SpriteNode('bg')
        sp2.src = 'bg.png'
        s2.add_child(sp2)

        codegen.generate_multi(
            scenes=[s1, s2],
            initial='level',  # explicit initial
            output_dir=output_dir,
        )

        proj = Path(output_dir, 'project.godot').read_text(encoding='utf-8')
        # initial=True on s2 takes precedence
        assert 'scenes/title.tscn' in proj


class TestMapSceneCodegen:
    """Test world map scene code generation."""

    def test_map_scene_generates_map_controller(self, output_dir, codegen):
        """Map scenes generate a script with map navigation logic."""
        title = SceneNode('title')
        title.initial = True
        sp = SpriteNode('bg')
        sp.src = 'bg.png'
        title.add_child(sp)

        world_map = SceneNode('world-map')
        world_map.scene_type = 'map'
        bg = SpriteNode('map-bg')
        bg.src = 'map.png'
        world_map.add_child(bg)
        mario = SpriteNode('Mario')
        mario.src = 'mario_map.png'
        mario.x = 32
        mario.y = 180
        world_map.add_child(mario)

        # Map nodes
        start = MapNodeDef('start')
        start.x = 32
        start.y = 180
        world_map.add_child(start)

        level1 = MapNodeDef('level-1')
        level1.x = 80
        level1.y = 180
        level1.scene = 'level-1'
        world_map.add_child(level1)

        level2 = MapNodeDef('level-2')
        level2.x = 128
        level2.y = 160
        level2.scene = 'level-2'
        level2.locked = True
        world_map.add_child(level2)

        # Map paths
        path1 = MapPathNode('start', 'level-1')
        world_map.add_child(path1)

        path2 = MapPathNode('level-1', 'level-2')
        path2.unlock = 'level-1-cleared'
        world_map.add_child(path2)

        codegen.generate_multi(
            scenes=[title, world_map],
            initial='title',
            output_dir=output_dir,
        )

        script_path = Path(output_dir, 'scripts', 'scene_world_map.gd')
        assert script_path.exists()
        script = script_path.read_text(encoding='utf-8')

        # Map data should be embedded
        assert 'map_nodes' in script
        assert '"start"' in script
        assert '"level-1"' in script
        assert '"level-2"' in script

        # Navigation functions should exist
        assert '_enter_node' in script
        assert '_try_move' in script
        assert '_move_to' in script
        assert '_get_neighbors' in script
        assert '_get_node_pos' in script

        # Map paths should be embedded
        assert 'map_paths' in script
        assert '"from": "start"' in script
        assert '"to": "level-1"' in script
        assert '"unlock": "level-1-cleared"' in script

    def test_map_scene_has_transition_to(self, output_dir, codegen):
        """Map controller enters levels via SceneManager.transition_to."""
        title = SceneNode('title')
        title.initial = True
        sp = SpriteNode('bg')
        sp.src = 'bg.png'
        title.add_child(sp)

        world_map = SceneNode('world-map')
        world_map.scene_type = 'map'
        bg = SpriteNode('map-bg')
        bg.src = 'map.png'
        world_map.add_child(bg)

        start = MapNodeDef('start')
        start.x = 32
        start.y = 180
        world_map.add_child(start)

        level1 = MapNodeDef('level-1')
        level1.x = 80
        level1.y = 180
        level1.scene = 'level-1'
        world_map.add_child(level1)

        path1 = MapPathNode('start', 'level-1')
        world_map.add_child(path1)

        codegen.generate_multi(
            scenes=[title, world_map],
            initial='title',
            output_dir=output_dir,
        )

        script = Path(output_dir, 'scripts', 'scene_world_map.gd').read_text(encoding='utf-8')
        assert 'SceneManager.transition_to(scene_name' in script

    def test_map_scene_locked_nodes(self, output_dir, codegen):
        """Locked nodes should have locked=true in map data."""
        title = SceneNode('title')
        title.initial = True
        sp = SpriteNode('bg')
        sp.src = 'bg.png'
        title.add_child(sp)

        world_map = SceneNode('world-map')
        world_map.scene_type = 'map'
        bg = SpriteNode('map-bg')
        bg.src = 'map.png'
        world_map.add_child(bg)

        locked_node = MapNodeDef('castle')
        locked_node.x = 200
        locked_node.y = 140
        locked_node.scene = 'castle'
        locked_node.locked = True
        world_map.add_child(locked_node)

        codegen.generate_multi(
            scenes=[title, world_map],
            initial='title',
            output_dir=output_dir,
        )

        script = Path(output_dir, 'scripts', 'scene_world_map.gd').read_text(encoding='utf-8')
        assert '"locked": true' in script

    def test_map_scene_sets_current_scene_name(self, output_dir, codegen):
        """Map scene script sets SceneManager.current_scene_name."""
        title = SceneNode('title')
        title.initial = True
        sp = SpriteNode('bg')
        sp.src = 'bg.png'
        title.add_child(sp)

        world_map = SceneNode('world-map')
        world_map.scene_type = 'map'
        bg = SpriteNode('bg')
        bg.src = 'bg.png'
        world_map.add_child(bg)

        start = MapNodeDef('start')
        start.x = 0
        start.y = 0
        world_map.add_child(start)

        codegen.generate_multi(
            scenes=[title, world_map],
            initial='title',
            output_dir=output_dir,
        )

        script = Path(output_dir, 'scripts', 'scene_world_map.gd').read_text(encoding='utf-8')
        assert 'SceneManager.current_scene_name = "world-map"' in script


# ==========================================================================
# Phase 1: Player Controller Parity Tests
# ==========================================================================

class TestPlayerControllerParity:
    """Test that player controller uses sprite-level physics attrs."""

    def test_player_uses_sprite_gravity(self, codegen, output_dir):
        """Player controller should use gravity_up/gravity_down from sprite."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600
        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.body = 'dynamic'
        player.controls = 'arrows'
        player.gravity_up = 600.0
        player.gravity_down = 1050.0
        player.jump_hold_boost = 50.0
        player.max_fall_speed = 240.0
        player.coyote_frames = 6
        scene.add_child(player)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'player_controller.gd').read_text(encoding='utf-8')
        assert 'gravity_up: float = 600.0' in script
        assert 'gravity_down: float = 1050.0' in script
        assert 'jump_hold_boost: float = 50.0' in script
        assert 'max_fall_speed: float = 240.0' in script

    def test_player_collision_layer_and_mask(self, codegen, output_dir):
        """Player controller should set collision_layer and collision_mask."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600
        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.body = 'dynamic'
        player.controls = 'arrows'
        player.collision_layer = 2
        player.collision_mask = 5
        scene.add_child(player)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'player_controller.gd').read_text(encoding='utf-8')
        assert 'collision_layer = 2' in script
        assert 'collision_mask = 5' in script

    def test_player_floor_max_angle(self, codegen, output_dir):
        """Player controller should set floor_max_angle from sprite."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600
        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.body = 'dynamic'
        player.controls = 'arrows'
        player.floor_max_angle = 70.0
        scene.add_child(player)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'player_controller.gd').read_text(encoding='utf-8')
        assert 'floor_max_angle = deg_to_rad(70.0)' in script

    def test_player_defaults_without_collision_attrs(self, codegen, output_dir):
        """Without collision attrs, defaults to layer=1 mask=1 angle=45."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600
        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.body = 'dynamic'
        player.controls = 'arrows'
        scene.add_child(player)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'player_controller.gd').read_text(encoding='utf-8')
        assert 'collision_layer = 1' in script
        assert 'collision_mask = 1' in script
        assert 'floor_max_angle = deg_to_rad(45.0)' in script

    def test_player_process_mode_in_die(self, codegen, output_dir):
        """die() should set process_mode = PROCESS_MODE_ALWAYS."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600
        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.body = 'dynamic'
        player.controls = 'arrows'
        scene.add_child(player)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'player_controller.gd').read_text(encoding='utf-8')
        assert 'process_mode = Node.PROCESS_MODE_ALWAYS' in script

    def test_player_qblock_detection(self, codegen, output_dir):
        """Player controller should detect qblock and rotating_block collisions."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600
        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.body = 'dynamic'
        player.controls = 'arrows'
        scene.add_child(player)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'player_controller.gd').read_text(encoding='utf-8')
        assert 'qblock-hit' in script
        assert 'rotating-block-hit' in script


# ==========================================================================
# Phase 2: Enemy Prefab Parity Tests
# ==========================================================================

class TestEnemyPrefabParity:
    """Test enemy prefab script generation with full semantics."""

    def _make_enemy_scene(self, prefab):
        """Helper: create a scene with a prefab + instance."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600
        scene.add_child(prefab)
        inst = InstanceNode(prefab.name)
        inst.x = 100
        inst.y = 200
        scene.add_child(inst)
        return scene

    def test_prefab_uses_move_speed_directly(self, codegen, output_dir):
        """move_speed >= 10 should be used as-is (px/s)."""
        prefab = PrefabNode('rex')
        prefab.entity_type = 'enemy'
        prefab.movement = 'patrol'
        prefab.move_speed = 30.0
        sprite = SpriteNode('rex_body')
        sprite.src = 'rex.png'
        sprite.tag = 'enemy'
        sprite.body = 'dynamic'
        prefab.add_child(sprite)

        scene = self._make_enemy_scene(prefab)
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_rex.gd').read_text(encoding='utf-8')
        assert 'patrol_speed: float = 30.0' in script

    def test_prefab_turn_cooldown(self, codegen, output_dir):
        """turn_cooldown should generate anti-oscillation timer."""
        prefab = PrefabNode('rex')
        prefab.entity_type = 'enemy'
        prefab.movement = 'patrol'
        prefab.move_speed = 30.0
        prefab.turn_cooldown = 0.15
        sprite = SpriteNode('rex_body')
        sprite.src = 'rex.png'
        sprite.tag = 'enemy'
        sprite.body = 'dynamic'
        prefab.add_child(sprite)

        scene = self._make_enemy_scene(prefab)
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_rex.gd').read_text(encoding='utf-8')
        assert '_turn_cooldown' in script
        assert '_turn_timer' in script
        assert '0.15' in script
        assert '_turn_timer <= 0' in script

    def test_prefab_squish_mechanic(self, codegen, output_dir):
        """health >= 2 + defeated_by=stomp should generate squish."""
        prefab = PrefabNode('rex')
        prefab.entity_type = 'enemy'
        prefab.movement = 'patrol'
        prefab.move_speed = 30.0
        prefab.health = 2
        prefab.defeated_by = 'stomp'
        prefab.stomp_bounce = -200
        prefab.reward = 'score:100'
        prefab.reward_kill = 'score:200'
        sprite = SpriteNode('rex_body')
        sprite.src = 'rex.png'
        sprite.tag = 'enemy'
        sprite.body = 'dynamic'
        prefab.add_child(sprite)

        scene = self._make_enemy_scene(prefab)
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_rex.gd').read_text(encoding='utf-8')
        assert '_health' in script
        assert '_is_squished' in script
        assert 'func stomp()' in script
        assert 'scale.y = 0.5' in script
        assert 'enemy-stomped' in script
        assert 'enemy-killed' in script
        assert '200' in script

    def test_prefab_collision_layers_from_child_sprite(self, codegen, output_dir):
        """Prefab should read collision_layer/mask from its child sprite."""
        prefab = PrefabNode('rex')
        prefab.entity_type = 'enemy'
        prefab.movement = 'patrol'
        prefab.move_speed = 30.0
        sprite = SpriteNode('rex_body')
        sprite.src = 'rex.png'
        sprite.tag = 'enemy'
        sprite.body = 'dynamic'
        sprite.collision_layer = 4
        sprite.collision_mask = 3
        prefab.add_child(sprite)

        scene = self._make_enemy_scene(prefab)
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_rex.gd').read_text(encoding='utf-8')
        assert 'collision_layer = 4' in script
        assert 'collision_mask = 3' in script

    def test_prefab_die_emits_event(self, codegen, output_dir):
        """die() should emit enemy-killed event."""
        prefab = PrefabNode('goomba')
        prefab.entity_type = 'enemy'
        prefab.movement = 'patrol'
        sprite = SpriteNode('g_body')
        sprite.src = 'goomba.png'
        sprite.tag = 'enemy'
        sprite.body = 'dynamic'
        prefab.add_child(sprite)

        scene = self._make_enemy_scene(prefab)
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_goomba.gd').read_text(encoding='utf-8')
        assert 'func die()' in script
        assert 'enemy-killed' in script

    def test_prefab_no_squish_without_stomp(self, codegen, output_dir):
        """health >= 2 but no defeated_by=stomp -> no squish."""
        prefab = PrefabNode('buzzy')
        prefab.entity_type = 'enemy'
        prefab.movement = 'patrol'
        prefab.health = 3
        prefab.defeated_by = 'fire'
        sprite = SpriteNode('b_body')
        sprite.src = 'buzzy.png'
        sprite.tag = 'enemy'
        sprite.body = 'dynamic'
        prefab.add_child(sprite)

        scene = self._make_enemy_scene(prefab)
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_buzzy.gd').read_text(encoding='utf-8')
        assert '_is_squished' not in script
        assert 'func stomp()' not in script


# ==========================================================================
# Phase 3: Scene Events & Death Sequence Tests
# ==========================================================================

class TestSceneEventsParity:
    """Test semantic scene script generation."""

    def _make_level_scene(self, death_sequence=None, death_timer=3.0):
        """Helper: create a scene with player + enemy prefab."""
        scene = SceneNode('level-1')
        scene.width = 800
        scene.height = 600
        if death_sequence:
            scene.death_sequence = death_sequence
            scene.death_timer = death_timer
        # Player
        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.body = 'dynamic'
        player.controls = 'arrows'
        scene.add_child(player)
        # Enemy prefab
        prefab = PrefabNode('rex')
        prefab.entity_type = 'enemy'
        prefab.movement = 'patrol'
        prefab.defeated_by = 'stomp'
        prefab.health = 2
        prefab.stomp_bounce = -200
        prefab.reward = 'score:100'
        sprite = SpriteNode('rex_body')
        sprite.src = 'rex.png'
        sprite.tag = 'enemy'
        sprite.body = 'dynamic'
        prefab.add_child(sprite)
        scene.add_child(prefab)
        # Instance
        inst = InstanceNode('rex')
        inst.x = 200
        inst.y = 300
        scene.add_child(inst)
        return scene

    def test_stomp_detection_generated(self, codegen, output_dir):
        """Scene with stomp enemies should auto-generate two-stage stomp handler."""
        scene = self._make_level_scene()
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert '_on_enemy_collision' in script
        assert 'normal_y < -0.5' in script
        # Two-stage stomp: squish first, kill on second
        assert 'rex_squished' in script
        assert 'destroy_sprite' in script
        assert 'score += 100' in script
        assert 'score += 200' in script

    def test_stomp_bounce_player(self, codegen, output_dir):
        """After stomp, player should bounce."""
        scene = self._make_level_scene()
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'velocity.y = -200' in script

    def test_death_sequence_smw(self, codegen, output_dir):
        """death-sequence=smw should generate kill_player + death_complete."""
        scene = self._make_level_scene(death_sequence='smw', death_timer=3.5)
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'func _kill_player()' in script
        assert '_is_dead' in script
        assert 'QuantumBridge.kill_player(' in script
        assert 'get_tree().paused = true' in script
        assert 'Timer.new()' in script
        assert '_on_death_complete' in script
        assert 'get_tree().reload_current_scene()' in script

    def test_death_sequence_instant(self, codegen, output_dir):
        """death-sequence=instant should reload immediately."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600
        scene.death_sequence = 'instant'
        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.body = 'dynamic'
        player.controls = 'arrows'
        scene.add_child(player)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'func _kill_player()' in script
        assert 'reload_current_scene()' in script

    def test_death_sequence_respawn(self, codegen, output_dir):
        """death-sequence=respawn should respawn player at origin."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600
        scene.death_sequence = 'respawn'
        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.body = 'dynamic'
        player.controls = 'arrows'
        scene.add_child(player)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'QuantumBridge.respawn("mario"' in script

    def test_no_death_sequence_no_kill_player(self, codegen, output_dir):
        """Without death-sequence, no _kill_player function."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600
        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.body = 'dynamic'
        player.controls = 'arrows'
        scene.add_child(player)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert '_kill_player' not in script

    def test_event_actions_score(self, codegen, output_dir):
        """Event with score action should generate score event emission."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600
        player = SpriteNode('p')
        player.src = 'p.png'
        scene.add_child(player)

        evt = EventNode('coin-collected', '')
        action1 = EventActionNode()
        action1.action_type = 'score'
        action1.amount = 10
        evt.children.append(action1)
        action2 = EventActionNode()
        action2.action_type = 'sound'
        action2.target = 'sfx-coin'
        evt.children.append(action2)
        scene.add_child(evt)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert '_on_coin_collected' in script
        assert 'score-changed' in script
        assert '"amount": 10' in script
        assert 'play_sound("sfx-coin")' in script

    def test_event_actions_destroy(self, codegen, output_dir):
        """Event with destroy action targeting data.other."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600
        player = SpriteNode('p')
        player.src = 'p.png'
        scene.add_child(player)

        evt = EventNode('item-collected', '')
        action = EventActionNode()
        action.action_type = 'destroy'
        action.target = '{data.other}'
        evt.children.append(action)
        scene.add_child(evt)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert '_on_item_collected' in script
        assert 'queue_free()' in script

    def test_event_actions_camera_shake(self, codegen, output_dir):
        """Event with camera-shake action."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600
        player = SpriteNode('p')
        player.src = 'p.png'
        scene.add_child(player)

        evt = EventNode('big-explosion', '')
        action = EventActionNode()
        action.action_type = 'camera-shake'
        action.value = '5.0,0.3'
        evt.children.append(action)
        scene.add_child(evt)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'camera_shake(5.0, 0.3)' in script

    def test_event_actions_set(self, codegen, output_dir):
        """Event with set action."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600
        player = SpriteNode('p')
        player.src = 'p.png'
        scene.add_child(player)

        evt = EventNode('power-up', '')
        action = EventActionNode()
        action.action_type = 'set'
        action.target = 'coins'
        action.value = '{coins+1}'
        evt.children.append(action)
        scene.add_child(evt)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'coins = coins+1' in script

    def test_event_actions_emit(self, codegen, output_dir):
        """Event with emit action."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600
        player = SpriteNode('p')
        player.src = 'p.png'
        scene.add_child(player)

        evt = EventNode('chain-event', '')
        action = EventActionNode()
        action.action_type = 'emit'
        action.value = 'score-updated'
        evt.children.append(action)
        scene.add_child(evt)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'emit_event("score-updated"' in script

    def test_explicit_handler_not_auto_generated(self, codegen, output_dir):
        """Event with explicit handler should NOT auto-generate action handler."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600
        player = SpriteNode('p')
        player.src = 'p.png'
        scene.add_child(player)

        evt = EventNode('custom-event', 'onCustom')
        scene.add_child(evt)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'Callable(self, "onCustom")' in script
        assert '_on_custom_event' not in script

    def test_no_stomp_without_stomp_enemies(self, codegen, output_dir):
        """Scene without stomp enemies should not generate stomp handler."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600
        player = SpriteNode('p')
        player.src = 'p.png'
        player.body = 'dynamic'
        player.controls = 'arrows'
        scene.add_child(player)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert '_on_enemy_collision' not in script

    def test_quantum_bridge_save_load_state(self, codegen, output_dir):
        """QuantumBridge should have save_state/load_state methods."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600
        player = SpriteNode('p')
        player.src = 'p.png'
        scene.add_child(player)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'quantum_bridge.gd').read_text(encoding='utf-8')
        assert 'func save_state(' in script
        assert 'func load_state(' in script

    def test_camera_shake_method(self, codegen, output_dir):
        """Camera script should have shake method."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600
        camera = CameraNode()
        camera.follow = 'player'
        scene.add_child(camera)
        player = SpriteNode('player')
        player.src = 'p.png'
        scene.add_child(player)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'camera_follow.gd').read_text(encoding='utf-8')
        assert 'func shake(' in script


# ==========================================================================
# Phase 4: Game Over Screen Tests
# ==========================================================================

class TestGameOverScreen:
    """Test game over screen generation."""

    def test_game_over_screen_generated_with_smw(self, codegen, output_dir):
        """death_sequence=smw should generate game_over_screen.gd."""
        scene = SceneNode('level-1')
        scene.width = 800
        scene.height = 600
        scene.death_sequence = 'smw'
        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.body = 'dynamic'
        player.controls = 'arrows'
        scene.add_child(player)

        codegen.generate(scene, output_dir=output_dir)
        go_script = Path(output_dir, 'scripts', 'game_over_screen.gd')
        assert go_script.exists()
        content = go_script.read_text(encoding='utf-8')
        assert 'extends CanvasLayer' in content
        assert 'game_over_finished' in content
        assert 'GAME' in content
        assert 'OVER' in content

    def test_game_over_screen_custom_jingle(self, codegen, output_dir):
        """Custom game_over_jingle path should be used."""
        scene = SceneNode('level-1')
        scene.width = 800
        scene.height = 600
        scene.death_sequence = 'smw'
        scene.game_over_jingle = 'custom_gameover.ogg'
        player = SpriteNode('p')
        player.src = 'p.png'
        scene.add_child(player)

        codegen.generate(scene, output_dir=output_dir)
        content = Path(output_dir, 'scripts', 'game_over_screen.gd').read_text(encoding='utf-8')
        assert 'custom_gameover.ogg' in content

    def test_game_over_screen_custom_alphabet(self, codegen, output_dir):
        """Custom game_over_alphabet path should be used."""
        scene = SceneNode('level-1')
        scene.width = 800
        scene.height = 600
        scene.death_sequence = 'smw'
        scene.game_over_alphabet = 'my_alphabet.png'
        player = SpriteNode('p')
        player.src = 'p.png'
        scene.add_child(player)

        codegen.generate(scene, output_dir=output_dir)
        content = Path(output_dir, 'scripts', 'game_over_screen.gd').read_text(encoding='utf-8')
        assert 'my_alphabet.png' in content

    def test_game_over_not_generated_without_smw(self, codegen, output_dir):
        """Without death_sequence=smw, no game_over_screen.gd."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600
        player = SpriteNode('p')
        player.src = 'p.png'
        scene.add_child(player)

        codegen.generate(scene, output_dir=output_dir)
        go_script = Path(output_dir, 'scripts', 'game_over_screen.gd')
        assert not go_script.exists()

    def test_game_over_viewport_width(self, codegen, output_dir):
        """Viewport width should be used in game over screen."""
        scene = SceneNode('level-1')
        scene.width = 800
        scene.height = 600
        scene.viewport_width = 320
        scene.death_sequence = 'smw'
        player = SpriteNode('p')
        player.src = 'p.png'
        scene.add_child(player)

        codegen.generate(scene, output_dir=output_dir)
        content = Path(output_dir, 'scripts', 'game_over_screen.gd').read_text(encoding='utf-8')
        assert '320.0' in content


# ==========================================================================
# Phase 5: Named Collision Layers Tests
# ==========================================================================

class TestNamedCollisionLayers:
    """Test named collision layer resolution and project.godot output."""

    def test_named_collision_layer_in_project_godot(self, codegen, output_dir):
        """Named collision layers should appear in project.godot."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600
        physics = PhysicsNode()
        physics.collision_layers = {'world': 1, 'player': 2, 'enemies': 4}
        scene.add_child(physics)
        player = SpriteNode('p')
        player.src = 'p.png'
        scene.add_child(player)

        codegen.generate(scene, output_dir=output_dir)
        project = Path(output_dir, 'project.godot').read_text(encoding='utf-8')
        assert '2d_physics/layer_1="world"' in project
        assert '2d_physics/layer_2="player"' in project
        assert '2d_physics/layer_3="enemies"' in project

    def test_named_collision_layer_resolution_player(self, codegen, output_dir):
        """Named collision-layer='player' should resolve to bitmask 2."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600
        physics = PhysicsNode()
        physics.collision_layers = {'world': 1, 'player': 2, 'enemies': 4}
        scene.add_child(physics)

        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.body = 'dynamic'
        player.controls = 'arrows'
        player.collision_layer = 'player'
        player.collision_mask = 'world,enemies'
        scene.add_child(player)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'player_controller.gd').read_text(encoding='utf-8')
        assert 'collision_layer = 2' in script
        assert 'collision_mask = 5' in script  # world(1) | enemies(4) = 5

    def test_named_collision_layer_resolution_prefab(self, codegen, output_dir):
        """Named collision layers in prefab sprites should be resolved."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600
        physics = PhysicsNode()
        physics.collision_layers = {'world': 1, 'player': 2, 'enemies': 4}
        scene.add_child(physics)

        prefab = PrefabNode('rex')
        prefab.entity_type = 'enemy'
        prefab.movement = 'patrol'
        sprite = SpriteNode('rex_body')
        sprite.src = 'rex.png'
        sprite.tag = 'enemy'
        sprite.body = 'dynamic'
        sprite.collision_layer = 'enemies'
        sprite.collision_mask = 'world,player'
        prefab.add_child(sprite)
        scene.add_child(prefab)

        inst = InstanceNode('rex')
        inst.x = 100
        inst.y = 200
        scene.add_child(inst)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_rex.gd').read_text(encoding='utf-8')
        assert 'collision_layer = 4' in script  # enemies = 4
        assert 'collision_mask = 3' in script   # world(1) | player(2) = 3

    def test_default_layer_names_without_physics(self, codegen, output_dir):
        """Without physics collision layers, use default SMW names."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600
        player = SpriteNode('p')
        player.src = 'p.png'
        scene.add_child(player)

        codegen.generate(scene, output_dir=output_dir)
        project = Path(output_dir, 'project.godot').read_text(encoding='utf-8')
        assert '2d_physics/layer_1="world"' in project
        assert '2d_physics/layer_2="player"' in project

    def test_numeric_collision_still_works(self, codegen, output_dir):
        """Numeric collision-layer/mask should still work."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600
        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.body = 'dynamic'
        player.controls = 'arrows'
        player.collision_layer = 3
        player.collision_mask = 7
        scene.add_child(player)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'player_controller.gd').read_text(encoding='utf-8')
        assert 'collision_layer = 3' in script
        assert 'collision_mask = 7' in script

    def test_parser_named_collision_layer_string(self):
        """Parser should store named collision layers as strings."""
        from quantum.core.parser import QuantumParser
        parser = QuantumParser()
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:sprite id="mario" src="m.png" x="0" y="0"
                           collision-layer="player" collision-mask="world,enemies" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        sprite = ast.scenes[0].children[0]
        assert sprite.collision_layer == 'player'
        assert sprite.collision_mask == 'world,enemies'


# ==========================================================================
# Phase 6: Prefab Behaviors — blocks, coins, checkpoint
# ==========================================================================

class TestBlockPrefabBehavior:
    """Test qblock (content + hits) code generation."""

    def test_qblock_generates_hit_method(self, codegen, output_dir):
        """Qblock with content and hits should generate hit() method."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600

        prefab = PrefabNode('qblock')
        prefab.entity_type = 'block'
        prefab.content = 'coin'
        prefab.hits = 1
        sprite = SpriteNode('qblock_body')
        sprite.src = 'qblock.png'
        sprite.tag = 'qblock'
        sprite.body = 'static'
        anim = AnimationNode('shine')
        anim.frames = '0,1,2,3'
        anim.speed = 0.15
        anim.loop = True
        anim.auto_play = True
        sprite.add_child(anim)
        prefab.add_child(sprite)
        scene.add_child(prefab)

        inst = InstanceNode('qblock')
        inst.x = 100
        inst.y = 200
        scene.add_child(inst)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_qblock.gd').read_text(encoding='utf-8')
        assert 'func hit()' in script
        assert '_hits_remaining' in script
        assert '_is_used' in script
        assert 'block-hit' in script

    def test_qblock_hits_countdown(self, codegen, output_dir):
        """Qblock should countdown hits and switch to used state."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600

        prefab = PrefabNode('qblock')
        prefab.entity_type = 'block'
        prefab.content = 'mushroom'
        prefab.hits = 3
        sprite = SpriteNode('qb')
        sprite.src = 'qb.png'
        sprite.body = 'static'
        prefab.add_child(sprite)
        scene.add_child(prefab)

        inst = InstanceNode('qblock')
        inst.x = 50
        inst.y = 50
        scene.add_child(inst)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_qblock.gd').read_text(encoding='utf-8')
        assert '_hits_remaining = 3' in script or 'var _hits_remaining: int = 3' in script
        assert '"mushroom"' in script
        assert '_hits_remaining -= 1' in script
        assert '_hits_remaining <= 0' in script

    def test_qblock_used_state_stops_animation(self, codegen, output_dir):
        """When qblock becomes used, animation should stop."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600

        prefab = PrefabNode('qblock')
        prefab.entity_type = 'block'
        prefab.content = 'coin'
        prefab.hits = 1
        sprite = SpriteNode('qb')
        sprite.src = 'qb.png'
        sprite.body = 'static'
        prefab.add_child(sprite)
        scene.add_child(prefab)

        inst = InstanceNode('qblock')
        inst.x = 50
        inst.y = 50
        scene.add_child(inst)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_qblock.gd').read_text(encoding='utf-8')
        # _process should return early when used
        assert 'if _is_used' in script
        assert 'return' in script

    def test_qblock_scene_is_static_body(self, codegen, output_dir):
        """Qblock TSCN should use StaticBody2D with script."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600

        prefab = PrefabNode('qblock')
        prefab.entity_type = 'block'
        prefab.content = 'coin'
        prefab.hits = 1
        sprite = SpriteNode('qb')
        sprite.src = 'qb.png'
        sprite.body = 'static'
        prefab.add_child(sprite)
        scene.add_child(prefab)

        inst = InstanceNode('qblock')
        inst.x = 50
        inst.y = 50
        scene.add_child(inst)

        codegen.generate(scene, output_dir=output_dir)
        tscn = Path(output_dir, 'prefabs', 'qblock.tscn').read_text(encoding='utf-8')
        assert 'StaticBody2D' in tscn
        assert 'prefab_qblock.gd' in tscn


class TestBreakableBlockBehavior:
    """Test breakable block (rotating block) code generation."""

    def test_breakable_generates_tween_rotation(self, codegen, output_dir):
        """Breakable block should generate hit() with tween rotation."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600

        prefab = PrefabNode('rotating_block')
        prefab.entity_type = 'block'
        prefab.breakable = True
        sprite = SpriteNode('rb')
        sprite.src = 'rotating_block.png'
        sprite.tag = 'rotating_block'
        sprite.body = 'static'
        prefab.add_child(sprite)
        scene.add_child(prefab)

        inst = InstanceNode('rotating_block')
        inst.x = 200
        inst.y = 300
        scene.add_child(inst)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_rotating_block.gd').read_text(encoding='utf-8')
        assert 'func hit()' in script
        assert 'create_tween()' in script
        assert 'rotation_degrees' in script
        assert 'block-broken' in script

    def test_breakable_toggles_collision(self, codegen, output_dir):
        """Breakable block should disable/re-enable collision."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600

        prefab = PrefabNode('rotating_block')
        prefab.entity_type = 'block'
        prefab.breakable = True
        sprite = SpriteNode('rb')
        sprite.src = 'rb.png'
        sprite.body = 'static'
        prefab.add_child(sprite)
        scene.add_child(prefab)

        inst = InstanceNode('rotating_block')
        inst.x = 50
        inst.y = 50
        scene.add_child(inst)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_rotating_block.gd').read_text(encoding='utf-8')
        assert 'CollisionShape2D' in script
        assert 'disabled = true' in script
        assert 'disabled = false' in script
        assert '_restore' in script


class TestCollectibleBehavior:
    """Test collectible item code generation."""

    def test_collectible_generates_body_entered(self, codegen, output_dir):
        """Collectible should connect body_entered and queue_free on collect."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600

        prefab = PrefabNode('coin')
        prefab.entity_type = 'item'
        prefab.collectible = True
        prefab.reward = 'score:10'
        sprite = SpriteNode('coin_body')
        sprite.src = 'coin.png'
        sprite.tag = 'coin'
        sprite.sensor = True
        prefab.add_child(sprite)
        scene.add_child(prefab)

        inst = InstanceNode('coin')
        inst.x = 150
        inst.y = 100
        scene.add_child(inst)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_coin.gd').read_text(encoding='utf-8')
        assert 'body_entered.connect' in script
        assert 'queue_free()' in script
        assert 'CharacterBody2D' in script
        assert '_collected' in script

    def test_collectible_emits_event_with_score(self, codegen, output_dir):
        """Collectible with reward should emit event with score."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600

        prefab = PrefabNode('coin')
        prefab.entity_type = 'item'
        prefab.collectible = True
        prefab.reward = 'score:10'
        sprite = SpriteNode('c')
        sprite.src = 'c.png'
        sprite.tag = 'coin'
        sprite.sensor = True
        prefab.add_child(sprite)
        scene.add_child(prefab)

        inst = InstanceNode('coin')
        inst.x = 50
        inst.y = 50
        scene.add_child(inst)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_coin.gd').read_text(encoding='utf-8')
        assert 'score' in script
        assert '10' in script
        assert 'QuantumEventBus.emit_event' in script

    def test_yoshi_coin_shimmer(self, codegen, output_dir):
        """Yoshi coin (collectible + tag yoshi_coin) should have shimmer modulate effect."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600

        prefab = PrefabNode('yoshi_coin')
        prefab.entity_type = 'item'
        prefab.collectible = True
        prefab.reward = 'score:50'
        sprite = SpriteNode('yc')
        sprite.src = 'yoshi_coin.png'
        sprite.tag = 'yoshi_coin'
        sprite.sensor = True
        prefab.add_child(sprite)
        scene.add_child(prefab)

        inst = InstanceNode('yoshi_coin')
        inst.x = 300
        inst.y = 200
        scene.add_child(inst)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_yoshi_coin.gd').read_text(encoding='utf-8')
        assert 'modulate' in script
        assert '_shimmer_time' in script
        assert 'sin(' in script

    def test_collectible_area2d_scene(self, codegen, output_dir):
        """Collectible TSCN should use Area2D."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600

        prefab = PrefabNode('coin')
        prefab.entity_type = 'item'
        prefab.collectible = True
        sprite = SpriteNode('c')
        sprite.src = 'c.png'
        sprite.sensor = True
        prefab.add_child(sprite)
        scene.add_child(prefab)

        inst = InstanceNode('coin')
        inst.x = 50
        inst.y = 50
        scene.add_child(inst)

        codegen.generate(scene, output_dir=output_dir)
        tscn = Path(output_dir, 'prefabs', 'coin.tscn').read_text(encoding='utf-8')
        assert 'Area2D' in tscn
        assert 'prefab_coin.gd' in tscn


class TestCheckpointBehavior:
    """Test checkpoint prefab code generation."""

    def test_checkpoint_generates_signal(self, codegen, output_dir):
        """Checkpoint should declare checkpoint_activated signal."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600

        prefab = PrefabNode('checkpoint')
        prefab.entity_type = 'goal'
        prefab.checkpoint = True
        sprite = SpriteNode('cp')
        sprite.src = 'checkpoint.png'
        sprite.tag = 'checkpoint'
        sprite.sensor = True
        prefab.add_child(sprite)
        scene.add_child(prefab)

        inst = InstanceNode('checkpoint')
        inst.x = 500
        inst.y = 300
        scene.add_child(inst)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_checkpoint.gd').read_text(encoding='utf-8')
        assert 'checkpoint_activated' in script
        assert 'signal' in script

    def test_checkpoint_one_time_activation(self, codegen, output_dir):
        """Checkpoint should only activate once."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600

        prefab = PrefabNode('checkpoint')
        prefab.entity_type = 'goal'
        prefab.checkpoint = True
        sprite = SpriteNode('cp')
        sprite.src = 'cp.png'
        sprite.sensor = True
        prefab.add_child(sprite)
        scene.add_child(prefab)

        inst = InstanceNode('checkpoint')
        inst.x = 50
        inst.y = 50
        scene.add_child(inst)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_checkpoint.gd').read_text(encoding='utf-8')
        assert '_activated' in script
        assert 'if _activated' in script
        assert 'return' in script

    def test_checkpoint_tint_feedback(self, codegen, output_dir):
        """Checkpoint should apply green tint on activation."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600

        prefab = PrefabNode('checkpoint')
        prefab.entity_type = 'goal'
        prefab.checkpoint = True
        sprite = SpriteNode('cp')
        sprite.src = 'cp.png'
        sprite.sensor = True
        prefab.add_child(sprite)
        scene.add_child(prefab)

        inst = InstanceNode('checkpoint')
        inst.x = 50
        inst.y = 50
        scene.add_child(inst)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_checkpoint.gd').read_text(encoding='utf-8')
        assert 'modulate' in script
        assert 'Color(' in script

    def test_checkpoint_emits_event(self, codegen, output_dir):
        """Checkpoint should emit checkpoint-activated event."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600

        prefab = PrefabNode('checkpoint')
        prefab.entity_type = 'goal'
        prefab.checkpoint = True
        sprite = SpriteNode('cp')
        sprite.src = 'cp.png'
        sprite.sensor = True
        prefab.add_child(sprite)
        scene.add_child(prefab)

        inst = InstanceNode('checkpoint')
        inst.x = 50
        inst.y = 50
        scene.add_child(inst)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_checkpoint.gd').read_text(encoding='utf-8')
        assert 'checkpoint-activated' in script
        assert 'QuantumEventBus.emit_event' in script
        assert 'global_position' in script


class TestCheckpointParsing:
    """Test checkpoint attribute parsing."""

    def test_parser_checkpoint_attribute(self):
        """Parser should handle checkpoint='true' on prefab."""
        from quantum.core.parser import QuantumParser
        parser = QuantumParser()
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:prefab name="cp" entity-type="goal" checkpoint="true">
                    <qg:sprite id="cp_s" src="cp.png" />
                </qg:prefab>
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        prefab = ast.scenes[0].children[0]
        assert prefab.checkpoint is True

    def test_parser_checkpoint_default_none(self):
        """Checkpoint should default to None when not set."""
        from quantum.core.parser import QuantumParser
        parser = QuantumParser()
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:prefab name="rex" entity-type="enemy">
                    <qg:sprite id="r" src="r.png" />
                </qg:prefab>
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        prefab = ast.scenes[0].children[0]
        assert prefab.checkpoint is None


# ==========================================================================
# GodotCodeGenerator Tests - Tilemap with data-src (external JSON)
# ==========================================================================

class TestTilemapDataSrcGeneration:
    """Test tilemap generation with external JSON data source."""

    def test_tilemap_data_src_generates_loader_script(self, codegen, output_dir):
        """Tilemap with data-src should generate tilemap_loader.gd."""
        scene = SceneNode('main')
        tilemap = TilemapNode('terrain')
        tilemap.src = 'collision_tileset.tres'
        tilemap.data_src = 'tile_map.json'
        tilemap.tile_width = 16
        tilemap.tile_height = 16

        layer = TilemapLayerNode('terrain')
        layer.collision = True
        tilemap.add_layer(layer)
        scene.add_child(tilemap)

        codegen.generate(scene, output_dir=output_dir)
        loader = Path(output_dir, 'scripts', 'tilemap_loader.gd')
        assert loader.exists()
        content = loader.read_text(encoding='utf-8')
        assert 'extends TileMapLayer' in content
        assert 'tile_map.json' in content

    def test_tilemap_data_src_loader_has_correct_json_path(self, codegen, output_dir):
        """Loader script should reference res://tile_map.json."""
        scene = SceneNode('main')
        tilemap = TilemapNode('terrain')
        tilemap.src = 'tileset.tres'
        tilemap.data_src = 'assets/smw/tile_map.json'
        tilemap.tile_width = 16
        tilemap.tile_height = 16

        layer = TilemapLayerNode('ground')
        layer.collision = True
        tilemap.add_layer(layer)
        scene.add_child(tilemap)

        codegen.generate(scene, output_dir=output_dir)
        content = Path(output_dir, 'scripts', 'tilemap_loader.gd').read_text(encoding='utf-8')
        assert 'res://tile_map.json' in content

    def test_tilemap_data_src_tscn_has_script(self, codegen, output_dir):
        """TileMapLayer in TSCN should reference tilemap_loader.gd script."""
        scene = SceneNode('main')
        tilemap = TilemapNode('terrain')
        tilemap.src = 'collision_tileset.tres'
        tilemap.data_src = 'tile_map.json'
        tilemap.tile_width = 16
        tilemap.tile_height = 16

        layer = TilemapLayerNode('terrain')
        layer.collision = True
        tilemap.add_layer(layer)
        scene.add_child(tilemap)

        codegen.generate(scene, output_dir=output_dir)
        tscn = Path(output_dir, 'main.tscn').read_text(encoding='utf-8')
        assert 'tilemap_loader.gd' in tscn
        assert 'TileMapLayer' in tscn

    def test_tilemap_data_src_tscn_references_tileset(self, codegen, output_dir):
        """TSCN should have ext_resource for the .tres tileset."""
        scene = SceneNode('main')
        tilemap = TilemapNode('terrain')
        tilemap.src = 'collision_tileset.tres'
        tilemap.data_src = 'tile_map.json'
        tilemap.tile_width = 16
        tilemap.tile_height = 16

        layer = TilemapLayerNode('terrain')
        layer.collision = True
        tilemap.add_layer(layer)
        scene.add_child(tilemap)

        codegen.generate(scene, output_dir=output_dir)
        tscn = Path(output_dir, 'main.tscn').read_text(encoding='utf-8')
        assert 'collision_tileset.tres' in tscn
        assert 'TileSet' in tscn

    def test_tilemap_data_src_no_inline_setup(self, codegen, output_dir):
        """data-src tilemap should NOT generate _setup_tilemaps in scene script."""
        scene = SceneNode('main')
        sprite = SpriteNode('s1')
        sprite.src = 'a.png'
        scene.add_child(sprite)

        tilemap = TilemapNode('terrain')
        tilemap.src = 'collision_tileset.tres'
        tilemap.data_src = 'tile_map.json'
        tilemap.tile_width = 16
        tilemap.tile_height = 16

        layer = TilemapLayerNode('terrain')
        layer.collision = True
        tilemap.add_layer(layer)
        scene.add_child(tilemap)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert '_setup_tilemaps' not in script
        assert 'TileSet.new()' not in script

    def test_tilemap_without_data_src_still_works(self, codegen, output_dir):
        """Tilemap without data-src should still generate inline CSV setup."""
        scene = SceneNode('main')
        tilemap = TilemapNode('world')
        tilemap.src = 'tileset.png'
        tilemap.tile_width = 16
        tilemap.tile_height = 16

        layer = TilemapLayerNode('ground')
        layer.data = '0,0,1,1\n0,0,1,1'
        layer.collision = True
        tilemap.add_layer(layer)
        scene.add_child(tilemap)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert '_setup_tilemaps' in script
        assert 'TileSet.new()' in script
        # Should NOT generate loader script
        loader = Path(output_dir, 'scripts', 'tilemap_loader.gd')
        assert not loader.exists()

    def test_tilemap_data_src_no_loader_when_absent(self, codegen, output_dir):
        """No tilemap_loader.gd should be generated when no tilemap uses data-src."""
        scene = SceneNode('main')
        sprite = SpriteNode('s1')
        sprite.src = 'a.png'
        scene.add_child(sprite)

        codegen.generate(scene, output_dir=output_dir)
        loader = Path(output_dir, 'scripts', 'tilemap_loader.gd')
        assert not loader.exists()


# ==========================================================================
# TILEMAP_LOADER_GD Template Tests
# ==========================================================================

class TestTilemapLoaderTemplate:
    """Test the TILEMAP_LOADER_GD template."""

    def test_template_generates_with_correct_path(self):
        """Template should format with json_path and source_id."""
        result = TILEMAP_LOADER_GD.format(json_path='res://tile_map.json', source_id=0)
        assert 'extends TileMapLayer' in result
        assert 'res://tile_map.json' in result
        assert 'set_cell(Vector2i(col_idx, row_idx), 0, Vector2i(atlas_x, atlas_y))' in result

    def test_template_with_custom_source_id(self):
        """Template should use the specified source_id."""
        result = TILEMAP_LOADER_GD.format(json_path='res://data.json', source_id=2)
        assert 'set_cell(Vector2i(col_idx, row_idx), 2, Vector2i(atlas_x, atlas_y))' in result


# ==========================================================================
# Phase 1: Bug Fix Tests
# ==========================================================================

class TestBugFixDuplicateCollisionConnects:
    """BUG 1: Collision signal should have ONE connect per sprite, not per on_collision."""

    def test_single_connect_per_sprite_with_multiple_collisions(self, codegen, output_dir):
        """Multiple on_collision children should still produce one body_entered.connect."""
        scene = SceneNode('main')
        sprite = SpriteNode('player')
        sprite.src = 'player.png'
        sprite.x = 100
        sprite.y = 200
        col1 = OnCollisionNode()
        col1.with_tag = 'enemy'
        col1.action = 'destroy-self'
        col2 = OnCollisionNode()
        col2.with_tag = 'coin'
        col2.action = 'destroy-other'
        sprite.add_child(col1)
        sprite.add_child(col2)
        scene.add_child(sprite)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        # Should only have ONE connect call for player_area
        connect_count = script.count('body_entered.connect(_on_player_collision)')
        assert connect_count == 1

    def test_no_connect_without_collisions(self, codegen, output_dir):
        """Sprites without on_collision should not generate any connect."""
        scene = SceneNode('main')
        sprite = SpriteNode('hero')
        sprite.src = 'hero.png'
        scene.add_child(sprite)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'body_entered.connect' not in script


class TestBugFixHyphenIdentifiers:
    """BUG 2: Hyphens in node IDs must use $\"name\" syntax."""

    def test_hyphenated_sprite_id_quoted(self, codegen, output_dir):
        """Sprite ID with hyphens should generate $\"name\" references."""
        scene = SceneNode('main')
        sprite = SpriteNode('level-bg')
        sprite.src = 'bg.png'
        scene.add_child(sprite)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert '$"level-bg"' in script
        assert '$level-bg' not in script.replace('$"level-bg"', '')

    def test_simple_sprite_id_not_quoted(self, codegen, output_dir):
        """Sprite ID without special chars should use plain $ syntax."""
        scene = SceneNode('main')
        sprite = SpriteNode('player')
        sprite.src = 'p.png'
        scene.add_child(sprite)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert '$player' in script


class TestBugFixUndeclaredStateVars:
    """BUG 3: Variables from event set actions should be auto-declared."""

    def test_set_action_declares_variable(self, codegen, output_dir):
        """Event action with type=set should auto-declare the target variable."""
        scene = SceneNode('main')
        evt = EventNode('coin-collected', '')
        action = EventActionNode()
        action.action_type = 'set'
        action.target = 'coins'
        action.value = 'coins+1'
        evt.add_child(action)
        scene.add_child(evt)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'var coins = 0' in script

    def test_score_action_declares_score_variable(self, codegen, output_dir):
        """Event action with type=score should auto-declare score variable."""
        scene = SceneNode('main')
        evt = EventNode('enemy-killed', '')
        action = EventActionNode()
        action.action_type = 'score'
        action.amount = 100
        evt.add_child(action)
        scene.add_child(evt)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'var score = 0' in script

    def test_no_duplicate_declaration(self, codegen, output_dir):
        """Explicitly declared variable should not be duplicated by auto-detection."""
        scene = SceneNode('main')
        # Explicit declaration
        set_node = SetNode('coins')
        set_node.value = 5
        scene.add_child(set_node)
        # Event action referencing same var
        evt = EventNode('coin-collected', '')
        action = EventActionNode()
        action.action_type = 'set'
        action.target = 'coins'
        action.value = 'coins+1'
        evt.add_child(action)
        scene.add_child(evt)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        # Should have exactly one declaration of coins
        assert script.count('var coins') == 1


# ==========================================================================
# Phase 2: Quantum Bridge game_state API Tests
# ==========================================================================

class TestQuantumBridgeGameState:
    """Bridge should have volatile game_state API (save/get/clear)."""

    def test_bridge_has_game_state_dict(self):
        from quantum.runtime.godot_templates import QUANTUM_BRIDGE_GD
        assert 'var game_state: Dictionary' in QUANTUM_BRIDGE_GD

    def test_bridge_has_save_game_state(self):
        from quantum.runtime.godot_templates import QUANTUM_BRIDGE_GD
        assert 'func save_game_state(' in QUANTUM_BRIDGE_GD
        assert 'game_state = data.duplicate()' in QUANTUM_BRIDGE_GD

    def test_bridge_has_get_and_clear_game_state(self):
        from quantum.runtime.godot_templates import QUANTUM_BRIDGE_GD
        assert 'func get_game_state()' in QUANTUM_BRIDGE_GD
        assert 'func clear_game_state()' in QUANTUM_BRIDGE_GD
        assert 'return game_state' in QUANTUM_BRIDGE_GD


# ==========================================================================
# Phase 3: Player Controller .hit() Tests
# ==========================================================================

class TestPlayerControllerHitCall:
    """Player controller should call collider.hit() on qblock/rotating_block."""

    def test_qblock_hit_call_before_emit(self):
        from quantum.runtime.godot_templates import PLAYER_CONTROLLER_GD
        # The template should call hit() before emit_event for qblock
        qblock_section = PLAYER_CONTROLLER_GD[PLAYER_CONTROLLER_GD.find('tag == "qblock"'):]
        assert 'collider.hit()' in qblock_section

    def test_rotating_block_hit_call(self):
        from quantum.runtime.godot_templates import PLAYER_CONTROLLER_GD
        rotating_section = PLAYER_CONTROLLER_GD[PLAYER_CONTROLLER_GD.find('tag == "rotating_block"'):]
        assert 'collider.hit()' in rotating_section


# ==========================================================================
# Phase 4: HUD Update in Event Handlers Tests
# ==========================================================================

class TestHudUpdateInEventHandlers:
    """Event actions that modify HUD-bound variables should emit $HUD.update_label."""

    def test_set_action_updates_hud_bound_var(self, codegen, output_dir):
        """Setting a variable bound to HUD counter should generate update_label."""
        scene = SceneNode('main')
        # HUD with counter bound to 'coins'
        hud = HudNode()
        hud.position = 'top'
        counter = HudCounterNode()
        counter.strip = 'digits.png'
        counter.x = 0
        counter.y = 0
        counter.digits = 2
        counter.bind = '{coins}'
        hud.add_child(counter)
        scene.add_child(hud)
        # Event that modifies coins
        evt = EventNode('coin-collected', '')
        action = EventActionNode()
        action.action_type = 'set'
        action.target = 'coins'
        action.value = 'coins+1'
        evt.add_child(action)
        scene.add_child(evt)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert '$HUD.update_label("coins", str(coins))' in script

    def test_score_action_updates_hud(self, codegen, output_dir):
        """Score action with HUD-bound score should generate update_label."""
        scene = SceneNode('main')
        hud = HudNode()
        hud.position = 'top'
        counter = HudCounterNode()
        counter.strip = 'digits.png'
        counter.x = 0
        counter.y = 0
        counter.digits = 6
        counter.bind = '{score}'
        hud.add_child(counter)
        scene.add_child(hud)
        evt = EventNode('enemy-killed', '')
        action = EventActionNode()
        action.action_type = 'score'
        action.amount = 100
        evt.add_child(action)
        scene.add_child(evt)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'score += 100' in script
        assert '$HUD.update_label("score", str(score))' in script

    def test_set_action_no_hud_no_update(self, codegen, output_dir):
        """Setting a variable NOT bound to HUD should not generate update_label."""
        scene = SceneNode('main')
        evt = EventNode('test-event', '')
        action = EventActionNode()
        action.action_type = 'set'
        action.target = 'some_flag'
        action.value = 'true'
        evt.add_child(action)
        scene.add_child(evt)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'update_label' not in script

    def test_hud_counter_countdown_auto_declares_with_default(self, codegen, output_dir):
        """HUD countdown counter should auto-declare bind var with default 300."""
        scene = SceneNode('main')
        hud = HudNode()
        hud.position = 'top'
        counter = HudCounterNode()
        counter.strip = 'digits.png'
        counter.x = 0
        counter.y = 0
        counter.digits = 3
        counter.bind = '{time}'
        counter.countdown = True
        hud.add_child(counter)
        scene.add_child(hud)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'var time = 300' in script


# ==========================================================================
# Phase 5: Stomp Enrichment Tests
# ==========================================================================

class TestStompEnrichment:
    """Stomp handler should include sound, camera shake, score, cooldown, puff."""

    def _scene_with_stomp(self):
        scene = SceneNode('main')
        scene.death_sequence = 'smw'
        scene.death_timer = 3.0
        sprite = SpriteNode('mario')
        sprite.src = 'mario.png'
        sprite.x = 50
        sprite.y = 100
        sprite.controls = 'platformer'
        scene.add_child(sprite)
        prefab = PrefabNode('rex')
        prefab.defeated_by = 'stomp'
        prefab.stomp_bounce = -200
        return scene, prefab

    def test_stomp_has_cooldown(self, codegen, output_dir):
        scene, prefab = self._scene_with_stomp()
        codegen.generate(scene, prefabs=[prefab], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'last_stomp_time' in script
        assert '500' in script or '0.5' in script

    def test_stomp_has_sound(self, codegen, output_dir):
        scene, prefab = self._scene_with_stomp()
        codegen.generate(scene, prefabs=[prefab], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'play_sound("sfx-stomp")' in script

    def test_stomp_has_camera_shake(self, codegen, output_dir):
        scene, prefab = self._scene_with_stomp()
        codegen.generate(scene, prefabs=[prefab], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'camera_shake(' in script

    def test_stomp_has_score(self, codegen, output_dir):
        scene, prefab = self._scene_with_stomp()
        codegen.generate(scene, prefabs=[prefab], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'score += 100' in script or 'score += ' in script

    def test_stomp_has_spawn_puff(self, codegen, output_dir):
        scene, prefab = self._scene_with_stomp()
        codegen.generate(scene, prefabs=[prefab], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert '_spawn_puff' in script


# ==========================================================================
# Phase 6: Death Sequence Tests
# ==========================================================================

class TestDeathSequenceComplete:
    """Death sequence should have lives, HUD update, process_mode, pause, SFX, timers."""

    def _scene_with_death(self):
        scene = SceneNode('main')
        scene.death_sequence = 'smw'
        scene.death_timer = 3.0
        sprite = SpriteNode('mario')
        sprite.src = 'mario.png'
        sprite.controls = 'platformer'
        scene.add_child(sprite)
        return scene

    def test_death_decrements_lives(self, codegen, output_dir):
        scene = self._scene_with_death()
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'lives -= 1' in script

    def test_death_pauses_tree(self, codegen, output_dir):
        scene = self._scene_with_death()
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'get_tree().paused = true' in script

    def test_death_sets_process_mode_always(self, codegen, output_dir):
        scene = self._scene_with_death()
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'PROCESS_MODE_ALWAYS' in script

    def test_death_uses_timer_not_create_timer(self, codegen, output_dir):
        """Should use Timer node with PROCESS_MODE_ALWAYS, not create_timer (broken in pause)."""
        scene = self._scene_with_death()
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'Timer.new()' in script
        assert 'create_timer' not in script

    def test_death_plays_sfx(self, codegen, output_dir):
        scene = self._scene_with_death()
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        # Death SFX plays directly with PROCESS_MODE_ALWAYS (works during pause)
        assert 'sfx-death' in script
        assert 'sfx.play()' in script

    def test_death_calls_kill_player_on_bridge(self, codegen, output_dir):
        scene = self._scene_with_death()
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'QuantumBridge.kill_player(' in script

    def test_death_complete_checks_game_over(self, codegen, output_dir):
        scene = self._scene_with_death()
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'lives <= 0' in script or 'lives < 1' in script

    def test_death_complete_has_checkpoint_branch(self, codegen, output_dir):
        scene = self._scene_with_death()
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'has_checkpoint' in script


# ==========================================================================
# Phase 7: Game Init + State Restoration Tests
# ==========================================================================

class TestGameInitStateRestore:
    """Game init should restore state, iris_in, update HUD, play BGM."""

    def test_game_init_called_in_ready(self, codegen, output_dir):
        scene = SceneNode('main')
        scene.death_sequence = 'smw'
        sprite = SpriteNode('mario')
        sprite.src = 'mario.png'
        sprite.controls = 'platformer'
        scene.add_child(sprite)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'on_game_init()' in script

    def test_game_init_restores_state(self, codegen, output_dir):
        scene = SceneNode('main')
        scene.death_sequence = 'smw'
        sprite = SpriteNode('mario')
        sprite.src = 'mario.png'
        sprite.controls = 'platformer'
        scene.add_child(sprite)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'get_game_state()' in script
        assert 'clear_game_state()' in script

    def test_game_init_iris_in(self, codegen, output_dir):
        scene = SceneNode('main')
        scene.death_sequence = 'smw'
        sprite = SpriteNode('mario')
        sprite.src = 'mario.png'
        sprite.controls = 'platformer'
        scene.add_child(sprite)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'iris_in(' in script

    def test_game_init_updates_hud(self, codegen, output_dir):
        scene = SceneNode('main')
        scene.death_sequence = 'smw'
        sprite = SpriteNode('mario')
        sprite.src = 'mario.png'
        sprite.controls = 'platformer'
        scene.add_child(sprite)
        hud = HudNode()
        hud.position = 'top'
        counter = HudCounterNode()
        counter.strip = 'digits.png'
        counter.bind = '{lives}'
        counter.x = 0
        counter.y = 0
        counter.digits = 2
        hud.add_child(counter)
        scene.add_child(hud)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        # on_game_init should update HUD labels
        init_section = script[script.find('func on_game_init'):]
        assert 'update_label(' in init_section

    def test_game_init_bgm_autoplay(self, codegen, output_dir):
        """BGM sounds with trigger=scene.start should auto-play in on_game_init."""
        scene = SceneNode('main')
        scene.death_sequence = 'smw'
        sprite = SpriteNode('mario')
        sprite.src = 'mario.png'
        sprite.controls = 'platformer'
        scene.add_child(sprite)
        bgm = SoundNode('bgm')
        bgm.src = 'music.ogg'
        bgm.trigger = 'scene.start'
        scene.add_child(bgm)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'play_sound("bgm")' in script


# ==========================================================================
# Phase 8: Checkpoint Integration Tests
# ==========================================================================

class TestCheckpointIntegration:
    """Scene script should connect checkpoint signals and handle respawn."""

    def test_checkpoint_vars_declared(self, codegen, output_dir):
        scene = SceneNode('main')
        scene.death_sequence = 'smw'
        sprite = SpriteNode('mario')
        sprite.src = 'mario.png'
        sprite.controls = 'platformer'
        scene.add_child(sprite)
        # Add a checkpoint prefab
        prefab = PrefabNode('checkpoint')
        prefab.tag = 'checkpoint'

        codegen.generate(scene, prefabs=[prefab], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'has_checkpoint' in script
        assert 'checkpoint_position' in script

    def test_checkpoint_activated_handler(self, codegen, output_dir):
        scene = SceneNode('main')
        scene.death_sequence = 'smw'
        sprite = SpriteNode('mario')
        sprite.src = 'mario.png'
        sprite.controls = 'platformer'
        scene.add_child(sprite)
        prefab = PrefabNode('checkpoint')
        prefab.tag = 'checkpoint'

        codegen.generate(scene, prefabs=[prefab], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert '_on_checkpoint_activated' in script

    def test_respawn_at_checkpoint(self, codegen, output_dir):
        scene = SceneNode('main')
        scene.death_sequence = 'smw'
        sprite = SpriteNode('mario')
        sprite.src = 'mario.png'
        sprite.controls = 'platformer'
        scene.add_child(sprite)
        prefab = PrefabNode('checkpoint')
        prefab.tag = 'checkpoint'

        codegen.generate(scene, prefabs=[prefab], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert '_respawn_at_checkpoint' in script

    def test_checkpoint_signal_connected_in_ready(self, codegen, output_dir):
        scene = SceneNode('main')
        scene.death_sequence = 'smw'
        sprite = SpriteNode('mario')
        sprite.src = 'mario.png'
        sprite.controls = 'platformer'
        scene.add_child(sprite)
        prefab = PrefabNode('checkpoint')
        prefab.tag = 'checkpoint'

        codegen.generate(scene, prefabs=[prefab], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'checkpoint_activated' in script

    def test_pause_false_before_checkpoint_branch(self, codegen, output_dir):
        """paused=false must come BEFORE if has_checkpoint, not inside else."""
        scene = SceneNode('main')
        scene.death_sequence = 'smw'
        sprite = SpriteNode('mario')
        sprite.src = 'mario.png'
        sprite.controls = 'platformer'
        scene.add_child(sprite)
        prefab = PrefabNode('checkpoint')
        prefab.tag = 'checkpoint'
        codegen.generate(scene, prefabs=[prefab], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        death_complete = script[script.find('func _on_death_complete'):]
        # paused=false should appear BEFORE has_checkpoint check
        pause_pos = death_complete.find('get_tree().paused = false')
        checkpoint_pos = death_complete.find('if has_checkpoint')
        assert pause_pos < checkpoint_pos, 'paused=false must come before checkpoint branch'


# ==========================================================================
# Phase 9: Rotating Block Timing + Yoshi Coin Polish Tests
# ==========================================================================

class TestRotatingBlockPolish:
    """Rotating block should have correct timing: 0.25s tween, 4 loops, 2.0s restore."""

    def test_rotation_tween_duration(self, codegen, output_dir):
        scene = SceneNode('main')
        prefab = PrefabNode('rotating_block')
        prefab.entity_type = 'block'
        prefab.breakable = True

        codegen.generate(scene, prefabs=[prefab], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_rotating_block.gd').read_text(encoding='utf-8')
        assert '0.25' in script

    def test_rotation_set_loops(self, codegen, output_dir):
        scene = SceneNode('main')
        prefab = PrefabNode('rotating_block')
        prefab.entity_type = 'block'
        prefab.breakable = True

        codegen.generate(scene, prefabs=[prefab], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_rotating_block.gd').read_text(encoding='utf-8')
        assert 'set_loops(4)' in script

    def test_restore_timer_2_seconds(self, codegen, output_dir):
        scene = SceneNode('main')
        prefab = PrefabNode('rotating_block')
        prefab.entity_type = 'block'
        prefab.breakable = True

        codegen.generate(scene, prefabs=[prefab], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_rotating_block.gd').read_text(encoding='utf-8')
        assert '2.0' in script


class TestYoshiCoinPolish:
    """Yoshi coin should have random phase init and speed * 5.0."""

    def test_yoshi_coin_random_phase(self, codegen, output_dir):
        scene = SceneNode('main')
        prefab = PrefabNode('yoshi_coin')
        prefab.entity_type = 'item'
        prefab.collectible = True
        prefab.reward = 'score:1000'
        # Add sprite child with yoshi_coin tag
        sprite = SpriteNode('yoshi_coin_sprite')
        sprite.src = 'yoshi_coin.png'
        sprite.tag = 'yoshi_coin'
        prefab.add_child(sprite)

        codegen.generate(scene, prefabs=[prefab], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_yoshi_coin.gd').read_text(encoding='utf-8')
        assert 'randf()' in script and 'TAU' in script


# ==========================================================================
# Phase 10: Integration + Edge Case Tests
# ==========================================================================

class TestIntegrationEndToEnd:
    """End-to-end test with complete scene: player, enemies, HUD, death, checkpoint."""

    def test_complete_scene_generates_all_functions(self, codegen, output_dir):
        """A complete SMW-style scene should generate all expected functions."""
        scene = SceneNode('main')
        scene.death_sequence = 'smw'
        scene.death_timer = 3.0

        # Player
        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.controls = 'platformer'
        scene.add_child(player)

        # HUD with coins + score + lives
        hud = HudNode()
        hud.position = 'top'
        for bind_name, digits in [('coins', 2), ('score', 6), ('lives', 2)]:
            counter = HudCounterNode()
            counter.strip = 'digits.png'
            counter.bind = '{' + bind_name + '}'
            counter.x = 0
            counter.y = 0
            counter.digits = digits
            hud.add_child(counter)
        scene.add_child(hud)

        # Enemy event
        evt = EventNode('coin-collected', '')
        action = EventActionNode()
        action.action_type = 'set'
        action.target = 'coins'
        action.value = 'coins+1'
        evt.add_child(action)
        scene.add_child(evt)

        # Prefabs
        rex = PrefabNode('rex')
        rex.defeated_by = 'stomp'
        rex.stomp_bounce = -200
        checkpoint = PrefabNode('checkpoint')
        checkpoint.tag = 'checkpoint'

        codegen.generate(scene, prefabs=[rex, checkpoint], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')

        # All major functions should be present
        assert 'func _ready()' in script
        assert 'func _kill_player()' in script
        assert 'func _on_death_complete()' in script
        assert 'func _on_enemy_collision(' in script
        assert 'func on_game_init()' in script
        assert 'func _on_checkpoint_activated(' in script
        assert 'func _respawn_at_checkpoint()' in script
        assert 'func _spawn_puff(' in script

    def test_scene_without_hud_death_still_works(self, codegen, output_dir):
        """Scene with death but no HUD should not crash."""
        scene = SceneNode('main')
        scene.death_sequence = 'smw'
        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.controls = 'platformer'
        scene.add_child(player)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'func _kill_player()' in script

    def test_scene_without_enemies_death_still_works(self, codegen, output_dir):
        """Scene with death but no enemies should still generate death handler."""
        scene = SceneNode('main')
        scene.death_sequence = 'smw'
        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.controls = 'platformer'
        scene.add_child(player)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert '_kill_player' in script
        # No stomp handler since no enemies
        assert '_on_enemy_collision' not in script

    def test_checkpoint_without_death_no_crash(self, codegen, output_dir):
        """Checkpoint prefab without death_sequence should not crash."""
        scene = SceneNode('main')
        player = SpriteNode('mario')
        player.src = 'mario.png'
        scene.add_child(player)
        checkpoint = PrefabNode('checkpoint')
        checkpoint.tag = 'checkpoint'

        codegen.generate(scene, prefabs=[checkpoint], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'extends Node2D' in script


# ==========================================================================
# Parity Gap Fixes: BGM stop, 2-stage stomp, area_entered, time-up, etc.
# ==========================================================================

class TestParityBGMStop:
    """_kill_player should stop BGM and play SFX with PROCESS_MODE_ALWAYS."""

    def _scene_with_death_and_bgm(self):
        scene = SceneNode('main')
        scene.death_sequence = 'smw'
        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.controls = 'platformer'
        scene.add_child(player)
        bgm = SoundNode('bgm-level')
        bgm.src = 'music.ogg'
        bgm.trigger = 'scene.start'
        scene.add_child(bgm)
        return scene

    def test_kill_player_stops_bgm(self, codegen, output_dir):
        scene = self._scene_with_death_and_bgm()
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'bgm.stop()' in script

    def test_kill_player_sfx_process_mode(self, codegen, output_dir):
        scene = self._scene_with_death_and_bgm()
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'sfx.process_mode = Node.PROCESS_MODE_ALWAYS' in script
        assert 'sfx.play()' in script

    def test_respawn_resumes_bgm(self, codegen, output_dir):
        scene = self._scene_with_death_and_bgm()
        checkpoint = PrefabNode('checkpoint')
        checkpoint.tag = 'checkpoint'
        codegen.generate(scene, prefabs=[checkpoint], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        # _respawn_at_checkpoint should resume BGM
        respawn_section = script[script.find('func _respawn_at_checkpoint'):]
        assert 'bgm.play()' in respawn_section


class TestParityTwoStageStomp:
    """Stomp handler should use two-stage logic: squish then kill."""

    def _scene_with_stomp(self):
        scene = SceneNode('main')
        scene.death_sequence = 'smw'
        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.controls = 'platformer'
        scene.add_child(player)
        hud = HudNode()
        hud.position = 'top'
        counter = HudCounterNode()
        counter.strip = 'digits.png'
        counter.bind = '{score}'
        counter.x = 0
        counter.y = 0
        counter.digits = 6
        hud.add_child(counter)
        scene.add_child(hud)
        rex = PrefabNode('rex')
        rex.defeated_by = 'stomp'
        rex.stomp_bounce = -200
        return scene, rex

    def test_two_stage_squish(self, codegen, output_dir):
        scene, rex = self._scene_with_stomp()
        codegen.generate(scene, prefabs=[rex], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        # First stomp: squish sprite + collision shape
        assert 'rex_squished' in script
        assert 'scale.y = 0.5' in script
        assert 'position.y += fh * 0.25' in script
        # CollisionShape2D also adjusted
        assert 'CollisionShape2D' in script
        assert 'col_shape.size.y *= 0.5' in script

    def test_two_stage_kill(self, codegen, output_dir):
        scene, rex = self._scene_with_stomp()
        codegen.generate(scene, prefabs=[rex], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        # Second stomp: kill + puff
        assert 'score += 200' in script
        assert 'destroy_sprite' in script
        assert '_spawn_puff' in script

    def test_squish_increases_speed(self, codegen, output_dir):
        scene, rex = self._scene_with_stomp()
        codegen.generate(scene, prefabs=[rex], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'set_patrol(80.0)' in script

    def test_stomp_hud_update(self, codegen, output_dir):
        scene, rex = self._scene_with_stomp()
        codegen.generate(scene, prefabs=[rex], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'update_label("score"' in script


class TestParityAreaEntered:
    """Collision connections should include both body_entered and area_entered."""

    def test_area_entered_connected(self, codegen, output_dir):
        scene = SceneNode('main')
        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.controls = 'platformer'
        col = OnCollisionNode()
        col.with_tag = 'coin'
        col.action = 'emit:coin-collected'
        player.add_child(col)
        scene.add_child(player)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'body_entered.connect' in script
        assert 'area_entered.connect' in script

    def test_area_entered_handler_delegates(self, codegen, output_dir):
        scene = SceneNode('main')
        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.controls = 'platformer'
        col = OnCollisionNode()
        col.with_tag = 'coin'
        col.action = 'emit:coin-collected'
        player.add_child(col)
        scene.add_child(player)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert '_on_mario_area_entered' in script
        assert 'area.get_parent()' in script


class TestParityTimeUp:
    """Countdown HUD should auto-generate time-up handler."""

    def _scene_with_countdown(self):
        scene = SceneNode('main')
        scene.death_sequence = 'smw'
        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.controls = 'platformer'
        scene.add_child(player)
        hud = HudNode()
        hud.position = 'top'
        counter = HudCounterNode()
        counter.strip = 'digits.png'
        counter.bind = '{time_left}'
        counter.x = 0
        counter.y = 0
        counter.digits = 3
        counter.countdown = True
        hud.add_child(counter)
        scene.add_child(hud)
        return scene

    def test_time_up_listener(self, codegen, output_dir):
        scene = self._scene_with_countdown()
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'time-up' in script
        assert '_on_time_up' in script

    def test_time_up_handler_kills_player(self, codegen, output_dir):
        scene = self._scene_with_countdown()
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        handler_section = script[script.find('func _on_time_up'):]
        assert '_kill_player()' in handler_section

    def test_time_up_guards_dead(self, codegen, output_dir):
        scene = self._scene_with_countdown()
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        handler_section = script[script.find('func _on_time_up'):]
        assert '_is_dead' in handler_section


class TestParityFellInPit:
    """fell-in-pit should auto-generate handler when death collision + death sequence."""

    def _scene_with_death_collision(self):
        scene = SceneNode('main')
        scene.death_sequence = 'smw'
        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.controls = 'platformer'
        col = OnCollisionNode()
        col.with_tag = 'death'
        col.action = 'emit:fell-in-pit'
        player.add_child(col)
        scene.add_child(player)
        return scene

    def test_fell_in_pit_listener(self, codegen, output_dir):
        scene = self._scene_with_death_collision()
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'fell-in-pit' in script
        assert '_on_fell_in_pit' in script

    def test_fell_in_pit_handler(self, codegen, output_dir):
        scene = self._scene_with_death_collision()
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        handler = script[script.find('func _on_fell_in_pit'):]
        assert '_is_dead' in handler
        assert '_kill_player()' in handler


class TestParityShowGameOver:
    """_show_game_over should have HUD stop_timer, PROCESS_MODE_ALWAYS, await, cleanup."""

    def test_game_over_stops_timer(self, codegen, output_dir):
        scene = SceneNode('main')
        scene.death_sequence = 'smw'
        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.controls = 'platformer'
        scene.add_child(player)
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        go_section = script[script.find('func _show_game_over'):]
        assert 'stop_timer()' in go_section

    def test_game_over_process_mode(self, codegen, output_dir):
        scene = SceneNode('main')
        scene.death_sequence = 'smw'
        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.controls = 'platformer'
        scene.add_child(player)
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        go_section = script[script.find('func _show_game_over'):]
        assert 'PROCESS_MODE_ALWAYS' in go_section

    def test_game_over_awaits_and_reloads(self, codegen, output_dir):
        scene = SceneNode('main')
        scene.death_sequence = 'smw'
        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.controls = 'platformer'
        scene.add_child(player)
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        go_section = script[script.find('func _show_game_over'):]
        assert 'await' in go_section
        assert 'clear_game_state()' in go_section
        assert 'reload_current_scene()' in go_section


class TestParityRespawnAtCheckpoint:
    """_respawn_at_checkpoint should restore sprite, process_mode, lives HUD."""

    def _scene_with_checkpoint(self):
        scene = SceneNode('main')
        scene.death_sequence = 'smw'
        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.controls = 'platformer'
        scene.add_child(player)
        hud = HudNode()
        hud.position = 'top'
        counter = HudCounterNode()
        counter.strip = 'digits.png'
        counter.bind = '{lives}'
        counter.x = 0
        counter.y = 0
        counter.digits = 2
        hud.add_child(counter)
        scene.add_child(hud)
        checkpoint = PrefabNode('checkpoint')
        checkpoint.tag = 'checkpoint'
        bgm = SoundNode('bgm-level')
        bgm.src = 'music.ogg'
        bgm.trigger = 'scene.start'
        scene.add_child(bgm)
        return scene, checkpoint

    def test_respawn_restores_sprite(self, codegen, output_dir):
        scene, checkpoint = self._scene_with_checkpoint()
        codegen.generate(scene, prefabs=[checkpoint], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        respawn = script[script.find('func _respawn_at_checkpoint'):]
        assert 'hframes = 5' in respawn
        assert 'frame = 0' in respawn
        assert 'flip_h = false' in respawn

    def test_respawn_restores_process_mode(self, codegen, output_dir):
        scene, checkpoint = self._scene_with_checkpoint()
        codegen.generate(scene, prefabs=[checkpoint], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        respawn = script[script.find('func _respawn_at_checkpoint'):]
        assert 'PROCESS_MODE_INHERIT' in respawn

    def test_respawn_updates_lives_hud(self, codegen, output_dir):
        scene, checkpoint = self._scene_with_checkpoint()
        codegen.generate(scene, prefabs=[checkpoint], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        respawn = script[script.find('func _respawn_at_checkpoint'):]
        assert 'update_label("lives"' in respawn


class TestCompoundCollisionAction:
    """Collision actions with ';' should generate multiple statements."""

    def test_emit_and_destroy(self, codegen, output_dir):
        scene = SceneNode('main')
        player = SpriteNode('mario')
        player.src = 'mario.png'
        col = OnCollisionNode()
        col.with_tag = 'coin'
        col.action = 'emit:coin-collected;destroy'
        player.add_child(col)
        scene.add_child(player)
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'emit_event("coin-collected"' in script
        assert 'body.queue_free()' in script

    def test_single_action_still_works(self, codegen, output_dir):
        scene = SceneNode('main')
        player = SpriteNode('mario')
        player.src = 'mario.png'
        col = OnCollisionNode()
        col.with_tag = 'enemy'
        col.action = 'emit:enemy-hit'
        player.add_child(col)
        scene.add_child(player)
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'emit_event("enemy-hit"' in script

    def test_destroy_alias(self, codegen, output_dir):
        """'destroy' should work same as 'destroy-other'."""
        scene = SceneNode('main')
        player = SpriteNode('mario')
        player.src = 'mario.png'
        col = OnCollisionNode()
        col.with_tag = 'powerup'
        col.action = 'destroy'
        player.add_child(col)
        scene.add_child(player)
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'body.queue_free()' in script


class TestDynamicSpriteRegistration:
    """When prefab instances exist, register all children dynamically."""

    def test_dynamic_registration_with_instances(self, codegen, output_dir):
        scene = SceneNode('main')
        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.controls = 'platformer'
        scene.add_child(player)
        rex = PrefabNode('rex')
        rex.defeated_by = 'stomp'
        inst = InstanceNode('rex1')
        inst.x = 200; inst.y = 300
        scene.add_child(inst)
        codegen.generate(scene, prefabs=[rex], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        # Should use dynamic loop, not individual register
        assert 'for child in get_children()' in script
        assert 'register_sprite(child.name, child)' in script

    def test_static_registration_without_instances(self, codegen, output_dir):
        scene = SceneNode('main')
        player = SpriteNode('mario')
        player.src = 'mario.png'
        scene.add_child(player)
        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        # No instances → individual register
        assert 'register_sprite("mario"' in script
        assert 'for child in get_children()' not in script


class TestParitySpawnPuff:
    """_spawn_puff should use global_position, Image texture, set_parallel."""

    def _scene_with_stomp(self):
        scene = SceneNode('main')
        scene.death_sequence = 'smw'
        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.controls = 'platformer'
        scene.add_child(player)
        rex = PrefabNode('rex')
        rex.defeated_by = 'stomp'
        rex.stomp_bounce = -200
        return scene, rex

    def test_puff_uses_global_position(self, codegen, output_dir):
        scene, rex = self._scene_with_stomp()
        codegen.generate(scene, prefabs=[rex], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        puff = script[script.find('func _spawn_puff'):]
        assert 'global_position' in puff

    def test_puff_creates_image_texture(self, codegen, output_dir):
        scene, rex = self._scene_with_stomp()
        codegen.generate(scene, prefabs=[rex], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        puff = script[script.find('func _spawn_puff'):]
        assert 'Image.create(8, 8' in puff
        assert 'ImageTexture.create_from_image' in puff

    def test_puff_uses_set_parallel(self, codegen, output_dir):
        scene, rex = self._scene_with_stomp()
        codegen.generate(scene, prefabs=[rex], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        puff = script[script.find('func _spawn_puff'):]
        assert 'set_parallel(true)' in puff
        assert 'set_parallel(false)' in puff


# ==========================================================================
# EnemyNode Codegen Tests
# ==========================================================================

class TestEnemyCodegen:
    """Test code generation from EnemyNode definitions."""

    def _make_enemy_scene(self):
        """Create scene with prefab + EnemyNode + instances."""
        scene = SceneNode('main')
        scene.width = 3840
        scene.height = 600
        scene.death_sequence = 'smw'

        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.controls = 'platformer'
        scene.add_child(player)

        # Prefab (visual only)
        rex = PrefabNode('rex')
        rex.entity_type = 'enemy'
        sprite = SpriteNode('rex_body')
        sprite.src = 'rex.png'
        sprite.tag = 'enemy'
        sprite.body = 'dynamic'
        sprite.collision_layer = 2
        sprite.collision_mask = 1
        anim = AnimationNode('walk')
        anim.frames = '0-1'
        anim.speed = 0.15
        anim.loop = True
        anim.auto_play = True
        sprite.add_child(anim)
        rex.add_child(sprite)
        scene.add_child(rex)

        # Enemy (behavior)
        enemy = EnemyNode('rex')
        ai = EnemyAiNode()
        ai.ai_type = 'patrol'
        ai.speed = 30.0
        ai.turn_cooldown = 0.15
        ai.turn_on_edge = True
        ai.facing = 'left'
        enemy.ai = ai

        defeat = EnemyDefeatNode()
        defeat.by = 'stomp'
        defeat.health = 2
        defeat.bounce = -200
        on_hit = EnemyOnHitNode()
        on_hit.score = 100
        on_hit.effect = 'squish'
        on_hit.speed_multiply = 1.6
        defeat.on_hit = on_hit
        on_kill = EnemyOnKillNode()
        on_kill.score = 200
        on_kill.effect = 'puff'
        defeat.on_kill = on_kill
        enemy.defeat = defeat
        scene.add_child(enemy)

        # Instances
        inst1 = InstanceNode('rex')
        inst1.instance_id = 'rex1'
        inst1.x = 416
        inst1.y = 370
        scene.add_child(inst1)

        return scene, rex, enemy

    def test_enemy_script_ai_data(self, codegen, output_dir):
        scene, rex, enemy = self._make_enemy_scene()
        codegen.generate(scene, prefabs=[rex], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_rex.gd').read_text(encoding='utf-8')
        assert 'patrol_speed' in script
        assert '30.0' in script
        assert '_turn_cooldown' in script
        assert '0.15' in script

    def test_enemy_script_squish(self, codegen, output_dir):
        scene, rex, enemy = self._make_enemy_scene()
        codegen.generate(scene, prefabs=[rex], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_rex.gd').read_text(encoding='utf-8')
        assert '_health' in script
        assert '_is_squished' in script
        assert 'func stomp' in script

    def test_enemy_stomp_scores_data_driven(self, codegen, output_dir):
        scene, rex, enemy = self._make_enemy_scene()
        codegen.generate(scene, prefabs=[rex], output_dir=output_dir)
        # Prefab script should have data-driven scores
        script = Path(output_dir, 'scripts', 'prefab_rex.gd').read_text(encoding='utf-8')
        assert '"score": 100' in script
        assert '"score": 200' in script

    def test_enemy_meta_key_per_prefab(self, codegen, output_dir):
        scene, rex, enemy = self._make_enemy_scene()
        codegen.generate(scene, prefabs=[rex], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        # Should use prefab-specific meta key, not hardcoded "rex_squished"
        assert 'rex_squished' in script

    def test_enemy_bounce_from_defeat(self, codegen, output_dir):
        scene, rex, enemy = self._make_enemy_scene()
        codegen.generate(scene, prefabs=[rex], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert '-200' in script

    def test_enemy_backward_compat(self, codegen, output_dir):
        """PrefabNode without EnemyNode should use legacy path."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600
        scene.death_sequence = 'smw'

        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.controls = 'platformer'
        scene.add_child(player)

        # Legacy prefab with attrs
        rex = PrefabNode('rex')
        rex.entity_type = 'enemy'
        rex.defeated_by = 'stomp'
        rex.health = 2
        rex.stomp_bounce = -200
        rex.movement = 'patrol'
        rex.move_speed = 50.0
        sprite = SpriteNode('rex_body')
        sprite.src = 'rex.png'
        sprite.tag = 'enemy'
        sprite.body = 'dynamic'
        rex.add_child(sprite)
        scene.add_child(rex)

        codegen.generate(scene, prefabs=[rex], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_rex.gd').read_text(encoding='utf-8')
        # Should use _write_prefab_script (legacy), not _write_enemy_script
        assert 'patrol_speed' in script
        # Scene script should use legacy stomp
        scene_script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        assert 'rex_squished' in scene_script

    def test_enemy_speed_multiply(self, codegen, output_dir):
        scene, rex, enemy = self._make_enemy_scene()
        codegen.generate(scene, prefabs=[rex], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_rex.gd').read_text(encoding='utf-8')
        assert '_squish_speed_mult' in script
        assert '1.6' in script

    def test_enemy_scene_handler_uses_qualified_patrol_speed(self, codegen, output_dir):
        """Scene handler must use enemy.patrol_speed, not bare patrol_speed."""
        scene, rex, enemy = self._make_enemy_scene()
        codegen.generate(scene, prefabs=[rex], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'scene_main.gd').read_text(encoding='utf-8')
        # Must reference enemy.patrol_speed (qualified), not bare patrol_speed
        assert 'enemy.patrol_speed' in script


# ================================================================
# BATCH SMW FEATURES TESTS
# ================================================================

class TestQblockTagDetection:
    """F1: Qblock prefab with tag='qblock' generates block script even without explicit content/hits."""

    def test_qblock_tag_generates_hit_method(self, codegen, output_dir):
        """A prefab with sprite tag='qblock' should generate hit() method via _write_block_script."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600

        qblock = PrefabNode('qblock')
        sprite = SpriteNode('qblock_body')
        sprite.src = 'qblock.png'
        sprite.frame_width = 16
        sprite.frame_height = 16
        sprite.tag = 'qblock'
        sprite.body = 'static'
        anim = AnimationNode('shine')
        anim.frames = '0,1,2,3'
        anim.speed = 0.15
        anim.loop = True
        anim.auto_play = True
        sprite.add_child(anim)
        qblock.add_child(sprite)

        codegen.generate(scene, prefabs=[qblock], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_qblock.gd').read_text(encoding='utf-8')
        assert 'func hit()' in script
        assert '_hits_remaining' in script
        assert '_content' in script
        assert '"coin"' in script  # default content

    def test_qblock_tag_defaults_coin_content_1_hit(self, codegen, output_dir):
        """Qblock without explicit content/hits defaults to coin/1."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600

        qblock = PrefabNode('qblock')
        sprite = SpriteNode('qblock_body')
        sprite.src = 'qblock.png'
        sprite.tag = 'qblock'
        sprite.body = 'static'
        qblock.add_child(sprite)

        codegen.generate(scene, prefabs=[qblock], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_qblock.gd').read_text(encoding='utf-8')
        assert '_hits_remaining: int = 1' in script or 'var _hits_remaining = 1' in script
        assert '"coin"' in script

    def test_qblock_with_explicit_content_uses_it(self, codegen, output_dir):
        """Qblock with explicit content='mushroom' uses that instead of default."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600

        qblock = PrefabNode('qblock')
        qblock.content = 'mushroom'
        qblock.hits = 1
        sprite = SpriteNode('qblock_body')
        sprite.src = 'qblock.png'
        sprite.tag = 'qblock'
        sprite.body = 'static'
        qblock.add_child(sprite)

        codegen.generate(scene, prefabs=[qblock], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_qblock.gd').read_text(encoding='utf-8')
        assert 'func hit()' in script
        assert '"mushroom"' in script


class TestShimmerEffect:
    """F3: Yoshi coin collectible uses shimmer instead of cos() spin."""

    def test_yoshi_coin_uses_shimmer_not_spin(self, codegen, output_dir):
        """Yoshi coin collectible should use modulate shimmer, not scale.x = cos()."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600

        yc = PrefabNode('yoshi_coin')
        yc.collectible = True
        yc.reward = 'score:1000'
        sprite = SpriteNode('yc_body')
        sprite.src = 'yoshi_coin.png'
        sprite.tag = 'yoshi_coin'
        sprite.sensor = True
        yc.add_child(sprite)

        codegen.generate(scene, prefabs=[yc], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_yoshi_coin.gd').read_text(encoding='utf-8')
        # Should NOT use cos() scale.x spin
        assert 'scale.x = cos(' not in script
        # Should use shimmer modulate
        assert 'modulate' in script


class TestChargeAI:
    """F4: Banzai Bill uses 'charge' AI type - horizontal flight without gravity."""

    def test_charge_ai_generates_no_gravity(self, codegen, output_dir):
        """Enemy with charge AI should move horizontally without gravity."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600

        bb = PrefabNode('banzai_bill')
        sprite = SpriteNode('bb_body')
        sprite.src = 'banzai_bill.png'
        sprite.tag = 'enemy'
        sprite.body = 'dynamic'
        sprite.collision_layer = 2
        sprite.collision_mask = 1
        bb.add_child(sprite)
        scene.add_child(bb)

        ai = EnemyAiNode()
        ai.ai_type = 'charge'
        ai.speed = 90.0
        ai.facing = 'left'
        defeat = EnemyDefeatNode()
        defeat.by = 'stomp'
        defeat.health = 1
        defeat.bounce = -250
        on_kill = EnemyOnKillNode()
        on_kill.score = 400
        on_kill.effect = 'puff'
        defeat.on_kill = on_kill
        enemy = EnemyNode('banzai_bill')
        enemy.ai = ai
        enemy.defeat = defeat
        scene.add_child(enemy)

        codegen.generate(scene, prefabs=[bb], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_banzai_bill.gd').read_text(encoding='utf-8')
        # Charge AI: horizontal flight, no gravity
        assert 'charge_speed' in script
        assert 'velocity.x' in script
        assert 'velocity.y = 0' in script or "velocity.y', '0'" in script
        # Should have stomp handler
        assert 'func stomp()' in script
        assert '400' in script  # kill score

    def test_charge_ai_destroys_offscreen(self, codegen, output_dir):
        """Charge enemy auto-destroys when far off-screen left."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600

        bb = PrefabNode('banzai_bill')
        sprite = SpriteNode('bb_body')
        sprite.src = 'banzai_bill.png'
        sprite.tag = 'enemy'
        sprite.body = 'dynamic'
        bb.add_child(sprite)
        scene.add_child(bb)

        ai = EnemyAiNode()
        ai.ai_type = 'charge'
        ai.speed = 90.0
        ai.facing = 'left'
        enemy = EnemyNode('banzai_bill')
        enemy.ai = ai
        scene.add_child(enemy)

        codegen.generate(scene, prefabs=[bb], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_banzai_bill.gd').read_text(encoding='utf-8')
        assert 'queue_free()' in script
        assert '-200' in script  # off-screen threshold


class TestSpinJump:
    """F5: Spin jump attribute generates spin jump logic in player controller."""

    def test_spin_jump_attr_in_player_controller(self, codegen, output_dir):
        """Player with spin-jump generates spin jump input handling."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600
        scene.death_sequence = 'smw'

        player = SpriteNode('mario')
        player.src = 'mario.png'
        player.frame_width = 16
        player.frame_height = 24
        player.body = 'dynamic'
        player.controls = 'arrows'
        player.speed = 1.5
        player.jump_force = 5.3
        player.tag = 'player'
        player.spin_jump = True
        idle = AnimationNode('idle')
        idle.frames = '0'
        walk = AnimationNode('walk')
        walk.frames = '1-3'
        jump = AnimationNode('jump')
        jump.frames = '4'
        player.add_child(idle)
        player.add_child(walk)
        player.add_child(jump)
        scene.add_child(player)

        codegen.generate(scene, output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'player_controller.gd').read_text(encoding='utf-8')
        assert 'spin_jump' in script


class TestFlyingBlock:
    """F6: Flying qblock generates oscillation + hit handler."""

    def test_flying_qblock_generates_oscillation(self, codegen, output_dir):
        """Prefab with flying=True generates sine wave movement."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600

        fqb = PrefabNode('flying_qblock')
        fqb.flying = True
        fqb.content = 'mushroom'
        fqb.hits = 1
        sprite = SpriteNode('fqb_body')
        sprite.src = 'qblock.png'
        sprite.tag = 'qblock'
        sprite.body = 'static'
        fqb.add_child(sprite)

        codegen.generate(scene, prefabs=[fqb], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_flying_qblock.gd').read_text(encoding='utf-8')
        assert 'sin(' in script
        assert 'func hit()' in script


class TestEmergeAI:
    """F7: Piranha Plant uses 'emerge' AI type - timer-based emerge/retract."""

    def test_emerge_ai_generates_timer_cycle(self, codegen, output_dir):
        """Enemy with emerge AI generates emerge/retract cycle script."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600

        pp = PrefabNode('piranha_plant')
        sprite = SpriteNode('pp_body')
        sprite.src = 'piranha_plant.png'
        sprite.frame_width = 16
        sprite.frame_height = 16
        sprite.tag = 'hazard'
        sprite.body = 'static'
        sprite.sensor = True
        sprite.collision_layer = 2
        sprite.collision_mask = 1
        pp.add_child(sprite)
        scene.add_child(pp)

        ai = EnemyAiNode()
        ai.ai_type = 'emerge'
        ai.speed = 1.5  # emerge speed
        defeat = EnemyDefeatNode()
        defeat.by = 'fire'
        defeat.health = 1
        enemy = EnemyNode('piranha_plant')
        enemy.ai = ai
        enemy.defeat = defeat
        scene.add_child(enemy)

        codegen.generate(scene, prefabs=[pp], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_piranha_plant.gd').read_text(encoding='utf-8')
        assert '_emerged' in script
        assert 'emerge_height' in script
        assert '_player_near' in script
        assert 'safe_distance' in script
        assert '_retracting' in script

    def test_emerge_ai_has_die_method(self, codegen, output_dir):
        """Emerge enemy should have die() method."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600

        pp = PrefabNode('piranha_plant')
        sprite = SpriteNode('pp_body')
        sprite.src = 'piranha_plant.png'
        sprite.tag = 'hazard'
        sprite.body = 'static'
        sprite.sensor = True
        pp.add_child(sprite)
        scene.add_child(pp)

        ai = EnemyAiNode()
        ai.ai_type = 'emerge'
        enemy = EnemyNode('piranha_plant')
        enemy.ai = ai
        scene.add_child(enemy)

        codegen.generate(scene, prefabs=[pp], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_piranha_plant.gd').read_text(encoding='utf-8')
        assert 'func die()' in script


class TestMushroomPipeline:
    """F8: Mushroom power-up pipeline test."""

    def test_qblock_mushroom_content_codegen(self, codegen, output_dir):
        """Qblock with content='mushroom' generates correct block script."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600

        qblock = PrefabNode('qblock')
        qblock.content = 'mushroom'
        qblock.hits = 1
        sprite = SpriteNode('qb_body')
        sprite.src = 'qblock.png'
        sprite.tag = 'qblock'
        sprite.body = 'static'
        qblock.add_child(sprite)

        codegen.generate(scene, prefabs=[qblock], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_qblock.gd').read_text(encoding='utf-8')
        assert '"mushroom"' in script
        assert 'block-hit' in script


class TestCollectibleDataDriven:
    """F10: Data-driven collectibles with escalating score."""

    def test_yoshi_coin_escalating_score(self, codegen, output_dir):
        """Yoshi coin collectible should emit event with escalating score support."""
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600

        yc = PrefabNode('yoshi_coin')
        yc.collectible = True
        yc.reward = 'score:1000'
        sprite = SpriteNode('yc_body')
        sprite.src = 'yoshi_coin.png'
        sprite.tag = 'yoshi_coin'
        sprite.sensor = True
        yc.add_child(sprite)

        codegen.generate(scene, prefabs=[yc], output_dir=output_dir)
        script = Path(output_dir, 'scripts', 'prefab_yoshi_coin.gd').read_text(encoding='utf-8')
        assert 'yoshi_coin-collected' in script
        assert '1000' in script
