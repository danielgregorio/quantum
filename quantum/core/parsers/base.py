"""
Base Tag Parser - Abstract base class for all tag parsers

All parsers inherit from BaseTagParser and implement the parse() method.
The ParserRegistry uses the 'tag_names' property to dispatch parsing to the correct parser.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, TYPE_CHECKING
from xml.etree import ElementTree as ET

if TYPE_CHECKING:
    from quantum.core.ast_nodes import QuantumNode, QuantumParam
    from quantum.core.parser import QuantumParser


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
        from quantum.core.features.conditionals.src.ast_node import IfNode

        statements = []
        for child in parent:
            name = self.get_element_name(child)

            # `<q:else>` / `<q:elseif>` as a SIBLING of `<q:if>`.
            #
            # The form that worked was only the NESTED one (the else inside the
            # if); the sibling — `</q:if>` and then `<q:else>` — had no parser
            # registered (IfParser.tag_names = ['if']), fell into the fallback
            # and was DROPPED without a word. The documentation taught the
            # sibling form in dozens of examples (the quick-start's step 3
            # among them) and 7 shipped .q files used it, so the else simply
            # did not happen and nobody was told.
            #
            # Now an else/elseif that follows a q:if is attached to it — both
            # forms mean the same thing. An else/elseif WITHOUT an if before it
            # is a real error, and it is now said out loud.
            if name in ('else', 'elseif'):
                previous = statements[-1] if statements else None
                if isinstance(previous, IfNode):
                    self._attach_else_branch(previous, name, child)
                    continue
                from quantum.core.parser import QuantumParseError
                raise QuantumParseError(
                    f"<q:{name}> has no matching <q:if> before it. "
                    f"Put it inside the if, or right after it: "
                    f"<q:if ...>...</q:if> <q:{name}>...</q:{name}>"
                )

            node = self.parse_statement(child)
            if node is not None:
                statements.append(node)
        return statements

    def _attach_else_branch(self, if_node, kind: str, element: 'ET.Element'):
        """Attaches a SIBLING else/elseif to the previous IfNode — the same
        result as the nested form, which IfParser builds with these same methods."""
        if kind == 'elseif':
            condition = self.get_attr(element, 'condition', '')
            body = []
            for child in element:
                stmt = self.parse_statement(child)
                if stmt:
                    body.append(stmt)
            if_node.add_elseif_block(condition, body)
        else:
            for child in element:
                stmt = self.parse_statement(child)
                if stmt:
                    if_node.add_else_statement(stmt)

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

    def parse_param(self, element: ET.Element) -> 'QuantumParam':
        """
        Parse a q:param element.

        Args:
            element: Param element

        Returns:
            QuantumParam node
        """
        return self._parser._parse_param(element)

    def parse_child(self, element: ET.Element) -> Optional['QuantumNode']:
        """
        Alias for parse_statement. Parse a child element using the registry.

        Args:
            element: Child element to parse

        Returns:
            AST node or None
        """
        return self.parse_statement(element)

    def _get_element_name(self, element: ET.Element) -> str:
        """
        Alias for get_element_name. Get element name without namespace prefix.

        Args:
            element: XML element

        Returns:
            Tag name without namespace
        """
        return self.get_element_name(element)
