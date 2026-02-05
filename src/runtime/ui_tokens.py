"""
UI Engine - Design Tokens System

Provides a normalized design system that works across HTML and Textual targets.
Tokens ensure visual consistency when the same UI definition is rendered
in different environments.

Token Categories:
  - Spacing: xs, sm, md, lg, xl (padding, margin, gap)
  - Sizing: auto, fill, 1/2, 1/3, 1/4, 2/3, 3/4
  - Colors: semantic (primary, secondary, success, danger, warning, info)
  - Typography: xs, sm, md, lg, xl, 2xl

Usage:
    from runtime.ui_tokens import TokenConverter

    html_converter = TokenConverter('html')
    textual_converter = TokenConverter('textual')

    html_converter.spacing('md')  # -> '16px'
    textual_converter.spacing('md')  # -> '2'
"""

from typing import Dict, Optional, Tuple


# ==========================================================================
# Spacing Tokens
# ==========================================================================

# Spacing in abstract units (converted per-target)
SPACING_TOKENS = {
    'none': 0,
    'xs': 4,
    'sm': 8,
    'md': 16,
    'lg': 24,
    'xl': 32,
    '2xl': 48,
}

# HTML: pixels
SPACING_HTML = {k: f"{v}px" for k, v in SPACING_TOKENS.items()}
SPACING_HTML['none'] = '0'

# Textual: character cells (roughly 8px per cell)
SPACING_TEXTUAL = {
    'none': '0',
    'xs': '1',
    'sm': '1',
    'md': '2',
    'lg': '3',
    'xl': '4',
    '2xl': '6',
}


# ==========================================================================
# Sizing Tokens
# ==========================================================================

SIZE_TOKENS = {
    'auto': 'auto',
    'fill': 'full',
    '1/2': '50%',
    '1/3': '33.333%',
    '1/4': '25%',
    '2/3': '66.666%',
    '3/4': '75%',
    'full': '100%',
}

# HTML sizing
SIZE_HTML = {
    'auto': 'auto',
    'fill': '100%',
    'full': '100%',
    '1/2': '50%',
    '1/3': '33.333%',
    '1/4': '25%',
    '2/3': '66.666%',
    '3/4': '75%',
}

# Textual sizing (uses fr units or %)
SIZE_TEXTUAL = {
    'auto': 'auto',
    'fill': '1fr',
    'full': '100%',
    '1/2': '1fr',  # In a 2-column context
    '1/3': '1fr',  # In a 3-column context
    '1/4': '1fr',  # In a 4-column context
    '2/3': '2fr',
    '3/4': '3fr',
}


# ==========================================================================
# Color Tokens
# ==========================================================================

# Semantic color names
COLOR_SEMANTIC = {
    'primary', 'secondary', 'success', 'danger',
    'warning', 'info', 'light', 'dark',
    'text', 'background', 'border', 'muted',
}

# HTML: CSS custom properties
COLOR_HTML = {
    'primary': 'var(--q-primary)',
    'secondary': 'var(--q-secondary)',
    'success': 'var(--q-success)',
    'danger': 'var(--q-danger)',
    'warning': 'var(--q-warning)',
    'info': 'var(--q-info)',
    'light': 'var(--q-light)',
    'dark': 'var(--q-dark)',
    'text': 'var(--q-text)',
    'background': 'var(--q-bg)',
    'border': 'var(--q-border)',
    'muted': 'var(--q-secondary)',
}

# Textual: theme variables ($ prefix)
COLOR_TEXTUAL = {
    'primary': '$primary',
    'secondary': '$secondary',
    'success': '$success',
    'danger': '$error',
    'warning': '$warning',
    'info': '$accent',
    'light': '$surface',
    'dark': '$background',
    'text': '$text',
    'background': '$background',
    'border': '$primary-background',
    'muted': '$text-muted',
}


# ==========================================================================
# Typography Tokens
# ==========================================================================

FONT_SIZE_TOKENS = {
    'xs': 0.75,   # 12px
    'sm': 0.875,  # 14px
    'md': 1.0,    # 16px
    'lg': 1.25,   # 20px
    'xl': 1.5,    # 24px
    '2xl': 2.0,   # 32px
}

FONT_SIZE_HTML = {
    'xs': 'var(--q-font-xs)',
    'sm': 'var(--q-font-sm)',
    'md': 'var(--q-font-md)',
    'lg': 'var(--q-font-lg)',
    'xl': 'var(--q-font-xl)',
    '2xl': 'var(--q-font-2xl)',
}

# Textual doesn't support font sizes in the same way
# We use text styles instead
FONT_SIZE_TEXTUAL = {
    'xs': '',       # No direct mapping
    'sm': '',       # No direct mapping
    'md': '',       # Default
    'lg': 'bold',   # Emphasize with bold
    'xl': 'bold',
    '2xl': 'bold',
}


# ==========================================================================
# Align/Justify Tokens
# ==========================================================================

ALIGN_TOKENS = {'start', 'center', 'end', 'stretch'}

ALIGN_HTML = {
    'start': 'flex-start',
    'center': 'center',
    'end': 'flex-end',
    'stretch': 'stretch',
}

# Textual uses different alignment syntax: "horizontal vertical"
ALIGN_TEXTUAL = {
    'start': 'left',
    'center': 'center',
    'end': 'right',
    'stretch': 'center',  # No direct equivalent
}

JUSTIFY_TOKENS = {'start', 'center', 'end', 'between', 'around'}

JUSTIFY_HTML = {
    'start': 'flex-start',
    'center': 'center',
    'end': 'flex-end',
    'between': 'space-between',
    'around': 'space-around',
}

# Textual doesn't have justify-content equivalent
# We approximate with alignment
JUSTIFY_TEXTUAL = {
    'start': 'left',
    'center': 'center',
    'end': 'right',
    'between': 'center',  # No equivalent, use center
    'around': 'center',   # No equivalent, use center
}


# ==========================================================================
# Token Converter
# ==========================================================================

class TokenConverter:
    """Converts design tokens to target-specific values."""

    def __init__(self, target: str = 'html'):
        """
        Args:
            target: 'html' or 'textual'
        """
        self.target = target.lower()
        if self.target not in ('html', 'textual'):
            raise ValueError(f"Unknown target: {target}")

    def spacing(self, value: str) -> str:
        """Convert spacing token or raw value to target format.

        Accepts:
          - Token: 'sm', 'md', 'lg', etc.
          - Raw pixel: '16', '16px'
          - Raw percentage: '10%'
        """
        if not value:
            return ''

        value_lower = value.lower().strip()

        # Check if it's a token
        if value_lower in SPACING_TOKENS:
            if self.target == 'html':
                return SPACING_HTML[value_lower]
            else:
                return SPACING_TEXTUAL[value_lower]

        # Raw value - convert for target
        return self._convert_raw_spacing(value)

    def _convert_raw_spacing(self, value: str) -> str:
        """Convert raw spacing value to target format."""
        if self.target == 'html':
            # HTML accepts px, %, em, etc.
            if value.endswith(('px', '%', 'em', 'rem')):
                return value
            try:
                int(value)
                return f"{value}px"
            except ValueError:
                return value
        else:
            # Textual uses character cells
            if value.endswith('px'):
                px = int(value[:-2])
                return str(max(1, px // 8))
            if value.endswith('%'):
                return value  # Textual supports %
            try:
                px = int(value)
                return str(max(1, px // 8))
            except ValueError:
                return '1'  # Default to 1 cell

    def size(self, value: str) -> str:
        """Convert size token or raw value to target format.

        Accepts:
          - Token: 'fill', 'auto', '1/2', '1/3', etc.
          - Raw pixel: '200', '200px'
          - Raw percentage: '50%'
        """
        if not value:
            return ''

        value_lower = value.lower().strip()

        # Check if it's a token
        if value_lower in SIZE_TOKENS:
            if self.target == 'html':
                return SIZE_HTML.get(value_lower, value)
            else:
                return SIZE_TEXTUAL.get(value_lower, value)

        # Raw value
        return self._convert_raw_size(value)

    def _convert_raw_size(self, value: str) -> str:
        """Convert raw size value to target format."""
        if self.target == 'html':
            if value == 'fill':
                return '100%'
            if value.endswith(('px', '%', 'em', 'rem', 'vw', 'vh')):
                return value
            try:
                int(value)
                return f"{value}px"
            except ValueError:
                return value
        else:
            # Textual
            if value == 'fill':
                return '100%'
            if value.endswith('%'):
                return value
            if value.endswith('px'):
                px = int(value[:-2])
                return str(max(1, px // 8))  # Convert to cells
            try:
                px = int(value)
                return str(max(1, px // 8))
            except ValueError:
                return 'auto'

    def color(self, value: str) -> str:
        """Convert color token or raw value to target format.

        Accepts:
          - Token: 'primary', 'success', etc.
          - Raw hex: '#ff0000'
          - Raw name: 'red', 'blue'
        """
        if not value:
            return ''

        value_lower = value.lower().strip()

        # Check if it's a semantic token
        if value_lower in COLOR_SEMANTIC:
            if self.target == 'html':
                return COLOR_HTML.get(value_lower, value)
            else:
                return COLOR_TEXTUAL.get(value_lower, value)

        # Raw color value
        if self.target == 'html':
            return value  # HTML accepts any CSS color
        else:
            # Textual accepts color names and some formats
            return self._convert_raw_color_textual(value)

    def _convert_raw_color_textual(self, value: str) -> str:
        """Convert raw color for Textual."""
        # Textual supports: color names, rgb(), ansi colors
        if value.startswith('#'):
            # Convert hex to rgb for better compatibility
            return value  # Textual 0.40+ supports hex
        return value

    def font_size(self, value: str) -> str:
        """Convert font size token to target format."""
        if not value:
            return ''

        value_lower = value.lower().strip()

        if value_lower in FONT_SIZE_TOKENS:
            if self.target == 'html':
                return FONT_SIZE_HTML.get(value_lower, value)
            else:
                return FONT_SIZE_TEXTUAL.get(value_lower, '')

        # Raw value
        return value if self.target == 'html' else ''

    def align(self, value: str) -> str:
        """Convert align token to target format."""
        if not value:
            return ''

        value_lower = value.lower().strip()

        if self.target == 'html':
            return ALIGN_HTML.get(value_lower, value)
        else:
            return ALIGN_TEXTUAL.get(value_lower, 'center')

    def justify(self, value: str) -> str:
        """Convert justify token to target format."""
        if not value:
            return ''

        value_lower = value.lower().strip()

        if self.target == 'html':
            return JUSTIFY_HTML.get(value_lower, value)
        else:
            return JUSTIFY_TEXTUAL.get(value_lower, 'center')


# ==========================================================================
# Compatibility Warnings
# ==========================================================================

# Features that don't translate well between targets
COMPATIBILITY_WARNINGS = {
    'gap': {
        'textual': "gap is not supported in Textual; using margin on children",
    },
    'justify_between': {
        'textual': "justify='between' has no Textual equivalent; items will be centered",
    },
    'justify_around': {
        'textual': "justify='around' has no Textual equivalent; items will be centered",
    },
    'image': {
        'textual': "Images cannot be displayed in terminal; showing placeholder text",
    },
    'link_external': {
        'textual': "External links are not clickable in terminal; showing as text",
    },
    'font_size': {
        'textual': "Font sizes are not adjustable in terminal; using text weight instead",
    },
    'animation': {
        'textual': "CSS animations are not supported in terminal",
    },
    'pixel_units': {
        'textual': "Pixel values are converted to character cells (÷8)",
    },
}


def get_compatibility_warnings(features_used: set, target: str) -> list:
    """Get list of compatibility warnings for features used."""
    warnings = []
    for feature in features_used:
        if feature in COMPATIBILITY_WARNINGS:
            warning = COMPATIBILITY_WARNINGS[feature].get(target)
            if warning:
                warnings.append(f"[{feature}] {warning}")
    return warnings


# ==========================================================================
# Utility: Check if value is a token
# ==========================================================================

def is_spacing_token(value: str) -> bool:
    return value.lower().strip() in SPACING_TOKENS

def is_size_token(value: str) -> bool:
    return value.lower().strip() in SIZE_TOKENS

def is_color_token(value: str) -> bool:
    return value.lower().strip() in COLOR_SEMANTIC

def is_font_token(value: str) -> bool:
    return value.lower().strip() in FONT_SIZE_TOKENS
