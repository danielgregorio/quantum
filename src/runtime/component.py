"""
Quantum Component Runtime - Execute Quantum components
"""

import sys
from pathlib import Path
from typing import Any, Dict, List

# Fix imports
sys.path.append(str(Path(__file__).parent.parent))

from core.ast_nodes import ComponentNode, QuantumReturn, IfNode

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
                return self._process_return_value(first_return.value)
            
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
    
    def _process_return_value(self, value: str) -> Any:
        """Process return value (basic support for now)"""
        if not value:
            return ""
        
        # Remove quotes if it's a string literal
        if value.startswith('"') and value.endswith('"'):
            return value[1:-1]
        if value.startswith("'") and value.endswith("'"):
            return value[1:-1]
        
        # Try to parse JSON
        if value.startswith('{') or value.startswith('['):
            try:
                import json
                return json.loads(value)
            except:
                pass
        
        return value
    
    def _execute_statement(self, statement, context: Dict[str, Any]):
        """Execute a control flow statement"""
        if isinstance(statement, IfNode):
            return self._execute_if(statement, context)
        # TODO: Add other statement types (set, loop, etc)
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
                return self._process_return_value(statement.value)
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
