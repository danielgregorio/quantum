"""
Python Parser - Parse q:python statements

Handles embedded Python code.
"""

from typing import List
from xml.etree import ElementTree as ET
from core.parsers.base import BaseTagParser, ParserError
from core.ast_nodes import PythonNode


class PythonParser(BaseTagParser):
    """
    Parser for q:python statements.

    Supports:
    - Inline Python code
    - Scope management
    - Async execution
    - Result capture
    """

    @property
    def tag_names(self) -> List[str]:
        return ['python']

    def parse(self, element: ET.Element) -> PythonNode:
        """
        Parse q:python statement.

        Args:
            element: XML element for q:python

        Returns:
            PythonNode AST node
        """
        code = self.get_text(element)

        if not code or not code.strip():
            raise ParserError("Python block cannot be empty")

        return PythonNode(
            code=code,
            scope=self.get_attr(element, 'scope', 'component'),
            async_mode=self.get_bool_attr(element, 'async', False),
            timeout=self.get_attr(element, 'timeout'),
            result=self.get_attr(element, 'result')
        )
