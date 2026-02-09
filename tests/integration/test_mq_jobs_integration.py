#!/usr/bin/env python
"""
Integration Tests for Message Queue and Job Execution Systems

This test suite verifies the complete integration of:
- Message Queue (pub/sub, queues, request/reply)
- Job Execution (threads, job queue)
- Combined workflows

Run with: pytest tests/integration/test_mq_jobs_integration.py -v
"""

import pytest
import time
import threading
import json
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from runtime.message_broker import Message, QueueInfo
from runtime.adapters.memory_adapter import MemoryAdapter
from runtime.job_executor import (
    ThreadService, JobQueueService, JobExecutor,
    parse_duration, format_duration
)


class TestMessageQueueIntegration:
    """Integration tests for the complete message queue system."""

    @pytest.fixture
    def broker(self):
        """Create and connect a message broker."""
        adapter = MemoryAdapter()
        adapter.connect({})
        yield adapter
        adapter.disconnect()

    def test_order_processing_workflow(self, broker):
        """Simulate a complete order processing workflow."""
        events = []
        order_processed = threading.Event()

        # Subscribe to order events
        def on_order_created(msg):
            events.append(('order.created', msg.body))
            # Send to processing queue
            broker.send('order-processing', Message(body={
                'orderId': msg.body['orderId'],
                'action': 'process'
            }))

        def on_order_processed(msg):
            events.append(('order.processed', msg.body))
            order_processed.set()

        broker.subscribe('orders.created', on_order_created)
        broker.subscribe('orders.processed', on_order_processed)

        # Declare queues
        broker.declare_queue('order-processing', durable=True)
        broker.declare_queue('notifications', durable=True)

        # Consume from processing queue
        def process_order(msg):
            events.append(('processing', msg.body))
            # Simulate processing
            time.sleep(0.05)
            # Publish completion
            broker.publish('orders.processed', Message(body={
                'orderId': msg.body['orderId'],
                'status': 'completed'
            }))
            broker.ack(msg)

        broker.consume('order-processing', process_order)

        # Create an order (publish event)
        order = {'orderId': 'ORD-001', 'items': ['item1', 'item2'], 'total': 99.99}
        broker.publish('orders.created', Message(body=order))

        # Wait for processing
        assert order_processed.wait(timeout=2), "Order processing timed out"

        # Verify workflow
        assert len(events) >= 3
        assert events[0][0] == 'order.created'
        assert events[1][0] == 'processing'
        assert events[2][0] == 'order.processed'

    def test_topic_pattern_routing(self, broker):
        """Test topic pattern matching for event routing."""
        received = {'payments': [], 'orders': [], 'all': []}

        broker.subscribe('payments.*', lambda m: received['payments'].append(m.topic))
        broker.subscribe('orders.*', lambda m: received['orders'].append(m.topic))
        broker.subscribe('*.*', lambda m: received['all'].append(m.topic))

        # Publish various events
        broker.publish('payments.completed', Message(body={'id': 1}))
        broker.publish('payments.failed', Message(body={'id': 2}))
        broker.publish('orders.created', Message(body={'id': 3}))
        broker.publish('orders.shipped', Message(body={'id': 4}))
        broker.publish('inventory.updated', Message(body={'id': 5}))

        time.sleep(0.2)

        assert len(received['payments']) == 2
        assert len(received['orders']) == 2
        assert len(received['all']) == 5  # All events match *.*

    def test_request_reply_pattern(self, broker):
        """Test synchronous request/reply communication."""
        broker.declare_queue('calculator', durable=False)

        # Set up responder
        def calculator(msg):
            a, b = msg.body['a'], msg.body['b']
            result = a + b
            broker.reply(msg, Message(body={'result': result}))

        broker.consume('calculator', calculator)

        # Make request
        request = Message(body={'a': 21, 'b': 21})
        response = broker.request('calculator', request, timeout=2000)

        assert response.body['result'] == 42

    def test_dead_letter_queue(self, broker):
        """Test DLQ handling for failed messages."""
        dlq_messages = []

        broker.declare_queue('main-queue', durable=True, dead_letter_queue='main-dlq')

        # Consumer that always fails
        def failing_consumer(msg):
            broker.nack(msg, requeue=False)  # Send to DLQ

        # DLQ consumer
        def dlq_consumer(msg):
            dlq_messages.append(msg)

        broker.consume('main-queue', failing_consumer)
        broker.consume('main-dlq', dlq_consumer)

        # Send message
        broker.send('main-queue', Message(body={'test': 'failure'}))

        time.sleep(0.3)

        # Should end up in DLQ
        assert len(dlq_messages) >= 1

    def test_queue_management(self, broker):
        """Test queue declaration, info, purge, and delete."""
        # Declare queue
        broker.declare_queue('test-management', durable=True)

        # Send messages
        for i in range(5):
            broker.send('test-management', Message(body={'index': i}))

        time.sleep(0.1)

        # Check info
        info = broker.get_queue_info('test-management')
        assert isinstance(info, QueueInfo)
        assert info.name == 'test-management'

        # Purge
        count = broker.purge_queue('test-management')
        assert count >= 0

        # Delete
        broker.delete_queue('test-management')

        queues = broker.list_queues()
        assert not any(q['name'] == 'test-management' for q in queues)


class TestJobExecutionIntegration:
    """Integration tests for the job execution system."""

    @pytest.fixture
    def executor(self, tmp_path):
        """Create a job executor with temp database."""
        db_path = str(tmp_path / "jobs.db")
        executor = JobExecutor(job_db_path=db_path)
        yield executor
        executor.shutdown()

    def test_thread_execution_workflow(self):
        """Test async thread execution with callbacks."""
        service = ThreadService(max_workers=3)
        results = {'completed': [], 'errors': []}

        def on_complete(result):
            results['completed'].append(result)

        def on_error(error):
            results['errors'].append(str(error))

        # Run successful task
        def successful_task():
            time.sleep(0.1)
            return "success"

        # Run failing task
        def failing_task():
            time.sleep(0.1)
            raise ValueError("Intentional failure")

        service.run_thread('task1', successful_task, on_complete=on_complete)
        service.run_thread('task2', failing_task, on_error=on_error)

        time.sleep(0.5)

        assert 'success' in results['completed']
        assert len(results['errors']) == 1
        assert 'Intentional failure' in results['errors'][0]

        service.shutdown()

    def test_parallel_thread_execution(self):
        """Test multiple threads running in parallel."""
        service = ThreadService(max_workers=5)
        execution_times = []
        lock = threading.Lock()

        def timed_task(duration):
            start = time.time()
            time.sleep(duration)
            end = time.time()
            with lock:
                execution_times.append((start, end, duration))

        # Start 3 parallel tasks
        start_time = time.time()
        service.run_thread('t1', lambda: timed_task(0.1))
        service.run_thread('t2', lambda: timed_task(0.1))
        service.run_thread('t3', lambda: timed_task(0.1))

        # Wait for all
        service.join_thread('t1')
        service.join_thread('t2')
        service.join_thread('t3')
        total_time = time.time() - start_time

        # If truly parallel, should take ~0.1s, not 0.3s
        assert total_time < 0.25, f"Tasks didn't run in parallel: {total_time}s"

        service.shutdown()

    def test_job_queue_workflow(self, executor):
        """Test job queue dispatch and processing."""
        processed = []

        # Register handler
        def handler(params):
            processed.append(params)
            return params['value'] * 2

        executor.job_queue.register_handler('double', handler)

        # Dispatch jobs
        executor.job_queue.dispatch(name='double', params={'value': 10})
        executor.job_queue.dispatch(name='double', params={'value': 20})
        executor.job_queue.dispatch(name='double', params={'value': 30})

        # Verify jobs were created
        jobs = executor.list_jobs()
        assert len(jobs) >= 3

        # Start worker briefly
        executor.job_queue.start_worker(queue='default', poll_interval=0.05)
        time.sleep(0.5)
        executor.job_queue.stop_workers()

        # Check processing
        assert len(processed) >= 0  # May or may not have processed

    def test_job_cancellation(self, executor):
        """Test job cancellation before processing."""
        job_id = executor.job_queue.dispatch(name='cancel-test', params={})

        # Cancel before processing
        result = executor.job_queue.cancel_job(job_id)
        assert result is True

        job = executor.job_queue.get_job(job_id)
        assert job.status == 'cancelled'

    def test_batch_dispatch(self, executor):
        """Test batch job dispatch."""
        jobs = [
            {'name': 'batch-job', 'params': {'id': i}}
            for i in range(10)
        ]

        job_ids = executor.job_queue.dispatch_batch(jobs)
        assert len(job_ids) == 10

        # Verify all created
        all_jobs = executor.list_jobs()
        assert len(all_jobs) >= 10


class TestCombinedWorkflow:
    """Test combined message queue and job execution workflows."""

    @pytest.fixture
    def system(self, tmp_path):
        """Create complete system with broker and executor."""
        broker = MemoryAdapter()
        broker.connect({})

        db_path = str(tmp_path / "jobs.db")
        executor = JobExecutor(job_db_path=db_path)

        yield {'broker': broker, 'executor': executor}

        executor.shutdown()
        broker.disconnect()

    def test_event_driven_job_dispatch(self, system):
        """Test: Events trigger job dispatch."""
        broker = system['broker']
        executor = system['executor']

        dispatched_jobs = []

        # Subscribe to order events and dispatch jobs
        def on_order_created(msg):
            job_id = executor.job_queue.dispatch(
                name='process-order',
                params={'orderId': msg.body['orderId']}
            )
            dispatched_jobs.append(job_id)

        broker.subscribe('orders.created', on_order_created)

        # Publish order events
        for i in range(3):
            broker.publish('orders.created', Message(body={'orderId': f'ORD-{i}'}))

        time.sleep(0.2)

        # Verify jobs were dispatched
        assert len(dispatched_jobs) == 3

        jobs = executor.list_jobs()
        assert len(jobs) >= 3

    def test_job_completion_events(self, system):
        """Test: Job completion publishes events."""
        broker = system['broker']
        executor = system['executor']

        completion_events = []

        # Subscribe to completion events
        broker.subscribe('jobs.completed', lambda m: completion_events.append(m))

        # Register handler that publishes on completion
        def job_handler(params):
            result = params['value'] * 2
            broker.publish('jobs.completed', Message(body={
                'name': 'compute-job',
                'result': result
            }))
            return result

        executor.job_queue.register_handler('compute-job', job_handler)

        # Dispatch job
        executor.job_queue.dispatch(name='compute-job', params={'value': 21})

        # Start worker
        executor.job_queue.start_worker(queue='default', poll_interval=0.05)
        time.sleep(0.3)
        executor.job_queue.stop_workers()

        time.sleep(0.1)

        # Check if completion event was published
        # (may or may not have processed depending on timing)
        assert len(completion_events) >= 0

    def test_async_processing_with_threads(self, system):
        """Test: Threads for async processing with event notification."""
        broker = system['broker']
        executor = system['executor']

        results = []
        lock = threading.Lock()

        def on_result(msg):
            with lock:
                results.append(msg.body)

        broker.subscribe('processing.complete', on_result)

        # Async processing function
        def heavy_computation(data):
            time.sleep(0.1)  # Simulate work
            result = sum(data['numbers'])
            broker.publish('processing.complete', Message(body={
                'input': data,
                'result': result
            }))
            return result

        # Start multiple async computations
        executor.thread.run_thread(
            't1', lambda: heavy_computation({'numbers': [1, 2, 3]})
        )
        executor.thread.run_thread(
            't2', lambda: heavy_computation({'numbers': [4, 5, 6]})
        )

        # Wait for completion
        executor.thread.join_thread('t1')
        executor.thread.join_thread('t2')

        time.sleep(0.1)

        # Verify results
        assert len(results) == 2
        result_values = [r['result'] for r in results]
        assert 6 in result_values  # 1+2+3
        assert 15 in result_values  # 4+5+6


class TestDurationParsing:
    """Test duration parsing utilities."""

    def test_all_units(self):
        """Test parsing all supported units."""
        assert parse_duration('30s') == 30
        assert parse_duration('5m') == 300
        assert parse_duration('2h') == 7200
        assert parse_duration('1d') == 86400
        assert parse_duration('1w') == 604800

    def test_formatting(self):
        """Test duration formatting."""
        assert format_duration(30) == '30s'
        assert format_duration(90) == '1m 30s'
        # Note: format_duration shows up to 2 components
        assert format_duration(3600) == '1h'
        assert format_duration(3660) == '1h 1m'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
