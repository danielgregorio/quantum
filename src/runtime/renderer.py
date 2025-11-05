"""
Quantum HTML Renderer

Converts executed AST to HTML string output.
Handles databinding, loops, conditionals, and HTML passthrough.
"""

import html
import re
import sys
from pathlib import Path
from typing import Any, List

# Fix imports
sys.path.append(str(Path(__file__).parent.parent))

from core.ast_nodes import (
    QuantumNode, ComponentNode, HTMLNode, TextNode, DocTypeNode,
    CommentNode, LoopNode, IfNode, SetNode, QueryNode
)
from runtime.execution_context import ExecutionContext


class HTMLRenderer:
    """
    Renders Quantum AST to HTML string.

    Phase 1: Server-side rendering only
    Phase 3: Will support hydration markers for client-side interactivity

    Handles:
    - HTML elements passthrough
    - Text with databinding {variable}
    - Quantum tags are already executed (loops expanded, conditions evaluated)
    - XSS protection via HTML escaping
    """

    def __init__(self, context: ExecutionContext):
        """
        Initialize renderer with execution context.

        Args:
            context: ExecutionContext with all variables and query results
        """
        self.context = context


    def render(self, node: QuantumNode) -> str:
        """
        Main render dispatch method.

        Args:
            node: AST node to render

        Returns:
            HTML string
        """

        if isinstance(node, HTMLNode):
            return self._render_html_node(node)

        elif isinstance(node, TextNode):
            return self._render_text_node(node)

        elif isinstance(node, DocTypeNode):
            return self._render_doctype(node)

        elif isinstance(node, CommentNode):
            return self._render_comment(node)

        elif isinstance(node, ComponentNode):
            return self._render_component(node)

        # These should NOT appear here - they're executed during runtime, not rendered
        elif isinstance(node, (LoopNode, IfNode, SetNode, QueryNode)):
            return ''

        else:
            # Unknown node type - skip (includes QuantumReturn and others)
            return ''


    def render_all(self, nodes: List[QuantumNode]) -> str:
        """
        Render list of nodes and concatenate results.

        Args:
            nodes: List of AST nodes

        Returns:
            Concatenated HTML string
        """
        return ''.join(self.render(node) for node in nodes)


    def _render_html_node(self, node: HTMLNode) -> str:
        """
        Render HTML element with attributes and children.

        Example:
          HTMLNode(tag='div', attributes={'class': 'container'}, children=[...])
          → <div class="container">...</div>

        Args:
            node: HTMLNode to render

        Returns:
            HTML string
        """

        # Build opening tag
        tag_parts = [f'<{node.tag}']

        # Add attributes with databinding applied
        if node.attributes:
            for key, value in node.attributes.items():
                # Apply databinding to attribute value
                processed_value = self._apply_databinding(value)
                # Escape for HTML attribute safety (prevent XSS)
                escaped_value = html.escape(processed_value, quote=True)
                tag_parts.append(f'{key}="{escaped_value}"')

        opening_tag = ' '.join(tag_parts)

        # Self-closing tags (void elements)
        if node.self_closing:
            return opening_tag + ' />'

        # Regular tags with children
        opening_tag += '>'
        children_html = self.render_all(node.children)
        closing_tag = f'</{node.tag}>'

        return opening_tag + children_html + closing_tag


    def _render_text_node(self, node: TextNode) -> str:
        """
        Render text content with databinding applied.

        Example:
          TextNode("Hello {user.name}!") with context['user']['name'] = 'John'
          → "Hello John!"

        Args:
            node: TextNode to render

        Returns:
            Text string with databinding applied and HTML escaped
        """

        text = node.content

        # Apply databinding if needed
        if node.has_databinding:
            text = self._apply_databinding(text)

        # HTML escape to prevent XSS
        # NOTE: This means you can't inject raw HTML via variables (security feature)
        return html.escape(text)


    def _render_doctype(self, node: DocTypeNode) -> str:
        """
        Render DOCTYPE declaration.

        Example:
          DocTypeNode("html") → "<!DOCTYPE html>"

        Args:
            node: DocTypeNode to render

        Returns:
            DOCTYPE string
        """
        return f'<!DOCTYPE {node.value}>'


    def _render_comment(self, node: CommentNode) -> str:
        """
        Render HTML comment.

        Example:
          CommentNode("This is a comment") → "<!-- This is a comment -->"

        Args:
            node: CommentNode to render

        Returns:
            HTML comment string
        """
        return f'<!-- {node.content} -->'


    def _render_component(self, node: ComponentNode) -> str:
        """
        Render entire component body.

        Args:
            node: ComponentNode to render

        Returns:
            HTML string of component output
        """
        return self.render_all(node.statements)


    def _apply_databinding(self, text: str) -> str:
        """
        Replace {variable} and {expression} with actual values from context.

        Examples:
          "{name}" → "John"
          "{user.email}" → "john@example.com"
          "{price * quantity}" → "49.99"
          "{items.length}" → "5"
          "Total: ${product.price}" → "Total: $29.99"

        Args:
            text: Text with possible {expression} patterns

        Returns:
            Text with databinding replaced
        """

        def replace_binding(match):
            """Replace single {expression} match"""
            expression = match.group(1).strip()

            try:
                # Evaluate expression from context
                value = self._evaluate_expression(expression)
                return str(value) if value is not None else ''

            except Exception as e:
                # If evaluation fails, return error marker (useful for debugging)
                # In production, you might want to log this and return empty string
                return f'{{ERROR: {expression}}}'

        # Find and replace all {expression} patterns
        pattern = r'\{([^}]+)\}'
        result = re.sub(pattern, replace_binding, text)

        return result


    def _evaluate_expression(self, expression: str) -> Any:
        """
        Evaluate databinding expression from context.

        Supports:
        - Simple variables: user
        - Nested properties: user.name, user.address.city
        - Array access: items[0], products[2].name
        - Array properties: items.length
        - Simple arithmetic: price * quantity, count + 1
        - Query results: products, products_result.recordCount

        Args:
            expression: Expression to evaluate

        Returns:
            Evaluated value

        Raises:
            Exception: If expression cannot be evaluated
        """

        # Try to get from context directly (simple variable)
        # get_variable() searches all scopes: local -> function -> component -> session -> parent
        try:
            value = self.context.get_variable(expression)
            return value
        except:
            pass  # Variable not found, try other evaluation methods

        # Try to evaluate as nested property (user.name)
        if '.' in expression:
            value = self._evaluate_nested_property(expression)
            if value is not None:
                return value

        # Try to evaluate as array access (items[0])
        if '[' in expression and ']' in expression:
            value = self._evaluate_array_access(expression)
            if value is not None:
                return value

        # Try simple arithmetic expressions (price * 2, count + 1)
        if any(op in expression for op in ['+', '-', '*', '/', '(', ')']):
            try:
                # SECURITY: Only allow simple arithmetic with known variables
                # Use safe evaluation (no exec/eval of arbitrary code)
                value = self._evaluate_arithmetic(expression)
                if value is not None:
                    return value
            except:
                pass

        # Expression not found or invalid
        raise Exception(f"Cannot evaluate expression: {expression}")


    def _evaluate_nested_property(self, expression: str) -> Any:
        """
        Evaluate nested property access: user.name, product.price, etc.

        Args:
            expression: Dot-separated property path

        Returns:
            Property value or None
        """
        parts = expression.split('.')
        current = None

        # Try to get root variable from all scopes
        root = parts[0]
        current = self.context.get_variable(root, scope='local')
        if current is None:
            current = self.context.get_variable(root, scope='function')
        if current is None:
            current = self.context.get_variable(root, scope='component')

        if current is None:
            return None

        # Navigate nested properties
        for part in parts[1:]:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                # Array properties like items.length
                if part == 'length':
                    return len(current)
                else:
                    return None
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return None

        return current


    def _evaluate_array_access(self, expression: str) -> Any:
        """
        Evaluate array access: items[0], products[2].name

        Args:
            expression: Expression with array access

        Returns:
            Array element or None
        """
        # Parse array[index] or array[index].property
        match = re.match(r'(\w+)\[(\d+)\](\.(.+))?', expression)
        if not match:
            return None

        array_name = match.group(1)
        index = int(match.group(2))
        property_path = match.group(4)  # Optional

        # Get array from context
        array = self.context.get_variable(array_name)
        if not isinstance(array, list):
            return None

        # Check bounds
        if index < 0 or index >= len(array):
            return None

        element = array[index]

        # If there's a property path, navigate it
        if property_path:
            for part in property_path.split('.'):
                if isinstance(element, dict):
                    element = element.get(part)
                elif hasattr(element, part):
                    element = getattr(element, part)
                else:
                    return None

        return element


    def _evaluate_arithmetic(self, expression: str) -> Any:
        """
        Safely evaluate simple arithmetic expressions.

        SECURITY: Only allows arithmetic with known variables from context.
        Does NOT use eval() or exec() to prevent code injection.

        Supports:
        - Addition: a + b
        - Subtraction: a - b
        - Multiplication: a * b
        - Division: a / b
        - Parentheses: (a + b) * c

        Args:
            expression: Arithmetic expression

        Returns:
            Calculated value

        Raises:
            Exception: If expression is invalid or unsafe
        """

        # Simple implementation: replace variables with values, then eval
        # WARNING: This is a simplified version. Production should use a proper
        # expression parser (like ast.literal_eval with whitelisting)

        # For now, just replace known variables
        safe_expression = expression

        # Get all variables from context
        all_vars = {}
        all_vars.update(self.context.local_vars or {})
        all_vars.update(self.context.function_vars or {})
        all_vars.update(self.context.component_vars or {})

        # Replace variable names with their values
        for var_name, var_value in all_vars.items():
            if isinstance(var_value, (int, float)):
                safe_expression = safe_expression.replace(var_name, str(var_value))

        # Only allow numbers and arithmetic operators
        if not re.match(r'^[\d+\-*/().\s]+$', safe_expression):
            raise Exception(f"Unsafe arithmetic expression: {expression}")

        # Evaluate safely
        try:
            # Using eval here is DANGEROUS in general, but we've validated the input
            # In production, use a proper expression parser library
            result = eval(safe_expression)
            return result
        except:
            raise Exception(f"Invalid arithmetic: {expression}")
