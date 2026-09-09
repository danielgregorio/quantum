"""
Schedule Executor - Execute q:schedule statements

Handles scheduled task execution (cron-like).
"""

import logging
from typing import Any, List, Dict, Type
from quantum.runtime.executors.base import BaseExecutor, ExecutorError
from quantum.core.ast_nodes import ScheduleNode

logger = logging.getLogger(__name__)


def schedule_info_to_dict(info) -> Dict[str, Any]:
    """Convert a ScheduleInfo dataclass to a template-friendly dict."""
    def _iso(value):
        return value.isoformat() if hasattr(value, 'isoformat') else value

    return {
        'name': info.name,
        'triggerType': info.trigger_type,
        'triggerInfo': info.trigger_info,
        'nextRun': _iso(info.next_run),
        'enabled': info.enabled,
        'runCount': info.run_count,
        'lastRun': _iso(info.last_run),
        'lastError': info.last_error,
    }


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

        except ExecutorError:
            raise
        except Exception as e:
            raise ExecutorError(f"Schedule execution error: {e}")

    @property
    def _schedule_service(self):
        """The real scheduling service.

        There is no services.scheduler — schedules live on the JobExecutor
        facade as services.job_executor.schedule (a ScheduleService).
        """
        return self.services.job_executor.schedule

    def _execute_run(self, node: ScheduleNode, context: Dict[str, Any], exec_context) -> Dict:
        """Create/update a scheduled task."""
        interval = self.apply_databinding(node.interval, context) if node.interval else None
        cron = self.apply_databinding(node.cron, context) if node.cron else None
        at = self.apply_databinding(node.at, context) if node.at else None

        body = node.body

        def run_scheduled_body():
            """Runs on the scheduler thread — must not raise into APScheduler."""
            try:
                return self.run_body_in_child_context(body)
            except Exception as exc:  # noqa: BLE001 - reported via ScheduleInfo.last_error
                logger.error(f"Scheduled task '{node.name}' failed: {exc}")
                raise

        info = self._schedule_service.add_schedule(
            name=node.name,
            callback=run_scheduled_body,
            interval=interval,
            cron=cron,
            at=at,
            timezone=node.timezone or 'UTC',
            enabled=node.enabled,
            overlap=node.overlap,
        )

        return schedule_info_to_dict(info)

    def _execute_pause(self, name: str) -> Dict:
        """Pause a scheduled task."""
        return {'name': name, 'action': 'pause', 'success': self._schedule_service.pause_schedule(name)}

    def _execute_resume(self, name: str) -> Dict:
        """Resume a paused scheduled task."""
        return {'name': name, 'action': 'resume', 'success': self._schedule_service.resume_schedule(name)}

    def _execute_delete(self, name: str) -> Dict:
        """Delete a scheduled task."""
        return {'name': name, 'action': 'delete', 'success': self._schedule_service.remove_schedule(name)}
