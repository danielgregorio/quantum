"""
WebSocket Service - Connection Management and Messaging

Manages WebSocket connections for Quantum components, providing:
- Connection lifecycle management
- Message sending/receiving
- Event dispatching
- Reconnection logic
- Connection state tracking

Server-side counterpart to client WebSocket connections.

Usage:
    from runtime.websocket_service import get_websocket_service

    ws_service = get_websocket_service()

    # Register connection handler
    ws_service.register_handler("chat", on_message=handle_message)

    # Send message to connected clients
    ws_service.broadcast("chat", {"type": "notification", "text": "Hello!"})
"""

import json
import logging
import threading
import time
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum

logger = logging.getLogger(__name__)


class WebSocketState(IntEnum):
    """WebSocket connection states (matches JavaScript WebSocket.readyState)."""
    CONNECTING = 0
    OPEN = 1
    CLOSING = 2
    CLOSED = 3


@dataclass
class WebSocketConnection:
    """Represents a WebSocket connection."""
    id: str
    name: str
    url: str
    state: WebSocketState = WebSocketState.CLOSED
    connected_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    message_count: int = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for template access."""
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "connected": self.state == WebSocketState.OPEN,
            "readyState": int(self.state),
            "connectedAt": self.connected_at.isoformat() if self.connected_at else None,
            "lastMessageAt": self.last_message_at.isoformat() if self.last_message_at else None,
            "messageCount": self.message_count,
            "error": self.error
        }


@dataclass
class WebSocketMessage:
    """Represents a WebSocket message."""
    connection_id: str
    data: Any
    type: str = "text"  # text, json, binary
    timestamp: datetime = field(default_factory=datetime.now)
    direction: str = "incoming"  # incoming, outgoing

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "connectionId": self.connection_id,
            "data": self.data,
            "type": self.type,
            "timestamp": self.timestamp.isoformat(),
            "direction": self.direction
        }


class WebSocketError(Exception):
    """WebSocket-related error."""
    pass


class WebSocketService:
    """
    Manages WebSocket connections and messaging.

    This service handles:
    - Connection registration and lifecycle
    - Message routing to handlers
    - Broadcasting to multiple connections
    - Connection state tracking
    """

    def __init__(self):
        self._connections: Dict[str, WebSocketConnection] = {}
        self._handlers: Dict[str, Dict[str, List[Callable]]] = {}
        self._message_queue: Dict[str, List[WebSocketMessage]] = {}
        self._lock = threading.RLock()
        self._connection_counter = 0

    def _generate_connection_id(self) -> str:
        """Generate unique connection ID."""
        self._connection_counter += 1
        return f"ws_{self._connection_counter}_{int(time.time() * 1000)}"

    def register_connection(
        self,
        name: str,
        url: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> WebSocketConnection:
        """
        Register a new WebSocket connection.

        Args:
            name: Connection name (used for referencing)
            url: WebSocket URL
            metadata: Additional connection metadata

        Returns:
            WebSocketConnection object
        """
        with self._lock:
            conn_id = self._generate_connection_id()
            connection = WebSocketConnection(
                id=conn_id,
                name=name,
                url=url,
                state=WebSocketState.CONNECTING,
                metadata=metadata or {}
            )
            self._connections[conn_id] = connection
            self._message_queue[conn_id] = []

            logger.info(f"Registered WebSocket connection: {name} -> {url}")
            return connection

    def get_connection(self, name_or_id: str) -> Optional[WebSocketConnection]:
        """Get connection by name or ID."""
        with self._lock:
            # Try by ID first
            if name_or_id in self._connections:
                return self._connections[name_or_id]

            # Try by name
            for conn in self._connections.values():
                if conn.name == name_or_id:
                    return conn

            return None

    def get_connections_by_name(self, name: str) -> List[WebSocketConnection]:
        """Get all connections with the given name."""
        with self._lock:
            return [c for c in self._connections.values() if c.name == name]

    def set_connection_state(
        self,
        connection_id: str,
        state: WebSocketState,
        error: Optional[str] = None
    ):
        """Update connection state."""
        with self._lock:
            if connection_id in self._connections:
                conn = self._connections[connection_id]
                old_state = conn.state
                conn.state = state
                conn.error = error

                if state == WebSocketState.OPEN and old_state != WebSocketState.OPEN:
                    conn.connected_at = datetime.now()
                    self._dispatch_event(connection_id, "connect", {})

                elif state in (WebSocketState.CLOSING, WebSocketState.CLOSED):
                    self._dispatch_event(connection_id, "close", {"error": error})

                logger.debug(f"Connection {connection_id} state: {old_state.name} -> {state.name}")

    def remove_connection(self, connection_id: str):
        """Remove a connection."""
        with self._lock:
            if connection_id in self._connections:
                del self._connections[connection_id]
            if connection_id in self._message_queue:
                del self._message_queue[connection_id]
            if connection_id in self._handlers:
                del self._handlers[connection_id]

            logger.info(f"Removed WebSocket connection: {connection_id}")

    def register_handler(
        self,
        connection_name: str,
        event: str,
        handler: Callable[[Dict[str, Any]], None]
    ):
        """
        Register an event handler for a connection.

        Args:
            connection_name: Name of the connection
            event: Event type (connect, message, error, close)
            handler: Callback function
        """
        with self._lock:
            if connection_name not in self._handlers:
                self._handlers[connection_name] = {}
            if event not in self._handlers[connection_name]:
                self._handlers[connection_name][event] = []

            self._handlers[connection_name][event].append(handler)
            logger.debug(f"Registered handler for {connection_name}:{event}")

    def _dispatch_event(
        self,
        connection_id: str,
        event: str,
        data: Dict[str, Any]
    ):
        """Dispatch event to registered handlers."""
        conn = self._connections.get(connection_id)
        if not conn:
            return

        handlers = self._handlers.get(conn.name, {}).get(event, [])
        for handler in handlers:
            try:
                handler(data)
            except Exception as e:
                logger.error(f"Error in WebSocket handler {conn.name}:{event}: {e}")

    def receive_message(
        self,
        connection_id: str,
        data: Any,
        msg_type: str = "text"
    ):
        """
        Process an incoming message.

        Args:
            connection_id: Connection that received the message
            data: Message data
            msg_type: Message type (text, json, binary)
        """
        with self._lock:
            if connection_id not in self._connections:
                logger.warning(f"Message for unknown connection: {connection_id}")
                return

            conn = self._connections[connection_id]
            conn.message_count += 1
            conn.last_message_at = datetime.now()

            # Parse JSON if needed
            parsed_data = data
            if msg_type == "json" and isinstance(data, str):
                try:
                    parsed_data = json.loads(data)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON message: {data[:100]}")

            message = WebSocketMessage(
                connection_id=connection_id,
                data=parsed_data,
                type=msg_type,
                direction="incoming"
            )

            # Store in queue
            self._message_queue[connection_id].append(message)

            # Keep only last 100 messages per connection
            if len(self._message_queue[connection_id]) > 100:
                self._message_queue[connection_id] = self._message_queue[connection_id][-100:]

            # Dispatch to handlers
            self._dispatch_event(connection_id, "message", {
                "data": parsed_data,
                "type": msg_type,
                "raw": data,
                "timestamp": message.timestamp.isoformat()
            })

    def send_message(
        self,
        connection_name: str,
        data: Any,
        msg_type: str = "text"
    ) -> bool:
        """
        Send a message to a connection.

        Args:
            connection_name: Name of the connection
            data: Message data
            msg_type: Message type (text, json)

        Returns:
            True if message was queued/sent
        """
        connections = self.get_connections_by_name(connection_name)
        if not connections:
            logger.warning(f"No connections found for: {connection_name}")
            return False

        success = False
        for conn in connections:
            if conn.state == WebSocketState.OPEN:
                # Serialize if needed
                send_data = data
                if msg_type == "json" and not isinstance(data, str):
                    send_data = json.dumps(data, default=str)

                message = WebSocketMessage(
                    connection_id=conn.id,
                    data=send_data,
                    type=msg_type,
                    direction="outgoing"
                )
                self._message_queue[conn.id].append(message)
                success = True

                logger.debug(f"Message queued for {conn.name}: {str(data)[:100]}")

        return success

    def broadcast(
        self,
        connection_name: str,
        data: Any,
        msg_type: str = "json"
    ) -> int:
        """
        Broadcast message to all connections with the given name.

        Args:
            connection_name: Name of connections to broadcast to
            data: Message data
            msg_type: Message type

        Returns:
            Number of connections messaged
        """
        connections = self.get_connections_by_name(connection_name)
        sent = 0

        for conn in connections:
            if conn.state == WebSocketState.OPEN:
                if self.send_message(conn.name, data, msg_type):
                    sent += 1

        return sent

    def get_pending_messages(self, connection_id: str) -> List[WebSocketMessage]:
        """Get pending outgoing messages for a connection."""
        with self._lock:
            messages = [
                m for m in self._message_queue.get(connection_id, [])
                if m.direction == "outgoing"
            ]
            # Clear sent messages
            self._message_queue[connection_id] = [
                m for m in self._message_queue.get(connection_id, [])
                if m.direction == "incoming"
            ]
            return messages

    def get_connection_status(self, name: str) -> Dict[str, Any]:
        """Get status object for a connection."""
        conn = self.get_connection(name)
        if conn:
            return conn.to_dict()
        return {
            "connected": False,
            "readyState": WebSocketState.CLOSED,
            "error": "Connection not found"
        }

    def get_all_connections(self) -> List[Dict[str, Any]]:
        """Get all connections as dictionaries."""
        with self._lock:
            return [c.to_dict() for c in self._connections.values()]

    def close_connection(
        self,
        connection_name: str,
        code: int = 1000,
        reason: str = ""
    ):
        """Request connection close."""
        connections = self.get_connections_by_name(connection_name)
        for conn in connections:
            self.set_connection_state(
                conn.id,
                WebSocketState.CLOSING,
                reason or f"Close requested (code: {code})"
            )


# Global singleton
_websocket_service: Optional[WebSocketService] = None


def get_websocket_service() -> WebSocketService:
    """Get the global WebSocket service instance."""
    global _websocket_service
    if _websocket_service is None:
        _websocket_service = WebSocketService()
    return _websocket_service


def reset_websocket_service():
    """Reset the global WebSocket service (for testing)."""
    global _websocket_service
    _websocket_service = None
