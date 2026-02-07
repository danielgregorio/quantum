"""
UI Engine - React Native Mobile Templates

Provides templates for React Native mobile apps:
  - REACT_NATIVE_APP_TEMPLATE: Complete App.js template
  - COMPONENT_TEMPLATE: Individual component template
  - STYLE_HELPERS: Helper functions for StyleSheet generation
  - IMPORTS_MAP: Mapping of UI components to RN imports
"""

from typing import Dict, Set


# ==========================================================================
# React Native Component Imports
# ==========================================================================

# Map Quantum UI components to React Native imports
RN_IMPORTS = {
    'View': 'react-native',
    'Text': 'react-native',
    'TouchableOpacity': 'react-native',
    'TextInput': 'react-native',
    'ScrollView': 'react-native',
    'FlatList': 'react-native',
    'Image': 'react-native',
    'Switch': 'react-native',
    'ActivityIndicator': 'react-native',
    'Button': 'react-native',
    'SafeAreaView': 'react-native',
    'StatusBar': 'react-native',
    'StyleSheet': 'react-native',
    'Pressable': 'react-native',
    'Modal': 'react-native',
}


def generate_imports(components_used: Set[str]) -> str:
    """Generate React Native import statements.

    Args:
        components_used: Set of RN component names used in the app.

    Returns:
        Import statements as string.
    """
    # Always include core imports
    core_imports = {'View', 'Text', 'StyleSheet', 'SafeAreaView', 'StatusBar'}
    all_components = core_imports | components_used

    # Group by source
    rn_components = sorted([c for c in all_components if c in RN_IMPORTS])

    imports = [
        "import React, { useState, useCallback } from 'react';",
        f"import {{ {', '.join(rn_components)} }} from 'react-native';",
    ]

    return '\n'.join(imports)


# ==========================================================================
# JavaScript Code Builder
# ==========================================================================

class JsBuilder:
    """Builds well-formatted JavaScript/JSX with proper indentation."""

    def __init__(self, indent_size: int = 2):
        self._lines: list = []
        self._indent: int = 0
        self._indent_size: int = indent_size

    @property
    def _pad(self) -> str:
        return ' ' * (self._indent * self._indent_size)

    def line(self, code: str = '') -> 'JsBuilder':
        self._lines.append(f"{self._pad}{code}" if code else '')
        return self

    def raw(self, code: str) -> 'JsBuilder':
        for ln in code.split('\n'):
            self._lines.append(f"{self._pad}{ln}")
        return self

    def blank(self) -> 'JsBuilder':
        self._lines.append('')
        return self

    def indent(self) -> 'JsBuilder':
        self._indent += 1
        return self

    def dedent(self) -> 'JsBuilder':
        self._indent = max(0, self._indent - 1)
        return self

    def comment(self, text: str) -> 'JsBuilder':
        self.line(f'// {text}')
        return self

    def jsx_open(self, tag: str, attrs: Dict[str, str] = None,
                 self_closing: bool = False) -> 'JsBuilder':
        """Open a JSX tag with optional attributes."""
        attr_str = ''
        if attrs:
            parts = []
            for k, v in attrs.items():
                if v is True:
                    parts.append(k)
                elif v is not None and v is not False:
                    # Check if value is already a JSX expression (starts with {)
                    if isinstance(v, str) and v.startswith('{') and v.endswith('}'):
                        # Already wrapped in braces, use as-is
                        parts.append(f'{k}={v}')
                    elif isinstance(v, str) and (v.startswith('styles.') or v.startswith('[')):
                        # Style reference or array - wrap in braces
                        parts.append(f'{k}={{{v}}}')
                    else:
                        parts.append(f'{k}="{v}"')
            if parts:
                attr_str = ' ' + ' '.join(parts)

        if self_closing:
            self.line(f'<{tag}{attr_str} />')
        else:
            self.line(f'<{tag}{attr_str}>')
        return self

    def jsx_close(self, tag: str) -> 'JsBuilder':
        self.line(f'</{tag}>')
        return self

    def jsx_text(self, content: str) -> 'JsBuilder':
        """Add text content, wrapping in Text component if needed."""
        self.line(content)
        return self

    def build(self) -> str:
        return '\n'.join(self._lines)


# ==========================================================================
# StyleSheet Helpers
# ==========================================================================

def js_string(s: str) -> str:
    """Escape string for JavaScript."""
    if s is None:
        return "''"
    escaped = s.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
    return f"'{escaped}'"


def js_number(s: str) -> str:
    """Convert to JS number, returning string if not a number."""
    if s is None:
        return 'undefined'
    try:
        # Try integer
        return str(int(s))
    except ValueError:
        try:
            # Try float
            return str(float(s))
        except ValueError:
            return js_string(s)


# ==========================================================================
# Spacing/Sizing Token Conversion for RN
# ==========================================================================

SPACING_RN = {
    'none': '0',
    'xs': '4',
    'sm': '8',
    'md': '16',
    'lg': '24',
    'xl': '32',
    '2xl': '48',
}

SIZE_RN = {
    'auto': "'auto'",
    'fill': "'100%'",
    'full': "'100%'",
    '1/2': "'50%'",
    '1/3': "'33.33%'",
    '1/4': "'25%'",
    '2/3': "'66.66%'",
    '3/4': "'75%'",
}

# Semantic colors for RN
COLOR_RN = {
    'primary': "'#3b82f6'",
    'secondary': "'#64748b'",
    'success': "'#22c55e'",
    'danger': "'#ef4444'",
    'warning': "'#f59e0b'",
    'info': "'#06b6d4'",
    'light': "'#f8fafc'",
    'dark': "'#1e293b'",
    'text': "'#1e293b'",
    'background': "'#ffffff'",
    'border': "'#e2e8f0'",
    'muted': "'#64748b'",
}

FONT_SIZE_RN = {
    'xs': '12',
    'sm': '14',
    'md': '16',
    'lg': '20',
    'xl': '24',
    '2xl': '32',
}


def rn_spacing(value: str) -> str:
    """Convert spacing token to RN value."""
    if not value:
        return '0'
    value_lower = value.lower().strip()
    if value_lower in SPACING_RN:
        return SPACING_RN[value_lower]
    # Raw value
    if value.endswith('px'):
        return value[:-2]
    try:
        int(value)
        return value
    except ValueError:
        return '0'


def rn_size(value: str) -> str:
    """Convert size token to RN value."""
    if not value:
        return 'undefined'
    value_lower = value.lower().strip()
    if value_lower in SIZE_RN:
        return SIZE_RN[value_lower]
    # Raw value
    if value.endswith('%'):
        return f"'{value}'"
    if value.endswith('px'):
        return value[:-2]
    try:
        int(value)
        return value
    except ValueError:
        return 'undefined'


def rn_color(value: str) -> str:
    """Convert color token to RN value."""
    if not value:
        return "'#000000'"
    value_lower = value.lower().strip()
    if value_lower in COLOR_RN:
        return COLOR_RN[value_lower]
    # Raw hex or color name
    return f"'{value}'"


def rn_font_size(value: str) -> str:
    """Convert font size token to RN value."""
    if not value:
        return '16'
    value_lower = value.lower().strip()
    if value_lower in FONT_SIZE_RN:
        return FONT_SIZE_RN[value_lower]
    # Raw value
    if value.endswith('px'):
        return value[:-2]
    try:
        int(value)
        return value
    except ValueError:
        return '16'


def rn_align(value: str) -> str:
    """Convert align token to RN alignItems value."""
    mapping = {
        'start': "'flex-start'",
        'center': "'center'",
        'end': "'flex-end'",
        'stretch': "'stretch'",
    }
    return mapping.get(value, "'stretch'")


def rn_justify(value: str) -> str:
    """Convert justify token to RN justifyContent value."""
    mapping = {
        'start': "'flex-start'",
        'center': "'center'",
        'end': "'flex-end'",
        'between': "'space-between'",
        'around': "'space-around'",
    }
    return mapping.get(value, "'flex-start'")


# ==========================================================================
# App Template
# ==========================================================================

REACT_NATIVE_APP_TEMPLATE = """\
/**
 * Quantum UI - React Native Mobile App
 *
 * Generated by the Quantum UI Engine.
 * This file can be used as App.js in a React Native project.
 */

{imports}

{state_declarations}

{function_declarations}

export default function App() {{
  return (
    <SafeAreaView style={{styles.safeArea}}>
      <StatusBar barStyle="dark-content" />
{jsx_content}
    </SafeAreaView>
  );
}}

const styles = StyleSheet.create({{
  safeArea: {{
    flex: 1,
    backgroundColor: '#ffffff',
  }},
{styles_content}
}});
"""


# ==========================================================================
# Component Templates
# ==========================================================================

# Base styles for common components
BASE_STYLES = {
    'container': """\
  container: {
    flex: 1,
    backgroundColor: '#ffffff',
  },""",

    'hbox': """\
  hbox: {
    flexDirection: 'row',
    alignItems: 'center',
  },""",

    'vbox': """\
  vbox: {
    flexDirection: 'column',
  },""",

    'panel': """\
  panel: {
    backgroundColor: '#ffffff',
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
    elevation: 2,
  },
  panelTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 12,
    color: '#1e293b',
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0',
    paddingBottom: 8,
  },""",

    'button': """\
  button: {
    backgroundColor: '#3b82f6',
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 6,
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonText: {
    color: '#ffffff',
    fontWeight: '500',
    fontSize: 16,
  },
  buttonSecondary: {
    backgroundColor: '#64748b',
  },
  buttonDanger: {
    backgroundColor: '#ef4444',
  },
  buttonSuccess: {
    backgroundColor: '#22c55e',
  },
  buttonDisabled: {
    opacity: 0.5,
  },""",

    'input': """\
  input: {
    borderWidth: 1,
    borderColor: '#e2e8f0',
    borderRadius: 6,
    paddingVertical: 8,
    paddingHorizontal: 12,
    fontSize: 16,
    backgroundColor: '#ffffff',
  },
  inputFocused: {
    borderColor: '#3b82f6',
  },""",

    'text': """\
  text: {
    fontSize: 16,
    color: '#1e293b',
  },
  textBold: {
    fontWeight: 'bold',
  },""",

    'header': """\
  header: {
    backgroundColor: '#1e293b',
    paddingVertical: 12,
    paddingHorizontal: 16,
  },
  headerText: {
    color: '#ffffff',
    fontSize: 18,
    fontWeight: '600',
  },""",

    'footer': """\
  footer: {
    backgroundColor: '#f8fafc',
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderTopWidth: 1,
    borderTopColor: '#e2e8f0',
  },
  footerText: {
    color: '#64748b',
    fontSize: 14,
  },""",

    'badge': """\
  badge: {
    paddingVertical: 2,
    paddingHorizontal: 8,
    borderRadius: 12,
    backgroundColor: '#f8fafc',
  },
  badgeText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#1e293b',
  },
  badgePrimary: {
    backgroundColor: '#3b82f6',
  },
  badgeSuccess: {
    backgroundColor: '#22c55e',
  },
  badgeDanger: {
    backgroundColor: '#ef4444',
  },
  badgeWarning: {
    backgroundColor: '#f59e0b',
  },
  badgePrimaryText: {
    color: '#ffffff',
  },""",

    'loading': """\
  loading: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  loadingText: {
    color: '#64748b',
  },""",

    'progress': """\
  progressContainer: {
    height: 8,
    backgroundColor: '#f8fafc',
    borderRadius: 4,
    overflow: 'hidden',
  },
  progressBar: {
    height: '100%',
    backgroundColor: '#3b82f6',
    borderRadius: 4,
  },""",

    'switch': """\
  switchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },""",

    'image': """\
  image: {
    width: '100%',
    resizeMode: 'contain',
  },""",

    'list': """\
  listItem: {
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0',
  },""",

    'form': """\
  form: {
    gap: 16,
  },
  formItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  formLabel: {
    minWidth: 100,
    fontWeight: '500',
    color: '#1e293b',
  },""",

    'tab': """\
  tabHeader: {
    flexDirection: 'row',
    borderBottomWidth: 2,
    borderBottomColor: '#e2e8f0',
  },
  tabButton: {
    paddingVertical: 10,
    paddingHorizontal: 20,
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
    marginBottom: -2,
  },
  tabButtonActive: {
    borderBottomColor: '#3b82f6',
  },
  tabButtonText: {
    color: '#64748b',
    fontWeight: '500',
  },
  tabButtonTextActive: {
    color: '#3b82f6',
  },
  tabContent: {
    padding: 16,
  },""",

    'select': """\
  select: {
    borderWidth: 1,
    borderColor: '#e2e8f0',
    borderRadius: 6,
    paddingVertical: 8,
    paddingHorizontal: 12,
    backgroundColor: '#ffffff',
  },""",

    'scrollbox': """\
  scrollbox: {
    flex: 1,
  },""",

    'rule': """\
  rule: {
    height: 1,
    backgroundColor: '#e2e8f0',
    marginVertical: 8,
  },""",

    'link': """\
  link: {
    color: '#3b82f6',
  },""",

    'checkbox': """\
  checkboxRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  checkbox: {
    width: 20,
    height: 20,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    borderRadius: 4,
    alignItems: 'center',
    justifyContent: 'center',
  },
  checkboxChecked: {
    backgroundColor: '#3b82f6',
    borderColor: '#3b82f6',
  },
  checkboxLabel: {
    fontSize: 16,
    color: '#1e293b',
  },""",

    'accordion': """\
  section: {
    borderWidth: 1,
    borderColor: '#e2e8f0',
    borderRadius: 6,
    marginBottom: 4,
    overflow: 'hidden',
  },
  sectionHeader: {
    padding: 12,
    backgroundColor: '#f8fafc',
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0',
  },
  sectionHeaderText: {
    fontWeight: '500',
    color: '#1e293b',
  },
  sectionContent: {
    padding: 12,
  },""",

    'spacer': """\
  spacer: {
    flex: 1,
  },""",

    'menu': """\
  menu: {
    flexDirection: 'row',
    gap: 4,
  },
  menuItem: {
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 6,
  },
  menuItemText: {
    color: '#1e293b',
  },""",

    'card': """\
  card: {
    backgroundColor: '#ffffff',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
    overflow: 'hidden',
  },
  cardHeader: {
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e2e8f0',
  },
  cardBody: {
    padding: 16,
  },
  cardFooter: {
    padding: 16,
    backgroundColor: '#f8fafc',
    borderTopWidth: 1,
    borderTopColor: '#e2e8f0',
  },""",

    'modal': """\
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContent: {
    backgroundColor: '#ffffff',
    borderRadius: 8,
    padding: 20,
    width: '90%',
    maxHeight: '80%',
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 16,
    color: '#1e293b',
  },
  modalClose: {
    position: 'absolute',
    top: 12,
    right: 12,
    padding: 8,
  },""",

    'alert': """\
  alert: {
    padding: 16,
    borderRadius: 6,
    borderWidth: 1,
  },
  alertInfo: {
    backgroundColor: '#eff6ff',
    borderColor: '#3b82f6',
  },
  alertSuccess: {
    backgroundColor: '#f0fdf4',
    borderColor: '#22c55e',
  },
  alertWarning: {
    backgroundColor: '#fffbeb',
    borderColor: '#f59e0b',
  },
  alertDanger: {
    backgroundColor: '#fef2f2',
    borderColor: '#ef4444',
  },
  alertTitle: {
    fontWeight: '600',
    marginBottom: 4,
    color: '#1e293b',
  },
  alertText: {
    color: '#1e293b',
  },""",

    'avatar': """\
  avatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#3b82f6',
    justifyContent: 'center',
    alignItems: 'center',
  },
  avatarText: {
    color: '#ffffff',
    fontWeight: '600',
  },""",

    'dropdown': """\
  dropdownTrigger: {
    paddingVertical: 10,
    paddingHorizontal: 16,
    backgroundColor: '#f8fafc',
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  dropdownMenu: {
    position: 'absolute',
    top: '100%',
    left: 0,
    right: 0,
    backgroundColor: '#ffffff',
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#e2e8f0',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
    zIndex: 100,
  },""",

    'toast': """\
  toastContainer: {
    position: 'absolute',
    top: 50,
    right: 16,
    zIndex: 1000,
  },
  toast: {
    padding: 16,
    borderRadius: 8,
    marginBottom: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  toastInfo: {
    backgroundColor: '#3b82f6',
  },
  toastSuccess: {
    backgroundColor: '#22c55e',
  },
  toastWarning: {
    backgroundColor: '#f59e0b',
  },
  toastDanger: {
    backgroundColor: '#ef4444',
  },
  toastTitle: {
    fontWeight: '600',
    color: '#ffffff',
    marginBottom: 4,
  },
  toastText: {
    color: '#ffffff',
  },""",

    'carousel': """\
  carousel: {
    flexDirection: 'row',
  },
  slide: {
    width: '100%',
  },""",

    'stepper': """\
  stepItem: {
    alignItems: 'center',
    flex: 1,
  },
  stepCircle: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#e2e8f0',
    justifyContent: 'center',
    alignItems: 'center',
  },
  stepCircleActive: {
    backgroundColor: '#3b82f6',
  },
  stepCircleComplete: {
    backgroundColor: '#22c55e',
  },
  stepNumber: {
    color: '#ffffff',
    fontWeight: '600',
  },
  stepLabel: {
    marginTop: 8,
    fontSize: 12,
    color: '#64748b',
  },
  stepContent: {
    padding: 16,
  },""",

    'calendar': """\
  calendar: {
    padding: 16,
    backgroundColor: '#ffffff',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e2e8f0',
  },
  calendarPlaceholder: {
    color: '#64748b',
    textAlign: 'center',
  },
  datePickerContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },""",
}


def get_base_styles(styles_used: Set[str]) -> str:
    """Generate StyleSheet entries for used component types.

    Args:
        styles_used: Set of style keys that were used.

    Returns:
        StyleSheet entries as string.
    """
    entries = []
    for style_key in sorted(styles_used):
        if style_key in BASE_STYLES:
            entries.append(BASE_STYLES[style_key])
    return '\n'.join(entries)
