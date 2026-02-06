"""
Attribute definitions and utilities.
"""

from typing import Dict, List, Optional
from .types import AttributeInfo, AttributeType
from .tags import QUANTUM_TAGS, get_tag_info


# Common HTML attributes that can appear on any element
COMMON_ATTRIBUTES: Dict[str, AttributeInfo] = {
    "id": AttributeInfo(
        name="id",
        type=AttributeType.STRING,
        description="Unique identifier for the element"
    ),
    "class": AttributeInfo(
        name="class",
        type=AttributeType.STRING,
        description="CSS class name(s)"
    ),
    "style": AttributeInfo(
        name="style",
        type=AttributeType.STRING,
        description="Inline CSS styles"
    ),
}


def get_attributes_for_tag(tag_name: str) -> Dict[str, AttributeInfo]:
    """
    Get all attributes available for a tag.

    Args:
        tag_name: Full tag name (e.g., 'q:set', 'ui:button')

    Returns:
        Dictionary of attribute name to AttributeInfo
    """
    tag_info = get_tag_info(tag_name)
    if tag_info:
        return tag_info.attributes

    # Return empty dict for unknown tags
    return {}


def get_attribute_info(tag_name: str, attr_name: str) -> Optional[AttributeInfo]:
    """
    Get information about a specific attribute on a tag.

    Args:
        tag_name: Full tag name (e.g., 'q:set')
        attr_name: Attribute name (e.g., 'name')

    Returns:
        AttributeInfo or None if not found
    """
    attrs = get_attributes_for_tag(tag_name)
    return attrs.get(attr_name)


def get_required_attributes(tag_name: str) -> List[str]:
    """
    Get list of required attribute names for a tag.

    Args:
        tag_name: Full tag name

    Returns:
        List of required attribute names
    """
    tag_info = get_tag_info(tag_name)
    if tag_info:
        return tag_info.get_required_attributes()
    return []


def get_enum_values(tag_name: str, attr_name: str) -> List[str]:
    """
    Get enum values for an attribute.

    Args:
        tag_name: Full tag name
        attr_name: Attribute name

    Returns:
        List of valid enum values, or empty list
    """
    attr_info = get_attribute_info(tag_name, attr_name)
    if attr_info and attr_info.type == AttributeType.ENUM:
        return attr_info.enum_values
    return []


def validate_attribute_value(tag_name: str, attr_name: str, value: str) -> Optional[str]:
    """
    Validate an attribute value.

    Args:
        tag_name: Full tag name
        attr_name: Attribute name
        value: Value to validate

    Returns:
        Error message if invalid, None if valid
    """
    attr_info = get_attribute_info(tag_name, attr_name)
    if not attr_info:
        # Unknown attribute - could be HTML attribute
        return None

    # Validate enum values
    if attr_info.type == AttributeType.ENUM and attr_info.enum_values:
        if value not in attr_info.enum_values:
            return f"Invalid value '{value}' for attribute '{attr_name}'. Expected one of: {', '.join(attr_info.enum_values)}"

    # Validate boolean values
    if attr_info.type == AttributeType.BOOLEAN:
        if value.lower() not in ('true', 'false', '1', '0', 'yes', 'no'):
            return f"Invalid boolean value '{value}' for attribute '{attr_name}'"

    # Validate integer values
    if attr_info.type == AttributeType.INTEGER:
        # Allow databinding expressions
        if not value.startswith('{'):
            try:
                int(value)
            except ValueError:
                return f"Invalid integer value '{value}' for attribute '{attr_name}'"

    # Validate decimal values
    if attr_info.type == AttributeType.DECIMAL:
        if not value.startswith('{'):
            try:
                float(value)
            except ValueError:
                return f"Invalid decimal value '{value}' for attribute '{attr_name}'"

    return None
