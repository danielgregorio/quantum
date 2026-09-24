"""
Workspace analyzer for managing multiple documents.
"""

import logging
from typing import Dict, List, Optional
from pathlib import Path
from lsprotocol import types

from .document import QuantumDocument
from .symbols import Symbol, SymbolKind

logger = logging.getLogger("quantum-lsp")


class WorkspaceAnalyzer:
    """
    Manages analysis across multiple documents in a workspace.

    Provides:
    - Document tracking and lifecycle management
    - Cross-document symbol resolution
    - Workspace-wide search
    """

    def __init__(self, server):
        self.server = server
        self._documents: Dict[str, QuantumDocument] = {}
        self._component_paths: Dict[str, str] = {}  # component_name -> uri

    def open_document(self, uri: str, text: str, version: Optional[int] = None):
        """Handle document open."""
        doc = QuantumDocument(uri, text, version)
        self._documents[uri] = doc

        # Index component definitions
        self._index_components(doc)

        # Publish diagnostics
        self._publish_diagnostics(uri)

        logger.debug(f"Opened document: {uri}")

    def update_document(self, uri: str, text: str, version: Optional[int] = None):
        """Handle document change."""
        if uri in self._documents:
            self._documents[uri].update(text, version)
            self._index_components(self._documents[uri])
            self._publish_diagnostics(uri)
        else:
            self.open_document(uri, text, version)

        logger.debug(f"Updated document: {uri}")

    def close_document(self, uri: str):
        """Handle document close."""
        if uri in self._documents:
            # Clear diagnostics
            self.server.publish_diagnostics(uri, [])

            # Remove from component index
            doc = self._documents[uri]
            for symbol in doc.symbols.get_components():
                if self._component_paths.get(symbol.name) == uri:
                    del self._component_paths[symbol.name]

            del self._documents[uri]
            logger.debug(f"Closed document: {uri}")

    def get_document(self, uri: str) -> Optional[QuantumDocument]:
        """Get a document by URI."""
        return self._documents.get(uri)

    def validate_document(self, uri: str) -> List[types.Diagnostic]:
        """Validate a document and return diagnostics."""
        doc = self.get_document(uri)
        if not doc:
            return []
        return doc.get_diagnostics()

    def _publish_diagnostics(self, uri: str):
        """Publish diagnostics for a document."""
        doc = self.get_document(uri)
        if doc:
            diagnostics = doc.get_diagnostics()
            self.server.publish_diagnostics(uri, diagnostics)

    def _index_components(self, doc: QuantumDocument):
        """Index component definitions from a document."""
        for symbol in doc.symbols.get_components():
            self._component_paths[symbol.name] = doc.uri

    def find_component(self, name: str) -> Optional[Symbol]:
        """Find a component definition by name across all documents."""
        uri = self._component_paths.get(name)
        if uri:
            doc = self.get_document(uri)
            if doc:
                return doc.symbols.get_symbol(name, SymbolKind.COMPONENT)
        return None

    def find_symbol(self, name: str, kind: SymbolKind = None) -> Optional[Symbol]:
        """
        Find a symbol by name across all documents.

        If kind is None, searches all symbol kinds.
        """
        for doc in self._documents.values():
            if kind:
                symbol = doc.symbols.get_symbol(name, kind)
            else:
                symbol = doc.symbols.find_definition(name)
            if symbol:
                return symbol
        return None

    def find_references(self, name: str) -> List[types.Location]:
        """Find all references to a symbol across all documents."""
        references = []
        for doc in self._documents.values():
            refs = doc.symbols.get_references(name)
            references.extend(refs)
        return references

    def get_all_variables(self) -> List[Symbol]:
        """Get all variable symbols across all documents."""
        variables = []
        for doc in self._documents.values():
            variables.extend(doc.symbols.get_variables())
        return variables

    def get_all_functions(self) -> List[Symbol]:
        """Get all function symbols across all documents."""
        functions = []
        for doc in self._documents.values():
            functions.extend(doc.symbols.get_functions())
        return functions

    def get_all_components(self) -> List[Symbol]:
        """Get all component symbols across all documents."""
        components = []
        for doc in self._documents.values():
            components.extend(doc.symbols.get_components())
        return components

    def get_imported_components(self, uri: str) -> List[Symbol]:
        """Get imported components for a document."""
        doc = self.get_document(uri)
        if not doc:
            return []
        return doc.symbols.get_imports()

    def get_document_uris(self) -> List[str]:
        """Get all tracked document URIs."""
        return list(self._documents.keys())
