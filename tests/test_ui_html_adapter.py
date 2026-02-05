"""
Tests for UI Engine HTML Adapter + Desktop Adapter

Tests generation of HTML/CSS from UI AST nodes.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import pytest
from core.parser import QuantumParser
from core.ast_nodes import ApplicationNode
from core.features.ui_engine.src.ast_nodes import (
    UIWindowNode, UIHBoxNode, UIVBoxNode, UIPanelNode,
    UITabPanelNode, UITabNode, UIGridNode, UITextNode,
    UIButtonNode, UIInputNode, UICheckboxNode, UISwitchNode,
    UISelectNode, UITableNode, UIColumnNode, UIProgressNode,
    UIImageNode, UIRuleNode, UILoadingNode, UIBadgeNode,
    UIHeaderNode, UIFooterNode, UILogNode, UIFormNode,
    UIFormItemNode, UIAccordionNode, UISectionNode,
    UIScrollBoxNode, UISpacerNode,
)
from runtime.ui_html_adapter import UIHtmlAdapter
from runtime.ui_builder import UIBuilder


@pytest.fixture
def parser():
    return QuantumParser()


@pytest.fixture
def adapter():
    return UIHtmlAdapter()


def parse_ui(parser, body: str) -> ApplicationNode:
    source = f'<q:application id="test" type="ui">{body}</q:application>'
    return parser.parse(source)


# ============================================
# HTML Container tests
# ============================================

class TestHtmlContainers:
    def test_hbox_flex_row(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:hbox><ui:text>A</ui:text></ui:hbox></ui:window>')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'flex-direction: row' in html

    def test_vbox_flex_column(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:vbox><ui:text>A</ui:text></ui:vbox></ui:window>')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'flex-direction: column' in html

    def test_panel_with_title(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:panel title="CPU"><ui:text>45%</ui:text></ui:panel></ui:window>')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'q-panel' in html
        assert 'CPU' in html
        assert 'q-panel-title' in html

    def test_tabpanel_generates_tabs(self, parser, adapter):
        src = '''
        <ui:window title="T">
            <ui:tabpanel>
                <ui:tab title="Tab1"><ui:text>C1</ui:text></ui:tab>
                <ui:tab title="Tab2"><ui:text>C2</ui:text></ui:tab>
            </ui:tabpanel>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'q-tabs' in html
        assert 'q-tab-headers' in html
        assert 'Tab1' in html
        assert 'Tab2' in html
        assert 'q-tab-content' in html

    def test_grid_css_grid(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:grid columns="3"><ui:text>A</ui:text></ui:grid></ui:window>')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'display: grid' in html
        assert 'repeat(3, 1fr)' in html

    def test_nested_containers(self, parser, adapter):
        src = '''
        <ui:window title="T">
            <ui:hbox>
                <ui:vbox><ui:text>Inner</ui:text></ui:vbox>
            </ui:hbox>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'flex-direction: row' in html
        assert 'flex-direction: column' in html
        assert 'Inner' in html

    def test_accordion_details(self, parser, adapter):
        src = '''
        <ui:window title="T">
            <ui:accordion>
                <ui:section title="Sec1" expanded="true"><ui:text>Content</ui:text></ui:section>
            </ui:accordion>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert '<details' in html
        assert '<summary>' in html
        assert 'Sec1' in html

    def test_form(self, parser, adapter):
        src = '''
        <ui:window title="T">
            <ui:form on-submit="save">
                <ui:formitem label="Name">
                    <ui:input bind="name" />
                </ui:formitem>
            </ui:form>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert '<form' in html
        assert 'q-form' in html
        assert 'q-formitem' in html
        assert 'Name' in html


# ============================================
# HTML Widget tests
# ============================================

class TestHtmlWidgets:
    def test_button(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:button variant="primary">Click</ui:button></ui:window>')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert '<button' in html
        assert 'q-btn' in html
        assert 'q-btn-primary' in html
        assert 'Click' in html

    def test_input(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:input bind="email" placeholder="Enter email" type="email" /></ui:window>')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert '<input' in html
        assert 'q-input' in html
        assert 'type="email"' in html
        assert 'placeholder="Enter email"' in html

    def test_table(self, parser, adapter):
        src = '''
        <ui:window title="T">
            <ui:table source="{data}">
                <ui:column key="id" label="ID" />
                <ui:column key="name" label="Name" />
            </ui:table>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert '<table' in html
        assert 'q-table' in html
        assert '<thead>' in html
        assert '<th' in html
        assert 'ID' in html
        assert 'Name' in html

    def test_image(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:image src="/logo.png" alt="Logo" /></ui:window>')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert '<img' in html
        assert 'src="/logo.png"' in html
        assert 'alt="Logo"' in html

    def test_progress(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:progress value="45" max="100" /></ui:window>')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert '<progress' in html
        assert 'value="45"' in html
        assert 'max="100"' in html

    def test_text(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:text size="xl" weight="bold">Hello</ui:text></ui:window>')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'Hello' in html
        assert 'font-size' in html
        assert 'font-weight: bold' in html

    def test_badge(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:badge variant="success">Active</ui:badge></ui:window>')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'q-badge' in html
        assert 'q-badge-success' in html
        assert 'Active' in html

    def test_rule(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:rule /></ui:window>')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert '<hr' in html

    def test_loading(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:loading text="Wait..." /></ui:window>')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'q-loading' in html
        assert 'q-spinner' in html
        assert 'Wait...' in html

    def test_checkbox(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:checkbox bind="agree" label="I agree" /></ui:window>')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'type="checkbox"' in html
        assert 'I agree' in html

    def test_switch(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:switch bind="dark" label="Dark mode" /></ui:window>')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'q-switch' in html
        assert 'Dark mode' in html

    def test_header_footer(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:header title="Title" /><ui:footer>v1.0</ui:footer></ui:window>')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert '<header' in html
        assert 'q-header' in html
        assert 'Title' in html
        assert '<footer' in html
        assert 'q-footer' in html
        assert 'v1.0' in html

    def test_log(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:log /></ui:window>')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'q-log' in html


# ============================================
# Layout to CSS tests
# ============================================

class TestLayoutToCSS:
    def test_gap_to_css(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:hbox gap="8"><ui:text>A</ui:text></ui:hbox></ui:window>')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'gap: 8px' in html

    def test_padding_to_css(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:hbox padding="16"><ui:text>A</ui:text></ui:hbox></ui:window>')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'padding: 16px' in html

    def test_width_fill(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:panel title="P" width="fill"><ui:text>A</ui:text></ui:panel></ui:window>')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'width: 100%' in html

    def test_width_pixels(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:panel title="P" width="300"><ui:text>A</ui:text></ui:panel></ui:window>')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'width: 300px' in html

    def test_width_percentage(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:panel title="P" width="50%"><ui:text>A</ui:text></ui:panel></ui:window>')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'width: 50%' in html

    def test_align_center(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:vbox align="center"><ui:text>A</ui:text></ui:vbox></ui:window>')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'align-items: center' in html

    def test_justify_between(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:hbox justify="between"><ui:text>A</ui:text></ui:hbox></ui:window>')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'justify-content: space-between' in html

    def test_background_theme_color(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:vbox background="primary"><ui:text>A</ui:text></ui:vbox></ui:window>')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'var(--q-primary)' in html


# ============================================
# Integration tests
# ============================================

class TestIntegration:
    def test_full_dashboard_html(self, parser, adapter):
        """Full dashboard generates valid HTML."""
        src = '''
        <ui:window title="Dashboard">
            <ui:header title="Dashboard" />
            <ui:hbox gap="16" padding="16">
                <ui:panel title="CPU" width="50%">
                    <ui:vbox align="center">
                        <ui:text size="xl" weight="bold">45%</ui:text>
                        <ui:progress value="45" max="100" />
                    </ui:vbox>
                </ui:panel>
            </ui:hbox>
            <ui:footer>v1.0</ui:footer>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        html = adapter.generate(app.ui_windows, app.ui_children, 'Dashboard')
        assert '<!DOCTYPE html>' in html
        assert '<title>Dashboard</title>' in html
        assert 'Dashboard' in html
        assert 'q-panel' in html
        assert '<progress' in html

    def test_builder_html_target(self, parser):
        """UIBuilder with html target produces valid HTML."""
        app = parse_ui(parser, '<ui:window title="T"><ui:text>Hello</ui:text></ui:window>')
        builder = UIBuilder()
        html = builder.build(app, target='html')
        assert '<!DOCTYPE html>' in html
        assert 'Hello' in html

    def test_html_contains_css_reset(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:text>A</ui:text></ui:window>')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'box-sizing: border-box' in html

    def test_html_contains_theme(self, parser, adapter):
        app = parse_ui(parser, '<ui:window title="T"><ui:text>A</ui:text></ui:window>')
        html = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert '--q-primary' in html


# ============================================
# Desktop Adapter tests
# ============================================

class TestDesktopAdapter:
    def test_desktop_generates_python(self, parser):
        """Desktop adapter generates valid Python."""
        app = parse_ui(parser, '<ui:window title="T"><ui:text>Hello</ui:text></ui:window>')
        builder = UIBuilder()
        code = builder.build(app, target='desktop')
        assert 'import webview' in code
        assert 'webview.create_window' in code
        assert 'webview.start()' in code

    def test_desktop_contains_html(self, parser):
        """Desktop adapter embeds HTML content."""
        app = parse_ui(parser, '<ui:window title="T"><ui:text>Hello</ui:text></ui:window>')
        builder = UIBuilder()
        code = builder.build(app, target='desktop')
        assert 'Hello' in code
        assert 'DOCTYPE html' in code

    def test_desktop_code_compiles(self, parser):
        """Desktop generated Python compiles successfully."""
        app = parse_ui(parser, '<ui:window title="T"><ui:text>Hello</ui:text></ui:window>')
        builder = UIBuilder()
        code = builder.build(app, target='desktop')
        compile(code, '<test>', 'exec')
