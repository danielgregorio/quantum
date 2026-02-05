"""AST nodes for q:knowledge and q:source."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from core.ast_nodes import QuantumNode


@dataclass
class KnowledgeSourceNode(QuantumNode):
    """
    Represents <q:source> inside <q:knowledge>.

    Examples:
      <q:source type="text">Quantum Framework allows...</q:source>
      <q:source type="file" path="./docs/guide.md" />
      <q:source type="directory" path="./docs/" pattern="*.md" />
      <q:source type="query" datasource="mydb">
          SELECT title, content FROM articles
      </q:source>
    """
    source_type: str = "text"          # text, file, directory, url, query
    content: Optional[str] = None      # Inline text content
    path: Optional[str] = None         # File or directory path
    pattern: Optional[str] = None      # Glob pattern for directory type
    url: Optional[str] = None          # URL for url type
    datasource: Optional[str] = None   # Datasource for query type
    sql: Optional[str] = None          # SQL for query type
    chunk_size: Optional[int] = None   # Override parent chunk_size
    chunk_overlap: Optional[int] = None  # Override parent chunk_overlap

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "knowledge_source",
            "source_type": self.source_type,
            "content": self.content[:50] + "..." if self.content and len(self.content) > 50 else self.content,
            "path": self.path,
            "pattern": self.pattern,
            "url": self.url,
            "datasource": self.datasource,
        }

    def validate(self) -> List[str]:
        errors = []
        valid_types = ['text', 'file', 'directory', 'url', 'query']
        if self.source_type not in valid_types:
            errors.append(f"Invalid source type: {self.source_type}. Must be one of {valid_types}")

        if self.source_type == 'text' and not self.content:
            errors.append("Text source requires content")
        if self.source_type == 'file' and not self.path:
            errors.append("File source requires 'path' attribute")
        if self.source_type == 'directory' and not self.path:
            errors.append("Directory source requires 'path' attribute")
        if self.source_type == 'url' and not self.url:
            errors.append("URL source requires 'url' attribute")
        if self.source_type == 'query' and not self.datasource:
            errors.append("Query source requires 'datasource' attribute")

        return errors

    def __repr__(self):
        return f'<KnowledgeSourceNode type={self.source_type}>'


@dataclass
class KnowledgeNode(QuantumNode):
    """
    Represents <q:knowledge> - defines a virtual knowledge base.

    Examples:
      <q:knowledge name="docs" model="phi3" embedModel="nomic-embed-text">
          <q:source type="text">Quantum Framework allows...</q:source>
          <q:source type="file" path="./docs/guide.md" />
      </q:knowledge>
    """
    name: str = ""
    model: Optional[str] = None              # LLM model for RAG
    embed_model: str = "nomic-embed-text"     # Embedding model
    chunk_size: int = 500                     # Characters per chunk
    chunk_overlap: int = 50                   # Overlap between chunks
    sources: List[KnowledgeSourceNode] = field(default_factory=list)
    persist: bool = False                     # Persist ChromaDB to disk
    persist_path: Optional[str] = None        # ChromaDB persistence path
    rebuild: bool = False                     # Force reindex

    def add_source(self, source: KnowledgeSourceNode):
        self.sources.append(source)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "knowledge",
            "name": self.name,
            "model": self.model,
            "embed_model": self.embed_model,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "sources": [s.to_dict() for s in self.sources],
            "persist": self.persist,
            "rebuild": self.rebuild,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("Knowledge base name is required")
        if not self.sources:
            errors.append("Knowledge base requires at least one <q:source>")
        for source in self.sources:
            errors.extend(source.validate())
        return errors

    def __repr__(self):
        return f'<KnowledgeNode name={self.name} sources={len(self.sources)}>'
