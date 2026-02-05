"""Knowledge Base feature - RAG with virtual knowledge bases."""

from .ast_node import KnowledgeNode, KnowledgeSourceNode
from .parser import parse_knowledge

__all__ = ['KnowledgeNode', 'KnowledgeSourceNode', 'parse_knowledge']
