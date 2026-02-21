"""
Queue Executor - Execute q:queue statements

Handles queue/exchange management operations.
"""

from typing import Any, List, Dict, Type
from runtime.executors.base import BaseExecutor, ExecutorError
from core.ast_nodes import QueueNode


class QueueExecutor(BaseExecutor):
    """
    Executor for q:queue statements.

    Supports:
    - Queue declaration
    - Queue purge
    - Queue deletion
    - Queue info retrieval
    - Dead letter queue configuration
    """

    @property
    def handles(self) -> List[Type]:
        return [QueueNode]

    def execute(self, node: QueueNode, exec_context) -> Any:
        """
        Execute queue management operation.

        Args:
            node: QueueNode with queue configuration
            exec_context: Execution context

        Returns:
            Queue operation result dict
        """
        try:
            context = exec_context.get_all_variables()

            # Resolve queue name
            queue_name = self.apply_databinding(node.name, context)

            # Execute based on action
            if node.action == 'declare':
                result = self._execute_declare(node, queue_name, context)
            elif node.action == 'purge':
                result = self._execute_purge(queue_name)
            elif node.action == 'delete':
                result = self._execute_delete(queue_name)
            elif node.action == 'info':
                result = self._execute_info(queue_name)
            else:
                raise ExecutorError(f"Unknown queue action: {node.action}")

            # Store result
            result_var = node.result if hasattr(node, 'result') and node.result else f"{queue_name}_result"
            exec_context.set_variable(result_var, result, scope="component")

            return result

        except Exception as e:
            raise ExecutorError(f"Queue operation error: {e}")

    def _execute_declare(self, node: QueueNode, queue_name: str, context: Dict[str, Any]) -> Dict:
        """Declare a queue with configuration."""
        # Build queue options
        options = {
            'durable': getattr(node, 'durable', True),
            'exclusive': getattr(node, 'exclusive', False),
            'auto_delete': getattr(node, 'auto_delete', False)
        }

        # Dead letter queue
        if hasattr(node, 'dead_letter') and node.dead_letter:
            dlq = self.apply_databinding(node.dead_letter, context)
            options['dead_letter_queue'] = dlq

        # TTL
        if hasattr(node, 'ttl') and node.ttl:
            options['ttl'] = int(node.ttl)

        # Max length
        if hasattr(node, 'max_length') and node.max_length:
            options['max_length'] = int(node.max_length)

        return self.services.messaging.declare_queue(
            name=queue_name,
            **options
        )

    def _execute_purge(self, queue_name: str) -> Dict:
        """Purge all messages from a queue."""
        return self.services.messaging.purge_queue(queue_name)

    def _execute_delete(self, queue_name: str) -> Dict:
        """Delete a queue."""
        return self.services.messaging.delete_queue(queue_name)

    def _execute_info(self, queue_name: str) -> Dict:
        """Get queue information."""
        return self.services.messaging.queue_info(queue_name)
