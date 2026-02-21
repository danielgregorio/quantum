"""
Thread Executor - Execute q:thread statements

Handles async thread execution.
"""

from typing import Any, List, Dict, Type
from runtime.executors.base import BaseExecutor, ExecutorError
from core.ast_nodes import ThreadNode


class ThreadExecutor(BaseExecutor):
    """
    Executor for q:thread statements.

    Supports:
    - Async thread execution
    - Thread join (wait for completion)
    - Thread termination
    - Priority levels
    - Timeout and callbacks
    """

    @property
    def handles(self) -> List[Type]:
        return [ThreadNode]

    def execute(self, node: ThreadNode, exec_context) -> Any:
        """
        Execute thread management.

        Args:
            node: ThreadNode with thread configuration
            exec_context: Execution context

        Returns:
            Thread operation result dict
        """
        try:
            context = exec_context.get_all_variables()

            # Execute based on action
            if node.action == 'run':
                result = self._execute_run(node, context, exec_context)
            elif node.action == 'join':
                result = self._execute_join(node.name)
            elif node.action == 'terminate':
                result = self._execute_terminate(node.name)
            else:
                raise ExecutorError(f"Unknown thread action: {node.action}")

            # Store result
            exec_context.set_variable(f"{node.name}_thread", result, scope="component")

            return result

        except Exception as e:
            raise ExecutorError(f"Thread execution error: {e}")

    def _execute_run(self, node: ThreadNode, context: Dict[str, Any], exec_context) -> Dict:
        """Start a new thread."""
        # Build thread config
        config = {
            'name': node.name,
            'priority': node.priority,
            'timeout': node.timeout,
            'on_complete': node.on_complete,
            'on_error': node.on_error,
            'body': node.body,
            'runtime': self._runtime,
            'exec_context': exec_context,
            'context_snapshot': context.copy()
        }

        return self.services.threading.run(config)

    def _execute_join(self, name: str) -> Dict:
        """Wait for thread to complete."""
        return self.services.threading.join(name)

    def _execute_terminate(self, name: str) -> Dict:
        """Terminate a running thread."""
        return self.services.threading.terminate(name)
