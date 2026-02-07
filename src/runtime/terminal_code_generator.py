"""
Terminal Engine - Code Generator

Transforms Terminal AST nodes into Python code that runs with Textual.
This is a compiler/transpiler: Python generates Python TUI apps.

Uses PyBuilder for structured, safe Python generation.
"""

import json
import re
from typing import List, Dict, Any, Optional

from core.features.terminal_engine.src.ast_nodes import (
    ScreenNode, PanelNode, LayoutNode, TableNode, ColumnNode,
    TerminalInputNode, ButtonNode, MenuNode, OptionNode,
    TextNode_Terminal, ProgressNode, TreeNode, TabsNode, TabNode,
    LogNode_Terminal, HeaderNode_Terminal, FooterNode, StatusNode,
    KeybindingNode, TimerNode_Terminal, ServiceNode, CssNode,
    OnEventNode_Terminal, RawCodeNode_Terminal,
)
from core.ast_nodes import QuantumNode, QueryNode
from core.features.conditionals.src.ast_node import IfNode
from core.features.loops.src.ast_node import LoopNode
from core.features.state_management.src.ast_node import SetNode
from core.features.functions.src.ast_node import FunctionNode

from runtime.terminal_templates import (
    APP_TEMPLATE, PyBuilder, py_string, py_id, py_bool,
)


class TerminalCodeGenerator:
    """Generates standalone Python Textual app from a terminal AST."""

    def __init__(self):
        self._state_vars: List[Dict] = []  # {name, value, type}
        self._functions: List[FunctionNode] = []
        self._keybindings: List[Dict] = []
        self._timers: List[Dict] = []
        self._services: List[Dict] = []
        self._css_blocks: List[str] = []
        self._queries: List[Dict] = []
        self._screens: List[ScreenNode] = []
        self._extra_imports: List[str] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, screens: List[ScreenNode], title: str = "Quantum TUI",
                 terminal_css: str = "", keybindings: List = None,
                 services: List = None) -> str:
        """Generate full Python app from ScreenNodes."""

        if terminal_css:
            self._css_blocks.append(terminal_css)

        # Process top-level keybindings/services
        for kb in (keybindings or []):
            if isinstance(kb, KeybindingNode):
                self._keybindings.append({
                    'key': kb.key,
                    'action': kb.action,
                    'description': kb.description or kb.action,
                })

        for svc in (services or []):
            if isinstance(svc, ServiceNode):
                self._services.append({
                    'id': svc.service_id,
                    'handler': svc.handler,
                })

        self._screens = screens

        # Process all screens
        for screen in screens:
            self._process_screen_children(screen.children)

        # Build app code
        py = PyBuilder()
        self._build_app_class(py, screens, title)
        app_code = py.build()

        # Determine app class name
        app_class = py_id(title.replace(' ', '')) + "App"

        # Determine filename
        filename = py_id(title.lower().replace(' ', '_')) + ".py"

        # Extra imports
        extra_imports = '\n'.join(self._extra_imports)

        return APP_TEMPLATE.format(
            title=title,
            filename=filename,
            extra_imports=extra_imports,
            app_code=app_code,
            app_class=app_class,
        )

    # ------------------------------------------------------------------
    # Process AST children (collect metadata)
    # ------------------------------------------------------------------

    def _process_screen_children(self, children: List[QuantumNode]):
        """Walk screen children to collect state vars, functions, etc."""
        for child in children:
            if isinstance(child, SetNode):
                self._state_vars.append({
                    'name': child.name,
                    'value': child.value,
                    'type': getattr(child, 'type', 'string'),
                })
            elif isinstance(child, FunctionNode):
                self._functions.append(child)
            elif isinstance(child, KeybindingNode):
                self._keybindings.append({
                    'key': child.key,
                    'action': child.action,
                    'description': child.description or child.action,
                })
            elif isinstance(child, TimerNode_Terminal):
                self._timers.append({
                    'id': child.timer_id,
                    'interval': child.interval,
                    'action': child.action,
                })
            elif isinstance(child, ServiceNode):
                self._services.append({
                    'id': child.service_id,
                    'handler': child.handler,
                })
            elif isinstance(child, CssNode):
                self._css_blocks.append(child.content)
            elif isinstance(child, QueryNode):
                self._queries.append({
                    'name': child.name,
                    'datasource': getattr(child, 'datasource', ''),
                    'sql': getattr(child, 'sql', ''),
                })
                if 'import sqlite3' not in self._extra_imports:
                    self._extra_imports.append('import sqlite3')
            elif hasattr(child, 'children'):
                self._process_screen_children(child.children)

    # ------------------------------------------------------------------
    # Build the App class
    # ------------------------------------------------------------------

    def _build_app_class(self, py: PyBuilder, screens: List[ScreenNode], title: str):
        """Build the main Textual App class."""
        app_class = py_id(title.replace(' ', '')) + "App"

        py.blank()
        py.class_def(app_class, 'App')

        # TITLE
        py.assign('TITLE', py_string(title))

        # CSS
        if self._css_blocks:
            css_combined = '\n'.join(self._css_blocks)
            py.assign('CSS', f'"""{css_combined}"""')
        py.blank()

        # BINDINGS
        if self._keybindings:
            bindings_list = []
            for kb in self._keybindings:
                desc = kb.get('description', kb['action'])
                bindings_list.append(
                    f'Binding({py_string(kb["key"])}, {py_string(kb["action"])}, {py_string(desc)})'
                )
            py.assign('BINDINGS', f'[\n        ' + ',\n        '.join(bindings_list) + ',\n    ]')
            py.blank()

        # Reactive state vars
        for var in self._state_vars:
            default = self._get_default_value(var)
            py.assign(var['name'], f'reactive({default})')
        if self._state_vars:
            py.blank()

        # compose() method
        self._emit_compose(py, screens)

        # on_mount() for timers
        if self._timers:
            py.blank()
            py.method_def('on_mount', 'self')
            py.docstring('Set up timers on app mount.')
            for timer in self._timers:
                action = timer['action']
                interval = timer['interval']
                py.line(f'self.set_interval({interval}, self.action_{py_id(action)})')
            py.end_block()

        # Event handlers
        self._emit_event_handlers(py)

        # User-defined functions
        self._emit_functions(py)

        # Query functions
        self._emit_queries(py)

        # Action methods for keybindings/timers
        self._emit_action_methods(py)

        py.end_block()  # Close class

    # ------------------------------------------------------------------
    # compose() - Widget tree
    # ------------------------------------------------------------------

    def _emit_compose(self, py: PyBuilder, screens: List[ScreenNode]):
        """Emit the compose() method that yields the widget tree."""
        py.line('def compose(self) -> ComposeResult:')
        py.indent()
        py.docstring('Build the widget tree.')

        # Use first screen as main compose
        if screens:
            screen = screens[0]
            for child in screen.children:
                self._emit_widget(py, child)

        py.end_block()

    def _emit_widget(self, py: PyBuilder, node: QuantumNode):
        """Emit a yield statement for a widget node."""

        if isinstance(node, HeaderNode_Terminal):
            if node.show_clock:
                py.line('yield Header(show_clock=True)')
            else:
                py.line('yield Header()')

        elif isinstance(node, FooterNode):
            py.line('yield Footer()')

        elif isinstance(node, TextNode_Terminal):
            content = node.content or ''
            id_part = f', id={py_string(node.text_id)}' if node.text_id else ''
            py.line(f'yield Static({py_string(content)}{id_part})')

        elif isinstance(node, ProgressNode):
            parts = []
            parts.append(f'total={node.total}')
            if node.progress_id:
                parts.append(f'id={py_string(node.progress_id)}')
            py.line(f'yield ProgressBar({", ".join(parts)})')

        elif isinstance(node, TerminalInputNode):
            parts = []
            if node.placeholder:
                parts.append(f'placeholder={py_string(node.placeholder)}')
            if node.password:
                parts.append('password=True')
            if node.input_id:
                parts.append(f'id={py_string(node.input_id)}')
            py.line(f'yield Input({", ".join(parts)})')

        elif isinstance(node, ButtonNode):
            parts = [py_string(node.label)]
            if node.variant and node.variant != 'default':
                parts.append(f'variant={py_string(node.variant)}')
            if node.button_id:
                parts.append(f'id={py_string(node.button_id)}')
            py.line(f'yield Button({", ".join(parts)})')

        elif isinstance(node, LogNode_Terminal):
            parts = []
            if not node.auto_scroll:
                parts.append('auto_scroll=False')
            if not node.markup:
                parts.append('markup=False')
            if node.max_lines:
                parts.append(f'max_lines={node.max_lines}')
            if node.log_id:
                parts.append(f'id={py_string(node.log_id)}')
            py.line(f'yield RichLog({", ".join(parts)})')

        elif isinstance(node, TreeNode):
            label = node.label or 'Root'
            parts = [py_string(label)]
            if node.tree_id:
                parts.append(f'id={py_string(node.tree_id)}')
            py.line(f'yield Tree({", ".join(parts)})')

        elif isinstance(node, MenuNode):
            parts = []
            if node.menu_id:
                parts.append(f'id={py_string(node.menu_id)}')
            py.line(f'yield OptionList({", ".join(parts)})')

        elif isinstance(node, StatusNode):
            content = node.content or ''
            id_part = f', id={py_string(node.status_id)}' if node.status_id else ''
            py.line(f'yield Static({py_string(content)}{id_part})')

        elif isinstance(node, TableNode):
            self._emit_table_widget(py, node)

        elif isinstance(node, PanelNode):
            self._emit_container(py, node, 'Vertical')

        elif isinstance(node, LayoutNode):
            container = 'Horizontal' if node.direction == 'horizontal' else 'Vertical'
            self._emit_container(py, node, container)

        elif isinstance(node, TabsNode):
            self._emit_tabs_widget(py, node)

        # Skip non-widget nodes (SetNode, FunctionNode, etc.)

    def _emit_container(self, py: PyBuilder, node, container_type: str):
        """Emit a container widget (Vertical/Horizontal) with children."""
        node_id = getattr(node, 'panel_id', None) or getattr(node, 'layout_id', None)
        id_part = f'id={py_string(node_id)}' if node_id else ''
        py.line(f'with {container_type}({id_part}):')
        py.indent()

        has_children = False
        for child in node.children:
            if self._is_widget_node(child):
                self._emit_widget(py, child)
                has_children = True

        if not has_children:
            py.pass_stmt()
        py.end_block()

    def _emit_table_widget(self, py: PyBuilder, node: TableNode):
        """Emit DataTable setup."""
        id_part = f'id={py_string(node.table_id)}' if node.table_id else ''
        if node.zebra:
            if id_part:
                id_part += ', '
            id_part += 'zebra_stripes=True'
        py.line(f'yield DataTable({id_part})')

    def _emit_tabs_widget(self, py: PyBuilder, node: TabsNode):
        """Emit TabbedContent with TabPanes."""
        id_part = f'id={py_string(node.tabs_id)}' if node.tabs_id else ''
        py.line(f'with TabbedContent({id_part}):')
        py.indent()

        for tab in node.tabs:
            tab_id_part = f', id={py_string(tab.tab_id)}' if tab.tab_id else ''
            py.line(f'with TabPane({py_string(tab.title)}{tab_id_part}):')
            py.indent()
            has_children = False
            for child in tab.children:
                if self._is_widget_node(child):
                    self._emit_widget(py, child)
                    has_children = True
            if not has_children:
                py.pass_stmt()
            py.end_block()

        if not node.tabs:
            py.pass_stmt()
        py.end_block()

    def _is_widget_node(self, node: QuantumNode) -> bool:
        """Check if a node produces a widget."""
        return isinstance(node, (
            HeaderNode_Terminal, FooterNode, TextNode_Terminal, ProgressNode,
            TerminalInputNode, ButtonNode, LogNode_Terminal, TreeNode,
            MenuNode, StatusNode, TableNode, PanelNode, LayoutNode,
            TabsNode,
        ))

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _emit_event_handlers(self, py: PyBuilder):
        """Emit Textual event handler methods (on_button_pressed, on_input_submitted)."""
        # Collect button on_click handlers
        button_handlers = self._collect_handlers_of_type(ButtonNode, 'on_click')
        input_handlers = self._collect_handlers_of_type(TerminalInputNode, 'on_submit')

        if button_handlers:
            py.blank()
            py.method_def('on_button_pressed', 'self, event: Button.Pressed')
            py.docstring('Handle button press events.')
            first = True
            for btn_id, action in button_handlers:
                if btn_id:
                    cond = f'event.button.id == {py_string(btn_id)}'
                    if first:
                        py.if_block(cond)
                        first = False
                    else:
                        py.elif_block(cond)
                    py.line(f'self.action_{py_id(action)}()')
            if not first:
                py.end_block()
            py.end_block()

        if input_handlers:
            py.blank()
            py.method_def('on_input_submitted', 'self, event: Input.Submitted')
            py.docstring('Handle input submit events.')
            first = True
            for input_id, action in input_handlers:
                if input_id:
                    cond = f'event.input.id == {py_string(input_id)}'
                    if first:
                        py.if_block(cond)
                        first = False
                    else:
                        py.elif_block(cond)
                    py.line(f'self.action_{py_id(action)}()')
            if not first:
                py.end_block()
            py.end_block()

    def _collect_handlers_of_type(self, node_type, attr_name: str) -> List[tuple]:
        """Walk all screens to collect (id, handler) pairs for a widget type."""
        handlers = []
        for screen in self._screens:
            self._walk_for_handlers(screen.children, node_type, attr_name, handlers)
        return handlers

    def _walk_for_handlers(self, children, node_type, attr_name, handlers):
        for child in children:
            if isinstance(child, node_type):
                handler = getattr(child, attr_name, None)
                node_id = getattr(child, 'button_id', None) or getattr(child, 'input_id', None)
                if handler:
                    handlers.append((node_id, handler))
            if hasattr(child, 'children'):
                self._walk_for_handlers(child.children, node_type, attr_name, handlers)
            if isinstance(child, TabsNode):
                for tab in child.tabs:
                    self._walk_for_handlers(tab.children, node_type, attr_name, handlers)
            if isinstance(child, TableNode):
                pass  # No children to walk

    # ------------------------------------------------------------------
    # User functions
    # ------------------------------------------------------------------

    def _emit_functions(self, py: PyBuilder):
        """Emit user-defined q:function nodes as app methods."""
        for func in self._functions:
            py.blank()
            params = 'self'
            if hasattr(func, 'params') and func.params:
                param_names = ', '.join(p.name for p in func.params)
                params = f'self, {param_names}'

            py.method_def(py_id(func.name), params)

            if hasattr(func, 'body') and func.body:
                for stmt in func.body:
                    if isinstance(stmt, RawCodeNode_Terminal):
                        py.line(stmt.code)
                    elif isinstance(stmt, SetNode):
                        py.line(f'self.{py_id(stmt.name)} = {self._format_value(stmt.value, getattr(stmt, "type", "string"))}')
                    else:
                        py.comment(f'TODO: {type(stmt).__name__}')
            else:
                py.pass_stmt()

            py.end_block()

    # ------------------------------------------------------------------
    # Query functions
    # ------------------------------------------------------------------

    def _emit_queries(self, py: PyBuilder):
        """Emit q:query nodes as database access methods."""
        for query in self._queries:
            py.blank()
            py.method_def(f'query_{py_id(query["name"])}', 'self')
            py.docstring(f'Execute query: {query["name"]}')
            ds = query.get('datasource', 'app.db')
            sql = query.get('sql', '').strip()
            py.line(f'conn = sqlite3.connect({py_string(ds)})')
            py.line('cursor = conn.cursor()')
            py.line(f'cursor.execute({py_string(sql)})')
            py.line('columns = [desc[0] for desc in cursor.description] if cursor.description else []')
            py.line('rows = [dict(zip(columns, row)) for row in cursor.fetchall()]')
            py.line('conn.close()')
            py.return_stmt('rows')
            py.end_block()

    # ------------------------------------------------------------------
    # Action methods for keybindings & timers
    # ------------------------------------------------------------------

    def _emit_action_methods(self, py: PyBuilder):
        """Emit action_ methods for keybindings and timers."""
        emitted = set()

        # Built-in actions don't need methods
        builtin_actions = {'quit', 'toggle_dark', 'bell', 'screenshot'}

        all_actions = set()
        for kb in self._keybindings:
            all_actions.add(kb['action'])
        for timer in self._timers:
            all_actions.add(timer['action'])

        # Collect actions from button/input handlers
        button_handlers = self._collect_handlers_of_type(ButtonNode, 'on_click')
        input_handlers = self._collect_handlers_of_type(TerminalInputNode, 'on_submit')
        for _, action in button_handlers:
            all_actions.add(action)
        for _, action in input_handlers:
            all_actions.add(action)

        # Check which actions already have a user function
        user_func_names = {f.name for f in self._functions}

        for action in sorted(all_actions):
            if action in builtin_actions:
                continue
            if action in emitted:
                continue
            emitted.add(action)

            py.blank()
            safe_action = py_id(action)

            # If user defined a function with this name, the action calls it
            if action in user_func_names:
                py.method_def(f'action_{safe_action}', 'self')
                py.docstring(f'Action: {action}')
                py.line(f'self.{safe_action}()')
                py.end_block()
            else:
                py.method_def(f'action_{safe_action}', 'self')
                py.docstring(f'Action: {action}')
                py.line(f'self.notify({py_string(f"Action: {action}")})')
                py.end_block()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_default_value(self, var: Dict) -> str:
        """Convert a q:set variable to its Python reactive default."""
        val = var.get('value', '')
        vtype = var.get('type', 'string')
        return self._format_value(val, vtype)

    def _format_value(self, val: str, vtype: str) -> str:
        """Format a value string according to its type for Python code."""
        if vtype == 'integer':
            try:
                return str(int(val)) if val else '0'
            except (ValueError, TypeError):
                return '0'
        elif vtype == 'number' or vtype == 'float':
            try:
                return str(float(val)) if val else '0.0'
            except (ValueError, TypeError):
                return '0.0'
        elif vtype == 'boolean':
            if isinstance(val, str):
                return 'True' if val.lower() in ('true', '1', 'yes') else 'False'
            return py_bool(bool(val))
        elif vtype == 'array':
            if val and val.strip().startswith('['):
                return val
            return '[]'
        elif vtype == 'object':
            if val and val.strip().startswith('{'):
                return val
            return '{}'
        else:
            return py_string(val) if val else py_string('')
