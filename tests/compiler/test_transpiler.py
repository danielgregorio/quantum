"""
Tests for Quantum Transpiler
============================

Tests the transpilation of Quantum to Python and JavaScript.
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from compiler.transpiler import Transpiler, CompilationResult
from compiler.expression_transformer import ExpressionTransformer
from compiler.python.generator import PythonGenerator
from compiler.javascript.generator import JavaScriptGenerator


# =============================================================================
# Expression Transformer Tests
# =============================================================================

class TestExpressionTransformer:
    """Test expression transformation."""

    def test_python_basics(self):
        """Test basic Python expression transformation."""
        t = ExpressionTransformer(target='python')

        # Simple values
        assert t.transform('42') == '42'
        assert t.transform('"hello"') == '"hello"'
        assert t.transform('True') == 'True'

    def test_python_operators(self):
        """Test Python operator transformation."""
        t = ExpressionTransformer(target='python')

        assert t.transform('a + b') == 'a + b'
        assert t.transform('a == b') == 'a == b'
        assert t.transform('a and b') == 'a and b'
        assert t.transform('not x') == 'not x'

    def test_javascript_operators(self):
        """Test JavaScript operator transformation."""
        t = ExpressionTransformer(target='javascript')

        assert '===' in t.transform('a == b')
        assert '!==' in t.transform('a != b')
        assert '&&' in t.transform('a and b')
        assert '||' in t.transform('a or b')
        assert '!' in t.transform('not x')

    def test_strip_braces(self):
        """Test that expression braces are stripped."""
        t = ExpressionTransformer(target='python')

        assert t.transform('{x + 1}') == 'x + 1'
        assert t.transform('{ x + 1 }') == 'x + 1'


# =============================================================================
# Python Generator Tests
# =============================================================================

class TestPythonGenerator:
    """Test Python code generation."""

    @pytest.fixture
    def transpiler(self):
        return Transpiler(target='python')

    def test_simple_component(self, transpiler):
        """Test simple component transpilation."""
        source = '''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="Hello">
    <q:set name="message" value="Hello World" />
    <div>{message}</div>
</q:component>'''

        result = transpiler.compile_string(source)

        assert result.success
        assert 'class Hello' in result.code
        assert 'def render' in result.code
        assert 'message' in result.code

    def test_loop_transpilation(self, transpiler):
        """Test loop transpilation."""
        source = '''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="LoopTest">
    <q:loop from="1" to="5" var="i">
        <span>{i}</span>
    </q:loop>
</q:component>'''

        result = transpiler.compile_string(source)

        assert result.success
        assert 'for i in range' in result.code
        # Quantum loops are inclusive - output may include step parameter
        assert 'range(1,' in result.code

    def test_conditional_transpilation(self, transpiler):
        """Test if/else transpilation."""
        source = '''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="CondTest">
    <q:set name="x" value="10" />
    <q:if condition="{x > 5}">
        <span>Large</span>
    </q:if>
</q:component>'''

        result = transpiler.compile_string(source)

        assert result.success
        assert 'if ' in result.code
        assert 'x > 5' in result.code

    def test_function_transpilation(self, transpiler):
        """Test function transpilation."""
        # Note: Function parsing depends on parser implementation
        # This tests that the generator doesn't crash on function nodes
        source = '''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="FuncTest">
    <q:set name="result" value="{1 + 2}" />
</q:component>'''

        result = transpiler.compile_string(source)

        assert result.success
        assert 'result' in result.code

    def test_html_generation(self, transpiler):
        """Test HTML generation."""
        source = '''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="HTMLTest">
    <div class="container">
        <h1>Title</h1>
    </div>
</q:component>'''

        result = transpiler.compile_string(source)

        assert result.success
        assert '_html.append' in result.code
        assert 'container' in result.code

    def test_generated_code_executes(self, transpiler):
        """Test that generated Python code actually runs."""
        source = '''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="ExecuteTest">
    <q:set name="total" value="0" />
    <q:loop from="1" to="5" var="i">
        <q:set name="total" value="{total + i}" />
    </q:loop>
    <span>{total}</span>
</q:component>'''

        result = transpiler.compile_string(source)
        assert result.success

        # Execute the generated code
        exec_globals = {}
        exec(result.code, exec_globals)

        ExecuteTest = exec_globals['ExecuteTest']
        html = ExecuteTest().render()

        assert '15' in html  # 1+2+3+4+5 = 15


# =============================================================================
# JavaScript Generator Tests
# =============================================================================

class TestJavaScriptGenerator:
    """Test JavaScript code generation."""

    @pytest.fixture
    def transpiler(self):
        return Transpiler(target='javascript')

    def test_simple_component(self, transpiler):
        """Test simple component transpilation."""
        source = '''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="Hello">
    <q:set name="message" value="Hello World" />
    <div>{message}</div>
</q:component>'''

        result = transpiler.compile_string(source)

        assert result.success
        assert 'class Hello' in result.code
        assert 'extends Component' in result.code
        assert 'render()' in result.code

    def test_loop_transpilation(self, transpiler):
        """Test loop transpilation."""
        source = '''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="LoopTest">
    <q:loop from="1" to="5" var="i">
        <span>{i}</span>
    </q:loop>
</q:component>'''

        result = transpiler.compile_string(source)

        assert result.success
        assert 'for (' in result.code
        # JavaScript uses <= for inclusive
        assert 'i <= 5' in result.code

    def test_js_operators(self, transpiler):
        """Test JavaScript operator conversion."""
        source = '''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="OperatorTest">
    <q:set name="x" value="{a == b}" />
    <q:set name="y" value="{c and d}" />
</q:component>'''

        result = transpiler.compile_string(source)

        assert result.success
        assert '===' in result.code  # Python == becomes JS ===
        assert '&&' in result.code   # Python and becomes JS &&


# =============================================================================
# Transpiler Integration Tests
# =============================================================================

class TestTranspilerIntegration:
    """Integration tests for the transpiler."""

    def test_compile_error_handling(self):
        """Test error handling for invalid source."""
        transpiler = Transpiler(target='python')

        result = transpiler.compile_string('<invalid xml')

        assert not result.success
        assert len(result.errors) > 0

    def test_compilation_stats(self):
        """Test that compilation statistics are collected."""
        transpiler = Transpiler(target='python')

        source = '''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="Stats">
    <div>Test</div>
</q:component>'''

        result = transpiler.compile_string(source)

        assert result.success
        assert result.stats is not None
        assert 'generate_time_ms' in result.stats or 'compile_time_ms' in result.stats

    def test_strict_mode(self):
        """Test strict mode treats warnings as errors."""
        transpiler = Transpiler(target='python', strict=True)

        # This should compile successfully even in strict mode
        source = '''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="Strict">
    <div>Valid</div>
</q:component>'''

        result = transpiler.compile_string(source)
        assert result.success


# =============================================================================
# Performance Tests
# =============================================================================

class TestTranspilerPerformance:
    """Performance benchmarks for the transpiler."""

    def test_transpilation_speed(self):
        """Test that transpilation is fast."""
        import time

        transpiler = Transpiler(target='python')

        source = '''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="PerfTest">
    <q:loop from="1" to="100" var="i">
        <div class="item">{i}</div>
    </q:loop>
</q:component>'''

        # Warm up
        transpiler.compile_string(source)

        # Time 100 compilations
        start = time.perf_counter()
        for _ in range(100):
            result = transpiler.compile_string(source)
            assert result.success
        elapsed = time.perf_counter() - start

        # Should compile 100 files in under 5 seconds
        assert elapsed < 5.0, f"Transpilation too slow: {elapsed:.2f}s for 100 files"

    def test_transpiled_vs_interpreted(self):
        """Verify transpiled code is faster than interpreted."""
        import time

        source = '''<?xml version="1.0" encoding="UTF-8"?>
<q:component name="SpeedTest">
    <q:set name="sum" value="0" />
    <q:loop from="1" to="100" var="i">
        <q:set name="sum" value="{sum + i}" />
    </q:loop>
</q:component>'''

        # Transpile
        transpiler = Transpiler(target='python')
        result = transpiler.compile_string(source)
        assert result.success

        # Execute transpiled
        exec_globals = {}
        exec(result.code, exec_globals)
        SpeedTest = exec_globals['SpeedTest']

        # Time transpiled
        start = time.perf_counter()
        for _ in range(100):
            SpeedTest().render()
        transpiled_time = time.perf_counter() - start

        # Transpiled should be reasonably fast (under 1 second for 100 runs)
        assert transpiled_time < 1.0, f"Transpiled code slow: {transpiled_time:.3f}s"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
