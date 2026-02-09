"""
Message Queue Service

High-level service for Quantum message queue operations.
Wraps the message broker abstraction for use in the ComponentRuntime.
"""

import os
import json
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass

from runtime.message_broker import Message, QueueInfo, MessageBrokerError
from runtime.adapters import get_adapter, MemoryAdapter


class MessageQueueError(Exception):
    """Raised when message queue operation fails"""
    pass


@dataclass
class MessageResult:
    """Result of a message operation"""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    data: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'message_id': self.message_id,
            'error': self.error,
            'data': self.data
        }


class MessageQueueService:
    """
    Service for message queue operations in Quantum components.

    Provides a high-level interface for:
    - Publishing messages to topics
    - Sending messages to queues
    - Request/reply pattern
    - Queue management
    - Subscriptions

    Configuration (environment variables):
        MESSAGE_BROKER_TYPE: 'memory', 'redis', or 'rabbitmq' (default: memory)
        REDIS_HOST: Redis host (default: localhost)
        REDIS_PORT: Redis port (default: 6379)
        RABBITMQ_HOST: RabbitMQ host (default: localhost)
        RABBITMQ_PORT: RabbitMQ port (default: 5672)
        RABBITMQ_USER: RabbitMQ username (default: guest)
        RABBITMQ_PASSWORD: RabbitMQ password (default: guest)
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the message queue service.

        Args:
            config: Optional configuration (overrides environment)
        """
        self._config = config or {}
        self._broker = None
        self._subscriptions: Dict[str, str] = {}  # name -> subscription_id
        self._handlers: Dict[str, Callable] = {}  # name -> handler function
        self._current_message: Optional[Message] = None  # For ack/nack

    def _get_broker_type(self) -> str:
        """Get broker type from config or environment."""
        return self._config.get(
            'broker_type',
            os.getenv('MESSAGE_BROKER_TYPE', 'memory')
        )

    def _get_broker_config(self) -> Dict[str, Any]:
        """Build broker configuration from environment."""
        broker_type = self._get_broker_type()

        if broker_type == 'redis':
            return {
                'host': os.getenv('REDIS_HOST', 'localhost'),
                'port': int(os.getenv('REDIS_PORT', '6379')),
                'db': int(os.getenv('REDIS_DB', '0')),
                'password': os.getenv('REDIS_PASSWORD'),
                'prefix': os.getenv('REDIS_PREFIX', 'quantum:')
            }
        elif broker_type == 'rabbitmq':
            return {
                'host': os.getenv('RABBITMQ_HOST', 'localhost'),
                'port': int(os.getenv('RABBITMQ_PORT', '5672')),
                'virtual_host': os.getenv('RABBITMQ_VHOST', '/'),
                'username': os.getenv('RABBITMQ_USER', 'guest'),
                'password': os.getenv('RABBITMQ_PASSWORD', 'guest'),
                'exchange': os.getenv('RABBITMQ_EXCHANGE', 'quantum')
            }
        else:
            return {}

    def connect(self) -> None:
        """Connect to the message broker."""
        if self._broker is not None:
            return

        broker_type = self._get_broker_type()
        broker_config = self._get_broker_config()

        try:
            self._broker = get_adapter(broker_type)
            self._broker.connect(broker_config)
        except ImportError as e:
            # Fall back to memory adapter if required package not available
            print(f"[MessageQueue] {e}. Falling back to in-memory broker.")
            self._broker = MemoryAdapter()
            self._broker.connect({})
        except Exception as e:
            raise MessageQueueError(f"Failed to connect to message broker: {e}")

    def disconnect(self) -> None:
        """Disconnect from the message broker."""
        if self._broker:
            self._broker.disconnect()
            self._broker = None
            self._subscriptions.clear()

    def _ensure_connected(self) -> None:
        """Ensure broker is connected."""
        if self._broker is None or not self._broker.is_connected():
            self.connect()

    def publish(
        self,
        topic: str,
        body: Any,
        headers: Dict[str, str] = None
    ) -> MessageResult:
        """
        Publish a message to a topic.

        Args:
            topic: Topic name
            body: Message body (will be JSON serialized if not string)
            headers: Optional message headers

        Returns:
            MessageResult with operation status
        """
        self._ensure_connected()

        try:
            # Serialize body if needed
            if not isinstance(body, str):
                body = json.dumps(body)

            message = Message(
                topic=topic,
                body=body,
                headers=headers or {}
            )

            self._broker.publish(topic, message)

            return MessageResult(
                success=True,
                message_id=message.id
            )

        except Exception as e:
            return MessageResult(
                success=False,
                error=str(e)
            )

    def send(
        self,
        queue: str,
        body: Any,
        headers: Dict[str, str] = None
    ) -> MessageResult:
        """
        Send a message to a queue.

        Args:
            queue: Queue name
            body: Message body
            headers: Optional message headers

        Returns:
            MessageResult with operation status
        """
        self._ensure_connected()

        try:
            if not isinstance(body, str):
                body = json.dumps(body)

            message = Message(
                queue=queue,
                body=body,
                headers=headers or {}
            )

            self._broker.send(queue, message)

            return MessageResult(
                success=True,
                message_id=message.id
            )

        except Exception as e:
            return MessageResult(
                success=False,
                error=str(e)
            )

    def request(
        self,
        queue: str,
        body: Any,
        headers: Dict[str, str] = None,
        timeout: int = 5000
    ) -> MessageResult:
        """
        Send a request and wait for a reply.

        Args:
            queue: Queue name
            body: Request body
            headers: Optional headers
            timeout: Timeout in milliseconds

        Returns:
            MessageResult with response data
        """
        self._ensure_connected()

        try:
            if not isinstance(body, str):
                body = json.dumps(body)

            message = Message(
                queue=queue,
                body=body,
                headers=headers or {}
            )

            response = self._broker.request(queue, message, timeout)

            # Parse response body
            response_body = response.body
            if isinstance(response_body, str):
                try:
                    response_body = json.loads(response_body)
                except json.JSONDecodeError:
                    pass

            return MessageResult(
                success=True,
                message_id=response.id,
                data=response_body
            )

        except TimeoutError as e:
            return MessageResult(
                success=False,
                error=f"Request timed out: {e}"
            )
        except Exception as e:
            return MessageResult(
                success=False,
                error=str(e)
            )

    def subscribe(
        self,
        name: str,
        topic: str = None,
        topics: str = None,
        queue: str = None,
        handler: Callable = None,
        ack: str = 'auto',
        prefetch: int = 1
    ) -> str:
        """
        Subscribe to a topic or start consuming from a queue.

        Args:
            name: Subscription name
            topic: Single topic pattern
            topics: Comma-separated topic patterns
            queue: Queue name (for consumption)
            handler: Message handler function
            ack: Ack mode ('auto' or 'manual')
            prefetch: Number of messages to prefetch

        Returns:
            Subscription ID
        """
        self._ensure_connected()

        # Store handler for this subscription
        self._handlers[name] = handler

        def message_callback(msg: Message):
            """Internal callback that wraps the user handler."""
            self._current_message = msg

            # Parse message body
            body = msg.body
            if isinstance(body, str):
                try:
                    body = json.loads(body)
                except json.JSONDecodeError:
                    pass

            # Create message context for handler
            message_context = {
                'id': msg.id,
                'topic': msg.topic,
                'queue': msg.queue,
                'body': body,
                'headers': msg.headers,
                'timestamp': msg.timestamp
            }

            try:
                if handler:
                    handler(message_context)

                # Auto-ack if configured
                if ack == 'auto':
                    self._broker.ack(msg)

            except Exception as e:
                print(f"[MessageQueue] Handler error: {e}")
                if ack == 'manual':
                    self._broker.nack(msg, requeue=True)
            finally:
                self._current_message = None

        # Subscribe to topic(s) or consume from queue
        if queue:
            sub_id = self._broker.consume(queue, message_callback, prefetch)
        elif topic:
            sub_id = self._broker.subscribe(topic, message_callback)
        elif topics:
            # Subscribe to multiple topics
            topic_list = [t.strip() for t in topics.split(',')]
            sub_ids = []
            for t in topic_list:
                sid = self._broker.subscribe(t, message_callback)
                sub_ids.append(sid)
            sub_id = ','.join(sub_ids)
        else:
            raise MessageQueueError("Subscribe requires 'topic', 'topics', or 'queue'")

        self._subscriptions[name] = sub_id
        return sub_id

    def unsubscribe(self, name: str) -> None:
        """
        Unsubscribe from a topic or stop consuming.

        Args:
            name: Subscription name
        """
        if name in self._subscriptions:
            sub_id = self._subscriptions[name]

            # Handle multiple subscription IDs
            for sid in sub_id.split(','):
                self._broker.unsubscribe(sid.strip())

            del self._subscriptions[name]

        if name in self._handlers:
            del self._handlers[name]

    def ack(self) -> None:
        """Acknowledge the current message (for manual ack mode)."""
        if self._current_message and self._broker:
            self._broker.ack(self._current_message)

    def nack(self, requeue: bool = True) -> None:
        """
        Negative acknowledge the current message.

        Args:
            requeue: If True, requeue the message
        """
        if self._current_message and self._broker:
            self._broker.nack(self._current_message, requeue)

    def declare_queue(
        self,
        name: str,
        durable: bool = True,
        exclusive: bool = False,
        auto_delete: bool = False,
        dead_letter_queue: str = None,
        ttl: int = None
    ) -> MessageResult:
        """
        Declare a queue.

        Args:
            name: Queue name
            durable: Survive broker restart
            exclusive: Only this connection can access
            auto_delete: Delete when last consumer disconnects
            dead_letter_queue: Queue for rejected messages
            ttl: Message TTL in milliseconds

        Returns:
            MessageResult with operation status
        """
        self._ensure_connected()

        try:
            self._broker.declare_queue(
                name=name,
                durable=durable,
                exclusive=exclusive,
                auto_delete=auto_delete,
                dead_letter_queue=dead_letter_queue,
                ttl=ttl
            )

            return MessageResult(success=True)

        except Exception as e:
            return MessageResult(
                success=False,
                error=str(e)
            )

    def purge_queue(self, name: str) -> MessageResult:
        """
        Remove all messages from a queue.

        Args:
            name: Queue name

        Returns:
            MessageResult with count of purged messages
        """
        self._ensure_connected()

        try:
            count = self._broker.purge_queue(name)
            return MessageResult(
                success=True,
                data={'purged_count': count}
            )
        except Exception as e:
            return MessageResult(
                success=False,
                error=str(e)
            )

    def delete_queue(self, name: str) -> MessageResult:
        """
        Delete a queue.

        Args:
            name: Queue name

        Returns:
            MessageResult with operation status
        """
        self._ensure_connected()

        try:
            self._broker.delete_queue(name)
            return MessageResult(success=True)
        except Exception as e:
            return MessageResult(
                success=False,
                error=str(e)
            )

    def get_queue_info(self, name: str) -> MessageResult:
        """
        Get queue information.

        Args:
            name: Queue name

        Returns:
            MessageResult with queue info
        """
        self._ensure_connected()

        try:
            info = self._broker.get_queue_info(name)
            return MessageResult(
                success=True,
                data={
                    'name': info.name,
                    'message_count': info.message_count,
                    'consumer_count': info.consumer_count,
                    'durable': info.durable,
                    'auto_delete': info.auto_delete
                }
            )
        except Exception as e:
            return MessageResult(
                success=False,
                error=str(e)
            )
