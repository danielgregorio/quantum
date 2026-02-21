"""
PyImport Parser - Parse q:pyimport statements

Handles Python module imports.
"""

from typing import List
from xml.etree import ElementTree as ET
from core.parsers.base import BaseTagParser, ParserError
from core.ast_nodes import PyImportNode


class PyImportParser(BaseTagParser):
    """
    Parser for q:pyimport statements.

    Supports:
    - Module import with alias
    - Specific name imports
    - Star imports
    """

    @property
    def tag_names(self) -> List[str]:
        return ['pyimport']

    def parse(self, element: ET.Element) -> PyImportNode:
        """
        Parse q:pyimport statement.

        Args:
            element: XML element for q:pyimport

        Returns:
            PyImportNode AST node
        """
        module = self.get_attr(element, 'module')

        if not module:
            raise ParserError("pyimport requires 'module' attribute")

        # Parse names if present
        names_attr = self.get_attr(element, 'names')
        names = []
        if names_attr:
            names = [n.strip() for n in names_attr.split(',')]

        return PyImportNode(
            module=module,
            alias=self.get_attr(element, 'as'),
            names=names
        )
