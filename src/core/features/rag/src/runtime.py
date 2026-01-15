"""
Runtime for RAG Feature

Handles knowledge base creation, embeddings, and semantic search.
"""

from typing import List, Dict, Any, Optional
import os
import glob
from pathlib import Path
import hashlib


class Document:
    """Represents a document chunk"""
    def __init__(self, content: str, metadata: Dict[str, Any] = None):
        self.content = content
        self.metadata = metadata or {}
        self.doc_id = self._generate_id()

    def _generate_id(self) -> str:
        """Generate unique ID for document"""
        content_hash = hashlib.md5(self.content.encode()).hexdigest()
        return f"doc_{content_hash[:16]}"


class DocumentLoader:
    """Loads documents from various sources"""

    @staticmethod
    def load_files(pattern: str) -> List[Document]:
        """
        Load documents from file pattern

        Args:
            pattern: Glob pattern (e.g., "./docs/**/*.md")

        Returns:
            List of Document objects
        """
        documents = []
        files = glob.glob(pattern, recursive=True)

        for file_path in files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Extract metadata from file
                metadata = {
                    'source': file_path,
                    'filename': os.path.basename(file_path),
                    'extension': os.path.splitext(file_path)[1]
                }

                doc = Document(content, metadata)
                documents.append(doc)
            except Exception as e:
                print(f"[WARNING] Failed to load {file_path}: {e}")

        return documents

    @staticmethod
    def load_url(url: str) -> List[Document]:
        """Load document from URL (TODO: implement web scraping)"""
        # Placeholder - would use requests + BeautifulSoup
        print(f"[WARNING] URL loading not yet implemented: {url}")
        return []

    @staticmethod
    def load_database(database: str, table: str, query: Optional[str] = None) -> List[Document]:
        """Load documents from database (TODO: implement DB loading)"""
        # Placeholder - would query database
        print(f"[WARNING] Database loading not yet implemented: {database}.{table}")
        return []


class TextChunker:
    """Chunks documents into smaller pieces"""

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
        """
        Split text into overlapping chunks

        Args:
            text: Text to chunk
            chunk_size: Size of each chunk in characters
            chunk_overlap: Overlap between chunks

        Returns:
            List of text chunks
        """
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence end markers
                for marker in ['. ', '! ', '? ', '\n\n']:
                    last_marker = text.rfind(marker, start, end)
                    if last_marker != -1:
                        end = last_marker + len(marker)
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - chunk_overlap

        return chunks


class OllamaEmbeddings:
    """Generate embeddings using Ollama"""

    def __init__(self, model: str = "nomic-embed-text"):
        self.model = model
        self._ollama = None

    @property
    def ollama(self):
        """Lazy load ollama library"""
        if self._ollama is None:
            try:
                import ollama
                self._ollama = ollama
            except ImportError:
                raise ImportError(
                    "ollama library not installed. Install with: pip install ollama"
                )
        return self._ollama

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for text using Ollama

        Args:
            text: Text to embed

        Returns:
            Embedding vector (list of floats)
        """
        try:
            response = self.ollama.embeddings(
                model=self.model,
                prompt=text
            )
            return response['embedding']
        except Exception as e:
            print(f"[ERROR] Embedding failed: {e}")
            print(f"[INFO] Make sure model '{self.model}' is pulled: ollama pull {self.model}")
            # Return zero vector as fallback
            return [0.0] * 768  # Default embedding size

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        return [self.embed_text(text) for text in texts]


class ChromaDBVectorStore:
    """Vector store using ChromaDB"""

    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        self._client = None
        self._collection = None

    @property
    def client(self):
        """Lazy load ChromaDB client"""
        if self._client is None:
            try:
                import chromadb
                self._client = chromadb.Client()
            except ImportError:
                raise ImportError(
                    "chromadb not installed. Install with: pip install chromadb"
                )
        return self._client

    @property
    def collection(self):
        """Get or create collection"""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name
            )
        return self._collection

    def add_documents(
        self,
        documents: List[str],
        embeddings: List[List[float]],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None
    ):
        """
        Add documents to vector store

        Args:
            documents: List of text chunks
            embeddings: List of embedding vectors
            metadatas: List of metadata dicts
            ids: List of document IDs
        """
        if ids is None:
            ids = [f"doc_{i}" for i in range(len(documents))]

        if metadatas is None:
            metadatas = [{} for _ in documents]

        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids
        )

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents

        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            filter_metadata: Filter by metadata

        Returns:
            List of results with documents, scores, and metadata
        """
        where = filter_metadata if filter_metadata else None

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where
        )

        # Format results
        formatted_results = []
        if results['documents'] and len(results['documents']) > 0:
            for i, doc in enumerate(results['documents'][0]):
                result = {
                    'content': doc,
                    'score': 1 - results['distances'][0][i],  # Convert distance to similarity
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {}
                }
                formatted_results.append(result)

        return formatted_results


class KnowledgeBaseRegistry:
    """Registry for knowledge bases"""

    def __init__(self):
        self.knowledge_bases: Dict[str, Any] = {}

    def register(self, knowledge_id: str, knowledge_base):
        """Register a knowledge base"""
        self.knowledge_bases[knowledge_id] = knowledge_base

    def get(self, knowledge_id: str):
        """Get a knowledge base by ID"""
        return self.knowledge_bases.get(knowledge_id)


class KnowledgeBase:
    """
    Main knowledge base class

    Handles document loading, chunking, embedding, and search.
    """

    def __init__(
        self,
        knowledge_id: str,
        embedding_provider: str = "ollama",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        vector_db: str = "chromadb"
    ):
        self.knowledge_id = knowledge_id
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # Initialize components
        self.loader = DocumentLoader()
        self.chunker = TextChunker()

        # Initialize embeddings
        if embedding_provider == "ollama":
            self.embeddings = OllamaEmbeddings()
        else:
            raise ValueError(f"Unknown embedding provider: {embedding_provider}")

        # Initialize vector store
        if vector_db == "chromadb":
            self.vector_store = ChromaDBVectorStore(collection_name=knowledge_id)
        else:
            raise ValueError(f"Unknown vector DB: {vector_db}")

        self.is_built = False

    def add_source(self, source_type: str, **kwargs):
        """
        Add documents from a source

        Args:
            source_type: "file", "url", or "database"
            **kwargs: Source-specific parameters
        """
        # Load documents
        if source_type == "file":
            documents = self.loader.load_files(kwargs.get('path'))
        elif source_type == "url":
            documents = self.loader.load_url(kwargs.get('url'))
        elif source_type == "database":
            documents = self.loader.load_database(
                kwargs.get('database'),
                kwargs.get('table'),
                kwargs.get('query')
            )
        else:
            print(f"[WARNING] Unknown source type: {source_type}")
            return

        if not documents:
            print(f"[WARNING] No documents loaded from {source_type}")
            return

        print(f"[INFO] Loaded {len(documents)} documents from {source_type}")

        # Chunk documents
        all_chunks = []
        all_metadatas = []
        all_ids = []

        for doc in documents:
            chunks = self.chunker.chunk_text(
                doc.content,
                self.chunk_size,
                self.chunk_overlap
            )

            for i, chunk in enumerate(chunks):
                all_chunks.append(chunk)
                metadata = doc.metadata.copy()
                metadata['chunk_index'] = i
                all_metadatas.append(metadata)
                all_ids.append(f"{doc.doc_id}_chunk_{i}")

        print(f"[INFO] Created {len(all_chunks)} chunks")

        # Generate embeddings
        print(f"[INFO] Generating embeddings...")
        embeddings = self.embeddings.embed_documents(all_chunks)
        print(f"[INFO] Generated {len(embeddings)} embeddings")

        # Add to vector store
        print(f"[INFO] Adding to vector store...")
        self.vector_store.add_documents(
            documents=all_chunks,
            embeddings=embeddings,
            metadatas=all_metadatas,
            ids=all_ids
        )

        self.is_built = True
        print(f"[SUCCESS] ✅ Knowledge base '{self.knowledge_id}' ready!")

    def search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.0,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search the knowledge base

        Args:
            query: Search query text
            top_k: Number of results
            threshold: Minimum similarity score
            filter_metadata: Filter by metadata

        Returns:
            List of results
        """
        if not self.is_built:
            print(f"[WARNING] Knowledge base '{self.knowledge_id}' not built yet")
            return []

        # Generate query embedding
        query_embedding = self.embeddings.embed_text(query)

        # Search vector store
        results = self.vector_store.search(
            query_embedding,
            top_k=top_k,
            filter_metadata=filter_metadata
        )

        # Filter by threshold
        filtered_results = [r for r in results if r['score'] >= threshold]

        return filtered_results


class RAGRuntime:
    """Runtime for RAG operations"""

    def __init__(self):
        self.registry = KnowledgeBaseRegistry()

    def build_knowledge_base(self, knowledge_node) -> KnowledgeBase:
        """
        Build a knowledge base from KnowledgeNode

        Args:
            knowledge_node: KnowledgeNode from parser

        Returns:
            KnowledgeBase instance
        """
        print(f"[INFO] Building knowledge base: {knowledge_node.knowledge_id}")

        kb = KnowledgeBase(
            knowledge_id=knowledge_node.knowledge_id,
            embedding_provider=knowledge_node.embedding,
            chunk_size=knowledge_node.chunk_size,
            chunk_overlap=knowledge_node.chunk_overlap,
            vector_db=knowledge_node.vector_db
        )

        # Add simple source
        if knowledge_node.source:
            kb.add_source("file", path=knowledge_node.source)

        # Add multiple sources
        for source in knowledge_node.sources:
            kb.add_source(
                source.type,
                path=source.path,
                url=source.url,
                database=source.database,
                table=source.table,
                query=source.query
            )

        # Register knowledge base
        self.registry.register(knowledge_node.knowledge_id, kb)

        return kb

    def search_knowledge_base(
        self,
        search_node,
        context_vars: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Search a knowledge base

        Args:
            search_node: SearchNode from parser
            context_vars: Variables for databinding

        Returns:
            Search results
        """
        # Get knowledge base
        kb = self.registry.get(search_node.knowledge_id)
        if not kb:
            print(f"[ERROR] Knowledge base '{search_node.knowledge_id}' not found")
            return []

        # Apply databinding to query
        query = self._apply_databinding(search_node.query, context_vars)

        # Search
        results = kb.search(
            query=query,
            top_k=search_node.top_k,
            threshold=search_node.threshold,
            filter_metadata=search_node.filter_metadata
        )

        return results

    def _apply_databinding(self, text: str, context_vars: Dict[str, Any]) -> str:
        """Apply databinding to text"""
        import re

        def replace_var(match):
            var_name = match.group(1).strip()
            return str(context_vars.get(var_name, f'{{{var_name}}}'))

        return re.sub(r'\{([^}]+)\}', replace_var, text)
