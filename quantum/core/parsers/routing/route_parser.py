"""
Route Parser - Parse q:route statements
"""

from typing import List
from xml.etree import ElementTree as ET
from quantum.core.parsers.base import BaseTagParser
from quantum.core.ast_nodes import QuantumRoute


class RouteParser(BaseTagParser):
    """
    Parser for q:route statements.

    Examples:
        <q:route path="/users" method="GET" />
        <q:route path="/api/products/{id}" method="POST">
            <q:return name="product" type="object" />
        </q:route>
    """

    @property
    def tag_names(self) -> List[str]:
        return ['route']

    def parse(self, element: ET.Element) -> QuantumRoute:
        """Parse q:route element"""
        path = element.get('path', '/')
        method = element.get('method', 'GET').upper()

        route = QuantumRoute(path, method)

        # Parse q:return inside the route
        for child in element:
            child_type = self._get_element_name(child)
            if child_type == 'return':
                return_node = self.parse_child(child)
                if return_node:
                    route.returns.append(return_node)

        return route
