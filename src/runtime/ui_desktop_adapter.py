"""
UI Engine - Desktop Adapter (pywebview wrapper)

Generates interactive Python pywebview desktop applications with:
- Bidirectional Python-JS communication via pywebview's JS API
- Reactive state management (QuantumState)
- Generated API class from q:function nodes (QuantumAPI)
- Event transformation (on-click, on-submit, bind)
"""

import re
from typing import List, Dict, Any, Optional

from core.ast_nodes import QuantumNode, SetNode
from core.features.functions.src.ast_node import FunctionNode
from runtime.ui_html_adapter import UIHtmlAdapter
from runtime.ui_desktop_templates import (
    QUANTUM_STATE_CLASS,
    QUANTUM_API_CLASS,
    JS_BRIDGE_CODE,
    DESKTOP_TEMPLATE,
)


class UIDesktopAdapter:
    """Generates Python pywebview app with JS bridge from UI AST nodes."""

    def __init__(self):
        self._functions: Dict[str, FunctionNode] = {}
        self._state_vars: Dict[str, Any] = {}

    def generate(
        self,
        windows: List[QuantumNode],
        ui_children: List[QuantumNode],
        title: str = "Quantum UI",
        functions: Optional[Dict[str, FunctionNode]] = None,
        state_vars: Optional[Dict[str, Any]] = None,
        width: int = 1024,
        height: int = 768,
    ) -> str:
        """Generate Python pywebview app with JS bridge from UI AST.

        Args:
            windows: List of UIWindowNode elements.
            ui_children: List of top-level UI nodes (outside windows).
            title: Window title.
            functions: Dict of function name -> FunctionNode from q:function.
            state_vars: Dict of variable name -> initial value from q:set.
            width: Window width in pixels.
            height: Window height in pixels.

        Returns:
            Generated Python source code as string.
        """
        self._functions = functions or {}
        self._state_vars = state_vars or {}

        # Generate HTML with desktop_mode=True for event transformation
        html_adapter = UIHtmlAdapter(desktop_mode=True)
        html = html_adapter.generate(windows, ui_children, title)

        # Inject JS bridge before </body>
        binding_script = html_adapter._generate_binding_script()
        js_injection = JS_BRIDGE_CODE
        if binding_script:
            js_injection += '\n' + binding_script

        html = html.replace('</body>', f'{js_injection}\n</body>')

        # Generate state initialization code
        state_init = self._generate_state_init()

        # Generate function methods
        function_methods = self._generate_functions()

        # Build the final Python code
        return DESKTOP_TEMPLATE.format(
            quantum_state_class=QUANTUM_STATE_CLASS,
            quantum_api_class=QUANTUM_API_CLASS.format(
                state_init=state_init,
                function_methods=function_methods,
            ),
            title=repr(title),
            width=width,
            height=height,
            html_content=repr(html),
        )

    def _generate_state_init(self) -> str:
        """Generate Python code to initialize state variables.

        Returns:
            Indented Python code for state initialization.
        """
        if not self._state_vars:
            return '        pass  # No state variables'

        lines = []
        for name, value in self._state_vars.items():
            # Convert value to Python representation
            py_value = self._convert_value(value)
            lines.append(f"        self.state.set('{name}', {py_value})")

        return '\n'.join(lines)

    def _generate_functions(self) -> str:
        """Generate Python methods from q:function nodes.

        Returns:
            Python code for all function methods.
        """
        if not self._functions:
            return '    pass  # No functions defined'

        methods = []
        for func_name, func_node in self._functions.items():
            method_code = self._generate_function_method(func_name, func_node)
            methods.append(method_code)

        return '\n\n'.join(methods)

    def _generate_function_method(self, func_name: str, func_node: FunctionNode) -> str:
        """Generate a Python method from a q:function node.

        Args:
            func_name: Name of the function.
            func_node: FunctionNode AST node.

        Returns:
            Python method code as string.
        """
        lines = [f"    def {func_name}(self, args=None):"]
        lines.append(f'        """Generated from q:function {func_name}"""')

        # Generate body from function statements
        if func_node.body:
            for stmt in func_node.body:
                stmt_code = self._generate_statement(stmt)
                if stmt_code:
                    lines.append(stmt_code)
        else:
            lines.append("        pass")

        return '\n'.join(lines)

    def _generate_statement(self, stmt: QuantumNode, indent: int = 8) -> str:
        """Generate Python code from a statement node.

        Args:
            stmt: A statement node (SetNode, etc.).
            indent: Number of spaces for indentation.

        Returns:
            Python code line.
        """
        pad = ' ' * indent

        if isinstance(stmt, SetNode):
            # Handle q:set statements
            value_expr = self._convert_expression(stmt.value)
            return f"{pad}self.state.set('{stmt.name}', {value_expr})"

        # TODO: Handle other statement types (IfNode, LoopNode, etc.)
        return f"{pad}pass  # Unsupported statement type: {type(stmt).__name__}"

    def _convert_expression(self, expr: str) -> str:
        """Convert a Quantum expression {var + 1} to Python.

        Args:
            expr: Expression string, possibly with {brackets}.

        Returns:
            Python expression string.
        """
        if expr is None:
            return 'None'

        # Remove surrounding braces if present
        expr = expr.strip()
        if expr.startswith('{') and expr.endswith('}'):
            expr = expr[1:-1].strip()

        # Replace variable references with self.state.get('var')
        # Pattern: word that's not a Python keyword or number
        def replace_var(match):
            var = match.group(0)
            # Skip Python keywords and built-ins
            if var in ('True', 'False', 'None', 'and', 'or', 'not', 'if', 'else', 'for', 'in', 'is'):
                return var
            # Skip if it looks like a number
            if var.isdigit():
                return var
            # Skip if it's a method call (followed by parenthesis)
            return f"self.state.get('{var}')"

        # Match word boundaries for variable names
        result = re.sub(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', replace_var, expr)

        return result

    def _convert_value(self, value: Any) -> str:
        """Convert a value to Python literal representation.

        Args:
            value: Value to convert (can be string, number, bool, etc.).

        Returns:
            Python literal string.
        """
        if value is None:
            return 'None'

        # Check if it's a string representation of a number
        if isinstance(value, str):
            # Try to parse as number
            if value.isdigit():
                return value
            try:
                float(value)
                return value
            except ValueError:
                pass

            # Boolean strings
            if value.lower() == 'true':
                return 'True'
            if value.lower() == 'false':
                return 'False'

            # Regular string
            return repr(value)

        # Already a Python value
        return repr(value)
