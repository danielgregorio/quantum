"""
Tests for Game Engine 2D Parser

Verifies that game XML (qg: namespace) is correctly parsed into Game AST nodes.
"""

import pytest
import sys
from pathlib import Path


from quantum.core.parser import QuantumParser, QuantumParseError
from quantum.core.ast_nodes import ApplicationNode
from quantum.core.features.game_engine_2d.src.ast_nodes import (
    SceneNode, SpriteNode, PhysicsNode, ColliderNode, AnimationNode,
    CameraNode, InputNode, SoundNode, ParticleNode, TimerNode,
    SpawnNode, HudNode, TweenNode, BehaviorNode, UseNode,
    PrefabNode, InstanceNode, GroupNode, TilemapNode,
    StateMachineNode, StateNode, TransitionNode, ClickableNode,
    OnCollisionNode, EventNode,
    HudTileNode, HudCounterNode, HudCollectionNode,
    HudSlotNode, HudOptionNode, HudBehaviorNode, HudActionNode,
    SceneTransitionNode, PersistentNode, MapNodeDef, MapPathNode,
    EventActionNode, CollisionLayerDef,
    EnemyNode, EnemyAiNode, EnemyDefeatNode, EnemyOnHitNode, EnemyOnKillNode,
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


class TestPrefabSemanticParsing:
    """Test semantic attributes on <qg:prefab>."""

    def test_enemy_prefab_full(self, parser):
        """Test a fully-specified enemy prefab with combat + movement attributes."""
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:prefab name="Rex" type="enemy" health="2" defeated-by="stomp"
                       on-defeat="emit:enemy-killed" contact-damage="1" knockback="5.0"
                       i-frames="60" stomp-bounce="12.0"
                       movement="patrol" move-speed="2.5" turn-on-edge="true" facing="left"
                       reward-kill="score:200">
                <qg:sprite src="rex.png" body="dynamic" tag="enemy" />
            </qg:prefab>
            <qg:scene name="main" width="800" height="600">
                <qg:sprite id="p" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        p = ast.prefabs[0]
        assert isinstance(p, PrefabNode)
        assert p.name == 'Rex'
        # Classification
        assert p.entity_type == 'enemy'
        # Combat
        assert p.health == 2
        assert p.defeated_by == 'stomp'
        assert p.on_defeat == 'emit:enemy-killed'
        assert p.contact_damage == 1
        assert p.knockback == 5.0
        assert p.i_frames == 60
        assert p.stomp_bounce == 12.0
        # Movement
        assert p.movement == 'patrol'
        assert p.move_speed == 2.5
        assert p.turn_on_edge is True
        assert p.facing == 'left'
        # Reward
        assert p.reward_kill == 'score:200'

    def test_item_prefab(self, parser):
        """Test an item prefab with effect and collectible attributes."""
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:prefab name="Mushroom" type="item" effect="grow"
                       auto-move="true" collectible="true" reward="score:100">
                <qg:sprite src="mushroom.png" body="dynamic" tag="powerup" />
            </qg:prefab>
            <qg:scene name="main" width="800" height="600">
                <qg:sprite id="p" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        p = ast.prefabs[0]
        assert p.entity_type == 'item'
        assert p.effect == 'grow'
        assert p.auto_move is True
        assert p.collectible is True
        assert p.reward == 'score:100'

    def test_block_prefab(self, parser):
        """Test a block prefab with content and breakable attributes."""
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:prefab name="QuestionBlock" type="block" content="mushroom"
                       hits="1" breakable="false" invisible="false">
                <qg:sprite src="qblock.png" body="static" tag="block" />
            </qg:prefab>
            <qg:scene name="main" width="800" height="600">
                <qg:sprite id="p" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        p = ast.prefabs[0]
        assert p.entity_type == 'block'
        assert p.content == 'mushroom'
        assert p.hits == 1
        assert p.breakable is False
        assert p.invisible is False

    def test_prefab_defaults_when_no_semantic_attrs(self, parser):
        """Existing prefabs without semantic attrs keep None defaults."""
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:prefab name="Coin">
                <qg:sprite src="coin.png" body="dynamic" sensor="true" tag="coin" />
            </qg:prefab>
            <qg:scene name="main" width="800" height="600">
                <qg:sprite id="p" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        p = ast.prefabs[0]
        assert p.name == 'Coin'
        assert p.entity_type is None
        assert p.health is None
        assert p.defeated_by is None
        assert p.movement is None
        assert p.effect is None
        assert p.content is None
        assert p.breakable is None
        assert p.collectible is None
        assert p.reward is None
        assert p.hits is None

    def test_hazard_prefab(self, parser):
        """Test a hazard entity type."""
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:prefab name="Spike" type="hazard" contact-damage="1">
                <qg:sprite src="spike.png" body="static" tag="hazard" />
            </qg:prefab>
            <qg:scene name="main" width="800" height="600">
                <qg:sprite id="p" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        p = ast.prefabs[0]
        assert p.entity_type == 'hazard'
        assert p.contact_damage == 1
        assert p.health is None  # Hazards don't need health

    def test_respawn_attributes(self, parser):
        """Test respawn-related attributes."""
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:prefab name="Goomba" type="enemy" health="1" defeated-by="stomp"
                       respawns="true" respawn-delay="5.0">
                <qg:sprite src="goomba.png" body="dynamic" tag="enemy" />
            </qg:prefab>
            <qg:scene name="main" width="800" height="600">
                <qg:sprite id="p" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        p = ast.prefabs[0]
        assert p.respawns is True
        assert p.respawn_delay == 5.0

    def test_item_with_duration_and_carryable(self, parser):
        """Test item with duration and carryable attributes."""
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:prefab name="Star" type="item" effect="invincible"
                       duration="10.0" collectible="true" carryable="false">
                <qg:sprite src="star.png" body="dynamic" tag="powerup" />
            </qg:prefab>
            <qg:scene name="main" width="800" height="600">
                <qg:sprite id="p" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        p = ast.prefabs[0]
        assert p.effect == 'invincible'
        assert p.duration == 10.0
        assert p.collectible is True
        assert p.carryable is False

    def test_invisible_block(self, parser):
        """Test invisible block that appears when hit."""
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:prefab name="HiddenBlock" type="block" content="coin"
                       hits="1" invisible="true">
                <qg:sprite src="empty.png" body="static" tag="block" />
            </qg:prefab>
            <qg:scene name="main" width="800" height="600">
                <qg:sprite id="p" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        p = ast.prefabs[0]
        assert p.invisible is True
        assert p.content == 'coin'
        assert p.hits == 1

    def test_prefab_to_dict_includes_semantic_attrs(self, parser):
        """Test that to_dict() includes semantic attrs when set."""
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:prefab name="Rex" type="enemy" health="2" defeated-by="stomp"
                       movement="patrol" move-speed="2.5">
                <qg:sprite src="rex.png" body="dynamic" tag="enemy" />
            </qg:prefab>
            <qg:scene name="main" width="800" height="600">
                <qg:sprite id="p" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        d = ast.prefabs[0].to_dict()
        assert d["entity_type"] == "enemy"
        assert d["health"] == 2
        assert d["defeated_by"] == "stomp"
        assert d["movement"] == "patrol"
        assert d["move_speed"] == 2.5
        # Unset fields should NOT appear in dict
        assert "effect" not in d
        assert "content" not in d
        assert "breakable" not in d

    def test_prefab_to_dict_excludes_none_attrs(self):
        """Test that to_dict() omits None-valued semantic attrs."""
        p = PrefabNode("Plain")
        p.children.append(SpriteNode("s"))
        d = p.to_dict()
        assert d == {"type": "game_prefab", "name": "Plain", "children_count": 1}

    def test_prefab_validate_invalid_entity_type(self):
        """Test validation rejects invalid entity_type."""
        p = PrefabNode("Bad")
        p.children.append(SpriteNode("s"))
        p.entity_type = "dragon"
        errors = p.validate()
        assert any("entity type" in e.lower() for e in errors)

    def test_prefab_validate_invalid_movement(self):
        """Test validation rejects invalid movement type."""
        p = PrefabNode("Bad")
        p.children.append(SpriteNode("s"))
        p.movement = "teleport"
        errors = p.validate()
        assert any("movement" in e.lower() for e in errors)

    def test_prefab_validate_invalid_defeated_by(self):
        """Test validation rejects invalid defeated-by value."""
        p = PrefabNode("Bad")
        p.children.append(SpriteNode("s"))
        p.defeated_by = "laser"
        errors = p.validate()
        assert any("defeated-by" in e.lower() for e in errors)

    def test_prefab_validate_negative_health(self):
        """Test validation rejects negative health."""
        p = PrefabNode("Bad")
        p.children.append(SpriteNode("s"))
        p.health = -1
        errors = p.validate()
        assert any("health" in e.lower() for e in errors)

    def test_prefab_validate_valid_semantic_attrs(self):
        """Test validation passes with valid semantic attrs."""
        p = PrefabNode("Good")
        p.children.append(SpriteNode("s"))
        p.entity_type = "enemy"
        p.health = 2
        p.defeated_by = "stomp"
        p.movement = "patrol"
        errors = p.validate()
        assert len(errors) == 0


class TestHudTileBasedParsing:
    """Test <qg:hud> tile-based declarative parsing."""

    def test_hud_tile(self, parser):
        """Test <qg:tile> inside <qg:hud>."""
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="256" height="224">
                <qg:hud background="rgba(0,0,0,0.5)" background-height="26">
                    <qg:tile sprite="mario_text.png" x="24" y="8" />
                </qg:hud>
                <qg:sprite id="p" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        huds = [c for c in scene.children if isinstance(c, HudNode)]
        assert len(huds) == 1
        hud = huds[0]
        assert hud.background == 'rgba(0,0,0,0.5)'
        assert hud.background_height == 26
        assert len(hud.children) == 1
        tile = hud.children[0]
        assert isinstance(tile, HudTileNode)
        assert tile.sprite == 'mario_text.png'
        assert tile.x == 24
        assert tile.y == 8

    def test_hud_counter(self, parser):
        """Test <qg:counter> with countdown and flash."""
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="256" height="224">
                <qg:hud background="rgba(0,0,0,0.5)">
                    <qg:counter strip="numbers.png" x="96" y="8" digits="3"
                               bind="{time_left}" countdown="true"
                               hurry-at="100" flash="red" />
                </qg:hud>
                <qg:sprite id="p" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        hud = [c for c in scene.children if isinstance(c, HudNode)][0]
        counter = hud.children[0]
        assert isinstance(counter, HudCounterNode)
        assert counter.strip == 'numbers.png'
        assert counter.digits == 3
        assert counter.bind == '{time_left}'
        assert counter.countdown is True
        assert counter.hurry_at == 100
        assert counter.flash == 'red'

    def test_hud_collection(self, parser):
        """Test <qg:collection> for repeated sprites."""
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="256" height="224">
                <qg:hud background="rgba(0,0,0,0.5)">
                    <qg:collection sprite="coin.png" x="148" y="8"
                                   spacing="8" max="5" bind="{yoshi_coins}" />
                </qg:hud>
                <qg:sprite id="p" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        hud = [c for c in scene.children if isinstance(c, HudNode)][0]
        col = hud.children[0]
        assert isinstance(col, HudCollectionNode)
        assert col.sprite == 'coin.png'
        assert col.spacing == 8
        assert col.max == 5
        assert col.bind == '{yoshi_coins}'

    def test_hud_slot_with_options(self, parser):
        """Test <qg:slot> with <qg:option> children."""
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="256" height="224">
                <qg:hud background="rgba(0,0,0,0.5)">
                    <qg:slot x="112" y="0" bind="{powerup}">
                        <qg:option value="mushroom" sprite="mushroom_icon.png" />
                        <qg:option value="flower" sprite="flower_icon.png" />
                    </qg:slot>
                </qg:hud>
                <qg:sprite id="p" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        hud = [c for c in scene.children if isinstance(c, HudNode)][0]
        slot = hud.children[0]
        assert isinstance(slot, HudSlotNode)
        assert slot.bind == '{powerup}'
        assert len(slot.options) == 2
        assert isinstance(slot.options[0], HudOptionNode)
        assert slot.options[0].value == 'mushroom'
        assert slot.options[0].sprite == 'mushroom_icon.png'
        assert slot.options[1].value == 'flower'

    def test_hud_behavior_with_action(self, parser):
        """Test <qg:hud-behavior> with <qg:action> children."""
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="256" height="224">
                <qg:hud background="rgba(0,0,0,0.5)">
                    <qg:hud-behavior target="time_left" event="reach" value="0">
                        <qg:action type="emit" event="time-up" />
                    </qg:hud-behavior>
                </qg:hud>
                <qg:sprite id="p" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        hud = [c for c in scene.children if isinstance(c, HudNode)][0]
        beh = hud.children[0]
        assert isinstance(beh, HudBehaviorNode)
        assert beh.target == 'time_left'
        assert beh.event == 'reach'
        assert beh.value == 0
        assert len(beh.actions) == 1
        action = beh.actions[0]
        assert isinstance(action, HudActionNode)
        assert action.action_type == 'emit'
        assert action.event == 'time-up'

    def test_hud_sprite_prefix(self, parser):
        """Test sprite-prefix resolves short names in tile children."""
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="256" height="224">
                <qg:hud sprite-prefix="assets/hud_" background="rgba(0,0,0,0.5)">
                    <qg:tile sprite="mario.png" x="0" y="0" />
                    <qg:tile sprite="assets/full/path.png" x="10" y="10" />
                </qg:hud>
                <qg:sprite id="p" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        hud = [c for c in scene.children if isinstance(c, HudNode)][0]
        assert hud.sprite_prefix == 'assets/hud_'
        # Prefix resolution happens in codegen, not parser
        # Parser preserves raw sprite values
        assert hud.children[0].sprite == 'mario.png'
        assert hud.children[1].sprite == 'assets/full/path.png'

    def test_hud_mixed_tile_and_html(self, parser):
        """Test HUD with both tile-based and HTML children (backward compat)."""
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="256" height="224">
                <qg:hud background="rgba(0,0,0,0.5)">
                    <qg:tile sprite="label.png" x="10" y="10" />
                </qg:hud>
                <qg:hud position="center">
                    <div id="game-over" style="display:none;">GAME OVER</div>
                </qg:hud>
                <qg:sprite id="p" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        huds = [c for c in scene.children if isinstance(c, HudNode)]
        assert len(huds) == 2
        # First HUD is tile-based
        assert huds[0].background == 'rgba(0,0,0,0.5)'
        assert isinstance(huds[0].children[0], HudTileNode)
        # Second HUD is HTML (legacy)
        assert huds[1].position == 'center'
        assert huds[1].background is None


# ============================================
# Multi-Scene Parsing Tests
# ============================================

class TestSceneTypeAndInitial:
    """Test SceneNode type and initial attributes."""

    def test_scene_type_default_is_level(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:sprite id="p" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        assert scene.scene_type == 'level'
        assert scene.initial is False

    def test_scene_type_title(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="title" type="title" initial="true" width="256" height="224">
                <qg:sprite id="bg" src="bg.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        assert scene.scene_type == 'title'
        assert scene.initial is True

    def test_scene_type_map(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="world-map" type="map" width="512" height="512">
                <qg:sprite id="bg" src="map.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        assert scene.scene_type == 'map'

    def test_scene_type_overlay(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="pause" type="overlay" width="256" height="224">
                <qg:sprite id="bg" src="pause.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        assert scene.scene_type == 'overlay'

    def test_scene_type_validation(self):
        scene = SceneNode('test')
        scene.scene_type = 'invalid'
        errors = scene.validate()
        assert any('Invalid scene type' in e for e in errors)


class TestSceneTransitionParsing:
    """Test <qg:transition> parsing."""

    def test_transition_basic(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="title" type="title" width="256" height="224">
                <qg:sprite id="bg" src="bg.png" x="0" y="0" />
                <qg:event name="press-start">
                    <qg:transition to="world-map" effect="fade" duration="0.5" />
                </qg:event>
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        events = [c for c in scene.children if isinstance(c, EventNode)]
        assert len(events) == 1
        event = events[0]
        assert event.name == 'press-start'
        assert len(event.children) == 1
        transition = event.children[0]
        assert isinstance(transition, SceneTransitionNode)
        assert transition.to == 'world-map'
        assert transition.effect == 'fade'
        assert transition.duration == 0.5

    def test_transition_iris_out(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="level" width="256" height="224">
                <qg:sprite id="p" src="p.png" x="0" y="0" />
                <qg:event name="level-complete">
                    <qg:transition to="world-map" effect="iris-out" duration="1.0" />
                </qg:event>
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        events = [c for c in scene.children if isinstance(c, EventNode)]
        transition = events[0].children[0]
        assert transition.effect == 'iris-out'
        assert transition.duration == 1.0

    def test_transition_default_effect(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="level" width="256" height="224">
                <qg:sprite id="p" src="p.png" x="0" y="0" />
                <qg:event name="done">
                    <qg:transition to="next-level" />
                </qg:event>
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        events = [c for c in scene.children if isinstance(c, EventNode)]
        transition = events[0].children[0]
        assert transition.effect == 'fade'
        assert transition.duration == 0.5

    def test_transition_with_data(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="level" width="256" height="224">
                <qg:sprite id="p" src="p.png" x="0" y="0" />
                <qg:event name="done">
                    <qg:transition to="next" data-score="100" data-level="2" />
                </qg:event>
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        events = [c for c in scene.children if isinstance(c, EventNode)]
        transition = events[0].children[0]
        assert transition.data == {'score': '100', 'level': '2'}

    def test_transition_validation(self):
        node = SceneTransitionNode('')
        errors = node.validate()
        assert any('target (to) is required' in e for e in errors)

        node2 = SceneTransitionNode('level')
        node2.effect = 'invalid'
        errors2 = node2.validate()
        assert any('Invalid transition effect' in e for e in errors2)

    def test_transition_to_dict(self):
        node = SceneTransitionNode('world-map')
        node.effect = 'iris-out'
        node.duration = 1.0
        d = node.to_dict()
        assert d['type'] == 'game_scene_transition'
        assert d['to'] == 'world-map'
        assert d['effect'] == 'iris-out'


class TestPersistentParsing:
    """Test <qg:persistent> parsing."""

    def test_persistent_basic(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:persistent>
                <q:set name="lives" value="5" type="integer" />
                <q:set name="score" value="0" type="integer" />
                <q:set name="coins" value="0" type="integer" />
            </qg:persistent>
            <qg:scene name="main" width="800" height="600">
                <qg:sprite id="p" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        assert len(ast.persistent) == 1
        persistent = ast.persistent[0]
        assert isinstance(persistent, PersistentNode)
        assert len(persistent.children) == 3

    def test_persistent_validation(self):
        node = PersistentNode()
        errors = node.validate()
        assert any('at least one child' in e for e in errors)

    def test_persistent_to_dict(self):
        node = PersistentNode()
        from quantum.core.features.state_management.src.ast_node import SetNode
        set_node = SetNode('lives')
        set_node.value = '5'
        node.add_child(set_node)
        d = node.to_dict()
        assert d['type'] == 'game_persistent'
        assert d['children_count'] == 1


class TestMapNodeParsing:
    """Test <qg:map-node> and <qg:map-path> parsing."""

    def test_map_node_basic(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="world-map" type="map" width="512" height="512">
                <qg:sprite id="bg" src="map.png" x="0" y="0" />
                <qg:map-node id="start" x="32" y="180" />
                <qg:map-node id="level-1" x="80" y="180" scene="level-1" icon="dot.png" />
                <qg:map-node id="level-2" x="128" y="160" scene="level-2" locked="true" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        map_nodes = [c for c in scene.children if isinstance(c, MapNodeDef)]
        assert len(map_nodes) == 3

        start = map_nodes[0]
        assert start.node_id == 'start'
        assert start.x == 32
        assert start.y == 180
        assert start.scene is None
        assert start.locked is False

        level1 = map_nodes[1]
        assert level1.scene == 'level-1'
        assert level1.icon == 'dot.png'

        level2 = map_nodes[2]
        assert level2.locked is True

    def test_map_path_basic(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="world-map" type="map" width="512" height="512">
                <qg:sprite id="bg" src="map.png" x="0" y="0" />
                <qg:map-node id="start" x="32" y="180" />
                <qg:map-node id="level-1" x="80" y="180" scene="level-1" />
                <qg:map-path from="start" to="level-1" />
                <qg:map-path from="level-1" to="level-2" unlock="level-1-cleared" direction="up" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        paths = [c for c in scene.children if isinstance(c, MapPathNode)]
        assert len(paths) == 2

        p1 = paths[0]
        assert p1.from_node == 'start'
        assert p1.to_node == 'level-1'
        assert p1.unlock is None

        p2 = paths[1]
        assert p2.from_node == 'level-1'
        assert p2.to_node == 'level-2'
        assert p2.unlock == 'level-1-cleared'
        assert p2.direction == 'up'

    def test_map_node_validation(self):
        node = MapNodeDef('')
        errors = node.validate()
        assert any('id is required' in e for e in errors)

    def test_map_path_validation(self):
        node = MapPathNode('', '')
        errors = node.validate()
        assert any('from_node is required' in e for e in errors)
        assert any('to_node is required' in e for e in errors)

    def test_map_node_to_dict(self):
        node = MapNodeDef('level-1')
        node.x = 80
        node.y = 180
        node.scene = 'level-1'
        d = node.to_dict()
        assert d['type'] == 'game_map_node'
        assert d['id'] == 'level-1'
        assert d['scene'] == 'level-1'

    def test_map_path_to_dict(self):
        node = MapPathNode('start', 'level-1')
        d = node.to_dict()
        assert d['type'] == 'game_map_path'
        assert d['from'] == 'start'
        assert d['to'] == 'level-1'


class TestMultiSceneApplication:
    """Test multi-scene game applications."""

    def test_multiple_scenes_with_types(self, parser):
        src = '''<q:application id="mario" type="game" engine="2d">
            <qg:persistent>
                <q:set name="lives" value="5" type="integer" />
            </qg:persistent>
            <qg:scene name="title" type="title" initial="true" width="256" height="224">
                <qg:sprite id="bg" src="title.png" x="0" y="0" />
                <qg:event name="start">
                    <qg:transition to="world-map" effect="fade" />
                </qg:event>
            </qg:scene>
            <qg:scene name="world-map" type="map" width="512" height="512">
                <qg:sprite id="bg" src="map.png" x="0" y="0" />
                <qg:map-node id="start" x="32" y="180" />
                <qg:map-node id="level-1" x="80" y="180" scene="level-1" />
                <qg:map-path from="start" to="level-1" />
            </qg:scene>
            <qg:scene name="level-1" type="level" width="5120" height="432">
                <qg:sprite id="player" src="mario.png" x="32" y="350" />
                <qg:event name="level-complete">
                    <qg:transition to="world-map" effect="iris-out" />
                </qg:event>
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        assert len(ast.scenes) == 3
        assert len(ast.persistent) == 1

        title = ast.scenes[0]
        assert title.scene_type == 'title'
        assert title.initial is True

        world_map = ast.scenes[1]
        assert world_map.scene_type == 'map'

        level = ast.scenes[2]
        assert level.scene_type == 'level'

    def test_event_with_inline_transition_and_handler(self, parser):
        """Events can have both handler and inline children."""
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:sprite id="p" src="p.png" x="0" y="0" />
                <qg:event name="done" handler="onDone" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        events = [c for c in scene.children if isinstance(c, EventNode)]
        assert events[0].handler == 'onDone'
        assert events[0].children == []


# ==========================================================================
# Phase 1: Collision Layer/Mask/Floor Angle Parser Tests
# ==========================================================================

class TestSpriteCollisionLayerParsing:
    """Test parsing of collision-layer, collision-mask, floor-max-angle on sprites."""

    def test_sprite_collision_layer_and_mask(self, parser):
        """Parse collision-layer and collision-mask attributes."""
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:sprite id="mario" src="mario.png" x="0" y="0"
                           body="dynamic" controls="arrows"
                           collision-layer="2" collision-mask="5" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        sprite = scene.children[0]
        assert isinstance(sprite, SpriteNode)
        assert sprite.collision_layer == 2
        assert sprite.collision_mask == 5

    def test_sprite_floor_max_angle(self, parser):
        """Parse floor-max-angle attribute."""
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:sprite id="mario" src="mario.png" x="0" y="0"
                           body="dynamic" controls="arrows"
                           floor-max-angle="70" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        sprite = ast.scenes[0].children[0]
        assert sprite.floor_max_angle == 70.0

    def test_sprite_collision_defaults_none(self, parser):
        """Without collision attrs, defaults are None."""
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:sprite id="p" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        sprite = ast.scenes[0].children[0]
        assert sprite.collision_layer is None
        assert sprite.collision_mask is None
        assert sprite.floor_max_angle is None


class TestPrefabTurnCooldownParsing:
    """Test parsing of turn-cooldown on prefabs."""

    def test_prefab_turn_cooldown(self, parser):
        """Parse turn-cooldown attribute."""
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:prefab name="rex" type="enemy" movement="patrol"
                           turn-cooldown="0.15">
                    <qg:sprite id="rex_body" src="rex.png" tag="enemy" body="dynamic" />
                </qg:prefab>
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        prefab = [c for c in scene.children if isinstance(c, PrefabNode)][0]
        assert prefab.turn_cooldown == 0.15

    def test_prefab_turn_cooldown_default_none(self, parser):
        """Without turn-cooldown, default is None."""
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:prefab name="goomba" type="enemy" movement="patrol">
                    <qg:sprite id="g_body" src="g.png" tag="enemy" body="dynamic" />
                </qg:prefab>
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        prefab = [c for c in ast.scenes[0].children if isinstance(c, PrefabNode)][0]
        assert prefab.turn_cooldown is None


class TestSceneDeathSequenceParsing:
    """Test parsing of death-sequence and death-timer on scenes."""

    def test_scene_death_sequence(self, parser):
        """Parse death-sequence and death-timer."""
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="level-1" type="level"
                       death-sequence="smw" death-timer="3.5"
                       width="800" height="600">
                <qg:sprite id="p" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        assert scene.death_sequence == 'smw'
        assert scene.death_timer == 3.5

    def test_scene_game_over_attrs(self, parser):
        """Parse game-over-jingle and game-over-alphabet."""
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="level-1" type="level"
                       death-sequence="smw"
                       game-over-jingle="gameover.ogg"
                       game-over-alphabet="hud_alphabet.png"
                       width="800" height="600">
                <qg:sprite id="p" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        assert scene.game_over_jingle == 'gameover.ogg'
        assert scene.game_over_alphabet == 'hud_alphabet.png'


class TestEventActionParsing:
    """Test parsing of EventActionNode inside events."""

    def test_event_with_inline_actions(self, parser):
        """Parse qg:action children inside qg:event."""
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:sprite id="p" src="p.png" x="0" y="0" />
                <qg:event name="coin-collected" handler="">
                    <qg:action type="score" amount="10" />
                    <qg:action type="sound" target="sfx-coin" />
                    <qg:action type="destroy" target="{data.other}" />
                </qg:event>
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        events = [c for c in scene.children if isinstance(c, EventNode)]
        assert len(events) == 1
        actions = [c for c in events[0].children if isinstance(c, EventActionNode)]
        assert len(actions) == 3
        assert actions[0].action_type == 'score'
        assert actions[0].amount == 10
        assert actions[1].action_type == 'sound'
        assert actions[1].target == 'sfx-coin'
        assert actions[2].action_type == 'destroy'


class TestCollisionLayerDefParsing:
    """Test parsing of named collision layers in physics."""

    def test_physics_collision_layers(self, parser):
        """Parse qg:collision-layer children inside qg:physics."""
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:physics gravity-y="1.5">
                    <qg:collision-layer id="1" name="world" />
                    <qg:collision-layer id="2" name="player" />
                    <qg:collision-layer id="4" name="enemies" />
                </qg:physics>
                <qg:sprite id="p" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        physics = [c for c in scene.children if isinstance(c, PhysicsNode)][0]
        assert physics.collision_layers == {'world': 1, 'player': 2, 'enemies': 4}
        assert len(physics.children) == 3
        assert isinstance(physics.children[0], CollisionLayerDef)


# ==========================================================================
# Tilemap data-src parsing
# ==========================================================================

class TestTilemapDataSrc:
    """Test tilemap data-src attribute parsing."""

    def test_tilemap_data_src_parsed(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:tilemap id="terrain" src="collision_tileset.tres"
                            data-src="tile_map.json"
                            tile-width="16" tile-height="16">
                    <qg:layer name="ground" collision="true" />
                </qg:tilemap>
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        tilemap = [c for c in scene.children if isinstance(c, TilemapNode)][0]
        assert tilemap.tilemap_id == 'terrain'
        assert tilemap.src == 'collision_tileset.tres'
        assert tilemap.data_src == 'tile_map.json'
        assert tilemap.tile_width == 16
        assert tilemap.tile_height == 16
        assert len(tilemap.layers) == 1
        assert tilemap.layers[0].name == 'ground'
        assert tilemap.layers[0].collision is True

    def test_tilemap_data_src_none_when_not_specified(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:tilemap id="world" src="tiles.png"
                            tile-width="32" tile-height="32">
                    <qg:layer name="bg" />
                </qg:tilemap>
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        tilemap = [c for c in scene.children if isinstance(c, TilemapNode)][0]
        assert tilemap.data_src is None


class TestEnemyParsing:
    """Test <qg:enemy> system parsing."""

    def test_enemy_basic_parse(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:enemy prefab="rex">
                    <qg:ai type="patrol" speed="30" />
                    <qg:defeat by="stomp" health="2" bounce="-200">
                        <qg:on-hit score="100" effect="squish" />
                        <qg:on-kill score="200" effect="puff" />
                    </qg:defeat>
                </qg:enemy>
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        enemies = [c for c in scene.children if isinstance(c, EnemyNode)]
        assert len(enemies) == 1
        enemy = enemies[0]
        assert enemy.prefab == 'rex'
        assert enemy.ai is not None
        assert enemy.defeat is not None

    def test_enemy_ai_attrs(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:enemy prefab="goomba">
                    <qg:ai type="patrol" speed="45" turn-cooldown="0.2"
                           turn-on-edge="true" facing="right" />
                </qg:enemy>
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        enemy = [c for c in scene.children if isinstance(c, EnemyNode)][0]
        ai = enemy.ai
        assert ai.ai_type == 'patrol'
        assert ai.speed == 45.0
        assert ai.turn_cooldown == 0.2
        assert ai.turn_on_edge is True
        assert ai.facing == 'right'

    def test_enemy_defeat_with_children(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:enemy prefab="rex">
                    <qg:defeat by="stomp" health="2" bounce="-250">
                        <qg:on-hit score="100" effect="squish" speed-multiply="1.6" />
                        <qg:on-kill score="200" effect="puff" drop="coin" />
                    </qg:defeat>
                </qg:enemy>
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        enemy = [c for c in scene.children if isinstance(c, EnemyNode)][0]
        d = enemy.defeat
        assert d.by == 'stomp'
        assert d.health == 2
        assert d.bounce == -250.0
        assert d.on_hit is not None
        assert d.on_hit.score == 100
        assert d.on_hit.effect == 'squish'
        assert d.on_hit.speed_multiply == 1.6
        assert d.on_kill is not None
        assert d.on_kill.score == 200
        assert d.on_kill.effect == 'puff'
        assert d.on_kill.drop == 'coin'

    def test_enemy_defaults(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:enemy prefab="beetle" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        enemy = [c for c in scene.children if isinstance(c, EnemyNode)][0]
        assert enemy.prefab == 'beetle'
        assert enemy.ai is None
        assert enemy.defeat is None

    def test_enemy_validate_invalid(self):
        enemy = EnemyNode('')
        errors = enemy.validate()
        assert any('prefab' in e.lower() for e in errors)

        ai = EnemyAiNode()
        ai.ai_type = 'invalid_type'
        errors = ai.validate()
        assert any('AI type' in e for e in errors)

        defeat = EnemyDefeatNode()
        defeat.by = 'laser'
        errors = defeat.validate()
        assert any('defeat by' in e.lower() for e in errors)

    def test_enemy_with_instance_placement(self, parser):
        src = '''<q:application id="g" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:prefab name="rex">
                    <qg:sprite id="rex_body" src="rex.png" tag="enemy" body="dynamic" />
                </qg:prefab>
                <qg:enemy prefab="rex">
                    <qg:ai type="patrol" speed="30" />
                    <qg:defeat by="stomp" health="2" />
                </qg:enemy>
                <qg:instance prefab="rex" id="rex1" x="416" y="370" />
                <qg:instance prefab="rex" id="rex2" x="560" y="370" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        scene = ast.scenes[0]
        prefabs = [c for c in scene.children if isinstance(c, PrefabNode)]
        enemies = [c for c in scene.children if isinstance(c, EnemyNode)]
        instances = [c for c in scene.children if isinstance(c, InstanceNode)]
        assert len(prefabs) == 1
        assert len(enemies) == 1
        assert len(instances) == 2
        assert enemies[0].prefab == 'rex'
        assert instances[0].prefab == 'rex'
