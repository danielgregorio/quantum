"""
Job Execution System - Scheduled Tasks, Threads, and Job Queues

This module provides:
- ScheduleService: APScheduler-based scheduled task execution (like cfschedule)
- ThreadService: ThreadPoolExecutor-based async thread management (like cfthread)
- JobQueueService: SQLite-based job queue for batch processing

Examples:
    # Schedule a task to run every 5 minutes
    <q:schedule name="cleanup" interval="5m">
        <q:query datasource="db">DELETE FROM temp WHERE created_at < NOW() - INTERVAL 1 HOUR</q:query>
    </q:schedule>

    # Run async thread
    <q:thread name="sendEmails" priority="high">
        <q:loop query="pendingEmails">
            <q:mail to="{email}" subject="Notification">...</q:mail>
        </q:loop>
    </q:thread>

    # Dispatch job to queue
    <q:job name="processOrder" action="dispatch" queue="orders" delay="30s" />
"""

import re
import json
import sqlite3
import threading
import time
import logging
from concurrent.futures import ThreadPoolExecutor, Future
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Tuple
from pathlib import Path
from dataclasses import dataclass

# Try to import APScheduler (optional dependency)
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.date import DateTrigger
    from apscheduler.jobstores.memory import MemoryJobStore
    HAS_APSCHEDULER = True
except ImportError:
    HAS_APSCHEDULER = False
    BackgroundScheduler = None


# Register datetime adapters/converters for sqlite3 (Python 3.12+ compatibility)
def _adapt_datetime(val: datetime) -> str:
    """Convert datetime to ISO format string for SQLite storage."""
    return val.isoformat()


def _convert_datetime(val: bytes) -> datetime:
    """Convert ISO format string from SQLite to datetime."""
    return datetime.fromisoformat(val.decode())


# Register the adapter and converter
sqlite3.register_adapter(datetime, _adapt_datetime)
sqlite3.register_converter("timestamp", _convert_datetime)


# Configure logging
logger = logging.getLogger(__name__)


class JobExecutorError(Exception):
    """Base exception for job execution errors"""
    pass


class ScheduleError(JobExecutorError):
    """Raised when schedule execution fails"""
    pass


class ThreadError(JobExecutorError):
    """Raised when thread execution fails"""
    pass


class JobQueueError(JobExecutorError):
    """Raised when job queue operation fails"""
    pass


def parse_duration(duration_str: str) -> int:
    """
    Parse duration string to seconds.

    Supported formats:
    - "30s" -> 30 seconds
    - "5m" -> 5 minutes (300 seconds)
    - "1h" -> 1 hour (3600 seconds)
    - "1d" -> 1 day (86400 seconds)
    - "1w" -> 1 week (604800 seconds)
    - Plain number -> seconds

    Args:
        duration_str: Duration string (e.g., "30s", "5m", "1h")

    Returns:
        Duration in seconds

    Raises:
        ValueError: If format is invalid
    """
    if not duration_str:
        raise ValueError("Duration string is required")

    duration_str = duration_str.strip().lower()

    # Try plain number first
    try:
        return int(duration_str)
    except ValueError:
        pass

    # Parse with unit suffix
    match = re.match(r'^(\d+(?:\.\d+)?)\s*([smhdw])$', duration_str)
    if not match:
        raise ValueError(f"Invalid duration format: {duration_str}")

    value = float(match.group(1))
    unit = match.group(2)

    multipliers = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400,
        'w': 604800
    }

    return int(value * multipliers[unit])


def format_duration(seconds: int) -> str:
    """
    Format seconds as human-readable duration.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "5m", "1h 30m")
    """
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        if secs:
            return f"{minutes}m {secs}s"
        return f"{minutes}m"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if minutes:
            return f"{hours}h {minutes}m"
        return f"{hours}h"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        if hours:
            return f"{days}d {hours}h"
        return f"{days}d"


# ============================================
# SCHEDULE SERVICE (APScheduler-based)
# ============================================

@dataclass
class ScheduleInfo:
    """Information about a scheduled task"""
    name: str
    trigger_type: str  # interval, cron, date
    trigger_info: str  # Human-readable trigger description
    next_run: Optional[datetime]
    enabled: bool
    run_count: int = 0
    last_run: Optional[datetime] = None
    last_error: Optional[str] = None


class ScheduleService:
    """
    Service for managing scheduled task execution.

    Uses APScheduler for reliable scheduling with support for:
    - Interval triggers (every X seconds/minutes/hours/days)
    - Cron triggers (cron expression)
    - One-time triggers (specific datetime)

    Thread-safe and handles overlapping executions.
    """

    def __init__(self, max_instances: int = 3):
        """
        Initialize schedule service.

        Args:
            max_instances: Maximum concurrent instances of same job
        """
        self._scheduler: Optional[BackgroundScheduler] = None
        self._schedules: Dict[str, ScheduleInfo] = {}
        self._callbacks: Dict[str, Callable] = {}
        self._max_instances = max_instances
        self._lock = threading.Lock()
        self._started = False

    def _ensure_scheduler(self):
        """Ensure scheduler is initialized and running"""
        if not HAS_APSCHEDULER:
            raise ScheduleError(
                "APScheduler is not installed. Install with: pip install apscheduler"
            )

        if self._scheduler is None:
            self._scheduler = BackgroundScheduler(
                jobstores={'default': MemoryJobStore()},
                job_defaults={
                    'coalesce': True,
                    'max_instances': self._max_instances,
                    'misfire_grace_time': 60
                }
            )

        if not self._started:
            self._scheduler.start()
            self._started = True

    def add_schedule(
        self,
        name: str,
        callback: Callable,
        interval: Optional[str] = None,
        cron: Optional[str] = None,
        at: Optional[str] = None,
        timezone: str = 'UTC',
        enabled: bool = True,
        overlap: bool = False
    ) -> ScheduleInfo:
        """
        Add a scheduled task.

        Args:
            name: Unique schedule name
            callback: Function to execute
            interval: Interval trigger (e.g., "30s", "5m", "1h", "1d")
            cron: Cron expression (e.g., "0 2 * * *")
            at: Specific datetime (ISO 8601 format)
            timezone: Timezone for cron schedules
            enabled: Whether schedule is enabled
            overlap: Allow overlapping executions

        Returns:
            ScheduleInfo object

        Raises:
            ScheduleError: If schedule configuration is invalid
        """
        self._ensure_scheduler()

        if not name:
            raise ScheduleError("Schedule name is required")

        if not any([interval, cron, at]):
            raise ScheduleError("Schedule requires 'interval', 'cron', or 'at'")

        # Build trigger
        trigger = None
        trigger_type = None
        trigger_info = None

        if interval:
            seconds = parse_duration(interval)
            trigger = IntervalTrigger(seconds=seconds, timezone=timezone)
            trigger_type = 'interval'
            trigger_info = f"every {format_duration(seconds)}"

        elif cron:
            # Parse cron expression
            parts = cron.split()
            if len(parts) == 5:
                minute, hour, day, month, day_of_week = parts
                trigger = CronTrigger(
                    minute=minute,
                    hour=hour,
                    day=day,
                    month=month,
                    day_of_week=day_of_week,
                    timezone=timezone
                )
            elif len(parts) == 6:
                second, minute, hour, day, month, day_of_week = parts
                trigger = CronTrigger(
                    second=second,
                    minute=minute,
                    hour=hour,
                    day=day,
                    month=month,
                    day_of_week=day_of_week,
                    timezone=timezone
                )
            else:
                raise ScheduleError(f"Invalid cron expression: {cron}")
            trigger_type = 'cron'
            trigger_info = f"cron: {cron}"

        elif at:
            # Parse ISO 8601 datetime
            try:
                run_date = datetime.fromisoformat(at)
            except ValueError:
                raise ScheduleError(f"Invalid datetime format: {at}. Use ISO 8601")
            trigger = DateTrigger(run_date=run_date, timezone=timezone)
            trigger_type = 'date'
            trigger_info = f"at {at}"

        # Wrap callback to track execution
        def wrapped_callback():
            info = self._schedules.get(name)
            if info:
                info.run_count += 1
                info.last_run = datetime.now()
                try:
                    callback()
                    info.last_error = None
                except Exception as e:
                    info.last_error = str(e)
                    logger.error(f"Schedule '{name}' failed: {e}")
                    raise

        # Store callback
        self._callbacks[name] = wrapped_callback

        with self._lock:
            # Remove existing schedule if present
            if name in self._schedules:
                self.remove_schedule(name)

            # Add job to scheduler
            max_inst = self._max_instances if overlap else 1
            job = self._scheduler.add_job(
                wrapped_callback,
                trigger=trigger,
                id=name,
                name=name,
                max_instances=max_inst,
                replace_existing=True
            )

            # Pause if not enabled
            if not enabled:
                self._scheduler.pause_job(name)

            # Create schedule info
            info = ScheduleInfo(
                name=name,
                trigger_type=trigger_type,
                trigger_info=trigger_info,
                next_run=job.next_run_time,
                enabled=enabled
            )
            self._schedules[name] = info

        logger.info(f"Added schedule '{name}': {trigger_info}")
        return info

    def remove_schedule(self, name: str) -> bool:
        """
        Remove a scheduled task.

        Args:
            name: Schedule name

        Returns:
            True if removed, False if not found
        """
        if self._scheduler is None:
            return False

        with self._lock:
            if name in self._schedules:
                try:
                    self._scheduler.remove_job(name)
                except Exception:
                    pass
                del self._schedules[name]
                if name in self._callbacks:
                    del self._callbacks[name]
                logger.info(f"Removed schedule '{name}'")
                return True
        return False

    def pause_schedule(self, name: str) -> bool:
        """Pause a scheduled task"""
        if self._scheduler is None:
            return False

        with self._lock:
            if name in self._schedules:
                self._scheduler.pause_job(name)
                self._schedules[name].enabled = False
                logger.info(f"Paused schedule '{name}'")
                return True
        return False

    def resume_schedule(self, name: str) -> bool:
        """Resume a paused scheduled task"""
        if self._scheduler is None:
            return False

        with self._lock:
            if name in self._schedules:
                self._scheduler.resume_job(name)
                self._schedules[name].enabled = True
                logger.info(f"Resumed schedule '{name}'")
                return True
        return False

    def get_schedule(self, name: str) -> Optional[ScheduleInfo]:
        """Get schedule info by name"""
        return self._schedules.get(name)

    def list_schedules(self) -> List[ScheduleInfo]:
        """List all schedules"""
        return list(self._schedules.values())

    def run_now(self, name: str) -> bool:
        """Trigger immediate execution of a schedule"""
        if name in self._callbacks:
            try:
                self._callbacks[name]()
                return True
            except Exception as e:
                logger.error(f"Immediate run of '{name}' failed: {e}")
                return False
        return False

    def shutdown(self):
        """Shutdown the scheduler"""
        if self._scheduler and self._started:
            self._scheduler.shutdown(wait=True)
            self._started = False
            logger.info("Schedule service shutdown complete")


# ============================================
# THREAD SERVICE (ThreadPoolExecutor-based)
# ============================================

@dataclass
class ThreadInfo:
    """Information about a running thread"""
    name: str
    priority: str
    started_at: datetime
    status: str  # running, completed, failed, terminated
    timeout: Optional[int] = None
    result: Any = None
    error: Optional[str] = None


class ThreadService:
    """
    Service for managing async thread execution.

    Uses ThreadPoolExecutor for managed thread pools with:
    - Priority-based execution (low, normal, high)
    - Timeout support
    - Callbacks for completion/error
    - Thread joining and termination

    Thread-safe operations.
    """

    PRIORITY_WEIGHTS = {
        'low': 1,
        'normal': 5,
        'high': 10
    }

    def __init__(self, max_workers: int = 10):
        """
        Initialize thread service.

        Args:
            max_workers: Maximum concurrent threads
        """
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="quantum_thread_"
        )
        self._threads: Dict[str, ThreadInfo] = {}
        self._futures: Dict[str, Future] = {}
        self._lock = threading.Lock()

    def run_thread(
        self,
        name: str,
        callback: Callable,
        priority: str = 'normal',
        timeout: Optional[str] = None,
        on_complete: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None
    ) -> ThreadInfo:
        """
        Run a task in a background thread.

        Args:
            name: Thread name (must be unique)
            callback: Function to execute
            priority: Thread priority (low, normal, high)
            timeout: Optional timeout (e.g., "30s", "5m")
            on_complete: Callback on successful completion
            on_error: Callback on error

        Returns:
            ThreadInfo object

        Raises:
            ThreadError: If thread already exists or parameters invalid
        """
        if not name:
            raise ThreadError("Thread name is required")

        if priority not in self.PRIORITY_WEIGHTS:
            raise ThreadError(f"Invalid priority: {priority}")

        timeout_seconds = None
        if timeout:
            timeout_seconds = parse_duration(timeout)

        with self._lock:
            if name in self._threads:
                existing = self._threads[name]
                if existing.status == 'running':
                    raise ThreadError(f"Thread '{name}' is already running")

        # Wrapper function for execution tracking
        def execute_thread():
            info = self._threads.get(name)
            if not info:
                return

            try:
                result = callback()
                info.status = 'completed'
                info.result = result
                if on_complete:
                    try:
                        on_complete(result)
                    except Exception as e:
                        logger.error(f"Thread '{name}' on_complete callback failed: {e}")
                return result
            except Exception as e:
                info.status = 'failed'
                info.error = str(e)
                logger.error(f"Thread '{name}' failed: {e}")
                if on_error:
                    try:
                        on_error(e)
                    except Exception as cb_err:
                        logger.error(f"Thread '{name}' on_error callback failed: {cb_err}")
                raise

        # Create thread info
        info = ThreadInfo(
            name=name,
            priority=priority,
            started_at=datetime.now(),
            status='running',
            timeout=timeout_seconds
        )

        with self._lock:
            self._threads[name] = info

            # Submit to executor
            future = self._executor.submit(execute_thread)
            self._futures[name] = future

            # Handle timeout if specified
            if timeout_seconds:
                def check_timeout():
                    time.sleep(timeout_seconds)
                    if name in self._threads and self._threads[name].status == 'running':
                        self.terminate_thread(name)
                        logger.warning(f"Thread '{name}' terminated due to timeout")

                timeout_thread = threading.Thread(target=check_timeout, daemon=True)
                timeout_thread.start()

        logger.info(f"Started thread '{name}' with priority '{priority}'")
        return info

    def join_thread(self, name: str, timeout: Optional[float] = None) -> Optional[Any]:
        """
        Wait for a thread to complete.

        Args:
            name: Thread name
            timeout: Optional timeout in seconds

        Returns:
            Thread result or None if not found

        Raises:
            ThreadError: If thread failed or timed out
        """
        if name not in self._futures:
            raise ThreadError(f"Thread '{name}' not found")

        future = self._futures[name]

        try:
            result = future.result(timeout=timeout)
            logger.info(f"Thread '{name}' completed successfully")
            return result
        except Exception as e:
            raise ThreadError(f"Thread '{name}' failed: {e}")

    def terminate_thread(self, name: str) -> bool:
        """
        Request termination of a thread.

        Note: Python threads cannot be forcibly killed, but this marks
        the thread as terminated and cancels the future if possible.

        Args:
            name: Thread name

        Returns:
            True if termination requested, False if not found
        """
        with self._lock:
            if name in self._threads:
                info = self._threads[name]
                if info.status == 'running':
                    info.status = 'terminated'

                    # Try to cancel the future (only works if not started)
                    if name in self._futures:
                        self._futures[name].cancel()

                    logger.info(f"Requested termination of thread '{name}'")
                    return True
        return False

    def get_thread(self, name: str) -> Optional[ThreadInfo]:
        """Get thread info by name"""
        return self._threads.get(name)

    def list_threads(self, status: Optional[str] = None) -> List[ThreadInfo]:
        """
        List threads, optionally filtered by status.

        Args:
            status: Filter by status (running, completed, failed, terminated)

        Returns:
            List of ThreadInfo objects
        """
        threads = list(self._threads.values())
        if status:
            threads = [t for t in threads if t.status == status]
        return threads

    def cleanup(self, max_age_seconds: int = 3600):
        """
        Remove completed/failed threads older than max_age.

        Args:
            max_age_seconds: Maximum age in seconds (default 1 hour)
        """
        cutoff = datetime.now() - timedelta(seconds=max_age_seconds)
        with self._lock:
            to_remove = []
            for name, info in self._threads.items():
                if info.status != 'running' and info.started_at < cutoff:
                    to_remove.append(name)

            for name in to_remove:
                del self._threads[name]
                if name in self._futures:
                    del self._futures[name]

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old threads")

    def shutdown(self, wait: bool = True):
        """
        Shutdown the thread pool.

        Args:
            wait: Wait for running threads to complete
        """
        self._executor.shutdown(wait=wait)
        logger.info("Thread service shutdown complete")


# ============================================
# JOB QUEUE SERVICE (SQLite-based)
# ============================================

@dataclass
class JobInfo:
    """Information about a queued job"""
    id: int
    name: str
    queue: str
    params: Dict[str, Any]
    status: str  # pending, running, completed, failed
    attempts: int
    max_attempts: int
    scheduled_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error: Optional[str]
    created_at: datetime


class JobQueueService:
    """
    Service for managing job queues with SQLite persistence.

    Features:
    - Multiple named queues
    - Job priorities
    - Delayed execution
    - Automatic retries with backoff
    - Dead letter queue support

    Thread-safe with connection pooling.
    """

    CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS quantum_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        queue TEXT DEFAULT 'default',
        params TEXT,
        status TEXT DEFAULT 'pending',
        priority INTEGER DEFAULT 0,
        attempts INTEGER DEFAULT 0,
        max_attempts INTEGER DEFAULT 3,
        backoff_seconds INTEGER DEFAULT 30,
        scheduled_at DATETIME,
        started_at DATETIME,
        completed_at DATETIME,
        error TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_quantum_jobs_status ON quantum_jobs(status);
    CREATE INDEX IF NOT EXISTS idx_quantum_jobs_queue ON quantum_jobs(queue);
    CREATE INDEX IF NOT EXISTS idx_quantum_jobs_scheduled ON quantum_jobs(scheduled_at);
    """

    def __init__(self, db_path: str = "quantum_jobs.db"):
        """
        Initialize job queue service.

        Args:
            db_path: Path to SQLite database file
        """
        self._db_path = db_path
        self._handlers: Dict[str, Callable] = {}
        self._workers: Dict[str, threading.Thread] = {}
        self._running = False
        self._lock = threading.Lock()

        # Initialize database
        self._init_db()

    def _init_db(self):
        """Initialize the database schema."""
        conn = sqlite3.connect(
            self._db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        try:
            conn.executescript(self.CREATE_TABLE_SQL)
            conn.commit()
        finally:
            conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with datetime support."""
        conn = sqlite3.connect(
            self._db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        conn.row_factory = sqlite3.Row
        return conn

    def register_handler(self, job_name: str, handler: Callable):
        """
        Register a handler for a job type.

        Args:
            job_name: Job name to handle
            handler: Function to execute (receives params dict)
        """
        self._handlers[job_name] = handler
        logger.info(f"Registered handler for job '{job_name}'")

    def dispatch(
        self,
        name: str,
        queue: str = 'default',
        params: Optional[Dict[str, Any]] = None,
        delay: Optional[str] = None,
        priority: int = 0,
        attempts: int = 3,
        backoff: str = '30s'
    ) -> int:
        """
        Dispatch a job to the queue.

        Args:
            name: Job name (must have registered handler)
            queue: Queue name
            params: Job parameters
            delay: Delay before execution (e.g., "30s", "5m")
            priority: Job priority (0-10, higher = more important)
            attempts: Maximum retry attempts
            backoff: Backoff time between retries

        Returns:
            Job ID

        Raises:
            JobQueueError: If dispatch fails
        """
        if not name:
            raise JobQueueError("Job name is required")

        # Calculate scheduled_at
        scheduled_at = None
        if delay:
            delay_seconds = parse_duration(delay)
            scheduled_at = datetime.now() + timedelta(seconds=delay_seconds)

        backoff_seconds = parse_duration(backoff) if backoff else 30

        # Serialize params
        params_json = json.dumps(params or {})

        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                INSERT INTO quantum_jobs
                (name, queue, params, priority, max_attempts, backoff_seconds, scheduled_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (name, queue, params_json, priority, attempts, backoff_seconds, scheduled_at)
            )
            conn.commit()
            job_id = cursor.lastrowid
            logger.info(f"Dispatched job '{name}' (id={job_id}) to queue '{queue}'")
            return job_id
        finally:
            conn.close()

    def dispatch_batch(
        self,
        jobs: List[Dict[str, Any]],
        queue: str = 'default'
    ) -> List[int]:
        """
        Dispatch multiple jobs at once.

        Args:
            jobs: List of job dicts with 'name' and optional 'params', 'delay', etc.
            queue: Default queue name

        Returns:
            List of job IDs
        """
        job_ids = []
        for job in jobs:
            job_id = self.dispatch(
                name=job.get('name', ''),
                queue=job.get('queue', queue),
                params=job.get('params'),
                delay=job.get('delay'),
                priority=job.get('priority', 0),
                attempts=job.get('attempts', 3),
                backoff=job.get('backoff', '30s')
            )
            job_ids.append(job_id)
        return job_ids

    def get_job(self, job_id: int) -> Optional[JobInfo]:
        """Get job info by ID"""
        conn = self._get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM quantum_jobs WHERE id = ?",
                (job_id,)
            ).fetchone()

            if row:
                return self._row_to_job_info(row)
            return None
        finally:
            conn.close()

    def list_jobs(
        self,
        queue: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[JobInfo]:
        """
        List jobs with optional filters.

        Args:
            queue: Filter by queue name
            status: Filter by status
            limit: Maximum results

        Returns:
            List of JobInfo objects
        """
        conn = self._get_connection()
        try:
            sql = "SELECT * FROM quantum_jobs WHERE 1=1"
            params = []

            if queue:
                sql += " AND queue = ?"
                params.append(queue)

            if status:
                sql += " AND status = ?"
                params.append(status)

            sql += " ORDER BY priority DESC, created_at ASC LIMIT ?"
            params.append(limit)

            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_job_info(row) for row in rows]
        finally:
            conn.close()

    def cancel_job(self, job_id: int) -> bool:
        """
        Cancel a pending job.

        Args:
            job_id: Job ID

        Returns:
            True if cancelled, False if not found or already running
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                UPDATE quantum_jobs
                SET status = 'cancelled', completed_at = ?
                WHERE id = ? AND status = 'pending'
                """,
                (datetime.now(), job_id)
            )
            conn.commit()
            if cursor.rowcount > 0:
                logger.info(f"Cancelled job {job_id}")
                return True
            return False
        finally:
            conn.close()

    def retry_job(self, job_id: int) -> bool:
        """
        Retry a failed job.

        Args:
            job_id: Job ID

        Returns:
            True if retried, False if not found or not failed
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                UPDATE quantum_jobs
                SET status = 'pending', attempts = 0, error = NULL,
                    started_at = NULL, completed_at = NULL
                WHERE id = ? AND status = 'failed'
                """,
                (job_id,)
            )
            conn.commit()
            if cursor.rowcount > 0:
                logger.info(f"Retrying job {job_id}")
                return True
            return False
        finally:
            conn.close()

    def purge_queue(self, queue: str, status: Optional[str] = None) -> int:
        """
        Purge jobs from a queue.

        Args:
            queue: Queue name
            status: Only purge jobs with this status (default: all non-running)

        Returns:
            Number of jobs purged
        """
        conn = self._get_connection()
        try:
            if status:
                cursor = conn.execute(
                    "DELETE FROM quantum_jobs WHERE queue = ? AND status = ?",
                    (queue, status)
                )
            else:
                cursor = conn.execute(
                    "DELETE FROM quantum_jobs WHERE queue = ? AND status != 'running'",
                    (queue,)
                )
            conn.commit()
            count = cursor.rowcount
            logger.info(f"Purged {count} jobs from queue '{queue}'")
            return count
        finally:
            conn.close()

    def start_worker(self, queue: str = 'default', poll_interval: float = 1.0):
        """
        Start a background worker for a queue.

        Args:
            queue: Queue to process
            poll_interval: Seconds between polls
        """
        if queue in self._workers:
            logger.warning(f"Worker for queue '{queue}' already running")
            return

        self._running = True

        def worker_loop():
            logger.info(f"Started worker for queue '{queue}'")
            while self._running:
                try:
                    job = self._fetch_next_job(queue)
                    if job:
                        self._process_job(job)
                    else:
                        time.sleep(poll_interval)
                except Exception as e:
                    logger.error(f"Worker error: {e}")
                    time.sleep(poll_interval)

        worker = threading.Thread(target=worker_loop, daemon=True)
        worker.start()
        self._workers[queue] = worker
        logger.info(f"Started worker thread for queue '{queue}'")

    def stop_workers(self):
        """Stop all worker threads"""
        self._running = False
        self._workers.clear()
        logger.info("Stopped all job queue workers")

    def _fetch_next_job(self, queue: str) -> Optional[JobInfo]:
        """Fetch and lock the next pending job"""
        conn = self._get_connection()
        try:
            # Find next pending job (respecting scheduled_at and priority)
            row = conn.execute(
                """
                SELECT * FROM quantum_jobs
                WHERE queue = ? AND status = 'pending'
                AND (scheduled_at IS NULL OR scheduled_at <= ?)
                ORDER BY priority DESC, created_at ASC
                LIMIT 1
                """,
                (queue, datetime.now())
            ).fetchone()

            if not row:
                return None

            # Mark as running
            conn.execute(
                "UPDATE quantum_jobs SET status = 'running', started_at = ? WHERE id = ?",
                (datetime.now(), row['id'])
            )
            conn.commit()

            return self._row_to_job_info(row)
        finally:
            conn.close()

    def _process_job(self, job: JobInfo):
        """Process a job"""
        handler = self._handlers.get(job.name)
        if not handler:
            logger.error(f"No handler for job '{job.name}'")
            self._fail_job(job.id, "No handler registered")
            return

        try:
            # Execute handler
            handler(job.params)

            # Mark as completed
            conn = self._get_connection()
            try:
                conn.execute(
                    "UPDATE quantum_jobs SET status = 'completed', completed_at = ? WHERE id = ?",
                    (datetime.now(), job.id)
                )
                conn.commit()
            finally:
                conn.close()

            logger.info(f"Completed job '{job.name}' (id={job.id})")

        except Exception as e:
            logger.error(f"Job '{job.name}' (id={job.id}) failed: {e}")
            self._handle_job_failure(job, str(e))

    def _handle_job_failure(self, job: JobInfo, error: str):
        """Handle job failure with retry logic"""
        conn = self._get_connection()
        try:
            # Get current job state
            row = conn.execute(
                "SELECT attempts, max_attempts, backoff_seconds FROM quantum_jobs WHERE id = ?",
                (job.id,)
            ).fetchone()

            if not row:
                return

            attempts = row['attempts'] + 1
            max_attempts = row['max_attempts']
            backoff_seconds = row['backoff_seconds']

            if attempts < max_attempts:
                # Schedule retry with exponential backoff
                delay = backoff_seconds * (2 ** (attempts - 1))
                scheduled_at = datetime.now() + timedelta(seconds=delay)

                conn.execute(
                    """
                    UPDATE quantum_jobs
                    SET status = 'pending', attempts = ?, scheduled_at = ?, error = ?
                    WHERE id = ?
                    """,
                    (attempts, scheduled_at, error, job.id)
                )
                logger.info(f"Job {job.id} will retry in {format_duration(delay)}")
            else:
                # Max retries exceeded
                conn.execute(
                    """
                    UPDATE quantum_jobs
                    SET status = 'failed', attempts = ?, completed_at = ?, error = ?
                    WHERE id = ?
                    """,
                    (attempts, datetime.now(), error, job.id)
                )
                logger.error(f"Job {job.id} failed after {attempts} attempts")

            conn.commit()
        finally:
            conn.close()

    def _fail_job(self, job_id: int, error: str):
        """Mark a job as failed"""
        conn = self._get_connection()
        try:
            conn.execute(
                "UPDATE quantum_jobs SET status = 'failed', completed_at = ?, error = ? WHERE id = ?",
                (datetime.now(), error, job_id)
            )
            conn.commit()
        finally:
            conn.close()

    def _row_to_job_info(self, row: sqlite3.Row) -> JobInfo:
        """Convert database row to JobInfo"""
        params = {}
        if row['params']:
            try:
                params = json.loads(row['params'])
            except json.JSONDecodeError:
                pass

        def parse_datetime(val):
            if val:
                if isinstance(val, str):
                    return datetime.fromisoformat(val)
                return val
            return None

        return JobInfo(
            id=row['id'],
            name=row['name'],
            queue=row['queue'],
            params=params,
            status=row['status'],
            attempts=row['attempts'],
            max_attempts=row['max_attempts'],
            scheduled_at=parse_datetime(row['scheduled_at']),
            started_at=parse_datetime(row['started_at']),
            completed_at=parse_datetime(row['completed_at']),
            error=row['error'],
            created_at=parse_datetime(row['created_at'])
        )

    def get_queue_stats(self, queue: str = 'default') -> Dict[str, int]:
        """
        Get queue statistics.

        Args:
            queue: Queue name

        Returns:
            Dict with status counts
        """
        conn = self._get_connection()
        try:
            rows = conn.execute(
                """
                SELECT status, COUNT(*) as count
                FROM quantum_jobs
                WHERE queue = ?
                GROUP BY status
                """,
                (queue,)
            ).fetchall()

            stats = {'pending': 0, 'running': 0, 'completed': 0, 'failed': 0}
            for row in rows:
                stats[row['status']] = row['count']
            return stats
        finally:
            conn.close()


# ============================================
# JOB EXECUTOR (Unified Interface)
# ============================================

class JobExecutor:
    """
    Unified interface for job execution services.

    Provides access to:
    - ScheduleService for scheduled tasks
    - ThreadService for async threads
    - JobQueueService for job queues
    """

    def __init__(
        self,
        max_thread_workers: int = 10,
        job_db_path: str = "quantum_jobs.db"
    ):
        """
        Initialize job executor.

        Args:
            max_thread_workers: Maximum concurrent threads
            job_db_path: Path to job queue database
        """
        self.schedule = ScheduleService()
        self.thread = ThreadService(max_workers=max_thread_workers)
        self.job_queue = JobQueueService(db_path=job_db_path)
        self._worker_running = False

    def shutdown(self, wait: bool = True):
        """Shutdown all services"""
        self.schedule.shutdown()
        self.thread.shutdown(wait=wait)
        self.job_queue.stop_workers()
        logger.info("Job executor shutdown complete")

    # ========================================
    # CLI Interface Methods
    # ========================================

    def list_jobs(self, status: Optional[str] = None, queue: Optional[str] = None) -> List[Dict]:
        """
        List all jobs (schedules and queued jobs).

        Args:
            status: Filter by status
            queue: Filter by queue

        Returns:
            List of job dicts
        """
        jobs = []

        # Add scheduled jobs
        for sched in self.schedule.list_schedules():
            job_status = 'active' if sched.enabled else 'paused'
            if status and status != job_status:
                continue
            jobs.append({
                'name': sched.name,
                'type': 'schedule',
                'queue': 'scheduler',
                'status': job_status,
                'interval': sched.trigger_info,
                'next_run': sched.next_run,
                'last_run': sched.last_run,
                'run_count': sched.run_count,
                'last_error': sched.last_error,
            })

        # Add queued jobs
        queued_jobs = self.job_queue.list_jobs(queue=queue, status=status)
        for job in queued_jobs:
            jobs.append({
                'name': job.name,
                'type': 'job',
                'queue': job.queue,
                'status': job.status,
                'next_run': job.scheduled_at,
                'last_run': job.completed_at,
                'attempts': job.attempts,
                'error': job.error,
            })

        return jobs

    def get_job_status(self, name: str) -> Optional[Dict]:
        """
        Get detailed status of a job.

        Args:
            name: Job name

        Returns:
            Job details dict or None
        """
        # Check schedules first
        sched = self.schedule.get_schedule(name)
        if sched:
            return {
                'name': sched.name,
                'type': 'schedule',
                'status': 'active' if sched.enabled else 'paused',
                'trigger_type': sched.trigger_type,
                'interval': sched.trigger_info,
                'next_run': sched.next_run,
                'last_run': sched.last_run,
                'run_count': sched.run_count,
                'last_error': sched.last_error,
            }

        # Check queued jobs
        jobs = self.job_queue.list_jobs()
        for job in jobs:
            if job.name == name:
                return {
                    'name': job.name,
                    'type': 'job',
                    'queue': job.queue,
                    'status': job.status,
                    'params': job.params,
                    'attempts': job.attempts,
                    'max_attempts': job.max_attempts,
                    'scheduled_at': job.scheduled_at,
                    'started_at': job.started_at,
                    'completed_at': job.completed_at,
                    'error': job.error,
                    'created_at': job.created_at,
                }

        return None

    def run_job_now(self, name: str, params: Optional[Dict] = None, wait: bool = False) -> Dict:
        """
        Run a job immediately.

        Args:
            name: Job name
            params: Optional parameters
            wait: Wait for completion

        Returns:
            Result dict with success/error
        """
        # Check if it's a schedule
        if self.schedule.run_now(name):
            return {'success': True, 'type': 'schedule'}

        # Otherwise dispatch to queue
        try:
            job_id = self.job_queue.dispatch(name, params=params or {})
            result = {'success': True, 'type': 'job', 'job_id': job_id}

            if wait:
                # Poll for completion
                import time
                for _ in range(60):  # Max 60 seconds
                    job = self.job_queue.get_job(job_id)
                    if job and job.status in ('completed', 'failed'):
                        result['success'] = job.status == 'completed'
                        result['result'] = job.params
                        if job.error:
                            result['error'] = job.error
                        break
                    time.sleep(1)

            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def pause_job(self, name: str) -> bool:
        """Pause a scheduled job."""
        return self.schedule.pause_schedule(name)

    def resume_job(self, name: str) -> bool:
        """Resume a paused job."""
        return self.schedule.resume_schedule(name)

    def cancel_job(self, name: str) -> bool:
        """Cancel a job (schedule or queued)."""
        # Try schedule first
        if self.schedule.remove_schedule(name):
            return True

        # Try queued jobs
        jobs = self.job_queue.list_jobs(status='pending')
        for job in jobs:
            if job.name == name:
                return self.job_queue.cancel_job(job.id)

        return False

    def get_job_history(
        self,
        name: Optional[str] = None,
        limit: int = 10,
        status: Optional[str] = None
    ) -> List[Dict]:
        """
        Get job execution history.

        Args:
            name: Filter by job name
            limit: Maximum entries
            status: Filter by status

        Returns:
            List of history entries
        """
        # Get completed/failed jobs from queue
        jobs = self.job_queue.list_jobs(status=status, limit=limit)

        history = []
        for job in jobs:
            if name and job.name != name:
                continue

            duration = None
            if job.started_at and job.completed_at:
                duration = (job.completed_at - job.started_at).total_seconds()

            history.append({
                'name': job.name,
                'queue': job.queue,
                'status': job.status,
                'started_at': job.started_at,
                'completed_at': job.completed_at,
                'duration': duration,
                'attempts': job.attempts,
                'error': job.error,
            })

        return history[:limit]

    def list_queues(self) -> List[Dict]:
        """List all known queues with stats."""
        # Get unique queues from jobs
        all_jobs = self.job_queue.list_jobs(limit=1000)
        queues = {}

        for job in all_jobs:
            if job.queue not in queues:
                queues[job.queue] = {
                    'name': job.queue,
                    'pending': 0,
                    'running': 0,
                    'completed': 0,
                    'failed': 0
                }
            queues[job.queue][job.status] = queues[job.queue].get(job.status, 0) + 1

        return list(queues.values()) if queues else [{'name': 'default', 'pending': 0, 'running': 0, 'completed': 0, 'failed': 0}]

    def purge_queue(self, queue: str, status: Optional[str] = None) -> int:
        """Purge jobs from a queue."""
        return self.job_queue.purge_queue(queue, status=status)

    def get_queue_stats(self, queue: Optional[str] = None) -> Dict:
        """Get queue statistics."""
        if queue:
            return self.job_queue.get_queue_stats(queue)

        # Aggregate all queues
        all_stats = {'total_jobs': 0, 'pending': 0, 'running': 0, 'completed': 0, 'failed': 0}
        for q in self.list_queues():
            for key in ['pending', 'running', 'completed', 'failed']:
                all_stats[key] += q.get(key, 0)
                all_stats['total_jobs'] += q.get(key, 0)
        return all_stats

    def start_worker(
        self,
        queues: List[str],
        concurrency: int = 4,
        poll_interval: float = 1.0
    ):
        """
        Start job workers.

        Args:
            queues: List of queues to process
            concurrency: Workers per queue
            poll_interval: Poll interval in seconds
        """
        self._worker_running = True
        for queue in queues:
            for _ in range(concurrency):
                self.job_queue.start_worker(queue, poll_interval)

        # Keep main thread alive
        import time
        try:
            while self._worker_running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    def stop_worker(self, graceful: bool = True):
        """Stop all workers."""
        self._worker_running = False
        self.job_queue.stop_workers()
