"""
Tests for QueueExecutor - q:queue queue management operations

Coverage target: 29% -> 60%
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from runtime.executors.messaging.queue_executor import QueueExecutor
from runtime.executors.base import ExecutorError
from core.ast_nodes import QueueNode

# Import fixtures from conftest.py
from tests.unit.executors.conftest import MockRuntime, MockExecutionContext


# =============================================================================
# Mock Objects for Queue Service
# =============================================================================

class MockQueueService:
    """Mock queue management service"""

    def __init__(self):
        self.last_declare = None
        self.last_purge = None
        self.last_delete = None
        self.last_info = None

    def declare_queue(self, name: str, durable: bool = True, exclusive: bool = False,
                      auto_delete: bool = False, dead_letter_queue: str = None,
                      ttl: int = None, max_length: int = None) -> Dict:
        """Mock queue declaration"""
        self.last_declare = {
            'name': name,
            'durable': durable,
            'exclusive': exclusive,
            'auto_delete': auto_delete,
            'dead_letter_queue': dead_letter_queue,
            'ttl': ttl,
            'max_length': max_length
        }
        return {'name': name, 'created': True, 'messageCount': 0}

    def purge_queue(self, name: str) -> Dict:
        """Mock queue purge"""
        self.last_purge = name
        return {'name': name, 'purged': True, 'messagesRemoved': 10}

    def delete_queue(self, name: str) -> Dict:
        """Mock queue delete"""
        self.last_delete = name
        return {'name': name, 'deleted': True}

    def queue_info(self, name: str) -> Dict:
        """Mock queue info"""
        self.last_info = name
        return {
            'name': name,
            'messageCount': 100,
            'consumerCount': 2,
            'durable': True
        }


class MockQueueRuntime(MockRuntime):
    """Extended mock runtime with queue service"""

    def __init__(self, variables: Dict[str, Any] = None):
        super().__init__(variables)
        self._queue_service = MockQueueService()
        self._services = MagicMock()
        self._services.messaging = self._queue_service

    @property
    def services(self):
        return self._services


# =============================================================================
# Test Classes
# =============================================================================

class TestQueueExecutorBasic:
    """Basic functionality tests"""

    def test_handles_queue_node(self):
        """Test that QueueExecutor handles QueueNode"""
        runtime = MockQueueRuntime()
        executor = QueueExecutor(runtime)
        assert QueueNode in executor.handles

    def test_handles_returns_list(self):
        """Test that handles returns a list"""
        runtime = MockQueueRuntime()
        executor = QueueExecutor(runtime)
        assert isinstance(executor.handles, list)
        assert len(executor.handles) == 1


class TestDeclareAction:
    """Test queue declare action"""

    def test_declare_basic(self):
        """Test basic queue declaration"""
        runtime = MockQueueRuntime()
        executor = QueueExecutor(runtime)

        node = QueueNode()
        node.name = "tasks"
        node.action = "declare"

        executor.execute(node, runtime.execution_context)

        declare = runtime._queue_service.last_declare
        assert declare["name"] == "tasks"
        assert declare["durable"] is True

    def test_declare_with_databinding(self):
        """Test declare with name databinding"""
        runtime = MockQueueRuntime({"queueName": "priority-tasks"})
        executor = QueueExecutor(runtime)

        node = QueueNode()
        node.name = "{queueName}"
        node.action = "declare"

        executor.execute(node, runtime.execution_context)

        assert runtime._queue_service.last_declare["name"] == "priority-tasks"

    def test_declare_not_durable(self):
        """Test declare with durable=False"""
        runtime = MockQueueRuntime()
        executor = QueueExecutor(runtime)

        node = QueueNode()
        node.name = "temp"
        node.action = "declare"
        node.durable = False

        executor.execute(node, runtime.execution_context)

        assert runtime._queue_service.last_declare["durable"] is False

    def test_declare_exclusive(self):
        """Test declare exclusive queue"""
        runtime = MockQueueRuntime()
        executor = QueueExecutor(runtime)

        node = QueueNode()
        node.name = "private"
        node.action = "declare"
        node.exclusive = True

        executor.execute(node, runtime.execution_context)

        assert runtime._queue_service.last_declare["exclusive"] is True

    def test_declare_auto_delete(self):
        """Test declare auto-delete queue"""
        runtime = MockQueueRuntime()
        executor = QueueExecutor(runtime)

        node = QueueNode()
        node.name = "transient"
        node.action = "declare"
        node.auto_delete = True

        executor.execute(node, runtime.execution_context)

        assert runtime._queue_service.last_declare["auto_delete"] is True

    def test_declare_with_dead_letter_queue(self):
        """Test declare with dead letter queue"""
        runtime = MockQueueRuntime({"dlq": "tasks-dlq"})
        executor = QueueExecutor(runtime)

        node = QueueNode()
        node.name = "tasks"
        node.action = "declare"
        node.dead_letter = "{dlq}"

        executor.execute(node, runtime.execution_context)

        assert runtime._queue_service.last_declare["dead_letter_queue"] == "tasks-dlq"

    def test_declare_with_ttl(self):
        """Test declare with message TTL"""
        runtime = MockQueueRuntime()
        executor = QueueExecutor(runtime)

        node = QueueNode()
        node.name = "expiring"
        node.action = "declare"
        node.ttl = 60000

        executor.execute(node, runtime.execution_context)

        assert runtime._queue_service.last_declare["ttl"] == 60000

    def test_declare_with_max_length(self):
        """Test declare with max length"""
        runtime = MockQueueRuntime()
        executor = QueueExecutor(runtime)

        node = QueueNode()
        node.name = "limited"
        node.action = "declare"
        node.max_length = 1000

        executor.execute(node, runtime.execution_context)

        assert runtime._queue_service.last_declare["max_length"] == 1000


class TestPurgeAction:
    """Test queue purge action"""

    def test_purge_queue(self):
        """Test queue purge"""
        runtime = MockQueueRuntime()
        executor = QueueExecutor(runtime)

        node = QueueNode()
        node.name = "tasks"
        node.action = "purge"

        executor.execute(node, runtime.execution_context)

        assert runtime._queue_service.last_purge == "tasks"

    def test_purge_with_databinding(self):
        """Test purge with name databinding"""
        runtime = MockQueueRuntime({"queueToPurge": "old-tasks"})
        executor = QueueExecutor(runtime)

        node = QueueNode()
        node.name = "{queueToPurge}"
        node.action = "purge"

        executor.execute(node, runtime.execution_context)

        assert runtime._queue_service.last_purge == "old-tasks"


class TestDeleteAction:
    """Test queue delete action"""

    def test_delete_queue(self):
        """Test queue delete"""
        runtime = MockQueueRuntime()
        executor = QueueExecutor(runtime)

        node = QueueNode()
        node.name = "obsolete"
        node.action = "delete"

        executor.execute(node, runtime.execution_context)

        assert runtime._queue_service.last_delete == "obsolete"


class TestInfoAction:
    """Test queue info action"""

    def test_get_queue_info(self):
        """Test getting queue info"""
        runtime = MockQueueRuntime()
        executor = QueueExecutor(runtime)

        node = QueueNode()
        node.name = "tasks"
        node.action = "info"

        result = executor.execute(node, runtime.execution_context)

        assert runtime._queue_service.last_info == "tasks"
        assert result["messageCount"] == 100
        assert result["consumerCount"] == 2


class TestResultStorage:
    """Test result storage"""

    def test_stores_result_default_name(self):
        """Test result stored in default variable"""
        runtime = MockQueueRuntime()
        executor = QueueExecutor(runtime)

        node = QueueNode()
        node.name = "myQueue"
        node.action = "info"

        executor.execute(node, runtime.execution_context)

        stored = runtime.execution_context.get_variable("myQueue_result")
        assert stored is not None
        assert stored["name"] == "myQueue"

    def test_stores_result_custom_name(self):
        """Test result stored in custom variable"""
        runtime = MockQueueRuntime()
        executor = QueueExecutor(runtime)

        node = QueueNode()
        node.name = "tasks"
        node.action = "info"
        node.result = "queueInfo"

        executor.execute(node, runtime.execution_context)

        stored = runtime.execution_context.get_variable("queueInfo")
        assert stored is not None


class TestErrorHandling:
    """Test error handling"""

    def test_unknown_action_raises_error(self):
        """Test that unknown action raises error"""
        runtime = MockQueueRuntime()
        executor = QueueExecutor(runtime)

        node = QueueNode()
        node.name = "test"
        node.action = "unknown"

        with pytest.raises(ExecutorError, match="Unknown queue action"):
            executor.execute(node, runtime.execution_context)

    def test_declare_error_wrapped(self):
        """Test that declare error is wrapped"""
        runtime = MockQueueRuntime()
        runtime._queue_service.declare_queue = MagicMock(
            side_effect=Exception("Connection refused")
        )
        executor = QueueExecutor(runtime)

        node = QueueNode()
        node.name = "test"
        node.action = "declare"

        with pytest.raises(ExecutorError, match="Queue operation error"):
            executor.execute(node, runtime.execution_context)

