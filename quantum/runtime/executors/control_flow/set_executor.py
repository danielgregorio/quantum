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
import re
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

        # SET-1: default= is what to store when value= resolves to nothing.
        # It was only read when value= was ABSENT from the tag, so
        # <q:set name="clicks" value="{session.click_count}" default="0"/>
        # stored '' on the first visit and the next {clicks + 1} failed.
        if (processed_value is None or processed_value == '') and node.value is not None \
                and node.default is not None:
            processed_value = self.apply_databinding(node.default, context)

        # Convert to appropriate type
        return self._convert_to_type(processed_value, node.type, source=value_expr)

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

    def _convert_to_type(self, value: Any, target_type: str, source: str = None) -> Any:
        """Convert value to target type.

        ERR-1: a value that does not convert is an error that shows the value
        and how to write it. The messages used to be Python's own — "could not
        convert string to float: '10 + 20'" for value="{a} + {b}", and
        "Expecting property name enclosed in double quotes" for an array
        written with single quotes — neither of which says what to change.
        """
        if value is None:
            return None

        if target_type in ("integer", "number", "decimal"):
            if isinstance(value, bool):
                raise ExecutorError(f"{value!r} is a boolean, not a number")
            numero = coerce_number(value)
            if not isinstance(numero, (int, float)):
                raise ExecutorError(self._not_a_number(value, source))
            if target_type == "decimal":
                return float(numero)
            if target_type == "integer":
                # It used to be int(value): {7 / 2} became 3, silently.
                if isinstance(numero, float):
                    if not numero.is_integer():
                        raise ExecutorError(
                            f"{numero!r} is not a whole number; use round() in the "
                            f"expression, or type=\"number\"")
                    return int(numero)
                return numero
            # type="number" also went through int() first: {5 / 2} stored 2.
            return numero

        if target_type == "boolean":
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                texto = value.strip().lower()
                if texto in ('true', '1', 'yes'):
                    return True
                if texto in ('false', '0', 'no', ''):
                    return False
                raise ExecutorError(
                    f"{value!r} is not a boolean; use true or false")
            return bool(value)

        if target_type in ("array", "object", "json"):
            vazio = {"array": [value], "object": {}, "json": value}[target_type]
            if isinstance(value, (dict, list)):
                if target_type == "array" and not isinstance(value, list):
                    raise ExecutorError(f"expected an array, got an object")
                if target_type == "object" and not isinstance(value, dict):
                    raise ExecutorError(f"expected an object, got an array")
                return value
            if not isinstance(value, str):
                return vazio
            try:
                return json.loads(value)
            except json.JSONDecodeError as exc:
                raise ExecutorError(self._not_json(value, target_type, exc)) from None

        if target_type == "string":
            return str(value)
        return value

    @staticmethod
    def _not_a_number(value: Any, source: str) -> str:
        mensagem = f"{value!r} is not a number"
        # value="{a} + {b}": each pair of braces is evaluated alone and the
        # text between them is kept, so the result is the text '10 + 20'.
        if source and '{' in source and not re.fullmatch(r'\s*\{[^{}]*\}\s*', source):
            junto = '{' + re.sub(r'\{([^{}]*)\}', r'\1', source).strip() + '}'
            mensagem += (f". Only what is inside one pair of braces is calculated: "
                         f"write value=\"{junto}\" instead of value=\"{source}\"")
        return mensagem

    @staticmethod
    def _not_json(value: str, target_type: str, exc: json.JSONDecodeError) -> str:
        trecho = value.strip()
        if len(trecho) > 60:
            trecho = trecho[:57] + '...'
        mensagem = (f"value is not a valid {target_type} (JSON): {trecho!r}, "
                    f"problem at character {exc.pos + 1}")
        if "'" in value:
            mensagem += ('. JSON uses double quotes for text and keys: '
                         'value=\'[{"name": "Ana"}]\' — put the attribute itself in single quotes')
        return mensagem

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
