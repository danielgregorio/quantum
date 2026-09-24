"""
If Parser - Parse q:if statements

Handles conditional statements with elseif and else blocks.
"""

from typing import List
from xml.etree import ElementTree as ET
from quantum.core.parsers.base import BaseTagParser
from quantum.core.features.conditionals.src.ast_node import IfNode
from quantum.core.ast_nodes import TextNode


class IfParser(BaseTagParser):
    """
    Parser for q:if statements.

    Supports:
    - Simple if conditions
    - Multiple elseif blocks
    - Optional else block
    """

    @property
    def tag_names(self) -> List[str]:
        return ['if']

    def parse(self, element: ET.Element) -> IfNode:
        """
        Parse q:if statement with elseif and else blocks.

        Args:
            element: XML element for q:if

        Returns:
            IfNode AST node
        """
        condition = self.get_attr(element, 'condition', '')
        if_node = IfNode(condition)

        # IF-3: text directly in a branch is content, like in q:loop and in an
        # HTML element. Only child elements were read, so
        # <h2><q:if condition="tag">Posts tagged {tag}</q:if></h2> rendered
        # an empty heading.
        principal = self._body(element, skip=('elseif', 'else'))
        for statement in principal:
            if_node.add_if_statement(statement)

        for child in element:
            child_type = self.get_element_name(child)
            if child_type == 'elseif':
                if_node.add_elseif_block(self.get_attr(child, 'condition', ''), self._body(child))
            elif child_type == 'else':
                for statement in self._body(child):
                    if_node.add_else_statement(statement)

        return if_node

    def _body(self, element: ET.Element, skip=()) -> list:
        """The statements and text of a branch, in document order."""
        body = []
        if element.text and element.text.strip():
            body.append(TextNode(element.text))
        for child in element:
            if self.get_element_name(child) not in skip:
                statement = self.parse_statement(child)
                if statement:
                    body.append(statement)
            if child.tail and child.tail.strip():
                body.append(TextNode(child.tail))
        return body
