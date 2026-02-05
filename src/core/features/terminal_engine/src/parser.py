"""
Terminal Engine Parser - Parse qt: namespace elements into Terminal AST nodes.

This module provides parse functions for all terminal-specific tags.
It is called from the main QuantumParser when a qt: prefixed tag is encountered.
"""

from xml.etree import ElementTree as ET
from typing import Optional, List

from .ast_nodes import (
    ScreenNode, PanelNode, LayoutNode, TableNode, ColumnNode,
    TerminalInputNode, ButtonNode, MenuNode, OptionNode,
    TextNode_Terminal, ProgressNode, TreeNode, TabsNode, TabNode,
    LogNode_Terminal, HeaderNode_Terminal, FooterNode, StatusNode,
    KeybindingNode, TimerNode_Terminal, ServiceNode, CssNode,
    OnEventNode_Terminal, RawCodeNode_Terminal,
)


class TerminalParseError(Exception):
    """Terminal-specific parse error."""
    pass


class TerminalParser:
    """Parser for qt: namespace terminal elements."""

    def __init__(self, parent_parser):
        """
        Args:
            parent_parser: The main QuantumParser instance, used to parse
                           q: namespace children (q:set, q:function, q:if, etc.)
        """
        self.parent = parent_parser

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    TERMINAL_TAG_MAP = {
        'screen': '_parse_terminal_screen',
        'panel': '_parse_terminal_panel',
        'layout': '_parse_terminal_layout',
        'table': '_parse_terminal_table',
        'column': '_parse_terminal_column',
        'input': '_parse_terminal_input',
        'button': '_parse_terminal_button',
        'menu': '_parse_terminal_menu',
        'option': '_parse_terminal_option',
        'text': '_parse_terminal_text',
        'progress': '_parse_terminal_progress',
        'tree': '_parse_terminal_tree',
        'tabs': '_parse_terminal_tabs',
        'tab': '_parse_terminal_tab',
        'log': '_parse_terminal_log',
        'header': '_parse_terminal_header',
        'footer': '_parse_terminal_footer',
        'status': '_parse_terminal_status',
        'keybinding': '_parse_terminal_keybinding',
        'timer': '_parse_terminal_timer',
        'service': '_parse_terminal_service',
        'css': '_parse_terminal_css',
        'on': '_parse_terminal_on',
    }

    def parse_terminal_element(self, local_name: str, element: ET.Element):
        """Dispatch a qt: element to the correct parse method."""
        method_name = self.TERMINAL_TAG_MAP.get(local_name)
        if method_name is None:
            raise TerminalParseError(f"Unknown terminal tag: qt:{local_name}")
        method = getattr(self, method_name)
        return method(element)

    # ------------------------------------------------------------------
    # Helper: get local name from element
    # ------------------------------------------------------------------

    def _get_local_name(self, element: ET.Element) -> str:
        tag = element.tag
        if '}' in tag:
            return tag.split('}')[-1]
        if ':' in tag:
            return tag.split(':')[-1]
        return tag

    def _get_namespace(self, element: ET.Element) -> Optional[str]:
        tag = element.tag
        if '{https://quantum.lang/terminal}' in tag:
            return 'terminal'
        if '{https://quantum.lang/ns}' in tag:
            return 'quantum'
        if tag.startswith('qt:'):
            return 'terminal'
        if tag.startswith('q:'):
            return 'quantum'
        return None

    def _parse_float(self, value: Optional[str], default: float = 0) -> float:
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            return default

    def _parse_int(self, value: Optional[str], default: int = 0) -> int:
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    def _parse_bool(self, value: Optional[str], default: bool = False) -> bool:
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes')

    # ------------------------------------------------------------------
    # Parse children - dispatches both qt: and q: tags
    # ------------------------------------------------------------------

    def _parse_child(self, child: ET.Element):
        """Parse a child element that can be either qt: or q: namespace."""
        ns = self._get_namespace(child)
        local = self._get_local_name(child)

        if ns == 'terminal':
            return self.parse_terminal_element(local, child)
        elif ns == 'quantum':
            if local == 'function':
                return self._parse_terminal_function(child)
            return self.parent._parse_statement(child)
        return None

    def _parse_terminal_function(self, element: ET.Element):
        """Parse q:function with mixed raw Python code and XML statement children.

        Captures element.text and child.tail as RawCodeNode_Terminal, alongside
        regular q:set / q:if / etc children parsed normally.
        """
        func_node = self.parent._parse_function(element)

        mixed_body = []

        # Leading text before first child
        if element.text and element.text.strip():
            for line in element.text.strip().splitlines():
                line = line.strip()
                if line:
                    mixed_body.append(RawCodeNode_Terminal(line))

        # Process children: XML elements + their tail text
        for child in element:
            parsed = self._parse_child(child)
            if parsed:
                mixed_body.append(parsed)
            if child.tail and child.tail.strip():
                for line in child.tail.strip().splitlines():
                    line = line.strip()
                    if line:
                        mixed_body.append(RawCodeNode_Terminal(line))

        # Only replace body if we found raw code nodes
        has_raw = any(isinstance(n, RawCodeNode_Terminal) for n in mixed_body)
        if has_raw:
            func_node.body = mixed_body

        return func_node

    # ------------------------------------------------------------------
    # Core terminal nodes
    # ------------------------------------------------------------------

    def _parse_terminal_screen(self, element: ET.Element) -> ScreenNode:
        name = element.get('name', 'main')
        node = ScreenNode(name)
        node.title = element.get('title')

        for child in element:
            parsed = self._parse_child(child)
            if parsed:
                node.add_child(parsed)
        return node

    def _parse_terminal_panel(self, element: ET.Element) -> PanelNode:
        node = PanelNode()
        node.panel_id = element.get('id')
        node.title = element.get('title')

        for child in element:
            parsed = self._parse_child(child)
            if parsed:
                node.add_child(parsed)
        return node

    def _parse_terminal_layout(self, element: ET.Element) -> LayoutNode:
        node = LayoutNode()
        node.layout_id = element.get('id')
        node.direction = element.get('direction', 'vertical')

        for child in element:
            parsed = self._parse_child(child)
            if parsed:
                node.add_child(parsed)
        return node

    def _parse_terminal_table(self, element: ET.Element) -> TableNode:
        node = TableNode()
        node.table_id = element.get('id')
        node.data_source = element.get('data-source')
        node.zebra = self._parse_bool(element.get('zebra'))

        for child in element:
            local = self._get_local_name(child)
            ns = self._get_namespace(child)
            if ns == 'terminal' and local == 'column':
                col = self._parse_terminal_column(child)
                node.add_column(col)
        return node

    def _parse_terminal_column(self, element: ET.Element) -> ColumnNode:
        node = ColumnNode()
        node.name = element.get('name', '')
        node.key = element.get('key', '')
        node.width = self._parse_int(element.get('width')) if element.get('width') else None
        node.align = element.get('align', 'left')
        return node

    def _parse_terminal_input(self, element: ET.Element) -> TerminalInputNode:
        node = TerminalInputNode()
        node.input_id = element.get('id')
        node.placeholder = element.get('placeholder')
        node.on_submit = element.get('on-submit')
        node.password = self._parse_bool(element.get('password'))
        return node

    def _parse_terminal_button(self, element: ET.Element) -> ButtonNode:
        node = ButtonNode()
        node.button_id = element.get('id')
        node.label = element.get('label', '')
        node.variant = element.get('variant', 'default')
        node.on_click = element.get('on-click')
        return node

    def _parse_terminal_menu(self, element: ET.Element) -> MenuNode:
        node = MenuNode()
        node.menu_id = element.get('id')
        node.on_select = element.get('on-select')

        for child in element:
            local = self._get_local_name(child)
            ns = self._get_namespace(child)
            if ns == 'terminal' and local == 'option':
                opt = self._parse_terminal_option(child)
                node.add_option(opt)
        return node

    def _parse_terminal_option(self, element: ET.Element) -> OptionNode:
        node = OptionNode()
        node.value = element.get('value', '')
        node.label = element.get('label', '') or (element.text or '').strip()
        return node

    def _parse_terminal_text(self, element: ET.Element) -> TextNode_Terminal:
        node = TextNode_Terminal()
        node.text_id = element.get('id')
        node.content = (element.text or '').strip()
        return node

    def _parse_terminal_progress(self, element: ET.Element) -> ProgressNode:
        node = ProgressNode()
        node.progress_id = element.get('id')
        node.total = self._parse_float(element.get('total'), 100)
        node.value_var = element.get('value-var')
        return node

    def _parse_terminal_tree(self, element: ET.Element) -> TreeNode:
        node = TreeNode()
        node.tree_id = element.get('id')
        node.label = element.get('label', '')
        node.on_select = element.get('on-select')
        return node

    def _parse_terminal_tabs(self, element: ET.Element) -> TabsNode:
        node = TabsNode()
        node.tabs_id = element.get('id')

        for child in element:
            local = self._get_local_name(child)
            ns = self._get_namespace(child)
            if ns == 'terminal' and local == 'tab':
                tab = self._parse_terminal_tab(child)
                node.add_tab(tab)
        return node

    def _parse_terminal_tab(self, element: ET.Element) -> TabNode:
        node = TabNode()
        node.tab_id = element.get('id')
        node.title = element.get('title', '')

        for child in element:
            parsed = self._parse_child(child)
            if parsed:
                node.add_child(parsed)
        return node

    def _parse_terminal_log(self, element: ET.Element) -> LogNode_Terminal:
        node = LogNode_Terminal()
        node.log_id = element.get('id')
        node.auto_scroll = self._parse_bool(element.get('auto-scroll'), True)
        node.markup = self._parse_bool(element.get('markup'), True)
        node.max_lines = self._parse_int(element.get('max-lines')) if element.get('max-lines') else None
        return node

    def _parse_terminal_header(self, element: ET.Element) -> HeaderNode_Terminal:
        node = HeaderNode_Terminal()
        node.title = element.get('title')
        node.show_clock = self._parse_bool(element.get('show-clock'))
        return node

    def _parse_terminal_footer(self, element: ET.Element) -> FooterNode:
        return FooterNode()

    def _parse_terminal_status(self, element: ET.Element) -> StatusNode:
        node = StatusNode()
        node.status_id = element.get('id')
        node.content = (element.text or '').strip()
        return node

    def _parse_terminal_keybinding(self, element: ET.Element) -> KeybindingNode:
        node = KeybindingNode()
        node.key = element.get('key', '')
        node.action = element.get('action', '')
        node.description = element.get('description')
        return node

    def _parse_terminal_timer(self, element: ET.Element) -> TimerNode_Terminal:
        node = TimerNode_Terminal()
        node.timer_id = element.get('id')
        node.interval = self._parse_float(element.get('interval'), 1.0)
        node.action = element.get('action', '')
        return node

    def _parse_terminal_service(self, element: ET.Element) -> ServiceNode:
        node = ServiceNode()
        node.service_id = element.get('id')
        node.handler = element.get('handler', '')
        return node

    def _parse_terminal_css(self, element: ET.Element) -> CssNode:
        node = CssNode()
        node.content = (element.text or '').strip()
        return node

    def _parse_terminal_on(self, element: ET.Element) -> OnEventNode_Terminal:
        node = OnEventNode_Terminal()
        node.event = element.get('event', '')
        node.action = element.get('action', '')
        return node
