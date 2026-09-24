"""
Queue Parser - Parse q:queue statements

Handles queue management operations.
"""

from typing import List
from xml.etree import ElementTree as ET
from quantum.core.parsers.base import BaseTagParser, ParserError
from quantum.core.ast_nodes import QueueNode


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

        # Parse attributes matching legacy method
        durable = self.get_bool_attr(element, 'durable', True)
        exclusive = self.get_bool_attr(element, 'exclusive', False)
        auto_delete = self.get_bool_attr(element, 'autoDelete', False)
        dead_letter_queue = self.get_attr(element, 'deadLetterQueue')
        ttl_str = self.get_attr(element, 'ttl')
        ttl = int(ttl_str) if ttl_str else None
        result = self.get_attr(element, 'result')

        return QueueNode(
            name=name,
            action=action,
            durable=durable,
            exclusive=exclusive,
            auto_delete=auto_delete,
            dead_letter_queue=dead_letter_queue,
            ttl=ttl,
            result=result
        )
