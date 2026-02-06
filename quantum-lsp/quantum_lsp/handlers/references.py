"""
References handler for textDocument/references.

Find all references to:
- Variables
- Functions
- Components
- Queries
"""

import logging
from typing import Optional, List

from lsprotocol import types

logger = logging.getLogger("quantum-lsp")


def register_references_handlers(server):
    """Register references handlers with the server."""

    @server.feature(types.TEXT_DOCUMENT_REFERENCES)
    def references(params: types.ReferenceParams) -> Optional[List[types.Location]]:
        """Handle find references request."""
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

        logger.debug(f"Find references for: {word}")

        # Get the base name (handle dot notation)
        base_name = word.split('.')[0]

        # Collect references
        locations = []

        # Get references from current document
        refs = doc.symbols.get_references(base_name)
        locations.extend(refs)

        # Get references from workspace
        workspace_refs = server.workspace_analyzer.find_references(base_name)
        locations.extend(workspace_refs)

        # Include the definition itself if requested
        if params.context and params.context.include_declaration:
            symbol = doc.symbols.find_definition(base_name)
            if symbol:
                locations.insert(0, symbol.to_location())

        # Remove duplicates
        seen = set()
        unique_locations = []
        for loc in locations:
            key = (loc.uri, loc.range.start.line, loc.range.start.character)
            if key not in seen:
                seen.add(key)
                unique_locations.append(loc)

        return unique_locations if unique_locations else None
