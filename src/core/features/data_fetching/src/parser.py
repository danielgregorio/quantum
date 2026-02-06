"""
Data Fetching Feature - Parser
Parses q:fetch elements from XML into FetchNode AST
"""

from xml.etree import ElementTree as ET
from typing import Optional, List

from .ast_node import (
    FetchNode,
    FetchLoadingNode,
    FetchErrorNode,
    FetchSuccessNode,
    FetchHeaderNode,
)


class FetchParseError(Exception):
    """Error during fetch element parsing."""
    pass


def parse_fetch(element: ET.Element, parent_parser) -> FetchNode:
    """
    Parse a <q:fetch> element into a FetchNode.

    Args:
        element: XML element for q:fetch
        parent_parser: Reference to QuantumParser for parsing child elements

    Returns:
        FetchNode AST node

    Raises:
        FetchParseError: If required attributes are missing or invalid
    """
    # Required attributes
    name = element.get('name')
    url = element.get('url')

    if not name:
        raise FetchParseError("q:fetch requires 'name' attribute")
    if not url:
        raise FetchParseError("q:fetch requires 'url' attribute")

    fetch_node = FetchNode(name, url)

    # HTTP method
    method = element.get('method', 'GET').upper()
    fetch_node.method = method

    # Request body
    fetch_node.body = element.get('body')

    # Content type
    content_type = element.get('contentType')
    if content_type:
        fetch_node.content_type = content_type

    # Caching
    fetch_node.cache = element.get('cache')
    fetch_node.cache_key = element.get('cacheKey')

    # Polling
    fetch_node.interval = element.get('interval')
    fetch_node.refetch_on = element.get('refetchOn')

    # Timeout
    timeout_attr = element.get('timeout')
    if timeout_attr:
        try:
            fetch_node.timeout = int(timeout_attr)
        except ValueError:
            pass

    # Retry
    retry_attr = element.get('retry')
    if retry_attr:
        try:
            fetch_node.retry = int(retry_attr)
        except ValueError:
            pass

    retry_delay_attr = element.get('retryDelay')
    if retry_delay_attr:
        try:
            fetch_node.retry_delay = int(retry_delay_attr)
        except ValueError:
            pass

    # Response handling
    fetch_node.transform = element.get('transform')
    response_format = element.get('responseFormat')
    if response_format:
        fetch_node.response_format = response_format

    # Callbacks
    fetch_node.on_success = element.get('onSuccess')
    fetch_node.on_error = element.get('onError')

    # Abort on unmount
    abort_attr = element.get('abortOnUnmount', 'true').lower()
    fetch_node.abort_on_unmount = abort_attr in ['true', '1', 'yes']

    # Lazy loading
    lazy_attr = element.get('lazy', 'false').lower()
    fetch_node.lazy = lazy_attr in ['true', '1', 'yes']

    # Credentials mode
    fetch_node.credentials = element.get('credentials')

    # Parse child elements
    for child in element:
        child_type = _get_element_name(child)

        if child_type == 'header':
            header = _parse_fetch_header(child)
            fetch_node.add_header(header)
        elif child_type == 'loading':
            loading = _parse_fetch_loading(child, parent_parser)
            fetch_node.set_loading(loading)
        elif child_type == 'error':
            error = _parse_fetch_error(child, parent_parser)
            fetch_node.set_error(error)
        elif child_type == 'success':
            success = _parse_fetch_success(child, parent_parser)
            fetch_node.set_success(success)
        else:
            # Parse other children as fallback content
            if parent_parser:
                child_node = parent_parser._parse_statement(child)
                if child_node:
                    fetch_node.add_fallback_child(child_node)

    return fetch_node


def _get_element_name(element: ET.Element) -> str:
    """Extract element name removing namespace."""
    return element.tag.split('}')[-1] if '}' in element.tag else element.tag.split(':')[-1]


def _parse_fetch_header(element: ET.Element) -> FetchHeaderNode:
    """Parse <q:header> within q:fetch."""
    name = element.get('name')
    value = element.get('value')

    if not name:
        raise FetchParseError("q:header requires 'name' attribute")
    if value is None:
        raise FetchParseError(f"q:header '{name}' requires 'value' attribute")

    return FetchHeaderNode(name=name, value=value)


def _parse_fetch_loading(element: ET.Element, parent_parser) -> FetchLoadingNode:
    """Parse <q:loading> within q:fetch."""
    loading_node = FetchLoadingNode()

    # Parse text content
    if element.text and element.text.strip():
        from core.ast_nodes import TextNode
        loading_node.add_child(TextNode(element.text.strip()))

    # Parse child elements
    for child in element:
        if parent_parser:
            child_node = parent_parser._parse_statement(child)
            if child_node:
                loading_node.add_child(child_node)

        # Add tail text after child
        if child.tail and child.tail.strip():
            from core.ast_nodes import TextNode
            loading_node.add_child(TextNode(child.tail.strip()))

    return loading_node


def _parse_fetch_error(element: ET.Element, parent_parser) -> FetchErrorNode:
    """Parse <q:error> within q:fetch."""
    error_node = FetchErrorNode()

    # Parse text content
    if element.text and element.text.strip():
        from core.ast_nodes import TextNode
        error_node.add_child(TextNode(element.text.strip()))

    # Parse child elements
    for child in element:
        if parent_parser:
            child_node = parent_parser._parse_statement(child)
            if child_node:
                error_node.add_child(child_node)

        # Add tail text after child
        if child.tail and child.tail.strip():
            from core.ast_nodes import TextNode
            error_node.add_child(TextNode(child.tail.strip()))

    return error_node


def _parse_fetch_success(element: ET.Element, parent_parser) -> FetchSuccessNode:
    """Parse <q:success> within q:fetch."""
    success_node = FetchSuccessNode()

    # Parse text content
    if element.text and element.text.strip():
        from core.ast_nodes import TextNode
        success_node.add_child(TextNode(element.text.strip()))

    # Parse child elements
    for child in element:
        if parent_parser:
            child_node = parent_parser._parse_statement(child)
            if child_node:
                success_node.add_child(child_node)

        # Add tail text after child
        if child.tail and child.tail.strip():
            from core.ast_nodes import TextNode
            success_node.add_child(TextNode(child.tail.strip()))

    return success_node
