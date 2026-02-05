"""
Tests for Game Engine 2D Parser

Verifies that game XML (qg: namespace) is correctly parsed into Game AST nodes.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.parser import QuantumParser, QuantumParseError
from core.ast_nodes import ApplicationNode
from core.features.game_engine_2d.src.ast_nodes import (
    SceneNode, SpriteNode, PhysicsNode, ColliderNode, AnimationNode,
    CameraNode, InputNode, SoundNode, ParticleNode, TimerNode,
    SpawnNode, HudNode, TweenNode, BehaviorNode, UseNode,
    PrefabNode, InstanceNode, GroupNode,
    StateMachineNode, StateNode, TransitionNode, ClickableNode,
)


@pytest.fixture
def parser():
    return QuantumParser()


class TestGameNamespaceInjection:
    """Test automatic namespace injection for qg: prefix."""

    def test_auto_inject_qg_namespace(self, parser):
        src = '''<q:application id="test" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:sprite id="player" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        assert isinstance(ast, ApplicationNode)
        assert ast.app_type == 'game'
        assert ast.engine == '2d'

    def test_game_app_has_scenes(self, parser):
        src = '''<q:application id="test" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:sprite id="s1" src="a.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        assert len(ast.scenes) == 1
        assert isinstance(ast.scenes[0], SceneNode)
        assert ast.scenes[0].name == 'main'


class TestSceneParsing:
    """Test <qg:scene> parsing."""

    def test_scene_attributes(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="level1" width="1280" height="720" background="#87CEEB">
                <qg:sprite id="p" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        assert scene.width == 1280
        assert scene.height == 720
        assert scene.background == '#87CEEB'

    def test_scene_children(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:physics gravity-y="9.8" bounds="canvas" />
                <qg:sprite id="player" src="p.png" x="100" y="200" body="dynamic" controls="wasd" speed="5" />
                <qg:sprite id="ground" src="g.png" x="400" y="580" width="800" height="40" body="static" />
                <qg:camera follow="player" lerp="0.1" bounds="scene" />
                <q:set name="score" value="0" type="integer" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        types = [type(c).__name__ for c in scene.children]
        assert 'PhysicsNode' in types
        assert 'SpriteNode' in types
        assert 'CameraNode' in types
        assert 'SetNode' in types


class TestSpriteParsing:
    """Test <qg:sprite> parsing."""

    def test_sprite_basic(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:sprite id="hero" src="hero.png" x="100" y="200"
                           body="dynamic" bounce="0.3" friction="0.5"
                           controls="wasd" speed="5" jump-force="12"
                           tag="player" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        sprites = [c for c in scene.children if isinstance(c, SpriteNode)]
        assert len(sprites) == 1
        s = sprites[0]
        assert s.sprite_id == 'hero'
        assert s.src == 'hero.png'
        assert s.x == 100
        assert s.y == 200
        assert s.body == 'dynamic'
        assert s.bounce == 0.3
        assert s.friction == 0.5
        assert s.controls == 'wasd'
        assert s.speed == 5.0
        assert s.jump_force == 12.0
        assert s.tag == 'player'

    def test_sprite_children(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:sprite id="hero" src="hero.png" x="0" y="0" frame-width="32" frame-height="32">
                    <qg:animation name="idle" frames="0-3" speed="0.15" auto-play="true" />
                    <qg:animation name="walk" frames="4-11" speed="0.08" />
                    <qg:collider shape="box" />
                    <qg:use behavior="Damageable" health="5" />
                </qg:sprite>
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        sprites = [c for c in scene.children if isinstance(c, SpriteNode)]
        s = sprites[0]
        assert s.frame_width == 32
        assert s.frame_height == 32
        child_types = [type(c).__name__ for c in s.children]
        assert child_types.count('AnimationNode') == 2
        assert 'ColliderNode' in child_types
        assert 'UseNode' in child_types


class TestPhysicsParsing:
    def test_physics_attributes(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:physics gravity-x="0" gravity-y="9.8" bounds="canvas" debug="true" />
                <qg:sprite id="p" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        physics = [c for c in scene.children if isinstance(c, PhysicsNode)]
        assert len(physics) == 1
        p = physics[0]
        assert p.gravity_x == 0
        assert p.gravity_y == 9.8
        assert p.bounds == 'canvas'
        assert p.debug is True


class TestBehaviorParsing:
    """Test <qg:behavior> and <qg:use> parsing."""

    def test_behavior_with_state_and_functions(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:behavior name="Collectible">
                <q:set name="value" value="10" />
                <q:function name="onCollect">
                    <q:set name="score" value="{score + self.value}" scope="scene" />
                </q:function>
            </qg:behavior>
            <qg:scene name="main" width="800" height="600">
                <qg:sprite id="p" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        assert len(ast.behaviors) == 1
        b = ast.behaviors[0]
        assert isinstance(b, BehaviorNode)
        assert b.name == 'Collectible'
        assert len(b.children) == 2  # SetNode + FunctionNode

    def test_use_with_overrides(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:sprite id="coin" src="coin.png" x="100" y="200">
                    <qg:use behavior="Collectible" value="50" on-collision="onCollect" />
                </qg:sprite>
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        sprites = [c for c in scene.children if isinstance(c, SpriteNode)]
        s = sprites[0]
        uses = [c for c in s.children if isinstance(c, UseNode)]
        assert len(uses) == 1
        u = uses[0]
        assert u.behavior == 'Collectible'
        assert u.overrides.get('value') == '50'
        assert u.on_collision == 'onCollect'


class TestPrefabParsing:
    """Test <qg:prefab> and <qg:instance> parsing."""

    def test_prefab_and_instance(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:prefab name="Coin">
                <qg:sprite src="coin.png" body="dynamic" sensor="true" tag="coin">
                    <qg:use behavior="Collectible" value="10" on-collision="onCollect" />
                </qg:sprite>
            </qg:prefab>
            <qg:scene name="main" width="800" height="600">
                <qg:instance prefab="Coin" x="300" y="350" />
                <qg:instance prefab="Coin" x="500" y="350" />
                <qg:sprite id="p" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        assert len(ast.prefabs) == 1
        p = ast.prefabs[0]
        assert isinstance(p, PrefabNode)
        assert p.name == 'Coin'
        scene = ast.scenes[0]
        instances = [c for c in scene.children if isinstance(c, InstanceNode)]
        assert len(instances) == 2
        assert instances[0].prefab == 'Coin'
        assert instances[0].x == 300


class TestGroupParsing:
    def test_group_with_children(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:group name="coins" tag="collectible">
                    <qg:sprite id="c1" src="coin.png" x="100" y="200" />
                    <qg:sprite id="c2" src="coin.png" x="200" y="200" />
                </qg:group>
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        groups = [c for c in scene.children if isinstance(c, GroupNode)]
        assert len(groups) == 1
        g = groups[0]
        assert g.name == 'coins'
        assert g.tag == 'collectible'
        assert len(g.children) == 2


class TestStateMachineParsing:
    def test_state_machine_in_behavior(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:behavior name="Patrol">
                <q:set name="speed" value="2" />
                <qg:state-machine initial="walk-right">
                    <qg:state name="walk-right">
                        <qg:on event="hit-wall" transition="walk-left" />
                        <q:function name="update">
                            <q:set name="self.x" value="{self.x + self.speed}" />
                        </q:function>
                    </qg:state>
                    <qg:state name="walk-left">
                        <qg:on event="hit-wall" transition="walk-right" />
                        <q:function name="update">
                            <q:set name="self.x" value="{self.x - self.speed}" />
                        </q:function>
                    </qg:state>
                </qg:state-machine>
            </qg:behavior>
            <qg:scene name="main" width="800" height="600">
                <qg:sprite id="p" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        b = ast.behaviors[0]
        sm_nodes = [c for c in b.children if isinstance(c, StateMachineNode)]
        assert len(sm_nodes) == 1
        sm = sm_nodes[0]
        assert sm.initial == 'walk-right'
        assert len(sm.states) == 2
        assert sm.states[0].name == 'walk-right'
        assert len(sm.states[0].transitions) == 1
        assert sm.states[0].transitions[0].event == 'hit-wall'
        assert sm.states[0].transitions[0].transition == 'walk-left'


class TestInputParsing:
    def test_custom_input(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:input key="space" action="restart" type="press" />
                <qg:sprite id="p" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        inputs = [c for c in scene.children if isinstance(c, InputNode)]
        assert len(inputs) == 1
        assert inputs[0].key == 'space'
        assert inputs[0].action == 'restart'


class TestSoundParsing:
    def test_sound_attributes(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:sound id="bgm" src="music.mp3" volume="0.4" loop="true"
                          trigger="scene.start" channel="music" />
                <qg:sprite id="p" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        sounds = [c for c in scene.children if isinstance(c, SoundNode)]
        assert len(sounds) == 1
        s = sounds[0]
        assert s.sound_id == 'bgm'
        assert s.src == 'music.mp3'
        assert s.volume == 0.4
        assert s.loop is True
        assert s.trigger == 'scene.start'
        assert s.channel == 'music'


class TestHudParsing:
    def test_hud_position(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:hud position="top-left">
                    <text style="color:white">Score: {score}</text>
                </qg:hud>
                <qg:sprite id="p" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        huds = [c for c in scene.children if isinstance(c, HudNode)]
        assert len(huds) == 1
        assert huds[0].position == 'top-left'


class TestValidation:
    def test_scene_validation(self):
        scene = SceneNode('')
        errors = scene.validate()
        assert any('name' in e.lower() for e in errors)

    def test_sprite_invalid_body(self):
        s = SpriteNode('test')
        s.body = 'invalid'
        errors = s.validate()
        assert any('body type' in e.lower() for e in errors)

    def test_prefab_no_children(self):
        p = PrefabNode('Empty')
        errors = p.validate()
        assert any('child' in e.lower() for e in errors)

    def test_state_machine_missing_initial(self):
        sm = StateMachineNode('nonexistent')
        sm.add_state(StateNode('idle'))
        errors = sm.validate()
        assert any('not found' in e.lower() for e in errors)

    def test_clickable_no_action(self):
        c = ClickableNode()
        errors = c.validate()
        assert any('action' in e.lower() for e in errors)


class TestClickableParsing:
    """Test <qg:clickable> parsing."""

    def test_clickable_in_sprite(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:sprite id="btn" src="btn.png" x="400" y="300">
                    <qg:clickable action="onClick" cursor="pointer" />
                </qg:sprite>
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        sprites = [c for c in scene.children if isinstance(c, SpriteNode)]
        s = sprites[0]
        clickables = [c for c in s.children if isinstance(c, ClickableNode)]
        assert len(clickables) == 1
        assert clickables[0].action == 'onClick'
        assert clickables[0].cursor == 'pointer'

    def test_clickable_default_cursor(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:sprite id="btn" src="btn.png" x="0" y="0">
                    <qg:clickable action="doSomething" />
                </qg:sprite>
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        sprites = [c for c in scene.children if isinstance(c, SpriteNode)]
        clickables = [c for c in sprites[0].children if isinstance(c, ClickableNode)]
        assert clickables[0].cursor == 'pointer'

    def test_clickable_crosshair_cursor(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:sprite id="target" src="t.png" x="0" y="0">
                    <qg:clickable action="onShoot" cursor="crosshair" />
                </qg:sprite>
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        sprites = [c for c in scene.children if isinstance(c, SpriteNode)]
        clickables = [c for c in sprites[0].children if isinstance(c, ClickableNode)]
        assert clickables[0].cursor == 'crosshair'
