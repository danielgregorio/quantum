"""
Knowledge Parser - Parse q:knowledge statements

Handles knowledge base configuration for RAG.
"""

from typing import List
from xml.etree import ElementTree as ET
from core.parsers.base import BaseTagParser, ParserError
from core.features.knowledge_base.src.ast_node import KnowledgeNode, KnowledgeSourceNode


class KnowledgeParser(BaseTagParser):
    """
    Parser for q:knowledge statements.

    Supports:
    - Multiple source types
    - Embedding configuration
    - Persistence options
    """

    @property
    def tag_names(self) -> List[str]:
        return ['knowledge']

    def parse(self, element: ET.Element) -> KnowledgeNode:
        """
        Parse q:knowledge statement.

        Args:
            element: XML element for q:knowledge

        Returns:
            KnowledgeNode AST node
        """
        name = self.get_attr(element, 'name')

        if not name:
            raise ParserError("Knowledge requires 'name' attribute")

        knowledge_node = KnowledgeNode(
            name=name,
            model=self.get_attr(element, 'model'),
            embed_model=self.get_attr(element, 'embedModel', 'nomic-embed-text'),
            chunk_size=self.get_int_attr(element, 'chunkSize', 500),
            chunk_overlap=self.get_int_attr(element, 'chunkOverlap', 50),
            persist=self.get_bool_attr(element, 'persist', False),
            persist_path=self.get_attr(element, 'persistPath'),
            rebuild=self.get_bool_attr(element, 'rebuild', False)
        )

        # Parse sources
        for child in element:
            child_type = self.get_element_name(child)

            if child_type == 'source':
                source = self._parse_source(child)
                knowledge_node.add_source(source)

        return knowledge_node

    def _parse_source(self, element: ET.Element) -> KnowledgeSourceNode:
        """Parse q:source within q:knowledge."""
        source_type = self.get_attr(element, 'type', 'text')

        source = KnowledgeSourceNode(
            source_type=source_type,
            path=self.get_attr(element, 'path'),
            pattern=self.get_attr(element, 'pattern'),
            url=self.get_attr(element, 'url'),
            datasource=self.get_attr(element, 'datasource'),
            chunk_size=self.get_int_attr(element, 'chunkSize', 0) or None,
            chunk_overlap=self.get_int_attr(element, 'chunkOverlap', 0) or None
        )

        # Get content for text source
        if source_type == 'text':
            source.content = self.get_text(element)
        elif source_type == 'query':
            source.sql = self.get_text(element)

        return source
