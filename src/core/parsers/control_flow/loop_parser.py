"""
Loop Parser - Parse q:loop statements

Handles various loop types: range, array, list, query.
"""

from typing import List
from xml.etree import ElementTree as ET
from core.parsers.base import BaseTagParser, ParserError
from core.features.loops.src.ast_node import LoopNode
from core.ast_nodes import TextNode


class LoopParser(BaseTagParser):
    """
    Parser for q:loop statements.

    Supports:
    - Range loops (from/to)
    - Array iteration
    - List iteration (with delimiter)
    - Query result iteration
    """

    @property
    def tag_names(self) -> List[str]:
        return ['loop']

    def parse(self, element: ET.Element) -> LoopNode:
        """
        Parse q:loop statement with various types.

        Args:
            element: XML element for q:loop

        Returns:
            LoopNode AST node
        """
        # Check for query attribute (shorthand syntax)
        query_attr = self.get_attr(element, 'query')

        if query_attr:
            # <q:loop query="users"> shorthand syntax
            loop_type = 'query'
            var_name = query_attr
            loop_node = LoopNode(loop_type, var_name)
            loop_node.query_name = query_attr
        else:
            # Traditional syntax
            loop_type = self.get_attr(element, 'type', 'range')
            var_name = self.get_attr(element, 'var')

            if not var_name:
                raise ParserError("Loop requires 'var' attribute")

            loop_node = LoopNode(loop_type, var_name)

        # Configure based on loop type
        if loop_type == 'range':
            loop_node.from_value = self.get_attr(element, 'from')
            loop_node.to_value = self.get_attr(element, 'to')
            loop_node.step_value = self.get_int_attr(element, 'step', 1)

        elif loop_type == 'array':
            loop_node.items = self.get_attr(element, 'items')
            loop_node.index_name = self.get_attr(element, 'index')

        elif loop_type == 'list':
            loop_node.items = self.get_attr(element, 'items')
            loop_node.delimiter = self.get_attr(element, 'delimiter', ',')
            loop_node.index_name = self.get_attr(element, 'index')

        elif loop_type == 'query':
            loop_node.index_name = self.get_attr(element, 'index')

        # Parse loop body - add text content before first child
        if element.text and element.text.strip():
            loop_node.add_statement(TextNode(element.text))

        # Parse loop body statements
        for child in element:
            statement = self.parse_statement(child)
            if statement:
                loop_node.add_statement(statement)
            # Add tail text after child element
            if child.tail and child.tail.strip():
                loop_node.add_statement(TextNode(child.tail))

        return loop_node
