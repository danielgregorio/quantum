"""
Theming System for Quantum UI Engine

Provides dark/light mode support, custom color themes, and runtime theme switching.
Integrates with the design tokens system for consistent styling.

Usage:
    # In .q files:
    <q:application id="MyApp" type="ui" theme="dark">
        <ui:window>...</ui:window>
    </q:application>

    # Or with ui:theme tag:
    <q:application id="MyApp" type="ui">
        <ui:theme preset="dark" />
        <ui:window>...</ui:window>
    </q:application>

    # Custom theme:
    <q:application id="MyApp" type="ui">
        <ui:theme name="custom">
            <ui:color name="primary" value="#ff6b6b" />
            <ui:color name="background" value="#2d3436" />
        </ui:theme>
        <ui:window>...</ui:window>
    </q:application>
"""

from .ast_node import UIThemeNode, UIColorNode
from .presets import (
    THEME_LIGHT,
    THEME_DARK,
    THEME_PRESETS,
    get_theme_css,
    get_theme_preset,
    get_theme_switch_js,
)

__all__ = [
    'UIThemeNode',
    'UIColorNode',
    'THEME_LIGHT',
    'THEME_DARK',
    'THEME_PRESETS',
    'get_theme_css',
    'get_theme_preset',
    'get_theme_switch_js',
]
