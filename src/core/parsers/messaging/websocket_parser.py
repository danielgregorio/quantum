"""
WebSocket Parser - Parse q:websocket statements

Handles WebSocket connection and messaging configuration.
"""

from typing import List
from xml.etree import ElementTree as ET
from core.parsers.base import BaseTagParser, ParserError
from core.features.websocket.src.ast_node import (
    WebSocketNode, WebSocketHandlerNode,
    WebSocketSendNode, WebSocketCloseNode
)


class WebSocketParser(BaseTagParser):
    """
    Parser for q:websocket statements.

    Supports:
    - Connection configuration
    - Event handlers
    - Reconnection settings
    """

    @property
    def tag_names(self) -> List[str]:
        return ['websocket']

    def parse(self, element: ET.Element) -> WebSocketNode:
        """
        Parse q:websocket statement.

        Args:
            element: XML element for q:websocket

        Returns:
            WebSocketNode AST node
        """
        name = self.get_attr(element, 'name')
        url = self.get_attr(element, 'url')

        if not name:
            raise ParserError("WebSocket requires 'name' attribute")
        if not url:
            raise ParserError("WebSocket requires 'url' attribute")

        ws_node = WebSocketNode(
            name=name,
            url=url,
            auto_connect=self.get_bool_attr(element, 'autoConnect', True),
            reconnect=self.get_bool_attr(element, 'reconnect', True),
            reconnect_delay=self.get_int_attr(element, 'reconnectDelay', 1000),
            max_reconnects=self.get_int_attr(element, 'maxReconnects', 10),
            heartbeat=self.get_int_attr(element, 'heartbeat', 30000),
            protocols=self.get_attr(element, 'protocols', '')
        )

        # Parse event handlers
        for child in element:
            child_type = self.get_element_name(child)

            if child_type.startswith('on-'):
                event = child_type[3:]  # Remove 'on-' prefix
                handler = self._parse_handler(child, event)
                ws_node.handlers.append(handler)

        return ws_node

    def _parse_handler(self, element: ET.Element, event: str) -> WebSocketHandlerNode:
        """Parse event handler."""
        handler = WebSocketHandlerNode(event=event)

        for child in element:
            statement = self.parse_statement(child)
            if statement:
                handler.body.append(statement)

        return handler


class WebSocketSendParser(BaseTagParser):
    """Parser for q:websocket-send statements."""

    @property
    def tag_names(self) -> List[str]:
        return ['websocket-send']

    def parse(self, element: ET.Element) -> WebSocketSendNode:
        connection = self.get_attr(element, 'connection')
        message = self.get_attr(element, 'message')
        msg_type = self.get_attr(element, 'type', 'text')

        if not connection:
            raise ParserError("websocket-send requires 'connection' attribute")

        return WebSocketSendNode(
            connection=connection,
            message=message or '',
            type=msg_type
        )


class WebSocketCloseParser(BaseTagParser):
    """Parser for q:websocket-close statements."""

    @property
    def tag_names(self) -> List[str]:
        return ['websocket-close']

    def parse(self, element: ET.Element) -> WebSocketCloseNode:
        connection = self.get_attr(element, 'connection')

        if not connection:
            raise ParserError("websocket-close requires 'connection' attribute")

        return WebSocketCloseNode(
            connection=connection,
            code=self.get_int_attr(element, 'code', 1000),
            reason=self.get_attr(element, 'reason', '')
        )
