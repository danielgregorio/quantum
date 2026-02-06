"""
Quantum document analysis.

Parses and analyzes .q documents for LSP features.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from xml.etree import ElementTree as ET
from lsprotocol import types

from .symbols import SymbolTable, Symbol, SymbolKind
from ..schema import get_tag_info, get_attributes_for_tag, QUANTUM_TAGS
from ..schema.attributes import get_required_attributes, validate_attribute_value
from ..utils.position import offset_to_position, position_to_offset

logger = logging.getLogger("quantum-lsp")


@dataclass
class ParsedElement:
    """Represents a parsed XML element with position info."""
    tag: str
    attributes: Dict[str, str]
    start_line: int
    start_col: int
    end_line: int
    end_col: int
    children: List['ParsedElement']
    text: Optional[str] = None
    parent: Optional['ParsedElement'] = None


class QuantumDocument:
    """
    Represents an open Quantum document with parsed state.

    Provides:
    - XML parsing with position tracking
    - Symbol extraction
    - Validation and diagnostics
    - Context detection for completion
    """

    def __init__(self, uri: str, text: str, version: Optional[int] = None):
        self.uri = uri
        self.text = text
        self.version = version
        self.lines = text.split('\n')

        # Parsed state
        self._ast: Any = None
        self._parse_error: Optional[str] = None
        self._elements: List[ParsedElement] = []

        # Symbol table
        self.symbols = SymbolTable(uri)

        # Parse the document
        self._parse()

    def _parse(self):
        """Parse the document and extract symbols."""
        self.symbols.clear()
        self._elements = []
        self._parse_error = None

        try:
            # Parse XML structure for position-aware analysis
            self._parse_elements()

            # Extract symbols from elements
            self._extract_symbols()

        except ET.ParseError as e:
            self._parse_error = str(e)
            logger.debug(f"XML parse error: {e}")
        except Exception as e:
            self._parse_error = str(e)
            logger.debug(f"Parse error: {e}")

    def _parse_elements(self):
        """
        Parse XML elements with position tracking.

        Uses regex-based parsing to track positions since
        ElementTree doesn't preserve line numbers.
        """
        # Match opening and closing tags
        tag_pattern = re.compile(
            r'<(/?)([a-zA-Z_][\w:-]*)'  # Opening < and optional /, tag name
            r'([^>]*?)'                  # Attributes
            r'(/?)>',                    # Optional self-closing / and >
            re.DOTALL
        )

        # Match attributes
        attr_pattern = re.compile(
            r'([a-zA-Z_][\w:-]*)'        # Attribute name
            r'\s*=\s*'                   # =
            r'["\']([^"\']*)["\']'       # Value in quotes
        )

        stack: List[ParsedElement] = []
        root_elements: List[ParsedElement] = []

        for match in tag_pattern.finditer(self.text):
            is_closing = match.group(1) == '/'
            tag_name = match.group(2)
            attrs_str = match.group(3)
            is_self_closing = match.group(4) == '/'

            start_offset = match.start()
            end_offset = match.end()
            start_line, start_col = offset_to_position(self.text, start_offset)
            end_line, end_col = offset_to_position(self.text, end_offset)

            if is_closing:
                # Closing tag - pop from stack
                if stack and stack[-1].tag.split(':')[-1] == tag_name.split(':')[-1]:
                    elem = stack.pop()
                    elem.end_line = end_line
                    elem.end_col = end_col
            else:
                # Opening tag - parse attributes
                attributes = {}
                for attr_match in attr_pattern.finditer(attrs_str):
                    attr_name = attr_match.group(1)
                    attr_value = attr_match.group(2)
                    attributes[attr_name] = attr_value

                elem = ParsedElement(
                    tag=tag_name,
                    attributes=attributes,
                    start_line=start_line,
                    start_col=start_col,
                    end_line=end_line,
                    end_col=end_col,
                    children=[],
                    parent=stack[-1] if stack else None
                )

                if stack:
                    stack[-1].children.append(elem)
                else:
                    root_elements.append(elem)

                if not is_self_closing:
                    stack.append(elem)
                else:
                    # Self-closing tag
                    elem.end_line = end_line
                    elem.end_col = end_col

        self._elements = root_elements

    def _extract_symbols(self):
        """Extract symbols from parsed elements."""
        for elem in self._elements:
            self._extract_symbols_recursive(elem)

    def _extract_symbols_recursive(self, elem: ParsedElement, parent_name: str = None):
        """Recursively extract symbols from an element and its children."""
        tag = elem.tag

        # q:component
        if tag in ('q:component', 'component'):
            name = elem.attributes.get('name', 'unnamed')
            symbol = Symbol(
                name=name,
                kind=SymbolKind.COMPONENT,
                line=elem.start_line,
                column=elem.start_col,
                end_line=elem.end_line,
                end_column=elem.end_col,
                uri=self.uri,
                type_hint=elem.attributes.get('type', 'pure'),
                description=f"Component: {name}"
            )
            self.symbols.add_symbol(symbol)
            parent_name = name

        # q:function
        elif tag in ('q:function', 'function'):
            name = elem.attributes.get('name', '')
            if name:
                symbol = Symbol(
                    name=name,
                    kind=SymbolKind.FUNCTION,
                    line=elem.start_line,
                    column=elem.start_col,
                    end_line=elem.end_line,
                    end_column=elem.end_col,
                    uri=self.uri,
                    parent=parent_name,
                    type_hint=elem.attributes.get('returnType', 'any'),
                    description=elem.attributes.get('description', f"Function: {name}")
                )
                self.symbols.add_symbol(symbol)

        # q:set (variable definition)
        elif tag in ('q:set', 'set'):
            name = elem.attributes.get('name', '')
            if name:
                symbol = Symbol(
                    name=name,
                    kind=SymbolKind.VARIABLE,
                    line=elem.start_line,
                    column=elem.start_col,
                    end_line=elem.end_line,
                    end_column=elem.end_col,
                    uri=self.uri,
                    parent=parent_name,
                    type_hint=elem.attributes.get('type', 'string'),
                    attributes=elem.attributes
                )
                self.symbols.add_symbol(symbol)

        # q:param
        elif tag in ('q:param', 'param'):
            name = elem.attributes.get('name', '')
            if name:
                symbol = Symbol(
                    name=name,
                    kind=SymbolKind.PARAMETER,
                    line=elem.start_line,
                    column=elem.start_col,
                    end_line=elem.end_line,
                    end_column=elem.end_col,
                    uri=self.uri,
                    parent=parent_name,
                    type_hint=elem.attributes.get('type', 'string')
                )
                self.symbols.add_symbol(symbol)

        # q:query
        elif tag in ('q:query', 'query'):
            name = elem.attributes.get('name', '')
            if name:
                symbol = Symbol(
                    name=name,
                    kind=SymbolKind.QUERY,
                    line=elem.start_line,
                    column=elem.start_col,
                    end_line=elem.end_line,
                    end_column=elem.end_col,
                    uri=self.uri,
                    parent=parent_name,
                    type_hint='query',
                    description=f"Query: {name}"
                )
                self.symbols.add_symbol(symbol)

        # q:action
        elif tag in ('q:action', 'action'):
            name = elem.attributes.get('name', '')
            if name:
                symbol = Symbol(
                    name=name,
                    kind=SymbolKind.ACTION,
                    line=elem.start_line,
                    column=elem.start_col,
                    end_line=elem.end_line,
                    end_column=elem.end_col,
                    uri=self.uri,
                    parent=parent_name,
                    type_hint=elem.attributes.get('method', 'POST'),
                    description=f"Action: {name}"
                )
                self.symbols.add_symbol(symbol)

        # q:import
        elif tag in ('q:import', 'import'):
            component = elem.attributes.get('component', '')
            alias = elem.attributes.get('as', component)
            if component:
                symbol = Symbol(
                    name=alias,
                    kind=SymbolKind.IMPORT,
                    line=elem.start_line,
                    column=elem.start_col,
                    end_line=elem.end_line,
                    end_column=elem.end_col,
                    uri=self.uri,
                    parent=parent_name,
                    type_hint=component,
                    description=f"Import: {component}" + (f" as {alias}" if alias != component else "")
                )
                self.symbols.add_symbol(symbol)

        # q:slot
        elif tag in ('q:slot', 'slot'):
            name = elem.attributes.get('name', 'default')
            symbol = Symbol(
                name=name,
                kind=SymbolKind.SLOT,
                line=elem.start_line,
                column=elem.start_col,
                end_line=elem.end_line,
                end_column=elem.end_col,
                uri=self.uri,
                parent=parent_name,
                description=f"Slot: {name}"
            )
            self.symbols.add_symbol(symbol)

        # q:route
        elif tag in ('q:route', 'route'):
            path = elem.attributes.get('path', '/')
            method = elem.attributes.get('method', 'GET')
            symbol = Symbol(
                name=f"{method} {path}",
                kind=SymbolKind.ROUTE,
                line=elem.start_line,
                column=elem.start_col,
                end_line=elem.end_line,
                end_column=elem.end_col,
                uri=self.uri,
                parent=parent_name,
                type_hint=method,
                description=f"Route: {method} {path}"
            )
            self.symbols.add_symbol(symbol)

        # Extract variable references for databinding
        self._extract_references(elem)

        # Recurse into children
        for child in elem.children:
            self._extract_symbols_recursive(child, parent_name)

    def _extract_references(self, elem: ParsedElement):
        """Extract variable references from databinding expressions."""
        # Pattern for {variable} references
        ref_pattern = re.compile(r'\{([a-zA-Z_][\w.]*)\}')

        # Check all attribute values
        for attr_name, attr_value in elem.attributes.items():
            for match in ref_pattern.finditer(attr_value):
                var_name = match.group(1).split('.')[0]  # Get base variable name
                location = types.Location(
                    uri=self.uri,
                    range=types.Range(
                        start=types.Position(line=elem.start_line, character=0),
                        end=types.Position(line=elem.start_line, character=100)
                    )
                )
                self.symbols.add_reference(var_name, location)

    def get_ast(self) -> Any:
        """Get the parsed AST (if using Quantum parser)."""
        return self._ast

    def get_parse_error(self) -> Optional[str]:
        """Get parse error message if parsing failed."""
        return self._parse_error

    def get_diagnostics(self) -> List[types.Diagnostic]:
        """
        Get diagnostics for this document.

        Returns list of errors, warnings, and hints.
        """
        diagnostics = []

        # Report parse errors
        if self._parse_error:
            diagnostics.append(types.Diagnostic(
                range=types.Range(
                    start=types.Position(line=0, character=0),
                    end=types.Position(line=0, character=100)
                ),
                message=f"Parse error: {self._parse_error}",
                severity=types.DiagnosticSeverity.Error,
                source="quantum-lsp"
            ))
            return diagnostics

        # Validate elements
        for elem in self._elements:
            diagnostics.extend(self._validate_element(elem))

        return diagnostics

    def _validate_element(self, elem: ParsedElement) -> List[types.Diagnostic]:
        """Validate an element and return diagnostics."""
        diagnostics = []

        tag = elem.tag
        tag_info = get_tag_info(tag)

        if tag_info:
            # Check required attributes
            required = get_required_attributes(tag)
            for attr_name in required:
                if attr_name not in elem.attributes:
                    diagnostics.append(types.Diagnostic(
                        range=types.Range(
                            start=types.Position(line=elem.start_line, character=elem.start_col),
                            end=types.Position(line=elem.start_line, character=elem.end_col)
                        ),
                        message=f"Missing required attribute '{attr_name}' on <{tag}>",
                        severity=types.DiagnosticSeverity.Error,
                        source="quantum-lsp"
                    ))

            # Validate attribute values
            for attr_name, attr_value in elem.attributes.items():
                error = validate_attribute_value(tag, attr_name, attr_value)
                if error:
                    diagnostics.append(types.Diagnostic(
                        range=types.Range(
                            start=types.Position(line=elem.start_line, character=elem.start_col),
                            end=types.Position(line=elem.start_line, character=elem.end_col)
                        ),
                        message=error,
                        severity=types.DiagnosticSeverity.Warning,
                        source="quantum-lsp"
                    ))

        elif tag.startswith('q:') or tag.startswith('ui:'):
            # Unknown Quantum tag
            diagnostics.append(types.Diagnostic(
                range=types.Range(
                    start=types.Position(line=elem.start_line, character=elem.start_col),
                    end=types.Position(line=elem.start_line, character=elem.end_col)
                ),
                message=f"Unknown tag <{tag}>",
                severity=types.DiagnosticSeverity.Warning,
                source="quantum-lsp"
            ))

        # Validate children recursively
        for child in elem.children:
            diagnostics.extend(self._validate_element(child))

        return diagnostics

    def get_context_at_position(self, line: int, character: int) -> Dict[str, Any]:
        """
        Determine the context at a given position.

        Returns information about:
        - Whether we're inside a tag, attribute, value, or content
        - The current tag name
        - The current attribute name (if in attribute context)
        - Preceding characters for completion filtering
        """
        if line >= len(self.lines):
            return {"context": "content", "tag": None}

        line_text = self.lines[line]
        prefix = line_text[:character]

        # Default context
        context = {
            "context": "content",
            "tag": None,
            "attribute": None,
            "prefix": "",
            "inside_databinding": False,
        }

        # Check if we're inside a databinding expression
        # Count { and } before cursor
        open_braces = prefix.count('{')
        close_braces = prefix.count('}')
        if open_braces > close_braces:
            context["inside_databinding"] = True
            # Find the start of databinding
            last_brace = prefix.rfind('{')
            context["prefix"] = prefix[last_brace + 1:]
            context["context"] = "databinding"
            return context

        # Check if we're in a tag
        # Look for < before cursor without matching >
        tag_start = prefix.rfind('<')
        if tag_start != -1:
            tag_text = prefix[tag_start:]

            # Check if tag is closed
            if '>' not in tag_text:
                context["context"] = "tag"

                # Extract tag name
                tag_match = re.match(r'</?([a-zA-Z_][\w:-]*)', tag_text)
                if tag_match:
                    context["tag"] = tag_match.group(1)

                # Check if we're typing the tag name
                if re.match(r'^<[a-zA-Z_][\w:-]*$', tag_text):
                    context["context"] = "tag_name"
                    context["prefix"] = tag_text[1:]  # Remove <
                    return context

                # Check if we're in an attribute value
                attr_value_match = re.search(r'(\w+)\s*=\s*["\']([^"\']*)?$', tag_text)
                if attr_value_match:
                    context["context"] = "attribute_value"
                    context["attribute"] = attr_value_match.group(1)
                    context["prefix"] = attr_value_match.group(2) or ""
                    return context

                # Check if we're typing an attribute name
                if tag_text.endswith(' ') or re.search(r'\s+\w*$', tag_text):
                    context["context"] = "attribute_name"
                    attr_match = re.search(r'\s+(\w*)$', tag_text)
                    context["prefix"] = attr_match.group(1) if attr_match else ""
                    return context

        return context

    def get_element_at_position(self, line: int, character: int) -> Optional[ParsedElement]:
        """Find the element at a given position."""
        def find_in_elements(elements: List[ParsedElement]) -> Optional[ParsedElement]:
            for elem in elements:
                if (elem.start_line <= line <= elem.end_line):
                    # Check children first (more specific)
                    child_result = find_in_elements(elem.children)
                    if child_result:
                        return child_result
                    return elem
            return None

        return find_in_elements(self._elements)

    def get_word_at_position(self, line: int, character: int) -> Tuple[str, int, int]:
        """
        Get the word at a position.

        Returns (word, start_col, end_col).
        """
        if line >= len(self.lines):
            return ("", character, character)

        line_text = self.lines[line]
        if character >= len(line_text):
            return ("", character, character)

        # Find word boundaries
        word_pattern = re.compile(r'[\w:-]+')

        for match in word_pattern.finditer(line_text):
            if match.start() <= character <= match.end():
                return (match.group(), match.start(), match.end())

        return ("", character, character)

    def update(self, text: str, version: Optional[int] = None):
        """Update document content and reparse."""
        self.text = text
        self.version = version
        self.lines = text.split('\n')
        self._parse()
