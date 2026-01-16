"""
Databinding Engine - Resolve {variable} expressions

Supports:
- Simple variables: {name}
- Object properties: {user.name}
- Array access: {items[0]}
- Operations: {price * quantity}
- Function calls: {calculateTotal(100, 2)}
"""

import re
from typing import Any, Dict, Optional
import operator


class DatabindingEngine:
    """Resolves databinding expressions in templates"""

    def __init__(self):
        # Supported operators
        self.operators = {
            '+': operator.add,
            '-': operator.sub,
            '*': operator.mul,
            '/': operator.truediv,
            '%': operator.mod,
            '==': operator.eq,
            '!=': operator.ne,
            '>': operator.gt,
            '>=': operator.ge,
            '<': operator.lt,
            '<=': operator.le,
            'and': operator.and_,
            'or': operator.or_,
        }

    def resolve(self, template: str, context: Dict[str, Any]) -> str:
        """
        Resolve all {variable} expressions in template

        Args:
            template: String with {expressions}
            context: Variables dictionary

        Returns:
            Resolved string
        """
        if not template:
            return ""

        # Find all {expression} patterns
        pattern = r'\{([^}]+)\}'

        def replace_expression(match):
            expression = match.group(1).strip()
            try:
                result = self.evaluate_expression(expression, context)
                return str(result) if result is not None else ""
            except Exception as e:
                # In production, might want to log this
                return f"{{ERROR: {e}}}"

        return re.sub(pattern, replace_expression, template)

    def evaluate_expression(self, expression: str, context: Dict[str, Any]) -> Any:
        """
        Evaluate a single expression

        Examples:
            name -> context['name']
            user.email -> context['user']['email']
            items[0] -> context['items'][0]
            price * quantity -> context['price'] * context['quantity']
        """
        expression = expression.strip()

        # Handle simple variable
        if self._is_simple_variable(expression):
            return self._resolve_variable(expression, context)

        # Handle operations (e.g., "price * quantity")
        if any(op in expression for op in self.operators.keys()):
            return self._evaluate_operation(expression, context)

        # Handle function calls (e.g., "calculateTotal(100, 2)")
        if '(' in expression and expression.endswith(')'):
            return self._evaluate_function_call(expression, context)

        # Fallback: try to evaluate as variable
        return self._resolve_variable(expression, context)

    def _is_simple_variable(self, expr: str) -> bool:
        """Check if expression is a simple variable (no operators)"""
        for op in self.operators.keys():
            if op in expr:
                return False
        return True

    def _resolve_variable(self, var_path: str, context: Dict[str, Any]) -> Any:
        """
        Resolve variable path like 'user.name' or 'items[0]'

        Args:
            var_path: Variable path (e.g., "user.email", "items[0]")
            context: Context dictionary

        Returns:
            Resolved value
        """
        # Handle array access: items[0]
        if '[' in var_path and ']' in var_path:
            # Extract array name and index
            match = re.match(r'(\w+)\[(\d+)\]', var_path)
            if match:
                array_name = match.group(1)
                index = int(match.group(2))
                if array_name in context:
                    array = context[array_name]
                    if isinstance(array, (list, tuple)) and 0 <= index < len(array):
                        return array[index]
            return None

        # Handle object property access: user.name
        if '.' in var_path:
            parts = var_path.split('.')
            value = context.get(parts[0])

            for part in parts[1:]:
                if value is None:
                    return None

                # Try dictionary access
                if isinstance(value, dict):
                    value = value.get(part)
                # Try object attribute
                elif hasattr(value, part):
                    value = getattr(value, part)
                else:
                    return None

            return value

        # Simple variable
        return context.get(var_path)

    def _evaluate_operation(self, expression: str, context: Dict[str, Any]) -> Any:
        """
        Evaluate operation like "price * quantity" or "x + y"

        Supports: +, -, *, /, %, ==, !=, >, >=, <, <=, and, or
        """
        # Try each operator (longest first to handle >= before >)
        for op_str in sorted(self.operators.keys(), key=len, reverse=True):
            if op_str in expression:
                parts = expression.split(op_str, 1)
                if len(parts) == 2:
                    left = self.evaluate_expression(parts[0].strip(), context)
                    right = self.evaluate_expression(parts[1].strip(), context)

                    # Convert to numbers if needed
                    left = self._to_number(left)
                    right = self._to_number(right)

                    op_func = self.operators[op_str]
                    return op_func(left, right)

        # No operator found, return as is
        return expression

    def _evaluate_function_call(self, expression: str, context: Dict[str, Any]) -> Any:
        """
        Evaluate function call like "calculateTotal(100, 2)"

        Note: This is a simplified version. Full implementation would
        integrate with FunctionRuntime.
        """
        # Extract function name and arguments
        match = re.match(r'(\w+)\((.*)\)', expression)
        if not match:
            return expression

        func_name = match.group(1)
        args_str = match.group(2)

        # Parse arguments
        args = []
        if args_str.strip():
            for arg in args_str.split(','):
                arg = arg.strip()
                # Evaluate each argument
                arg_value = self.evaluate_expression(arg, context)
                args.append(arg_value)

        # Check if function exists in context
        if func_name in context:
            func = context[func_name]
            if callable(func):
                return func(*args)

        # Function not found
        return f"{{FUNCTION_NOT_FOUND: {func_name}}}"

    def _to_number(self, value: Any) -> Any:
        """Convert value to number if it's a numeric string"""
        if isinstance(value, str):
            try:
                # Try int first
                if '.' not in value:
                    return int(value)
                # Then float
                return float(value)
            except ValueError:
                return value
        return value

    def resolve_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """
        Resolve boolean condition for q:if

        Examples:
            age >= 18
            name == "Alice"
            items.length > 0
        """
        result = self.evaluate_expression(condition, context)

        # Convert to boolean
        if isinstance(result, bool):
            return result
        if isinstance(result, (int, float)):
            return result != 0
        if isinstance(result, str):
            return len(result) > 0
        if isinstance(result, (list, dict)):
            return len(result) > 0

        return bool(result)


# Global instance
_databinding_engine = DatabindingEngine()


def resolve(template: str, context: Dict[str, Any]) -> str:
    """Resolve databinding expressions in template"""
    return _databinding_engine.resolve(template, context)


def evaluate(expression: str, context: Dict[str, Any]) -> Any:
    """Evaluate single expression"""
    return _databinding_engine.evaluate_expression(expression, context)


def resolve_condition(condition: str, context: Dict[str, Any]) -> bool:
    """Resolve boolean condition"""
    return _databinding_engine.resolve_condition(condition, context)
