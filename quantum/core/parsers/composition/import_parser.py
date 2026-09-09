"""
Import Parser - Parse q:import statements
"""

from typing import List
from xml.etree import ElementTree as ET
from quantum.core.parsers.base import BaseTagParser
from quantum.core.ast_nodes import ImportNode


class ImportParser(BaseTagParser):
    """
    Parser for q:import statements.

    Examples:
        <q:import component="Header" />
        <q:import component="Button" from="./ui" />
        <q:import component="AdminLayout" as="Layout" />

    Game Engine Imports:
        <q:import behavior="PlayerBehavior" from="./behaviors" />
        <q:import prefab="KoopaGreen" from="./prefabs" />
        <q:import tilemap="yi1" from="./levels" />
    """

    @property
    def tag_names(self) -> List[str]:
        return ['import']

    def parse(self, element: ET.Element) -> ImportNode:
        """Parse q:import element"""
        component = element.get('component')
        behavior = element.get('behavior')
        prefab = element.get('prefab')
        tilemap = element.get('tilemap')
        from_path = element.get('from')
        alias = element.get('as')

        if not component and not behavior and not prefab and not tilemap:
            from quantum.core.parser import QuantumParseError
            raise QuantumParseError("q:import requires one of 'component', 'behavior', 'prefab', or 'tilemap' attribute")

        return ImportNode(
            component=component,
            from_path=from_path,
            alias=alias,
            behavior=behavior,
            prefab=prefab,
            tilemap=tilemap
        )
