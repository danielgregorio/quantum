"""
Set Executor - Execute q:set statements

Handles variable assignment and all operations:
- assign, increment, decrement
- add, multiply (arithmetic)
- append, prepend, remove, clear, sort, etc. (array)
- merge, setProperty, deleteProperty, clone (object)
- uppercase, lowercase, trim, format (string)
"""

from typing import Any, List, Dict, Type
import json
from quantum.runtime.executors.base import BaseExecutor, ExecutorError
from quantum.core.features.state_management.src.ast_node import SetNode
from quantum.core.expressions import coerce_number


class SetExecutor(BaseExecutor):
    """
    Executor for q:set statements.

    Supports:
    - Basic assignment with type conversion
    - Increment/decrement operations
    - Array operations (append, remove, sort, etc.)
    - Object operations (merge, setProperty, etc.)
    - String transformations (uppercase, trim, etc.)
    - Validation rules
    """

    @property
    def handles(self) -> List[Type]:
        return [SetNode]

    def execute(self, node: SetNode, exec_context) -> Any:
        """
        Execute q:set statement.

        Args:
            node: SetNode to execute
            exec_context: Execution context

        Returns:
            None (set doesn't return a value)
        """
        try:
            context = exec_context.get_all_variables()

            # Handle different operations
            if node.operation == "assign":
                value = self._execute_assign(node, context)
            elif node.operation == "increment":
                value = self._execute_increment(node, exec_context, node.step)
            elif node.operation == "decrement":
                value = self._execute_decrement(node, exec_context, node.step)
            elif node.operation in ["add", "multiply"]:
                value = self._execute_arithmetic(node, exec_context, context)
            elif node.operation in ["append", "prepend", "remove", "removeAt", "clear", "sort", "reverse", "unique"]:
                value = self._execute_array_operation(node, exec_context)
            elif node.operation in ["merge", "setProperty", "deleteProperty", "clone"]:
                value = self._execute_object_operation(node, exec_context, context)
            elif node.operation in ["uppercase", "lowercase", "trim", "format"]:
                value = self._execute_transformation(node, exec_context)
            else:
                raise ExecutorError(f"Unsupported operation: {node.operation}")

            # Validate the value
            self._validate_value(node, value)

            # Set the variable in the appropriate scope
            self._set_variable(node, value, exec_context)

            return None  # q:set doesn't return a value

        except Exception as e:
            raise ExecutorError(f"Set execution error for '{node.name}': {e}")

    def _execute_assign(self, node: SetNode, context: Dict[str, Any]) -> Any:
        """Execute assign operation"""
        value_expr = node.value if node.value is not None else node.default

        if value_expr is None:
            if not node.nullable:
                raise ExecutorError(f"Variable '{node.name}' cannot be null")
            return None

        # Process databinding
        processed_value = self.apply_databinding(value_expr, context)

        # Convert to appropriate type
        return self._convert_to_type(processed_value, node.type)

    def _numeric_or_fail(self, value: Any, op: str, where: str) -> Any:
        """Coerce a numeric-looking value, or fail loudly.

        A .q attribute is a string by nature — `<q:set name="estoque"
        value="7" />` stores "7" unless the author remembered type="number".
        Refusing to add to that made increment/decrement unusable in the
        ordinary case, so it is coerced, the same way {a + b} coerces.
        """
        coerced = coerce_number(value)
        if isinstance(coerced, bool) or not isinstance(coerced, (int, float)):
            raise ExecutorError(
                f"Cannot {op} non-numeric value {value!r} ({where}). "
                f"Set it with type=\"number\", or give q:set a numeric value."
            )
        return coerced

    def _current_numeric(self, node: SetNode, exec_context, op: str):
        """(value, exists) for the variable being incremented/decremented.

        The previous version wrapped BOTH the lookup and the type check in one
        `try: ... except Exception: return step`, so the ExecutorError it
        raised for a non-numeric value was caught by its own handler one line
        later and turned into the step itself. A stock of "7" decremented by 5
        became -5 — the detection was correct and then discarded. Missing and
        non-numeric are separated here so only the first one falls back.
        """
        try:
            current = exec_context.get_variable(node.name)
        except Exception:
            return None, False
        if current is None or current == '':
            return None, False
        return self._numeric_or_fail(current, op, f"current value of {node.name!r}"), True

    def _execute_increment(self, node: SetNode, exec_context, step: int) -> Any:
        """Execute increment operation"""
        if node.value:
            context = exec_context.get_all_variables()
            base_value = self.apply_databinding(node.value, context)
            return self._numeric_or_fail(base_value, 'increment', 'value=') + step

        current, exists = self._current_numeric(node, exec_context, 'increment')
        return (current + step) if exists else step

    def _execute_decrement(self, node: SetNode, exec_context, step: int) -> Any:
        """Execute decrement operation"""
        if node.value:
            context = exec_context.get_all_variables()
            base_value = self.apply_databinding(node.value, context)
            return self._numeric_or_fail(base_value, 'decrement', 'value=') - step

        current, exists = self._current_numeric(node, exec_context, 'decrement')
        return (current - step) if exists else -step

    def _execute_arithmetic(self, node: SetNode, exec_context, context: Dict[str, Any]) -> Any:
        """Execute arithmetic operations (add, multiply)"""
        try:
            current_value = exec_context.get_variable(node.name)
        except Exception:
            current_value = 0
        if current_value is None or current_value == '':
            current_value = 0

        # Same coercion as increment/decrement: a .q attribute is a string by
        # nature, so add/multiply on a variable set without type="number" used
        # to fail even though the value was plainly numeric.
        current_value = self._numeric_or_fail(
            current_value, node.operation, f"current value of {node.name!r}"
        )

        operand_expr = node.value
        if not operand_expr:
            raise ExecutorError("Arithmetic operation requires a value")

        fresh_context = exec_context.get_all_variables()
        processed = self.apply_databinding(operand_expr, fresh_context)
        operand = self._convert_to_type(processed, "number")

        if node.operation == "add":
            return current_value + operand
        elif node.operation == "multiply":
            return current_value * operand

        return current_value

    def _execute_array_operation(self, node: SetNode, exec_context) -> Any:
        """Execute array operations"""
        try:
            current_value = exec_context.get_variable(node.name)
        except Exception:
            current_value = []

        if not isinstance(current_value, list):
            raise ExecutorError(f"Cannot perform array operation on non-array: {type(current_value)}")

        result = current_value.copy()

        # Resolve databinding in value
        resolved_value = node.value
        if resolved_value and node.operation in ("append", "prepend", "remove"):
            context = exec_context.get_all_variables()
            resolved = self.apply_databinding(resolved_value, context)
            if resolved is not None:
                resolved_value = resolved

        if node.operation == "append":
            if resolved_value:
                result.append(resolved_value)
        elif node.operation == "prepend":
            if resolved_value:
                result.insert(0, resolved_value)
        elif node.operation == "remove":
            if resolved_value and resolved_value in result:
                result.remove(resolved_value)
        elif node.operation == "removeAt":
            if node.index is not None:
                idx = int(node.index)
                if 0 <= idx < len(result):
                    result.pop(idx)
        elif node.operation == "clear":
            result = []
        elif node.operation == "sort":
            result.sort()
        elif node.operation == "reverse":
            result.reverse()
        elif node.operation == "unique":
            result = list(dict.fromkeys(result))

        return result

    def _execute_object_operation(self, node: SetNode, exec_context, context: Dict[str, Any]) -> Any:
        """Execute object operations"""
        try:
            current_value = exec_context.get_variable(node.name)
        except Exception:
            current_value = {}

        if not isinstance(current_value, dict):
            raise ExecutorError(f"Cannot perform object operation on non-object: {type(current_value)}")

        result = current_value.copy()

        if node.operation == "merge":
            if node.value:
                try:
                    merge_data = json.loads(node.value)
                    result.update(merge_data)
                except json.JSONDecodeError:
                    raise ExecutorError(f"Invalid JSON for merge: {node.value}")
        elif node.operation == "setProperty":
            if node.key and node.value:
                result[node.key] = node.value
        elif node.operation == "deleteProperty":
            if node.key and node.key in result:
                del result[node.key]
        elif node.operation == "clone":
            if node.source:
                try:
                    source_obj = exec_context.get_variable(node.source)
                    if isinstance(source_obj, dict):
                        result = source_obj.copy()
                except Exception:
                    pass

        return result

    def _execute_transformation(self, node: SetNode, exec_context) -> Any:
        """Execute string transformation operations"""
        if node.value:
            context = exec_context.get_all_variables()
            processed_value = self.apply_databinding(node.value, context)
            value_str = str(processed_value)
        else:
            try:
                current_value = exec_context.get_variable(node.name)
                value_str = str(current_value)
            except Exception:
                value_str = ""

        if node.operation == "uppercase":
            return value_str.upper()
        elif node.operation == "lowercase":
            return value_str.lower()
        elif node.operation == "trim":
            return value_str.strip()
        elif node.operation == "format":
            return value_str

        return value_str

    def _convert_to_type(self, value: Any, target_type: str) -> Any:
        """Convert value to target type"""
        if value is None:
            return None

        try:
            if target_type == "string":
                return str(value)
            elif target_type in ("integer", "number"):
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return float(value)
            elif target_type == "decimal":
                return float(value)
            elif target_type == "boolean":
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.lower() in ['true', '1', 'yes']
                return bool(value)
            elif target_type == "array":
                if isinstance(value, list):
                    return value
                if isinstance(value, str):
                    return json.loads(value)
                return [value]
            elif target_type == "object":
                if isinstance(value, dict):
                    return value
                if isinstance(value, str):
                    return json.loads(value)
                return {}
            elif target_type == "json":
                if isinstance(value, (dict, list)):
                    return value
                if isinstance(value, str):
                    return json.loads(value)
                return value
            else:
                return value
        except Exception as e:
            raise ExecutorError(f"Type conversion error to '{target_type}': {e}")

    def _validate_value(self, node: SetNode, value: Any):
        """Validate value against set_node rules"""
        # Import validators lazily to avoid circular imports
        from quantum.runtime.validators import QuantumValidators, ValidationError

        # Check required
        if node.required:
            is_valid, error = QuantumValidators.validate_required(value)
            if not is_valid:
                raise ExecutorError(error)

        # Check nullable
        if not node.nullable and value is None:
            raise ExecutorError(f"Variable '{node.name}' cannot be null")

        # Skip other validations if null and nullable
        if value is None and node.nullable:
            return

        # Check validate_rule
        if node.validate_rule:
            if node.validate_rule == 'cpf':
                is_valid, error = QuantumValidators.validate_cpf(str(value))
            elif node.validate_rule == 'cnpj':
                is_valid, error = QuantumValidators.validate_cnpj(str(value))
            else:
                is_valid, error = QuantumValidators.validate(value, node.validate_rule)

            if not is_valid:
                raise ExecutorError(error)

        # Check pattern
        if node.pattern and not node.validate_rule:
            is_valid, error = QuantumValidators.validate(value, node.pattern)
            if not is_valid:
                raise ExecutorError(error)

        # Check range
        if node.range:
            is_valid, error = QuantumValidators.validate_range(value, node.range)
            if not is_valid:
                raise ExecutorError(error)

        # Check enum
        if node.enum:
            is_valid, error = QuantumValidators.validate_enum(value, node.enum)
            if not is_valid:
                raise ExecutorError(error)

        # Check min/max
        if node.min or node.max:
            is_valid, error = QuantumValidators.validate_min_max(
                value, min_val=node.min, max_val=node.max
            )
            if not is_valid:
                raise ExecutorError(error)

        # Check minlength/maxlength
        if node.type == "string" and (node.minlength or node.maxlength):
            minlen = int(node.minlength) if node.minlength else None
            maxlen = int(node.maxlength) if node.maxlength else None

            is_valid, error = QuantumValidators.validate_length(
                value, minlength=minlen, maxlength=maxlen
            )
            if not is_valid:
                raise ExecutorError(error)

    def _set_variable(self, node: SetNode, value: Any, exec_context):
        """Set variable in the appropriate scope"""
        is_update_operation = node.operation in [
            "increment", "decrement", "add", "multiply",
            "append", "prepend", "remove", "removeAt",
            "clear", "sort", "reverse", "unique",
            "merge", "setProperty", "deleteProperty",
            "uppercase", "lowercase", "trim", "format"
        ]

        if is_update_operation or (exec_context.has_variable(node.name) and node.scope == "local"):
            exec_context.update_variable(node.name, value)
        else:
            actual_scope = node.scope
            if node.scope == "local" and exec_context.parent is not None:
                actual_scope = "function"
            exec_context.set_variable(node.name, value, scope=actual_scope)
