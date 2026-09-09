"""
Definition handler for textDocument/definition.

Provides go-to-definition for:
- q:function references
- q:component references
- Variable references (q:set)
- Imported components
"""

import logging
import re
from typing import Optional, Union, List

from lsprotocol import types

from ..analysis.symbols import SymbolKind

logger = logging.getLogger("quantum-lsp")


def register_definition_handlers(server):
    """Register definition handlers with the server."""

    @server.feature(types.TEXT_DOCUMENT_DEFINITION)
    def definition(
        params: types.DefinitionParams
    ) -> Optional[Union[types.Location, List[types.Location]]]:
        """Handle go-to-definition request."""
        uri = params.text_document.uri
        position = params.position

        doc = server.workspace_analyzer.get_document(uri)
        if not doc:
            return None

        line = position.line
        character = position.character

        # Get word at cursor
        word, _, _ = doc.get_word_at_position(line, character)
        if not word:
            return None

        logger.debug(f"Go to definition for: {word}")

        # Get context
        context = doc.get_context_at_position(line, character)

        # If in databinding, extract variable name
        if context.get("inside_databinding") or context["context"] == "databinding":
            word = word.split('.')[0]  # Get base variable name

        # Check for component call (uppercase tag)
        line_text = doc.lines[line] if line < len(doc.lines) else ""
        component_match = re.search(rf'<({word})\s', line_text)
        if component_match and word[0].isupper():
            # Look for component definition
            symbol = server.workspace_analyzer.find_component(word)
            if symbol:
                return symbol.to_location()

            # Check imports
            for imp in doc.symbols.get_imports():
                if imp.name == word or imp.type_hint == word:
                    # TODO: Resolve import path and find component
                    return imp.to_location()

        # Look up symbol in current document first
        symbol = doc.symbols.find_definition(word)
        if symbol:
            return symbol.to_location()

        # Search workspace
        symbol = server.workspace_analyzer.find_symbol(word)
        if symbol:
            return symbol.to_location()

        # Check if it's a function call
        if context["context"] == "databinding":
            # Might be a function reference
            symbol = doc.symbols.get_symbol(word, SymbolKind.FUNCTION)
            if symbol:
                return symbol.to_location()

        return None
