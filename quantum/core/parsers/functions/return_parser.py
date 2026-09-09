"""
Return Parser - Parse q:return statements
"""

from typing import List
from xml.etree import ElementTree as ET
from quantum.core.parsers.base import BaseTagParser
from quantum.core.ast_nodes import QuantumReturn


class ReturnParser(BaseTagParser):
    """
    Parser for q:return statements.

    Examples:
        <q:return name="result" type="string" value="{computedValue}" />
        <q:return type="integer" value="42" />
    """

    @property
    def tag_names(self) -> List[str]:
        return ['return']

    def parse(self, element: ET.Element) -> QuantumReturn:
        """Parse q:return element"""
        return QuantumReturn(
            name=element.get('name'),
            type=element.get('type', 'string'),
            value=element.get('value', ''),
            description=element.get('description')
        )
