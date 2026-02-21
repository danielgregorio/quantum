"""
Tests for ThreadExecutor - q:thread async thread execution

Coverage target: 39% -> 60%
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from runtime.executors.jobs.thread_executor import ThreadExecutor
from runtime.executors.base import ExecutorError
from core.ast_nodes import ThreadNode

# Import fixtures from conftest.py
from tests.unit.executors.conftest import MockRuntime, MockExecutionContext


# =============================================================================
# Mock Objects for Threading Service
# =============================================================================

class MockThreadingService:
    """Mock threading service"""

    def __init__(self):
        self.last_run = None
        self.last_join = None
        self.last_terminate = None

    def run(self, config: Dict) -> Dict:
        """Mock thread start"""
        self.last_run = config
        return {
            'name': config['name'],
            'threadId': 'thread-123',
            'status': 'running'
        }

    def join(self, name: str) -> Dict:
        """Mock thread join"""
        self.last_join = name
        return {
            'name': name,
            'status': 'completed',
            'result': {'data': 'done'}
        }

    def terminate(self, name: str) -> Dict:
        """Mock thread terminate"""
        self.last_terminate = name
        return {
            'name': name,
            'terminated': True
        }


class MockThreadRuntime(MockRuntime):
    """Extended mock runtime with threading service"""

    def __init__(self, variables: Dict[str, Any] = None):
        super().__init__(variables)
        self._threading_service = MockThreadingService()
        self._services = MagicMock()
        self._services.threading = self._threading_service

    @property
    def services(self):
        return self._services


# =============================================================================
# Test Classes
# =============================================================================

class TestThreadExecutorBasic:
    """Basic functionality tests"""

    def test_handles_thread_node(self):
        """Test that ThreadExecutor handles ThreadNode"""
        runtime = MockThreadRuntime()
        executor = ThreadExecutor(runtime)
        assert ThreadNode in executor.handles

    def test_handles_returns_list(self):
        """Test that handles returns a list"""
        runtime = MockThreadRuntime()
        executor = ThreadExecutor(runtime)
        assert isinstance(executor.handles, list)
        assert len(executor.handles) == 1


class TestRunAction:
    """Test thread run action"""

    def test_run_basic(self):
        """Test basic thread start"""
        runtime = MockThreadRuntime()
        executor = ThreadExecutor(runtime)

        # ThreadNode is dataclass with name as first required arg
        node = ThreadNode(name="worker")
        node.action = "run"
        node.priority = "normal"
        node.timeout = "30s"  # String, not int

        executor.execute(node, runtime.execution_context)

        config = runtime._threading_service.last_run
        assert config["name"] == "worker"
        assert config["priority"] == "normal"
        assert config["timeout"] == "30s"

    def test_run_high_priority(self):
        """Test high priority thread"""
        runtime = MockThreadRuntime()
        executor = ThreadExecutor(runtime)

        node = ThreadNode(name="urgent")
        node.action = "run"
        node.priority = "high"
        node.timeout = "10s"

        executor.execute(node, runtime.execution_context)

        assert runtime._threading_service.last_run["priority"] == "high"

    def test_run_with_callbacks(self):
        """Test thread with callbacks"""
        runtime = MockThreadRuntime()
        executor = ThreadExecutor(runtime)

        node = ThreadNode(name="task")
        node.action = "run"
        node.priority = "normal"
        # Callbacks are function names (strings), not lists
        node.on_complete = "handleComplete"
        node.on_error = "handleError"

        executor.execute(node, runtime.execution_context)

        config = runtime._threading_service.last_run
        assert config["on_complete"] == "handleComplete"
        assert config["on_error"] == "handleError"

    def test_run_captures_context_snapshot(self):
        """Test that context is snapshotted"""
        runtime = MockThreadRuntime({"userId": 123, "taskId": 456})
        executor = ThreadExecutor(runtime)

        node = ThreadNode(name="task")
        node.action = "run"

        executor.execute(node, runtime.execution_context)

        snapshot = runtime._threading_service.last_run["context_snapshot"]
        assert snapshot["userId"] == 123
        assert snapshot["taskId"] == 456


class TestJoinAction:
    """Test thread join action"""

    def test_join_thread(self):
        """Test joining a thread"""
        runtime = MockThreadRuntime()
        executor = ThreadExecutor(runtime)

        node = ThreadNode(name="worker")
        node.action = "join"

        result = executor.execute(node, runtime.execution_context)

        assert runtime._threading_service.last_join == "worker"
        assert result["status"] == "completed"


class TestTerminateAction:
    """Test thread terminate action"""

    def test_terminate_thread(self):
        """Test terminating a thread"""
        runtime = MockThreadRuntime()
        executor = ThreadExecutor(runtime)

        node = ThreadNode(name="stuck-task")
        node.action = "terminate"

        executor.execute(node, runtime.execution_context)

        assert runtime._threading_service.last_terminate == "stuck-task"


class TestResultStorage:
    """Test result storage"""

    def test_stores_result(self):
        """Test that result is stored"""
        runtime = MockThreadRuntime()
        executor = ThreadExecutor(runtime)

        node = ThreadNode(name="myWorker")
        node.action = "run"

        executor.execute(node, runtime.execution_context)

        stored = runtime.execution_context.get_variable("myWorker_thread")
        assert stored["threadId"] == "thread-123"
        assert stored["status"] == "running"


class TestErrorHandling:
    """Test error handling"""

    def test_unknown_action_raises_error(self):
        """Test that unknown action raises error"""
        runtime = MockThreadRuntime()
        executor = ThreadExecutor(runtime)

        node = ThreadNode(name="test")
        node.action = "invalid"

        with pytest.raises(ExecutorError, match="Unknown thread action"):
            executor.execute(node, runtime.execution_context)

    def test_run_error_wrapped(self):
        """Test that run error is wrapped"""
        runtime = MockThreadRuntime()
        runtime._threading_service.run = MagicMock(
            side_effect=Exception("Thread pool exhausted")
        )
        executor = ThreadExecutor(runtime)

        node = ThreadNode(name="test")
        node.action = "run"

        with pytest.raises(ExecutorError, match="Thread execution error"):
            executor.execute(node, runtime.execution_context)

