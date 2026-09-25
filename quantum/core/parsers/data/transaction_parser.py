"""
Transaction Parser - Parse q:transaction statements

Handles atomic database transactions.
"""

from typing import List
from xml.etree import ElementTree as ET
from quantum.core.parsers.base import BaseTagParser
from quantum.core.ast_nodes import TransactionNode


_LEVELS = ('READ_UNCOMMITTED', 'READ_COMMITTED', 'REPEATABLE_READ', 'SERIALIZABLE')


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

        # Isolation level. Everything written in this repository and in the
        # docs spells it isolationLevel; the parser read `isolation`, so the
        # level was silently dropped every time. Both spellings work.
        #
        # DB-4: the node took the datasource as its FIRST positional argument
        # — which is isolation_level — and the level went to an attribute
        # nothing read. Every q:transaction then failed validation with
        # "Invalid isolation level: " (the empty datasource), and an explicit
        # datasource= reached neither the node nor the executor.
        level = (self.get_attr(element, 'isolationLevel')
                 or self.get_attr(element, 'isolation') or 'READ_COMMITTED')
        if level not in _LEVELS:
            from quantum.core.parser import QuantumParseError
            raise QuantumParseError(
                f'<q:transaction isolationLevel="{level}">: the level is one of '
                f'{", ".join(_LEVELS)}')
        transaction_node = TransactionNode(isolation_level=level)
        transaction_node.datasource = datasource or ''

        # DB-4: a q:query inside a transaction with datasource= uses it. Every
        # query had to repeat it, or parsing failed with "Query requires
        # either 'datasource' or 'source' attribute" — the guide's own
        # transaction example did not parse. Nested ones too: a q:query in a
        # q:loop or a q:if of the transaction (loading a file row by row)
        # still had to repeat it.
        if datasource:
            self._inherit_datasource(element, datasource)

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

    def _inherit_datasource(self, element: ET.Element, datasource: str) -> None:
        """Give `datasource` to every q:query under `element` that names none.

        A nested q:transaction with its own datasource= passes on its own."""
        for child in element:
            name = self.get_element_name(child)
            if name == 'query':
                if not child.get('datasource') and not child.get('source'):
                    child.set('datasource', datasource)
            elif not (name == 'transaction' and child.get('datasource')):
                self._inherit_datasource(child, datasource)

    def _datasource_of_children(self, transaction_node) -> str:
        """The datasource of the first child query that names one."""
        for statement in getattr(transaction_node, 'statements', []) or []:
            name = getattr(statement, 'datasource', None)
            if name:
                return name
        return ''
