"""
Runtime for q:function execution

Handles function calls, parameter binding, caching, and return values.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import hashlib
import json
from datetime import datetime, timedelta

# Fix imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from .ast_node import FunctionNode


class FunctionCache:
    """Simple in-memory cache for function results"""

    def __init__(self):
        self._cache: Dict[str, tuple] = {}  # key -> (value, expiry_time)
        self._memoize: Dict[str, Any] = {}  # key -> value (no expiry)

    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired"""
        if key in self._cache:
            value, expiry = self._cache[key]
            if expiry is None or datetime.now() < expiry:
                return value
            else:
                # Expired, remove
                del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set cached value with optional TTL (seconds)"""
        expiry = None
        if ttl:
            expiry = datetime.now() + timedelta(seconds=ttl)
        self._cache[key] = (value, expiry)

    def get_memoized(self, key: str) -> Optional[Any]:
        """Get memoized value (never expires)"""
        return self._memoize.get(key)

    def set_memoized(self, key: str, value: Any):
        """Set memoized value"""
        self._memoize[key] = value

    def clear(self):
        """Clear all cache"""
        self._cache.clear()
        self._memoize.clear()


class FunctionRuntime:
    """Runtime for executing Quantum functions"""

    def __init__(self):
        self.functions: Dict[str, FunctionNode] = {}
        self.cache = FunctionCache()

    def register_function(self, function: FunctionNode):
        """Register a function for execution"""
        self.functions[function.name] = function

    def call(self, name: str, args: Dict[str, Any], context: Dict[str, Any]) -> Any:
        """
        Call a function with arguments

        Args:
            name: Function name
            args: Function arguments (param_name -> value)
            context: Execution context (variables, state, etc)

        Returns:
            Function result
        """
        if name not in self.functions:
            raise RuntimeError(f"Function '{name}' not found")

        function = self.functions[name]

        # Check cache/memoize
        if function.cache or function.memoize:
            cache_key = self._make_cache_key(name, args)

            if function.memoize:
                cached = self.cache.get_memoized(cache_key)
                if cached is not None:
                    return cached
            elif function.cache:
                cached = self.cache.get(cache_key)
                if cached is not None:
                    return cached

        # Validate parameters
        if function.validate_params:
            self._validate_params(function, args)

        # Bind parameters to local scope
        local_scope = self._bind_params(function, args, context)

        # Execute function body
        result = self._execute_body(function, local_scope, context)

        # Store in cache
        if function.cache or function.memoize:
            cache_key = self._make_cache_key(name, args)
            if function.memoize:
                self.cache.set_memoized(cache_key, result)
            elif function.cache:
                self.cache.set(cache_key, result, function.cache_ttl)

        return result

    def _make_cache_key(self, name: str, args: Dict[str, Any]) -> str:
        """Generate cache key from function name and arguments"""
        # Sort args for consistent hashing
        args_str = json.dumps(args, sort_keys=True)
        key_str = f"{name}:{args_str}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _validate_params(self, function: FunctionNode, args: Dict[str, Any]):
        """Validate function parameters"""
        for param in function.params:
            # Check required params
            if param.required and param.name not in args:
                raise ValueError(f"Required parameter '{param.name}' missing in function '{function.name}'")

            # Type validation (basic)
            if param.name in args:
                value = args[param.name]
                expected_type = param.type

                if expected_type == 'number' and not isinstance(value, (int, float)):
                    try:
                        args[param.name] = float(value)
                    except (ValueError, TypeError):
                        raise TypeError(f"Parameter '{param.name}' must be a number, got {type(value).__name__}")

                elif expected_type == 'string' and not isinstance(value, str):
                    args[param.name] = str(value)

                elif expected_type == 'boolean' and not isinstance(value, bool):
                    if isinstance(value, str):
                        args[param.name] = value.lower() in ('true', '1', 'yes')
                    else:
                        args[param.name] = bool(value)

    def _bind_params(self, function: FunctionNode, args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Bind function parameters to local scope

        Creates a new scope with parameters + defaults
        """
        local_scope = {}

        for param in function.params:
            if param.name in args:
                local_scope[param.name] = args[param.name]
            elif param.default is not None:
                # Use default value
                local_scope[param.name] = self._evaluate_default(param.default, context)
            elif not param.required:
                # Optional param not provided, use None
                local_scope[param.name] = None

        return local_scope

    def _evaluate_default(self, default: str, context: Dict[str, Any]) -> Any:
        """Evaluate default value (may contain expressions)"""
        # Simple evaluation - in real implementation would use databinding engine
        if default.startswith('{') and default.endswith('}'):
            # Expression like {query.page}
            expr = default[1:-1]
            # For now, just return the string - real impl would evaluate
            return default
        else:
            # Literal value
            if default.lower() == 'true':
                return True
            elif default.lower() == 'false':
                return False
            elif default.lower() == 'null':
                return None
            try:
                return int(default)
            except ValueError:
                try:
                    return float(default)
                except ValueError:
                    return default

    def _execute_body(self, function: FunctionNode, local_scope: Dict[str, Any], context: Dict[str, Any]) -> Any:
        """
        Execute function body statements

        Returns the result from q:return statement
        """
        # Merge local scope with context (local scope takes precedence)
        execution_context = {**context, **local_scope}

        result = None

        # Execute each statement in function body
        for statement in function.body:
            statement_type = statement.__class__.__name__

            # Handle q:return
            if statement_type == 'QuantumReturn':
                # Return statement found - extract value and return
                result = self._evaluate_return(statement, execution_context)
                break

            # Handle q:set
            elif statement_type == 'SetNode':
                var_name = statement.name
                var_value = self._evaluate_expression(statement.value, execution_context)
                execution_context[var_name] = var_value
                local_scope[var_name] = var_value

            # Handle q:query (would delegate to query runtime)
            elif statement_type in ('QueryNode', 'LLMGenerateNode', 'SearchNode'):
                # In real implementation, would execute query and store result
                # For now, just acknowledge it exists
                pass

            # Handle q:if
            elif statement_type == 'IfNode':
                # In real implementation, would evaluate condition
                pass

            # Handle q:loop
            elif statement_type == 'LoopNode':
                # In real implementation, would execute loop
                pass

        return result

    def _evaluate_return(self, return_node, context: Dict[str, Any]) -> Any:
        """Evaluate q:return value"""
        if hasattr(return_node, 'value') and return_node.value:
            return self._evaluate_expression(return_node.value, context)
        return None

    def _evaluate_expression(self, expr: str, context: Dict[str, Any]) -> Any:
        """
        Evaluate an expression like {price * 0.9} or {user.name}

        This is a simplified version - real implementation would use
        the full databinding engine from runtime/databinding.py
        """
        if not expr:
            return None

        # Check if it's a databinding expression
        if '{' in expr and '}' in expr:
            # For now, just return the expression string
            # Real implementation would:
            # 1. Parse the expression
            # 2. Resolve variables from context
            # 3. Evaluate operators/functions
            # 4. Return result
            return expr
        else:
            # Literal value
            return expr


# Global function registry
_global_runtime = FunctionRuntime()


def register_function(function: FunctionNode):
    """Register function in global registry"""
    _global_runtime.register_function(function)


def call_function(name: str, args: Dict[str, Any], context: Dict[str, Any]) -> Any:
    """Call function from global registry"""
    return _global_runtime.call(name, args, context)


def clear_cache():
    """Clear function cache"""
    _global_runtime.cache.clear()
