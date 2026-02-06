"""
Tests for the Theming System feature.

Tests:
1. Theme preset parsing (light/dark)
2. Custom theme with color overrides
3. Theme attribute on q:application
4. ui:theme tag parsing
5. Auto-switch theme mode
6. Theme CSS generation
7. Theme JavaScript injection
"""

import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.parser import QuantumParser
from core.ast_nodes import ApplicationNode
from core.features.theming.src import (
    UIThemeNode, UIColorNode,
    THEME_LIGHT, THEME_DARK, THEME_PRESETS,
    get_theme_css, get_theme_preset, get_theme_switch_js,
)
from runtime.ui_html_adapter import UIHtmlAdapter
from runtime.ui_builder import UIBuilder


# ==========================================================================
# AST Node Tests
# ==========================================================================

class TestUIThemeNode:
    """Test UIThemeNode creation and validation."""

    def test_default_theme_node(self):
        """Test default UIThemeNode values."""
        node = UIThemeNode()
        assert node.preset == 'light'
        assert node.name is None
        assert node.auto_switch is False
        assert node.colors == []

    def test_add_color(self):
        """Test adding color overrides."""
        node = UIThemeNode()
        color = UIColorNode()
        color.name = 'primary'
        color.value = '#ff0000'
        node.add_color(color)

        assert len(node.colors) == 1
        assert node.colors[0].name == 'primary'
        assert node.colors[0].value == '#ff0000'

    def test_get_color(self):
        """Test getting color by name."""
        node = UIThemeNode()
        color = UIColorNode()
        color.name = 'primary'
        color.value = '#00ff00'
        node.add_color(color)

        assert node.get_color('primary') == '#00ff00'
        assert node.get_color('secondary') is None

    def test_get_color_overrides(self):
        """Test getting all color overrides as dict."""
        node = UIThemeNode()

        color1 = UIColorNode()
        color1.name = 'primary'
        color1.value = '#111'
        node.add_color(color1)

        color2 = UIColorNode()
        color2.name = 'secondary'
        color2.value = '#222'
        node.add_color(color2)

        overrides = node.get_color_overrides()
        assert overrides == {'primary': '#111', 'secondary': '#222'}

    def test_validate_valid_preset(self):
        """Test validation of valid preset."""
        node = UIThemeNode()
        node.preset = 'dark'
        errors = node.validate()
        assert errors == []

    def test_validate_invalid_preset(self):
        """Test validation fails for invalid preset."""
        node = UIThemeNode()
        node.preset = 'neon'
        errors = node.validate()
        assert len(errors) == 1
        assert 'Invalid theme preset' in errors[0]

    def test_to_dict(self):
        """Test serialization to dict."""
        node = UIThemeNode()
        node.name = 'custom'
        node.preset = 'dark'
        node.auto_switch = True

        color = UIColorNode()
        color.name = 'primary'
        color.value = '#abc'
        node.add_color(color)

        d = node.to_dict()
        assert d['type'] == 'ui_theme'
        assert d['name'] == 'custom'
        assert d['preset'] == 'dark'
        assert d['auto_switch'] is True
        assert len(d['colors']) == 1


class TestUIColorNode:
    """Test UIColorNode creation and validation."""

    def test_default_color_node(self):
        """Test default UIColorNode values."""
        node = UIColorNode()
        assert node.name == ''
        assert node.value == ''

    def test_validate_missing_name(self):
        """Test validation fails when name is missing."""
        node = UIColorNode()
        node.value = '#fff'
        errors = node.validate()
        assert any('name is required' in e for e in errors)

    def test_validate_missing_value(self):
        """Test validation fails when value is missing."""
        node = UIColorNode()
        node.name = 'primary'
        errors = node.validate()
        assert any('value is required' in e for e in errors)


# ==========================================================================
# Theme Presets Tests
# ==========================================================================

class TestThemePresets:
    """Test theme preset definitions."""

    def test_light_preset_exists(self):
        """Test that light preset is defined."""
        assert 'light' in THEME_PRESETS
        assert THEME_LIGHT is THEME_PRESETS['light']

    def test_dark_preset_exists(self):
        """Test that dark preset is defined."""
        assert 'dark' in THEME_PRESETS
        assert THEME_DARK is THEME_PRESETS['dark']

    def test_presets_have_required_colors(self):
        """Test that presets define all required color tokens."""
        required = ['primary', 'secondary', 'background', 'text', 'border']
        for preset_name, preset in THEME_PRESETS.items():
            for color in required:
                assert color in preset, f"Preset '{preset_name}' missing '{color}'"

    def test_get_theme_preset(self):
        """Test get_theme_preset helper."""
        assert get_theme_preset('light') == THEME_LIGHT
        assert get_theme_preset('dark') == THEME_DARK
        assert get_theme_preset('unknown') is None


# ==========================================================================
# CSS Generation Tests
# ==========================================================================

class TestThemeCssGeneration:
    """Test theme CSS generation."""

    def test_get_theme_css_light(self):
        """Test CSS generation for light theme."""
        css = get_theme_css('light')
        assert ':root' in css
        assert '--q-primary' in css
        assert '--q-background' in css

    def test_get_theme_css_dark(self):
        """Test CSS generation for dark theme."""
        css = get_theme_css('dark')
        assert ':root' in css
        assert '--q-primary' in css
        assert '[data-theme="dark"]' in css

    def test_get_theme_css_with_overrides(self):
        """Test CSS generation with color overrides."""
        overrides = {'primary': '#custom123'}
        css = get_theme_css('light', overrides)
        assert '#custom123' in css

    def test_get_theme_css_auto_switch(self):
        """Test CSS generation with auto-switch mode."""
        css = get_theme_css('light', auto_switch=True)
        assert '@media (prefers-color-scheme: dark)' in css
        assert '[data-theme="light"]' in css
        assert '[data-theme="dark"]' in css


# ==========================================================================
# JavaScript Generation Tests
# ==========================================================================

class TestThemeJavaScript:
    """Test theme JavaScript generation."""

    def test_get_theme_switch_js(self):
        """Test theme switching JS generation."""
        js = get_theme_switch_js()
        assert '<script>' in js
        assert '__quantumSetTheme' in js
        assert '__quantumToggleTheme' in js
        assert '__quantumGetTheme' in js
        assert 'localStorage' in js

    def test_js_contains_system_preference_listener(self):
        """Test that JS listens for system preference changes."""
        js = get_theme_switch_js()
        assert 'prefers-color-scheme: dark' in js


# ==========================================================================
# Parser Tests
# ==========================================================================

class TestThemeParsing:
    """Test parsing of theme elements."""

    def test_parse_theme_attribute(self):
        """Test parsing theme attribute on q:application."""
        xml = '''<q:application id="TestApp" type="ui" theme="dark">
            <ui:window title="Test">
                <ui:text>Hello</ui:text>
            </ui:window>
        </q:application>'''

        parser = QuantumParser()
        ast = parser.parse(xml)

        assert isinstance(ast, ApplicationNode)
        assert ast.ui_theme is not None
        assert ast.ui_theme.preset == 'dark'
        assert ast.ui_theme_preset == 'dark'

    def test_parse_ui_theme_tag(self):
        """Test parsing ui:theme tag."""
        xml = '''<q:application id="TestApp" type="ui">
            <ui:theme preset="dark" />
            <ui:window title="Test">
                <ui:text>Hello</ui:text>
            </ui:window>
        </q:application>'''

        parser = QuantumParser()
        ast = parser.parse(xml)

        assert isinstance(ast, ApplicationNode)
        assert ast.ui_theme is not None
        assert ast.ui_theme.preset == 'dark'

    def test_parse_ui_theme_with_colors(self):
        """Test parsing ui:theme with custom colors."""
        xml = '''<q:application id="TestApp" type="ui">
            <ui:theme name="ocean" preset="light">
                <ui:color name="primary" value="#0ea5e9" />
                <ui:color name="secondary" value="#06b6d4" />
            </ui:theme>
            <ui:window title="Test">
                <ui:text>Hello</ui:text>
            </ui:window>
        </q:application>'''

        parser = QuantumParser()
        ast = parser.parse(xml)

        assert ast.ui_theme is not None
        assert ast.ui_theme.name == 'ocean'
        assert ast.ui_theme.preset == 'light'
        assert len(ast.ui_theme.colors) == 2
        assert ast.ui_theme.get_color('primary') == '#0ea5e9'

    def test_parse_ui_theme_auto_switch(self):
        """Test parsing ui:theme with auto-switch."""
        xml = '''<q:application id="TestApp" type="ui">
            <ui:theme preset="light" auto-switch="true" />
            <ui:window title="Test">
                <ui:text>Hello</ui:text>
            </ui:window>
        </q:application>'''

        parser = QuantumParser()
        ast = parser.parse(xml)

        assert ast.ui_theme is not None
        assert ast.ui_theme.auto_switch is True

    def test_ui_theme_overrides_attribute(self):
        """Test that ui:theme tag overrides theme attribute."""
        xml = '''<q:application id="TestApp" type="ui" theme="light">
            <ui:theme preset="dark" />
            <ui:window title="Test">
                <ui:text>Hello</ui:text>
            </ui:window>
        </q:application>'''

        parser = QuantumParser()
        ast = parser.parse(xml)

        # ui:theme should override theme attribute
        assert ast.ui_theme.preset == 'dark'


# ==========================================================================
# HTML Adapter Integration Tests
# ==========================================================================

class TestThemeHtmlIntegration:
    """Test theme integration with HTML adapter."""

    def test_adapter_generates_theme_css(self):
        """Test that adapter generates theme CSS."""
        theme = UIThemeNode()
        theme.preset = 'dark'

        adapter = UIHtmlAdapter()
        html = adapter.generate([], [], title="Test", theme=theme)

        assert '--q-primary' in html
        assert '--q-background' in html

    def test_adapter_generates_theme_js(self):
        """Test that adapter includes theme switching JS."""
        theme = UIThemeNode()
        theme.preset = 'light'

        adapter = UIHtmlAdapter()
        html = adapter.generate([], [], title="Test", theme=theme)

        assert '__quantumSetTheme' in html
        assert '__quantumToggleTheme' in html

    def test_adapter_applies_color_overrides(self):
        """Test that adapter applies color overrides."""
        theme = UIThemeNode()
        theme.preset = 'light'

        color = UIColorNode()
        color.name = 'primary'
        color.value = '#customcolor'
        theme.add_color(color)

        adapter = UIHtmlAdapter()
        html = adapter.generate([], [], title="Test", theme=theme)

        assert '#customcolor' in html

    def test_adapter_auto_switch_media_query(self):
        """Test that adapter adds media query for auto-switch."""
        theme = UIThemeNode()
        theme.preset = 'light'
        theme.auto_switch = True

        adapter = UIHtmlAdapter()
        html = adapter.generate([], [], title="Test", theme=theme)

        assert '@media (prefers-color-scheme: dark)' in html


# ==========================================================================
# UI Builder Integration Tests
# ==========================================================================

class TestThemeBuilderIntegration:
    """Test theme integration with UI Builder."""

    def test_builder_passes_theme_to_adapter(self):
        """Test that builder passes theme to HTML adapter."""
        xml = '''<q:application id="ThemeApp" type="ui" theme="dark">
            <ui:window title="Themed App">
                <ui:text>Dark theme content</ui:text>
            </ui:window>
        </q:application>'''

        parser = QuantumParser()
        ast = parser.parse(xml)

        builder = UIBuilder()
        html = builder.build(ast, target='html')

        # Check that dark theme CSS is present
        assert '--q-primary' in html
        assert '__quantumSetTheme' in html


# ==========================================================================
# Negative Tests
# ==========================================================================

class TestThemeNegativeCases:
    """Test error handling for invalid theme configurations."""

    def test_invalid_preset_validation(self):
        """Test that invalid preset is caught during validation."""
        node = UIThemeNode()
        node.preset = 'nonexistent'
        errors = node.validate()
        assert len(errors) > 0

    def test_color_without_value_validation(self):
        """Test that color without value is caught."""
        color = UIColorNode()
        color.name = 'primary'
        # value not set
        errors = color.validate()
        assert len(errors) > 0

    def test_color_without_name_validation(self):
        """Test that color without name is caught."""
        color = UIColorNode()
        color.value = '#fff'
        # name not set
        errors = color.validate()
        assert len(errors) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
