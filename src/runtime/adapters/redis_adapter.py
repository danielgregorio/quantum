"""
Redis Message Broker Adapter

Provides a Redis-based implementation of the MessageBroker interface.

Uses:
- Redis Pub/Sub for topic-based messaging
- Redis Lists for queue-based messaging (LPUSH/BRPOP)
- JSON serialization for messages

Requires: redis package (pip install redis)
"""

import threading
import json
import time
import uuid
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from message_broker import (
    MessageBroker, Message, QueueInfo, MessageHandler,
    MessageBrokerError, ConnectionError, PublishError,
    SubscribeError, QueueError
)


@dataclass
class RedisSubscription:
    """Internal state for a Redis subscription"""
    id: str
    pattern: str
    handler: MessageHandler
    is_queue: bool = False
    prefetch: int = 1
    active: bool = True
    thread: Optional[threading.Thread] = None


class RedisAdapter(MessageBroker):
    """
    Redis-based implementation of MessageBroker.

    Features:
    - Redis Pub/Sub for topic messaging
    - Redis Lists (LPUSH/BRPOP) for queue messaging
    - Pattern-based topic subscriptions
    - Persistent queues (Redis persistence settings apply)

    Configuration:
        {
            'host': 'localhost',
            'port': 6379,
            'db': 0,
            'password': None,
            'decode_responses': True,
            'prefix': 'quantum:'  # Key prefix for namespacing
        }
    """

    def __init__(self):
        if not REDIS_AVAILABLE:
            raise ImportError(
                "Redis adapter requires 'redis' package. "
                "Install with: pip install redis"
            )

        self._client: Optional[redis.Redis] = None
        self._pubsub: Optional[redis.client.PubSub] = None
        self._connected = False
        self._config: Dict[str, Any] = {}
        self._prefix = 'quantum:'

        self._lock = threading.RLock()
        self._subscriptions: Dict[str, RedisSubscription] = {}
        self._pending_acks: Dict[str, Message] = {}
        self._reply_queues: Dict[str, Any] = {}

        self._shutdown = threading.Event()
        self._workers: List[threading.Thread] = []

    def connect(self, config: Dict[str, Any] = None) -> None:
        """
        Connect to Redis.

        Args:
            config: Redis connection configuration
        """
        if config is None:
            config = {}

        self._config = config
        self._prefix = config.get('prefix', 'quantum:')

        try:
            self._client = redis.Redis(
                host=config.get('host', 'localhost'),
                port=config.get('port', 6379),
                db=config.get('db', 0),
                password=config.get('password'),
                decode_responses=True
            )

            # Test connection
            self._client.ping()

            self._pubsub = self._client.pubsub()
            self._connected = True
            self._shutdown.clear()

        except redis.ConnectionError as e:
            raise ConnectionError(f"Failed to connect to Redis: {e}")

    def disconnect(self) -> None:
        """Disconnect from Redis and clean up resources."""
        with self._lock:
            if not self._connected:
                return

            self._shutdown.set()

            # Stop subscription threads
            for sub in self._subscriptions.values():
                sub.active = False
                if sub.thread and sub.thread.is_alive():
                    sub.thread.join(timeout=1.0)

            self._subscriptions.clear()
            self._workers.clear()

            if self._pubsub:
                self._pubsub.close()
                self._pubsub = None

            if self._client:
                self._client.close()
                self._client = None

            self._connected = False

    def is_connected(self) -> bool:
        """Check if connected to Redis."""
        if not self._connected or not self._client:
            return False

        try:
            self._client.ping()
            return True
        except redis.ConnectionError:
            return False

    def publish(self, topic: str, message: Message) -> None:
        """
        Publish a message to a topic using Redis Pub/Sub.

        Args:
            topic: Topic name
            message: Message to publish
        """
        if not self._connected:
            raise ConnectionError("Not connected to Redis")

        message.topic = topic
        channel = f"{self._prefix}topic:{topic}"

        try:
            self._client.publish(channel, message.to_json())
        except redis.RedisError as e:
            raise PublishError(f"Failed to publish message: {e}")

    def send(self, queue_name: str, message: Message) -> None:
        """
        Send a message to a queue using Redis Lists.

        Uses LPUSH to add message to the left of the list.

        Args:
            queue_name: Queue name
            message: Message to send
        """
        if not self._connected:
            raise ConnectionError("Not connected to Redis")

        message.queue = queue_name
        key = f"{self._prefix}queue:{queue_name}"

        try:
            # Store message with metadata
            self._client.lpush(key, message.to_json())

            # Set TTL if queue has one configured
            ttl_key = f"{self._prefix}queue_ttl:{queue_name}"
            ttl = self._client.get(ttl_key)
            if ttl:
                # Set expiry on individual message (stored separately)
                msg_key = f"{self._prefix}msg:{message.id}"
                self._client.setex(msg_key, int(int(ttl) / 1000), message.to_json())

        except redis.RedisError as e:
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
        if not self._connected:
            raise ConnectionError("Not connected to Redis")

        # Create unique reply queue
        reply_queue = f"_reply_{uuid.uuid4().hex}"
        correlation_id = str(uuid.uuid4())

        message.reply_to = reply_queue
        message.correlation_id = correlation_id

        reply_key = f"{self._prefix}queue:{reply_queue}"

        try:
            # Send request
            self.send(queue_name, message)

            # Wait for reply using BRPOP
            timeout_seconds = timeout / 1000.0
            result = self._client.brpop(reply_key, timeout=timeout_seconds)

            if result is None:
                raise TimeoutError(f"Request timed out after {timeout}ms")

            _, reply_json = result
            reply = Message.from_json(reply_json)

            return reply

        except redis.RedisError as e:
            raise PublishError(f"Request failed: {e}")
        finally:
            # Clean up reply queue
            self._client.delete(reply_key)

    def subscribe(self, topic: str, handler: MessageHandler) -> str:
        """
        Subscribe to a topic pattern.

        Args:
            topic: Topic pattern (supports * wildcards)
            handler: Callback for received messages

        Returns:
            Subscription ID
        """
        if not self._connected:
            raise ConnectionError("Not connected to Redis")

        sub_id = f"sub_{uuid.uuid4().hex}"
        pattern = f"{self._prefix}topic:{topic}"

        subscription = RedisSubscription(
            id=sub_id,
            pattern=topic,
            handler=handler,
            is_queue=False
        )

        with self._lock:
            self._subscriptions[sub_id] = subscription

        # Start subscription thread
        thread = threading.Thread(
            target=self._pubsub_worker,
            args=(subscription, pattern),
            daemon=True,
            name=f"Redis-Sub-{sub_id}"
        )
        subscription.thread = thread
        thread.start()

        return sub_id

    def consume(self, queue_name: str, handler: MessageHandler, prefetch: int = 1) -> str:
        """
        Start consuming messages from a queue.

        Args:
            queue_name: Queue name
            handler: Callback for received messages
            prefetch: Number of messages to prefetch (not fully supported in Redis)

        Returns:
            Consumer ID
        """
        if not self._connected:
            raise ConnectionError("Not connected to Redis")

        consumer_id = f"consumer_{uuid.uuid4().hex}"

        subscription = RedisSubscription(
            id=consumer_id,
            pattern=queue_name,
            handler=handler,
            is_queue=True,
            prefetch=prefetch
        )

        with self._lock:
            self._subscriptions[consumer_id] = subscription

        # Start consumer thread
        thread = threading.Thread(
            target=self._queue_worker,
            args=(subscription,),
            daemon=True,
            name=f"Redis-Consumer-{consumer_id}"
        )
        subscription.thread = thread
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

                if sub.thread and sub.thread.is_alive():
                    sub.thread.join(timeout=1.0)

                del self._subscriptions[subscription_id]

    def ack(self, message: Message) -> None:
        """
        Acknowledge message processing.

        For Redis, this removes the message from pending.
        """
        with self._lock:
            self._pending_acks.pop(message.id, None)

    def nack(self, message: Message, requeue: bool = True) -> None:
        """
        Negative acknowledge - reject a message.

        Args:
            message: Message to reject
            requeue: If True, requeue the message
        """
        with self._lock:
            self._pending_acks.pop(message.id, None)

        if requeue and message.queue:
            # Requeue by pushing back to the queue
            key = f"{self._prefix}queue:{message.queue}"
            try:
                self._client.rpush(key, message.to_json())
            except redis.RedisError:
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

        For Redis, queues are created implicitly. This stores metadata.
        """
        if not self._connected:
            raise ConnectionError("Not connected to Redis")

        meta_key = f"{self._prefix}queue_meta:{name}"

        try:
            meta = {
                'durable': durable,
                'exclusive': exclusive,
                'auto_delete': auto_delete,
                'dead_letter_queue': dead_letter_queue,
                'ttl': ttl
            }
            self._client.hset(meta_key, mapping={
                k: json.dumps(v) for k, v in meta.items()
            })

            if ttl:
                ttl_key = f"{self._prefix}queue_ttl:{name}"
                self._client.set(ttl_key, str(ttl))

        except redis.RedisError as e:
            raise QueueError(f"Failed to declare queue: {e}")

    def purge_queue(self, name: str) -> int:
        """
        Remove all messages from a queue.

        Args:
            name: Queue name

        Returns:
            Number of messages purged
        """
        if not self._connected:
            raise ConnectionError("Not connected to Redis")

        key = f"{self._prefix}queue:{name}"

        try:
            count = self._client.llen(key)
            self._client.delete(key)
            return count
        except redis.RedisError as e:
            raise QueueError(f"Failed to purge queue: {e}")

    def delete_queue(self, name: str) -> None:
        """
        Delete a queue and its metadata.

        Args:
            name: Queue name
        """
        if not self._connected:
            raise ConnectionError("Not connected to Redis")

        keys = [
            f"{self._prefix}queue:{name}",
            f"{self._prefix}queue_meta:{name}",
            f"{self._prefix}queue_ttl:{name}"
        ]

        try:
            self._client.delete(*keys)
        except redis.RedisError as e:
            raise QueueError(f"Failed to delete queue: {e}")

    def get_queue_info(self, name: str) -> QueueInfo:
        """
        Get queue statistics.

        Args:
            name: Queue name

        Returns:
            QueueInfo with statistics
        """
        if not self._connected:
            raise ConnectionError("Not connected to Redis")

        key = f"{self._prefix}queue:{name}"
        meta_key = f"{self._prefix}queue_meta:{name}"

        try:
            message_count = self._client.llen(key)

            # Get metadata
            meta = self._client.hgetall(meta_key)
            durable = json.loads(meta.get('durable', 'true'))
            auto_delete = json.loads(meta.get('auto_delete', 'false'))

            # Count active consumers for this queue
            consumer_count = sum(
                1 for s in self._subscriptions.values()
                if s.is_queue and s.pattern == name and s.active
            )

            return QueueInfo(
                name=name,
                message_count=message_count,
                consumer_count=consumer_count,
                durable=durable,
                auto_delete=auto_delete
            )

        except redis.RedisError as e:
            raise QueueError(f"Failed to get queue info: {e}")

    def _pubsub_worker(self, subscription: RedisSubscription, pattern: str) -> None:
        """Background worker for Redis Pub/Sub subscriptions."""
        try:
            # Create a new pubsub instance for this subscription
            pubsub = self._client.pubsub()

            if '*' in pattern or '?' in pattern:
                pubsub.psubscribe(pattern)
            else:
                pubsub.subscribe(pattern)

            for message in pubsub.listen():
                if not subscription.active or self._shutdown.is_set():
                    break

                if message['type'] in ('message', 'pmessage'):
                    try:
                        data = message['data']
                        if isinstance(data, str):
                            msg = Message.from_json(data)
                            subscription.handler(msg)
                    except Exception as e:
                        print(f"[Redis] Pub/Sub handler error: {e}")

            pubsub.close()

        except Exception as e:
            print(f"[Redis] Pub/Sub worker error: {e}")

    def _queue_worker(self, subscription: RedisSubscription) -> None:
        """Background worker for Redis queue consumption."""
        key = f"{self._prefix}queue:{subscription.pattern}"

        while subscription.active and not self._shutdown.is_set():
            try:
                # BRPOP with 1 second timeout for graceful shutdown
                result = self._client.brpop(key, timeout=1)

                if result is None:
                    continue

                _, msg_json = result
                msg = Message.from_json(msg_json)

                # Track pending ack
                with self._lock:
                    self._pending_acks[msg.id] = msg

                try:
                    subscription.handler(msg)
                except Exception as e:
                    print(f"[Redis] Queue handler error: {e}")
                    # Requeue on error
                    self.nack(msg, requeue=True)

            except Exception as e:
                if subscription.active:
                    print(f"[Redis] Queue worker error: {e}")
                    time.sleep(1)

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

        reply_key = f"{self._prefix}queue:{original_message.reply_to}"

        try:
            self._client.lpush(reply_key, response.to_json())
        except redis.RedisError as e:
            raise PublishError(f"Failed to send reply: {e}")
