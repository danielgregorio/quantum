"""
q:websocket used to return a connection-shaped result for a connection that
did not exist: a record in state CONNECTING that nothing ever moved to OPEN,
and a send_message that queued into a list nothing drained.

The transport is real now (tests/integration/test_websocket_transport.py runs
it against a live server). What must stay true is the honesty: a connection
that was NOT opened may not look open, and nothing may report delivery for a
socket that does not exist.
"""

import pytest

from quantum.runtime.websocket_service import WebSocketService, WebSocketState


@pytest.fixture
def svc():
    return WebSocketService()


class TestRegisteringIsNotConnecting:
    def test_it_is_not_reported_connected(self, svc):
        conn = svc.register_connection(name="ws", url="ws://x/y")
        assert conn.to_dict()["connected"] is False

    def test_it_says_no_socket_was_opened(self, svc):
        d = svc.register_connection(name="ws", url="ws://x/y").to_dict()
        assert d["transport"] == "none"
        assert "no socket" in d["note"]

    def test_state_after_register(self, svc):
        conn = svc.register_connection(name="ws", url="ws://x/y")
        assert conn.state == WebSocketState.CONNECTING
        assert conn.state != WebSocketState.OPEN


class TestSendDoesNotClaimDelivery:
    def test_send_returns_false(self, svc):
        svc.register_connection(name="ws", url="ws://x/y")
        assert svc.send_message("ws", "ola") is False

    def test_send_to_an_unknown_name_returns_false(self, svc):
        assert svc.send_message("naoexiste", "ola") is False

    def test_opening_a_connection_that_does_not_exist_returns_false(self, svc):
        assert svc.open("naoexiste") is False


class TestFailureIsNotLeftPending:
    def test_a_failed_open_lands_on_closed_with_a_reason(self, svc):
        # Nothing listens on port 1. Whether the transport is installed or
        # not, "connecting" forever is the one answer that must not happen:
        # it reads as in-progress to every template that checks readyState.
        svc.register_connection(name="ws", url="ws://127.0.0.1:1/")
        assert svc.open("ws", timeout=3) is False

        conn = svc.get_connection("ws")
        assert conn.state == WebSocketState.CLOSED
        assert conn.error, "a failure must carry its reason"

    def test_the_close_handler_runs_once_per_failure(self, svc):
        # The failure path settles the state from the caller, from on_error
        # and from on_close. The app's on-close body must still run once.
        calls = []
        svc.register_handler("ws", "close", lambda d: calls.append(d))
        svc.register_connection(name="ws", url="ws://127.0.0.1:1/")
        svc.open("ws", timeout=3)

        assert len(calls) == 1, f"on-close ran {len(calls)}x for one failure"
