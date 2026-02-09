"""
WebSocket AST Nodes

Defines the AST structure for WebSocket connections and messaging.

Classes:
    WebSocketHandlerNode - Event handler (on-connect, on-message, etc.)
    WebSocketSendNode - Send message action
    WebSocketNode - Main WebSocket connection definition
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any

# Import base class
try:
    from core.ast_nodes import QuantumNode
except ImportError:
    from ...ast_nodes import QuantumNode


@dataclass
class WebSocketHandlerNode(QuantumNode):
    """
    Event handler for WebSocket events.

    Attributes:
        event: Event type (connect, message, error, close, open)
        body: List of AST nodes to execute when event fires

    Example:
        <q:on-message>
            <q:set name="lastMessage" value="{data}" />
            <q:set name="messages" operation="append" value="{data}" />
        </q:on-message>
    """
    event: str = ""  # connect, message, error, close, open
    body: List[QuantumNode] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "event": self.event,
            "body": [b.to_dict() if hasattr(b, 'to_dict') else str(b) for b in self.body]
        }

    def validate(self) -> List[str]:
        """Validate the handler node."""
        errors = []
        valid_events = {"connect", "open", "message", "error", "close", "disconnect"}
        if self.event not in valid_events:
            errors.append(f"Invalid WebSocket event '{self.event}'. Valid: {valid_events}")
        return errors


@dataclass
class WebSocketSendNode(QuantumNode):
    """
    Send a message through a WebSocket connection.

    Attributes:
        connection: Name of the WebSocket connection to use
        message: Message content to send (supports databinding)
        type: Message type (text, json, binary)

    Example:
        <q:websocket-send connection="chat" message="{userInput}" type="json" />
    """
    connection: str = ""
    message: str = ""
    type: str = "text"  # text, json, binary

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "connection": self.connection,
            "message": self.message,
            "type": self.type
        }

    def validate(self) -> List[str]:
        """Validate the send node."""
        errors = []
        if not self.connection:
            errors.append("WebSocketSendNode requires 'connection' attribute")
        if not self.message:
            errors.append("WebSocketSendNode requires 'message' attribute")
        valid_types = {"text", "json", "binary"}
        if self.type not in valid_types:
            errors.append(f"Invalid message type '{self.type}'. Valid: {valid_types}")
        return errors


@dataclass
class WebSocketCloseNode(QuantumNode):
    """
    Close a WebSocket connection.

    Attributes:
        connection: Name of the WebSocket connection to close
        code: Close code (optional, default 1000 = normal closure)
        reason: Close reason message (optional)

    Example:
        <q:websocket-close connection="chat" code="1000" reason="User logged out" />
    """
    connection: str = ""
    code: int = 1000
    reason: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "connection": self.connection,
            "code": self.code,
            "reason": self.reason
        }

    def validate(self) -> List[str]:
        """Validate the close node."""
        errors = []
        if not self.connection:
            errors.append("WebSocketCloseNode requires 'connection' attribute")
        return errors


@dataclass
class WebSocketNode(QuantumNode):
    """
    WebSocket connection definition.

    Creates a persistent WebSocket connection with event handlers
    for real-time bidirectional communication.

    Attributes:
        name: Variable name for the connection (required)
        url: WebSocket URL (ws:// or wss://)
        auto_connect: Connect automatically on component mount (default: true)
        reconnect: Auto-reconnect on disconnect (default: true)
        reconnect_delay: Initial delay between reconnects in ms (default: 1000)
        max_reconnects: Maximum reconnection attempts (default: 10)
        heartbeat: Heartbeat interval in ms, 0 to disable (default: 30000)
        protocols: WebSocket sub-protocols (optional, comma-separated)
        handlers: Event handlers (on-connect, on-message, etc.)

    Result Object:
        {name}: Connection status object with:
            - connected: bool
            - url: str
            - readyState: int (0=CONNECTING, 1=OPEN, 2=CLOSING, 3=CLOSED)
            - lastMessage: any
            - error: str or None
            - messageCount: int
            - connectedAt: datetime or None

    Example:
        <q:websocket name="chat" url="wss://api.example.com/chat"
                     auto_connect="true" reconnect="true">

            <q:on-connect>
                <q:log level="info">Connected to chat server</q:log>
                <q:set name="chatStatus" value="online" />
            </q:on-connect>

            <q:on-message>
                <q:set name="messages" operation="append" value="{data}" />
            </q:on-message>

            <q:on-error>
                <q:log level="error">WebSocket error: {error}</q:log>
            </q:on-error>

            <q:on-close>
                <q:set name="chatStatus" value="offline" />
            </q:on-close>

        </q:websocket>

        <!-- Send message -->
        <q:action name="sendMessage">
            <q:websocket-send connection="chat" message="{messageInput}" type="json" />
            <q:set name="messageInput" value="" />
        </q:action>
    """
    name: str = ""
    url: str = ""
    auto_connect: bool = True
    reconnect: bool = True
    reconnect_delay: int = 1000  # ms
    max_reconnects: int = 10
    heartbeat: int = 30000  # ms, 0 to disable
    protocols: str = ""  # comma-separated sub-protocols

    # Event handlers
    handlers: List[WebSocketHandlerNode] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "url": self.url,
            "auto_connect": self.auto_connect,
            "reconnect": self.reconnect,
            "reconnect_delay": self.reconnect_delay,
            "max_reconnects": self.max_reconnects,
            "heartbeat": self.heartbeat,
            "protocols": self.protocols,
            "handlers": [h.to_dict() for h in self.handlers]
        }

    def validate(self) -> List[str]:
        """Validate the WebSocket node."""
        errors = []

        if not self.name:
            errors.append("WebSocketNode requires 'name' attribute")

        if not self.url:
            errors.append("WebSocketNode requires 'url' attribute")
        elif not self.url.startswith(("{", "ws://", "wss://")):
            errors.append(f"WebSocket URL must start with ws:// or wss://, got: {self.url}")

        if self.reconnect_delay < 0:
            errors.append("reconnect_delay must be non-negative")

        if self.max_reconnects < 0:
            errors.append("max_reconnects must be non-negative")

        if self.heartbeat < 0:
            errors.append("heartbeat must be non-negative")

        # Validate handlers
        for handler in self.handlers:
            errors.extend(handler.validate())

        return errors

    def get_handler(self, event: str) -> Optional[WebSocketHandlerNode]:
        """Get handler for specific event."""
        for handler in self.handlers:
            if handler.event == event:
                return handler
        return None

    def has_handler(self, event: str) -> bool:
        """Check if handler exists for event."""
        return self.get_handler(event) is not None
