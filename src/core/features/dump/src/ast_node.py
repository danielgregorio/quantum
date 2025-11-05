"""
AST Node for q:dump - Variable Inspection
"""

from typing import Optional
from core.ast_nodes import QuantumNode


class DumpNode(QuantumNode):
    """
    Represents a <q:dump> - Variable inspection statement

    Example:
        <q:dump var="{user}" label="User Object" />
        <q:dump var="{data}" format="json" depth="3" />
    """

    VALID_FORMATS = ['html', 'json', 'text']

    def __init__(
        self,
        var: str,
        label: Optional[str] = None,
        format: str = 'html',
        depth: int = 10,
        when: Optional[str] = None,
        expand: int = 2,
        show_types: bool = True
    ):
        """
        Initialize a DumpNode

        Args:
            var: Variable to inspect (databinding expression)
            label: Optional identifying label
            format: Output format (html, json, text)
            depth: Max depth for nested structures
            when: Optional conditional expression
            expand: Auto-expand depth (Phase 2)
            show_types: Show type information (Phase 2)
        """
        # Validate var
        if not var:
            raise ValueError("Dump requires 'var' attribute")

        # Validate format
        if format and format not in self.VALID_FORMATS:
            raise ValueError(
                f"Invalid dump format '{format}'. Must be one of: {', '.join(self.VALID_FORMATS)}"
            )

        # Validate depth
        if depth is not None:
            try:
                depth_int = int(depth)
                if depth_int < 0:
                    raise ValueError("Dump depth must be a positive integer")
                depth = depth_int
            except (ValueError, TypeError):
                raise ValueError("Dump depth must be a positive integer")

        self.var = var
        self.label = label if label else var
        self.format = format
        self.depth = depth
        self.when = when
        self.expand = expand
        self.show_types = show_types

    def __repr__(self):
        attrs = [f"var={self.var!r}"]
        if self.label != self.var:
            attrs.append(f"label={self.label!r}")
        if self.format != 'html':
            attrs.append(f"format={self.format!r}")
        if self.when:
            attrs.append(f"when={self.when!r}")
        return f"DumpNode({', '.join(attrs)})"

    def to_dict(self):
        """Convert node to dictionary for debugging/serialization"""
        return {
            "type": "dump",
            "var": self.var,
            "label": self.label,
            "format": self.format,
            "depth": self.depth,
            "when": self.when,
            "expand": self.expand,
            "show_types": self.show_types
        }

    def validate(self):
        """Validate the node and return list of errors"""
        errors = []

        if not self.var:
            errors.append("Dump requires 'var' attribute")

        if self.format and self.format not in self.VALID_FORMATS:
            errors.append(f"Invalid dump format '{self.format}'. Must be one of: {', '.join(self.VALID_FORMATS)}")

        if self.depth is not None and (not isinstance(self.depth, int) or self.depth < 0):
            errors.append("Dump depth must be a positive integer")

        return errors
