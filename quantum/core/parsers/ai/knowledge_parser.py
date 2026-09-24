"""
Knowledge Parser - Parse q:knowledge statements

Handles knowledge base configuration for RAG.
"""

from typing import List
from xml.etree import ElementTree as ET
from quantum.core.parsers.base import BaseTagParser, ParserError
from quantum.core.features.knowledge_base.src.ast_node import KnowledgeNode, KnowledgeSourceNode


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
        if element.get('model') is not None:
            # IA-2: only the removed q:query mode="rag" read it (IA-3).
            raise ParserError(f'<q:knowledge name="{name}"> model= is not supported: a knowledge base only embeds its sources (embedModel=). The model that answers is chosen on q:llm: <q:llm model="…" knowledge="{name}"> (IA-3, IA-6)')

        knowledge_node = KnowledgeNode(
            name=name,
            embed_model=self.get_attr(element, 'embedModel', 'nomic-embed-text'),
            chunk_size=self.get_int_attr(element, 'chunkSize', 500),
            chunk_overlap=self.get_int_attr(element, 'chunkOverlap', 50),
            # Persist by default: re-embedding an unchanged corpus on every
            # boot costs minutes of API calls and buys nothing. Opt out with
            # persist="false" for throwaway/in-memory bases.
            persist=self.get_bool_attr(element, 'persist', True),
            persist_path=self.get_attr(element, 'persistPath', './.quantum/knowledge'),
            rebuild=self.get_bool_attr(element, 'rebuild', False)
        )
        # IA-5: a base that cannot be built stops the page unless the page handles it.
        knowledge_node.on_error = self.get_attr(element, 'onerror', 'fail')
        if knowledge_node.on_error not in ('fail', 'continue'):
            raise ParserError(f'<q:knowledge name="{name}"> onerror must be "fail" or "continue", '
                              f'not "{knowledge_node.on_error}"')

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
        # IA-8: type="url" was accepted and read nothing (a log line said "not
        # yet implemented"); an unknown type read nothing at all.
        if source_type not in ('text', 'file', 'directory', 'query'):
            raise ParserError(f'<q:source type="{source_type}">: use text, file, directory or query'
                              + (' (url is not supported)' if source_type == 'url' else ''))

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
