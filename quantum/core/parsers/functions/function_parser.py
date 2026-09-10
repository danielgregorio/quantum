"""
Function Parser - Parse q:function statements
"""

from typing import List
from xml.etree import ElementTree as ET
from quantum.core.parsers.base import BaseTagParser
from quantum.core.ast_nodes import FunctionNode


_NO_OP = "it was accepted and never did anything, and was removed in Quantum 0.11"
_NEVER_IMPLEMENTED = {
    'validate': "parameters are always converted and checked against their rules (FN-1); remove it",
    'cache': _NO_OP, 'memoize': _NO_OP, 'pure': _NO_OP, 'async': _NO_OP,
    'retry': _NO_OP, 'timeout': _NO_OP, 'access': _NO_OP,
    'scope': "a function belongs to its component; scope=\"global\" never made it callable from another page. " + _NO_OP,
    'endpoint': "functions are not served as REST endpoints; " + _NO_OP,
    'method': _NO_OP, 'produces': _NO_OP, 'consumes': _NO_OP, 'auth': _NO_OP,
    'roles': _NO_OP, 'rateLimit': _NO_OP, 'cors': _NO_OP, 'status': _NO_OP,
}


class FunctionParser(BaseTagParser):
    """
    Parser for q:function statements.

    Examples:
        <q:function name="calculateTotal" returnType="number">
            <q:param name="items" type="array" />
            <q:set name="total" value="0" />
            <q:loop array="{items}" item="item">
                <q:set name="total" value="{total + item.price}" />
            </q:loop>
        </q:function>

        <q:function name="getUser" endpoint="/api/users/{id}" method="GET">
            <q:param name="id" type="integer" source="path" />
            <q:query datasource="db">SELECT * FROM users WHERE id = :id</q:query>
        </q:function>
    """

    @property
    def tag_names(self) -> List[str]:
        return ['function']

    def parse(self, element: ET.Element) -> FunctionNode:
        """Parse q:function element"""
        name = element.get('name')

        if not name:
            from quantum.core.parser import QuantumParseError
            raise QuantumParseError("Function requires 'name' attribute")

        func_node = FunctionNode(name)

        # FN-2: attributes that were parsed into the AST and never did anything.
        # memoize="true" or endpoint="/api/x" looked like working features —
        # the guide documented them — and silently changed nothing.
        for attr in element.attrib:
            if attr in _NEVER_IMPLEMENTED:
                from quantum.core.parser import QuantumParseError
                raise QuantumParseError(
                    f'<q:function name="{name}"> {attr}= is not supported: '
                    f'{_NEVER_IMPLEMENTED[attr]}')

        # Core attributes
        func_node.return_type = element.get('returnType', 'any')
        func_node.description = element.get('description')
        func_node.hint = element.get('hint')

        # Parse function params and body
        for child in element:
            child_type = self._get_element_name(child)

            if child_type == 'param':
                param = self.parse_param(child)
                func_node.add_param(param)
            elif child_type == 'return':
                # ReturnParser is deliberately not in the tag registry (it is
                # an internal parser), so parse_child() returns None for it —
                # which silently dropped every <q:return> from every function
                # body, making functions return nothing. Parse it directly.
                from quantum.core.parsers.functions.return_parser import ReturnParser
                func_node.add_statement(ReturnParser(self._parser).parse(child))
            else:
                # Parse body statements
                statement = self.parse_child(child)
                if statement:
                    func_node.add_statement(statement)

        return func_node
