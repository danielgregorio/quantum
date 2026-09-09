#!/usr/bin/env python
"""
RabbitMQ Example 03: Publish/Subscribe (Fanout)

Broadcasts messages to all connected subscribers.
Uses a fanout exchange to deliver messages to all queues.

Usage:
    # Terminal 1 & 2 - Start subscribers
    python 03_pubsub.py subscribe

    # Terminal 3 - Publish messages
    python 03_pubsub.py publish "Breaking news!"
"""

import sys
import pika


EXCHANGE_NAME = 'logs'


def publish(message: str):
    """Publish a message to all subscribers."""
    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost')
    )
    channel = connection.channel()

    # Declare fanout exchange (broadcasts to all bound queues)
    channel.exchange_declare(
        exchange=EXCHANGE_NAME,
        exchange_type='fanout'
    )

    channel.basic_publish(
        exchange=EXCHANGE_NAME,
        routing_key='',  # Ignored for fanout
        body=message
    )

    print(f" [x] Published: {message}")
    connection.close()


def subscribe():
    """Subscribe to all messages from the fanout exchange."""
    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost')
    )
    channel = connection.channel()

    channel.exchange_declare(
        exchange=EXCHANGE_NAME,
        exchange_type='fanout'
    )

    # Create exclusive queue (auto-deleted when connection closes)
    result = channel.queue_declare(queue='', exclusive=True)
    queue_name = result.method.queue

    # Bind queue to exchange
    channel.queue_bind(
        exchange=EXCHANGE_NAME,
        queue=queue_name
    )

    def callback(ch, method, properties, body):
        print(f" [x] Received: {body.decode()}")

    channel.basic_consume(
        queue=queue_name,
        on_message_callback=callback,
        auto_ack=True
    )

    print(f' [*] Subscriber ready (queue: {queue_name}). Press CTRL+C to exit.')
    channel.start_consuming()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python 03_pubsub.py [publish|subscribe] [message]")
        sys.exit(1)

    command = sys.argv[1]

    if command == 'publish':
        message = sys.argv[2] if len(sys.argv) > 2 else "Hello subscribers!"
        publish(message)
    elif command == 'subscribe':
        try:
            subscribe()
        except KeyboardInterrupt:
            print('\nSubscriber stopped.')
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
