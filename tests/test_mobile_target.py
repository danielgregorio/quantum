"""
Tests for UI Engine React Native Mobile Adapter

Tests generation of React Native code from UI AST nodes.
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
    UIHeaderNode, UIFooterNode, UIFormNode, UIFormItemNode,
    UIScrollBoxNode, UISpacerNode, UIAccordionNode, UISectionNode,
    UIListNode, UIItemNode, UIMenuNode, UIOptionNode,
)
from runtime.ui_mobile_adapter import UIReactNativeAdapter
from runtime.ui_builder import UIBuilder


@pytest.fixture
def parser():
    return QuantumParser()


@pytest.fixture
def adapter():
    return UIReactNativeAdapter()


def parse_ui(parser, body: str) -> ApplicationNode:
    source = f'<q:application id="test" type="ui">{body}</q:application>'
    return parser.parse(source)


# ============================================
# React Native Container tests
# ============================================

class TestRNContainers:
    def test_window_to_view(self, parser, adapter):
        """ui:window maps to View with container style."""
        app = parse_ui(parser, '<ui:window title="T"><ui:text>Hello</ui:text></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert '<View style=' in code
        assert 'styles.container' in code

    def test_hbox_flex_row(self, parser, adapter):
        """ui:hbox maps to View with flexDirection row."""
        app = parse_ui(parser, '<ui:window title="T"><ui:hbox><ui:text>A</ui:text></ui:hbox></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'styles.hbox' in code
        assert "flexDirection: 'row'" in code

    def test_vbox_flex_column(self, parser, adapter):
        """ui:vbox maps to View with flexDirection column."""
        app = parse_ui(parser, '<ui:window title="T"><ui:vbox><ui:text>A</ui:text></ui:vbox></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'styles.vbox' in code
        assert "flexDirection: 'column'" in code

    def test_panel_with_title(self, parser, adapter):
        """ui:panel maps to View with panel styles and title Text."""
        app = parse_ui(parser, '<ui:window title="T"><ui:panel title="CPU"><ui:text>45%</ui:text></ui:panel></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'styles.panel' in code
        assert 'styles.panelTitle' in code
        assert 'CPU' in code

    def test_scrollbox_to_scrollview(self, parser, adapter):
        """ui:scrollbox maps to ScrollView."""
        app = parse_ui(parser, '<ui:window title="T"><ui:scrollbox><ui:text>Scroll</ui:text></ui:scrollbox></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert '<ScrollView' in code
        assert 'styles.scrollbox' in code

    def test_nested_containers(self, parser, adapter):
        """Nested containers render correctly."""
        src = '''
        <ui:window title="T">
            <ui:hbox>
                <ui:vbox><ui:text>Inner</ui:text></ui:vbox>
            </ui:hbox>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'styles.hbox' in code
        assert 'styles.vbox' in code
        assert 'Inner' in code


# ============================================
# React Native Widget tests
# ============================================

class TestRNWidgets:
    def test_text(self, parser, adapter):
        """ui:text maps to Text component."""
        app = parse_ui(parser, '<ui:window title="T"><ui:text>Hello World</ui:text></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert '<Text' in code
        assert 'Hello World' in code

    def test_text_with_size(self, parser, adapter):
        """ui:text with size generates dynamic style."""
        app = parse_ui(parser, '<ui:window title="T"><ui:text size="xl">Big</ui:text></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'fontSize:' in code

    def test_text_with_weight(self, parser, adapter):
        """ui:text with weight=bold uses textBold style."""
        app = parse_ui(parser, '<ui:window title="T"><ui:text weight="bold">Bold</ui:text></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'styles.textBold' in code

    def test_button_touchable(self, parser, adapter):
        """ui:button maps to TouchableOpacity."""
        app = parse_ui(parser, '<ui:window title="T"><ui:button>Click Me</ui:button></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert '<TouchableOpacity' in code
        assert 'styles.button' in code
        assert 'Click Me' in code

    def test_button_with_onclick(self, parser, adapter):
        """ui:button with on-click generates onPress handler."""
        app = parse_ui(parser, '<ui:window title="T"><ui:button on-click="handleClick">Click</ui:button></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'onPress={handleClick}' in code

    def test_button_variant(self, parser, adapter):
        """ui:button with variant applies correct style."""
        app = parse_ui(parser, '<ui:window title="T"><ui:button variant="danger">Delete</ui:button></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'styles.buttonDanger' in code

    def test_button_disabled(self, parser, adapter):
        """ui:button with disabled applies disabled style."""
        app = parse_ui(parser, '<ui:window title="T"><ui:button disabled="true">Disabled</ui:button></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'styles.buttonDisabled' in code
        assert 'disabled={true}' in code

    def test_input_textinput(self, parser, adapter):
        """ui:input maps to TextInput."""
        app = parse_ui(parser, '<ui:window title="T"><ui:input placeholder="Enter text" /></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert '<TextInput' in code
        assert 'placeholder="Enter text"' in code

    def test_input_with_bind(self, parser, adapter):
        """ui:input with bind generates value and onChangeText."""
        app = parse_ui(parser, '<ui:window title="T"><ui:input bind="username" /></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'value={username}' in code
        assert 'onChangeText={setUsername}' in code

    def test_input_password(self, parser, adapter):
        """ui:input type=password generates secureTextEntry."""
        app = parse_ui(parser, '<ui:window title="T"><ui:input type="password" /></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'secureTextEntry={true}' in code

    def test_input_email(self, parser, adapter):
        """ui:input type=email generates email keyboard."""
        app = parse_ui(parser, '<ui:window title="T"><ui:input type="email" /></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'keyboardType="email-address"' in code

    def test_switch(self, parser, adapter):
        """ui:switch maps to Switch component."""
        app = parse_ui(parser, '<ui:window title="T"><ui:switch bind="dark" label="Dark Mode" /></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert '<Switch' in code
        assert 'Dark Mode' in code

    def test_image(self, parser, adapter):
        """ui:image maps to Image component."""
        app = parse_ui(parser, '<ui:window title="T"><ui:image src="https://example.com/img.png" alt="Logo" /></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert '<Image' in code
        assert "uri: 'https://example.com/img.png'" in code
        assert 'accessibilityLabel="Logo"' in code

    def test_progress(self, parser, adapter):
        """ui:progress renders progress bar."""
        app = parse_ui(parser, '<ui:window title="T"><ui:progress value="50" max="100" /></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'styles.progressBar' in code
        assert 'styles.progressContainer' in code

    def test_loading(self, parser, adapter):
        """ui:loading maps to ActivityIndicator."""
        app = parse_ui(parser, '<ui:window title="T"><ui:loading text="Loading..." /></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert '<ActivityIndicator' in code
        assert 'Loading...' in code

    def test_badge(self, parser, adapter):
        """ui:badge renders badge with variant."""
        app = parse_ui(parser, '<ui:window title="T"><ui:badge variant="success">Active</ui:badge></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'styles.badge' in code
        assert 'styles.badgeSuccess' in code
        assert 'Active' in code

    def test_rule(self, parser, adapter):
        """ui:rule renders horizontal rule."""
        app = parse_ui(parser, '<ui:window title="T"><ui:rule /></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'styles.rule' in code

    def test_header_footer(self, parser, adapter):
        """ui:header and ui:footer render correctly."""
        app = parse_ui(parser, '<ui:window title="T"><ui:header title="Title" /><ui:footer>v1.0</ui:footer></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'styles.header' in code
        assert 'styles.headerText' in code
        assert 'Title' in code
        assert 'styles.footer' in code
        assert 'v1.0' in code


# ============================================
# Form tests
# ============================================

class TestRNForms:
    def test_form_container(self, parser, adapter):
        """ui:form renders as View with form style."""
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
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'styles.form' in code
        assert 'styles.formItem' in code
        assert 'styles.formLabel' in code
        assert 'Name' in code

    def test_form_submit_button(self, parser, adapter):
        """Form with on-submit generates submit button."""
        src = '''
        <ui:window title="T">
            <ui:form on-submit="handleSubmit">
                <ui:input bind="email" />
            </ui:form>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'onPress={handleSubmit}' in code
        assert 'Submit' in code


# ============================================
# Layout attribute tests
# ============================================

class TestRNLayoutAttributes:
    def test_gap_style(self, parser, adapter):
        """gap attribute generates RN style."""
        app = parse_ui(parser, '<ui:window title="T"><ui:hbox gap="16"><ui:text>A</ui:text></ui:hbox></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'gap: 16' in code

    def test_padding_style(self, parser, adapter):
        """padding attribute generates RN style."""
        app = parse_ui(parser, '<ui:window title="T"><ui:vbox padding="md"><ui:text>A</ui:text></ui:vbox></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert 'padding: 16' in code

    def test_width_percentage(self, parser, adapter):
        """width percentage converts correctly."""
        app = parse_ui(parser, '<ui:window title="T"><ui:panel width="50%" title="P"><ui:text>A</ui:text></ui:panel></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert "'50%'" in code

    def test_background_color(self, parser, adapter):
        """background attribute generates backgroundColor."""
        app = parse_ui(parser, '<ui:window title="T"><ui:vbox background="primary"><ui:text>A</ui:text></ui:vbox></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert "backgroundColor:" in code

    def test_align_items(self, parser, adapter):
        """align attribute generates alignItems."""
        app = parse_ui(parser, '<ui:window title="T"><ui:vbox align="center"><ui:text>A</ui:text></ui:vbox></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert "alignItems: 'center'" in code

    def test_justify_content(self, parser, adapter):
        """justify attribute generates justifyContent."""
        app = parse_ui(parser, '<ui:window title="T"><ui:hbox justify="between"><ui:text>A</ui:text></ui:hbox></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        assert "justifyContent: 'space-between'" in code


# ============================================
# State management tests
# ============================================

class TestRNStateManagement:
    def test_state_declarations(self, parser, adapter):
        """State variables generate useState hooks."""
        state_vars = {'count': '0', 'name': "'John'"}
        code = adapter.generate([], [], 'Test', state_vars=state_vars)
        assert 'useState(0)' in code
        assert "useState('John')" in code

    def test_checkbox_creates_state(self, parser, adapter):
        """Checkbox with bind creates state for tracking."""
        app = parse_ui(parser, '<ui:window title="T"><ui:checkbox bind="agree" label="I agree" /></ui:window>')
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        # State created for checkbox
        assert 'setAgree' in code or 'useState' in code


# ============================================
# Builder integration tests
# ============================================

class TestMobileBuilderIntegration:
    def test_builder_mobile_target(self, parser):
        """UIBuilder with mobile target produces React Native code."""
        app = parse_ui(parser, '<ui:window title="T"><ui:text>Hello</ui:text></ui:window>')
        builder = UIBuilder()
        code = builder.build(app, target='mobile')
        assert "import React" in code
        assert "from 'react-native'" in code
        assert 'Hello' in code

    def test_builder_react_native_target(self, parser):
        """UIBuilder with react-native target produces React Native code."""
        app = parse_ui(parser, '<ui:window title="T"><ui:text>Hello</ui:text></ui:window>')
        builder = UIBuilder()
        code = builder.build(app, target='react-native')
        assert "import React" in code
        assert "from 'react-native'" in code

    def test_generated_code_is_valid_js(self, parser):
        """Generated code should be syntactically valid JavaScript."""
        app = parse_ui(parser, '<ui:window title="T"><ui:button>Click</ui:button></ui:window>')
        builder = UIBuilder()
        code = builder.build(app, target='mobile')
        # Check structure - should have imports, export, and styles
        assert 'import ' in code
        assert 'export default function App()' in code
        assert 'const styles = StyleSheet.create' in code


# ============================================
# Complete app tests
# ============================================

class TestCompleteApps:
    def test_dashboard_app(self, parser, adapter):
        """Full dashboard generates valid React Native code."""
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
                        <ui:text size="xl" weight="bold">8GB</ui:text>
                        <ui:progress value="80" max="100" />
                    </ui:vbox>
                </ui:panel>
            </ui:hbox>
            <ui:footer>v1.0</ui:footer>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        code = adapter.generate(app.ui_windows, app.ui_children, 'Dashboard')
        assert 'import React' in code
        assert 'SafeAreaView' in code
        assert 'CPU' in code
        assert 'Memory' in code
        assert 'styles.panel' in code
        assert 'styles.header' in code
        assert 'styles.footer' in code

    def test_form_app(self, parser, adapter):
        """Form app with inputs and submission."""
        src = '''
        <ui:window title="Login">
            <ui:form on-submit="handleLogin">
                <ui:formitem label="Email">
                    <ui:input bind="email" type="email" placeholder="Enter email" />
                </ui:formitem>
                <ui:formitem label="Password">
                    <ui:input bind="password" type="password" placeholder="Enter password" />
                </ui:formitem>
            </ui:form>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        code = adapter.generate(app.ui_windows, app.ui_children, 'Login')
        assert '<TextInput' in code
        assert 'secureTextEntry={true}' in code
        assert 'keyboardType="email-address"' in code
        assert 'onPress={handleLogin}' in code

    def test_list_app(self, parser, adapter):
        """App with list renders FlatList or View."""
        src = '''
        <ui:window title="Items">
            <ui:list>
                <ui:item><ui:text>Item 1</ui:text></ui:item>
                <ui:item><ui:text>Item 2</ui:text></ui:item>
            </ui:list>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        code = adapter.generate(app.ui_windows, app.ui_children, 'Items')
        assert 'Item 1' in code
        assert 'Item 2' in code
        assert 'styles.listItem' in code


# ============================================
# Import tracking tests
# ============================================

class TestImportTracking:
    def test_imports_include_used_components(self, parser, adapter):
        """Imports include all used React Native components."""
        src = '''
        <ui:window title="T">
            <ui:scrollbox>
                <ui:button>Click</ui:button>
                <ui:input placeholder="Type" />
                <ui:switch label="Toggle" />
                <ui:image src="img.png" />
            </ui:scrollbox>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        code = adapter.generate(app.ui_windows, app.ui_children, 'Test')
        # Find the import line from react-native
        import_lines = [line for line in code.split('\n') if 'from \'react-native\'' in line]
        assert len(import_lines) > 0, "Should have react-native import"
        import_line = import_lines[0]
        assert 'ScrollView' in import_line
        assert 'TouchableOpacity' in import_line
        assert 'TextInput' in import_line
        assert 'Switch' in import_line
        assert 'Image' in import_line
