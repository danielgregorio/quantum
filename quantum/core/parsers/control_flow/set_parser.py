"""
Set Parser - Parse q:set statements

Handles variable assignment with validation and persistence.
"""

from typing import List
from xml.etree import ElementTree as ET
from quantum.core.parsers.base import BaseTagParser, ParserError
from quantum.core.features.state_management.src.ast_node import SetNode


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

        # Type and value. SET-5: without type=, the value keeps the type of a
        # value that is exactly one expression; the node still says 'string'
        # for the code generators, and type_given tells the runtime.
        given_type = self.get_attr(element, 'type')
        set_node.type = given_type or 'string'
        set_node.type_given = given_type is not None
        if given_type is not None:
            from quantum.runtime.executors.control_flow.set_executor import SET_TYPES
            _one_of(name, 'type', given_type, SET_TYPES)
        set_node.value = self.get_attr(element, 'value')
        set_node.default = self.get_attr(element, 'default')

        # Validation
        set_node.required = self.get_bool_attr(element, 'required', False)
        set_node.nullable = self.get_bool_attr(element, 'nullable', True)
        set_node.validate_rule = self.get_attr(element, 'validate')
        set_node.pattern = self.get_attr(element, 'pattern')
        if element.get('mask') is not None:
            # A2: accepted and never applied.
            from quantum.core.parser import QuantumParseError
            raise QuantumParseError(
                f'<q:set name="{set_node.name}"> mask= is not supported: it was accepted and '
                f'never did anything. To validate a format use pattern=.')
        set_node.range = self.get_attr(element, 'range')
        set_node.enum = self.get_attr(element, 'enum')
        if element.get('unique') is not None:
            # PARSE-3: accepted and never applied (operation="unique" is the list operation).
            from quantum.core.parser import QuantumParseError
            raise QuantumParseError(
                f'<q:set name="{set_node.name}"> unique= is not supported: it was accepted and '
                f'never did anything. To drop repeated items of a list use operation="unique".')
        set_node.min = self.get_attr(element, 'min')
        set_node.max = self.get_attr(element, 'max')
        set_node.minlength = self.get_attr(element, 'minlength')
        set_node.maxlength = self.get_attr(element, 'maxlength')

        # Behavior
        set_node.scope = self.get_attr(element, 'scope', 'local')
        set_node.operation = self.get_attr(element, 'operation', 'assign')
        # SET-3, SET-4: a value nothing understands is a parse error with the
        # line. They used to fail only when the q:set ran ("Unsupported
        # operation"), or — for validate= — to fail every value it checked.
        _one_of(set_node.name, 'operation', set_node.operation, OPERATIONS)
        _one_of(set_node.name, 'scope', set_node.scope, SCOPES)
        if set_node.validate_rule and not _is_regex(set_node.validate_rule):
            from quantum.runtime.validators import QuantumValidators
            _one_of(set_node.name, 'validate', set_node.validate_rule,
                    tuple(QuantumValidators.PATTERNS), 'or a regular expression starting with ^')

        # Step for increment/decrement
        set_node.step = self.get_int_attr(element, 'step', 1)

        # Collection operations
        set_node.index = self.get_attr(element, 'index')
        set_node.key = self.get_attr(element, 'key')
        set_node.source = self.get_attr(element, 'source')

        # SET-2: browser persistence never ran in a page.
        persist = [a for a in ('persist', 'persistKey', 'persistTtl', 'persistEncrypt')
                   if element.get(a) is not None]
        if persist:
            from quantum.core.parser import QuantumParseError
            raise QuantumParseError(
                f'<q:set name="{set_node.name}"> {persist[0]}= was removed in Quantum 0.16: it '
                f'kept the variable in the browser, and a page\'s variables live on the server, '
                f'for one request. Keep what must last in session.{set_node.name} (per user) '
                f'or in the database.')

        return set_node


# SET-3: what the executor does with each operation, and the scopes it writes to.
OPERATIONS = ('assign', 'increment', 'decrement', 'add', 'multiply',
              'append', 'prepend', 'remove', 'removeAt', 'clear', 'sort', 'reverse', 'unique',
              'merge', 'setProperty', 'deleteProperty', 'clone',
              'uppercase', 'lowercase', 'trim', 'format')
SCOPES = ('local', 'function', 'component', 'session', 'application', 'request')


def _is_regex(rule: str) -> bool:
    """validate= also takes a regular expression (QuantumValidators.validate)."""
    return rule.startswith('^') or rule.startswith('.*')


def _one_of(name: str, attr: str, value: str, allowed, extra: str = '') -> None:
    if value not in allowed:
        raise ParserError(f'<q:set name="{name}"> {attr}="{value}" does not exist; '
                          f'{attr} is one of: {", ".join(allowed)}' + (f', {extra}' if extra else ''))
