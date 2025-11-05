"""
Quantum Component Runtime - Execute Quantum components
"""

import sys
from pathlib import Path
from typing import Any, Dict, List

# Fix imports
sys.path.append(str(Path(__file__).parent.parent))

from core.ast_nodes import ComponentNode, QuantumReturn, IfNode, LoopNode, SetNode, FunctionNode, DispatchEventNode, OnEventNode, QueryNode, InvokeNode, DataNode
from core.features.logging.src import LogNode, LoggingService
from core.features.dump.src import DumpNode, DumpService
from runtime.database_service import DatabaseService, QueryResult
from runtime.query_validators import QueryValidator, QueryValidationError
from runtime.execution_context import ExecutionContext, VariableNotFoundError
from runtime.validators import QuantumValidators, ValidationError
from runtime.function_registry import FunctionRegistry
from core.features.invocation.src.runtime import InvocationService
from core.features.data_import.src.runtime import DataImportService
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
        # Database service for query execution
        self.database_service = DatabaseService()
        # Invocation service for q:invoke
        self.invocation_service = InvocationService()
        # Data import service for q:data
        self.data_import_service = DataImportService()
        # Logging service for q:log
        self.logging_service = LoggingService()
        # Dump service for q:dump
        self.dump_service = DumpService()
    
    def execute_component(self, component: ComponentNode, params: Dict[str, Any] = None) -> Any:
        """Execute a component and return the result"""
        if params is None:
            params = {}

        # Set current component
        self.current_component = component

        # Register component functions
        self.function_registry.register_component(component)

        # Phase F: Initialize scopes from special parameters before validation
        if '_session_scope' in params:
            self.execution_context.session_vars = params.pop('_session_scope')
        if '_application_scope' in params:
            self.execution_context.application_vars = params.pop('_application_scope')
        if '_request_scope' in params:
            self.execution_context.request_vars = params.pop('_request_scope')

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

        # Try to parse as number
        try:
            # Try int first
            if '.' not in processed_value:
                return int(processed_value)
            else:
                return float(processed_value)
        except (ValueError, AttributeError):
            # Not a number, return as string
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
        elif isinstance(statement, QueryNode):
            return self._execute_query(statement, exec_context)
        elif isinstance(statement, InvokeNode):
            return self._execute_invoke(statement, exec_context)
        elif isinstance(statement, DataNode):
            return self._execute_data(statement, exec_context)
        elif isinstance(statement, LogNode):
            return self._execute_log(statement, exec_context)
        elif isinstance(statement, DumpNode):
            return self._execute_dump(statement, exec_context)
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
            elif isinstance(statement, LogNode):
                self._execute_log(statement, self.execution_context)
            elif isinstance(statement, DumpNode):
                self._execute_dump(statement, self.execution_context)
            # TODO: Handle other statement types
        return None
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate a condition string using databinding"""
        if not condition:
            return False

        try:
            # Apply databinding to resolve variables
            evaluated_condition = self._apply_databinding(condition, context)

            # If it's still a string, try to evaluate it as a boolean expression
            if isinstance(evaluated_condition, str):
                return bool(eval(evaluated_condition))

            # If databinding returned a boolean, use it directly
            return bool(evaluated_condition)
        except Exception as e:
            # Fallback - return False for safety
            return False
    
    def _execute_loop(self, loop_node: LoopNode, context: Dict[str, Any], exec_context: ExecutionContext = None):
        """Execute q:loop statement with various types"""
        # Use provided exec_context or fall back to component context
        if exec_context is None:
            exec_context = self.execution_context

        if loop_node.loop_type == 'range':
            return self._execute_range_loop(loop_node, context, exec_context)
        elif loop_node.loop_type == 'array':
            return self._execute_array_loop(loop_node, context, exec_context)
        elif loop_node.loop_type == 'list':
            return self._execute_list_loop(loop_node, context, exec_context)
        elif loop_node.loop_type == 'query':
            return self._execute_query_loop(loop_node, context, exec_context)
        else:
            raise ComponentExecutionError(f"Unsupported loop type: {loop_node.loop_type}")
    
    def _execute_range_loop(self, loop_node: LoopNode, context: Dict[str, Any], exec_context: ExecutionContext):
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
                exec_context.set_variable(loop_node.var_name, i, scope="local")

                # Execute loop body
                for statement in loop_node.body:
                    result = self._execute_loop_body_statement(statement, loop_context, exec_context)
                    if result is not None:
                        results.append(result)

            return results

        except (ValueError, TypeError) as e:
            raise ComponentExecutionError(f"Range loop error: {e}")
    
    def _execute_array_loop(self, loop_node: LoopNode, context: Dict[str, Any], exec_context: ExecutionContext):
        """Execute array loop"""
        results = []

        try:
            # Get array data (for now, parse simple array notation)
            array_data = self._parse_array_items(loop_node.items, context)

            # Execute loop
            for index, item in enumerate(array_data):
                # Set loop variable in execution context
                exec_context.set_variable(loop_node.var_name, item, scope="local")

                # Add index if specified
                if loop_node.index_name:
                    exec_context.set_variable(loop_node.index_name, index, scope="local")

                # Get fresh context dict from execution context (includes all updated variables)
                loop_context = exec_context.get_all_variables()

                # Execute loop body
                for statement in loop_node.body:
                    result = self._execute_loop_body_statement(statement, loop_context, exec_context)
                    if result is not None:
                        results.append(result)

                    # Sync loop_context after each statement to see updates
                    loop_context = exec_context.get_all_variables()

            return results

        except Exception as e:
            raise ComponentExecutionError(f"Array loop error: {e}")
    
    def _execute_list_loop(self, loop_node: LoopNode, context: Dict[str, Any], exec_context: ExecutionContext):
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

                # Also update execution context for q:set support
                exec_context.set_variable(loop_node.var_name, item.strip(), scope="local")

                # Add index if specified
                if loop_node.index_name:
                    loop_context[loop_node.index_name] = index
                    exec_context.set_variable(loop_node.index_name, index, scope="local")

                # Execute loop body
                for statement in loop_node.body:
                    result = self._execute_loop_body_statement(statement, loop_context, exec_context)
                    if result is not None:
                        results.append(result)

            return results

        except Exception as e:
            raise ComponentExecutionError(f"List loop error: {e}")

    def _execute_query_loop(self, loop_node: LoopNode, context: Dict[str, Any], exec_context: ExecutionContext):
        """Execute query loop - iterate over query result rows"""
        results = []

        try:
            # Get query data from context
            query_name = loop_node.query_name if hasattr(loop_node, 'query_name') else loop_node.var_name
            query_data = context.get(query_name)

            if query_data is None:
                # Try execution context
                query_data = exec_context.get_variable(query_name)

            if not query_data:
                raise ComponentExecutionError(f"Query '{query_name}' not found in context")

            if not isinstance(query_data, list):
                raise ComponentExecutionError(f"Query '{query_name}' is not iterable (got {type(query_data).__name__})")

            # Iterate over query rows
            for index, row in enumerate(query_data):
                # Create loop context with current row fields available as {queryName.fieldName}
                loop_context = context.copy()

                # Set current row index
                current_row_index = index

                # Make row fields accessible via dot notation
                # Store row data under query name for {queryName.field} access
                if isinstance(row, dict):
                    for field_name, field_value in row.items():
                        # Set {queryName.fieldName} in context
                        dotted_key = f"{query_name}.{field_name}"
                        loop_context[dotted_key] = field_value
                        exec_context.set_variable(dotted_key, field_value, scope="local")

                # Also provide currentRow variable for explicit access
                loop_context['currentRow'] = row
                exec_context.set_variable('currentRow', row, scope="local")

                # Provide index if requested
                if loop_node.index_name:
                    loop_context[loop_node.index_name] = index
                    exec_context.set_variable(loop_node.index_name, index, scope="local")

                # Execute loop body
                for statement in loop_node.body:
                    result = self._execute_loop_body_statement(statement, loop_context, exec_context)
                    if result is not None:
                        results.append(result)

            return results

        except Exception as e:
            raise ComponentExecutionError(f"Query loop error: {e}")

    def _execute_loop_body_statement(self, statement, context: Dict[str, Any], exec_context: ExecutionContext):
        """Execute a statement inside a loop body"""
        if isinstance(statement, QuantumReturn):
            return self._process_return_value(statement.value, context)
        elif isinstance(statement, IfNode):
            return self._execute_if(statement, context)
        elif isinstance(statement, LoopNode):
            return self._execute_loop(statement, context, exec_context)
        elif isinstance(statement, SetNode):
            # Execute set using the provided execution context
            return self._execute_set(statement, exec_context)
        elif isinstance(statement, LogNode):
            return self._execute_log(statement, exec_context)
        elif isinstance(statement, DumpNode):
            return self._execute_dump(statement, exec_context)
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

        # Apply databinding if expression contains {variable}
        if '{' in items_expr and '}' in items_expr:
            resolved = self._apply_databinding(items_expr, context)
            # If databinding returned an array, use it
            if isinstance(resolved, list):
                return resolved
            # Otherwise continue processing the resolved value
            items_expr = str(resolved) if not isinstance(resolved, str) else resolved

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
        """Evaluate a databinding expression like 'variable' or 'user.name' or 'functionName(args)' or 'result[0].id'"""

        # Handle function calls first (e.g., add(5, 3))
        # Check if it looks like a function call: word followed by (
        if '(' in expr and ')' in expr and re.match(r'^\s*\w+\s*\(', expr):
            return self._evaluate_function_call(expr, context)

        # Handle array indexing (e.g., result[0] or result[0].id)
        if '[' in expr and ']' in expr:
            return self._evaluate_array_index(expr, context)

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

        # Handle arithmetic and comparison expressions (count + 1, num > 0, etc.)
        if any(op in expr for op in ['+', '-', '*', '/', '>', '<', '=', '!', '(', ')']):
            return self._evaluate_arithmetic_expression(expr, context)

        # If not found, raise error
        raise ValueError(f"Variable '{expr}' not found in context")

    def _evaluate_array_index(self, expr: str, context: Dict[str, Any]) -> Any:
        """
        Evaluate array indexing expressions like:
        - result[0]
        - result[0].id
        - users[1].name
        """
        import re

        # Match pattern: variable[index] or variable[index].property.chain
        # Pattern: word[number](.property)*
        match = re.match(r'^(\w+)\[(\d+)\](\.(.+))?$', expr.strip())

        if not match:
            raise ValueError(f"Invalid array index expression: {expr}")

        var_name = match.group(1)
        index = int(match.group(2))
        property_chain = match.group(4)  # Everything after the ]., or None

        # Get the array
        array = context.get(var_name)
        if array is None:
            raise ValueError(f"Array '{var_name}' not found in context")

        if not isinstance(array, list):
            raise ValueError(f"Variable '{var_name}' is not an array (got {type(array).__name__})")

        # Check bounds
        if index < 0 or index >= len(array):
            raise ValueError(f"Array index {index} out of bounds for '{var_name}' (length {len(array)})")

        # Get the element
        element = array[index]

        # If no property chain, return the element
        if not property_chain:
            return element

        # Navigate property chain
        value = element
        for prop in property_chain.split('.'):
            if isinstance(value, dict) and prop in value:
                value = value[prop]
            else:
                raise ValueError(f"Property '{prop}' not found in array element")

        return value

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
            # For update operations (increment, decrement, etc.) or if variable already exists,
            # update it where it is; otherwise create in specified scope
            is_update_operation = set_node.operation in ["increment", "decrement", "add", "multiply",
                                                          "append", "prepend", "remove", "removeAt",
                                                          "clear", "sort", "reverse", "unique",
                                                          "merge", "setProperty", "deleteProperty",
                                                          "uppercase", "lowercase", "trim", "format"]

            if is_update_operation or (exec_context.has_variable(set_node.name) and set_node.scope == "local"):
                # Update variable in its existing scope
                exec_context.update_variable(set_node.name, value)
            else:
                # Create new variable in specified scope
                # Inside a function, if scope is "local" (default), use "function" scope instead
                # This ensures function-level variables are accessible in nested loops
                actual_scope = set_node.scope
                if set_node.scope == "local" and exec_context.parent is not None:
                    # We're in a nested context (e.g., function) - use function scope
                    actual_scope = "function"
                exec_context.set_variable(set_node.name, value, scope=actual_scope)

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
        # If value is provided, increment that; otherwise increment existing variable
        if set_node.value:
            dict_context = exec_context.get_all_variables()
            base_value = self._apply_databinding(set_node.value, dict_context)
            if not isinstance(base_value, (int, float)):
                raise ComponentExecutionError(f"Cannot increment non-numeric value: {base_value}")
            return base_value + step

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
        # If value is provided, decrement that; otherwise decrement existing variable
        if set_node.value:
            dict_context = exec_context.get_all_variables()
            base_value = self._apply_databinding(set_node.value, dict_context)
            if not isinstance(base_value, (int, float)):
                raise ComponentExecutionError(f"Cannot decrement non-numeric value: {base_value}")
            return base_value - step

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
        # If a value is provided, use that; otherwise use existing variable
        if set_node.value:
            dict_context = exec_context.get_all_variables()
            processed_value = self._apply_databinding(set_node.value, dict_context)
            value_str = str(processed_value)
        else:
            try:
                current_value = exec_context.get_variable(set_node.name)
                value_str = str(current_value)
            except VariableNotFoundError:
                value_str = ""

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
            elif target_type == "integer" or target_type == "number":
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
                self._execute_loop(statement, func_context.get_all_variables(), func_context)
            elif isinstance(statement, DispatchEventNode):
                self._execute_dispatch_event(statement, func_context.get_all_variables())
            elif isinstance(statement, LogNode):
                self._execute_log(statement, func_context)
            elif isinstance(statement, DumpNode):
                self._execute_dump(statement, func_context)

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
                # Use the generic validate method for all rules
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

    def _execute_query(self, query_node: QueryNode, exec_context: ExecutionContext) -> QueryResult:
        """
        Execute database query

        Args:
            query_node: QueryNode with query configuration
            exec_context: Execution context for variables

        Returns:
            QueryResult with data and metadata

        Raises:
            ComponentExecutionError: If query execution fails
        """
        try:
            # Get dict context for parameter resolution
            dict_context = exec_context.get_all_variables()

            # Resolve and validate parameters
            resolved_params = {}
            for param_node in query_node.params:
                # Resolve parameter value (apply databinding)
                param_value = self._apply_databinding(param_node.value, dict_context)

                # Build attributes dict for validation
                attributes = {
                    'null': param_node.null,
                    'max_length': param_node.max_length,
                    'scale': param_node.scale
                }

                # Validate and convert parameter
                try:
                    validated_value = QueryValidator.validate_param(
                        param_value,
                        param_node.param_type,
                        attributes
                    )
                    resolved_params[param_node.name] = validated_value
                except QueryValidationError as e:
                    raise ComponentExecutionError(
                        f"Parameter '{param_node.name}' validation failed: {e}"
                    )

            # Sanitize SQL (basic check)
            QueryValidator.sanitize_sql(query_node.sql)

            # Check if this is a Query of Queries (in-memory SQL)
            if query_node.source:
                return self._execute_query_of_queries(query_node, dict_context, resolved_params, exec_context)

            # Handle pagination if enabled
            pagination_metadata = None
            sql_to_execute = query_node.sql

            if query_node.paginate:
                # Execute COUNT(*) query to get total records
                count_sql = self._generate_count_query(query_node.sql)
                count_result = self.database_service.execute_query(
                    query_node.datasource,
                    count_sql,
                    resolved_params
                )

                # Get total count from result
                total_records = count_result.data[0]['count'] if count_result.data else 0

                # Calculate pagination metadata
                page = query_node.page if query_node.page is not None else 1
                page_size = query_node.page_size
                total_pages = (total_records + page_size - 1) // page_size  # Ceiling division

                # Add LIMIT and OFFSET to SQL
                offset = (page - 1) * page_size
                sql_to_execute = f"{query_node.sql}\nLIMIT {page_size} OFFSET {offset}"

                # Store pagination metadata
                pagination_metadata = {
                    'totalRecords': total_records,
                    'totalPages': total_pages,
                    'currentPage': page,
                    'pageSize': page_size,
                    'hasNextPage': page < total_pages,
                    'hasPreviousPage': page > 1,
                    'startRecord': offset + 1 if total_records > 0 else 0,
                    'endRecord': min(offset + page_size, total_records)
                }

            # Execute query via DatabaseService
            result = self.database_service.execute_query(
                query_node.datasource,
                sql_to_execute,
                resolved_params
            )

            # Store result in context with query name
            # Store both as QueryResult object and as plain dict for template access
            result_dict = result.to_dict()

            # Add pagination metadata if enabled
            if pagination_metadata:
                result_dict['pagination'] = pagination_metadata

            # Make data accessible directly as array (for q:loop)
            exec_context.set_variable(query_node.name, result.data, scope="component")

            # Also store full result object with metadata
            exec_context.set_variable(f"{query_node.name}_result", result_dict, scope="component")

            # Store in self.context for backward compatibility
            self.context[query_node.name] = result.data
            self.context[f"{query_node.name}_result"] = result_dict

            # For single-row results (INSERT RETURNING, etc.), expose fields directly
            # Allows {insertResult.id} instead of {insertResult[0].id}
            if result.data and len(result.data) == 1 and isinstance(result.data[0], dict):
                for field_name, field_value in result.data[0].items():
                    dotted_key = f"{query_node.name}.{field_name}"
                    exec_context.set_variable(dotted_key, field_value, scope="component")
                    self.context[dotted_key] = field_value

            # If result variable name specified, store metadata separately
            if query_node.result:
                exec_context.set_variable(query_node.result, result_dict, scope="component")
                self.context[query_node.result] = result_dict

            return result

        except QueryValidationError as e:
            raise ComponentExecutionError(f"Query validation error in '{query_node.name}': {e}")
        except Exception as e:
            raise ComponentExecutionError(f"Query execution error in '{query_node.name}': {e}")

    def _generate_count_query(self, original_sql: str) -> str:
        """
        Generate a COUNT(*) query from the original SQL.
        Wraps the original query in a subquery to handle complex cases.

        Example:
            Input:  SELECT id, name FROM users WHERE status = 'active' ORDER BY created_at DESC
            Output: SELECT COUNT(*) as count FROM (SELECT id, name FROM users WHERE status = 'active') AS count_query

        This approach works for:
        - Simple queries
        - Queries with JOINs
        - Queries with GROUP BY
        - Queries with complex WHERE clauses
        """
        import re

        # Normalize SQL (remove extra whitespace, newlines)
        sql = ' '.join(original_sql.split())

        # Remove ORDER BY clause (not needed for COUNT and causes issues in subquery)
        # Match ORDER BY ... up to end or until LIMIT/OFFSET/FOR UPDATE
        sql = re.sub(r'\s+ORDER\s+BY\s+[^;]+?(?=\s+(?:LIMIT|OFFSET|FOR\s+UPDATE)|$)', '', sql, flags=re.IGNORECASE)

        # Remove LIMIT and OFFSET clauses (pagination will be added separately)
        sql = re.sub(r'\s+LIMIT\s+\d+', '', sql, flags=re.IGNORECASE)
        sql = re.sub(r'\s+OFFSET\s+\d+', '', sql, flags=re.IGNORECASE)

        # Wrap in COUNT subquery
        # This handles all edge cases: JOINs, GROUP BY, complex WHERE, etc.
        count_sql = f"SELECT COUNT(*) as count FROM ({sql}) AS count_query"

        return count_sql

    def _execute_query_of_queries(self, query_node: 'QueryNode', context: Dict[str, Any],
                                   params: Dict[str, Any], exec_context: 'ExecutionContext') -> 'QueryResult':
        """
        Execute Query of Queries - SQL on in-memory result sets.

        Uses SQLite in-memory database to execute SQL on previous query results.

        Args:
            query_node: QueryNode with source attribute set
            context: Variable context
            params: Resolved query parameters
            exec_context: Execution context

        Returns:
            QueryResult with data and metadata

        Raises:
            ComponentExecutionError: If source query not found or execution fails
        """
        import sqlite3
        import time
        from .database_service import QueryResult

        try:
            # Get source query result from context
            source_name = query_node.source
            source_data = context.get(source_name) or exec_context.get_variable(source_name)

            if source_data is None:
                raise ComponentExecutionError(
                    f"Source query '{source_name}' not found for Query of Queries"
                )

            if not isinstance(source_data, list):
                raise ComponentExecutionError(
                    f"Source '{source_name}' is not a query result (got {type(source_data).__name__})"
                )

            if not source_data:
                # Empty source - return empty result
                return QueryResult(
                    success=True,
                    data=[],
                    record_count=0,
                    column_list=[],
                    execution_time=0,
                    sql=query_node.sql
                )

            # Create in-memory SQLite database
            conn = sqlite3.connect(':memory:')
            conn.row_factory = sqlite3.Row  # Enable column access by name
            cursor = conn.cursor()

            # Infer table structure from first row
            first_row = source_data[0]
            if not isinstance(first_row, dict):
                raise ComponentExecutionError(
                    f"Source data must be list of dictionaries (got {type(first_row).__name__})"
                )

            # Create table schema
            columns = list(first_row.keys())
            column_defs = ', '.join([f'"{col}" TEXT' for col in columns])  # Use TEXT for simplicity
            create_table_sql = f'CREATE TABLE source_table ({column_defs})'
            cursor.execute(create_table_sql)

            # Insert source data
            placeholders = ', '.join(['?' for _ in columns])
            insert_sql = f'INSERT INTO source_table VALUES ({placeholders})'
            for row in source_data:
                values = [row.get(col) for col in columns]
                cursor.execute(insert_sql, values)

            # Replace source name in SQL with actual table name
            # Support both "FROM source" and "FROM {source}" syntax
            sql = query_node.sql
            sql = sql.replace(f'FROM {source_name}', 'FROM source_table')
            sql = sql.replace(f'FROM {{{source_name}}}', 'FROM source_table')

            # Apply parameter binding (convert :name to ?)
            for param_name, param_value in params.items():
                sql = sql.replace(f':{param_name}', '?')

            # Execute query
            start_time = time.time()
            cursor.execute(sql, list(params.values()) if params else [])
            result_rows = cursor.fetchall()
            execution_time = (time.time() - start_time) * 1000  # Convert to ms

            # Convert to list of dicts
            result_data = []
            if result_rows:
                column_names = [description[0] for description in cursor.description]
                for row in result_rows:
                    result_data.append(dict(zip(column_names, row)))

            # Close connection
            conn.close()

            # Return QueryResult
            result = QueryResult(
                success=True,
                data=result_data,
                record_count=len(result_data),
                column_list=column_names if result_data else [],
                execution_time=int(execution_time),
                sql=query_node.sql
            )

            # Store result in context (same as regular query)
            result_dict = result.to_dict()
            exec_context.set_variable(query_node.name, result.data, scope="component")
            exec_context.set_variable(f"{query_node.name}_result", result_dict, scope="component")
            self.context[query_node.name] = result.data
            self.context[f"{query_node.name}_result"] = result_dict

            # Single-row field exposure
            if result.data and len(result.data) == 1 and isinstance(result.data[0], dict):
                for field_name, field_value in result.data[0].items():
                    dotted_key = f"{query_node.name}.{field_name}"
                    exec_context.set_variable(dotted_key, field_value, scope="component")
                    self.context[dotted_key] = field_value

            return result

        except sqlite3.Error as e:
            raise ComponentExecutionError(f"Query of Queries SQL error in '{query_node.name}': {e}")
        except Exception as e:
            raise ComponentExecutionError(f"Query of Queries execution error in '{query_node.name}': {e}")

    def _execute_invoke(self, invoke_node: InvokeNode, exec_context: ExecutionContext):
        """
        Execute invocation (function, component, HTTP, etc.)

        Args:
            invoke_node: InvokeNode with invocation configuration
            exec_context: Execution context for variables

        Returns:
            None (stores result in context)

        Raises:
            ComponentExecutionError: If invocation fails
        """
        try:
            # Get dict context for parameter resolution and databinding
            dict_context = exec_context.get_all_variables()

            # Get invocation type
            invocation_type = invoke_node.get_invocation_type()

            if invocation_type == "unknown":
                raise ComponentExecutionError(
                    f"Invoke '{invoke_node.name}' requires one of: function, component, url, endpoint, or service"
                )

            # Build invocation parameters based on type
            if invocation_type == "function":
                params = self._build_function_invoke_params(invoke_node, dict_context)
            elif invocation_type == "component":
                params = self._build_component_invoke_params(invoke_node, dict_context)
            elif invocation_type == "http":
                params = self._build_http_invoke_params(invoke_node, dict_context)
            else:
                raise ComponentExecutionError(f"Unsupported invocation type: {invocation_type}")

            # Check cache if enabled
            if invoke_node.cache:
                cache_key = f"invoke_{invoke_node.name}_{hash(str(params))}"
                cached_result = self.invocation_service.get_from_cache(cache_key)
                if cached_result is not None:
                    self._store_invoke_result(invoke_node, cached_result, exec_context)
                    return

            # Execute invocation
            result = self.invocation_service.invoke(
                invocation_type,
                params,
                context=self  # Pass runtime as context for function/component calls
            )

            # Cache result if enabled
            if invoke_node.cache and result.success:
                cache_key = f"invoke_{invoke_node.name}_{hash(str(params))}"
                self.invocation_service.put_in_cache(cache_key, result, invoke_node.ttl)

            # Store result in context
            self._store_invoke_result(invoke_node, result, exec_context)

        except Exception as e:
            raise ComponentExecutionError(f"Invoke execution error in '{invoke_node.name}': {e}")

    def _build_function_invoke_params(self, invoke_node: InvokeNode, dict_context: Dict[str, Any]) -> Dict[str, Any]:
        """Build parameters for function invocation"""
        args = {}

        # Resolve parameters
        for param in invoke_node.params:
            param_value = self._apply_databinding(param.default if param.default else "", dict_context)
            args[param.name] = param_value

        return {
            'function': invoke_node.function,
            'args': args
        }

    def _build_component_invoke_params(self, invoke_node: InvokeNode, dict_context: Dict[str, Any]) -> Dict[str, Any]:
        """Build parameters for component invocation"""
        args = {}

        # Resolve parameters
        for param in invoke_node.params:
            param_value = self._apply_databinding(param.default if param.default else "", dict_context)
            args[param.name] = param_value

        return {
            'component': invoke_node.component,
            'args': args
        }

    def _build_http_invoke_params(self, invoke_node: InvokeNode, dict_context: Dict[str, Any]) -> Dict[str, Any]:
        """Build parameters for HTTP invocation"""
        # Resolve URL (may contain databinding)
        url = self._apply_databinding(invoke_node.url, dict_context)

        # Build headers
        headers = {}
        for header_node in invoke_node.headers:
            header_value = self._apply_databinding(header_node.value, dict_context)
            headers[header_node.name] = header_value

        # Add content-type header if not present
        if 'Content-Type' not in headers and 'content-type' not in headers:
            headers['Content-Type'] = invoke_node.content_type

        # Build query parameters
        query_params = {}
        for param in invoke_node.params:
            param_value = self._apply_databinding(param.default if param.default else "", dict_context)
            query_params[param.name] = param_value

        # Resolve body (may contain databinding)
        body = None
        if invoke_node.body:
            body = self._apply_databinding(invoke_node.body, dict_context)
            # Try to parse as JSON if it's a string and content-type is JSON
            if isinstance(body, str) and 'json' in invoke_node.content_type.lower():
                try:
                    import json
                    body = json.loads(body)
                except:
                    pass  # Keep as string if not valid JSON

        return {
            'url': url,
            'method': invoke_node.method,
            'headers': headers,
            'params': query_params,
            'body': body,
            'auth_type': invoke_node.auth_type,
            'auth_token': self._apply_databinding(invoke_node.auth_token, dict_context) if invoke_node.auth_token else None,
            'auth_header': invoke_node.auth_header,
            'auth_username': self._apply_databinding(invoke_node.auth_username, dict_context) if invoke_node.auth_username else None,
            'auth_password': self._apply_databinding(invoke_node.auth_password, dict_context) if invoke_node.auth_password else None,
            'timeout': invoke_node.timeout,
            'retry': invoke_node.retry,
            'retry_delay': invoke_node.retry_delay,
            'response_format': invoke_node.response_format
        }

    def _store_invoke_result(self, invoke_node: InvokeNode, result, exec_context: ExecutionContext):
        """Store invocation result in context"""
        # Store data directly (for easy access in templates)
        exec_context.set_variable(invoke_node.name, result.data, scope="component")
        self.context[invoke_node.name] = result.data

        # Build result object
        result_dict = {
            'success': result.success,
            'data': result.data,
            'error': result.error,
            'executionTime': result.execution_time,
            'invocationType': result.invocation_type,
            'metadata': result.metadata
        }

        # Store full result object
        exec_context.set_variable(f"{invoke_node.name}_result", result_dict, scope="component")
        self.context[f"{invoke_node.name}_result"] = result_dict

        # If result variable name specified, store metadata separately
        if invoke_node.result:
            exec_context.set_variable(invoke_node.result, result_dict, scope="component")
            self.context[invoke_node.result] = result_dict

    def _execute_data(self, data_node: DataNode, exec_context: ExecutionContext):
        """
        Execute data import and transformation

        Args:
            data_node: DataNode with import configuration
            exec_context: Execution context for variables

        Returns:
            None (stores result in context)

        Raises:
            ComponentExecutionError: If data import fails
        """
        try:
            # Get dict context for parameter resolution and databinding
            dict_context = exec_context.get_all_variables()

            # Resolve source (may contain databinding)
            source = self._apply_databinding(data_node.source, dict_context)

            # Build parameters for data import
            params = {
                'cache': data_node.cache,
                'ttl': data_node.ttl,
                'delimiter': data_node.delimiter,
                'quote': data_node.quote,
                'header': data_node.header,
                'encoding': data_node.encoding,
                'skip_rows': data_node.skip_rows,
                'xpath': data_node.xpath,
                'namespace': data_node.namespace,
                'columns': [],
                'fields': [],
                'transforms': [],
                'headers': []
            }

            # Add column definitions (for CSV)
            for col in data_node.columns:
                params['columns'].append({
                    'name': col.name,
                    'type': col.col_type,
                    'required': col.required,
                    'default': col.default
                })

            # Add field definitions (for XML)
            for field in data_node.fields:
                params['fields'].append({
                    'name': field.name,
                    'xpath': field.xpath,
                    'type': field.field_type
                })

            # Add HTTP headers
            for header in data_node.headers:
                resolved_value = self._apply_databinding(header.value, dict_context)
                params['headers'].append({
                    'name': header.name,
                    'value': resolved_value
                })

            # Add transformations
            for transform in data_node.transforms:
                for operation in transform.operations:
                    op_dict = {
                        'type': operation.__class__.__name__.replace('Node', '').lower()
                    }

                    if hasattr(operation, 'condition'):
                        # Filter operation
                        op_dict['condition'] = operation.condition
                    elif hasattr(operation, 'by'):
                        # Sort operation
                        op_dict['by'] = operation.by
                        op_dict['order'] = operation.order
                    elif hasattr(operation, 'value'):
                        # Limit operation
                        op_dict['value'] = operation.value
                    elif hasattr(operation, 'field'):
                        # Compute operation
                        op_dict['field'] = operation.field
                        op_dict['expression'] = operation.expression
                        op_dict['type'] = operation.comp_type

                    params['transforms'].append(op_dict)

            # Execute data import
            result = self.data_import_service.import_data(
                data_node.data_type,
                source,
                params,
                context=exec_context
            )

            # Store result in context
            self._store_data_result(data_node, result, exec_context)

        except Exception as e:
            raise ComponentExecutionError(f"Data import error in '{data_node.name}': {e}")

    def _store_data_result(self, data_node: DataNode, result, exec_context: ExecutionContext):
        """Store data import result in context"""
        # Store data directly (for easy access in templates and loops)
        exec_context.set_variable(data_node.name, result.data, scope="component")
        self.context[data_node.name] = result.data

        # Build result object
        result_dict = {
            'success': result.success,
            'data': result.data,
            'error': result.error,
            'recordCount': result.recordCount,
            'loadTime': result.loadTime,
            'cached': result.cached,
            'source': result.source
        }

        # Store full result object
        exec_context.set_variable(f"{data_node.name}_result", result_dict, scope="component")
        self.context[f"{data_node.name}_result"] = result_dict

        # If result variable name specified, store metadata separately
        if data_node.result:
            exec_context.set_variable(data_node.result, result_dict, scope="component")
            self.context[data_node.result] = result_dict

    def get_function(self, function_name: str) -> FunctionNode:
        """Get function by name from current component"""
        if not self.current_component:
            return None

        for func in self.current_component.functions:
            if func.name == function_name:
                return func

        return None


    def _execute_log(self, log_node: LogNode, exec_context: ExecutionContext):
        """
        Execute logging statement

        Args:
            log_node: LogNode with logging configuration
            exec_context: Execution context for variables

        Returns:
            None (logs to configured output)

        Raises:
            ComponentExecutionError: If logging fails
        """
        try:
            # Get dict context for databinding
            dict_context = exec_context.get_all_variables()

            # Check conditional execution
            if log_node.when:
                condition_result = self._apply_databinding(log_node.when, dict_context)
                if not self.logging_service.should_log(condition_result):
                    return

            # Resolve message (apply databinding)
            message = self._apply_databinding(log_node.message, dict_context)

            # Resolve context data if provided
            context_data = None
            if log_node.context:
                # Parse context as JSON or variable reference
                context_expr = self._apply_databinding(log_node.context, dict_context)
                if isinstance(context_expr, dict):
                    context_data = context_expr
                elif isinstance(context_expr, str):
                    try:
                        import json
                        context_data = json.loads(context_expr)
                    except:
                        # Not JSON - treat as single value
                        context_data = {'value': context_expr}

            # Resolve correlation_id if provided
            correlation_id = None
            if log_node.correlation_id:
                correlation_id = self._apply_databinding(log_node.correlation_id, dict_context)

            # Execute logging
            result = self.logging_service.log(
                level=log_node.level,
                message=str(message),
                context=context_data,
                correlation_id=correlation_id
            )

            # Note: We don't store log result in context since logging is side-effect only
            # However, we could expose {log_result.success} if needed in future

        except Exception as e:
            raise ComponentExecutionError(f"Logging error: {e}")

    def _execute_dump(self, dump_node: DumpNode, exec_context: ExecutionContext):
        """
        Execute variable dump/inspection

        Args:
            dump_node: DumpNode with dump configuration
            exec_context: Execution context for variables

        Returns:
            str: Formatted dump output (stored in context and printed)

        Raises:
            ComponentExecutionError: If dump fails
        """
        try:
            # Get dict context for databinding
            dict_context = exec_context.get_all_variables()

            # Check conditional execution
            if dump_node.when:
                condition_result = self._apply_databinding(dump_node.when, dict_context)
                if not self.dump_service.should_dump(condition_result):
                    return

            # Resolve variable to dump
            var_expr = dump_node.var
            try:
                var_value = self._apply_databinding(var_expr, dict_context)
            except Exception as e:
                # If variable not found, dump the error
                var_value = f"<Variable '{var_expr}' not found: {e}>"

            # Generate dump output
            dump_output = self.dump_service.dump(
                var=var_value,
                label=dump_node.label,
                format=dump_node.format,
                depth=dump_node.depth
            )

            # Print dump output (for development/debugging)
            print(dump_output)

            # Also store in context for potential template rendering
            dump_var_name = f"_dump_{dump_node.label.replace(' ', '_')}"
            exec_context.set_variable(dump_var_name, dump_output, scope="component")
            self.context[dump_var_name] = dump_output

            return dump_output

        except Exception as e:
            raise ComponentExecutionError(f"Dump error: {e}")

    def execute_function(self, function_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute function and return result"""
        try:
            result = self.function_registry.call_function(function_name, args, self)
            return {
                'success': True,
                'data': result
            }
        except Exception as e:
            return {
                'success': False,
                'error': {
                    'message': str(e),
                    'type': type(e).__name__
                }
            }
