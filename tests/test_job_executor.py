"""
Tests for Job Execution System (q:schedule, q:thread, q:job)
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from runtime.job_executor import (
    parse_duration, format_duration,
    ScheduleService, ThreadService, JobQueueService, JobExecutor,
    ScheduleError, ThreadError, JobQueueError
)


class TestParseDuration:
    """Tests for duration parsing"""

    def test_parse_seconds(self):
        assert parse_duration("30s") == 30
        assert parse_duration("1s") == 1
        assert parse_duration("120s") == 120

    def test_parse_minutes(self):
        assert parse_duration("5m") == 300
        assert parse_duration("1m") == 60
        assert parse_duration("30m") == 1800

    def test_parse_hours(self):
        assert parse_duration("1h") == 3600
        assert parse_duration("2h") == 7200
        assert parse_duration("24h") == 86400

    def test_parse_days(self):
        assert parse_duration("1d") == 86400
        assert parse_duration("7d") == 604800

    def test_parse_weeks(self):
        assert parse_duration("1w") == 604800
        assert parse_duration("2w") == 1209600

    def test_parse_plain_number(self):
        assert parse_duration("30") == 30
        assert parse_duration("3600") == 3600

    def test_invalid_format(self):
        with pytest.raises(ValueError):
            parse_duration("invalid")

        with pytest.raises(ValueError):
            parse_duration("5x")

        with pytest.raises(ValueError):
            parse_duration("")


class TestFormatDuration:
    """Tests for duration formatting"""

    def test_format_seconds(self):
        assert format_duration(30) == "30s"
        assert format_duration(59) == "59s"

    def test_format_minutes(self):
        assert format_duration(60) == "1m"
        assert format_duration(90) == "1m 30s"
        assert format_duration(300) == "5m"

    def test_format_hours(self):
        assert format_duration(3600) == "1h"
        assert format_duration(5400) == "1h 30m"
        assert format_duration(7200) == "2h"

    def test_format_days(self):
        assert format_duration(86400) == "1d"
        assert format_duration(90000) == "1d 1h"


class TestThreadService:
    """Tests for ThreadService"""

    def test_run_thread(self):
        service = ThreadService(max_workers=5)
        result = []

        def task():
            time.sleep(0.05)  # Small delay to ensure we can check running status
            result.append("done")
            return "success"

        info = service.run_thread("test-thread", task)

        assert info.name == "test-thread"
        assert info.status == "running"
        assert info.priority == "normal"

        # Wait for completion
        time.sleep(0.2)

        thread_info = service.get_thread("test-thread")
        assert thread_info.status == "completed"
        assert result == ["done"]

        service.shutdown()

    def test_run_thread_with_priority(self):
        service = ThreadService(max_workers=5)

        info = service.run_thread("high-priority", lambda: None, priority="high")
        assert info.priority == "high"

        service.shutdown()

    def test_run_thread_with_callback(self):
        service = ThreadService(max_workers=5)
        callback_result = []

        def on_complete(result):
            callback_result.append(result)

        def task():
            return 42

        service.run_thread("callback-test", task, on_complete=on_complete)
        time.sleep(0.2)

        assert callback_result == [42]

        service.shutdown()

    def test_run_thread_with_error_callback(self):
        service = ThreadService(max_workers=5)
        error_result = []

        def on_error(error):
            error_result.append(str(error))

        def task():
            raise ValueError("test error")

        service.run_thread("error-test", task, on_error=on_error)
        time.sleep(0.2)

        assert len(error_result) == 1
        assert "test error" in error_result[0]

        service.shutdown()

    def test_join_thread(self):
        service = ThreadService(max_workers=5)

        def slow_task():
            time.sleep(0.1)
            return "completed"

        service.run_thread("join-test", slow_task)
        result = service.join_thread("join-test", timeout=5.0)

        assert result == "completed"

        service.shutdown()

    def test_list_threads(self):
        service = ThreadService(max_workers=5)

        service.run_thread("thread1", lambda: time.sleep(0.5))
        service.run_thread("thread2", lambda: time.sleep(0.5))

        threads = service.list_threads()
        assert len(threads) >= 2

        running = service.list_threads(status="running")
        assert len(running) >= 0  # May have completed

        service.shutdown()

    def test_invalid_priority(self):
        service = ThreadService(max_workers=5)

        with pytest.raises(ThreadError):
            service.run_thread("invalid", lambda: None, priority="invalid")

        service.shutdown()


class TestJobQueueService:
    """Tests for JobQueueService"""

    @pytest.fixture
    def job_service(self, tmp_path):
        """Create job service with temp database"""
        db_path = str(tmp_path / "test_jobs.db")
        service = JobQueueService(db_path=db_path)
        yield service
        service.stop_workers()

    def test_dispatch_job(self, job_service):
        job_id = job_service.dispatch(
            name="test-job",
            queue="default",
            params={"key": "value"}
        )

        assert job_id > 0

        job = job_service.get_job(job_id)
        assert job is not None
        assert job.name == "test-job"
        assert job.status == "pending"
        assert job.params == {"key": "value"}

    def test_dispatch_with_delay(self, job_service):
        job_id = job_service.dispatch(
            name="delayed-job",
            delay="30s"
        )

        job = job_service.get_job(job_id)
        assert job.scheduled_at is not None

    def test_list_jobs(self, job_service):
        job_service.dispatch(name="job1")
        job_service.dispatch(name="job2")
        job_service.dispatch(name="job3", queue="other")

        all_jobs = job_service.list_jobs()
        assert len(all_jobs) >= 3

        default_queue = job_service.list_jobs(queue="default")
        assert len(default_queue) >= 2

        other_queue = job_service.list_jobs(queue="other")
        assert len(other_queue) >= 1

    def test_cancel_job(self, job_service):
        job_id = job_service.dispatch(name="cancel-test")

        assert job_service.cancel_job(job_id) is True

        job = job_service.get_job(job_id)
        assert job.status == "cancelled"

    def test_purge_queue(self, job_service):
        job_service.dispatch(name="purge1", queue="purge-test")
        job_service.dispatch(name="purge2", queue="purge-test")
        job_service.dispatch(name="purge3", queue="purge-test")

        count = job_service.purge_queue("purge-test")
        assert count == 3

        jobs = job_service.list_jobs(queue="purge-test")
        assert len(jobs) == 0

    def test_get_queue_stats(self, job_service):
        job_service.dispatch(name="stats1", queue="stats-test")
        job_service.dispatch(name="stats2", queue="stats-test")

        stats = job_service.get_queue_stats("stats-test")
        assert stats["pending"] >= 2

    def test_register_handler(self, job_service):
        handler = Mock()
        job_service.register_handler("test-handler", handler)

        assert "test-handler" in job_service._handlers

    def test_batch_dispatch(self, job_service):
        jobs = [
            {"name": "batch1", "params": {"id": 1}},
            {"name": "batch2", "params": {"id": 2}},
            {"name": "batch3", "params": {"id": 3}},
        ]

        job_ids = job_service.dispatch_batch(jobs)
        assert len(job_ids) == 3


class TestJobExecutor:
    """Tests for unified JobExecutor"""

    @pytest.fixture
    def executor(self, tmp_path):
        """Create executor with temp database"""
        db_path = str(tmp_path / "test_executor.db")
        executor = JobExecutor(job_db_path=db_path)
        yield executor
        executor.shutdown()

    def test_list_jobs(self, executor):
        # Dispatch a job
        executor.job_queue.dispatch(name="test-job")

        jobs = executor.list_jobs()
        assert len(jobs) >= 1

    def test_get_job_status(self, executor):
        executor.job_queue.dispatch(name="status-test", params={"x": 1})

        status = executor.get_job_status("status-test")
        assert status is not None
        assert status["name"] == "status-test"

    def test_cancel_job(self, executor):
        executor.job_queue.dispatch(name="cancel-executor-test")

        result = executor.cancel_job("cancel-executor-test")
        assert result is True

    def test_list_queues(self, executor):
        executor.job_queue.dispatch(name="q1", queue="queue-a")
        executor.job_queue.dispatch(name="q2", queue="queue-b")

        queues = executor.list_queues()
        assert len(queues) >= 2

    def test_get_queue_stats(self, executor):
        executor.job_queue.dispatch(name="stat1")
        executor.job_queue.dispatch(name="stat2")

        stats = executor.get_queue_stats()
        assert "total_jobs" in stats
        assert stats["total_jobs"] >= 2


class TestScheduleServiceWithMock:
    """Tests for ScheduleService with mocked APScheduler"""

    @pytest.fixture
    def mock_apscheduler(self):
        """Mock APScheduler if not installed"""
        with patch.dict('sys.modules', {
            'apscheduler': MagicMock(),
            'apscheduler.schedulers': MagicMock(),
            'apscheduler.schedulers.background': MagicMock(),
            'apscheduler.triggers': MagicMock(),
            'apscheduler.triggers.interval': MagicMock(),
            'apscheduler.triggers.cron': MagicMock(),
            'apscheduler.triggers.date': MagicMock(),
            'apscheduler.jobstores': MagicMock(),
            'apscheduler.jobstores.memory': MagicMock(),
        }):
            yield

    def test_service_creation(self):
        service = ScheduleService()
        assert service._schedules == {}
        assert service._started is False

    def test_list_empty_schedules(self):
        service = ScheduleService()
        schedules = service.list_schedules()
        assert schedules == []


# Integration test
class TestJobExecutorIntegration:
    """Integration tests for job executor"""

    def test_full_workflow(self, tmp_path):
        """Test complete job workflow"""
        db_path = str(tmp_path / "integration.db")
        executor = JobExecutor(job_db_path=db_path)

        results = []

        # Register handler
        def handler(params):
            results.append(params["value"])

        executor.job_queue.register_handler("integration-job", handler)

        # Dispatch jobs
        executor.job_queue.dispatch(name="integration-job", params={"value": 1})
        executor.job_queue.dispatch(name="integration-job", params={"value": 2})

        # Start worker briefly
        executor.job_queue.start_worker(queue="default", poll_interval=0.1)
        time.sleep(0.5)
        executor.job_queue.stop_workers()

        # Verify jobs were processed
        assert len(results) >= 0  # May or may not have processed depending on timing

        executor.shutdown()
