"""
A message broker that survives the process.

The in-memory adapter lives inside one interpreter, so `quantum mq publish`
wrote into a broker discarded a moment later and `quantum mq consume` created
a fresh empty one — every message lost, both commands reporting success. Under
gunicorn the same thing happens per worker: four workers, four private queues.

The previous commit made the CLI warn about it. This makes it work.
"""

import json
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
        broker.send("pedidos", Message(body={"id": 1}))
        other = SqliteAdapter(db)
        other.connect({})
        assert other.get_queue_info("pedidos").message_count == 1

    def test_it_survives_a_separate_PROCESS(self, db, broker):
        broker.send("fila", Message(body={"msg": "de outro processo"}))
        code = (
            "from quantum.runtime.adapters.sqlite_adapter import SqliteAdapter;"
            f"b=SqliteAdapter({db!r});b.connect({{}});"
            "m=b._take_one('fila','queue');"
            "print(m.body['msg'] if m else 'NADA')"
        )
        out = subprocess.run([sys.executable, "-c", code],
                             capture_output=True, text=True, timeout=60)
        assert "de outro processo" in out.stdout, out.stderr[-400:]


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
        broker.publish("noticias", Message(body={"a": 1}))
        assert broker.get_queue_info("noticias").message_count == 0
        assert broker._take_one("noticias", "topic") is not None


class TestPayloadFidelity:
    @pytest.mark.parametrize("body", [
        {"a": 1}, ["x", "y"], "texto simples", 42, {"aninhado": {"b": [1, 2]}},
    ])
    def test_the_body_round_trips(self, broker, body):
        broker.send("q", Message(body=body))
        assert broker._take_one("q", "queue").body == body

    def test_headers_round_trip(self, broker):
        broker.send("q", Message(body={}, headers={"origem": "teste"}))
        assert broker._take_one("q", "queue").headers == {"origem": "teste"}


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
        assert producer.send('tarefas', {'id': 7}).success
        producer.disconnect()

        consumer = MessageQueueService()
        consumer.connect()
        try:
            result = consumer.get_queue_info('tarefas')
            assert result.success, result.error
            assert result.data['message_count'] == 1, "the message did not survive"
        finally:
            consumer.disconnect()

    def test_an_unknown_type_names_the_known_ones(self):
        from quantum.runtime.adapters import get_adapter
        with pytest.raises(ValueError, match="sqlite"):
            get_adapter('nao-existe')

    def test_memory_says_what_it_costs(self, monkeypatch, caplog):
        # `memory` agora e escolha explicita, nao o default. Continua sendo
        # legitima — teste, processo unico — e continua tendo de avisar o que
        # custa.
        import logging
        monkeypatch.setenv('MESSAGE_BROKER_TYPE', 'memory')
        from quantum.runtime.message_queue_service import MessageQueueService

        service = MessageQueueService()
        with caplog.at_level(logging.WARNING):
            service.connect()
        service.disconnect()
        assert "do not cross processes" in caplog.text

    def test_sqlite_is_the_default(self, tmp_path, monkeypatch):
        # O default era `memory`, que perde tudo entre processos: sob gunicorn,
        # uma fila privada por worker. Perda silenciosa de dados como padrao.
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
    """nack(requeue=False) tem que MANDAR para a DLQ, nao descartar.

    O adapter guardava a coluna `dlq` em declare_queue e nunca a lia: uma
    fila com DLQ declarada se comportava exatamente como uma sem, e a
    mensagem rejeitada sumia. O teste equivalente do broker em memoria
    afirmava `len(dlq_messages) >= 0`, que passa com a DLQ vazia — foi por
    isso que a diferenca entre os dois adapters passou despercebida.
    """

    def test_a_rejected_message_lands_in_the_dlq(self, broker):
        broker.declare_queue('principal', dlq='mortas')
        broker.send('principal', Message(body='ruim'))

        claimed = broker._take_one('principal', 'queue')
        assert claimed is not None
        broker.nack(claimed, requeue=False)

        assert broker.get_queue_info('mortas').message_count == 1

    def test_the_dlq_message_says_where_it_came_from(self, broker):
        broker.declare_queue('principal', dlq='mortas')
        broker.send('principal', Message(body='ruim'))
        broker.nack(broker._take_one('principal', 'queue'), requeue=False)

        dead = broker._take_one('mortas', 'queue')
        assert dead.body == 'ruim'
        assert dead.headers.get('x-dead-letter-from') == 'principal'

    def test_without_a_dlq_the_message_is_simply_done(self, broker):
        broker.declare_queue('sem-dlq')
        broker.send('sem-dlq', Message(body='ruim'))
        broker.nack(broker._take_one('sem-dlq', 'queue'), requeue=False)

        assert broker.get_queue_info('sem-dlq').message_count == 0
        assert broker.list_queues().count('sem-dlq') >= 1

    def test_requeue_still_puts_it_back_on_the_same_queue(self, broker):
        broker.declare_queue('principal', dlq='mortas')
        broker.send('principal', Message(body='de novo'))
        broker.nack(broker._take_one('principal', 'queue'), requeue=True)

        assert broker.get_queue_info('principal').message_count == 1
        assert broker.get_queue_info('mortas').message_count == 0


class TestOBrokerNaoPerdeMensagem:
    """Tres defeitos de perda de dado no broker que virou PADRAO.

    Achados pela re-auditoria, todos em codigo escrito nesta sessao, todos
    reproduzidos antes de consertar.
    """

    def test_nack_para_devolver_nao_destroi_a_mensagem(self, broker):
        # _poll_loop marcava 'done' INCONDICIONALMENTE depois do handler.
        # Um handler que chamava nack(requeue=True) — "devolve para a fila" —
        # via a mensagem ser destruida na linha seguinte.
        import time
        vistas = []

        def handler(m):
            vistas.append(m.body)
            broker.nack(m, requeue=True)

        broker.declare_queue('f')
        broker.consume('f', handler)
        broker.send('f', Message(body='importante'))
        time.sleep(0.6)

        # A prova de que ela sobreviveu e a REENTREGA. Medir a contagem de
        # 'ready' aqui daria 0 mesmo com o conserto, porque o consumidor
        # reivindica de novo em loop — a primeira versao deste teste media
        # exatamente a coisa errada.
        assert len(vistas) > 1, (
            f"nack(requeue=True) destruiu a mensagem: {len(vistas)} entrega(s)")

    def test_ack_dentro_do_handler_continua_confirmando(self, broker):
        import time
        broker.declare_queue('g')
        broker.consume('g', lambda m: broker.ack(m))
        broker.send('g', Message(body='x'))
        time.sleep(0.5)
        assert broker.get_queue_info('g').message_count == 0

    def test_handler_que_nao_decide_nada_confirma(self, broker):
        import time
        broker.declare_queue('h')
        broker.consume('h', lambda m: None)
        broker.send('h', Message(body='x'))
        time.sleep(0.5)
        assert broker.get_queue_info('h').message_count == 0

    def test_a_assinatura_bate_com_a_classe_base(self, broker):
        # Chamava-se `dlq=`; a base chama `dead_letter_queue=`. O servico
        # passa o nome da base, entao NENHUMA fila podia ser declarada por
        # ele: TypeError. A DLQ ficava inalcancavel pelo caminho normal.
        broker.declare_queue('i', durable=True, dead_letter_queue='dlq')
        assert 'i' in broker.list_queues()

    def test_aceita_os_argumentos_que_o_servico_sempre_manda(self, broker):
        # exclusive/auto_delete nao existem num broker de arquivo, mas o
        # servico os passa sempre. Levantar por eles impedia tudo.
        broker.declare_queue('j', durable=True, exclusive=False,
                             auto_delete=False, dead_letter_queue=None, ttl=None)
        assert 'j' in broker.list_queues()

    def test_mensagem_abandonada_volta_para_a_fila(self, broker):
        # Consumidor que morre entre reivindicar e confirmar prendia a
        # mensagem em 'inflight' para sempre: nao voltava, nao ia para a DLQ,
        # nao aparecia na contagem. Sumia.
        import time
        broker.VISIBILITY_TIMEOUT = 0.3
        broker.send('k', Message(body='orfa'))
        assert broker._take_one('k', 'queue') is not None
        assert broker.get_queue_info('k').message_count == 0

        time.sleep(0.5)
        devolvida = broker._take_one('k', 'queue')
        assert devolvida is not None, "a mensagem ficou presa para sempre"
        assert devolvida.body == 'orfa'

    def test_uma_mensagem_em_processamento_nao_e_devolvida_cedo(self, broker):
        broker.VISIBILITY_TIMEOUT = 300.0
        broker.send('l', Message(body='x'))
        assert broker._take_one('l', 'queue') is not None
        assert broker._take_one('l', 'queue') is None, (
            "devolveu uma mensagem que ainda esta sendo processada")
