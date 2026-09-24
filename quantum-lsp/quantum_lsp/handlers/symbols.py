"""
Document symbols handler for textDocument/documentSymbol.

Provides outline/symbol navigation for:
- Components
- Functions
- Variables
- Queries
- Actions
- Routes
"""

import logging
from typing import List, Optional, Union

from lsprotocol import types

from ..analysis.symbols import SymbolKind

logger = logging.getLogger("quantum-lsp")


def register_symbols_handlers(server):
    """Register document symbol handlers with the server."""

    @server.feature(types.TEXT_DOCUMENT_DOCUMENT_SYMBOL)
    def document_symbol(
        params: types.DocumentSymbolParams
    ) -> Optional[Union[List[types.DocumentSymbol], List[types.SymbolInformation]]]:
        """Handle document symbol request (outline)."""
        uri = params.text_document.uri

        doc = server.workspace_analyzer.get_document(uri)
        if not doc:
            return None

        logger.debug(f"Getting symbols for: {uri}")

        # Build hierarchical document symbols
        symbols = []

        # Get component symbols (top-level containers)
        for component in doc.symbols.get_components():
            # Get children of this component
            children = _get_component_children(doc, component.name)

            doc_symbol = component.to_document_symbol(children)
            symbols.append(doc_symbol)

        # If no components, add all symbols at top level
        if not symbols:
            for symbol in doc.symbols.get_all_symbols():
                symbols.append(symbol.to_document_symbol())

        return symbols


def _get_component_children(doc, component_name: str) -> List:
    """Get child symbols for a component."""
    children = []

    # Functions in this component
    for func in doc.symbols.get_functions():
        if func.parent == component_name:
            children.append(func)

    # Variables in this component
    for var in doc.symbols.get_variables():
        if var.parent == component_name:
            children.append(var)

    # Queries in this component
    for query in doc.symbols.get_queries():
        if query.parent == component_name:
            children.append(query)

    # Actions in this component
    for action in doc.symbols.get_symbols_by_kind(SymbolKind.ACTION):
        if action.parent == component_name:
            children.append(action)

    # Routes in this component
    for route in doc.symbols.get_symbols_by_kind(SymbolKind.ROUTE):
        if route.parent == component_name:
            children.append(route)

    return children
