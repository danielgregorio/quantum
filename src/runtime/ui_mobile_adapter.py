"""
UI Engine - React Native Mobile Adapter

Transforms UI AST nodes into a standalone React Native mobile application.
Generates App.js file with:
  - Mapped UI components to React Native equivalents
  - State management with useState hooks
  - Event handlers from q:function nodes
  - StyleSheet for styling

Component Mapping:
  - ui:window -> SafeAreaView + View
  - ui:text -> Text
  - ui:button -> TouchableOpacity
  - ui:input -> TextInput
  - ui:hbox -> View (flexDirection: 'row')
  - ui:vbox -> View (flexDirection: 'column')
  - ui:image -> Image
  - ui:list -> FlatList
  - etc.
"""

import re
from typing import List, Optional, Set, Dict, Any

from core.ast_nodes import QuantumNode
from core.features.conditionals.src.ast_node import IfNode
from core.features.loops.src.ast_node import LoopNode
from core.features.state_management.src.ast_node import SetNode
from core.features.functions.src.ast_node import FunctionNode
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
    UICardNode, UICardHeaderNode, UICardBodyNode, UICardFooterNode,
    UIModalNode, UIAlertNode, UIAvatarNode, UIDropdownNode,
    UIToastNode, UIToastContainerNode, UICarouselNode, UISlideNode,
    UIStepperNode, UIStepNode, UICalendarNode, UIDatePickerNode,
    UIAnimateNode, UIChartNode, UITooltipNode, UIBreadcrumbNode,
    UIBreadcrumbItemNode, UIPaginationNode, UISkeletonNode,
)
from runtime.ui_mobile_templates import (
    JsBuilder,
    REACT_NATIVE_APP_TEMPLATE,
    generate_imports,
    get_base_styles,
    rn_spacing,
    rn_size,
    rn_color,
    rn_font_size,
    rn_align,
    rn_justify,
    js_string,
    js_number,
)


class UIReactNativeAdapter:
    """Generates React Native app from UI AST nodes."""

    def __init__(self):
        self._widget_counter = 0
        self._components_used: Set[str] = set()
        self._styles_used: Set[str] = set()
        self._dynamic_styles: List[str] = []
        self._state_vars: Dict[str, Any] = {}
        self._functions: Dict[str, FunctionNode] = {}
        self._features_used: Set[str] = set()

    def _next_id(self, prefix: str = 'q') -> str:
        """Generate unique widget ID."""
        self._widget_counter += 1
        return f"{prefix}_{self._widget_counter}"

    def generate(
        self,
        windows: List[QuantumNode],
        ui_children: List[QuantumNode],
        title: str = "Quantum UI",
        functions: Optional[Dict[str, FunctionNode]] = None,
        state_vars: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate complete React Native app from UI AST.

        Args:
            windows: List of UIWindowNode elements.
            ui_children: List of top-level UI nodes (outside windows).
            title: App title (used in comments).
            functions: Dict of function name -> FunctionNode from q:function.
            state_vars: Dict of variable name -> initial value from q:set.

        Returns:
            Generated JavaScript/React Native source code.
        """
        # Reset state
        self._widget_counter = 0
        self._components_used = set()
        self._styles_used = set()
        self._dynamic_styles = []
        self._state_vars = state_vars or {}
        self._functions = functions or {}
        self._features_used = set()

        # Build JSX content
        jsx_builder = JsBuilder()
        jsx_builder._indent = 3  # Inside SafeAreaView

        # Render windows
        for window in windows:
            self._render_node(window, jsx_builder)

        # Render top-level children
        for child in ui_children:
            self._render_node(child, jsx_builder)

        jsx_content = jsx_builder.build()
        if not jsx_content.strip():
            jsx_content = '      <View style={styles.container}>\n        <Text>Empty UI</Text>\n      </View>'

        # Generate state declarations
        state_declarations = self._generate_state_declarations()

        # Generate function declarations
        function_declarations = self._generate_functions()

        # Generate imports
        imports = generate_imports(self._components_used)

        # Generate styles
        styles_content = get_base_styles(self._styles_used)
        if self._dynamic_styles:
            if styles_content:
                styles_content += '\n'
            styles_content += '\n'.join(self._dynamic_styles)

        # Build final code
        return REACT_NATIVE_APP_TEMPLATE.format(
            imports=imports,
            state_declarations=state_declarations,
            function_declarations=function_declarations,
            jsx_content=jsx_content,
            styles_content=styles_content,
        )

    def get_features_used(self) -> Set[str]:
        """Return set of features used during generation."""
        return self._features_used.copy()

    # ------------------------------------------------------------------
    # State and Functions Generation
    # ------------------------------------------------------------------

    def _generate_state_declarations(self) -> str:
        """Generate useState declarations for state variables."""
        if not self._state_vars:
            return '// No state variables'

        lines = []
        for name, value in self._state_vars.items():
            js_value = self._convert_value(value)
            # Capitalize first letter for setter
            setter_name = f"set{name[0].upper()}{name[1:]}"
            lines.append(f"const [{name}, {setter_name}] = useState({js_value});")

        return '\n'.join(lines)

    def _generate_functions(self) -> str:
        """Generate function declarations from q:function nodes."""
        if not self._functions:
            return '// No function handlers'

        functions = []
        for func_name, func_node in self._functions.items():
            func_code = self._generate_function(func_name, func_node)
            functions.append(func_code)

        return '\n\n'.join(functions)

    def _generate_function(self, func_name: str, func_node: FunctionNode) -> str:
        """Generate a JavaScript function from q:function node."""
        lines = [f"const {func_name} = useCallback((args) => {{"]

        # Generate body from function statements
        if func_node.body:
            for stmt in func_node.body:
                stmt_code = self._generate_statement(stmt)
                if stmt_code:
                    lines.append(f"  {stmt_code}")
        else:
            lines.append("  // Empty function")

        # Close with dependencies
        deps = self._get_state_deps(func_node)
        deps_str = ', '.join(deps) if deps else ''
        lines.append(f"}}, [{deps_str}]);")

        return '\n'.join(lines)

    def _generate_statement(self, stmt: QuantumNode) -> str:
        """Generate JavaScript code from a statement node."""
        if isinstance(stmt, SetNode):
            value_expr = self._convert_expression(stmt.value)
            setter_name = f"set{stmt.name[0].upper()}{stmt.name[1:]}"
            return f"{setter_name}({value_expr});"

        return f"// Unsupported statement: {type(stmt).__name__}"

    def _get_state_deps(self, func_node: FunctionNode) -> List[str]:
        """Get state variables used in a function for useCallback deps."""
        deps = set()
        for stmt in func_node.body or []:
            if isinstance(stmt, SetNode):
                # Check if value references other state vars
                if stmt.value:
                    for var_name in self._state_vars.keys():
                        if var_name in str(stmt.value):
                            deps.add(var_name)
        return sorted(deps)

    def _convert_expression(self, expr: str) -> str:
        """Convert a Quantum expression to JavaScript."""
        if expr is None:
            return 'null'

        expr = expr.strip()
        if expr.startswith('{') and expr.endswith('}'):
            expr = expr[1:-1].strip()

        # Replace variable references
        for var_name in self._state_vars.keys():
            expr = re.sub(rf'\b{var_name}\b', var_name, expr)

        return expr

    def _convert_value(self, value: Any) -> str:
        """Convert a value to JavaScript literal."""
        if value is None:
            return 'null'

        if isinstance(value, str):
            # Already a JS expression (starts/ends with quotes)
            if (value.startswith("'") and value.endswith("'")) or \
               (value.startswith('"') and value.endswith('"')):
                return value

            if value.isdigit():
                return value
            try:
                float(value)
                return value
            except ValueError:
                pass

            if value.lower() == 'true':
                return 'true'
            if value.lower() == 'false':
                return 'false'

            return js_string(value)

        return str(value)

    # ------------------------------------------------------------------
    # Style Helpers
    # ------------------------------------------------------------------

    def _build_style_props(self, node, base_style: str = None) -> Dict[str, str]:
        """Build style properties for a node."""
        styles = []
        if base_style:
            styles.append(f"styles.{base_style}")

        # Check for dynamic style from layout attributes
        dynamic_id = self._generate_layout_style(node)
        if dynamic_id:
            styles.append(f"styles.{dynamic_id}")

        if not styles:
            return {}

        if len(styles) == 1:
            return {'style': styles[0]}
        else:
            return {'style': f"[{', '.join(styles)}]"}

    def _generate_layout_style(self, node) -> Optional[str]:
        """Generate dynamic style for layout attributes.

        Returns style name if generated, None otherwise.
        """
        rules = []

        if hasattr(node, 'gap') and node.gap:
            rules.append(f"    gap: {rn_spacing(node.gap)},")
            self._features_used.add('gap')

        if hasattr(node, 'padding') and node.padding:
            rules.append(f"    padding: {rn_spacing(node.padding)},")

        if hasattr(node, 'margin') and node.margin:
            rules.append(f"    margin: {rn_spacing(node.margin)},")

        if hasattr(node, 'align') and node.align:
            rules.append(f"    alignItems: {rn_align(node.align)},")

        if hasattr(node, 'justify') and node.justify:
            rules.append(f"    justifyContent: {rn_justify(node.justify)},")

        if hasattr(node, 'width') and node.width:
            val = rn_size(node.width)
            if val != 'undefined':
                rules.append(f"    width: {val},")

        if hasattr(node, 'height') and node.height:
            val = rn_size(node.height)
            if val != 'undefined':
                rules.append(f"    height: {val},")

        if hasattr(node, 'background') and node.background:
            rules.append(f"    backgroundColor: {rn_color(node.background)},")

        if hasattr(node, 'color') and node.color:
            rules.append(f"    color: {rn_color(node.color)},")

        if hasattr(node, 'border') and node.border:
            rules.append("    borderWidth: 1,")
            rules.append(f"    borderColor: {rn_color('border')},")

        if hasattr(node, 'visible') and node.visible == 'false':
            rules.append("    display: 'none',")

        if rules:
            style_id = self._next_id('dyn')
            style_def = f"  {style_id}: {{\n" + '\n'.join(rules) + "\n  },"
            self._dynamic_styles.append(style_def)
            return style_id

        return None

    # ------------------------------------------------------------------
    # Node Rendering Dispatch
    # ------------------------------------------------------------------

    def _render_node(self, node: QuantumNode, js: JsBuilder):
        """Dispatch node to its render method."""
        # Containers
        if isinstance(node, UIWindowNode):
            self._render_window(node, js)
        elif isinstance(node, UIHBoxNode):
            self._render_hbox(node, js)
        elif isinstance(node, UIVBoxNode):
            self._render_vbox(node, js)
        elif isinstance(node, UIPanelNode):
            self._render_panel(node, js)
        elif isinstance(node, UITabPanelNode):
            self._render_tabpanel(node, js)
        elif isinstance(node, UITabNode):
            self._render_tab(node, js)
        elif isinstance(node, UIGridNode):
            self._render_grid(node, js)
        elif isinstance(node, UIAccordionNode):
            self._render_accordion(node, js)
        elif isinstance(node, UISectionNode):
            self._render_section(node, js)
        elif isinstance(node, UIScrollBoxNode):
            self._render_scrollbox(node, js)
        elif isinstance(node, UIFormNode):
            self._render_form(node, js)
        elif isinstance(node, UIFormItemNode):
            self._render_formitem(node, js)
        elif isinstance(node, UISpacerNode):
            self._render_spacer(node, js)
        elif isinstance(node, UIDividedBoxNode):
            self._render_dividedbox(node, js)
        # Widgets
        elif isinstance(node, UITextNode):
            self._render_text(node, js)
        elif isinstance(node, UIButtonNode):
            self._render_button(node, js)
        elif isinstance(node, UIInputNode):
            self._render_input(node, js)
        elif isinstance(node, UICheckboxNode):
            self._render_checkbox(node, js)
        elif isinstance(node, UIRadioNode):
            self._render_radio(node, js)
        elif isinstance(node, UISwitchNode):
            self._render_switch(node, js)
        elif isinstance(node, UISelectNode):
            self._render_select(node, js)
        elif isinstance(node, UITableNode):
            self._render_table(node, js)
        elif isinstance(node, UIListNode):
            self._render_list(node, js)
        elif isinstance(node, UIItemNode):
            self._render_item(node, js)
        elif isinstance(node, UIImageNode):
            self._render_image(node, js)
        elif isinstance(node, UILinkNode):
            self._render_link(node, js)
        elif isinstance(node, UIProgressNode):
            self._render_progress(node, js)
        elif isinstance(node, UITreeNode):
            self._render_tree(node, js)
        elif isinstance(node, UIMenuNode):
            self._render_menu(node, js)
        elif isinstance(node, UIOptionNode):
            self._render_option(node, js)
        elif isinstance(node, UILogNode):
            self._render_log(node, js)
        elif isinstance(node, UIMarkdownNode):
            self._render_markdown(node, js)
        elif isinstance(node, UIHeaderNode):
            self._render_header(node, js)
        elif isinstance(node, UIFooterNode):
            self._render_footer(node, js)
        elif isinstance(node, UIRuleNode):
            self._render_rule(node, js)
        elif isinstance(node, UILoadingNode):
            self._render_loading(node, js)
        elif isinstance(node, UIBadgeNode):
            self._render_badge(node, js)
        # Component Library nodes
        elif isinstance(node, UICardNode):
            self._render_card(node, js)
        elif isinstance(node, UICardHeaderNode):
            self._render_card_header(node, js)
        elif isinstance(node, UICardBodyNode):
            self._render_card_body(node, js)
        elif isinstance(node, UICardFooterNode):
            self._render_card_footer(node, js)
        elif isinstance(node, UIModalNode):
            self._render_modal(node, js)
        elif isinstance(node, UIAlertNode):
            self._render_alert(node, js)
        elif isinstance(node, UIAvatarNode):
            self._render_avatar(node, js)
        elif isinstance(node, UIDropdownNode):
            self._render_dropdown(node, js)
        elif isinstance(node, UIToastNode):
            self._render_toast(node, js)
        elif isinstance(node, UIToastContainerNode):
            self._render_toast_container(node, js)
        elif isinstance(node, UICarouselNode):
            self._render_carousel(node, js)
        elif isinstance(node, UISlideNode):
            self._render_slide(node, js)
        elif isinstance(node, UIStepperNode):
            self._render_stepper(node, js)
        elif isinstance(node, UIStepNode):
            self._render_step(node, js)
        elif isinstance(node, UICalendarNode):
            self._render_calendar(node, js)
        elif isinstance(node, UIDatePickerNode):
            self._render_date_picker(node, js)
        elif isinstance(node, UIAnimateNode):
            self._render_animate(node, js)
        elif isinstance(node, UIChartNode):
            self._render_chart(node, js)
        elif isinstance(node, UITooltipNode):
            self._render_tooltip(node, js)
        elif isinstance(node, UIBreadcrumbNode):
            self._render_breadcrumb(node, js)
        elif isinstance(node, UIBreadcrumbItemNode):
            self._render_breadcrumb_item(node, js)
        elif isinstance(node, UIPaginationNode):
            self._render_pagination(node, js)
        elif isinstance(node, UISkeletonNode):
            self._render_skeleton(node, js)
        # Quantum passthrough
        elif isinstance(node, SetNode):
            js.comment(f'q:set {node.name} = {node.value}')
        elif isinstance(node, LoopNode):
            js.comment(f'q:loop {node.var_name}')
        elif isinstance(node, IfNode):
            js.comment(f'q:if {node.condition}')

    def _render_children(self, children: list, js: JsBuilder):
        for child in children:
            self._render_node(child, js)

    # ------------------------------------------------------------------
    # Container Renders
    # ------------------------------------------------------------------

    def _render_window(self, node: UIWindowNode, js: JsBuilder):
        self._components_used.add('View')
        self._styles_used.add('container')

        style_props = self._build_style_props(node, 'container')
        js.jsx_open('View', style_props)
        js.indent()
        self._render_children(node.children, js)
        js.dedent()
        js.jsx_close('View')

    def _render_hbox(self, node: UIHBoxNode, js: JsBuilder):
        self._components_used.add('View')
        self._styles_used.add('hbox')

        style_props = self._build_style_props(node, 'hbox')
        js.jsx_open('View', style_props)
        js.indent()
        self._render_children(node.children, js)
        js.dedent()
        js.jsx_close('View')

    def _render_vbox(self, node: UIVBoxNode, js: JsBuilder):
        self._components_used.add('View')
        self._styles_used.add('vbox')

        style_props = self._build_style_props(node, 'vbox')
        js.jsx_open('View', style_props)
        js.indent()
        self._render_children(node.children, js)
        js.dedent()
        js.jsx_close('View')

    def _render_panel(self, node: UIPanelNode, js: JsBuilder):
        self._components_used.add('View')
        self._components_used.add('Text')
        self._styles_used.add('panel')

        style_props = self._build_style_props(node, 'panel')
        js.jsx_open('View', style_props)
        js.indent()
        if node.title:
            js.jsx_open('Text', {'style': 'styles.panelTitle'})
            js.indent()
            js.jsx_text(node.title)
            js.dedent()
            js.jsx_close('Text')
        self._render_children(node.children, js)
        js.dedent()
        js.jsx_close('View')

    def _render_tabpanel(self, node: UITabPanelNode, js: JsBuilder):
        self._components_used.add('View')
        self._components_used.add('Text')
        self._components_used.add('TouchableOpacity')
        self._styles_used.add('tab')

        # Generate tab state
        tab_state_id = self._next_id('activeTab')

        js.jsx_open('View')
        js.indent()

        # Tab headers
        js.comment('Tab headers')
        js.jsx_open('View', {'style': 'styles.tabHeader'})
        js.indent()

        tabs = [c for c in node.children if isinstance(c, UITabNode)]
        for i, tab in enumerate(tabs):
            is_active = '{' + f'{tab_state_id} === {i}' + '}'
            on_press = '{() => set' + f'{tab_state_id[0].upper()}{tab_state_id[1:]}({i})' + '}'

            js.jsx_open('TouchableOpacity', {
                'style': f'[styles.tabButton, {tab_state_id} === {i} && styles.tabButtonActive]',
                'onPress': on_press,
            })
            js.indent()
            js.jsx_open('Text', {
                'style': f'[styles.tabButtonText, {tab_state_id} === {i} && styles.tabButtonTextActive]'
            })
            js.indent()
            js.jsx_text(tab.title)
            js.dedent()
            js.jsx_close('Text')
            js.dedent()
            js.jsx_close('TouchableOpacity')

        js.dedent()
        js.jsx_close('View')

        # Tab contents
        js.comment('Tab contents')
        for i, tab in enumerate(tabs):
            js.line(f'{{{tab_state_id} === {i} && (')
            js.indent()
            js.jsx_open('View', {'style': 'styles.tabContent'})
            js.indent()
            self._render_children(tab.children, js)
            js.dedent()
            js.jsx_close('View')
            js.dedent()
            js.line(')}')

        js.dedent()
        js.jsx_close('View')

        # Add tab state to state vars
        self._state_vars[tab_state_id] = '0'

    def _render_tab(self, node: UITabNode, js: JsBuilder):
        # Standalone tab renders as View
        self._components_used.add('View')
        style_props = self._build_style_props(node)
        js.jsx_open('View', style_props if style_props else None)
        js.indent()
        self._render_children(node.children, js)
        js.dedent()
        js.jsx_close('View')

    def _render_grid(self, node: UIGridNode, js: JsBuilder):
        self._components_used.add('View')

        # Grid layout using flexWrap
        grid_id = self._next_id('grid')
        cols = node.columns or '2'
        try:
            n = int(cols)
            item_width = f"'{100 / n:.2f}%'"
        except ValueError:
            item_width = "'50%'"

        self._dynamic_styles.append(f"""  {grid_id}: {{
    flexDirection: 'row',
    flexWrap: 'wrap',
  }},
  {grid_id}Item: {{
    width: {item_width},
  }},""")

        js.jsx_open('View', {'style': f'styles.{grid_id}'})
        js.indent()
        self._render_children(node.children, js)
        js.dedent()
        js.jsx_close('View')

    def _render_accordion(self, node: UIAccordionNode, js: JsBuilder):
        self._components_used.add('View')
        self._styles_used.add('accordion')

        js.jsx_open('View')
        js.indent()
        self._render_children(node.children, js)
        js.dedent()
        js.jsx_close('View')

    def _render_section(self, node: UISectionNode, js: JsBuilder):
        self._components_used.add('View')
        self._components_used.add('Text')
        self._components_used.add('TouchableOpacity')
        self._styles_used.add('accordion')

        section_id = self._next_id('expanded')
        initial = 'true' if node.expanded else 'false'
        self._state_vars[section_id] = initial

        js.jsx_open('View', {'style': 'styles.section'})
        js.indent()

        # Header (toggle)
        js.jsx_open('TouchableOpacity', {
            'style': 'styles.sectionHeader',
            'onPress': '{() => set' + f'{section_id[0].upper()}{section_id[1:]}(!{section_id})' + '}',
        })
        js.indent()
        js.jsx_open('Text', {'style': 'styles.sectionHeaderText'})
        js.indent()
        js.jsx_text(node.title)
        js.dedent()
        js.jsx_close('Text')
        js.dedent()
        js.jsx_close('TouchableOpacity')

        # Content (conditional)
        js.line(f'{{{section_id} && (')
        js.indent()
        js.jsx_open('View', {'style': 'styles.sectionContent'})
        js.indent()
        self._render_children(node.children, js)
        js.dedent()
        js.jsx_close('View')
        js.dedent()
        js.line(')}')

        js.dedent()
        js.jsx_close('View')

    def _render_scrollbox(self, node: UIScrollBoxNode, js: JsBuilder):
        self._components_used.add('ScrollView')
        self._styles_used.add('scrollbox')

        style_props = self._build_style_props(node, 'scrollbox')
        js.jsx_open('ScrollView', style_props)
        js.indent()
        self._render_children(node.children, js)
        js.dedent()
        js.jsx_close('ScrollView')

    def _render_form(self, node: UIFormNode, js: JsBuilder):
        self._components_used.add('View')
        self._styles_used.add('form')

        attrs = {'style': 'styles.form'}
        js.jsx_open('View', attrs)
        js.indent()
        self._render_children(node.children, js)

        # If there's an on_submit, the button should call it
        if node.on_submit:
            self._components_used.add('TouchableOpacity')
            self._components_used.add('Text')
            self._styles_used.add('button')
            js.jsx_open('TouchableOpacity', {
                'style': 'styles.button',
                'onPress': '{' + node.on_submit + '}',
            })
            js.indent()
            js.jsx_open('Text', {'style': 'styles.buttonText'})
            js.indent()
            js.jsx_text('Submit')
            js.dedent()
            js.jsx_close('Text')
            js.dedent()
            js.jsx_close('TouchableOpacity')

        js.dedent()
        js.jsx_close('View')

    def _render_formitem(self, node: UIFormItemNode, js: JsBuilder):
        self._components_used.add('View')
        self._components_used.add('Text')
        self._styles_used.add('form')

        js.jsx_open('View', {'style': 'styles.formItem'})
        js.indent()
        if node.label:
            js.jsx_open('Text', {'style': 'styles.formLabel'})
            js.indent()
            js.jsx_text(node.label)
            js.dedent()
            js.jsx_close('Text')
        self._render_children(node.children, js)
        js.dedent()
        js.jsx_close('View')

    def _render_spacer(self, node: UISpacerNode, js: JsBuilder):
        self._components_used.add('View')
        self._styles_used.add('spacer')

        if node.size:
            spacer_id = self._next_id('spacer')
            size_val = rn_spacing(node.size)
            self._dynamic_styles.append(f"""  {spacer_id}: {{
    height: {size_val},
    width: {size_val},
  }},""")
            js.jsx_open('View', {'style': f'styles.{spacer_id}'}, self_closing=True)
        else:
            js.jsx_open('View', {'style': 'styles.spacer'}, self_closing=True)

    def _render_dividedbox(self, node: UIDividedBoxNode, js: JsBuilder):
        self._components_used.add('View')

        direction = 'row' if node.direction == 'horizontal' else 'column'
        div_id = self._next_id('divided')
        self._dynamic_styles.append(f"""  {div_id}: {{
    flexDirection: '{direction}',
    flex: 1,
  }},""")

        js.jsx_open('View', {'style': f'styles.{div_id}'})
        js.indent()
        self._render_children(node.children, js)
        js.dedent()
        js.jsx_close('View')

    # ------------------------------------------------------------------
    # Widget Renders
    # ------------------------------------------------------------------

    def _render_text(self, node: UITextNode, js: JsBuilder):
        self._components_used.add('Text')
        self._styles_used.add('text')

        style_parts = ['styles.text']
        if node.weight == 'bold':
            style_parts.append('styles.textBold')

        # Dynamic font size
        if node.size:
            size_id = self._next_id('textSize')
            font_size = rn_font_size(node.size)
            self._dynamic_styles.append(f"  {size_id}: {{ fontSize: {font_size} }},")
            style_parts.append(f'styles.{size_id}')

        # Layout styles
        layout_id = self._generate_layout_style(node)
        if layout_id:
            style_parts.append(f'styles.{layout_id}')

        style_val = style_parts[0] if len(style_parts) == 1 else f'[{", ".join(style_parts)}]'
        js.jsx_open('Text', {'style': style_val})
        js.indent()

        # Check for data binding expressions
        content = node.content
        if '{' in content and '}' in content:
            # Convert {var} to {var} (JSX expression)
            js.jsx_text(content)
        else:
            js.jsx_text(content)

        js.dedent()
        js.jsx_close('Text')

    def _render_button(self, node: UIButtonNode, js: JsBuilder):
        self._components_used.add('TouchableOpacity')
        self._components_used.add('Text')
        self._styles_used.add('button')

        style_parts = ['styles.button']
        text_style = 'styles.buttonText'

        if node.variant:
            variant_map = {
                'secondary': 'buttonSecondary',
                'danger': 'buttonDanger',
                'success': 'buttonSuccess',
            }
            if node.variant in variant_map:
                style_parts.append(f'styles.{variant_map[node.variant]}')

        if node.disabled:
            style_parts.append('styles.buttonDisabled')

        style_val = style_parts[0] if len(style_parts) == 1 else f'[{", ".join(style_parts)}]'

        attrs = {'style': style_val}
        if node.on_click:
            attrs['onPress'] = '{' + node.on_click + '}'
        if node.disabled:
            attrs['disabled'] = '{true}'

        js.jsx_open('TouchableOpacity', attrs)
        js.indent()
        js.jsx_open('Text', {'style': text_style})
        js.indent()
        js.jsx_text(node.content)
        js.dedent()
        js.jsx_close('Text')
        js.dedent()
        js.jsx_close('TouchableOpacity')

    def _render_input(self, node: UIInputNode, js: JsBuilder):
        self._components_used.add('TextInput')
        self._styles_used.add('input')

        attrs = {'style': 'styles.input'}

        if node.placeholder:
            attrs['placeholder'] = node.placeholder

        if node.bind:
            attrs['value'] = '{' + node.bind + '}'
            setter = f"set{node.bind[0].upper()}{node.bind[1:]}"
            attrs['onChangeText'] = '{' + setter + '}'

        if node.input_type == 'password':
            attrs['secureTextEntry'] = '{true}'
        elif node.input_type == 'email':
            attrs['keyboardType'] = 'email-address'
        elif node.input_type == 'number':
            attrs['keyboardType'] = 'numeric'

        js.jsx_open('TextInput', attrs, self_closing=True)

    def _render_checkbox(self, node: UICheckboxNode, js: JsBuilder):
        self._components_used.add('View')
        self._components_used.add('Text')
        self._components_used.add('TouchableOpacity')
        self._styles_used.add('checkbox')

        check_id = node.bind or self._next_id('checked')
        if node.bind and node.bind not in self._state_vars:
            self._state_vars[node.bind] = 'false'

        js.jsx_open('TouchableOpacity', {
            'style': 'styles.checkboxRow',
            'onPress': '{() => set' + f'{check_id[0].upper()}{check_id[1:]}(!{check_id})' + '}',
        })
        js.indent()
        js.jsx_open('View', {
            'style': f'[styles.checkbox, {check_id} && styles.checkboxChecked]'
        })
        js.dedent()
        js.jsx_close('View')
        if node.label:
            js.jsx_open('Text', {'style': 'styles.checkboxLabel'})
            js.indent()
            js.jsx_text(node.label)
            js.dedent()
            js.jsx_close('Text')
        js.jsx_close('TouchableOpacity')

    def _render_radio(self, node: UIRadioNode, js: JsBuilder):
        self._components_used.add('View')
        self._components_used.add('Text')
        self._components_used.add('TouchableOpacity')
        self._styles_used.add('checkbox')

        radio_id = node.bind or self._next_id('radio')
        if node.bind and node.bind not in self._state_vars:
            self._state_vars[node.bind] = "''"

        js.jsx_open('View')
        js.indent()
        if node.options:
            for opt in node.options.split(','):
                opt = opt.strip()
                js.jsx_open('TouchableOpacity', {
                    'style': 'styles.checkboxRow',
                    'onPress': '{() => set' + f'{radio_id[0].upper()}{radio_id[1:]}({js_string(opt)})' + '}',
                })
                js.indent()
                js.jsx_open('View', {
                    'style': f'[styles.checkbox, {radio_id} === {js_string(opt)} && styles.checkboxChecked]'
                })
                js.dedent()
                js.jsx_close('View')
                js.jsx_open('Text', {'style': 'styles.checkboxLabel'})
                js.indent()
                js.jsx_text(opt)
                js.dedent()
                js.jsx_close('Text')
                js.jsx_close('TouchableOpacity')
        js.dedent()
        js.jsx_close('View')

    def _render_switch(self, node: UISwitchNode, js: JsBuilder):
        self._components_used.add('View')
        self._components_used.add('Text')
        self._components_used.add('Switch')
        self._styles_used.add('switch')

        switch_id = node.bind or self._next_id('switch')
        if node.bind and node.bind not in self._state_vars:
            self._state_vars[node.bind] = 'false'

        js.jsx_open('View', {'style': 'styles.switchRow'})
        js.indent()
        js.jsx_open('Switch', {
            'value': '{' + switch_id + '}',
            'onValueChange': '{set' + f'{switch_id[0].upper()}{switch_id[1:]}' + '}',
        }, self_closing=True)
        if node.label:
            js.jsx_open('Text')
            js.indent()
            js.jsx_text(node.label)
            js.dedent()
            js.jsx_close('Text')
        js.dedent()
        js.jsx_close('View')

    def _render_select(self, node: UISelectNode, js: JsBuilder):
        # React Native doesn't have a built-in Select
        # Using a simple View with TouchableOpacity options
        self._components_used.add('View')
        self._components_used.add('Text')
        self._components_used.add('TouchableOpacity')
        self._styles_used.add('select')

        select_id = node.bind or self._next_id('select')
        if node.bind and node.bind not in self._state_vars:
            self._state_vars[node.bind] = "''"

        js.jsx_open('View', {'style': 'styles.select'})
        js.indent()
        if node.options:
            for opt in node.options.split(','):
                opt = opt.strip()
                js.jsx_open('TouchableOpacity', {
                    'onPress': '{() => set' + f'{select_id[0].upper()}{select_id[1:]}({js_string(opt)})' + '}',
                })
                js.indent()
                js.jsx_open('Text')
                js.indent()
                js.jsx_text(opt)
                js.dedent()
                js.jsx_close('Text')
                js.jsx_close('TouchableOpacity')
        js.dedent()
        js.jsx_close('View')

    def _render_table(self, node: UITableNode, js: JsBuilder):
        # Simplified table as rows
        self._components_used.add('View')
        self._components_used.add('Text')
        self._styles_used.add('list')

        columns = [c for c in node.children if isinstance(c, UIColumnNode)]

        js.jsx_open('View')
        js.indent()

        # Header row
        js.jsx_open('View', {'style': 'styles.listItem'})
        js.indent()
        for col in columns:
            js.jsx_open('Text', {'style': 'styles.textBold'})
            js.indent()
            js.jsx_text(col.label or col.key or '')
            js.dedent()
            js.jsx_close('Text')
        js.dedent()
        js.jsx_close('View')

        # Data rows (placeholder)
        if node.source:
            js.comment(f'Data source: {node.source}')

        js.dedent()
        js.jsx_close('View')

    def _render_list(self, node: UIListNode, js: JsBuilder):
        self._components_used.add('FlatList')
        self._components_used.add('View')
        self._styles_used.add('list')

        list_id = self._next_id('list')

        if node.source:
            # Use FlatList for data source
            js.jsx_open('FlatList', {
                'data': '{' + node.source.strip('{}') + '}',
                'renderItem': '{({item}) => <View style={styles.listItem}><Text>{item}</Text></View>}',
                'keyExtractor': '{(item, index) => index.toString()}',
            }, self_closing=True)
        else:
            # Static list
            js.jsx_open('View')
            js.indent()
            self._render_children(node.children, js)
            js.dedent()
            js.jsx_close('View')

    def _render_item(self, node: UIItemNode, js: JsBuilder):
        self._components_used.add('View')
        self._styles_used.add('list')

        js.jsx_open('View', {'style': 'styles.listItem'})
        js.indent()
        self._render_children(node.children, js)
        js.dedent()
        js.jsx_close('View')

    def _render_image(self, node: UIImageNode, js: JsBuilder):
        self._components_used.add('Image')
        self._styles_used.add('image')
        self._features_used.add('image')

        attrs = {'style': 'styles.image'}

        if node.src:
            if node.src.startswith('http'):
                attrs['source'] = "{{ uri: '" + node.src + "' }}"
            else:
                attrs['source'] = '{require(' + js_string(node.src) + ')}'

        if node.alt:
            attrs['accessibilityLabel'] = node.alt

        js.jsx_open('Image', attrs, self_closing=True)

    def _render_link(self, node: UILinkNode, js: JsBuilder):
        self._components_used.add('Text')
        self._components_used.add('TouchableOpacity')
        self._styles_used.add('link')

        if node.external:
            self._features_used.add('link_external')

        js.jsx_open('TouchableOpacity')
        js.indent()
        js.jsx_open('Text', {'style': 'styles.link'})
        js.indent()
        js.jsx_text(node.content)
        js.dedent()
        js.jsx_close('Text')
        js.dedent()
        js.jsx_close('TouchableOpacity')

    def _render_progress(self, node: UIProgressNode, js: JsBuilder):
        self._components_used.add('View')
        self._styles_used.add('progress')

        # Calculate percentage
        value = node.value or '0'
        max_val = node.max or '100'
        progress_id = self._next_id('prog')

        self._dynamic_styles.append(f"""  {progress_id}: {{
    width: '{value}%',
  }},""")

        js.jsx_open('View', {'style': 'styles.progressContainer'})
        js.indent()
        js.jsx_open('View', {'style': f'[styles.progressBar, styles.{progress_id}]'}, self_closing=True)
        js.dedent()
        js.jsx_close('View')

    def _render_tree(self, node: UITreeNode, js: JsBuilder):
        # Simple tree placeholder
        self._components_used.add('View')
        self._components_used.add('Text')

        js.jsx_open('View')
        js.indent()
        if node.source:
            js.jsx_open('Text')
            js.indent()
            js.jsx_text(f'Tree: {node.source}')
            js.dedent()
            js.jsx_close('Text')
        js.dedent()
        js.jsx_close('View')

    def _render_menu(self, node: UIMenuNode, js: JsBuilder):
        self._components_used.add('View')
        self._styles_used.add('menu')

        js.jsx_open('View', {'style': 'styles.menu'})
        js.indent()
        self._render_children(node.children, js)
        js.dedent()
        js.jsx_close('View')

    def _render_option(self, node: UIOptionNode, js: JsBuilder):
        self._components_used.add('TouchableOpacity')
        self._components_used.add('Text')
        self._styles_used.add('menu')

        attrs = {'style': 'styles.menuItem'}
        if node.on_click:
            attrs['onPress'] = '{' + node.on_click + '}'

        js.jsx_open('TouchableOpacity', attrs)
        js.indent()
        js.jsx_open('Text', {'style': 'styles.menuItemText'})
        js.indent()
        js.jsx_text(node.label or node.value or '')
        js.dedent()
        js.jsx_close('Text')
        js.dedent()
        js.jsx_close('TouchableOpacity')

    def _render_log(self, node: UILogNode, js: JsBuilder):
        # Log as ScrollView with Text
        self._components_used.add('ScrollView')
        self._components_used.add('Text')

        log_id = self._next_id('log')
        self._dynamic_styles.append(f"""  {log_id}: {{
    backgroundColor: '#1e293b',
    padding: 12,
    borderRadius: 6,
    maxHeight: 200,
  }},
  {log_id}Text: {{
    fontFamily: 'monospace',
    fontSize: 12,
    color: '#e2e8f0',
  }},""")

        js.jsx_open('ScrollView', {'style': f'styles.{log_id}'})
        js.indent()
        js.jsx_open('Text', {'style': f'styles.{log_id}Text'})
        js.indent()
        js.jsx_text('Log output...')
        js.dedent()
        js.jsx_close('Text')
        js.dedent()
        js.jsx_close('ScrollView')

    def _render_markdown(self, node: UIMarkdownNode, js: JsBuilder):
        # Markdown as plain Text (would need react-native-markdown)
        self._components_used.add('Text')

        js.jsx_open('Text')
        js.indent()
        js.jsx_text(node.content)
        js.dedent()
        js.jsx_close('Text')

    def _render_header(self, node: UIHeaderNode, js: JsBuilder):
        self._components_used.add('View')
        self._components_used.add('Text')
        self._styles_used.add('header')

        js.jsx_open('View', {'style': 'styles.header'})
        js.indent()
        js.jsx_open('Text', {'style': 'styles.headerText'})
        js.indent()
        if node.title:
            js.jsx_text(node.title)
        elif node.content:
            js.jsx_text(node.content)
        js.dedent()
        js.jsx_close('Text')
        self._render_children(node.children, js)
        js.dedent()
        js.jsx_close('View')

    def _render_footer(self, node: UIFooterNode, js: JsBuilder):
        self._components_used.add('View')
        self._components_used.add('Text')
        self._styles_used.add('footer')

        js.jsx_open('View', {'style': 'styles.footer'})
        js.indent()
        if node.content:
            js.jsx_open('Text', {'style': 'styles.footerText'})
            js.indent()
            js.jsx_text(node.content)
            js.dedent()
            js.jsx_close('Text')
        self._render_children(node.children, js)
        js.dedent()
        js.jsx_close('View')

    def _render_rule(self, node: UIRuleNode, js: JsBuilder):
        self._components_used.add('View')
        self._styles_used.add('rule')

        js.jsx_open('View', {'style': 'styles.rule'}, self_closing=True)

    def _render_loading(self, node: UILoadingNode, js: JsBuilder):
        self._components_used.add('View')
        self._components_used.add('ActivityIndicator')
        self._components_used.add('Text')
        self._styles_used.add('loading')

        js.jsx_open('View', {'style': 'styles.loading'})
        js.indent()
        js.jsx_open('ActivityIndicator', {'size': 'small', 'color': '#3b82f6'}, self_closing=True)
        if node.text:
            js.jsx_open('Text', {'style': 'styles.loadingText'})
            js.indent()
            js.jsx_text(node.text)
            js.dedent()
            js.jsx_close('Text')
        js.dedent()
        js.jsx_close('View')

    def _render_badge(self, node: UIBadgeNode, js: JsBuilder):
        self._components_used.add('View')
        self._components_used.add('Text')
        self._styles_used.add('badge')

        style_parts = ['styles.badge']
        text_style_parts = ['styles.badgeText']

        if node.variant:
            variant_map = {
                'primary': ('badgePrimary', 'badgePrimaryText'),
                'success': ('badgeSuccess', 'badgePrimaryText'),
                'danger': ('badgeDanger', 'badgePrimaryText'),
                'warning': ('badgeWarning', 'badgePrimaryText'),
            }
            if node.variant in variant_map:
                badge_style, text_style = variant_map[node.variant]
                style_parts.append(f'styles.{badge_style}')
                text_style_parts.append(f'styles.{text_style}')

        style_val = style_parts[0] if len(style_parts) == 1 else f'[{", ".join(style_parts)}]'
        text_style_val = text_style_parts[0] if len(text_style_parts) == 1 else f'[{", ".join(text_style_parts)}]'

        js.jsx_open('View', {'style': style_val})
        js.indent()
        js.jsx_open('Text', {'style': text_style_val})
        js.indent()
        js.jsx_text(node.content)
        js.dedent()
        js.jsx_close('Text')
        js.dedent()
        js.jsx_close('View')

    # ------------------------------------------------------------------
    # Component Library Renders
    # ------------------------------------------------------------------

    def _render_card(self, node: UICardNode, js: JsBuilder):
        self._components_used.add('View')
        self._styles_used.add('card')

        style_props = self._build_style_props(node, 'card')
        js.jsx_open('View', style_props)
        js.indent()
        self._render_children(node.children, js)
        js.dedent()
        js.jsx_close('View')

    def _render_card_header(self, node: UICardHeaderNode, js: JsBuilder):
        self._components_used.add('View')
        self._styles_used.add('card')

        js.jsx_open('View', {'style': 'styles.cardHeader'})
        js.indent()
        self._render_children(node.children, js)
        js.dedent()
        js.jsx_close('View')

    def _render_card_body(self, node: UICardBodyNode, js: JsBuilder):
        self._components_used.add('View')
        self._styles_used.add('card')

        js.jsx_open('View', {'style': 'styles.cardBody'})
        js.indent()
        self._render_children(node.children, js)
        js.dedent()
        js.jsx_close('View')

    def _render_card_footer(self, node: UICardFooterNode, js: JsBuilder):
        self._components_used.add('View')
        self._styles_used.add('card')

        js.jsx_open('View', {'style': 'styles.cardFooter'})
        js.indent()
        self._render_children(node.children, js)
        js.dedent()
        js.jsx_close('View')

    def _render_modal(self, node: UIModalNode, js: JsBuilder):
        self._components_used.add('Modal')
        self._components_used.add('View')
        self._components_used.add('Text')
        self._components_used.add('TouchableOpacity')
        self._styles_used.add('modal')

        modal_id = node.modal_id or self._next_id('modal')
        if modal_id not in self._state_vars:
            self._state_vars[modal_id] = 'true' if node.open else 'false'

        js.jsx_open('Modal', {
            'visible': '{' + modal_id + '}',
            'transparent': '{true}',
            'animationType': 'fade',
        })
        js.indent()
        js.jsx_open('View', {'style': 'styles.modalOverlay'})
        js.indent()
        js.jsx_open('View', {'style': 'styles.modalContent'})
        js.indent()

        # Title
        if node.title:
            js.jsx_open('Text', {'style': 'styles.modalTitle'})
            js.indent()
            js.jsx_text(node.title)
            js.dedent()
            js.jsx_close('Text')

        # Close button
        if node.closable:
            js.jsx_open('TouchableOpacity', {
                'style': 'styles.modalClose',
                'onPress': '{() => set' + f'{modal_id[0].upper()}{modal_id[1:]}(false)' + '}',
            })
            js.indent()
            js.jsx_open('Text')
            js.indent()
            js.jsx_text('✕')
            js.dedent()
            js.jsx_close('Text')
            js.dedent()
            js.jsx_close('TouchableOpacity')

        self._render_children(node.children, js)
        js.dedent()
        js.jsx_close('View')
        js.dedent()
        js.jsx_close('View')
        js.dedent()
        js.jsx_close('Modal')

    def _render_alert(self, node: UIAlertNode, js: JsBuilder):
        self._components_used.add('View')
        self._components_used.add('Text')
        self._styles_used.add('alert')

        variant_map = {
            'info': 'alertInfo',
            'success': 'alertSuccess',
            'warning': 'alertWarning',
            'danger': 'alertDanger',
        }
        variant_style = variant_map.get(node.variant, 'alertInfo')

        js.jsx_open('View', {'style': f'[styles.alert, styles.{variant_style}]'})
        js.indent()
        if node.title:
            js.jsx_open('Text', {'style': 'styles.alertTitle'})
            js.indent()
            js.jsx_text(node.title)
            js.dedent()
            js.jsx_close('Text')
        if node.content:
            js.jsx_open('Text', {'style': 'styles.alertText'})
            js.indent()
            js.jsx_text(node.content)
            js.dedent()
            js.jsx_close('Text')
        self._render_children(node.children, js)
        js.dedent()
        js.jsx_close('View')

    def _render_avatar(self, node: UIAvatarNode, js: JsBuilder):
        self._components_used.add('View')
        self._components_used.add('Text')
        self._styles_used.add('avatar')

        size_map = {
            'xs': 24,
            'sm': 32,
            'md': 40,
            'lg': 56,
            'xl': 72,
        }
        size = size_map.get(node.size, 40)
        avatar_id = self._next_id('avatar')

        self._dynamic_styles.append(f"""  {avatar_id}: {{
    width: {size},
    height: {size},
    borderRadius: {size // 2},
  }},""")

        if node.src:
            self._components_used.add('Image')
            js.jsx_open('Image', {
                'source': "{{ uri: '" + node.src + "' }}",
                'style': f'[styles.avatar, styles.{avatar_id}]',
            }, self_closing=True)
        else:
            # Show initials
            initials = ''
            if node.name:
                parts = node.name.split()
                initials = ''.join(p[0].upper() for p in parts[:2])

            js.jsx_open('View', {'style': f'[styles.avatar, styles.{avatar_id}]'})
            js.indent()
            js.jsx_open('Text', {'style': 'styles.avatarText'})
            js.indent()
            js.jsx_text(initials or '?')
            js.dedent()
            js.jsx_close('Text')
            js.dedent()
            js.jsx_close('View')

    def _render_dropdown(self, node: UIDropdownNode, js: JsBuilder):
        self._components_used.add('View')
        self._components_used.add('Text')
        self._components_used.add('TouchableOpacity')
        self._styles_used.add('dropdown')

        dropdown_id = self._next_id('dropdownOpen')
        self._state_vars[dropdown_id] = 'false'

        js.jsx_open('View')
        js.indent()

        # Trigger button
        js.jsx_open('TouchableOpacity', {
            'style': 'styles.dropdownTrigger',
            'onPress': '{() => set' + f'{dropdown_id[0].upper()}{dropdown_id[1:]}(!{dropdown_id})' + '}',
        })
        js.indent()
        js.jsx_open('Text')
        js.indent()
        js.jsx_text(node.label or 'Select')
        js.dedent()
        js.jsx_close('Text')
        js.dedent()
        js.jsx_close('TouchableOpacity')

        # Dropdown menu
        js.line(f'{{{dropdown_id} && (')
        js.indent()
        js.jsx_open('View', {'style': 'styles.dropdownMenu'})
        js.indent()
        self._render_children(node.children, js)
        js.dedent()
        js.jsx_close('View')
        js.dedent()
        js.line(')}')

        js.dedent()
        js.jsx_close('View')

    def _render_toast(self, node: UIToastNode, js: JsBuilder):
        self._components_used.add('View')
        self._components_used.add('Text')
        self._styles_used.add('toast')

        variant_map = {
            'info': 'toastInfo',
            'success': 'toastSuccess',
            'warning': 'toastWarning',
            'danger': 'toastDanger',
        }
        variant_style = variant_map.get(node.variant, 'toastInfo')

        js.jsx_open('View', {'style': f'[styles.toast, styles.{variant_style}]'})
        js.indent()
        if node.title:
            js.jsx_open('Text', {'style': 'styles.toastTitle'})
            js.indent()
            js.jsx_text(node.title)
            js.dedent()
            js.jsx_close('Text')
        js.jsx_open('Text', {'style': 'styles.toastText'})
        js.indent()
        js.jsx_text(node.message)
        js.dedent()
        js.jsx_close('Text')
        js.dedent()
        js.jsx_close('View')

    def _render_toast_container(self, node: UIToastContainerNode, js: JsBuilder):
        self._components_used.add('View')
        self._styles_used.add('toast')

        js.jsx_open('View', {'style': 'styles.toastContainer'}, self_closing=True)

    def _render_carousel(self, node: UICarouselNode, js: JsBuilder):
        self._components_used.add('ScrollView')
        self._components_used.add('View')
        self._styles_used.add('carousel')

        js.jsx_open('ScrollView', {
            'horizontal': '{true}',
            'pagingEnabled': '{true}',
            'showsHorizontalScrollIndicator': '{false}',
            'style': 'styles.carousel',
        })
        js.indent()
        self._render_children(node.children, js)
        js.dedent()
        js.jsx_close('ScrollView')

    def _render_slide(self, node: UISlideNode, js: JsBuilder):
        self._components_used.add('View')
        self._styles_used.add('carousel')

        js.jsx_open('View', {'style': 'styles.slide'})
        js.indent()
        self._render_children(node.children, js)
        js.dedent()
        js.jsx_close('View')

    def _render_stepper(self, node: UIStepperNode, js: JsBuilder):
        self._components_used.add('View')
        self._components_used.add('Text')
        self._styles_used.add('stepper')

        stepper_id = node.bind or self._next_id('currentStep')
        if stepper_id not in self._state_vars:
            self._state_vars[stepper_id] = str(node.current)

        steps = [c for c in node.children if isinstance(c, UIStepNode)]

        orientation = 'row' if node.orientation == 'horizontal' else 'column'
        stepper_style_id = self._next_id('stepper')
        self._dynamic_styles.append(f"""  {stepper_style_id}: {{
    flexDirection: '{orientation}',
    alignItems: 'center',
  }},""")

        js.jsx_open('View', {'style': f'styles.{stepper_style_id}'})
        js.indent()

        # Step indicators
        for i, step in enumerate(steps):
            is_active = f'{stepper_id} === {i}'
            is_complete = f'{stepper_id} > {i}'

            js.jsx_open('View', {'style': 'styles.stepItem'})
            js.indent()

            # Circle
            js.jsx_open('View', {
                'style': f'[styles.stepCircle, {is_active} && styles.stepCircleActive, {is_complete} && styles.stepCircleComplete]'
            })
            js.indent()
            js.jsx_open('Text', {'style': 'styles.stepNumber'})
            js.indent()
            js.jsx_text(str(i + 1))
            js.dedent()
            js.jsx_close('Text')
            js.dedent()
            js.jsx_close('View')

            # Label
            if node.show_labels and step.title:
                js.jsx_open('Text', {'style': 'styles.stepLabel'})
                js.indent()
                js.jsx_text(step.title)
                js.dedent()
                js.jsx_close('Text')

            js.dedent()
            js.jsx_close('View')

        js.dedent()
        js.jsx_close('View')

        # Step content
        for i, step in enumerate(steps):
            js.line(f'{{{stepper_id} === {i} && (')
            js.indent()
            js.jsx_open('View', {'style': 'styles.stepContent'})
            js.indent()
            self._render_children(step.children, js)
            js.dedent()
            js.jsx_close('View')
            js.dedent()
            js.line(')}')

    def _render_step(self, node: UIStepNode, js: JsBuilder):
        # Standalone step renders as View
        self._components_used.add('View')

        js.jsx_open('View')
        js.indent()
        self._render_children(node.children, js)
        js.dedent()
        js.jsx_close('View')

    def _render_calendar(self, node: UICalendarNode, js: JsBuilder):
        # Simplified calendar placeholder (real impl would need a calendar lib)
        self._components_used.add('View')
        self._components_used.add('Text')
        self._styles_used.add('calendar')

        js.jsx_open('View', {'style': 'styles.calendar'})
        js.indent()
        js.jsx_open('Text', {'style': 'styles.calendarPlaceholder'})
        js.indent()
        js.jsx_text('Calendar (requires react-native-calendars)')
        js.dedent()
        js.jsx_close('Text')
        js.dedent()
        js.jsx_close('View')

    def _render_date_picker(self, node: UIDatePickerNode, js: JsBuilder):
        self._components_used.add('View')
        self._components_used.add('TextInput')
        self._components_used.add('TouchableOpacity')
        self._components_used.add('Text')
        self._styles_used.add('input')

        picker_id = node.bind or self._next_id('date')
        if node.bind and node.bind not in self._state_vars:
            self._state_vars[node.bind] = "''"

        attrs = {'style': 'styles.input'}
        if node.placeholder:
            attrs['placeholder'] = node.placeholder
        if node.bind:
            attrs['value'] = '{' + node.bind + '}'

        js.jsx_open('View', {'style': 'styles.datePickerContainer'})
        js.indent()
        js.jsx_open('TextInput', attrs, self_closing=True)
        js.comment('Note: For full date picker, use @react-native-community/datetimepicker')
        js.dedent()
        js.jsx_close('View')

    # ------------------------------------------------------------------
    # Additional Component Renderers
    # ------------------------------------------------------------------

    def _render_animate(self, node: UIAnimateNode, js: JsBuilder):
        """Render animation wrapper using Animated API"""
        self._components_used.add('Animated')
        self._components_used.add('View')
        self._styles_used.add('animate')

        anim_type = getattr(node, 'type', 'fade') or 'fade'
        duration = getattr(node, 'duration', 300) or 300

        js.comment(f'Animation: {anim_type} ({duration}ms)')
        js.jsx_open('Animated.View', {'style': 'styles.animate'})
        js.indent()
        self._render_children(node.children, js)
        js.dedent()
        js.jsx_close('Animated.View')

    def _render_chart(self, node: UIChartNode, js: JsBuilder):
        """Render chart placeholder - requires react-native-chart-kit"""
        self._components_used.add('View')
        self._components_used.add('Text')
        self._styles_used.add('chart')

        chart_type = getattr(node, 'type', 'bar') or 'bar'

        js.jsx_open('View', {'style': 'styles.chart'})
        js.indent()
        js.jsx_open('Text', {'style': 'styles.chartPlaceholder'})
        js.indent()
        js.jsx_text(f'{chart_type.title()} Chart (requires react-native-chart-kit)')
        js.dedent()
        js.jsx_close('Text')
        js.dedent()
        js.jsx_close('View')

    def _render_tooltip(self, node: UITooltipNode, js: JsBuilder):
        """Render tooltip wrapper"""
        self._components_used.add('View')
        self._components_used.add('Text')
        self._styles_used.add('tooltip')

        content = getattr(node, 'content', '') or ''

        js.jsx_open('View', {'style': 'styles.tooltipContainer'})
        js.indent()
        self._render_children(node.children, js)
        if content:
            js.jsx_open('View', {'style': 'styles.tooltip'})
            js.indent()
            js.jsx_open('Text', {'style': 'styles.tooltipText'})
            js.indent()
            js.jsx_text(content)
            js.dedent()
            js.jsx_close('Text')
            js.dedent()
            js.jsx_close('View')
        js.dedent()
        js.jsx_close('View')

    def _render_breadcrumb(self, node: UIBreadcrumbNode, js: JsBuilder):
        """Render breadcrumb navigation"""
        self._components_used.add('View')
        self._components_used.add('Text')
        self._styles_used.add('breadcrumb')

        js.jsx_open('View', {'style': 'styles.breadcrumb'})
        js.indent()
        self._render_children(node.children, js)
        js.dedent()
        js.jsx_close('View')

    def _render_breadcrumb_item(self, node: UIBreadcrumbItemNode, js: JsBuilder):
        """Render breadcrumb item"""
        self._components_used.add('TouchableOpacity')
        self._components_used.add('Text')
        self._styles_used.add('breadcrumb')

        label = getattr(node, 'label', '') or getattr(node, 'content', '') or ''
        is_active = getattr(node, 'active', False)

        style = 'styles.breadcrumbItemActive' if is_active else 'styles.breadcrumbItem'

        js.jsx_open('TouchableOpacity', {'style': style})
        js.indent()
        js.jsx_open('Text', {'style': 'styles.breadcrumbText'})
        js.indent()
        js.jsx_text(label)
        js.dedent()
        js.jsx_close('Text')
        js.dedent()
        js.jsx_close('TouchableOpacity')

    def _render_pagination(self, node: UIPaginationNode, js: JsBuilder):
        """Render pagination controls"""
        self._components_used.add('View')
        self._components_used.add('TouchableOpacity')
        self._components_used.add('Text')
        self._styles_used.add('pagination')

        total = getattr(node, 'total', 1) or 1
        current = getattr(node, 'current', 1) or 1

        js.jsx_open('View', {'style': 'styles.pagination'})
        js.indent()
        # Previous button
        js.jsx_open('TouchableOpacity', {'style': 'styles.paginationButton'})
        js.indent()
        js.jsx_open('Text')
        js.jsx_text('←')
        js.dedent()
        js.jsx_close('Text')
        js.dedent()
        js.jsx_close('TouchableOpacity')
        # Page indicator
        js.jsx_open('Text', {'style': 'styles.paginationText'})
        js.indent()
        js.jsx_text(f'{current} / {total}')
        js.dedent()
        js.jsx_close('Text')
        # Next button
        js.jsx_open('TouchableOpacity', {'style': 'styles.paginationButton'})
        js.indent()
        js.jsx_open('Text')
        js.jsx_text('→')
        js.dedent()
        js.jsx_close('Text')
        js.dedent()
        js.jsx_close('TouchableOpacity')
        js.dedent()
        js.jsx_close('View')

    def _render_skeleton(self, node: UISkeletonNode, js: JsBuilder):
        """Render skeleton loading placeholder"""
        self._components_used.add('View')
        self._styles_used.add('skeleton')

        variant = getattr(node, 'variant', 'text') or 'text'
        width = getattr(node, 'width', None)
        height = getattr(node, 'height', None)

        style_parts = ['styles.skeleton']
        if variant == 'circle':
            style_parts.append('styles.skeletonCircle')
        elif variant == 'rect':
            style_parts.append('styles.skeletonRect')

        style = style_parts[0] if len(style_parts) == 1 else f'[{", ".join(style_parts)}]'

        attrs = {'style': style}
        js.jsx_open('View', attrs, self_closing=True)
