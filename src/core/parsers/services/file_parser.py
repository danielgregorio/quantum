"""
File Parser - Parse q:file statements

Handles file upload and deletion.
"""

from typing import List
from xml.etree import ElementTree as ET
from core.parsers.base import BaseTagParser, ParserError
from core.ast_nodes import FileNode


class FileParser(BaseTagParser):
    """
    Parser for q:file statements.

    Supports:
    - File upload with conflict handling
    - File deletion
    - Result storage
    """

    @property
    def tag_names(self) -> List[str]:
        return ['file']

    def parse(self, element: ET.Element) -> FileNode:
        """
        Parse q:file statement.

        Args:
            element: XML element for q:file

        Returns:
            FileNode AST node
        """
        action = self.get_attr(element, 'action', 'upload')
        file_attr = self.get_attr(element, 'file')

        if not file_attr:
            raise ParserError("File requires 'file' attribute")

        file_node = FileNode(action, file_attr)
        file_node.destination = self.get_attr(element, 'destination')
        file_node.name_conflict = self.get_attr(element, 'nameConflict', 'makeunique')
        file_node.result = self.get_attr(element, 'result')

        return file_node
