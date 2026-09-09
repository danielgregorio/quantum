#!/usr/bin/env python
"""
RabbitMQ Example 01: Hello World

The simplest possible producer/consumer example.

Usage:
    # Terminal 1 - Start consumer
    python 01_hello_world.py receive

    # Terminal 2 - Send message
    python 01_hello_world.py send "Hello World!"
"""

import sys
import pika


def send(message: str):
    """Send a message to the hello queue."""
    # Connect to RabbitMQ
    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost')
    )
    channel = connection.channel()

    # Declare queue (idempotent)
    channel.queue_declare(queue='hello')

    # Publish message
    channel.basic_publish(
        exchange='',          # Default exchange
        routing_key='hello',  # Queue name
        body=message
    )

    print(f" [x] Sent: {message}")
    connection.close()


def receive():
    """Receive messages from the hello queue."""
    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost')
    )
    channel = connection.channel()

    channel.queue_declare(queue='hello')

    def callback(ch, method, properties, body):
        print(f" [x] Received: {body.decode()}")

    channel.basic_consume(
        queue='hello',
        on_message_callback=callback,
        auto_ack=True
    )

    print(' [*] Waiting for messages. Press CTRL+C to exit.')
    channel.start_consuming()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python 01_hello_world.py [send|receive] [message]")
        sys.exit(1)

    command = sys.argv[1]

    if command == 'send':
        message = sys.argv[2] if len(sys.argv) > 2 else "Hello World!"
        send(message)
    elif command == 'receive':
        try:
            receive()
        except KeyboardInterrupt:
            print('\nGoodbye!')
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
