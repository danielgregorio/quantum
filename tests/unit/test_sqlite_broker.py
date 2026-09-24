"""
A message broker that survives the process.

The in-memory adapter lives inside one interpreter, so `quantum mq publish`
wrote into a broker discarded a moment later and `quantum mq consume` created
a fresh empty one — every message lost, both commands reporting success. Under
gunicorn the same thing happens per worker: four workers, four private queues.

The previous commit made the CLI warn about it. This makes it work.
"""

import subprocess
import sys

import pytest

from quantum.runtime.adapters.sqlite_adapter import SqliteAdapter
from quantum.runtime.message_broker import Message


@pytest.fixture
def db(tmp_path):
    return str(tmp_path / "m.db")


@pytest.fixture
def broker(db):
    b = SqliteAdapter(db)
    b.connect({})
    return b


class TestDurability:
    def test_a_message_survives_a_new_instance(self, db, broker):
        """The exact thing the in-memory adapter could not do."""
        broker.send("orders", Message(body={"id": 1}))
        other = SqliteAdapter(db)
        other.connect({})
        assert other.get_queue_info("orders").message_count == 1

    def test_it_survives_a_separate_PROCESS(self, db, broker):
        broker.send("queue", Message(body={"msg": "from another process"}))
        code = (
            "from quantum.runtime.adapters.sqlite_adapter import SqliteAdapter;"
            f"b=SqliteAdapter({db!r});b.connect({{}});"
            "m=b._take_one('queue','queue');"
            "print(m.body['msg'] if m else 'NOTHING')"
        )
        out = subprocess.run([sys.executable, "-c", code],
                             capture_output=True, text=True, timeout=60)
        assert "from another process" in out.stdout, out.stderr[-400:]


class TestQueueSemantics:
    def test_fifo(self, broker):
        for i in range(3):
            broker.send("q", Message(body={"i": i}))
        got = [broker._take_one("q", "queue").body["i"] for _ in range(3)]
        assert got == [0, 1, 2]

    def test_a_claimed_message_is_not_handed_out_twice(self, broker):
        broker.send("q", Message(body={"i": 1}))
        first = broker._take_one("q", "queue")
        second = broker._take_one("q", "queue")
        assert first is not None
        assert second is None, "the same message was delivered twice"

    def test_ack_removes_it(self, broker):
        broker.send("q", Message(body={"i": 1}))
        m = broker._take_one("q", "queue")
        broker.ack(m)
        assert broker.get_queue_info("q").message_count == 0

    def test_nack_requeues_it(self, broker):
        broker.send("q", Message(body={"i": 1}))
        m = broker._take_one("q", "queue")
        broker.nack(m, requeue=True)
        assert broker.get_queue_info("q").message_count == 1
        assert broker._take_one("q", "queue").body == {"i": 1}

    def test_nack_without_requeue_drops_it(self, broker):
        broker.send("q", Message(body={"i": 1}))
        broker.nack(broker._take_one("q", "queue"), requeue=False)
        assert broker.get_queue_info("q").message_count == 0

    def test_purge(self, broker):
        for i in range(4):
            broker.send("q", Message(body={"i": i}))
        assert broker.purge_queue("q") == 4
        assert broker.get_queue_info("q").message_count == 0


class TestTopicsAndQueuesAreSeparate:
    def test_a_topic_message_is_not_in_the_queue(self, broker):
        broker.publish("news", Message(body={"a": 1}))
        assert broker.get_queue_info("news").message_count == 0
        assert broker._take_one("news", "topic") is not None


class TestPayloadFidelity:
    @pytest.mark.parametrize("body", [
        {"a": 1}, ["x", "y"], "plain text", 42, {"nested": {"b": [1, 2]}},
    ])
    def test_the_body_round_trips(self, broker, body):
        broker.send("q", Message(body=body))
        assert broker._take_one("q", "queue").body == body

    def test_headers_round_trip(self, broker):
        broker.send("q", Message(body={}, headers={"source": "test"}))
        assert broker._take_one("q", "queue").headers == {"source": "test"}


class TestTheBrokerIsSelectable:
    """MESSAGE_BROKER_TYPE=sqlite raised "Unknown adapter type: sqlite".

    The durable broker existed and was reachable only from `quantum mq`. The
    documented way to ask for it — the environment variable the service's own
    docstring names — did not work.
    """

    def test_the_factory_knows_sqlite(self):
        from quantum.runtime.adapters import get_adapter
        from quantum.runtime.adapters.sqlite_adapter import SqliteAdapter
        assert isinstance(get_adapter('sqlite'), SqliteAdapter)

    def test_the_env_var_selects_it(self, tmp_path, monkeypatch):
        monkeypatch.setenv('MESSAGE_BROKER_TYPE', 'sqlite')
        monkeypatch.setenv('QUANTUM_MQ_PATH', str(tmp_path / 'mq.db'))
        from quantum.runtime.message_queue_service import MessageQueueService
        from quantum.runtime.adapters.sqlite_adapter import SqliteAdapter

        service = MessageQueueService()
        service.connect()
        try:
            assert isinstance(service._broker, SqliteAdapter)
            assert (tmp_path / 'mq.db').exists()
        finally:
            service.disconnect()

    def test_a_message_survives_a_new_service(self, tmp_path, monkeypatch):
        # The whole point: another process picks it up. A second service over
        # the same file is the same thing in one test.
        monkeypatch.setenv('MESSAGE_BROKER_TYPE', 'sqlite')
        monkeypatch.setenv('QUANTUM_MQ_PATH', str(tmp_path / 'mq.db'))
        from quantum.runtime.message_queue_service import MessageQueueService

        producer = MessageQueueService()
        producer.connect()
        assert producer.send('tasks', {'id': 7}).success
        producer.disconnect()

        consumer = MessageQueueService()
        consumer.connect()
        try:
            result = consumer.get_queue_info('tasks')
            assert result.success, result.error
            assert result.data['message_count'] == 1, "the message did not survive"
        finally:
            consumer.disconnect()

    def test_an_unknown_type_names_the_known_ones(self):
        from quantum.runtime.adapters import get_adapter
        with pytest.raises(ValueError, match="sqlite"):
            get_adapter('does-not-exist')

    def test_memory_says_what_it_costs(self, monkeypatch, caplog):
        # `memory` is now an explicit choice, not the default. It is still
        # legitimate — tests, a single process — and still has to warn what it
        # costs.
        import logging
        monkeypatch.setenv('MESSAGE_BROKER_TYPE', 'memory')
        from quantum.runtime.message_queue_service import MessageQueueService

        service = MessageQueueService()
        with caplog.at_level(logging.WARNING):
            service.connect()
        service.disconnect()
        assert "do not cross processes" in caplog.text

    def test_sqlite_is_the_default(self, tmp_path, monkeypatch):
        # The default was `memory`, which loses everything between processes:
        # under gunicorn, a private queue per worker. Silent data loss by default.
        monkeypatch.delenv('MESSAGE_BROKER_TYPE', raising=False)
        monkeypatch.setenv('QUANTUM_MQ_PATH', str(tmp_path / 'mq.db'))
        from quantum.runtime.message_queue_service import MessageQueueService
        from quantum.runtime.adapters.sqlite_adapter import SqliteAdapter

        service = MessageQueueService()
        service.connect()
        try:
            assert isinstance(service._broker, SqliteAdapter)
        finally:
            service.disconnect()

    def test_memory_is_still_reachable_on_purpose(self, monkeypatch):
        monkeypatch.setenv('MESSAGE_BROKER_TYPE', 'memory')
        from quantum.runtime.message_queue_service import MessageQueueService
        from quantum.runtime.adapters import MemoryAdapter

        service = MessageQueueService()
        service.connect()
        try:
            assert isinstance(service._broker, MemoryAdapter)
        finally:
            service.disconnect()

    def test_the_config_wins_over_the_default(self, monkeypatch):
        monkeypatch.delenv('MESSAGE_BROKER_TYPE', raising=False)
        from quantum.runtime.message_queue_service import MessageQueueService
        from quantum.runtime.adapters import MemoryAdapter

        service = MessageQueueService(config={'broker_type': 'memory'})
        service.connect()
        try:
            assert isinstance(service._broker, MemoryAdapter)
        finally:
            service.disconnect()


class TestDeadLetterQueue:
    """nack(requeue=False) must SEND to the DLQ, not drop.

    The adapter stored the `dlq` column in declare_queue and never read it: a
    queue with a declared DLQ behaved exactly like one without, and the
    rejected message vanished. The in-memory broker's equivalent test asserted
    `len(dlq_messages) >= 0`, which passes with an empty DLQ — that is why the
    difference between the two adapters went unnoticed.
    """

    def test_a_rejected_message_lands_in_the_dlq(self, broker):
        broker.declare_queue('main', dlq='dead')
        broker.send('main', Message(body='bad'))

        claimed = broker._take_one('main', 'queue')
        assert claimed is not None
        broker.nack(claimed, requeue=False)

        assert broker.get_queue_info('dead').message_count == 1

    def test_the_dlq_message_says_where_it_came_from(self, broker):
        broker.declare_queue('main', dlq='dead')
        broker.send('main', Message(body='bad'))
        broker.nack(broker._take_one('main', 'queue'), requeue=False)

        dead = broker._take_one('dead', 'queue')
        assert dead.body == 'bad'
        assert dead.headers.get('x-dead-letter-from') == 'main'

    def test_without_a_dlq_the_message_is_simply_done(self, broker):
        broker.declare_queue('no-dlq')
        broker.send('no-dlq', Message(body='bad'))
        broker.nack(broker._take_one('no-dlq', 'queue'), requeue=False)

        assert broker.get_queue_info('no-dlq').message_count == 0
        assert broker.list_queues().count('no-dlq') >= 1

    def test_requeue_still_puts_it_back_on_the_same_queue(self, broker):
        broker.declare_queue('main', dlq='dead')
        broker.send('main', Message(body='again'))
        broker.nack(broker._take_one('main', 'queue'), requeue=True)

        assert broker.get_queue_info('main').message_count == 1
        assert broker.get_queue_info('dead').message_count == 0


class TestTheBrokerDoesNotLoseMessages:
    """Three data-loss defects in the broker that became the DEFAULT.

    Found by the re-audit, all in code written in that session, all reproduced
    before fixing.
    """

    def test_nack_to_requeue_does_not_destroy_the_message(self, broker):
        # _poll_loop marked 'done' UNCONDITIONALLY after the handler.
        # A handler that called nack(requeue=True) — "put it back in the queue" —
        # saw the message destroyed on the next line.
        import time
        seen = []

        def handler(m):
            seen.append(m.body)
            broker.nack(m, requeue=True)

        broker.declare_queue('f')
        broker.consume('f', handler)
        broker.send('f', Message(body='important'))
        time.sleep(0.6)

        # The proof that it survived is the REDELIVERY. Counting 'ready' here
        # would give 0 even with the fix, because the consumer claims it again
        # in a loop — the first version of this test measured exactly the
        # wrong thing.
        assert len(seen) > 1, (
            f"nack(requeue=True) destroyed the message: {len(seen)} delivery(ies)")

    def test_ack_inside_the_handler_still_confirms(self, broker):
        import time
        broker.declare_queue('g')
        broker.consume('g', lambda m: broker.ack(m))
        broker.send('g', Message(body='x'))
        time.sleep(0.5)
        assert broker.get_queue_info('g').message_count == 0

    def test_a_handler_that_decides_nothing_confirms(self, broker):
        import time
        broker.declare_queue('h')
        broker.consume('h', lambda m: None)
        broker.send('h', Message(body='x'))
        time.sleep(0.5)
        assert broker.get_queue_info('h').message_count == 0

    def test_the_signature_matches_the_base_class(self, broker):
        # It was called `dlq=`; the base calls it `dead_letter_queue=`. The
        # service passes the base's name, so NO queue could be declared by it:
        # TypeError. The DLQ was unreachable through the normal path.
        broker.declare_queue('i', durable=True, dead_letter_queue='dlq')
        assert 'i' in broker.list_queues()

    def test_it_accepts_the_arguments_the_service_always_sends(self, broker):
        # exclusive/auto_delete do not exist in a file broker, but the service
        # always passes them. Raising on them blocked everything.
        broker.declare_queue('j', durable=True, exclusive=False,
                             auto_delete=False, dead_letter_queue=None, ttl=None)
        assert 'j' in broker.list_queues()

    def test_an_abandoned_message_goes_back_to_the_queue(self, broker):
        # A consumer that dies between claiming and confirming held the message
        # in 'inflight' forever: it did not come back, did not go to the DLQ,
        # did not show in the count. It vanished.
        import time
        broker.VISIBILITY_TIMEOUT = 0.3
        broker.send('k', Message(body='orphan'))
        assert broker._take_one('k', 'queue') is not None
        assert broker.get_queue_info('k').message_count == 0

        time.sleep(0.5)
        returned = broker._take_one('k', 'queue')
        assert returned is not None, "the message was stuck forever"
        assert returned.body == 'orphan'

    def test_a_message_being_processed_is_not_returned_early(self, broker):
        broker.VISIBILITY_TIMEOUT = 300.0
        broker.send('l', Message(body='x'))
        assert broker._take_one('l', 'queue') is not None
        assert broker._take_one('l', 'queue') is None, (
            "it returned a message that is still being processed")
