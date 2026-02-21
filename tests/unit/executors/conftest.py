"""
Shared fixtures for executor tests.

Provides mock runtime and execution context that properly implement
the interfaces required by BaseExecutor.
"""

import pytest
import re
from unittest.mock import MagicMock
from typing import Any, Dict


class MockExecutionContext:
    """Mock execution context that mimics real ExecutionContext"""

    def __init__(self, variables: Dict[str, Any] = None):
        self._variables = variables.copy() if variables else {}
        self.parent = None

    def get_all_variables(self) -> Dict[str, Any]:
        """Get all variables"""
        return self._variables.copy()

    def get_variable(self, name: str) -> Any:
        """Get a variable by name"""
        if name in self._variables:
            return self._variables[name]
        # Support dotted access like "obj.field"
        if '.' in name:
            parts = name.split('.')
            value = self._variables.get(parts[0])
            for part in parts[1:]:
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    raise KeyError(name)
            return value
        raise KeyError(f"Variable '{name}' not found")

    def set_variable(self, name: str, value: Any, scope: str = "local"):
        """Set a variable"""
        self._variables[name] = value

    def has_variable(self, name: str) -> bool:
        """Check if variable exists"""
        return name in self._variables

    def update_variable(self, name: str, value: Any):
        """Update an existing variable"""
        self._variables[name] = value


class MockRuntime:
    """
    Mock runtime that implements all methods required by BaseExecutor.

    This mock provides:
    - _apply_databinding: Resolves {variable} expressions
    - _evaluate_condition: Evaluates condition strings
    - _process_return_value: Processes return values
    - executor_registry: Mock registry for child execution
    """

    def __init__(self, variables: Dict[str, Any] = None):
        self.execution_context = MockExecutionContext(variables)
        self._executor_registry = MagicMock()

    @property
    def services(self):
        """Mock service container"""
        return MagicMock()

    @property
    def executor_registry(self):
        """Mock executor registry"""
        return self._executor_registry

    def _apply_databinding(self, value: str, context: Dict[str, Any]) -> Any:
        """
        Apply databinding to resolve {variable} expressions.

        Examples:
            "{name}" -> context["name"]
            "{user.name}" -> context["user"]["name"]
            "Hello {name}" -> "Hello " + context["name"]
        """
        if not isinstance(value, str):
            return value

        if not ('{' in value and '}' in value):
            return value

        # Simple case: just a variable reference like "{varname}"
        simple_match = re.match(r'^\{([^}]+)\}$', value.strip())
        if simple_match:
            var_name = simple_match.group(1)
            return self._get_nested_value(var_name, context)

        # Complex case: mixed text and variables
        def replacer(match):
            var_name = match.group(1)
            resolved = self._get_nested_value(var_name, context)
            return str(resolved) if resolved is not None else ''

        return re.sub(r'\{([^}]+)\}', replacer, value)

    def _get_nested_value(self, path: str, context: Dict[str, Any]) -> Any:
        """Get a value from context, supporting dotted paths"""
        if '.' not in path:
            return context.get(path, path)

        parts = path.split('.')
        value = context.get(parts[0])
        for part in parts[1:]:
            if isinstance(value, dict):
                value = value.get(part)
            elif hasattr(value, part):
                value = getattr(value, part)
            else:
                return None
        return value

    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """
        Evaluate a condition string.

        Supports:
            - Variable references
            - Comparison operators: ==, !=, >, <, >=, <=
            - Logical operators: and, or, not
            - in operator for list membership
            - is None check
        """
        if not condition:
            return False

        # First, apply databinding to resolve variables
        resolved = self._apply_databinding(condition, context)

        # Build evaluation context with all variables
        eval_context = context.copy()
        eval_context['True'] = True
        eval_context['False'] = False
        eval_context['None'] = None

        try:
            # Safely evaluate the condition
            return bool(eval(resolved, {"__builtins__": {}}, eval_context))
        except Exception:
            # If eval fails, try to evaluate as a simple truthy check
            if resolved in context:
                return bool(context[resolved])
            return bool(resolved)

    def _process_return_value(self, value: str, context: Dict[str, Any]) -> Any:
        """Process a return value, resolving databinding"""
        return self._apply_databinding(value, context)


@pytest.fixture
def mock_runtime():
    """Create a fresh mock runtime"""
    return MockRuntime()


@pytest.fixture
def mock_runtime_with_vars():
    """Factory fixture to create mock runtime with specific variables"""
    def _create(variables: Dict[str, Any]):
        return MockRuntime(variables)
    return _create


# ============================================================================
# Executor-specific fixtures
# ============================================================================

@pytest.fixture
def set_executor():
    """Create a SetExecutor with mock runtime"""
    from runtime.executors.control_flow.set_executor import SetExecutor
    runtime = MockRuntime()
    return SetExecutor(runtime)


@pytest.fixture
def if_executor():
    """Create an IfExecutor with mock runtime"""
    from runtime.executors.control_flow.if_executor import IfExecutor
    runtime = MockRuntime()
    return IfExecutor(runtime)


@pytest.fixture
def loop_executor():
    """Create a LoopExecutor with mock runtime"""
    from runtime.executors.control_flow.loop_executor import LoopExecutor
    runtime = MockRuntime()
    return LoopExecutor(runtime)


# Generic executor fixture that returns the appropriate executor based on test module
@pytest.fixture
def executor(request):
    """
    Generic executor fixture.
    Returns the appropriate executor based on the test module name.
    """
    module_name = request.module.__name__
    runtime = MockRuntime()

    if 'set_executor' in module_name:
        from runtime.executors.control_flow.set_executor import SetExecutor
        return SetExecutor(runtime)
    elif 'if_executor' in module_name:
        from runtime.executors.control_flow.if_executor import IfExecutor
        return IfExecutor(runtime)
    elif 'loop_executor' in module_name:
        from runtime.executors.control_flow.loop_executor import LoopExecutor
        return LoopExecutor(runtime)
    else:
        raise ValueError(f"Unknown executor type for module: {module_name}")


@pytest.fixture
def runtime():
    """Alias for mock_runtime for backward compatibility"""
    return MockRuntime()
