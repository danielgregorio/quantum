"""
Message Queue System - Message Broker Abstraction

Provides a unified interface for message queue operations across
different backends (In-Memory, Redis, RabbitMQ).

Supports:
- Publish/Subscribe (topics)
- Direct queue messaging
- Request/Reply pattern
- Message acknowledgment
- Dead letter queues
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable, List
import uuid
import time
import json


class MessageBrokerError(Exception):
    """Base exception for message broker errors"""
    pass


class ConnectionError(MessageBrokerError):
    """Raised when connection to broker fails"""
    pass


class PublishError(MessageBrokerError):
    """Raised when message publish fails"""
    pass


class SubscribeError(MessageBrokerError):
    """Raised when subscription fails"""
    pass


class QueueError(MessageBrokerError):
    """Raised when queue operation fails"""
    pass


@dataclass
class Message:
    """
    Represents a message in the queue system.

    Attributes:
        id: Unique message identifier
        topic: Topic name (for pub/sub)
        queue: Queue name (for direct messaging)
        body: Message payload (can be any JSON-serializable type)
        headers: Custom message headers
        timestamp: Message creation timestamp
        reply_to: Queue for reply (used in request/reply pattern)
        correlation_id: ID linking request and response
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    topic: Optional[str] = None
    queue: Optional[str] = None
    body: Any = None
    headers: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    reply_to: Optional[str] = None
    correlation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize message to dictionary"""
        return {
            'id': self.id,
            'topic': self.topic,
            'queue': self.queue,
            'body': self.body,
            'headers': self.headers,
            'timestamp': self.timestamp,
            'reply_to': self.reply_to,
            'correlation_id': self.correlation_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Deserialize message from dictionary"""
        return cls(
            id=data.get('id', str(uuid.uuid4())),
            topic=data.get('topic'),
            queue=data.get('queue'),
            body=data.get('body'),
            headers=data.get('headers', {}),
            timestamp=data.get('timestamp', time.time()),
            reply_to=data.get('reply_to'),
            correlation_id=data.get('correlation_id')
        )

    def to_json(self) -> str:
        """Serialize message to JSON string"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> 'Message':
        """Deserialize message from JSON string"""
        return cls.from_dict(json.loads(json_str))


@dataclass
class QueueInfo:
    """
    Information about a queue.

    Attributes:
        name: Queue name
        message_count: Number of messages in queue
        consumer_count: Number of active consumers
        durable: Whether queue survives broker restart
        auto_delete: Whether queue is deleted when last consumer disconnects
    """
    name: str
    message_count: int = 0
    consumer_count: int = 0
    durable: bool = True
    auto_delete: bool = False


# Type alias for message handler callbacks
MessageHandler = Callable[[Message], None]


class MessageBroker(ABC):
    """
    Abstract base class for message broker implementations.

    Provides a unified interface for:
    - Connection management
    - Publishing to topics
    - Sending to queues
    - Subscribing to topics/queues
    - Message acknowledgment
    - Queue management
    """

    @abstractmethod
    def connect(self, config: Dict[str, Any]) -> None:
        """
        Connect to the message broker.

        Args:
            config: Connection configuration (host, port, credentials, etc.)

        Raises:
            ConnectionError: If connection fails
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """
        Disconnect from the message broker.

        Should clean up all resources, close connections, and
        cancel any active subscriptions.
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if connected to the broker.

        Returns:
            True if connected, False otherwise
        """
        pass

    @abstractmethod
    def publish(self, topic: str, message: Message) -> None:
        """
        Publish a message to a topic (pub/sub pattern).

        All subscribers to the topic will receive the message.

        Args:
            topic: Topic name (supports wildcards in some implementations)
            message: Message to publish

        Raises:
            PublishError: If publish fails
        """
        pass

    @abstractmethod
    def send(self, queue: str, message: Message) -> None:
        """
        Send a message directly to a queue (point-to-point).

        Only one consumer will receive the message.

        Args:
            queue: Queue name
            message: Message to send

        Raises:
            PublishError: If send fails
        """
        pass

    @abstractmethod
    def request(self, queue: str, message: Message, timeout: int = 5000) -> Message:
        """
        Send a request and wait for a reply (request/reply pattern).

        Args:
            queue: Queue to send request to
            message: Request message
            timeout: Timeout in milliseconds

        Returns:
            Response message

        Raises:
            PublishError: If request fails
            TimeoutError: If no response within timeout
        """
        pass

    @abstractmethod
    def subscribe(self, topic: str, handler: MessageHandler) -> str:
        """
        Subscribe to a topic.

        Args:
            topic: Topic pattern to subscribe to
            handler: Callback function for received messages

        Returns:
            Subscription ID (for unsubscribing)

        Raises:
            SubscribeError: If subscription fails
        """
        pass

    @abstractmethod
    def consume(self, queue: str, handler: MessageHandler, prefetch: int = 1) -> str:
        """
        Start consuming messages from a queue.

        Args:
            queue: Queue name
            handler: Callback function for received messages
            prefetch: Number of messages to prefetch

        Returns:
            Consumer ID (for stopping consumption)

        Raises:
            SubscribeError: If consumption setup fails
        """
        pass

    @abstractmethod
    def unsubscribe(self, subscription_id: str) -> None:
        """
        Unsubscribe from a topic or stop consuming from a queue.

        Args:
            subscription_id: ID returned from subscribe() or consume()
        """
        pass

    @abstractmethod
    def ack(self, message: Message) -> None:
        """
        Acknowledge successful message processing.

        Args:
            message: Message to acknowledge
        """
        pass

    @abstractmethod
    def nack(self, message: Message, requeue: bool = True) -> None:
        """
        Negative acknowledge - reject a message.

        Args:
            message: Message to reject
            requeue: If True, requeue the message; if False, discard or send to DLQ
        """
        pass

    @abstractmethod
    def declare_queue(
        self,
        name: str,
        durable: bool = True,
        exclusive: bool = False,
        auto_delete: bool = False,
        dead_letter_queue: Optional[str] = None,
        ttl: Optional[int] = None
    ) -> None:
        """
        Declare a queue (create if not exists).

        Args:
            name: Queue name
            durable: Survive broker restart
            exclusive: Only this connection can access
            auto_delete: Delete when last consumer disconnects
            dead_letter_queue: Queue for rejected/expired messages
            ttl: Message TTL in milliseconds

        Raises:
            QueueError: If declaration fails
        """
        pass

    @abstractmethod
    def purge_queue(self, name: str) -> int:
        """
        Purge all messages from a queue.

        Args:
            name: Queue name

        Returns:
            Number of messages purged

        Raises:
            QueueError: If purge fails
        """
        pass

    @abstractmethod
    def delete_queue(self, name: str) -> None:
        """
        Delete a queue.

        Args:
            name: Queue name

        Raises:
            QueueError: If deletion fails
        """
        pass

    @abstractmethod
    def get_queue_info(self, name: str) -> QueueInfo:
        """
        Get information about a queue.

        Args:
            name: Queue name

        Returns:
            QueueInfo with queue statistics

        Raises:
            QueueError: If queue doesn't exist or info retrieval fails
        """
        pass
