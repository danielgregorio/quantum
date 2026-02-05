"""
Tests for Terminal Engine Code Generator

Verifies that Terminal AST nodes compile correctly to Python/Textual code.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.parser import QuantumParser
from core.features.terminal_engine.src.ast_nodes import (
    ScreenNode, PanelNode, LayoutNode, TableNode, ColumnNode,
    TerminalInputNode, ButtonNode, TextNode_Terminal, ProgressNode,
    LogNode_Terminal, HeaderNode_Terminal, FooterNode,
    KeybindingNode, TimerNode_Terminal, TreeNode, TabsNode, TabNode,
    CssNode, MenuNode, OptionNode,
)
from core.ast_nodes import SetNode, FunctionNode
from runtime.terminal_code_generator import TerminalCodeGenerator


@pytest.fixture
def parser():
    return QuantumParser()


@pytest.fixture
def codegen():
    return TerminalCodeGenerator()


class TestBasicGeneration:
    """Test basic Python code generation."""

    def test_generates_python(self, codegen):
        screen = ScreenNode('main')
        screen.title = 'Test App'
        text = TextNode_Terminal()
        text.content = 'Hello World'
        screen.add_child(text)
        code = codegen.generate([screen], title='Test App')
        assert 'from textual.app import App' in code
        assert 'class TestAppApp(App)' in code
        assert 'if __name__' in code

    def test_app_title(self, codegen):
        screen = ScreenNode('main')
        text = TextNode_Terminal()
        text.content = 'Hello'
        screen.add_child(text)
        code = codegen.generate([screen], title='My Dashboard')
        assert 'TITLE = "My Dashboard"' in code

    def test_header_widget(self, codegen):
        screen = ScreenNode('main')
        header = HeaderNode_Terminal()
        header.show_clock = True
        screen.add_child(header)
        code = codegen.generate([screen])
        assert 'yield Header(show_clock=True)' in code

    def test_footer_widget(self, codegen):
        screen = ScreenNode('main')
        footer = FooterNode()
        screen.add_child(footer)
        code = codegen.generate([screen])
        assert 'yield Footer()' in code

    def test_text_widget(self, codegen):
        screen = ScreenNode('main')
        text = TextNode_Terminal()
        text.text_id = 'msg'
        text.content = 'Hello World'
        screen.add_child(text)
        code = codegen.generate([screen])
        assert 'yield Static("Hello World", id="msg")' in code

    def test_input_widget(self, codegen):
        screen = ScreenNode('main')
        inp = TerminalInputNode()
        inp.input_id = 'user-input'
        inp.placeholder = 'Type here...'
        screen.add_child(inp)
        code = codegen.generate([screen])
        assert 'yield Input(placeholder="Type here...", id="user-input")' in code

    def test_button_widget(self, codegen):
        screen = ScreenNode('main')
        btn = ButtonNode()
        btn.button_id = 'send'
        btn.label = 'Send'
        btn.variant = 'primary'
        screen.add_child(btn)
        code = codegen.generate([screen])
        assert 'yield Button("Send", variant="primary", id="send")' in code

    def test_progress_widget(self, codegen):
        screen = ScreenNode('main')
        prog = ProgressNode()
        prog.progress_id = 'bar'
        prog.total = 100
        screen.add_child(prog)
        code = codegen.generate([screen])
        assert 'yield ProgressBar(total=100' in code

    def test_log_widget(self, codegen):
        screen = ScreenNode('main')
        log = LogNode_Terminal()
        log.log_id = 'chat-log'
        log.max_lines = 200
        screen.add_child(log)
        code = codegen.generate([screen])
        assert 'yield RichLog(' in code
        assert 'id="chat-log"' in code

    def test_tree_widget(self, codegen):
        screen = ScreenNode('main')
        tree = TreeNode()
        tree.tree_id = 'file-tree'
        tree.label = '.'
        screen.add_child(tree)
        code = codegen.generate([screen])
        assert 'yield Tree(".", id="file-tree")' in code

    def test_table_widget(self, codegen):
        screen = ScreenNode('main')
        table = TableNode()
        table.table_id = 'data'
        table.zebra = True
        screen.add_child(table)
        code = codegen.generate([screen])
        assert 'yield DataTable(' in code
        assert 'zebra_stripes=True' in code


class TestContainerGeneration:
    """Test container widget code generation."""

    def test_horizontal_layout(self, codegen):
        screen = ScreenNode('main')
        layout = LayoutNode()
        layout.direction = 'horizontal'
        text = TextNode_Terminal()
        text.content = 'Hello'
        layout.add_child(text)
        screen.add_child(layout)
        code = codegen.generate([screen])
        assert 'with Horizontal(' in code

    def test_vertical_layout(self, codegen):
        screen = ScreenNode('main')
        layout = LayoutNode()
        layout.direction = 'vertical'
        text = TextNode_Terminal()
        text.content = 'Hello'
        layout.add_child(text)
        screen.add_child(layout)
        code = codegen.generate([screen])
        assert 'with Vertical(' in code

    def test_panel_generates_vertical(self, codegen):
        screen = ScreenNode('main')
        panel = PanelNode()
        panel.panel_id = 'info'
        text = TextNode_Terminal()
        text.content = 'Content'
        panel.add_child(text)
        screen.add_child(panel)
        code = codegen.generate([screen])
        assert 'with Vertical(id="info")' in code


class TestBindingsGeneration:
    """Test keybinding generation."""

    def test_keybinding(self, codegen):
        screen = ScreenNode('main')
        kb = KeybindingNode()
        kb.key = 'q'
        kb.action = 'quit'
        kb.description = 'Quit'
        screen.add_child(kb)
        text = TextNode_Terminal()
        text.content = 'Hello'
        screen.add_child(text)
        code = codegen.generate([screen])
        assert 'BINDINGS' in code
        assert 'Binding("q", "quit", "Quit")' in code

    def test_timer_generates_set_interval(self, codegen):
        screen = ScreenNode('main')
        timer = TimerNode_Terminal()
        timer.interval = 5.0
        timer.action = 'refresh'
        text = TextNode_Terminal()
        text.content = 'Hello'
        screen.add_child(text)
        screen.add_child(timer)
        code = codegen.generate([screen])
        assert 'on_mount' in code
        assert 'set_interval(5.0' in code


class TestStateVars:
    """Test reactive state variable generation."""

    def test_set_generates_reactive(self, codegen):
        screen = ScreenNode('main')
        var = SetNode('counter')
        var.value = '0'
        var.type = 'integer'
        text = TextNode_Terminal()
        text.content = '{counter}'
        screen.add_child(var)
        screen.add_child(text)
        code = codegen.generate([screen])
        assert 'counter = reactive(0)' in code

    def test_string_var(self, codegen):
        screen = ScreenNode('main')
        var = SetNode('name')
        var.value = 'hello'
        var.type = 'string'
        text = TextNode_Terminal()
        text.content = '{name}'
        screen.add_child(var)
        screen.add_child(text)
        code = codegen.generate([screen])
        assert 'name = reactive("hello")' in code

    def test_array_var(self, codegen):
        screen = ScreenNode('main')
        var = SetNode('items')
        var.value = '[]'
        var.type = 'array'
        text = TextNode_Terminal()
        text.content = 'test'
        screen.add_child(var)
        screen.add_child(text)
        code = codegen.generate([screen])
        assert 'items = reactive([])' in code


class TestCssGeneration:
    """Test CSS integration."""

    def test_css_in_output(self, codegen):
        screen = ScreenNode('main')
        text = TextNode_Terminal()
        text.content = 'Hello'
        screen.add_child(text)
        code = codegen.generate([screen], terminal_css='#panel { border: solid green; }')
        assert 'CSS = """#panel { border: solid green; }"""' in code


class TestEventHandlers:
    """Test event handler generation."""

    def test_button_on_click_handler(self, codegen):
        screen = ScreenNode('main')
        btn = ButtonNode()
        btn.button_id = 'send-btn'
        btn.label = 'Send'
        btn.on_click = 'send_message'
        screen.add_child(btn)
        code = codegen.generate([screen])
        assert 'on_button_pressed' in code
        assert 'send-btn' in code

    def test_input_on_submit_handler(self, codegen):
        screen = ScreenNode('main')
        inp = TerminalInputNode()
        inp.input_id = 'user-input'
        inp.on_submit = 'handle_input'
        screen.add_child(inp)
        code = codegen.generate([screen])
        assert 'on_input_submitted' in code
        assert 'user-input' in code


class TestFunctionGeneration:
    """Test user function generation."""

    def test_function_becomes_method(self, codegen):
        screen = ScreenNode('main')
        func = FunctionNode('do_something')
        text = TextNode_Terminal()
        text.content = 'Hello'
        screen.add_child(func)
        screen.add_child(text)
        code = codegen.generate([screen])
        assert 'def do_something(self)' in code


class TestFullPipeline:
    """Integration: parse + generate."""

    def test_parse_and_generate_basic(self, parser):
        src = '''<q:application id="my-app" type="terminal">
            <qt:screen name="main" title="My App">
                <qt:header title="My App"/>
                <qt:text id="hello">Hello World</qt:text>
                <qt:footer/>
                <qt:keybinding key="q" action="quit" description="Quit"/>
            </qt:screen>
        </q:application>'''
        ast = parser.parse(src)

        codegen = TerminalCodeGenerator()
        code = codegen.generate(
            screens=[s for s in ast.screens],
            title=ast.app_id,
            terminal_css=ast.terminal_css,
        )
        assert 'from textual.app import App' in code
        assert 'yield Header()' in code
        assert 'yield Footer()' in code
        assert 'Hello World' in code
        assert 'BINDINGS' in code

    def test_parse_and_generate_dashboard(self, parser):
        src = '''<q:application id="dashboard" type="terminal">
            <qt:css>
                #cpu-panel { border: solid green; }
            </qt:css>
            <qt:screen name="main" title="Dashboard">
                <qt:header title="Dashboard" show-clock="true"/>
                <q:set name="cpu_pct" type="integer" value="50"/>
                <qt:layout direction="horizontal">
                    <qt:panel id="cpu-panel" title="CPU">
                        <qt:progress id="cpu-bar" total="100"/>
                        <qt:text>{cpu_pct}%</qt:text>
                    </qt:panel>
                </qt:layout>
                <qt:footer/>
                <qt:keybinding key="q" action="quit" description="Quit"/>
                <qt:timer id="refresh" interval="5.0" action="refresh_data"/>
            </qt:screen>
        </q:application>'''
        ast = parser.parse(src)

        codegen = TerminalCodeGenerator()
        code = codegen.generate(
            screens=[s for s in ast.screens],
            title=ast.app_id,
            terminal_css=ast.terminal_css,
        )
        assert 'cpu_pct = reactive(50)' in code
        assert 'with Horizontal(' in code
        assert 'yield ProgressBar(' in code
        assert 'set_interval(5.0' in code
        assert '#cpu-panel' in code
