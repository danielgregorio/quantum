"""
AST Nodes for RAG Feature

Represents q:knowledge and q:search tags in the AST.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class KnowledgeSourceNode:
    """Represents a single knowledge source"""
    type: str  # "file", "url", "database"
    path: Optional[str] = None
    url: Optional[str] = None
    database: Optional[str] = None
    table: Optional[str] = None
    query: Optional[str] = None


@dataclass
class KnowledgeNode:
    """
    Represents a <q:knowledge> tag - defines a knowledge base

    Example:
        <q:knowledge id="docs" source="./docs/**/*.md" />

    Advanced Example:
        <q:knowledge id="docs" embedding="ollama" chunk_size="1000">
            <source path="./docs/*.md" />
            <source url="https://blog.example.com" />
        </q:knowledge>

    Attributes:
        knowledge_id: Unique identifier for this knowledge base
        source: Simple source pattern (for single source)
        sources: List of multiple sources
        embedding: Embedding provider ("ollama", "openai", "local")
        chunk_size: Size of text chunks for embedding
        chunk_overlap: Overlap between chunks
        vector_db: Vector database backend ("chromadb", "faiss", "memory")
        auto_update: Watch for source changes
        metadata_fields: Fields to extract as metadata
    """
    knowledge_id: str
    source: Optional[str] = None
    sources: List[KnowledgeSourceNode] = field(default_factory=list)
    embedding: str = "ollama"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    vector_db: str = "chromadb"
    auto_update: bool = False
    metadata_fields: List[str] = field(default_factory=list)

    def validate(self) -> List[str]:
        """Validate knowledge configuration"""
        errors = []

        if not self.knowledge_id:
            errors.append("Knowledge must have an 'id' attribute")

        if not self.source and not self.sources:
            errors.append("Knowledge must have either 'source' attribute or <source> children")

        if self.chunk_size < 100:
            errors.append(f"chunk_size too small: {self.chunk_size} (min: 100)")

        if self.chunk_overlap >= self.chunk_size:
            errors.append(f"chunk_overlap ({self.chunk_overlap}) must be < chunk_size ({self.chunk_size})")

        if self.embedding not in ["ollama", "openai", "local"]:
            errors.append(f"Unknown embedding provider: {self.embedding}")

        if self.vector_db not in ["chromadb", "faiss", "memory"]:
            errors.append(f"Unknown vector_db: {self.vector_db}")

        return errors


@dataclass
class SearchNode:
    """
    Represents a <q:search> tag - searches a knowledge base

    Example:
        <q:search knowledge="docs" query="{userQuery}" result="results" top_k="5" />

    Attributes:
        knowledge_id: ID of the knowledge base to search
        query: Search query text (can include databinding)
        result_var: Variable name to store results
        top_k: Number of results to return
        threshold: Minimum similarity score (0-1)
        filter_metadata: Filter by metadata fields
    """
    knowledge_id: str
    query: str
    result_var: str
    top_k: int = 5
    threshold: float = 0.0
    filter_metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> List[str]:
        """Validate search configuration"""
        errors = []

        if not self.knowledge_id:
            errors.append("Search must have a 'knowledge' attribute")

        if not self.query:
            errors.append("Search must have a 'query' attribute")

        if not self.result_var:
            errors.append("Search must have a 'result' attribute")

        if self.top_k < 1:
            errors.append(f"top_k must be >= 1, got {self.top_k}")

        if self.threshold < 0 or self.threshold > 1:
            errors.append(f"threshold must be between 0 and 1, got {self.threshold}")

        return errors
