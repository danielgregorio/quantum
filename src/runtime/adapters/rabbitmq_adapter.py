"""
RabbitMQ Message Broker Adapter

Provides a full-featured AMQP implementation of the MessageBroker interface
using the pika library.

Features:
- Topic exchanges for pub/sub
- Direct queues for point-to-point
- Durable queues and messages
- Dead letter exchanges
- Message TTL
- Consumer prefetch
- Acknowledgments

Requires: pika package (pip install pika)
"""

import threading
import json
import time
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

import sys
from pathlib import Path

try:
    import pika
    from pika.exceptions import AMQPConnectionError, AMQPChannelError
    PIKA_AVAILABLE = True
except ImportError:
    PIKA_AVAILABLE = False
    pika = None
    AMQPConnectionError = Exception
    AMQPChannelError = Exception

# Support both direct execution and import from parent
try:
    from runtime.message_broker import (
        MessageBroker, Message, QueueInfo, MessageHandler,
        MessageBrokerError, ConnectionError, PublishError,
        SubscribeError, QueueError
    )
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from message_broker import (
        MessageBroker, Message, QueueInfo, MessageHandler,
        MessageBrokerError, ConnectionError, PublishError,
        SubscribeError, QueueError
    )


@dataclass
class RabbitSubscription:
    """Internal state for a RabbitMQ subscription"""
    id: str
    pattern: str
    handler: MessageHandler
    is_queue: bool = False
    prefetch: int = 1
    active: bool = True
    consumer_tag: Optional[str] = None
    thread: Optional[threading.Thread] = None
    channel: Any = None


class RabbitMQAdapter(MessageBroker):
    """
    RabbitMQ-based implementation of MessageBroker.

    Features:
    - Full AMQP 0-9-1 support
    - Durable queues and exchanges
    - Topic exchange for pub/sub with wildcards (* and #)
    - Dead letter exchanges
    - Consumer acknowledgments
    - Request/reply pattern with reply queues

    Configuration:
        {
            'host': 'localhost',
            'port': 5672,
            'virtual_host': '/',
            'username': 'guest',
            'password': 'guest',
            'heartbeat': 600,
            'exchange': 'quantum'  # Default exchange name
        }
    """

    def __init__(self):
        if not PIKA_AVAILABLE:
            raise ImportError(
                "RabbitMQ adapter requires 'pika' package. "
                "Install with: pip install pika"
            )

        self._connection: Any = None
        self._channel: Any = None
        self._connected = False
        self._config: Dict[str, Any] = {}
        self._exchange = 'quantum'

        self._lock = threading.RLock()
        self._subscriptions: Dict[str, RabbitSubscription] = {}
        self._pending_acks: Dict[str, Any] = {}  # message_id -> delivery_tag
        self._reply_queues: Dict[str, Any] = {}

        self._shutdown = threading.Event()

    def connect(self, config: Dict[str, Any] = None) -> None:
        """
        Connect to RabbitMQ.

        Args:
            config: RabbitMQ connection configuration
        """
        if config is None:
            config = {}

        self._config = config
        self._exchange = config.get('exchange', 'quantum')

        try:
            credentials = pika.PlainCredentials(
                config.get('username', 'guest'),
                config.get('password', 'guest')
            )

            parameters = pika.ConnectionParameters(
                host=config.get('host', 'localhost'),
                port=config.get('port', 5672),
                virtual_host=config.get('virtual_host', '/'),
                credentials=credentials,
                heartbeat=config.get('heartbeat', 600)
            )

            self._connection = pika.BlockingConnection(parameters)
            self._channel = self._connection.channel()

            # Declare the main topic exchange
            self._channel.exchange_declare(
                exchange=self._exchange,
                exchange_type='topic',
                durable=True
            )

            self._connected = True
            self._shutdown.clear()

        except AMQPConnectionError as e:
            raise ConnectionError(f"Failed to connect to RabbitMQ: {e}")

    def disconnect(self) -> None:
        """Disconnect from RabbitMQ and clean up resources."""
        with self._lock:
            if not self._connected:
                return

            self._shutdown.set()

            # Stop all subscriptions
            for sub in list(self._subscriptions.values()):
                sub.active = False
                if sub.consumer_tag and sub.channel:
                    try:
                        sub.channel.basic_cancel(sub.consumer_tag)
                    except Exception:
                        pass
                if sub.thread and sub.thread.is_alive():
                    sub.thread.join(timeout=1.0)

            self._subscriptions.clear()

            # Close channel and connection
            try:
                if self._channel and self._channel.is_open:
                    self._channel.close()
            except Exception:
                pass

            try:
                if self._connection and self._connection.is_open:
                    self._connection.close()
            except Exception:
                pass

            self._channel = None
            self._connection = None
            self._connected = False

    def is_connected(self) -> bool:
        """Check if connected to RabbitMQ."""
        return (
            self._connected and
            self._connection is not None and
            self._connection.is_open and
            self._channel is not None and
            self._channel.is_open
        )

    def publish(self, topic: str, message: Message) -> None:
        """
        Publish a message to a topic.

        Uses the topic exchange with routing key = topic.

        Args:
            topic: Topic name (routing key)
            message: Message to publish
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to RabbitMQ")

        message.topic = topic

        try:
            properties = pika.BasicProperties(
                message_id=message.id,
                timestamp=int(message.timestamp),
                headers=message.headers,
                content_type='application/json',
                delivery_mode=2  # Persistent
            )

            self._channel.basic_publish(
                exchange=self._exchange,
                routing_key=topic,
                body=message.to_json(),
                properties=properties
            )

        except AMQPChannelError as e:
            raise PublishError(f"Failed to publish message: {e}")

    def send(self, queue_name: str, message: Message) -> None:
        """
        Send a message directly to a queue.

        Args:
            queue_name: Queue name
            message: Message to send
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to RabbitMQ")

        message.queue = queue_name

        try:
            properties = pika.BasicProperties(
                message_id=message.id,
                timestamp=int(message.timestamp),
                headers=message.headers,
                content_type='application/json',
                delivery_mode=2,  # Persistent
                reply_to=message.reply_to,
                correlation_id=message.correlation_id
            )

            self._channel.basic_publish(
                exchange='',  # Default exchange
                routing_key=queue_name,
                body=message.to_json(),
                properties=properties
            )

        except AMQPChannelError as e:
            raise PublishError(f"Failed to send message: {e}")

    def request(self, queue_name: str, message: Message, timeout: int = 5000) -> Message:
        """
        Send a request and wait for a reply.

        Args:
            queue_name: Queue to send request to
            message: Request message
            timeout: Timeout in milliseconds

        Returns:
            Response message
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to RabbitMQ")

        # Create exclusive reply queue
        result = self._channel.queue_declare(queue='', exclusive=True)
        reply_queue = result.method.queue
        correlation_id = str(uuid.uuid4())

        message.reply_to = reply_queue
        message.correlation_id = correlation_id

        response = [None]
        response_received = threading.Event()

        def on_response(ch, method, props, body):
            if props.correlation_id == correlation_id:
                response[0] = Message.from_json(body.decode())
                response_received.set()

        try:
            self._channel.basic_consume(
                queue=reply_queue,
                on_message_callback=on_response,
                auto_ack=True
            )

            # Send request
            self.send(queue_name, message)

            # Wait for response
            start_time = time.time()
            while not response_received.is_set():
                self._connection.process_data_events(time_limit=0.1)
                if time.time() - start_time > timeout / 1000.0:
                    raise TimeoutError(f"Request timed out after {timeout}ms")

            return response[0]

        finally:
            # Clean up reply queue
            try:
                self._channel.queue_delete(queue=reply_queue)
            except Exception:
                pass

    def subscribe(self, topic: str, handler: MessageHandler) -> str:
        """
        Subscribe to a topic pattern.

        Args:
            topic: Topic pattern (supports * and # wildcards)
            handler: Callback for received messages

        Returns:
            Subscription ID
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to RabbitMQ")

        sub_id = f"sub_{uuid.uuid4().hex}"

        try:
            # Create exclusive queue for this subscription
            result = self._channel.queue_declare(queue='', exclusive=True)
            queue_name = result.method.queue

            # Bind to topic exchange
            self._channel.queue_bind(
                exchange=self._exchange,
                queue=queue_name,
                routing_key=topic
            )

            subscription = RabbitSubscription(
                id=sub_id,
                pattern=topic,
                handler=handler,
                is_queue=False
            )

            # Start consumer in separate thread
            thread = threading.Thread(
                target=self._consume_thread,
                args=(subscription, queue_name, True),
                daemon=True,
                name=f"RabbitMQ-Sub-{sub_id}"
            )
            subscription.thread = thread

            with self._lock:
                self._subscriptions[sub_id] = subscription

            thread.start()

            return sub_id

        except AMQPChannelError as e:
            raise SubscribeError(f"Failed to subscribe: {e}")

    def consume(self, queue_name: str, handler: MessageHandler, prefetch: int = 1) -> str:
        """
        Start consuming messages from a queue.

        Args:
            queue_name: Queue name
            handler: Callback for received messages
            prefetch: Number of messages to prefetch

        Returns:
            Consumer ID
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to RabbitMQ")

        consumer_id = f"consumer_{uuid.uuid4().hex}"

        subscription = RabbitSubscription(
            id=consumer_id,
            pattern=queue_name,
            handler=handler,
            is_queue=True,
            prefetch=prefetch
        )

        # Start consumer in separate thread
        thread = threading.Thread(
            target=self._consume_thread,
            args=(subscription, queue_name, False),
            daemon=True,
            name=f"RabbitMQ-Consumer-{consumer_id}"
        )
        subscription.thread = thread

        with self._lock:
            self._subscriptions[consumer_id] = subscription

        thread.start()

        return consumer_id

    def unsubscribe(self, subscription_id: str) -> None:
        """
        Unsubscribe or stop consuming.

        Args:
            subscription_id: Subscription or consumer ID
        """
        with self._lock:
            if subscription_id in self._subscriptions:
                sub = self._subscriptions[subscription_id]
                sub.active = False

                if sub.consumer_tag and sub.channel:
                    try:
                        sub.channel.basic_cancel(sub.consumer_tag)
                    except Exception:
                        pass

                if sub.thread and sub.thread.is_alive():
                    sub.thread.join(timeout=1.0)

                del self._subscriptions[subscription_id]

    def ack(self, message: Message) -> None:
        """
        Acknowledge message processing.

        Args:
            message: Message to acknowledge
        """
        with self._lock:
            delivery_tag = self._pending_acks.pop(message.id, None)
            if delivery_tag:
                try:
                    self._channel.basic_ack(delivery_tag=delivery_tag)
                except Exception:
                    pass

    def nack(self, message: Message, requeue: bool = True) -> None:
        """
        Negative acknowledge - reject a message.

        Args:
            message: Message to reject
            requeue: If True, requeue; if False, send to DLX
        """
        with self._lock:
            delivery_tag = self._pending_acks.pop(message.id, None)
            if delivery_tag:
                try:
                    self._channel.basic_nack(
                        delivery_tag=delivery_tag,
                        requeue=requeue
                    )
                except Exception:
                    pass

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
        Declare a queue.

        Args:
            name: Queue name
            durable: Survive broker restart
            exclusive: Only this connection can access
            auto_delete: Delete when last consumer disconnects
            dead_letter_queue: Queue for rejected messages
            ttl: Message TTL in milliseconds
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to RabbitMQ")

        try:
            arguments = {}

            if dead_letter_queue:
                # Create dead letter exchange
                dlx_name = f"{name}_dlx"
                self._channel.exchange_declare(
                    exchange=dlx_name,
                    exchange_type='direct',
                    durable=True
                )

                # Create dead letter queue
                self._channel.queue_declare(
                    queue=dead_letter_queue,
                    durable=True
                )

                # Bind DLQ to DLX
                self._channel.queue_bind(
                    exchange=dlx_name,
                    queue=dead_letter_queue,
                    routing_key=dead_letter_queue
                )

                arguments['x-dead-letter-exchange'] = dlx_name
                arguments['x-dead-letter-routing-key'] = dead_letter_queue

            if ttl:
                arguments['x-message-ttl'] = ttl

            self._channel.queue_declare(
                queue=name,
                durable=durable,
                exclusive=exclusive,
                auto_delete=auto_delete,
                arguments=arguments if arguments else None
            )

        except AMQPChannelError as e:
            raise QueueError(f"Failed to declare queue: {e}")

    def purge_queue(self, name: str) -> int:
        """
        Remove all messages from a queue.

        Args:
            name: Queue name

        Returns:
            Number of messages purged
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to RabbitMQ")

        try:
            result = self._channel.queue_purge(queue=name)
            return result.method.message_count
        except AMQPChannelError as e:
            raise QueueError(f"Failed to purge queue: {e}")

    def delete_queue(self, name: str) -> None:
        """
        Delete a queue.

        Args:
            name: Queue name
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to RabbitMQ")

        try:
            self._channel.queue_delete(queue=name)
        except AMQPChannelError as e:
            raise QueueError(f"Failed to delete queue: {e}")

    def get_queue_info(self, name: str) -> QueueInfo:
        """
        Get queue statistics.

        Args:
            name: Queue name

        Returns:
            QueueInfo with statistics
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to RabbitMQ")

        try:
            result = self._channel.queue_declare(
                queue=name,
                passive=True  # Only check, don't create
            )

            return QueueInfo(
                name=name,
                message_count=result.method.message_count,
                consumer_count=result.method.consumer_count,
                durable=True,  # Cannot determine from passive declare
                auto_delete=False
            )

        except AMQPChannelError as e:
            raise QueueError(f"Queue '{name}' not found: {e}")

    def _consume_thread(
        self,
        subscription: RabbitSubscription,
        queue_name: str,
        auto_ack: bool
    ) -> None:
        """Background thread for consuming messages."""
        try:
            # Create new connection for this thread
            credentials = pika.PlainCredentials(
                self._config.get('username', 'guest'),
                self._config.get('password', 'guest')
            )

            parameters = pika.ConnectionParameters(
                host=self._config.get('host', 'localhost'),
                port=self._config.get('port', 5672),
                virtual_host=self._config.get('virtual_host', '/'),
                credentials=credentials,
                heartbeat=self._config.get('heartbeat', 600)
            )

            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            subscription.channel = channel

            # Set prefetch
            channel.basic_qos(prefetch_count=subscription.prefetch)

            def callback(ch, method, properties, body):
                if not subscription.active:
                    return

                try:
                    msg = Message.from_json(body.decode())

                    if not auto_ack:
                        with self._lock:
                            self._pending_acks[msg.id] = method.delivery_tag

                    subscription.handler(msg)

                    if auto_ack:
                        ch.basic_ack(delivery_tag=method.delivery_tag)

                except Exception as e:
                    print(f"[RabbitMQ] Handler error: {e}")
                    if not auto_ack:
                        ch.basic_nack(
                            delivery_tag=method.delivery_tag,
                            requeue=True
                        )

            consumer_tag = channel.basic_consume(
                queue=queue_name,
                on_message_callback=callback,
                auto_ack=False
            )
            subscription.consumer_tag = consumer_tag

            while subscription.active and not self._shutdown.is_set():
                try:
                    connection.process_data_events(time_limit=1.0)
                except Exception:
                    if subscription.active:
                        time.sleep(1)

            # Cleanup
            try:
                channel.close()
                connection.close()
            except Exception:
                pass

        except Exception as e:
            print(f"[RabbitMQ] Consumer thread error: {e}")

    def reply(self, original_message: Message, response: Message) -> None:
        """
        Send a reply to a request message.

        Args:
            original_message: The request message
            response: The response message
        """
        if not original_message.reply_to:
            raise PublishError("Original message has no reply_to queue")

        response.correlation_id = original_message.correlation_id
        response.queue = original_message.reply_to

        try:
            properties = pika.BasicProperties(
                message_id=response.id,
                correlation_id=response.correlation_id,
                content_type='application/json'
            )

            self._channel.basic_publish(
                exchange='',
                routing_key=original_message.reply_to,
                body=response.to_json(),
                properties=properties
            )

        except AMQPChannelError as e:
            raise PublishError(f"Failed to send reply: {e}")
