"""
WebSocket Manager for Quantum Admin
Handles real-time log streaming for deployments
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


@dataclass
class LogMessage:
    """A log message with metadata"""
    timestamp: datetime
    level: str  # info, warning, error, success
    message: str
    step: Optional[str] = None

    def to_dict(self):
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level,
            "message": self.message,
            "step": self.step
        }


@dataclass
class DeploymentChannel:
    """A channel for a specific deployment"""
    deploy_id: str
    connections: Set[WebSocket] = field(default_factory=set)
    logs: List[LogMessage] = field(default_factory=list)
    status: str = "pending"
    current_step: Optional[str] = None


class WebSocketManager:
    """
    Manages WebSocket connections for real-time deployment logs

    Features:
    - Multiple connections per deployment
    - Log buffering for late joiners
    - Status updates and step progress
    """

    def __init__(self, max_log_buffer: int = 1000):
        """
        Initialize WebSocket manager

        Args:
            max_log_buffer: Maximum number of logs to buffer per deployment
        """
        self.channels: Dict[str, DeploymentChannel] = {}
        self.max_log_buffer = max_log_buffer
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, deploy_id: str) -> bool:
        """
        Connect a WebSocket to a deployment channel

        Args:
            websocket: The WebSocket connection
            deploy_id: Deployment ID to subscribe to

        Returns:
            True if connected successfully
        """
        try:
            await websocket.accept()

            async with self._lock:
                if deploy_id not in self.channels:
                    self.channels[deploy_id] = DeploymentChannel(deploy_id=deploy_id)

                channel = self.channels[deploy_id]
                channel.connections.add(websocket)

            # Send buffered logs to new connection
            for log in channel.logs:
                try:
                    await websocket.send_json({
                        "type": "log",
                        "data": log.to_dict()
                    })
                except Exception:
                    break

            # Send current status
            await websocket.send_json({
                "type": "status",
                "data": {
                    "status": channel.status,
                    "step": channel.current_step
                }
            })

            logger.info(f"WebSocket connected to deployment {deploy_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect WebSocket: {e}")
            return False

    async def disconnect(self, websocket: WebSocket, deploy_id: str):
        """
        Disconnect a WebSocket from a deployment channel

        Args:
            websocket: The WebSocket connection
            deploy_id: Deployment ID to unsubscribe from
        """
        async with self._lock:
            if deploy_id in self.channels:
                channel = self.channels[deploy_id]
                channel.connections.discard(websocket)

                # Clean up empty channels for completed deployments
                if not channel.connections and channel.status in ("completed", "failed", "cancelled"):
                    del self.channels[deploy_id]
                    logger.info(f"Cleaned up channel for deployment {deploy_id}")

        logger.info(f"WebSocket disconnected from deployment {deploy_id}")

    async def broadcast_log(
        self,
        deploy_id: str,
        message: str,
        level: str = "info",
        step: Optional[str] = None
    ):
        """
        Broadcast a log message to all connected clients

        Args:
            deploy_id: Deployment ID
            message: Log message
            level: Log level (info, warning, error, success)
            step: Current pipeline step (optional)
        """
        log = LogMessage(
            timestamp=datetime.now(),
            level=level,
            message=message,
            step=step
        )

        async with self._lock:
            if deploy_id not in self.channels:
                self.channels[deploy_id] = DeploymentChannel(deploy_id=deploy_id)

            channel = self.channels[deploy_id]

            # Buffer the log
            channel.logs.append(log)
            if len(channel.logs) > self.max_log_buffer:
                channel.logs = channel.logs[-self.max_log_buffer:]

            # Broadcast to all connections
            disconnected = set()
            for ws in channel.connections:
                try:
                    await ws.send_json({
                        "type": "log",
                        "data": log.to_dict()
                    })
                except Exception:
                    disconnected.add(ws)

            # Remove disconnected clients
            channel.connections -= disconnected

    async def broadcast_status(
        self,
        deploy_id: str,
        status: str,
        step: Optional[str] = None,
        progress: Optional[int] = None
    ):
        """
        Broadcast a status update to all connected clients

        Args:
            deploy_id: Deployment ID
            status: Deployment status (pending, running, completed, failed, cancelled)
            step: Current pipeline step
            progress: Progress percentage (0-100)
        """
        async with self._lock:
            if deploy_id not in self.channels:
                self.channels[deploy_id] = DeploymentChannel(deploy_id=deploy_id)

            channel = self.channels[deploy_id]
            channel.status = status
            channel.current_step = step

            data = {
                "status": status,
                "step": step
            }
            if progress is not None:
                data["progress"] = progress

            # Broadcast to all connections
            disconnected = set()
            for ws in channel.connections:
                try:
                    await ws.send_json({
                        "type": "status",
                        "data": data
                    })
                except Exception:
                    disconnected.add(ws)

            # Remove disconnected clients
            channel.connections -= disconnected

    async def broadcast_step_complete(
        self,
        deploy_id: str,
        step: str,
        success: bool,
        duration_seconds: float,
        message: Optional[str] = None
    ):
        """
        Broadcast that a pipeline step has completed

        Args:
            deploy_id: Deployment ID
            step: Step name that completed
            success: Whether the step succeeded
            duration_seconds: How long the step took
            message: Optional completion message
        """
        async with self._lock:
            if deploy_id not in self.channels:
                return

            channel = self.channels[deploy_id]

            data = {
                "step": step,
                "success": success,
                "duration": duration_seconds,
                "message": message
            }

            disconnected = set()
            for ws in channel.connections:
                try:
                    await ws.send_json({
                        "type": "step_complete",
                        "data": data
                    })
                except Exception:
                    disconnected.add(ws)

            channel.connections -= disconnected

    async def broadcast_complete(
        self,
        deploy_id: str,
        success: bool,
        message: str,
        version: Optional[str] = None
    ):
        """
        Broadcast that the deployment has completed

        Args:
            deploy_id: Deployment ID
            success: Whether the deployment succeeded
            message: Completion message
            version: Deployed version (git commit or docker tag)
        """
        status = "completed" if success else "failed"

        async with self._lock:
            if deploy_id not in self.channels:
                self.channels[deploy_id] = DeploymentChannel(deploy_id=deploy_id)

            channel = self.channels[deploy_id]
            channel.status = status

            data = {
                "success": success,
                "message": message,
                "version": version
            }

            disconnected = set()
            for ws in channel.connections:
                try:
                    await ws.send_json({
                        "type": "complete",
                        "data": data
                    })
                except Exception:
                    disconnected.add(ws)

            channel.connections -= disconnected

    def get_channel_info(self, deploy_id: str) -> Optional[Dict]:
        """
        Get information about a deployment channel

        Args:
            deploy_id: Deployment ID

        Returns:
            Channel info dict or None
        """
        channel = self.channels.get(deploy_id)
        if not channel:
            return None

        return {
            "deploy_id": channel.deploy_id,
            "connections": len(channel.connections),
            "log_count": len(channel.logs),
            "status": channel.status,
            "current_step": channel.current_step
        }

    def get_logs(self, deploy_id: str, limit: int = 100) -> List[Dict]:
        """
        Get buffered logs for a deployment

        Args:
            deploy_id: Deployment ID
            limit: Maximum number of logs to return

        Returns:
            List of log dicts
        """
        channel = self.channels.get(deploy_id)
        if not channel:
            return []

        logs = channel.logs[-limit:] if limit else channel.logs
        return [log.to_dict() for log in logs]


# Singleton instance
_ws_manager = None


def get_websocket_manager() -> WebSocketManager:
    """Get singleton instance of WebSocketManager"""
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager
