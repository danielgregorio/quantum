"""
The websocket transport that q:websocket never had.

Before this, `quantum/runtime/websocket_service.py` was pure bookkeeping: it
created a connection record in state CONNECTING, nothing ever moved it to
OPEN, and send_message — which only queues when the state is OPEN — always
returned False into a list nothing drained. The tag returned a
connection-shaped dict for a connection that did not exist.

This opens real client connections with the `websockets` library, on a
background asyncio loop, and drives the state machine and the handlers the
service already defines. It is deliberately a CLIENT transport: `q:websocket
url="wss://..."` connects a Quantum app to somewhere else, which is what the
tag's url= attribute always meant.

Optional by design: if `websockets` is not installed the service keeps its
honest stub behaviour and says so, rather than failing to import.
"""

import asyncio
import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger('quantum.websocket')

try:
    import websockets as _ws
    HAS_WEBSOCKETS = True
except ImportError:            # pragma: no cover - environment dependent
    _ws = None
    HAS_WEBSOCKETS = False


class WebSocketTransport:
    """Owns one background event loop and the live client connections on it."""

    def __init__(self):
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._sockets: Dict[str, Any] = {}      # connection id -> protocol
        self._lock = threading.RLock()
        # q:websocket handlers are Quantum bodies: they run a component
        # context and can block for a while. Running them on the event loop
        # would stall every other connection, so they go to a worker thread.
        #
        # UM executor POR CONEXAO, com um unico worker cada.
        #
        # Era um executor unico com max_workers=1 para o transporte inteiro,
        # justificado por "one, so message order is preserved". A ordem por
        # conexao esta certa; o alcance nao estava. Com um so worker, um
        # handler on-message lento de UMA conexao segurava a fila de TODAS —
        # dez conexoes, e um <q:query> de 2s numa delas atrasava as outras
        # nove em 2s cada. Nada em q:websocket ordena mensagens de conexoes
        # diferentes entre si, entao nao ha ordem a preservar ali.
        #
        # Um worker por conexao mantem a ordem onde ela existe e isola as
        # conexoes umas das outras.
        self._dispatchers: Dict[str, ThreadPoolExecutor] = {}
        self._closed = False

    def _dispatcher_for(self, conn_id: str) -> Optional[ThreadPoolExecutor]:
        with self._lock:
            pool = self._dispatchers.get(conn_id)
            if pool is not None:
                # Um worker que JA existe continua aceitando trabalho mesmo
                # durante o shutdown: e por ele que passa o on_close de cada
                # conexao sendo fechada. Recusar aqui faria o corpo
                # `on-close` do app nunca rodar num encerramento — que e
                # justamente quando ele importa.
                return pool
            if self._closed:
                return None
            pool = ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix=f'quantum-ws-{conn_id[:8]}')
            self._dispatchers[conn_id] = pool
            return pool

    def _fire(self, conn_id: str, fn: Callable, *args) -> None:
        """Run a user handler off the event loop, never letting it escape."""
        def guarded():
            try:
                fn(*args)
            except Exception:
                logger.exception("q:websocket handler raised")

        pool = self._dispatcher_for(conn_id)
        if pool is None:
            return
        try:
            pool.submit(guarded)
        except RuntimeError:      # pool already shut down
            pass

    # -- loop lifecycle ----------------------------------------------------

    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        with self._lock:
            # Um shutdown() nao pode aposentar o transporte: get_transport()
            # devolve um singleton de processo, e reconectar depois de fechar
            # tudo e uso normal.
            self._closed = False
            if self._loop and self._loop.is_running():
                return self._loop
            self._loop = asyncio.new_event_loop()

            def run():
                asyncio.set_event_loop(self._loop)
                self._loop.run_forever()

            self._thread = threading.Thread(
                target=run, name="quantum-websocket", daemon=True)
            self._thread.start()
            return self._loop

    def shutdown(self) -> None:
        # As conexoes sao fechadas FORA do lock.
        #
        # Antes o laco inteiro rodava com self._lock preso. close() espera o
        # `sock.close()` terminar no event loop — e o pump() daquela conexao,
        # ao terminar, faz `with self._lock` no finally, na thread do loop.
        # Com o lock preso aqui, o loop parava no finally, `sock.close()`
        # nunca completava, e cada close() gastava os 5s inteiros do timeout
        # antes de desistir. Cinco conexoes abertas = 25 segundos de shutdown.
        with self._lock:
            self._closed = True
            conn_ids = list(self._sockets)

        # Fechar PRIMEIRO, com os workers ainda vivos: o on_close de cada
        # conexao roda no worker dela, e o pump, ao terminar, aposenta esse
        # worker sozinho. Recolher os executores antes deixaria o corpo
        # `on-close` do app sem ninguem para executa-lo.
        for conn_id in conn_ids:
            self.close(conn_id)

        with self._lock:
            if self._loop and self._loop.is_running():
                self._loop.call_soon_threadsafe(self._loop.stop)
            self._loop = None
            self._thread = None
            restantes = list(self._dispatchers.values())
            self._dispatchers.clear()

        # E os workers de handler tambem morrem. Ficavam vivos para sempre:
        # cada reset_transport() em teste deixava mais uma thread
        # 'quantum-ws-handler' parada no processo, e um app que fechasse suas
        # conexoes nunca recuperava a thread.
        for pool in restantes:
            pool.shutdown(wait=False)

    # -- connecting --------------------------------------------------------

    def connect(
        self,
        conn_id: str,
        url: str,
        on_open: Callable[[], None],
        on_message: Callable[[Any], None],
        on_close: Callable[[], None],
        on_error: Callable[[Exception], None],
        timeout: float = 10.0,
    ):
        """Open a real connection. Returns (ok, error).

        Blocks up to `timeout` so q:websocket can report a truthful state
        instead of leaving the caller with a record that says CONNECTING
        forever — and returns the failure reason with the answer, because
        the on_error callback lands on the handler thread later and the
        caller needs it now.
        """
        if not HAS_WEBSOCKETS:
            logger.warning(
                "q:websocket needs the 'websockets' package to open a real "
                "connection (pip install websockets). Leaving %s unconnected.",
                url
            )
            return False, "the 'websockets' package is not installed"

        loop = self._ensure_loop()
        opened = threading.Event()
        result = {'ok': False, 'error': None}

        async def pump():
            try:
                async with _ws.connect(url, open_timeout=timeout) as sock:
                    with self._lock:
                        self._sockets[conn_id] = sock
                    result['ok'] = True
                    opened.set()
                    self._fire(conn_id, on_open)
                    async for raw in sock:
                        # JSON when it parses, raw text otherwise — the same
                        # rule the send side uses.
                        try:
                            payload = json.loads(raw)
                        except (ValueError, TypeError):
                            payload = raw
                        self._fire(conn_id, on_message, payload)
            except Exception as exc:
                result['error'] = exc
                opened.set()
                self._fire(conn_id, on_error, exc)
            finally:
                with self._lock:
                    self._sockets.pop(conn_id, None)
                self._fire(conn_id, on_close)
                # O worker desta conexao acaba com ela. shutdown(wait=False)
                # nao cancela o que ja foi submetido, entao o on_close acima
                # ainda roda; so nao fica uma thread parada por conexao ja
                # encerrada.
                with self._lock:
                    pool = self._dispatchers.pop(conn_id, None)
                if pool is not None:
                    pool.shutdown(wait=False)

        asyncio.run_coroutine_threadsafe(pump(), loop)
        if not opened.wait(timeout=timeout + 1):
            logger.warning("q:websocket: connecting to %s timed out", url)
            return False, f"connection to {url} timed out"

        if result['error'] is not None:
            logger.warning("q:websocket could not connect to %s: %s",
                           url, result['error'])
            return False, str(result['error']) or type(result['error']).__name__
        return bool(result['ok']), None

    # -- sending -----------------------------------------------------------

    def send(self, conn_id: str, data: Any, timeout: float = 5.0) -> bool:
        """Actually transmit. Returns True only when the frame was written."""
        with self._lock:
            sock = self._sockets.get(conn_id)
        if sock is None or self._loop is None:
            return False

        payload = data if isinstance(data, (str, bytes)) else json.dumps(
            data, default=str)
        fut = asyncio.run_coroutine_threadsafe(sock.send(payload), self._loop)
        try:
            fut.result(timeout=timeout)
            return True
        except Exception as exc:
            logger.warning("q:websocket send failed on %s: %s", conn_id, exc)
            return False

    # -- closing -----------------------------------------------------------

    def close(self, conn_id: str, timeout: float = 5.0) -> bool:
        with self._lock:
            sock = self._sockets.get(conn_id)
        if sock is None or self._loop is None:
            return False
        fut = asyncio.run_coroutine_threadsafe(sock.close(), self._loop)
        try:
            fut.result(timeout=timeout)
        except Exception:
            pass
        with self._lock:
            self._sockets.pop(conn_id, None)
        return True

    def is_open(self, conn_id: str) -> bool:
        with self._lock:
            return conn_id in self._sockets


_transport: Optional[WebSocketTransport] = None
_transport_lock = threading.Lock()


def get_transport() -> WebSocketTransport:
    """The process-wide transport (one event loop for every connection)."""
    global _transport
    with _transport_lock:
        if _transport is None:
            _transport = WebSocketTransport()
        return _transport


def reset_transport() -> None:
    """Drop the transport, closing whatever it holds (tests)."""
    global _transport
    with _transport_lock:
        if _transport is not None:
            _transport.shutdown()
        _transport = None
