"""
Parser for q:log - Structured Logging
"""

import xml.etree.ElementTree as ET
from typing import Optional
from .ast_node import LogNode


def parse_log(log_element: ET.Element) -> LogNode:
    """
    Parse a <q:log> element into a LogNode

    Args:
        log_element: The XML element representing the log statement

    Returns:
        LogNode instance

    Raises:
        ValueError: If required attributes are missing or invalid
    """
    # Get required attributes
    level = log_element.get('level')
    message = log_element.get('message')

    # Get optional attributes
    context = log_element.get('context')
    when = log_element.get('when')
    provider = log_element.get('provider')
    async_mode_str = log_element.get('async', 'true')
    correlation_id = log_element.get('correlation_id')

    # Parse async mode
    async_mode = async_mode_str.lower() == 'true' if async_mode_str else True

    # Validate no child elements (q:log should be self-closing)
    if len(log_element) > 0:
        raise ValueError("Log tag must be self-closing")

    # Create and return LogNode (validation happens in __init__)
    return LogNode(
        level=level,
        message=message,
        context=context,
        when=when,
        provider=provider,
        async_mode=async_mode,
        correlation_id=correlation_id
    )
