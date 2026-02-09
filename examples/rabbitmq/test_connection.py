#!/usr/bin/env python
"""
Test RabbitMQ Connection

Quick script to verify RabbitMQ is running and accessible.

Usage:
    python test_connection.py
"""

import sys


def test_pika_import():
    """Test that pika is installed."""
    print("1. Testing pika import...")
    try:
        import pika
        print(f"   OK - pika version: {pika.__version__}")
        return True
    except ImportError:
        print("   FAIL - pika not installed")
        print("   Run: pip install pika")
        return False


def test_connection():
    """Test connection to RabbitMQ."""
    print("\n2. Testing RabbitMQ connection...")
    try:
        import pika

        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host='localhost',
                port=5672,
                credentials=pika.PlainCredentials('guest', 'guest'),
                connection_attempts=3,
                retry_delay=1
            )
        )

        print("   OK - Connected to RabbitMQ")

        channel = connection.channel()
        print("   OK - Channel created")

        # Test queue operations
        result = channel.queue_declare(queue='test_queue', durable=False)
        print(f"   OK - Test queue created: {result.method.queue}")

        # Cleanup
        channel.queue_delete(queue='test_queue')
        print("   OK - Test queue deleted")

        connection.close()
        print("   OK - Connection closed")

        return True

    except Exception as e:
        print(f"   FAIL - {e}")
        print("\n   Make sure RabbitMQ is running:")
        print("   - Docker: docker run -d -p 5672:5672 -p 15672:15672 rabbitmq:management")
        print("   - Or use docker-compose in this directory")
        return False


def test_quantum_adapter():
    """Test the Quantum RabbitMQ adapter."""
    print("\n3. Testing Quantum RabbitMQ adapter...")
    try:
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

        from runtime.adapters.rabbitmq_adapter import RabbitMQAdapter
        from runtime.message_broker import Message

        adapter = RabbitMQAdapter()
        print("   OK - Adapter created")

        adapter.connect({
            'host': 'localhost',
            'port': 5672,
            'username': 'guest',
            'password': 'guest',
            'exchange': 'quantum_test'
        })
        print("   OK - Adapter connected")

        # Test queue
        adapter.declare_queue('quantum_test_queue', durable=False)
        print("   OK - Queue declared")

        # Test send/receive
        msg = Message(body={'test': True, 'value': 42})
        adapter.send('quantum_test_queue', msg)
        print(f"   OK - Message sent: {msg.id}")

        # Test queue info
        info = adapter.get_queue_info('quantum_test_queue')
        print(f"   OK - Queue info: {info.message_count} messages")

        # Cleanup
        adapter.purge_queue('quantum_test_queue')
        adapter.delete_queue('quantum_test_queue')
        adapter.disconnect()
        print("   OK - Cleanup complete")

        return True

    except Exception as e:
        print(f"   FAIL - {e}")
        return False


def main():
    print("=" * 50)
    print("RabbitMQ Connection Test")
    print("=" * 50)

    results = []

    results.append(("pika import", test_pika_import()))

    if results[-1][1]:
        results.append(("connection", test_connection()))

        if results[-1][1]:
            results.append(("quantum adapter", test_quantum_adapter()))

    print("\n" + "=" * 50)
    print("Results:")
    print("=" * 50)

    all_passed = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("All tests passed! RabbitMQ is ready to use.")
        print()
        print("Try the examples:")
        print("  python 01_hello_world.py receive")
        print("  python 01_hello_world.py send 'Hello!'")
    else:
        print("Some tests failed. Check the output above.")
        sys.exit(1)


if __name__ == '__main__':
    main()
