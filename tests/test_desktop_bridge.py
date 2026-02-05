"""
Tests for Desktop Bridge - Python-JS communication via pywebview

Tests the generation of interactive desktop apps with:
- QuantumState (reactive state management)
- QuantumAPI (Python functions exposed to JS)
- Event transformation (on-click, on-submit, bind)
- Binding registration ({var} -> span with ID)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import pytest
from core.parser import QuantumParser
from core.ast_nodes import ApplicationNode, SetNode
from core.features.functions.src.ast_node import FunctionNode
from core.features.ui_engine.src.ast_nodes import (
    UIWindowNode, UITextNode, UIButtonNode, UIInputNode, UIFormNode,
)
from runtime.ui_html_adapter import UIHtmlAdapter
from runtime.ui_desktop_adapter import UIDesktopAdapter
from runtime.ui_builder import UIBuilder


@pytest.fixture
def parser():
    return QuantumParser()


def parse_ui(parser, body: str) -> ApplicationNode:
    source = f'<q:application id="test" type="ui">{body}</q:application>'
    return parser.parse(source)


# ============================================
# HTML Adapter Desktop Mode Tests
# ============================================

class TestHtmlAdapterDesktopMode:
    """Test HTML adapter's desktop_mode transformations."""

    def test_desktop_mode_flag(self):
        """desktop_mode=True enables event transformation."""
        adapter = UIHtmlAdapter(desktop_mode=True)
        assert adapter._desktop_mode is True
        assert adapter._binding_counter == 0
        assert adapter._bindings == []

    def test_onclick_transformation(self, parser):
        """on-click transforms to __quantumCall in desktop mode."""
        adapter = UIHtmlAdapter(desktop_mode=True)
        app = parse_ui(parser, '<ui:window><ui:button on-click="increment">+1</ui:button></ui:window>')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')

        # Should contain transformed onclick
        assert "__quantumCall('increment')" in html
        # Should NOT contain raw handler
        assert 'on-click="increment"' not in html

    def test_onclick_not_transformed_in_normal_mode(self, parser):
        """on-click is NOT transformed when desktop_mode=False."""
        adapter = UIHtmlAdapter(desktop_mode=False)
        app = parse_ui(parser, '<ui:window><ui:button on-click="doSomething">Click</ui:button></ui:window>')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')

        # Should contain raw handler
        assert 'onclick="doSomething"' in html
        assert '__quantumCall' not in html

    def test_binding_registration_for_simple_var(self, parser):
        """Simple {var} creates span with binding."""
        adapter = UIHtmlAdapter(desktop_mode=True)
        app = parse_ui(parser, '<ui:window><ui:text>{count}</ui:text></ui:window>')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')

        # Should create span with binding ID
        assert 'id="__qb_0"' in html
        # Should have binding registered
        assert len(adapter._bindings) == 1
        assert adapter._bindings[0] == ('__qb_0', 'count', 'text')

    def test_binding_script_generation(self, parser):
        """Bindings generate DOMContentLoaded script."""
        adapter = UIHtmlAdapter(desktop_mode=True)
        app = parse_ui(parser, '<ui:window><ui:text>{count}</ui:text></ui:window>')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')

        # Should contain binding registration
        assert "__quantumBind('__qb_0', 'count', 'text')" in html
        assert 'DOMContentLoaded' in html

    def test_multiple_bindings(self, parser):
        """Multiple {vars} create multiple bindings."""
        adapter = UIHtmlAdapter(desktop_mode=True)
        app = parse_ui(parser, '''
            <ui:window>
                <ui:text>{count}</ui:text>
                <ui:text>{name}</ui:text>
            </ui:window>
        ''')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')

        # Should have two bindings
        assert len(adapter._bindings) == 2
        assert adapter._bindings[0][1] == 'count'
        assert adapter._bindings[1][1] == 'name'

    def test_complex_expression_not_bound(self, parser):
        """Complex expressions like {a + b} are not bound (rendered as-is)."""
        adapter = UIHtmlAdapter(desktop_mode=True)
        app = parse_ui(parser, '<ui:window><ui:text>{count + 1}</ui:text></ui:window>')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')

        # Should NOT create binding for complex expression
        assert len(adapter._bindings) == 0
        # Expression should be in output
        assert '{count + 1}' in html

    def test_form_onsubmit_transformation(self, parser):
        """on-submit transforms with form data collection."""
        adapter = UIHtmlAdapter(desktop_mode=True)
        app = parse_ui(parser, '''
            <ui:window>
                <ui:form on-submit="handleSubmit">
                    <ui:input bind="name" />
                </ui:form>
            </ui:window>
        ''')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')

        # Should contain transformed onsubmit
        assert "event.preventDefault()" in html
        assert "__quantumCall('handleSubmit'" in html
        assert "__quantumFormData(this)" in html

    def test_input_twoway_binding(self, parser):
        """Input with bind adds oninput for two-way binding."""
        adapter = UIHtmlAdapter(desktop_mode=True)
        app = parse_ui(parser, '<ui:window><ui:input bind="username" /></ui:window>')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')

        # Should have oninput handler
        assert "__quantumCall('__set_state'" in html
        assert "name:'username'" in html


# ============================================
# Desktop Adapter Tests
# ============================================

class TestDesktopAdapter:
    """Test UIDesktopAdapter code generation."""

    def test_generates_quantum_state_class(self, parser):
        """Generated code includes QuantumState class."""
        app = parse_ui(parser, '<ui:window><ui:text>Hello</ui:text></ui:window>')
        adapter = UIDesktopAdapter()
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')

        assert 'class QuantumState:' in code
        assert 'def set(self, name: str, value: Any):' in code
        assert '_notify_js' in code

    def test_generates_quantum_api_class(self, parser):
        """Generated code includes QuantumAPI class."""
        app = parse_ui(parser, '<ui:window><ui:text>Hello</ui:text></ui:window>')
        adapter = UIDesktopAdapter()
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')

        assert 'class QuantumAPI:' in code
        assert 'def _set_window(self, window):' in code
        assert 'def __set_state(self, args):' in code

    def test_generates_js_bridge(self, parser):
        """Generated HTML includes JS bridge code."""
        app = parse_ui(parser, '<ui:window><ui:text>Hello</ui:text></ui:window>')
        adapter = UIDesktopAdapter()
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')

        assert '__quantumStateUpdate' in code
        assert '__quantumBind' in code
        assert '__quantumCall' in code

    def test_function_method_generation(self):
        """q:function generates Python method."""
        # Create a FunctionNode manually
        func = FunctionNode('increment')
        set_node = SetNode('count')
        set_node.value = '{count + 1}'
        func.body.append(set_node)

        adapter = UIDesktopAdapter()

        # Create minimal window
        window = UIWindowNode('Test')
        code = adapter.generate(
            [window], [],
            'Test',
            functions={'increment': func},
            state_vars={'count': '0'}
        )

        # Should have increment method
        assert 'def increment(self, args=None):' in code
        assert "self.state.set('count'" in code

    def test_state_initialization(self):
        """State variables generate initialization code."""
        adapter = UIDesktopAdapter()
        window = UIWindowNode('Test')

        code = adapter.generate(
            [window], [],
            'Test',
            functions={},
            state_vars={'count': '0', 'name': 'Alice'}
        )

        assert "self.state.set('count', 0)" in code
        assert "self.state.set('name', 'Alice')" in code

    def test_expression_conversion(self):
        """Quantum expressions convert to Python."""
        adapter = UIDesktopAdapter()

        # Simple variable
        assert adapter._convert_expression('count') == "self.state.get('count')"

        # Expression with math
        result = adapter._convert_expression('{count + 1}')
        assert "self.state.get('count')" in result
        assert '+ 1' in result

        # None
        assert adapter._convert_expression(None) == 'None'

    def test_value_conversion(self):
        """Values convert to Python literals."""
        adapter = UIDesktopAdapter()

        assert adapter._convert_value('0') == '0'
        assert adapter._convert_value('3.14') == '3.14'
        assert adapter._convert_value('true') == 'True'
        assert adapter._convert_value('false') == 'False'
        assert adapter._convert_value('hello') == "'hello'"
        assert adapter._convert_value(None) == 'None'

    def test_generated_code_compiles(self, parser):
        """Generated code is valid Python."""
        app = parse_ui(parser, '<ui:window><ui:text>Hello</ui:text></ui:window>')
        adapter = UIDesktopAdapter()
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')

        # Should compile without syntax errors
        try:
            compile(code, '<generated>', 'exec')
        except SyntaxError as e:
            pytest.fail(f"Generated code has syntax error: {e}")

    def test_generated_code_with_functions_compiles(self):
        """Generated code with functions is valid Python."""
        func = FunctionNode('increment')
        set_node = SetNode('count')
        set_node.value = '{count + 1}'
        func.body.append(set_node)

        adapter = UIDesktopAdapter()
        window = UIWindowNode('Test')

        code = adapter.generate(
            [window], [],
            'Test',
            functions={'increment': func},
            state_vars={'count': '0'}
        )

        # Should compile without syntax errors
        try:
            compile(code, '<generated>', 'exec')
        except SyntaxError as e:
            pytest.fail(f"Generated code has syntax error: {e}")


# ============================================
# UIBuilder Desktop Integration Tests
# ============================================

class TestUIBuilderDesktop:
    """Test UIBuilder integration with desktop target."""

    def test_builder_uses_desktop_adapter(self, parser):
        """Builder uses UIDesktopAdapter for desktop target."""
        app = parse_ui(parser, '<ui:window><ui:text>Hello</ui:text></ui:window>')
        builder = UIBuilder()
        code = builder.build(app, target='desktop')

        # Should be Python code with pywebview
        assert 'import webview' in code
        assert 'class QuantumAPI:' in code

    def test_builder_extracts_state_from_ui_children(self, parser):
        """Builder extracts q:set from ui_children."""
        app = parse_ui(parser, '''
            <q:set name="count" value="0" type="number" />
            <ui:window>
                <ui:text>{count}</ui:text>
            </ui:window>
        ''')

        builder = UIBuilder()
        state = builder._extract_state(app)

        assert 'count' in state
        assert state['count'] == '0'

    def test_builder_extracts_state_from_window_children(self, parser):
        """Builder extracts q:set from inside ui:window."""
        app = parse_ui(parser, '''
            <ui:window>
                <q:set name="cpu" value="45" type="number" />
                <q:set name="memory" value="72" type="number" />
                <ui:text>{cpu}%</ui:text>
            </ui:window>
        ''')

        builder = UIBuilder()
        state = builder._extract_state(app)

        assert 'cpu' in state
        assert state['cpu'] == '45'
        assert 'memory' in state
        assert state['memory'] == '72'

    def test_builder_desktop_code_compiles(self, parser):
        """Desktop build output is valid Python."""
        app = parse_ui(parser, '''
            <ui:window>
                <ui:text>Hello World</ui:text>
                <ui:button on-click="click">Click Me</ui:button>
            </ui:window>
        ''')

        builder = UIBuilder()
        code = builder.build(app, target='desktop')

        try:
            compile(code, '<generated>', 'exec')
        except SyntaxError as e:
            pytest.fail(f"Generated code has syntax error: {e}")


# ============================================
# Integration Tests
# ============================================

class TestDesktopBridgeIntegration:
    """Integration tests for complete desktop app generation."""

    def test_counter_app_structure(self, parser):
        """Counter app generates expected structure."""
        source = '''
        <q:application id="Counter" type="ui">
            <ui:window title="Counter">
                <ui:text>{count}</ui:text>
                <ui:button on-click="increment">+1</ui:button>
            </ui:window>
        </q:application>
        '''
        app = parser.parse(source)

        adapter = UIDesktopAdapter()

        # Create mock function
        func = FunctionNode('increment')
        set_node = SetNode('count')
        set_node.value = '{count + 1}'
        func.body.append(set_node)

        code = adapter.generate(
            app.ui_windows, app.ui_children, 'Counter',
            functions={'increment': func},
            state_vars={'count': '0'}
        )

        # Verify structure
        assert 'title="Counter"' in code or "'Counter'" in code
        assert 'def increment(self, args=None):' in code
        # Check for quantumCall with increment (escaped or not)
        assert '__quantumCall' in code and 'increment' in code

    def test_form_app_structure(self, parser):
        """Form app generates expected structure."""
        source = '''
        <q:application id="Form" type="ui">
            <ui:window title="Form">
                <ui:form on-submit="handleSubmit">
                    <ui:input bind="name" placeholder="Your name" />
                    <ui:button>Submit</ui:button>
                </ui:form>
            </ui:window>
        </q:application>
        '''
        app = parser.parse(source)
        adapter = UIDesktopAdapter()

        code = adapter.generate(app.ui_windows, app.ui_children, 'Form')

        # Verify form handling (check for patterns, escaping may vary)
        assert '__quantumCall' in code and 'handleSubmit' in code
        assert '__quantumFormData' in code
        assert '__quantumCall' in code and '__set_state' in code
