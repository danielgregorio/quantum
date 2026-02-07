"""
Tests for UI Engine Parser (ui: namespace)

Tests parsing of ui: tags into UI AST nodes.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import pytest
from core.parser import QuantumParser, QuantumParseError
from core.ast_nodes import ApplicationNode
from core.features.ui_engine.src.ast_nodes import (
    UIWindowNode, UIHBoxNode, UIVBoxNode, UIPanelNode,
    UITabPanelNode, UITabNode, UIGridNode, UIAccordionNode,
    UISectionNode, UIDividedBoxNode, UIFormNode, UIFormItemNode,
    UISpacerNode, UIScrollBoxNode,
    UITextNode, UIButtonNode, UIInputNode, UICheckboxNode,
    UIRadioNode, UISwitchNode, UISelectNode, UITableNode,
    UIColumnNode, UIListNode, UIItemNode, UIImageNode,
    UILinkNode, UIProgressNode, UITreeNode, UIMenuNode,
    UIOptionNode, UILogNode, UIMarkdownNode, UIHeaderNode,
    UIFooterNode, UIRuleNode, UILoadingNode, UIBadgeNode,
)
from core.features.state_management.src.ast_node import SetNode
from core.features.conditionals.src.ast_node import IfNode
from core.features.loops.src.ast_node import LoopNode


@pytest.fixture
def parser():
    return QuantumParser()


def parse_ui(parser, body: str) -> ApplicationNode:
    """Helper: wrap body in <q:application type="ui"> and parse."""
    source = f'<q:application id="test" type="ui">{body}</q:application>'
    return parser.parse(source)


# ============================================
# Namespace auto-injection
# ============================================

class TestUINamespace:
    def test_auto_inject_ui_namespace(self, parser):
        """ui: namespace is auto-injected for type='ui' apps."""
        app = parse_ui(parser, '<ui:window title="Test" />')
        assert isinstance(app, ApplicationNode)
        assert app.app_type == 'ui'

    def test_app_type_detected(self, parser):
        """Application type is 'ui'."""
        app = parse_ui(parser, '')
        assert app.app_type == 'ui'

    def test_ui_window_parsed(self, parser):
        """<ui:window> is parsed into UIWindowNode."""
        app = parse_ui(parser, '<ui:window title="My Window" />')
        assert len(app.ui_windows) == 1
        assert isinstance(app.ui_windows[0], UIWindowNode)
        assert app.ui_windows[0].title == "My Window"


# ============================================
# Container Parsing
# ============================================

class TestContainerParsing:
    def test_hbox(self, parser):
        app = parse_ui(parser, '<ui:window title="T"><ui:hbox gap="8" /></ui:window>')
        window = app.ui_windows[0]
        assert len(window.children) == 1
        assert isinstance(window.children[0], UIHBoxNode)
        assert window.children[0].gap == '8'

    def test_vbox(self, parser):
        app = parse_ui(parser, '<ui:window title="T"><ui:vbox align="center" /></ui:window>')
        window = app.ui_windows[0]
        assert isinstance(window.children[0], UIVBoxNode)
        assert window.children[0].align == 'center'

    def test_panel(self, parser):
        app = parse_ui(parser, '<ui:window title="T"><ui:panel title="CPU" collapsible="true" /></ui:window>')
        panel = app.ui_windows[0].children[0]
        assert isinstance(panel, UIPanelNode)
        assert panel.title == 'CPU'
        assert panel.collapsible is True

    def test_tabpanel_with_tabs(self, parser):
        src = '''
        <ui:window title="T">
            <ui:tabpanel>
                <ui:tab title="Tab1"><ui:text>Content1</ui:text></ui:tab>
                <ui:tab title="Tab2"><ui:text>Content2</ui:text></ui:tab>
            </ui:tabpanel>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        tabpanel = app.ui_windows[0].children[0]
        assert isinstance(tabpanel, UITabPanelNode)
        assert len(tabpanel.children) == 2
        assert isinstance(tabpanel.children[0], UITabNode)
        assert tabpanel.children[0].title == 'Tab1'

    def test_grid(self, parser):
        app = parse_ui(parser, '<ui:window title="T"><ui:grid columns="3" /></ui:window>')
        grid = app.ui_windows[0].children[0]
        assert isinstance(grid, UIGridNode)
        assert grid.columns == '3'

    def test_accordion_with_sections(self, parser):
        src = '''
        <ui:window title="T">
            <ui:accordion>
                <ui:section title="S1" expanded="true"><ui:text>A</ui:text></ui:section>
                <ui:section title="S2"><ui:text>B</ui:text></ui:section>
            </ui:accordion>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        accordion = app.ui_windows[0].children[0]
        assert isinstance(accordion, UIAccordionNode)
        assert len(accordion.children) == 2
        s1 = accordion.children[0]
        assert isinstance(s1, UISectionNode)
        assert s1.title == 'S1'
        assert s1.expanded is True

    def test_form_with_formitems(self, parser):
        src = '''
        <ui:window title="T">
            <ui:form on-submit="save">
                <ui:formitem label="Name">
                    <ui:input bind="name" placeholder="Enter name" />
                </ui:formitem>
            </ui:form>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        form = app.ui_windows[0].children[0]
        assert isinstance(form, UIFormNode)
        assert form.on_submit == 'save'
        assert len(form.children) == 1
        fi = form.children[0]
        assert isinstance(fi, UIFormItemNode)
        assert fi.label == 'Name'

    def test_scrollbox(self, parser):
        app = parse_ui(parser, '<ui:window title="T"><ui:scrollbox><ui:text>content</ui:text></ui:scrollbox></ui:window>')
        sb = app.ui_windows[0].children[0]
        assert isinstance(sb, UIScrollBoxNode)
        assert len(sb.children) == 1

    def test_dividedbox(self, parser):
        app = parse_ui(parser, '<ui:window title="T"><ui:dividedbox direction="vertical"><ui:text>left</ui:text><ui:text>right</ui:text></ui:dividedbox></ui:window>')
        db = app.ui_windows[0].children[0]
        assert isinstance(db, UIDividedBoxNode)
        assert db.direction == 'vertical'
        assert len(db.children) == 2

    def test_nested_containers(self, parser):
        src = '''
        <ui:window title="T">
            <ui:hbox>
                <ui:vbox>
                    <ui:panel title="Inner" />
                </ui:vbox>
            </ui:hbox>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        hbox = app.ui_windows[0].children[0]
        assert isinstance(hbox, UIHBoxNode)
        vbox = hbox.children[0]
        assert isinstance(vbox, UIVBoxNode)
        panel = vbox.children[0]
        assert isinstance(panel, UIPanelNode)
        assert panel.title == 'Inner'

    def test_spacer(self, parser):
        app = parse_ui(parser, '<ui:window title="T"><ui:spacer size="32" /></ui:window>')
        spacer = app.ui_windows[0].children[0]
        assert isinstance(spacer, UISpacerNode)
        assert spacer.size == '32'


# ============================================
# Widget Parsing
# ============================================

class TestWidgetParsing:
    def test_text(self, parser):
        app = parse_ui(parser, '<ui:window title="T"><ui:text size="xl" weight="bold">Hello</ui:text></ui:window>')
        text = app.ui_windows[0].children[0]
        assert isinstance(text, UITextNode)
        assert text.content == 'Hello'
        assert text.size == 'xl'
        assert text.weight == 'bold'

    def test_button(self, parser):
        app = parse_ui(parser, '<ui:window title="T"><ui:button on-click="doIt" variant="primary" disabled="true">Click</ui:button></ui:window>')
        btn = app.ui_windows[0].children[0]
        assert isinstance(btn, UIButtonNode)
        assert btn.content == 'Click'
        assert btn.on_click == 'doIt'
        assert btn.variant == 'primary'
        assert btn.disabled is True

    def test_input(self, parser):
        app = parse_ui(parser, '<ui:window title="T"><ui:input bind="name" placeholder="Enter" type="email" /></ui:window>')
        inp = app.ui_windows[0].children[0]
        assert isinstance(inp, UIInputNode)
        assert inp.bind == 'name'
        assert inp.placeholder == 'Enter'
        assert inp.input_type == 'email'

    def test_checkbox(self, parser):
        app = parse_ui(parser, '<ui:window title="T"><ui:checkbox bind="agree" label="I agree" /></ui:window>')
        cb = app.ui_windows[0].children[0]
        assert isinstance(cb, UICheckboxNode)
        assert cb.bind == 'agree'
        assert cb.label == 'I agree'

    def test_radio(self, parser):
        app = parse_ui(parser, '<ui:window title="T"><ui:radio bind="color" options="red,green,blue" /></ui:window>')
        radio = app.ui_windows[0].children[0]
        assert isinstance(radio, UIRadioNode)
        assert radio.options == 'red,green,blue'

    def test_switch(self, parser):
        app = parse_ui(parser, '<ui:window title="T"><ui:switch bind="dark" label="Dark mode" /></ui:window>')
        sw = app.ui_windows[0].children[0]
        assert isinstance(sw, UISwitchNode)
        assert sw.bind == 'dark'
        assert sw.label == 'Dark mode'

    def test_select(self, parser):
        app = parse_ui(parser, '<ui:window title="T"><ui:select bind="size" options="S,M,L" /></ui:window>')
        sel = app.ui_windows[0].children[0]
        assert isinstance(sel, UISelectNode)
        assert sel.bind == 'size'
        assert sel.options == 'S,M,L'

    def test_table_with_columns(self, parser):
        src = '''
        <ui:window title="T">
            <ui:table source="{data}">
                <ui:column key="id" label="ID" width="80" align="right" />
                <ui:column key="name" label="Name" />
            </ui:table>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        table = app.ui_windows[0].children[0]
        assert isinstance(table, UITableNode)
        assert table.source == '{data}'
        assert len(table.children) == 2
        col = table.children[0]
        assert isinstance(col, UIColumnNode)
        assert col.key == 'id'
        assert col.label == 'ID'
        assert col.column_width == '80'
        assert col.align == 'right'

    def test_list_with_items(self, parser):
        src = '''
        <ui:window title="T">
            <ui:list source="{items}" as="item">
                <ui:item><ui:text>entry</ui:text></ui:item>
            </ui:list>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        lst = app.ui_windows[0].children[0]
        assert isinstance(lst, UIListNode)
        assert lst.source == '{items}'
        assert lst.as_var == 'item'
        item = lst.children[0]
        assert isinstance(item, UIItemNode)

    def test_image(self, parser):
        app = parse_ui(parser, '<ui:window title="T"><ui:image src="/logo.png" alt="Logo" /></ui:window>')
        img = app.ui_windows[0].children[0]
        assert isinstance(img, UIImageNode)
        assert img.src == '/logo.png'
        assert img.alt == 'Logo'

    def test_link(self, parser):
        app = parse_ui(parser, '<ui:window title="T"><ui:link to="/about" external="true">About</ui:link></ui:window>')
        link = app.ui_windows[0].children[0]
        assert isinstance(link, UILinkNode)
        assert link.to == '/about'
        assert link.external is True
        assert link.content == 'About'

    def test_progress(self, parser):
        app = parse_ui(parser, '<ui:window title="T"><ui:progress value="45" max="100" /></ui:window>')
        prog = app.ui_windows[0].children[0]
        assert isinstance(prog, UIProgressNode)
        assert prog.value == '45'
        assert prog.max == '100'

    def test_badge(self, parser):
        app = parse_ui(parser, '<ui:window title="T"><ui:badge variant="success">Active</ui:badge></ui:window>')
        badge = app.ui_windows[0].children[0]
        assert isinstance(badge, UIBadgeNode)
        assert badge.content == 'Active'
        assert badge.variant == 'success'

    def test_rule(self, parser):
        app = parse_ui(parser, '<ui:window title="T"><ui:rule /></ui:window>')
        rule = app.ui_windows[0].children[0]
        assert isinstance(rule, UIRuleNode)

    def test_loading(self, parser):
        app = parse_ui(parser, '<ui:window title="T"><ui:loading text="Please wait..." /></ui:window>')
        loading = app.ui_windows[0].children[0]
        assert isinstance(loading, UILoadingNode)
        assert loading.text == 'Please wait...'

    def test_log(self, parser):
        app = parse_ui(parser, '<ui:window title="T"><ui:log auto-scroll="true" max-lines="200" /></ui:window>')
        log = app.ui_windows[0].children[0]
        assert isinstance(log, UILogNode)
        assert log.auto_scroll is True
        assert log.max_lines == 200

    def test_markdown(self, parser):
        app = parse_ui(parser, '<ui:window title="T"><ui:markdown># Hello</ui:markdown></ui:window>')
        md = app.ui_windows[0].children[0]
        assert isinstance(md, UIMarkdownNode)
        assert md.content == '# Hello'

    def test_header(self, parser):
        app = parse_ui(parser, '<ui:window title="T"><ui:header title="Dashboard" /></ui:window>')
        header = app.ui_windows[0].children[0]
        assert isinstance(header, UIHeaderNode)
        assert header.title == 'Dashboard'

    def test_footer(self, parser):
        app = parse_ui(parser, '<ui:window title="T"><ui:footer>v1.0</ui:footer></ui:window>')
        footer = app.ui_windows[0].children[0]
        assert isinstance(footer, UIFooterNode)
        assert footer.content == 'v1.0'

    def test_tree(self, parser):
        app = parse_ui(parser, '<ui:window title="T"><ui:tree source="{files}" on-select="open" /></ui:window>')
        tree = app.ui_windows[0].children[0]
        assert isinstance(tree, UITreeNode)
        assert tree.source == '{files}'
        assert tree.on_select == 'open'

    def test_menu_with_options(self, parser):
        src = '''
        <ui:window title="T">
            <ui:menu>
                <ui:option value="home" label="Home" />
                <ui:option value="settings" label="Settings" on-click="openSettings" />
            </ui:menu>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        menu = app.ui_windows[0].children[0]
        assert isinstance(menu, UIMenuNode)
        assert len(menu.children) == 2
        opt = menu.children[1]
        assert isinstance(opt, UIOptionNode)
        assert opt.value == 'settings'
        assert opt.on_click == 'openSettings'


# ============================================
# Layout Attributes
# ============================================

class TestLayoutAttributes:
    def test_gap_padding_margin(self, parser):
        app = parse_ui(parser, '<ui:window title="T"><ui:hbox gap="16" padding="8" margin="4" /></ui:window>')
        hbox = app.ui_windows[0].children[0]
        assert hbox.gap == '16'
        assert hbox.padding == '8'
        assert hbox.margin == '4'

    def test_align_justify(self, parser):
        app = parse_ui(parser, '<ui:window title="T"><ui:vbox align="center" justify="between" /></ui:window>')
        vbox = app.ui_windows[0].children[0]
        assert vbox.align == 'center'
        assert vbox.justify == 'between'

    def test_width_height(self, parser):
        app = parse_ui(parser, '<ui:window title="T"><ui:panel title="P" width="50%" height="300" /></ui:window>')
        panel = app.ui_windows[0].children[0]
        assert panel.width == '50%'
        assert panel.height == '300'

    def test_background_color_border(self, parser):
        app = parse_ui(parser, '<ui:window title="T"><ui:vbox background="primary" color="white" border="1px solid red" /></ui:window>')
        vbox = app.ui_windows[0].children[0]
        assert vbox.background == 'primary'
        assert vbox.color == 'white'
        assert vbox.border == '1px solid red'

    def test_id_class_visible(self, parser):
        app = parse_ui(parser, '<ui:window title="T"><ui:hbox id="main" class="container" visible="false" /></ui:window>')
        hbox = app.ui_windows[0].children[0]
        assert hbox.ui_id == 'main'
        assert hbox.ui_class == 'container'
        assert hbox.visible == 'false'


# ============================================
# Quantum tags inside UI
# ============================================

class TestQuantumInsideUI:
    def test_qset_inside_window(self, parser):
        """q:set can be used inside ui: containers."""
        app = parse_ui(parser, '<ui:window title="T"><q:set name="x" value="10" /></ui:window>')
        children = app.ui_windows[0].children
        assert len(children) == 1
        assert isinstance(children[0], SetNode)
        assert children[0].name == 'x'

    def test_qset_at_app_level(self, parser):
        """q:set at top level of UI app goes to ui_children."""
        app = parse_ui(parser, '<q:set name="y" value="20" /><ui:window title="T" />')
        assert len(app.ui_children) == 1
        assert isinstance(app.ui_children[0], SetNode)

    def test_qloop_inside_container(self, parser):
        """q:loop can be used inside ui: containers."""
        src = '''
        <ui:window title="T">
            <ui:vbox>
                <q:loop var="i" type="range" from="1" to="5">
                    <q:set name="x" value="1" />
                </q:loop>
            </ui:vbox>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        vbox = app.ui_windows[0].children[0]
        loop = vbox.children[0]
        assert isinstance(loop, LoopNode)

    def test_qif_inside_container(self, parser):
        """q:if can be used inside ui: containers."""
        src = '''
        <ui:window title="T">
            <ui:hbox>
                <q:if condition="show">
                    <q:set name="x" value="1" />
                </q:if>
            </ui:hbox>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        hbox = app.ui_windows[0].children[0]
        assert isinstance(hbox.children[0], IfNode)


# ============================================
# Validation
# ============================================

class TestValidation:
    def test_window_without_title_ok(self, parser):
        """Window without title should still parse."""
        app = parse_ui(parser, '<ui:window />')
        assert len(app.ui_windows) == 1
        assert app.ui_windows[0].title is None

    def test_validates_successfully(self, parser):
        """Full app validates without errors."""
        src = '''
        <ui:window title="Test">
            <ui:hbox>
                <ui:text>Hello</ui:text>
                <ui:button variant="primary">Click</ui:button>
            </ui:hbox>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        errors = app.validate()
        assert errors == []


# ============================================
# Integration
# ============================================

class TestIntegration:
    def test_full_dashboard_parse(self, parser):
        """Parse a complete dashboard with multiple UI elements."""
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
                <ui:panel title="Memory" width="50%">
                    <ui:vbox align="center">
                        <ui:text size="xl" weight="bold">72%</ui:text>
                        <ui:progress value="72" max="100" />
                    </ui:vbox>
                </ui:panel>
            </ui:hbox>
            <ui:tabpanel>
                <ui:tab title="Processes">
                    <ui:table source="{processes}">
                        <ui:column key="pid" label="PID" />
                        <ui:column key="name" label="Name" />
                    </ui:table>
                </ui:tab>
                <ui:tab title="Logs">
                    <ui:log auto-scroll="true" />
                </ui:tab>
            </ui:tabpanel>
            <ui:footer>v1.0</ui:footer>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        assert len(app.ui_windows) == 1
        window = app.ui_windows[0]
        assert window.title == 'Dashboard'

        # header, hbox, tabpanel, footer
        assert len(window.children) == 4
        assert isinstance(window.children[0], UIHeaderNode)
        assert isinstance(window.children[1], UIHBoxNode)
        assert isinstance(window.children[2], UITabPanelNode)
        assert isinstance(window.children[3], UIFooterNode)

        # Check panels inside hbox
        hbox = window.children[1]
        assert len(hbox.children) == 2
        assert all(isinstance(c, UIPanelNode) for c in hbox.children)

        # Check tabs
        tabpanel = window.children[2]
        assert len(tabpanel.children) == 2
        assert all(isinstance(c, UITabNode) for c in tabpanel.children)

        # Validate
        errors = app.validate()
        assert errors == []
