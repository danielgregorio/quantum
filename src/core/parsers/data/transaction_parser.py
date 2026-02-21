"""
Transaction Parser - Parse q:transaction statements

Handles atomic database transactions.
"""

from typing import List
from xml.etree import ElementTree as ET
from core.parsers.base import BaseTagParser, ParserError
from core.ast_nodes import TransactionNode


class TransactionParser(BaseTagParser):
    """
    Parser for q:transaction statements.

    Supports:
    - Atomic transaction blocks
    - Automatic rollback on error
    - Nested statement execution
    """

    @property
    def tag_names(self) -> List[str]:
        return ['transaction']

    def parse(self, element: ET.Element) -> TransactionNode:
        """
        Parse q:transaction statement.

        Args:
            element: XML element for q:transaction

        Returns:
            TransactionNode AST node
        """
        datasource = self.get_attr(element, 'datasource')

        if not datasource:
            raise ParserError("Transaction requires 'datasource' attribute")

        transaction_node = TransactionNode(datasource)

        # Optional isolation level
        transaction_node.isolation = self.get_attr(element, 'isolation')

        # Parse child statements
        for child in element:
            statement = self.parse_statement(child)
            if statement:
                transaction_node.add_statement(statement)

        return transaction_node
