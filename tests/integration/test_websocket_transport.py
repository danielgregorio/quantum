"""
q:websocket now opens a real socket. This proves it against a real server.

The old behaviour: register_connection made a record in state CONNECTING,
nothing ever moved it to OPEN, and send_message — which only acts when the
state is OPEN — always returned False into a list nothing drained. No bytes
ever left the process.

Every test here runs a live websockets server on localhost, so a failure
means the transport is broken, not that a mock drifted.
"""

import asyncio
import json
import threading
import time

import pytest

from quantum.runtime.websocket_service import WebSocketService, WebSocketState
from quantum.runtime.websocket_transport import HAS_WEBSOCKETS, reset_transport

pytestmark = pytest.mark.skipif(
    not HAS_WEBSOCKETS, reason="the 'websockets' package is not installed"
)


class EchoServer:
    """A real websocket server on a background loop. Echoes, and records.

    Shutdown closes the live connections before the loop goes away — a loop
    that merely stops leaves the sockets open, and then the client never
    learns the server is gone.
    """

    def __init__(self, transform=None):
        self.received = []
        self.port = None
        self._transform = transform or (lambda m: m)
        self._loop = None
        self._thread = None
        self._stop = None            # asyncio.Event, made on the loop
        self._ready = threading.Event()
        self._error = None

    async def _handler(self, sock):
        try:
            async for raw in sock:
                self.received.append(raw)
                await sock.send(self._transform(raw))
        except Exception:
            pass

    def start(self):
        import websockets

        def run():
            loop = asyncio.new_event_loop()
            self._loop = loop
            asyncio.set_event_loop(loop)

            async def main():
                self._stop = asyncio.Event()
                async with websockets.serve(
                        self._handler, "127.0.0.1", 0) as server:
                    self.port = server.sockets[0].getsockname()[1]
                    self._ready.set()
                    await self._stop.wait()

            try:
                loop.run_until_complete(main())
            except Exception as exc:
                self._error = exc
                self._ready.set()
            finally:
                loop.close()

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()
        assert self._ready.wait(timeout=10), "server did not start"
        assert self._error is None, f"server failed: {self._error}"
        return self

    @property
    def url(self):
        return f"ws://127.0.0.1:{self.port}"

    def stop(self):
        if self._loop and self._loop.is_running() and self._stop is not None:
            self._loop.call_soon_threadsafe(self._stop.set)
        if self._thread:
            self._thread.join(timeout=5)


@pytest.fixture
def server():
    s = EchoServer().start()
    yield s
    s.stop()


@pytest.fixture
def svc():
    yield WebSocketService()
    reset_transport()


def wait_for(predicate, timeout=5.0):
    """Poll a condition — the handlers run on another thread."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


class TestItActuallyConnects:
    def test_auto_connect_opens_the_socket(self, svc, server):
        conn = svc.register_connection(
            name="chat", url=server.url, metadata={"auto_connect": True})
        assert conn.state == WebSocketState.OPEN
        assert conn.to_dict()["connected"] is True
        assert conn.to_dict()["transport"] == "websockets"

    def test_without_auto_connect_nothing_is_opened(self, svc, server):
        conn = svc.register_connection(name="chat", url=server.url)
        assert conn.state == WebSocketState.CONNECTING
        assert conn.to_dict()["transport"] == "none"

    def test_open_can_be_called_later(self, svc, server):
        svc.register_connection(name="chat", url=server.url)
        assert svc.open("chat") is True
        assert svc.get_connection("chat").state == WebSocketState.OPEN

    def test_a_refused_connection_reports_closed_not_connecting(self, svc):
        # Port 1 on loopback: nothing listens. The old code left such a
        # connection in CONNECTING forever, which reads as "in progress".
        conn = svc.register_connection(
            name="dead", url="ws://127.0.0.1:1/",
            metadata={"auto_connect": True})
        assert conn.state == WebSocketState.CLOSED
        assert conn.error
        assert conn.to_dict()["connected"] is False


class TestBytesActuallyMove:
    def test_send_reaches_the_server(self, svc, server):
        svc.register_connection(
            name="chat", url=server.url, metadata={"auto_connect": True})

        assert svc.send_message("chat", "ola") is True
        assert wait_for(lambda: "ola" in server.received), server.received

    def test_json_is_serialised_on_the_wire(self, svc, server):
        svc.register_connection(
            name="chat", url=server.url, metadata={"auto_connect": True})

        svc.send_message("chat", {"tipo": "oi", "n": 1}, msg_type="json")
        assert wait_for(lambda: server.received)
        assert json.loads(server.received[0]) == {"tipo": "oi", "n": 1}

    def test_the_reply_arrives_at_the_on_message_handler(self, svc, server):
        got = []
        svc.register_handler("chat", "message", lambda d: got.append(d))
        svc.register_connection(
            name="chat", url=server.url, metadata={"auto_connect": True})

        svc.send_message("chat", "ping")
        assert wait_for(lambda: got), "no message reached the handler"
        assert got[0]["data"] == "ping"

    def test_a_json_reply_arrives_parsed(self, svc, server):
        got = []
        svc.register_handler("chat", "message", lambda d: got.append(d))
        svc.register_connection(
            name="chat", url=server.url, metadata={"auto_connect": True})

        svc.send_message("chat", {"a": 1}, msg_type="json")
        assert wait_for(lambda: got)
        assert got[0]["data"] == {"a": 1}

    def test_the_connect_handler_fires(self, svc, server):
        fired = []
        svc.register_handler("chat", "connect", lambda d: fired.append(d))
        svc.register_connection(
            name="chat", url=server.url, metadata={"auto_connect": True})
        assert wait_for(lambda: fired), "on-connect never fired"

    def test_message_count_tracks_real_traffic(self, svc, server):
        svc.register_connection(
            name="chat", url=server.url, metadata={"auto_connect": True})
        svc.send_message("chat", "um")
        svc.send_message("chat", "dois")
        conn = svc.get_connection("chat")
        assert wait_for(lambda: conn.message_count == 2), conn.message_count


class TestClosing:
    def test_close_shuts_the_socket_down(self, svc, server):
        svc.register_connection(
            name="chat", url=server.url, metadata={"auto_connect": True})
        conn = svc.get_connection("chat")

        svc.close_connection("chat", code=1000, reason="tchau")

        from quantum.runtime.websocket_transport import get_transport
        assert wait_for(lambda: not get_transport().is_open(conn.id))

    def test_send_after_close_does_not_claim_success(self, svc, server):
        svc.register_connection(
            name="chat", url=server.url, metadata={"auto_connect": True})
        svc.close_connection("chat")
        assert wait_for(
            lambda: svc.get_connection("chat").state != WebSocketState.OPEN)
        assert svc.send_message("chat", "tarde demais") is False

    def test_the_close_handler_fires_when_the_server_goes_away(
            self, svc, server):
        closed = []
        svc.register_handler("chat", "close", lambda d: closed.append(d))
        svc.register_connection(
            name="chat", url=server.url, metadata={"auto_connect": True})

        server.stop()
        assert wait_for(lambda: closed, timeout=8), "on-close never fired"


class TestBroadcastSendsOneFramePerConnection:
    """`broadcast` mandava N frames para cada uma das N conexoes.

    O laco de `broadcast` chamava `send_message(conn.name, ...)`, e
    send_message ja percorre TODAS as conexoes com aquele nome. Com N
    conexoes chamadas "chat" saiam N*N frames — cada cliente via a mesma
    mensagem N vezes — e o retorno dizia N, o numero de conexoes, nao o de
    frames. Numa sala de 50 pessoas: 2500 frames e 50 copias por pessoa.
    """

    def test_tres_conexoes_recebem_uma_copia_cada(self, svc, server):
        for _ in range(3):
            svc.register_connection(
                name="chat", url=server.url, metadata={"auto_connect": True})

        assert len(svc.get_connections_by_name("chat")) == 3

        enviadas = svc.broadcast("chat", "oi", msg_type="text")

        assert enviadas == 3
        # Tres frames no servidor, nao nove.
        assert wait_for(lambda: len(server.received) >= 3)
        time.sleep(0.3)                      # deixa qualquer excedente chegar
        assert server.received == ["oi", "oi", "oi"], server.received

    def test_a_fila_de_saida_de_cada_conexao_tem_uma_mensagem(self, svc, server):
        for _ in range(3):
            svc.register_connection(
                name="chat", url=server.url, metadata={"auto_connect": True})

        svc.broadcast("chat", "x", msg_type="text")

        for conn in svc.get_connections_by_name("chat"):
            pendentes = svc.get_pending_messages(conn.id)
            assert len(pendentes) == 1, (conn.id, len(pendentes))


class TestUmHandlerLentoNaoTravaAsOutrasConexoes:
    """Um unico worker para o transporte inteiro serializava tudo.

    O executor era `max_workers=1` para TODAS as conexoes, com a
    justificativa de preservar a ordem das mensagens. A ordem so importa
    dentro de uma conexao; o efeito era que um on-message lento de uma
    conexao segurava a fila de todas as outras.
    """

    def test_a_conexao_b_e_entregue_enquanto_a_a_esta_ocupada(self, svc, server):
        segurando = threading.Event()
        libera = threading.Event()
        chegou_b = threading.Event()

        def handler_lento(_d):
            segurando.set()
            libera.wait(timeout=10)

        svc.register_handler("lenta", "message", handler_lento)
        svc.register_handler("rapida", "message", lambda d: chegou_b.set())

        svc.register_connection(name="lenta", url=server.url,
                                metadata={"auto_connect": True})
        svc.register_connection(name="rapida", url=server.url,
                                metadata={"auto_connect": True})

        svc.send_message("lenta", "trava")
        assert segurando.wait(timeout=5), "o handler lento nunca comecou"

        # Com a conexao "lenta" parada dentro do handler, a "rapida" tem de
        # ser entregue assim mesmo.
        inicio = time.time()
        svc.send_message("rapida", "passa")
        # O proprio send_message tinha de voltar na hora: ele pedia o mesmo
        # lock que o handler lento segurava, entao a THREAD QUE CHAMA ficava
        # presa tambem — nao so a entrega.
        gasto_no_send = time.time() - inicio
        entregue = chegou_b.wait(timeout=5)
        decorrido = time.time() - inicio
        libera.set()

        assert gasto_no_send < 3.0, (
            f"send_message ficou {gasto_no_send:.1f}s preso atras do handler")
        assert entregue, "a conexao rapida ficou presa atras da lenta"
        assert decorrido < 3.0, f"a entrega levou {decorrido:.1f}s"


class TestShutdown:
    def test_nao_gasta_o_timeout_inteiro_por_conexao(self, svc, server):
        """shutdown() prendia self._lock durante o fechamento.

        close() espera o `sock.close()` terminar na thread do event loop, e o
        pump() daquela conexao, ao terminar, precisa do MESMO lock no seu
        finally. Com o lock preso, o loop parava, o close nunca completava e
        cada conexao gastava os 5s inteiros do timeout. Tres conexoes = 15s.
        """
        from quantum.runtime.websocket_transport import get_transport

        for _ in range(3):
            svc.register_connection(
                name="chat", url=server.url, metadata={"auto_connect": True})

        inicio = time.time()
        get_transport().shutdown()
        decorrido = time.time() - inicio

        # Margem larga de proposito: o defeito custava >=15s, o correto custa
        # centesimos. Qualquer numero entre os dois ja separa os dois mundos.
        assert decorrido < 4.0, f"shutdown levou {decorrido:.1f}s"

    def test_encerra_as_threads_de_handler(self, svc, server):
        """As threads de dispatch ficavam vivas depois do shutdown."""
        from quantum.runtime.websocket_transport import get_transport

        svc.register_connection(name="chat", url=server.url,
                                metadata={"auto_connect": True})
        svc.send_message("chat", "oi")
        assert wait_for(
            lambda: any(t.name.startswith('quantum-ws-')
                        for t in threading.enumerate()))

        get_transport().shutdown()

        assert wait_for(
            lambda: not any(t.name.startswith('quantum-ws-')
                            for t in threading.enumerate()),
            timeout=5), [t.name for t in threading.enumerate()]

    def test_o_on_close_do_app_roda_no_shutdown(self, svc, server):
        """Encerrar o transporte nao pode engolir o `on-close` do app.

        Aposentar os workers ANTES de fechar as conexoes deixaria o handler
        de fechamento sem ninguem para executa-lo — e o shutdown e
        exatamente quando o app quer saber que a conexao caiu.
        """
        from quantum.runtime.websocket_transport import get_transport

        fechou = []
        svc.register_handler("chat", "close", lambda d: fechou.append(d))
        svc.register_connection(name="chat", url=server.url,
                                metadata={"auto_connect": True})

        get_transport().shutdown()

        assert wait_for(lambda: fechou), "o on-close nunca rodou"

    def test_da_para_reconectar_depois_de_um_shutdown(self, svc, server):
        """O transporte e um singleton de processo: fechar tudo nao pode
        aposenta-lo."""
        from quantum.runtime.websocket_transport import get_transport

        svc.register_connection(name="chat", url=server.url,
                                metadata={"auto_connect": True})
        get_transport().shutdown()

        recebidas = []
        svc2 = WebSocketService()
        svc2.register_handler("chat2", "message", lambda d: recebidas.append(d))
        conn = svc2.register_connection(name="chat2", url=server.url,
                                        metadata={"auto_connect": True})
        assert conn.state == WebSocketState.OPEN
        svc2.send_message("chat2", "de novo")
        assert wait_for(lambda: recebidas), "handler nao voltou a funcionar"
