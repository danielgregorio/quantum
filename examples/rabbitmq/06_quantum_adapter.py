#!/usr/bin/env python
"""
RabbitMQ Example 06: Quantum Adapter Integration

Demonstrates using the Quantum RabbitMQ adapter directly.
This is useful for testing and for building custom integrations.

Usage:
    # Terminal 1 - Start subscriber
    python 06_quantum_adapter.py subscribe "orders.*"

    # Terminal 2 - Publish messages
    python 06_quantum_adapter.py publish orders.created '{"orderId": "123"}'

    # Terminal 3 - Work queue
    python 06_quantum_adapter.py worker orders
    python 06_quantum_adapter.py send orders '{"task": "process"}'
"""

import sys
import json
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from runtime.adapters.rabbitmq_adapter import RabbitMQAdapter
from runtime.message_broker import Message


def connect_broker():
    """Create and connect to RabbitMQ."""
    adapter = RabbitMQAdapter()
    adapter.connect({
        'host': 'localhost',
        'port': 5672,
        'username': 'guest',
        'password': 'guest',
        'exchange': 'quantum_demo'
    })
    return adapter


def publish(topic: str, body: str):
    """Publish a message to a topic."""
    broker = connect_broker()

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        data = {'message': body}

    msg = Message(
        body=data,
        headers={'source': 'cli', 'demo': 'true'}
    )

    broker.publish(topic, msg)
    print(f" [x] Published to '{topic}':")
    print(f"     {json.dumps(data, indent=2)}")

    broker.disconnect()


def subscribe(pattern: str):
    """Subscribe to a topic pattern."""
    broker = connect_broker()

    def handler(msg: Message):
        print(f"\n [x] Received from '{msg.topic}':")
        print(f"     ID: {msg.id}")
        print(f"     Body: {json.dumps(msg.body, indent=2)}")
        print(f"     Headers: {msg.headers}")

    sub_id = broker.subscribe(pattern, handler)
    print(f" [*] Subscribed to pattern: '{pattern}'")
    print(f"     Subscription ID: {sub_id}")
    print(" [*] Waiting for messages. Press CTRL+C to exit.\n")

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n [*] Unsubscribing...")
        broker.unsubscribe(sub_id)
        broker.disconnect()
        print(" [*] Done.")


def send(queue_name: str, body: str):
    """Send a message to a queue."""
    broker = connect_broker()

    # Declare queue first
    broker.declare_queue(queue_name, durable=True)

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        data = {'message': body}

    msg = Message(body=data)
    broker.send(queue_name, msg)

    print(f" [x] Sent to queue '{queue_name}':")
    print(f"     {json.dumps(data, indent=2)}")

    broker.disconnect()


def worker(queue_name: str):
    """Start a queue worker."""
    broker = connect_broker()

    # Declare queue first
    broker.declare_queue(queue_name, durable=True)

    def handler(msg: Message):
        print(f"\n [x] Processing message:")
        print(f"     ID: {msg.id}")
        print(f"     Body: {json.dumps(msg.body, indent=2)}")

        # Simulate work
        time.sleep(1)
        print(" [x] Done processing")

        # Acknowledge
        broker.ack(msg)

    consumer_id = broker.consume(queue_name, handler, prefetch=5)
    print(f" [*] Worker started for queue: '{queue_name}'")
    print(f"     Consumer ID: {consumer_id}")
    print(" [*] Waiting for messages. Press CTRL+C to exit.\n")

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n [*] Stopping worker...")
        broker.unsubscribe(consumer_id)
        broker.disconnect()
        print(" [*] Done.")


def rpc_call(queue_name: str, body: str):
    """Make an RPC call."""
    broker = connect_broker()

    broker.declare_queue(queue_name, durable=True)

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        data = {'request': body}

    msg = Message(body=data)

    print(f" [x] Calling RPC on '{queue_name}':")
    print(f"     Request: {json.dumps(data, indent=2)}")

    try:
        response = broker.request(queue_name, msg, timeout=5000)
        print(f" [x] Response:")
        print(f"     {json.dumps(response.body, indent=2)}")
    except TimeoutError:
        print(" [!] Request timed out")

    broker.disconnect()


def info():
    """Show queue information."""
    broker = connect_broker()

    # List some common queues
    queues = ['orders', 'payments', 'notifications']

    print(" Queue Information:")
    print(" " + "-" * 50)

    for q in queues:
        try:
            info = broker.get_queue_info(q)
            print(f" {info.name}:")
            print(f"   Messages: {info.message_count}")
            print(f"   Consumers: {info.consumer_count}")
        except Exception as e:
            print(f" {q}: Not found or error ({e})")

    broker.disconnect()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Quantum RabbitMQ Adapter Demo")
        print()
        print("Usage:")
        print("  python 06_quantum_adapter.py publish <topic> <json>")
        print("  python 06_quantum_adapter.py subscribe <pattern>")
        print("  python 06_quantum_adapter.py send <queue> <json>")
        print("  python 06_quantum_adapter.py worker <queue>")
        print("  python 06_quantum_adapter.py rpc <queue> <json>")
        print("  python 06_quantum_adapter.py info")
        print()
        print("Examples:")
        print('  python 06_quantum_adapter.py publish orders.created \'{"id": 123}\'')
        print("  python 06_quantum_adapter.py subscribe \"orders.*\"")
        print('  python 06_quantum_adapter.py send tasks \'{"action": "process"}\'')
        print("  python 06_quantum_adapter.py worker tasks")
        sys.exit(1)

    command = sys.argv[1]

    try:
        if command == 'publish':
            topic = sys.argv[2] if len(sys.argv) > 2 else 'test.topic'
            body = sys.argv[3] if len(sys.argv) > 3 else '{"test": true}'
            publish(topic, body)

        elif command == 'subscribe':
            pattern = sys.argv[2] if len(sys.argv) > 2 else '#'
            subscribe(pattern)

        elif command == 'send':
            queue = sys.argv[2] if len(sys.argv) > 2 else 'test-queue'
            body = sys.argv[3] if len(sys.argv) > 3 else '{"test": true}'
            send(queue, body)

        elif command == 'worker':
            queue = sys.argv[2] if len(sys.argv) > 2 else 'test-queue'
            worker(queue)

        elif command == 'rpc':
            queue = sys.argv[2] if len(sys.argv) > 2 else 'rpc-queue'
            body = sys.argv[3] if len(sys.argv) > 3 else '{"n": 10}'
            rpc_call(queue, body)

        elif command == 'info':
            info()

        else:
            print(f"Unknown command: {command}")
            sys.exit(1)

    except Exception as e:
        print(f" [!] Error: {e}")
        print()
        print("Make sure RabbitMQ is running:")
        print("  docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:management")
        sys.exit(1)
