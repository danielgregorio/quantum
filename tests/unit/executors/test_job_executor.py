"""
Tests for JobExecutor - q:job job queue operations

Coverage target: 27% -> 60%
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from runtime.executors.jobs.job_executor import JobExecutor
from runtime.executors.base import ExecutorError
from core.ast_nodes import JobNode, QuantumParam

# Import fixtures from conftest.py
from tests.unit.executors.conftest import MockRuntime, MockExecutionContext


# =============================================================================
# Mock Objects for Jobs Service
# =============================================================================

class MockJobsService:
    """Mock jobs service"""

    def __init__(self):
        self.last_define = None
        self.last_dispatch = None
        self.last_batch = None

    def define(self, config: Dict) -> Dict:
        """Mock job definition"""
        self.last_define = config
        return {
            'name': config['name'],
            'defined': True,
            'queue': config.get('queue', 'default')
        }

    def dispatch(self, name: str, queue: str = None, params: Dict = None,
                 delay: str = None, priority: int = None, attempts: int = None,
                 backoff: str = None, timeout: str = None) -> Dict:
        """Mock job dispatch"""
        self.last_dispatch = {
            'name': name,
            'queue': queue,
            'params': params or {},
            'delay': delay,
            'priority': priority,
            'attempts': attempts,
            'backoff': backoff,
            'timeout': timeout
        }
        return {
            'name': name,
            'jobId': 'job-123',
            'queued': True
        }

    def batch(self, name: str, queue: str = None, tasks: List[Dict] = None,
              priority: int = None) -> Dict:
        """Mock batch dispatch"""
        self.last_batch = {
            'name': name,
            'queue': queue,
            'tasks': tasks or [],
            'priority': priority
        }
        return {
            'name': name,
            'batchId': 'batch-456',
            'jobsQueued': len(tasks) if tasks else 0
        }


class MockJobsRuntime(MockRuntime):
    """Extended mock runtime with jobs service"""

    def __init__(self, variables: Dict[str, Any] = None):
        super().__init__(variables)
        self._jobs_service = MockJobsService()
        self._services = MagicMock()
        self._services.jobs = self._jobs_service

    @property
    def services(self):
        return self._services


# =============================================================================
# Test Classes
# =============================================================================

class TestJobExecutorBasic:
    """Basic functionality tests"""

    def test_handles_job_node(self):
        """Test that JobExecutor handles JobNode"""
        runtime = MockJobsRuntime()
        executor = JobExecutor(runtime)
        assert JobNode in executor.handles

    def test_handles_returns_list(self):
        """Test that handles returns a list"""
        runtime = MockJobsRuntime()
        executor = JobExecutor(runtime)
        assert isinstance(executor.handles, list)
        assert len(executor.handles) == 1


class TestDefineAction:
    """Test job define action"""

    def test_define_basic(self):
        """Test basic job definition"""
        runtime = MockJobsRuntime()
        executor = JobExecutor(runtime)

        # JobNode uses __init__(name, queue, action)
        node = JobNode(name="sendEmail", queue="emails", action="define")
        node.attempts = 3
        node.backoff = "exponential"
        node.timeout = "30s"

        executor.execute(node, runtime.execution_context)

        config = runtime._jobs_service.last_define
        assert config["name"] == "sendEmail"
        assert config["queue"] == "emails"
        assert config["attempts"] == 3
        assert config["backoff"] == "exponential"

    def test_define_with_params(self):
        """Test job definition with parameters"""
        runtime = MockJobsRuntime()
        executor = JobExecutor(runtime)

        node = JobNode(name="processOrder", queue="orders", action="define")
        node.params = [
            QuantumParam(name="orderId", type="integer", required=True),
            QuantumParam(name="userId", type="integer", required=True),
            QuantumParam(name="priority", type="string", default="normal")
        ]
        node.attempts = 3
        node.timeout = "60s"

        executor.execute(node, runtime.execution_context)

        params = runtime._jobs_service.last_define["params"]
        assert len(params) == 3
        assert params[0]["name"] == "orderId"
        assert params[0]["required"] is True
        assert params[2]["default"] == "normal"


class TestDispatchAction:
    """Test job dispatch action"""

    def test_dispatch_basic(self):
        """Test basic job dispatch"""
        runtime = MockJobsRuntime()
        executor = JobExecutor(runtime)

        node = JobNode(name="sendEmail", queue="emails", action="dispatch")

        executor.execute(node, runtime.execution_context)

        dispatch = runtime._jobs_service.last_dispatch
        assert dispatch["name"] == "sendEmail"
        assert dispatch["queue"] == "emails"

    def test_dispatch_with_params(self):
        """Test job dispatch with parameters"""
        runtime = MockJobsRuntime({"email": "test@example.com", "subject": "Hello"})
        executor = JobExecutor(runtime)

        node = JobNode(name="sendEmail", queue="emails", action="dispatch")
        # Create params with value attribute
        param1 = QuantumParam(name="to")
        param1.value = "{email}"
        param2 = QuantumParam(name="subject")
        param2.value = "{subject}"
        node.params = [param1, param2]

        executor.execute(node, runtime.execution_context)

        params = runtime._jobs_service.last_dispatch["params"]
        assert params["to"] == "test@example.com"
        assert params["subject"] == "Hello"

    def test_dispatch_with_delay(self):
        """Test job dispatch with delay"""
        runtime = MockJobsRuntime()
        executor = JobExecutor(runtime)

        node = JobNode(name="reminder", queue="notifications", action="dispatch")
        node.delay = "60s"  # String format

        executor.execute(node, runtime.execution_context)

        assert runtime._jobs_service.last_dispatch["delay"] == "60s"

    def test_dispatch_with_priority(self):
        """Test job dispatch with priority"""
        runtime = MockJobsRuntime()
        executor = JobExecutor(runtime)

        node = JobNode(name="urgent", queue="tasks", action="dispatch")
        node.priority = 10
        node.attempts = 5

        executor.execute(node, runtime.execution_context)

        assert runtime._jobs_service.last_dispatch["priority"] == 10

    def test_dispatch_with_retry_config(self):
        """Test job dispatch with retry configuration"""
        runtime = MockJobsRuntime()
        executor = JobExecutor(runtime)

        node = JobNode(name="flaky", queue="tasks", action="dispatch")
        node.attempts = 5
        node.backoff = "exponential"
        node.timeout = "120s"

        executor.execute(node, runtime.execution_context)

        dispatch = runtime._jobs_service.last_dispatch
        assert dispatch["attempts"] == 5
        assert dispatch["backoff"] == "exponential"
        assert dispatch["timeout"] == "120s"


class TestBatchAction:
    """Test job batch action"""

    def test_batch_dispatch(self):
        """Test batch job dispatch"""
        runtime = MockJobsRuntime()
        executor = JobExecutor(runtime)

        node = JobNode(name="processOrders", queue="orders", action="batch")
        node.priority = 5
        node.tasks = [
            {"orderId": 1},
            {"orderId": 2},
            {"orderId": 3}
        ]

        executor.execute(node, runtime.execution_context)

        batch = runtime._jobs_service.last_batch
        assert batch["name"] == "processOrders"
        assert len(batch["tasks"]) == 3
        assert batch["priority"] == 5

    def test_batch_with_databinding(self):
        """Test batch with databinding in tasks"""
        runtime = MockJobsRuntime({"batchQueue": "high-priority"})
        executor = JobExecutor(runtime)

        node = JobNode(name="batchJob", queue="{batchQueue}", action="batch")
        node.tasks = [
            {"value": "{batchQueue}"}
        ]

        executor.execute(node, runtime.execution_context)

        # Tasks should have databinding resolved
        batch = runtime._jobs_service.last_batch
        assert batch["tasks"][0]["value"] == "high-priority"


class TestResultStorage:
    """Test result storage"""

    def test_stores_define_result(self):
        """Test that define result is stored"""
        runtime = MockJobsRuntime()
        executor = JobExecutor(runtime)

        node = JobNode(name="myJob", queue="default", action="define")

        executor.execute(node, runtime.execution_context)

        stored = runtime.execution_context.get_variable("myJob_job")
        assert stored["defined"] is True

    def test_stores_dispatch_result(self):
        """Test that dispatch result is stored"""
        runtime = MockJobsRuntime()
        executor = JobExecutor(runtime)

        node = JobNode(name="sendEmail", queue="emails", action="dispatch")

        executor.execute(node, runtime.execution_context)

        stored = runtime.execution_context.get_variable("sendEmail_job")
        assert stored["jobId"] == "job-123"
        assert stored["queued"] is True


class TestErrorHandling:
    """Test error handling"""

    def test_unknown_action_raises_error(self):
        """Test that unknown action raises error"""
        runtime = MockJobsRuntime()
        executor = JobExecutor(runtime)

        node = JobNode(name="test", queue="default", action="invalid")

        with pytest.raises(ExecutorError, match="Unknown job action"):
            executor.execute(node, runtime.execution_context)

    def test_dispatch_error_wrapped(self):
        """Test that dispatch error is wrapped"""
        runtime = MockJobsRuntime()
        runtime._jobs_service.dispatch = MagicMock(
            side_effect=Exception("Queue full")
        )
        executor = JobExecutor(runtime)

        node = JobNode(name="test", queue="tasks", action="dispatch")

        with pytest.raises(ExecutorError, match="Job execution error"):
            executor.execute(node, runtime.execution_context)

