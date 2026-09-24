#!/usr/bin/env python
"""
RabbitMQ Example 05: RPC (Request/Reply)

Implements the request/reply pattern for synchronous-style
communication over RabbitMQ.

Usage:
    # Terminal 1 - Start RPC server
    python 05_rpc.py server

    # Terminal 2 - Make RPC calls
    python 05_rpc.py call 30
    python 05_rpc.py call 5
"""

import sys
import uuid
import json
import pika


QUEUE_NAME = 'rpc_queue'


def fib(n: int) -> int:
    """Calculate Fibonacci number (simulated heavy computation)."""
    if n == 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fib(n - 1) + fib(n - 2)


def start_server():
    """Start the RPC server."""
    connection = pika.BlockingConnection(
        pika.ConnectionParameters('localhost')
    )
    channel = connection.channel()

    channel.queue_declare(queue=QUEUE_NAME)

    # Only one request at a time
    channel.basic_qos(prefetch_count=1)

    def on_request(ch, method, props, body):
        request = json.loads(body.decode())
        n = request.get('n', 0)

        print(f" [.] Computing fib({n})")
        result = fib(n)
        print(f" [x] fib({n}) = {result}")

        response = json.dumps({'result': result})

        # Send response
        ch.basic_publish(
            exchange='',
            routing_key=props.reply_to,
            properties=pika.BasicProperties(
                correlation_id=props.correlation_id
            ),
            body=response
        )

        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(
        queue=QUEUE_NAME,
        on_message_callback=on_request
    )

    print(" [*] RPC Server ready. Press CTRL+C to exit.")
    channel.start_consuming()


class RpcClient:
    """RPC Client for making synchronous calls."""

    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters('localhost')
        )
        self.channel = self.connection.channel()

        # Create callback queue
        result = self.channel.queue_declare(queue='', exclusive=True)
        self.callback_queue = result.method.queue

        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self._on_response,
            auto_ack=True
        )

        self.response = None
        self.correlation_id = None

    def _on_response(self, ch, method, props, body):
        if self.correlation_id == props.correlation_id:
            self.response = json.loads(body.decode())

    def call(self, n: int) -> int:
        """Make an RPC call to compute Fibonacci."""
        self.response = None
        self.correlation_id = str(uuid.uuid4())

        request = json.dumps({'n': n})

        self.channel.basic_publish(
            exchange='',
            routing_key=QUEUE_NAME,
            properties=pika.BasicProperties(
                reply_to=self.callback_queue,
                correlation_id=self.correlation_id
            ),
            body=request
        )

        # Wait for response
        while self.response is None:
            self.connection.process_data_events(time_limit=None)

        return self.response['result']

    def close(self):
        self.connection.close()


def make_call(n: int):
    """Make an RPC call."""
    print(f" [x] Requesting fib({n})")

    client = RpcClient()
    result = client.call(n)
    client.close()

    print(f" [.] Got result: {result}")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python 05_rpc.py server")
        print("  python 05_rpc.py call <number>")
        sys.exit(1)

    command = sys.argv[1]

    if command == 'server':
        try:
            start_server()
        except KeyboardInterrupt:
            print('\nServer stopped.')
    elif command == 'call':
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        make_call(n)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
