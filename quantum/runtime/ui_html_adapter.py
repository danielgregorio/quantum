"""
UI Engine - HTML/CSS Adapter

Transforms UI AST nodes into a standalone HTML/CSS page.
Uses the design tokens system for normalized styling across targets.

Desktop Mode:
    When desktop_mode=True, the adapter transforms events for pywebview:
    - on-click="fn" -> onclick="__quantumCall('fn')"
    - on-submit="fn" -> onsubmit with form data collection
    - bind="var" -> oninput with two-way binding
    - {var} in text -> <span id="..."> for reactive updates
"""

import calendar as _calendar
import re
from datetime import date as _date
from typing import Dict, List, Optional, Set, Tuple

from quantum.core.ast_nodes import QuantumNode
from quantum.core.features.conditionals.src.ast_node import IfNode
from quantum.core.features.loops.src.ast_node import LoopNode
from quantum.core.features.state_management.src.ast_node import SetNode
from quantum.core.features.ui_engine.src.ast_nodes import (
    UIWindowNode, UIHBoxNode, UIVBoxNode, UIPanelNode,
    UITabPanelNode, UITabNode, UIGridNode, UIAccordionNode,
    UISectionNode, UIDividedBoxNode, UIFormNode, UIFormItemNode,
    UISpacerNode, UIScrollBoxNode,
    UITextNode, UIButtonNode, UIInputNode, UICheckboxNode,
    UIRadioNode, UISwitchNode, UISelectNode, UITableNode,
    UIColumnNode, UIListNode, UIItemNode, UIImageNode,
    UILinkNode, UIProgressNode, UITreeNode, UIMenuNode,
    UIOptionNode, UILogNode, UIMarkdownNode, UIHeaderNode,
    UIFooterNode, UIRuleNode, UILoadingNode, UIBadgeNode,
    UILayoutMixin, UIValidatorNode, UIAnimateNode, UIAnimationMixin,
    # Component Library nodes
    UICardNode, UICardHeaderNode, UICardBodyNode, UICardFooterNode,
    UIModalNode, UIChartNode, UIAvatarNode, UITooltipNode,
    UIDropdownNode, UIAlertNode, UIBreadcrumbNode, UIBreadcrumbItemNode,
    UIPaginationNode, UISkeletonNode,
    # Toast / carousel / stepper / calendar nodes
    UIToastNode, UIToastContainerNode,
    UICarouselNode, UISlideNode,
    UIStepperNode, UIStepNode,
    UICalendarNode, UIDatePickerNode,
)
from quantum.runtime.ui_html_templates import (
    HtmlBuilder, HTML_TEMPLATE, CSS_RESET, CSS_THEME, TAB_JS,
    VALIDATION_JS, VALIDATION_CSS,
    PERSISTENCE_JS, generate_persistence_registration,
    CSS_ANIMATIONS, ANIMATION_JS,
    TOAST_JS, CAROUSEL_JS, STEPPER_JS, CALENDAR_JS,
)
from quantum.runtime.ui_tokens import TokenConverter
# Optional theming imports (may not be available)
try:
    from quantum.core.features.theming.src import (
        UIThemeNode,
        get_theme_css,
        get_theme_switch_js,
        THEME_PRESETS,
    )
    HAS_THEMING = True
except ImportError:
    HAS_THEMING = False
    UIThemeNode = None
    get_theme_css = None
    get_theme_switch_js = None
    THEME_PRESETS = None


# ==========================================================================
# Calendar labels (kept in sync with CALENDAR_JS in ui_html_templates.py)
# ==========================================================================

MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June',
               'July', 'August', 'September', 'October', 'November', 'December']
DAY_NAMES = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa']

# Default toast icons per variant (same glyphs used by TOAST_JS)
TOAST_ICONS = {
    'info': '&#9432;',
    'success': '&#10003;',
    'warning': '&#9888;',
    'danger': '&#10007;',
}


# ==========================================================================
# Date picker runtime (input + calendar popup)
# ==========================================================================

DATE_PICKER_JS = """\
<script>
// Quantum UI Date Picker (text input + q-calendar popup)
window.__quantumDatePicker = (function() {
    'use strict';

    var pickers = {};

    function root(id) { return document.getElementById(id); }
    function dropdown(id) { return document.getElementById(id + '-dropdown'); }
    function inputOf(id) { return document.getElementById(id + '-input'); }
    function valueOf(id) { return document.getElementById(id + '-value'); }

    function format(iso, pattern) {
        if (!iso) return '';
        var parts = String(iso).split('-');
        if (parts.length !== 3) return String(iso);
        return (pattern || 'YYYY-MM-DD')
            .replace('YYYY', parts[0])
            .replace('YY', parts[0].slice(2))
            .replace('MM', parts[1])
            .replace('DD', parts[2]);
    }

    function open(id) {
        closeAll(id);
        var d = dropdown(id);
        if (d) d.classList.add('open');
    }

    function close(id) {
        var d = dropdown(id);
        if (d) d.classList.remove('open');
    }

    function toggle(id) {
        var d = dropdown(id);
        if (!d) return;
        if (d.classList.contains('open')) close(id); else open(id);
    }

    function closeAll(except) {
        Object.keys(pickers).forEach(function(pid) {
            if (pid !== except) close(pid);
        });
    }

    function setValue(id, iso) {
        var opts = pickers[id] || {};
        var input = inputOf(id);
        var hidden = valueOf(id);
        if (input) input.value = format(iso, opts.format);
        if (hidden) hidden.value = iso || '';
        close(id);
        if (opts.onChange) opts.onChange(iso || '');
    }

    function clear(id) {
        setValue(id, '');
    }

    function getValue(id) {
        var hidden = valueOf(id);
        return hidden ? hidden.value : '';
    }

    function register(id, options) {
        options = options || {};
        pickers[id] = options;
        if (options.disabled) return;
        var input = inputOf(id);
        if (input) {
            input.addEventListener('click', function() { toggle(id); });
            input.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(id); }
                if (e.key === 'Escape') close(id);
            });
        }
    }

    document.addEventListener('click', function(e) {
        Object.keys(pickers).forEach(function(pid) {
            var el = root(pid);
            if (el && !el.contains(e.target)) close(pid);
        });
    });

    return {
        register: register,
        open: open,
        close: close,
        toggle: toggle,
        clear: clear,
        setValue: setValue,
        getValue: getValue,
        format: format
    };
})();
</script>
"""


# ==========================================================================
# Week numbers for ui:calendar (re-applied after every calendar re-render)
# ==========================================================================

CALENDAR_WEEKS_JS = """\
<script>
// Quantum UI - week number column for calendars with show-week-numbers
window.__quantumCalendarWeeks = (function() {
    'use strict';

    function isoWeek(d) {
        var t = new Date(d.getFullYear(), d.getMonth(), d.getDate());
        t.setDate(t.getDate() + 3 - ((t.getDay() + 6) % 7));
        var firstThursday = new Date(t.getFullYear(), 0, 4);
        firstThursday.setDate(firstThursday.getDate() + 3 - ((firstThursday.getDay() + 6) % 7));
        return 1 + Math.round((t - firstThursday) / 604800000);
    }

    function apply(id) {
        var state = window.__quantumCalendar && __quantumCalendar.get(id);
        var cal = document.getElementById(id);
        if (!state || !cal) return;
        var grid = cal.querySelector('.q-calendar-grid');
        if (!grid) return;
        var days = grid.querySelectorAll('.q-calendar-day:not(.week-number)');
        if (!days.length) return;

        var first = new Date(state.viewYear, state.viewMonth, 1);
        var offset = (first.getDay() - (state.firstDayOfWeek || 0) + 7) % 7;
        for (var i = 0; i < days.length; i += 7) {
            var rowDate = new Date(state.viewYear, state.viewMonth, 1 - offset + i);
            var cell = document.createElement('div');
            cell.className = 'q-calendar-day week-number';
            cell.textContent = isoWeek(rowDate);
            grid.insertBefore(cell, days[i]);
        }
    }

    return { apply: apply };
})();
</script>
"""


# ==========================================================================
# Visibility bindings for declarative toasts (data-q-show)
# ==========================================================================

SHOW_BINDING_JS = """\
<script>
// Quantum UI - toggles elements carrying data-q-show when their state changes
(function() {
    'use strict';

    function apply(name, value) {
        var visible = !(value === undefined || value === null || value === false ||
                        value === '' || value === 0 || value === 'false');
        document.querySelectorAll('[data-q-show="' + name + '"]').forEach(function(el) {
            el.style.display = visible ? '' : 'none';
        });
    }

    window.__quantumShowBinding = apply;

    document.addEventListener('DOMContentLoaded', function() {
        var previous = window.__quantumStateUpdate;
        window.__quantumStateUpdate = function(name, value) {
            if (previous) previous(name, value);
            apply(name, value);
        };
        var state = window.__quantumState || {};
        Object.keys(state).forEach(function(key) { apply(key, state[key]); });
    });
})();
</script>
"""


def completed_step_indices(steps, current: int) -> List[int]:
    """Quais passos de um ui:stepper contam como concluidos.

    Uma unica autoridade, de proposito. Esta regra vivia so aqui, e a ponte
    do adapter desktop tinha a SUA versao — `list(range(current)) if linear
    else []`. As duas discordavam de dois jeitos:

    - `linear` nao tem nada a ver com isso. Num stepper nao-linear a ponte
      emitia lista vazia e APAGAVA, no boot, as marcas que este arquivo tinha
      desenhado corretamente. O usuario via o progresso sumir.
    - `completed` e tri-state: nao setado (None), "true" e "false". A ponte
      colapsava None e "false" no mesmo valor, entao um passo marcado
      explicitamente como `completed="false"` antes do atual ganhava a marca
      de volta.

    A regra: o atributo explicito vence; sem atributo, um passo esta
    concluido se esta atras do atual.
    """
    indices: List[int] = []
    for i, step in enumerate(steps):
        explicito = getattr(step, 'completed', None)
        if explicito is not None:
            # Mesma lista de permissao de UIHtmlAdapter._as_bool. Uma lista de
            # NEGACAO trataria `completed="talvez"` como concluido, o oposto
            # do que este arquivo sempre fez.
            if explicito is True or (
                    not isinstance(explicito, bool)
                    and str(explicito).strip().lower() in ('true', '1', 'yes', 'on')):
                indices.append(i)
        elif i < current:
            indices.append(i)
    return indices


class UIHtmlAdapter:
    """Generates HTML/CSS from UI AST nodes."""

    def __init__(self, desktop_mode: bool = False):
        self._tab_counter = 0
        self._has_tabs = False
        self._has_validation = False  # Track if we have forms with validation
        self._has_persistence = False  # Track if we have persisted state
        self._has_animations = False  # Track if we have animations
        self._tokens = TokenConverter('html')
        self._features_used: Set[str] = set()  # Track features for compatibility

        # Desktop mode: enables event transformation and binding tracking
        self._desktop_mode = desktop_mode

        # State persistence tracking
        self._persisted_vars: List[Dict] = []  # List of persisted variable configs
        self._binding_counter = 0
        self._bindings: List[Tuple[str, str, str]] = []  # (element_id, var_name, bind_type)

        # Form validation tracking
        self._form_counter = 0
        self._form_validators: Dict[str, List[UIValidatorNode]] = {}  # form_id -> validators

        # Animation tracking
        self._animate_counter = 0

        # Toast / carousel / stepper / calendar tracking
        self._has_toast = False
        self._has_carousel = False
        self._has_stepper = False
        self._has_calendar = False
        self._has_date_picker = False
        self._has_calendar_weeks = False
        self._has_show_bindings = False
        self._toast_counter = 0
        self._toast_container_counter = 0
        self._carousel_counter = 0
        self._stepper_counter = 0
        self._calendar_counter = 0
        self._date_picker_counter = 0

        # Inline init statements executed on DOMContentLoaded
        self._component_inits: List[str] = []
        # Extra CSS rules emitted for specific component instances
        self._extra_css: List[str] = []

        # Theme configuration
        self._theme: Optional[UIThemeNode] = None

    def generate(self, windows: List[QuantumNode], ui_children: List[QuantumNode],
                 title: str = "Quantum UI",
                 theme: Optional[UIThemeNode] = None) -> str:
        """Generate complete HTML page from UI AST.

        Args:
            windows: List of UIWindowNode instances
            ui_children: List of top-level UI nodes
            title: Page title
            theme: Optional UIThemeNode for theme configuration
        """
        # Store theme for reference
        self._theme = theme

        body_builder = HtmlBuilder()

        # Render windows
        for window in windows:
            self._render_node(window, body_builder)

        # Render top-level children (outside windows)
        for child in ui_children:
            self._render_node(child, body_builder)

        body_html = body_builder.build()

        # Assemble CSS
        css = CSS_RESET + '\n'

        # Add theme CSS (replaces or augments CSS_THEME)
        if HAS_THEMING and theme and get_theme_css:
            preset = theme.preset or 'light'
            overrides = theme.get_color_overrides() if hasattr(theme, 'get_color_overrides') else {}
            auto_switch = getattr(theme, 'auto_switch', False)
            theme_css = get_theme_css(preset, overrides, auto_switch)
            css += theme_css + '\n'
        else:
            css += CSS_THEME + '\n'

        if self._has_validation:
            css += VALIDATION_CSS + '\n'
        if self._has_animations:
            css += CSS_ANIMATIONS + '\n'
        if self._extra_css:
            css += '\n'.join(self._extra_css) + '\n'

        # Assemble JS
        js = ''

        # Add theme switching JS if we have a theme
        if HAS_THEMING and theme and get_theme_switch_js:
            js += get_theme_switch_js() + '\n'

        if self._has_tabs:
            js += TAB_JS + '\n'
        if self._has_validation:
            js += VALIDATION_JS + '\n'
            # Add form-specific validators
            js += self._generate_validators_script() + '\n'

        # Add animation JS if needed
        if self._has_animations:
            js += ANIMATION_JS + '\n'

        # Component runtimes (toast, carousel, stepper, calendar, date picker)
        if self._has_toast:
            js += self._emit_runtime(TOAST_JS) + '\n'
        if self._has_carousel:
            js += self._emit_runtime(CAROUSEL_JS) + '\n'
        if self._has_stepper:
            js += self._emit_runtime(STEPPER_JS) + '\n'
        if self._has_calendar or self._has_date_picker:
            js += self._emit_runtime(CALENDAR_JS) + '\n'
        if self._has_calendar_weeks:
            js += CALENDAR_WEEKS_JS + '\n'
        if self._has_date_picker:
            js += DATE_PICKER_JS + '\n'
        if self._has_show_bindings:
            js += SHOW_BINDING_JS + '\n'
        if self._component_inits:
            js += self._generate_component_init_script() + '\n'

        # Add state persistence JS if needed
        if self._has_persistence and self._persisted_vars:
            js += PERSISTENCE_JS + '\n'
            js += generate_persistence_registration(self._persisted_vars) + '\n'

        # In desktop mode, append binding registration script
        if self._desktop_mode and self._bindings:
            js += self._generate_binding_script() + '\n'

        return HTML_TEMPLATE.format(
            title=title,
            css=css,
            body=body_html,
            js=js,
        )

    def get_bindings(self) -> List[Tuple[str, str, str]]:
        """Return the list of bindings for external use (desktop adapter)."""
        return self._bindings.copy()

    def _generate_binding_script(self) -> str:
        """Generate JS to register all bindings on DOMContentLoaded."""
        if not self._bindings:
            return ''

        lines = ['<script>', 'document.addEventListener("DOMContentLoaded", function() {']
        for bind_id, var_name, bind_type in self._bindings:
            lines.append(f"  __quantumBind('{bind_id}', '{var_name}', '{bind_type}');")
        lines.append('});')
        lines.append('</script>')
        return '\n'.join(lines)

    def _generate_validators_script(self) -> str:
        """Generate JS to register custom validators for each form."""
        if not self._form_validators:
            return ''

        lines = ['<script>', 'document.addEventListener("DOMContentLoaded", function() {']

        for form_id, validators in self._form_validators.items():
            for validator in validators:
                validator_obj = self._validator_to_js_object(validator)
                lines.append(f"  __qValidation.registerValidator('{form_id}', {validator_obj});")

        lines.append('});')
        lines.append('</script>')
        return '\n'.join(lines)

    def _emit_runtime(self, source: str) -> str:
        """Emit a shared JS runtime from ui_html_templates.

        Isto consertava o JS na SAIDA com um regex, porque TOAST_JS e
        CALENDAR_JS viviam em strings triplas nao-raw: o Python comia as
        barras que escapavam aspas dentro de literais JS aninhados, e a
        pagina recebia `dismiss('' + id + '')` — erro de sintaxe que derrubava
        o modulo inteiro no browser.

        Consertar a saida deixava a causa de pe: o proximo runtime escrito do
        mesmo jeito voltaria a quebrar, em silencio. As strings viraram raw na
        fonte, entao aqui nao ha mais o que reparar.
        """
        return source

    def _generate_component_init_script(self) -> str:
        """Generate the DOMContentLoaded script that boots interactive components.

        Every component gets its own listener: a failing user callback in one
        component must not stop the remaining ones from being initialised.
        """
        if not self._component_inits:
            return ''

        lines = ['<script>']
        for snippet in self._component_inits:
            lines.append('document.addEventListener("DOMContentLoaded", function() {')
            for raw in snippet.split('\n'):
                lines.append(('  ' + raw) if raw else '')
            lines.append('});')
        lines.append('</script>')
        return '\n'.join(lines)

    def _validator_to_js_object(self, validator: UIValidatorNode) -> str:
        """Convert a UIValidatorNode to a JavaScript object literal."""
        parts = []
        parts.append(f"name: '{validator.name}'")

        if validator.field:
            parts.append(f"field: '{validator.field}'")
        if validator.rule_type:
            parts.append(f"type: '{validator.rule_type}'")
        if validator.pattern:
            # Escape special characters for JS string
            escaped_pattern = validator.pattern.replace('\\', '\\\\').replace("'", "\\'")
            parts.append(f"pattern: '{escaped_pattern}'")
        if validator.match:
            parts.append(f"match: '{validator.match}'")
        if validator.min:
            parts.append(f"min: '{validator.min}'")
        if validator.max:
            parts.append(f"max: '{validator.max}'")
        if validator.minlength is not None:
            parts.append(f"minlength: {validator.minlength}")
        if validator.maxlength is not None:
            parts.append(f"maxlength: {validator.maxlength}")
        if validator.expression:
            # Custom JS expression - wrap in function
            parts.append(f"expression: function(value, form) {{ return {validator.expression}; }}")
        if validator.message:
            escaped_msg = validator.message.replace("'", "\\'")
            parts.append(f"message: '{escaped_msg}'")
        if validator.trigger:
            parts.append(f"trigger: '{validator.trigger}'")

        return '{' + ', '.join(parts) + '}'

    # ------------------------------------------------------------------
    # Layout style helper
    # ------------------------------------------------------------------

    def _layout_style(self, node) -> str:
        """Build inline CSS from layout attributes."""
        parts = []
        if hasattr(node, 'gap') and node.gap:
            self._features_used.add('gap')
            parts.append(f"gap: {self._css_size(node.gap)}")
        if hasattr(node, 'padding') and node.padding:
            parts.append(f"padding: {self._css_size(node.padding)}")
        if hasattr(node, 'margin') and node.margin:
            parts.append(f"margin: {self._css_size(node.margin)}")
        if hasattr(node, 'align') and node.align:
            parts.append(f"align-items: {self._css_align(node.align)}")
        if hasattr(node, 'justify') and node.justify:
            if node.justify in ('between', 'around'):
                self._features_used.add(f'justify_{node.justify}')
            parts.append(f"justify-content: {self._css_justify(node.justify)}")
        if hasattr(node, 'width') and node.width:
            if node.width.isdigit() or node.width.endswith('px'):
                self._features_used.add('pixel_units')
            parts.append(f"width: {self._css_dimension(node.width)}")
        if hasattr(node, 'height') and node.height:
            if node.height.isdigit() or node.height.endswith('px'):
                self._features_used.add('pixel_units')
            parts.append(f"height: {self._css_dimension(node.height)}")
        if hasattr(node, 'background') and node.background:
            parts.append(f"background-color: {self._css_color(node.background)}")
        if hasattr(node, 'color') and node.color:
            parts.append(f"color: {self._css_color(node.color)}")
        if hasattr(node, 'border') and node.border:
            parts.append(f"border: {node.border}")
        return '; '.join(parts)

    def get_features_used(self) -> Set[str]:
        """Return set of features used during generation (for compatibility checking)."""
        return self._features_used.copy()

    def _layout_attrs(self, node) -> dict:
        """Build HTML attributes from layout properties."""
        attrs = {}
        style = self._layout_style(node)
        if style:
            attrs['style'] = style
        if hasattr(node, 'ui_id') and node.ui_id:
            attrs['id'] = node.ui_id
        if hasattr(node, 'ui_class') and node.ui_class:
            attrs['class'] = node.ui_class
        if hasattr(node, 'visible') and node.visible == 'false':
            existing = attrs.get('style', '')
            attrs['style'] = (existing + '; ' if existing else '') + 'display: none'
        return attrs

    def _merge_attrs(self, base: dict, layout: dict) -> dict:
        """Merge class and style attrs."""
        result = dict(base)
        for k, v in layout.items():
            if k == 'class' and k in result:
                result[k] = result[k] + ' ' + v
            elif k == 'style' and k in result:
                result[k] = result[k] + '; ' + v
            elif k == 'id' and k not in result:
                result[k] = v
            else:
                result[k] = v
        return result

    # ------------------------------------------------------------------
    # CSS value helpers (using TokenConverter for normalization)
    # ------------------------------------------------------------------

    def _css_size(self, val: str) -> str:
        """Convert spacing value using tokens system."""
        return self._tokens.spacing(val)

    def _css_dimension(self, val: str) -> str:
        """Convert size/dimension value using tokens system."""
        return self._tokens.size(val)

    def _css_align(self, val: str) -> str:
        """Convert align value using tokens system."""
        return self._tokens.align(val)

    def _css_justify(self, val: str) -> str:
        """Convert justify value using tokens system."""
        return self._tokens.justify(val)

    def _css_color(self, val: str) -> str:
        """Convert color value using tokens system."""
        return self._tokens.color(val)

    def _css_font_size(self, val: str) -> str:
        """Convert font size using tokens system."""
        return self._tokens.font_size(val)

    # ------------------------------------------------------------------
    # Attribute / JS literal helpers
    # ------------------------------------------------------------------

    def _as_int(self, value, default: int = 0) -> int:
        """Coerce an attribute to int (parsers may hand over raw strings)."""
        if value is None:
            return default
        if isinstance(value, bool):
            return int(value)
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return default

    def _as_bool(self, value, default: bool = False) -> bool:
        """Coerce an attribute to bool (parsers may hand over raw strings)."""
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ('true', '1', 'yes', 'on')

    def _js_str(self, value) -> str:
        """Quote a value as a single-quoted JS string literal."""
        text = '' if value is None else str(value)
        text = (text.replace('\\', '\\\\')
                    .replace("'", "\\'")
                    .replace('\r', '')
                    .replace('\n', '\\n'))
        return f"'{text}'"

    def _js_bool(self, value) -> str:
        return 'true' if value else 'false'

    def _js_statement(self, handler: str, arg: str) -> str:
        """Turn an on-* handler attribute into a JS statement.

        ``on-change="doThing()"`` is used verbatim, ``on-change="doThing"``
        is called with the component value.
        """
        code = handler.strip()
        if not code.endswith((')', '}', ';')):
            code = f"{code}({arg})"
        if not code.endswith(';'):
            code += ';'
        return code

    def _js_change_handler(self, handler: Optional[str], bind: Optional[str],
                           arg: str = 'value') -> Optional[str]:
        """Build the JS callback used by interactive components.

        Writes the new value back to the bound state variable (when ``bind``
        is set) and then invokes the author's handler.
        """
        statements: List[str] = []
        if bind:
            if self._desktop_mode:
                statements.append(
                    f"__quantumCall('set_state', {{name: {self._js_str(bind)}, value: {arg}}});")
            else:
                statements.append('window.__quantumState = window.__quantumState || {};')
                statements.append(f"window.__quantumState[{self._js_str(bind)}] = {arg};")
                statements.append(
                    f"if (window.__quantumShowBinding) window.__quantumShowBinding({self._js_str(bind)}, {arg});")
        if handler:
            if self._desktop_mode:
                statements.append(
                    f"__quantumCall({self._js_str(self._split_handler(handler)[0])}, "
                    f"{{value: {arg}}});")
            else:
                statements.append(self._js_statement(handler, arg))
        if not statements:
            return None
        return 'function(' + arg + ') { ' + ' '.join(statements) + ' }'

    def _js_options(self, options: Dict[str, str]) -> str:
        """Render an ordered dict of already-encoded JS values as an object literal."""
        parts = [f"{k}: {v}" for k, v in options.items() if v is not None]
        return '{' + ', '.join(parts) + '}'

    def _parse_iso_date(self, value) -> Optional[_date]:
        """Parse an ISO (YYYY-MM-DD) date, returning None when unusable."""
        if not value:
            return None
        try:
            return _date.fromisoformat(str(value).strip()[:10])
        except (TypeError, ValueError):
            return None

    def _format_date(self, value: _date, pattern: str) -> str:
        """Format a date with the picker's display pattern (mirrors DATE_PICKER_JS)."""
        iso = value.isoformat()
        year, month, day = iso.split('-')
        return (pattern or 'YYYY-MM-DD') \
            .replace('YYYY', year) \
            .replace('YY', year[2:]) \
            .replace('MM', month) \
            .replace('DD', day)

    # ------------------------------------------------------------------
    # Desktop mode helpers
    # ------------------------------------------------------------------

    def _render_text_with_binding(self, content: str) -> str:
        """Render text content, wrapping {var} references in spans for binding.

        In desktop mode, {variable} expressions are wrapped in <span> elements
        with unique IDs so that Python can update them reactively.

        Args:
            content: Text content that may contain {var} expressions.

        Returns:
            HTML string with binding spans if in desktop_mode, otherwise original content.
        """
        if not self._desktop_mode or not content:
            return content

        # Pattern to match {variable} or {expression}
        # We only create bindings for simple variable names
        def replace_binding(match):
            expr = match.group(1).strip()
            # Only bind simple variable names (alphanumeric + underscore)
            if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', expr):
                bind_id = f"__qb_{self._binding_counter}"
                self._binding_counter += 1
                self._bindings.append((bind_id, expr, 'text'))
                return f'<span id="{bind_id}">{{{expr}}}</span>'
            else:
                # Complex expressions are not bound, just rendered
                return match.group(0)

        return re.sub(r'\{([^}]+)\}', replace_binding, content)

    @staticmethod
    def _split_handler(handler: str):
        """`"salvar(1)"` -> `("salvar", "1")`; `"salvar"` -> `("salvar", "")`.

        O handler ia CRU para dentro do `__quantumCall('...')`, e do outro
        lado esta

            window.pywebview.api[fn]

        cujas chaves sao os nomes das q:function. `api["salvar()"]` e
        undefined, entao TODO `on-click` escrito com parenteses — a forma
        como se escreve uma chamada em qualquer linguagem — caia no
        `console.warn` do else, dentro de uma janela nativa onde ninguem ve
        console. O botao simplesmente nao fazia nada.
        """
        import re as _re
        if not handler:
            return '', ''
        m = _re.match(r'^\s*([A-Za-z_$][\w$.]*)\s*\((.*)\)\s*$', handler,
                      _re.DOTALL)
        if m:
            return m.group(1), m.group(2).strip()
        return handler.strip(), ''

    def _transform_onclick(self, handler: str) -> str:
        """Transform on-click handler for desktop mode."""
        if self._desktop_mode:
            nome, args = self._split_handler(handler)
            if args:
                return f"__quantumCall({self._js_str(nome)},{{args:[{args}]}})"
            return f"__quantumCall({self._js_str(nome)})"
        return handler

    def _transform_onsubmit(self, handler: str) -> str:
        """Transform on-submit handler for desktop mode with form data collection."""
        if self._desktop_mode:
            nome, _args = self._split_handler(handler)
            return (f"event.preventDefault();__quantumCall("
                    f"{self._js_str(nome)},__quantumFormData(this))")
        return handler

    def _transform_onchange(self, handler: str) -> str:
        """Transform on-change handler for desktop mode."""
        if self._desktop_mode:
            nome, _args = self._split_handler(handler)
            return f"__quantumCall({self._js_str(nome)},{{value:this.value}})"
        return handler

    def _add_input_binding(self, bind_name: str, element_id: str = None) -> str:
        """Add two-way binding for input elements in desktop mode.

        Returns the oninput handler string to add to the element.
        """
        if not self._desktop_mode or not bind_name:
            return ''
        return f"__quantumCall('set_state',{{name:'{bind_name}',value:this.value}})"

    # ------------------------------------------------------------------
    # Node rendering dispatch
    # ------------------------------------------------------------------

    def _render_node(self, node: QuantumNode, b: HtmlBuilder):
        """Dispatch node to its render method."""
        # Containers
        if isinstance(node, UIWindowNode):
            self._render_window(node, b)
        elif isinstance(node, UIHBoxNode):
            self._render_hbox(node, b)
        elif isinstance(node, UIVBoxNode):
            self._render_vbox(node, b)
        elif isinstance(node, UIPanelNode):
            self._render_panel(node, b)
        elif isinstance(node, UITabPanelNode):
            self._render_tabpanel(node, b)
        elif isinstance(node, UITabNode):
            self._render_tab(node, b)
        elif isinstance(node, UIGridNode):
            self._render_grid(node, b)
        elif isinstance(node, UIAccordionNode):
            self._render_accordion(node, b)
        elif isinstance(node, UISectionNode):
            self._render_section(node, b)
        elif isinstance(node, UIDividedBoxNode):
            self._render_dividedbox(node, b)
        elif isinstance(node, UIFormNode):
            self._render_form(node, b)
        elif isinstance(node, UIFormItemNode):
            self._render_formitem(node, b)
        elif isinstance(node, UISpacerNode):
            self._render_spacer(node, b)
        elif isinstance(node, UIScrollBoxNode):
            self._render_scrollbox(node, b)
        elif isinstance(node, UIAnimateNode):
            self._render_animate(node, b)
        # Widgets
        elif isinstance(node, UITextNode):
            self._render_text(node, b)
        elif isinstance(node, UIButtonNode):
            self._render_button(node, b)
        elif isinstance(node, UIInputNode):
            self._render_input(node, b)
        elif isinstance(node, UICheckboxNode):
            self._render_checkbox(node, b)
        elif isinstance(node, UIRadioNode):
            self._render_radio(node, b)
        elif isinstance(node, UISwitchNode):
            self._render_switch(node, b)
        elif isinstance(node, UISelectNode):
            self._render_select(node, b)
        elif isinstance(node, UITableNode):
            self._render_table(node, b)
        elif isinstance(node, UIListNode):
            self._render_list(node, b)
        elif isinstance(node, UIItemNode):
            self._render_item(node, b)
        elif isinstance(node, UIImageNode):
            self._render_image(node, b)
        elif isinstance(node, UILinkNode):
            self._render_link(node, b)
        elif isinstance(node, UIProgressNode):
            self._render_progress(node, b)
        elif isinstance(node, UITreeNode):
            self._render_tree(node, b)
        elif isinstance(node, UIMenuNode):
            self._render_menu(node, b)
        elif isinstance(node, UIOptionNode):
            self._render_option(node, b)
        elif isinstance(node, UILogNode):
            self._render_log(node, b)
        elif isinstance(node, UIMarkdownNode):
            self._render_markdown(node, b)
        elif isinstance(node, UIHeaderNode):
            self._render_header(node, b)
        elif isinstance(node, UIFooterNode):
            self._render_footer(node, b)
        elif isinstance(node, UIRuleNode):
            self._render_rule(node, b)
        elif isinstance(node, UILoadingNode):
            self._render_loading(node, b)
        elif isinstance(node, UIBadgeNode):
            self._render_badge(node, b)
        # Component Library
        elif isinstance(node, UICardNode):
            self._render_card(node, b)
        elif isinstance(node, UICardHeaderNode):
            self._render_card_header(node, b)
        elif isinstance(node, UICardBodyNode):
            self._render_card_body(node, b)
        elif isinstance(node, UICardFooterNode):
            self._render_card_footer(node, b)
        elif isinstance(node, UIModalNode):
            self._render_modal(node, b)
        elif isinstance(node, UIChartNode):
            self._render_chart(node, b)
        elif isinstance(node, UIAvatarNode):
            self._render_avatar(node, b)
        elif isinstance(node, UITooltipNode):
            self._render_tooltip(node, b)
        elif isinstance(node, UIDropdownNode):
            self._render_dropdown(node, b)
        elif isinstance(node, UIAlertNode):
            self._render_alert(node, b)
        elif isinstance(node, UIBreadcrumbNode):
            self._render_breadcrumb(node, b)
        elif isinstance(node, UIBreadcrumbItemNode):
            self._render_breadcrumb_item(node, b)
        elif isinstance(node, UIPaginationNode):
            self._render_pagination(node, b)
        elif isinstance(node, UISkeletonNode):
            self._render_skeleton(node, b)
        # Toast / carousel / stepper / calendar
        elif isinstance(node, UIToastNode):
            self._render_toast(node, b)
        elif isinstance(node, UIToastContainerNode):
            self._render_toast_container(node, b)
        elif isinstance(node, UICarouselNode):
            self._render_carousel(node, b)
        elif isinstance(node, UISlideNode):
            self._render_slide(node, b)
        elif isinstance(node, UIStepperNode):
            self._render_stepper(node, b)
        elif isinstance(node, UIStepNode):
            self._render_step(node, b)
        elif isinstance(node, UICalendarNode):
            self._render_calendar(node, b)
        elif isinstance(node, UIDatePickerNode):
            self._render_date_picker(node, b)
        # Quantum nodes passthrough
        elif isinstance(node, SetNode):
            b.comment(f'q:set {node.name} = {node.value}')
            # Track persisted variables for HTML persistence
            if node.persist:
                self._has_persistence = True
                self._persisted_vars.append({
                    'name': node.name,
                    'scope': node.persist,
                    'key': node.persist_key or node.name,
                    'ttl': node.persist_ttl,
                    'encrypt': node.persist_encrypt
                })
        elif isinstance(node, LoopNode):
            b.comment(f'q:loop {node.var_name}')
        elif isinstance(node, IfNode):
            b.comment(f'q:if {node.condition}')
        # UIColumnNode is handled inside table render

    def _render_children(self, children: list, b: HtmlBuilder):
        for child in children:
            self._render_node(child, b)

    # ------------------------------------------------------------------
    # Container renders
    # ------------------------------------------------------------------

    def _render_window(self, node: UIWindowNode, b: HtmlBuilder):
        attrs = self._merge_attrs({'class': 'q-window'}, self._layout_attrs(node))
        b.open_tag('div', attrs)
        b.indent()
        self._render_children(node.children, b)
        b.dedent()
        b.close_tag('div')

    def _render_hbox(self, node: UIHBoxNode, b: HtmlBuilder):
        base_style = 'display: flex; flex-direction: row'
        attrs = self._merge_attrs({'style': base_style}, self._layout_attrs(node))
        b.open_tag('div', attrs)
        b.indent()
        self._render_children(node.children, b)
        b.dedent()
        b.close_tag('div')

    def _render_vbox(self, node: UIVBoxNode, b: HtmlBuilder):
        base_style = 'display: flex; flex-direction: column'
        attrs = self._merge_attrs({'style': base_style}, self._layout_attrs(node))
        b.open_tag('div', attrs)
        b.indent()
        self._render_children(node.children, b)
        b.dedent()
        b.close_tag('div')

    def _render_panel(self, node: UIPanelNode, b: HtmlBuilder):
        attrs = self._merge_attrs({'class': 'q-panel'}, self._layout_attrs(node))
        b.open_tag('div', attrs)
        b.indent()
        if node.title:
            b.open_tag('div', {'class': 'q-panel-title'})
            b.indent()
            b.text(node.title)
            b.dedent()
            b.close_tag('div')
        self._render_children(node.children, b)
        b.dedent()
        b.close_tag('div')

    def _render_tabpanel(self, node: UITabPanelNode, b: HtmlBuilder):
        self._has_tabs = True
        self._tab_counter += 1
        group_id = f"tabs-{self._tab_counter}"

        attrs = self._merge_attrs({'class': 'q-tabs'}, self._layout_attrs(node))
        b.open_tag('div', attrs)
        b.indent()

        # Tab headers
        b.open_tag('div', {'class': 'q-tab-headers'})
        b.indent()
        tabs = [c for c in node.children if isinstance(c, UITabNode)]
        for i, tab in enumerate(tabs):
            tab_id = f"{group_id}-tab-{i}"
            cls = 'q-tab-header active' if i == 0 else 'q-tab-header'
            b.open_tag('button', {'class': cls, 'data-tab': tab_id, 'data-tab-group': group_id})
            b.indent()
            b.text(tab.title)
            b.dedent()
            b.close_tag('button')
        b.dedent()
        b.close_tag('div')

        # Tab contents
        for i, tab in enumerate(tabs):
            tab_id = f"{group_id}-tab-{i}"
            cls = 'q-tab-content active' if i == 0 else 'q-tab-content'
            b.open_tag('div', {'id': tab_id, 'class': cls, 'data-tab-group': group_id})
            b.indent()
            self._render_children(tab.children, b)
            b.dedent()
            b.close_tag('div')

        b.dedent()
        b.close_tag('div')

    def _render_tab(self, node: UITabNode, b: HtmlBuilder):
        # Tabs are rendered inside tabpanel, standalone tab renders as div
        attrs = self._merge_attrs({}, self._layout_attrs(node))
        b.open_tag('div', attrs)
        b.indent()
        self._render_children(node.children, b)
        b.dedent()
        b.close_tag('div')

    def _render_grid(self, node: UIGridNode, b: HtmlBuilder):
        cols = node.columns or '1'
        try:
            n = int(cols)
            grid_css = f"display: grid; grid-template-columns: repeat({n}, 1fr)"
        except ValueError:
            grid_css = f"display: grid; grid-template-columns: {cols}"
        attrs = self._merge_attrs({'style': grid_css}, self._layout_attrs(node))
        b.open_tag('div', attrs)
        b.indent()
        self._render_children(node.children, b)
        b.dedent()
        b.close_tag('div')

    def _render_accordion(self, node: UIAccordionNode, b: HtmlBuilder):
        attrs = self._merge_attrs({}, self._layout_attrs(node))
        b.open_tag('div', attrs)
        b.indent()
        self._render_children(node.children, b)
        b.dedent()
        b.close_tag('div')

    def _render_section(self, node: UISectionNode, b: HtmlBuilder):
        detail_attrs = {'class': 'q-section'}
        if node.expanded:
            detail_attrs['open'] = True
        attrs = self._merge_attrs(detail_attrs, self._layout_attrs(node))
        b.open_tag('details', attrs)
        b.indent()
        b.open_tag('summary')
        b.indent()
        b.text(node.title)
        b.dedent()
        b.close_tag('summary')
        b.open_tag('div', {'class': 'q-section-content'})
        b.indent()
        self._render_children(node.children, b)
        b.dedent()
        b.close_tag('div')
        b.dedent()
        b.close_tag('details')

    def _render_dividedbox(self, node: UIDividedBoxNode, b: HtmlBuilder):
        dir_class = 'q-dividedbox-h' if node.direction == 'horizontal' else 'q-dividedbox-v'
        attrs = self._merge_attrs({'class': f'q-dividedbox {dir_class}'}, self._layout_attrs(node))
        b.open_tag('div', attrs)
        b.indent()
        for i, child in enumerate(node.children):
            if i > 0:
                b.open_tag('div', {'class': 'q-divider'}, self_closing=False)
                b.close_tag('div')
            self._render_node(child, b)
        b.dedent()
        b.close_tag('div')

    def _render_form(self, node: UIFormNode, b: HtmlBuilder):
        # Track form for validation
        self._form_counter += 1
        form_id = f"q-form-{self._form_counter}"

        form_attrs = {'class': 'q-form', 'id': form_id}

        # Validation mode attributes
        if node.validation_mode in ('client', 'both'):
            self._has_validation = True
            form_attrs['data-validation'] = node.validation_mode
            form_attrs['data-error-display'] = node.error_display

        # HTML5 novalidate attribute (use our custom JS validation instead)
        if node.novalidate or node.validation_mode in ('client', 'both'):
            form_attrs['novalidate'] = True

        if node.on_submit:
            if self._desktop_mode:
                # Transform on-submit for pywebview with form data collection
                form_attrs['onsubmit'] = self._transform_onsubmit(node.on_submit)
            else:
                # Add validation check before submit
                if node.validation_mode in ('client', 'both'):
                    form_attrs['onsubmit'] = f"return __qValidation.validateForm('{form_id}') && ({node.on_submit})"
                else:
                    form_attrs['onsubmit'] = node.on_submit

        attrs = self._merge_attrs(form_attrs, self._layout_attrs(node))
        b.open_tag('form', attrs)
        b.indent()

        # Register custom validators for this form
        if node.validators:
            self._form_validators[form_id] = node.validators

        # Render error summary if configured
        if node.error_display in ('summary', 'both'):
            b.open_tag('div', {'class': 'q-validation-summary', 'id': f'{form_id}-summary', 'style': 'display:none'})
            b.close_tag('div')

        self._render_children(node.children, b)
        b.dedent()
        b.close_tag('form')

    def _render_formitem(self, node: UIFormItemNode, b: HtmlBuilder):
        attrs = self._merge_attrs({'class': 'q-formitem'}, self._layout_attrs(node))
        b.open_tag('div', attrs)
        b.indent()
        if node.label:
            b.open_tag('label', {'class': 'q-formitem-label'})
            b.indent()
            b.text(node.label)
            b.dedent()
            b.close_tag('label')
        self._render_children(node.children, b)
        b.dedent()
        b.close_tag('div')

    def _render_spacer(self, node: UISpacerNode, b: HtmlBuilder):
        style = 'flex: 1'
        if node.size:
            style = f"flex: 0 0 {self._css_size(node.size)}"
        attrs = self._merge_attrs({'class': 'q-spacer', 'style': style}, self._layout_attrs(node))
        b.open_tag('div', attrs, self_closing=False)
        b.close_tag('div')

    def _render_scrollbox(self, node: UIScrollBoxNode, b: HtmlBuilder):
        attrs = self._merge_attrs({'class': 'q-scrollbox'}, self._layout_attrs(node))
        b.open_tag('div', attrs)
        b.indent()
        self._render_children(node.children, b)
        b.dedent()
        b.close_tag('div')

    # ------------------------------------------------------------------
    # Widget renders
    # ------------------------------------------------------------------

    def _render_text(self, node: UITextNode, b: HtmlBuilder):
        style_parts = []
        if node.size:
            self._features_used.add('font_size')
            style_parts.append(f"font-size: {self._css_font_size(node.size)}")
        if node.weight:
            style_parts.append(f"font-weight: {node.weight}")
        base_attrs = {}
        if style_parts:
            base_attrs['style'] = '; '.join(style_parts)
        attrs = self._merge_attrs(base_attrs, self._layout_attrs(node))
        b.open_tag('span', attrs)
        b.indent()
        # Render content with binding support in desktop mode
        content = self._render_text_with_binding(node.content) if self._desktop_mode else node.content
        b.text(content)
        b.dedent()
        b.close_tag('span')

    def _render_button(self, node: UIButtonNode, b: HtmlBuilder):
        cls = 'q-btn'
        if node.variant:
            cls += f' q-btn-{node.variant}'
        btn_attrs = {'class': cls}
        if node.disabled:
            btn_attrs['disabled'] = True
        if node.on_click:
            # _transform_onclick, e nao interpolacao crua: o botao e
            # justamente o lugar onde `on-click="salvar()"` mais aparece, e
            # `api["salvar()"]` e undefined.
            btn_attrs['onclick'] = self._transform_onclick(node.on_click)
        attrs = self._merge_attrs(btn_attrs, self._layout_attrs(node))
        b.open_tag('button', attrs)
        b.indent()
        # Render content with binding support
        content = self._render_text_with_binding(node.content) if self._desktop_mode else node.content
        b.text(content)
        b.dedent()
        b.close_tag('button')

    def _render_input(self, node: UIInputNode, b: HtmlBuilder):
        input_attrs = {'class': 'q-input', 'type': node.input_type}
        if node.placeholder:
            input_attrs['placeholder'] = node.placeholder
        if node.bind:
            input_attrs['name'] = node.bind
            # Add two-way binding in desktop mode
            if self._desktop_mode:
                input_attrs['oninput'] = self._add_input_binding(node.bind)

        # HTML5 validation attributes
        if node.required:
            input_attrs['required'] = True
        if node.min is not None:
            input_attrs['min'] = node.min
        if node.max is not None:
            input_attrs['max'] = node.max
        if node.minlength is not None:
            input_attrs['minlength'] = str(node.minlength)
        if node.maxlength is not None:
            input_attrs['maxlength'] = str(node.maxlength)
        if node.pattern:
            input_attrs['pattern'] = node.pattern

        # Custom error message for JS validation
        if node.error_message:
            input_attrs['data-error-message'] = node.error_message

        # Custom validators (comma-separated list)
        if node.validators:
            input_attrs['data-validators'] = ','.join(node.validators)

        # Check if input has any validation
        has_validation = (node.error_message or node.required or node.validators or
                          node.pattern or node.min or node.max or
                          node.minlength or node.maxlength)

        if has_validation:
            self._has_validation = True
            input_id = node.bind or f"input-{id(node)}"
            input_attrs['id'] = input_id
            attrs = self._merge_attrs(input_attrs, self._layout_attrs(node))

            # Create wrapper for input + error message
            b.open_tag('div', {'class': 'q-input-wrapper'})
            b.indent()
            b.open_tag('input', attrs, self_closing=True)
            b.open_tag('div', {'class': 'q-error-message', 'id': f'{input_id}-error', 'style': 'display:none'})
            if node.error_message:
                b.text(node.error_message)
            b.close_tag('div')
            b.dedent()
            b.close_tag('div')
        else:
            attrs = self._merge_attrs(input_attrs, self._layout_attrs(node))
            b.open_tag('input', attrs, self_closing=True)

    def _render_checkbox(self, node: UICheckboxNode, b: HtmlBuilder):
        attrs = self._merge_attrs({'class': 'q-checkbox'}, self._layout_attrs(node))
        b.open_tag('label', attrs)
        b.indent()
        cb_attrs = {'type': 'checkbox'}
        if node.bind:
            cb_attrs['name'] = node.bind
        b.open_tag('input', cb_attrs, self_closing=True)
        if node.label:
            b.text(node.label)
        b.dedent()
        b.close_tag('label')

    def _render_radio(self, node: UIRadioNode, b: HtmlBuilder):
        attrs = self._merge_attrs({}, self._layout_attrs(node))
        b.open_tag('div', attrs)
        b.indent()
        if node.options:
            for opt in node.options.split(','):
                opt = opt.strip()
                b.open_tag('label', {'class': 'q-checkbox'})
                b.indent()
                radio_attrs = {'type': 'radio', 'value': opt}
                if node.bind:
                    radio_attrs['name'] = node.bind
                b.open_tag('input', radio_attrs, self_closing=True)
                b.text(opt)
                b.dedent()
                b.close_tag('label')
        b.dedent()
        b.close_tag('div')

    def _render_switch(self, node: UISwitchNode, b: HtmlBuilder):
        attrs = self._merge_attrs({'class': 'q-switch'}, self._layout_attrs(node))
        b.open_tag('label', attrs)
        b.indent()
        cb_attrs = {'type': 'checkbox'}
        if node.bind:
            cb_attrs['name'] = node.bind
        b.open_tag('input', cb_attrs, self_closing=True)
        b.open_tag('span', {'class': 'q-switch-track'})
        b.indent()
        b.open_tag('span', {'class': 'q-switch-thumb'}, self_closing=False)
        b.close_tag('span')
        b.dedent()
        b.close_tag('span')
        if node.label:
            b.text(node.label)
        b.dedent()
        b.close_tag('label')

    def _render_select(self, node: UISelectNode, b: HtmlBuilder):
        select_attrs = {'class': 'q-select'}
        if node.bind:
            select_attrs['name'] = node.bind
        attrs = self._merge_attrs(select_attrs, self._layout_attrs(node))
        b.open_tag('select', attrs)
        b.indent()
        # Inline options
        if node.options:
            for opt in node.options.split(','):
                opt = opt.strip()
                b.open_tag('option', {'value': opt})
                b.indent()
                b.text(opt)
                b.dedent()
                b.close_tag('option')
        # Child option nodes
        for child in getattr(node, 'children', []):
            if isinstance(child, UIOptionNode):
                b.open_tag('option', {'value': child.value or ''})
                b.indent()
                b.text(child.label or child.value or '')
                b.dedent()
                b.close_tag('option')
        b.dedent()
        b.close_tag('select')

    def _render_table(self, node: UITableNode, b: HtmlBuilder):
        attrs = self._merge_attrs({'class': 'q-table'}, self._layout_attrs(node))
        b.open_tag('table', attrs)
        b.indent()
        columns = [c for c in node.children if isinstance(c, UIColumnNode)]
        if columns:
            b.open_tag('thead')
            b.indent()
            b.open_tag('tr')
            b.indent()
            for col in columns:
                th_attrs = {}
                if col.align:
                    th_attrs['style'] = f"text-align: {col.align}"
                if col.column_width:
                    existing = th_attrs.get('style', '')
                    th_attrs['style'] = (existing + '; ' if existing else '') + f"width: {self._css_dimension(col.column_width)}"
                b.open_tag('th', th_attrs if th_attrs else None)
                b.indent()
                b.text(col.label or col.key or '')
                b.dedent()
                b.close_tag('th')
            b.dedent()
            b.close_tag('tr')
            b.dedent()
            b.close_tag('thead')
        b.open_tag('tbody')
        b.indent()
        if node.source:
            b.comment(f'Data source: {node.source}')
        b.dedent()
        b.close_tag('tbody')
        b.dedent()
        b.close_tag('table')

    def _render_list(self, node: UIListNode, b: HtmlBuilder):
        attrs = self._merge_attrs({}, self._layout_attrs(node))
        b.open_tag('ul', attrs)
        b.indent()
        if node.source:
            b.comment(f'Data source: {node.source}')
        self._render_children(node.children, b)
        b.dedent()
        b.close_tag('ul')

    def _render_item(self, node: UIItemNode, b: HtmlBuilder):
        attrs = self._merge_attrs({}, self._layout_attrs(node))
        b.open_tag('li', attrs)
        b.indent()
        self._render_children(node.children, b)
        b.dedent()
        b.close_tag('li')

    def _render_image(self, node: UIImageNode, b: HtmlBuilder):
        self._features_used.add('image')
        img_attrs = {}
        if node.src:
            img_attrs['src'] = node.src
        if node.alt:
            img_attrs['alt'] = node.alt
        attrs = self._merge_attrs(img_attrs, self._layout_attrs(node))
        b.open_tag('img', attrs, self_closing=True)

    def _render_link(self, node: UILinkNode, b: HtmlBuilder):
        if node.external:
            self._features_used.add('link_external')
        a_attrs = {}
        if node.to:
            a_attrs['href'] = node.to
        if node.external:
            a_attrs['target'] = '_blank'
            a_attrs['rel'] = 'noopener noreferrer'
        attrs = self._merge_attrs(a_attrs, self._layout_attrs(node))
        b.open_tag('a', attrs)
        b.indent()
        b.text(node.content)
        b.dedent()
        b.close_tag('a')

    def _render_progress(self, node: UIProgressNode, b: HtmlBuilder):
        prog_attrs = {}
        if node.value:
            prog_attrs['value'] = node.value
        if node.max:
            prog_attrs['max'] = node.max
        attrs = self._merge_attrs(prog_attrs, self._layout_attrs(node))
        b.open_tag('progress', attrs)
        b.close_tag('progress')

    def _render_tree(self, node: UITreeNode, b: HtmlBuilder):
        attrs = self._merge_attrs({}, self._layout_attrs(node))
        b.open_tag('div', attrs)
        b.indent()
        if node.source:
            b.comment(f'Tree source: {node.source}')
        b.dedent()
        b.close_tag('div')

    def _render_menu(self, node: UIMenuNode, b: HtmlBuilder):
        attrs = self._merge_attrs({'class': 'q-menu'}, self._layout_attrs(node))
        b.open_tag('nav', attrs)
        b.indent()
        self._render_children(node.children, b)
        b.dedent()
        b.close_tag('nav')

    def _render_option(self, node: UIOptionNode, b: HtmlBuilder):
        opt_attrs = {'class': 'q-menu-item'}
        if node.on_click:
            if self._desktop_mode:
                opt_attrs['onclick'] = self._transform_onclick(node.on_click)
            else:
                opt_attrs['onclick'] = node.on_click
        b.open_tag('span', opt_attrs)
        b.indent()
        b.text(node.label or node.value or '')
        b.dedent()
        b.close_tag('span')

    def _render_log(self, node: UILogNode, b: HtmlBuilder):
        log_attrs = {'class': 'q-log'}
        attrs = self._merge_attrs(log_attrs, self._layout_attrs(node))
        b.open_tag('div', attrs)
        b.close_tag('div')

    def _render_markdown(self, node: UIMarkdownNode, b: HtmlBuilder):
        attrs = self._merge_attrs({}, self._layout_attrs(node))
        b.open_tag('div', attrs)
        b.indent()
        b.text(node.content)
        b.dedent()
        b.close_tag('div')

    def _render_header(self, node: UIHeaderNode, b: HtmlBuilder):
        attrs = self._merge_attrs({'class': 'q-header'}, self._layout_attrs(node))
        b.open_tag('header', attrs)
        b.indent()
        if node.title:
            b.text(node.title)
        elif node.content:
            b.text(node.content)
        self._render_children(node.children, b)
        b.dedent()
        b.close_tag('header')

    def _render_footer(self, node: UIFooterNode, b: HtmlBuilder):
        attrs = self._merge_attrs({'class': 'q-footer'}, self._layout_attrs(node))
        b.open_tag('footer', attrs)
        b.indent()
        if node.content:
            b.text(node.content)
        self._render_children(node.children, b)
        b.dedent()
        b.close_tag('footer')

    def _render_rule(self, node: UIRuleNode, b: HtmlBuilder):
        b.open_tag('hr', None, self_closing=True)

    def _render_loading(self, node: UILoadingNode, b: HtmlBuilder):
        attrs = self._merge_attrs({'class': 'q-loading'}, self._layout_attrs(node))
        b.open_tag('div', attrs)
        b.indent()
        b.open_tag('div', {'class': 'q-spinner'}, self_closing=False)
        b.close_tag('div')
        if node.text:
            b.text(node.text)
        b.dedent()
        b.close_tag('div')

    def _render_badge(self, node: UIBadgeNode, b: HtmlBuilder):
        cls = 'q-badge'
        if node.variant:
            cls += f' q-badge-{node.variant}'
        badge_attrs = {'class': cls}
        if node.badge_color:
            badge_attrs['style'] = f"background-color: {self._css_color(node.badge_color)}"
        attrs = self._merge_attrs(badge_attrs, self._layout_attrs(node))
        b.open_tag('span', attrs)
        b.indent()
        b.text(node.content)
        b.dedent()
        b.close_tag('span')

    # ------------------------------------------------------------------
    # Animation render
    # ------------------------------------------------------------------

    def _render_animate(self, node: UIAnimateNode, b: HtmlBuilder):
        """Render a ui:animate wrapper with animation effects.

        The ui:animate node wraps child elements and applies CSS animations
        based on the animation type, trigger, duration, and other properties.

        Attributes supported:
            - type/anim_type: fade, slide, scale, rotate, bounce, pulse, shake, etc.
            - animate: Animation preset name (alternative to type)
            - duration: Animation duration (e.g., '300', '300ms', '0.3s')
            - delay: Animation delay
            - easing: Easing function (ease, ease-in, ease-out, linear, spring, bounce)
            - repeat: Repeat count (1, 2, 'infinite')
            - trigger: Animation trigger (on-load, on-hover, on-click, on-visible)
            - direction: Animation direction (normal, reverse, alternate)
        """
        self._has_animations = True
        self._animate_counter += 1

        # Build CSS classes
        classes = ['q-animate']

        # Animation type/preset
        anim_type = node.anim_type or node.animate
        if anim_type:
            # Normalize animation type name
            anim_class = f"q-anim-{anim_type.replace('_', '-')}"
            classes.append(anim_class)

        # Trigger class
        trigger = node.anim_trigger or 'on-load'
        if trigger != 'on-load':
            classes.append(f"q-trigger-{trigger}")

        # Easing class
        if node.anim_easing:
            easing = node.anim_easing.replace('_', '-')
            classes.append(f"q-easing-{easing}")

        # Build inline styles for animation variables
        style_parts = []

        # Duration
        if node.anim_duration:
            duration = node.anim_duration
            # Add 'ms' if no unit specified
            if duration.isdigit():
                duration = f"{duration}ms"
            style_parts.append(f"--q-anim-duration: {duration}")

        # Delay
        if node.anim_delay:
            delay = node.anim_delay
            if delay.isdigit():
                delay = f"{delay}ms"
            style_parts.append(f"--q-anim-delay: {delay}")

        # Repeat
        if node.anim_repeat:
            style_parts.append(f"--q-anim-repeat: {node.anim_repeat}")

        # Direction
        if node.anim_direction:
            style_parts.append(f"--q-anim-direction: {node.anim_direction}")

        # Build attributes
        anim_attrs = {'class': ' '.join(classes)}

        if style_parts:
            anim_attrs['style'] = '; '.join(style_parts)

        # Add data attribute for once-only visibility trigger
        if trigger == 'on-visible':
            anim_attrs['data-anim-once'] = 'true'

        # Generate unique ID if needed for JS targeting
        anim_id = f"q-anim-{self._animate_counter}"
        anim_attrs['id'] = anim_id

        # Merge with layout attributes
        attrs = self._merge_attrs(anim_attrs, self._layout_attrs(node))

        # Render the wrapper div
        b.open_tag('div', attrs)
        b.indent()

        # Render children
        self._render_children(node.children, b)

        b.dedent()
        b.close_tag('div')

    def _animation_attrs(self, node) -> dict:
        """Build animation-related HTML attributes from animation properties.

        This method can be used to add animation attributes to any UI node
        that supports inline animations via the 'animate' or 'transition' attributes.
        """
        attrs = {}

        # Check if node has animation mixin
        if not hasattr(node, 'animate'):
            return attrs

        # Handle inline animate attribute
        if node.animate:
            self._has_animations = True
            classes = ['q-animate', f"q-anim-{node.animate.replace('_', '-')}"]
            attrs['class'] = ' '.join(classes)

        # Handle inline transition attribute (e.g., "scale:0.95:100ms")
        if hasattr(node, 'transition') and node.transition:
            self._has_animations = True
            attrs['data-transition'] = node.transition

        return attrs

    # ------------------------------------------------------------------
    # Component Library renders
    # ------------------------------------------------------------------

    def _render_card(self, node: UICardNode, b: HtmlBuilder):
        cls = 'q-card'
        if node.variant:
            cls += f' q-card-{node.variant}'
        attrs = self._merge_attrs({'class': cls}, self._layout_attrs(node))
        b.open_tag('div', attrs)
        b.indent()
        if node.image:
            b.open_tag('div', {'class': 'q-card-image'})
            b.open_tag('img', {'src': node.image, 'alt': node.title or ''}, self_closing=True)
            b.close_tag('div')
        if node.title and not any(isinstance(c, UICardHeaderNode) for c in node.children):
            b.open_tag('div', {'class': 'q-card-header'})
            b.open_tag('div', {'class': 'q-card-title'})
            b.text(node.title)
            b.close_tag('div')
            if node.subtitle:
                b.open_tag('div', {'class': 'q-card-subtitle'})
                b.text(node.subtitle)
                b.close_tag('div')
            b.close_tag('div')
        self._render_children(node.children, b)
        b.dedent()
        b.close_tag('div')

    def _render_card_header(self, node: UICardHeaderNode, b: HtmlBuilder):
        attrs = self._merge_attrs({'class': 'q-card-header'}, self._layout_attrs(node))
        b.open_tag('div', attrs)
        b.indent()
        self._render_children(node.children, b)
        b.dedent()
        b.close_tag('div')

    def _render_card_body(self, node: UICardBodyNode, b: HtmlBuilder):
        attrs = self._merge_attrs({'class': 'q-card-body'}, self._layout_attrs(node))
        b.open_tag('div', attrs)
        b.indent()
        self._render_children(node.children, b)
        b.dedent()
        b.close_tag('div')

    def _render_card_footer(self, node: UICardFooterNode, b: HtmlBuilder):
        attrs = self._merge_attrs({'class': 'q-card-footer'}, self._layout_attrs(node))
        b.open_tag('div', attrs)
        b.indent()
        self._render_children(node.children, b)
        b.dedent()
        b.close_tag('div')

    def _render_modal(self, node: UIModalNode, b: HtmlBuilder):
        self._features_used.add('modal')
        modal_id = node.modal_id or f'modal-{id(node)}'
        overlay_class = 'q-modal-overlay' + (' q-modal-open' if node.open else '')
        b.open_tag('div', {'class': overlay_class, 'id': modal_id})
        b.indent()
        dialog_class = 'q-modal' + (f' q-modal-{node.size}' if node.size else '')
        attrs = self._merge_attrs({'class': dialog_class, 'role': 'dialog'}, self._layout_attrs(node))
        b.open_tag('div', attrs)
        b.indent()
        if node.title or node.closable:
            b.open_tag('div', {'class': 'q-modal-header'})
            if node.title:
                b.open_tag('h3', {'class': 'q-modal-title'})
                b.text(node.title)
                b.close_tag('h3')
            if node.closable:
                b.open_tag('button', {'class': 'q-modal-close', 'onclick': f"document.getElementById('{modal_id}').classList.remove('q-modal-open')"})
                b.text('x')
                b.close_tag('button')
            b.close_tag('div')
        b.open_tag('div', {'class': 'q-modal-body'})
        self._render_children(node.children, b)
        b.close_tag('div')
        b.dedent()
        b.close_tag('div')
        b.dedent()
        b.close_tag('div')

    def _render_chart(self, node: UIChartNode, b: HtmlBuilder):
        self._features_used.add('chart')
        attrs = self._merge_attrs({'class': f'q-chart q-chart-{node.chart_type}'}, self._layout_attrs(node))
        b.open_tag('div', attrs)
        b.indent()
        if node.title:
            b.open_tag('div', {'class': 'q-chart-title'})
            b.text(node.title)
            b.close_tag('div')
        b.open_tag('div', {'class': 'q-chart-container'})
        if node.labels and node.values:
            labels = [l.strip() for l in node.labels.split(',')]
            values = [v.strip() for v in node.values.split(',')]
            colors = [c.strip() for c in node.colors.split(',')] if node.colors else []
            default_colors = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6']
            max_val = max(float(v) for v in values) if values else 100
            for i, (label, value) in enumerate(zip(labels, values)):
                color = colors[i] if i < len(colors) else default_colors[i % len(default_colors)]
                percent = (float(value) / max_val) * 100 if max_val > 0 else 0
                if node.chart_type == 'bar':
                    b.open_tag('div', {'class': 'q-chart-bar-group'})
                    b.open_tag('div', {'class': 'q-chart-label'})
                    b.text(label)
                    b.close_tag('div')
                    b.open_tag('div', {'class': 'q-chart-bar', 'style': f'width:{percent}%;background:{color}'})
                    b.open_tag('span', {'class': 'q-chart-value'})
                    b.text(value)
                    b.close_tag('span')
                    b.close_tag('div')
                    b.close_tag('div')
        b.close_tag('div')
        b.dedent()
        b.close_tag('div')

    def _render_avatar(self, node: UIAvatarNode, b: HtmlBuilder):
        cls = 'q-avatar' + (f' q-avatar-{node.size}' if node.size else '')
        if node.shape == 'square':
            cls += ' q-avatar-square'
        attrs = self._merge_attrs({'class': cls}, self._layout_attrs(node))
        b.open_tag('div', attrs)
        if node.src:
            b.open_tag('img', {'src': node.src, 'alt': node.name or ''}, self_closing=True)
        elif node.name:
            initials = ''.join(p[0].upper() for p in node.name.split()[:2])
            b.open_tag('span', {'class': 'q-avatar-initials'})
            b.text(initials or '?')
            b.close_tag('span')
        if node.status:
            b.open_tag('span', {'class': f'q-avatar-status q-avatar-status-{node.status}'})
            b.close_tag('span')
        b.close_tag('div')

    def _render_tooltip(self, node: UITooltipNode, b: HtmlBuilder):
        self._features_used.add('tooltip')
        attrs = self._merge_attrs({'class': f'q-tooltip-wrapper q-tooltip-{node.position}'}, self._layout_attrs(node))
        b.open_tag('div', attrs)
        self._render_children(node.children, b)
        b.open_tag('span', {'class': 'q-tooltip-text', 'role': 'tooltip'})
        b.text(node.content)
        b.close_tag('span')
        b.close_tag('div')

    def _render_dropdown(self, node: UIDropdownNode, b: HtmlBuilder):
        self._features_used.add('dropdown')
        cls = f'q-dropdown q-dropdown-{node.dropdown_align}'
        if node.trigger == 'hover':
            cls += ' q-dropdown-hover'
        attrs = self._merge_attrs({'class': cls}, self._layout_attrs(node))
        b.open_tag('div', attrs)
        b.open_tag('button', {'class': 'q-dropdown-trigger'})
        b.text(node.label or 'Menu')
        b.open_tag('span', {'class': 'q-dropdown-arrow'})
        b.text(' v')
        b.close_tag('span')
        b.close_tag('button')
        b.open_tag('div', {'class': 'q-dropdown-menu'})
        self._render_children(node.children, b)
        b.close_tag('div')
        b.close_tag('div')

    def _render_alert(self, node: UIAlertNode, b: HtmlBuilder):
        cls = f'q-alert q-alert-{node.variant}'
        if node.dismissible:
            cls += ' q-alert-dismissible'
        alert_id = f'alert-{id(node)}'
        attrs = self._merge_attrs({'class': cls, 'role': 'alert', 'id': alert_id}, self._layout_attrs(node))
        b.open_tag('div', attrs)
        if node.icon:
            b.open_tag('span', {'class': 'q-alert-icon'})
            b.text(node.icon)
            b.close_tag('span')
        b.open_tag('div', {'class': 'q-alert-content'})
        if node.title:
            b.open_tag('div', {'class': 'q-alert-title'})
            b.text(node.title)
            b.close_tag('div')
        if node.content:
            b.open_tag('div', {'class': 'q-alert-message'})
            b.text(node.content)
            b.close_tag('div')
        self._render_children(node.children, b)
        b.close_tag('div')
        if node.dismissible:
            b.open_tag('button', {'class': 'q-alert-dismiss', 'onclick': f"document.getElementById('{alert_id}').style.display='none'"})
            b.text('x')
            b.close_tag('button')
        b.close_tag('div')

    def _render_breadcrumb(self, node: UIBreadcrumbNode, b: HtmlBuilder):
        attrs = self._merge_attrs({'class': 'q-breadcrumb'}, self._layout_attrs(node))
        b.open_tag('nav', attrs)
        b.open_tag('ol', {'class': 'q-breadcrumb-list'})
        for i, child in enumerate(node.children):
            if isinstance(child, UIBreadcrumbItemNode):
                is_last = i == len(node.children) - 1
                self._render_breadcrumb_item_internal(child, b, node.separator, is_last)
        b.close_tag('ol')
        b.close_tag('nav')

    def _render_breadcrumb_item(self, node: UIBreadcrumbItemNode, b: HtmlBuilder):
        self._render_breadcrumb_item_internal(node, b, '/', False)

    def _render_breadcrumb_item_internal(self, node: UIBreadcrumbItemNode, b: HtmlBuilder, sep: str, is_last: bool):
        cls = 'q-breadcrumb-item' + (' q-breadcrumb-current' if is_last else '')
        b.open_tag('li', {'class': cls})
        if node.to and not is_last:
            b.open_tag('a', {'href': node.to, 'class': 'q-breadcrumb-link'})
            b.text(node.label)
            b.close_tag('a')
        else:
            b.open_tag('span', {'class': 'q-breadcrumb-text'})
            b.text(node.label)
            b.close_tag('span')
        if not is_last:
            b.open_tag('span', {'class': 'q-breadcrumb-separator'})
            b.text(sep)
            b.close_tag('span')
        b.close_tag('li')

    def _render_pagination(self, node: UIPaginationNode, b: HtmlBuilder):
        self._features_used.add('pagination')
        attrs = self._merge_attrs({'class': 'q-pagination'}, self._layout_attrs(node))
        b.open_tag('nav', attrs)
        if node.show_total:
            b.open_tag('span', {'class': 'q-pagination-total'})
            b.text(f'Total: {node.total or 0} items')
            b.close_tag('span')
        b.open_tag('div', {'class': 'q-pagination-controls'})
        b.open_tag('button', {'class': 'q-pagination-prev'})
        b.text('Prev')
        b.close_tag('button')
        b.open_tag('span', {'class': 'q-pagination-pages'})
        b.text(f'Page {node.current}')
        b.close_tag('span')
        b.open_tag('button', {'class': 'q-pagination-next'})
        b.text('Next')
        b.close_tag('button')
        b.close_tag('div')
        if node.show_jump:
            b.open_tag('div', {'class': 'q-pagination-jump'})
            b.text('Go to ')
            b.open_tag('input', {'type': 'number', 'min': '1', 'class': 'q-pagination-input'}, self_closing=True)
            b.close_tag('div')
        b.close_tag('nav')

    def _render_skeleton(self, node: UISkeletonNode, b: HtmlBuilder):
        cls = f'q-skeleton q-skeleton-{node.variant}'
        if node.animated:
            cls += ' q-skeleton-animated'
        attrs = self._merge_attrs({'class': cls}, self._layout_attrs(node))
        if node.variant == 'text':
            for _ in range(node.lines):
                b.open_tag('div', attrs)
                b.close_tag('div')
        elif node.variant == 'card':
            b.open_tag('div', {'class': 'q-skeleton-card'})
            b.open_tag('div', {'class': 'q-skeleton q-skeleton-rect q-skeleton-animated', 'style': 'height:120px'})
            b.close_tag('div')
            b.open_tag('div', {'class': 'q-skeleton q-skeleton-text q-skeleton-animated', 'style': 'width:60%'})
            b.close_tag('div')
            b.open_tag('div', {'class': 'q-skeleton q-skeleton-text q-skeleton-animated', 'style': 'width:80%'})
            b.close_tag('div')
            b.close_tag('div')
        else:
            b.open_tag('div', attrs)
            b.close_tag('div')

    # ------------------------------------------------------------------
    # Toast renders
    # ------------------------------------------------------------------

    def _render_toast(self, node: UIToastNode, b: HtmlBuilder):
        """Render ui:toast as a positioned, dismissible notification."""
        self._features_used.add('toast')
        self._has_toast = True
        self._toast_counter += 1

        toast_id = node.ui_id or f'q-toast-{self._toast_counter}'
        variant = node.variant or 'info'
        position = node.position or 'top-right'
        duration = self._as_int(node.duration, 3000)
        dismissible = self._as_bool(node.dismissible, True)

        # Fixed wrapper so a declared toast lands on the requested corner
        b.open_tag('div', {'class': f'q-toast-container q-toast-{position}'})
        b.indent()

        toast_attrs = {'class': f'q-toast q-toast-{variant}', 'id': toast_id, 'role': 'status'}
        if node.show:
            # Hidden until the bound variable becomes truthy (SHOW_BINDING_JS)
            self._has_show_bindings = True
            toast_attrs['data-q-show'] = node.show
            toast_attrs['style'] = 'display: none'
        attrs = self._merge_attrs(toast_attrs, self._layout_attrs(node))
        b.open_tag('div', attrs)
        b.indent()

        icon = node.icon or TOAST_ICONS.get(variant, TOAST_ICONS['info'])
        b.open_tag('span', {'class': 'q-toast-icon', 'aria-hidden': 'true'})
        b.indent()
        b.text(icon)
        b.dedent()
        b.close_tag('span')

        b.open_tag('div', {'class': 'q-toast-content'})
        b.indent()
        if node.title:
            b.open_tag('div', {'class': 'q-toast-title'})
            b.indent()
            b.text(node.title)
            b.dedent()
            b.close_tag('div')
        b.open_tag('div', {'class': 'q-toast-message'})
        b.indent()
        b.text(node.message)
        b.dedent()
        b.close_tag('div')
        b.dedent()
        b.close_tag('div')

        if dismissible:
            actions = []
            if node.on_close:
                if self._desktop_mode:
                    actions.append(f"__quantumCall({self._js_str(node.on_close)});")
                else:
                    actions.append(self._js_statement(node.on_close, self._js_str(toast_id)))
            actions.append(f"__quantumToast.dismiss({self._js_str(toast_id)});")
            b.open_tag('button', {'class': 'q-toast-close', 'type': 'button',
                                  'aria-label': 'Close', 'onclick': ' '.join(actions)})
            b.indent()
            b.text('&times;')
            b.dedent()
            b.close_tag('button')

        b.dedent()
        b.close_tag('div')
        b.dedent()
        b.close_tag('div')

        # Auto-dismiss (skipped while a show-binding controls visibility)
        if duration > 0 and not node.show:
            self._component_inits.append(
                f"setTimeout(function() {{ if (window.__quantumToast) "
                f"__quantumToast.dismiss({self._js_str(toast_id)}); }}, {duration});"
            )

    def _render_toast_container(self, node: UIToastContainerNode, b: HtmlBuilder):
        """Render ui:toast-container and make it the sink for runtime toasts."""
        self._features_used.add('toast')
        self._has_toast = True
        self._toast_container_counter += 1

        container_id = node.ui_id or f'q-toast-container-{self._toast_container_counter}'
        position = node.position or 'top-right'
        max_toasts = self._as_int(node.max_toasts, 5)

        base = {'class': f'q-toast-container q-toast-{position}', 'id': container_id,
                'data-max-toasts': str(max_toasts), 'aria-live': 'polite', 'role': 'region'}
        attrs = self._merge_attrs(base, self._layout_attrs(node))
        b.open_tag('div', attrs)
        b.close_tag('div')

        cid = self._js_str(container_id)
        pos = self._js_str(position)
        self._component_inits.append(f"""(function() {{
    var container = document.getElementById({cid});
    if (!container || !window.__quantumToast) return;
    var max = {max_toasts};
    var showToast = __quantumToast.show;
    __quantumToast.show = function(options) {{
        options = options || {{}};
        if (!options.position) options.position = {pos};
        var id = showToast(options);
        if (options.position === {pos}) {{
            var toast = document.getElementById(id);
            if (toast) container.appendChild(toast);
            // Toasts already fading out do not count towards the limit
            var items = container.querySelectorAll('.q-toast:not(.q-toast-out)');
            for (var i = 0; i < items.length - max; i++) {{
                __quantumToast.dismiss(items[i].id);
            }}
        }}
        return id;
    }};
    ['info', 'success', 'warning', 'danger'].forEach(function(variant) {{
        __quantumToast[variant] = function(message, options) {{
            options = options || {{}};
            options.message = message;
            options.variant = variant;
            return __quantumToast.show(options);
        }};
    }});
    __quantumToast.error = __quantumToast.danger;
}})();""")

    # ------------------------------------------------------------------
    # Carousel renders
    # ------------------------------------------------------------------

    def _render_carousel(self, node: UICarouselNode, b: HtmlBuilder):
        """Render ui:carousel with track, arrows and indicators."""
        self._features_used.add('carousel')
        self._has_carousel = True
        self._carousel_counter += 1

        carousel_id = node.ui_id or f'q-carousel-{self._carousel_counter}'
        animation = node.animation or 'slide'
        show_arrows = self._as_bool(node.show_arrows, True)
        show_indicators = self._as_bool(node.show_indicators, True)
        auto_play = self._as_bool(node.auto_play, False)
        loop = self._as_bool(node.loop, True)
        interval = self._as_int(node.interval, 5000)

        # Slides: explicit ui:slide children, otherwise one slide per child
        slide_nodes = [c for c in node.children if isinstance(c, UISlideNode)]
        if slide_nodes:
            slides = [(s, s.children) for s in slide_nodes]
        else:
            slides = [(None, [c]) for c in node.children]

        total = len(slides)
        current = self._as_int(node.current, 0)
        current = max(0, min(current, total - 1)) if total else 0

        cls = 'q-carousel'
        if animation == 'fade':
            cls += ' q-carousel-fade'
        attrs = self._merge_attrs({'class': cls, 'id': carousel_id}, self._layout_attrs(node))
        b.open_tag('div', attrs)
        b.indent()

        b.open_tag('div', {'class': 'q-carousel-track'})
        b.indent()
        for i, (slide_node, children) in enumerate(slides):
            slide_cls = 'q-carousel-slide'
            if i == current:
                slide_cls += ' active'
            slide_attrs = {'class': slide_cls, 'data-slide': str(i)}
            if slide_node is not None:
                slide_attrs = self._merge_attrs(slide_attrs, self._layout_attrs(slide_node))
            b.open_tag('div', slide_attrs)
            b.indent()
            self._render_children(children, b)
            b.dedent()
            b.close_tag('div')
        b.dedent()
        b.close_tag('div')

        if show_arrows and total > 1:
            b.open_tag('button', {'class': 'q-carousel-arrow q-carousel-prev', 'type': 'button',
                                  'aria-label': 'Previous slide'})
            b.indent()
            b.text('&#10094;')
            b.dedent()
            b.close_tag('button')
            b.open_tag('button', {'class': 'q-carousel-arrow q-carousel-next', 'type': 'button',
                                  'aria-label': 'Next slide'})
            b.indent()
            b.text('&#10095;')
            b.dedent()
            b.close_tag('button')

        if show_indicators and total > 1:
            b.open_tag('div', {'class': 'q-carousel-indicators'})
            b.indent()
            for i in range(total):
                ind_cls = 'q-carousel-indicator' + (' active' if i == current else '')
                b.open_tag('button', {'class': ind_cls, 'type': 'button',
                                      'aria-label': f'Go to slide {i + 1}'})
                b.close_tag('button')
            b.dedent()
            b.close_tag('div')

        b.dedent()
        b.close_tag('div')

        options = {
            'current': str(current),
            'autoPlay': self._js_bool(auto_play),
            'interval': str(interval),
            'loop': self._js_bool(loop),
            'animation': self._js_str(animation),
        }
        on_change = self._js_change_handler(node.on_change, node.bind, 'index')
        if on_change:
            options['onChange'] = on_change

        cid = self._js_str(carousel_id)
        self._component_inits.append(f"""(function() {{
    if (!window.__quantumCarousel) return;
    var api = __quantumCarousel.init({cid}, {self._js_options(options)});
    var state = __quantumCarousel.get({cid});
    if (api && state) {{
        for (var key in api) {{ state[key] = api[key]; }}
    }}
}})();""")

    def _render_slide(self, node: UISlideNode, b: HtmlBuilder):
        """Render a standalone ui:slide (outside a carousel)."""
        attrs = self._merge_attrs({'class': 'q-carousel-slide'}, self._layout_attrs(node))
        b.open_tag('div', attrs)
        b.indent()
        self._render_children(node.children, b)
        b.dedent()
        b.close_tag('div')

    # ------------------------------------------------------------------
    # Stepper renders
    # ------------------------------------------------------------------

    def _render_stepper(self, node: UIStepperNode, b: HtmlBuilder):
        """Render ui:stepper with step indicators and per-step content."""
        self._features_used.add('stepper')
        self._has_stepper = True
        self._stepper_counter += 1

        stepper_id = node.ui_id or f'q-stepper-{self._stepper_counter}'
        orientation = node.orientation or 'horizontal'
        show_labels = self._as_bool(node.show_labels, True)
        clickable = self._as_bool(node.clickable, False)
        linear = self._as_bool(node.linear, True)

        steps = [c for c in node.children if isinstance(c, UIStepNode)]
        total = len(steps)
        current = self._as_int(node.current, 0)
        current = max(0, min(current, total - 1)) if total else 0

        completed = completed_step_indices(steps, current)

        attrs = self._merge_attrs(
            {'class': f'q-stepper q-stepper-{orientation}', 'id': stepper_id},
            self._layout_attrs(node))
        b.open_tag('div', attrs)
        b.indent()

        # Step indicators
        b.open_tag('div', {'class': 'q-stepper-header'})
        b.indent()
        for i, step in enumerate(steps):
            item_cls = 'q-step-item'
            if i == current:
                item_cls += ' active'
            elif i in completed:
                item_cls += ' completed'
            if step.error:
                item_cls += ' error'
            b.open_tag('div', {'class': item_cls, 'data-step': str(i)})
            b.indent()

            b.open_tag('div', {'class': 'q-step-indicator'})
            b.indent()
            b.text(step.icon if step.icon else str(i + 1))
            b.dedent()
            b.close_tag('div')

            if show_labels and (step.title or step.description or step.error):
                b.open_tag('div', {'class': 'q-step-labels'})
                b.indent()
                if step.title:
                    b.open_tag('div', {'class': 'q-step-title'})
                    b.indent()
                    b.text(step.title)
                    b.dedent()
                    b.close_tag('div')
                if step.description:
                    b.open_tag('div', {'class': 'q-step-description'})
                    b.indent()
                    b.text(step.description)
                    b.dedent()
                    b.close_tag('div')
                if step.error:
                    b.open_tag('div', {'class': 'q-step-description q-step-error'})
                    b.indent()
                    b.text(step.error)
                    b.dedent()
                    b.close_tag('div')
                if self._as_bool(step.optional, False):
                    b.open_tag('div', {'class': 'q-step-optional'})
                    b.indent()
                    b.text('Optional')
                    b.dedent()
                    b.close_tag('div')
                b.dedent()
                b.close_tag('div')

            if i < total - 1:
                b.open_tag('div', {'class': 'q-step-connector'})
                b.close_tag('div')

            b.dedent()
            b.close_tag('div')
        b.dedent()
        b.close_tag('div')

        # Step contents (only the current one is visible)
        b.open_tag('div', {'class': 'q-stepper-content'})
        b.indent()
        for i, step in enumerate(steps):
            content_cls = 'q-step-content' + (' active' if i == current else '')
            content_attrs = self._merge_attrs({'class': content_cls, 'data-step': str(i)},
                                              self._layout_attrs(step))
            b.open_tag('div', content_attrs)
            b.indent()
            self._render_children(step.children, b)
            b.dedent()
            b.close_tag('div')
        b.dedent()
        b.close_tag('div')

        b.dedent()
        b.close_tag('div')

        options = {
            'current': str(current),
            'linear': self._js_bool(linear),
            'clickable': self._js_bool(clickable),
        }
        on_change = self._js_change_handler(node.on_change, node.bind, 'index')
        if on_change:
            options['onChange'] = on_change
        if node.on_complete:
            if self._desktop_mode:
                complete_body = f"__quantumCall({self._js_str(node.on_complete)});"
            else:
                complete_body = self._js_statement(node.on_complete, '')
            options['onComplete'] = 'function() { ' + complete_body + ' }'

        sid = self._js_str(stepper_id)
        completed_js = '[' + ', '.join(str(i) for i in completed) + ']'
        self._component_inits.append(f"""(function() {{
    if (!window.__quantumStepper) return;
    var api = __quantumStepper.init({sid}, {self._js_options(options)});
    var state = __quantumStepper.get({sid});
    if (!api || !state) return;
    for (var key in api) {{ state[key] = api[key]; }}
    {completed_js}.forEach(function(index) {{ api.complete(index); }});
}})();""")

    def _render_step(self, node: UIStepNode, b: HtmlBuilder):
        """Render a standalone ui:step (outside a stepper)."""
        attrs = self._merge_attrs({'class': 'q-step-item'}, self._layout_attrs(node))
        b.open_tag('div', attrs)
        b.indent()
        if node.title or node.description:
            b.open_tag('div', {'class': 'q-step-labels'})
            b.indent()
            if node.title:
                b.open_tag('div', {'class': 'q-step-title'})
                b.indent()
                b.text(node.title)
                b.dedent()
                b.close_tag('div')
            if node.description:
                b.open_tag('div', {'class': 'q-step-description'})
                b.indent()
                b.text(node.description)
                b.dedent()
                b.close_tag('div')
            b.dedent()
            b.close_tag('div')
        b.open_tag('div', {'class': 'q-step-content active'})
        b.indent()
        self._render_children(node.children, b)
        b.dedent()
        b.close_tag('div')
        b.dedent()
        b.close_tag('div')

    # ------------------------------------------------------------------
    # Calendar / date picker renders
    # ------------------------------------------------------------------

    def _calendar_settings(self, node) -> Dict:
        """Collect the parsed calendar configuration shared by both renders."""
        mode = getattr(node, 'mode', 'single') or 'single'
        raw = [v.strip() for v in str(getattr(node, 'value', '') or '').split(',') if v.strip()]
        dates = [d for d in (self._parse_iso_date(v) for v in raw) if d]
        disabled_dates = {d for d in
                          (self._parse_iso_date(v) for v in
                           str(getattr(node, 'disabled_dates', '') or '').split(','))
                          if d}
        disabled_days = {self._as_int(v, -1) for v in
                         str(getattr(node, 'disabled_days', '') or '').split(',') if v.strip()}
        return {
            'mode': mode,
            'selected': dates[0] if dates else None,
            'range_start': dates[0] if mode == 'range' and dates else None,
            'range_end': dates[1] if mode == 'range' and len(dates) > 1 else None,
            'multiple': dates if mode == 'multiple' else [],
            'min_date': self._parse_iso_date(getattr(node, 'min_date', None)),
            'max_date': self._parse_iso_date(getattr(node, 'max_date', None)),
            'disabled_dates': disabled_dates,
            'disabled_days': disabled_days,
            'first_day': self._as_int(getattr(node, 'first_day_of_week', 0), 0) % 7,
            'show_weeks': self._as_bool(getattr(node, 'show_week_numbers', False), False),
        }

    def _calendar_day_disabled(self, day: _date, settings: Dict) -> bool:
        """Whether a day cannot be selected (min/max, weekday or explicit list)."""
        if settings['min_date'] and day < settings['min_date']:
            return True
        if settings['max_date'] and day > settings['max_date']:
            return True
        # JS weekday numbering: 0 = Sunday
        if ((day.weekday() + 1) % 7) in settings['disabled_days']:
            return True
        return day in settings['disabled_dates']

    def _calendar_selection_classes(self, day: _date, settings: Dict) -> List[str]:
        """Selection related CSS classes for a single day cell."""
        mode = settings['mode']
        classes: List[str] = []
        if mode == 'range':
            if settings['range_start'] == day:
                classes.extend(['range-start', 'selected'])
            if settings['range_end'] == day:
                classes.extend(['range-end', 'selected'])
            if (settings['range_start'] and settings['range_end']
                    and settings['range_start'] < day < settings['range_end']):
                classes.append('in-range')
        elif mode == 'multiple':
            if day in settings['multiple']:
                classes.append('selected')
        elif settings['selected'] == day:
            classes.append('selected')
        return classes

    # The month navigation buttons carry .q-calendar-nav themselves (that is
    # what CALENDAR_JS renders), while CSS_THEME styles `.q-calendar-nav button`.
    CALENDAR_NAV_CSS = (
        ".q-calendar-header .q-calendar-nav { display: inline-flex; align-items: center;"
        " justify-content: center; width: 28px; height: 28px; background: none;"
        " border: 1px solid var(--q-border); border-radius: var(--q-radius); cursor: pointer; }\n"
        ".q-calendar-header .q-calendar-nav:hover { background: var(--q-light); }"
    )

    def _render_calendar_markup(self, b: HtmlBuilder, target_id: str, settings: Dict):
        """Render the month header and day grid of a calendar.

        The markup mirrors what CALENDAR_JS re-renders on interaction, so the
        page shows a usable month grid before (and without) JavaScript.
        """
        if self.CALENDAR_NAV_CSS not in self._extra_css:
            self._extra_css.append(self.CALENDAR_NAV_CSS)
        today = _date.today()
        year, month = today.year, today.month
        target = self._js_str(target_id)

        # Same element shape CALENDAR_JS re-renders, so markup stays stable
        # once the runtime takes over.
        b.open_tag('div', {'class': 'q-calendar-header'})
        b.indent()
        b.open_tag('button', {'class': 'q-calendar-nav', 'type': 'button',
                              'aria-label': 'Previous month',
                              'onclick': f"__quantumCalendar.prevMonth({target})"})
        b.indent()
        b.text('&lsaquo;')
        b.dedent()
        b.close_tag('button')
        b.open_tag('span', {'class': 'q-calendar-title'})
        b.indent()
        b.text(f'{MONTH_NAMES[month - 1]} {year}')
        b.dedent()
        b.close_tag('span')
        b.open_tag('button', {'class': 'q-calendar-nav', 'type': 'button',
                              'aria-label': 'Next month',
                              'onclick': f"__quantumCalendar.nextMonth({target})"})
        b.indent()
        b.text('&rsaquo;')
        b.dedent()
        b.close_tag('button')
        b.dedent()
        b.close_tag('div')

        first_day = settings['first_day']
        b.open_tag('div', {'class': 'q-calendar-grid'})
        b.indent()

        if settings['show_weeks']:
            b.open_tag('div', {'class': 'q-calendar-weekday'})
            b.close_tag('div')
        for name in DAY_NAMES[first_day:] + DAY_NAMES[:first_day]:
            b.open_tag('div', {'class': 'q-calendar-weekday'})
            b.indent()
            b.text(name)
            b.dedent()
            b.close_tag('div')

        # calendar.Calendar uses 0 = Monday, the node uses 0 = Sunday
        weeks = _calendar.Calendar((first_day + 6) % 7).monthdatescalendar(year, month)
        for week in weeks:
            if settings['show_weeks']:
                b.open_tag('div', {'class': 'q-calendar-day week-number'})
                b.indent()
                b.text(str(week[0].isocalendar()[1]))
                b.dedent()
                b.close_tag('div')
            for day in week:
                classes = ['q-calendar-day']
                onclick = None
                if day.month != month:
                    classes.append('other-month')
                else:
                    if day == today:
                        classes.append('today')
                    if self._calendar_day_disabled(day, settings):
                        classes.append('disabled')
                    else:
                        onclick = f"__quantumCalendar.selectDate({target}, {day.day})"
                    classes.extend(self._calendar_selection_classes(day, settings))
                day_attrs = {'class': ' '.join(classes)}
                if onclick:
                    day_attrs['onclick'] = onclick
                    day_attrs['role'] = 'button'
                b.open_tag('div', day_attrs)
                b.indent()
                b.text(str(day.day))
                b.dedent()
                b.close_tag('div')

        b.dedent()
        b.close_tag('div')

    def _calendar_init_options(self, node, settings: Dict,
                               on_change: Optional[str]) -> Dict[str, str]:
        """Build the option literal handed to __quantumCalendar.init."""
        options = {
            'mode': self._js_str(settings['mode']),
            'firstDayOfWeek': str(settings['first_day']),
            'showWeekNumbers': self._js_bool(settings['show_weeks']),
        }
        if getattr(node, 'value', None):
            options['value'] = self._js_str(node.value)
        if getattr(node, 'min_date', None):
            options['minDate'] = self._js_str(node.min_date)
        if getattr(node, 'max_date', None):
            options['maxDate'] = self._js_str(node.max_date)
        if getattr(node, 'disabled_dates', None):
            options['disabledDates'] = self._js_str(node.disabled_dates)
        if getattr(node, 'disabled_days', None):
            options['disabledDays'] = self._js_str(node.disabled_days)
        if on_change:
            options['onChange'] = on_change
        return options

    def _calendar_init_script(self, calendar_id: str, options: Dict[str, str],
                              show_weeks: bool) -> str:
        """Boot a calendar and expose its API through __quantumCalendar.get()."""
        cid = self._js_str(calendar_id)
        weeks_block = ''
        if show_weeks:
            weeks_block = f"""
    ['selectDate', 'prevMonth', 'nextMonth'].forEach(function(name) {{
        var fn = api[name];
        state[name] = function() {{
            var result = fn.apply(null, arguments);
            __quantumCalendarWeeks.apply({cid});
            return result;
        }};
    }});
    __quantumCalendarWeeks.apply({cid});"""
        return f"""(function() {{
    if (!window.__quantumCalendar) return;
    var api = __quantumCalendar.init({cid}, {self._js_options(options)});
    var state = __quantumCalendar.get({cid});
    if (!api || !state) return;
    for (var key in api) {{ state[key] = api[key]; }}{weeks_block}
}})();"""

    def _render_calendar(self, node: UICalendarNode, b: HtmlBuilder):
        """Render ui:calendar as an interactive month grid."""
        self._features_used.add('calendar')
        self._has_calendar = True
        self._calendar_counter += 1

        calendar_id = node.ui_id or f'q-calendar-{self._calendar_counter}'
        settings = self._calendar_settings(node)

        attrs = self._merge_attrs(
            {'class': 'q-calendar', 'id': calendar_id, 'data-mode': settings['mode']},
            self._layout_attrs(node))
        b.open_tag('div', attrs)
        b.indent()
        self._render_calendar_markup(b, calendar_id, settings)
        b.dedent()
        b.close_tag('div')

        if settings['show_weeks']:
            self._has_calendar_weeks = True
            # One extra column for the week numbers
            self._extra_css.append(
                f"#{calendar_id} .q-calendar-grid {{ grid-template-columns: repeat(8, 1fr); }}")

        on_change = self._js_change_handler(node.on_change, node.bind, 'value')
        options = self._calendar_init_options(node, settings, on_change)
        self._component_inits.append(
            self._calendar_init_script(calendar_id, options, settings['show_weeks']))

    def _render_date_picker(self, node: UIDatePickerNode, b: HtmlBuilder):
        """Render ui:date-picker as an input backed by a calendar popup."""
        self._features_used.add('date_picker')
        self._has_date_picker = True
        self._date_picker_counter += 1

        picker_id = node.ui_id or f'q-date-picker-{self._date_picker_counter}'
        pattern = node.format or 'YYYY-MM-DD'
        selected = self._parse_iso_date(node.value)
        disabled = self._as_bool(node.disabled, False)
        clearable = self._as_bool(node.clearable, True)
        required = self._as_bool(node.required, False)

        settings = self._calendar_settings(node)
        settings['mode'] = 'single'

        attrs = self._merge_attrs({'class': 'q-date-picker', 'id': picker_id},
                                  self._layout_attrs(node))
        b.open_tag('div', attrs)
        b.indent()

        input_attrs = {
            'type': 'text',
            'class': 'q-date-picker-input',
            'id': f'{picker_id}-input',
            'value': self._format_date(selected, pattern) if selected else '',
            'placeholder': node.placeholder or 'Select date',
            'data-format': pattern,
            'autocomplete': 'off',
            'aria-haspopup': 'dialog',
            'readonly': True,
        }
        if required:
            input_attrs['required'] = True
        if disabled:
            input_attrs['disabled'] = True
        b.open_tag('input', input_attrs, self_closing=True)

        # Canonical ISO value, so forms submit a machine readable date
        hidden_attrs = {'type': 'hidden', 'id': f'{picker_id}-value',
                        'value': selected.isoformat() if selected else ''}
        if node.bind:
            hidden_attrs['name'] = node.bind
        b.open_tag('input', hidden_attrs, self_closing=True)

        if clearable and not disabled:
            b.open_tag('button', {
                'class': 'q-date-picker-clear', 'type': 'button', 'aria-label': 'Clear date',
                'onclick': f"__quantumDatePicker.clear({self._js_str(picker_id)})"})
            b.indent()
            b.text('&times;')
            b.dedent()
            b.close_tag('button')

        b.open_tag('span', {'class': 'q-date-picker-icon', 'aria-hidden': 'true'})
        b.indent()
        b.text('&#128197;')
        b.dedent()
        b.close_tag('span')

        calendar_id = f'{picker_id}-cal'
        b.open_tag('div', {'class': 'q-date-picker-dropdown', 'id': f'{picker_id}-dropdown',
                           'role': 'dialog'})
        b.indent()
        b.open_tag('div', {'class': 'q-calendar', 'id': calendar_id, 'data-mode': 'single'})
        b.indent()
        self._render_calendar_markup(b, calendar_id, settings)
        b.dedent()
        b.close_tag('div')
        b.dedent()
        b.close_tag('div')

        b.dedent()
        b.close_tag('div')

        pid = self._js_str(picker_id)
        picker_change = (f"function(value) {{ __quantumDatePicker.setValue({pid}, value); }}")
        options = self._calendar_init_options(node, settings, picker_change)
        options['mode'] = self._js_str('single')

        register_options = {
            'format': self._js_str(pattern),
            'disabled': self._js_bool(disabled),
        }
        on_change = self._js_change_handler(node.on_change, node.bind, 'value')
        if on_change:
            register_options['onChange'] = on_change

        init = self._calendar_init_script(calendar_id, options, settings['show_weeks'])
        init += (f"\nif (window.__quantumDatePicker) __quantumDatePicker.register({pid}, "
                 f"{self._js_options(register_options)});")
        self._component_inits.append(init)
