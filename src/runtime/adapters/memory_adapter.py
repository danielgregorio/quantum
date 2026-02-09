"""
In-Memory Message Broker Adapter

Provides a simple in-memory implementation of the MessageBroker interface
for testing and development purposes.

Features:
- Topic-based pub/sub with pattern matching
- Queue-based point-to-point messaging
- Request/reply pattern support
- Message acknowledgment (simulated)
- No external dependencies
"""

import threading
import queue
import fnmatch
import time
import uuid
from typing import Dict, Any, Optional, List, Callable
from collections import defaultdict
from dataclasses import dataclass, field

import sys
from pathlib import Path

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
class QueueState:
    """Internal state for a queue"""
    messages: queue.Queue = field(default_factory=queue.Queue)
    durable: bool = True
    exclusive: bool = False
    auto_delete: bool = False
    dead_letter_queue: Optional[str] = None
    ttl: Optional[int] = None
    consumers: List[str] = field(default_factory=list)


@dataclass
class Subscription:
    """Internal state for a subscription"""
    id: str
    pattern: str  # topic pattern or queue name
    handler: MessageHandler
    is_queue: bool = False
    prefetch: int = 1
    active: bool = True


class MemoryAdapter(MessageBroker):
    """
    In-memory implementation of MessageBroker.

    Suitable for:
    - Unit testing
    - Development environments
    - Single-process applications
    - Prototyping

    Limitations:
    - Messages are lost on process restart
    - No persistence
    - Single process only (no IPC)
    """

    def __init__(self):
        self._connected = False
        self._lock = threading.RLock()

        # Queues: name -> QueueState
        self._queues: Dict[str, QueueState] = {}

        # Topic subscriptions: subscription_id -> Subscription
        self._subscriptions: Dict[str, Subscription] = {}

        # Pending acknowledgments: message_id -> Message
        self._pending_acks: Dict[str, Message] = {}

        # Reply queues for request/reply pattern
        self._reply_queues: Dict[str, queue.Queue] = {}

        # Background worker threads
        self._workers: List[threading.Thread] = []
        self._shutdown = threading.Event()

    def connect(self, config: Dict[str, Any] = None) -> None:
        """
        Initialize the in-memory broker.

        Args:
            config: Optional configuration (ignored for memory adapter)
        """
        with self._lock:
            if self._connected:
                return

            self._connected = True
            self._shutdown.clear()

            # Start background worker for queue consumption
            worker = threading.Thread(
                target=self._consume_worker,
                daemon=True,
                name="MemoryBroker-Worker"
            )
            worker.start()
            self._workers.append(worker)

    def disconnect(self) -> None:
        """Shutdown the in-memory broker and clean up resources."""
        with self._lock:
            if not self._connected:
                return

            # Signal workers to stop
            self._shutdown.set()

            # Wait for workers to finish
            for worker in self._workers:
                worker.join(timeout=1.0)

            self._workers.clear()

            # Clear all state
            self._queues.clear()
            self._subscriptions.clear()
            self._pending_acks.clear()
            self._reply_queues.clear()

            self._connected = False

    def is_connected(self) -> bool:
        """Check if broker is initialized."""
        return self._connected

    def publish(self, topic: str, message: Message) -> None:
        """
        Publish a message to a topic.

        All matching subscriptions will receive the message.

        Args:
            topic: Topic name
            message: Message to publish
        """
        if not self._connected:
            raise ConnectionError("Broker not connected")

        message.topic = topic

        with self._lock:
            # Find all matching subscriptions
            for sub in self._subscriptions.values():
                if sub.active and not sub.is_queue:
                    if self._match_topic(topic, sub.pattern):
                        try:
                            # Create a copy of the message for each subscriber
                            sub.handler(Message.from_dict(message.to_dict()))
                        except Exception as e:
                            # Log error but don't fail publish
                            print(f"[MemoryBroker] Handler error: {e}")

    def send(self, queue_name: str, message: Message) -> None:
        """
        Send a message to a queue.

        Args:
            queue_name: Queue name
            message: Message to send
        """
        if not self._connected:
            raise ConnectionError("Broker not connected")

        message.queue = queue_name

        with self._lock:
            # Ensure queue exists
            if queue_name not in self._queues:
                self._queues[queue_name] = QueueState()

            q = self._queues[queue_name]

            # Check TTL
            if q.ttl is not None:
                message.headers['_expires'] = str(time.time() * 1000 + q.ttl)

            q.messages.put(message)

    def request(self, queue_name: str, message: Message, timeout: int = 5000) -> Message:
        """
        Send a request and wait for a reply.

        Args:
            queue_name: Queue to send request to
            message: Request message
            timeout: Timeout in milliseconds

        Returns:
            Response message

        Raises:
            TimeoutError: If no response within timeout
        """
        if not self._connected:
            raise ConnectionError("Broker not connected")

        # Create unique reply queue
        reply_queue_name = f"_reply_{uuid.uuid4().hex}"
        correlation_id = str(uuid.uuid4())

        # Set up reply queue
        reply_queue = queue.Queue()
        with self._lock:
            self._reply_queues[reply_queue_name] = reply_queue

        try:
            # Set message properties for reply
            message.reply_to = reply_queue_name
            message.correlation_id = correlation_id

            # Send request
            self.send(queue_name, message)

            # Wait for reply
            try:
                reply = reply_queue.get(timeout=timeout / 1000.0)
                return reply
            except queue.Empty:
                raise TimeoutError(f"Request timed out after {timeout}ms")

        finally:
            # Clean up reply queue
            with self._lock:
                self._reply_queues.pop(reply_queue_name, None)

    def subscribe(self, topic: str, handler: MessageHandler) -> str:
        """
        Subscribe to a topic pattern.

        Args:
            topic: Topic pattern (supports * and # wildcards)
            handler: Callback for received messages

        Returns:
            Subscription ID
        """
        if not self._connected:
            raise ConnectionError("Broker not connected")

        sub_id = f"sub_{uuid.uuid4().hex}"

        with self._lock:
            self._subscriptions[sub_id] = Subscription(
                id=sub_id,
                pattern=topic,
                handler=handler,
                is_queue=False
            )

        return sub_id

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
        if not self._connected:
            raise ConnectionError("Broker not connected")

        consumer_id = f"consumer_{uuid.uuid4().hex}"

        with self._lock:
            # Ensure queue exists
            if queue_name not in self._queues:
                self._queues[queue_name] = QueueState()

            self._queues[queue_name].consumers.append(consumer_id)

            self._subscriptions[consumer_id] = Subscription(
                id=consumer_id,
                pattern=queue_name,
                handler=handler,
                is_queue=True,
                prefetch=prefetch
            )

        return consumer_id

    def unsubscribe(self, subscription_id: str) -> None:
        """
        Unsubscribe from a topic or stop consuming.

        Args:
            subscription_id: Subscription or consumer ID
        """
        with self._lock:
            if subscription_id in self._subscriptions:
                sub = self._subscriptions[subscription_id]
                sub.active = False

                # Remove from queue consumers if applicable
                if sub.is_queue and sub.pattern in self._queues:
                    consumers = self._queues[sub.pattern].consumers
                    if subscription_id in consumers:
                        consumers.remove(subscription_id)

                del self._subscriptions[subscription_id]

    def ack(self, message: Message) -> None:
        """
        Acknowledge message processing.

        Args:
            message: Message to acknowledge
        """
        with self._lock:
            self._pending_acks.pop(message.id, None)

    def nack(self, message: Message, requeue: bool = True) -> None:
        """
        Negative acknowledge - reject a message.

        Args:
            message: Message to reject
            requeue: If True, requeue; if False, send to DLQ
        """
        with self._lock:
            self._pending_acks.pop(message.id, None)

            if message.queue:
                q = self._queues.get(message.queue)

                if requeue and q:
                    # Requeue the message
                    q.messages.put(message)
                elif q and q.dead_letter_queue:
                    # Send to dead letter queue
                    if q.dead_letter_queue not in self._queues:
                        self._queues[q.dead_letter_queue] = QueueState()
                    self._queues[q.dead_letter_queue].messages.put(message)

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
            durable: (ignored in memory adapter)
            exclusive: If True, only this connection can access
            auto_delete: If True, delete when last consumer disconnects
            dead_letter_queue: Queue for rejected messages
            ttl: Message TTL in milliseconds
        """
        if not self._connected:
            raise ConnectionError("Broker not connected")

        with self._lock:
            if name not in self._queues:
                self._queues[name] = QueueState(
                    durable=durable,
                    exclusive=exclusive,
                    auto_delete=auto_delete,
                    dead_letter_queue=dead_letter_queue,
                    ttl=ttl
                )

            # Also declare DLQ if specified
            if dead_letter_queue and dead_letter_queue not in self._queues:
                self._queues[dead_letter_queue] = QueueState(durable=True)

    def purge_queue(self, name: str) -> int:
        """
        Remove all messages from a queue.

        Args:
            name: Queue name

        Returns:
            Number of messages purged
        """
        if not self._connected:
            raise ConnectionError("Broker not connected")

        with self._lock:
            if name not in self._queues:
                raise QueueError(f"Queue '{name}' not found")

            q = self._queues[name]
            count = q.messages.qsize()

            # Clear the queue
            while not q.messages.empty():
                try:
                    q.messages.get_nowait()
                except queue.Empty:
                    break

            return count

    def delete_queue(self, name: str) -> None:
        """
        Delete a queue.

        Args:
            name: Queue name
        """
        if not self._connected:
            raise ConnectionError("Broker not connected")

        with self._lock:
            if name in self._queues:
                del self._queues[name]

    def get_queue_info(self, name: str) -> QueueInfo:
        """
        Get queue statistics.

        Args:
            name: Queue name

        Returns:
            QueueInfo with statistics
        """
        if not self._connected:
            raise ConnectionError("Broker not connected")

        with self._lock:
            if name not in self._queues:
                raise QueueError(f"Queue '{name}' not found")

            q = self._queues[name]
            return QueueInfo(
                name=name,
                message_count=q.messages.qsize(),
                consumer_count=len(q.consumers),
                durable=q.durable,
                auto_delete=q.auto_delete
            )

    def _match_topic(self, topic: str, pattern: str) -> bool:
        """
        Match a topic against a pattern.

        Supports MQTT-style wildcards:
        - * matches exactly one level
        - # matches zero or more levels

        Args:
            topic: Actual topic name
            pattern: Pattern to match against

        Returns:
            True if topic matches pattern
        """
        if pattern == topic:
            return True

        # Convert MQTT-style wildcards to fnmatch
        # * -> [^.]* (match one level)
        # # -> * (match any)
        if '#' in pattern or '*' in pattern:
            # Simple wildcard matching
            regex_pattern = pattern.replace('.', r'\.').replace('#', '*').replace('*', '[^.]*')
            import re
            return bool(re.match(f'^{regex_pattern}$', topic))

        return False

    def _consume_worker(self) -> None:
        """Background worker for delivering queue messages to consumers."""
        while not self._shutdown.is_set():
            try:
                with self._lock:
                    # Find all queue subscriptions
                    queue_subs = [
                        s for s in self._subscriptions.values()
                        if s.is_queue and s.active
                    ]

                for sub in queue_subs:
                    queue_name = sub.pattern
                    with self._lock:
                        if queue_name not in self._queues:
                            continue

                        q = self._queues[queue_name]
                        if q.messages.empty():
                            continue

                        # Get message
                        try:
                            msg = q.messages.get_nowait()
                        except queue.Empty:
                            continue

                    # Check if message expired
                    expires = msg.headers.get('_expires')
                    if expires and float(expires) < time.time() * 1000:
                        # Message expired - send to DLQ
                        with self._lock:
                            if q.dead_letter_queue:
                                dlq = self._queues.get(q.dead_letter_queue)
                                if dlq:
                                    dlq.messages.put(msg)
                        continue

                    # Track pending ack
                    with self._lock:
                        self._pending_acks[msg.id] = msg

                    # Call handler
                    try:
                        sub.handler(msg)

                        # Auto-ack if not in pending (handler didn't manually ack)
                        # In real implementation, this would depend on ack mode
                    except Exception as e:
                        print(f"[MemoryBroker] Consumer error: {e}")
                        # Requeue on error
                        self.nack(msg, requeue=True)

                    # Check for reply (request/reply pattern)
                    if msg.reply_to and msg.reply_to in self._reply_queues:
                        # The handler should have put a reply in the reply queue
                        pass

                # Small sleep to prevent busy-waiting
                time.sleep(0.01)

            except Exception as e:
                print(f"[MemoryBroker] Worker error: {e}")
                time.sleep(0.1)

    def reply(self, original_message: Message, response: Message) -> None:
        """
        Send a reply to a request message.

        Used by consumers to respond in request/reply pattern.

        Args:
            original_message: The request message
            response: The response message
        """
        if not original_message.reply_to:
            raise PublishError("Original message has no reply_to queue")

        response.correlation_id = original_message.correlation_id

        with self._lock:
            reply_queue = self._reply_queues.get(original_message.reply_to)
            if reply_queue:
                reply_queue.put(response)

    # ========================================
    # CLI Helper Methods
    # ========================================

    def list_queues(self) -> List[Dict[str, Any]]:
        """List all queues with statistics."""
        with self._lock:
            return [
                {
                    'name': name,
                    'messages': q.messages.qsize(),
                    'consumers': len(q.consumers),
                    'durable': q.durable,
                }
                for name, q in self._queues.items()
            ]

    def list_topics(self) -> List[str]:
        """List all subscribed topics."""
        with self._lock:
            return list(set(
                s.pattern for s in self._subscriptions.values()
                if not s.is_queue and s.active
            ))

    def peek_queue(self, name: str, limit: int = 10) -> List[Message]:
        """
        Peek at messages in a queue without consuming them.

        Args:
            name: Queue name
            limit: Maximum messages to return

        Returns:
            List of messages
        """
        with self._lock:
            if name not in self._queues:
                return []

            q = self._queues[name]
            messages = []

            # Convert queue to list temporarily
            temp_list = []
            while not q.messages.empty() and len(temp_list) < 1000:
                try:
                    temp_list.append(q.messages.get_nowait())
                except queue.Empty:
                    break

            # Get first N messages
            messages = temp_list[:limit]

            # Put all messages back
            for msg in temp_list:
                q.messages.put(msg)

            return messages

    def delete_queue(self, name: str, force: bool = False) -> None:
        """
        Delete a queue.

        Args:
            name: Queue name
            force: Force delete even if not empty
        """
        with self._lock:
            if name in self._queues:
                q = self._queues[name]
                if not force and not q.messages.empty():
                    raise QueueError(f"Queue '{name}' is not empty. Use force=True to delete anyway.")
                del self._queues[name]

    def cancel_consumer(self, consumer_id: str) -> None:
        """Cancel a consumer. Alias for unsubscribe."""
        self.unsubscribe(consumer_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get broker statistics."""
        with self._lock:
            total_messages = sum(q.messages.qsize() for q in self._queues.values())
            total_consumers = sum(len(q.consumers) for q in self._queues.values())

            return {
                'broker_type': 'memory',
                'connected': self._connected,
                'queues': len(self._queues),
                'subscriptions': len(self._subscriptions),
                'total_messages': total_messages,
                'total_consumers': total_consumers,
                'pending_acks': len(self._pending_acks),
            }

    def get_info(self) -> Dict[str, Any]:
        """Get broker connection info."""
        return {
            'type': 'InMemory',
            'connected': self._connected,
            'persistent': False,
            'note': 'Messages are lost on restart',
        }


# Alias for backwards compatibility
InMemoryAdapter = MemoryAdapter
