"""
Quantum Schema - Tag and attribute definitions

This module provides the complete schema for Quantum tags including:
- Tag definitions with descriptions
- Attribute definitions with types and requirements
- Value enumerations for validation
"""

from .tags import QUANTUM_TAGS, get_tag_info, get_all_tags, get_tags_by_namespace
from .attributes import get_attributes_for_tag, COMMON_ATTRIBUTES
from .types import AttributeType, TagInfo, AttributeInfo

__all__ = [
    "QUANTUM_TAGS",
    "get_tag_info",
    "get_all_tags",
    "get_tags_by_namespace",
    "get_attributes_for_tag",
    "COMMON_ATTRIBUTES",
    "AttributeType",
    "TagInfo",
    "AttributeInfo",
]
