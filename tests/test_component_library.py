"""
Tests for UI Engine Component Library

Tests parsing and rendering of the component library UI elements:
- Card (with header, body, footer)
- Modal
- Chart
- Avatar
- Tooltip
- Dropdown
- Alert
- Breadcrumb
- Pagination
- Skeleton
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import pytest
from core.parser import QuantumParser
from core.ast_nodes import ApplicationNode
from core.features.ui_engine.src.ast_nodes import (
    UICardNode, UICardHeaderNode, UICardBodyNode, UICardFooterNode,
    UIModalNode, UIChartNode, UIAvatarNode, UITooltipNode,
    UIDropdownNode, UIAlertNode, UIBreadcrumbNode, UIBreadcrumbItemNode,
    UIPaginationNode, UISkeletonNode,
    UITextNode, UIButtonNode,
)
from runtime.ui_html_adapter import UIHtmlAdapter


@pytest.fixture
def parser():
    return QuantumParser()


def parse_ui(parser, body: str) -> ApplicationNode:
    """Helper: wrap body in <q:application type="ui"> and parse."""
    source = f'<q:application id="test" type="ui">{body}</q:application>'
    return parser.parse(source)


# ============================================
# Card Component
# ============================================

class TestCardComponent:
    def test_card_basic(self, parser):
        """Parse basic card with title."""
        app = parse_ui(parser, '<ui:window title="T"><ui:card title="My Card" /></ui:window>')
        card = app.ui_windows[0].children[0]
        assert isinstance(card, UICardNode)
        assert card.title == "My Card"

    def test_card_with_subtitle(self, parser):
        """Parse card with subtitle."""
        app = parse_ui(parser, '<ui:window title="T"><ui:card title="Title" subtitle="Subtitle" /></ui:window>')
        card = app.ui_windows[0].children[0]
        assert card.title == "Title"
        assert card.subtitle == "Subtitle"

    def test_card_with_image(self, parser):
        """Parse card with header image."""
        app = parse_ui(parser, '<ui:window title="T"><ui:card image="/img.jpg" /></ui:window>')
        card = app.ui_windows[0].children[0]
        assert card.image == "/img.jpg"

    def test_card_variant(self, parser):
        """Parse card with variant."""
        app = parse_ui(parser, '<ui:window title="T"><ui:card variant="elevated" /></ui:window>')
        card = app.ui_windows[0].children[0]
        assert card.variant == "elevated"

    def test_card_with_sections(self, parser):
        """Parse card with explicit header, body, footer."""
        src = '''
        <ui:window title="T">
            <ui:card>
                <ui:card-header><ui:text>Header</ui:text></ui:card-header>
                <ui:card-body><ui:text>Body content</ui:text></ui:card-body>
                <ui:card-footer><ui:button>OK</ui:button></ui:card-footer>
            </ui:card>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        card = app.ui_windows[0].children[0]
        assert isinstance(card, UICardNode)
        assert len(card.children) == 3
        assert isinstance(card.children[0], UICardHeaderNode)
        assert isinstance(card.children[1], UICardBodyNode)
        assert isinstance(card.children[2], UICardFooterNode)


# ============================================
# Modal Component
# ============================================

class TestModalComponent:
    def test_modal_basic(self, parser):
        """Parse basic modal."""
        app = parse_ui(parser, '<ui:window title="T"><ui:modal title="Confirm" /></ui:window>')
        modal = app.ui_windows[0].children[0]
        assert isinstance(modal, UIModalNode)
        assert modal.title == "Confirm"

    def test_modal_with_id(self, parser):
        """Parse modal with explicit ID."""
        app = parse_ui(parser, '<ui:window title="T"><ui:modal modal-id="my-modal" /></ui:window>')
        modal = app.ui_windows[0].children[0]
        assert modal.modal_id == "my-modal"

    def test_modal_open_state(self, parser):
        """Parse modal with open state."""
        app = parse_ui(parser, '<ui:window title="T"><ui:modal open="true" /></ui:window>')
        modal = app.ui_windows[0].children[0]
        assert modal.open is True

    def test_modal_closable(self, parser):
        """Parse modal with closable attribute."""
        app = parse_ui(parser, '<ui:window title="T"><ui:modal closable="false" /></ui:window>')
        modal = app.ui_windows[0].children[0]
        assert modal.closable is False

    def test_modal_size(self, parser):
        """Parse modal with size."""
        app = parse_ui(parser, '<ui:window title="T"><ui:modal size="lg" /></ui:window>')
        modal = app.ui_windows[0].children[0]
        assert modal.size == "lg"


# ============================================
# Chart Component
# ============================================

class TestChartComponent:
    def test_chart_bar(self, parser):
        """Parse bar chart."""
        app = parse_ui(parser, '<ui:window title="T"><ui:chart type="bar" labels="A,B,C" values="10,20,30" /></ui:window>')
        chart = app.ui_windows[0].children[0]
        assert isinstance(chart, UIChartNode)
        assert chart.chart_type == "bar"
        assert chart.labels == "A,B,C"
        assert chart.values == "10,20,30"

    def test_chart_line(self, parser):
        """Parse line chart."""
        app = parse_ui(parser, '<ui:window title="T"><ui:chart type="line" /></ui:window>')
        chart = app.ui_windows[0].children[0]
        assert chart.chart_type == "line"

    def test_chart_pie(self, parser):
        """Parse pie chart."""
        app = parse_ui(parser, '<ui:window title="T"><ui:chart type="pie" /></ui:window>')
        chart = app.ui_windows[0].children[0]
        assert chart.chart_type == "pie"

    def test_chart_with_title(self, parser):
        """Parse chart with title."""
        app = parse_ui(parser, '<ui:window title="T"><ui:chart title="Sales Data" /></ui:window>')
        chart = app.ui_windows[0].children[0]
        assert chart.title == "Sales Data"

    def test_chart_with_colors(self, parser):
        """Parse chart with custom colors."""
        app = parse_ui(parser, '<ui:window title="T"><ui:chart colors="#ff0000,#00ff00" /></ui:window>')
        chart = app.ui_windows[0].children[0]
        assert chart.colors == "#ff0000,#00ff00"


# ============================================
# Avatar Component
# ============================================

class TestAvatarComponent:
    def test_avatar_with_image(self, parser):
        """Parse avatar with image."""
        app = parse_ui(parser, '<ui:window title="T"><ui:avatar src="/user.jpg" /></ui:window>')
        avatar = app.ui_windows[0].children[0]
        assert isinstance(avatar, UIAvatarNode)
        assert avatar.src == "/user.jpg"

    def test_avatar_with_name(self, parser):
        """Parse avatar with name for initials."""
        app = parse_ui(parser, '<ui:window title="T"><ui:avatar name="John Doe" /></ui:window>')
        avatar = app.ui_windows[0].children[0]
        assert avatar.name == "John Doe"

    def test_avatar_size(self, parser):
        """Parse avatar with size."""
        app = parse_ui(parser, '<ui:window title="T"><ui:avatar size="lg" /></ui:window>')
        avatar = app.ui_windows[0].children[0]
        assert avatar.size == "lg"

    def test_avatar_shape(self, parser):
        """Parse avatar with square shape."""
        app = parse_ui(parser, '<ui:window title="T"><ui:avatar shape="square" /></ui:window>')
        avatar = app.ui_windows[0].children[0]
        assert avatar.shape == "square"

    def test_avatar_status(self, parser):
        """Parse avatar with status indicator."""
        app = parse_ui(parser, '<ui:window title="T"><ui:avatar status="online" /></ui:window>')
        avatar = app.ui_windows[0].children[0]
        assert avatar.status == "online"


# ============================================
# Tooltip Component
# ============================================

class TestTooltipComponent:
    def test_tooltip_basic(self, parser):
        """Parse basic tooltip."""
        src = '''
        <ui:window title="T">
            <ui:tooltip content="Help text">
                <ui:button>Hover me</ui:button>
            </ui:tooltip>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        tooltip = app.ui_windows[0].children[0]
        assert isinstance(tooltip, UITooltipNode)
        assert tooltip.content == "Help text"
        assert len(tooltip.children) == 1

    def test_tooltip_position(self, parser):
        """Parse tooltip with position."""
        app = parse_ui(parser, '<ui:window title="T"><ui:tooltip content="Tip" position="bottom" /></ui:window>')
        tooltip = app.ui_windows[0].children[0]
        assert tooltip.position == "bottom"


# ============================================
# Dropdown Component
# ============================================

class TestDropdownComponent:
    def test_dropdown_basic(self, parser):
        """Parse basic dropdown."""
        app = parse_ui(parser, '<ui:window title="T"><ui:dropdown label="Menu" /></ui:window>')
        dropdown = app.ui_windows[0].children[0]
        assert isinstance(dropdown, UIDropdownNode)
        assert dropdown.label == "Menu"

    def test_dropdown_with_options(self, parser):
        """Parse dropdown with options."""
        src = '''
        <ui:window title="T">
            <ui:dropdown label="Actions">
                <ui:option value="edit" label="Edit" />
                <ui:option value="delete" label="Delete" />
            </ui:dropdown>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        dropdown = app.ui_windows[0].children[0]
        assert len(dropdown.children) == 2

    def test_dropdown_trigger(self, parser):
        """Parse dropdown with hover trigger."""
        app = parse_ui(parser, '<ui:window title="T"><ui:dropdown trigger="hover" /></ui:window>')
        dropdown = app.ui_windows[0].children[0]
        assert dropdown.trigger == "hover"

    def test_dropdown_align(self, parser):
        """Parse dropdown with right alignment."""
        app = parse_ui(parser, '<ui:window title="T"><ui:dropdown align="right" /></ui:window>')
        dropdown = app.ui_windows[0].children[0]
        assert dropdown.dropdown_align == "right"


# ============================================
# Alert Component
# ============================================

class TestAlertComponent:
    def test_alert_basic(self, parser):
        """Parse basic alert."""
        app = parse_ui(parser, '<ui:window title="T"><ui:alert>Message</ui:alert></ui:window>')
        alert = app.ui_windows[0].children[0]
        assert isinstance(alert, UIAlertNode)
        assert alert.content == "Message"

    def test_alert_variant(self, parser):
        """Parse alert with variant."""
        app = parse_ui(parser, '<ui:window title="T"><ui:alert variant="success" /></ui:window>')
        alert = app.ui_windows[0].children[0]
        assert alert.variant == "success"

    def test_alert_with_title(self, parser):
        """Parse alert with title."""
        app = parse_ui(parser, '<ui:window title="T"><ui:alert title="Warning">Content</ui:alert></ui:window>')
        alert = app.ui_windows[0].children[0]
        assert alert.title == "Warning"

    def test_alert_dismissible(self, parser):
        """Parse dismissible alert."""
        app = parse_ui(parser, '<ui:window title="T"><ui:alert dismissible="true" /></ui:window>')
        alert = app.ui_windows[0].children[0]
        assert alert.dismissible is True

    def test_alert_with_icon(self, parser):
        """Parse alert with icon."""
        app = parse_ui(parser, '<ui:window title="T"><ui:alert icon="!" /></ui:window>')
        alert = app.ui_windows[0].children[0]
        assert alert.icon == "!"


# ============================================
# Breadcrumb Component
# ============================================

class TestBreadcrumbComponent:
    def test_breadcrumb_basic(self, parser):
        """Parse basic breadcrumb."""
        src = '''
        <ui:window title="T">
            <ui:breadcrumb>
                <ui:breadcrumb-item label="Home" to="/" />
                <ui:breadcrumb-item label="Products" to="/products" />
                <ui:breadcrumb-item label="Item" />
            </ui:breadcrumb>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        breadcrumb = app.ui_windows[0].children[0]
        assert isinstance(breadcrumb, UIBreadcrumbNode)
        assert len(breadcrumb.children) == 3

        item1 = breadcrumb.children[0]
        assert isinstance(item1, UIBreadcrumbItemNode)
        assert item1.label == "Home"
        assert item1.to == "/"

    def test_breadcrumb_separator(self, parser):
        """Parse breadcrumb with custom separator."""
        app = parse_ui(parser, '<ui:window title="T"><ui:breadcrumb separator=">" /></ui:window>')
        breadcrumb = app.ui_windows[0].children[0]
        assert breadcrumb.separator == ">"


# ============================================
# Pagination Component
# ============================================

class TestPaginationComponent:
    def test_pagination_basic(self, parser):
        """Parse basic pagination."""
        app = parse_ui(parser, '<ui:window title="T"><ui:pagination total="100" /></ui:window>')
        pagination = app.ui_windows[0].children[0]
        assert isinstance(pagination, UIPaginationNode)
        assert pagination.total == "100"

    def test_pagination_page_size(self, parser):
        """Parse pagination with page size."""
        app = parse_ui(parser, '<ui:window title="T"><ui:pagination page-size="20" /></ui:window>')
        pagination = app.ui_windows[0].children[0]
        assert pagination.page_size == "20"

    def test_pagination_current(self, parser):
        """Parse pagination with current page."""
        app = parse_ui(parser, '<ui:window title="T"><ui:pagination current="3" /></ui:window>')
        pagination = app.ui_windows[0].children[0]
        assert pagination.current == "3"

    def test_pagination_show_total(self, parser):
        """Parse pagination with show total."""
        app = parse_ui(parser, '<ui:window title="T"><ui:pagination show-total="true" /></ui:window>')
        pagination = app.ui_windows[0].children[0]
        assert pagination.show_total is True

    def test_pagination_show_jump(self, parser):
        """Parse pagination with page jump input."""
        app = parse_ui(parser, '<ui:window title="T"><ui:pagination show-jump="true" /></ui:window>')
        pagination = app.ui_windows[0].children[0]
        assert pagination.show_jump is True


# ============================================
# Skeleton Component
# ============================================

class TestSkeletonComponent:
    def test_skeleton_text(self, parser):
        """Parse text skeleton."""
        app = parse_ui(parser, '<ui:window title="T"><ui:skeleton variant="text" lines="3" /></ui:window>')
        skeleton = app.ui_windows[0].children[0]
        assert isinstance(skeleton, UISkeletonNode)
        assert skeleton.variant == "text"
        assert skeleton.lines == 3

    def test_skeleton_circle(self, parser):
        """Parse circle skeleton."""
        app = parse_ui(parser, '<ui:window title="T"><ui:skeleton variant="circle" /></ui:window>')
        skeleton = app.ui_windows[0].children[0]
        assert skeleton.variant == "circle"

    def test_skeleton_rect(self, parser):
        """Parse rect skeleton."""
        app = parse_ui(parser, '<ui:window title="T"><ui:skeleton variant="rect" /></ui:window>')
        skeleton = app.ui_windows[0].children[0]
        assert skeleton.variant == "rect"

    def test_skeleton_card(self, parser):
        """Parse card skeleton."""
        app = parse_ui(parser, '<ui:window title="T"><ui:skeleton variant="card" /></ui:window>')
        skeleton = app.ui_windows[0].children[0]
        assert skeleton.variant == "card"

    def test_skeleton_animated(self, parser):
        """Parse skeleton with animation disabled."""
        app = parse_ui(parser, '<ui:window title="T"><ui:skeleton animated="false" /></ui:window>')
        skeleton = app.ui_windows[0].children[0]
        assert skeleton.animated is False


# ============================================
# HTML Rendering Tests
# ============================================

class TestComponentRendering:
    def test_render_card(self, parser):
        """Render card to HTML."""
        app = parse_ui(parser, '<ui:window title="T"><ui:card title="Test Card" subtitle="Description" /></ui:window>')
        adapter = UIHtmlAdapter()
        html = adapter.generate(app.ui_windows, app.ui_children)
        assert 'q-card' in html
        assert 'q-card-title' in html
        assert 'Test Card' in html
        assert 'q-card-subtitle' in html
        assert 'Description' in html

    def test_render_modal(self, parser):
        """Render modal to HTML."""
        app = parse_ui(parser, '<ui:window title="T"><ui:modal title="Confirm Action" modal-id="test-modal" /></ui:window>')
        adapter = UIHtmlAdapter()
        html = adapter.generate(app.ui_windows, app.ui_children)
        assert 'q-modal-overlay' in html
        assert 'q-modal' in html
        assert 'q-modal-header' in html
        assert 'Confirm Action' in html
        assert 'test-modal' in html

    def test_render_chart(self, parser):
        """Render chart to HTML."""
        app = parse_ui(parser, '<ui:window title="T"><ui:chart type="bar" labels="A,B" values="10,20" title="Sales" /></ui:window>')
        adapter = UIHtmlAdapter()
        html = adapter.generate(app.ui_windows, app.ui_children)
        assert 'q-chart' in html
        assert 'q-chart-bar' in html
        assert 'q-chart-title' in html
        assert 'Sales' in html

    def test_render_avatar(self, parser):
        """Render avatar to HTML."""
        app = parse_ui(parser, '<ui:window title="T"><ui:avatar name="John Doe" status="online" /></ui:window>')
        adapter = UIHtmlAdapter()
        html = adapter.generate(app.ui_windows, app.ui_children)
        assert 'q-avatar' in html
        assert 'q-avatar-initials' in html
        assert 'JD' in html
        assert 'q-avatar-status-online' in html

    def test_render_tooltip(self, parser):
        """Render tooltip to HTML."""
        src = '<ui:window title="T"><ui:tooltip content="Help text" position="top"><ui:button>Hover</ui:button></ui:tooltip></ui:window>'
        app = parse_ui(parser, src)
        adapter = UIHtmlAdapter()
        html = adapter.generate(app.ui_windows, app.ui_children)
        assert 'q-tooltip-wrapper' in html
        assert 'q-tooltip-top' in html
        assert 'q-tooltip-text' in html
        assert 'Help text' in html

    def test_render_dropdown(self, parser):
        """Render dropdown to HTML."""
        app = parse_ui(parser, '<ui:window title="T"><ui:dropdown label="Menu" trigger="hover" /></ui:window>')
        adapter = UIHtmlAdapter()
        html = adapter.generate(app.ui_windows, app.ui_children)
        assert 'q-dropdown' in html
        assert 'q-dropdown-trigger' in html
        assert 'q-dropdown-hover' in html
        assert 'Menu' in html

    def test_render_alert(self, parser):
        """Render alert to HTML."""
        app = parse_ui(parser, '<ui:window title="T"><ui:alert variant="success" title="Success" dismissible="true">Done!</ui:alert></ui:window>')
        adapter = UIHtmlAdapter()
        html = adapter.generate(app.ui_windows, app.ui_children)
        assert 'q-alert' in html
        assert 'q-alert-success' in html
        assert 'q-alert-dismissible' in html
        assert 'q-alert-title' in html
        assert 'Success' in html
        assert 'Done!' in html

    def test_render_breadcrumb(self, parser):
        """Render breadcrumb to HTML."""
        src = '''
        <ui:window title="T">
            <ui:breadcrumb separator=">">
                <ui:breadcrumb-item label="Home" to="/" />
                <ui:breadcrumb-item label="Current" />
            </ui:breadcrumb>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        adapter = UIHtmlAdapter()
        html = adapter.generate(app.ui_windows, app.ui_children)
        assert 'q-breadcrumb' in html
        assert 'q-breadcrumb-list' in html
        assert 'q-breadcrumb-link' in html
        assert 'Home' in html
        assert 'q-breadcrumb-separator' in html

    def test_render_pagination(self, parser):
        """Render pagination to HTML."""
        app = parse_ui(parser, '<ui:window title="T"><ui:pagination total="100" show-total="true" show-jump="true" /></ui:window>')
        adapter = UIHtmlAdapter()
        html = adapter.generate(app.ui_windows, app.ui_children)
        assert 'q-pagination' in html
        assert 'q-pagination-controls' in html
        assert 'q-pagination-total' in html
        assert 'q-pagination-jump' in html
        assert 'Total: 100 items' in html

    def test_render_skeleton(self, parser):
        """Render skeleton to HTML."""
        app = parse_ui(parser, '<ui:window title="T"><ui:skeleton variant="text" lines="2" /></ui:window>')
        adapter = UIHtmlAdapter()
        html = adapter.generate(app.ui_windows, app.ui_children)
        assert 'q-skeleton' in html
        assert 'q-skeleton-text' in html
        assert 'q-skeleton-animated' in html


# ============================================
# Validation Tests
# ============================================

class TestComponentValidation:
    def test_chart_invalid_type(self, parser):
        """Chart with invalid type should fail validation."""
        app = parse_ui(parser, '<ui:window title="T"><ui:chart type="invalid" /></ui:window>')
        chart = app.ui_windows[0].children[0]
        chart.chart_type = "invalid"
        errors = chart.validate()
        assert len(errors) > 0
        assert "Invalid chart type" in errors[0]

    def test_avatar_invalid_shape(self, parser):
        """Avatar with invalid shape should fail validation."""
        app = parse_ui(parser, '<ui:window title="T"><ui:avatar /></ui:window>')
        avatar = app.ui_windows[0].children[0]
        avatar.shape = "hexagon"
        errors = avatar.validate()
        assert len(errors) > 0
        assert "Invalid avatar shape" in errors[0]

    def test_tooltip_invalid_position(self, parser):
        """Tooltip with invalid position should fail validation."""
        app = parse_ui(parser, '<ui:window title="T"><ui:tooltip content="x" /></ui:window>')
        tooltip = app.ui_windows[0].children[0]
        tooltip.position = "diagonal"
        errors = tooltip.validate()
        assert len(errors) > 0
        assert "Invalid tooltip position" in errors[0]

    def test_alert_invalid_variant(self, parser):
        """Alert with invalid variant should fail validation."""
        app = parse_ui(parser, '<ui:window title="T"><ui:alert /></ui:window>')
        alert = app.ui_windows[0].children[0]
        alert.variant = "critical"
        errors = alert.validate()
        assert len(errors) > 0
        assert "Invalid alert variant" in errors[0]

    def test_skeleton_invalid_variant(self, parser):
        """Skeleton with invalid variant should fail validation."""
        app = parse_ui(parser, '<ui:window title="T"><ui:skeleton /></ui:window>')
        skeleton = app.ui_windows[0].children[0]
        skeleton.variant = "blob"
        errors = skeleton.validate()
        assert len(errors) > 0
        assert "Invalid skeleton variant" in errors[0]
