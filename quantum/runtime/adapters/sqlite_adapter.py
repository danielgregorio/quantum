"""
A message broker that survives the process.

The in-memory adapter lives inside one interpreter, so `quantum mq publish`
wrote into a broker that was discarded a moment later and `quantum mq consume`
created a fresh empty one — every message lost, both commands reporting
success. Under gunicorn the same thing happens per worker: four workers, four
private queues.

This stores messages in SQLite, the same way JobQueueService already stores
jobs, so a publish in one process is visible to a consume in another and
survives a restart. No server to run.

It is not a replacement for RabbitMQ or Redis at scale — consumers POLL, and
there is no clustering. It is the honest default: durable, ordered, with real
ack/nack semantics, and adequate for the single-host deployments this
framework targets.
"""

import json
import sqlite3
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from quantum.runtime.message_broker import (
    MessageBroker, Message, QueueInfo,
)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS quantum_messages (
    id            TEXT PRIMARY KEY,
    destination   TEXT NOT NULL,      -- queue name, or topic for pub/sub
    kind          TEXT NOT NULL,      -- 'queue' | 'topic'
    body          TEXT NOT NULL,      -- JSON
    headers       TEXT NOT NULL,      -- JSON
    reply_to      TEXT,
    correlation_id TEXT,
    state         TEXT NOT NULL DEFAULT 'ready',   -- ready | inflight | done
    delivered_at  TEXT,
    created_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_messages_pick
    ON quantum_messages (destination, kind, state, created_at);

CREATE TABLE IF NOT EXISTS quantum_queues (
    name       TEXT PRIMARY KEY,
    durable    INTEGER NOT NULL DEFAULT 1,
    dlq        TEXT,
    created_at TEXT NOT NULL
);
"""


class SqliteAdapter(MessageBroker):
    """Durable, cross-process message broker backed by a SQLite file."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or 'quantum_messages.db'
        self._connected = False
        self._lock = threading.RLock()
        self._subs: Dict[str, Dict[str, Any]] = {}
        self._threads: Dict[str, threading.Thread] = {}
        self._running = False

    # -- connection --------------------------------------------------------

    def _conn(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def connect(self, config: Dict[str, Any] = None) -> None:
        config = config or {}
        if config.get('path'):
            self.db_path = config['path']
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = self._conn()
        try:
            conn.executescript(_SCHEMA)
            conn.commit()
        finally:
            conn.close()
        self._connected = True
        self._running = True

    def disconnect(self) -> None:
        self._running = False
        with self._lock:
            self._subs.clear()
        self._threads.clear()
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    # -- producing ---------------------------------------------------------

    def _store(self, destination: str, kind: str, message: Message) -> None:
        conn = self._conn()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO quantum_messages "
                "(id, destination, kind, body, headers, reply_to, "
                " correlation_id, state, created_at) "
                "VALUES (?,?,?,?,?,?,?,'ready',?)",
                (
                    message.id or str(uuid.uuid4()),
                    destination,
                    kind,
                    json.dumps(message.body, default=str),
                    json.dumps(message.headers or {}, default=str),
                    message.reply_to,
                    message.correlation_id,
                    datetime.now().isoformat(),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def publish(self, topic: str, message: Message) -> None:
        self._store(topic, 'topic', message)

    def send(self, queue: str, message: Message) -> None:
        self._store(queue, 'queue', message)

    def request(self, queue: str, message: Message, timeout: int = 5000) -> Message:
        """Request/reply. Polls the reply queue until the timeout."""
        reply_to = message.reply_to or f"reply.{uuid.uuid4().hex[:12]}"
        message.reply_to = reply_to
        message.correlation_id = message.correlation_id or str(uuid.uuid4())
        self.send(queue, message)

        deadline = time.time() + (timeout / 1000.0)
        while time.time() < deadline:
            got = self._take_one(reply_to, 'queue')
            if got is not None:
                self._mark_done(got.id)
                return got
            time.sleep(0.05)
        raise TimeoutError(
            f"no reply on {reply_to!r} within {timeout}ms"
        )

    # -- consuming ---------------------------------------------------------

    def _row_to_message(self, row) -> Message:
        return Message(
            id=row['id'],
            topic=row['destination'] if row['kind'] == 'topic' else None,
            queue=row['destination'] if row['kind'] == 'queue' else None,
            body=json.loads(row['body']),
            headers=json.loads(row['headers']),
            reply_to=row['reply_to'],
            correlation_id=row['correlation_id'],
        )

    # Depois de quanto tempo uma mensagem reivindicada e considerada
    # abandonada. Sem isto, um consumidor que morre entre reivindicar e
    # confirmar prende a mensagem em 'inflight' PARA SEMPRE: ela nao volta
    # para a fila, nao vai para a DLQ e nao aparece na contagem. Some.
    VISIBILITY_TIMEOUT = 300.0     # segundos

    def _reclaim_abandoned(self, conn, destination: str, kind: str) -> None:
        """Devolve para a fila o que ficou reivindicado tempo demais."""
        limite = datetime.fromtimestamp(
            time.time() - self.VISIBILITY_TIMEOUT).isoformat()
        conn.execute(
            "UPDATE quantum_messages SET state='ready', delivered_at=NULL "
            "WHERE destination = ? AND kind = ? AND state = 'inflight' "
            "  AND delivered_at IS NOT NULL AND delivered_at < ?",
            (destination, kind, limite),
        )

    def _take_one(self, destination: str, kind: str) -> Optional[Message]:
        """Claim the oldest ready message, atomically."""
        with self._lock:
            conn = self._conn()
            try:
                self._reclaim_abandoned(conn, destination, kind)
                row = conn.execute(
                    "SELECT * FROM quantum_messages "
                    "WHERE destination = ? AND kind = ? AND state = 'ready' "
                    "ORDER BY created_at ASC LIMIT 1",
                    (destination, kind),
                ).fetchone()
                if not row:
                    return None
                # Claim it. The WHERE state='ready' makes this safe against a
                # second process that read the same row a moment ago.
                changed = conn.execute(
                    "UPDATE quantum_messages SET state='inflight', delivered_at=? "
                    "WHERE id = ? AND state = 'ready'",
                    (datetime.now().isoformat(), row['id']),
                ).rowcount
                conn.commit()
                if not changed:
                    return None
                return self._row_to_message(row)
            finally:
                conn.close()

    def _mark_done(self, message_id: str) -> None:
        conn = self._conn()
        try:
            conn.execute(
                "UPDATE quantum_messages SET state='done' WHERE id = ?",
                (message_id,),
            )
            conn.commit()
        finally:
            conn.close()

    def _mark_ready(self, message_id: str) -> None:
        conn = self._conn()
        try:
            conn.execute(
                "UPDATE quantum_messages SET state='ready', delivered_at=NULL "
                "WHERE id = ?",
                (message_id,),
            )
            conn.commit()
        finally:
            conn.close()

    def _poll_loop(self, sub_id: str, destination: str, kind: str,
                   handler: Callable, poll_interval: float = 0.1):
        while self._running and sub_id in self._subs:
            msg = self._take_one(destination, kind)
            if msg is None:
                time.sleep(poll_interval)
                continue
            try:
                handler(msg)
                # `done` so quando o handler NAO decidiu nada. Isto marcava
                # done incondicionalmente, entao um handler que chamava
                # `nack(msg, requeue=True)` — "devolve para a fila" — via a
                # mensagem ser DESTRUIDA logo depois: o nack a punha em
                # 'ready' e a linha seguinte a punha em 'done'. Perda de
                # dado no broker que e o padrao.
                self._finish_if_untouched(msg.id)
            except Exception:
                # Put it back rather than losing it; the handler failing is
                # not evidence the message is bad.
                self._mark_ready(msg.id)
                time.sleep(poll_interval)

    def _finish_if_untouched(self, message_id: str) -> None:
        """Confirma a mensagem so se o handler nao a tiver movido.

        `WHERE state = 'inflight'` e a guarda: se o handler chamou ack (done)
        ou nack (ready, ou movida para a DLQ), o estado ja mudou e este
        UPDATE nao casa com nada.
        """
        conn = self._conn()
        try:
            conn.execute(
                "UPDATE quantum_messages SET state='done' "
                "WHERE id = ? AND state = 'inflight'",
                (message_id,),
            )
            conn.commit()
        finally:
            conn.close()

    def _start_sub(self, destination: str, kind: str, handler: Callable) -> str:
        sub_id = str(uuid.uuid4())
        with self._lock:
            self._subs[sub_id] = {'destination': destination, 'kind': kind}
        t = threading.Thread(
            target=self._poll_loop, args=(sub_id, destination, kind, handler),
            daemon=True,
        )
        self._threads[sub_id] = t
        t.start()
        return sub_id

    def subscribe(self, topic: str, handler: Callable) -> str:
        return self._start_sub(topic, 'topic', handler)

    def consume(self, queue: str, handler: Callable, prefetch: int = 1) -> str:
        return self._start_sub(queue, 'queue', handler)

    def unsubscribe(self, subscription_id: str) -> None:
        with self._lock:
            self._subs.pop(subscription_id, None)
        self._threads.pop(subscription_id, None)

    def ack(self, message: Message) -> None:
        self._mark_done(message.id)

    def nack(self, message: Message, requeue: bool = True) -> None:
        if requeue:
            self._mark_ready(message.id)
            return

        # requeue=False means "this message is bad" — it belongs in the dead
        # letter queue, which is the whole point of declaring one. This
        # marked it done and the message VANISHED: declare_queue stored the
        # dlq column and nothing ever read it, so a queue with a DLQ behaved
        # exactly like a queue without one. The memory adapter routes it; the
        # test that should have caught the difference asserted
        # `len(dlq_messages) >= 0`.
        dlq = self._dlq_for(message.queue) if message.queue else None
        if dlq:
            self._store(dlq, 'queue', Message(
                body=message.body,
                headers={**(message.headers or {}),
                         'x-dead-letter-from': message.queue or ''},
                reply_to=message.reply_to,
                correlation_id=message.correlation_id,
            ))
        self._mark_done(message.id)

    def _dlq_for(self, queue: str) -> Optional[str]:
        """The dead letter queue declared for `queue`, if any."""
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT dlq FROM quantum_queues WHERE name = ?", (queue,)
            ).fetchone()
        finally:
            conn.close()
        return row['dlq'] if row and row['dlq'] else None

    # -- queue administration ---------------------------------------------

    def declare_queue(self, name: str, durable: bool = True,
                      dead_letter_queue: str = None, ttl: int = None,
                      max_length: int = None, dlq: str = None,
                      exclusive: bool = False, auto_delete: bool = False) -> None:
        """Declara uma fila.

        O parametro se chamava `dlq`, e a classe base chama
        `dead_letter_queue`. MessageQueueService passa o nome da base, entao
        NENHUMA fila podia ser declarada pelo servico: TypeError. E como este
        adapter virou o broker padrao, a DLQ que eu tinha acabado de ligar era
        inalcancavel pelo caminho normal.

        `dlq=` continua aceito porque os testes e o codigo interno o usam.
        `exclusive` e `auto_delete` sao aceitos e IGNORADOS: o servico os
        passa sempre, e nao ha conexao exclusiva nem fila efemera num broker
        de arquivo. Levantar TypeError por eles impedia declarar qualquer
        fila; fingir que os implementa seria pior.
        """
        dead_letter_queue = dead_letter_queue or dlq
        conn = self._conn()
        try:
            conn.execute(
                "INSERT OR IGNORE INTO quantum_queues (name, durable, dlq, created_at) "
                "VALUES (?,?,?,?)",
                (name, 1 if durable else 0, dead_letter_queue,
                 datetime.now().isoformat()),
            )
            conn.commit()
        finally:
            conn.close()

    def purge_queue(self, name: str) -> int:
        conn = self._conn()
        try:
            n = conn.execute(
                "DELETE FROM quantum_messages WHERE destination = ? AND kind = 'queue'",
                (name,),
            ).rowcount
            conn.commit()
            return n
        finally:
            conn.close()

    def delete_queue(self, name: str) -> None:
        conn = self._conn()
        try:
            conn.execute("DELETE FROM quantum_messages WHERE destination = ?", (name,))
            conn.execute("DELETE FROM quantum_queues WHERE name = ?", (name,))
            conn.commit()
        finally:
            conn.close()

    def get_queue_info(self, name: str) -> QueueInfo:
        conn = self._conn()
        try:
            ready = conn.execute(
                "SELECT COUNT(*) FROM quantum_messages "
                "WHERE destination = ? AND kind = 'queue' AND state = 'ready'",
                (name,),
            ).fetchone()[0]
            row = conn.execute(
                "SELECT durable FROM quantum_queues WHERE name = ?", (name,)
            ).fetchone()
        finally:
            conn.close()
        return QueueInfo(
            name=name,
            message_count=ready,
            consumer_count=sum(
                1 for s in self._subs.values() if s['destination'] == name
            ),
            durable=bool(row['durable']) if row else True,
        )

    def list_queues(self) -> List[str]:
        conn = self._conn()
        try:
            return [r[0] for r in conn.execute(
                "SELECT DISTINCT destination FROM quantum_messages WHERE kind='queue' "
                "UNION SELECT name FROM quantum_queues"
            )]
        finally:
            conn.close()
