"""
Quantum Component Runtime - Execute Quantum components
"""

import sys
from pathlib import Path
from typing import Any, Dict, List

# Fix imports
sys.path.append(str(Path(__file__).parent.parent))

from core.ast_nodes import ComponentNode, QuantumReturn, IfNode, LoopNode, SetNode, FunctionNode, DispatchEventNode, OnEventNode
from runtime.execution_context import ExecutionContext, VariableNotFoundError
from runtime.validators import QuantumValidators, ValidationError
from runtime.function_registry import FunctionRegistry
import re

class ComponentExecutionError(Exception):
    """Error in component execution"""
    pass

class ComponentRuntime:
    """Runtime for executing Quantum components"""

    def __init__(self):
        self.execution_context = ExecutionContext()
        # Keep self.context for backward compatibility
        self.context: Dict[str, Any] = {}
        # Function registry
        self.function_registry = FunctionRegistry()
        # Current component (for function resolution)
        self.current_component: ComponentNode = None
    
    def execute_component(self, component: ComponentNode, params: Dict[str, Any] = None) -> Any:
        """Execute a component and return the result"""
        if params is None:
            params = {}

        # Set current component
        self.current_component = component

        # Register component functions
        self.function_registry.register_component(component)

        # Validate parameters
        validation_errors = self._validate_params(component, params)
        if validation_errors:
            raise ComponentExecutionError(f"Validation errors: {validation_errors}")

        # Setup context - add params to both contexts
        self.context.update(params)
        for key, value in params.items():
            self.execution_context.set_variable(key, value, scope="component")

        # Execute component
        try:
            # Execute control flow statements first
            for statement in component.statements:
                result = self._execute_statement(statement, self.execution_context)
                # Only return if the statement explicitly returns a value (not just executing)
                # SetNode returns None, LoopNode returns a list but shouldn't cause early return
                if result is not None and isinstance(statement, (IfNode,)):
                    # Only IfNode with a return statement should cause early return
                    return result

            # For now, simple execution based on q:return
            if component.returns:
                first_return = component.returns[0]
                # Use get_all_variables() for backward compatibility
                return self._process_return_value(first_return.value, self.execution_context.get_all_variables())

            return None

        except Exception as e:
            raise ComponentExecutionError(f"Execution error: {e}")
    
    def _validate_params(self, component: ComponentNode, params: Dict[str, Any]) -> List[str]:
        """Validate component parameters"""
        errors = []
        
        for param_def in component.params:
            if param_def.required and param_def.name not in params:
                errors.append(f"Required parameter '{param_def.name}' is missing")
        
        return errors
    
    def _process_return_value(self, value: str, context: Dict[str, Any] = None) -> Any:
        """Process return value with databinding support"""
        if not value:
            return ""

        if context is None:
            context = {}

        # Apply databinding first
        processed_value = self._apply_databinding(value, context)

        # If databinding returned a non-string (e.g., int, float, dict), return it as-is
        if not isinstance(processed_value, str):
            return processed_value

        # Remove quotes if it's a string literal (after databinding)
        if processed_value.startswith('"') and processed_value.endswith('"'):
            return processed_value[1:-1]
        if processed_value.startswith("'") and processed_value.endswith("'"):
            return processed_value[1:-1]
        
        # Try to parse JSON
        if processed_value.startswith('{') or processed_value.startswith('['):
            try:
                import json
                return json.loads(processed_value)
            except:
                pass
        
        return processed_value
    
    def _execute_statement(self, statement, context):
        """Execute a control flow statement"""
        # Accept both ExecutionContext and Dict for backward compatibility
        if isinstance(context, ExecutionContext):
            exec_context = context
            dict_context = context.get_all_variables()
        else:
            exec_context = self.execution_context
            dict_context = context

        if isinstance(statement, IfNode):
            return self._execute_if(statement, dict_context)
        elif isinstance(statement, LoopNode):
            return self._execute_loop(statement, dict_context)
        elif isinstance(statement, SetNode):
            return self._execute_set(statement, exec_context)
        return None
    
    def _execute_if(self, if_node: IfNode, context: Dict[str, Any]):
        """Execute q:if statement with elseif and else"""
        
        # Evaluate main if condition
        if self._evaluate_condition(if_node.condition, context):
            return self._execute_body(if_node.if_body, context)
        
        # Check elseif conditions
        for elseif_block in if_node.elseif_blocks:
            if self._evaluate_condition(elseif_block["condition"], context):
                return self._execute_body(elseif_block["body"], context)
        
        # Execute else block if present
        if if_node.else_body:
            return self._execute_body(if_node.else_body, context)
        
        return None
    
    def _execute_body(self, statements: List, context: Dict[str, Any]):
        """Execute a list of statements"""
        for statement in statements:
            if isinstance(statement, QuantumReturn):
                return self._process_return_value(statement.value, context)
            # TODO: Handle other statement types
        return None
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate a condition string - BASIC implementation for now"""
        if not condition:
            return False
        
        # Very basic evaluation - just check for simple comparisons
        # TODO: Implement proper expression evaluation
        
        # For now, support simple cases like "user.age >= 18"
        try:
            # Replace context variables (very basic)
            evaluated_condition = condition
            for key, value in context.items():
                if isinstance(value, dict):
                    for subkey, subvalue in value.items():
                        placeholder = f"{key}.{subkey}"
                        if placeholder in evaluated_condition:
                            evaluated_condition = evaluated_condition.replace(placeholder, str(subvalue))
                else:
                    if key in evaluated_condition:
                        evaluated_condition = evaluated_condition.replace(key, str(value))
            
            # Basic evaluation
            return eval(evaluated_condition)
        except:
            # Fallback - just return False for now
            return False
    
    def _execute_loop(self, loop_node: LoopNode, context: Dict[str, Any]):
        """Execute q:loop statement with various types"""
        if loop_node.loop_type == 'range':
            return self._execute_range_loop(loop_node, context)
        elif loop_node.loop_type == 'array':
            return self._execute_array_loop(loop_node, context)
        elif loop_node.loop_type == 'list':
            return self._execute_list_loop(loop_node, context)
        else:
            raise ComponentExecutionError(f"Unsupported loop type: {loop_node.loop_type}")
    
    def _execute_range_loop(self, loop_node: LoopNode, context: Dict[str, Any]):
        """Execute range loop (from/to/step)"""
        results = []
        
        try:
            # Evaluate from and to values
            start = int(self._evaluate_simple_expression(loop_node.from_value, context))
            end = int(self._evaluate_simple_expression(loop_node.to_value, context))
            step = loop_node.step_value
            
            # Execute loop
            for i in range(start, end + 1, step):
                # Create loop context with loop variable
                loop_context = context.copy()
                loop_context[loop_node.var_name] = i

                # Also update execution context for q:set support
                self.execution_context.set_variable(loop_node.var_name, i, scope="local")

                # Execute loop body
                for statement in loop_node.body:
                    result = self._execute_loop_body_statement(statement, loop_context)
                    if result is not None:
                        results.append(result)
            
            return results
            
        except (ValueError, TypeError) as e:
            raise ComponentExecutionError(f"Range loop error: {e}")
    
    def _execute_array_loop(self, loop_node: LoopNode, context: Dict[str, Any]):
        """Execute array loop"""
        results = []
        
        try:
            # Get array data (for now, parse simple array notation)
            array_data = self._parse_array_items(loop_node.items, context)
            
            # Execute loop
            for index, item in enumerate(array_data):
                # Create loop context with loop variable(s)
                loop_context = context.copy()
                loop_context[loop_node.var_name] = item
                
                # Add index if specified
                if loop_node.index_name:
                    loop_context[loop_node.index_name] = index
                
                # Execute loop body
                for statement in loop_node.body:
                    result = self._execute_loop_body_statement(statement, loop_context)
                    if result is not None:
                        results.append(result)
            
            return results
            
        except Exception as e:
            raise ComponentExecutionError(f"Array loop error: {e}")
    
    def _execute_list_loop(self, loop_node: LoopNode, context: Dict[str, Any]):
        """Execute list loop"""
        results = []
        
        try:
            # Get list data and split by delimiter
            list_data = self._parse_list_items(loop_node.items, loop_node.delimiter, context)
            
            # Execute loop
            for index, item in enumerate(list_data):
                # Create loop context with loop variable(s)
                loop_context = context.copy()
                loop_context[loop_node.var_name] = item.strip()
                
                # Add index if specified
                if loop_node.index_name:
                    loop_context[loop_node.index_name] = index
                
                # Execute loop body
                for statement in loop_node.body:
                    result = self._execute_loop_body_statement(statement, loop_context)
                    if result is not None:
                        results.append(result)
            
            return results
            
        except Exception as e:
            raise ComponentExecutionError(f"List loop error: {e}")
    
    def _execute_loop_body_statement(self, statement, context: Dict[str, Any]):
        """Execute a statement inside a loop body"""
        if isinstance(statement, QuantumReturn):
            return self._process_return_value(statement.value, context)
        elif isinstance(statement, IfNode):
            return self._execute_if(statement, context)
        elif isinstance(statement, LoopNode):
            return self._execute_loop(statement, context)
        elif isinstance(statement, SetNode):
            # Execute set using the execution context
            return self._execute_set(statement, self.execution_context)
        return None
    
    def _evaluate_simple_expression(self, expr: str, context: Dict[str, Any]) -> Any:
        """Basic expression evaluation for simple values"""
        if not expr:
            return 0
        
        # For now, just handle simple numeric values
        # TODO: Expand to handle variables and complex expressions
        try:
            return int(expr)
        except ValueError:
            try:
                return float(expr)
            except ValueError:
                # Try to get from context
                return context.get(expr, expr)
    
    def _parse_array_items(self, items_expr: str, context: Dict[str, Any]) -> list:
        """Parse array items from expression"""
        if not items_expr:
            return []
        
        # Handle simple array notation: ["item1", "item2", "item3"]
        if items_expr.startswith('[') and items_expr.endswith(']'):
            try:
                import json
                return json.loads(items_expr)
            except json.JSONDecodeError:
                # Fallback to simple parsing
                items_str = items_expr[1:-1]  # Remove brackets
                return [item.strip().strip('"\'') for item in items_str.split(',') if item.strip()]
        
        # Handle variable reference from context
        if items_expr in context:
            return context[items_expr]
        
        # Default: treat as single item
        return [items_expr]
    
    def _parse_list_items(self, items_expr: str, delimiter: str, context: Dict[str, Any]) -> list:
        """Parse list items from delimited string"""
        if not items_expr:
            return []
        
        # Handle variable reference from context
        if items_expr in context:
            items_value = context[items_expr]
            if isinstance(items_value, list):
                return items_value
            elif isinstance(items_value, str):
                return items_value.split(delimiter)
        
        # Handle direct string list
        return items_expr.split(delimiter)
    
    def _apply_databinding(self, text: str, context: Dict[str, Any]) -> Any:
        """Apply variable databinding to text using {variable} syntax"""
        import re

        if not text:
            return text

        # Even if context is empty, we still need to process function calls
        if context is None:
            context = {}

        # Pattern to match {variable} or {variable.property}
        pattern = r'\{([^}]+)\}'

        # Check if the ENTIRE text is just a single databinding expression
        full_match = re.fullmatch(pattern, text.strip())
        if full_match:
            # Pure expression - return the actual value (not converted to string)
            var_expr = full_match.group(1).strip()
            try:
                return self._evaluate_databinding_expression(var_expr, context)
            except Exception as e:
                # If evaluation fails, return original placeholder
                return text

        # Mixed content (text + expressions) - need string interpolation
        def replace_variable(match):
            var_expr = match.group(1).strip()
            try:
                result = self._evaluate_databinding_expression(var_expr, context)
                return str(result)
            except Exception as e:
                # If evaluation fails, return original placeholder
                return match.group(0)

        # Replace all {variable} patterns
        result = re.sub(pattern, replace_variable, text)
        return result
    
    def _evaluate_databinding_expression(self, expr: str, context: Dict[str, Any]) -> Any:
        """Evaluate a databinding expression like 'variable' or 'user.name' or 'functionName(args)' or 'count + 1'"""

        # Handle function calls first (e.g., add(5, 3))
        # Check if it looks like a function call: word followed by (
        if '(' in expr and ')' in expr and re.match(r'^\s*\w+\s*\(', expr):
            return self._evaluate_function_call(expr, context)

        # Handle simple variable access
        if expr in context:
            return context[expr]

        # Handle dot notation (user.name)
        if '.' in expr and '(' not in expr:
            parts = expr.split('.')
            value = context
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    raise ValueError(f"Property '{part}' not found")
            return value

        # Handle simple arithmetic expressions (count + 1, i * 2, etc.)
        if any(op in expr for op in ['+', '-', '*', '/', '(', ')']):
            return self._evaluate_arithmetic_expression(expr, context)

        # If not found, raise error
        raise ValueError(f"Variable '{expr}' not found in context")
    
    def _evaluate_arithmetic_expression(self, expr: str, context: Dict[str, Any]) -> Any:
        """Evaluate arithmetic expressions with variables"""
        # Replace variables in expression with their values
        for var_name, var_value in context.items():
            if var_name in expr and isinstance(var_value, (int, float)):
                expr = expr.replace(var_name, str(var_value))

        try:
            # Use eval for arithmetic (safe since we control the input)
            return eval(expr)
        except:
            raise ValueError(f"Cannot evaluate expression: {expr}")

    def _execute_set(self, set_node: SetNode, exec_context: ExecutionContext):
        """Execute q:set statement"""
        try:
            # Get dict context for evaluation
            dict_context = exec_context.get_all_variables()

            # Handle different operations
            if set_node.operation == "assign":
                value = self._execute_set_assign(set_node, dict_context)
            elif set_node.operation == "increment":
                value = self._execute_set_increment(set_node, exec_context, set_node.step)
            elif set_node.operation == "decrement":
                value = self._execute_set_decrement(set_node, exec_context, set_node.step)
            elif set_node.operation in ["add", "multiply"]:
                value = self._execute_set_arithmetic(set_node, exec_context, dict_context)
            elif set_node.operation in ["append", "prepend", "remove", "removeAt", "clear", "sort", "reverse", "unique"]:
                value = self._execute_set_array_operation(set_node, exec_context)
            elif set_node.operation in ["merge", "setProperty", "deleteProperty", "clone"]:
                value = self._execute_set_object_operation(set_node, exec_context, dict_context)
            elif set_node.operation in ["uppercase", "lowercase", "trim", "format"]:
                value = self._execute_set_transformation(set_node, exec_context)
            else:
                raise ComponentExecutionError(f"Unsupported operation: {set_node.operation}")

            # Validate the value before setting
            self._validate_set_value(set_node, value)

            # Set the variable in the appropriate scope
            # If variable already exists, update it where it is; otherwise use specified scope
            if exec_context.has_variable(set_node.name) and set_node.scope == "local":
                # Variable exists, update it in its current location
                # Try to find where it is and update there
                if set_node.name in exec_context.component_vars or (exec_context.parent and set_node.name in exec_context._get_root_context().component_vars):
                    exec_context.set_variable(set_node.name, value, scope="component")
                elif set_node.name in exec_context.function_vars:
                    exec_context.set_variable(set_node.name, value, scope="function")
                else:
                    exec_context.set_variable(set_node.name, value, scope="local")
            else:
                exec_context.set_variable(set_node.name, value, scope=set_node.scope)

            # Update self.context for backward compatibility
            self.context[set_node.name] = value

            return None  # q:set doesn't return a value

        except ValidationError as e:
            raise ComponentExecutionError(f"Validation error for '{set_node.name}': {e}")
        except Exception as e:
            raise ComponentExecutionError(f"Set execution error for '{set_node.name}': {e}")

    def _execute_set_assign(self, set_node: SetNode, context: Dict[str, Any]) -> Any:
        """Execute assign operation"""
        # Get value (or default)
        value_expr = set_node.value if set_node.value is not None else set_node.default

        if value_expr is None:
            if not set_node.nullable:
                raise ComponentExecutionError(f"Variable '{set_node.name}' cannot be null")
            return None

        # Process databinding in value
        processed_value = self._apply_databinding(value_expr, context)

        # Convert to appropriate type
        return self._convert_to_type(processed_value, set_node.type)

    def _execute_set_increment(self, set_node: SetNode, exec_context: ExecutionContext, step: int) -> Any:
        """Execute increment operation"""
        try:
            current_value = exec_context.get_variable(set_node.name)
            if not isinstance(current_value, (int, float)):
                raise ComponentExecutionError(f"Cannot increment non-numeric value: {current_value}")
            return current_value + step
        except VariableNotFoundError:
            # If variable doesn't exist, start from step
            return step

    def _execute_set_decrement(self, set_node: SetNode, exec_context: ExecutionContext, step: int) -> Any:
        """Execute decrement operation"""
        try:
            current_value = exec_context.get_variable(set_node.name)
            if not isinstance(current_value, (int, float)):
                raise ComponentExecutionError(f"Cannot decrement non-numeric value: {current_value}")
            return current_value - step
        except VariableNotFoundError:
            # If variable doesn't exist, start from -step
            return -step

    def _execute_set_arithmetic(self, set_node: SetNode, exec_context: ExecutionContext, context: Dict[str, Any]) -> Any:
        """Execute arithmetic operations (add, multiply)"""
        try:
            current_value = exec_context.get_variable(set_node.name)
        except VariableNotFoundError:
            current_value = 0

        if not isinstance(current_value, (int, float)):
            raise ComponentExecutionError(f"Cannot perform arithmetic on non-numeric value: {current_value}")

        # Get operand value
        operand_expr = set_node.value
        if not operand_expr:
            raise ComponentExecutionError("Arithmetic operation requires a value")

        # Get fresh context to include loop variables
        fresh_context = exec_context.get_all_variables()
        processed = self._apply_databinding(operand_expr, fresh_context)
        operand = self._convert_to_type(processed, "number")

        if set_node.operation == "add":
            return current_value + operand
        elif set_node.operation == "multiply":
            return current_value * operand

        return current_value

    def _execute_set_array_operation(self, set_node: SetNode, exec_context: ExecutionContext) -> Any:
        """Execute array operations"""
        try:
            current_value = exec_context.get_variable(set_node.name)
        except VariableNotFoundError:
            current_value = []

        if not isinstance(current_value, list):
            raise ComponentExecutionError(f"Cannot perform array operation on non-array: {type(current_value)}")

        # Create a copy to avoid modifying original
        result = current_value.copy()

        if set_node.operation == "append":
            if set_node.value:
                result.append(set_node.value)
        elif set_node.operation == "prepend":
            if set_node.value:
                result.insert(0, set_node.value)
        elif set_node.operation == "remove":
            if set_node.value and set_node.value in result:
                result.remove(set_node.value)
        elif set_node.operation == "removeAt":
            if set_node.index is not None:
                idx = int(set_node.index)
                if 0 <= idx < len(result):
                    result.pop(idx)
        elif set_node.operation == "clear":
            result = []
        elif set_node.operation == "sort":
            result.sort()
        elif set_node.operation == "reverse":
            result.reverse()
        elif set_node.operation == "unique":
            result = list(dict.fromkeys(result))  # Preserve order

        return result

    def _execute_set_object_operation(self, set_node: SetNode, exec_context: ExecutionContext, context: Dict[str, Any]) -> Any:
        """Execute object operations"""
        try:
            current_value = exec_context.get_variable(set_node.name)
        except VariableNotFoundError:
            current_value = {}

        if not isinstance(current_value, dict):
            raise ComponentExecutionError(f"Cannot perform object operation on non-object: {type(current_value)}")

        result = current_value.copy()

        if set_node.operation == "merge":
            if set_node.value:
                import json
                try:
                    merge_data = json.loads(set_node.value)
                    result.update(merge_data)
                except json.JSONDecodeError:
                    raise ComponentExecutionError(f"Invalid JSON for merge: {set_node.value}")
        elif set_node.operation == "setProperty":
            if set_node.key and set_node.value:
                result[set_node.key] = set_node.value
        elif set_node.operation == "deleteProperty":
            if set_node.key and set_node.key in result:
                del result[set_node.key]
        elif set_node.operation == "clone":
            if set_node.source:
                try:
                    source_obj = exec_context.get_variable(set_node.source)
                    if isinstance(source_obj, dict):
                        result = source_obj.copy()
                except VariableNotFoundError:
                    pass

        return result

    def _execute_set_transformation(self, set_node: SetNode, exec_context: ExecutionContext) -> Any:
        """Execute string transformation operations"""
        try:
            current_value = exec_context.get_variable(set_node.name)
        except VariableNotFoundError:
            current_value = ""

        value_str = str(current_value)

        if set_node.operation == "uppercase":
            return value_str.upper()
        elif set_node.operation == "lowercase":
            return value_str.lower()
        elif set_node.operation == "trim":
            return value_str.strip()
        elif set_node.operation == "format":
            # TODO: Implement format based on format attribute
            return value_str

        return value_str

    def _convert_to_type(self, value: Any, target_type: str) -> Any:
        """Convert value to target type"""
        if value is None:
            return None

        try:
            if target_type == "string":
                return str(value)
            elif target_type == "number":
                # Try int first, then float
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
                    import json
                    return json.loads(value)
                return [value]
            elif target_type == "object":
                if isinstance(value, dict):
                    return value
                if isinstance(value, str):
                    import json
                    return json.loads(value)
                return {}
            else:
                # Default: return as is
                return value
        except Exception as e:
            raise ComponentExecutionError(f"Type conversion error to '{target_type}': {e}")

    def _validate_set_value(self, set_node: SetNode, value: Any):
        """
        Validate a value against set_node validation rules

        Args:
            set_node: SetNode with validation rules
            value: Value to validate

        Raises:
            ValidationError: If validation fails
        """
        # Check required
        if set_node.required:
            is_valid, error = QuantumValidators.validate_required(value)
            if not is_valid:
                raise ValidationError(error)

        # Check nullable
        if not set_node.nullable and value is None:
            raise ValidationError(f"Variable '{set_node.name}' cannot be null")

        # If value is None and nullable=True, skip other validations
        if value is None and set_node.nullable:
            return

        # Check validate_rule (regex or built-in validator)
        if set_node.validate_rule:
            # Special case: CPF and CNPJ have digit validation
            if set_node.validate_rule == 'cpf':
                is_valid, error = QuantumValidators.validate_cpf(str(value))
            elif set_node.validate_rule == 'cnpj':
                is_valid, error = QuantumValidators.validate_cnpj(str(value))
            else:
                is_valid, error = QuantumValidators.validate(value, set_node.validate_rule)

            if not is_valid:
                raise ValidationError(error)

        # Check pattern (alias for validate_rule)
        if set_node.pattern and not set_node.validate_rule:
            is_valid, error = QuantumValidators.validate(value, set_node.pattern)
            if not is_valid:
                raise ValidationError(error)

        # Check range
        if set_node.range:
            is_valid, error = QuantumValidators.validate_range(value, set_node.range)
            if not is_valid:
                raise ValidationError(error)

        # Check enum
        if set_node.enum:
            is_valid, error = QuantumValidators.validate_enum(value, set_node.enum)
            if not is_valid:
                raise ValidationError(error)

        # Check min/max
        if set_node.min or set_node.max:
            is_valid, error = QuantumValidators.validate_min_max(
                value,
                min_val=set_node.min,
                max_val=set_node.max
            )
            if not is_valid:
                raise ValidationError(error)

        # Check minlength/maxlength
        if set_node.type == "string" and (set_node.minlength or set_node.maxlength):
            minlen = int(set_node.minlength) if set_node.minlength else None
            maxlen = int(set_node.maxlength) if set_node.maxlength else None

            is_valid, error = QuantumValidators.validate_length(
                value,
                minlength=minlen,
                maxlength=maxlen
            )
            if not is_valid:
                raise ValidationError(error)

    def _evaluate_function_call(self, expr: str, context: Dict[str, Any]) -> Any:
        """
        Evaluate function call expression like 'add(5, 3)' or 'calculateTotal(items, 0.1)'
        """
        # Parse function name and arguments
        match = re.match(r'(\w+)\((.*)\)', expr.strip())
        if not match:
            raise ComponentExecutionError(f"Invalid function call syntax: {expr}")

        func_name = match.group(1)
        args_str = match.group(2).strip()

        # Resolve function
        func_node = self.function_registry.resolve_function(func_name, self.current_component)
        if not func_node:
            raise ComponentExecutionError(f"Function '{func_name}' not found")

        # Parse arguments
        args = self._parse_function_arguments(args_str, context, func_node)

        # Execute function
        return self._execute_function(func_node, args)

    def _parse_function_arguments(self, args_str: str, context: Dict[str, Any], func_node: FunctionNode) -> Dict[str, Any]:
        """Parse function arguments from string like '5, 3' or 'items, 0.1' or 'add(2, 3), 4'"""
        if not args_str:
            return {}

        # Smart split by comma - respect nested parentheses
        args = self._smart_split_args(args_str)

        arg_values = []
        for arg in args:
            arg = arg.strip()

            # Evaluate each argument as an expression
            try:
                # Try to evaluate as databinding expression (handles nested function calls)
                value = self._evaluate_databinding_expression(arg, context)
                arg_values.append(value)
            except:
                # Fallback: try as literal
                try:
                    # Try to parse as number
                    if '.' in arg:
                        arg_values.append(float(arg))
                    else:
                        arg_values.append(int(arg))
                except:
                    # Use as string (remove quotes if present)
                    if arg.startswith('\"') and arg.endswith('\"'):
                        arg_values.append(arg[1:-1])
                    elif arg.startswith("'") and arg.endswith("'"):
                        arg_values.append(arg[1:-1])
                    else:
                        arg_values.append(arg)

        # Match positional args to parameter names
        return dict(zip([p.name for p in func_node.params], arg_values))

    def _smart_split_args(self, args_str: str) -> List[str]:
        """Split arguments by comma, respecting nested parentheses"""
        args = []
        current_arg = []
        paren_depth = 0

        for char in args_str:
            if char == '(':
                paren_depth += 1
                current_arg.append(char)
            elif char == ')':
                paren_depth -= 1
                current_arg.append(char)
            elif char == ',' and paren_depth == 0:
                # Top-level comma - split here
                args.append(''.join(current_arg))
                current_arg = []
            else:
                current_arg.append(char)

        # Add last argument
        if current_arg:
            args.append(''.join(current_arg))

        return args

    def _execute_function(self, func_node: FunctionNode, args: Dict[str, Any]) -> Any:
        """Execute function with given arguments"""

        # Validate function parameters if requested
        if func_node.validate_params:
            self._validate_function_args(func_node, args)

        # Create function execution context (child of current context)
        func_context = self.execution_context.create_child_context()

        # Bind parameters to context
        for param in func_node.params:
            value = args.get(param.name)

            # Use default if not provided
            if value is None and param.default is not None:
                value = param.default

            # Check required
            if param.required and value is None:
                raise ComponentExecutionError(f"Required parameter '{param.name}' not provided")

            # Set in function context
            func_context.set_variable(param.name, value, scope="local")

        # Execute function body
        result = None
        for statement in func_node.body:
            if isinstance(statement, QuantumReturn):
                # Evaluate return value
                result = self._process_return_value(statement.value, func_context.get_all_variables())
                break
            elif isinstance(statement, SetNode):
                self._execute_set(statement, func_context)
            elif isinstance(statement, IfNode):
                result = self._execute_if(statement, func_context.get_all_variables())
                if result is not None:
                    break
            elif isinstance(statement, LoopNode):
                self._execute_loop(statement, func_context.get_all_variables())
            elif isinstance(statement, DispatchEventNode):
                self._execute_dispatch_event(statement, func_context.get_all_variables())

        return result

    def _validate_function_args(self, func_node: FunctionNode, args: Dict[str, Any]):
        """Validate function arguments against parameter definitions"""
        for param in func_node.params:
            value = args.get(param.name)

            # Check required
            if param.required and value is None:
                raise ComponentExecutionError(f"Required parameter '{param.name}' is missing")

            # Skip validation if no value provided
            if value is None:
                continue

            # Validate using QuantumValidators
            if param.validate_rule:
                if param.validate_rule == 'email':
                    is_valid, error = QuantumValidators.validate_email(str(value))
                elif param.validate_rule == 'cpf':
                    is_valid, error = QuantumValidators.validate_cpf(str(value))
                elif param.validate_rule == 'cnpj':
                    is_valid, error = QuantumValidators.validate_cnpj(str(value))
                else:
                    is_valid, error = QuantumValidators.validate(value, param.validate_rule)

                if not is_valid:
                    raise ValidationError(f"Parameter '{param.name}': {error}")

            # Validate range
            if param.range:
                is_valid, error = QuantumValidators.validate_range(value, param.range)
                if not is_valid:
                    raise ValidationError(f"Parameter '{param.name}': {error}")

            # Validate enum
            if param.enum:
                is_valid, error = QuantumValidators.validate_enum(value, param.enum)
                if not is_valid:
                    raise ValidationError(f"Parameter '{param.name}': {error}")

    def _execute_dispatch_event(self, dispatch_node: DispatchEventNode, context: Dict[str, Any]):
        """Execute q:dispatchEvent statement"""
        # For now, just log the event (TODO: integrate with actual message queue)
        event_data = {
            'event': dispatch_node.event,
            'data': self._apply_databinding(dispatch_node.data, context) if dispatch_node.data else None,
            'queue': dispatch_node.queue,
            'priority': dispatch_node.priority,
        }

        print(f"[EVENT DISPATCHED] {event_data}")
        # TODO: Integrate with RabbitMQ/SQS/etc

    def _execute_on_event(self, event_node: OnEventNode, event_data: Dict[str, Any]):
        """Execute q:onEvent handler (called by event system)"""
        # Create event context
        event_context = self.execution_context.create_child_context(scope="local")

        # Add event data to context
        for key, value in event_data.items():
            event_context.set_variable(key, value, scope="local")

        # Execute event handler body
        for statement in event_node.body:
            if isinstance(statement, SetNode):
                self._execute_set(statement, event_context)
            elif isinstance(statement, IfNode):
                self._execute_if(statement, event_context.get_all_variables())
            elif isinstance(statement, LoopNode):
                self._execute_loop(statement, event_context.get_all_variables())
            elif isinstance(statement, DispatchEventNode):
                self._execute_dispatch_event(statement, event_context.get_all_variables())
