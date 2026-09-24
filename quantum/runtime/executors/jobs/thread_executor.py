"""
Thread Executor - Execute q:thread statements

Handles async thread execution.
"""

import logging
from typing import Any, List, Dict, Type
from quantum.runtime.executors.base import BaseExecutor, ExecutorError
from quantum.core.ast_nodes import ThreadNode

logger = logging.getLogger(__name__)


def thread_info_to_dict(info) -> Dict[str, Any]:
    """Convert a ThreadInfo dataclass to a template-friendly dict."""
    def _iso(value):
        return value.isoformat() if hasattr(value, 'isoformat') else value

    return {
        'name': info.name,
        'priority': info.priority,
        'startedAt': _iso(info.started_at),
        'status': info.status,
        'timeout': info.timeout,
        'result': info.result,
        'error': info.error,
    }


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

        except ExecutorError:
            raise
        except Exception as e:
            raise ExecutorError(f"Thread execution error: {e}")

    @property
    def _thread_service(self):
        """The real threading service.

        There is no services.threading — threads live on the JobExecutor
        facade as services.job_executor.thread (a ThreadService).
        """
        return self.services.job_executor.thread

    def _execute_run(self, node: ThreadNode, context: Dict[str, Any], exec_context) -> Dict:
        """Start a new thread."""
        body = node.body
        # Snapshot the caller's variables: the thread runs after this
        # component's own execution has moved on.
        snapshot = dict(context)

        def run_thread_body():
            try:
                return self.run_body_in_child_context(body, snapshot)
            except Exception as exc:  # noqa: BLE001 - surfaced via ThreadInfo.error
                logger.error(f"Thread '{node.name}' failed: {exc}")
                raise

        info = self._thread_service.run_thread(
            name=node.name,
            callback=run_thread_body,
            priority=node.priority or 'normal',
            timeout=node.timeout,
        )

        return thread_info_to_dict(info)

    def _execute_join(self, name: str) -> Dict:
        """Wait for thread to complete."""
        result = self._thread_service.join_thread(name)
        info = self._thread_service.get_thread(name)
        joined = thread_info_to_dict(info) if info else {'name': name}
        joined['result'] = result
        return joined

    def _execute_terminate(self, name: str) -> Dict:
        """Terminate a running thread."""
        return {
            'name': name,
            'action': 'terminate',
            'success': self._thread_service.terminate_thread(name),
        }
