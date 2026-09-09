"""
UI Engine - Textual Adapter

Transforms UI AST nodes into a standalone Python Textual (TUI) application.
Uses the design tokens system for normalized styling across targets.
"""

from datetime import date as _date
from typing import Any, List, Optional, Set, Dict

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
    UICarouselNode, UISlideNode, UIStepperNode, UIStepNode,
    UICalendarNode, UIDatePickerNode, UIToastNode, UIToastContainerNode,
)
from quantum.runtime.terminal_templates import PyBuilder, py_string, py_id
from quantum.runtime.ui_tokens import TokenConverter, get_compatibility_warnings
from quantum.runtime.ui_html_adapter import completed_step_indices


# ==========================================================================
# Generated runtime helpers
#
# These blocks are emitted (verbatim, at class level) into the generated
# Textual app only when the matching ui: component is present in the AST.
# ==========================================================================

_CAROUSEL_METHODS = '''
def _q_carousel_init(self) -> None:
    """Set the initial slide / indicator and start auto-play timers."""
    for cid, info in self._q_carousels.items():
        info["index"] = max(0, min(info["index"], len(info["slides"]) - 1))
        self._q_carousel_apply(cid)
        if info["auto_play"] and len(info["slides"]) > 1:
            self.set_interval(info["interval"], lambda cid=cid: self._q_carousel_go(cid, 1))

def _q_carousel_apply(self, cid: str) -> None:
    """Show the current slide of one carousel and refresh its indicator."""
    info = self._q_carousels[cid]
    index = info["index"]
    self.query_one("#" + cid + "__switcher", ContentSwitcher).current = info["slides"][index]
    for indicator in self.query("#" + cid + "__indicator"):
        indicator.update("%d / %d" % (index + 1, len(info["slides"])))
    if info["bind"]:
        self._q_set_state(info["bind"], index)

def _q_carousel_go(self, cid: str, delta: int) -> None:
    """Move a carousel by delta slides (honouring the loop attribute)."""
    info = self._q_carousels[cid]
    total = len(info["slides"])
    index = info["index"] + delta
    if info["loop"]:
        index %= total
    else:
        index = max(0, min(total - 1, index))
    info["index"] = index
    self._q_carousel_apply(cid)

def _q_carousel_focused(self) -> str:
    """The carousel that currently holds focus, else the first one."""
    node = self.focused
    while node is not None:
        if getattr(node, "id", None) in self._q_carousels:
            return node.id
        node = node.parent
    return next(iter(self._q_carousels))

def action_q_carousel_next(self) -> None:
    self._q_carousel_go(self._q_carousel_focused(), 1)

def action_q_carousel_prev(self) -> None:
    self._q_carousel_go(self._q_carousel_focused(), -1)
'''


_STEPPER_METHODS = '''
def _q_stepper_init(self) -> None:
    for sid in self._q_steppers:
        self._q_stepper_apply(sid)

def _q_stepper_apply(self, sid: str) -> None:
    """Show the current step and repaint the step indicators."""
    info = self._q_steppers[sid]
    steps = info["steps"]
    index = info["index"]
    self.query_one("#" + sid + "__switcher", ContentSwitcher).current = steps[index]
    explicit = info.get("explicit_done") or {}
    for position in range(len(steps)):
        # Mesma regra do adapter html: a marca explicita vence; sem ela, o
        # passo esta concluido se esta atras do atual.
        done = explicit[position] if position in explicit else position < index
        for indicator in self.query("#" + sid + "__ind_" + str(position)):
            indicator.set_class(position == index, "q-step-active")
            indicator.set_class(done, "q-step-done")
    for button in self.query("#" + sid + "__prev"):
        button.disabled = index == 0
    for button in self.query("#" + sid + "__next"):
        button.disabled = index >= len(steps) - 1
    if info["bind"]:
        self._q_set_state(info["bind"], index)

def _q_stepper_goto(self, sid: str, index: int) -> None:
    """Jump to a step. A linear stepper never skips ahead more than one step."""
    info = self._q_steppers[sid]
    if info["linear"] and index > info["index"] + 1:
        index = info["index"] + 1
    info["index"] = max(0, min(len(info["steps"]) - 1, index))
    self._q_stepper_apply(sid)

def _q_stepper_focused(self) -> str:
    node = self.focused
    while node is not None:
        if getattr(node, "id", None) in self._q_steppers:
            return node.id
        node = node.parent
    return next(iter(self._q_steppers))

def action_q_stepper_next(self) -> None:
    sid = self._q_stepper_focused()
    self._q_stepper_goto(sid, self._q_steppers[sid]["index"] + 1)

def action_q_stepper_prev(self) -> None:
    sid = self._q_stepper_focused()
    self._q_stepper_goto(sid, self._q_steppers[sid]["index"] - 1)
'''


_CALENDAR_METHODS = '''
def _q_calendar_init(self) -> None:
    for cid, info in self._q_calendars.items():
        anchor = info["selected"][0] if info["selected"] else date.today()
        info["year"] = anchor.year
        info["month"] = anchor.month
        self._q_calendar_render(cid)

def _q_calendar_labels(self, cid: str):
    """Weekday abbreviations + month title, localised when the locale exists."""
    info = self._q_calendars[cid]
    first = (info["first_day"] - 1) % 7
    if info["locale"]:
        try:
            localized = calendar.LocaleTextCalendar(first, info["locale"])
            heads = localized.formatweekheader(3).split()
            title = localized.formatmonthname(info["year"], info["month"], 0, withyear=True).strip()
            if len(heads) == 7 and title:
                return heads, title
        except Exception:
            pass
    heads = [calendar.day_abbr[(first + offset) % 7] for offset in range(7)]
    return heads, "%s %d" % (calendar.month_name[info["month"]], info["year"])

def _q_calendar_disabled(self, cid: str, day) -> bool:
    info = self._q_calendars[cid]
    if info["min"] and day < info["min"]:
        return True
    if info["max"] and day > info["max"]:
        return True
    if day.isoformat() in info["disabled_dates"]:
        return True
    return ((day.weekday() + 1) % 7) in info["disabled_days"]

def _q_calendar_render(self, cid: str) -> None:
    """Repaint the month grid. info["cells"] maps grid coordinates to dates."""
    info = self._q_calendars[cid]
    heads, title = self._q_calendar_labels(cid)
    table = self.query_one("#" + cid + "__grid", DataTable)
    table.clear(columns=True)
    table.add_columns(*((["Wk"] if info["week_numbers"] else []) + heads))
    selected = info["selected"]
    in_range = info["mode"] == "range" and len(selected) == 2
    info["cells"] = []
    for week in calendar.Calendar((info["first_day"] - 1) % 7).monthdatescalendar(
            info["year"], info["month"]):
        row = []
        cells = []
        if info["week_numbers"]:
            row.append(Text(str(week[0].isocalendar()[1]), style="dim"))
            cells.append(None)
        for day in week:
            if day.month != info["month"]:
                row.append(Text(""))
                cells.append(None)
                continue
            if self._q_calendar_disabled(cid, day):
                row.append(Text(str(day.day), style="dim strike"))
                cells.append(None)
                continue
            if day in selected:
                row.append(Text(str(day.day), style="reverse bold"))
            elif in_range and selected[0] < day < selected[1]:
                row.append(Text(str(day.day), style="underline"))
            else:
                row.append(Text(str(day.day)))
            cells.append(day)
        table.add_row(*row)
        info["cells"].append(cells)
    for label in self.query("#" + cid + "__title"):
        label.update(title)
    self._q_calendar_show_value(cid)

def _q_calendar_show_value(self, cid: str) -> None:
    info = self._q_calendars[cid]
    selected = info["selected"]
    if info["mode"] == "range" and len(selected) == 2:
        text = selected[0].isoformat() + " -> " + selected[1].isoformat()
    else:
        text = ", ".join(day.isoformat() for day in selected)
    if info["bind"]:
        self._q_set_state(info["bind"], text)
    for label in self.query("#" + cid + "__value"):
        label.update(text or "No date selected")

def _q_calendar_move(self, cid: str, delta: int) -> None:
    info = self._q_calendars[cid]
    month = info["month"] + delta - 1
    info["year"] = info["year"] + month // 12
    info["month"] = month % 12 + 1
    self._q_calendar_render(cid)

def _q_calendar_select(self, cid: str, day) -> None:
    info = self._q_calendars[cid]
    selected = info["selected"]
    if info["mode"] == "multiple":
        if day in selected:
            selected.remove(day)
        else:
            selected.append(day)
            selected.sort()
    elif info["mode"] == "range":
        if len(selected) == 1 and day != selected[0]:
            selected[:] = sorted([selected[0], day])
        else:
            selected[:] = [day]
    else:
        selected[:] = [day]
    self._q_calendar_render(cid)

def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
    table_id = event.data_table.id or ""
    if not table_id.endswith("__grid"):
        return
    info = self._q_calendars.get(table_id[: -len("__grid")])
    if info is None:
        return
    row = event.coordinate.row
    column = event.coordinate.column
    if row >= len(info["cells"]) or column >= len(info["cells"][row]):
        return
    day = info["cells"][row][column]
    if day is not None:
        self._q_calendar_select(table_id[: -len("__grid")], day)
'''


_DATE_PICKER_METHODS = '''
def _q_date_picker_init(self) -> None:
    for pid in self._q_date_pickers:
        value = ""
        for field in self.query("#" + pid + "__input"):
            value = field.value
        self._q_date_validate(pid, value)

def _q_date_validate(self, pid: str, raw: str) -> None:
    """Parse the typed date against the declared format / min / max."""
    info = self._q_date_pickers[pid]
    raw = (raw or "").strip()
    valid = True
    value = ""
    message = info["format"]
    if not raw:
        if info["required"]:
            valid = False
            message = "This date is required"
    else:
        try:
            parsed = datetime.strptime(raw, info["strptime"]).date()
        except ValueError:
            valid = False
            message = "Expected format: " + info["format"]
        else:
            if info["min"] and parsed < info["min"]:
                valid = False
                message = "Earliest allowed: " + info["min"].isoformat()
            elif info["max"] and parsed > info["max"]:
                valid = False
                message = "Latest allowed: " + info["max"].isoformat()
            else:
                value = parsed.isoformat()
                message = parsed.strftime(info["strptime"])
    for hint in self.query("#" + pid + "__hint"):
        hint.update(message)
        hint.set_class(not valid, "q-invalid")
    for field in self.query("#" + pid + "__input"):
        field.set_class(not valid, "q-invalid")
    if info["bind"]:
        self._q_set_state(info["bind"], value)

def on_input_changed(self, event: Input.Changed) -> None:
    input_id = event.input.id or ""
    if input_id.endswith("__input") and input_id[: -len("__input")] in self._q_date_pickers:
        self._q_date_validate(input_id[: -len("__input")], event.value)
'''


_STATE_ACCESSOR = '''
def _q_truthy(self, value) -> bool:
    """Mesma nocao de verdadeiro que o alvo html usa num binding."""
    if value is None or value is False:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in ('', 'false', '0', 'no', 'off')
    return bool(value)

def _q_set_state(self, name: str, value) -> None:
    """Ponto unico de escrita do estado ligado por bind=.

    Os widgets escreviam direto em self._q_state, entao nada podia REAGIR a
    uma mudanca — e era por isso que `show=` de um ui:toast so podia virar
    comentario. Com um ponto unico, quem precisa observar, observa.
    """
    self._q_state[name] = value
    reagir = getattr(self, '_q_toast_on_state', None)
    if reagir is not None:
        reagir(name)

def q_state(self) -> dict:
    """Current value of every bound ui: widget (bind="..." attributes)."""
    return dict(self._q_state)
'''


class UITextualAdapter:
    """Generates Python Textual app from UI AST nodes."""

    # ui:toast position -> Textual ToastRack `align` value
    TOAST_ALIGN = {
        'top-right': 'right top',
        'top-left': 'left top',
        'bottom-right': 'right bottom',
        'bottom-left': 'left bottom',
        'top-center': 'center top',
        'bottom-center': 'center bottom',
    }

    # ui:toast variant -> Textual notification severity
    TOAST_SEVERITY = {
        'info': 'information',
        'success': 'information',
        'warning': 'warning',
        'danger': 'error',
    }

    def __init__(self):
        self._indent = 2  # compose() body starts at indent 2
        self._tokens = TokenConverter('textual')
        self._features_used: Set[str] = set()
        self._css_rules: List[str] = []
        self._widget_counter = 0
        self._reset_component_state()

    def _reset_component_state(self):
        """Reset per-generation state for the stateful components."""
        self._extra_imports: List[str] = []
        self._datetime_imports: Set[str] = set()
        self._carousels: Dict[str, Dict[str, Any]] = {}
        self._steppers: Dict[str, Dict[str, Any]] = {}
        self._calendars: Dict[str, Dict[str, Any]] = {}
        self._date_pickers: Dict[str, Dict[str, Any]] = {}
        self._toasts: List[Dict[str, Any]] = []
        self._toast_rack_position: Optional[str] = None
        self._toast_first_position: Optional[str] = None
        self._max_toasts: Optional[int] = None

    def _next_id(self, prefix: str = 'q') -> str:
        """Generate unique widget ID."""
        self._widget_counter += 1
        return f"{prefix}_{self._widget_counter}"

    def _need_import(self, statement: str):
        """Register an import needed by a generated component (deduplicated)."""
        if statement not in self._extra_imports:
            self._extra_imports.append(statement)

    def _need_datetime(self, *names: str):
        """Register names for a single merged `from datetime import ...` line."""
        self._datetime_imports.update(names)

    # ------------------------------------------------------------------
    # Attribute coercion helpers
    #
    # AST nodes declare ints/bools, but attributes arriving straight from XML
    # are strings ("true", "3000"). Coerce defensively so a parser that keeps
    # the raw text still produces a working app.
    # ------------------------------------------------------------------

    @staticmethod
    def _as_int(value, default: int = 0) -> int:
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _as_bool(value, default: bool = False) -> bool:
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in ('true', '1', 'yes', 'on'):
            return True
        if text in ('false', '0', 'no', 'off', ''):
            return False
        return default

    def generate(self, windows: List[QuantumNode], ui_children: List[QuantumNode],
                 title: str = "Quantum UI") -> str:
        """Generate complete Python Textual app from UI AST."""
        # Reset state
        self._css_rules = []
        self._widget_counter = 0
        self._features_used = set()
        self._reset_component_state()

        py = PyBuilder()

        # Build compose body
        compose_lines = PyBuilder()
        compose_lines._indent = 2  # inside class > compose method

        # Render windows
        for window in windows:
            self._render_node(window, compose_lines)

        # Render top-level children
        for child in ui_children:
            self._render_node(child, compose_lines)

        compose_body = compose_lines.build()
        if not self._has_statement(compose_body):
            # Nothing (or only source-mapping comments) reached compose():
            # a bare comment body would be a syntax error.
            compose_body = f'{compose_body}\n        yield Static("Empty UI")'.lstrip('\n')

        # Build CSS
        css = self._build_css()

        # Use template
        from quantum.runtime.ui_textual_templates import UI_TEXTUAL_APP_TEMPLATE
        code = UI_TEXTUAL_APP_TEMPLATE.format(
            title=py_string(title),
            css=css,
            compose_body=compose_body,
            extra_imports=self._build_extra_imports(),
            bindings=self._build_bindings(),
            methods=self._build_methods(),
        )

        return code

    @staticmethod
    def _has_statement(body: str) -> bool:
        """True when a generated block contains real code (not just comments)."""
        return any(line.strip() and not line.strip().startswith('#')
                   for line in body.split('\n'))

    def _build_extra_imports(self) -> str:
        """Imports required by the generated components (empty when unused)."""
        lines = list(self._extra_imports)
        if self._datetime_imports:
            lines.append('from datetime import ' + ', '.join(sorted(self._datetime_imports)))
        return '\n'.join(lines)

    def _build_css(self) -> str:
        """Generate Textual CSS including dynamic rules from layout attributes."""
        base_css = [
            "/* Quantum UI Textual CSS */",
            "",
            "/* Base styles */",
            ".q-panel { border: solid $primary; padding: 1 2; }",
            ".q-panel-title { text-style: bold; color: $text; }",
            "",
            "/* Badge styles */",
            ".q-badge { padding: 0 1; }",
            ".q-badge-primary { background: $primary; color: $text; }",
            ".q-badge-secondary { background: $secondary; color: $text; }",
            ".q-badge-success { background: $success; color: $text; }",
            ".q-badge-danger { background: $error; color: $text; }",
            ".q-badge-warning { background: $warning; color: $text; }",
            "",
            "/* Image placeholder */",
            ".q-image-placeholder { color: $text-muted; text-style: italic; }",
            "",
            "/* Link style */",
            ".q-link { color: $primary; text-style: underline; }",
            "",
        ]

        # Component styles - only emitted when the component is actually used
        if self._carousels:
            base_css.extend([
                "/* Carousel */",
                ".q-carousel { height: auto; }",
                ".q-slide { height: auto; }",
                ".q-carousel-nav { height: auto; align-horizontal: center; }",
                ".q-carousel-arrow { min-width: 5; }",
                ".q-carousel-indicator { padding: 1 2; color: $text-muted; }",
                "",
            ])

        if self._steppers:
            base_css.extend([
                "/* Stepper */",
                ".q-stepper { height: auto; }",
                ".q-stepper-indicators { height: auto; }",
                ".q-step { height: auto; }",
                ".q-step-indicator { padding: 0 1; color: $text-muted; }",
                ".q-step-indicator.q-step-active { color: $primary; text-style: bold; }",
                ".q-step-indicator.q-step-done { color: $success; }",
                ".q-step-title { text-style: bold; }",
                ".q-step-description { color: $text-muted; text-style: italic; }",
                ".q-step-error { color: $error; }",
                ".q-stepper-nav { height: auto; align-horizontal: right; }",
                "",
            ])

        if self._calendars:
            base_css.extend([
                "/* Calendar */",
                ".q-calendar { height: auto; }",
                ".q-calendar-header { height: auto; align-horizontal: center; }",
                ".q-calendar-title { padding: 1 2; text-style: bold; }",
                ".q-calendar-nav { min-width: 5; }",
                ".q-calendar-grid { height: auto; max-height: 10; }",
                ".q-calendar-value { color: $text-muted; }",
                "",
            ])

        if self._date_pickers:
            base_css.extend([
                "/* Date picker */",
                ".q-date-picker { height: auto; }",
                ".q-date-picker-row { height: auto; }",
                ".q-date-picker-clear { min-width: 5; }",
                ".q-date-picker-hint { color: $text-muted; }",
                ".q-invalid { color: $error; }",
                "",
            ])

        if self._carousels or self._steppers:
            base_css.extend([
                "/* Empty container feedback */",
                ".q-empty { color: $text-muted; text-style: italic; }",
                "",
            ])

        toast_position = self._toast_rack_position or self._toast_first_position
        if toast_position:
            align = self.TOAST_ALIGN.get(toast_position, 'right bottom')
            base_css.extend([
                "/* Toast notifications (ui:toast-container position) */",
                f"ToastRack {{ align: {align}; }}",
                "",
            ])

        # Add dynamic rules
        if self._css_rules:
            base_css.append("/* Dynamic layout styles */")
            base_css.extend(self._css_rules)

        return '\\n'.join(base_css)

    def get_features_used(self) -> Set[str]:
        """Return set of features used during generation (for compatibility checking)."""
        return self._features_used.copy()

    def get_compatibility_warnings(self) -> List[str]:
        """Get warnings about features that don't translate well to Textual."""
        return get_compatibility_warnings(self._features_used, 'textual')

    # ------------------------------------------------------------------
    # Layout CSS helpers
    # ------------------------------------------------------------------

    def _layout_css_rules(self, node, widget_id: str) -> Optional[str]:
        """Generate Textual CSS rule for a node's layout attributes."""
        rules = []

        if hasattr(node, 'padding') and node.padding:
            val = self._tokens.spacing(node.padding)
            rules.append(f"padding: {val}")

        if hasattr(node, 'margin') and node.margin:
            val = self._tokens.spacing(node.margin)
            rules.append(f"margin: {val}")

        if hasattr(node, 'width') and node.width:
            val = self._tokens.size(node.width)
            if val and val != 'auto':
                rules.append(f"width: {val}")
            if node.width.isdigit() or str(node.width).endswith('px'):
                self._features_used.add('pixel_units')

        if hasattr(node, 'height') and node.height:
            val = self._tokens.size(node.height)
            if val and val != 'auto':
                rules.append(f"height: {val}")
            if node.height.isdigit() or str(node.height).endswith('px'):
                self._features_used.add('pixel_units')

        if hasattr(node, 'background') and node.background:
            val = self._tokens.color(node.background)
            rules.append(f"background: {val}")

        if hasattr(node, 'color') and node.color:
            val = self._tokens.color(node.color)
            rules.append(f"color: {val}")

        if hasattr(node, 'border') and node.border:
            # Simplified border handling
            rules.append(f"border: solid $primary")

        if hasattr(node, 'align') and node.align:
            # Textual align is different - it's a content alignment
            # align-horizontal: left | center | right
            val = self._tokens.align(node.align)
            rules.append(f"align-horizontal: {val}")

        if hasattr(node, 'justify') and node.justify:
            # Textual doesn't have justify-content
            # We track it for compatibility warnings
            if node.justify in ('between', 'around'):
                self._features_used.add(f'justify_{node.justify}')

        if hasattr(node, 'gap') and node.gap:
            # Textual doesn't support gap directly
            # Track for compatibility warning
            self._features_used.add('gap')

        if hasattr(node, 'visible') and node.visible == 'false':
            rules.append("display: none")

        if rules:
            return f"#{widget_id} {{ {'; '.join(rules)}; }}"
        return None

    def _get_widget_attrs(self, node, default_id: str = None,
                          default_classes: str = None) -> Dict[str, str]:
        """Build widget constructor attributes from node."""
        attrs = {}

        # Use node's ui_id or generate one
        widget_id = None
        if hasattr(node, 'ui_id') and node.ui_id:
            widget_id = node.ui_id
        elif default_id:
            widget_id = default_id

        if widget_id:
            attrs['id'] = widget_id

        # Collect classes
        classes = []
        if default_classes:
            classes.append(default_classes)
        if hasattr(node, 'ui_class') and node.ui_class:
            classes.append(node.ui_class)

        if classes:
            attrs['classes'] = ' '.join(classes)

        # Generate CSS rules if we have an ID
        if widget_id:
            css_rule = self._layout_css_rules(node, widget_id)
            if css_rule:
                self._css_rules.append(css_rule)

        return attrs

    def _format_widget_attrs(self, attrs: Dict[str, str]) -> str:
        """Format widget attributes for Python constructor."""
        if not attrs:
            return ''
        parts = []
        for k, v in attrs.items():
            parts.append(f'{k}={py_string(v)}')
        return ', '.join(parts)

    # ------------------------------------------------------------------
    # Node rendering dispatch
    # ------------------------------------------------------------------

    def _render_node(self, node: QuantumNode, py: PyBuilder):
        """Dispatch node to its render method."""
        # Containers
        if isinstance(node, UIWindowNode):
            self._render_window(node, py)
        elif isinstance(node, UIHBoxNode):
            self._render_hbox(node, py)
        elif isinstance(node, UIVBoxNode):
            self._render_vbox(node, py)
        elif isinstance(node, UIPanelNode):
            self._render_panel(node, py)
        elif isinstance(node, UITabPanelNode):
            self._render_tabpanel(node, py)
        elif isinstance(node, UITabNode):
            self._render_tab(node, py)
        elif isinstance(node, UIGridNode):
            self._render_grid(node, py)
        elif isinstance(node, UIAccordionNode):
            self._render_accordion(node, py)
        elif isinstance(node, UISectionNode):
            self._render_section(node, py)
        elif isinstance(node, UIScrollBoxNode):
            self._render_scrollbox(node, py)
        elif isinstance(node, UIFormNode):
            self._render_form(node, py)
        elif isinstance(node, UIFormItemNode):
            self._render_formitem(node, py)
        elif isinstance(node, UISpacerNode):
            self._render_spacer(node, py)
        # Widgets
        elif isinstance(node, UITextNode):
            self._render_text(node, py)
        elif isinstance(node, UIButtonNode):
            self._render_button(node, py)
        elif isinstance(node, UIInputNode):
            self._render_input(node, py)
        elif isinstance(node, UICheckboxNode):
            self._render_checkbox(node, py)
        elif isinstance(node, UISwitchNode):
            self._render_switch(node, py)
        elif isinstance(node, UISelectNode):
            self._render_select(node, py)
        elif isinstance(node, UITableNode):
            self._render_table(node, py)
        elif isinstance(node, UIProgressNode):
            self._render_progress(node, py)
        elif isinstance(node, UITreeNode):
            self._render_tree(node, py)
        elif isinstance(node, UILogNode):
            self._render_log(node, py)
        elif isinstance(node, UIMarkdownNode):
            self._render_markdown(node, py)
        elif isinstance(node, UIHeaderNode):
            self._render_header(node, py)
        elif isinstance(node, UIFooterNode):
            self._render_footer(node, py)
        elif isinstance(node, UIRuleNode):
            self._render_rule(node, py)
        elif isinstance(node, UILoadingNode):
            self._render_loading(node, py)
        elif isinstance(node, UIImageNode):
            self._render_image(node, py)
        elif isinstance(node, UILinkNode):
            self._render_link(node, py)
        elif isinstance(node, UIBadgeNode):
            self._render_badge(node, py)
        elif isinstance(node, UIListNode):
            self._render_list(node, py)
        elif isinstance(node, UIItemNode):
            self._render_item(node, py)
        elif isinstance(node, UIMenuNode):
            self._render_menu(node, py)
        elif isinstance(node, UIOptionNode):
            self._render_option(node, py)
        elif isinstance(node, UIDividedBoxNode):
            self._render_dividedbox(node, py)
        elif isinstance(node, UIRadioNode):
            self._render_radio(node, py)
        # Component library
        elif isinstance(node, UICarouselNode):
            self._render_carousel(node, py)
        elif isinstance(node, UISlideNode):
            self._render_slide(node, py)
        elif isinstance(node, UIStepperNode):
            self._render_stepper(node, py)
        elif isinstance(node, UIStepNode):
            self._render_step(node, py)
        elif isinstance(node, UICalendarNode):
            self._render_calendar(node, py)
        elif isinstance(node, UIDatePickerNode):
            self._render_date_picker(node, py)
        elif isinstance(node, UIToastNode):
            self._render_toast(node, py)
        elif isinstance(node, UIToastContainerNode):
            self._render_toast_container(node, py)
        # Quantum passthrough
        elif isinstance(node, SetNode):
            py.comment(f'q:set {node.name} = {node.value}')

    def _render_children(self, children: list, py: PyBuilder):
        """Render children inside an already-opened `with` block.

        Emits `pass` when the children produced no statement (empty container,
        or only comment lines such as a ui:toast) so the block stays valid
        Python.
        """
        start = len(py._lines)
        for child in children:
            self._render_node(child, py)
        if not self._has_statement('\n'.join(py._lines[start:])):
            py.line('pass')

    # ------------------------------------------------------------------
    # Container renders
    # ------------------------------------------------------------------

    def _render_window(self, node: UIWindowNode, py: PyBuilder):
        widget_id = self._next_id('window')
        attrs = self._get_widget_attrs(node, widget_id)
        attrs_str = self._format_widget_attrs(attrs)

        if attrs_str:
            py.line(f'with Vertical({attrs_str}):')
        else:
            py.line(f'with Vertical():')
        py.indent()
        self._render_children(node.children, py)
        py.dedent()

    def _render_hbox(self, node: UIHBoxNode, py: PyBuilder):
        widget_id = self._next_id('hbox')
        attrs = self._get_widget_attrs(node, widget_id)
        attrs_str = self._format_widget_attrs(attrs)

        if attrs_str:
            py.line(f'with Horizontal({attrs_str}):')
        else:
            py.line(f'with Horizontal():')
        py.indent()
        self._render_children(node.children, py)
        py.dedent()

    def _render_vbox(self, node: UIVBoxNode, py: PyBuilder):
        widget_id = self._next_id('vbox')
        attrs = self._get_widget_attrs(node, widget_id)
        attrs_str = self._format_widget_attrs(attrs)

        if attrs_str:
            py.line(f'with Vertical({attrs_str}):')
        else:
            py.line(f'with Vertical():')
        py.indent()
        self._render_children(node.children, py)
        py.dedent()

    def _render_panel(self, node: UIPanelNode, py: PyBuilder):
        widget_id = self._next_id('panel')
        attrs = self._get_widget_attrs(node, widget_id, 'q-panel')
        attrs_str = self._format_widget_attrs(attrs)

        py.line(f'with Vertical({attrs_str}):')
        py.indent()
        if node.title:
            py.line(f'yield Static({py_string(node.title)}, classes="q-panel-title")')
        self._render_children(node.children, py)
        py.dedent()

    def _render_tabpanel(self, node: UITabPanelNode, py: PyBuilder):
        widget_id = self._next_id('tabs')
        attrs = self._get_widget_attrs(node, widget_id)
        attrs_str = self._format_widget_attrs(attrs)

        if attrs_str:
            py.line(f'with TabbedContent({attrs_str}):')
        else:
            py.line(f'with TabbedContent():')
        py.indent()
        tabs = [c for c in node.children if isinstance(c, UITabNode)]
        for tab in tabs:
            py.line(f'with TabPane({py_string(tab.title)}):')
            py.indent()
            self._render_children(tab.children, py)
            py.dedent()
        py.dedent()

    def _render_tab(self, node: UITabNode, py: PyBuilder):
        # Standalone tab (should be inside tabpanel normally)
        widget_id = self._next_id('tab')
        attrs = self._get_widget_attrs(node, widget_id)
        attrs_str = self._format_widget_attrs(attrs)

        if attrs_str:
            py.line(f'with Vertical({attrs_str}):')
        else:
            py.line(f'with Vertical():')
        py.indent()
        self._render_children(node.children, py)
        py.dedent()

    def _render_grid(self, node: UIGridNode, py: PyBuilder):
        widget_id = self._next_id('grid')
        attrs = self._get_widget_attrs(node, widget_id)
        attrs_str = self._format_widget_attrs(attrs)

        if attrs_str:
            py.line(f'with Grid({attrs_str}):')
        else:
            py.line(f'with Grid():')
        py.indent()
        self._render_children(node.children, py)
        py.dedent()

    def _render_accordion(self, node: UIAccordionNode, py: PyBuilder):
        # Render sections as individual Collapsible widgets
        for child in node.children:
            self._render_node(child, py)

    def _render_section(self, node: UISectionNode, py: PyBuilder):
        widget_id = self._next_id('section')
        attrs = self._get_widget_attrs(node, widget_id)

        collapsed = 'False' if node.expanded else 'True'
        attrs_parts = [f'title={py_string(node.title)}', f'collapsed={collapsed}']
        if 'id' in attrs:
            attrs_parts.append(f'id={py_string(attrs["id"])}')
        if 'classes' in attrs:
            attrs_parts.append(f'classes={py_string(attrs["classes"])}')

        py.line(f'with Collapsible({", ".join(attrs_parts)}):')
        py.indent()
        self._render_children(node.children, py)
        py.dedent()

    def _render_scrollbox(self, node: UIScrollBoxNode, py: PyBuilder):
        widget_id = self._next_id('scroll')
        attrs = self._get_widget_attrs(node, widget_id)
        attrs_str = self._format_widget_attrs(attrs)

        if attrs_str:
            py.line(f'with ScrollableContainer({attrs_str}):')
        else:
            py.line(f'with ScrollableContainer():')
        py.indent()
        self._render_children(node.children, py)
        py.dedent()

    def _render_form(self, node: UIFormNode, py: PyBuilder):
        widget_id = self._next_id('form')
        attrs = self._get_widget_attrs(node, widget_id)
        attrs_str = self._format_widget_attrs(attrs)

        if attrs_str:
            py.line(f'with Vertical({attrs_str}):')
        else:
            py.line(f'with Vertical():')
        py.indent()
        self._render_children(node.children, py)
        py.dedent()

    def _render_formitem(self, node: UIFormItemNode, py: PyBuilder):
        widget_id = self._next_id('formitem')
        attrs = self._get_widget_attrs(node, widget_id)
        attrs_str = self._format_widget_attrs(attrs)

        if attrs_str:
            py.line(f'with Horizontal({attrs_str}):')
        else:
            py.line(f'with Horizontal():')
        py.indent()
        if node.label:
            py.line(f'yield Label({py_string(node.label)})')
        self._render_children(node.children, py)
        py.dedent()

    def _render_spacer(self, node: UISpacerNode, py: PyBuilder):
        widget_id = self._next_id('spacer')
        py.line(f'yield Static("", id={py_string(widget_id)})')
        # Add CSS rule for spacer
        self._css_rules.append(f'#{widget_id} {{ height: 1; }}')

    def _render_dividedbox(self, node: UIDividedBoxNode, py: PyBuilder):
        widget_id = self._next_id('divided')
        attrs = self._get_widget_attrs(node, widget_id)
        attrs_str = self._format_widget_attrs(attrs)

        container = 'Horizontal' if node.direction == 'horizontal' else 'Vertical'
        if attrs_str:
            py.line(f'with {container}({attrs_str}):')
        else:
            py.line(f'with {container}():')
        py.indent()
        self._render_children(node.children, py)
        py.dedent()

    # ------------------------------------------------------------------
    # Widget renders
    # ------------------------------------------------------------------

    def _render_text(self, node: UITextNode, py: PyBuilder):
        widget_id = self._next_id('text')
        attrs = self._get_widget_attrs(node, widget_id)

        # Handle font size (limited in Textual)
        if node.size:
            self._features_used.add('font_size')

        # Handle weight with text-style CSS
        if node.weight == 'bold':
            self._css_rules.append(f'#{widget_id} {{ text-style: bold; }}')

        parts = [py_string(node.content)]
        if 'id' in attrs:
            parts.append(f'id={py_string(attrs["id"])}')
        if 'classes' in attrs:
            parts.append(f'classes={py_string(attrs["classes"])}')

        py.line(f'yield Static({", ".join(parts)})')

    def _render_button(self, node: UIButtonNode, py: PyBuilder):
        widget_id = self._next_id('btn')
        attrs = self._get_widget_attrs(node, widget_id)

        # Map HTML variants to Textual variants
        # Textual accepts: default, error, primary, success, warning
        variant_map = {
            'secondary': 'default',
            'danger': 'error',
            'primary': 'primary',
            'success': 'success',
            'warning': 'warning',
        }

        parts = [py_string(node.content)]
        if node.variant:
            mapped_variant = variant_map.get(node.variant, 'default')
            parts.append(f'variant={py_string(mapped_variant)}')
        if 'id' in attrs:
            parts.append(f'id={py_string(attrs["id"])}')
        if 'classes' in attrs:
            parts.append(f'classes={py_string(attrs["classes"])}')

        py.line(f'yield Button({", ".join(parts)})')

    def _render_input(self, node: UIInputNode, py: PyBuilder):
        widget_id = self._next_id('input')
        attrs = self._get_widget_attrs(node, widget_id)

        parts = []
        if node.placeholder:
            parts.append(f'placeholder={py_string(node.placeholder)}')
        if 'id' in attrs:
            parts.append(f'id={py_string(attrs["id"])}')
        if 'classes' in attrs:
            parts.append(f'classes={py_string(attrs["classes"])}')

        py.line(f'yield Input({", ".join(parts)})')

    def _render_checkbox(self, node: UICheckboxNode, py: PyBuilder):
        widget_id = self._next_id('cb')
        attrs = self._get_widget_attrs(node, widget_id)

        parts = []
        if node.label:
            parts.append(py_string(node.label))
        if 'id' in attrs:
            parts.append(f'id={py_string(attrs["id"])}')
        if 'classes' in attrs:
            parts.append(f'classes={py_string(attrs["classes"])}')

        py.line(f'yield Checkbox({", ".join(parts)})')

    def _render_radio(self, node: UIRadioNode, py: PyBuilder):
        widget_id = self._next_id('radio')
        attrs = self._get_widget_attrs(node, widget_id)
        attrs_str = self._format_widget_attrs(attrs)

        # RadioSet in Textual or OptionList
        if node.options:
            opts = [o.strip() for o in node.options.split(',')]
            opts_str = ', '.join(py_string(o) for o in opts)
            py.line(f'yield OptionList({opts_str})')
        else:
            py.line(f'yield OptionList()')

    def _render_switch(self, node: UISwitchNode, py: PyBuilder):
        widget_id = self._next_id('sw')
        attrs = self._get_widget_attrs(node, widget_id)

        parts = []
        if 'id' in attrs:
            parts.append(f'id={py_string(attrs["id"])}')
        if 'classes' in attrs:
            parts.append(f'classes={py_string(attrs["classes"])}')

        py.line(f'yield Switch({", ".join(parts)})')

    def _render_select(self, node: UISelectNode, py: PyBuilder):
        widget_id = self._next_id('sel')
        attrs = self._get_widget_attrs(node, widget_id)

        if node.options:
            opts = [o.strip() for o in node.options.split(',')]
            opts_str = ', '.join(f'({py_string(o)}, {py_string(o)})' for o in opts)
            py.line(f'yield Select([{opts_str}])')
        else:
            py.line(f'yield Select([])')

    def _render_table(self, node: UITableNode, py: PyBuilder):
        widget_id = self._next_id('table')
        attrs = self._get_widget_attrs(node, widget_id)

        parts = []
        if 'id' in attrs:
            parts.append(f'id={py_string(attrs["id"])}')
        if 'classes' in attrs:
            parts.append(f'classes={py_string(attrs["classes"])}')

        py.line(f'yield DataTable({", ".join(parts)})')

    def _render_progress(self, node: UIProgressNode, py: PyBuilder):
        widget_id = self._next_id('prog')
        attrs = self._get_widget_attrs(node, widget_id)

        parts = []
        if 'id' in attrs:
            parts.append(f'id={py_string(attrs["id"])}')
        if 'classes' in attrs:
            parts.append(f'classes={py_string(attrs["classes"])}')

        py.line(f'yield ProgressBar({", ".join(parts)})')

    def _render_tree(self, node: UITreeNode, py: PyBuilder):
        widget_id = self._next_id('tree')
        attrs = self._get_widget_attrs(node, widget_id)

        parts = [py_string("Tree")]
        if 'id' in attrs:
            parts.append(f'id={py_string(attrs["id"])}')
        if 'classes' in attrs:
            parts.append(f'classes={py_string(attrs["classes"])}')

        py.line(f'yield Tree({", ".join(parts)})')

    def _render_log(self, node: UILogNode, py: PyBuilder):
        widget_id = self._next_id('log')
        attrs = self._get_widget_attrs(node, widget_id)

        parts = []
        if 'id' in attrs:
            parts.append(f'id={py_string(attrs["id"])}')
        if 'classes' in attrs:
            parts.append(f'classes={py_string(attrs["classes"])}')

        py.line(f'yield RichLog({", ".join(parts)})')

    def _render_markdown(self, node: UIMarkdownNode, py: PyBuilder):
        widget_id = self._next_id('md')
        attrs = self._get_widget_attrs(node, widget_id)

        parts = [py_string(node.content)]
        if 'id' in attrs:
            parts.append(f'id={py_string(attrs["id"])}')
        if 'classes' in attrs:
            parts.append(f'classes={py_string(attrs["classes"])}')

        py.line(f'yield Markdown({", ".join(parts)})')

    def _render_header(self, node: UIHeaderNode, py: PyBuilder):
        py.line(f'yield Header()')

    def _render_footer(self, node: UIFooterNode, py: PyBuilder):
        py.line(f'yield Footer()')

    def _render_rule(self, node: UIRuleNode, py: PyBuilder):
        py.line(f'yield Rule()')

    def _render_loading(self, node: UILoadingNode, py: PyBuilder):
        widget_id = self._next_id('loading')
        attrs = self._get_widget_attrs(node, widget_id)

        parts = []
        if 'id' in attrs:
            parts.append(f'id={py_string(attrs["id"])}')
        if 'classes' in attrs:
            parts.append(f'classes={py_string(attrs["classes"])}')

        py.line(f'yield LoadingIndicator({", ".join(parts)})')

    def _render_image(self, node: UIImageNode, py: PyBuilder):
        """Render image as placeholder text (graceful degradation)."""
        self._features_used.add('image')
        widget_id = self._next_id('img')

        # Create descriptive placeholder
        src = node.src or ''
        alt = node.alt or src.split('/')[-1] if src else 'image'
        placeholder = f"🖼 [{alt}]"

        py.line(f'yield Static({py_string(placeholder)}, id={py_string(widget_id)}, classes="q-image-placeholder")')

    def _render_link(self, node: UILinkNode, py: PyBuilder):
        """Render link as styled text (graceful degradation)."""
        if node.external:
            self._features_used.add('link_external')

        widget_id = self._next_id('link')
        content = node.content
        if node.to:
            content = f"{content} → {node.to}"

        py.line(f'yield Static({py_string(content)}, id={py_string(widget_id)}, classes="q-link")')

    def _render_badge(self, node: UIBadgeNode, py: PyBuilder):
        widget_id = self._next_id('badge')
        classes = 'q-badge'
        if node.variant:
            classes += f' q-badge-{node.variant}'

        py.line(f'yield Static({py_string(node.content)}, id={py_string(widget_id)}, classes={py_string(classes)})')

    def _render_list(self, node: UIListNode, py: PyBuilder):
        widget_id = self._next_id('list')
        attrs = self._get_widget_attrs(node, widget_id)
        attrs_str = self._format_widget_attrs(attrs)

        if attrs_str:
            py.line(f'with Vertical({attrs_str}):')
        else:
            py.line(f'with Vertical():')
        py.indent()
        self._render_children(node.children, py)
        py.dedent()

    def _render_item(self, node: UIItemNode, py: PyBuilder):
        widget_id = self._next_id('item')
        attrs = self._get_widget_attrs(node, widget_id)
        attrs_str = self._format_widget_attrs(attrs)

        if attrs_str:
            py.line(f'with Horizontal({attrs_str}):')
        else:
            py.line(f'with Horizontal():')
        py.indent()
        self._render_children(node.children, py)
        py.dedent()

    def _render_menu(self, node: UIMenuNode, py: PyBuilder):
        # OptionList for menu
        widget_id = self._next_id('menu')
        options = [c for c in node.children if isinstance(c, UIOptionNode)]
        if options:
            opts_str = ', '.join(py_string(o.label or o.value or '') for o in options)
            py.line(f'yield OptionList({opts_str}, id={py_string(widget_id)})')
        else:
            py.line(f'yield OptionList(id={py_string(widget_id)})')

    def _render_option(self, node: UIOptionNode, py: PyBuilder):
        # Standalone options are unusual, render as Static
        widget_id = self._next_id('opt')
        py.line(f'yield Static({py_string(node.label or node.value or "")}, id={py_string(widget_id)})')

    # ------------------------------------------------------------------
    # Component library renders
    # ------------------------------------------------------------------

    def _pane_ids(self, owner_id: str, panes: list, pane_type: type,
                  prefix: str) -> List[str]:
        """Stable ids for ContentSwitcher panes.

        A pane keeps its own ui_id when it has one; anything else gets a
        generated id so we never duplicate a child widget's id.
        """
        ids = []
        for index, pane in enumerate(panes):
            own = getattr(pane, 'ui_id', None) if isinstance(pane, pane_type) else None
            ids.append(own or f'{owner_id}__{prefix}_{index}')
        return ids

    def _render_carousel(self, node: UICarouselNode, py: PyBuilder):
        """One slide visible at a time (ContentSwitcher) + arrows/indicator.

        A terminal has no horizontal swipe, so navigation is the arrow
        buttons (Tab/Enter), ctrl+left / ctrl+right, and the auto-play timer.
        """
        attrs = self._get_widget_attrs(node, self._next_id('carousel'), 'q-carousel')
        cid = attrs['id']

        py.line(f'with Vertical({self._format_widget_attrs(attrs)}):')
        py.indent()

        slides = [c for c in node.children if isinstance(c, UISlideNode)]
        if not slides:
            # Keep any non-slide content instead of dropping it
            slides = list(node.children)

        if not slides:
            py.line('yield Static("(carousel has no slides)", classes="q-empty")')
            py.dedent()
            return

        slide_ids = self._pane_ids(cid, slides, UISlideNode, 'slide')
        self._need_import('from textual.widgets import ContentSwitcher')

        py.line(f'with ContentSwitcher(initial={py_string(slide_ids[0])}, '
                f'id={py_string(cid + "__switcher")}):')
        py.indent()
        for slide_id, slide in zip(slide_ids, slides):
            if isinstance(slide, UISlideNode):
                self._render_slide(slide, py, pane_id=slide_id)
            else:
                py.line(f'with Vertical(id={py_string(slide_id)}, classes="q-slide"):')
                py.indent()
                self._render_children([slide], py)
                py.dedent()
        py.dedent()

        show_arrows = self._as_bool(node.show_arrows, True)
        show_indicators = self._as_bool(node.show_indicators, True)
        if show_arrows or show_indicators:
            py.line('with Horizontal(classes="q-carousel-nav"):')
            py.indent()
            if show_arrows:
                py.line(f'yield Button("<", id={py_string(cid + "__prev")}, '
                        f'classes="q-carousel-arrow")')
            if show_indicators:
                py.line(f'yield Static({py_string(f"1 / {len(slides)}")}, '
                        f'id={py_string(cid + "__indicator")}, '
                        f'classes="q-carousel-indicator")')
            if show_arrows:
                py.line(f'yield Button(">", id={py_string(cid + "__next")}, '
                        f'classes="q-carousel-arrow")')
            py.dedent()

        py.dedent()

        if node.animation and node.animation != 'slide':
            # Textual switches panes instantly; a fade has no terminal analogue
            self._features_used.add('carousel_fade')

        self._carousels[cid] = {
            'slides': slide_ids,
            'index': max(0, min(self._as_int(node.current, 0), len(slides) - 1)),
            'loop': self._as_bool(node.loop, True),
            'auto_play': self._as_bool(node.auto_play, False),
            'interval': max(0.1, self._as_int(node.interval, 5000) / 1000.0),
            'bind': node.bind,
        }

    def _render_slide(self, node: UISlideNode, py: PyBuilder,
                      pane_id: Optional[str] = None):
        """A slide is a plain container; inside a carousel it is a switcher pane."""
        attrs = self._get_widget_attrs(node, pane_id or self._next_id('slide'), 'q-slide')
        py.line(f'with Vertical({self._format_widget_attrs(attrs)}):')
        py.indent()
        self._render_children(node.children, py)
        py.dedent()

    def _render_stepper(self, node: UIStepperNode, py: PyBuilder):
        """Indicator row/column + one step pane visible at a time + Prev/Next."""
        attrs = self._get_widget_attrs(node, self._next_id('stepper'), 'q-stepper')
        sid = attrs['id']

        py.line(f'with Vertical({self._format_widget_attrs(attrs)}):')
        py.indent()

        steps = [c for c in node.children if isinstance(c, UIStepNode)]
        if not steps:
            py.line('yield Static("(stepper has no steps)", classes="q-empty")')
            py.dedent()
            return

        step_ids = self._pane_ids(sid, steps, UIStepNode, 'step')
        current = max(0, min(self._as_int(node.current, 0), len(steps) - 1))
        show_labels = self._as_bool(node.show_labels, True)
        clickable = self._as_bool(node.clickable, False)
        self._need_import('from textual.widgets import ContentSwitcher')

        # A MESMA regra do adapter html. Aqui havia uma terceira versao —
        # `index < current or _as_bool(step.completed, False)` — que ignorava
        # `completed="false"` explicito, porque _as_bool colapsa "nao setado"
        # e "setado como false".
        concluidos = set(completed_step_indices(steps, current))

        # Step indicators
        indicators = 'Horizontal' if node.orientation != 'vertical' else 'Vertical'
        py.line(f'with {indicators}(classes="q-stepper-indicators"):')
        py.indent()
        for index, step in enumerate(steps):
            # O adapter html usa `step.icon if step.icon else str(i + 1)` no
            # indicador. Aqui o icone era silenciosamente descartado — nem no
            # indicador, nem no painel. Atributo documentado que nao fazia
            # nada, sem aviso nenhum.
            marca = step.icon if step.icon else f'{index + 1}'
            label = marca
            if show_labels and step.title:
                label = f'{marca}. {step.title}'
            if self._as_bool(step.optional, False):
                label += ' (optional)'
            classes = 'q-step-indicator'
            if index == current:
                classes += ' q-step-active'
            elif index in concluidos:
                classes += ' q-step-done'
            widget = 'Button' if clickable else 'Static'
            py.line(f'yield {widget}({py_string(label)}, '
                    f'id={py_string(f"{sid}__ind_{index}")}, '
                    f'classes={py_string(classes)})')
        py.dedent()

        # Step content
        py.line(f'with ContentSwitcher(initial={py_string(step_ids[current])}, '
                f'id={py_string(sid + "__switcher")}):')
        py.indent()
        for step_id, step in zip(step_ids, steps):
            self._render_step(step, py, pane_id=step_id)
        py.dedent()

        # Navigation
        py.line('with Horizontal(classes="q-stepper-nav"):')
        py.indent()
        py.line(f'yield Button("Previous", id={py_string(sid + "__prev")})')
        py.line(f'yield Button("Next", variant="primary", id={py_string(sid + "__next")})')
        py.dedent()

        py.dedent()

        # `completed` e tri-state — nao setado, "true", "false" — e a marca
        # explicita nao muda quando o usuario navega, enquanto a posicional
        # muda. Guardar so um booleano por passo perderia a diferenca, que e
        # exatamente o que acontecia: _q_stepper_apply fazia
        # `set_class(position < index, "q-step-done")` e apagava, depois do
        # mount, o que o compose() tinha desenhado a partir de `completed`.
        # O atributo nao tinha efeito nenhum.
        explicito = {}
        for i, filho in enumerate(steps):
            if getattr(filho, 'completed', None) is not None:
                explicito[i] = self._as_bool(filho.completed, False)

        self._steppers[sid] = {
            'steps': step_ids,
            'index': current,
            'linear': self._as_bool(node.linear, True),
            'bind': node.bind,
            'explicit_done': explicito,
        }

    def _render_step(self, node: UIStepNode, py: PyBuilder,
                     pane_id: Optional[str] = None):
        """A step is a container; its title lives in the stepper indicator."""
        attrs = self._get_widget_attrs(node, pane_id or self._next_id('step'), 'q-step')
        py.line(f'with Vertical({self._format_widget_attrs(attrs)}):')
        py.indent()
        if node.title and pane_id is None:
            # Standalone step: nothing else shows the title
            py.line(f'yield Static({py_string(node.title)}, classes="q-step-title")')
        if node.description:
            py.line(f'yield Static({py_string(node.description)}, classes="q-step-description")')
        if node.error:
            py.line(f'yield Static({py_string(node.error)}, classes="q-step-error")')
        self._render_children(node.children, py)
        py.dedent()

    def _render_calendar(self, node: UICalendarNode, py: PyBuilder):
        """Month grid as a DataTable: cell cursor selects a day, arrows change month."""
        attrs = self._get_widget_attrs(node, self._next_id('calendar'), 'q-calendar')
        cid = attrs['id']
        self._need_import('import calendar')
        self._need_import('from rich.text import Text')
        self._need_datetime('date')

        py.line(f'with Vertical({self._format_widget_attrs(attrs)}):')
        py.indent()
        py.line('with Horizontal(classes="q-calendar-header"):')
        py.indent()
        py.line(f'yield Button("<", id={py_string(cid + "__prev")}, classes="q-calendar-nav")')
        py.line(f'yield Static("", id={py_string(cid + "__title")}, classes="q-calendar-title")')
        py.line(f'yield Button(">", id={py_string(cid + "__next")}, classes="q-calendar-nav")')
        py.dedent()
        py.line(f'yield DataTable(id={py_string(cid + "__grid")}, '
                f'cursor_type="cell", classes="q-calendar-grid")')
        py.line(f'yield Static("", id={py_string(cid + "__value")}, classes="q-calendar-value")')
        py.dedent()

        mode = node.mode if node.mode in ('single', 'range', 'multiple') else 'single'
        self._calendars[cid] = {
            'mode': mode,
            'selected': self._split_dates(node.value),
            'min': (node.min_date or '').strip(),
            'max': (node.max_date or '').strip(),
            'disabled_dates': self._split_dates(node.disabled_dates),
            'disabled_days': [self._as_int(d, -1) for d in self._split_list(node.disabled_days)],
            'week_numbers': self._as_bool(node.show_week_numbers, False),
            'first_day': self._as_int(node.first_day_of_week, 0) % 7,
            'locale': (node.locale or '').strip(),
            'bind': node.bind,
        }
        if not self._as_bool(node.inline, True):
            # A popup calendar has no terminal analogue - it is always inline
            self._features_used.add('calendar_popup')

    def _render_date_picker(self, node: UIDatePickerNode, py: PyBuilder):
        """Text input validated against the declared format, plus a clear button."""
        attrs = self._get_widget_attrs(node, self._next_id('datepicker'), 'q-date-picker')
        pid = attrs['id']
        self._need_datetime('date', 'datetime')

        fmt = node.format or 'YYYY-MM-DD'
        disabled = self._as_bool(node.disabled, False)

        py.line(f'with Vertical({self._format_widget_attrs(attrs)}):')
        py.indent()
        py.line('with Horizontal(classes="q-date-picker-row"):')
        py.indent()
        parts = []
        if node.value:
            parts.append(f'value={py_string(node.value)}')
        parts.append(f'placeholder={py_string(node.placeholder or "Select date")}')
        parts.append(f'id={py_string(pid + "__input")}')
        parts.append('classes="q-date-picker-input"')
        if disabled:
            parts.append('disabled=True')
        py.line(f'yield Input({", ".join(parts)})')
        if self._as_bool(node.clearable, True) and not disabled:
            py.line(f'yield Button("X", id={py_string(pid + "__clear")}, '
                    f'classes="q-date-picker-clear")')
        py.dedent()
        py.line(f'yield Static({py_string(fmt)}, id={py_string(pid + "__hint")}, '
                f'classes="q-date-picker-hint")')
        py.dedent()

        self._date_pickers[pid] = {
            'format': fmt,
            'strptime': self._to_strptime(fmt),
            'min': (node.min_date or '').strip(),
            'max': (node.max_date or '').strip(),
            'required': self._as_bool(node.required, False),
            'bind': node.bind,
        }

    def _render_toast(self, node: UIToastNode, py: PyBuilder):
        """A ui:toast becomes a real Textual notification raised on mount."""
        index = len(self._toasts) + 1
        method = f'q_toast_{index}'
        variant = node.variant or 'info'
        severity = self.TOAST_SEVERITY.get(variant, 'information')

        message = (node.message or '').strip()
        title = (node.title or '').strip()
        if not message:
            message, title = (title or variant.title()), ''
        if node.icon:
            # Textual notifications have no icon slot: prefix whatever is shown
            if title:
                title = f'{node.icon} {title}'
            else:
                message = f'{node.icon} {message}'

        duration = self._as_int(node.duration, 3000)
        # Textual always auto-dismisses; duration="0" becomes a full day.
        timeout = 86400.0 if duration <= 0 else duration / 1000.0

        if self._toast_first_position is None:
            self._toast_first_position = node.position
        if variant == 'success':
            # Textual only knows information/warning/error
            self._features_used.add('toast_success_severity')
        if not self._as_bool(node.dismissible, True):
            # Textual toasts are always click-dismissible
            self._features_used.add('toast_not_dismissible')

        self._toasts.append({
            'method': method,
            'message': message,
            'title': title,
            'severity': severity,
            'timeout': timeout,
            'variant': variant,
            'show': node.show,
        })
        py.comment(f'ui:toast ({variant}) -> self.{method}() / App.notify()')

    def _render_toast_container(self, node: UIToastContainerNode, py: PyBuilder):
        """Textual owns a single ToastRack; the container positions and caps it."""
        position = node.position or 'top-right'
        self._toast_rack_position = position
        self._max_toasts = max(0, self._as_int(node.max_toasts, 5))
        py.comment(f'ui:toast-container -> ToastRack (position={position}, '
                   f'max-toasts={self._max_toasts})')

    # ------------------------------------------------------------------
    # Value helpers for the component library
    # ------------------------------------------------------------------

    @staticmethod
    def _split_list(value) -> List[str]:
        if not value:
            return []
        if isinstance(value, (list, tuple)):
            items = list(value)
        else:
            items = str(value).split(',')
        return [str(item).strip() for item in items if str(item).strip()]

    def _split_dates(self, value) -> List[str]:
        """Keep only ISO dates - anything else would crash date.fromisoformat."""
        dates = []
        for item in self._split_list(value):
            try:
                _date.fromisoformat(item)
            except ValueError:
                continue
            dates.append(item)
        return dates

    # Longest token first so YYYY wins over YY and MMMM over MM.
    _FORMAT_TOKENS = (
        ('YYYY', '%Y'), ('YY', '%y'),
        ('MMMM', '%B'), ('MMM', '%b'), ('MM', '%m'),
        ('DDDD', '%A'), ('DDD', '%a'), ('DD', '%d'),
        ('HH', '%H'), ('mm', '%M'), ('ss', '%S'),
    )

    @classmethod
    def _to_strptime(cls, fmt: str) -> str:
        """Translate a date-picker display format into a strptime pattern."""
        out = []
        i = 0
        while i < len(fmt):
            for token, code in cls._FORMAT_TOKENS:
                if fmt.startswith(token, i):
                    out.append(code)
                    i += len(token)
                    break
            else:
                if fmt[i] == '%':
                    out.append('%%')
                else:
                    out.append(fmt[i])
                i += 1
        return ''.join(out)

    # ------------------------------------------------------------------
    # Generated class body: BINDINGS and methods
    # ------------------------------------------------------------------

    def _build_bindings(self) -> str:
        """Keyboard navigation for the components that need it."""
        rows = []
        if self._carousels:
            rows.append('("ctrl+right", "q_carousel_next", "Next slide"),')
            rows.append('("ctrl+left", "q_carousel_prev", "Previous slide"),')
        if self._steppers:
            rows.append('("ctrl+down", "q_stepper_next", "Next step"),')
            rows.append('("ctrl+up", "q_stepper_prev", "Previous step"),')
        if not rows:
            return ''
        body = '\n'.join(f'        {row}' for row in rows)
        return f'    BINDINGS = [\n{body}\n    ]\n'

    def _emit_block(self, py: PyBuilder, source: str):
        """Emit a verbatim source block at the builder's current indent."""
        for line in source.strip('\n').split('\n'):
            if line.strip():
                py.line(line)
            else:
                py.blank()

    def _build_methods(self) -> str:
        """Class body emitted after compose(): state tables, handlers, actions."""
        stateful = bool(self._carousels or self._steppers
                        or self._calendars or self._date_pickers)
        if not stateful and not self._toasts:
            return '    pass'

        py = PyBuilder()
        py._indent = 1

        # --- static configuration tables ---
        if self._carousels:
            py.line(f'Q_CAROUSELS = {self._carousels!r}')
            py.blank()
        if self._steppers:
            py.line(f'Q_STEPPERS = {self._steppers!r}')
            py.blank()
        if self._calendars:
            py.line(f'Q_CALENDARS = {self._calendars!r}')
            py.blank()
        if self._date_pickers:
            py.line(f'Q_DATE_PICKERS = {self._date_pickers!r}')
            py.blank()

        # --- on_mount: build runtime state, then initialise each component ---
        py.line('def on_mount(self) -> None:')
        py.indent()
        if stateful:
            py.line('self._q_state = {}')
        if self._carousels:
            py.line('self._q_carousels = {cid: dict(spec, slides=list(spec["slides"]))')
            py.line('                     for cid, spec in self.Q_CAROUSELS.items()}')
        if self._steppers:
            py.line('self._q_steppers = {sid: dict(spec, steps=list(spec["steps"]))')
            py.line('                    for sid, spec in self.Q_STEPPERS.items()}')
        if self._calendars:
            py.line('self._q_calendars = {}')
            py.line('for cid, spec in self.Q_CALENDARS.items():')
            py.indent()
            py.line('self._q_calendars[cid] = dict(')
            py.line('    spec,')
            py.line('    min=self._q_date(spec["min"]),')
            py.line('    max=self._q_date(spec["max"]),')
            py.line('    selected=[self._q_date(day) for day in spec["selected"]],')
            py.line('    disabled_dates=set(spec["disabled_dates"]),')
            py.line('    disabled_days=set(spec["disabled_days"]),')
            py.line('    cells=[],')
            py.line(')')
            py.dedent()
        if self._date_pickers:
            py.line('self._q_date_pickers = {}')
            py.line('for pid, spec in self.Q_DATE_PICKERS.items():')
            py.indent()
            py.line('self._q_date_pickers[pid] = dict(')
            py.line('    spec,')
            py.line('    min=self._q_date(spec["min"]),')
            py.line('    max=self._q_date(spec["max"]),')
            py.line(')')
            py.dedent()
        if self._carousels:
            py.line('self._q_carousel_init()')
        if self._steppers:
            py.line('self._q_stepper_init()')
        if self._calendars:
            py.line('self._q_calendar_init()')
        if self._date_pickers:
            py.line('self._q_date_picker_init()')
        if self._toasts:
            py.line('self._q_show_toasts()')
        py.dedent()
        py.blank()

        # --- shared date helper ---
        if self._calendars or self._date_pickers:
            py.line('def _q_date(self, value):')
            py.indent()
            py.line('"""Parse an ISO date attribute, ignoring unusable values."""')
            py.line('try:')
            py.line('    return date.fromisoformat(value) if value else None')
            py.line('except (TypeError, ValueError):')
            py.line('    return None')
            py.dedent()
            py.blank()

        # --- button dispatch shared by carousel / stepper / calendar / picker ---
        if self._carousels or self._steppers or self._calendars or self._date_pickers:
            py.line('def on_button_pressed(self, event: Button.Pressed) -> None:')
            py.indent()
            py.line('owner, _, action = (event.button.id or "").rpartition("__")')
            py.line('if not owner:')
            py.line('    return')
            if self._carousels:
                py.line('if owner in self._q_carousels:')
                py.line('    if action in ("prev", "next"):')
                py.line('        self._q_carousel_go(owner, 1 if action == "next" else -1)')
                py.line('    return')
            if self._steppers:
                py.line('if owner in self._q_steppers:')
                py.line('    index = self._q_steppers[owner]["index"]')
                py.line('    if action == "next":')
                py.line('        self._q_stepper_goto(owner, index + 1)')
                py.line('    elif action == "prev":')
                py.line('        self._q_stepper_goto(owner, index - 1)')
                py.line('    elif action.startswith("ind_"):')
                py.line('        self._q_stepper_goto(owner, int(action[4:]))')
                py.line('    return')
            if self._calendars:
                py.line('if owner in self._q_calendars:')
                py.line('    if action in ("prev", "next"):')
                py.line('        self._q_calendar_move(owner, 1 if action == "next" else -1)')
                py.line('    return')
            if self._date_pickers:
                py.line('if owner in self._q_date_pickers and action == "clear":')
                py.line('    for field in self.query("#" + owner + "__input"):')
                py.line('        field.value = ""')
            py.dedent()
            py.blank()

        # --- per-component runtime ---
        for used, block in ((self._carousels, _CAROUSEL_METHODS),
                            (self._steppers, _STEPPER_METHODS),
                            (self._calendars, _CALENDAR_METHODS),
                            (self._date_pickers, _DATE_PICKER_METHODS)):
            if used:
                self._emit_block(py, block)
                py.blank()

        # --- toasts ---
        if self._toasts:
            shown = self._toasts if self._max_toasts is None else self._toasts[:self._max_toasts]
            py.line('def _q_show_toasts(self) -> None:')
            py.indent()
            py.line('"""Raise every declared ui:toast once the app is running."""')
            if not shown:
                py.line('return')
            # `show=` nomeia uma variavel de estado, e o binding virava um
            # COMENTARIO: `self.q_toast_1()  # show="hasError"`. O toast
            # disparava incondicionalmente — um <ui:toast show="hasError">
            # aparecia em todo lancamento do app, tivesse erro ou nao. O
            # adapter html trata isso como "escondido ate a variavel ficar
            # verdadeira"; aqui vale o mesmo contrato.
            condicionais = []
            for toast in shown:
                if toast['show']:
                    condicionais.append(toast)
                    py.line(f'if self._q_truthy(self._q_state.get({py_string(toast["show"])})):')
                    py.line(f'    self.{toast["method"]}()')
                else:
                    py.line(f'self.{toast["method"]}()')
            py.dedent()
            py.blank()

            # E quando a variavel muda DEPOIS do mount, o toast aparece —
            # senao "escondido ate ficar verdadeiro" viraria "nunca".
            py.line('def _q_toast_on_state(self, name: str) -> None:')
            py.indent()
            py.line('"""Dispara os toasts cujo show= acabou de ficar verdadeiro."""')
            if not condicionais:
                py.line('return')
            else:
                py.line('if not self._q_truthy(self._q_state.get(name)):')
                py.line('    return')
                py.line('ja = getattr(self, "_q_toasts_shown", None)')
                py.line('if ja is None:')
                py.line('    ja = self._q_toasts_shown = set()')
                for toast in condicionais:
                    nome = py_string(toast['show'])
                    metodo = py_string(toast['method'])
                    py.line(f'if name == {nome} and {metodo} not in ja:')
                    py.line(f'    ja.add({metodo})')
                    py.line(f'    self.{toast["method"]}()')
            py.dedent()
            py.blank()
            for toast in self._toasts:
                py.line(f'def {toast["method"]}(self) -> None:')
                py.indent()
                py.line(f'"""ui:toast variant={toast["variant"]}."""')
                args = [py_string(toast['message'])]
                if toast['title']:
                    args.append(f'title={py_string(toast["title"])}')
                args.append(f'severity={py_string(toast["severity"])}')
                args.append(f'timeout={toast["timeout"]!r}')
                py.line(f'self.notify({", ".join(args)})')
                py.dedent()
                py.blank()

        if stateful:
            self._emit_block(py, _STATE_ACCESSOR)

        return py.build().rstrip()
