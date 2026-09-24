"""
Parser for q:dump - Variable Inspection
"""

import xml.etree.ElementTree as ET
from .ast_node import DumpNode


def parse_dump(dump_element: ET.Element) -> DumpNode:
    """
    Parse a <q:dump> element into a DumpNode

    Args:
        dump_element: The XML element representing the dump statement

    Returns:
        DumpNode instance

    Raises:
        ValueError: If required attributes are missing or invalid
    """
    # Get required attribute
    var = dump_element.get('var')

    # Get optional attributes
    label = dump_element.get('label')
    format_str = dump_element.get('format', 'html')
    depth_str = dump_element.get('depth', '10')
    when = dump_element.get('when')
    expand_str = dump_element.get('expand', '2')
    show_types_str = dump_element.get('show_types', 'true')

    # Parse depth
    try:
        depth = int(depth_str) if depth_str else 10
    except ValueError:
        depth = 10

    # Parse expand
    try:
        expand = int(expand_str) if expand_str else 2
    except ValueError:
        expand = 2

    # Parse show_types
    show_types = show_types_str.lower() == 'true' if show_types_str else True

    # Validate no child elements (q:dump should be self-closing)
    if len(dump_element) > 0:
        raise ValueError("Dump tag must be self-closing")

    # Create and return DumpNode (validation happens in __init__)
    return DumpNode(
        var=var,
        label=label,
        format=format_str,
        depth=depth,
        when=when,
        expand=expand,
        show_types=show_types
    )
