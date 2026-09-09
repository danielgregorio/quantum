#!/usr/bin/env python
"""
RabbitMQ Example 02: Work Queue

Distributes time-consuming tasks among multiple workers.
Uses manual acknowledgment to ensure messages aren't lost.

Usage:
    # Terminal 1 & 2 - Start workers
    python 02_work_queue.py worker

    # Terminal 3 - Send tasks
    python 02_work_queue.py task "Process order #123"
    python 02_work_queue.py task "Generate report..."
    python 02_work_queue.py task "Send email....."
"""

import sys
import time
import pika


QUEUE_NAME = 'task_queue'


def send_task(message: str):
    """Send a task to the work queue."""
    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost')
    )
    channel = connection.channel()

    # Durable queue survives broker restart
    channel.queue_declare(queue=QUEUE_NAME, durable=True)

    # Persistent message
    channel.basic_publish(
        exchange='',
        routing_key=QUEUE_NAME,
        body=message,
        properties=pika.BasicProperties(
            delivery_mode=pika.DeliveryMode.Persistent
        )
    )

    print(f" [x] Sent task: {message}")
    connection.close()


def worker():
    """Process tasks from the work queue."""
    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost')
    )
    channel = connection.channel()

    channel.queue_declare(queue=QUEUE_NAME, durable=True)

    # Fair dispatch: don't give more than one message at a time
    channel.basic_qos(prefetch_count=1)

    def callback(ch, method, properties, body):
        message = body.decode()
        print(f" [x] Received: {message}")

        # Simulate work (1 second per dot in message)
        dots = message.count('.')
        time.sleep(dots)

        print(f" [x] Done in {dots}s")

        # Manual acknowledgment
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(
        queue=QUEUE_NAME,
        on_message_callback=callback,
        auto_ack=False  # Manual ack
    )

    print(' [*] Worker waiting for tasks. Press CTRL+C to exit.')
    channel.start_consuming()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python 02_work_queue.py [task|worker] [message]")
        sys.exit(1)

    command = sys.argv[1]

    if command == 'task':
        message = sys.argv[2] if len(sys.argv) > 2 else "Default task..."
        send_task(message)
    elif command == 'worker':
        try:
            worker()
        except KeyboardInterrupt:
            print('\nWorker stopped.')
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
