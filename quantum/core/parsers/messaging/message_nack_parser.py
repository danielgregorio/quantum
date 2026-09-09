"""
MessageNack Parser - Parse q:messageNack statements
"""

from typing import List
from xml.etree import ElementTree as ET
from quantum.core.parsers.base import BaseTagParser
from quantum.core.ast_nodes import MessageNackNode


class MessageNackParser(BaseTagParser):
    """
    Parser for q:messageNack statements for negative acknowledgment.

    Examples:
        <!-- Reject and requeue -->
        <q:messageNack requeue="true" />

        <!-- Reject without requeue (send to DLQ) -->
        <q:messageNack requeue="false" />
    """

    @property
    def tag_names(self) -> List[str]:
        return ['messageNack']

    def parse(self, element: ET.Element) -> MessageNackNode:
        """Parse q:messageNack element"""
        requeue = element.get('requeue', 'true').lower() == 'true'
        return MessageNackNode(requeue=requeue)
