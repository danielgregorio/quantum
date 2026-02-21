"""
WebSocket Executor - Execute q:websocket statements

Handles WebSocket connection management and messaging.
"""

from typing import Any, List, Dict, Type
from runtime.executors.base import BaseExecutor, ExecutorError

# Import from features module
try:
    from core.features.websocket.src.ast_node import (
        WebSocketNode, WebSocketSendNode, WebSocketCloseNode
    )
except ImportError:
    from core.features.websocket.src import (
        WebSocketNode, WebSocketSendNode, WebSocketCloseNode
    )


class WebSocketExecutor(BaseExecutor):
    """
    Executor for q:websocket statements.

    Supports:
    - WebSocket connection creation
    - Auto-connect and reconnection
    - Event handlers (on-connect, on-message, on-error, on-close)
    - Heartbeat/ping-pong
    """

    @property
    def handles(self) -> List[Type]:
        return [WebSocketNode]

    def execute(self, node: WebSocketNode, exec_context) -> Any:
        """
        Execute WebSocket connection creation.

        Args:
            node: WebSocketNode with WebSocket configuration
            exec_context: Execution context

        Returns:
            WebSocket connection info dict
        """
        try:
            context = exec_context.get_all_variables()

            # Resolve URL
            url = self.apply_databinding(node.url, context)

            # Build handlers config
            handlers = {}
            for handler in node.handlers:
                handlers[handler.event] = {
                    'body': handler.body,
                    'runtime': self._runtime,
                    'exec_context': exec_context
                }

            # Create WebSocket connection
            result = self.services.websocket.create_connection(
                name=node.name,
                url=url,
                auto_connect=node.auto_connect,
                reconnect=node.reconnect,
                reconnect_delay=node.reconnect_delay,
                max_reconnects=node.max_reconnects,
                heartbeat=node.heartbeat,
                protocols=node.protocols.split(',') if node.protocols else [],
                handlers=handlers
            )

            # Store connection reference
            exec_context.set_variable(node.name, result, scope="component")

            return result

        except Exception as e:
            exec_context.set_variable(node.name, {
                'connected': False,
                'error': str(e),
                'url': node.url
            }, scope="component")
            raise ExecutorError(f"WebSocket creation error: {e}")


class WebSocketSendExecutor(BaseExecutor):
    """
    Executor for q:websocket-send statements.

    Sends messages through an existing WebSocket connection.
    """

    @property
    def handles(self) -> List[Type]:
        return [WebSocketSendNode]

    def execute(self, node: WebSocketSendNode, exec_context) -> Any:
        """
        Execute WebSocket message send.

        Args:
            node: WebSocketSendNode with send configuration
            exec_context: Execution context

        Returns:
            Send result dict
        """
        try:
            context = exec_context.get_all_variables()

            # Resolve message
            message = self.apply_databinding(node.message, context)

            # Get connection
            connection = node.connection

            # Send message
            result = self.services.websocket.send(
                connection=connection,
                message=message,
                message_type=node.type
            )

            return result

        except Exception as e:
            raise ExecutorError(f"WebSocket send error: {e}")


class WebSocketCloseExecutor(BaseExecutor):
    """
    Executor for q:websocket-close statements.

    Closes an existing WebSocket connection.
    """

    @property
    def handles(self) -> List[Type]:
        return [WebSocketCloseNode]

    def execute(self, node: WebSocketCloseNode, exec_context) -> Any:
        """
        Execute WebSocket connection close.

        Args:
            node: WebSocketCloseNode with close configuration
            exec_context: Execution context

        Returns:
            Close result dict
        """
        try:
            context = exec_context.get_all_variables()

            # Resolve reason if provided
            reason = ""
            if node.reason:
                reason = self.apply_databinding(node.reason, context)

            # Close connection
            result = self.services.websocket.close(
                connection=node.connection,
                code=node.code,
                reason=reason
            )

            return result

        except Exception as e:
            raise ExecutorError(f"WebSocket close error: {e}")
