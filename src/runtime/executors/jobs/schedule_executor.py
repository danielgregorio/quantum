"""
Schedule Executor - Execute q:schedule statements

Handles scheduled task execution (cron-like).
"""

from typing import Any, List, Dict, Type
from runtime.executors.base import BaseExecutor, ExecutorError
from core.ast_nodes import ScheduleNode


class ScheduleExecutor(BaseExecutor):
    """
    Executor for q:schedule statements.

    Supports:
    - Interval-based scheduling (30s, 5m, 1h, 1d)
    - Cron expression scheduling
    - One-time scheduled execution
    - Timezone support
    - Retry configuration
    """

    @property
    def handles(self) -> List[Type]:
        return [ScheduleNode]

    def execute(self, node: ScheduleNode, exec_context) -> Any:
        """
        Execute schedule management.

        Args:
            node: ScheduleNode with schedule configuration
            exec_context: Execution context

        Returns:
            Schedule operation result dict
        """
        try:
            context = exec_context.get_all_variables()

            # Execute based on action
            if node.action == 'run':
                result = self._execute_run(node, context, exec_context)
            elif node.action == 'pause':
                result = self._execute_pause(node.name)
            elif node.action == 'resume':
                result = self._execute_resume(node.name)
            elif node.action == 'delete':
                result = self._execute_delete(node.name)
            else:
                raise ExecutorError(f"Unknown schedule action: {node.action}")

            # Store result
            exec_context.set_variable(f"{node.name}_schedule", result, scope="component")

            return result

        except Exception as e:
            raise ExecutorError(f"Schedule execution error: {e}")

    def _execute_run(self, node: ScheduleNode, context: Dict[str, Any], exec_context) -> Dict:
        """Create/update a scheduled task."""
        # Resolve trigger
        interval = None
        if node.interval:
            interval = self.apply_databinding(node.interval, context)

        cron = None
        if node.cron:
            cron = self.apply_databinding(node.cron, context)

        at = None
        if node.at:
            at = self.apply_databinding(node.at, context)

        # Build schedule config
        config = {
            'name': node.name,
            'interval': interval,
            'cron': cron,
            'at': at,
            'timezone': node.timezone,
            'retry': node.retry,
            'timeout': node.timeout,
            'overlap': node.overlap,
            'enabled': node.enabled,
            'body': node.body,
            'runtime': self._runtime,
            'exec_context': exec_context
        }

        return self.services.scheduler.schedule(config)

    def _execute_pause(self, name: str) -> Dict:
        """Pause a scheduled task."""
        return self.services.scheduler.pause(name)

    def _execute_resume(self, name: str) -> Dict:
        """Resume a paused scheduled task."""
        return self.services.scheduler.resume(name)

    def _execute_delete(self, name: str) -> Dict:
        """Delete a scheduled task."""
        return self.services.scheduler.delete(name)
