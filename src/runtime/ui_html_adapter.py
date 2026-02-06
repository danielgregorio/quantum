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

import re
from typing import Dict, List, Optional, Set, Tuple

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
    UILayoutMixin, UIValidatorNode, UIAnimateNode, UIAnimationMixin,
    # Component Library nodes
    UICardNode, UICardHeaderNode, UICardBodyNode, UICardFooterNode,
    UIModalNode, UIChartNode, UIAvatarNode, UITooltipNode,
    UIDropdownNode, UIAlertNode, UIBreadcrumbNode, UIBreadcrumbItemNode,
    UIPaginationNode, UISkeletonNode,
)
from runtime.ui_html_templates import (
    HtmlBuilder, HTML_TEMPLATE, CSS_RESET, CSS_THEME, TAB_JS,
    VALIDATION_JS, VALIDATION_CSS,
    PERSISTENCE_JS, generate_persistence_registration,
    CSS_ANIMATIONS, ANIMATION_JS,
)
from runtime.ui_tokens import TokenConverter
# Optional theming imports (may not be available)
try:
    from core.features.theming.src import (
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

    def _transform_onclick(self, handler: str) -> str:
        """Transform on-click handler for desktop mode."""
        if self._desktop_mode:
            return f"__quantumCall('{handler}')"
        return handler

    def _transform_onsubmit(self, handler: str) -> str:
        """Transform on-submit handler for desktop mode with form data collection."""
        if self._desktop_mode:
            return f"event.preventDefault();__quantumCall('{handler}',__quantumFormData(this))"
        return handler

    def _transform_onchange(self, handler: str) -> str:
        """Transform on-change handler for desktop mode."""
        if self._desktop_mode:
            return f"__quantumCall('{handler}',{{value:this.value}})"
        return handler

    def _add_input_binding(self, bind_name: str, element_id: str = None) -> str:
        """Add two-way binding for input elements in desktop mode.

        Returns the oninput handler string to add to the element.
        """
        if not self._desktop_mode or not bind_name:
            return ''
        return f"__quantumCall('__set_state',{{name:'{bind_name}',value:this.value}})"

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
            if self._desktop_mode:
                # Transform on-click for pywebview JS bridge
                btn_attrs['onclick'] = f"__quantumCall('{node.on_click}')"
            else:
                btn_attrs['onclick'] = node.on_click
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
