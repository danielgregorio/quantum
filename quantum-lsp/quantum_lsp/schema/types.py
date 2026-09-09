"""
Type definitions for Quantum schema.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class AttributeType(Enum):
    """Types of attribute values."""
    STRING = "string"
    INTEGER = "integer"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    EXPRESSION = "expression"  # {databinding} expression
    ENUM = "enum"
    CSS_SIZE = "css_size"  # e.g., "10px", "50%", "auto"
    CSS_COLOR = "css_color"
    URL = "url"
    PATH = "path"
    SQL = "sql"
    REGEX = "regex"


@dataclass
class AttributeInfo:
    """Information about a tag attribute."""
    name: str
    type: AttributeType
    required: bool = False
    default: Optional[str] = None
    description: str = ""
    enum_values: List[str] = field(default_factory=list)
    deprecated: bool = False
    since_version: str = "1.0.0"

    def get_documentation(self) -> str:
        """Get formatted documentation string."""
        doc_parts = [f"**{self.name}**"]

        if self.required:
            doc_parts.append("*(required)*")

        doc_parts.append(f"\n\nType: `{self.type.value}`")

        if self.default:
            doc_parts.append(f"\n\nDefault: `{self.default}`")

        if self.enum_values:
            doc_parts.append(f"\n\nValues: {', '.join(f'`{v}`' for v in self.enum_values)}")

        if self.description:
            doc_parts.append(f"\n\n{self.description}")

        if self.deprecated:
            doc_parts.append("\n\n*Deprecated*")

        return " ".join(doc_parts)


@dataclass
class TagInfo:
    """Information about a Quantum tag."""
    name: str
    namespace: str  # "q", "ui", "qg", "qt", "qtest"
    description: str
    attributes: Dict[str, AttributeInfo] = field(default_factory=dict)
    children: List[str] = field(default_factory=list)  # Allowed child tags
    parent_tags: List[str] = field(default_factory=list)  # Allowed parent tags
    self_closing: bool = False
    deprecated: bool = False
    since_version: str = "1.0.0"
    examples: List[str] = field(default_factory=list)
    see_also: List[str] = field(default_factory=list)

    @property
    def full_name(self) -> str:
        """Get full tag name with namespace."""
        return f"{self.namespace}:{self.name}"

    def get_documentation(self) -> str:
        """Get formatted documentation string."""
        doc_parts = [f"## `<{self.full_name}>`\n"]

        doc_parts.append(f"{self.description}\n")

        if self.attributes:
            doc_parts.append("\n### Attributes\n")
            for attr_name, attr_info in self.attributes.items():
                req = " *(required)*" if attr_info.required else ""
                doc_parts.append(f"- `{attr_name}`{req}: {attr_info.description}")

        if self.examples:
            doc_parts.append("\n### Examples\n")
            for example in self.examples:
                doc_parts.append(f"```xml\n{example}\n```\n")

        if self.see_also:
            doc_parts.append("\n### See Also\n")
            doc_parts.append(", ".join(f"`<{t}>`" for t in self.see_also))

        if self.deprecated:
            doc_parts.append("\n\n**Deprecated**")

        return "\n".join(doc_parts)

    def get_required_attributes(self) -> List[str]:
        """Get list of required attribute names."""
        return [name for name, attr in self.attributes.items() if attr.required]

    def get_optional_attributes(self) -> List[str]:
        """Get list of optional attribute names."""
        return [name for name, attr in self.attributes.items() if not attr.required]
