"""
MessageAck Parser - Parse q:messageAck statements
"""

from typing import List
from xml.etree import ElementTree as ET
from quantum.core.parsers.base import BaseTagParser
from quantum.core.ast_nodes import MessageAckNode


class MessageAckParser(BaseTagParser):
    """
    Parser for q:messageAck statements for acknowledging messages.

    Example:
        <q:subscribe name="worker" queue="tasks" ack="manual">
            <q:onMessage>
                <q:set name="processed" value="true" />
                <q:messageAck />
            </q:onMessage>
        </q:subscribe>
    """

    @property
    def tag_names(self) -> List[str]:
        return ['messageAck']

    def parse(self, element: ET.Element) -> MessageAckNode:
        """Parse q:messageAck element"""
        return MessageAckNode()
