"""
AST Nodes for Theming System

UIThemeNode: Represents <ui:theme> tag for theme configuration
UIColorNode: Represents <ui:color> tag for custom color definitions
"""

from typing import Dict, Any, List, Optional
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
from core.ast_nodes import QuantumNode


class UIColorNode(QuantumNode):
    """
    Represents <ui:color> - Custom color definition within a theme.

    Attributes:
        name: Color token name (e.g., 'primary', 'background', 'text')
        value: CSS color value (e.g., '#ff6b6b', 'rgb(255, 107, 107)')

    Example:
        <ui:color name="primary" value="#3b82f6" />
        <ui:color name="danger" value="rgb(239, 68, 68)" />
    """

    def __init__(self):
        self.name: str = ""
        self.value: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "ui_color",
            "name": self.name,
            "value": self.value,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Color name is required")
        if not self.value:
            errors.append(f"Color value is required for '{self.name}'")
        return errors


class UIThemeNode(QuantumNode):
    """
    Represents <ui:theme> - Theme configuration for the UI.

    Supports:
        - Preset themes: 'light', 'dark'
        - Custom themes with color definitions
        - Runtime theme switching

    Attributes:
        name: Theme name (for custom themes)
        preset: Preset theme to extend ('light', 'dark')
        colors: List of custom color overrides
        auto_switch: Enable automatic dark/light switching based on system preference

    Examples:
        <!-- Use dark preset -->
        <ui:theme preset="dark" />

        <!-- Custom theme extending light -->
        <ui:theme name="ocean" preset="light">
            <ui:color name="primary" value="#0ea5e9" />
            <ui:color name="secondary" value="#06b6d4" />
        </ui:theme>

        <!-- Auto-switch based on system preference -->
        <ui:theme preset="light" auto-switch="true" />
    """

    # Valid preset names
    VALID_PRESETS = {'light', 'dark', 'high-contrast', 'sepia', 'nord', 'dracula'}

    # Valid color token names (matching design tokens)
    VALID_COLOR_NAMES = {
        'primary', 'secondary', 'success', 'danger', 'warning', 'info',
        'light', 'dark', 'background', 'text', 'border', 'muted',
        # Extended color tokens
        'surface', 'overlay', 'accent', 'focus',
        # Font size tokens (for completeness)
        'font-xs', 'font-sm', 'font-md', 'font-lg', 'font-xl', 'font-2xl',
    }

    def __init__(self):
        self.name: Optional[str] = None
        self.preset: str = "light"  # Default to light theme
        self.colors: List[UIColorNode] = []
        self.auto_switch: bool = False

    def add_color(self, color: UIColorNode):
        """Add a custom color override."""
        self.colors.append(color)

    def get_color(self, name: str) -> Optional[str]:
        """Get color value by name, or None if not defined."""
        for color in self.colors:
            if color.name == name:
                return color.value
        return None

    def get_color_overrides(self) -> Dict[str, str]:
        """Return all custom colors as a dict."""
        return {c.name: c.value for c in self.colors}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "ui_theme",
            "name": self.name,
            "preset": self.preset,
            "auto_switch": self.auto_switch,
            "colors": [c.to_dict() for c in self.colors],
        }

    def validate(self) -> List[str]:
        errors = []

        # Validate preset
        if self.preset and self.preset not in self.VALID_PRESETS:
            errors.append(
                f"Invalid theme preset '{self.preset}'. "
                f"Valid presets: {', '.join(sorted(self.VALID_PRESETS))}"
            )

        # Validate colors
        for color in self.colors:
            errors.extend(color.validate())
            # Warn about unknown color names (soft validation)
            if color.name and color.name not in self.VALID_COLOR_NAMES:
                # This is a warning, not an error - custom colors are allowed
                pass

        return errors
