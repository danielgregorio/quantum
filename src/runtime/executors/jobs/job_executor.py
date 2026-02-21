"""
Job Executor - Execute q:job statements

Handles job queue operations.
"""

from typing import Any, List, Dict, Type
from runtime.executors.base import BaseExecutor, ExecutorError
from core.ast_nodes import JobNode


class JobExecutor(BaseExecutor):
    """
    Executor for q:job statements.

    Supports:
    - Job definition
    - Job dispatch (enqueue)
    - Batch job dispatch
    - Priority and delay
    - Retry with backoff
    """

    @property
    def handles(self) -> List[Type]:
        return [JobNode]

    def execute(self, node: JobNode, exec_context) -> Any:
        """
        Execute job management.

        Args:
            node: JobNode with job configuration
            exec_context: Execution context

        Returns:
            Job operation result dict
        """
        try:
            context = exec_context.get_all_variables()

            # Execute based on action
            if node.action == 'define':
                result = self._execute_define(node, context, exec_context)
            elif node.action == 'dispatch':
                result = self._execute_dispatch(node, context, exec_context)
            elif node.action == 'batch':
                result = self._execute_batch(node, context, exec_context)
            else:
                raise ExecutorError(f"Unknown job action: {node.action}")

            # Store result
            exec_context.set_variable(f"{node.name}_job", result, scope="component")

            return result

        except Exception as e:
            raise ExecutorError(f"Job execution error: {e}")

    def _execute_define(self, node: JobNode, context: Dict[str, Any], exec_context) -> Dict:
        """Define a job (register handler)."""
        # Build job definition
        config = {
            'name': node.name,
            'queue': node.queue,
            'params': [self._param_to_dict(p) for p in node.params],
            'body': node.body,
            'attempts': node.attempts,
            'backoff': node.backoff,
            'timeout': node.timeout,
            'runtime': self._runtime,
            'exec_context': exec_context
        }

        return self.services.jobs.define(config)

    def _execute_dispatch(self, node: JobNode, context: Dict[str, Any], exec_context) -> Dict:
        """Dispatch a job to the queue."""
        # Resolve parameters
        params = {}
        for param in node.params:
            if hasattr(param, 'value') and param.value:
                params[param.name] = self.apply_databinding(param.value, context)

        # Build dispatch options
        options = {
            'delay': node.delay,
            'priority': node.priority,
            'attempts': node.attempts,
            'backoff': node.backoff,
            'timeout': node.timeout
        }

        return self.services.jobs.dispatch(
            name=node.name,
            queue=node.queue,
            params=params,
            **options
        )

    def _execute_batch(self, node: JobNode, context: Dict[str, Any], exec_context) -> Dict:
        """Dispatch multiple jobs as a batch."""
        # Get tasks from legacy format or params
        tasks = node.tasks if node.tasks else []

        # Resolve tasks
        resolved_tasks = []
        for task in tasks:
            resolved_task = {}
            for key, value in task.items():
                if isinstance(value, str):
                    resolved_task[key] = self.apply_databinding(value, context)
                else:
                    resolved_task[key] = value
            resolved_tasks.append(resolved_task)

        return self.services.jobs.batch(
            name=node.name,
            queue=node.queue,
            tasks=resolved_tasks,
            priority=node.priority
        )

    def _param_to_dict(self, param) -> Dict:
        """Convert param node to dict."""
        return {
            'name': param.name,
            'type': getattr(param, 'type', 'string'),
            'required': getattr(param, 'required', False),
            'default': getattr(param, 'default', None)
        }
