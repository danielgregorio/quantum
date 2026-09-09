"""
Tests for ThreadExecutor - q:thread async execution

Rewritten 2026-09-07: the previous version mocked services.threading with
run()/join()/terminate() — none of which exist. Threads live on
services.job_executor.thread (a ThreadService) with run_thread()/
join_thread()/terminate_thread(), and run_thread() takes a *callback*.
See FULL_AUDIT_2026-09.md, Cluster C.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock
from typing import Any, Dict, Optional

from quantum.runtime.executors.jobs.thread_executor import ThreadExecutor
from quantum.runtime.executors.base import ExecutorError
from quantum.runtime.job_executor import ThreadInfo
from quantum.core.ast_nodes import ThreadNode, QuantumReturn

from tests.unit.executors.conftest import MockRuntime


class MockThreadService:
    """Mirrors the real ThreadService interface."""

    def __init__(self):
        self.last_kwargs: Optional[Dict[str, Any]] = None
        self.joined = []
        self.terminated = []
        self._threads: Dict[str, ThreadInfo] = {}

    def run_thread(self, name, callback, priority='normal', timeout=None,
                   on_complete=None, on_error=None) -> ThreadInfo:
        self.last_kwargs = dict(name=name, callback=callback, priority=priority,
                                timeout=timeout)
        info = ThreadInfo(name=name, priority=priority,
                          started_at=datetime(2026, 1, 1), status='running')
        self._threads[name] = info
        return info

    def join_thread(self, name, timeout=None):
        self.joined.append(name)
        return "thread-result"

    def get_thread(self, name):
        return self._threads.get(name)

    def terminate_thread(self, name):
        self.terminated.append(name)
        return True


class MockThreadRuntime(MockRuntime):
    def __init__(self, variables: Dict[str, Any] = None):
        super().__init__(variables)
        self._thread_service = MockThreadService()
        self._services = MagicMock()
        self._services.job_executor.thread = self._thread_service

    @property
    def services(self):
        return self._services


class TestThreadExecutorBasic:
    def test_handles_thread_node(self):
        executor = ThreadExecutor(MockThreadRuntime())
        assert ThreadNode in executor.handles

    def test_handles_returns_list(self):
        executor = ThreadExecutor(MockThreadRuntime())
        assert len(executor.handles) == 1


class TestThreadRun:
    def test_run_passes_name_and_callback(self):
        runtime = MockThreadRuntime()
        executor = ThreadExecutor(runtime)

        executor.execute(ThreadNode(name="worker"), runtime.execution_context)

        kwargs = runtime._thread_service.last_kwargs
        assert kwargs["name"] == "worker"
        assert callable(kwargs["callback"])

    def test_priority_and_timeout_passed(self):
        runtime = MockThreadRuntime()
        executor = ThreadExecutor(runtime)

        node = ThreadNode(name="worker", priority="high", timeout="30s")
        executor.execute(node, runtime.execution_context)

        kwargs = runtime._thread_service.last_kwargs
        assert kwargs["priority"] == "high"
        assert kwargs["timeout"] == "30s"

    def test_callback_runs_body_with_context_snapshot(self):
        runtime = MockThreadRuntime({"value": 99})
        executor = ThreadExecutor(runtime)

        node = ThreadNode(name="worker")
        node.body = [QuantumReturn(value="{value}")]

        executor.execute(node, runtime.execution_context)
        callback = runtime._thread_service.last_kwargs["callback"]

        assert callback() == 99


class TestThreadActions:
    def test_join_returns_result(self):
        runtime = MockThreadRuntime()
        executor = ThreadExecutor(runtime)

        executor.execute(ThreadNode(name="worker"), runtime.execution_context)
        result = executor.execute(ThreadNode(name="worker", action="join"),
                                   runtime.execution_context)

        assert runtime._thread_service.joined == ["worker"]
        assert result["result"] == "thread-result"

    def test_terminate_calls_terminate_thread(self):
        runtime = MockThreadRuntime()
        executor = ThreadExecutor(runtime)

        result = executor.execute(ThreadNode(name="worker", action="terminate"),
                                   runtime.execution_context)

        assert runtime._thread_service.terminated == ["worker"]
        assert result["success"] is True


class TestThreadResultStorage:
    def test_stores_result(self):
        runtime = MockThreadRuntime()
        executor = ThreadExecutor(runtime)

        executor.execute(ThreadNode(name="worker", priority="low"),
                         runtime.execution_context)

        stored = runtime.execution_context.get_variable("worker_thread")
        assert stored["name"] == "worker"
        assert stored["priority"] == "low"
        assert stored["status"] == "running"


class TestThreadErrorHandling:
    def test_unknown_action_raises_error(self):
        runtime = MockThreadRuntime()
        executor = ThreadExecutor(runtime)

        with pytest.raises(ExecutorError, match="Unknown thread action"):
            executor.execute(ThreadNode(name="worker", action="bogus"),
                             runtime.execution_context)

    def test_service_error_wrapped(self):
        runtime = MockThreadRuntime()
        runtime._thread_service.run_thread = MagicMock(side_effect=Exception("pool full"))
        executor = ThreadExecutor(runtime)

        with pytest.raises(ExecutorError, match="Thread execution error"):
            executor.execute(ThreadNode(name="worker"), runtime.execution_context)
