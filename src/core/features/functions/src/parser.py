"""
Parser for q:function tags

Handles parsing of function definitions and function calls.
"""

import sys
from pathlib import Path
from xml.etree import ElementTree as ET
from typing import Optional

# Fix imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.ast_nodes import QuantumParam

from .ast_node import FunctionNode, RestConfig


def parse_function(element: ET.Element) -> FunctionNode:
    """
    Parse <q:function> tag

    Examples:
      <!-- Basic function -->
      <q:function name="greet">
        <q:param name="name" type="string" />
        <q:return value="Hello {name}!" />
      </q:function>

      <!-- Function with REST API -->
      <q:function name="getUser" return="object" rest="/api/users/{id}" method="GET">
        <q:param name="id" type="number" required="true" />
        <q:query name="user" datasource="db">
          SELECT * FROM users WHERE id = {id}
        </q:query>
        <q:return value="{user}" />
      </q:function>

      <!-- Cached function -->
      <q:function name="expensiveCalc" cache="true" cache_ttl="3600">
        <q:param name="input" type="number" />
        <!-- ... -->
      </q:function>
    """
    name = element.get('name')
    if not name:
        raise ValueError("Function requires 'name' attribute")

    function = FunctionNode(name)

    # Core attributes
    function.return_type = element.get('return', 'any')
    function.scope = element.get('scope', 'component')
    function.access = element.get('access', 'public')

    # Documentation
    function.description = element.get('description')
    function.hint = element.get('hint')

    # Validation
    validate_str = element.get('validate_params', 'false')
    function.validate_params = validate_str.lower() == 'true'

    # Performance attributes
    cache_str = element.get('cache', 'false')
    function.cache = cache_str.lower() == 'true'

    cache_ttl_str = element.get('cache_ttl')
    if cache_ttl_str:
        function.cache_ttl = int(cache_ttl_str)

    memoize_str = element.get('memoize', 'false')
    function.memoize = memoize_str.lower() == 'true'

    pure_str = element.get('pure', 'false')
    function.pure = pure_str.lower() == 'true'

    # Behavior attributes
    async_str = element.get('async', 'false')
    function.async_func = async_str.lower() == 'true'

    retry_str = element.get('retry', '0')
    function.retry = int(retry_str)

    timeout_str = element.get('timeout')
    if timeout_str:
        function.timeout = int(timeout_str)

    # REST API configuration (shorthand)
    rest_endpoint = element.get('rest')
    if rest_endpoint:
        rest_method = element.get('method', 'GET')
        rest_produces = element.get('produces', 'application/json')
        rest_consumes = element.get('consumes', 'application/json')
        rest_auth = element.get('auth')
        rest_status_str = element.get('status', '200')
        rest_status = int(rest_status_str)

        # Parse roles
        roles_str = element.get('roles')
        roles = roles_str.split(',') if roles_str else []

        function.rest_config = RestConfig(
            endpoint=rest_endpoint,
            method=rest_method,
            produces=rest_produces,
            consumes=rest_consumes,
            auth=rest_auth,
            roles=roles,
            status=rest_status
        )

    return function


def parse_function_param(element: ET.Element) -> QuantumParam:
    """
    Parse <q:param> within q:function

    Example:
      <q:param name="price" type="number" required="true" default="0" />
    """
    name = element.get('name')
    if not name:
        raise ValueError("Function parameter requires 'name' attribute")

    param_type = element.get('type', 'any')
    required_str = element.get('required', 'false')
    required = required_str.lower() == 'true'
    default = element.get('default')
    validation = element.get('validation')
    description = element.get('description')

    return QuantumParam(
        name=name,
        type=param_type,
        required=required,
        default=default,
        validation=validation,
        description=description
    )


def extract_text_content(element: ET.Element) -> str:
    """Extract all text content from element (including children)"""
    parts = []
    if element.text:
        parts.append(element.text.strip())

    for child in element:
        if child.tail:
            parts.append(child.tail.strip())

    return '\n'.join(part for part in parts if part)
