"""
UI Engine - Cross-Target Parity Tests

Verifies that both HTML and Textual adapters:
1. Accept the same UI AST inputs
2. Produce valid outputs for their respective targets
3. Handle all UI components consistently
4. Apply design tokens correctly
"""

import pytest
from core.features.ui_engine.src.ast_nodes import (
    UIWindowNode, UIHBoxNode, UIVBoxNode, UIPanelNode,
    UITabPanelNode, UITabNode, UIGridNode, UIAccordionNode,
    UISectionNode, UIFormNode, UIFormItemNode, UISpacerNode,
    UIScrollBoxNode,
    UITextNode, UIButtonNode, UIInputNode, UICheckboxNode,
    UISwitchNode, UISelectNode, UITableNode, UIColumnNode,
    UIProgressNode, UIImageNode, UILinkNode, UIBadgeNode,
    UIRuleNode, UILoadingNode, UILogNode, UIMarkdownNode,
    UIHeaderNode, UIFooterNode, UIListNode, UIItemNode,
)
from runtime.ui_html_adapter import UIHtmlAdapter
from runtime.ui_textual_adapter import UITextualAdapter
from runtime.ui_tokens import TokenConverter
from runtime.ui_validator import UIValidator, validate_cross_target


# ===========================================================================
# Helper functions to create AST nodes
# ===========================================================================

def make_window(title="Test"):
    node = UIWindowNode()
    node.title = title
    node.children = []
    return node


def make_text(content, size=None, weight=None):
    node = UITextNode()
    node.content = content
    node.size = size
    node.weight = weight
    return node


def make_button(content, variant=None):
    node = UIButtonNode()
    node.content = content
    node.variant = variant
    return node


def make_input(placeholder=None, input_type="text"):
    node = UIInputNode()
    node.placeholder = placeholder
    node.input_type = input_type
    return node


def make_checkbox(label=None):
    node = UICheckboxNode()
    node.label = label
    return node


def make_switch(label=None):
    node = UISwitchNode()
    node.label = label
    return node


def make_progress(value, max_val="100"):
    node = UIProgressNode()
    node.value = value
    node.max = max_val
    return node


def make_badge(content, variant=None):
    node = UIBadgeNode()
    node.content = content
    node.variant = variant
    return node


def make_image(src, alt=None):
    node = UIImageNode()
    node.src = src
    node.alt = alt
    return node


def make_link(to, content, external=False):
    node = UILinkNode()
    node.to = to
    node.content = content
    node.external = external
    return node


def make_panel(title=None):
    node = UIPanelNode()
    node.title = title
    node.children = []
    return node


def make_hbox():
    node = UIHBoxNode()
    node.children = []
    return node


def make_vbox():
    node = UIVBoxNode()
    node.children = []
    return node


def make_grid(columns=None):
    node = UIGridNode()
    node.columns = columns
    node.children = []
    return node


def make_scrollbox():
    node = UIScrollBoxNode()
    node.children = []
    return node


def make_tabpanel():
    node = UITabPanelNode()
    node.children = []
    return node


def make_tab(title):
    node = UITabNode()
    node.title = title
    node.children = []
    return node


def make_form():
    node = UIFormNode()
    node.children = []
    return node


def make_formitem(label=None):
    node = UIFormItemNode()
    node.label = label
    node.children = []
    return node


def make_header(title=None):
    node = UIHeaderNode()
    node.title = title
    return node


def make_footer(content=None):
    node = UIFooterNode()
    node.content = content
    return node


def make_table(source=None):
    node = UITableNode()
    node.source = source
    node.children = []
    return node


def make_log():
    return UILogNode()


def make_rule():
    return UIRuleNode()


def make_loading():
    return UILoadingNode()


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def html_adapter():
    return UIHtmlAdapter()


@pytest.fixture
def textual_adapter():
    return UITextualAdapter()


@pytest.fixture
def simple_window():
    """Simple window with basic content."""
    window = make_window("Test Window")
    window.children = [
        make_text("Hello World"),
        make_button("Click Me", "primary"),
    ]
    return window


@pytest.fixture
def complex_layout():
    """Complex layout with nested containers."""
    window = make_window("Dashboard")

    # Header
    header = make_header("Dashboard")

    # Main content with hbox
    hbox = make_hbox()
    hbox.gap = "md"
    hbox.padding = "lg"

    panel1 = make_panel("Panel 1")
    panel1.width = "50%"
    panel1.children = [
        make_text("Content 1", size="lg"),
        make_progress("50"),
    ]

    panel2 = make_panel("Panel 2")
    panel2.width = "50%"
    panel2.children = [
        make_text("Content 2"),
        make_button("Action", "success"),
    ]

    hbox.children = [panel1, panel2]

    # Footer
    footer = make_footer("Footer text")

    window.children = [header, hbox, footer]
    return window


@pytest.fixture
def form_layout():
    """Form with inputs."""
    form = make_form()
    form.on_submit = "handleSubmit"

    item1 = make_formitem("Username")
    item1.children = [make_input("Enter username", "text")]

    item2 = make_formitem("Password")
    item2.children = [make_input("Enter password", "password")]

    item3 = make_formitem("Remember")
    item3.children = [make_checkbox("Remember me")]

    item4 = make_formitem("Theme")
    item4.children = [make_switch("Dark mode")]

    hbox = make_hbox()
    hbox.justify = "end"
    hbox.gap = "sm"
    hbox.children = [
        make_button("Cancel", "secondary"),
        make_button("Submit", "primary"),
    ]

    form.children = [item1, item2, item3, item4, hbox]
    return form


@pytest.fixture
def tabbed_layout():
    """Tabbed interface."""
    tabs = make_tabpanel()

    tab1 = make_tab("Overview")
    tab1.children = [
        make_text("Overview content"),
        make_progress("75"),
    ]

    tab2 = make_tab("Details")
    tab2.children = [
        make_table("{data}"),
    ]

    tab3 = make_tab("Logs")
    tab3.children = [
        make_log(),
    ]

    tabs.children = [tab1, tab2, tab3]
    return tabs


# ===========================================================================
# Parity Tests - Both adapters handle same inputs
# ===========================================================================

class TestAdapterParity:
    """Test that both adapters can process the same inputs."""

    def test_simple_window_both_adapters(self, html_adapter, textual_adapter, simple_window):
        """Both adapters should handle simple window."""
        html = html_adapter.generate([simple_window], [], "Test")
        textual = textual_adapter.generate([simple_window], [], "Test")

        assert html is not None
        assert textual is not None
        assert len(html) > 0
        assert len(textual) > 0

    def test_complex_layout_both_adapters(self, html_adapter, textual_adapter, complex_layout):
        """Both adapters should handle complex layouts."""
        html = html_adapter.generate([complex_layout], [], "Dashboard")
        textual = textual_adapter.generate([complex_layout], [], "Dashboard")

        assert html is not None
        assert textual is not None
        assert len(html) > 0
        assert len(textual) > 0

    def test_form_both_adapters(self, html_adapter, textual_adapter, form_layout):
        """Both adapters should handle forms."""
        html = html_adapter.generate([], [form_layout], "Form")
        textual = textual_adapter.generate([], [form_layout], "Form")

        assert html is not None
        assert textual is not None

    def test_tabs_both_adapters(self, html_adapter, textual_adapter, tabbed_layout):
        """Both adapters should handle tabs."""
        html = html_adapter.generate([], [tabbed_layout], "Tabs")
        textual = textual_adapter.generate([], [tabbed_layout], "Tabs")

        assert html is not None
        assert textual is not None


# ===========================================================================
# Output Validity Tests
# ===========================================================================

class TestOutputValidity:
    """Test that generated outputs are valid for their targets."""

    def test_html_is_valid(self, html_adapter, complex_layout):
        """HTML output should be valid HTML."""
        html = html_adapter.generate([complex_layout], [], "Test")

        # Basic HTML structure checks
        assert "<!DOCTYPE html>" in html
        assert "<html" in html
        assert "</html>" in html
        assert "<head>" in html
        assert "<body>" in html

    def test_textual_is_valid_python(self, textual_adapter, complex_layout):
        """Textual output should be valid Python."""
        code = textual_adapter.generate([complex_layout], [], "Test")

        # Should compile without syntax errors
        compile(code, '<test>', 'exec')

        # Basic Python structure checks
        assert "from textual.app import App" in code
        assert "class QuantumUIApp(App):" in code
        assert "def compose(self)" in code

    def test_html_contains_css(self, html_adapter, complex_layout):
        """HTML should include CSS styles."""
        html = html_adapter.generate([complex_layout], [], "Test")

        assert "<style>" in html
        assert "--q-primary" in html  # CSS variables
        assert ".q-panel" in html     # Component classes

    def test_textual_contains_css(self, textual_adapter, complex_layout):
        """Textual should include CSS styles."""
        code = textual_adapter.generate([complex_layout], [], "Test")

        assert "CSS = " in code
        assert ".q-panel" in code


# ===========================================================================
# Token System Tests
# ===========================================================================

class TestTokenParity:
    """Test that token system works consistently across targets."""

    def test_spacing_tokens_html(self):
        """HTML token converter returns pixel values."""
        conv = TokenConverter('html')
        assert conv.spacing('sm') == '8px'
        assert conv.spacing('md') == '16px'
        assert conv.spacing('lg') == '24px'

    def test_spacing_tokens_textual(self):
        """Textual token converter returns cell counts."""
        conv = TokenConverter('textual')
        assert conv.spacing('sm') == '1'
        assert conv.spacing('md') == '2'
        assert conv.spacing('lg') == '3'

    def test_color_tokens_html(self):
        """HTML color tokens use CSS variables."""
        conv = TokenConverter('html')
        assert 'var(--q-primary)' in conv.color('primary')
        assert 'var(--q-success)' in conv.color('success')

    def test_color_tokens_textual(self):
        """Textual color tokens use $ variables."""
        conv = TokenConverter('textual')
        assert conv.color('primary') == '$primary'
        assert conv.color('success') == '$success'

    def test_size_tokens_html(self):
        """HTML size tokens return percentages."""
        conv = TokenConverter('html')
        assert conv.size('fill') == '100%'
        assert conv.size('1/2') == '50%'

    def test_size_tokens_textual(self):
        """Textual size tokens return fr units or percentages."""
        conv = TokenConverter('textual')
        assert conv.size('fill') == '1fr'
        assert conv.size('full') == '100%'

    def test_raw_pixel_conversion(self):
        """Raw pixel values should convert appropriately."""
        html_conv = TokenConverter('html')
        textual_conv = TokenConverter('textual')

        # HTML keeps px
        assert html_conv.spacing('16') == '16px'
        assert html_conv.spacing('24px') == '24px'

        # Textual converts to cells
        assert textual_conv.spacing('16') == '2'  # 16 / 8 = 2
        assert textual_conv.spacing('24px') == '3'  # 24 / 8 = 3


# ===========================================================================
# Widget Rendering Tests
# ===========================================================================

class TestWidgetRendering:
    """Test that specific widgets render in both targets."""

    def test_button_renders_in_both(self, html_adapter, textual_adapter):
        """Button should render in both targets."""
        btn = make_button("Click", "primary")
        html = html_adapter.generate([], [btn], "Test")
        textual = textual_adapter.generate([], [btn], "Test")

        assert "q-btn-primary" in html
        assert "Button" in textual

    def test_input_renders_in_both(self, html_adapter, textual_adapter):
        """Input should render in both targets."""
        inp = make_input("Enter text")
        html = html_adapter.generate([], [inp], "Test")
        textual = textual_adapter.generate([], [inp], "Test")

        assert "q-input" in html
        assert "Input" in textual

    def test_checkbox_renders_in_both(self, html_adapter, textual_adapter):
        """Checkbox should render in both targets."""
        cb = make_checkbox("Check me")
        html = html_adapter.generate([], [cb], "Test")
        textual = textual_adapter.generate([], [cb], "Test")

        assert "checkbox" in html.lower()
        assert "Checkbox" in textual

    def test_progress_renders_in_both(self, html_adapter, textual_adapter):
        """Progress should render in both targets."""
        prog = make_progress("50", "100")
        html = html_adapter.generate([], [prog], "Test")
        textual = textual_adapter.generate([], [prog], "Test")

        assert "progress" in html.lower()
        assert "ProgressBar" in textual

    def test_badge_renders_in_both(self, html_adapter, textual_adapter):
        """Badge should render in both targets."""
        badge = make_badge("New", "success")
        html = html_adapter.generate([], [badge], "Test")
        textual = textual_adapter.generate([], [badge], "Test")

        assert "q-badge" in html
        assert "Static" in textual

    def test_rule_renders_in_both(self, html_adapter, textual_adapter):
        """Rule should render in both targets."""
        rule = make_rule()
        html = html_adapter.generate([], [rule], "Test")
        textual = textual_adapter.generate([], [rule], "Test")

        assert "<hr" in html
        assert "Rule" in textual

    def test_image_degradation(self, html_adapter, textual_adapter):
        """Image should render as placeholder in Textual."""
        img = make_image("/img/photo.png", "Photo")

        html = html_adapter.generate([], [img], "Test")
        textual = textual_adapter.generate([], [img], "Test")

        # HTML has actual img tag
        assert "<img" in html
        assert 'src="/img/photo.png"' in html

        # Textual has placeholder
        assert "Photo" in textual  # Alt text
        assert "Static" in textual

    def test_link_degradation(self, html_adapter, textual_adapter):
        """External link should degrade in Textual."""
        link = make_link("https://example.com", "Visit", external=True)

        html = html_adapter.generate([], [link], "Test")
        textual = textual_adapter.generate([], [link], "Test")

        # HTML has anchor
        assert "<a" in html
        assert "https://example.com" in html

        # Textual has static text with URL
        assert "example.com" in textual
        assert "Static" in textual


# ===========================================================================
# Validator Tests
# ===========================================================================

class TestValidator:
    """Test cross-target validator."""

    def test_validator_simple_layout(self, simple_window):
        """Simple layout should have high compatibility."""
        report = validate_cross_target([simple_window], [])

        assert report.compatibility_score >= 80
        assert report.html_compatible
        assert report.textual_compatible

    def test_validator_detects_image(self):
        """Validator should detect image compatibility issue."""
        window = make_window("Test")
        window.children = [make_image("/photo.png", "Photo")]

        report = validate_cross_target([window], [])

        assert 'image' in report.features_used
        assert any('image' in str(i.feature) for i in report.issues)

    def test_validator_detects_gap(self):
        """Validator should detect gap compatibility issue."""
        hbox = make_hbox()
        hbox.gap = "16"
        hbox.children = [make_text("A"), make_text("B")]

        report = validate_cross_target([], [hbox])

        assert 'gap' in report.features_used
        assert any('gap' in str(i.feature) for i in report.issues)

    def test_validator_detects_pixel_units(self):
        """Validator should detect pixel unit usage."""
        panel = make_panel("Test")
        panel.width = "300px"

        report = validate_cross_target([], [panel])

        assert 'pixel_units' in report.features_used

    def test_validator_counts_elements(self, complex_layout):
        """Validator should count containers and widgets."""
        report = validate_cross_target([complex_layout], [])

        assert report.containers_count > 0
        assert report.widgets_count > 0

    def test_validator_returns_warnings(self):
        """Validator should return formatted warnings."""
        window = make_window("Test")
        hbox = make_hbox()
        hbox.gap = "md"
        hbox.justify = "between"
        hbox.children = [
            make_image("/a.png", "A"),
            make_link("http://x.com", "Link", external=True),
        ]
        window.children = [hbox]

        report = validate_cross_target([window], [])

        assert len(report.warnings) > 0
        assert len(report.issues) > 0


# ===========================================================================
# Container Layout Tests
# ===========================================================================

class TestContainerLayout:
    """Test layout containers in both targets."""

    def test_hbox_renders_horizontal(self, html_adapter, textual_adapter):
        """HBox should render as horizontal layout."""
        hbox = make_hbox()
        hbox.children = [make_text("A"), make_text("B")]

        html = html_adapter.generate([], [hbox], "Test")
        textual = textual_adapter.generate([], [hbox], "Test")

        # HTML uses flex-direction: row
        assert "flex-direction: row" in html or "flex-direction:row" in html

        # Textual uses Horizontal
        assert "Horizontal" in textual

    def test_vbox_renders_vertical(self, html_adapter, textual_adapter):
        """VBox should render as vertical layout."""
        vbox = make_vbox()
        vbox.children = [make_text("A"), make_text("B")]

        html = html_adapter.generate([], [vbox], "Test")
        textual = textual_adapter.generate([], [vbox], "Test")

        # HTML uses flex-direction: column
        assert "flex-direction: column" in html or "flex-direction:column" in html

        # Textual uses Vertical
        assert "Vertical" in textual

    def test_grid_renders(self, html_adapter, textual_adapter):
        """Grid should render in both targets."""
        grid = make_grid("3")
        grid.children = [make_text("1"), make_text("2"), make_text("3")]

        html = html_adapter.generate([], [grid], "Test")
        textual = textual_adapter.generate([], [grid], "Test")

        # HTML uses CSS grid
        assert "grid" in html.lower()

        # Textual uses Grid
        assert "Grid" in textual

    def test_scrollbox_renders(self, html_adapter, textual_adapter):
        """ScrollBox should render with scroll capability."""
        scroll = make_scrollbox()
        scroll.children = [make_text("Content")]

        html = html_adapter.generate([], [scroll], "Test")
        textual = textual_adapter.generate([], [scroll], "Test")

        # HTML uses overflow
        assert "overflow" in html.lower()

        # Textual uses ScrollableContainer
        assert "ScrollableContainer" in textual


# ===========================================================================
# Integration Tests
# ===========================================================================

class TestIntegration:
    """Integration tests for complete UI trees."""

    def test_dashboard_ui(self, html_adapter, textual_adapter):
        """Full dashboard UI should render in both targets."""
        # Build a realistic dashboard
        window = make_window("Dashboard")

        header = make_header("Server Dashboard")

        # Stats row
        stats = make_hbox()
        stats.gap = "md"
        stats.padding = "md"
        stats.children = []

        for name, value in [("CPU", "45"), ("Memory", "72"), ("Disk", "35")]:
            panel = make_panel(name)
            panel.width = "1/3"
            vbox = make_vbox()
            vbox.align = "center"
            vbox.children = [
                make_text(f"{value}%", size="xl"),
                make_progress(value),
            ]
            panel.children = [vbox]
            stats.children.append(panel)

        # Tabs
        tabs = make_tabpanel()
        tab1 = make_tab("Overview")
        tab1.children = [make_text("Overview content")]
        tab2 = make_tab("Logs")
        tab2.children = [make_log()]
        tabs.children = [tab1, tab2]

        footer = make_footer("v1.0")

        window.children = [header, stats, tabs, footer]

        # Generate both
        html = html_adapter.generate([window], [], "Dashboard")
        textual = textual_adapter.generate([window], [], "Dashboard")

        # Both should produce valid output
        assert len(html) > 500  # Substantial HTML
        assert len(textual) > 200  # Substantial Python

        # HTML should be valid
        assert "<!DOCTYPE html>" in html

        # Python should compile
        compile(textual, '<test>', 'exec')

        # Validate compatibility
        report = validate_cross_target([window], [])
        assert report.compatibility_score >= 60  # Acceptable with some issues
