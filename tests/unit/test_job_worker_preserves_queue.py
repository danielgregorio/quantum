"""
`quantum jobs worker start` destroyed the queue on its first poll.

_process_job looked up a handler for the job name and, finding none, called
_fail_job(job.id, "No handler registered"). Handlers are registered by
EXECUTING the .q file that declares <q:job>, so a standalone worker process
has an EMPTY handler table — it marked every pending job 'failed' immediately,
permanently destroying queued work that another worker could have run.

A worker that cannot do a job has not learned that the job is bad.
"""

import sqlite3
import pytest

from quantum.runtime.job_executor import JobQueueService


@pytest.fixture
def queue(tmp_path):
    svc = JobQueueService(db_path=str(tmp_path / "jobs.db"))
    return svc


def _status(svc, job_id):
    conn = svc._get_connection()
    try:
        row = conn.execute(
            "SELECT status FROM quantum_jobs WHERE id = ?", (job_id,)
        ).fetchone()
        return row["status"] if row else None
    finally:
        conn.close()


class TestAnUnhandleableJobStaysQueued:
    def test_it_is_not_failed(self, queue):
        job_id = queue.dispatch(name="semHandler", queue="default", params={"a": 1})
        job = queue._fetch_next_job("default")
        assert job is not None
        queue._process_job(job)
        assert _status(queue, job_id) != "failed", (
            "the worker destroyed a job it simply could not run"
        )

    def test_it_returns_to_pending(self, queue):
        """It was marked 'running' by the fetch; it must not be stranded there."""
        job_id = queue.dispatch(name="semHandler", queue="default", params={})
        job = queue._fetch_next_job("default")
        queue._process_job(job)
        assert _status(queue, job_id) == "pending"

    def test_process_job_reports_that_it_did_not_run(self, queue):
        """The worker loop uses this to back off instead of spinning on the
        same row at full speed."""
        queue.dispatch(name="semHandler", queue="default", params={})
        job = queue._fetch_next_job("default")
        assert queue._process_job(job) is False


class TestARealJobStillRuns:
    def test_completed(self, queue):
        seen = []
        queue.register_handler("comHandler", lambda params: seen.append(params))
        job_id = queue.dispatch(name="comHandler", queue="default", params={"x": 9})
        job = queue._fetch_next_job("default")
        queue._process_job(job)
        assert seen == [{"x": 9}]
        assert _status(queue, job_id) == "completed"

    def test_a_raising_handler_is_still_a_failure(self, queue):
        """Releasing must not swallow genuine failures."""
        def boom(params):
            raise RuntimeError("nope")
        queue.register_handler("quebra", boom)
        job_id = queue.dispatch(name="quebra", queue="default", params={})
        job = queue._fetch_next_job("default")
        queue._process_job(job)
        assert _status(queue, job_id) in ("failed", "pending")  # retry or fail
        assert _status(queue, job_id) != "completed"
