"""
Tests for Game Engine 2D Code Generator

Verifies that Game AST nodes compile correctly to JavaScript/HTML.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.parser import QuantumParser
from core.features.game_engine_2d.src.ast_nodes import (
    SceneNode, SpriteNode, PhysicsNode, CameraNode, BehaviorNode,
    PrefabNode, InstanceNode, GroupNode, UseNode, HudNode,
    SoundNode, InputNode, AnimationNode, ColliderNode, TimerNode,
    TweenNode, StateMachineNode, StateNode, TransitionNode,
    ParticleNode,
)
from core.features.state_management.src.ast_node import SetNode
from core.features.functions.src.ast_node import FunctionNode
from core.features.game_engine_2d.src.ast_nodes import RawCodeNode, TilemapLayerNode, SpawnNode, ClickableNode
from runtime.game_code_generator import GameCodeGenerator


@pytest.fixture
def parser():
    return QuantumParser()


@pytest.fixture
def codegen():
    return GameCodeGenerator()


class TestBasicGeneration:
    """Test basic HTML/JS generation."""

    def test_generates_html(self, codegen):
        scene = SceneNode('main')
        scene.width = 800
        scene.height = 600
        scene.background = '#000'
        sprite = SpriteNode('player')
        sprite.src = 'player.png'
        sprite.x = 100
        sprite.y = 200
        scene.add_child(sprite)
        html = codegen.generate(scene)
        assert '<!DOCTYPE html>' in html
        assert 'pixi' in html.lower()
        assert 'matter' in html.lower()
        assert 'player.png' in html

    def test_standalone_html_structure(self, codegen):
        scene = SceneNode('test')
        sprite = SpriteNode('s1')
        sprite.src = 'test.png'
        scene.add_child(sprite)
        html = codegen.generate(scene)
        assert '<html>' in html
        assert '<head>' in html
        assert '<body>' in html
        assert '<script' in html
        assert 'PIXI.Application' in html

    def test_pixi_app_dimensions(self, codegen):
        scene = SceneNode('main')
        scene.width = 1280
        scene.height = 720
        sprite = SpriteNode('s1')
        sprite.src = 'a.png'
        scene.add_child(sprite)
        html = codegen.generate(scene)
        assert 'width: 1280' in html
        assert 'height: 720' in html


class TestSpriteGeneration:
    """Test sprite JS code generation."""

    def test_sprite_creation(self, codegen):
        scene = SceneNode('main')
        s = SpriteNode('hero')
        s.src = 'hero.png'
        s.x = 100
        s.y = 200
        scene.add_child(s)
        html = codegen.generate(scene)
        assert 'PIXI.Sprite.from("hero.png")' in html
        assert '_spr_hero.x = 100' in html
        assert '_spr_hero.y = 200' in html

    def test_sprite_with_body(self, codegen):
        scene = SceneNode('main')
        s = SpriteNode('box')
        s.src = 'box.png'
        s.x = 50
        s.y = 50
        s.width = 32
        s.height = 32
        s.body = 'static'
        scene.add_child(s)
        html = codegen.generate(scene)
        assert 'Matter.Bodies.rectangle' in html
        assert 'isStatic: true' in html

    def test_dynamic_body(self, codegen):
        scene = SceneNode('main')
        s = SpriteNode('ball')
        s.src = 'ball.png'
        s.x = 100
        s.y = 100
        s.body = 'dynamic'
        s.bounce = 0.8
        scene.add_child(s)
        html = codegen.generate(scene)
        assert 'isStatic: false' in html
        assert 'restitution: 0.8' in html


class TestPhysicsGeneration:
    def test_physics_gravity(self, codegen):
        scene = SceneNode('main')
        p = PhysicsNode()
        p.gravity_x = 0
        p.gravity_y = 9.8
        p.bounds = 'canvas'
        scene.add_child(p)
        sprite = SpriteNode('s')
        sprite.src = 'a.png'
        scene.add_child(sprite)
        html = codegen.generate(scene)
        assert 'mEngine.gravity.x = 0' in html
        assert 'mEngine.gravity.y = 9.8' in html
        assert 'Matter.Engine.update' in html


class TestInputGeneration:
    def test_wasd_controls(self, codegen):
        scene = SceneNode('main')
        s = SpriteNode('player')
        s.src = 'p.png'
        s.controls = 'wasd'
        s.speed = 5
        s.body = 'dynamic'
        scene.add_child(s)
        html = codegen.generate(scene)
        assert '_controlledSprites' in html
        assert "left: 'a'" in html or 'left: \'a\'' in html
        assert 'setVelocity' in html

    def test_custom_input(self, codegen):
        scene = SceneNode('main')
        inp = InputNode()
        inp.key = 'space'
        inp.action = 'restart'
        inp.input_type = 'press'
        scene.add_child(inp)
        sprite = SpriteNode('s')
        sprite.src = 'a.png'
        scene.add_child(sprite)
        html = codegen.generate(scene)
        assert '"space"' in html
        assert 'restart' in html


class TestCameraGeneration:
    def test_camera_follow(self, codegen):
        scene = SceneNode('main')
        cam = CameraNode()
        cam.follow = 'player'
        cam.lerp = 0.1
        cam.bounds = 'scene'
        scene.add_child(cam)
        s = SpriteNode('player')
        s.src = 'p.png'
        scene.add_child(s)
        html = codegen.generate(scene)
        assert 'updateCamera' in html
        assert '"player"' in html
        assert '0.1' in html


class TestBehaviorGeneration:
    def test_behavior_class(self, codegen):
        scene = SceneNode('main')
        s = SpriteNode('coin')
        s.src = 'coin.png'
        use = UseNode('Collectible')
        use.overrides = {'value': '10'}
        s.add_child(use)
        scene.add_child(s)

        beh = BehaviorNode('Collectible')
        sv = SetNode('value')
        sv.value = '10'
        sv.type = 'integer'
        beh.add_child(sv)
        fn = FunctionNode('onCollect')
        beh.add_child(fn)

        html = codegen.generate(scene, behaviors=[beh])
        assert 'class Collectible' in html
        assert 'this.value = 10' in html
        assert 'onCollect' in html

    def test_behavior_attachment(self, codegen):
        scene = SceneNode('main')
        s = SpriteNode('coin')
        s.src = 'coin.png'
        use = UseNode('Collectible')
        use.overrides = {'value': '50'}
        use.on_collision = 'onCollect'
        s.add_child(use)
        scene.add_child(s)

        beh = BehaviorNode('Collectible')
        beh.add_child(SetNode('value'))
        fn = FunctionNode('onCollect')
        beh.add_child(fn)

        html = codegen.generate(scene, behaviors=[beh])
        assert 'new Collectible' in html
        assert 'collisionHandlers' in html


class TestPrefabGeneration:
    def test_prefab_instance(self, codegen):
        scene = SceneNode('main')
        inst = InstanceNode('Coin')
        inst.x = 300
        inst.y = 400
        scene.add_child(inst)

        prefab = PrefabNode('Coin')
        ps = SpriteNode('coin')
        ps.src = 'coin.png'
        ps.body = 'dynamic'
        ps.sensor = True
        prefab.add_child(ps)

        html = codegen.generate(scene, prefabs=[prefab])
        assert 'coin.png' in html
        assert '300' in html
        assert '400' in html
        assert 'isSensor: true' in html


class TestGroupGeneration:
    def test_group_sprites(self, codegen):
        scene = SceneNode('main')
        group = GroupNode('coins')
        s1 = SpriteNode('c1')
        s1.src = 'coin.png'
        s1.x = 100
        s1.y = 200
        s2 = SpriteNode('c2')
        s2.src = 'coin.png'
        s2.x = 200
        s2.y = 200
        group.add_child(s1)
        group.add_child(s2)
        scene.add_child(group)
        html = codegen.generate(scene)
        assert 'c1' in html
        assert 'c2' in html


class TestHudGeneration:
    def test_hud_html(self, codegen):
        from core.ast_nodes import HTMLNode, TextNode
        scene = SceneNode('main')
        hud = HudNode()
        hud.position = 'top-left'
        text_node = HTMLNode('text', {'style': 'color:white'}, [TextNode('Score: {score}')])
        hud.add_child(text_node)
        scene.add_child(hud)
        s = SpriteNode('s')
        s.src = 'a.png'
        scene.add_child(s)
        html = codegen.generate(scene)
        assert 'qg-hud-top-left' in html
        assert 'Score:' in html

    def test_hud_update(self, codegen):
        from core.ast_nodes import HTMLNode, TextNode
        scene = SceneNode('main')
        hud = HudNode()
        hud.position = 'top-left'
        hud.add_child(HTMLNode('text', {}, [TextNode('{score}')]))
        scene.add_child(hud)
        s = SpriteNode('s')
        s.src = 'a.png'
        scene.add_child(s)
        html = codegen.generate(scene)
        assert '_updateHUD' in html


class TestSoundGeneration:
    def test_sound_loading(self, codegen):
        scene = SceneNode('main')
        snd = SoundNode('bgm')
        snd.src = 'music.mp3'
        snd.volume = 0.5
        snd.loop = True
        snd.trigger = 'scene.start'
        snd.channel = 'music'
        scene.add_child(snd)
        s = SpriteNode('s')
        s.src = 'a.png'
        scene.add_child(s)
        html = codegen.generate(scene)
        assert '_loadSound' in html
        assert 'music.mp3' in html
        assert '_playSound' in html


class TestStateVars:
    def test_state_compilation(self, codegen):
        scene = SceneNode('main')
        sv = SetNode('score')
        sv.value = '0'
        sv.type = 'integer'
        scene.add_child(sv)
        s = SpriteNode('s')
        s.src = 'a.png'
        scene.add_child(s)
        html = codegen.generate(scene)
        assert 'let score = 0;' in html


class TestFullPipeline:
    """Test parsing + code generation end-to-end."""

    def test_parse_and_generate(self, parser):
        src = '''<q:application id="test-game" type="game" engine="2d">
            <qg:behavior name="Collectible">
                <q:set name="value" value="10" />
                <q:function name="onCollect">
                    <q:set name="score" value="{score + self.value}" scope="scene" />
                </q:function>
            </qg:behavior>
            <qg:prefab name="Coin">
                <qg:sprite src="coin.png" body="dynamic" sensor="true" tag="coin">
                    <qg:use behavior="Collectible" value="10" on-collision="onCollect" />
                </qg:sprite>
            </qg:prefab>
            <qg:scene name="level1" width="1280" height="720" background="#87CEEB">
                <qg:physics gravity-y="9.8" bounds="canvas" />
                <q:set name="score" value="0" type="integer" />
                <qg:camera follow="player" lerp="0.1" bounds="scene" />
                <qg:sprite id="player" src="hero.png" x="100" y="400"
                           controls="wasd" speed="5" jump-force="12" body="dynamic" />
                <qg:sprite id="ground" src="ground.png" x="640" y="700"
                           width="1280" height="40" body="static" tag="solid" />
                <qg:instance prefab="Coin" x="300" y="350" />
                <qg:instance prefab="Coin" x="500" y="350" />
                <qg:hud position="top-left">
                    <text style="font-size:24px; color:white">Score: {score}</text>
                </qg:hud>
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        gen = GameCodeGenerator()
        html = gen.generate(
            scene=ast.scenes[0],
            behaviors=ast.behaviors,
            prefabs=ast.prefabs,
            title=ast.app_id,
        )
        assert '<!DOCTYPE html>' in html
        assert 'PIXI.Application' in html
        assert 'Matter.Engine.create' in html
        assert 'class Collectible' in html
        assert 'hero.png' in html
        assert 'coin.png' in html
        assert 'let score = 0;' in html
        assert 'updateCamera' in html
        assert 'qg-hud-top-left' in html
        assert '_updateHUD' in html


class TestJsSyntaxValidation:
    """Validate that generated JS has correct syntax structure."""

    def _extract_js(self, html: str) -> str:
        """Extract JS content from the generated HTML."""
        import re
        match = re.search(r'<script>\s*(.*?)\s*</script>', html, re.DOTALL)
        return match.group(1) if match else ''

    def _count_balanced(self, text: str, open_char: str, close_char: str) -> bool:
        """Check that open/close characters are balanced (ignoring strings)."""
        count = 0
        in_str = None
        escape = False
        for ch in text:
            if escape:
                escape = False
                continue
            if ch == '\\':
                escape = True
                continue
            if ch in ('"', "'", '`'):
                if in_str is None:
                    in_str = ch
                elif in_str == ch:
                    in_str = None
                continue
            if in_str:
                continue
            if ch == open_char:
                count += 1
            elif ch == close_char:
                count -= 1
        return count == 0

    def test_braces_balanced(self, codegen):
        scene = SceneNode('main')
        s = SpriteNode('player')
        s.src = 'p.png'
        s.body = 'dynamic'
        s.controls = 'wasd'
        s.speed = 5
        scene.add_child(s)

        beh = BehaviorNode('Test')
        sv = SetNode('hp')
        sv.value = '10'
        sv.type = 'integer'
        beh.add_child(sv)
        fn = FunctionNode('hit')
        beh.add_child(fn)

        html = codegen.generate(scene, behaviors=[beh])
        js = self._extract_js(html)
        assert self._count_balanced(js, '{', '}'), "Braces are unbalanced"

    def test_parens_balanced(self, codegen):
        scene = SceneNode('main')
        s = SpriteNode('p')
        s.src = 'p.png'
        s.body = 'dynamic'
        scene.add_child(s)
        html = codegen.generate(scene)
        js = self._extract_js(html)
        assert self._count_balanced(js, '(', ')'), "Parentheses are unbalanced"

    def test_brackets_balanced(self, codegen):
        scene = SceneNode('main')
        s = SpriteNode('p')
        s.src = 'p.png'
        s.body = 'dynamic'
        scene.add_child(s)
        html = codegen.generate(scene)
        js = self._extract_js(html)
        assert self._count_balanced(js, '[', ']'), "Brackets are unbalanced"

    def test_no_eval_in_output(self, codegen):
        """Ensure no eval() calls appear in generated code."""
        scene = SceneNode('main')
        s = SpriteNode('p')
        s.src = 'p.png'
        scene.add_child(s)
        snd = SoundNode('sfx')
        snd.src = 'a.wav'
        snd.trigger = 'scene.start'
        scene.add_child(snd)
        timer = TimerNode('t1')
        timer.interval = 1.0
        timer.action = 'tick'
        timer.auto_start = True
        scene.add_child(timer)
        html = codegen.generate(scene)
        js = self._extract_js(html)
        assert 'eval(' not in js

    def test_no_innerhtml_in_hud(self, codegen):
        """HUD must use textContent, not innerHTML."""
        from core.ast_nodes import HTMLNode, TextNode
        scene = SceneNode('main')
        hud = HudNode()
        hud.position = 'top-left'
        hud.add_child(HTMLNode('text', {}, [TextNode('{score}')]))
        scene.add_child(hud)
        s = SpriteNode('s')
        s.src = 'a.png'
        scene.add_child(s)
        html = codegen.generate(scene)
        js = self._extract_js(html)
        assert 'innerHTML' not in js
        assert 'textContent' in js


class TestAnimationGeneration:
    """Test animation system code generation."""

    def test_animation_registration(self, codegen):
        scene = SceneNode('main')
        s = SpriteNode('player')
        s.src = 'hero.png'
        s.frame_width = 32
        s.frame_height = 32
        anim = AnimationNode('idle')
        anim.frames = '0-3'
        anim.speed = 0.15
        anim.auto_play = True
        s.add_child(anim)
        scene.add_child(s)
        html = codegen.generate(scene)
        assert '_registerAnimation' in html
        assert '"idle"' in html
        assert '"0-3"' in html

    def test_animation_system_functions(self, codegen):
        scene = SceneNode('main')
        s = SpriteNode('player')
        s.src = 'hero.png'
        s.frame_width = 32
        s.frame_height = 32
        anim = AnimationNode('walk')
        anim.frames = '4-11'
        anim.speed = 0.1
        s.add_child(anim)
        scene.add_child(s)
        html = codegen.generate(scene)
        assert '_switchAnimation' in html
        assert '_updateControlAnimations' in html
        assert 'PIXI.Rectangle' in html


class TestTweenGeneration:
    """Test tween system code generation."""

    def test_tween_instance(self, codegen):
        scene = SceneNode('main')
        tw = TweenNode('tw1')
        tw.target = 'player'
        tw.property = 'alpha'
        tw.to_value = 0
        tw.duration = 1.0
        tw.easing = 'easeOut'
        tw.auto_start = True
        scene.add_child(tw)
        s = SpriteNode('player')
        s.src = 'p.png'
        scene.add_child(s)
        html = codegen.generate(scene)
        assert '_createTween' in html
        assert '"easeOut"' in html
        assert '_updateTweens' in html

    def test_easing_functions_present(self, codegen):
        scene = SceneNode('main')
        tw = TweenNode('tw1')
        tw.target = 'x'
        tw.property = 'x'
        tw.to_value = 100
        tw.duration = 1.0
        tw.auto_start = True
        scene.add_child(tw)
        s = SpriteNode('x')
        s.src = 'a.png'
        scene.add_child(s)
        html = codegen.generate(scene)
        assert 'easeIn' in html
        assert 'easeOut' in html
        assert 'easeInOut' in html
        assert 'bounce' in html.lower() or 'Bounce' in html


class TestParticleGeneration:
    """Test particle system code generation."""

    def test_particle_instance(self, codegen):
        scene = SceneNode('main')
        p = ParticleNode('dust')
        p.follow = 'player'
        p.count = 15
        p.emit_rate = 8
        p.lifetime = 0.4
        p.trigger = 'player.walk'
        scene.add_child(p)
        s = SpriteNode('player')
        s.src = 'p.png'
        scene.add_child(s)
        html = codegen.generate(scene)
        assert '_createParticleSystem' in html
        assert '_updateParticles' in html
        assert '"dust"' in html

    def test_particle_pool_system(self, codegen):
        scene = SceneNode('main')
        p = ParticleNode('sparks')
        p.count = 20
        p.emit_rate = 10
        p.lifetime = 0.5
        scene.add_child(p)
        s = SpriteNode('s')
        s.src = 'a.png'
        scene.add_child(s)
        html = codegen.generate(scene)
        assert 'PIXI.Graphics' in html
        assert 'pool' in html.lower() or '_particles' in html


class TestAudioGeneration:
    """Test audio system code generation."""

    def test_audio_unlock_pattern(self, codegen):
        scene = SceneNode('main')
        snd = SoundNode('bgm')
        snd.src = 'music.mp3'
        snd.volume = 0.4
        snd.loop = True
        snd.trigger = 'scene.start'
        scene.add_child(snd)
        s = SpriteNode('s')
        s.src = 'a.png'
        scene.add_child(s)
        html = codegen.generate(scene)
        assert 'AudioContext' in html
        assert '_loadSound' in html
        assert '_playSound' in html
        # Must handle autoplay unlock
        assert 'click' in html or 'keydown' in html


class TestExpressionSafety:
    """Test that expression compilation is safe."""

    def test_safe_expression(self, codegen):
        scene = SceneNode('main')
        sv = SetNode('score')
        sv.value = '0'
        sv.type = 'integer'
        scene.add_child(sv)
        fn = FunctionNode('addScore')
        set_stmt = SetNode('score')
        set_stmt.value = '{score + 10}'
        fn.body = [set_stmt]
        scene.add_child(fn)
        s = SpriteNode('s')
        s.src = 'a.png'
        scene.add_child(s)
        html = codegen.generate(scene)
        assert 'score + 10' in html
        assert 'let score = 0;' in html

    def test_hud_xss_prevention(self, codegen):
        """Ensure HUD content is sanitized."""
        from core.ast_nodes import HTMLNode, TextNode
        scene = SceneNode('main')
        hud = HudNode()
        hud.position = 'top-left'
        hud.add_child(HTMLNode('text', {}, [TextNode('<script>alert(1)</script>')]))
        scene.add_child(hud)
        s = SpriteNode('s')
        s.src = 'a.png'
        scene.add_child(s)
        html = codegen.generate(scene)
        # Script tag should be escaped in HUD HTML
        assert '<script>alert(1)</script>' not in html
        assert '&lt;script&gt;' in html


# =============================================================================
# NEW TESTS - Expression, Event Bus, Game API, RawCode, Collision Tag, etc.
# =============================================================================


class TestExpressionCompilerEnhancements:
    """Test enhanced expression compiler with array access, ternary, triple equals."""

    def test_array_access_expression(self, codegen):
        scene = SceneNode('main')
        sv = SetNode('items')
        sv.value = '0'
        sv.type = 'integer'
        scene.add_child(sv)
        fn = FunctionNode('getFirst')
        set_stmt = SetNode('result')
        set_stmt.value = '{items[0]}'
        fn.body = [set_stmt]
        scene.add_child(fn)
        s = SpriteNode('s')
        s.src = 'a.png'
        scene.add_child(s)
        html = codegen.generate(scene)
        assert 'items[0]' in html

    def test_ternary_expression(self, codegen):
        scene = SceneNode('main')
        fn = FunctionNode('check')
        set_stmt = SetNode('msg')
        set_stmt.value = "{x > 0 ? 'yes' : 'no'}"
        fn.body = [set_stmt]
        scene.add_child(fn)
        s = SpriteNode('s')
        s.src = 'a.png'
        scene.add_child(s)
        html = codegen.generate(scene)
        assert "x > 0 ? 'yes' : 'no'" in html

    def test_triple_equals(self, codegen):
        scene = SceneNode('main')
        fn = FunctionNode('check')
        set_stmt = SetNode('active')
        set_stmt.value = "{state === 'active'}"
        fn.body = [set_stmt]
        scene.add_child(fn)
        s = SpriteNode('s')
        s.src = 'a.png'
        scene.add_child(s)
        html = codegen.generate(scene)
        assert "state === 'active'" in html


class TestEventBus:
    """Test event bus generation."""

    def test_event_bus_generated(self, codegen):
        scene = SceneNode('main')
        s = SpriteNode('s')
        s.src = 'a.png'
        scene.add_child(s)
        html = codegen.generate(scene)
        assert '_gameEvents' in html
        assert '_gameEvents.on' in html
        assert '_gameEvents.emit' in html

    def test_sound_trigger_event_bus(self, codegen):
        scene = SceneNode('main')
        snd = SoundNode('jump_sfx')
        snd.src = 'jump.wav'
        snd.trigger = 'player.jump'
        snd.volume = 1.0
        scene.add_child(snd)
        s = SpriteNode('s')
        s.src = 'a.png'
        scene.add_child(s)
        html = codegen.generate(scene)
        assert '_gameEvents.on("player.jump"' in html

    def test_jump_emits_event(self, codegen):
        scene = SceneNode('main')
        s = SpriteNode('player')
        s.src = 'p.png'
        s.controls = 'wasd'
        s.speed = 5
        s.body = 'dynamic'
        scene.add_child(s)
        html = codegen.generate(scene)
        assert "_gameEvents.emit('player.jump'" in html


class TestGameAPI:
    """Test game API object generation."""

    def test_game_object_generated(self, codegen):
        scene = SceneNode('main')
        s = SpriteNode('s')
        s.src = 'a.png'
        scene.add_child(s)
        html = codegen.generate(scene)
        assert 'const game = ' in html

    def test_game_destroy_method(self, codegen):
        scene = SceneNode('main')
        s = SpriteNode('s')
        s.src = 'a.png'
        scene.add_child(s)
        html = codegen.generate(scene)
        assert 'game.destroy' in html

    def test_game_play_method(self, codegen):
        scene = SceneNode('main')
        s = SpriteNode('s')
        s.src = 'a.png'
        scene.add_child(s)
        html = codegen.generate(scene)
        assert 'game.play' in html

    def test_game_camera_shake(self, codegen):
        scene = SceneNode('main')
        s = SpriteNode('s')
        s.src = 'a.png'
        scene.add_child(s)
        html = codegen.generate(scene)
        assert 'game.camera.shake' in html


class TestRawCodeNode:
    """Test RawCodeNode emission."""

    def test_raw_code_in_function(self, codegen):
        scene = SceneNode('main')
        fn = FunctionNode('onHit')
        fn.body = [RawCodeNode('game.destroy(self);')]
        scene.add_child(fn)
        s = SpriteNode('s')
        s.src = 'a.png'
        scene.add_child(s)
        html = codegen.generate(scene)
        assert 'game.destroy(self);' in html

    def test_raw_code_mixed_with_set(self, codegen):
        scene = SceneNode('main')
        fn = FunctionNode('onCollect')
        set_node = SetNode('score')
        set_node.value = '{score + 10}'
        fn.body = [
            set_node,
            RawCodeNode('game.destroy(self);'),
        ]
        scene.add_child(fn)
        s = SpriteNode('s')
        s.src = 'a.png'
        scene.add_child(s)
        html = codegen.generate(scene)
        assert 'score + 10' in html
        assert 'game.destroy(self);' in html


class TestCollisionTagFilter:
    """Test collision tag filtering."""

    def test_collision_tag_filter(self, codegen):
        scene = SceneNode('main')
        s = SpriteNode('player')
        s.src = 'p.png'
        s.body = 'dynamic'
        use = UseNode('Collectible')
        use.on_collision = 'onCollect'
        use.collision_tag = 'coin'
        s.add_child(use)
        scene.add_child(s)

        beh = BehaviorNode('Collectible')
        fn = FunctionNode('onCollect')
        beh.add_child(fn)

        html = codegen.generate(scene, behaviors=[beh])
        assert 'other.tag !== "coin"' in html

    def test_collision_no_tag_fires_always(self, codegen):
        scene = SceneNode('main')
        s = SpriteNode('player')
        s.src = 'p.png'
        s.body = 'dynamic'
        use = UseNode('Collectible')
        use.on_collision = 'onCollect'
        # No collision_tag set
        s.add_child(use)
        scene.add_child(s)

        beh = BehaviorNode('Collectible')
        fn = FunctionNode('onCollect')
        beh.add_child(fn)

        html = codegen.generate(scene, behaviors=[beh])
        # Should NOT have a tag filter
        assert 'other.tag !==' not in html
        assert 'collisionHandlers' in html


class TestParticleTriggers:
    """Test particle trigger wiring."""

    def test_particle_trigger_wired(self, codegen):
        scene = SceneNode('main')
        p = ParticleNode('dust')
        p.follow = 'player'
        p.trigger = 'player.walk'
        p.count = 10
        scene.add_child(p)
        s = SpriteNode('player')
        s.src = 'p.png'
        scene.add_child(s)
        html = codegen.generate(scene)
        assert '_gameEvents.on("player.walk"' in html

    def test_particle_scene_start(self, codegen):
        scene = SceneNode('main')
        p = ParticleNode('ambient')
        p.trigger = 'scene.start'
        p.count = 20
        scene.add_child(p)
        s = SpriteNode('s')
        s.src = 'a.png'
        scene.add_child(s)
        html = codegen.generate(scene)
        # scene.start triggers should activate directly, not via event bus
        assert '_activateParticles("ambient")' in html


class TestSpawnCodegen:
    """Test spawn system code generation."""

    def test_spawn_codegen(self, codegen):
        scene = SceneNode('main')
        spawn = SpawnNode('enemy_spawner')
        spawn.prefab = 'Enemy'
        spawn.pool_size = 5
        spawn.x = '100'
        spawn.y = '0'
        scene.add_child(spawn)
        s = SpriteNode('s')
        s.src = 'a.png'
        scene.add_child(s)
        html = codegen.generate(scene)
        assert '_createSpawner' in html
        assert '"enemy_spawner"' in html

    def test_spawn_with_prefab(self, codegen):
        scene = SceneNode('main')
        spawn = SpawnNode('coin_spawner')
        spawn.prefab = 'Coin'
        spawn.pool_size = 10
        scene.add_child(spawn)
        s = SpriteNode('s')
        s.src = 'a.png'
        scene.add_child(s)
        html = codegen.generate(scene)
        assert '"Coin"' in html


class TestTilemapVisual:
    """Test tilemap visual rendering."""

    def test_tilemap_visual_sprites(self, codegen):
        from core.features.game_engine_2d.src.ast_nodes import TilemapNode, TilemapLayerNode
        scene = SceneNode('main')
        tm = TilemapNode('map1')
        tm.src = 'tileset.png'
        tm.tile_width = 32
        tm.tile_height = 32
        visual_layer = TilemapLayerNode('ground')
        visual_layer.collision = False
        visual_layer.data = '1,2,3\n4,5,6'
        tm.add_layer(visual_layer)
        scene.add_child(tm)
        s = SpriteNode('s')
        s.src = 'a.png'
        scene.add_child(s)
        html = codegen.generate(scene)
        assert 'PIXI.Rectangle' in html
        assert 'PIXI.Texture' in html
        assert '_tileData_map1_ground' in html

    def test_tilemap_collision_still_works(self, codegen):
        from core.features.game_engine_2d.src.ast_nodes import TilemapNode, TilemapLayerNode
        scene = SceneNode('main')
        tm = TilemapNode('map1')
        tm.tile_width = 32
        tm.tile_height = 32
        col_layer = TilemapLayerNode('walls')
        col_layer.collision = True
        col_layer.data = '1,0\n0,1'
        tm.add_layer(col_layer)
        scene.add_child(tm)
        s = SpriteNode('s')
        s.src = 'a.png'
        scene.add_child(s)
        html = codegen.generate(scene)
        # Collision layer generates invisible bodies
        assert 'isStatic: true' in html
        assert 'tilemap-collision' in html


class TestClickableGeneration:
    """Test clickable sprite code generation."""

    def test_clickable_emits_event_mode(self, codegen):
        scene = SceneNode('main')
        s = SpriteNode('btn')
        s.src = 'btn.png'
        s.x = 400
        s.y = 300
        click = ClickableNode()
        click.action = 'onClick'
        click.cursor = 'pointer'
        s.add_child(click)
        scene.add_child(s)
        html = codegen.generate(scene)
        assert "eventMode" in html
        assert "'static'" in html

    def test_clickable_emits_cursor(self, codegen):
        scene = SceneNode('main')
        s = SpriteNode('btn')
        s.src = 'btn.png'
        click = ClickableNode()
        click.action = 'onClick'
        click.cursor = 'crosshair'
        s.add_child(click)
        scene.add_child(s)
        html = codegen.generate(scene)
        assert '"crosshair"' in html

    def test_clickable_emits_pointerdown(self, codegen):
        scene = SceneNode('main')
        s = SpriteNode('btn')
        s.src = 'btn.png'
        click = ClickableNode()
        click.action = 'onClick'
        s.add_child(click)
        scene.add_child(s)
        html = codegen.generate(scene)
        assert "pointerdown" in html
        assert "onClick" in html

    def test_clickable_safe_action_reference(self, codegen):
        scene = SceneNode('main')
        s = SpriteNode('btn')
        s.src = 'btn.png'
        click = ClickableNode()
        click.action = 'handleClick'
        s.add_child(click)
        scene.add_child(s)
        html = codegen.generate(scene)
        assert "typeof handleClick === 'function'" in html


class TestMouseSystemGeneration:
    """Test mouse tracking system code generation."""

    def test_mouse_tracking_vars(self, codegen):
        scene = SceneNode('main')
        s = SpriteNode('s')
        s.src = 'a.png'
        scene.add_child(s)
        html = codegen.generate(scene)
        assert '_mouseX' in html
        assert '_mouseY' in html
        assert '_mouseWorldX' in html
        assert '_mouseWorldY' in html

    def test_mouse_pointermove_listener(self, codegen):
        scene = SceneNode('main')
        s = SpriteNode('s')
        s.src = 'a.png'
        scene.add_child(s)
        html = codegen.generate(scene)
        assert 'pointermove' in html
