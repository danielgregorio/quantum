"""
Quantum Knowledge Service - RAG with ChromaDB + Ollama embeddings.

Provides indexing and vector search for q:knowledge, used by
q:llm knowledge= (IA-6) and the q:query knowledge: datasource.
"""

import os
import re
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
        self._chunks: Dict[str, int] = {}  # name -> how many chunks the index was built with
        self._clients: Dict[Optional[str], Any] = {}  # absolute persist path (None: memory) -> client
        self._ollama_base_url = os.getenv(
            'QUANTUM_LLM_BASE_URL', 'http://localhost:11434'
        ).rstrip('/')

    def _get_client(self, persist: bool = False, persist_path: Optional[str] = None):
        """The ChromaDB client for this store: in memory, or at `persist_path`.

        IA-2: a relative `persist_path` (the default is `./.quantum/knowledge`)
        is resolved against the working directory NOW. ChromaDB keeps one store
        per process for each path *string* it is given, so the relative string
        itself named a single store opened in whichever directory used it
        first: a base indexed from another directory was written to — or
        reused from — the first one, and once that directory was gone,
        indexing failed with "Failed to get segments" (a flaky CI failure,
        tests/conformance/test_ai_attributes.py). The client used to be one per
        service, too, so the first base's `persist` decided every later one.
        """
        key = str(Path(persist_path).resolve()) if persist and persist_path else None
        if key in self._clients:
            return self._clients[key]

        try:
            import chromadb
        except ImportError:
            raise KnowledgeError(
                "q:knowledge needs the optional RAG dependencies, which are not "
                "installed.\n"
                "  pip install 'quantum-framework[rag]'   (or: pip install chromadb)\n"
                "You also need an embedding model available on your LLM server, "
                "e.g. `ollama pull nomic-embed-text`."
            )

        if key is not None:
            client = chromadb.PersistentClient(path=key)
        else:
            client = chromadb.Client()
        self._clients[key] = client
        return client

    @staticmethod
    def _collection_name(name: str) -> str:
        """A ChromaDB collection name for any q:knowledge name.

        ChromaDB accepts 3-512 characters from [a-zA-Z0-9._-], starting and
        ending alphanumeric. `<q:knowledge name="kb">` failed with ChromaDB's
        own validation message. The prefix makes every name long enough and
        keeps Quantum's collections recognisable in a shared store.
        """
        safe = re.sub(r'[^a-zA-Z0-9._-]', '-', str(name)).strip('._-') or 'base'
        return f"quantum-{safe}"[:512]

    @staticmethod
    def _fingerprint(all_texts, embed_model, chunk_size, chunk_overlap) -> str:
        """What the index was built from: texts, their sources, and chunking."""
        digest = hashlib.sha256()
        digest.update(f"{embed_model}|{chunk_size}|{chunk_overlap}".encode())
        for item in all_texts:
            digest.update(str(item.get('source', '')).encode())
            digest.update(b'\x00')
            digest.update(str(item.get('text', '')).encode())
            digest.update(b'\x00')
            digest.update(f"{item.get('chunk_size')}|{item.get('chunk_overlap')}".encode())
        return digest.hexdigest()

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
        # Extract text first: whether the stored index is still valid depends
        # on what the sources say NOW. Reading them is cheap; embedding is the
        # expensive part, and that is what an unchanged fingerprint skips.
        # Before the vector store, too: a missing source file is the error the
        # author needs to see, not a missing optional dependency (IA-8).
        all_texts = []
        for source in sources:
            texts = self._extract_source_text(
                source, database_service, exec_context
            )
            all_texts.extend(texts)

        client = self._get_client(persist, persist_path)

        fingerprint = self._fingerprint(all_texts, embed_model, chunk_size, chunk_overlap)
        # IA-2: in memory, every base of the process shares one store, by
        # collection name. Two pages (or two apps) with a base "docs" built from
        # different sources deleted each other's index — the other page's search
        # then failed, or found nothing and read as "I don't know" (IA-9). An
        # in-memory base is named after its fingerprint too: different sources
        # never meet, the same sources are shared and reused across requests,
        # and two first requests write the same rows (the ids come from the text).
        collection_name = (self._collection_name(name) if persist
                           else self._collection_name(f"{name}-{fingerprint[:16]}"))

        # Knowledge bases persist by default (./.quantum/knowledge). The stored
        # collection used to be reused whenever it had any chunks — so a base
        # named "docs" indexed last week answered from last week's text, and
        # changing the q:source did nothing. Measured: inline sources declared
        # in a new file came back as chunks of docs/index.md from an earlier
        # run. Reuse only when the fingerprint matches.
        if not rebuild:
            try:
                existing = client.get_collection(collection_name)
            except Exception:
                existing = None
            if existing is not None:
                if (existing.count() > 0
                        and (existing.metadata or {}).get("quantum_fingerprint") == fingerprint):
                    self._collections[name] = existing
                    self._chunks[name] = existing.count()
                    logger.info(f"Knowledge base '{name}' already indexed ({existing.count()} chunks)")
                    return
                logger.info(f"Knowledge base '{name}': sources changed, reindexing")
                rebuild = True

        if rebuild:
            try:
                client.delete_collection(collection_name)
            except Exception:
                pass

        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine", "quantum_fingerprint": fingerprint}
        )

        if not all_texts:
            logger.warning(f"Knowledge base '{name}': no text extracted from sources")
            self._collections[name] = collection
            self._chunks[name] = 0
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
            self._chunks[name] = 0
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
        self._chunks[name] = len(all_chunks)
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
            # IA-8: a source that cannot be read is an error — it used to be a
            # log warning, and the base answered from fewer documents, silently.
            path = Path(source.path or '')
            if not path.is_file():
                raise KnowledgeError(f"<q:source type=\"file\" path=\"{source.path}\">: no such file "
                                     f"(relative to {Path.cwd()})")
            try:
                results.append({'text': path.read_text(encoding='utf-8'), 'source': str(path), **extra})
            except (OSError, UnicodeDecodeError) as exc:
                raise KnowledgeError(f"<q:source path=\"{source.path}\">: cannot be read: {exc}") from exc

        elif st == 'directory':
            dir_path = Path(source.path or '')
            pattern = source.pattern or '*.md'
            if not dir_path.is_dir():
                raise KnowledgeError(f"<q:source type=\"directory\" path=\"{source.path}\">: no such folder "
                                     f"(relative to {Path.cwd()})")
            files = [f for f in sorted(dir_path.glob(pattern)) if f.is_file()]
            if not files:
                raise KnowledgeError(f"<q:source type=\"directory\" path=\"{source.path}\">: no file "
                                     f"matches {pattern!r}")
            for file_path in files:
                try:
                    results.append({'text': file_path.read_text(encoding='utf-8'),
                                    'source': str(file_path), **extra})
                except (OSError, UnicodeDecodeError) as exc:
                    raise KnowledgeError(f"<q:source>: {file_path} cannot be read: {exc}") from exc

        elif st == 'query':
            if not (database_service and source.datasource and source.sql):
                raise KnowledgeError('<q:source type="query"> needs datasource= and the SQL as its text')
            try:
                result = database_service.execute_query(source.datasource, source.sql, {})
            except Exception as exc:
                raise KnowledgeError(f'<q:source type="query">: {exc}') from exc
            for row in result.data:
                # Concatenate all string values in the row
                parts = [str(v) for v in row.values() if v is not None]
                text = ' '.join(parts)
                if text.strip():
                    results.append({'text': text, 'source': f"query:{source.datasource}", **extra})

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

        # IA-6 / IA-9: an empty result means "nothing in this base is relevant".
        # A base that was built with chunks and has none now lost its index;
        # answering "found nothing" would pass that off as an honest "I don't know".
        try:
            count = collection.count()
        except Exception as e:
            raise KnowledgeError(f"Knowledge base '{name}' lost its index: {e}")
        if count == 0:
            if self._chunks.get(name, 0) > 0:
                raise KnowledgeError(
                    f"Knowledge base '{name}' lost its index: it was built with "
                    f"{self._chunks[name]} chunks and has none now")
            return []

        # Generate query embedding
        query_embedding = self._generate_embeddings([query_text], embed_model)
        if not query_embedding:
            return []

        # Search ChromaDB
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=min(n_results, count),
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
