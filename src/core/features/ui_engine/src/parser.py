"""
UI Engine Parser - Parse ui: namespace elements into UI AST nodes.

This module provides parse functions for all UI-specific tags.
It is called from the main QuantumParser when a ui: prefixed tag is encountered.
"""

from xml.etree import ElementTree as ET
from typing import Optional, List

from .ast_nodes import (
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


class UIParseError(Exception):
    """UI-specific parse error."""
    pass


class UIParser:
    """Parser for ui: namespace UI elements."""

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

    UI_TAG_MAP = {
        'window': '_parse_ui_window',
        'hbox': '_parse_ui_hbox',
        'vbox': '_parse_ui_vbox',
        'panel': '_parse_ui_panel',
        'tabpanel': '_parse_ui_tabpanel',
        'tab': '_parse_ui_tab',
        'grid': '_parse_ui_grid',
        'accordion': '_parse_ui_accordion',
        'section': '_parse_ui_section',
        'dividedbox': '_parse_ui_dividedbox',
        'form': '_parse_ui_form',
        'formitem': '_parse_ui_formitem',
        'spacer': '_parse_ui_spacer',
        'scrollbox': '_parse_ui_scrollbox',
        'text': '_parse_ui_text',
        'button': '_parse_ui_button',
        'input': '_parse_ui_input',
        'checkbox': '_parse_ui_checkbox',
        'radio': '_parse_ui_radio',
        'switch': '_parse_ui_switch',
        'select': '_parse_ui_select',
        'table': '_parse_ui_table',
        'column': '_parse_ui_column',
        'list': '_parse_ui_list',
        'item': '_parse_ui_item',
        'image': '_parse_ui_image',
        'link': '_parse_ui_link',
        'progress': '_parse_ui_progress',
        'tree': '_parse_ui_tree',
        'menu': '_parse_ui_menu',
        'option': '_parse_ui_option',
        'log': '_parse_ui_log',
        'markdown': '_parse_ui_markdown',
        'header': '_parse_ui_header',
        'footer': '_parse_ui_footer',
        'rule': '_parse_ui_rule',
        'loading': '_parse_ui_loading',
        'badge': '_parse_ui_badge',
    }

    def parse_ui_element(self, local_name: str, element: ET.Element):
        """Dispatch a ui: element to the correct parse method."""
        method_name = self.UI_TAG_MAP.get(local_name)
        if method_name is None:
            raise UIParseError(f"Unknown UI tag: ui:{local_name}")
        method = getattr(self, method_name)
        return method(element)

    # ------------------------------------------------------------------
    # Helpers
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
        if '{https://quantum.lang/ui}' in tag:
            return 'ui'
        if '{https://quantum.lang/ns}' in tag:
            return 'quantum'
        if tag.startswith('ui:'):
            return 'ui'
        if tag.startswith('q:'):
            return 'quantum'
        return None

    def _parse_bool(self, value: Optional[str], default: bool = False) -> bool:
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes')

    def _parse_int(self, value: Optional[str], default: int = 0) -> int:
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    # ------------------------------------------------------------------
    # Layout attributes helper
    # ------------------------------------------------------------------

    def _apply_layout_attrs(self, node, element: ET.Element):
        """Apply common layout attributes from XML element to node."""
        node.gap = element.get('gap')
        node.padding = element.get('padding')
        node.margin = element.get('margin')
        node.align = element.get('align')
        node.justify = element.get('justify')
        node.width = element.get('width')
        node.height = element.get('height')
        node.background = element.get('background')
        node.color = element.get('color')
        node.border = element.get('border')
        node.ui_id = element.get('id')
        node.ui_class = element.get('class')
        node.visible = element.get('visible')

    # ------------------------------------------------------------------
    # Children dispatch - both ui: and q: tags
    # ------------------------------------------------------------------

    def _parse_child(self, child: ET.Element):
        """Parse a child element that can be either ui: or q: namespace."""
        ns = self._get_namespace(child)
        local = self._get_local_name(child)

        if ns == 'ui':
            return self.parse_ui_element(local, child)
        elif ns == 'quantum':
            return self.parent._parse_statement(child)
        return None

    def _parse_children(self, element: ET.Element, node):
        """Parse all children of an element, adding them to node."""
        for child in element:
            parsed = self._parse_child(child)
            if parsed:
                node.add_child(parsed)

    # ------------------------------------------------------------------
    # Containers
    # ------------------------------------------------------------------

    def _parse_ui_window(self, element: ET.Element) -> UIWindowNode:
        title = element.get('title')
        node = UIWindowNode(title)
        self._apply_layout_attrs(node, element)
        self._parse_children(element, node)
        return node

    def _parse_ui_hbox(self, element: ET.Element) -> UIHBoxNode:
        node = UIHBoxNode()
        self._apply_layout_attrs(node, element)
        self._parse_children(element, node)
        return node

    def _parse_ui_vbox(self, element: ET.Element) -> UIVBoxNode:
        node = UIVBoxNode()
        self._apply_layout_attrs(node, element)
        self._parse_children(element, node)
        return node

    def _parse_ui_panel(self, element: ET.Element) -> UIPanelNode:
        node = UIPanelNode()
        node.title = element.get('title')
        node.collapsible = self._parse_bool(element.get('collapsible'))
        self._apply_layout_attrs(node, element)
        self._parse_children(element, node)
        return node

    def _parse_ui_tabpanel(self, element: ET.Element) -> UITabPanelNode:
        node = UITabPanelNode()
        self._apply_layout_attrs(node, element)
        self._parse_children(element, node)
        return node

    def _parse_ui_tab(self, element: ET.Element) -> UITabNode:
        node = UITabNode()
        node.title = element.get('title', '')
        self._apply_layout_attrs(node, element)
        self._parse_children(element, node)
        return node

    def _parse_ui_grid(self, element: ET.Element) -> UIGridNode:
        node = UIGridNode()
        node.columns = element.get('columns')
        self._apply_layout_attrs(node, element)
        self._parse_children(element, node)
        return node

    def _parse_ui_accordion(self, element: ET.Element) -> UIAccordionNode:
        node = UIAccordionNode()
        self._apply_layout_attrs(node, element)
        self._parse_children(element, node)
        return node

    def _parse_ui_section(self, element: ET.Element) -> UISectionNode:
        node = UISectionNode()
        node.title = element.get('title', '')
        node.expanded = self._parse_bool(element.get('expanded'))
        self._apply_layout_attrs(node, element)
        self._parse_children(element, node)
        return node

    def _parse_ui_dividedbox(self, element: ET.Element) -> UIDividedBoxNode:
        node = UIDividedBoxNode()
        node.direction = element.get('direction', 'horizontal')
        self._apply_layout_attrs(node, element)
        self._parse_children(element, node)
        return node

    def _parse_ui_form(self, element: ET.Element) -> UIFormNode:
        node = UIFormNode()
        node.on_submit = element.get('on-submit')
        self._apply_layout_attrs(node, element)
        self._parse_children(element, node)
        return node

    def _parse_ui_formitem(self, element: ET.Element) -> UIFormItemNode:
        node = UIFormItemNode()
        node.label = element.get('label')
        self._apply_layout_attrs(node, element)
        self._parse_children(element, node)
        return node

    def _parse_ui_spacer(self, element: ET.Element) -> UISpacerNode:
        node = UISpacerNode()
        node.size = element.get('size')
        self._apply_layout_attrs(node, element)
        return node

    def _parse_ui_scrollbox(self, element: ET.Element) -> UIScrollBoxNode:
        node = UIScrollBoxNode()
        self._apply_layout_attrs(node, element)
        self._parse_children(element, node)
        return node

    # ------------------------------------------------------------------
    # Widgets
    # ------------------------------------------------------------------

    def _parse_ui_text(self, element: ET.Element) -> UITextNode:
        node = UITextNode()
        node.content = (element.text or '').strip()
        node.size = element.get('size')
        node.weight = element.get('weight')
        # color from layout attrs
        self._apply_layout_attrs(node, element)
        return node

    def _parse_ui_button(self, element: ET.Element) -> UIButtonNode:
        node = UIButtonNode()
        node.content = (element.text or '').strip()
        node.on_click = element.get('on-click')
        node.variant = element.get('variant')
        node.disabled = self._parse_bool(element.get('disabled'))
        self._apply_layout_attrs(node, element)
        return node

    def _parse_ui_input(self, element: ET.Element) -> UIInputNode:
        node = UIInputNode()
        node.bind = element.get('bind')
        node.placeholder = element.get('placeholder')
        node.input_type = element.get('type', 'text')
        node.on_change = element.get('on-change')
        node.on_submit = element.get('on-submit')
        self._apply_layout_attrs(node, element)
        return node

    def _parse_ui_checkbox(self, element: ET.Element) -> UICheckboxNode:
        node = UICheckboxNode()
        node.bind = element.get('bind')
        node.label = element.get('label')
        self._apply_layout_attrs(node, element)
        return node

    def _parse_ui_radio(self, element: ET.Element) -> UIRadioNode:
        node = UIRadioNode()
        node.bind = element.get('bind')
        node.options = element.get('options')
        self._apply_layout_attrs(node, element)
        return node

    def _parse_ui_switch(self, element: ET.Element) -> UISwitchNode:
        node = UISwitchNode()
        node.bind = element.get('bind')
        node.label = element.get('label')
        self._apply_layout_attrs(node, element)
        return node

    def _parse_ui_select(self, element: ET.Element) -> UISelectNode:
        node = UISelectNode()
        node.bind = element.get('bind')
        node.options = element.get('options')
        node.source = element.get('source')
        self._apply_layout_attrs(node, element)
        # Parse child <ui:option> elements
        self._parse_children(element, node)
        return node

    def _parse_ui_table(self, element: ET.Element) -> UITableNode:
        node = UITableNode()
        node.source = element.get('source')
        self._apply_layout_attrs(node, element)
        # Parse child <ui:column> elements
        self._parse_children(element, node)
        return node

    def _parse_ui_column(self, element: ET.Element) -> UIColumnNode:
        node = UIColumnNode()
        node.key = element.get('key')
        node.label = element.get('label')
        node.column_width = element.get('width')
        node.align = element.get('align')
        return node

    def _parse_ui_list(self, element: ET.Element) -> UIListNode:
        node = UIListNode()
        node.source = element.get('source')
        node.as_var = element.get('as')
        self._apply_layout_attrs(node, element)
        self._parse_children(element, node)
        return node

    def _parse_ui_item(self, element: ET.Element) -> UIItemNode:
        node = UIItemNode()
        self._apply_layout_attrs(node, element)
        self._parse_children(element, node)
        return node

    def _parse_ui_image(self, element: ET.Element) -> UIImageNode:
        node = UIImageNode()
        node.src = element.get('src')
        node.alt = element.get('alt')
        self._apply_layout_attrs(node, element)
        return node

    def _parse_ui_link(self, element: ET.Element) -> UILinkNode:
        node = UILinkNode()
        node.to = element.get('to')
        node.external = self._parse_bool(element.get('external'))
        node.content = (element.text or '').strip()
        self._apply_layout_attrs(node, element)
        return node

    def _parse_ui_progress(self, element: ET.Element) -> UIProgressNode:
        node = UIProgressNode()
        node.value = element.get('value')
        node.max = element.get('max')
        self._apply_layout_attrs(node, element)
        return node

    def _parse_ui_tree(self, element: ET.Element) -> UITreeNode:
        node = UITreeNode()
        node.source = element.get('source')
        node.on_select = element.get('on-select')
        self._apply_layout_attrs(node, element)
        return node

    def _parse_ui_menu(self, element: ET.Element) -> UIMenuNode:
        node = UIMenuNode()
        self._apply_layout_attrs(node, element)
        self._parse_children(element, node)
        return node

    def _parse_ui_option(self, element: ET.Element) -> UIOptionNode:
        node = UIOptionNode()
        node.value = element.get('value')
        node.label = element.get('label') or (element.text or '').strip()
        node.on_click = element.get('on-click')
        return node

    def _parse_ui_log(self, element: ET.Element) -> UILogNode:
        node = UILogNode()
        node.auto_scroll = self._parse_bool(element.get('auto-scroll'), True)
        node.max_lines = self._parse_int(element.get('max-lines')) if element.get('max-lines') else None
        self._apply_layout_attrs(node, element)
        return node

    def _parse_ui_markdown(self, element: ET.Element) -> UIMarkdownNode:
        node = UIMarkdownNode()
        node.content = (element.text or '').strip()
        self._apply_layout_attrs(node, element)
        return node

    def _parse_ui_header(self, element: ET.Element) -> UIHeaderNode:
        node = UIHeaderNode()
        node.title = element.get('title')
        node.content = (element.text or '').strip()
        self._apply_layout_attrs(node, element)
        self._parse_children(element, node)
        return node

    def _parse_ui_footer(self, element: ET.Element) -> UIFooterNode:
        node = UIFooterNode()
        node.content = (element.text or '').strip()
        self._apply_layout_attrs(node, element)
        self._parse_children(element, node)
        return node

    def _parse_ui_rule(self, element: ET.Element) -> UIRuleNode:
        return UIRuleNode()

    def _parse_ui_loading(self, element: ET.Element) -> UILoadingNode:
        node = UILoadingNode()
        node.text = element.get('text')
        self._apply_layout_attrs(node, element)
        return node

    def _parse_ui_badge(self, element: ET.Element) -> UIBadgeNode:
        node = UIBadgeNode()
        node.content = (element.text or '').strip()
        node.variant = element.get('variant')
        node.badge_color = element.get('color')
        self._apply_layout_attrs(node, element)
        return node
