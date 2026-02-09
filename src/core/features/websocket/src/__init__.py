"""
WebSocket Feature Module

Provides real-time bidirectional communication via WebSockets.

Usage:
    from core.features.websocket.src import (
        WebSocketNode, WebSocketHandlerNode, WebSocketSendNode, WebSocketCloseNode
    )
"""

from .ast_node import (
    WebSocketNode,
    WebSocketHandlerNode,
    WebSocketSendNode,
    WebSocketCloseNode
)

__all__ = [
    'WebSocketNode',
    'WebSocketHandlerNode',
    'WebSocketSendNode',
    'WebSocketCloseNode'
]
