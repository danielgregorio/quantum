"""
PyClass Parser - Parse q:class statements

Handles inline Python class definitions.
"""

from typing import List
from xml.etree import ElementTree as ET
from core.parsers.base import BaseTagParser, ParserError
from core.ast_nodes import PyClassNode


class PyClassParser(BaseTagParser):
    """
    Parser for q:class statements.

    Supports:
    - Class definition
    - Base class inheritance
    - Decorator application
    """

    @property
    def tag_names(self) -> List[str]:
        return ['class', 'pyclass']

    def parse(self, element: ET.Element) -> PyClassNode:
        """
        Parse q:class statement.

        Args:
            element: XML element for q:class

        Returns:
            PyClassNode AST node
        """
        name = self.get_attr(element, 'name')
        code = self.get_text(element)

        if not name:
            raise ParserError("class requires 'name' attribute")
        if not code or not code.strip():
            raise ParserError("class body cannot be empty")

        # Parse bases
        bases_attr = self.get_attr(element, 'bases')
        bases = []
        if bases_attr:
            bases = [b.strip() for b in bases_attr.split(',')]

        # Parse decorators
        decorators_attr = self.get_attr(element, 'decorators')
        decorators = []
        if decorators_attr:
            decorators = [d.strip() for d in decorators_attr.split(',')]

        return PyClassNode(
            name=name,
            code=code,
            bases=bases,
            decorators=decorators
        )
