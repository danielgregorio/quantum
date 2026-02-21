"""
Message Parser - Parse q:message and q:subscribe statements

Handles message queue operations.
"""

from typing import List
from xml.etree import ElementTree as ET
from core.parsers.base import BaseTagParser, ParserError
from core.ast_nodes import MessageNode, SubscribeNode, MessageHeaderNode


class MessageParser(BaseTagParser):
    """
    Parser for q:message statements.

    Supports:
    - Publish (topic)
    - Send (queue)
    - Request/reply
    """

    @property
    def tag_names(self) -> List[str]:
        return ['message']

    def parse(self, element: ET.Element) -> MessageNode:
        """
        Parse q:message statement.

        Args:
            element: XML element for q:message

        Returns:
            MessageNode AST node
        """
        msg_node = MessageNode(
            name=self.get_attr(element, 'name'),
            topic=self.get_attr(element, 'topic'),
            queue=self.get_attr(element, 'queue'),
            type=self.get_attr(element, 'type', 'publish'),
            timeout=self.get_attr(element, 'timeout')
        )

        # Parse children
        for child in element:
            child_type = self.get_element_name(child)

            if child_type == 'header':
                header = MessageHeaderNode(
                    name=self.get_attr(child, 'name', ''),
                    value=self.get_attr(child, 'value', '')
                )
                msg_node.add_header(header)
            elif child_type == 'body':
                msg_node.body = self.get_text(child)

        return msg_node


class SubscribeParser(BaseTagParser):
    """
    Parser for q:subscribe statements.

    Supports:
    - Topic subscription
    - Queue consumption
    - Message handlers
    """

    @property
    def tag_names(self) -> List[str]:
        return ['subscribe']

    def parse(self, element: ET.Element) -> SubscribeNode:
        """
        Parse q:subscribe statement.

        Args:
            element: XML element for q:subscribe

        Returns:
            SubscribeNode AST node
        """
        name = self.get_attr(element, 'name')

        if not name:
            raise ParserError("Subscribe requires 'name' attribute")

        sub_node = SubscribeNode(
            name=name,
            topic=self.get_attr(element, 'topic'),
            topics=self.get_attr(element, 'topics'),
            queue=self.get_attr(element, 'queue'),
            ack=self.get_attr(element, 'ack', 'auto'),
            prefetch=self.get_int_attr(element, 'prefetch', 1)
        )

        # Parse handlers
        for child in element:
            child_type = self.get_element_name(child)

            if child_type == 'onMessage':
                for handler_child in child:
                    statement = self.parse_statement(handler_child)
                    if statement:
                        sub_node.add_on_message_statement(statement)
            elif child_type == 'onError':
                for handler_child in child:
                    statement = self.parse_statement(handler_child)
                    if statement:
                        sub_node.add_on_error_statement(statement)

        return sub_node
