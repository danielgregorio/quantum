"""
HTML Parser - Parse HTML elements

Handles parsing of standard HTML elements within Quantum components.
"""

from typing import List, Optional
from xml.etree import ElementTree as ET
from core.parsers.base import BaseTagParser
from core.ast_nodes import HTMLNode, TextNode, HTML_VOID_ELEMENTS


class HTMLParser(BaseTagParser):
    """
    Parser for HTML elements.

    Handles standard HTML tags like div, span, p, a, etc.
    This parser is used as a fallback for elements that aren't
    Quantum-specific tags.
    """

    # Common HTML tags (not exhaustive - uses detection logic)
    HTML_TAGS = {
        'div', 'span', 'p', 'a', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'table', 'tr', 'td', 'th', 'thead', 'tbody',
        'form', 'input', 'button', 'select', 'option', 'textarea', 'label',
        'img', 'video', 'audio', 'source', 'canvas', 'svg',
        'header', 'footer', 'nav', 'main', 'section', 'article', 'aside',
        'br', 'hr', 'pre', 'code', 'blockquote', 'em', 'strong', 'b', 'i',
        'script', 'style', 'link', 'meta', 'head', 'body', 'html',
    }

    @property
    def tag_names(self) -> List[str]:
        """HTML parser handles all HTML tags."""
        return list(self.HTML_TAGS)

    def parse(self, element: ET.Element) -> HTMLNode:
        """
        Parse HTML element.

        Args:
            element: XML element representing HTML tag

        Returns:
            HTMLNode AST node
        """
        tag_name = self._get_local_name(element)

        # Get attributes
        attributes = dict(element.attrib)

        # Check if void element
        is_void = tag_name.lower() in HTML_VOID_ELEMENTS

        # Create HTML node
        html_node = HTMLNode(tag_name, attributes)

        # Parse children if not void element
        if not is_void:
            html_node.children = self._parse_children(element)

        return html_node

    def _get_local_name(self, element: ET.Element) -> str:
        """Extract local name from element tag."""
        tag = element.tag
        if '}' in tag:
            return tag.split('}')[1]
        if ':' in tag:
            return tag.split(':')[1]
        return tag

    def _parse_children(self, element: ET.Element) -> List:
        """Parse child elements and text."""
        children = []

        # Add leading text if present
        if element.text and element.text.strip():
            children.append(TextNode(element.text))

        # Parse child elements
        for child in element:
            # Use main parser to handle child
            child_node = self.parse_statement(child)
            if child_node:
                children.append(child_node)

            # Add tail text after child
            if child.tail and child.tail.strip():
                children.append(TextNode(child.tail))

        return children

    def can_parse(self, tag_name: str) -> bool:
        """
        Check if this parser can handle the tag.

        Uses heuristics to detect HTML elements:
        1. Known HTML tags
        2. Lowercase tags (not Quantum q: or component PascalCase)
        """
        if not tag_name:
            return False

        # Lowercase and in known tags
        lower_tag = tag_name.lower()
        if lower_tag in self.HTML_TAGS:
            return True

        # Lowercase first letter (not a component)
        if tag_name[0].islower():
            return True

        return False
