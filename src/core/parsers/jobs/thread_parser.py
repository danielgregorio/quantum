"""
Thread Parser - Parse q:thread statements

Handles async thread configuration.
"""

from typing import List
from xml.etree import ElementTree as ET
from core.parsers.base import BaseTagParser, ParserError
from core.ast_nodes import ThreadNode


class ThreadParser(BaseTagParser):
    """
    Parser for q:thread statements.

    Supports:
    - Thread execution
    - Join/terminate actions
    - Priority and callbacks
    """

    @property
    def tag_names(self) -> List[str]:
        return ['thread']

    def parse(self, element: ET.Element) -> ThreadNode:
        """
        Parse q:thread statement.

        Args:
            element: XML element for q:thread

        Returns:
            ThreadNode AST node
        """
        name = self.get_attr(element, 'name')

        if not name:
            raise ParserError("Thread requires 'name' attribute")

        thread_node = ThreadNode(
            name=name,
            action=self.get_attr(element, 'action', 'run'),
            priority=self.get_attr(element, 'priority', 'normal'),
            timeout=self.get_attr(element, 'timeout'),
            on_complete=self.get_attr(element, 'onComplete'),
            on_error=self.get_attr(element, 'onError')
        )

        # Parse body statements
        for child in element:
            statement = self.parse_statement(child)
            if statement:
                thread_node.add_statement(statement)

        return thread_node
