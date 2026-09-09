"""
WebSocket Executor - Execute q:websocket statements

Handles WebSocket connection management and messaging.
"""

from typing import Any, List, Dict, Type
from quantum.runtime.executors.base import BaseExecutor, ExecutorError

# Import from features module
try:
    from quantum.core.features.websocket.src.ast_node import (
        WebSocketNode, WebSocketSendNode, WebSocketCloseNode
    )
except ImportError:
    from quantum.core.features.websocket.src import (
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

            # register_handler() expects a callable, not a config dict —
            # build a closure per event that runs the handler's AST body
            # with the incoming event payload bound as local variables.
            handlers = {}
            for handler in node.handlers:
                handlers[handler.event] = self._build_event_handler(handler.body)

            # Handlers first, connection second. Handlers are keyed by
            # connection NAME, so registering them early is safe — and with a
            # real transport, autoConnect opens the socket inside
            # register_connection and fires on-connect immediately. Register
            # after, and that first event is dispatched to nobody.
            for event, handler in handlers.items():
                self.services.websocket.register_handler(node.name, event, handler)

            # WebSocketService.register_connection() takes (name, url,
            # metadata) — there is no create_connection(). Connection options
            # ride along as metadata; auto_connect there decides whether a
            # socket is actually opened.
            connection = self.services.websocket.register_connection(
                name=node.name,
                url=url,
                metadata={
                    'auto_connect': node.auto_connect,
                    'reconnect': node.reconnect,
                    'reconnect_delay': node.reconnect_delay,
                    'max_reconnects': node.max_reconnects,
                    'heartbeat': node.heartbeat,
                    'protocols': node.protocols.split(',') if node.protocols else [],
                },
            )

            result = connection.to_dict()

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

    def _build_event_handler(self, body):
        """Build a callable for WebSocketService.register_handler().

        The service calls handlers with the event payload dict; that payload
        is bound as local variables so the handler body can reference it.
        """
        def handle_event(event_data=None):
            variables = event_data if isinstance(event_data, dict) else {'event': event_data}
            return self.run_body_in_child_context(body, variables)

        return handle_event


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
            sent = self.services.websocket.send_message(
                connection_name=connection,
                data=message,
                msg_type=node.type or 'text',
            )

            return {'connection': connection, 'sent': sent}

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
            self.services.websocket.close_connection(
                connection_name=node.connection,
                code=node.code,
                reason=reason,
            )

            return {'connection': node.connection, 'closed': True, 'code': node.code}

        except Exception as e:
            raise ExecutorError(f"WebSocket close error: {e}")
