"""Job threads stop when asked, and a request does not start its own (RUN-1).

A queue worker slept between polls and only checked a flag: stop_workers()
returned while the thread went on, and a job it was running logged after the
program (or the test) that started it had closed its streams. And the web
server builds a service container per request (ACT-10), each with its own
JobExecutor: every request to a page with q:job started one more worker.
"""

import threading
import time

from quantum.core.parser import QuantumParser
from quantum.runtime.component import ComponentRuntime
from quantum.runtime.job_executor import JobQueueService, shared_job_executor

NS = 'xmlns:q="https://quantum.lang/ns"'
PAGE = (f'<q:component name="J" {NS}><q:job name="noop" queue="threads" action="define">'
        '<q:set name="x" value="1"/></q:job><q:return value="ok"/></q:component>')


def workers(queue):
    return [t for t in threading.enumerate() if t.name == f'quantum-job-worker-{queue}' and t.is_alive()]


def test_stopping_the_workers_waits_for_them(tmp_path):
    # RUN-1: a worker asleep for its poll interval stops at once, and is gone when stop returns
    queue = JobQueueService(db_path=str(tmp_path / 'jobs.db'))
    queue.start_worker('slow', poll_interval=30)
    assert workers('slow')
    started = time.monotonic()
    queue.stop_workers()
    assert workers('slow') == [] and time.monotonic() - started < 5


def test_requests_share_the_process_executor(tmp_path):
    # RUN-1: ten runtimes (ten requests) running q:job — one executor, one worker
    config = {'job_db_path': str(tmp_path / 'jobs.db')}
    try:
        for _ in range(10):
            assert ComponentRuntime(config=config).execute_component(QuantumParser().parse(PAGE)) == 'ok'
        assert len(workers('threads')) == 1
        assert ComponentRuntime(config=config).job_executor is shared_job_executor(config['job_db_path'])
    finally:
        shared_job_executor(config['job_db_path']).shutdown()
    assert workers('threads') == []
    # a shut-down executor is replaced, not handed out again
    assert shared_job_executor(config['job_db_path']).closed is False
    shared_job_executor(config['job_db_path']).shutdown()
