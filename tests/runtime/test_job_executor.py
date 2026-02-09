"""
Tests for the Job Execution System (q:schedule, q:thread, q:job)
"""

import pytest
import time
import tempfile
import os
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from runtime.job_executor import (
    parse_duration, format_duration,
    JobExecutor, ScheduleService, ThreadService, JobQueueService,
    JobExecutorError, ScheduleError, ThreadError, JobQueueError,
    HAS_APSCHEDULER
)


class TestDurationParsing:
    """Tests for duration string parsing"""

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

    def test_parse_with_spaces(self):
        assert parse_duration(" 30s ") == 30
        assert parse_duration("  5m") == 300

    def test_parse_case_insensitive(self):
        assert parse_duration("30S") == 30
        assert parse_duration("5M") == 300
        assert parse_duration("1H") == 3600

    def test_parse_invalid_format(self):
        with pytest.raises(ValueError):
            parse_duration("30x")
        with pytest.raises(ValueError):
            parse_duration("abc")
        with pytest.raises(ValueError):
            parse_duration("")


class TestDurationFormatting:
    """Tests for duration formatting"""

    def test_format_seconds(self):
        assert format_duration(30) == "30s"
        assert format_duration(59) == "59s"

    def test_format_minutes(self):
        assert format_duration(60) == "1m"
        assert format_duration(300) == "5m"
        assert format_duration(90) == "1m 30s"

    def test_format_hours(self):
        assert format_duration(3600) == "1h"
        assert format_duration(7200) == "2h"
        assert format_duration(5400) == "1h 30m"

    def test_format_days(self):
        assert format_duration(86400) == "1d"
        assert format_duration(172800) == "2d"
        assert format_duration(90000) == "1d 1h"


class TestThreadService:
    """Tests for ThreadService"""

    def test_thread_service_creation(self):
        ts = ThreadService(max_workers=5)
        assert ts is not None
        ts.shutdown()

    def test_run_simple_thread(self):
        ts = ThreadService(max_workers=5)
        result = []

        def task():
            time.sleep(0.1)  # Small delay to ensure status check happens while running
            result.append("done")
            return "completed"

        info = ts.run_thread(name="test", callback=task)
        assert info.name == "test"
        # Thread may start running immediately or complete quickly
        assert info.status in ["running", "completed"]

        thread_result = ts.join_thread("test", timeout=5)
        assert thread_result == "completed"
        assert result == ["done"]

        ts.shutdown()

    def test_thread_with_priority(self):
        ts = ThreadService(max_workers=5)

        def task():
            return "ok"

        info = ts.run_thread(name="test", callback=task, priority="high")
        assert info.priority == "high"

        ts.join_thread("test", timeout=5)
        ts.shutdown()

    def test_thread_invalid_priority(self):
        ts = ThreadService(max_workers=5)

        with pytest.raises(ThreadError):
            ts.run_thread(name="test", callback=lambda: None, priority="invalid")

        ts.shutdown()

    def test_list_threads(self):
        ts = ThreadService(max_workers=5)

        def slow_task():
            time.sleep(0.1)
            return "done"

        ts.run_thread(name="t1", callback=slow_task)
        ts.run_thread(name="t2", callback=slow_task)

        threads = ts.list_threads()
        assert len(threads) == 2

        # Wait for completion
        ts.join_thread("t1", timeout=5)
        ts.join_thread("t2", timeout=5)

        ts.shutdown()

    def test_terminate_thread(self):
        ts = ThreadService(max_workers=5)

        def slow_task():
            time.sleep(10)
            return "done"

        ts.run_thread(name="test", callback=slow_task)
        success = ts.terminate_thread("test")
        assert success

        info = ts.get_thread("test")
        assert info.status == "terminated"

        ts.shutdown()

    def test_on_complete_callback(self):
        ts = ThreadService(max_workers=5)
        callback_result = []

        def task():
            return "task_result"

        def on_complete(result):
            callback_result.append(result)

        ts.run_thread(name="test", callback=task, on_complete=on_complete)
        ts.join_thread("test", timeout=5)

        assert callback_result == ["task_result"]
        ts.shutdown()

    def test_on_error_callback(self):
        ts = ThreadService(max_workers=5)
        error_result = []

        def task():
            raise ValueError("test error")

        def on_error(error):
            error_result.append(str(error))

        ts.run_thread(name="test", callback=task, on_error=on_error)

        with pytest.raises(ThreadError):
            ts.join_thread("test", timeout=5)

        assert len(error_result) == 1
        assert "test error" in error_result[0]
        ts.shutdown()


class TestJobQueueService:
    """Tests for JobQueueService"""

    @pytest.fixture
    def job_queue(self):
        """Create a temporary job queue service"""
        db_path = os.path.join(tempfile.gettempdir(), f"test_jobs_{os.getpid()}.db")
        jq = JobQueueService(db_path=db_path)
        yield jq
        jq.stop_workers()
        if os.path.exists(db_path):
            os.remove(db_path)

    def test_dispatch_job(self, job_queue):
        job_id = job_queue.dispatch("test_job", params={"x": 1})
        assert job_id > 0

        job = job_queue.get_job(job_id)
        assert job.name == "test_job"
        assert job.status == "pending"
        assert job.params == {"x": 1}

    def test_dispatch_to_queue(self, job_queue):
        job_id = job_queue.dispatch("test_job", queue="emails")
        job = job_queue.get_job(job_id)
        assert job.queue == "emails"

    def test_dispatch_with_delay(self, job_queue):
        job_id = job_queue.dispatch("test_job", delay="30s")
        job = job_queue.get_job(job_id)
        assert job.scheduled_at is not None

    def test_dispatch_with_priority(self, job_queue):
        job1 = job_queue.dispatch("low_priority", priority=1)
        job2 = job_queue.dispatch("high_priority", priority=10)

        jobs = job_queue.list_jobs()
        # Should be sorted by priority descending
        assert jobs[0].name == "high_priority"

    def test_cancel_job(self, job_queue):
        job_id = job_queue.dispatch("test_job")
        success = job_queue.cancel_job(job_id)
        assert success

        job = job_queue.get_job(job_id)
        assert job.status == "cancelled"

    def test_cancel_running_job_fails(self, job_queue):
        job_id = job_queue.dispatch("test_job")
        # Simulate running state
        conn = job_queue._get_connection()
        conn.execute("UPDATE quantum_jobs SET status = 'running' WHERE id = ?", (job_id,))
        conn.commit()
        conn.close()

        success = job_queue.cancel_job(job_id)
        assert not success

    def test_list_jobs(self, job_queue):
        job_queue.dispatch("job1")
        job_queue.dispatch("job2")
        job_queue.dispatch("job3")

        jobs = job_queue.list_jobs()
        assert len(jobs) == 3

    def test_list_jobs_by_status(self, job_queue):
        job_queue.dispatch("pending_job")
        conn = job_queue._get_connection()
        conn.execute("INSERT INTO quantum_jobs (name, status) VALUES ('completed_job', 'completed')")
        conn.commit()
        conn.close()

        pending = job_queue.list_jobs(status="pending")
        assert len(pending) == 1
        assert pending[0].name == "pending_job"

    def test_get_queue_stats(self, job_queue):
        job_queue.dispatch("job1")
        job_queue.dispatch("job2")

        stats = job_queue.get_queue_stats()
        assert stats["pending"] == 2
        assert stats["completed"] == 0

    def test_purge_queue(self, job_queue):
        job_queue.dispatch("job1")
        job_queue.dispatch("job2")

        count = job_queue.purge_queue("default")
        assert count == 2

        jobs = job_queue.list_jobs()
        assert len(jobs) == 0

    def test_register_and_process_job(self, job_queue):
        processed = []

        def handler(params):
            processed.append(params)

        job_queue.register_handler("process", handler)
        job_queue.dispatch("process", params={"data": "test"})

        # Manually fetch and process
        job = job_queue._fetch_next_job("default")
        job_queue._process_job(job)

        assert len(processed) == 1
        assert processed[0] == {"data": "test"}

    def test_job_retry_on_failure(self, job_queue):
        call_count = [0]

        def failing_handler(params):
            call_count[0] += 1
            raise ValueError("Simulated failure")

        job_queue.register_handler("failing_job", failing_handler)
        job_id = job_queue.dispatch("failing_job", attempts=3, backoff="1s")

        # Process first attempt
        job = job_queue._fetch_next_job("default")
        job_queue._process_job(job)

        # Check job is scheduled for retry
        job = job_queue.get_job(job_id)
        assert job.status == "pending"
        assert job.attempts == 1

    def test_dispatch_batch(self, job_queue):
        jobs = [
            {"name": "job1", "params": {"x": 1}},
            {"name": "job2", "params": {"x": 2}},
        ]
        job_ids = job_queue.dispatch_batch(jobs)

        assert len(job_ids) == 2
        assert all(id > 0 for id in job_ids)


@pytest.mark.skipif(not HAS_APSCHEDULER, reason="APScheduler not installed")
class TestScheduleService:
    """Tests for ScheduleService (requires APScheduler)"""

    def test_schedule_service_creation(self):
        ss = ScheduleService()
        assert ss is not None
        ss.shutdown()

    def test_add_interval_schedule(self):
        ss = ScheduleService()
        executed = []

        def task():
            executed.append(1)

        info = ss.add_schedule(
            name="test",
            callback=task,
            interval="1s"
        )

        assert info.name == "test"
        assert info.trigger_type == "interval"
        assert info.enabled

        # Wait for execution
        time.sleep(1.5)
        assert len(executed) >= 1

        ss.shutdown()

    def test_add_cron_schedule(self):
        ss = ScheduleService()

        info = ss.add_schedule(
            name="test",
            callback=lambda: None,
            cron="* * * * *"  # Every minute
        )

        assert info.trigger_type == "cron"
        ss.shutdown()

    def test_pause_resume_schedule(self):
        ss = ScheduleService()

        ss.add_schedule(
            name="test",
            callback=lambda: None,
            interval="1s"
        )

        ss.pause_schedule("test")
        info = ss.get_schedule("test")
        assert not info.enabled

        ss.resume_schedule("test")
        info = ss.get_schedule("test")
        assert info.enabled

        ss.shutdown()

    def test_remove_schedule(self):
        ss = ScheduleService()

        ss.add_schedule(
            name="test",
            callback=lambda: None,
            interval="1s"
        )

        success = ss.remove_schedule("test")
        assert success

        info = ss.get_schedule("test")
        assert info is None

        ss.shutdown()

    def test_list_schedules(self):
        ss = ScheduleService()

        ss.add_schedule(name="s1", callback=lambda: None, interval="1s")
        ss.add_schedule(name="s2", callback=lambda: None, interval="2s")

        schedules = ss.list_schedules()
        assert len(schedules) == 2

        ss.shutdown()


class TestJobExecutor:
    """Tests for the unified JobExecutor interface"""

    def test_job_executor_creation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "jobs.db")
            executor = JobExecutor(
                max_thread_workers=5,
                job_db_path=db_path
            )

            assert executor.schedule is not None
            assert executor.thread is not None
            assert executor.job_queue is not None

            executor.shutdown()


class TestComponentIntegration:
    """Integration tests for job execution in components"""

    def test_parse_schedule_in_component(self):
        from core.parser import QuantumParser

        parser = QuantumParser()
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <q:component name="Test" xmlns:q="https://quantum.lang/ns">
            <q:schedule name="test" interval="1h">
                <q:set name="x" value="1" />
            </q:schedule>
        </q:component>
        '''

        component = parser.parse(xml)
        assert len(component.statements) == 1

        schedule = component.statements[0]
        assert schedule.name == "test"
        assert schedule.interval == "1h"
        assert len(schedule.body) == 1

    def test_parse_thread_in_component(self):
        from core.parser import QuantumParser

        parser = QuantumParser()
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <q:component name="Test" xmlns:q="https://quantum.lang/ns">
            <q:thread name="worker" priority="high" timeout="5m">
                <q:set name="status" value="running" />
            </q:thread>
        </q:component>
        '''

        component = parser.parse(xml)
        assert len(component.statements) == 1

        thread = component.statements[0]
        assert thread.name == "worker"
        assert thread.priority == "high"
        assert thread.timeout == "5m"
        assert len(thread.body) == 1

    def test_parse_job_in_component(self):
        from core.parser import QuantumParser

        parser = QuantumParser()
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <q:component name="Test" xmlns:q="https://quantum.lang/ns">
            <q:job name="sendEmail" queue="emails" priority="5" attempts="3">
                <q:param name="to" type="string" />
                <q:param name="subject" type="string" />
            </q:job>
        </q:component>
        '''

        component = parser.parse(xml)
        assert len(component.statements) == 1

        job = component.statements[0]
        assert job.name == "sendEmail"
        assert job.queue == "emails"
        assert job.priority == 5
        assert job.attempts == 3
        assert len(job.params) == 2

    def test_execute_job_dispatch(self):
        from core.parser import QuantumParser
        from runtime.component import ComponentRuntime

        parser = QuantumParser()
        xml = '''<?xml version="1.0" encoding="UTF-8"?>
        <q:component name="Test" xmlns:q="https://quantum.lang/ns">
            <q:job name="testJob" queue="test" action="define">
                <q:set name="done" value="true" />
            </q:job>
            <q:job name="testJob" action="dispatch" queue="test" />
            <q:return value="{dispatched_job_testJob.job_id}" />
        </q:component>
        '''

        component = parser.parse(xml)
        runtime = ComponentRuntime()
        result = runtime.execute_component(component)

        assert result is not None
        assert result > 0  # Job ID should be positive

        runtime.job_executor.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
