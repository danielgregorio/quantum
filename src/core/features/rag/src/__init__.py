"""
RAG Feature - Retrieval-Augmented Generation

Provides q:knowledge tag for creating searchable knowledge bases.
"""

from .ast_node import KnowledgeNode, SearchNode
from .parser import parse_knowledge, parse_search
from .runtime import RAGRuntime

__all__ = ['KnowledgeNode', 'SearchNode', 'parse_knowledge', 'parse_search', 'RAGRuntime']
