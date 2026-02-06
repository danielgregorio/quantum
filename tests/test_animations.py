"""
Tests for UI Animation System

Tests for the ui:animate tag and animation attributes in the Quantum UI Engine.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import pytest
from core.parser import QuantumParser
from core.ast_nodes import ApplicationNode
from core.features.ui_engine.src.ast_nodes import (
    UIAnimateNode, UIAnimationMixin, UITextNode, UIPanelNode,
    UIButtonNode, UIVBoxNode, UIHBoxNode,
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
# UIAnimateNode AST Tests
# ============================================

class TestUIAnimateNodeAST:
    """Test UIAnimateNode creation and attributes."""

    def test_animate_node_init(self):
        """UIAnimateNode initializes with correct defaults."""
        node = UIAnimateNode()
        assert node.children == []
        assert node.anim_type is None
        assert node.anim_duration is None
        assert node.anim_delay is None
        assert node.anim_easing is None
        assert node.anim_repeat is None
        assert node.anim_trigger is None
        assert node.anim_direction is None
        assert node.animate is None
        assert node.transition is None

    def test_animate_node_add_child(self):
        """UIAnimateNode can add children."""
        node = UIAnimateNode()
        child = UITextNode()
        child.content = "Hello"
        node.add_child(child)
        assert len(node.children) == 1
        assert node.children[0].content == "Hello"

    def test_animate_node_to_dict(self):
        """UIAnimateNode.to_dict() returns correct structure."""
        node = UIAnimateNode()
        node.anim_type = "fade"
        node.anim_duration = "300"
        node.anim_trigger = "on-load"
        node.add_child(UITextNode())

        d = node.to_dict()
        assert d["type"] == "ui_animate"
        assert d["children_count"] == 1
        assert d["anim_type"] == "fade"
        assert d["anim_duration"] == "300"
        assert d["anim_trigger"] == "on-load"

    def test_animate_node_validate_missing_type(self):
        """UIAnimateNode.validate() requires type or animate attribute."""
        node = UIAnimateNode()
        errors = node.validate()
        assert len(errors) > 0
        assert any("requires 'type' or 'animate'" in e for e in errors)

    def test_animate_node_validate_with_type(self):
        """UIAnimateNode.validate() passes with type attribute."""
        node = UIAnimateNode()
        node.anim_type = "fade"
        errors = node.validate()
        assert errors == []

    def test_animate_node_validate_with_animate(self):
        """UIAnimateNode.validate() passes with animate attribute."""
        node = UIAnimateNode()
        node.animate = "slide-in-left"
        errors = node.validate()
        assert errors == []

    def test_animate_node_validate_invalid_type(self):
        """UIAnimateNode.validate() rejects invalid animation type."""
        node = UIAnimateNode()
        node.anim_type = "invalid-animation"
        errors = node.validate()
        assert any("Invalid animation type" in e for e in errors)

    def test_animate_node_validate_invalid_trigger(self):
        """UIAnimateNode.validate() rejects invalid trigger."""
        node = UIAnimateNode()
        node.anim_type = "fade"
        node.anim_trigger = "invalid-trigger"
        errors = node.validate()
        assert any("Invalid animation trigger" in e for e in errors)

    def test_animate_node_validate_invalid_easing(self):
        """UIAnimateNode.validate() rejects invalid easing."""
        node = UIAnimateNode()
        node.anim_type = "fade"
        node.anim_easing = "invalid-easing"
        errors = node.validate()
        assert any("Invalid easing function" in e for e in errors)


# ============================================
# UIAnimationMixin Tests
# ============================================

class TestUIAnimationMixin:
    """Test UIAnimationMixin functionality."""

    def test_mixin_constants(self):
        """UIAnimationMixin has correct animation constants."""
        assert 'fade' in UIAnimationMixin.ANIMATION_TYPES
        assert 'slide' in UIAnimationMixin.ANIMATION_TYPES
        assert 'scale' in UIAnimationMixin.ANIMATION_TYPES
        assert 'rotate' in UIAnimationMixin.ANIMATION_TYPES
        assert 'bounce' in UIAnimationMixin.ANIMATION_TYPES
        assert 'pulse' in UIAnimationMixin.ANIMATION_TYPES
        assert 'shake' in UIAnimationMixin.ANIMATION_TYPES

    def test_mixin_triggers(self):
        """UIAnimationMixin has correct trigger constants."""
        assert 'on-load' in UIAnimationMixin.ANIMATION_TRIGGERS
        assert 'on-hover' in UIAnimationMixin.ANIMATION_TRIGGERS
        assert 'on-click' in UIAnimationMixin.ANIMATION_TRIGGERS
        assert 'on-visible' in UIAnimationMixin.ANIMATION_TRIGGERS

    def test_mixin_easing(self):
        """UIAnimationMixin has correct easing constants."""
        assert 'ease' in UIAnimationMixin.EASING_FUNCTIONS
        assert 'ease-in' in UIAnimationMixin.EASING_FUNCTIONS
        assert 'ease-out' in UIAnimationMixin.EASING_FUNCTIONS
        assert 'linear' in UIAnimationMixin.EASING_FUNCTIONS
        assert 'spring' in UIAnimationMixin.EASING_FUNCTIONS

    def test_has_animation(self):
        """UIAnimateNode.has_animation() returns correct value."""
        node = UIAnimateNode()
        assert node.has_animation() is False

        node.animate = "fade"
        assert node.has_animation() is True

        node2 = UIAnimateNode()
        node2.anim_type = "slide"
        assert node2.has_animation() is True


# ============================================
# Parser Tests
# ============================================

class TestUIAnimateParsing:
    """Test parsing ui:animate tags."""

    def test_parse_basic_animate(self, parser):
        """Parse basic ui:animate tag."""
        src = '''
        <ui:window title="Test">
            <ui:animate type="fade">
                <ui:text>Content</ui:text>
            </ui:animate>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        window = app.ui_windows[0]
        assert len(window.children) == 1
        animate = window.children[0]
        assert isinstance(animate, UIAnimateNode)
        assert animate.anim_type == "fade"
        assert len(animate.children) == 1
        assert isinstance(animate.children[0], UITextNode)

    def test_parse_animate_with_duration(self, parser):
        """Parse ui:animate with duration attribute."""
        src = '''
        <ui:window title="Test">
            <ui:animate type="fade" duration="300">
                <ui:text>Content</ui:text>
            </ui:animate>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        animate = app.ui_windows[0].children[0]
        assert animate.anim_duration == "300"

    def test_parse_animate_with_delay(self, parser):
        """Parse ui:animate with delay attribute."""
        src = '''
        <ui:window title="Test">
            <ui:animate type="slide-left" delay="200">
                <ui:text>Content</ui:text>
            </ui:animate>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        animate = app.ui_windows[0].children[0]
        assert animate.anim_delay == "200"

    def test_parse_animate_with_trigger(self, parser):
        """Parse ui:animate with trigger attribute."""
        src = '''
        <ui:window title="Test">
            <ui:animate type="scale" trigger="on-hover">
                <ui:button>Hover me</ui:button>
            </ui:animate>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        animate = app.ui_windows[0].children[0]
        assert animate.anim_trigger == "on-hover"

    def test_parse_animate_with_easing(self, parser):
        """Parse ui:animate with easing attribute."""
        src = '''
        <ui:window title="Test">
            <ui:animate type="fade" easing="ease-out">
                <ui:text>Content</ui:text>
            </ui:animate>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        animate = app.ui_windows[0].children[0]
        assert animate.anim_easing == "ease-out"

    def test_parse_animate_with_repeat(self, parser):
        """Parse ui:animate with repeat attribute."""
        src = '''
        <ui:window title="Test">
            <ui:animate type="bounce" repeat="infinite">
                <ui:badge>NEW</ui:badge>
            </ui:animate>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        animate = app.ui_windows[0].children[0]
        assert animate.anim_repeat == "infinite"

    def test_parse_animate_with_direction(self, parser):
        """Parse ui:animate with direction attribute."""
        src = '''
        <ui:window title="Test">
            <ui:animate type="pulse" direction="alternate">
                <ui:text>Pulse</ui:text>
            </ui:animate>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        animate = app.ui_windows[0].children[0]
        assert animate.anim_direction == "alternate"

    def test_parse_animate_full_attributes(self, parser):
        """Parse ui:animate with all attributes."""
        src = '''
        <ui:window title="Test">
            <ui:animate type="slide-left" duration="500" delay="100"
                        easing="spring" repeat="2" trigger="on-click"
                        direction="alternate">
                <ui:panel title="Animated Panel">
                    <ui:text>Content</ui:text>
                </ui:panel>
            </ui:animate>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        animate = app.ui_windows[0].children[0]
        assert animate.anim_type == "slide-left"
        assert animate.anim_duration == "500"
        assert animate.anim_delay == "100"
        assert animate.anim_easing == "spring"
        assert animate.anim_repeat == "2"
        assert animate.anim_trigger == "on-click"
        assert animate.anim_direction == "alternate"
        assert len(animate.children) == 1
        assert isinstance(animate.children[0], UIPanelNode)

    def test_parse_nested_animate(self, parser):
        """Parse nested ui:animate tags."""
        src = '''
        <ui:window title="Test">
            <ui:animate type="fade" duration="300">
                <ui:vbox>
                    <ui:animate type="slide-left" delay="100">
                        <ui:text>Item 1</ui:text>
                    </ui:animate>
                    <ui:animate type="slide-left" delay="200">
                        <ui:text>Item 2</ui:text>
                    </ui:animate>
                </ui:vbox>
            </ui:animate>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        outer_animate = app.ui_windows[0].children[0]
        assert isinstance(outer_animate, UIAnimateNode)
        assert outer_animate.anim_type == "fade"

        vbox = outer_animate.children[0]
        assert isinstance(vbox, UIVBoxNode)
        assert len(vbox.children) == 2

        inner_animate1 = vbox.children[0]
        assert isinstance(inner_animate1, UIAnimateNode)
        assert inner_animate1.anim_delay == "100"

    def test_parse_animate_on_visible_trigger(self, parser):
        """Parse ui:animate with on-visible trigger."""
        src = '''
        <ui:window title="Test">
            <ui:animate type="fade-in" trigger="on-visible">
                <ui:panel title="Lazy Load">
                    <ui:text>Appears when scrolled into view</ui:text>
                </ui:panel>
            </ui:animate>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        animate = app.ui_windows[0].children[0]
        assert animate.anim_trigger == "on-visible"


# ============================================
# HTML Adapter Tests
# ============================================

class TestUIAnimateHtmlAdapter:
    """Test HTML rendering of ui:animate nodes."""

    def test_render_basic_animate(self, parser):
        """Render basic ui:animate to HTML."""
        src = '''
        <ui:window title="Test">
            <ui:animate type="fade">
                <ui:text>Content</ui:text>
            </ui:animate>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        adapter = UIHtmlAdapter()
        html = adapter.generate(app.ui_windows, [], title="Test")

        # Should contain animation classes
        assert 'q-animate' in html
        assert 'q-anim-fade' in html
        # Should include animation CSS
        assert '@keyframes q-fade-in' in html

    def test_render_animate_with_duration(self, parser):
        """Render ui:animate with custom duration."""
        src = '''
        <ui:window title="Test">
            <ui:animate type="fade" duration="500">
                <ui:text>Content</ui:text>
            </ui:animate>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        adapter = UIHtmlAdapter()
        html = adapter.generate(app.ui_windows, [], title="Test")

        # Should have duration CSS variable
        assert '--q-anim-duration: 500ms' in html

    def test_render_animate_with_delay(self, parser):
        """Render ui:animate with delay."""
        src = '''
        <ui:window title="Test">
            <ui:animate type="slide-left" delay="200">
                <ui:text>Content</ui:text>
            </ui:animate>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        adapter = UIHtmlAdapter()
        html = adapter.generate(app.ui_windows, [], title="Test")

        assert '--q-anim-delay: 200ms' in html

    def test_render_animate_with_trigger(self, parser):
        """Render ui:animate with trigger class."""
        src = '''
        <ui:window title="Test">
            <ui:animate type="scale" trigger="on-hover">
                <ui:button>Hover</ui:button>
            </ui:animate>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        adapter = UIHtmlAdapter()
        html = adapter.generate(app.ui_windows, [], title="Test")

        assert 'q-trigger-on-hover' in html

    def test_render_animate_with_easing(self, parser):
        """Render ui:animate with easing class."""
        src = '''
        <ui:window title="Test">
            <ui:animate type="fade" easing="spring">
                <ui:text>Content</ui:text>
            </ui:animate>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        adapter = UIHtmlAdapter()
        html = adapter.generate(app.ui_windows, [], title="Test")

        assert 'q-easing-spring' in html

    def test_render_animate_with_repeat(self, parser):
        """Render ui:animate with repeat."""
        src = '''
        <ui:window title="Test">
            <ui:animate type="bounce" repeat="infinite">
                <ui:badge>NEW</ui:badge>
            </ui:animate>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        adapter = UIHtmlAdapter()
        html = adapter.generate(app.ui_windows, [], title="Test")

        assert '--q-anim-repeat: infinite' in html

    def test_render_animate_includes_js(self, parser):
        """Render ui:animate includes animation JS."""
        src = '''
        <ui:window title="Test">
            <ui:animate type="fade" trigger="on-click">
                <ui:text>Click me</ui:text>
            </ui:animate>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        adapter = UIHtmlAdapter()
        html = adapter.generate(app.ui_windows, [], title="Test")

        # Should include animation JS
        assert '__quantumAnimate' in html

    def test_render_animate_unique_ids(self, parser):
        """Render multiple ui:animate with unique IDs."""
        src = '''
        <ui:window title="Test">
            <ui:animate type="fade">
                <ui:text>First</ui:text>
            </ui:animate>
            <ui:animate type="slide">
                <ui:text>Second</ui:text>
            </ui:animate>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        adapter = UIHtmlAdapter()
        html = adapter.generate(app.ui_windows, [], title="Test")

        assert 'id="q-anim-1"' in html
        assert 'id="q-anim-2"' in html

    def test_render_all_animation_types(self, parser):
        """Render all supported animation types."""
        animation_types = ['fade', 'slide', 'scale', 'rotate', 'bounce', 'pulse', 'shake']

        for anim_type in animation_types:
            src = f'''
            <ui:window title="Test">
                <ui:animate type="{anim_type}">
                    <ui:text>Content</ui:text>
                </ui:animate>
            </ui:window>
            '''
            app = parse_ui(parser, src)
            adapter = UIHtmlAdapter()
            html = adapter.generate(app.ui_windows, [], title="Test")

            assert f'q-anim-{anim_type}' in html

    def test_render_on_visible_trigger(self, parser):
        """Render ui:animate with on-visible trigger includes data attribute."""
        src = '''
        <ui:window title="Test">
            <ui:animate type="fade" trigger="on-visible">
                <ui:text>Lazy content</ui:text>
            </ui:animate>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        adapter = UIHtmlAdapter()
        html = adapter.generate(app.ui_windows, [], title="Test")

        assert 'q-trigger-on-visible' in html
        assert 'data-anim-once="true"' in html


# ============================================
# Integration Tests
# ============================================

class TestAnimationIntegration:
    """Integration tests for animation system."""

    def test_animation_with_layout_attrs(self, parser):
        """Test ui:animate works with layout attributes."""
        src = '''
        <ui:window title="Test">
            <ui:animate type="fade" duration="300"
                        width="100%" padding="16" background="primary">
                <ui:text>Styled animated content</ui:text>
            </ui:animate>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        animate = app.ui_windows[0].children[0]

        # Animation attributes
        assert animate.anim_type == "fade"
        assert animate.anim_duration == "300"

        # Layout attributes
        assert animate.width == "100%"
        assert animate.padding == "16"
        assert animate.background == "primary"

    def test_animation_validates_children(self, parser):
        """Test ui:animate validates its children."""
        node = UIAnimateNode()
        node.anim_type = "fade"

        # Add child with invalid content
        from core.features.ui_engine.src.ast_nodes import UITabNode
        child = UITabNode()  # Tab requires title
        child.title = ""  # Empty title
        node.add_child(child)

        errors = node.validate()
        assert any("Tab title is required" in e for e in errors)

    def test_complex_animation_scene(self, parser):
        """Test complex animation scenario with multiple animations."""
        src = '''
        <ui:window title="Animated Dashboard">
            <ui:animate type="fade" duration="500">
                <ui:header title="Dashboard" />
            </ui:animate>

            <ui:hbox gap="16" padding="16">
                <ui:animate type="slide-left" delay="100" trigger="on-load">
                    <ui:panel title="Stats">
                        <ui:animate type="scale" trigger="on-hover">
                            <ui:text size="xl">42</ui:text>
                        </ui:animate>
                    </ui:panel>
                </ui:animate>

                <ui:animate type="slide-right" delay="200" trigger="on-load">
                    <ui:panel title="Chart">
                        <ui:text>Chart here</ui:text>
                    </ui:panel>
                </ui:animate>
            </ui:hbox>

            <ui:animate type="fade-in" trigger="on-visible" delay="300">
                <ui:footer>Footer content</ui:footer>
            </ui:animate>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        adapter = UIHtmlAdapter()
        html = adapter.generate(app.ui_windows, [], title="Dashboard")

        # Verify all animations are present
        assert 'q-anim-fade' in html
        assert 'q-anim-slide-left' in html
        assert 'q-anim-slide-right' in html
        assert 'q-anim-scale' in html
        assert 'q-anim-fade-in' in html

        # Verify triggers
        assert 'q-trigger-on-hover' in html
        assert 'q-trigger-on-visible' in html

        # Verify delays
        assert '--q-anim-delay: 100ms' in html
        assert '--q-anim-delay: 200ms' in html
        assert '--q-anim-delay: 300ms' in html

    def test_reduced_motion_css(self, parser):
        """Test CSS includes reduced motion media query."""
        src = '''
        <ui:window title="Test">
            <ui:animate type="fade">
                <ui:text>Content</ui:text>
            </ui:animate>
        </ui:window>
        '''
        app = parse_ui(parser, src)
        adapter = UIHtmlAdapter()
        html = adapter.generate(app.ui_windows, [], title="Test")

        assert '@media (prefers-reduced-motion: reduce)' in html
