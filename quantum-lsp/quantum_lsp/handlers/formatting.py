"""
Formatting handler for textDocument/formatting.

Formats .q files with proper indentation and structure.
"""

import logging
import re
from typing import List, Optional

from lsprotocol import types

logger = logging.getLogger("quantum-lsp")


def register_formatting_handlers(server):
    """Register formatting handlers with the server."""

    @server.feature(types.TEXT_DOCUMENT_FORMATTING)
    def formatting(params: types.DocumentFormattingParams) -> Optional[List[types.TextEdit]]:
        """Handle document formatting request."""
        uri = params.text_document.uri
        options = params.options

        doc = server.workspace_analyzer.get_document(uri)
        if not doc:
            return None

        logger.debug(f"Formatting document: {uri}")

        # Get formatting options
        tab_size = options.tab_size if options.tab_size else 2
        insert_spaces = options.insert_spaces if options.insert_spaces is not None else True
        indent_char = " " * tab_size if insert_spaces else "\t"

        # Format the document
        formatted = _format_xml(doc.text, indent_char)

        if formatted == doc.text:
            return None  # No changes needed

        # Return a single edit that replaces the entire document
        return [types.TextEdit(
            range=types.Range(
                start=types.Position(line=0, character=0),
                end=types.Position(line=len(doc.lines), character=0)
            ),
            new_text=formatted
        )]

    @server.feature(types.TEXT_DOCUMENT_RANGE_FORMATTING)
    def range_formatting(params: types.DocumentRangeFormattingParams) -> Optional[List[types.TextEdit]]:
        """Handle range formatting request."""
        uri = params.text_document.uri
        range_ = params.range
        options = params.options

        doc = server.workspace_analyzer.get_document(uri)
        if not doc:
            return None

        # Get the text in the range
        start_line = range_.start.line
        end_line = range_.end.line

        if start_line >= len(doc.lines) or end_line >= len(doc.lines):
            return None

        # Extract lines to format
        lines = doc.lines[start_line:end_line + 1]
        text_to_format = "\n".join(lines)

        # Get formatting options
        tab_size = options.tab_size if options.tab_size else 2
        insert_spaces = options.insert_spaces if options.insert_spaces is not None else True
        indent_char = " " * tab_size if insert_spaces else "\t"

        # Format the selection
        formatted = _format_xml(text_to_format, indent_char)

        if formatted == text_to_format:
            return None

        return [types.TextEdit(
            range=types.Range(
                start=types.Position(line=start_line, character=0),
                end=types.Position(line=end_line, character=len(doc.lines[end_line]))
            ),
            new_text=formatted
        )]


def _format_xml(text: str, indent_char: str = "  ") -> str:
    """
    Format XML/Quantum document with proper indentation.

    Args:
        text: The XML text to format
        indent_char: Character(s) to use for indentation

    Returns:
        Formatted XML text
    """
    lines = []
    indent_level = 0

    # Split into lines and process
    raw_lines = text.split('\n')

    # Track if we're inside CDATA or SQL content
    in_cdata = False
    in_sql = False

    for line in raw_lines:
        stripped = line.strip()

        if not stripped:
            # Preserve blank lines
            lines.append("")
            continue

        # Check for CDATA
        if "<![CDATA[" in stripped:
            in_cdata = True
        if "]]>" in stripped:
            in_cdata = False

        # Check for SQL in query tags
        if re.match(r'<q:query\s', stripped) or re.match(r'<query\s', stripped):
            in_sql = True
        if re.match(r'</q:query>', stripped) or re.match(r'</query>', stripped):
            in_sql = False

        # Don't reformat CDATA or SQL content
        if in_cdata or in_sql:
            lines.append(indent_char * indent_level + stripped)
            continue

        # Handle closing tags
        if stripped.startswith('</'):
            indent_level = max(0, indent_level - 1)

        # Handle self-closing tags (no indent change)
        is_self_closing = stripped.endswith('/>') or re.match(r'<\?.*\?>', stripped)

        # Handle opening tags followed by closing on same line
        has_content = re.match(r'<[^/][^>]*>[^<]+</[^>]+>', stripped)

        # Add the formatted line
        lines.append(indent_char * indent_level + stripped)

        # Adjust indent for next line
        if not is_self_closing and not has_content:
            if stripped.startswith('<') and not stripped.startswith('</') and not stripped.startswith('<!'):
                # Opening tag - increase indent
                if not stripped.endswith('/>'):
                    indent_level += 1

    return '\n'.join(lines)


def _should_preserve_whitespace(tag: str) -> bool:
    """Check if a tag should preserve its whitespace content."""
    # Tags where whitespace is significant
    preserve_tags = {
        'q:script', 'script',
        'q:prompt', 'prompt',
        'pre', 'code', 'textarea'
    }
    return tag.lower() in preserve_tags
