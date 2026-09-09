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
    UIValidatorNode, UIAnimateNode, UIAnimationMixin,
    # Component Library nodes
    UICardNode, UICardHeaderNode, UICardBodyNode, UICardFooterNode,
    UIModalNode, UIChartNode, UIAvatarNode, UITooltipNode,
    UIDropdownNode, UIAlertNode, UIBreadcrumbNode, UIBreadcrumbItemNode,
    UIPaginationNode, UISkeletonNode,
    UIToastNode, UIToastContainerNode,
    UICarouselNode, UISlideNode,
    UIStepperNode, UIStepNode,
    UICalendarNode, UIDatePickerNode,
)
from quantum.core.features.theming.src import UIThemeNode, UIColorNode


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
        'validator': '_parse_ui_validator',
        'animate': '_parse_ui_animate',
        # Component Library
        'card': '_parse_ui_card',
        'card-header': '_parse_ui_card_header',
        'card-body': '_parse_ui_card_body',
        'card-footer': '_parse_ui_card_footer',
        'modal': '_parse_ui_modal',
        'chart': '_parse_ui_chart',
        'avatar': '_parse_ui_avatar',
        'tooltip': '_parse_ui_tooltip',
        'dropdown': '_parse_ui_dropdown',
        'alert': '_parse_ui_alert',
        'breadcrumb': '_parse_ui_breadcrumb',
        'breadcrumb-item': '_parse_ui_breadcrumb_item',
        'pagination': '_parse_ui_pagination',
        'skeleton': '_parse_ui_skeleton',
        # Toast notifications
        'toast': '_parse_ui_toast',
        'toast-container': '_parse_ui_toast_container',
        # Carousel / slider
        'carousel': '_parse_ui_carousel',
        'slide': '_parse_ui_slide',
        # Stepper / wizard
        'stepper': '_parse_ui_stepper',
        'step': '_parse_ui_step',
        # Calendar / date picker
        'calendar': '_parse_ui_calendar',
        'date-picker': '_parse_ui_date_picker',
        # Theming
        'theme': '_parse_ui_theme',
        'color': '_parse_ui_color',
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
    # Animation attributes helper
    # ------------------------------------------------------------------

    def _apply_animation_attrs(self, node, element: ET.Element):
        """Apply animation attributes from XML element to node.

        Supports:
            - animate: Animation preset name (e.g., 'slide-in-left', 'fade-in')
            - transition: Transition shorthand (e.g., 'scale:0.95:100ms')
            - type: Animation type for ui:animate
            - duration: Animation duration in ms or CSS format
            - delay: Animation delay in ms or CSS format
            - easing: Easing function (ease, ease-in, ease-out, linear, etc.)
            - repeat: Repeat count ('1', '2', 'infinite')
            - trigger: Animation trigger (on-load, on-hover, on-click, on-visible)
            - direction: Animation direction (normal, reverse, alternate)
        """
        if not hasattr(node, '_init_animation_attrs'):
            return

        node.animate = element.get('animate')
        node.transition = element.get('transition')
        node.anim_type = element.get('type')
        node.anim_duration = element.get('duration')
        node.anim_delay = element.get('delay')
        node.anim_easing = element.get('easing')
        node.anim_repeat = element.get('repeat')
        node.anim_trigger = element.get('trigger')
        node.anim_direction = element.get('direction')

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

        # Validation attributes
        node.validation_mode = element.get('validation', 'both')
        node.error_display = element.get('error-display', 'inline')
        node.novalidate = self._parse_bool(element.get('novalidate'))

        self._apply_layout_attrs(node, element)

        # Parse children, separating validators from regular children
        for child in element:
            ns = self._get_namespace(child)
            local = self._get_local_name(child)

            if ns == 'ui' and local == 'validator':
                # Parse validator and add to form's validator list
                validator = self._parse_ui_validator(child)
                node.add_validator(validator)
            else:
                # Regular child element
                parsed = self._parse_child(child)
                if parsed:
                    node.add_child(parsed)

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

        # Validation attributes
        node.required = self._parse_bool(element.get('required'))
        node.min = element.get('min')
        node.max = element.get('max')
        node.pattern = element.get('pattern')
        node.error_message = element.get('error-message')

        # Integer-based validation attributes
        minlength_str = element.get('minlength')
        if minlength_str:
            node.minlength = self._parse_int(minlength_str)

        maxlength_str = element.get('maxlength')
        if maxlength_str:
            node.maxlength = self._parse_int(maxlength_str)

        # Custom validators (comma-separated list of validator names)
        validators_str = element.get('validators')
        if validators_str:
            node.validators = [v.strip() for v in validators_str.split(',')]

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

    def _parse_ui_validator(self, element: ET.Element) -> UIValidatorNode:
        """
        Parse <ui:validator> custom validation rule.

        Examples:
            <ui:validator name="phone" pattern="^\d{10}$" message="Invalid phone" />
            <ui:validator name="confirmPassword" match="password"
                          message="Passwords must match" />
            <ui:validator name="custom" expression="value.length > 5"
                          message="Too short" />
        """
        node = UIValidatorNode()

        # Identification
        node.name = element.get('name')
        node.field = element.get('field')

        # Validation rules
        node.rule_type = element.get('type')  # 'pattern', 'email', 'url', etc.
        node.pattern = element.get('pattern')
        node.match = element.get('match')
        node.min = element.get('min')
        node.max = element.get('max')
        node.expression = element.get('expression')
        node.server_expression = element.get('server-expression')

        # Integer validation attributes
        minlength_str = element.get('minlength')
        if minlength_str:
            node.minlength = self._parse_int(minlength_str)

        maxlength_str = element.get('maxlength')
        if maxlength_str:
            node.maxlength = self._parse_int(maxlength_str)

        # Error handling
        node.message = element.get('message')
        node.trigger = element.get('trigger', 'submit')

        return node

    # ------------------------------------------------------------------
    # Animation
    # ------------------------------------------------------------------

    def _parse_ui_animate(self, element: ET.Element) -> UIAnimateNode:
        """
        Parse <ui:animate> animation wrapper container.

        Wraps child elements and applies animation effects based on the
        specified animation type, duration, trigger, and other properties.

        Syntax examples:
            <ui:animate type="fade" duration="300" trigger="on-load">
                <ui:panel>Content fades in</ui:panel>
            </ui:animate>

            <ui:animate type="slide-left" delay="200" easing="ease-out">
                <ui:text>Slides in from left</ui:text>
            </ui:animate>

            <ui:animate type="scale" trigger="on-hover" duration="150">
                <ui:button>Hover me</ui:button>
            </ui:animate>

            <ui:animate type="bounce" repeat="infinite">
                <ui:badge>NEW</ui:badge>
            </ui:animate>

        Attributes:
            type: Animation type (fade, slide, scale, rotate, slide-left, etc.)
            duration: Animation duration in ms (default: 300)
            delay: Animation delay in ms (default: 0)
            easing: Easing function (ease, ease-in, ease-out, linear, spring)
            repeat: Repeat count (1, 2, ..., 'infinite')
            trigger: When to trigger (on-load, on-hover, on-click, on-visible)
            direction: Animation direction (normal, reverse, alternate)
        """
        node = UIAnimateNode()

        # Apply layout attributes
        self._apply_layout_attrs(node, element)

        # Apply animation attributes
        self._apply_animation_attrs(node, element)

        # Parse children
        self._parse_children(element, node)

        return node

    # ------------------------------------------------------------------
    # Component Library
    # ------------------------------------------------------------------

    def _parse_ui_card(self, element: ET.Element) -> UICardNode:
        """Parse <ui:card> - Card with header, body, footer."""
        node = UICardNode()
        node.title = element.get('title')
        node.subtitle = element.get('subtitle')
        node.image = element.get('image')
        node.variant = element.get('variant')
        self._apply_layout_attrs(node, element)
        self._parse_children(element, node)
        return node

    def _parse_ui_card_header(self, element: ET.Element) -> UICardHeaderNode:
        """Parse <ui:card-header> - Card header section."""
        node = UICardHeaderNode()
        self._apply_layout_attrs(node, element)
        self._parse_children(element, node)
        return node

    def _parse_ui_card_body(self, element: ET.Element) -> UICardBodyNode:
        """Parse <ui:card-body> - Card body section."""
        node = UICardBodyNode()
        self._apply_layout_attrs(node, element)
        self._parse_children(element, node)
        return node

    def _parse_ui_card_footer(self, element: ET.Element) -> UICardFooterNode:
        """Parse <ui:card-footer> - Card footer section."""
        node = UICardFooterNode()
        self._apply_layout_attrs(node, element)
        self._parse_children(element, node)
        return node

    def _parse_ui_modal(self, element: ET.Element) -> UIModalNode:
        """Parse <ui:modal> - Modal/dialog with open/close."""
        node = UIModalNode()
        node.title = element.get('title')
        node.modal_id = element.get('modal-id') or element.get('id')
        node.open = self._parse_bool(element.get('open'))
        node.closable = self._parse_bool(element.get('closable'), True)
        node.size = element.get('size')
        self._apply_layout_attrs(node, element)
        self._parse_children(element, node)
        return node

    def _parse_ui_chart(self, element: ET.Element) -> UIChartNode:
        """Parse <ui:chart> - Simple charts (bar, line, pie)."""
        node = UIChartNode()
        node.chart_type = element.get('type', 'bar')
        node.source = element.get('source')
        node.labels = element.get('labels')
        node.values = element.get('values')
        node.title = element.get('title')
        node.colors = element.get('colors')
        self._apply_layout_attrs(node, element)
        return node

    def _parse_ui_avatar(self, element: ET.Element) -> UIAvatarNode:
        """Parse <ui:avatar> - User avatar with image/initials."""
        node = UIAvatarNode()
        node.src = element.get('src')
        node.name = element.get('name')
        node.size = element.get('size')
        node.shape = element.get('shape', 'circle')
        node.status = element.get('status')
        self._apply_layout_attrs(node, element)
        return node

    def _parse_ui_tooltip(self, element: ET.Element) -> UITooltipNode:
        """Parse <ui:tooltip> - Tooltip on hover."""
        node = UITooltipNode()
        node.content = element.get('content') or (element.text or '').strip()
        node.position = element.get('position', 'top')
        self._apply_layout_attrs(node, element)
        self._parse_children(element, node)
        return node

    def _parse_ui_dropdown(self, element: ET.Element) -> UIDropdownNode:
        """Parse <ui:dropdown> - Dropdown menu."""
        node = UIDropdownNode()
        node.label = element.get('label')
        node.trigger = element.get('trigger', 'click')
        node.dropdown_align = element.get('align', 'left')
        self._apply_layout_attrs(node, element)
        self._parse_children(element, node)
        return node

    def _parse_ui_alert(self, element: ET.Element) -> UIAlertNode:
        """Parse <ui:alert> - Alert/notification box."""
        node = UIAlertNode()
        node.content = (element.text or '').strip()
        node.title = element.get('title')
        node.variant = element.get('variant', 'info')
        node.dismissible = self._parse_bool(element.get('dismissible'))
        node.icon = element.get('icon')
        self._apply_layout_attrs(node, element)
        self._parse_children(element, node)
        return node

    def _parse_ui_breadcrumb(self, element: ET.Element) -> UIBreadcrumbNode:
        """Parse <ui:breadcrumb> - Navigation breadcrumbs."""
        node = UIBreadcrumbNode()
        node.separator = element.get('separator', '/')
        self._apply_layout_attrs(node, element)
        self._parse_children(element, node)
        return node

    def _parse_ui_breadcrumb_item(self, element: ET.Element) -> UIBreadcrumbItemNode:
        """Parse <ui:breadcrumb-item> - Individual breadcrumb item."""
        node = UIBreadcrumbItemNode()
        node.label = element.get('label') or (element.text or '').strip()
        node.to = element.get('to')
        node.icon = element.get('icon')
        return node

    def _parse_ui_pagination(self, element: ET.Element) -> UIPaginationNode:
        """Parse <ui:pagination> - Pagination controls."""
        node = UIPaginationNode()
        node.total = element.get('total')
        node.page_size = element.get('page-size', '10')
        node.current = element.get('current', '1')
        node.bind = element.get('bind')
        node.on_change = element.get('on-change')
        node.show_total = self._parse_bool(element.get('show-total'))
        node.show_jump = self._parse_bool(element.get('show-jump'))
        self._apply_layout_attrs(node, element)
        return node

    def _parse_ui_skeleton(self, element: ET.Element) -> UISkeletonNode:
        """Parse <ui:skeleton> - Loading skeleton placeholder."""
        node = UISkeletonNode()
        node.variant = element.get('variant', 'text')
        node.lines = self._parse_int(element.get('lines'), 1)
        node.animated = self._parse_bool(element.get('animated'), True)
        self._apply_layout_attrs(node, element)
        return node

    # ------------------------------------------------------------------
    # Toast Notifications
    # ------------------------------------------------------------------

    def _parse_ui_toast(self, element: ET.Element) -> UIToastNode:
        """
        Parse <ui:toast> - Temporary notification message.

        Syntax:
            <ui:toast variant="success" position="top-right" duration="3000">
                File saved successfully!
            </ui:toast>

            <ui:toast variant="danger" title="Error" message="Could not save"
                      show="hasError" on-close="clearError()" />

        Attributes:
            variant: info, success, warning, danger
            position: top-right, top-left, bottom-right, bottom-left,
                      top-center, bottom-center
            duration: auto-dismiss time in ms (0 = no auto-dismiss)
            dismissible: show close button (default true)
            icon: icon name
            title: optional bold heading
            message: body text (falls back to the element text content)
            show: binding expression controlling visibility
            on-close: callback fired when the toast is dismissed
        """
        node = UIToastNode()
        node.variant = element.get('variant', 'info')
        node.position = element.get('position', 'top-right')
        node.duration = self._parse_int(element.get('duration'), 3000)
        node.dismissible = self._parse_bool(element.get('dismissible'), True)
        node.icon = element.get('icon')
        node.title = element.get('title')
        node.message = element.get('message') or (element.text or '').strip()
        node.show = element.get('show')
        node.on_close = element.get('on-close')
        self._apply_layout_attrs(node, element)
        return node

    def _parse_ui_toast_container(self, element: ET.Element) -> UIToastContainerNode:
        """
        Parse <ui:toast-container> - Host container for toast notifications.

        Syntax:
            <ui:toast-container position="top-right" max-toasts="5" />

        Attributes:
            position: default position for toasts spawned in this container
            max-toasts: maximum visible toasts (older ones are dismissed)
        """
        node = UIToastContainerNode()
        node.position = element.get('position', 'top-right')
        node.max_toasts = self._parse_int(element.get('max-toasts'), 5)
        self._apply_layout_attrs(node, element)
        return node

    # ------------------------------------------------------------------
    # Carousel / Slider
    # ------------------------------------------------------------------

    def _parse_ui_carousel(self, element: ET.Element) -> UICarouselNode:
        """
        Parse <ui:carousel> - Slider containing <ui:slide> children.

        Syntax:
            <ui:carousel auto-play="true" interval="4000"
                         show-indicators="true" show-arrows="true"
                         animation="slide">
                <ui:slide><ui:image src="a.jpg" /></ui:slide>
                <ui:slide><ui:image src="b.jpg" /></ui:slide>
            </ui:carousel>

        Attributes:
            auto-play: advance slides automatically (default false)
            interval: ms between slides when auto-playing (default 5000)
            show-indicators: render dot indicators (default true)
            show-arrows: render prev/next arrows (default true)
            loop: wrap around after the last slide (default true)
            animation: slide | fade
            current: initial slide index (0-based)
            bind: binding for the current slide index
            on-change: callback fired when the slide changes
        """
        node = UICarouselNode()
        node.auto_play = self._parse_bool(element.get('auto-play'))
        node.interval = self._parse_int(element.get('interval'), 5000)
        node.show_indicators = self._parse_bool(element.get('show-indicators'), True)
        node.show_arrows = self._parse_bool(element.get('show-arrows'), True)
        node.loop = self._parse_bool(element.get('loop'), True)
        node.animation = element.get('animation', 'slide')
        node.current = self._parse_int(element.get('current'), 0)
        node.bind = element.get('bind')
        node.on_change = element.get('on-change')
        self._apply_layout_attrs(node, element)
        # Parse child <ui:slide> elements (and any other allowed content)
        self._parse_children(element, node)
        return node

    def _parse_ui_slide(self, element: ET.Element) -> UISlideNode:
        """Parse <ui:slide> - Single slide inside a <ui:carousel>."""
        node = UISlideNode()
        self._apply_layout_attrs(node, element)
        self._parse_children(element, node)
        return node

    # ------------------------------------------------------------------
    # Stepper / Wizard
    # ------------------------------------------------------------------

    def _parse_ui_stepper(self, element: ET.Element) -> UIStepperNode:
        """
        Parse <ui:stepper> - Multi-step wizard containing <ui:step> children.

        Syntax:
            <ui:stepper orientation="horizontal" current="0" linear="true">
                <ui:step title="Account" description="Create account">...</ui:step>
                <ui:step title="Done" description="All set!">...</ui:step>
            </ui:stepper>

        Attributes:
            orientation: horizontal | vertical
            current: active step index (0-based)
            linear: steps must be completed in order (default true)
            show-labels: render step titles under the indicators (default true)
            clickable: allow clicking an indicator to navigate (default false)
            bind: binding for the current step index
            on-change: callback fired when the active step changes
            on-complete: callback fired when the last step is completed
        """
        node = UIStepperNode()
        node.orientation = element.get('orientation', 'horizontal')
        node.current = self._parse_int(element.get('current'), 0)
        node.linear = self._parse_bool(element.get('linear'), True)
        node.show_labels = self._parse_bool(element.get('show-labels'), True)
        node.clickable = self._parse_bool(element.get('clickable'))
        node.bind = element.get('bind')
        node.on_change = element.get('on-change')
        node.on_complete = element.get('on-complete')
        self._apply_layout_attrs(node, element)
        # Parse child <ui:step> elements
        self._parse_children(element, node)
        return node

    def _parse_ui_step(self, element: ET.Element) -> UIStepNode:
        """
        Parse <ui:step> - Single step inside a <ui:stepper>.

        Attributes:
            title: step title shown in the indicator (required)
            description: optional supporting text
            icon: optional icon name
            optional: step may be skipped (default false)
            completed: explicit completed-state override
            error: error message to display for this step
        """
        node = UIStepNode()
        node.title = element.get('title', '')
        node.description = element.get('description')
        node.icon = element.get('icon')
        node.optional = self._parse_bool(element.get('optional'))

        # completed is a tri-state override: leave as None when not declared
        completed_str = element.get('completed')
        if completed_str is not None:
            node.completed = self._parse_bool(completed_str)

        node.error = element.get('error')
        self._apply_layout_attrs(node, element)
        self._parse_children(element, node)
        return node

    # ------------------------------------------------------------------
    # Calendar / Date Picker
    # ------------------------------------------------------------------

    def _parse_ui_calendar(self, element: ET.Element) -> UICalendarNode:
        """
        Parse <ui:calendar> - Inline calendar for date selection.

        Syntax:
            <ui:calendar mode="single" bind="selectedDate" min-date="2024-01-01" />
            <ui:calendar mode="range" bind="dateRange" first-day-of-week="1" />

        Attributes:
            mode: single | range | multiple
            value: preselected date(s), ISO format (comma-separated for multiple)
            bind: binding for the selected date(s)
            min-date / max-date: selectable range bounds (ISO)
            disabled-dates: comma-separated ISO dates that cannot be picked
            disabled-days: comma-separated weekday numbers (0-6) to disable
            show-week-numbers: render the week-number column (default false)
            first-day-of-week: 0=Sunday .. 6=Saturday (default 0)
            locale: locale for month/day names (default 'en')
            inline: render inline instead of as a popup (default true)
            on-change: callback fired when the selection changes
            on-month-change: callback fired when navigating months
        """
        node = UICalendarNode()
        node.mode = element.get('mode', 'single')
        node.value = element.get('value')
        node.bind = element.get('bind')
        node.min_date = element.get('min-date')
        node.max_date = element.get('max-date')
        node.disabled_dates = element.get('disabled-dates')
        node.disabled_days = element.get('disabled-days')
        node.show_week_numbers = self._parse_bool(element.get('show-week-numbers'))
        node.first_day_of_week = self._parse_int(element.get('first-day-of-week'), 0)
        node.locale = element.get('locale', 'en')
        node.inline = self._parse_bool(element.get('inline'), True)
        node.on_change = element.get('on-change')
        node.on_month_change = element.get('on-month-change')
        self._apply_layout_attrs(node, element)
        return node

    def _parse_ui_date_picker(self, element: ET.Element) -> UIDatePickerNode:
        """
        Parse <ui:date-picker> - Text input with a calendar popup.

        Syntax:
            <ui:date-picker bind="birthDate" placeholder="Select date"
                            format="MM/DD/YYYY" min-date="2024-01-01" />

        Attributes:
            value: initial date (ISO)
            bind: binding for the selected date
            placeholder: input placeholder (default 'Select date')
            format: display format (default 'YYYY-MM-DD')
            min-date / max-date: selectable range bounds (ISO)
            clearable: show the clear button (default true)
            disabled: render the input as disabled (default false)
            required: mark the field as required (default false)
            on-change: callback fired when the date changes
        """
        node = UIDatePickerNode()
        node.value = element.get('value')
        node.bind = element.get('bind')
        node.placeholder = element.get('placeholder', 'Select date')
        node.format = element.get('format', 'YYYY-MM-DD')
        node.min_date = element.get('min-date')
        node.max_date = element.get('max-date')
        node.clearable = self._parse_bool(element.get('clearable'), True)
        node.disabled = self._parse_bool(element.get('disabled'))
        node.required = self._parse_bool(element.get('required'))
        node.on_change = element.get('on-change')
        self._apply_layout_attrs(node, element)
        return node

    # ------------------------------------------------------------------
    # Theming
    # ------------------------------------------------------------------

    def _parse_ui_theme(self, element: ET.Element) -> UIThemeNode:
        """
        Parse <ui:theme> theme configuration.

        Syntax examples:
            <!-- Use a preset theme -->
            <ui:theme preset="dark" />

            <!-- Custom theme extending a preset -->
            <ui:theme name="ocean" preset="light">
                <ui:color name="primary" value="#0ea5e9" />
                <ui:color name="secondary" value="#06b6d4" />
            </ui:theme>

            <!-- Auto-switch based on system preference -->
            <ui:theme preset="light" auto-switch="true" />

        Attributes:
            name: Custom theme name (optional)
            preset: Base theme preset ('light', 'dark')
            auto-switch: Enable automatic dark/light switching
        """
        node = UIThemeNode()

        node.name = element.get('name')
        node.preset = element.get('preset', 'light')
        node.auto_switch = self._parse_bool(element.get('auto-switch'))

        # Parse child <ui:color> elements
        for child in element:
            local = self._get_local_name(child)
            if local == 'color':
                color = self._parse_ui_color(child)
                node.add_color(color)

        return node

    def _parse_ui_color(self, element: ET.Element) -> UIColorNode:
        """
        Parse <ui:color> custom color definition.

        Syntax:
            <ui:color name="primary" value="#3b82f6" />
            <ui:color name="background" value="rgb(15, 23, 42)" />

        Attributes:
            name: Color token name (e.g., 'primary', 'background')
            value: CSS color value (hex, rgb, hsl, etc.)
        """
        node = UIColorNode()

        node.name = element.get('name', '')
        node.value = element.get('value', '')

        return node
