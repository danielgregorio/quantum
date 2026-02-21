"""
Tests for WebSocketExecutor - q:websocket WebSocket connections

Coverage target: 34% -> 60%
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from runtime.executors.messaging.websocket_executor import (
    WebSocketExecutor, WebSocketSendExecutor, WebSocketCloseExecutor
)
from runtime.executors.base import ExecutorError

# Import WebSocket nodes from the correct location
try:
    from core.features.websocket.src.ast_node import (
        WebSocketNode, WebSocketSendNode, WebSocketCloseNode
    )
except ImportError:
    from core.features.websocket.src import (
        WebSocketNode, WebSocketSendNode, WebSocketCloseNode
    )

# Import fixtures from conftest.py
from tests.unit.executors.conftest import MockRuntime, MockExecutionContext


# =============================================================================
# Mock Objects for WebSocket Service
# =============================================================================

class MockWebSocketService:
    """Mock WebSocket service"""

    def __init__(self):
        self.last_config = None
        self.last_send = None
        self.last_close = None
        self._connections = {}

    def create_connection(self, name: str, url: str, auto_connect: bool = True,
                          reconnect: bool = False, reconnect_delay: int = 5000,
                          max_reconnects: int = 5, heartbeat: int = 0,
                          protocols: List[str] = None, handlers: Dict = None) -> Dict:
        """Mock connection creation"""
        self.last_config = {
            'name': name,
            'url': url,
            'auto_connect': auto_connect,
            'reconnect': reconnect,
            'reconnect_delay': reconnect_delay,
            'max_reconnects': max_reconnects,
            'heartbeat': heartbeat,
            'protocols': protocols or [],
            'handlers': handlers or {}
        }

        connection = {
            'name': name,
            'url': url,
            'connected': True,
            'status': 'connected'
        }
        self._connections[name] = connection
        return connection

    def send(self, connection: str, message: str, message_type: str = 'text') -> Dict:
        """Mock message send"""
        self.last_send = {
            'connection': connection,
            'message': message,
            'type': message_type
        }
        return {'success': True, 'sent': True}

    def close(self, connection: str, code: int = 1000, reason: str = '') -> Dict:
        """Mock connection close"""
        self.last_close = {
            'connection': connection,
            'code': code,
            'reason': reason
        }
        return {'success': True, 'closed': True}


class MockWebSocketRuntime(MockRuntime):
    """Extended mock runtime with WebSocket service"""

    def __init__(self, variables: Dict[str, Any] = None):
        super().__init__(variables)
        self._websocket_service = MockWebSocketService()
        self._services = MagicMock()
        self._services.websocket = self._websocket_service

    @property
    def services(self):
        return self._services


# =============================================================================
# Mock Handler Node
# =============================================================================

@dataclass
class MockHandlerNode:
    """Mock handler node for WebSocket events"""
    event: str
    body: Any = None


# =============================================================================
# Test Classes - WebSocketExecutor
# =============================================================================

class TestWebSocketExecutorBasic:
    """Basic functionality tests"""

    def test_handles_websocket_node(self):
        """Test that WebSocketExecutor handles WebSocketNode"""
        runtime = MockWebSocketRuntime()
        executor = WebSocketExecutor(runtime)
        assert WebSocketNode in executor.handles

    def test_handles_returns_list(self):
        """Test that handles returns a list"""
        runtime = MockWebSocketRuntime()
        executor = WebSocketExecutor(runtime)
        assert isinstance(executor.handles, list)
        assert len(executor.handles) == 1


class TestWebSocketConnection:
    """Test WebSocket connection creation"""

    def test_create_connection_basic(self):
        """Test basic connection creation"""
        runtime = MockWebSocketRuntime()
        executor = WebSocketExecutor(runtime)

        node = WebSocketNode()
        node.name = "mySocket"
        node.url = "ws://localhost:8080/ws"
        node.handlers = []

        executor.execute(node, runtime.execution_context)

        config = runtime._websocket_service.last_config
        assert config["name"] == "mySocket"
        assert config["url"] == "ws://localhost:8080/ws"

    def test_connection_with_databinding(self):
        """Test connection URL with databinding"""
        runtime = MockWebSocketRuntime({"host": "example.com", "port": 9090})
        executor = WebSocketExecutor(runtime)

        node = WebSocketNode()
        node.name = "socket"
        node.url = "ws://{host}:{port}/ws"
        node.handlers = []

        executor.execute(node, runtime.execution_context)

        config = runtime._websocket_service.last_config
        assert config["url"] == "ws://example.com:9090/ws"

    def test_auto_connect_enabled(self):
        """Test auto-connect option"""
        runtime = MockWebSocketRuntime()
        executor = WebSocketExecutor(runtime)

        node = WebSocketNode()
        node.name = "socket"
        node.url = "ws://localhost/ws"
        node.auto_connect = True
        node.handlers = []

        executor.execute(node, runtime.execution_context)

        assert runtime._websocket_service.last_config["auto_connect"] is True

    def test_reconnect_configuration(self):
        """Test reconnection settings"""
        runtime = MockWebSocketRuntime()
        executor = WebSocketExecutor(runtime)

        node = WebSocketNode()
        node.name = "socket"
        node.url = "ws://localhost/ws"
        node.reconnect = True
        node.reconnect_delay = 3000
        node.max_reconnects = 10
        node.handlers = []

        executor.execute(node, runtime.execution_context)

        config = runtime._websocket_service.last_config
        assert config["reconnect"] is True
        assert config["reconnect_delay"] == 3000
        assert config["max_reconnects"] == 10

    def test_heartbeat_configuration(self):
        """Test heartbeat setting"""
        runtime = MockWebSocketRuntime()
        executor = WebSocketExecutor(runtime)

        node = WebSocketNode()
        node.name = "socket"
        node.url = "ws://localhost/ws"
        node.heartbeat = 30000
        node.handlers = []

        executor.execute(node, runtime.execution_context)

        assert runtime._websocket_service.last_config["heartbeat"] == 30000

    def test_protocols_configuration(self):
        """Test WebSocket protocols"""
        runtime = MockWebSocketRuntime()
        executor = WebSocketExecutor(runtime)

        node = WebSocketNode()
        node.name = "socket"
        node.url = "ws://localhost/ws"
        node.protocols = "graphql-ws,subscriptions-transport-ws"
        node.handlers = []

        executor.execute(node, runtime.execution_context)

        protocols = runtime._websocket_service.last_config["protocols"]
        assert "graphql-ws" in protocols
        assert "subscriptions-transport-ws" in protocols


class TestWebSocketHandlers:
    """Test WebSocket event handlers"""

    def test_handlers_passed(self):
        """Test that handlers are passed to service"""
        runtime = MockWebSocketRuntime()
        executor = WebSocketExecutor(runtime)

        node = WebSocketNode()
        node.name = "socket"
        node.url = "ws://localhost/ws"
        node.handlers = [
            MockHandlerNode("connect", body=[]),
            MockHandlerNode("message", body=[]),
            MockHandlerNode("error", body=[])
        ]

        executor.execute(node, runtime.execution_context)

        handlers = runtime._websocket_service.last_config["handlers"]
        assert "connect" in handlers
        assert "message" in handlers
        assert "error" in handlers


class TestWebSocketResultStorage:
    """Test result storage"""

    def test_stores_connection_reference(self):
        """Test that connection reference is stored"""
        runtime = MockWebSocketRuntime()
        executor = WebSocketExecutor(runtime)

        node = WebSocketNode()
        node.name = "myConn"
        node.url = "ws://localhost/ws"
        node.handlers = []

        executor.execute(node, runtime.execution_context)

        stored = runtime.execution_context.get_variable("myConn")
        assert stored["connected"] is True
        assert stored["url"] == "ws://localhost/ws"


class TestWebSocketErrorHandling:
    """Test error handling"""

    def test_error_stores_failure(self):
        """Test that error stores failure info"""
        runtime = MockWebSocketRuntime()
        runtime._websocket_service.create_connection = MagicMock(
            side_effect=Exception("Connection refused")
        )
        executor = WebSocketExecutor(runtime)

        node = WebSocketNode()
        node.name = "socket"
        node.url = "ws://localhost/ws"
        node.handlers = []

        with pytest.raises(ExecutorError, match="WebSocket creation error"):
            executor.execute(node, runtime.execution_context)

        error_info = runtime.execution_context.get_variable("socket")
        assert error_info["connected"] is False
        assert "Connection refused" in error_info["error"]


# =============================================================================
# Test Classes - WebSocketSendExecutor
# =============================================================================

class TestWebSocketSendExecutorBasic:
    """Basic functionality tests"""

    def test_handles_send_node(self):
        """Test that WebSocketSendExecutor handles WebSocketSendNode"""
        runtime = MockWebSocketRuntime()
        executor = WebSocketSendExecutor(runtime)
        assert WebSocketSendNode in executor.handles


class TestWebSocketSend:
    """Test WebSocket message sending"""

    def test_send_text_message(self):
        """Test sending text message"""
        runtime = MockWebSocketRuntime()
        executor = WebSocketSendExecutor(runtime)

        node = WebSocketSendNode()
        node.connection = "mySocket"
        node.message = "Hello, WebSocket!"
        node.type = "text"

        executor.execute(node, runtime.execution_context)

        send = runtime._websocket_service.last_send
        assert send["connection"] == "mySocket"
        assert send["message"] == "Hello, WebSocket!"
        assert send["type"] == "text"

    def test_send_with_databinding(self):
        """Test sending message with databinding"""
        runtime = MockWebSocketRuntime({"userName": "Alice"})
        executor = WebSocketSendExecutor(runtime)

        node = WebSocketSendNode()
        node.connection = "socket"
        node.message = "Hello, {userName}!"
        node.type = "text"

        executor.execute(node, runtime.execution_context)

        assert runtime._websocket_service.last_send["message"] == "Hello, Alice!"

    def test_send_binary_type(self):
        """Test sending binary message"""
        runtime = MockWebSocketRuntime()
        executor = WebSocketSendExecutor(runtime)

        node = WebSocketSendNode()
        node.connection = "socket"
        node.message = "binary data"
        node.type = "binary"

        executor.execute(node, runtime.execution_context)

        assert runtime._websocket_service.last_send["type"] == "binary"


class TestWebSocketSendError:
    """Test send error handling"""

    def test_send_error_wrapped(self):
        """Test that send error is wrapped"""
        runtime = MockWebSocketRuntime()
        runtime._websocket_service.send = MagicMock(
            side_effect=Exception("Connection closed")
        )
        executor = WebSocketSendExecutor(runtime)

        node = WebSocketSendNode()
        node.connection = "socket"
        node.message = "test"
        node.type = "text"

        with pytest.raises(ExecutorError, match="WebSocket send error"):
            executor.execute(node, runtime.execution_context)


# =============================================================================
# Test Classes - WebSocketCloseExecutor
# =============================================================================

class TestWebSocketCloseExecutorBasic:
    """Basic functionality tests"""

    def test_handles_close_node(self):
        """Test that WebSocketCloseExecutor handles WebSocketCloseNode"""
        runtime = MockWebSocketRuntime()
        executor = WebSocketCloseExecutor(runtime)
        assert WebSocketCloseNode in executor.handles


class TestWebSocketClose:
    """Test WebSocket connection close"""

    def test_close_connection_basic(self):
        """Test basic connection close"""
        runtime = MockWebSocketRuntime()
        executor = WebSocketCloseExecutor(runtime)

        node = WebSocketCloseNode()
        node.connection = "mySocket"
        node.code = 1000
        node.reason = None

        executor.execute(node, runtime.execution_context)

        close = runtime._websocket_service.last_close
        assert close["connection"] == "mySocket"
        assert close["code"] == 1000

    def test_close_with_reason(self):
        """Test close with reason"""
        runtime = MockWebSocketRuntime()
        executor = WebSocketCloseExecutor(runtime)

        node = WebSocketCloseNode()
        node.connection = "socket"
        node.code = 1001
        node.reason = "Going away"

        executor.execute(node, runtime.execution_context)

        close = runtime._websocket_service.last_close
        assert close["reason"] == "Going away"

    def test_close_with_reason_databinding(self):
        """Test close with reason databinding"""
        runtime = MockWebSocketRuntime({"closeReason": "Session ended"})
        executor = WebSocketCloseExecutor(runtime)

        node = WebSocketCloseNode()
        node.connection = "socket"
        node.code = 1000
        node.reason = "{closeReason}"

        executor.execute(node, runtime.execution_context)

        assert runtime._websocket_service.last_close["reason"] == "Session ended"


class TestWebSocketCloseError:
    """Test close error handling"""

    def test_close_error_wrapped(self):
        """Test that close error is wrapped"""
        runtime = MockWebSocketRuntime()
        runtime._websocket_service.close = MagicMock(
            side_effect=Exception("Already closed")
        )
        executor = WebSocketCloseExecutor(runtime)

        node = WebSocketCloseNode()
        node.connection = "socket"
        node.code = 1000
        node.reason = None

        with pytest.raises(ExecutorError, match="WebSocket close error"):
            executor.execute(node, runtime.execution_context)

