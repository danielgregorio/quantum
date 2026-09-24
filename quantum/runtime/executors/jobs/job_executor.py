"""
Job Executor - Execute q:job statements

Handles job queue operations.
"""

from typing import Any, List, Dict, Type
from quantum.runtime.executors.base import BaseExecutor, ExecutorError
from quantum.core.ast_nodes import JobNode


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

            # Store result with both naming conventions for compatibility
            exec_context.set_variable(f"dispatched_job_{node.name}", result, scope="component")
            exec_context.set_variable(f"job_{node.name}", result, scope="component")

            # Also store in runtime context if available
            if hasattr(self._runtime, 'context'):
                self._runtime.context[f"dispatched_job_{node.name}"] = result
                self._runtime.context[f"job_{node.name}"] = result

            return result

        except Exception as e:
            raise ExecutorError(f"Job execution error: {e}")

    def _execute_define(self, node: JobNode, context: Dict[str, Any], exec_context) -> Dict:
        """Define a job (register handler)."""
        name = node.name
        queue = node.queue

        # Get job_executor from runtime (same as legacy code)
        job_executor = self._runtime.job_executor

        # Create job handler that executes the job body
        def job_handler(params: Dict[str, Any]):
            from quantum.runtime.execution_context import ExecutionContext as EC
            child_context = EC()
            for param_name, param_value in params.items():
                child_context.set_variable(param_name, param_value, scope="component")

            # Execute job body statements
            for statement in node.body:
                self._runtime._execute_statement(statement, child_context)

        # Register handler with job queue
        job_executor.job_queue.register_handler(name, job_handler)

        # Start worker for the queue if not already running
        job_executor.job_queue.start_worker(queue)

        result = {
            'name': name,
            'action': 'define',
            'queue': queue,
            'success': True
        }

        return result

    def _execute_dispatch(self, node: JobNode, context: Dict[str, Any], exec_context) -> Dict:
        """Dispatch a job to the queue."""
        name = node.name

        # Get job_executor from runtime (same as legacy code)
        job_executor = self._runtime.job_executor

        # Build params from job params
        params = {}
        for param in node.params:
            param_value = getattr(param, 'default', None)
            if param.name in context:
                param_value = context[param.name]
            # If param has value attribute, resolve it
            if hasattr(param, 'value') and param.value:
                param_value = self.apply_databinding(param.value, context)
            params[param.name] = param_value

        # Dispatch job to queue
        job_id = job_executor.job_queue.dispatch(
            name=name,
            queue=node.queue,
            params=params,
            delay=node.delay,
            priority=node.priority,
            attempts=node.attempts,
            backoff=node.backoff
        )

        result = {
            'job_id': job_id,
            'name': name,
            'action': 'dispatch',
            'queue': node.queue,
            'status': 'queued',
            'success': True
        }

        return result

    def _execute_batch(self, node: JobNode, context: Dict[str, Any], exec_context) -> Dict:
        """Dispatch multiple jobs as a batch."""
        name = node.name

        # Get job_executor from runtime (same as legacy code)
        job_executor = self._runtime.job_executor

        # Get tasks from node
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

        # Dispatch batch
        job_ids = []
        for task in resolved_tasks:
            job_id = job_executor.job_queue.dispatch(
                name=name,
                queue=node.queue,
                params=task,
                priority=node.priority
            )
            job_ids.append(job_id)

        result = {
            'job_ids': job_ids,
            'name': name,
            'action': 'batch',
            'queue': node.queue,
            'count': len(job_ids),
            'success': True
        }

        return result

    def _param_to_dict(self, param) -> Dict:
        """Convert param node to dict."""
        return {
            'name': param.name,
            'type': getattr(param, 'type', 'string'),
            'required': getattr(param, 'required', False),
            'default': getattr(param, 'default', None)
        }
