#!/usr/bin/env python
"""
RabbitMQ Example 04: Topic-based Routing

Routes messages based on topic patterns.
Supports wildcards:
    * (asterisk) matches exactly one word
    # (hash) matches zero or more words

Usage:
    # Terminal 1 - Subscribe to all orders
    python 04_topics.py subscribe "orders.*"

    # Terminal 2 - Subscribe to all events
    python 04_topics.py subscribe "#"

    # Terminal 3 - Subscribe to payments only
    python 04_topics.py subscribe "payments.completed"

    # Terminal 4 - Publish messages
    python 04_topics.py publish orders.created "Order #123 created"
    python 04_topics.py publish orders.shipped "Order #123 shipped"
    python 04_topics.py publish payments.completed "Payment received"
"""

import sys
import json
from datetime import datetime
import pika


EXCHANGE_NAME = 'events'


def publish(topic: str, message: str):
    """Publish a message to a specific topic."""
    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost')
    )
    channel = connection.channel()

    # Declare topic exchange
    channel.exchange_declare(
        exchange=EXCHANGE_NAME,
        exchange_type='topic',
        durable=True
    )

    # Create message payload
    payload = json.dumps({
        'topic': topic,
        'message': message,
        'timestamp': datetime.now().isoformat()
    })

    channel.basic_publish(
        exchange=EXCHANGE_NAME,
        routing_key=topic,
        body=payload,
        properties=pika.BasicProperties(
            delivery_mode=pika.DeliveryMode.Persistent,
            content_type='application/json'
        )
    )

    print(f" [x] Published to '{topic}': {message}")
    connection.close()


def subscribe(pattern: str):
    """Subscribe to topics matching a pattern."""
    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost')
    )
    channel = connection.channel()

    channel.exchange_declare(
        exchange=EXCHANGE_NAME,
        exchange_type='topic',
        durable=True
    )

    # Create exclusive queue
    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue

    # Bind with pattern
    channel.queue_bind(
        exchange=EXCHANGE_NAME,
        queue=queue_name,
        routing_key=pattern
    )

    def callback(ch, method, properties, body):
        data = json.loads(body.decode())
        print(f" [x] [{method.routing_key}] {data['message']}")
        print(f"     Timestamp: {data['timestamp']}")

    channel.basic_consume(
        queue=queue_name,
        on_message_callback=callback,
        auto_ack=True
    )

    print(f" [*] Subscribed to pattern: '{pattern}'")
    print(' [*] Press CTRL+C to exit.')
    channel.start_consuming()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python 04_topics.py subscribe <pattern>")
        print("  python 04_topics.py publish <topic> <message>")
        print()
        print("Patterns:")
        print("  orders.*         - Match orders.created, orders.shipped, etc.")
        print("  payments.#       - Match all payment events")
        print("  *.completed      - Match orders.completed, payments.completed")
        print("  #                - Match everything")
        sys.exit(1)

    command = sys.argv[1]

    if command == 'subscribe':
        pattern = sys.argv[2] if len(sys.argv) > 2 else '#'
        try:
            subscribe(pattern)
        except KeyboardInterrupt:
            print('\nSubscriber stopped.')
    elif command == 'publish':
        if len(sys.argv) < 4:
            print("Usage: python 04_topics.py publish <topic> <message>")
            sys.exit(1)
        topic = sys.argv[2]
        message = sys.argv[3]
        publish(topic, message)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
