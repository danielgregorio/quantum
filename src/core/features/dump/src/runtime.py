"""
Runtime service for q:dump - Variable Inspection
"""

import json
from typing import Any, Dict, Set
from html import escape


class DumpService:
    """
    Service to handle variable inspection and formatted output

    Phase 1 Features:
    - HTML, JSON, and text output formats
    - Depth limiting
    - Type information
    - Circular reference detection

    Phase 2 Features (TODO):
    - Rich library integration for beautiful output
    - Expandable/collapsible trees
    - Search within dumps
    - Side-by-side comparison
    - Custom themes
    """

    def __init__(self):
        """Initialize the dump service"""
        self._seen_objects: Set[int] = set()

    def dump(
        self,
        var: Any,
        label: str,
        format: str = 'html',
        depth: int = 10,
        current_depth: int = 0
    ) -> str:
        """
        Generate formatted dump output for a variable

        Args:
            var: Variable to inspect
            label: Label for the dump
            format: Output format (html, json, text)
            depth: Maximum nesting depth
            current_depth: Current recursion depth

        Returns:
            Formatted string output
        """
        # Reset seen objects for new dump
        if current_depth == 0:
            self._seen_objects = set()

        if format == 'json':
            return self._dump_json(var, label)
        elif format == 'text':
            return self._dump_text(var, label, depth, current_depth)
        else:  # html (default)
            return self._dump_html(var, label, depth, current_depth)

    def _dump_json(self, var: Any, label: str) -> str:
        """Dump as pretty-printed JSON"""
        output = [f"=== {label} ==="]
        try:
            json_str = json.dumps(var, indent=2, default=str)
            output.append(json_str)
        except Exception as e:
            output.append(f"Error dumping as JSON: {e}")
            output.append(f"Type: {type(var).__name__}")
            output.append(f"Value: {str(var)}")
        return '\n'.join(output)

    def _dump_text(
        self,
        var: Any,
        label: str,
        max_depth: int,
        current_depth: int,
        prefix: str = ''
    ) -> str:
        """Dump as plain text tree structure"""
        if current_depth == 0:
            output = [f"=== {label} ==="]
        else:
            output = []

        # Check depth limit
        if current_depth >= max_depth:
            output.append(f"{prefix}... (max depth reached)")
            return '\n'.join(output)

        # Get type name
        type_name = type(var).__name__

        # Handle None/null
        if var is None:
            output.append(f"{prefix}{label} => null")
            return '\n'.join(output)

        # Handle primitives
        if isinstance(var, (str, int, float, bool)):
            if isinstance(var, str):
                value_repr = f'"{var}"'
            else:
                value_repr = str(var).lower() if isinstance(var, bool) else str(var)
            output.append(f"{prefix}{label} => {value_repr} ({type_name})")
            return '\n'.join(output)

        # Handle dictionaries/objects
        if isinstance(var, dict):
            output.append(f"{prefix}{label} (dict, {len(var)} items):")
            for key, value in var.items():
                sub_output = self._dump_text(
                    value,
                    str(key),
                    max_depth,
                    current_depth + 1,
                    prefix + '  '
                )
                # Skip the header line for nested items
                sub_lines = sub_output.split('\n')
                if current_depth > 0 and sub_lines:
                    output.extend(sub_lines)
                else:
                    output.append(sub_output)
            return '\n'.join(output)

        # Handle lists/arrays
        if isinstance(var, (list, tuple)):
            output.append(f"{prefix}{label} ({type_name}, {len(var)} items):")
            for i, item in enumerate(var):
                sub_output = self._dump_text(
                    item,
                    f"[{i}]",
                    max_depth,
                    current_depth + 1,
                    prefix + '  '
                )
                sub_lines = sub_output.split('\n')
                if current_depth > 0 and sub_lines:
                    output.extend(sub_lines)
                else:
                    output.append(sub_output)
            return '\n'.join(output)

        # Handle other types
        output.append(f"{prefix}{label} => {str(var)} ({type_name})")
        return '\n'.join(output)

    def _dump_html(
        self,
        var: Any,
        label: str,
        max_depth: int,
        current_depth: int
    ) -> str:
        """Dump as HTML with styling"""
        if current_depth == 0:
            output = [
                '<div class="quantum-dump" style="font-family: monospace; background: #f5f5f5; padding: 10px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px;">',
                f'<h4 style="margin: 0 0 10px 0; color: #333;">{escape(label)}</h4>'
            ]
        else:
            output = []

        # Check depth limit
        if current_depth >= max_depth:
            output.append(f'<span style="color: #999;">... (max depth reached)</span>')
            if current_depth == 0:
                output.append('</div>')
            return ''.join(output)

        # Get type name
        type_name = type(var).__name__

        # Handle None/null
        if var is None:
            output.append('<span style="color: #999; font-style: italic;">null</span>')
            if current_depth == 0:
                output.append('</div>')
            return ''.join(output)

        # Handle primitives
        if isinstance(var, bool):
            color = '#008800' if var else '#cc0000'
            output.append(f'<span style="color: {color}; font-weight: bold;">{str(var).lower()}</span>')
            output.append(f' <span style="color: #999; font-size: 0.9em;">(boolean)</span>')
        elif isinstance(var, (int, float)):
            output.append(f'<span style="color: #0066cc; font-weight: bold;">{var}</span>')
            output.append(f' <span style="color: #999; font-size: 0.9em;">({type_name})</span>')
        elif isinstance(var, str):
            output.append(f'<span style="color: #cc6600;">"{escape(var)}"</span>')
            output.append(f' <span style="color: #999; font-size: 0.9em;">(string)</span>')
        # Handle dictionaries/objects
        elif isinstance(var, dict):
            output.append(f'<span style="color: #999;">(dict, {len(var)} items)</span>')
            output.append('<ul style="margin: 5px 0; padding-left: 20px; list-style: none;">')
            for key, value in var.items():
                output.append('<li style="margin: 2px 0;">')
                output.append(f'<span style="color: #660066; font-weight: bold;">{escape(str(key))}</span>: ')
                output.append(self._dump_html(value, '', max_depth, current_depth + 1))
                output.append('</li>')
            output.append('</ul>')
        # Handle lists/arrays
        elif isinstance(var, (list, tuple)):
            output.append(f'<span style="color: #999;">({type_name}, {len(var)} items)</span>')
            output.append('<ul style="margin: 5px 0; padding-left: 20px; list-style: none;">')
            for i, item in enumerate(var):
                output.append('<li style="margin: 2px 0;">')
                output.append(f'<span style="color: #660066; font-weight: bold;">[{i}]</span>: ')
                output.append(self._dump_html(item, '', max_depth, current_depth + 1))
                output.append('</li>')
            output.append('</ul>')
        # Handle other types
        else:
            output.append(f'<span style="color: #666;">{escape(str(var))}</span>')
            output.append(f' <span style="color: #999; font-size: 0.9em;">({type_name})</span>')

        if current_depth == 0:
            output.append('</div>')

        return ''.join(output)

    def should_dump(self, condition: Any) -> bool:
        """
        Evaluate if dumping should occur based on 'when' condition

        Args:
            condition: Evaluated condition value

        Returns:
            True if should dump, False otherwise
        """
        # If no condition, always dump
        if condition is None:
            return True

        # Evaluate boolean condition
        if isinstance(condition, bool):
            return condition

        # Truthy evaluation for other types
        return bool(condition)
