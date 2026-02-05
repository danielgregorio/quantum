"""
Quantum Knowledge Service - RAG with ChromaDB + Ollama embeddings.

Provides indexing, vector search, and RAG query capabilities for
the q:knowledge / q:query knowledge: datasource integration.
"""

import os
import re
import glob
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

import requests

logger = logging.getLogger(__name__)


class KnowledgeError(Exception):
    """Raised when knowledge base operations fail."""
    pass


class KnowledgeService:
    """ChromaDB + Ollama embeddings service for RAG."""

    def __init__(self, llm_service=None):
        self.llm_service = llm_service
        self._collections: Dict[str, Any] = {}  # name -> ChromaDB collection
        self._client = None
        self._ollama_base_url = os.getenv(
            'QUANTUM_LLM_BASE_URL', 'http://localhost:11434'
        ).rstrip('/')

    def _get_client(self, persist: bool = False, persist_path: Optional[str] = None):
        """Get or create ChromaDB client."""
        if self._client is not None:
            return self._client

        try:
            import chromadb
        except ImportError:
            raise KnowledgeError(
                "chromadb package is required for q:knowledge. "
                "Install it with: pip install chromadb"
            )

        if persist and persist_path:
            self._client = chromadb.PersistentClient(path=persist_path)
        else:
            self._client = chromadb.Client()

        return self._client

    def index_knowledge(
        self,
        name: str,
        sources: list,
        embed_model: str = "nomic-embed-text",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        persist: bool = False,
        persist_path: Optional[str] = None,
        rebuild: bool = False,
        database_service=None,
        exec_context=None,
    ):
        """
        Index knowledge base sources into ChromaDB.

        Args:
            name: Knowledge base name (used as collection name)
            sources: List of KnowledgeSourceNode objects
            embed_model: Ollama embedding model name
            chunk_size: Characters per chunk
            chunk_overlap: Overlap between chunks
            persist: Whether to persist ChromaDB to disk
            persist_path: Path for ChromaDB persistence
            rebuild: Force reindex even if collection exists
            database_service: DatabaseService for query-type sources
            exec_context: ExecutionContext for variable resolution
        """
        client = self._get_client(persist, persist_path)

        # Get or create collection
        if rebuild:
            try:
                client.delete_collection(name)
            except Exception:
                pass

        collection = client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"}
        )

        # If collection already has documents and not rebuilding, skip
        if collection.count() > 0 and not rebuild:
            self._collections[name] = collection
            logger.info(f"Knowledge base '{name}' already indexed ({collection.count()} chunks)")
            return

        # Extract text from all sources
        all_texts = []
        for source in sources:
            texts = self._extract_source_text(
                source, database_service, exec_context
            )
            all_texts.extend(texts)

        if not all_texts:
            logger.warning(f"Knowledge base '{name}': no text extracted from sources")
            self._collections[name] = collection
            return

        # Chunk all extracted texts
        all_chunks = []
        all_metadata = []
        for text_item in all_texts:
            text = text_item['text']
            source_label = text_item.get('source', 'inline')
            cs = text_item.get('chunk_size', chunk_size)
            co = text_item.get('chunk_overlap', chunk_overlap)

            chunks = self._chunk_text(text, cs, co)
            for i, chunk in enumerate(chunks):
                all_chunks.append(chunk)
                all_metadata.append({
                    "source": source_label,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                })

        if not all_chunks:
            self._collections[name] = collection
            return

        # Generate embeddings via Ollama
        embeddings = self._generate_embeddings(all_chunks, embed_model)

        # Generate IDs
        ids = [
            f"{name}_{hashlib.md5(chunk.encode()).hexdigest()[:12]}_{i}"
            for i, chunk in enumerate(all_chunks)
        ]

        # Upsert into ChromaDB (batch to avoid limits)
        batch_size = 100
        for start in range(0, len(all_chunks), batch_size):
            end = min(start + batch_size, len(all_chunks))
            collection.upsert(
                ids=ids[start:end],
                documents=all_chunks[start:end],
                embeddings=embeddings[start:end],
                metadatas=all_metadata[start:end],
            )

        self._collections[name] = collection
        logger.info(f"Knowledge base '{name}' indexed: {len(all_chunks)} chunks from {len(all_texts)} text segments")

    def _extract_source_text(
        self, source, database_service=None, exec_context=None
    ) -> List[Dict[str, Any]]:
        """
        Extract text from a KnowledgeSourceNode.

        Returns list of dicts: [{text, source, chunk_size?, chunk_overlap?}]
        """
        results = []
        st = source.source_type
        extra = {}
        if source.chunk_size is not None:
            extra['chunk_size'] = source.chunk_size
        if source.chunk_overlap is not None:
            extra['chunk_overlap'] = source.chunk_overlap

        if st == 'text':
            if source.content:
                results.append({'text': source.content, 'source': 'inline', **extra})

        elif st == 'file':
            path = Path(source.path)
            if path.exists() and path.is_file():
                try:
                    text = path.read_text(encoding='utf-8')
                    results.append({'text': text, 'source': str(path), **extra})
                except Exception as e:
                    logger.warning(f"Failed to read file {path}: {e}")
            else:
                logger.warning(f"Knowledge source file not found: {source.path}")

        elif st == 'directory':
            dir_path = Path(source.path)
            pattern = source.pattern or '*.md'
            if dir_path.exists() and dir_path.is_dir():
                for file_path in sorted(dir_path.glob(pattern)):
                    if file_path.is_file():
                        try:
                            text = file_path.read_text(encoding='utf-8')
                            results.append({'text': text, 'source': str(file_path), **extra})
                        except Exception as e:
                            logger.warning(f"Failed to read {file_path}: {e}")
            else:
                logger.warning(f"Knowledge source directory not found: {source.path}")

        elif st == 'url':
            logger.warning("URL source type is not yet implemented for q:knowledge")

        elif st == 'query':
            if database_service and source.datasource and source.sql:
                try:
                    result = database_service.execute_query(
                        source.datasource, source.sql, {}
                    )
                    for row in result.data:
                        # Concatenate all string values in the row
                        parts = [str(v) for v in row.values() if v is not None]
                        text = ' '.join(parts)
                        if text.strip():
                            results.append({'text': text, 'source': f"query:{source.datasource}", **extra})
                except Exception as e:
                    logger.warning(f"Failed to execute knowledge source query: {e}")
            else:
                logger.warning("Query source requires datasource, sql, and database_service")

        return results

    def _chunk_text(self, text: str, chunk_size: int = 500, chunk_overlap: int = 50) -> List[str]:
        """
        Split text into chunks using a sliding window with paragraph/sentence awareness.

        Args:
            text: Input text
            chunk_size: Target characters per chunk
            chunk_overlap: Overlap between chunks

        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            return []

        text = text.strip()

        # If text is smaller than chunk_size, return as single chunk
        if len(text) <= chunk_size:
            return [text]

        # Split into paragraphs first
        paragraphs = re.split(r'\n\s*\n', text)

        chunks = []
        current_chunk = ""

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # If adding this paragraph exceeds chunk_size
            if current_chunk and len(current_chunk) + len(paragraph) + 1 > chunk_size:
                chunks.append(current_chunk.strip())
                # Start new chunk with overlap from end of previous
                if chunk_overlap > 0 and len(current_chunk) > chunk_overlap:
                    current_chunk = current_chunk[-chunk_overlap:] + "\n" + paragraph
                else:
                    current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += "\n" + paragraph
                else:
                    current_chunk = paragraph

            # If single paragraph exceeds chunk_size, split by sentences
            while len(current_chunk) > chunk_size:
                # Find a good split point (end of sentence)
                split_at = chunk_size
                for sep in ['. ', '! ', '? ', '\n', '; ', ', ']:
                    idx = current_chunk.rfind(sep, 0, chunk_size)
                    if idx > chunk_size // 3:
                        split_at = idx + len(sep)
                        break

                chunks.append(current_chunk[:split_at].strip())
                if chunk_overlap > 0:
                    overlap_start = max(0, split_at - chunk_overlap)
                    current_chunk = current_chunk[overlap_start:]
                else:
                    current_chunk = current_chunk[split_at:]

        # Don't forget the last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks

    def _generate_embeddings(self, texts: List[str], model: str = "nomic-embed-text") -> List[List[float]]:
        """
        Generate embeddings via Ollama /api/embed endpoint.

        Args:
            texts: List of text strings to embed
            model: Ollama embedding model name

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        url = f"{self._ollama_base_url}/api/embed"

        # Batch to avoid very large payloads
        all_embeddings = []
        batch_size = 50

        for start in range(0, len(texts), batch_size):
            batch = texts[start:start + batch_size]
            payload = {
                "model": model,
                "input": batch,
            }

            try:
                embed_timeout = int(os.getenv('QUANTUM_EMBED_TIMEOUT', '50'))
                resp = requests.post(url, json=payload, timeout=embed_timeout)
                resp.raise_for_status()
                data = resp.json()

                embeddings = data.get("embeddings", [])
                if len(embeddings) != len(batch):
                    raise KnowledgeError(
                        f"Embedding count mismatch: expected {len(batch)}, got {len(embeddings)}"
                    )
                all_embeddings.extend(embeddings)

            except requests.ConnectionError:
                raise KnowledgeError(
                    f"Cannot connect to Ollama at {self._ollama_base_url}. "
                    "Ensure Ollama is running (ollama serve) and the embedding model is pulled "
                    f"(ollama pull {model})"
                )
            except requests.Timeout:
                raise KnowledgeError(f"Embedding request timed out for model {model}")
            except requests.HTTPError as e:
                raise KnowledgeError(f"Ollama embedding API error: {e.response.status_code} - {e.response.text}")
            except KnowledgeError:
                raise
            except Exception as e:
                raise KnowledgeError(f"Embedding generation error: {e}")

        return all_embeddings

    def search(
        self,
        name: str,
        query_text: str,
        n_results: int = 5,
        embed_model: str = "nomic-embed-text",
    ) -> List[Dict[str, Any]]:
        """
        Vector similarity search on a knowledge base.

        Args:
            name: Knowledge base name
            query_text: Search query text
            n_results: Number of results to return
            embed_model: Embedding model to use for query

        Returns:
            List of dicts: [{content, relevance, source, chunk_index}]
        """
        collection = self._collections.get(name)
        if collection is None:
            raise KnowledgeError(f"Knowledge base '{name}' not found. Define it with <q:knowledge> first.")

        if collection.count() == 0:
            return []

        # Generate query embedding
        query_embedding = self._generate_embeddings([query_text], embed_model)
        if not query_embedding:
            return []

        # Search ChromaDB
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=min(n_results, collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        # Format results
        formatted = []
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for doc, meta, dist in zip(documents, metadatas, distances):
            # ChromaDB cosine distance: 0 = identical, 2 = opposite
            # Convert to relevance score: 1.0 = perfect match, 0.0 = no match
            relevance = max(0.0, 1.0 - dist / 2.0)
            formatted.append({
                "content": doc,
                "relevance": round(relevance, 4),
                "source": meta.get("source", "unknown"),
                "chunk_index": meta.get("chunk_index", 0),
            })

        return formatted

    def rag_query(
        self,
        name: str,
        question: str,
        model: Optional[str] = None,
        n_results: int = 5,
        embed_model: str = "nomic-embed-text",
    ) -> Dict[str, Any]:
        """
        Full RAG pipeline: search + LLM answer.

        Args:
            name: Knowledge base name
            question: User question
            model: LLM model for answer generation
            n_results: Number of chunks to retrieve for context
            embed_model: Embedding model for search

        Returns:
            Dict: {answer, sources, confidence}
        """
        if self.llm_service is None:
            raise KnowledgeError("LLM service is required for RAG queries. Ensure Ollama is available.")

        # Step 1: Vector search
        search_results = self.search(name, question, n_results, embed_model)

        if not search_results:
            return {
                "answer": "No relevant information found in the knowledge base.",
                "sources": [],
                "confidence": 0.0,
            }

        # Step 2: Build context from search results
        context_parts = []
        sources = []
        for i, result in enumerate(search_results):
            context_parts.append(f"[{i+1}] {result['content']}")
            src = result.get('source', 'unknown')
            if src not in sources:
                sources.append(src)

        context = "\n\n".join(context_parts)

        # Step 3: Generate answer via LLM
        system_prompt = (
            "You are a helpful assistant that answers questions based on the provided context. "
            "Only use information from the context below. If the context doesn't contain "
            "enough information to answer, say so. Be concise and accurate."
        )

        prompt = (
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\n"
            f"Answer:"
        )

        try:
            llm_result = self.llm_service.generate(
                prompt=prompt,
                model=model,
                system=system_prompt,
                temperature=0.3,
            )

            answer = llm_result.get("data", "")
            success = llm_result.get("success", False)

            # Calculate confidence based on search relevance
            avg_relevance = sum(r['relevance'] for r in search_results) / len(search_results) if search_results else 0.0

            return {
                "answer": answer.strip() if answer else "Failed to generate answer.",
                "sources": sources,
                "confidence": round(avg_relevance, 4),
            }

        except Exception as e:
            logger.error(f"RAG query failed for '{name}': {e}")
            return {
                "answer": f"Error generating answer: {e}",
                "sources": sources,
                "confidence": 0.0,
            }
