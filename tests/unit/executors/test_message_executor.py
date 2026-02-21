"""
Tests for MessageExecutor - q:message messaging operations

Coverage target: 19% -> 60%
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from runtime.executors.messaging.message_executor import MessageExecutor, SubscribeExecutor
from runtime.executors.base import ExecutorError
from core.ast_nodes import MessageNode, SubscribeNode

# Import fixtures from conftest.py
from tests.unit.executors.conftest import MockRuntime, MockExecutionContext


# =============================================================================
# Mock Objects for Messaging Service
# =============================================================================

class MockMessagingService:
    """Mock messaging service"""

    def __init__(self):
        self.last_publish = None
        self.last_send = None
        self.last_request = None
        self.last_subscribe = None
        self._results = {}

    def set_result(self, key: str, result: Dict):
        """Set mock result"""
        self._results[key] = result

    def publish(self, topic: str, body: Any, headers: Dict = None) -> Dict:
        """Mock publish"""
        self.last_publish = {
            'topic': topic,
            'body': body,
            'headers': headers or {}
        }
        return {'success': True, 'messageId': 'msg-123'}

    def send(self, queue: str, body: Any, headers: Dict = None) -> Dict:
        """Mock send"""
        self.last_send = {
            'queue': queue,
            'body': body,
            'headers': headers or {}
        }
        return {'success': True, 'messageId': 'msg-456'}

    def request(self, queue: str, body: Any, headers: Dict = None, timeout: int = 30000) -> Dict:
        """Mock request/reply"""
        self.last_request = {
            'queue': queue,
            'body': body,
            'headers': headers or {},
            'timeout': timeout
        }
        return {'success': True, 'response': {'data': 'reply'}}

    def subscribe(self, name: str, topics: List[str] = None, queue: str = None,
                  ack: str = 'auto', prefetch: int = 10, handlers: Dict = None) -> Dict:
        """Mock subscribe"""
        self.last_subscribe = {
            'name': name,
            'topics': topics or [],
            'queue': queue,
            'ack': ack,
            'prefetch': prefetch,
            'handlers': handlers or {}
        }
        return {'name': name, 'active': True, 'subscriptionId': 'sub-789'}


class MockMessagingRuntime(MockRuntime):
    """Extended mock runtime with messaging service"""

    def __init__(self, variables: Dict[str, Any] = None):
        super().__init__(variables)
        self._messaging_service = MockMessagingService()
        self._services = MagicMock()
        self._services.messaging = self._messaging_service

    @property
    def services(self):
        return self._services


# =============================================================================
# Mock Header Node
# =============================================================================

@dataclass
class MockHeaderNode:
    """Mock header node"""
    name: str
    value: str


# =============================================================================
# Test Classes - MessageExecutor
# =============================================================================

class TestMessageExecutorBasic:
    """Basic functionality tests"""

    def test_handles_message_node(self):
        """Test that MessageExecutor handles MessageNode"""
        runtime = MockMessagingRuntime()
        executor = MessageExecutor(runtime)
        assert MessageNode in executor.handles

    def test_handles_returns_list(self):
        """Test that handles returns a list"""
        runtime = MockMessagingRuntime()
        executor = MessageExecutor(runtime)
        assert isinstance(executor.handles, list)
        assert len(executor.handles) == 1


class TestPublishMessage:
    """Test publish message type"""

    def test_publish_basic(self):
        """Test basic publish"""
        runtime = MockMessagingRuntime()
        executor = MessageExecutor(runtime)

        node = MessageNode()
        node.name = "result"
        node.type = "publish"
        node.topic = "events.user.created"
        node.body = "userId: 123"  # Plain text to avoid databinding issues
        node.headers = []

        executor.execute(node, runtime.execution_context)

        publish = runtime._messaging_service.last_publish
        assert publish["topic"] == "events.user.created"
        assert publish["body"] == "userId: 123"

    def test_publish_with_databinding(self):
        """Test publish with databinding in topic and body"""
        runtime = MockMessagingRuntime({"eventType": "order.created", "orderId": 456})
        executor = MessageExecutor(runtime)

        node = MessageNode()
        node.name = "result"
        node.type = "publish"
        node.topic = "events.{eventType}"
        node.body = "Order {orderId}"
        node.headers = []

        executor.execute(node, runtime.execution_context)

        publish = runtime._messaging_service.last_publish
        assert publish["topic"] == "events.order.created"
        assert "456" in publish["body"]

    def test_publish_with_headers(self):
        """Test publish with headers"""
        runtime = MockMessagingRuntime({"correlationId": "abc-123"})
        executor = MessageExecutor(runtime)

        node = MessageNode()
        node.name = "result"
        node.type = "publish"
        node.topic = "events"
        node.body = "test"
        node.headers = [
            MockHeaderNode("x-correlation-id", "{correlationId}"),
            MockHeaderNode("content-type", "application/json")
        ]

        executor.execute(node, runtime.execution_context)

        headers = runtime._messaging_service.last_publish["headers"]
        assert headers["x-correlation-id"] == "abc-123"
        assert headers["content-type"] == "application/json"


class TestSendMessage:
    """Test send message type (direct queue)"""

    def test_send_basic(self):
        """Test basic send to queue"""
        runtime = MockMessagingRuntime()
        executor = MessageExecutor(runtime)

        node = MessageNode()
        node.name = "result"
        node.type = "send"
        node.queue = "tasks"
        node.body = "Do work"
        node.headers = []

        executor.execute(node, runtime.execution_context)

        send = runtime._messaging_service.last_send
        assert send["queue"] == "tasks"
        assert send["body"] == "Do work"

    def test_send_with_databinding(self):
        """Test send with databinding"""
        runtime = MockMessagingRuntime({"queueName": "priority-tasks"})
        executor = MessageExecutor(runtime)

        node = MessageNode()
        node.name = "result"
        node.type = "send"
        node.queue = "{queueName}"
        node.body = "urgent task"
        node.headers = []

        executor.execute(node, runtime.execution_context)

        assert runtime._messaging_service.last_send["queue"] == "priority-tasks"


class TestRequestMessage:
    """Test request/reply message type"""

    def test_request_basic(self):
        """Test basic request/reply"""
        runtime = MockMessagingRuntime()
        executor = MessageExecutor(runtime)

        node = MessageNode()
        node.name = "result"
        node.type = "request"
        node.queue = "rpc.calculate"
        node.body = '{"operation": "sum", "values": [1,2,3]}'
        node.timeout = 5000
        node.headers = []

        executor.execute(node, runtime.execution_context)

        request = runtime._messaging_service.last_request
        assert request["queue"] == "rpc.calculate"
        assert request["timeout"] == 5000

    def test_request_default_timeout(self):
        """Test request with default timeout"""
        runtime = MockMessagingRuntime()
        executor = MessageExecutor(runtime)

        node = MessageNode()
        node.name = "result"
        node.type = "request"
        node.queue = "rpc.service"
        node.body = "test"
        node.timeout = None  # Should default to 30000
        node.headers = []

        executor.execute(node, runtime.execution_context)

        assert runtime._messaging_service.last_request["timeout"] == 30000


class TestMessageResultStorage:
    """Test result storage"""

    def test_stores_result(self):
        """Test that result is stored"""
        runtime = MockMessagingRuntime()
        executor = MessageExecutor(runtime)

        node = MessageNode()
        node.name = "myMessage"
        node.type = "publish"
        node.topic = "test"
        node.body = "data"
        node.headers = []

        executor.execute(node, runtime.execution_context)

        stored = runtime.execution_context.get_variable("myMessage")
        assert stored["success"] is True
        assert "messageId" in stored

    def test_no_name_skips_storage(self):
        """Test that missing name skips storage"""
        runtime = MockMessagingRuntime()
        executor = MessageExecutor(runtime)

        node = MessageNode()
        node.name = None
        node.type = "publish"
        node.topic = "test"
        node.body = "data"
        node.headers = []

        # Should not raise
        executor.execute(node, runtime.execution_context)


class TestMessageErrorHandling:
    """Test error handling"""

    def test_unknown_type_raises_error(self):
        """Test that unknown message type raises error"""
        runtime = MockMessagingRuntime()
        executor = MessageExecutor(runtime)

        node = MessageNode()
        node.name = "result"
        node.type = "unknown"
        node.headers = []

        with pytest.raises(ExecutorError, match="Unknown message type"):
            executor.execute(node, runtime.execution_context)

    def test_error_stores_failure(self):
        """Test that error stores failure info"""
        runtime = MockMessagingRuntime()
        runtime._messaging_service.publish = MagicMock(
            side_effect=Exception("Broker unavailable")
        )
        executor = MessageExecutor(runtime)

        node = MessageNode()
        node.name = "result"
        node.type = "publish"
        node.topic = "test"
        node.body = "data"
        node.headers = []

        with pytest.raises(ExecutorError, match="Message operation error"):
            executor.execute(node, runtime.execution_context)

        error_info = runtime.execution_context.get_variable("result")
        assert error_info["success"] is False
        assert "Broker unavailable" in error_info["error"]


# =============================================================================
# Test Classes - SubscribeExecutor
# =============================================================================

class TestSubscribeExecutorBasic:
    """Basic functionality tests"""

    def test_handles_subscribe_node(self):
        """Test that SubscribeExecutor handles SubscribeNode"""
        runtime = MockMessagingRuntime()
        executor = SubscribeExecutor(runtime)
        assert SubscribeNode in executor.handles


class TestSubscribeTopic:
    """Test topic subscription"""

    def test_subscribe_single_topic(self):
        """Test subscribing to single topic"""
        runtime = MockMessagingRuntime()
        executor = SubscribeExecutor(runtime)

        node = SubscribeNode()
        node.name = "mySub"
        node.topic = "events.user.*"
        node.topics = None
        node.queue = None
        node.ack = "auto"
        node.prefetch = 10
        node.on_message = []
        node.on_error = []

        executor.execute(node, runtime.execution_context)

        sub = runtime._messaging_service.last_subscribe
        assert sub["name"] == "mySub"
        assert "events.user.*" in sub["topics"]

    def test_subscribe_multiple_topics(self):
        """Test subscribing to multiple topics"""
        runtime = MockMessagingRuntime()
        executor = SubscribeExecutor(runtime)

        node = SubscribeNode()
        node.name = "mySub"
        node.topic = None
        node.topics = "events.user.*, events.order.*, events.payment.*"
        node.queue = None
        node.ack = "auto"
        node.prefetch = 10
        node.on_message = []
        node.on_error = []

        executor.execute(node, runtime.execution_context)

        topics = runtime._messaging_service.last_subscribe["topics"]
        assert len(topics) == 3

    def test_subscribe_with_databinding(self):
        """Test subscription topic with databinding"""
        runtime = MockMessagingRuntime({"topicPattern": "events.user.created"})
        executor = SubscribeExecutor(runtime)

        node = SubscribeNode()
        node.name = "sub"
        node.topic = "{topicPattern}"
        node.topics = None
        node.queue = None
        node.ack = "auto"
        node.prefetch = 10
        node.on_message = []
        node.on_error = []

        executor.execute(node, runtime.execution_context)

        assert "events.user.created" in runtime._messaging_service.last_subscribe["topics"]


class TestSubscribeQueue:
    """Test queue subscription"""

    def test_subscribe_queue(self):
        """Test subscribing to queue"""
        runtime = MockMessagingRuntime()
        executor = SubscribeExecutor(runtime)

        node = SubscribeNode()
        node.name = "worker"
        node.topic = None
        node.topics = None
        node.queue = "tasks"
        node.ack = "manual"
        node.prefetch = 5
        node.on_message = []
        node.on_error = []

        executor.execute(node, runtime.execution_context)

        sub = runtime._messaging_service.last_subscribe
        assert sub["queue"] == "tasks"
        assert sub["ack"] == "manual"
        assert sub["prefetch"] == 5


class TestSubscribeHandlers:
    """Test subscription handlers"""

    def test_handlers_passed(self):
        """Test that handlers are passed"""
        runtime = MockMessagingRuntime()
        executor = SubscribeExecutor(runtime)

        node = SubscribeNode()
        node.name = "sub"
        node.topic = "events"
        node.topics = None
        node.queue = None
        node.ack = "auto"
        node.prefetch = 10
        node.on_message = [{"type": "set"}]
        node.on_error = [{"type": "log"}]

        executor.execute(node, runtime.execution_context)

        handlers = runtime._messaging_service.last_subscribe["handlers"]
        assert "on_message" in handlers
        assert "on_error" in handlers


class TestSubscribeResultStorage:
    """Test result storage"""

    def test_stores_subscription_reference(self):
        """Test that subscription reference is stored"""
        runtime = MockMessagingRuntime()
        executor = SubscribeExecutor(runtime)

        node = SubscribeNode()
        node.name = "mySub"
        node.topic = "events"
        node.topics = None
        node.queue = None
        node.ack = "auto"
        node.prefetch = 10
        node.on_message = []
        node.on_error = []

        executor.execute(node, runtime.execution_context)

        stored = runtime.execution_context.get_variable("mySub")
        assert stored["active"] is True
        assert stored["subscriptionId"] == "sub-789"


class TestSubscribeErrorHandling:
    """Test error handling"""

    def test_error_stores_failure(self):
        """Test that error stores failure info"""
        runtime = MockMessagingRuntime()
        runtime._messaging_service.subscribe = MagicMock(
            side_effect=Exception("Topic not found")
        )
        executor = SubscribeExecutor(runtime)

        node = SubscribeNode()
        node.name = "sub"
        node.topic = "invalid"
        node.topics = None
        node.queue = None
        node.ack = "auto"
        node.prefetch = 10
        node.on_message = []
        node.on_error = []

        with pytest.raises(ExecutorError, match="Subscription error"):
            executor.execute(node, runtime.execution_context)

        error_info = runtime.execution_context.get_variable("sub")
        assert error_info["active"] is False
        assert "Topic not found" in error_info["error"]

