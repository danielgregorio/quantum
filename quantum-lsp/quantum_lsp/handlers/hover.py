"""
Hover handler for textDocument/hover.

Provides documentation on hover for:
- Tags (description, attributes, examples)
- Attributes (type, required, default, description)
- Variables and functions
"""

import logging
import re
from typing import Optional

from lsprotocol import types

from ..schema import get_tag_info, get_attributes_for_tag

logger = logging.getLogger("quantum-lsp")


def register_hover_handlers(server):
    """Register hover handlers with the server."""

    @server.feature(types.TEXT_DOCUMENT_HOVER)
    def hover(params: types.HoverParams) -> Optional[types.Hover]:
        """Handle hover request."""
        uri = params.text_document.uri
        position = params.position

        doc = server.workspace_analyzer.get_document(uri)
        if not doc:
            return None

        line = position.line
        character = position.character

        # Get the word at cursor position
        word, start_col, end_col = doc.get_word_at_position(line, character)
        if not word:
            return None

        logger.debug(f"Hover on word: {word}")

        # Check context
        context = doc.get_context_at_position(line, character)

        markdown_content = None

        # Hover on tag name
        if context["context"] in ("tag_name", "tag"):
            tag_name = word
            # Try with namespace prefix
            if ':' not in tag_name:
                # Check if it's preceded by a namespace
                line_text = doc.lines[line] if line < len(doc.lines) else ""
                ns_match = re.search(rf'<(\w+):{re.escape(tag_name)}', line_text)
                if ns_match:
                    tag_name = f"{ns_match.group(1)}:{tag_name}"

            tag_info = get_tag_info(tag_name)
            if tag_info:
                markdown_content = tag_info.get_documentation()

        # Hover on attribute name
        elif context["context"] == "attribute_name" or context["context"] == "attribute_value":
            tag = context.get("tag")
            if tag:
                attrs = get_attributes_for_tag(tag)
                attr_info = attrs.get(word)
                if attr_info:
                    markdown_content = attr_info.get_documentation()

        # Hover on databinding variable
        elif context["context"] == "databinding" or context.get("inside_databinding"):
            var_name = word.split('.')[0]  # Handle dot notation
            symbol = doc.symbols.find_definition(var_name)
            if symbol:
                markdown_content = _format_symbol_hover(symbol)

        # Check if hovering over a symbol
        if not markdown_content:
            symbol = doc.symbols.find_definition(word)
            if symbol:
                markdown_content = _format_symbol_hover(symbol)

        if markdown_content:
            return types.Hover(
                contents=types.MarkupContent(
                    kind=types.MarkupKind.Markdown,
                    value=markdown_content
                ),
                range=types.Range(
                    start=types.Position(line=line, character=start_col),
                    end=types.Position(line=line, character=end_col)
                )
            )

        return None


def _format_symbol_hover(symbol) -> str:
    """Format symbol information for hover display."""
    parts = []

    # Symbol kind and name
    kind_labels = {
        "component": "Component",
        "function": "Function",
        "variable": "Variable",
        "parameter": "Parameter",
        "query": "Query",
        "action": "Action",
        "import": "Import",
        "slot": "Slot",
        "route": "Route",
    }

    kind_label = kind_labels.get(symbol.kind.value, symbol.kind.value)
    parts.append(f"**{kind_label}** `{symbol.name}`")

    # Type hint
    if symbol.type_hint:
        parts.append(f"\n\nType: `{symbol.type_hint}`")

    # Description
    if symbol.description:
        parts.append(f"\n\n{symbol.description}")

    # Parent
    if symbol.parent:
        parts.append(f"\n\nDefined in: `{symbol.parent}`")

    # Location
    parts.append(f"\n\n*Line {symbol.line + 1}*")

    return "".join(parts)
