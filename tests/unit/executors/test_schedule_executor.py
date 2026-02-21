"""
Tests for ScheduleExecutor - q:schedule scheduled task execution

Coverage target: 29% -> 60%
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from runtime.executors.jobs.schedule_executor import ScheduleExecutor
from runtime.executors.base import ExecutorError
from core.ast_nodes import ScheduleNode

# Import fixtures from conftest.py
from tests.unit.executors.conftest import MockRuntime, MockExecutionContext


# =============================================================================
# Mock Objects for Scheduler Service
# =============================================================================

class MockSchedulerService:
    """Mock scheduler service"""

    def __init__(self):
        self.last_schedule = None
        self.last_pause = None
        self.last_resume = None
        self.last_delete = None

    def schedule(self, config: Dict) -> Dict:
        """Mock schedule creation"""
        self.last_schedule = config
        return {
            'name': config['name'],
            'scheduled': True,
            'nextRun': '2024-01-01T00:00:00Z'
        }

    def pause(self, name: str) -> Dict:
        """Mock pause"""
        self.last_pause = name
        return {'name': name, 'paused': True}

    def resume(self, name: str) -> Dict:
        """Mock resume"""
        self.last_resume = name
        return {'name': name, 'resumed': True}

    def delete(self, name: str) -> Dict:
        """Mock delete"""
        self.last_delete = name
        return {'name': name, 'deleted': True}


class MockSchedulerRuntime(MockRuntime):
    """Extended mock runtime with scheduler service"""

    def __init__(self, variables: Dict[str, Any] = None):
        super().__init__(variables)
        self._scheduler_service = MockSchedulerService()
        self._services = MagicMock()
        self._services.scheduler = self._scheduler_service

    @property
    def services(self):
        return self._services


# =============================================================================
# Test Classes
# =============================================================================

class TestScheduleExecutorBasic:
    """Basic functionality tests"""

    def test_handles_schedule_node(self):
        """Test that ScheduleExecutor handles ScheduleNode"""
        runtime = MockSchedulerRuntime()
        executor = ScheduleExecutor(runtime)
        assert ScheduleNode in executor.handles

    def test_handles_returns_list(self):
        """Test that handles returns a list"""
        runtime = MockSchedulerRuntime()
        executor = ScheduleExecutor(runtime)
        assert isinstance(executor.handles, list)
        assert len(executor.handles) == 1


class TestRunAction:
    """Test schedule run action"""

    def test_run_with_interval(self):
        """Test scheduling with interval"""
        runtime = MockSchedulerRuntime()
        executor = ScheduleExecutor(runtime)

        # ScheduleNode is dataclass with name as first required arg
        node = ScheduleNode(name="cleanup")
        node.action = "run"
        node.interval = "5m"

        executor.execute(node, runtime.execution_context)

        config = runtime._scheduler_service.last_schedule
        assert config["name"] == "cleanup"
        assert config["interval"] == "5m"

    def test_run_with_cron(self):
        """Test scheduling with cron expression"""
        runtime = MockSchedulerRuntime()
        executor = ScheduleExecutor(runtime)

        node = ScheduleNode(name="daily-report")
        node.action = "run"
        node.cron = "0 9 * * *"
        node.timezone = "America/Sao_Paulo"
        node.retry = 3

        executor.execute(node, runtime.execution_context)

        config = runtime._scheduler_service.last_schedule
        assert config["cron"] == "0 9 * * *"
        assert config["timezone"] == "America/Sao_Paulo"
        assert config["retry"] == 3

    def test_run_with_at(self):
        """Test scheduling one-time execution"""
        runtime = MockSchedulerRuntime()
        executor = ScheduleExecutor(runtime)

        node = ScheduleNode(name="one-time")
        node.action = "run"
        node.at = "2024-12-31T23:59:00Z"

        executor.execute(node, runtime.execution_context)

        config = runtime._scheduler_service.last_schedule
        assert config["at"] == "2024-12-31T23:59:00Z"

    def test_run_with_databinding(self):
        """Test scheduling with databinding"""
        runtime = MockSchedulerRuntime({"intervalValue": "10m"})
        executor = ScheduleExecutor(runtime)

        node = ScheduleNode(name="task")
        node.action = "run"
        node.interval = "{intervalValue}"

        executor.execute(node, runtime.execution_context)

        assert runtime._scheduler_service.last_schedule["interval"] == "10m"

    def test_run_with_overlap(self):
        """Test scheduling allowing overlap"""
        runtime = MockSchedulerRuntime()
        executor = ScheduleExecutor(runtime)

        node = ScheduleNode(name="concurrent")
        node.action = "run"
        node.interval = "1s"
        node.overlap = True

        executor.execute(node, runtime.execution_context)

        assert runtime._scheduler_service.last_schedule["overlap"] is True

    def test_run_disabled(self):
        """Test scheduling disabled task"""
        runtime = MockSchedulerRuntime()
        executor = ScheduleExecutor(runtime)

        node = ScheduleNode(name="paused-task")
        node.action = "run"
        node.interval = "1h"
        node.enabled = False

        executor.execute(node, runtime.execution_context)

        assert runtime._scheduler_service.last_schedule["enabled"] is False


class TestPauseAction:
    """Test schedule pause action"""

    def test_pause_schedule(self):
        """Test pausing a schedule"""
        runtime = MockSchedulerRuntime()
        executor = ScheduleExecutor(runtime)

        node = ScheduleNode(name="my-task")
        node.action = "pause"

        executor.execute(node, runtime.execution_context)

        assert runtime._scheduler_service.last_pause == "my-task"


class TestResumeAction:
    """Test schedule resume action"""

    def test_resume_schedule(self):
        """Test resuming a schedule"""
        runtime = MockSchedulerRuntime()
        executor = ScheduleExecutor(runtime)

        node = ScheduleNode(name="my-task")
        node.action = "resume"

        executor.execute(node, runtime.execution_context)

        assert runtime._scheduler_service.last_resume == "my-task"


class TestDeleteAction:
    """Test schedule delete action"""

    def test_delete_schedule(self):
        """Test deleting a schedule"""
        runtime = MockSchedulerRuntime()
        executor = ScheduleExecutor(runtime)

        node = ScheduleNode(name="old-task")
        node.action = "delete"

        executor.execute(node, runtime.execution_context)

        assert runtime._scheduler_service.last_delete == "old-task"


class TestResultStorage:
    """Test result storage"""

    def test_stores_result(self):
        """Test that result is stored"""
        runtime = MockSchedulerRuntime()
        executor = ScheduleExecutor(runtime)

        node = ScheduleNode(name="myTask")
        node.action = "run"
        node.interval = "5m"

        executor.execute(node, runtime.execution_context)

        stored = runtime.execution_context.get_variable("myTask_schedule")
        assert stored["scheduled"] is True
        assert "nextRun" in stored


class TestErrorHandling:
    """Test error handling"""

    def test_unknown_action_raises_error(self):
        """Test that unknown action raises error"""
        runtime = MockSchedulerRuntime()
        executor = ScheduleExecutor(runtime)

        node = ScheduleNode(name="test")
        node.action = "invalid"

        with pytest.raises(ExecutorError, match="Unknown schedule action"):
            executor.execute(node, runtime.execution_context)

    def test_schedule_error_wrapped(self):
        """Test that schedule error is wrapped"""
        runtime = MockSchedulerRuntime()
        runtime._scheduler_service.schedule = MagicMock(
            side_effect=Exception("Invalid cron expression")
        )
        executor = ScheduleExecutor(runtime)

        node = ScheduleNode(name="test")
        node.action = "run"
        node.cron = "invalid"

        with pytest.raises(ExecutorError, match="Schedule execution error"):
            executor.execute(node, runtime.execution_context)

