"""
Persist Parser - Parse q:persist statements
"""

from typing import List
from xml.etree import ElementTree as ET
from quantum.core.parsers.base import BaseTagParser
from quantum.core.ast_nodes import PersistNode


class PersistParser(BaseTagParser):
    """
    Parser for q:persist statements for explicit persistence configuration.

    Examples:
        <q:persist scope="local" prefix="myapp_">
            <q:var name="theme" />
            <q:var name="locale" />
        </q:persist>

        <q:persist scope="sync" key="user_prefs" encrypt="true">
            <q:var name="darkMode" />
            <q:var name="fontSize" />
        </q:persist>
    """

    @property
    def tag_names(self) -> List[str]:
        return ['persist']

    def parse(self, element: ET.Element) -> PersistNode:
        """Parse q:persist element"""
        scope = element.get('scope', 'local')
        prefix = element.get('prefix')
        key = element.get('key')
        encrypt = element.get('encrypt', 'false').lower() == 'true'
        storage = element.get('storage')

        ttl = None
        ttl_attr = element.get('ttl')
        if ttl_attr:
            try:
                ttl = int(ttl_attr)
            except ValueError:
                pass

        persist_node = PersistNode(
            scope=scope,
            prefix=prefix,
            key=key,
            encrypt=encrypt,
            ttl=ttl,
            storage=storage
        )

        # Parse q:var children
        for child in element:
            child_type = self._get_element_name(child)
            if child_type == 'var':
                var_name = child.get('name')
                if var_name:
                    persist_node.add_variable(var_name)

        return persist_node
