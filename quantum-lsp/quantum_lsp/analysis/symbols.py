"""
Symbol table for Quantum documents.

Tracks defined symbols (variables, functions, components) for
go-to-definition, find-references, and completion.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set
from lsprotocol import types


class SymbolKind(Enum):
    """Types of symbols in Quantum documents."""
    COMPONENT = "component"
    FUNCTION = "function"
    VARIABLE = "variable"
    PARAMETER = "parameter"
    QUERY = "query"
    ACTION = "action"
    IMPORT = "import"
    SLOT = "slot"
    ROUTE = "route"


@dataclass
class Symbol:
    """Represents a defined symbol."""
    name: str
    kind: SymbolKind
    line: int
    column: int
    end_line: int
    end_column: int
    uri: str
    parent: Optional[str] = None
    type_hint: Optional[str] = None
    description: Optional[str] = None
    attributes: Dict[str, str] = field(default_factory=dict)

    def to_location(self) -> types.Location:
        """Convert to LSP Location."""
        return types.Location(
            uri=self.uri,
            range=types.Range(
                start=types.Position(line=self.line, character=self.column),
                end=types.Position(line=self.end_line, character=self.end_column)
            )
        )

    def to_symbol_information(self) -> types.SymbolInformation:
        """Convert to LSP SymbolInformation."""
        kind_map = {
            SymbolKind.COMPONENT: types.SymbolKind.Class,
            SymbolKind.FUNCTION: types.SymbolKind.Function,
            SymbolKind.VARIABLE: types.SymbolKind.Variable,
            SymbolKind.PARAMETER: types.SymbolKind.Property,
            SymbolKind.QUERY: types.SymbolKind.Struct,
            SymbolKind.ACTION: types.SymbolKind.Method,
            SymbolKind.IMPORT: types.SymbolKind.Module,
            SymbolKind.SLOT: types.SymbolKind.Field,
            SymbolKind.ROUTE: types.SymbolKind.Interface,
        }

        return types.SymbolInformation(
            name=self.name,
            kind=kind_map.get(self.kind, types.SymbolKind.Variable),
            location=self.to_location(),
            container_name=self.parent
        )

    def to_document_symbol(self, children: List['Symbol'] = None) -> types.DocumentSymbol:
        """Convert to LSP DocumentSymbol."""
        kind_map = {
            SymbolKind.COMPONENT: types.SymbolKind.Class,
            SymbolKind.FUNCTION: types.SymbolKind.Function,
            SymbolKind.VARIABLE: types.SymbolKind.Variable,
            SymbolKind.PARAMETER: types.SymbolKind.Property,
            SymbolKind.QUERY: types.SymbolKind.Struct,
            SymbolKind.ACTION: types.SymbolKind.Method,
            SymbolKind.IMPORT: types.SymbolKind.Module,
            SymbolKind.SLOT: types.SymbolKind.Field,
            SymbolKind.ROUTE: types.SymbolKind.Interface,
        }

        child_symbols = []
        if children:
            child_symbols = [c.to_document_symbol() for c in children]

        return types.DocumentSymbol(
            name=self.name,
            kind=kind_map.get(self.kind, types.SymbolKind.Variable),
            range=types.Range(
                start=types.Position(line=self.line, character=self.column),
                end=types.Position(line=self.end_line, character=self.end_column)
            ),
            selection_range=types.Range(
                start=types.Position(line=self.line, character=self.column),
                end=types.Position(line=self.line, character=self.column + len(self.name))
            ),
            detail=self.type_hint,
            children=child_symbols if child_symbols else None
        )


class SymbolTable:
    """
    Symbol table for a Quantum document.

    Tracks all defined symbols and their locations for
    navigation and analysis features.
    """

    def __init__(self, uri: str):
        self.uri = uri
        self._symbols: Dict[str, Symbol] = {}
        self._by_kind: Dict[SymbolKind, List[Symbol]] = {k: [] for k in SymbolKind}
        self._references: Dict[str, List[types.Location]] = {}

    def add_symbol(self, symbol: Symbol):
        """Add a symbol to the table."""
        key = f"{symbol.kind.value}:{symbol.name}"
        if symbol.parent:
            key = f"{symbol.parent}.{key}"

        self._symbols[key] = symbol
        self._by_kind[symbol.kind].append(symbol)

    def get_symbol(self, name: str, kind: SymbolKind, parent: str = None) -> Optional[Symbol]:
        """Get a symbol by name and kind."""
        key = f"{kind.value}:{name}"
        if parent:
            key = f"{parent}.{key}"
        return self._symbols.get(key)

    def get_symbols_by_kind(self, kind: SymbolKind) -> List[Symbol]:
        """Get all symbols of a given kind."""
        return self._by_kind.get(kind, [])

    def get_all_symbols(self) -> List[Symbol]:
        """Get all symbols."""
        return list(self._symbols.values())

    def get_variables(self) -> List[Symbol]:
        """Get all variable symbols."""
        return self._by_kind[SymbolKind.VARIABLE]

    def get_functions(self) -> List[Symbol]:
        """Get all function symbols."""
        return self._by_kind[SymbolKind.FUNCTION]

    def get_components(self) -> List[Symbol]:
        """Get all component symbols."""
        return self._by_kind[SymbolKind.COMPONENT]

    def get_queries(self) -> List[Symbol]:
        """Get all query symbols."""
        return self._by_kind[SymbolKind.QUERY]

    def get_imports(self) -> List[Symbol]:
        """Get all import symbols."""
        return self._by_kind[SymbolKind.IMPORT]

    def add_reference(self, name: str, location: types.Location):
        """Add a reference to a symbol."""
        if name not in self._references:
            self._references[name] = []
        self._references[name].append(location)

    def get_references(self, name: str) -> List[types.Location]:
        """Get all references to a symbol."""
        return self._references.get(name, [])

    def find_symbol_at_position(self, line: int, column: int) -> Optional[Symbol]:
        """Find symbol at a given position."""
        for symbol in self._symbols.values():
            if (symbol.line <= line <= symbol.end_line and
                symbol.column <= column <= symbol.end_column):
                return symbol
        return None

    def find_definition(self, name: str) -> Optional[Symbol]:
        """
        Find the definition of a symbol by name.

        Searches variables, functions, queries, components in that order.
        """
        # Search in order of likelihood
        for kind in [SymbolKind.VARIABLE, SymbolKind.FUNCTION, SymbolKind.QUERY,
                     SymbolKind.COMPONENT, SymbolKind.PARAMETER, SymbolKind.IMPORT]:
            symbol = self.get_symbol(name, kind)
            if symbol:
                return symbol
        return None

    def clear(self):
        """Clear all symbols."""
        self._symbols.clear()
        for kind in SymbolKind:
            self._by_kind[kind] = []
        self._references.clear()
