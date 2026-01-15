"""
Parser for RAG Feature

Parses q:knowledge and q:search tags.
"""

import xml.etree.ElementTree as ET
from typing import List
from .ast_node import KnowledgeNode, KnowledgeSourceNode, SearchNode


def parse_knowledge(element: ET.Element) -> KnowledgeNode:
    """
    Parse <q:knowledge> tag

    Examples:
        <q:knowledge id="docs" source="./docs/**/*.md" />

        <q:knowledge id="docs" embedding="ollama" chunk_size="1000">
            <source path="./docs/*.md" />
            <source url="https://blog.example.com" />
        </q:knowledge>
    """
    knowledge_id = element.get('id')
    source = element.get('source')
    embedding = element.get('embedding', 'ollama')
    chunk_size = int(element.get('chunk_size', '1000'))
    chunk_overlap = int(element.get('chunk_overlap', '200'))
    vector_db = element.get('vector_db', 'chromadb')
    auto_update = element.get('auto_update', 'false').lower() == 'true'

    # Parse multiple sources from child elements
    sources = []
    for source_elem in element.findall('.//source'):
        source_node = parse_knowledge_source(source_elem)
        sources.append(source_node)

    # Parse metadata fields
    metadata_fields = []
    metadata_elem = element.find('.//metadata')
    if metadata_elem is not None:
        for field_elem in metadata_elem.findall('.//field'):
            field_name = field_elem.get('name')
            if field_name:
                metadata_fields.append(field_name)

    return KnowledgeNode(
        knowledge_id=knowledge_id,
        source=source,
        sources=sources,
        embedding=embedding,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        vector_db=vector_db,
        auto_update=auto_update,
        metadata_fields=metadata_fields
    )


def parse_knowledge_source(element: ET.Element) -> KnowledgeSourceNode:
    """
    Parse <source> tag within q:knowledge

    Examples:
        <source path="./docs/*.md" />
        <source url="https://example.com" />
        <source database="db" table="articles" />
    """
    path = element.get('path')
    url = element.get('url')
    database = element.get('database')
    table = element.get('table')
    query = element.get('query')

    # Determine type
    if path:
        source_type = "file"
    elif url:
        source_type = "url"
    elif database:
        source_type = "database"
    else:
        source_type = "file"

    return KnowledgeSourceNode(
        type=source_type,
        path=path,
        url=url,
        database=database,
        table=table,
        query=query
    )


def parse_search(element: ET.Element) -> SearchNode:
    """
    Parse <q:search> tag

    Example:
        <q:search knowledge="docs" query="{userQuery}" result="results" top_k="5" />
    """
    knowledge_id = element.get('knowledge')
    query = element.get('query')
    result_var = element.get('result')
    top_k = int(element.get('top_k', '5'))
    threshold = float(element.get('threshold', '0.0'))

    # Parse filter metadata
    filter_metadata = {}
    for key, value in element.attrib.items():
        if key.startswith('filter_'):
            filter_key = key.replace('filter_', '')
            filter_metadata[filter_key] = value

    return SearchNode(
        knowledge_id=knowledge_id,
        query=query,
        result_var=result_var,
        top_k=top_k,
        threshold=threshold,
        filter_metadata=filter_metadata
    )
