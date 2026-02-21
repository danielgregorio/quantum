"""
Invoke Parser - Parse q:invoke statements

Handles function, component, and HTTP invocations.
"""

from typing import List
from xml.etree import ElementTree as ET
from core.parsers.base import BaseTagParser, ParserError
from core.features.invocation.src.ast_node import InvokeNode, InvokeHeaderNode
from core.ast_nodes import QuantumParam


class InvokeParser(BaseTagParser):
    """
    Parser for q:invoke statements.

    Supports:
    - Function invocation
    - Component invocation
    - HTTP requests (REST APIs)
    - Service invocation
    - Authentication (bearer, basic, custom)
    """

    @property
    def tag_names(self) -> List[str]:
        return ['invoke']

    def parse(self, element: ET.Element) -> InvokeNode:
        """
        Parse q:invoke statement.

        Args:
            element: XML element for q:invoke

        Returns:
            InvokeNode AST node
        """
        name = self.get_attr(element, 'name')
        if not name:
            raise ParserError("Invoke requires 'name' attribute")

        invoke_node = InvokeNode(name)

        # Parse invocation target
        invoke_node.function = self.get_attr(element, 'function')
        invoke_node.component = self.get_attr(element, 'component')
        invoke_node.url = self.get_attr(element, 'url')
        invoke_node.endpoint = self.get_attr(element, 'endpoint')
        invoke_node.service = self.get_attr(element, 'service')

        # HTTP attributes
        invoke_node.method = self.get_attr(element, 'method', 'GET').upper()
        invoke_node.content_type = self.get_attr(element, 'contentType', 'application/json')

        # Authentication
        invoke_node.auth_type = self.get_attr(element, 'authType')
        invoke_node.auth_token = self.get_attr(element, 'authToken')
        invoke_node.auth_header = self.get_attr(element, 'authHeader')
        invoke_node.auth_username = self.get_attr(element, 'authUsername')
        invoke_node.auth_password = self.get_attr(element, 'authPassword')

        # Timeouts and retries
        invoke_node.timeout = self.get_int_attr(element, 'timeout', 0) or None
        invoke_node.retry = self.get_int_attr(element, 'retry', 0) or None
        invoke_node.retry_delay = self.get_int_attr(element, 'retryDelay', 0) or None

        # Response handling
        invoke_node.response_format = self.get_attr(element, 'responseFormat', 'auto')
        invoke_node.transform = self.get_attr(element, 'transform')
        invoke_node.cache = self.get_bool_attr(element, 'cache', False)
        invoke_node.ttl = self.get_int_attr(element, 'ttl', 0) or None
        invoke_node.result = self.get_attr(element, 'result')

        # Parse child elements
        for child in element:
            child_type = self.get_element_name(child)

            if child_type == 'header':
                header = self._parse_header(child)
                invoke_node.add_header(header)
            elif child_type == 'param':
                param = self._parse_param(child)
                invoke_node.add_param(param)
            elif child_type == 'body':
                invoke_node.body = child.text or ""

        return invoke_node

    def _parse_header(self, element: ET.Element) -> InvokeHeaderNode:
        """Parse q:header within q:invoke."""
        name = self.get_attr(element, 'name')
        value = self.get_attr(element, 'value')

        if not name:
            raise ParserError("Invoke header requires 'name' attribute")
        if value is None:
            raise ParserError(f"Invoke header '{name}' requires 'value' attribute")

        return InvokeHeaderNode(name, value)

    def _parse_param(self, element: ET.Element) -> QuantumParam:
        """Parse q:param within q:invoke."""
        name = self.get_attr(element, 'name')
        value = self.get_attr(element, 'value')
        param_type = self.get_attr(element, 'type', 'string')

        if not name:
            raise ParserError("Param requires 'name' attribute")

        param = QuantumParam(name, param_type)
        param.value = value
        param.required = self.get_bool_attr(element, 'required', False)
        param.default = self.get_attr(element, 'default')

        return param
