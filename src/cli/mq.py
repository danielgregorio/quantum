#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quantum CLI - Message Queue Commands

Commands for managing message queues, publishing messages, and running consumers.
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def create_mq_parser(subparsers):
    """Add mq subcommand to CLI parser"""
    mq_parser = subparsers.add_parser(
        'mq',
        help='Message queue operations',
        description='Commands for managing message queues, topics, and consumers'
    )

    mq_sub = mq_parser.add_subparsers(dest='mq_action', help='MQ action')

    # Queues management
    queues_parser = mq_sub.add_parser('queues', help='Manage message queues')
    queues_sub = queues_parser.add_subparsers(dest='queues_action', help='Queue action')

    list_queues = queues_sub.add_parser('list', help='List all queues')
    list_queues.add_argument('--format', choices=['table', 'json'], default='table')

    create_queue = queues_sub.add_parser('create', help='Create a queue')
    create_queue.add_argument('name', help='Queue name')
    create_queue.add_argument('--durable', action='store_true', default=True, help='Durable queue')
    create_queue.add_argument('--dlq', help='Dead letter queue name')
    create_queue.add_argument('--ttl', type=int, help='Message TTL in milliseconds')

    delete_queue = queues_sub.add_parser('delete', help='Delete a queue')
    delete_queue.add_argument('name', help='Queue name')
    delete_queue.add_argument('--force', action='store_true', help='Force delete even if not empty')

    purge_queue = queues_sub.add_parser('purge', help='Purge all messages from a queue')
    purge_queue.add_argument('name', help='Queue name')

    peek_queue = queues_sub.add_parser('peek', help='Peek messages without consuming')
    peek_queue.add_argument('name', help='Queue name')
    peek_queue.add_argument('--limit', type=int, default=10, help='Number of messages to peek')
    peek_queue.add_argument('--format', choices=['table', 'json'], default='table')

    # Topics management
    topics_parser = mq_sub.add_parser('topics', help='Manage topics')
    topics_sub = topics_parser.add_subparsers(dest='topics_action', help='Topic action')

    list_topics = topics_sub.add_parser('list', help='List all topics')
    list_topics.add_argument('--format', choices=['table', 'json'], default='table')

    # Publish message
    publish_parser = mq_sub.add_parser('publish', help='Publish a message to a topic')
    publish_parser.add_argument('topic', help='Topic name')
    publish_parser.add_argument('message', nargs='?', help='Message body (JSON string or plain text)')
    publish_parser.add_argument('--file', help='Read message from file')
    publish_parser.add_argument('--header', action='append', dest='headers',
                                help='Add header (format: key=value)')

    # Send to queue
    send_parser = mq_sub.add_parser('send', help='Send a message to a queue')
    send_parser.add_argument('queue', help='Queue name')
    send_parser.add_argument('message', nargs='?', help='Message body (JSON string or plain text)')
    send_parser.add_argument('--file', help='Read message from file')
    send_parser.add_argument('--header', action='append', dest='headers',
                             help='Add header (format: key=value)')
    send_parser.add_argument('--delay', type=int, help='Delay in seconds before delivery')

    # Consume messages
    consume_parser = mq_sub.add_parser('consume', help='Consume messages from a queue')
    consume_parser.add_argument('queue', help='Queue name')
    consume_parser.add_argument('--limit', type=int, default=1, help='Number of messages to consume')
    consume_parser.add_argument('--timeout', type=int, default=5, help='Timeout in seconds')
    consume_parser.add_argument('--ack', action='store_true', help='Auto-acknowledge messages')
    consume_parser.add_argument('--format', choices=['table', 'json'], default='json')

    # Subscribe to topic
    subscribe_parser = mq_sub.add_parser('subscribe', help='Subscribe to a topic (real-time)')
    subscribe_parser.add_argument('topic', help='Topic pattern (supports wildcards)')
    subscribe_parser.add_argument('--format', choices=['raw', 'json'], default='json')

    # Worker mode
    worker_parser = mq_sub.add_parser('worker', help='Start a message worker')
    worker_parser.add_argument('--queues', required=True, help='Queues to consume (comma-separated)')
    worker_parser.add_argument('--handler', help='Handler script (.q file)')
    worker_parser.add_argument('--concurrency', type=int, default=4, help='Number of concurrent consumers')
    worker_parser.add_argument('--prefetch', type=int, default=1, help='Prefetch count')

    # Stats
    stats_parser = mq_sub.add_parser('stats', help='Show message broker statistics')
    stats_parser.add_argument('--format', choices=['table', 'json'], default='table')

    # Connection info
    info_parser = mq_sub.add_parser('info', help='Show connection information')

    return mq_parser


def handle_mq(args) -> int:
    """Handle mq command"""
    from runtime.message_broker import MessageBroker, Message
    from runtime.adapters.memory_adapter import InMemoryAdapter

    if not args.mq_action:
        print("Usage: quantum mq <action>")
        print("Actions: queues, topics, publish, send, consume, subscribe, worker, stats, info")
        return 1

    try:
        # Initialize broker (use in-memory by default, can be configured)
        broker = _get_broker()

        if args.mq_action == 'queues':
            return _handle_mq_queues(broker, args)
        elif args.mq_action == 'topics':
            return _handle_mq_topics(broker, args)
        elif args.mq_action == 'publish':
            return _handle_mq_publish(broker, args)
        elif args.mq_action == 'send':
            return _handle_mq_send(broker, args)
        elif args.mq_action == 'consume':
            return _handle_mq_consume(broker, args)
        elif args.mq_action == 'subscribe':
            return _handle_mq_subscribe(broker, args)
        elif args.mq_action == 'worker':
            return _handle_mq_worker(broker, args)
        elif args.mq_action == 'stats':
            return _handle_mq_stats(broker, args)
        elif args.mq_action == 'info':
            return _handle_mq_info(broker, args)
        else:
            print(f"Unknown action: {args.mq_action}")
            return 1

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return 1


def _get_broker():
    """Get message broker instance based on configuration"""
    import os

    broker_type = os.environ.get('QUANTUM_MQ_BROKER', 'memory')

    if broker_type == 'rabbitmq':
        try:
            from runtime.adapters.rabbitmq_adapter import RabbitMQAdapter
            broker = RabbitMQAdapter()
            broker.connect({
                'host': os.environ.get('RABBITMQ_HOST', 'localhost'),
                'port': int(os.environ.get('RABBITMQ_PORT', 5672)),
                'username': os.environ.get('RABBITMQ_USER', 'guest'),
                'password': os.environ.get('RABBITMQ_PASS', 'guest'),
                'vhost': os.environ.get('RABBITMQ_VHOST', '/'),
            })
            return broker
        except ImportError:
            print("[WARN] RabbitMQ adapter not available, using in-memory")

    elif broker_type == 'redis':
        try:
            from runtime.adapters.redis_adapter import RedisAdapter
            broker = RedisAdapter()
            broker.connect({
                'host': os.environ.get('REDIS_HOST', 'localhost'),
                'port': int(os.environ.get('REDIS_PORT', 6379)),
                'db': int(os.environ.get('REDIS_DB', 0)),
                'password': os.environ.get('REDIS_PASSWORD'),
            })
            return broker
        except ImportError:
            print("[WARN] Redis adapter not available, using in-memory")

    # Default: in-memory
    from runtime.adapters.memory_adapter import InMemoryAdapter
    broker = InMemoryAdapter()
    broker.connect({})
    return broker


def _parse_headers(headers_list):
    """Parse headers from command line format"""
    if not headers_list:
        return {}

    result = {}
    for h in headers_list:
        if '=' in h:
            key, value = h.split('=', 1)
            result[key.strip()] = value.strip()
    return result


def _handle_mq_queues(broker, args) -> int:
    """Handle queue management commands"""
    if not args.queues_action:
        print("Usage: quantum mq queues <list|create|delete|purge|peek>")
        return 1

    if args.queues_action == 'list':
        queues = broker.list_queues() if hasattr(broker, 'list_queues') else []

        if args.format == 'json':
            print(json.dumps(queues, indent=2))
        else:
            if not queues:
                print("No queues found.")
                return 0

            print(f"{'Queue':<30} {'Messages':<10} {'Consumers':<10}")
            print("-" * 55)
            for q in queues:
                name = q if isinstance(q, str) else q.get('name', 'unknown')
                messages = q.get('messages', 0) if isinstance(q, dict) else 0
                consumers = q.get('consumers', 0) if isinstance(q, dict) else 0
                print(f"{name:<30} {messages:<10} {consumers:<10}")

        return 0

    elif args.queues_action == 'create':
        options = {
            'durable': args.durable,
        }
        if args.dlq:
            options['dead_letter_queue'] = args.dlq
        if args.ttl:
            options['ttl'] = args.ttl

        broker.declare_queue(args.name, **options)
        print(f"Queue created: {args.name}")
        return 0

    elif args.queues_action == 'delete':
        if hasattr(broker, 'delete_queue'):
            broker.delete_queue(args.name, force=args.force)
            print(f"Queue deleted: {args.name}")
        else:
            print("Delete queue not supported by this broker")
            return 1
        return 0

    elif args.queues_action == 'purge':
        if hasattr(broker, 'purge_queue'):
            count = broker.purge_queue(args.name)
            print(f"Purged {count} message(s) from queue: {args.name}")
        else:
            print("Purge queue not supported by this broker")
            return 1
        return 0

    elif args.queues_action == 'peek':
        if hasattr(broker, 'peek_queue'):
            messages = broker.peek_queue(args.name, limit=args.limit)
        else:
            print("Peek not supported by this broker")
            return 1

        if args.format == 'json':
            print(json.dumps([m.__dict__ for m in messages], indent=2, default=str))
        else:
            if not messages:
                print("No messages in queue.")
                return 0

            print(f"{'ID':<36} {'Body (truncated)':<50}")
            print("-" * 90)
            for msg in messages:
                body_str = str(msg.body)[:50]
                print(f"{msg.id:<36} {body_str:<50}")

        return 0

    return 1


def _handle_mq_topics(broker, args) -> int:
    """Handle topics management"""
    if not args.topics_action:
        print("Usage: quantum mq topics <list>")
        return 1

    if args.topics_action == 'list':
        topics = broker.list_topics() if hasattr(broker, 'list_topics') else []

        if args.format == 'json':
            print(json.dumps(topics, indent=2))
        else:
            if not topics:
                print("No topics found.")
                return 0

            print("Topics:")
            for t in topics:
                print(f"  - {t}")

        return 0

    return 1


def _handle_mq_publish(broker, args) -> int:
    """Publish message to topic"""
    from runtime.message_broker import Message

    # Get message body
    if args.file:
        with open(args.file, 'r') as f:
            body = f.read()
    elif args.message:
        body = args.message
    else:
        print("Error: Message body required (use positional argument or --file)")
        return 1

    # Try to parse as JSON
    try:
        body = json.loads(body)
    except json.JSONDecodeError:
        pass  # Keep as string

    # Create message
    message = Message(
        topic=args.topic,
        body=body,
        headers=_parse_headers(args.headers)
    )

    # Publish
    broker.publish(args.topic, message)
    print(f"Published to topic: {args.topic}")
    print(f"Message ID: {message.id}")

    return 0


def _handle_mq_send(broker, args) -> int:
    """Send message to queue"""
    from runtime.message_broker import Message

    # Get message body
    if args.file:
        with open(args.file, 'r') as f:
            body = f.read()
    elif args.message:
        body = args.message
    else:
        print("Error: Message body required (use positional argument or --file)")
        return 1

    # Try to parse as JSON
    try:
        body = json.loads(body)
    except json.JSONDecodeError:
        pass  # Keep as string

    # Create message
    message = Message(
        queue=args.queue,
        body=body,
        headers=_parse_headers(args.headers)
    )

    # Send (with delay if specified)
    if args.delay:
        if hasattr(broker, 'send_delayed'):
            broker.send_delayed(args.queue, message, delay=args.delay)
        else:
            print("[WARN] Delayed send not supported, sending immediately")
            broker.send(args.queue, message)
    else:
        broker.send(args.queue, message)

    print(f"Sent to queue: {args.queue}")
    print(f"Message ID: {message.id}")

    return 0


def _handle_mq_consume(broker, args) -> int:
    """Consume messages from queue"""
    import time

    messages = []
    start_time = time.time()

    def handler(msg):
        messages.append(msg)
        if args.ack:
            broker.ack(msg)

    # Start consuming
    consumer_id = broker.consume(args.queue, handler)

    # Wait for messages
    while len(messages) < args.limit and (time.time() - start_time) < args.timeout:
        time.sleep(0.1)

    # Stop consumer if supported
    if hasattr(broker, 'cancel_consumer'):
        broker.cancel_consumer(consumer_id)

    # Output
    if args.format == 'json':
        print(json.dumps([{
            'id': m.id,
            'body': m.body,
            'headers': m.headers,
            'timestamp': m.timestamp
        } for m in messages], indent=2, default=str))
    else:
        for msg in messages:
            print(f"--- Message {msg.id} ---")
            print(json.dumps(msg.body, indent=2) if isinstance(msg.body, dict) else msg.body)
            print()

    if not messages:
        print("No messages received within timeout.")

    return 0


def _handle_mq_subscribe(broker, args) -> int:
    """Subscribe to topic (real-time)"""
    print(f"Subscribing to topic: {args.topic}")
    print("Press Ctrl+C to stop.\n")

    def handler(msg):
        if args.format == 'json':
            print(json.dumps({
                'topic': msg.topic,
                'body': msg.body,
                'headers': msg.headers,
                'timestamp': msg.timestamp
            }, indent=2, default=str))
        else:
            print(f"[{msg.topic}] {msg.body}")

    try:
        consumer_id = broker.subscribe(args.topic, handler)

        # Keep running
        import time
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nUnsubscribing...")
        if hasattr(broker, 'unsubscribe'):
            broker.unsubscribe(consumer_id)

    return 0


def _handle_mq_worker(broker, args) -> int:
    """Start message worker"""
    queues = [q.strip() for q in args.queues.split(',')]

    print(f"Starting message worker...")
    print(f"  Queues: {', '.join(queues)}")
    print(f"  Concurrency: {args.concurrency}")
    print(f"  Prefetch: {args.prefetch}")
    if args.handler:
        print(f"  Handler: {args.handler}")
    print("")
    print("Press Ctrl+C to stop.\n")

    # Load handler if specified
    handler_func = None
    if args.handler:
        from core.parser import QuantumParser
        from runtime.component import ComponentRuntime

        parser = QuantumParser()
        runtime = ComponentRuntime()
        ast = parser.parse_file(args.handler)

        def handler_func(msg):
            context = {'message': msg}
            runtime.execute(ast, context)
    else:
        def handler_func(msg):
            print(f"[{msg.queue}] {msg.id}: {msg.body}")

    consumers = []

    try:
        for queue in queues:
            for i in range(args.concurrency):
                consumer_id = broker.consume(queue, handler_func)
                consumers.append(consumer_id)
                print(f"Started consumer {i+1} for queue: {queue}")

        # Keep running
        import time
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nStopping workers...")
        for consumer_id in consumers:
            if hasattr(broker, 'cancel_consumer'):
                broker.cancel_consumer(consumer_id)
        print("Workers stopped.")

    return 0


def _handle_mq_stats(broker, args) -> int:
    """Show broker statistics"""
    stats = broker.get_stats() if hasattr(broker, 'get_stats') else {}

    if args.format == 'json':
        print(json.dumps(stats, indent=2, default=str))
    else:
        print("Message Broker Statistics")
        print("-" * 40)
        for key, value in stats.items():
            print(f"  {key}: {value}")

    return 0


def _handle_mq_info(broker, args) -> int:
    """Show connection info"""
    info = broker.get_info() if hasattr(broker, 'get_info') else {}

    print("Message Broker Connection")
    print("-" * 40)
    print(f"  Type: {type(broker).__name__}")
    for key, value in info.items():
        print(f"  {key}: {value}")

    return 0
