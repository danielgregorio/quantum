"""
Tests for Terminal Engine Parser

Verifies that terminal XML (qt: namespace) is correctly parsed into Terminal AST nodes.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.parser import QuantumParser, QuantumParseError
from core.ast_nodes import ApplicationNode, SetNode, FunctionNode
from core.features.terminal_engine.src.ast_nodes import (
    ScreenNode, PanelNode, LayoutNode, TableNode, ColumnNode,
    TerminalInputNode, ButtonNode, MenuNode, OptionNode,
    TextNode_Terminal, ProgressNode, TreeNode, TabsNode, TabNode,
    LogNode_Terminal, HeaderNode_Terminal, FooterNode, StatusNode,
    KeybindingNode, TimerNode_Terminal, ServiceNode, CssNode,
    OnEventNode_Terminal,
)


@pytest.fixture
def parser():
    return QuantumParser()


class TestTerminalNamespaceInjection:
    """Test automatic namespace injection for qt: prefix."""

    def test_auto_inject_qt_namespace(self, parser):
        src = '''<q:application id="test" type="terminal">
            <qt:screen name="main" title="Test">
                <qt:text>Hello</qt:text>
            </qt:screen>
        </q:application>'''
        ast = parser.parse(src)
        assert isinstance(ast, ApplicationNode)
        assert ast.app_type == 'terminal'

    def test_terminal_app_has_screens(self, parser):
        src = '''<q:application id="test" type="terminal">
            <qt:screen name="main" title="Test">
                <qt:text>Hello</qt:text>
            </qt:screen>
        </q:application>'''
        ast = parser.parse(src)
        assert len(ast.screens) == 1
        assert isinstance(ast.screens[0], ScreenNode)
        assert ast.screens[0].name == 'main'
        assert ast.screens[0].title == 'Test'


class TestScreenParsing:
    """Test <qt:screen> parsing."""

    def test_screen_attributes(self, parser):
        src = '''<q:application id="g" type="terminal">
            <qt:screen name="dashboard" title="My Dashboard">
                <qt:text>Content</qt:text>
            </qt:screen>
        </q:application>'''
        ast = parser.parse(src)
        screen = ast.screens[0]
        assert screen.name == 'dashboard'
        assert screen.title == 'My Dashboard'

    def test_screen_children(self, parser):
        src = '''<q:application id="g" type="terminal">
            <qt:screen name="main" title="Test">
                <qt:header title="App Title"/>
                <qt:text id="msg">Hello World</qt:text>
                <qt:footer/>
                <q:set name="counter" value="0" type="integer"/>
            </qt:screen>
        </q:application>'''
        ast = parser.parse(src)
        screen = ast.screens[0]
        children = screen.children

        # Should have header, text, footer, and set
        types = [type(c).__name__ for c in children]
        assert 'HeaderNode_Terminal' in types
        assert 'TextNode_Terminal' in types
        assert 'FooterNode' in types
        assert 'SetNode' in types


class TestWidgetParsing:
    """Test individual widget parsing."""

    def test_header(self, parser):
        src = '''<q:application id="t" type="terminal">
            <qt:screen name="main">
                <qt:header title="My App" show-clock="true"/>
            </qt:screen>
        </q:application>'''
        ast = parser.parse(src)
        header = ast.screens[0].children[0]
        assert isinstance(header, HeaderNode_Terminal)
        assert header.title == 'My App'
        assert header.show_clock is True

    def test_footer(self, parser):
        src = '''<q:application id="t" type="terminal">
            <qt:screen name="main">
                <qt:footer/>
            </qt:screen>
        </q:application>'''
        ast = parser.parse(src)
        footer = ast.screens[0].children[0]
        assert isinstance(footer, FooterNode)

    def test_text(self, parser):
        src = '''<q:application id="t" type="terminal">
            <qt:screen name="main">
                <qt:text id="msg">Hello World</qt:text>
            </qt:screen>
        </q:application>'''
        ast = parser.parse(src)
        text = ast.screens[0].children[0]
        assert isinstance(text, TextNode_Terminal)
        assert text.text_id == 'msg'
        assert text.content == 'Hello World'

    def test_input(self, parser):
        src = '''<q:application id="t" type="terminal">
            <qt:screen name="main">
                <qt:input id="user-input" placeholder="Type here..." on-submit="handle_input"/>
            </qt:screen>
        </q:application>'''
        ast = parser.parse(src)
        inp = ast.screens[0].children[0]
        assert isinstance(inp, TerminalInputNode)
        assert inp.input_id == 'user-input'
        assert inp.placeholder == 'Type here...'
        assert inp.on_submit == 'handle_input'

    def test_button(self, parser):
        src = '''<q:application id="t" type="terminal">
            <qt:screen name="main">
                <qt:button id="btn" label="Click Me" variant="primary" on-click="do_thing"/>
            </qt:screen>
        </q:application>'''
        ast = parser.parse(src)
        btn = ast.screens[0].children[0]
        assert isinstance(btn, ButtonNode)
        assert btn.button_id == 'btn'
        assert btn.label == 'Click Me'
        assert btn.variant == 'primary'
        assert btn.on_click == 'do_thing'

    def test_progress(self, parser):
        src = '''<q:application id="t" type="terminal">
            <qt:screen name="main">
                <qt:progress id="bar" total="200" value-var="pct"/>
            </qt:screen>
        </q:application>'''
        ast = parser.parse(src)
        prog = ast.screens[0].children[0]
        assert isinstance(prog, ProgressNode)
        assert prog.progress_id == 'bar'
        assert prog.total == 200
        assert prog.value_var == 'pct'

    def test_log(self, parser):
        src = '''<q:application id="t" type="terminal">
            <qt:screen name="main">
                <qt:log id="chat-log" auto-scroll="true" markup="true" max-lines="100"/>
            </qt:screen>
        </q:application>'''
        ast = parser.parse(src)
        log = ast.screens[0].children[0]
        assert isinstance(log, LogNode_Terminal)
        assert log.log_id == 'chat-log'
        assert log.auto_scroll is True
        assert log.markup is True
        assert log.max_lines == 100

    def test_tree(self, parser):
        src = '''<q:application id="t" type="terminal">
            <qt:screen name="main">
                <qt:tree id="file-tree" label="." on-select="on_file_select"/>
            </qt:screen>
        </q:application>'''
        ast = parser.parse(src)
        tree = ast.screens[0].children[0]
        assert isinstance(tree, TreeNode)
        assert tree.tree_id == 'file-tree'
        assert tree.label == '.'
        assert tree.on_select == 'on_file_select'

    def test_keybinding(self, parser):
        src = '''<q:application id="t" type="terminal">
            <qt:screen name="main">
                <qt:keybinding key="q" action="quit" description="Quit"/>
            </qt:screen>
        </q:application>'''
        ast = parser.parse(src)
        kb = ast.screens[0].children[0]
        assert isinstance(kb, KeybindingNode)
        assert kb.key == 'q'
        assert kb.action == 'quit'
        assert kb.description == 'Quit'

    def test_timer(self, parser):
        src = '''<q:application id="t" type="terminal">
            <qt:screen name="main">
                <qt:timer id="refresh" interval="5.0" action="refresh_data"/>
            </qt:screen>
        </q:application>'''
        ast = parser.parse(src)
        timer = ast.screens[0].children[0]
        assert isinstance(timer, TimerNode_Terminal)
        assert timer.timer_id == 'refresh'
        assert timer.interval == 5.0
        assert timer.action == 'refresh_data'


class TestContainerParsing:
    """Test container widgets (panel, layout, tabs)."""

    def test_panel(self, parser):
        src = '''<q:application id="t" type="terminal">
            <qt:screen name="main">
                <qt:panel id="info" title="Info Panel">
                    <qt:text>Content</qt:text>
                </qt:panel>
            </qt:screen>
        </q:application>'''
        ast = parser.parse(src)
        panel = ast.screens[0].children[0]
        assert isinstance(panel, PanelNode)
        assert panel.panel_id == 'info'
        assert panel.title == 'Info Panel'
        assert len(panel.children) == 1
        assert isinstance(panel.children[0], TextNode_Terminal)

    def test_layout_horizontal(self, parser):
        src = '''<q:application id="t" type="terminal">
            <qt:screen name="main">
                <qt:layout direction="horizontal">
                    <qt:text>Left</qt:text>
                    <qt:text>Right</qt:text>
                </qt:layout>
            </qt:screen>
        </q:application>'''
        ast = parser.parse(src)
        layout = ast.screens[0].children[0]
        assert isinstance(layout, LayoutNode)
        assert layout.direction == 'horizontal'
        assert len(layout.children) == 2

    def test_table_with_columns(self, parser):
        src = '''<q:application id="t" type="terminal">
            <qt:screen name="main">
                <qt:table id="data" data-source="results" zebra="true">
                    <qt:column name="Name" key="name" width="30"/>
                    <qt:column name="Value" key="value" align="right"/>
                </qt:table>
            </qt:screen>
        </q:application>'''
        ast = parser.parse(src)
        table = ast.screens[0].children[0]
        assert isinstance(table, TableNode)
        assert table.table_id == 'data'
        assert table.data_source == 'results'
        assert table.zebra is True
        assert len(table.columns) == 2
        assert table.columns[0].name == 'Name'
        assert table.columns[0].key == 'name'
        assert table.columns[0].width == 30
        assert table.columns[1].align == 'right'

    def test_tabs_with_content(self, parser):
        src = '''<q:application id="t" type="terminal">
            <qt:screen name="main">
                <qt:tabs id="main-tabs">
                    <qt:tab title="Tab 1">
                        <qt:text>Content 1</qt:text>
                    </qt:tab>
                    <qt:tab title="Tab 2">
                        <qt:text>Content 2</qt:text>
                    </qt:tab>
                </qt:tabs>
            </qt:screen>
        </q:application>'''
        ast = parser.parse(src)
        tabs = ast.screens[0].children[0]
        assert isinstance(tabs, TabsNode)
        assert tabs.tabs_id == 'main-tabs'
        assert len(tabs.tabs) == 2
        assert tabs.tabs[0].title == 'Tab 1'
        assert isinstance(tabs.tabs[0].children[0], TextNode_Terminal)

    def test_menu_with_options(self, parser):
        src = '''<q:application id="t" type="terminal">
            <qt:screen name="main">
                <qt:menu id="main-menu" on-select="handle_select">
                    <qt:option value="opt1" label="Option 1"/>
                    <qt:option value="opt2" label="Option 2"/>
                </qt:menu>
            </qt:screen>
        </q:application>'''
        ast = parser.parse(src)
        menu = ast.screens[0].children[0]
        assert isinstance(menu, MenuNode)
        assert menu.menu_id == 'main-menu'
        assert len(menu.options) == 2
        assert menu.options[0].value == 'opt1'
        assert menu.options[0].label == 'Option 1'


class TestCssParsing:
    """Test <qt:css> at top level."""

    def test_css_block(self, parser):
        src = '''<q:application id="t" type="terminal">
            <qt:css>
                #panel { border: solid green; }
            </qt:css>
            <qt:screen name="main">
                <qt:text>Hello</qt:text>
            </qt:screen>
        </q:application>'''
        ast = parser.parse(src)
        assert '#panel { border: solid green; }' in ast.terminal_css


class TestQuantumTagsInTerminal:
    """Test that q: tags work inside qt: screens."""

    def test_set_variable(self, parser):
        src = '''<q:application id="t" type="terminal">
            <qt:screen name="main">
                <q:set name="counter" value="0" type="integer"/>
                <qt:text>{counter}</qt:text>
            </qt:screen>
        </q:application>'''
        ast = parser.parse(src)
        children = ast.screens[0].children
        set_nodes = [c for c in children if isinstance(c, SetNode)]
        assert len(set_nodes) == 1
        assert set_nodes[0].name == 'counter'
        assert set_nodes[0].value == '0'

    def test_function(self, parser):
        src = '''<q:application id="t" type="terminal">
            <qt:screen name="main">
                <q:function name="do_something">
                    <q:set name="x" value="1"/>
                </q:function>
                <qt:text>Hello</qt:text>
            </qt:screen>
        </q:application>'''
        ast = parser.parse(src)
        children = ast.screens[0].children
        func_nodes = [c for c in children if isinstance(c, FunctionNode)]
        assert len(func_nodes) == 1
        assert func_nodes[0].name == 'do_something'


class TestIntegration:
    """Integration tests: parse a full terminal app."""

    def test_full_dashboard(self, parser):
        src = '''<q:application id="server-dashboard" type="terminal">
            <qt:css>
                #cpu-panel { border: solid green; }
            </qt:css>
            <qt:screen name="main" title="Server Dashboard">
                <qt:header title="Server Dashboard" show-clock="true"/>
                <q:set name="cpu_pct" type="integer" value="0"/>
                <qt:layout direction="horizontal">
                    <qt:panel id="cpu-panel" title="CPU Usage">
                        <qt:progress id="cpu-bar" total="100" value-var="cpu_pct"/>
                        <qt:text>{cpu_pct}% used</qt:text>
                    </qt:panel>
                </qt:layout>
                <qt:footer/>
                <qt:keybinding key="q" action="quit" description="Quit"/>
                <qt:keybinding key="r" action="refresh_data" description="Refresh"/>
                <qt:timer id="auto-refresh" interval="5.0" action="refresh_data"/>
            </qt:screen>
        </q:application>'''
        ast = parser.parse(src)
        assert isinstance(ast, ApplicationNode)
        assert ast.app_type == 'terminal'
        assert len(ast.screens) == 1
        assert '#cpu-panel' in ast.terminal_css

        screen = ast.screens[0]
        assert screen.title == 'Server Dashboard'

        # Check children types
        types = [type(c).__name__ for c in screen.children]
        assert 'HeaderNode_Terminal' in types
        assert 'SetNode' in types
        assert 'LayoutNode' in types
        assert 'FooterNode' in types
        assert 'KeybindingNode' in types
        assert 'TimerNode_Terminal' in types

    def test_full_chat_app(self, parser):
        src = '''<q:application id="llm-chat" type="terminal">
            <qt:screen name="chat" title="Chat">
                <qt:header title="Chat"/>
                <q:set name="model" value="llama3"/>
                <qt:log id="chat-log" auto-scroll="true" markup="true"/>
                <qt:layout direction="horizontal" id="input-bar">
                    <qt:input id="user-input" placeholder="Type a message..." on-submit="send_message"/>
                    <qt:button id="send-btn" label="Send" variant="primary" on-click="send_message"/>
                </qt:layout>
                <qt:footer/>
                <qt:keybinding key="ctrl+c" action="quit" description="Quit"/>
            </qt:screen>
        </q:application>'''
        ast = parser.parse(src)
        assert len(ast.screens) == 1
        screen = ast.screens[0]

        # Find the layout
        layouts = [c for c in screen.children if isinstance(c, LayoutNode)]
        assert len(layouts) == 1
        layout = layouts[0]
        assert layout.direction == 'horizontal'
        assert len(layout.children) == 2
        assert isinstance(layout.children[0], TerminalInputNode)
        assert isinstance(layout.children[1], ButtonNode)
