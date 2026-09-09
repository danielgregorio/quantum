"""
Function Parser - Parse q:function statements
"""

from typing import List
from xml.etree import ElementTree as ET
from quantum.core.parsers.base import BaseTagParser
from quantum.core.ast_nodes import FunctionNode


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

        # Core attributes
        func_node.return_type = element.get('returnType', 'any')
        func_node.scope = element.get('scope', 'component')
        func_node.access = element.get('access', 'public')
        func_node.description = element.get('description')
        func_node.hint = element.get('hint')

        # Validation
        func_node.validate_params = element.get('validate', 'false').lower() == 'true'

        # Performance
        cache_attr = element.get('cache')
        if cache_attr:
            if cache_attr.lower() == 'true':
                func_node.cache = True
            elif cache_attr.endswith('s'):  # "60s"
                func_node.cache = True
                try:
                    func_node.cache_ttl = int(cache_attr[:-1])
                except ValueError:
                    pass

        func_node.memoize = element.get('memoize', 'false').lower() == 'true'
        func_node.pure = element.get('pure', 'false').lower() == 'true'

        # Behavior
        func_node.async_func = element.get('async', 'false').lower() == 'true'

        retry_attr = element.get('retry')
        if retry_attr:
            try:
                func_node.retry = int(retry_attr)
            except ValueError:
                pass

        timeout_attr = element.get('timeout')
        if timeout_attr:
            func_node.timeout = timeout_attr

        # REST API (optional)
        endpoint = element.get('endpoint')
        if endpoint:
            method = element.get('method', 'GET')
            func_node.enable_rest(endpoint, method)

            # REST-specific attributes
            if element.get('produces'):
                func_node.rest_config.produces = element.get('produces')

            if element.get('consumes'):
                func_node.rest_config.consumes = element.get('consumes')

            if element.get('auth'):
                func_node.rest_config.auth = element.get('auth')

            if element.get('roles'):
                roles_str = element.get('roles')
                func_node.rest_config.roles = [r.strip() for r in roles_str.split(',')]

            if element.get('rateLimit'):
                func_node.rest_config.rate_limit = element.get('rateLimit')

            cors_attr = element.get('cors')
            if cors_attr and cors_attr.lower() == 'true':
                func_node.rest_config.cors = True

            status_attr = element.get('status')
            if status_attr:
                try:
                    func_node.rest_config.status = int(status_attr)
                except ValueError:
                    pass

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
