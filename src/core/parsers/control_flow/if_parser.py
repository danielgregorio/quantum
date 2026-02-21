"""
If Parser - Parse q:if statements

Handles conditional statements with elseif and else blocks.
"""

from typing import List
from xml.etree import ElementTree as ET
from core.parsers.base import BaseTagParser
from core.features.conditionals.src.ast_node import IfNode


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

        for child in element:
            child_type = self.get_element_name(child)

            if child_type == 'elseif':
                # Parse elseif block
                elseif_condition = self.get_attr(child, 'condition', '')
                elseif_body = []

                for elseif_child in child:
                    statement = self.parse_statement(elseif_child)
                    if statement:
                        elseif_body.append(statement)

                if_node.add_elseif_block(elseif_condition, elseif_body)

            elif child_type == 'else':
                # Parse else block
                for else_child in child:
                    statement = self.parse_statement(else_child)
                    if statement:
                        if_node.add_else_statement(statement)

            else:
                # Main if block statement
                statement = self.parse_statement(child)
                if statement:
                    if_node.add_if_statement(statement)

        return if_node
