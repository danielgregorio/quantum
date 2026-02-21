"""
Parser Registry - Central dispatch for tag parsing

Replaces the large if-elif chain in parser.py with a tag-based lookup.
Parsers register themselves for specific tag names, and the registry
dispatches parsing to the correct parser.
"""

from typing import Dict, Optional, List, TYPE_CHECKING
from xml.etree import ElementTree as ET
import logging

if TYPE_CHECKING:
    from core.parsers.base import BaseTagParser
    from core.ast_nodes import QuantumNode

logger = logging.getLogger(__name__)


class ParserNotFoundError(Exception):
    """Raised when no parser is registered for a tag"""
    pass


class ParserRegistry:
    """
    Registry for tag parsers.

    Maps XML tag names to their parsers and dispatches parsing.

    Example:
        registry = ParserRegistry()
        registry.register(LoopParser(main_parser))
        registry.register(IfParser(main_parser))

        # Later, parse any element
        node = registry.parse(element, 'loop')
    """

    def __init__(self):
        """Initialize empty registry"""
        self._parsers: Dict[str, 'BaseTagParser'] = {}
        self._html_parser: Optional['BaseTagParser'] = None
        self._component_call_parser: Optional['BaseTagParser'] = None

    def register(self, parser: 'BaseTagParser') -> 'ParserRegistry':
        """
        Register a parser for its handled tags.

        Args:
            parser: Parser instance to register

        Returns:
            Self for chaining
        """
        for tag_name in parser.tag_names:
            if tag_name in self._parsers:
                logger.warning(
                    f"Overwriting parser for '{tag_name}': "
                    f"{self._parsers[tag_name].__class__.__name__} -> "
                    f"{parser.__class__.__name__}"
                )
            self._parsers[tag_name] = parser
            logger.debug(f"Registered {parser.__class__.__name__} for '{tag_name}'")

        return self

    def register_all(self, parsers: List['BaseTagParser']) -> 'ParserRegistry':
        """
        Register multiple parsers at once.

        Args:
            parsers: List of parser instances

        Returns:
            Self for chaining
        """
        for parser in parsers:
            self.register(parser)
        return self

    def register_html_parser(self, parser: 'BaseTagParser') -> 'ParserRegistry':
        """
        Register the HTML element parser.

        Args:
            parser: HTML parser instance

        Returns:
            Self for chaining
        """
        self._html_parser = parser
        logger.debug(f"Registered HTML parser: {parser.__class__.__name__}")
        return self

    def register_component_call_parser(self, parser: 'BaseTagParser') -> 'ParserRegistry':
        """
        Register the component call parser (for uppercase tags).

        Args:
            parser: Component call parser instance

        Returns:
            Self for chaining
        """
        self._component_call_parser = parser
        logger.debug(f"Registered component call parser: {parser.__class__.__name__}")
        return self

    def get_parser(self, tag_name: str) -> Optional['BaseTagParser']:
        """
        Get the parser for a tag name.

        Args:
            tag_name: Tag name (without q: prefix)

        Returns:
            Parser instance or None if not found
        """
        return self._parsers.get(tag_name)

    def has_parser(self, tag_name: str) -> bool:
        """
        Check if a parser is registered for a tag.

        Args:
            tag_name: Tag name

        Returns:
            True if parser exists
        """
        return tag_name in self._parsers

    def parse(self, element: ET.Element, tag_name: str) -> Optional['QuantumNode']:
        """
        Parse an element using its registered parser.

        Args:
            element: XML element to parse
            tag_name: Tag name (without q: prefix)

        Returns:
            AST node or None

        Raises:
            ParserNotFoundError: If no parser is registered for the tag
        """
        parser = self._parsers.get(tag_name)

        if parser is not None:
            return parser.parse(element)

        return None

    def parse_html(self, element: ET.Element) -> Optional['QuantumNode']:
        """
        Parse an HTML element.

        Args:
            element: HTML element to parse

        Returns:
            AST node or None
        """
        if self._html_parser is not None:
            return self._html_parser.parse(element)
        return None

    def parse_component_call(self, element: ET.Element) -> Optional['QuantumNode']:
        """
        Parse a component call (uppercase tag).

        Args:
            element: Component call element

        Returns:
            AST node or None
        """
        if self._component_call_parser is not None:
            return self._component_call_parser.parse(element)
        return None

    def is_uppercase(self, tag_name: str) -> bool:
        """
        Check if tag is a component call (uppercase first letter).

        Args:
            tag_name: Tag name

        Returns:
            True if uppercase
        """
        return bool(tag_name and tag_name[0].isupper())

    @property
    def registered_tags(self) -> List[str]:
        """Get list of all registered tag names"""
        return list(self._parsers.keys())

    @property
    def parser_count(self) -> int:
        """Get number of registered parsers (unique)"""
        return len(set(self._parsers.values()))

    def __repr__(self) -> str:
        tags = list(self._parsers.keys())
        return f"ParserRegistry({len(tags)} tags: {tags[:5]}{'...' if len(tags) > 5 else ''})"
