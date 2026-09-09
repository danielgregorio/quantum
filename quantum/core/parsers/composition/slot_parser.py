"""
Slot Parser - Parse q:slot statements
"""

from typing import List
from xml.etree import ElementTree as ET
from quantum.core.parsers.base import BaseTagParser
from quantum.core.ast_nodes import SlotNode, TextNode


class SlotParser(BaseTagParser):
    """
    Parser for q:slot statements.

    Examples:
        <q:slot />  <!-- Default slot -->
        <q:slot name="header" />
        <q:slot name="footer">
            <p>Default footer content</p>
        </q:slot>
    """

    @property
    def tag_names(self) -> List[str]:
        return ['slot']

    def parse(self, element: ET.Element) -> SlotNode:
        """Parse q:slot element"""
        name = element.get('name', 'default')

        # Parse default content (children of slot)
        default_content = []

        if element.text and element.text.strip():
            default_content.append(TextNode(element.text))

        for child in element:
            child_node = self.parse_child(child)
            if child_node:
                default_content.append(child_node)

            if child.tail and child.tail.strip():
                default_content.append(TextNode(child.tail))

        return SlotNode(
            name=name,
            default_content=default_content
        )
