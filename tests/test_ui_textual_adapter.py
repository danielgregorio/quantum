"""
Tests for UI Engine Textual Adapter

Tests generation of Python Textual TUI apps from UI AST nodes.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import pytest
from core.parser import QuantumParser
from core.ast_nodes import ApplicationNode
from runtime.ui_textual_adapter import UITextualAdapter
from runtime.ui_builder import UIBuilder


@pytest.fixture
def parser():
    return QuantumParser()


@pytest.fixture
def adapter():
    return UITextualAdapter()


def parse_ui(parser, body: str) -> ApplicationNode:
    source = f'<q:application id="test" type="ui">{body}</q:application>'
    return parser.parse(source)


# ============================================
# Container tests
# ============================================

class TestTextualContainers:
    def test_hbox_horizontal(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:hbox><ui:text>A</ui:text></ui:hbox></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'Horizontal(' in code

    def test_vbox_vertical(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:vbox><ui:text>A</ui:text></ui:vbox></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'with Vertical(' in code  # vbox inside window which is also Vertical

    def test_panel(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:panel title="CPU"><ui:text>45%</ui:text></ui:panel></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'Vertical(' in code
        assert 'q-panel' in code
        assert 'CPU' in code

    def test_tabpanel_tabbed_content(self, parser, adapter):
        src = '''
        <ui:window title="T">
            <ui:tabpanel>
                <ui:tab title="Tab1"><ui:text>C1</ui:text></ui:tab>
                <ui:tab title="Tab2"><ui:text>C2</ui:text></ui:tab>
            </ui:tabpanel>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'TabbedContent(' in code
        assert 'TabPane(' in code
        assert 'Tab1' in code
        assert 'Tab2' in code

    def test_grid(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:grid columns="3"><ui:text>A</ui:text></ui:grid></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'Grid(' in code

    def test_accordion_collapsible(self, parser, adapter):
        src = '''
        <ui:window title="T">
            <ui:accordion>
                <ui:section title="Sec1" expanded="true"><ui:text>Content</ui:text></ui:section>
            </ui:accordion>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'Collapsible(' in code
        assert 'Sec1' in code

    def test_scrollbox(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:scrollbox><ui:text>A</ui:text></ui:scrollbox></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'ScrollableContainer(' in code


# ============================================
# Widget tests
# ============================================

class TestTextualWidgets:
    def test_button(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:button variant="primary">Click</ui:button></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'Button(' in code
        assert 'Click' in code

    def test_input(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:input placeholder="Enter" /></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'Input(' in code
        assert 'Enter' in code

    def test_table(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:table source="{data}" /></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'DataTable(' in code

    def test_checkbox(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:checkbox label="I agree" /></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'Checkbox(' in code

    def test_switch(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:switch /></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'Switch(' in code

    def test_progress(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:progress value="50" max="100" /></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'ProgressBar(' in code

    def test_tree(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:tree source="{files}" /></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'Tree(' in code

    def test_log(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:log /></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'RichLog(' in code

    def test_markdown(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:markdown># Hello</ui:markdown></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'Markdown(' in code

    def test_header(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:header title="Title" /></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'Header()' in code

    def test_footer(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:footer>v1.0</ui:footer></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'Footer()' in code

    def test_rule(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:rule /></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'Rule()' in code

    def test_loading(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:loading /></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'LoadingIndicator(' in code

    def test_text(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:text>Hello World</ui:text></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'Static(' in code
        assert 'Hello World' in code


# ============================================
# Code validity tests
# ============================================

class TestTextualCodeValid:
    def test_basic_code_compiles(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:text>Hello</ui:text></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        compile(code, '<test>', 'exec')

    def test_complex_code_compiles(self, parser, adapter):
        src = '''
        <ui:window title="Dashboard">
            <ui:header title="Dashboard" />
            <ui:hbox>
                <ui:panel title="CPU">
                    <ui:vbox>
                        <ui:text>45%</ui:text>
                        <ui:progress value="45" max="100" />
                    </ui:vbox>
                </ui:panel>
            </ui:hbox>
            <ui:tabpanel>
                <ui:tab title="Logs"><ui:log /></ui:tab>
                <ui:tab title="Tree"><ui:tree source="{data}" /></ui:tab>
            </ui:tabpanel>
            <ui:footer>v1.0</ui:footer>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        compile(code, '<test>', 'exec')

    def test_builder_textual_target(self, parser):
        """UIBuilder with textual target produces valid Python."""
        app = parse_ui(parser, '<ui:window title="T"><ui:text>Hello</ui:text></ui:window>')
        builder = UIBuilder()
        code = builder.build(app, target='textual')
        assert 'class QuantumUIApp(App):' in code
        assert 'def compose' in code
        compile(code, '<test>', 'exec')


# ============================================
# Integration tests
# ============================================

class TestIntegration:
    def test_full_dashboard(self, parser, adapter):
        """Full dashboard generates valid Textual app."""
        src = '''
        <ui:window title="Dashboard">
            <ui:header title="Dashboard" />
            <ui:hbox>
                <ui:panel title="CPU">
                    <ui:text>45%</ui:text>
                </ui:panel>
                <ui:panel title="Memory">
                    <ui:text>72%</ui:text>
                </ui:panel>
            </ui:hbox>
            <ui:footer>v1.0</ui:footer>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        code = adapter.generate(app.ui_windows, app.ui_children, 'Dashboard')
        assert 'QuantumUIApp' in code
        assert 'compose' in code
        compile(code, '<test>', 'exec')

    def test_imports_present(self, parser, adapter):
        """Generated code has all needed imports."""
        app = parse_ui(parser, '<ui:window title="T"><ui:text>A</ui:text></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'from textual.app import App' in code
        assert 'from textual.containers import' in code
        assert 'from textual.widgets import' in code
