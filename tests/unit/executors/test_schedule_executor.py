"""
Tests for ScheduleExecutor - q:schedule scheduled task execution

Rewritten 2026-09-07: the previous version mocked a services.scheduler
service with schedule()/pause()/resume()/delete() — none of which exist.
Schedules live on services.job_executor.schedule (a ScheduleService) with
add_schedule()/pause_schedule()/resume_schedule()/remove_schedule(), and
add_schedule() takes a *callback*, not a config dict. See
FULL_AUDIT_2026-09.md, Cluster C.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock
from typing import Any, Dict, Optional

from quantum.runtime.executors.jobs.schedule_executor import ScheduleExecutor
from quantum.runtime.executors.base import ExecutorError
from quantum.runtime.job_executor import ScheduleInfo
from quantum.core.ast_nodes import ScheduleNode, QuantumReturn

from tests.unit.executors.conftest import MockRuntime


class MockScheduleService:
    """Mirrors the real ScheduleService interface."""

    def __init__(self):
        self.last_kwargs: Optional[Dict[str, Any]] = None
        self.paused = []
        self.resumed = []
        self.removed = []

    def add_schedule(self, name, callback, interval=None, cron=None, at=None,
                     timezone='UTC', enabled=True, overlap=False) -> ScheduleInfo:
        self.last_kwargs = dict(name=name, callback=callback, interval=interval,
                                cron=cron, at=at, timezone=timezone,
                                enabled=enabled, overlap=overlap)
        trigger = interval or cron or at or ''
        return ScheduleInfo(name=name, trigger_type='interval' if interval else 'cron',
                            trigger_info=str(trigger), next_run=datetime(2026, 1, 1),
                            enabled=enabled)

    def pause_schedule(self, name):
        self.paused.append(name)
        return True

    def resume_schedule(self, name):
        self.resumed.append(name)
        return True

    def remove_schedule(self, name):
        self.removed.append(name)
        return True


class MockScheduleRuntime(MockRuntime):
    def __init__(self, variables: Dict[str, Any] = None):
        super().__init__(variables)
        self._schedule_service = MockScheduleService()
        self._services = MagicMock()
        self._services.job_executor.schedule = self._schedule_service

    @property
    def services(self):
        return self._services


class TestScheduleExecutorBasic:
    def test_handles_schedule_node(self):
        executor = ScheduleExecutor(MockScheduleRuntime())
        assert ScheduleNode in executor.handles

    def test_handles_returns_list(self):
        executor = ScheduleExecutor(MockScheduleRuntime())
        assert isinstance(executor.handles, list)
        assert len(executor.handles) == 1


class TestScheduleRun:
    def test_run_with_interval(self):
        runtime = MockScheduleRuntime()
        executor = ScheduleExecutor(runtime)

        node = ScheduleNode(name="cleanup", interval="5m")
        executor.execute(node, runtime.execution_context)

        kwargs = runtime._schedule_service.last_kwargs
        assert kwargs["name"] == "cleanup"
        assert kwargs["interval"] == "5m"
        assert callable(kwargs["callback"])

    def test_run_with_cron(self):
        runtime = MockScheduleRuntime()
        executor = ScheduleExecutor(runtime)

        node = ScheduleNode(name="nightly", cron="0 2 * * *")
        executor.execute(node, runtime.execution_context)

        assert runtime._schedule_service.last_kwargs["cron"] == "0 2 * * *"

    def test_run_with_at(self):
        runtime = MockScheduleRuntime()
        executor = ScheduleExecutor(runtime)

        node = ScheduleNode(name="once", at="2026-01-01T00:00:00")
        executor.execute(node, runtime.execution_context)

        assert runtime._schedule_service.last_kwargs["at"] == "2026-01-01T00:00:00"

    def test_run_with_databinding(self):
        runtime = MockScheduleRuntime({"freq": "10m"})
        executor = ScheduleExecutor(runtime)

        node = ScheduleNode(name="dynamic", interval="{freq}")
        executor.execute(node, runtime.execution_context)

        assert runtime._schedule_service.last_kwargs["interval"] == "10m"

    def test_overlap_and_enabled_passed(self):
        runtime = MockScheduleRuntime()
        executor = ScheduleExecutor(runtime)

        node = ScheduleNode(name="job", interval="1h", overlap=True, enabled=False)
        executor.execute(node, runtime.execution_context)

        kwargs = runtime._schedule_service.last_kwargs
        assert kwargs["overlap"] is True
        assert kwargs["enabled"] is False

    def test_timezone_defaults_to_utc(self):
        runtime = MockScheduleRuntime()
        executor = ScheduleExecutor(runtime)

        node = ScheduleNode(name="job", interval="1h")
        executor.execute(node, runtime.execution_context)

        assert runtime._schedule_service.last_kwargs["timezone"] == "UTC"


class TestScheduleCallback:
    """The callback is what actually runs the q:schedule body."""

    def test_callback_runs_body(self):
        runtime = MockScheduleRuntime({"x": 7})
        executor = ScheduleExecutor(runtime)

        node = ScheduleNode(name="job", interval="1m")
        node.body = [QuantumReturn(value="{x}")]

        executor.execute(node, runtime.execution_context)
        callback = runtime._schedule_service.last_kwargs["callback"]

        assert callback() == 7


class TestScheduleActions:
    def test_pause_schedule(self):
        runtime = MockScheduleRuntime()
        executor = ScheduleExecutor(runtime)

        result = executor.execute(ScheduleNode(name="job", action="pause"),
                                   runtime.execution_context)

        assert runtime._schedule_service.paused == ["job"]
        assert result["success"] is True

    def test_resume_schedule(self):
        runtime = MockScheduleRuntime()
        executor = ScheduleExecutor(runtime)

        executor.execute(ScheduleNode(name="job", action="resume"),
                         runtime.execution_context)

        assert runtime._schedule_service.resumed == ["job"]

    def test_delete_schedule_calls_remove_schedule(self):
        runtime = MockScheduleRuntime()
        executor = ScheduleExecutor(runtime)

        executor.execute(ScheduleNode(name="job", action="delete"),
                         runtime.execution_context)

        assert runtime._schedule_service.removed == ["job"]


class TestScheduleResultStorage:
    def test_stores_result(self):
        runtime = MockScheduleRuntime()
        executor = ScheduleExecutor(runtime)

        node = ScheduleNode(name="cleanup", interval="5m")
        executor.execute(node, runtime.execution_context)

        stored = runtime.execution_context.get_variable("cleanup_schedule")
        assert stored["name"] == "cleanup"
        assert stored["triggerInfo"] == "5m"
        assert stored["enabled"] is True


class TestScheduleErrorHandling:
    def test_unknown_action_raises_error(self):
        runtime = MockScheduleRuntime()
        executor = ScheduleExecutor(runtime)

        with pytest.raises(ExecutorError, match="Unknown schedule action"):
            executor.execute(ScheduleNode(name="job", action="bogus"),
                             runtime.execution_context)

    def test_service_error_wrapped(self):
        runtime = MockScheduleRuntime()
        runtime._schedule_service.add_schedule = MagicMock(
            side_effect=Exception("APScheduler unavailable")
        )
        executor = ScheduleExecutor(runtime)

        with pytest.raises(ExecutorError, match="Schedule execution error"):
            executor.execute(ScheduleNode(name="job", interval="1m"),
                             runtime.execution_context)
