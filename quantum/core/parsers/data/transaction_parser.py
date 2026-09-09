"""
Transaction Parser - Parse q:transaction statements

Handles atomic database transactions.
"""

from typing import List
from xml.etree import ElementTree as ET
from quantum.core.parsers.base import BaseTagParser, ParserError
from quantum.core.ast_nodes import TransactionNode


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
        # datasource= is optional. Requiring it was stricter than the runtime
        # (DatabaseService.begin_transaction defaults it) and stricter than
        # everything written against it: all four q:transaction blocks in this
        # repository omit it, and three of them are tests that had been
        # failing on this line — "Transaction requires 'datasource'
        # attribute" — rather than on anything about transactions.
        datasource = self.get_attr(element, 'datasource')

        transaction_node = TransactionNode(datasource or '')

        # Isolation level. Everything written in this repository and in the
        # docs spells it isolationLevel; the parser read `isolation`, so the
        # level was silently dropped every time. Both spellings work.
        transaction_node.isolation = (
            self.get_attr(element, 'isolationLevel')
            or self.get_attr(element, 'isolation')
        )

        # Parse child statements
        for child in element:
            statement = self.parse_statement(child)
            if statement:
                transaction_node.add_statement(statement)

        if not datasource:
            # Take it from the queries being wrapped, which is what the author
            # means by wrapping them. Only if none of them names one does this
            # fall back to "default".
            transaction_node.datasource = (
                self._datasource_of_children(transaction_node) or 'default'
            )

        return transaction_node

    def _datasource_of_children(self, transaction_node) -> str:
        """The datasource of the first child query that names one."""
        for statement in getattr(transaction_node, 'statements', []) or []:
            name = getattr(statement, 'datasource', None)
            if name:
                return name
        return ''
