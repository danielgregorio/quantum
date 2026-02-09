"""
Tests for WebSocket Feature

Tests the WebSocket implementation:
- AST node classes
- Parser integration
- WebSocket service
- HTML adapter
"""

import pytest
from unittest.mock import Mock, patch
import json

# Add src to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.features.websocket.src import (
    WebSocketNode, WebSocketHandlerNode, WebSocketSendNode, WebSocketCloseNode
)
from runtime.websocket_service import (
    WebSocketService, WebSocketConnection, WebSocketMessage,
    WebSocketState, get_websocket_service, reset_websocket_service
)
from runtime.websocket_adapter import (
    WebSocketHTMLAdapter, WebSocketClientConfig, get_websocket_html_adapter
)


class TestWebSocketASTNodes:
    """Test WebSocket AST node classes."""

    def test_websocket_node_creation(self):
        """Test basic WebSocketNode creation."""
        ws = WebSocketNode(
            name="chat",
            url="wss://api.example.com/chat",
            auto_connect=True,
            reconnect=True
        )
        assert ws.name == "chat"
        assert ws.url == "wss://api.example.com/chat"
        assert ws.auto_connect is True
        assert ws.reconnect is True
        assert ws.max_reconnects == 10  # default
        assert ws.heartbeat == 30000  # default

    def test_websocket_node_with_handlers(self):
        """Test WebSocketNode with event handlers."""
        on_connect = WebSocketHandlerNode(event="connect", body=[])
        on_message = WebSocketHandlerNode(event="message", body=[])
        on_error = WebSocketHandlerNode(event="error", body=[])
        on_close = WebSocketHandlerNode(event="close", body=[])

        ws = WebSocketNode(
            name="chat",
            url="wss://example.com/ws",
            handlers=[on_connect, on_message, on_error, on_close]
        )

        assert len(ws.handlers) == 4
        assert ws.has_handler("connect")
        assert ws.has_handler("message")
        assert ws.has_handler("error")
        assert ws.has_handler("close")
        assert not ws.has_handler("unknown")

    def test_websocket_node_to_dict(self):
        """Test WebSocketNode serialization."""
        ws = WebSocketNode(
            name="test",
            url="wss://test.com/ws",
            auto_connect=False,
            heartbeat=60000
        )
        d = ws.to_dict()

        assert d["name"] == "test"
        assert d["url"] == "wss://test.com/ws"
        assert d["auto_connect"] is False
        assert d["heartbeat"] == 60000

    def test_websocket_node_validation(self):
        """Test WebSocketNode validation."""
        # Missing name
        ws = WebSocketNode(name="", url="wss://test.com")
        errors = ws.validate()
        assert any("name" in e.lower() for e in errors)

        # Missing URL
        ws = WebSocketNode(name="test", url="")
        errors = ws.validate()
        assert any("url" in e.lower() for e in errors)

        # Invalid URL scheme
        ws = WebSocketNode(name="test", url="http://test.com")
        errors = ws.validate()
        assert any("ws://" in e.lower() for e in errors)

        # Valid URL with databinding
        ws = WebSocketNode(name="test", url="{wsUrl}")
        errors = ws.validate()
        assert not any("url" in e.lower() for e in errors)

    def test_handler_node_validation(self):
        """Test WebSocketHandlerNode validation."""
        # Invalid event
        handler = WebSocketHandlerNode(event="invalid")
        errors = handler.validate()
        assert any("event" in e.lower() for e in errors)

        # Valid event
        handler = WebSocketHandlerNode(event="message")
        errors = handler.validate()
        assert len(errors) == 0

    def test_send_node_creation(self):
        """Test WebSocketSendNode creation."""
        send = WebSocketSendNode(
            connection="chat",
            message='{"type": "hello"}',
            type="json"
        )
        assert send.connection == "chat"
        assert send.message == '{"type": "hello"}'
        assert send.type == "json"

    def test_send_node_validation(self):
        """Test WebSocketSendNode validation."""
        # Missing connection
        send = WebSocketSendNode(connection="", message="hello")
        errors = send.validate()
        assert any("connection" in e.lower() for e in errors)

        # Missing message
        send = WebSocketSendNode(connection="chat", message="")
        errors = send.validate()
        assert any("message" in e.lower() for e in errors)

    def test_close_node_creation(self):
        """Test WebSocketCloseNode creation."""
        close = WebSocketCloseNode(
            connection="chat",
            code=1001,
            reason="Going away"
        )
        assert close.connection == "chat"
        assert close.code == 1001
        assert close.reason == "Going away"


class TestWebSocketService:
    """Test WebSocketService class."""

    @pytest.fixture
    def service(self):
        """Create fresh service instance."""
        reset_websocket_service()
        return WebSocketService()

    def test_register_connection(self, service):
        """Test connection registration."""
        conn = service.register_connection(
            name="chat",
            url="wss://example.com/chat"
        )

        assert conn.name == "chat"
        assert conn.url == "wss://example.com/chat"
        assert conn.state == WebSocketState.CONNECTING
        assert conn.id.startswith("ws_")

    def test_get_connection_by_name(self, service):
        """Test getting connection by name."""
        service.register_connection("chat", "wss://test.com")

        conn = service.get_connection("chat")
        assert conn is not None
        assert conn.name == "chat"

    def test_get_connection_by_id(self, service):
        """Test getting connection by ID."""
        conn = service.register_connection("chat", "wss://test.com")

        found = service.get_connection(conn.id)
        assert found is not None
        assert found.id == conn.id

    def test_connection_state_changes(self, service):
        """Test connection state transitions."""
        conn = service.register_connection("chat", "wss://test.com")

        # Initially connecting
        assert conn.state == WebSocketState.CONNECTING

        # Set to open
        service.set_connection_state(conn.id, WebSocketState.OPEN)
        assert conn.state == WebSocketState.OPEN
        assert conn.connected_at is not None

        # Set to closed
        service.set_connection_state(conn.id, WebSocketState.CLOSED)
        assert conn.state == WebSocketState.CLOSED

    def test_receive_message(self, service):
        """Test message receiving."""
        conn = service.register_connection("chat", "wss://test.com")
        service.set_connection_state(conn.id, WebSocketState.OPEN)

        # Track received messages
        received = []

        def handler(data):
            received.append(data)

        service.register_handler("chat", "message", handler)

        # Receive message
        service.receive_message(conn.id, '{"type": "hello"}', "json")

        assert len(received) == 1
        assert received[0]["data"]["type"] == "hello"
        assert conn.message_count == 1

    def test_send_message(self, service):
        """Test message sending."""
        conn = service.register_connection("chat", "wss://test.com")
        service.set_connection_state(conn.id, WebSocketState.OPEN)

        success = service.send_message("chat", {"text": "Hello!"}, "json")
        assert success is True

        # Get pending messages
        pending = service.get_pending_messages(conn.id)
        assert len(pending) == 1
        assert pending[0].direction == "outgoing"

    def test_send_to_closed_connection(self, service):
        """Test sending to closed connection fails."""
        service.register_connection("chat", "wss://test.com")
        # Connection stays in CONNECTING state

        success = service.send_message("chat", "hello", "text")
        assert success is False

    def test_broadcast(self, service):
        """Test broadcasting to multiple connections."""
        conn1 = service.register_connection("notifications", "wss://test.com/1")
        conn2 = service.register_connection("notifications", "wss://test.com/2")

        service.set_connection_state(conn1.id, WebSocketState.OPEN)
        service.set_connection_state(conn2.id, WebSocketState.OPEN)

        sent = service.broadcast("notifications", {"alert": "Test"})
        assert sent == 2

    def test_close_connection(self, service):
        """Test connection closing."""
        conn = service.register_connection("chat", "wss://test.com")
        service.set_connection_state(conn.id, WebSocketState.OPEN)

        close_events = []
        service.register_handler("chat", "close", lambda d: close_events.append(d))

        service.close_connection("chat", 1000, "Test close")

        assert conn.state == WebSocketState.CLOSING
        assert len(close_events) == 1

    def test_connection_to_dict(self, service):
        """Test connection serialization."""
        conn = service.register_connection("chat", "wss://test.com")
        service.set_connection_state(conn.id, WebSocketState.OPEN)

        d = conn.to_dict()
        assert d["connected"] is True
        assert d["readyState"] == WebSocketState.OPEN
        assert d["name"] == "chat"


class TestWebSocketHTMLAdapter:
    """Test WebSocket HTML adapter for client-side code generation."""

    @pytest.fixture
    def adapter(self):
        """Create adapter instance."""
        return WebSocketHTMLAdapter()

    def test_generate_manager_script(self, adapter):
        """Test manager script generation."""
        script = adapter.generate_manager_script()

        assert "QuantumWebSocket" in script
        assert "__qWebSockets" in script
        assert "__qCreateWebSocket" in script
        assert "__qWebSocketSend" in script

        # Should only generate once
        script2 = adapter.generate_manager_script()
        assert script2 == ""

    def test_generate_connection(self, adapter):
        """Test connection JavaScript generation."""
        ws_node = WebSocketNode(
            name="chat",
            url="wss://example.com/chat",
            auto_connect=True,
            reconnect=True,
            heartbeat=30000
        )

        js = adapter.generate_connection(ws_node, {})

        assert "chat" in js
        assert "wss://example.com/chat" in js
        assert "__qCreateWebSocket" in js
        assert "__qContext" in js

    def test_generate_connection_with_handlers(self, adapter):
        """Test connection with event handlers."""
        ws_node = WebSocketNode(
            name="chat",
            url="wss://test.com",
            handlers=[
                WebSocketHandlerNode(event="connect", body=[]),
                WebSocketHandlerNode(event="message", body=[])
            ]
        )

        js = adapter.generate_connection(ws_node, {})

        assert "ws.on('connect'" in js
        assert "ws.on('message'" in js

    def test_generate_send(self, adapter):
        """Test send JavaScript generation."""
        # Static message
        js = adapter.generate_send("chat", "Hello!", "text")
        assert "__qWebSocketSend" in js
        assert "'chat'" in js
        assert "'Hello!'" in js or '"Hello!"' in js

        # Databinding message
        js = adapter.generate_send("chat", "{userMessage}", "json")
        assert "__qContext['userMessage']" in js

    def test_generate_close(self, adapter):
        """Test close JavaScript generation."""
        js = adapter.generate_close("chat", 1000, "Goodbye")
        assert "__qWebSocketClose" in js
        assert "'chat'" in js
        assert "1000" in js


class TestWebSocketParsing:
    """Test parser integration."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        from core.parser import QuantumParser
        return QuantumParser(use_cache=False)

    def test_parse_simple_websocket(self, parser):
        """Test parsing a simple WebSocket."""
        xml = '''<?xml version="1.0"?>
<q:component name="Test" xmlns:q="urn:quantum">
    <q:websocket name="chat" url="wss://api.example.com/chat"
                 auto_connect="true" reconnect="true">
    </q:websocket>
</q:component>'''

        component = parser.parse(xml)
        assert component is not None

        # Find WebSocket node
        ws_node = None
        for stmt in component.statements:
            if isinstance(stmt, WebSocketNode):
                ws_node = stmt
                break

        assert ws_node is not None
        assert ws_node.name == "chat"
        assert ws_node.url == "wss://api.example.com/chat"
        assert ws_node.auto_connect is True

    def test_parse_websocket_with_handlers(self, parser):
        """Test parsing WebSocket with event handlers."""
        xml = '''<?xml version="1.0"?>
<q:component name="Test" xmlns:q="urn:quantum">
    <q:websocket name="chat" url="wss://test.com/ws">
        <q:on-connect>
            <q:set name="connected" value="true" />
        </q:on-connect>
        <q:on-message>
            <q:set name="lastMessage" value="{data}" />
        </q:on-message>
        <q:on-error>
            <q:log level="error" message="Error occurred" />
        </q:on-error>
        <q:on-close>
            <q:set name="connected" value="false" />
        </q:on-close>
    </q:websocket>
</q:component>'''

        component = parser.parse(xml)
        ws_node = next(s for s in component.statements if isinstance(s, WebSocketNode))

        assert len(ws_node.handlers) == 4

        events = [h.event for h in ws_node.handlers]
        assert "connect" in events
        assert "message" in events
        assert "error" in events
        assert "close" in events

    def test_parse_websocket_send(self, parser):
        """Test parsing websocket-send."""
        xml = '''<?xml version="1.0"?>
<q:component name="Test" xmlns:q="urn:quantum">
    <q:action name="sendMessage">
        <q:websocket-send connection="chat" message="{userInput}" type="json" />
    </q:action>
</q:component>'''

        component = parser.parse(xml)
        # The send node is inside the action
        assert component is not None

    def test_parse_websocket_close(self, parser):
        """Test parsing websocket-close."""
        xml = '''<?xml version="1.0"?>
<q:component name="Test" xmlns:q="urn:quantum">
    <q:action name="disconnect">
        <q:websocket-close connection="chat" code="1000" reason="User logout" />
    </q:action>
</q:component>'''

        component = parser.parse(xml)
        assert component is not None


class TestWebSocketMessage:
    """Test WebSocketMessage dataclass."""

    def test_message_creation(self):
        """Test message creation."""
        msg = WebSocketMessage(
            connection_id="ws_1",
            data={"type": "chat", "text": "Hello"},
            type="json",
            direction="incoming"
        )

        assert msg.connection_id == "ws_1"
        assert msg.data["type"] == "chat"
        assert msg.type == "json"
        assert msg.direction == "incoming"

    def test_message_to_dict(self):
        """Test message serialization."""
        msg = WebSocketMessage(
            connection_id="ws_1",
            data="Hello",
            type="text",
            direction="outgoing"
        )

        d = msg.to_dict()
        assert d["connectionId"] == "ws_1"
        assert d["data"] == "Hello"
        assert d["direction"] == "outgoing"
        assert "timestamp" in d


class TestWebSocketClientConfig:
    """Test WebSocketClientConfig dataclass."""

    def test_config_creation(self):
        """Test config creation."""
        config = WebSocketClientConfig(
            name="chat",
            url="wss://test.com",
            auto_connect=True,
            reconnect=True,
            reconnect_delay=2000,
            max_reconnects=5,
            heartbeat=60000,
            protocols=["v1", "v2"]
        )

        d = config.to_dict()
        assert d["name"] == "chat"
        assert d["url"] == "wss://test.com"
        assert d["autoConnect"] is True
        assert d["reconnect"] is True
        assert d["reconnectDelay"] == 2000
        assert d["maxReconnects"] == 5
        assert d["heartbeat"] == 60000
        assert d["protocols"] == ["v1", "v2"]


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
