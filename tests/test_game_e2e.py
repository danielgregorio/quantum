"""
End-to-End Tests for Game Engine 2D

Tests the full pipeline: Parse .q XML → Build AST → Generate HTML → Validate JS syntax.
Uses Node.js vm.Script() to verify generated JavaScript has no syntax errors.
"""

import pytest
import subprocess
import sys
import os
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.parser import QuantumParser
from runtime.game_code_generator import GameCodeGenerator

JS_VALIDATOR = str(Path(__file__).parent / 'js_validator.cjs')


def _has_node():
    """Check if Node.js is available."""
    try:
        result = subprocess.run(
            ['node', '--version'],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


HAS_NODE = _has_node()


def validate_js_syntax(html: str) -> tuple:
    """Validate JS syntax in generated HTML using Node.js.

    Returns (success: bool, error_message: str)
    """
    if not HAS_NODE:
        pytest.skip("Node.js not available")

    result = subprocess.run(
        ['node', JS_VALIDATOR],
        input=html, capture_output=True, text=True, timeout=15
    )
    if result.returncode == 0:
        return True, ''
    return False, result.stderr.strip()


def validate_balanced(html: str) -> list:
    """Validate balanced braces/parens/brackets in generated JS."""
    match = re.search(r'<script>\s*(.*?)\s*</script>', html, re.DOTALL)
    if not match:
        return ['No script block found']

    js = match.group(1)
    errors = []
    for open_c, close_c, name in [('{', '}', 'braces'), ('(', ')', 'parens'), ('[', ']', 'brackets')]:
        count = 0
        in_str = None
        escape = False
        for ch in js:
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
            if ch == open_c:
                count += 1
            elif ch == close_c:
                count -= 1
        if count != 0:
            errors.append(f"Unbalanced {name}: {count:+d}")
    return errors


def compile_game_q(source: str) -> str:
    """Compile a .q game source to HTML."""
    parser = QuantumParser()
    ast = parser.parse(source)
    gen = GameCodeGenerator()

    if hasattr(ast, 'scenes') and ast.scenes:
        if len(ast.scenes) == 1:
            return gen.generate(
                scene=ast.scenes[0],
                behaviors=getattr(ast, 'behaviors', []),
                prefabs=getattr(ast, 'prefabs', []),
                title=getattr(ast, 'app_id', 'Test'),
            )
        else:
            initial = ast.scenes[0].name
            return gen.generate_multi(
                scenes=ast.scenes,
                initial=initial,
                behaviors=getattr(ast, 'behaviors', []),
                prefabs=getattr(ast, 'prefabs', []),
                title=getattr(ast, 'app_id', 'Test'),
            )
    pytest.skip("No game scenes found in source")


# ===========================================================================
# Discover all .q game files in examples/
# ===========================================================================

EXAMPLES_DIR = Path(__file__).parent.parent / 'examples'
GAME_Q_FILES = sorted(EXAMPLES_DIR.glob('*.q'))

# Filter to only game-type .q files
def _is_game_file(path: Path) -> bool:
    """Check if a .q file is a game type (has type='game')."""
    try:
        content = path.read_text(encoding='utf-8')
        return 'type="game"' in content and 'engine="2d"' in content
    except Exception:
        return False


GAME_FILES = [f for f in GAME_Q_FILES if _is_game_file(f)]


# ===========================================================================
# E2E Tests - Validate every game .q example
# ===========================================================================

@pytest.mark.e2e
@pytest.mark.game
class TestGameExamplesE2E:
    """Test that all game .q examples produce valid JS."""

    @pytest.mark.parametrize('q_file', GAME_FILES, ids=lambda f: f.name)
    def test_game_example_valid_js(self, q_file):
        source = q_file.read_text(encoding='utf-8')
        html = compile_game_q(source)

        # Validate balanced delimiters
        balance_errors = validate_balanced(html)
        assert not balance_errors, f"Balance errors in {q_file.name}: {balance_errors}"

        # Validate JS syntax via Node.js
        ok, err = validate_js_syntax(html)
        assert ok, f"JS syntax error in {q_file.name}: {err}"

    @pytest.mark.parametrize('q_file', GAME_FILES, ids=lambda f: f.name)
    def test_no_eval_in_output(self, q_file):
        source = q_file.read_text(encoding='utf-8')
        html = compile_game_q(source)
        match = re.search(r'<script>\s*(.*?)\s*</script>', html, re.DOTALL)
        if match:
            assert 'eval(' not in match.group(1), f"eval() found in {q_file.name}"


# ===========================================================================
# Stress Tests - Complex game scenarios
# ===========================================================================

@pytest.mark.e2e
@pytest.mark.game
class TestStressScenarios:
    """Stress test: games using many features at once."""

    def test_all_features_combined(self):
        """A game using behaviors, FSM, prefabs, particles, tweens, HUD, sound, camera."""
        src = '''<q:application id="stress-test" type="game" engine="2d">
            <qg:behavior name="Enemy">
                <q:set name="hp" value="3" type="integer" />
                <q:set name="speed" value="2" type="integer" />
                <qg:state-machine initial="walk">
                    <qg:state name="walk">
                        <qg:on event="hit" transition="hurt" />
                        <q:function name="update">
                            game.moveX(this.owner, this.speed)
                        </q:function>
                    </qg:state>
                    <qg:state name="hurt">
                        <qg:on event="recover" transition="walk" />
                        <q:function name="enter">
                            <q:set name="self.hp" value="{self.hp - 1}" />
                        </q:function>
                    </qg:state>
                </qg:state-machine>
            </qg:behavior>
            <qg:prefab name="Coin">
                <qg:sprite src="coin.png" body="dynamic" sensor="true" tag="coin" />
            </qg:prefab>
            <qg:scene name="main" width="800" height="600" background="#87CEEB">
                <qg:physics gravity-y="9.8" bounds="canvas" />
                <q:set name="score" value="0" type="integer" />
                <qg:camera follow="player" lerp="0.1" bounds="scene" />
                <qg:sprite id="player" src="hero.png" x="100" y="400"
                           body="dynamic" controls="wasd" speed="5" jump-force="12"
                           frame-width="32" frame-height="32" tag="player">
                    <qg:animation name="idle" frames="0-3" speed="0.15" auto-play="true" />
                    <qg:animation name="walk" frames="4-11" speed="0.08" />
                </qg:sprite>
                <qg:sprite id="ground" src="ground.png" x="400" y="580"
                           width="800" height="40" body="static" tag="solid" />
                <qg:sprite id="enemy1" src="enemy.png" x="500" y="400" body="dynamic" tag="enemy">
                    <qg:use behavior="Enemy" on-collision="onHit" collision-tag="player" />
                </qg:sprite>
                <qg:instance prefab="Coin" x="300" y="350" />
                <qg:instance prefab="Coin" x="500" y="350" />
                <qg:particle id="dust" follow="player" trigger="player.walk"
                             count="15" emit-rate="8" lifetime="0.4" />
                <qg:tween id="tw1" target="enemy1" property="alpha" to="0.5"
                          duration="1" easing="easeInOut" loop="true" yoyo="true" />
                <qg:sound id="bgm" src="music.mp3" volume="0.4" loop="true"
                          trigger="scene.start" channel="music" />
                <qg:sound id="jump_sfx" src="jump.wav" trigger="player.jump" />
                <qg:timer id="spawn_timer" interval="3" action="spawnEnemy" auto-start="true" />
                <qg:hud position="top-left">
                    <text style="font-size:24px; color:white">Score: {score}</text>
                </qg:hud>
                <qg:input key="r" action="restart" type="press" />
            </qg:scene>
        </q:application>'''
        html = compile_game_q(src)
        balance_errors = validate_balanced(html)
        assert not balance_errors, f"Balance errors: {balance_errors}"
        ok, err = validate_js_syntax(html)
        assert ok, f"JS syntax error: {err}"

    def test_multi_scene_with_transition(self):
        """Multi-scene game with scene switching."""
        src = '''<q:application id="multi-scene" type="game" engine="2d">
            <qg:scene name="menu" width="800" height="600" background="#333">
                <qg:sprite id="title" src="title.png" x="400" y="200" />
                <qg:sprite id="start_btn" src="btn.png" x="400" y="400">
                    <qg:clickable action="startGame" cursor="pointer" />
                </qg:sprite>
                <q:function name="startGame">
                    game.loadScene('level1')
                </q:function>
            </qg:scene>
            <qg:scene name="level1" width="800" height="600" background="#87CEEB">
                <qg:physics gravity-y="9.8" />
                <q:set name="score" value="0" type="integer" />
                <qg:sprite id="player" src="hero.png" x="100" y="400"
                           body="dynamic" controls="wasd" speed="5" />
                <qg:sprite id="ground" src="ground.png" x="400" y="580"
                           width="800" height="40" body="static" />
                <qg:hud position="top-left">
                    <text style="color:white">Score: {score}</text>
                </qg:hud>
            </qg:scene>
        </q:application>'''
        html = compile_game_q(src)
        balance_errors = validate_balanced(html)
        assert not balance_errors, f"Balance errors: {balance_errors}"
        ok, err = validate_js_syntax(html)
        assert ok, f"JS syntax error: {err}"

    def test_complex_bindings(self):
        """Game with complex expressions in bindings."""
        src = '''<q:application id="bindings" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <q:set name="score" value="0" type="integer" />
                <q:set name="lives" value="3" type="integer" />
                <q:set name="level" value="1" type="integer" />
                <q:set name="gameOver" value="false" type="boolean" />
                <q:function name="addScore">
                    <q:set name="score" value="{score + level * 10}" />
                    <q:if condition="{score &gt; 100}">
                        <q:set name="level" value="{level + 1}" />
                    </q:if>
                </q:function>
                <q:function name="loseLife">
                    <q:set name="lives" value="{lives - 1}" />
                    <q:if condition="{lives &lt;= 0}">
                        <q:set name="gameOver" value="true" />
                    </q:if>
                </q:function>
                <qg:sprite id="s" src="a.png" x="0" y="0" />
                <qg:hud position="top-left">
                    <text style="color:white">Score: {score} | Lives: {lives} | Level: {level}</text>
                </qg:hud>
            </qg:scene>
        </q:application>'''
        html = compile_game_q(src)
        balance_errors = validate_balanced(html)
        assert not balance_errors, f"Balance errors: {balance_errors}"
        ok, err = validate_js_syntax(html)
        assert ok, f"JS syntax error: {err}"

    def test_many_sprites_and_prefabs(self):
        """Game with many sprites and prefab instances."""
        src = '''<q:application id="many-sprites" type="game" engine="2d">
            <qg:prefab name="Block">
                <qg:sprite src="block.png" body="static" tag="block" width="32" height="32" />
            </qg:prefab>
            <qg:scene name="main" width="800" height="600">
                <qg:physics gravity-y="9.8" />
                <qg:sprite id="player" src="p.png" x="100" y="100" body="dynamic" controls="wasd" speed="5" />
                <qg:instance prefab="Block" id="b1" x="100" y="500" />
                <qg:instance prefab="Block" id="b2" x="132" y="500" />
                <qg:instance prefab="Block" id="b3" x="164" y="500" />
                <qg:instance prefab="Block" id="b4" x="196" y="500" />
                <qg:instance prefab="Block" id="b5" x="228" y="500" />
                <qg:instance prefab="Block" id="b6" x="260" y="500" />
                <qg:instance prefab="Block" id="b7" x="292" y="500" />
                <qg:instance prefab="Block" id="b8" x="324" y="500" />
                <qg:instance prefab="Block" id="b9" x="356" y="500" />
                <qg:instance prefab="Block" id="b10" x="388" y="500" />
                <qg:sprite id="ground" src="g.png" x="400" y="590" width="800" height="20" body="static" />
            </qg:scene>
        </q:application>'''
        html = compile_game_q(src)
        balance_errors = validate_balanced(html)
        assert not balance_errors, f"Balance errors: {balance_errors}"
        ok, err = validate_js_syntax(html)
        assert ok, f"JS syntax error: {err}"

    def test_clickable_sprites(self):
        """Game with clickable sprites (mouse support)."""
        src = '''<q:application id="clickable" type="game" engine="2d">
            <qg:scene name="main" width="800" height="600">
                <q:set name="clicks" value="0" type="integer" />
                <q:function name="onButtonClick">
                    <q:set name="clicks" value="{clicks + 1}" />
                </q:function>
                <qg:sprite id="button" src="btn.png" x="400" y="300" width="100" height="50">
                    <qg:clickable action="onButtonClick" cursor="pointer" />
                </qg:sprite>
                <qg:hud position="top-center">
                    <text style="color:white">Clicks: {clicks}</text>
                </qg:hud>
            </qg:scene>
        </q:application>'''
        html = compile_game_q(src)
        assert "eventMode" in html
        assert "'static'" in html
        assert "'pointer'" in html or '"pointer"' in html
        balance_errors = validate_balanced(html)
        assert not balance_errors, f"Balance errors: {balance_errors}"
        ok, err = validate_js_syntax(html)
        assert ok, f"JS syntax error: {err}"
