"""
Python Executor - Execute q:python statements

Handles embedded Python code execution.
"""

from typing import Any, List, Dict, Type
from runtime.executors.base import BaseExecutor, ExecutorError
from core.ast_nodes import PythonNode


class PythonExecutor(BaseExecutor):
    """
    Executor for q:python statements.

    Supports:
    - Inline Python code execution
    - Component, isolated, and module scopes
    - Async execution
    - Timeout limits
    - Bridge object for context access
    """

    @property
    def handles(self) -> List[Type]:
        return [PythonNode]

    def execute(self, node: PythonNode, exec_context) -> Any:
        """
        Execute Python code block.

        Args:
            node: PythonNode with Python code
            exec_context: Execution context

        Returns:
            Execution result (if result attribute set)
        """
        try:
            context = exec_context.get_all_variables()

            # Build bridge object for q.variable access
            bridge = QuantumBridge(exec_context, context)

            # Build execution namespace
            namespace = {
                'q': bridge,
                '__quantum_context__': context
            }

            # Add component scope variables if not isolated
            if node.scope == 'component':
                namespace.update(context)

            # Execute code
            code = node.code.strip()

            if node.async_mode:
                result = self._execute_async(code, namespace, node.timeout)
            else:
                result = self._execute_sync(code, namespace, node.timeout)

            # Store result if requested
            if node.result:
                exec_context.set_variable(node.result, result, scope="component")

            # Export bridge changes to context
            for key, value in bridge._exports.items():
                exec_context.set_variable(key, value, scope="component")

            return result

        except Exception as e:
            raise ExecutorError(f"Python execution error: {e}")

    def _execute_sync(self, code: str, namespace: Dict, timeout: str = None) -> Any:
        """Execute Python code synchronously."""
        # Handle return statements
        if 'return ' in code:
            # Wrap in function
            wrapped = f"def __quantum_exec__():\n"
            for line in code.split('\n'):
                wrapped += f"    {line}\n"
            wrapped += "__quantum_result__ = __quantum_exec__()"
            exec(wrapped, namespace)
            return namespace.get('__quantum_result__')
        else:
            exec(code, namespace)
            return None

    def _execute_async(self, code: str, namespace: Dict, timeout: str = None) -> Any:
        """Execute Python code asynchronously."""
        import asyncio

        async def run_async():
            # Wrap in async function
            wrapped = f"async def __quantum_async__():\n"
            for line in code.split('\n'):
                wrapped += f"    {line}\n"
            exec(wrapped, namespace)
            return await namespace['__quantum_async__']()

        # Parse timeout
        timeout_seconds = None
        if timeout:
            timeout_seconds = self._parse_timeout(timeout)

        return asyncio.run(asyncio.wait_for(run_async(), timeout=timeout_seconds))

    def _parse_timeout(self, timeout: str) -> float:
        """Parse timeout string to seconds."""
        if timeout.endswith('s'):
            return float(timeout[:-1])
        elif timeout.endswith('m'):
            return float(timeout[:-1]) * 60
        elif timeout.endswith('h'):
            return float(timeout[:-1]) * 3600
        return float(timeout)


class QuantumBridge:
    """Bridge object for accessing Quantum context from Python."""

    def __init__(self, exec_context, context: Dict[str, Any]):
        self._exec_context = exec_context
        self._context = context
        self._exports = {}

    def __getattr__(self, name: str) -> Any:
        """Get variable from context."""
        if name.startswith('_'):
            return object.__getattribute__(self, name)
        return self._context.get(name)

    def __setattr__(self, name: str, value: Any):
        """Set variable in context."""
        if name.startswith('_'):
            object.__setattr__(self, name, value)
        else:
            self._exports[name] = value

    def export(self, name: str, value: Any):
        """Explicitly export a variable."""
        self._exports[name] = value

    def get(self, name: str, default: Any = None) -> Any:
        """Get variable with default."""
        return self._context.get(name, default)

    def set(self, name: str, value: Any):
        """Set variable."""
        self._exports[name] = value

    def has(self, name: str) -> bool:
        """Check if variable exists."""
        return name in self._context
