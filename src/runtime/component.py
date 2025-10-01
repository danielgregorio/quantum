"""
Quantum Component Runtime - Execute Quantum components
"""

import sys
from pathlib import Path
from typing import Any, Dict, List

# Fix imports
sys.path.append(str(Path(__file__).parent.parent))

from core.ast_nodes import ComponentNode, QuantumReturn, IfNode, LoopNode

class ComponentExecutionError(Exception):
    """Error in component execution"""
    pass

class ComponentRuntime:
    """Runtime for executing Quantum components"""
    
    def __init__(self):
        self.context: Dict[str, Any] = {}
    
    def execute_component(self, component: ComponentNode, params: Dict[str, Any] = None) -> Any:
        """Execute a component and return the result"""
        if params is None:
            params = {}
        
        # Validate parameters
        validation_errors = self._validate_params(component, params)
        if validation_errors:
            raise ComponentExecutionError(f"Validation errors: {validation_errors}")
        
        # Setup context
        self.context.update(params)
        
        # Execute component
        try:
            # Execute control flow statements first
            for statement in component.statements:
                result = self._execute_statement(statement, self.context)
                if result is not None:
                    return result
            
            # For now, simple execution based on q:return
            if component.returns:
                first_return = component.returns[0]
                return self._process_return_value(first_return.value, self.context)
            
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
    
    def _execute_statement(self, statement, context: Dict[str, Any]):
        """Execute a control flow statement"""
        if isinstance(statement, IfNode):
            return self._execute_if(statement, context)
        elif isinstance(statement, LoopNode):
            return self._execute_loop(statement, context)
        # TODO: Add other statement types (set, etc)
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
        # TODO: Handle other statement types
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
    
    def _apply_databinding(self, text: str, context: Dict[str, Any]) -> str:
        """Apply variable databinding to text using {variable} syntax"""
        import re
        
        if not text or not context:
            return text
        
        # Pattern to match {variable} or {variable.property}
        pattern = r'\{([^}]+)\}'
        
        def replace_variable(match):
            var_expr = match.group(1).strip()
            try:
                return str(self._evaluate_databinding_expression(var_expr, context))
            except:
                # If evaluation fails, return original placeholder
                return match.group(0)
        
        # Replace all {variable} patterns
        result = re.sub(pattern, replace_variable, text)
        return result
    
    def _evaluate_databinding_expression(self, expr: str, context: Dict[str, Any]) -> Any:
        """Evaluate a databinding expression like 'variable' or 'user.name' or 'count + 1'"""
        
        # Handle simple variable access
        if expr in context:
            return context[expr]
        
        # Handle dot notation (user.name)
        if '.' in expr:
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
