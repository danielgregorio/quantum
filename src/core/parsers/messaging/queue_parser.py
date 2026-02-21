"""
Queue Parser - Parse q:queue statements

Handles queue management operations.
"""

from typing import List
from xml.etree import ElementTree as ET
from core.parsers.base import BaseTagParser, ParserError
from core.ast_nodes import QueueNode


class QueueParser(BaseTagParser):
    """
    Parser for q:queue statements.

    Supports:
    - Queue declaration
    - Queue purge/delete
    - Queue info
    """

    @property
    def tag_names(self) -> List[str]:
        return ['queue']

    def parse(self, element: ET.Element) -> QueueNode:
        """
        Parse q:queue statement.

        Args:
            element: XML element for q:queue

        Returns:
            QueueNode AST node
        """
        name = self.get_attr(element, 'name')
        action = self.get_attr(element, 'action', 'declare')

        if not name:
            raise ParserError("Queue requires 'name' attribute")

        queue_node = QueueNode(name=name, action=action)

        # Queue options
        queue_node.durable = self.get_bool_attr(element, 'durable', True)
        queue_node.exclusive = self.get_bool_attr(element, 'exclusive', False)
        queue_node.auto_delete = self.get_bool_attr(element, 'autoDelete', False)
        queue_node.dead_letter = self.get_attr(element, 'deadLetter')
        queue_node.ttl = self.get_int_attr(element, 'ttl', 0) or None
        queue_node.max_length = self.get_int_attr(element, 'maxLength', 0) or None
        queue_node.result = self.get_attr(element, 'result')

        return queue_node
