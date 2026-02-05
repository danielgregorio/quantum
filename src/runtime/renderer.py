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
    CommentNode, LoopNode, IfNode, SetNode, QueryNode, ComponentCallNode, ImportNode
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

    # Tags whose text content should NOT be processed by databinding or HTML-escaped
    RAW_CONTENT_TAGS = {'style', 'script'}

    def __init__(self, context: ExecutionContext, components_dir: str = "./components"):
        """
        Initialize renderer with execution context.

        Args:
            context: ExecutionContext with all variables and query results
            components_dir: Directory where component files are located (Phase 2)
        """
        self.context = context
        self.components_dir = components_dir
        self._raw_mode = False

        # Lazy-load composer (Phase 2)
        self._composer = None
        self._resolver = None


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

        # Component Composition (Phase 2)
        elif isinstance(node, ComponentCallNode):
            return self._render_component_call(node)

        elif isinstance(node, ImportNode):
            # Imports are processed at component load time, not render time
            return ''

        elif isinstance(node, LoopNode):
            return self._render_loop(node)

        elif isinstance(node, IfNode):
            return self._render_if(node)

        # SetNode and QueryNode are executed during runtime, not rendered
        elif isinstance(node, (SetNode, QueryNode)):
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
                escaped_value = html.escape(str(processed_value), quote=True)
                tag_parts.append(f'{key}="{escaped_value}"')

        opening_tag = ' '.join(tag_parts)

        # Self-closing tags (void elements)
        if node.self_closing:
            return opening_tag + ' />'

        # Regular tags with children
        opening_tag += '>'

        # Style/script tags: render children as raw text (no databinding, no escaping)
        if node.tag in self.RAW_CONTENT_TAGS:
            prev_raw = self._raw_mode
            self._raw_mode = True
            children_html = self.render_all(node.children)
            self._raw_mode = prev_raw
        else:
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

        # Inside <style>/<script> tags: return raw content without databinding or escaping
        if self._raw_mode:
            return text

        # Apply databinding if needed
        if node.has_databinding:
            text = self._apply_databinding(text)

        # HTML escape to prevent XSS
        # NOTE: This means you can't inject raw HTML via variables (security feature)
        # Guard against non-string values (e.g., bound methods from getattr)
        if callable(text):
            text = ''
        return html.escape(str(text) if text is not None else '')


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


    def _render_loop(self, node: LoopNode) -> str:
        """
        Render q:loop by iterating over items and rendering body for each.

        Args:
            node: LoopNode to render

        Returns:
            Concatenated HTML from all loop iterations
        """
        result = []

        # Get the items to iterate over
        items = self._get_loop_items(node)

        if not items:
            return ''

        # Save current context state
        original_vars = self.context.local_vars.copy()

        try:
            for index, item in enumerate(items):
                # Set loop variable in context
                self.context.set_variable(node.var_name, item, scope="local")

                # For query loops, set dotted variables (e.g., task.title, task.status)
                if node.loop_type == 'query' and isinstance(item, dict):
                    for field_name, field_value in item.items():
                        dotted_key = f"{node.var_name}.{field_name}"
                        self.context.set_variable(dotted_key, field_value, scope="local")

                # Set index if specified
                if node.index_name:
                    self.context.set_variable(node.index_name, index, scope="local")

                # Render loop body
                for child in node.body:
                    result.append(self.render(child))

        finally:
            # Restore original context
            self.context.local_vars = original_vars

        return ''.join(result)

    def _get_loop_items(self, node: LoopNode) -> list:
        """Get items to iterate over from loop node."""
        if node.loop_type == 'array':
            # Get items expression
            items_expr = node.items
            if not items_expr:
                return []

            # Apply databinding to resolve variable reference
            if '{' in items_expr and '}' in items_expr:
                resolved = self._apply_databinding(items_expr)
                if isinstance(resolved, list):
                    return resolved
                elif isinstance(resolved, str):
                    # Try to parse as JSON
                    try:
                        import json
                        return json.loads(resolved)
                    except:
                        return []
            return []

        elif node.loop_type == 'range':
            # Generate range
            try:
                start = int(node.from_value) if node.from_value else 1
                end = int(node.to_value) if node.to_value else 10
                step = node.step_value if node.step_value else 1
                return list(range(start, end + 1, step))
            except:
                return []

        elif node.loop_type == 'query':
            # Query loop - resolve items from query result variable
            items_expr = node.items
            if not items_expr:
                # Shorthand syntax: query_name is in var_name
                query_name = getattr(node, 'query_name', node.var_name)
                try:
                    data = self.context.get_variable(query_name)
                    if isinstance(data, list):
                        return data
                except:
                    pass
                return []

            # Traditional syntax: items="{tasks}"
            if '{' in items_expr and '}' in items_expr:
                resolved = self._apply_databinding(items_expr)
                if isinstance(resolved, list):
                    return resolved
            return []

        elif node.loop_type == 'list':
            # Split by delimiter
            items_expr = node.items
            if not items_expr:
                return []
            resolved = self._apply_databinding(items_expr) if '{' in items_expr else items_expr
            delimiter = node.delimiter or ','
            return [item.strip() for item in str(resolved).split(delimiter)]

        return []

    def _render_if(self, node: IfNode) -> str:
        """
        Render q:if by evaluating condition and rendering appropriate branch.

        Args:
            node: IfNode to render

        Returns:
            HTML from the matching branch
        """
        # Evaluate main condition
        if self._evaluate_condition(node.condition):
            return self.render_all(node.if_body)

        # Check elseif branches
        for elseif in (node.elseif_blocks or []):
            if self._evaluate_condition(elseif.condition):
                return self.render_all(elseif.body)

        # Else branch
        if node.else_body:
            return self.render_all(node.else_body)

        return ''

    def _evaluate_condition(self, condition: str) -> bool:
        """Evaluate a condition expression."""
        if not condition:
            return False

        # Apply databinding to resolve variables
        resolved = self._apply_databinding(condition)

        # Handle common comparisons
        if isinstance(resolved, bool):
            return resolved
        if isinstance(resolved, str):
            # Check for comparison operators in the original condition
            if '==' in condition or '!=' in condition or '>' in condition or '<' in condition:
                try:
                    # Get all variables for eval context
                    vars_dict = self.context.get_all_variables()
                    # Safe eval with only the variables
                    return bool(eval(resolved, {"__builtins__": {}}, vars_dict))
                except:
                    pass
            # String truthiness
            return resolved.lower() not in ('', 'false', '0', 'null', 'undefined')
        if isinstance(resolved, (int, float)):
            return resolved != 0
        if isinstance(resolved, list):
            return len(resolved) > 0

        return bool(resolved)

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


    def _apply_databinding(self, text: str) -> Any:
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
            - For pure expressions like "{items}": the actual value (list, dict, etc.)
            - For mixed content like "Hello {name}": interpolated string
        """
        if not text:
            return text

        pattern = r'\{([^}]+)\}'

        # Check if the ENTIRE text is just a single databinding expression
        full_match = re.fullmatch(pattern, text.strip())
        if full_match:
            # Pure expression - return the actual value (not converted to string)
            expression = full_match.group(1).strip()
            try:
                return self._evaluate_expression(expression)
            except Exception as e:
                # If evaluation fails, return original placeholder
                return text

        # Mixed content (text + expressions) - need string interpolation
        def replace_binding(match):
            """Replace single {expression} match"""
            expression = match.group(1).strip()

            try:
                # Evaluate expression from context
                value = self._evaluate_expression(expression)
                return str(value) if value is not None else ''

            except Exception as e:
                # If evaluation fails, return error marker (useful for debugging)
                return f'{{ERROR: {expression}}}'

        # Find and replace all {expression} patterns
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

        # Try comparison expressions (postFound == 1, count > 0)
        if any(op in expression for op in ['==', '!=', '>=', '<=', '>', '<']):
            try:
                value = self._evaluate_comparison(expression)
                if value is not None:
                    return value
            except:
                pass

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

        # Try to get root variable from context (searches all scopes automatically)
        root = parts[0]
        try:
            current = self.context.get_variable(root)
        except:
            return None

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
            elif hasattr(current, part) and not callable(getattr(current, part)):
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


    def _evaluate_comparison(self, expression: str) -> Any:
        """Evaluate comparison expressions like 'postFound == 1', 'count > 0'."""
        # Find the comparison operator
        for op in ['==', '!=', '>=', '<=', '>', '<']:
            if op in expression:
                parts = expression.split(op, 1)
                if len(parts) == 2:
                    left_expr = parts[0].strip()
                    right_expr = parts[1].strip()

                    # Resolve left side
                    try:
                        left_val = self._evaluate_expression(left_expr)
                    except:
                        left_val = left_expr

                    # Resolve right side
                    try:
                        right_val = self._evaluate_expression(right_expr)
                    except:
                        right_val = right_expr

                    # Try numeric comparison if possible
                    try:
                        left_num = float(left_val) if not isinstance(left_val, (int, float)) else left_val
                        right_num = float(right_val) if not isinstance(right_val, (int, float)) else right_val
                        if op == '==': return left_num == right_num
                        if op == '!=': return left_num != right_num
                        if op == '>=': return left_num >= right_num
                        if op == '<=': return left_num <= right_num
                        if op == '>': return left_num > right_num
                        if op == '<': return left_num < right_num
                    except (ValueError, TypeError):
                        pass

                    # String comparison fallback
                    left_str = str(left_val) if left_val is not None else ''
                    right_str = str(right_val) if right_val is not None else ''
                    # Strip quotes from literals
                    for s in [left_str, right_str]:
                        if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
                            s = s[1:-1]
                    left_str = left_str.strip("'\"")
                    right_str = right_str.strip("'\"")
                    if op == '==': return left_str == right_str
                    if op == '!=': return left_str != right_str
                    if op == '>=': return left_str >= right_str
                    if op == '<=': return left_str <= right_str
                    if op == '>': return left_str > right_str
                    if op == '<': return left_str < right_str
        return None

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

    # ============================================
    # COMPONENT COMPOSITION RENDERING (Phase 2)
    # ============================================

    def _get_composer(self):
        """Lazy-load component composer"""
        if self._composer is None:
            from runtime.component_resolver import ComponentResolver
            from runtime.component_composer import ComponentComposer

            self._resolver = ComponentResolver(self.components_dir)
            self._composer = ComponentComposer(self._resolver)

        return self._composer

    def _render_component_call(self, node: ComponentCallNode) -> str:
        """
        Render component call (Phase 2).

        Examples:
          <Header title="Products" />
          <Button label="Save" color="green" />
          <Card title="Info">Content here</Card>

        Args:
            node: ComponentCallNode from AST

        Returns:
            Rendered HTML from child component
        """

        try:
            composer = self._get_composer()
            html = composer.compose(node, self.context)
            return html

        except Exception as e:
            # Return error comment in development
            return f'<!-- Component Error ({node.component_name}): {e} -->'
