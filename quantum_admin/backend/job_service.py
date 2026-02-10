"""
Job Management Service for Quantum Admin
Provides admin interface for managing Quantum jobs, schedules, and queues
"""
import os
import sys
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import asdict

logger = logging.getLogger(__name__)

# Add quantum src to path
QUANTUM_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(QUANTUM_ROOT, 'src'))

try:
    from runtime.job_executor import JobExecutor, JobQueueService, ScheduleService, ThreadService
    HAS_JOB_EXECUTOR = True
except ImportError as e:
    logger.warning(f"JobExecutor not available: {e}")
    HAS_JOB_EXECUTOR = False
    JobExecutor = None


class JobAdminService:
    """
    Admin service for managing Quantum jobs.

    Provides:
    - Job queue management
    - Schedule management
    - Thread monitoring
    - Queue statistics
    """

    def __init__(self, job_db_path: str = "quantum_jobs.db"):
        """
        Initialize job admin service.

        Args:
            job_db_path: Path to job queue database
        """
        self._executor: Optional[JobExecutor] = None
        self._job_db_path = job_db_path

    @property
    def executor(self) -> Optional[JobExecutor]:
        """Get or create job executor instance."""
        if not HAS_JOB_EXECUTOR:
            return None

        if self._executor is None:
            self._executor = JobExecutor(job_db_path=self._job_db_path)
        return self._executor

    def is_available(self) -> bool:
        """Check if job system is available."""
        return HAS_JOB_EXECUTOR

    # =========================================================================
    # Jobs (Queued)
    # =========================================================================

    def list_jobs(
        self,
        queue: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        List all queued jobs.

        Args:
            queue: Filter by queue name
            status: Filter by status (pending, running, completed, failed)
            limit: Maximum jobs to return

        Returns:
            List of job dicts
        """
        if not self.executor:
            return []

        jobs = self.executor.job_queue.list_jobs(queue=queue, status=status, limit=limit)
        return [self._job_to_dict(job) for job in jobs]

    def get_job(self, job_id: int) -> Optional[Dict]:
        """Get job details by ID."""
        if not self.executor:
            return None

        job = self.executor.job_queue.get_job(job_id)
        return self._job_to_dict(job) if job else None

    def cancel_job(self, job_id: int) -> bool:
        """Cancel a pending job."""
        if not self.executor:
            return False
        return self.executor.job_queue.cancel_job(job_id)

    def retry_job(self, job_id: int) -> bool:
        """Retry a failed job."""
        if not self.executor:
            return False
        return self.executor.job_queue.retry_job(job_id)

    def dispatch_job(
        self,
        name: str,
        queue: str = 'default',
        params: Optional[Dict] = None,
        delay: Optional[str] = None,
        priority: int = 0
    ) -> Optional[int]:
        """
        Dispatch a new job.

        Args:
            name: Job name
            queue: Queue name
            params: Job parameters
            delay: Delay before execution
            priority: Job priority (0-10)

        Returns:
            Job ID or None
        """
        if not self.executor:
            return None

        return self.executor.job_queue.dispatch(
            name=name,
            queue=queue,
            params=params,
            delay=delay,
            priority=priority
        )

    def _job_to_dict(self, job) -> Dict:
        """Convert JobInfo to dict."""
        if not job:
            return {}
        return {
            'id': job.id,
            'name': job.name,
            'queue': job.queue,
            'params': job.params,
            'status': job.status,
            'attempts': job.attempts,
            'max_attempts': job.max_attempts,
            'scheduled_at': job.scheduled_at.isoformat() if job.scheduled_at else None,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            'error': job.error,
            'created_at': job.created_at.isoformat() if job.created_at else None
        }

    # =========================================================================
    # Schedules
    # =========================================================================

    def list_schedules(self) -> List[Dict]:
        """List all scheduled tasks."""
        if not self.executor:
            return []

        schedules = self.executor.schedule.list_schedules()
        return [self._schedule_to_dict(s) for s in schedules]

    def get_schedule(self, name: str) -> Optional[Dict]:
        """Get schedule details by name."""
        if not self.executor:
            return None

        schedule = self.executor.schedule.get_schedule(name)
        return self._schedule_to_dict(schedule) if schedule else None

    def pause_schedule(self, name: str) -> bool:
        """Pause a scheduled task."""
        if not self.executor:
            return False
        return self.executor.schedule.pause_schedule(name)

    def resume_schedule(self, name: str) -> bool:
        """Resume a paused schedule."""
        if not self.executor:
            return False
        return self.executor.schedule.resume_schedule(name)

    def run_schedule_now(self, name: str) -> bool:
        """Trigger immediate execution of a schedule."""
        if not self.executor:
            return False
        return self.executor.schedule.run_now(name)

    def remove_schedule(self, name: str) -> bool:
        """Remove a scheduled task."""
        if not self.executor:
            return False
        return self.executor.schedule.remove_schedule(name)

    def _schedule_to_dict(self, schedule) -> Dict:
        """Convert ScheduleInfo to dict."""
        if not schedule:
            return {}
        return {
            'name': schedule.name,
            'trigger_type': schedule.trigger_type,
            'trigger_info': schedule.trigger_info,
            'next_run': schedule.next_run.isoformat() if schedule.next_run else None,
            'enabled': schedule.enabled,
            'run_count': schedule.run_count,
            'last_run': schedule.last_run.isoformat() if schedule.last_run else None,
            'last_error': schedule.last_error
        }

    # =========================================================================
    # Threads
    # =========================================================================

    def list_threads(self, status: Optional[str] = None) -> List[Dict]:
        """List all threads."""
        if not self.executor:
            return []

        threads = self.executor.thread.list_threads(status=status)
        return [self._thread_to_dict(t) for t in threads]

    def get_thread(self, name: str) -> Optional[Dict]:
        """Get thread details by name."""
        if not self.executor:
            return None

        thread = self.executor.thread.get_thread(name)
        return self._thread_to_dict(thread) if thread else None

    def terminate_thread(self, name: str) -> bool:
        """Request thread termination."""
        if not self.executor:
            return False
        return self.executor.thread.terminate_thread(name)

    def _thread_to_dict(self, thread) -> Dict:
        """Convert ThreadInfo to dict."""
        if not thread:
            return {}
        return {
            'name': thread.name,
            'priority': thread.priority,
            'started_at': thread.started_at.isoformat() if thread.started_at else None,
            'status': thread.status,
            'timeout': thread.timeout,
            'error': thread.error
        }

    # =========================================================================
    # Queues
    # =========================================================================

    def list_queues(self) -> List[Dict]:
        """List all queues with stats."""
        if not self.executor:
            return [{'name': 'default', 'pending': 0, 'running': 0, 'completed': 0, 'failed': 0}]
        return self.executor.list_queues()

    def get_queue_stats(self, queue: str = 'default') -> Dict:
        """Get queue statistics."""
        if not self.executor:
            return {'pending': 0, 'running': 0, 'completed': 0, 'failed': 0}
        return self.executor.job_queue.get_queue_stats(queue)

    def purge_queue(self, queue: str, status: Optional[str] = None) -> int:
        """Purge jobs from a queue."""
        if not self.executor:
            return 0
        return self.executor.job_queue.purge_queue(queue, status=status)

    # =========================================================================
    # Overview
    # =========================================================================

    def get_overview(self) -> Dict:
        """
        Get job system overview.

        Returns:
            Dict with counts and status
        """
        if not self.executor:
            return {
                'available': False,
                'message': 'Job executor not available'
            }

        # Get queue stats
        queue_stats = self.get_queue_stats()

        # Get schedule count
        schedules = self.list_schedules()
        active_schedules = len([s for s in schedules if s.get('enabled')])

        # Get thread count
        threads = self.list_threads()
        running_threads = len([t for t in threads if t.get('status') == 'running'])

        return {
            'available': True,
            'jobs': {
                'pending': queue_stats.get('pending', 0),
                'running': queue_stats.get('running', 0),
                'completed': queue_stats.get('completed', 0),
                'failed': queue_stats.get('failed', 0),
                'total': sum(queue_stats.values())
            },
            'schedules': {
                'total': len(schedules),
                'active': active_schedules,
                'paused': len(schedules) - active_schedules
            },
            'threads': {
                'total': len(threads),
                'running': running_threads
            },
            'queues': self.list_queues()
        }


# Singleton instance
_job_service: Optional[JobAdminService] = None


def get_job_service() -> JobAdminService:
    """Get job service singleton."""
    global _job_service
    if _job_service is None:
        _job_service = JobAdminService()
    return _job_service
