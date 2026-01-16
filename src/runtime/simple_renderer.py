"""
Simple Component Renderer - Renders AST to HTML

Supports:
- HTML tags with databinding
- q:set (variables)
- q:if/q:else
- q:loop
- q:function definitions
- q:call (function invocation)
"""

from typing import Dict, Any, List, Optional
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ast_nodes import *
from core.parser import QuantumParser
from runtime.databinding import resolve, evaluate, resolve_condition
from core.features.functions.src import FunctionRuntime, register_function


class SimpleRenderer:
    """Renders Quantum components to HTML"""

    def __init__(self):
        self.parser = QuantumParser()
        self.function_runtime = FunctionRuntime()

    def render_file(self, file_path: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Render component file to HTML

        Args:
            file_path: Path to .q file
            context: Initial context (variables, query params, etc)

        Returns:
            Rendered HTML string
        """
        # Parse file
        ast = self.parser.parse_file(file_path)

        # Initialize context
        if context is None:
            context = {}

        # Render component
        return self.render_component(ast, context)

    def render_component(self, component: ComponentNode, context: Dict[str, Any]) -> str:
        """Render component AST to HTML"""

        # Register functions
        for statement in component.statements:
            if isinstance(statement, FunctionNode):
                self.function_runtime.register_function(statement)

        # Render statements
        html_parts = []
        for statement in component.statements:
            rendered = self.render_statement(statement, context)
            if rendered:
                html_parts.append(rendered)

        return ''.join(html_parts)

    def render_statement(self, statement: QuantumNode, context: Dict[str, Any]) -> str:
        """Render single statement"""

        statement_type = type(statement).__name__

        # HTML elements
        if isinstance(statement, HTMLNode):
            return self.render_html_node(statement, context)

        # Text nodes
        if isinstance(statement, TextNode):
            return self.render_text_node(statement, context)

        # q:set
        if isinstance(statement, SetNode):
            self.execute_set(statement, context)
            return ""

        # q:if
        if isinstance(statement, IfNode):
            return self.render_if(statement, context)

        # q:loop
        if isinstance(statement, LoopNode):
            return self.render_loop(statement, context)

        # q:call
        if isinstance(statement, FunctionCallNode):
            return self.execute_function_call(statement, context)

        # q:function (definition, no output)
        if isinstance(statement, FunctionNode):
            return ""

        # Unknown statement
        return f"<!-- Unknown statement: {statement_type} -->"

    def render_html_node(self, node: HTMLNode, context: Dict[str, Any]) -> str:
        """Render HTML element"""

        # Resolve tag name
        tag = node.tag

        # Build attributes
        attrs = []
        if node.attributes:
            for key, value in node.attributes.items():
                # Resolve databinding in attribute values
                resolved_value = resolve(value, context)
                attrs.append(f'{key}="{resolved_value}"')

        attrs_str = ' ' + ' '.join(attrs) if attrs else ''

        # Self-closing tags
        if tag in HTML_VOID_ELEMENTS:
            return f'<{tag}{attrs_str} />'

        # Render children
        children_html = []
        if node.children:
            for child in node.children:
                child_html = self.render_statement(child, context)
                if child_html:
                    children_html.append(child_html)

        children_str = ''.join(children_html)

        return f'<{tag}{attrs_str}>{children_str}</{tag}>'

    def render_text_node(self, node: TextNode, context: Dict[str, Any]) -> str:
        """Render text with databinding"""
        if not node.content:
            return ""

        # Resolve databinding expressions
        return resolve(node.content, context)

    def execute_set(self, node: SetNode, context: Dict[str, Any]):
        """Execute q:set - Set variable in context"""

        value = node.value

        # Resolve databinding in value
        if value:
            # Check if it's a databinding expression or literal
            if '{' in value and '}' in value:
                # Has databinding, resolve it
                resolved_value = evaluate(value, context)
            else:
                # Literal value - try to parse as number or use as string
                resolved_value = self._parse_literal(value)
        else:
            resolved_value = node.default

        # Handle operations
        if node.operation == 'assign':
            context[node.name] = resolved_value
        elif node.operation == 'add':
            current = context.get(node.name, 0)
            context[node.name] = current + self._to_number(resolved_value)
        elif node.operation == 'subtract':
            current = context.get(node.name, 0)
            context[node.name] = current - self._to_number(resolved_value)
        elif node.operation == 'multiply':
            current = context.get(node.name, 1)
            context[node.name] = current * self._to_number(resolved_value)
        elif node.operation == 'divide':
            current = context.get(node.name, 1)
            context[node.name] = current / self._to_number(resolved_value)

    def render_if(self, node: IfNode, context: Dict[str, Any]) -> str:
        """Render q:if conditional"""

        # Evaluate condition
        condition_result = resolve_condition(node.condition, context)

        if condition_result:
            # Render if body
            html_parts = []
            for statement in node.body:
                rendered = self.render_statement(statement, context)
                if rendered:
                    html_parts.append(rendered)
            return ''.join(html_parts)
        else:
            # Check elseif
            if node.elseif_nodes:
                for elseif_node in node.elseif_nodes:
                    elseif_result = resolve_condition(elseif_node.condition, context)
                    if elseif_result:
                        html_parts = []
                        for statement in elseif_node.body:
                            rendered = self.render_statement(statement, context)
                            if rendered:
                                html_parts.append(rendered)
                        return ''.join(html_parts)

            # Render else body
            if node.else_body:
                html_parts = []
                for statement in node.else_body:
                    rendered = self.render_statement(statement, context)
                    if rendered:
                        html_parts.append(rendered)
                return ''.join(html_parts)

        return ""

    def render_loop(self, node: LoopNode, context: Dict[str, Any]) -> str:
        """Render q:loop"""

        html_parts = []

        if node.loop_type == 'range':
            # Range loop: from..to
            # Evaluate from/to values (might contain {variable})
            from_str = str(node.from_value) if node.from_value else "0"
            to_str = str(node.to_value) if node.to_value else "0"

            # Resolve any databinding in from/to
            if '{' in from_str:
                resolved_from = resolve(from_str, context)
                start_val = self._parse_literal(resolved_from)
            else:
                start_val = self._parse_literal(from_str)

            if '{' in to_str:
                resolved_to = resolve(to_str, context)
                end_val = self._parse_literal(resolved_to)
            else:
                end_val = self._parse_literal(to_str)

            start = int(start_val) if start_val is not None else 0
            end = int(end_val) if end_val is not None else 0
            step = int(node.step_value) if node.step_value else 1

            for i in range(start, end + 1, step):
                # Create loop context
                loop_context = context.copy()
                loop_context[node.var_name] = i

                # Render body
                for statement in node.body:
                    rendered = self.render_statement(statement, loop_context)
                    if rendered:
                        html_parts.append(rendered)

        elif node.loop_type == 'array':
            # Array loop
            array = evaluate(node.items, context) if node.items else []
            if isinstance(array, (list, tuple)):
                for item in array:
                    # Create loop context
                    loop_context = context.copy()
                    loop_context[node.var_name] = item

                    # Render body
                    for statement in node.body:
                        rendered = self.render_statement(statement, loop_context)
                        if rendered:
                            html_parts.append(rendered)

        return ''.join(html_parts)

    def execute_function_call(self, node: FunctionCallNode, context: Dict[str, Any]) -> str:
        """Execute q:call - Call function and optionally store result"""

        # Resolve arguments
        resolved_args = {}
        for key, value in node.args.items():
            resolved_args[key] = evaluate(value, context)

        # Call function
        try:
            result = self.function_runtime.call(node.function_name, resolved_args, context)

            # Store result if specified
            if node.result_var:
                context[node.result_var] = result
                return ""  # No output if storing result
            else:
                # Return result as string
                return str(result) if result is not None else ""

        except Exception as e:
            return f"<!-- Function call error: {e} -->"

    def _to_number(self, value: Any) -> float:
        """Convert value to number"""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return 0.0
        return 0.0

    def _parse_literal(self, value: str) -> Any:
        """Parse literal value (string, number, boolean, etc)"""
        value = value.strip()

        # Boolean
        if value.lower() == 'true':
            return True
        if value.lower() == 'false':
            return False

        # Null/None
        if value.lower() in ('null', 'none'):
            return None

        # Number
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # String (return as is)
        return value


# Helper function
def render(file_path: str, context: Optional[Dict[str, Any]] = None) -> str:
    """Render component file to HTML"""
    renderer = SimpleRenderer()
    return renderer.render_file(file_path, context)
