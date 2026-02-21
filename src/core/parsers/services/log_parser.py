"""
Log Parser - Parse q:log statements

Handles structured logging.
"""

from typing import List
from xml.etree import ElementTree as ET
from core.parsers.base import BaseTagParser
from core.features.logging.src import LogNode


class LogParser(BaseTagParser):
    """
    Parser for q:log statements.

    Supports:
    - Log levels (debug, info, warn, error)
    - Conditional logging
    - Context data
    - Correlation IDs
    """

    @property
    def tag_names(self) -> List[str]:
        return ['log']

    def parse(self, element: ET.Element) -> LogNode:
        """
        Parse q:log statement.

        Args:
            element: XML element for q:log

        Returns:
            LogNode AST node
        """
        level = self.get_attr(element, 'level', 'info')
        message = self.get_attr(element, 'message') or self.get_text(element)

        log_node = LogNode(level=level, message=message)
        log_node.when = self.get_attr(element, 'when')
        log_node.context = self.get_attr(element, 'context')
        log_node.correlation_id = self.get_attr(element, 'correlationId')

        return log_node
