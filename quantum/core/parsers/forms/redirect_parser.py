"""
Redirect Parser - Parse q:redirect statements
"""

from typing import List
from xml.etree import ElementTree as ET
from quantum.core.parsers.base import BaseTagParser
from quantum.core.ast_nodes import RedirectNode


class RedirectParser(BaseTagParser):
    """
    Parser for q:redirect statements.

    Examples:
        <q:redirect url="/thank-you" />
        <q:redirect url="/users/{userId}" />
        <q:redirect url="/products" flash="Product created!" />
        <q:redirect url="/error" status="500" flash="Error occurred" />
    """

    @property
    def tag_names(self) -> List[str]:
        return ['redirect']

    def parse(self, element: ET.Element) -> RedirectNode:
        """Parse q:redirect element"""
        # Accept to= as an alias for url= (both appear across examples)
        url = element.get('url') or element.get('to', '')
        flash = element.get('flash')
        status = int(element.get('status', '302'))

        return RedirectNode(url, flash, status)
