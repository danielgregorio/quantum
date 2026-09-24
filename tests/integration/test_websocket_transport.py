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
        svc.send_message("chat", "one")
        svc.send_message("chat", "two")
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
    """`broadcast` sent N frames to each of the N connections.

    The `broadcast` loop called `send_message(conn.name, ...)`, and
    send_message already goes through ALL the connections with that name.
    With N connections called "chat", N*N frames went out — each client saw
    the same message N times — and the return value said N, the number of
    connections, not of frames. In a room of 50 people: 2500 frames and 50
    copies per person.
    """

    def test_three_connections_get_one_copy_each(self, svc, server):
        for _ in range(3):
            svc.register_connection(
                name="chat", url=server.url, metadata={"auto_connect": True})

        assert len(svc.get_connections_by_name("chat")) == 3

        sent = svc.broadcast("chat", "hi", msg_type="text")

        assert sent == 3
        # Three frames at the server, not nine.
        assert wait_for(lambda: len(server.received) >= 3)
        time.sleep(0.3)                      # let any extra arrive
        assert server.received == ["hi", "hi", "hi"], server.received

    def test_each_connection_s_outgoing_queue_has_one_message(self, svc, server):
        for _ in range(3):
            svc.register_connection(
                name="chat", url=server.url, metadata={"auto_connect": True})

        svc.broadcast("chat", "x", msg_type="text")

        for conn in svc.get_connections_by_name("chat"):
            pending = svc.get_pending_messages(conn.id)
            assert len(pending) == 1, (conn.id, len(pending))


class TestASlowHandlerDoesNotBlockOtherConnections:
    """A single worker for the whole transport serialized everything.

    The executor was `max_workers=1` for ALL connections, to keep the order of
    messages. Order only matters within a connection; the effect was that a
    slow on-message of one connection held up the queue of all the others.
    """

    def test_connection_b_is_delivered_while_a_is_busy(self, svc, server):
        holding = threading.Event()
        release = threading.Event()
        b_arrived = threading.Event()

        def slow_handler(_d):
            holding.set()
            release.wait(timeout=10)

        svc.register_handler("slow", "message", slow_handler)
        svc.register_handler("fast", "message", lambda d: b_arrived.set())

        svc.register_connection(name="slow", url=server.url,
                                metadata={"auto_connect": True})
        svc.register_connection(name="fast", url=server.url,
                                metadata={"auto_connect": True})

        svc.send_message("slow", "block")
        assert holding.wait(timeout=5), "the slow handler never started"

        # With the "slow" connection stuck in its handler, the "fast" one must
        # still be delivered.
        start = time.time()
        svc.send_message("fast", "through")
        # send_message itself had to return at once: it asked for the same
        # lock the slow handler held, so the CALLING THREAD got stuck too —
        # not only the delivery.
        spent_in_send = time.time() - start
        delivered = b_arrived.wait(timeout=5)
        elapsed = time.time() - start
        release.set()

        assert spent_in_send < 3.0, (
            f"send_message was stuck {spent_in_send:.1f}s behind the handler")
        assert delivered, "the fast connection was stuck behind the slow one"
        assert elapsed < 3.0, f"delivery took {elapsed:.1f}s"


class TestShutdown:
    def test_it_does_not_spend_the_whole_timeout_per_connection(self, svc, server):
        """shutdown() held self._lock while closing.

        close() waits for `sock.close()` to finish on the event loop thread, and
        that connection's pump(), when it ends, needs the SAME lock in its
        finally. With the lock held, the loop stopped, close never completed and
        each connection spent the whole 5s timeout. Three connections = 15s.
        """
        from quantum.runtime.websocket_transport import get_transport

        for _ in range(3):
            svc.register_connection(
                name="chat", url=server.url, metadata={"auto_connect": True})

        start = time.time()
        get_transport().shutdown()
        elapsed = time.time() - start

        # A wide margin on purpose: the defect cost >=15s, the fix costs
        # hundredths. Any number in between separates the two worlds.
        assert elapsed < 4.0, f"shutdown took {elapsed:.1f}s"

    def test_it_ends_the_handler_threads(self, svc, server):
        """The dispatch threads stayed alive after shutdown."""
        from quantum.runtime.websocket_transport import get_transport

        svc.register_connection(name="chat", url=server.url,
                                metadata={"auto_connect": True})
        svc.send_message("chat", "hi")
        assert wait_for(
            lambda: any(t.name.startswith('quantum-ws-')
                        for t in threading.enumerate()))

        get_transport().shutdown()

        assert wait_for(
            lambda: not any(t.name.startswith('quantum-ws-')
                            for t in threading.enumerate()),
            timeout=5), [t.name for t in threading.enumerate()]

    def test_the_app_s_on_close_runs_on_shutdown(self, svc, server):
        """Ending the transport must not swallow the app's `on-close`.

        Retiring the workers BEFORE closing the connections would leave the
        close handler with nobody to run it — and shutdown is exactly when the
        app wants to know the connection dropped.
        """
        from quantum.runtime.websocket_transport import get_transport

        closed = []
        svc.register_handler("chat", "close", lambda d: closed.append(d))
        svc.register_connection(name="chat", url=server.url,
                                metadata={"auto_connect": True})

        get_transport().shutdown()

        assert wait_for(lambda: closed), "on-close never ran"

    def test_it_can_reconnect_after_a_shutdown(self, svc, server):
        """The transport is a process singleton: closing everything must not
        retire it."""
        from quantum.runtime.websocket_transport import get_transport

        svc.register_connection(name="chat", url=server.url,
                                metadata={"auto_connect": True})
        get_transport().shutdown()

        received = []
        svc2 = WebSocketService()
        svc2.register_handler("chat2", "message", lambda d: received.append(d))
        conn = svc2.register_connection(name="chat2", url=server.url,
                                        metadata={"auto_connect": True})
        assert conn.state == WebSocketState.OPEN
        svc2.send_message("chat2", "again")
        assert wait_for(lambda: received), "the handler did not work again"
