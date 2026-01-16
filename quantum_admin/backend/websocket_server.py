"""
Quantum Admin - WebSocket Server
Real-time event broadcasting and bidirectional communication
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Set, Optional, Any, List
from enum import Enum

from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel


# ============================================================================
# Event Types
# ============================================================================

class EventType(str, Enum):
    """WebSocket event types"""
    # Connection events
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"

    # Data events
    DATASOURCE_CREATED = "datasource.created"
    DATASOURCE_UPDATED = "datasource.updated"
    DATASOURCE_DELETED = "datasource.deleted"
    DATASOURCE_STATUS = "datasource.status"

    # Container events
    CONTAINER_CREATED = "container.created"
    CONTAINER_STARTED = "container.started"
    CONTAINER_STOPPED = "container.stopped"
    CONTAINER_DELETED = "container.deleted"
    CONTAINER_STATUS = "container.status"
    CONTAINER_LOGS = "container.logs"

    # Task events
    TASK_QUEUED = "task.queued"
    TASK_STARTED = "task.started"
    TASK_PROGRESS = "task.progress"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"

    # Deployment events
    DEPLOYMENT_STARTED = "deployment.started"
    DEPLOYMENT_PROGRESS = "deployment.progress"
    DEPLOYMENT_COMPLETED = "deployment.completed"
    DEPLOYMENT_FAILED = "deployment.failed"

    # System events
    SYSTEM_ALERT = "system.alert"
    SYSTEM_NOTIFICATION = "system.notification"
    CACHE_CLEARED = "cache.cleared"
    SETTINGS_UPDATED = "settings.updated"

    # Monitoring events
    METRICS_UPDATE = "metrics.update"
    LOG_ENTRY = "log.entry"
    ALERT_TRIGGERED = "alert.triggered"

    # User events
    USER_JOINED = "user.joined"
    USER_LEFT = "user.left"
    USER_ACTIVITY = "user.activity"


# ============================================================================
# Message Models
# ============================================================================

class WebSocketMessage(BaseModel):
    """WebSocket message schema"""
    type: str
    event: EventType
    data: Any
    timestamp: str = None
    user_id: Optional[int] = None

    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.utcnow().isoformat()
        super().__init__(**data)


class SubscriptionMessage(BaseModel):
    """Subscription request message"""
    action: str  # subscribe or unsubscribe
    channels: List[str]


# ============================================================================
# Connection Manager
# ============================================================================

class ConnectionManager:
    """Manages WebSocket connections and message broadcasting"""

    def __init__(self):
        # All active connections
        self.active_connections: Dict[str, WebSocket] = {}

        # User subscriptions: user_id -> set of channels
        self.subscriptions: Dict[str, Set[str]] = {}

        # Channel subscribers: channel -> set of user_ids
        self.channel_subscribers: Dict[str, Set[str]] = {}

        # Connection metadata
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------------
    # Connection Management
    # ------------------------------------------------------------------------

    async def connect(
        self,
        websocket: WebSocket,
        client_id: str,
        user_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()

        self.active_connections[client_id] = websocket
        self.subscriptions[client_id] = set()
        self.connection_metadata[client_id] = {
            "user_id": user_id,
            "connected_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }

        # Send connection confirmation
        await self.send_personal_message(
            client_id,
            WebSocketMessage(
                type="system",
                event=EventType.CONNECTED,
                data={
                    "client_id": client_id,
                    "message": "Connected to Quantum Admin WebSocket"
                }
            )
        )

        # Broadcast user joined event
        await self.broadcast(
            WebSocketMessage(
                type="system",
                event=EventType.USER_JOINED,
                data={
                    "client_id": client_id,
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            ),
            exclude=[client_id]
        )

    def disconnect(self, client_id: str):
        """Remove a WebSocket connection"""
        if client_id in self.active_connections:
            # Remove from active connections
            del self.active_connections[client_id]

            # Remove from all channels
            if client_id in self.subscriptions:
                for channel in self.subscriptions[client_id]:
                    if channel in self.channel_subscribers:
                        self.channel_subscribers[channel].discard(client_id)
                del self.subscriptions[client_id]

            # Remove metadata
            if client_id in self.connection_metadata:
                del self.connection_metadata[client_id]

    # ------------------------------------------------------------------------
    # Subscription Management
    # ------------------------------------------------------------------------

    def subscribe(self, client_id: str, channels: List[str]):
        """Subscribe a client to one or more channels"""
        if client_id not in self.subscriptions:
            self.subscriptions[client_id] = set()

        for channel in channels:
            # Add to client subscriptions
            self.subscriptions[client_id].add(channel)

            # Add to channel subscribers
            if channel not in self.channel_subscribers:
                self.channel_subscribers[channel] = set()
            self.channel_subscribers[channel].add(client_id)

    def unsubscribe(self, client_id: str, channels: List[str]):
        """Unsubscribe a client from one or more channels"""
        if client_id not in self.subscriptions:
            return

        for channel in channels:
            # Remove from client subscriptions
            self.subscriptions[client_id].discard(channel)

            # Remove from channel subscribers
            if channel in self.channel_subscribers:
                self.channel_subscribers[channel].discard(client_id)

    def get_subscriptions(self, client_id: str) -> Set[str]:
        """Get all channels a client is subscribed to"""
        return self.subscriptions.get(client_id, set())

    # ------------------------------------------------------------------------
    # Message Sending
    # ------------------------------------------------------------------------

    async def send_personal_message(self, client_id: str, message: WebSocketMessage):
        """Send a message to a specific client"""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_json(message.dict())
            except Exception as e:
                print(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)

    async def broadcast(
        self,
        message: WebSocketMessage,
        exclude: Optional[List[str]] = None
    ):
        """Broadcast a message to all connected clients"""
        exclude = exclude or []
        disconnected_clients = []

        for client_id, websocket in self.active_connections.items():
            if client_id not in exclude:
                try:
                    await websocket.send_json(message.dict())
                except Exception as e:
                    print(f"Error broadcasting to {client_id}: {e}")
                    disconnected_clients.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)

    async def broadcast_to_channel(
        self,
        channel: str,
        message: WebSocketMessage,
        exclude: Optional[List[str]] = None
    ):
        """Broadcast a message to all clients subscribed to a specific channel"""
        exclude = exclude or []

        if channel not in self.channel_subscribers:
            return

        subscribers = self.channel_subscribers[channel].copy()
        disconnected_clients = []

        for client_id in subscribers:
            if client_id not in exclude and client_id in self.active_connections:
                websocket = self.active_connections[client_id]
                try:
                    await websocket.send_json(message.dict())
                except Exception as e:
                    print(f"Error broadcasting to channel {channel} for {client_id}: {e}")
                    disconnected_clients.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)

    # ------------------------------------------------------------------------
    # Event Handlers
    # ------------------------------------------------------------------------

    async def emit_event(
        self,
        event: EventType,
        data: Any,
        channel: Optional[str] = None,
        user_id: Optional[int] = None
    ):
        """Emit an event to subscribers"""
        message = WebSocketMessage(
            type="event",
            event=event,
            data=data,
            user_id=user_id
        )

        if channel:
            await self.broadcast_to_channel(channel, message)
        else:
            await self.broadcast(message)

    # ------------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket server statistics"""
        return {
            "total_connections": len(self.active_connections),
            "total_channels": len(self.channel_subscribers),
            "connections": [
                {
                    "client_id": client_id,
                    "subscriptions": list(self.subscriptions.get(client_id, set())),
                    "metadata": self.connection_metadata.get(client_id, {})
                }
                for client_id in self.active_connections.keys()
            ],
            "channels": {
                channel: len(subscribers)
                for channel, subscribers in self.channel_subscribers.items()
            }
        }


# ============================================================================
# Global Connection Manager Instance
# ============================================================================

manager = ConnectionManager()


# ============================================================================
# Event Emitters (Helper Functions)
# ============================================================================

async def emit_datasource_event(event: EventType, datasource_id: int, data: Dict[str, Any]):
    """Emit a datasource-related event"""
    await manager.emit_event(
        event=event,
        data={"datasource_id": datasource_id, **data},
        channel="datasources"
    )


async def emit_container_event(event: EventType, container_id: str, data: Dict[str, Any]):
    """Emit a container-related event"""
    await manager.emit_event(
        event=event,
        data={"container_id": container_id, **data},
        channel="containers"
    )


async def emit_task_event(event: EventType, task_id: str, data: Dict[str, Any]):
    """Emit a task-related event"""
    await manager.emit_event(
        event=event,
        data={"task_id": task_id, **data},
        channel="tasks"
    )


async def emit_deployment_event(event: EventType, deployment_id: str, data: Dict[str, Any]):
    """Emit a deployment-related event"""
    await manager.emit_event(
        event=event,
        data={"deployment_id": deployment_id, **data},
        channel="deployments"
    )


async def emit_system_notification(message: str, level: str = "info"):
    """Emit a system notification"""
    await manager.emit_event(
        event=EventType.SYSTEM_NOTIFICATION,
        data={
            "message": message,
            "level": level,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


async def emit_metrics_update(metrics: Dict[str, Any]):
    """Emit a metrics update"""
    await manager.emit_event(
        event=EventType.METRICS_UPDATE,
        data=metrics,
        channel="monitoring"
    )


async def emit_log_entry(log_data: Dict[str, Any]):
    """Emit a log entry"""
    await manager.emit_event(
        event=EventType.LOG_ENTRY,
        data=log_data,
        channel="logs"
    )


# ============================================================================
# WebSocket Handler
# ============================================================================

async def websocket_handler(websocket: WebSocket, client_id: str):
    """Handle WebSocket connection and messages"""
    await manager.connect(websocket, client_id)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message_data = json.loads(data)

                # Handle subscription requests
                if message_data.get("action") == "subscribe":
                    channels = message_data.get("channels", [])
                    manager.subscribe(client_id, channels)
                    await manager.send_personal_message(
                        client_id,
                        WebSocketMessage(
                            type="system",
                            event=EventType.CONNECTED,
                            data={
                                "message": f"Subscribed to channels: {', '.join(channels)}",
                                "subscriptions": list(manager.get_subscriptions(client_id))
                            }
                        )
                    )

                elif message_data.get("action") == "unsubscribe":
                    channels = message_data.get("channels", [])
                    manager.unsubscribe(client_id, channels)
                    await manager.send_personal_message(
                        client_id,
                        WebSocketMessage(
                            type="system",
                            event=EventType.CONNECTED,
                            data={
                                "message": f"Unsubscribed from channels: {', '.join(channels)}",
                                "subscriptions": list(manager.get_subscriptions(client_id))
                            }
                        )
                    )

                elif message_data.get("action") == "ping":
                    # Respond to ping
                    await manager.send_personal_message(
                        client_id,
                        WebSocketMessage(
                            type="system",
                            event=EventType.CONNECTED,
                            data={"message": "pong"}
                        )
                    )

            except json.JSONDecodeError:
                await manager.send_personal_message(
                    client_id,
                    WebSocketMessage(
                        type="error",
                        event=EventType.SYSTEM_ALERT,
                        data={"message": "Invalid JSON message"}
                    )
                )

    except WebSocketDisconnect:
        manager.disconnect(client_id)
        # Broadcast user left event
        await manager.broadcast(
            WebSocketMessage(
                type="system",
                event=EventType.USER_LEFT,
                data={
                    "client_id": client_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
        )
