"""
DispatchEvent Parser - Parse q:dispatchEvent statements
"""

from typing import List
from xml.etree import ElementTree as ET
from quantum.core.parsers.base import BaseTagParser
from quantum.core.ast_nodes import DispatchEventNode


class DispatchEventParser(BaseTagParser):
    """
    Parser for q:dispatchEvent statements.

    Examples:
        <q:dispatchEvent event="userCreated" data="{userData}" />
        <q:dispatchEvent event="orderPlaced" queue="orders" priority="high" />
    """

    @property
    def tag_names(self) -> List[str]:
        return ['dispatchEvent']

    def parse(self, element: ET.Element) -> DispatchEventNode:
        """Parse q:dispatchEvent element"""
        event = element.get('event')

        if not event:
            from quantum.core.parser import QuantumParseError
            raise QuantumParseError("dispatchEvent requires 'event' attribute")

        dispatch_node = DispatchEventNode(event)

        # Optional attributes
        dispatch_node.data = element.get('data')
        dispatch_node.queue = element.get('queue')
        dispatch_node.exchange = element.get('exchange')
        dispatch_node.routing_key = element.get('routingKey')
        dispatch_node.priority = element.get('priority', 'normal')
        dispatch_node.delay = element.get('delay')
        dispatch_node.ttl = element.get('ttl')
        dispatch_node.metadata = element.get('metadata')

        return dispatch_node
