"""
Tests for Game Engine 2D - Integration / Builder tests

Tests the full pipeline: parse → build → HTML output.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.parser import QuantumParser
from core.ast_nodes import ApplicationNode
from runtime.game_builder import GameBuilder, GameBuildError


@pytest.fixture
def parser():
    return QuantumParser()


@pytest.fixture
def builder():
    return GameBuilder()


class TestGameBuilder:
    """Test the GameBuilder orchestrator."""

    def test_build_basic_game(self, parser, builder):
        src = '''<q:application id="basic" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:sprite id="player" src="player.png" x="100" y="200" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        html = builder.build(ast)
        assert '<!DOCTYPE html>' in html
        assert 'player.png' in html

    def test_build_no_scenes_raises(self, builder):
        app = ApplicationNode('empty', 'game')
        with pytest.raises(GameBuildError, match="No scenes found"):
            builder.build(app)

    def test_build_to_file(self, parser, builder, tmp_path):
        src = '''<q:application id="file-test" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:sprite id="p" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        out = tmp_path / "test_game.html"
        result = builder.build_to_file(ast, str(out))
        assert Path(result).exists()
        content = Path(result).read_text(encoding='utf-8')
        assert 'PIXI' in content

    def test_build_selects_active_scene(self, parser, builder):
        src = '''<q:application id="multi" type="game" engine="2d">
            <qg:scene name="menu" width="800" height="600" active="false">
                <qg:sprite id="title" src="title.png" x="400" y="300" />
            </qg:scene>
            <qg:scene name="level1" width="1280" height="720" active="true">
                <qg:sprite id="player" src="hero.png" x="100" y="400" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        html = builder.build(ast)
        assert 'hero.png' in html
        assert 'width: 1280' in html

    def test_full_platformer_build(self, parser, builder):
        src = '''<q:application id="platformer" type="game" engine="2d">
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
                <qg:group name="coins">
                    <qg:instance prefab="Coin" x="700" y="250" />
                    <qg:instance prefab="Coin" x="900" y="250" />
                </qg:group>
                <qg:sound id="bgm" src="music.mp3" volume="0.4" loop="true"
                          trigger="scene.start" channel="music" />
                <qg:hud position="top-left">
                    <text style="font-size:24px; color:white">Score: {score}</text>
                </qg:hud>
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        html = builder.build(ast)

        # Verify core structure
        assert '<!DOCTYPE html>' in html
        assert 'PIXI.Application' in html
        assert 'Matter.Engine.create' in html

        # Verify behaviors
        assert 'class Collectible' in html

        # Verify sprites
        assert 'hero.png' in html
        assert 'ground.png' in html
        assert 'coin.png' in html

        # Verify physics
        assert 'mEngine.gravity.y = 9.8' in html
        assert 'isStatic: true' in html  # ground
        assert 'isSensor: true' in html  # coins

        # Verify state
        assert 'let score = 0;' in html

        # Verify camera
        assert 'updateCamera' in html

        # Verify sound
        assert 'music.mp3' in html
        assert '_loadSound' in html

        # Verify HUD
        assert 'qg-hud-top-left' in html

        # Verify controls
        assert 'setVelocity' in html or '_keys' in html


class TestApplicationType:
    """Test that game type is correctly dispatched."""

    def test_game_type_parsed(self, parser):
        src = '''<q:application id="game" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:sprite id="p" src="p.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        assert isinstance(ast, ApplicationNode)
        assert ast.app_type == 'game'
        assert ast.engine == '2d'
        assert len(ast.scenes) == 1

    def test_non_game_app_unchanged(self, parser):
        src = '''<q:application id="web" type="html">
        </q:application>'''
        ast = parser.parse(src)
        assert ast.app_type == 'html'
        assert len(ast.scenes) == 0


class TestMultiSceneBuild:
    """Test multi-scene generation."""

    def test_multi_scene_generates_inits(self, parser, builder):
        src = '''<q:application id="multi-scene" type="game" engine="2d">
            <qg:scene name="level1" width="800" height="600" active="true">
                <qg:sprite id="player" src="hero.png" x="100" y="200" />
            </qg:scene>
            <qg:scene name="game-over" width="800" height="600" active="false">
                <qg:sprite id="title" src="gameover.png" x="400" y="300" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        html = builder.build(ast)
        assert '_sceneInits' in html
        assert '_loadScene' in html
        assert '"level1"' in html
        assert '"game-over"' in html

    def test_multi_scene_teardown(self, parser, builder):
        src = '''<q:application id="teardown-test" type="game" engine="2d">
            <qg:scene name="s1" width="800" height="600">
                <qg:sprite id="a" src="a.png" x="0" y="0" />
            </qg:scene>
            <qg:scene name="s2" width="800" height="600" active="false">
                <qg:sprite id="b" src="b.png" x="0" y="0" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        html = builder.build(ast)
        assert '_teardownScene' in html
        assert 'removeChildren' in html

    def test_single_scene_backward_compat(self, parser, builder):
        src = '''<q:application id="single" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <qg:sprite id="player" src="p.png" x="100" y="200" />
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        html = builder.build(ast)
        # Single scene should NOT have multi-scene infrastructure
        assert '<!DOCTYPE html>' in html
        assert 'PIXI.Application' in html
        # Uses single scene generate, not multi
        assert 'p.png' in html

    def test_multi_scene_integration(self, parser, builder):
        src = '''<q:application id="game" type="game" engine="2d">
            <qg:behavior name="Patrol">
                <q:set name="speed" value="2" />
            </qg:behavior>
            <qg:scene name="level1" width="1280" height="720" active="true">
                <qg:physics gravity-y="9.8" />
                <q:set name="score" value="0" type="integer" />
                <qg:sprite id="player" src="hero.png" x="100" y="400"
                           controls="wasd" speed="5" body="dynamic" />
                <qg:hud position="top-left">
                    <text style="color:white">Score: {score}</text>
                </qg:hud>
            </qg:scene>
            <qg:scene name="boss" width="1280" height="720" active="false">
                <qg:physics gravity-y="9.8" />
                <qg:sprite id="boss" src="boss.png" x="640" y="360" body="dynamic">
                    <qg:use behavior="Patrol" speed="3" />
                </qg:sprite>
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        html = builder.build(ast)
        assert '_sceneInits' in html
        assert '_loadScene' in html
        assert 'hero.png' in html
        assert 'boss.png' in html
        assert 'class Patrol' in html


class TestStateMachineBuild:
    def test_fsm_generates_js(self, parser, builder):
        src = '''<q:application id="fsm-test" type="game" engine="2d">
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
                <qg:sprite id="enemy" src="enemy.png" x="200" y="200" body="dynamic">
                    <qg:use behavior="Patrol" speed="2" />
                </qg:sprite>
            </qg:scene>
        </q:application>'''
        ast = parser.parse(src)
        html = builder.build(ast)
        assert 'class Patrol' in html
        assert '_smInit' in html
        assert '_smUpdate' in html
        assert '_smEmit' in html
        assert 'walk-right' in html or 'walk_right' in html
