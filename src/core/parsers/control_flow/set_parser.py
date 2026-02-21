"""
Set Parser - Parse q:set statements

Handles variable assignment with validation and persistence.
"""

from typing import List
from xml.etree import ElementTree as ET
from core.parsers.base import BaseTagParser, ParserError
from core.features.state_management.src.ast_node import SetNode


class SetParser(BaseTagParser):
    """
    Parser for q:set statements.

    Supports:
    - Type-safe variable assignment
    - Validation rules
    - Scope management
    - Operations (assign, append, increment, etc.)
    - State persistence
    """

    @property
    def tag_names(self) -> List[str]:
        return ['set']

    def parse(self, element: ET.Element) -> SetNode:
        """
        Parse q:set statement.

        Args:
            element: XML element for q:set

        Returns:
            SetNode AST node
        """
        name = self.get_attr(element, 'name')

        if not name:
            raise ParserError("Set requires 'name' attribute")

        set_node = SetNode(name)

        # Type and value
        set_node.type = self.get_attr(element, 'type', 'string')
        set_node.value = self.get_attr(element, 'value')
        set_node.default = self.get_attr(element, 'default')

        # Validation
        set_node.required = self.get_bool_attr(element, 'required', False)
        set_node.nullable = self.get_bool_attr(element, 'nullable', True)
        set_node.validate_rule = self.get_attr(element, 'validate')
        set_node.pattern = self.get_attr(element, 'pattern')
        set_node.mask = self.get_attr(element, 'mask')
        set_node.range = self.get_attr(element, 'range')
        set_node.enum = self.get_attr(element, 'enum')
        set_node.unique = self.get_attr(element, 'unique')
        set_node.min = self.get_attr(element, 'min')
        set_node.max = self.get_attr(element, 'max')
        set_node.minlength = self.get_attr(element, 'minlength')
        set_node.maxlength = self.get_attr(element, 'maxlength')

        # Behavior
        set_node.scope = self.get_attr(element, 'scope', 'local')
        set_node.operation = self.get_attr(element, 'operation', 'assign')

        # Step for increment/decrement
        set_node.step = self.get_int_attr(element, 'step', 1)

        # Collection operations
        set_node.index = self.get_attr(element, 'index')
        set_node.key = self.get_attr(element, 'key')
        set_node.source = self.get_attr(element, 'source')

        # State persistence
        set_node.persist = self.get_attr(element, 'persist')
        set_node.persist_key = self.get_attr(element, 'persistKey')
        set_node.persist_encrypt = self.get_bool_attr(element, 'persistEncrypt', False)

        persist_ttl = self.get_attr(element, 'persistTtl')
        if persist_ttl:
            try:
                set_node.persist_ttl = int(persist_ttl)
            except ValueError:
                pass

        return set_node
