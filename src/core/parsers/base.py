"""
Base Tag Parser - Abstract base class for all tag parsers

All parsers inherit from BaseTagParser and implement the parse() method.
The ParserRegistry uses the 'tag_names' property to dispatch parsing to the correct parser.
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional, TYPE_CHECKING
from xml.etree import ElementTree as ET

if TYPE_CHECKING:
    from core.ast_nodes import QuantumNode


class ParserError(Exception):
    """Base exception for parser errors"""
    pass


class BaseTagParser(ABC):
    """
    Abstract base class for tag-specific parsers.

    Each parser handles one or more XML tags and implements
    the parse() method to convert them to AST nodes.

    Example:
        class LoopParser(BaseTagParser):
            @property
            def tag_names(self) -> List[str]:
                return ['loop']

            def parse(self, element: ET.Element) -> LoopNode:
                # Parse loop element
                pass
    """

    def __init__(self, main_parser: 'QuantumParser'):
        """
        Initialize parser with reference to main parser.

        Args:
            main_parser: The QuantumParser instance (provides helpers and registry)
        """
        self._parser = main_parser

    @property
    def parser(self) -> 'QuantumParser':
        """Access to the main parser"""
        return self._parser

    @property
    @abstractmethod
    def tag_names(self) -> List[str]:
        """
        List of tag names this parser handles (without q: prefix).

        Returns:
            List of tag names (e.g., ['loop', 'for', 'while'])
        """
        pass

    @abstractmethod
    def parse(self, element: ET.Element) -> 'QuantumNode':
        """
        Parse the element and return AST node.

        Args:
            element: XML element to parse

        Returns:
            AST node representing the element
        """
        pass

    # ==========================================================================
    # Helper methods - Common utilities available to all parsers
    # ==========================================================================

    def get_element_name(self, element: ET.Element) -> str:
        """
        Get element name without namespace prefix.

        Args:
            element: XML element

        Returns:
            Tag name without namespace
        """
        return self._parser._get_element_name(element)

    def find_element(self, parent: ET.Element, tag: str) -> Optional[ET.Element]:
        """
        Find a child element by tag name.

        Args:
            parent: Parent element
            tag: Tag name to find

        Returns:
            Element or None
        """
        return self._parser._find_element(parent, tag)

    def find_all_elements(self, parent: ET.Element, tag: str) -> List[ET.Element]:
        """
        Find all child elements by tag name.

        Args:
            parent: Parent element
            tag: Tag name to find

        Returns:
            List of elements
        """
        return self._parser._find_all_elements(parent, tag)

    def parse_statement(self, element: ET.Element) -> Optional['QuantumNode']:
        """
        Parse a child statement using the registry.

        Args:
            element: Child element to parse

        Returns:
            AST node or None
        """
        return self._parser._parse_statement(element)

    def parse_statements(self, parent: ET.Element) -> List['QuantumNode']:
        """
        Parse all direct children as statements.

        Args:
            parent: Parent element

        Returns:
            List of AST nodes
        """
        statements = []
        for child in parent:
            node = self.parse_statement(child)
            if node is not None:
                statements.append(node)
        return statements

    def get_attr(self, element: ET.Element, name: str, default: str = None) -> Optional[str]:
        """
        Get element attribute with optional default.

        Args:
            element: XML element
            name: Attribute name
            default: Default value

        Returns:
            Attribute value or default
        """
        return element.get(name, default)

    def get_bool_attr(self, element: ET.Element, name: str, default: bool = False) -> bool:
        """
        Get boolean attribute.

        Args:
            element: XML element
            name: Attribute name
            default: Default value

        Returns:
            Boolean value
        """
        value = element.get(name, '').lower()
        if value in ('true', '1', 'yes'):
            return True
        if value in ('false', '0', 'no'):
            return False
        return default

    def get_int_attr(self, element: ET.Element, name: str, default: int = 0) -> int:
        """
        Get integer attribute.

        Args:
            element: XML element
            name: Attribute name
            default: Default value

        Returns:
            Integer value
        """
        try:
            return int(element.get(name, default))
        except (ValueError, TypeError):
            return default

    def get_text(self, element: ET.Element) -> str:
        """
        Get element text content.

        Args:
            element: XML element

        Returns:
            Text content (empty string if None)
        """
        return element.text or ''

    def require_attr(self, element: ET.Element, name: str) -> str:
        """
        Get required attribute, raise error if missing.

        Args:
            element: XML element
            name: Attribute name

        Returns:
            Attribute value

        Raises:
            ParserError: If attribute is missing
        """
        value = element.get(name)
        if value is None:
            tag = self.get_element_name(element)
            raise ParserError(f"<q:{tag}> requires '{name}' attribute")
        return value

    def is_html_element(self, element: ET.Element) -> bool:
        """
        Check if element is an HTML element.

        Args:
            element: XML element

        Returns:
            True if HTML element
        """
        return self._parser._is_html_element(element)
