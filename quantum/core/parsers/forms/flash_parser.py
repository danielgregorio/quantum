"""
Flash Parser - Parse q:flash statements for flash messages
"""

from typing import List
from xml.etree import ElementTree as ET
from quantum.core.parsers.base import BaseTagParser
from quantum.core.ast_nodes import FlashNode


class FlashParser(BaseTagParser):
    """
    Parser for q:flash statements.

    Examples:
        <q:flash type="success" message="User created!" />
        <q:flash type="error" message="{errorMessage}" />
        <q:flash type="warning">Please verify your email</q:flash>
    """

    @property
    def tag_names(self) -> List[str]:
        return ['flash']

    def parse(self, element: ET.Element) -> FlashNode:
        """Parse q:flash element"""
        flash_type = element.get('type', 'info')
        message = element.get('message')

        # If message not in attribute, check text content
        if not message and element.text:
            message = element.text.strip()

        return FlashNode(message, flash_type)
