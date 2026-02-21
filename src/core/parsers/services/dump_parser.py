"""
Dump Parser - Parse q:dump statements

Handles variable inspection and debugging.
"""

from typing import List
from xml.etree import ElementTree as ET
from core.parsers.base import BaseTagParser
from core.features.dump.src import DumpNode


class DumpParser(BaseTagParser):
    """
    Parser for q:dump statements.

    Supports:
    - Variable inspection
    - Multiple output formats
    - Depth control
    - Conditional dumping
    """

    @property
    def tag_names(self) -> List[str]:
        return ['dump']

    def parse(self, element: ET.Element) -> DumpNode:
        """
        Parse q:dump statement.

        Args:
            element: XML element for q:dump

        Returns:
            DumpNode AST node
        """
        var = self.get_attr(element, 'var', '')
        label = self.get_attr(element, 'label', var)
        format_type = self.get_attr(element, 'format', 'text')
        depth = self.get_int_attr(element, 'depth', 3)
        when = self.get_attr(element, 'when')

        dump_node = DumpNode(
            var=var,
            label=label,
            format=format_type,
            depth=depth,
            when=when
        )

        return dump_node
