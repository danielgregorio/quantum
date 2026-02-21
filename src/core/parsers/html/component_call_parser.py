"""
Component Call Parser - Parse component invocations

Handles parsing of component calls (PascalCase tags).
"""

from typing import List, Optional, Dict, Any
from xml.etree import ElementTree as ET
from core.parsers.base import BaseTagParser
from core.ast_nodes import ComponentCallNode, TextNode


class ComponentCallParser(BaseTagParser):
    """
    Parser for component call elements.

    Component calls are identified by PascalCase naming convention:
    - <MyComponent /> -> calls imported component "MyComponent"
    - <UserCard name="John" /> -> calls "UserCard" with props

    These are similar to React/Vue component usage.
    """

    @property
    def tag_names(self) -> List[str]:
        """
        Component call parser doesn't register for specific tags.
        Instead, it's called when a PascalCase tag is detected.
        """
        return []

    def parse(self, element: ET.Element) -> ComponentCallNode:
        """
        Parse component call element.

        Args:
            element: XML element representing component call

        Returns:
            ComponentCallNode AST node
        """
        component_name = self._get_local_name(element)

        # Get props from attributes
        props = self._parse_props(element)

        # Create component call node
        call_node = ComponentCallNode(component_name, props)

        # Parse children (slot content)
        call_node.children = self._parse_children(element)

        return call_node

    def _get_local_name(self, element: ET.Element) -> str:
        """Extract local name from element tag."""
        tag = element.tag
        if '}' in tag:
            return tag.split('}')[1]
        if ':' in tag:
            return tag.split(':')[1]
        return tag

    def _parse_props(self, element: ET.Element) -> Dict[str, Any]:
        """
        Parse element attributes as component props.

        Handles:
        - Simple string values: name="John"
        - Databinding expressions: user="{currentUser}"
        - Boolean shorthand: disabled (treated as disabled="true")
        """
        props = {}

        for key, value in element.attrib.items():
            # Skip namespace declarations
            if key.startswith('xmlns'):
                continue

            # Handle namespaced attributes
            if '}' in key:
                key = key.split('}')[1]

            props[key] = value

        return props

    def _parse_children(self, element: ET.Element) -> List:
        """Parse child elements as slot content."""
        children = []

        # Add leading text if present
        if element.text and element.text.strip():
            children.append(TextNode(element.text))

        # Parse child elements
        for child in element:
            child_node = self.parse_statement(child)
            if child_node:
                children.append(child_node)

            # Add tail text after child
            if child.tail and child.tail.strip():
                children.append(TextNode(child.tail))

        return children

    @staticmethod
    def is_component_call(tag_name: str) -> bool:
        """
        Check if tag name represents a component call.

        Components use PascalCase naming:
        - MyComponent -> True
        - UserCard -> True
        - div -> False
        - myComponent -> False
        """
        if not tag_name:
            return False

        # Must start with uppercase letter
        if not tag_name[0].isupper():
            return False

        # Should not be all uppercase (likely a constant/builtin)
        if tag_name.isupper():
            return False

        return True
