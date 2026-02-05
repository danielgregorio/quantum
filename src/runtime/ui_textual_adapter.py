"""
UI Engine - Textual Adapter

Transforms UI AST nodes into a standalone Python Textual (TUI) application.
"""

from typing import List, Optional

from core.ast_nodes import QuantumNode, SetNode, IfNode, LoopNode
from core.features.ui_engine.src.ast_nodes import (
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
)
from runtime.terminal_templates import PyBuilder, py_string, py_id


class UITextualAdapter:
    """Generates Python Textual app from UI AST nodes."""

    def __init__(self):
        self._indent = 2  # compose() body starts at indent 2

    def generate(self, windows: List[QuantumNode], ui_children: List[QuantumNode],
                 title: str = "Quantum UI") -> str:
        """Generate complete Python Textual app from UI AST."""
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
        if not compose_body.strip():
            compose_body = '        yield Static("Empty UI")'

        # Build CSS for panel styling
        css = self._build_css()

        # Use template
        from runtime.ui_textual_templates import UI_TEXTUAL_APP_TEMPLATE
        code = UI_TEXTUAL_APP_TEMPLATE.format(
            title=py_string(title),
            css=css,
            compose_body=compose_body,
            extra_imports='',
            bindings='',
            methods='    pass',
        )

        return code

    def _build_css(self) -> str:
        """Generate Textual CSS for common patterns."""
        return (
            "/* Quantum UI Textual CSS */\\n"
            ".q-panel { border: solid green; padding: 1 2; }\\n"
            ".q-panel-title { text-style: bold; }\\n"
        )

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
        # Quantum passthrough
        elif isinstance(node, SetNode):
            py.comment(f'q:set {node.name} = {node.value}')

    def _render_children(self, children: list, py: PyBuilder):
        for child in children:
            self._render_node(child, py)

    # ------------------------------------------------------------------
    # Container renders
    # ------------------------------------------------------------------

    def _render_window(self, node: UIWindowNode, py: PyBuilder):
        py.line(f'with Vertical():')
        py.indent()
        self._render_children(node.children, py)
        py.dedent()

    def _render_hbox(self, node: UIHBoxNode, py: PyBuilder):
        py.line(f'with Horizontal():')
        py.indent()
        self._render_children(node.children, py)
        py.dedent()

    def _render_vbox(self, node: UIVBoxNode, py: PyBuilder):
        py.line(f'with Vertical():')
        py.indent()
        self._render_children(node.children, py)
        py.dedent()

    def _render_panel(self, node: UIPanelNode, py: PyBuilder):
        py.line(f'with Vertical(classes="q-panel"):')
        py.indent()
        if node.title:
            py.line(f'yield Static({py_string(node.title)}, classes="q-panel-title")')
        self._render_children(node.children, py)
        py.dedent()

    def _render_tabpanel(self, node: UITabPanelNode, py: PyBuilder):
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
        py.line(f'with Vertical():')
        py.indent()
        self._render_children(node.children, py)
        py.dedent()

    def _render_grid(self, node: UIGridNode, py: PyBuilder):
        py.line(f'with Grid():')
        py.indent()
        self._render_children(node.children, py)
        py.dedent()

    def _render_accordion(self, node: UIAccordionNode, py: PyBuilder):
        # Render sections as individual Collapsible widgets
        for child in node.children:
            self._render_node(child, py)

    def _render_section(self, node: UISectionNode, py: PyBuilder):
        collapsed = 'False' if node.expanded else 'True'
        py.line(f'with Collapsible(title={py_string(node.title)}, collapsed={collapsed}):')
        py.indent()
        self._render_children(node.children, py)
        py.dedent()

    def _render_scrollbox(self, node: UIScrollBoxNode, py: PyBuilder):
        py.line(f'with ScrollableContainer():')
        py.indent()
        self._render_children(node.children, py)
        py.dedent()

    def _render_form(self, node: UIFormNode, py: PyBuilder):
        py.line(f'with Vertical():')
        py.indent()
        self._render_children(node.children, py)
        py.dedent()

    def _render_formitem(self, node: UIFormItemNode, py: PyBuilder):
        py.line(f'with Horizontal():')
        py.indent()
        if node.label:
            py.line(f'yield Label({py_string(node.label)})')
        self._render_children(node.children, py)
        py.dedent()

    def _render_spacer(self, node: UISpacerNode, py: PyBuilder):
        py.line(f'yield Static("")')

    def _render_dividedbox(self, node: UIDividedBoxNode, py: PyBuilder):
        container = 'Horizontal' if node.direction == 'horizontal' else 'Vertical'
        py.line(f'with {container}():')
        py.indent()
        self._render_children(node.children, py)
        py.dedent()

    # ------------------------------------------------------------------
    # Widget renders
    # ------------------------------------------------------------------

    def _render_text(self, node: UITextNode, py: PyBuilder):
        py.line(f'yield Static({py_string(node.content)})')

    def _render_button(self, node: UIButtonNode, py: PyBuilder):
        parts = [py_string(node.content)]
        if node.variant:
            parts.append(f'variant={py_string(node.variant)}')
        py.line(f'yield Button({", ".join(parts)})')

    def _render_input(self, node: UIInputNode, py: PyBuilder):
        parts = []
        if node.placeholder:
            parts.append(f'placeholder={py_string(node.placeholder)}')
        py.line(f'yield Input({", ".join(parts)})')

    def _render_checkbox(self, node: UICheckboxNode, py: PyBuilder):
        parts = []
        if node.label:
            parts.append(py_string(node.label))
        py.line(f'yield Checkbox({", ".join(parts)})')

    def _render_switch(self, node: UISwitchNode, py: PyBuilder):
        py.line(f'yield Switch()')

    def _render_select(self, node: UISelectNode, py: PyBuilder):
        if node.options:
            opts = [o.strip() for o in node.options.split(',')]
            opts_str = ', '.join(f'({py_string(o)}, {py_string(o)})' for o in opts)
            py.line(f'yield Select([{opts_str}])')
        else:
            py.line(f'yield Select([])')

    def _render_table(self, node: UITableNode, py: PyBuilder):
        py.line(f'yield DataTable()')

    def _render_progress(self, node: UIProgressNode, py: PyBuilder):
        py.line(f'yield ProgressBar()')

    def _render_tree(self, node: UITreeNode, py: PyBuilder):
        py.line(f'yield Tree("Tree")')

    def _render_log(self, node: UILogNode, py: PyBuilder):
        py.line(f'yield RichLog()')

    def _render_markdown(self, node: UIMarkdownNode, py: PyBuilder):
        py.line(f'yield Markdown({py_string(node.content)})')

    def _render_header(self, node: UIHeaderNode, py: PyBuilder):
        py.line(f'yield Header()')

    def _render_footer(self, node: UIFooterNode, py: PyBuilder):
        py.line(f'yield Footer()')

    def _render_rule(self, node: UIRuleNode, py: PyBuilder):
        py.line(f'yield Rule()')

    def _render_loading(self, node: UILoadingNode, py: PyBuilder):
        py.line(f'yield LoadingIndicator()')

    def _render_image(self, node: UIImageNode, py: PyBuilder):
        src = node.src or ''
        py.line(f'yield Static({py_string(f"[image: {src}]")})')

    def _render_link(self, node: UILinkNode, py: PyBuilder):
        py.line(f'yield Static({py_string(node.content)})')

    def _render_badge(self, node: UIBadgeNode, py: PyBuilder):
        py.line(f'yield Static({py_string(node.content)})')

    def _render_list(self, node: UIListNode, py: PyBuilder):
        py.line(f'with Vertical():')
        py.indent()
        self._render_children(node.children, py)
        py.dedent()

    def _render_item(self, node: UIItemNode, py: PyBuilder):
        py.line(f'with Horizontal():')
        py.indent()
        self._render_children(node.children, py)
        py.dedent()

    def _render_menu(self, node: UIMenuNode, py: PyBuilder):
        # OptionList for menu
        options = [c for c in node.children if isinstance(c, UIOptionNode)]
        if options:
            opts_str = ', '.join(py_string(o.label or o.value or '') for o in options)
            py.line(f'yield OptionList({opts_str})')
        else:
            py.line(f'yield OptionList()')

    def _render_option(self, node: UIOptionNode, py: PyBuilder):
        # Standalone options are unusual, render as Static
        py.line(f'yield Static({py_string(node.label or node.value or "")})')
