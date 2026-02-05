"""Parser for q:knowledge and q:source elements."""

from xml.etree import ElementTree as ET
from .ast_node import KnowledgeNode, KnowledgeSourceNode


def parse_knowledge(element: ET.Element) -> KnowledgeNode:
    """
    Parse <q:knowledge> element into KnowledgeNode.

    Args:
        element: XML element representing <q:knowledge>

    Returns:
        KnowledgeNode with parsed sources
    """
    name = element.get('name', '')
    node = KnowledgeNode(name=name)

    # Parse attributes
    node.model = element.get('model')
    node.embed_model = element.get('embedModel', 'nomic-embed-text')

    chunk_size = element.get('chunkSize')
    if chunk_size:
        try:
            node.chunk_size = int(chunk_size)
        except ValueError:
            pass

    chunk_overlap = element.get('chunkOverlap')
    if chunk_overlap:
        try:
            node.chunk_overlap = int(chunk_overlap)
        except ValueError:
            pass

    node.persist = element.get('persist', 'false').lower() in ('true', '1', 'yes')
    node.persist_path = element.get('persistPath')
    node.rebuild = element.get('rebuild', 'false').lower() in ('true', '1', 'yes')

    # Parse <q:source> children
    for child in element:
        local_name = child.tag.split('}')[-1] if '}' in child.tag else child.tag.split(':')[-1]
        if local_name == 'source':
            source = _parse_source(child)
            node.add_source(source)

    return node


def _parse_source(element: ET.Element) -> KnowledgeSourceNode:
    """Parse <q:source> element into KnowledgeSourceNode."""
    source = KnowledgeSourceNode()
    source.source_type = element.get('type', 'text')
    source.path = element.get('path')
    source.pattern = element.get('pattern', '*.md')
    source.url = element.get('url')
    source.datasource = element.get('datasource')

    chunk_size = element.get('chunkSize')
    if chunk_size:
        try:
            source.chunk_size = int(chunk_size)
        except ValueError:
            pass

    chunk_overlap = element.get('chunkOverlap')
    if chunk_overlap:
        try:
            source.chunk_overlap = int(chunk_overlap)
        except ValueError:
            pass

    # Text content (inline or SQL for query type)
    text = (element.text or '').strip()
    if source.source_type == 'query':
        source.sql = text
    elif source.source_type == 'text':
        source.content = text

    return source
