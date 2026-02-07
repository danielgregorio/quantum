"""
Theme Presets for Quantum UI Engine

Provides predefined color schemes for light and dark modes.
Colors are defined as CSS custom properties (variables) that integrate
with the existing design tokens system.
"""

from typing import Dict, Optional


# ==========================================================================
# Light Theme (Default)
# ==========================================================================

THEME_LIGHT: Dict[str, str] = {
    # Primary colors
    'primary': '#3b82f6',       # Blue 500
    'secondary': '#64748b',     # Slate 500
    'success': '#22c55e',       # Green 500
    'danger': '#ef4444',        # Red 500
    'warning': '#f59e0b',       # Amber 500
    'info': '#06b6d4',          # Cyan 500

    # Neutral colors
    'light': '#f8fafc',         # Slate 50
    'dark': '#1e293b',          # Slate 800
    'background': '#ffffff',    # White
    'text': '#1e293b',          # Slate 800
    'border': '#e2e8f0',        # Slate 200
    'muted': '#94a3b8',         # Slate 400

    # Extended colors
    'surface': '#f8fafc',       # Slate 50
    'overlay': 'rgba(0,0,0,0.5)',
    'accent': '#8b5cf6',        # Violet 500
    'focus': 'rgba(59,130,246,0.5)',  # Primary with alpha

    # UI elements
    'radius': '6px',
    'shadow': '0 1px 3px rgba(0,0,0,0.1)',

    # Font sizes (rem units)
    'font-xs': '0.75rem',
    'font-sm': '0.875rem',
    'font-md': '1rem',
    'font-lg': '1.25rem',
    'font-xl': '1.5rem',
    'font-2xl': '2rem',
}


# ==========================================================================
# Dark Theme
# ==========================================================================

THEME_DARK: Dict[str, str] = {
    # Primary colors (slightly adjusted for dark bg)
    'primary': '#60a5fa',       # Blue 400
    'secondary': '#94a3b8',     # Slate 400
    'success': '#4ade80',       # Green 400
    'danger': '#f87171',        # Red 400
    'warning': '#fbbf24',       # Amber 400
    'info': '#22d3ee',          # Cyan 400

    # Neutral colors (inverted for dark mode)
    'light': '#334155',         # Slate 700
    'dark': '#f8fafc',          # Slate 50
    'background': '#0f172a',    # Slate 900
    'text': '#f1f5f9',          # Slate 100
    'border': '#334155',        # Slate 700
    'muted': '#64748b',         # Slate 500

    # Extended colors
    'surface': '#1e293b',       # Slate 800
    'overlay': 'rgba(0,0,0,0.7)',
    'accent': '#a78bfa',        # Violet 400
    'focus': 'rgba(96,165,250,0.5)',  # Primary with alpha

    # UI elements (same as light, could be customized)
    'radius': '6px',
    'shadow': '0 1px 3px rgba(0,0,0,0.3)',

    # Font sizes (same as light)
    'font-xs': '0.75rem',
    'font-sm': '0.875rem',
    'font-md': '1rem',
    'font-lg': '1.25rem',
    'font-xl': '1.5rem',
    'font-2xl': '2rem',
}


# ==========================================================================
# High Contrast Theme (Accessibility)
# ==========================================================================

THEME_HIGH_CONTRAST: Dict[str, str] = {
    # Primary colors (high saturation)
    'primary': '#0066ff',       # Bright blue
    'secondary': '#595959',     # Dark gray
    'success': '#00aa00',       # Bright green
    'danger': '#dd0000',        # Bright red
    'warning': '#cc6600',       # Bright orange
    'info': '#0088cc',          # Bright cyan

    # Neutral colors (maximum contrast)
    'light': '#ffffff',         # Pure white
    'dark': '#000000',          # Pure black
    'background': '#ffffff',    # White
    'text': '#000000',          # Black
    'border': '#000000',        # Black border
    'muted': '#595959',         # Dark gray

    # Extended colors
    'surface': '#f0f0f0',       # Light gray
    'overlay': 'rgba(0,0,0,0.7)',
    'accent': '#6600cc',        # Purple
    'focus': 'rgba(0,102,255,0.5)',

    # UI elements (thicker borders, no shadows)
    'radius': '0px',            # Sharp corners for clarity
    'shadow': 'none',

    # Font sizes (slightly larger)
    'font-xs': '0.875rem',
    'font-sm': '1rem',
    'font-md': '1.125rem',
    'font-lg': '1.375rem',
    'font-xl': '1.625rem',
    'font-2xl': '2.25rem',
}


# ==========================================================================
# Sepia Theme (Reading/Paper)
# ==========================================================================

THEME_SEPIA: Dict[str, str] = {
    # Primary colors (warm tones)
    'primary': '#8b4513',       # Saddle brown
    'secondary': '#6b5344',     # Warm gray
    'success': '#5d8a4a',       # Olive green
    'danger': '#c24b3f',        # Brick red
    'warning': '#d4a03b',       # Golden
    'info': '#4a7a8a',          # Teal

    # Neutral colors (sepia tones)
    'light': '#f4ecd8',         # Cream
    'dark': '#3c2f2f',          # Dark brown
    'background': '#faf4e8',    # Warm white
    'text': '#3c2f2f',          # Dark brown
    'border': '#d4c5a9',        # Tan
    'muted': '#8b7355',         # Medium brown

    # Extended colors
    'surface': '#f0e6d2',       # Light cream
    'overlay': 'rgba(60,47,47,0.5)',
    'accent': '#9a5b4a',        # Terra cotta
    'focus': 'rgba(139,69,19,0.3)',

    # UI elements
    'radius': '4px',
    'shadow': '0 1px 3px rgba(60,47,47,0.1)',

    # Font sizes
    'font-xs': '0.75rem',
    'font-sm': '0.875rem',
    'font-md': '1rem',
    'font-lg': '1.25rem',
    'font-xl': '1.5rem',
    'font-2xl': '2rem',
}


# ==========================================================================
# Nord Theme (Popular dark theme)
# ==========================================================================

THEME_NORD: Dict[str, str] = {
    # Nord color palette
    'primary': '#88c0d0',       # Nord8 - Frost
    'secondary': '#81a1c1',     # Nord9 - Frost
    'success': '#a3be8c',       # Nord14 - Aurora
    'danger': '#bf616a',        # Nord11 - Aurora
    'warning': '#ebcb8b',       # Nord13 - Aurora
    'info': '#5e81ac',          # Nord10 - Frost

    # Neutral colors (Nord Polar Night)
    'light': '#4c566a',         # Nord3
    'dark': '#eceff4',          # Nord6 - Snow
    'background': '#2e3440',    # Nord0
    'text': '#eceff4',          # Nord6
    'border': '#4c566a',        # Nord3
    'muted': '#d8dee9',         # Nord4

    # Extended colors
    'surface': '#3b4252',       # Nord1
    'overlay': 'rgba(46,52,64,0.8)',
    'accent': '#b48ead',        # Nord15 - Aurora
    'focus': 'rgba(136,192,208,0.4)',

    # UI elements
    'radius': '4px',
    'shadow': '0 2px 8px rgba(0,0,0,0.3)',

    # Font sizes
    'font-xs': '0.75rem',
    'font-sm': '0.875rem',
    'font-md': '1rem',
    'font-lg': '1.25rem',
    'font-xl': '1.5rem',
    'font-2xl': '2rem',
}


# ==========================================================================
# Dracula Theme (Popular dark theme)
# ==========================================================================

THEME_DRACULA: Dict[str, str] = {
    # Dracula color palette
    'primary': '#bd93f9',       # Purple
    'secondary': '#6272a4',     # Comment
    'success': '#50fa7b',       # Green
    'danger': '#ff5555',        # Red
    'warning': '#ffb86c',       # Orange
    'info': '#8be9fd',          # Cyan

    # Neutral colors
    'light': '#44475a',         # Current Line
    'dark': '#f8f8f2',          # Foreground
    'background': '#282a36',    # Background
    'text': '#f8f8f2',          # Foreground
    'border': '#44475a',        # Current Line
    'muted': '#6272a4',         # Comment

    # Extended colors
    'surface': '#21222c',       # Darker background
    'overlay': 'rgba(40,42,54,0.9)',
    'accent': '#ff79c6',        # Pink
    'focus': 'rgba(189,147,249,0.4)',

    # UI elements
    'radius': '6px',
    'shadow': '0 2px 10px rgba(0,0,0,0.4)',

    # Font sizes
    'font-xs': '0.75rem',
    'font-sm': '0.875rem',
    'font-md': '1rem',
    'font-lg': '1.25rem',
    'font-xl': '1.5rem',
    'font-2xl': '2rem',
}


# ==========================================================================
# Theme Presets Registry
# ==========================================================================

THEME_PRESETS: Dict[str, Dict[str, str]] = {
    'light': THEME_LIGHT,
    'dark': THEME_DARK,
    'high-contrast': THEME_HIGH_CONTRAST,
    'sepia': THEME_SEPIA,
    'nord': THEME_NORD,
    'dracula': THEME_DRACULA,
}


def get_theme_preset(name: str) -> Optional[Dict[str, str]]:
    """Get a theme preset by name."""
    return THEME_PRESETS.get(name)


def get_theme_css(
    preset: str = 'light',
    overrides: Optional[Dict[str, str]] = None,
    auto_switch: bool = False
) -> str:
    """
    Generate CSS for a theme.

    Args:
        preset: Base theme preset ('light' or 'dark')
        overrides: Custom color overrides to apply on top of preset
        auto_switch: If True, adds media query for automatic dark/light switching

    Returns:
        CSS string with custom properties
    """
    base_theme = THEME_PRESETS.get(preset, THEME_LIGHT)

    # Merge overrides
    theme = dict(base_theme)
    if overrides:
        theme.update(overrides)

    # Generate CSS variables
    css_vars = _theme_to_css_vars(theme)

    if auto_switch:
        # Generate both light and dark with media query
        light_vars = _theme_to_css_vars(THEME_LIGHT)
        dark_vars = _theme_to_css_vars(THEME_DARK)

        # Apply overrides to both if provided
        if overrides:
            light_theme = dict(THEME_LIGHT)
            light_theme.update(overrides)
            light_vars = _theme_to_css_vars(light_theme)

            dark_theme = dict(THEME_DARK)
            dark_theme.update(overrides)
            dark_vars = _theme_to_css_vars(dark_theme)

        return f""":root {{
{light_vars}
}}

@media (prefers-color-scheme: dark) {{
  :root {{
{dark_vars}
  }}
}}

[data-theme="light"] {{
{light_vars}
}}

[data-theme="dark"] {{
{dark_vars}
}}
"""
    else:
        # Single theme
        return f""":root {{
{css_vars}
}}

[data-theme="{preset}"] {{
{css_vars}
}}
"""


def _theme_to_css_vars(theme: Dict[str, str]) -> str:
    """Convert theme dict to CSS variable declarations."""
    lines = []
    for key, value in theme.items():
        # Convert key to CSS variable name
        css_var = f"--q-{key}"
        lines.append(f"  {css_var}: {value};")
    return '\n'.join(lines)


# ==========================================================================
# Runtime Theme Switching JavaScript
# ==========================================================================

THEME_SWITCH_JS = """\
<script>
(function() {
  // Get initial theme from localStorage or default
  var stored = localStorage.getItem('quantum-theme');
  var prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  var initial = stored || (prefersDark ? 'dark' : 'light');
  document.documentElement.setAttribute('data-theme', initial);

  // Theme switching function
  window.__quantumSetTheme = function(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('quantum-theme', theme);
  };

  // Toggle between light and dark
  window.__quantumToggleTheme = function() {
    var current = document.documentElement.getAttribute('data-theme') || 'light';
    var next = current === 'light' ? 'dark' : 'light';
    window.__quantumSetTheme(next);
    return next;
  };

  // Get current theme
  window.__quantumGetTheme = function() {
    return document.documentElement.getAttribute('data-theme') || 'light';
  };

  // Listen for system preference changes (if auto-switch enabled)
  if (window.matchMedia) {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
      if (!localStorage.getItem('quantum-theme')) {
        document.documentElement.setAttribute('data-theme', e.matches ? 'dark' : 'light');
      }
    });
  }
})();
</script>
"""


def get_theme_switch_js() -> str:
    """Get the JavaScript for runtime theme switching."""
    return THEME_SWITCH_JS
