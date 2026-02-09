"""
Tests for the Quantum Message Queue System

Tests cover:
- AST nodes for message queue operations
- Parser for message queue tags
- In-memory message broker adapter
- Message queue service integration
- Component runtime execution
"""

import pytest
import time
import threading
from pathlib import Path
import sys

# Fix imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.ast_nodes import (
    MessageNode, MessageHeaderNode, SubscribeNode, QueueNode,
    MessageAckNode, MessageNackNode
)
from core.parser import QuantumParser
from runtime.message_broker import Message, QueueInfo
from runtime.adapters.memory_adapter import MemoryAdapter
from runtime.message_queue_service import MessageQueueService, MessageResult


class TestMessageQueueAST:
    """Test AST nodes for message queue system."""

    def test_message_node_creation(self):
        """Test MessageNode creation with all attributes."""
        node = MessageNode(
            name="result",
            topic="orders.created",
            type="publish",
            body='{"orderId": "123"}'
        )

        assert node.name == "result"
        assert node.topic == "orders.created"
        assert node.type == "publish"
        assert node.body == '{"orderId": "123"}'
        assert node.queue is None
        assert len(node.headers) == 0

    def test_message_node_with_headers(self):
        """Test MessageNode with headers."""
        node = MessageNode(
            topic="events",
            type="publish"
        )

        header1 = MessageHeaderNode(name="priority", value="high")
        header2 = MessageHeaderNode(name="source", value="web-app")

        node.add_header(header1)
        node.add_header(header2)

        assert len(node.headers) == 2
        assert node.headers[0].name == "priority"
        assert node.headers[1].value == "web-app"

    def test_message_node_validation(self):
        """Test MessageNode validation."""
        # Missing topic and queue
        node = MessageNode(type="publish")
        errors = node.validate()
        assert any("topic" in e.lower() or "queue" in e.lower() for e in errors)

        # Both topic and queue (invalid)
        node = MessageNode(topic="test", queue="test-queue")
        errors = node.validate()
        assert any("both" in e.lower() for e in errors)

        # Valid node
        node = MessageNode(topic="valid-topic")
        errors = node.validate()
        assert len(errors) == 0

    def test_subscribe_node_creation(self):
        """Test SubscribeNode creation."""
        node = SubscribeNode(
            name="orderHandler",
            topic="orders.*",
            ack="manual",
            prefetch=10
        )

        assert node.name == "orderHandler"
        assert node.topic == "orders.*"
        assert node.ack == "manual"
        assert node.prefetch == 10
        assert len(node.on_message) == 0
        assert len(node.on_error) == 0

    def test_subscribe_node_validation(self):
        """Test SubscribeNode validation."""
        # Missing name
        node = SubscribeNode(topic="test")
        errors = node.validate()
        assert any("name" in e.lower() for e in errors)

        # Missing topic/queue
        node = SubscribeNode(name="test")
        errors = node.validate()
        assert any("topic" in e.lower() or "queue" in e.lower() for e in errors)

        # Invalid ack mode
        node = SubscribeNode(name="test", topic="topic", ack="invalid")
        errors = node.validate()
        assert any("ack" in e.lower() for e in errors)

    def test_queue_node_creation(self):
        """Test QueueNode creation."""
        node = QueueNode(
            name="orders",
            action="declare",
            durable=True,
            dead_letter_queue="orders-dlq",
            ttl=86400000
        )

        assert node.name == "orders"
        assert node.action == "declare"
        assert node.durable is True
        assert node.dead_letter_queue == "orders-dlq"
        assert node.ttl == 86400000

    def test_queue_node_validation(self):
        """Test QueueNode validation."""
        # Missing name
        node = QueueNode(action="declare")
        errors = node.validate()
        assert any("name" in e.lower() for e in errors)

        # Invalid action
        node = QueueNode(name="test", action="invalid")
        errors = node.validate()
        assert any("action" in e.lower() for e in errors)

        # Info action without result
        node = QueueNode(name="test", action="info")
        errors = node.validate()
        assert any("result" in e.lower() for e in errors)

    def test_message_ack_node(self):
        """Test MessageAckNode."""
        node = MessageAckNode()
        assert node.to_dict()["type"] == "message_ack"
        assert len(node.validate()) == 0

    def test_message_nack_node(self):
        """Test MessageNackNode."""
        node = MessageNackNode(requeue=False)
        assert node.requeue is False
        assert node.to_dict()["requeue"] is False


class TestMessageQueueParser:
    """Test parser for message queue tags."""

    @pytest.fixture
    def parser(self):
        return QuantumParser()

    def test_parse_message_publish(self, parser):
        """Test parsing q:message for publish."""
        xml = '''<?xml version="1.0"?>
        <q:component name="Test" xmlns:q="https://quantum.lang/ns">
            <q:message name="result" topic="orders.created" type="publish">
                <q:header name="priority" value="high" />
                <q:body>{"orderId": "123"}</q:body>
            </q:message>
        </q:component>
        '''

        component = parser.parse(xml)
        assert len(component.statements) == 1

        msg = component.statements[0]
        assert isinstance(msg, MessageNode)
        assert msg.name == "result"
        assert msg.topic == "orders.created"
        assert msg.type == "publish"
        assert len(msg.headers) == 1
        assert msg.headers[0].name == "priority"
        assert msg.body == '{"orderId": "123"}'

    def test_parse_message_send(self, parser):
        """Test parsing q:message for send."""
        xml = '''<?xml version="1.0"?>
        <q:component name="Test" xmlns:q="https://quantum.lang/ns">
            <q:message name="taskId" queue="email-queue" type="send">
                <q:body>{"to": "test@example.com"}</q:body>
            </q:message>
        </q:component>
        '''

        component = parser.parse(xml)
        msg = component.statements[0]

        assert msg.queue == "email-queue"
        assert msg.type == "send"
        assert msg.topic is None

    def test_parse_message_request(self, parser):
        """Test parsing q:message for request/reply."""
        xml = '''<?xml version="1.0"?>
        <q:component name="Test" xmlns:q="https://quantum.lang/ns">
            <q:message name="response" queue="calculator" type="request" timeout="5000">
                <q:body>{"a": 5, "b": 3}</q:body>
            </q:message>
        </q:component>
        '''

        component = parser.parse(xml)
        msg = component.statements[0]

        assert msg.type == "request"
        assert msg.timeout == "5000"

    def test_parse_subscribe(self, parser):
        """Test parsing q:subscribe."""
        xml = '''<?xml version="1.0"?>
        <q:component name="Test" xmlns:q="https://quantum.lang/ns">
            <q:subscribe name="handler" topic="orders.*" ack="manual" prefetch="5">
                <q:onMessage>
                    <q:log level="info" message="Received: {message.body}" />
                </q:onMessage>
                <q:onError>
                    <q:log level="error" message="Error: {error}" />
                </q:onError>
            </q:subscribe>
        </q:component>
        '''

        component = parser.parse(xml)
        sub = component.statements[0]

        assert isinstance(sub, SubscribeNode)
        assert sub.name == "handler"
        assert sub.topic == "orders.*"
        assert sub.ack == "manual"
        assert sub.prefetch == 5
        assert len(sub.on_message) == 1
        assert len(sub.on_error) == 1

    def test_parse_queue_declare(self, parser):
        """Test parsing q:queue for declaration."""
        xml = '''<?xml version="1.0"?>
        <q:component name="Test" xmlns:q="https://quantum.lang/ns">
            <q:queue name="orders" action="declare" durable="true"
                     deadLetterQueue="orders-dlq" ttl="86400000" />
        </q:component>
        '''

        component = parser.parse(xml)
        q = component.statements[0]

        assert isinstance(q, QueueNode)
        assert q.name == "orders"
        assert q.action == "declare"
        assert q.durable is True
        assert q.dead_letter_queue == "orders-dlq"
        assert q.ttl == 86400000

    def test_parse_queue_info(self, parser):
        """Test parsing q:queue for info."""
        xml = '''<?xml version="1.0"?>
        <q:component name="Test" xmlns:q="https://quantum.lang/ns">
            <q:queue name="orders" action="info" result="queueInfo" />
        </q:component>
        '''

        component = parser.parse(xml)
        q = component.statements[0]

        assert q.action == "info"
        assert q.result == "queueInfo"

    def test_parse_message_ack(self, parser):
        """Test parsing q:messageAck."""
        xml = '''<?xml version="1.0"?>
        <q:component name="Test" xmlns:q="https://quantum.lang/ns">
            <q:messageAck />
        </q:component>
        '''

        component = parser.parse(xml)
        assert isinstance(component.statements[0], MessageAckNode)

    def test_parse_message_nack(self, parser):
        """Test parsing q:messageNack."""
        xml = '''<?xml version="1.0"?>
        <q:component name="Test" xmlns:q="https://quantum.lang/ns">
            <q:messageNack requeue="false" />
        </q:component>
        '''

        component = parser.parse(xml)
        nack = component.statements[0]

        assert isinstance(nack, MessageNackNode)
        assert nack.requeue is False


class TestMemoryAdapter:
    """Test in-memory message broker adapter."""

    @pytest.fixture
    def broker(self):
        adapter = MemoryAdapter()
        adapter.connect({})
        yield adapter
        adapter.disconnect()

    def test_connect_disconnect(self, broker):
        """Test connection lifecycle."""
        assert broker.is_connected()
        broker.disconnect()
        assert not broker.is_connected()

    def test_publish_subscribe(self, broker):
        """Test pub/sub pattern."""
        received = []

        def handler(msg):
            received.append(msg)

        # Subscribe to topic
        sub_id = broker.subscribe("test.topic", handler)
        assert sub_id is not None

        # Publish message
        msg = Message(topic="test.topic", body='{"data": "test"}')
        broker.publish("test.topic", msg)

        # Give time for message delivery
        time.sleep(0.1)

        assert len(received) == 1
        assert received[0].body == '{"data": "test"}'

        # Unsubscribe
        broker.unsubscribe(sub_id)

    def test_send_consume(self, broker):
        """Test queue send/consume pattern."""
        received = []

        def handler(msg):
            received.append(msg)
            broker.ack(msg)

        # Declare queue
        broker.declare_queue("test-queue")

        # Start consuming
        consumer_id = broker.consume("test-queue", handler)

        # Send message
        msg = Message(queue="test-queue", body="test message")
        broker.send("test-queue", msg)

        # Give time for message delivery
        time.sleep(0.2)

        assert len(received) == 1
        assert received[0].body == "test message"

        # Stop consuming
        broker.unsubscribe(consumer_id)

    def test_queue_operations(self, broker):
        """Test queue management operations."""
        # Declare queue
        broker.declare_queue(
            "managed-queue",
            durable=True,
            dead_letter_queue="managed-queue-dlq"
        )

        # Get queue info
        info = broker.get_queue_info("managed-queue")
        assert info.name == "managed-queue"
        assert info.message_count == 0
        assert info.durable is True

        # Send messages
        for i in range(3):
            msg = Message(body=f"message-{i}")
            broker.send("managed-queue", msg)

        # Check count
        info = broker.get_queue_info("managed-queue")
        assert info.message_count == 3

        # Purge queue
        count = broker.purge_queue("managed-queue")
        assert count == 3

        info = broker.get_queue_info("managed-queue")
        assert info.message_count == 0

        # Delete queue
        broker.delete_queue("managed-queue")

        with pytest.raises(Exception):
            broker.get_queue_info("managed-queue")

    def test_topic_pattern_matching(self, broker):
        """Test topic pattern wildcards."""
        received = []

        def handler(msg):
            received.append(msg)

        # Subscribe to pattern
        broker.subscribe("orders.*", handler)

        # Publish to matching topics
        broker.publish("orders.created", Message(body="created"))
        broker.publish("orders.updated", Message(body="updated"))
        broker.publish("users.created", Message(body="should not match"))

        time.sleep(0.1)

        # Should receive only orders.* messages
        assert len(received) == 2
        bodies = [m.body for m in received]
        assert "created" in bodies
        assert "updated" in bodies

    def test_nack_requeue(self, broker):
        """Test negative acknowledgment with requeue."""
        received = []
        process_count = [0]

        def handler(msg):
            process_count[0] += 1
            if process_count[0] == 1:
                # First attempt - reject and requeue
                broker.nack(msg, requeue=True)
            else:
                # Second attempt - accept
                received.append(msg)
                broker.ack(msg)

        broker.declare_queue("retry-queue")
        broker.consume("retry-queue", handler)

        msg = Message(body="retry-test")
        broker.send("retry-queue", msg)

        time.sleep(0.3)

        assert process_count[0] >= 2
        assert len(received) == 1


class TestMessageQueueService:
    """Test high-level message queue service."""

    @pytest.fixture
    def service(self):
        svc = MessageQueueService({'broker_type': 'memory'})
        svc.connect()
        yield svc
        svc.disconnect()

    def test_publish(self, service):
        """Test publishing to topics."""
        result = service.publish(
            topic="test.topic",
            body={"message": "hello"},
            headers={"source": "test"}
        )

        assert result.success
        assert result.message_id is not None

    def test_send(self, service):
        """Test sending to queues."""
        result = service.send(
            queue="test-queue",
            body={"task": "process"},
            headers={"priority": "high"}
        )

        assert result.success
        assert result.message_id is not None

    def test_queue_management(self, service):
        """Test queue declaration and info."""
        # Declare
        result = service.declare_queue(
            name="managed-queue",
            durable=True,
            ttl=60000
        )
        assert result.success

        # Info
        result = service.get_queue_info("managed-queue")
        assert result.success
        assert result.data["name"] == "managed-queue"
        assert result.data["message_count"] == 0

        # Purge
        service.send("managed-queue", {"test": "data"})
        result = service.purge_queue("managed-queue")
        assert result.success

        # Delete
        result = service.delete_queue("managed-queue")
        assert result.success

    def test_subscribe(self, service):
        """Test subscription to topics."""
        received = []

        def handler(msg_context):
            received.append(msg_context)

        # Subscribe
        sub_id = service.subscribe(
            name="test-sub",
            topic="events.*",
            handler=handler
        )

        assert sub_id is not None

        # Publish
        service.publish("events.test", {"event": "test"})

        time.sleep(0.2)

        assert len(received) >= 1

        # Unsubscribe
        service.unsubscribe("test-sub")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
