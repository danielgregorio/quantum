"""
Tests for KnowledgeExecutor - q:knowledge knowledge base creation and RAG

Rewritten 2026-09-07: the previous version of this file mocked a `create(dict)`
method that never existed on the real KnowledgeService (which only ever had
index_knowledge()/search()/rag_query(), taking KnowledgeSourceNode objects,
not dicts) — see FULL_AUDIT_2026-09.md, Cluster B. It also asserted against
runtime.services.knowledge, but the real executor must index into
runtime.knowledge_service — the same instance component.py's
_execute_knowledge_query() searches later; services.knowledge is a separate,
unrelated KnowledgeService instance.
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from quantum.runtime.executors.ai.knowledge_executor import KnowledgeExecutor
from quantum.runtime.executors.base import ExecutorError

# Import KnowledgeNode from the correct location
try:
    from quantum.core.features.knowledge_base.src.ast_node import KnowledgeNode, KnowledgeSourceNode
except ImportError:
    from quantum.core.features.knowledge_base.src import KnowledgeNode, KnowledgeSourceNode

# Import fixtures from conftest.py
from tests.unit.executors.conftest import MockRuntime, MockExecutionContext


# =============================================================================
# Mock Objects for Knowledge Service
# =============================================================================

class MockKnowledgeService:
    """Mock knowledge service matching the real index_knowledge() signature."""

    def __init__(self):
        self.last_kwargs: Optional[Dict[str, Any]] = None

    def index_knowledge(self, name, sources, embed_model=None, chunk_size=None,
                         chunk_overlap=None, persist=None, persist_path=None,
                         rebuild=None, database_service=None, exec_context=None):
        self.last_kwargs = dict(
            name=name, sources=sources, embed_model=embed_model,
            chunk_size=chunk_size, chunk_overlap=chunk_overlap, persist=persist,
            persist_path=persist_path, rebuild=rebuild,
            database_service=database_service, exec_context=exec_context,
        )


class MockKnowledgeRuntime(MockRuntime):
    """Extended mock runtime with knowledge service"""

    def __init__(self, variables: Dict[str, Any] = None):
        super().__init__(variables)
        self._knowledge_service = MockKnowledgeService()
        # The executor reads runtime.knowledge_service directly (matching
        # component.py's own attribute, not services.knowledge).
        self.knowledge_service = self._knowledge_service
        self._services = MagicMock()

    @property
    def services(self):
        return self._services


# =============================================================================
# Test Classes
# =============================================================================

class TestKnowledgeExecutorBasic:
    """Basic functionality tests"""

    def test_handles_knowledge_node(self):
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)
        assert KnowledgeNode in executor.handles

    def test_handles_returns_list(self):
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)
        assert isinstance(executor.handles, list)
        assert len(executor.handles) == 1


class TestTextSource:
    """Test text source type"""

    def test_text_source_basic(self):
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "text"
        source.content = "Quantum Framework is a declarative web framework"

        node = KnowledgeNode()
        node.name = "docs"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        kwargs = runtime._knowledge_service.last_kwargs
        assert kwargs["name"] == "docs"
        assert len(kwargs["sources"]) == 1
        assert kwargs["sources"][0].source_type == "text"
        assert kwargs["sources"][0].content == "Quantum Framework is a declarative web framework"

    def test_text_source_with_databinding(self):
        runtime = MockKnowledgeRuntime({"projectName": "Quantum"})
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "text"
        source.content = "{projectName} Framework documentation"

        node = KnowledgeNode()
        node.name = "docs"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        kwargs = runtime._knowledge_service.last_kwargs
        assert kwargs["sources"][0].content == "Quantum Framework documentation"


class TestFileSource:
    """Test file source type"""

    def test_file_source_basic(self):
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "file"
        source.path = "./docs/guide.md"

        node = KnowledgeNode()
        node.name = "guide"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        kwargs = runtime._knowledge_service.last_kwargs
        assert kwargs["sources"][0].source_type == "file"
        assert kwargs["sources"][0].path == "./docs/guide.md"

    def test_file_source_with_databinding(self):
        runtime = MockKnowledgeRuntime({"docPath": "./custom/docs.md"})
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "file"
        source.path = "{docPath}"

        node = KnowledgeNode()
        node.name = "custom"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        kwargs = runtime._knowledge_service.last_kwargs
        assert kwargs["sources"][0].path == "./custom/docs.md"


class TestDirectorySource:
    """Test directory source type"""

    def test_directory_source_basic(self):
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "directory"
        source.path = "./docs/"
        source.pattern = "*.md"

        node = KnowledgeNode()
        node.name = "all_docs"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        kwargs = runtime._knowledge_service.last_kwargs
        assert kwargs["sources"][0].source_type == "directory"
        assert kwargs["sources"][0].path == "./docs/"
        assert kwargs["sources"][0].pattern == "*.md"

    def test_directory_source_databinding(self):
        runtime = MockKnowledgeRuntime({"docsDir": "./custom-docs/"})
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "directory"
        source.path = "{docsDir}"

        node = KnowledgeNode()
        node.name = "docs"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        kwargs = runtime._knowledge_service.last_kwargs
        assert kwargs["sources"][0].path == "./custom-docs/"


class TestURLSource:
    """Test URL source type"""

    def test_url_source_basic(self):
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "url"
        source.url = "https://docs.quantum.dev/guide"

        node = KnowledgeNode()
        node.name = "web_docs"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        kwargs = runtime._knowledge_service.last_kwargs
        assert kwargs["sources"][0].source_type == "url"
        assert kwargs["sources"][0].url == "https://docs.quantum.dev/guide"

    def test_url_source_with_databinding(self):
        runtime = MockKnowledgeRuntime({"docsUrl": "https://example.com/docs"})
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "url"
        source.url = "{docsUrl}"

        node = KnowledgeNode()
        node.name = "external"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        kwargs = runtime._knowledge_service.last_kwargs
        assert kwargs["sources"][0].url == "https://example.com/docs"


class TestQuerySource:
    """Test query source type"""

    def test_query_source_basic(self):
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "query"
        source.datasource = "mydb"
        source.sql = "SELECT title, content FROM articles"

        node = KnowledgeNode()
        node.name = "articles"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        kwargs = runtime._knowledge_service.last_kwargs
        assert kwargs["sources"][0].source_type == "query"
        assert kwargs["sources"][0].datasource == "mydb"
        assert kwargs["sources"][0].sql == "SELECT title, content FROM articles"
        # database_service must be forwarded — query sources need it
        assert kwargs["database_service"] is runtime.services.database

    def test_query_source_with_databinding(self):
        runtime = MockKnowledgeRuntime({"category": "tech"})
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "query"
        source.datasource = "mydb"
        source.sql = "SELECT * FROM articles WHERE category = '{category}'"

        node = KnowledgeNode()
        node.name = "tech_articles"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        kwargs = runtime._knowledge_service.last_kwargs
        assert "tech" in kwargs["sources"][0].sql


class TestMultipleSources:
    """Test multiple sources"""

    def test_multiple_sources(self):
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)

        source1 = KnowledgeSourceNode()
        source1.source_type = "text"
        source1.content = "Introduction text"

        source2 = KnowledgeSourceNode()
        source2.source_type = "file"
        source2.path = "./docs/guide.md"

        source3 = KnowledgeSourceNode()
        source3.source_type = "url"
        source3.url = "https://docs.example.com"

        node = KnowledgeNode()
        node.name = "combined"
        node.sources = [source1, source2, source3]

        executor.execute(node, runtime.execution_context)

        sources = runtime._knowledge_service.last_kwargs["sources"]
        assert len(sources) == 3
        assert sources[0].source_type == "text"
        assert sources[1].source_type == "file"
        assert sources[2].source_type == "url"

    def test_original_source_objects_not_mutated(self):
        """Databinding resolution must not mutate the AST's own source nodes
        (they could be re-executed on a later pass with different context)."""
        runtime = MockKnowledgeRuntime({"name": "Alice"})
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "text"
        source.content = "Hello {name}"

        node = KnowledgeNode()
        node.name = "greeting"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        assert source.content == "Hello {name}"


class TestChunkConfiguration:
    """Test chunk size and overlap configuration — passed as top-level
    kwargs to index_knowledge(); per-source overrides stay on the source
    object itself and are applied downstream by KnowledgeService."""

    def test_default_chunk_settings(self):
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "text"
        source.content = "Test content"

        node = KnowledgeNode()
        node.name = "test"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        kwargs = runtime._knowledge_service.last_kwargs
        assert kwargs["chunk_size"] == 500
        assert kwargs["chunk_overlap"] == 50

    def test_custom_chunk_settings(self):
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "text"
        source.content = "Test content"

        node = KnowledgeNode()
        node.name = "test"
        node.chunk_size = 1000
        node.chunk_overlap = 100
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        kwargs = runtime._knowledge_service.last_kwargs
        assert kwargs["chunk_size"] == 1000
        assert kwargs["chunk_overlap"] == 100

    def test_source_chunk_override_preserved(self):
        """Source-level overrides ride along on the source object itself —
        KnowledgeService._extract_source_text() applies them, not this executor."""
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "text"
        source.content = "Test content"
        source.chunk_size = 200
        source.chunk_overlap = 20

        node = KnowledgeNode()
        node.name = "test"
        node.chunk_size = 500
        node.chunk_overlap = 50
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        resolved_source = runtime._knowledge_service.last_kwargs["sources"][0]
        assert resolved_source.chunk_size == 200
        assert resolved_source.chunk_overlap == 20


class TestEmbeddingConfiguration:
    """Test embedding model configuration"""

    def test_default_embed_model(self):
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "text"
        source.content = "Test"

        node = KnowledgeNode()
        node.name = "test"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        assert runtime._knowledge_service.last_kwargs["embed_model"] == "nomic-embed-text"

    def test_custom_embed_model(self):
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "text"
        source.content = "Test"

        node = KnowledgeNode()
        node.name = "test"
        node.embed_model = "text-embedding-ada-002"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        assert runtime._knowledge_service.last_kwargs["embed_model"] == "text-embedding-ada-002"


class TestPersistence:
    """Test persistence options"""

    def test_persist_disabled_by_default(self):
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "text"
        source.content = "Test"

        node = KnowledgeNode()
        node.name = "test"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        assert runtime._knowledge_service.last_kwargs["persist"] is False

    def test_persist_enabled(self):
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "text"
        source.content = "Test"

        node = KnowledgeNode()
        node.name = "test"
        node.persist = True
        node.persist_path = "./data/chromadb"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        kwargs = runtime._knowledge_service.last_kwargs
        assert kwargs["persist"] is True
        assert kwargs["persist_path"] == "./data/chromadb"

    def test_rebuild_flag(self):
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "text"
        source.content = "Test"

        node = KnowledgeNode()
        node.name = "test"
        node.rebuild = True
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        assert runtime._knowledge_service.last_kwargs["rebuild"] is True


class TestResultStorage:
    """Test result storage"""

    def test_stores_knowledge_base_reference(self):
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "text"
        source.content = "Test"

        node = KnowledgeNode()
        node.name = "myKB"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        stored = runtime.execution_context.get_variable("myKB")
        assert stored["success"] is True
        assert stored["name"] == "myKB"

    def test_stores_info_metadata(self):
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)

        source1 = KnowledgeSourceNode()
        source1.source_type = "text"
        source1.content = "Text 1"

        source2 = KnowledgeSourceNode()
        source2.source_type = "file"
        source2.path = "./doc.md"

        node = KnowledgeNode()
        node.name = "docs"
        node.sources = [source1, source2]

        executor.execute(node, runtime.execution_context)

        info = runtime.execution_context.get_variable("docs_info")
        assert info["success"] is True
        assert info["name"] == "docs"

    def test_stores_knowledge_metadata_for_query_lookup(self):
        """_execute_knowledge_query() (component.py) reads
        _knowledge_{name} to get embed_model/model for later q:query
        datasource="knowledge:{name}" calls."""
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "text"
        source.content = "Test"

        node = KnowledgeNode()
        node.name = "docs"
        node.model = "phi3"
        node.embed_model = "nomic-embed-text"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        meta = runtime.execution_context.get_variable("_knowledge_docs")
        assert meta["embed_model"] == "nomic-embed-text"
        assert meta["model"] == "phi3"

    def test_indexes_into_runtime_knowledge_service_not_services_knowledge(self):
        """The bug this test guards against: indexing into a different
        KnowledgeService instance than the one q:query searches leaves
        every subsequent search silently empty."""
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "text"
        source.content = "Test"

        node = KnowledgeNode()
        node.name = "docs"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        assert runtime._knowledge_service.last_kwargs is not None
        runtime.services.knowledge.index_knowledge.assert_not_called()


class TestErrorHandling:
    """Test error handling"""

    def test_error_stores_failure_info(self):
        runtime = MockKnowledgeRuntime()
        runtime._knowledge_service.index_knowledge = MagicMock(
            side_effect=Exception("Embedding failed")
        )
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "text"
        source.content = "Test"

        node = KnowledgeNode()
        node.name = "test"
        node.sources = [source]

        with pytest.raises(ExecutorError, match="Knowledge base creation error"):
            executor.execute(node, runtime.execution_context)

        error_info = runtime.execution_context.get_variable("test_info")
        assert error_info["success"] is False
        assert "Embedding failed" in error_info["error"]
        assert error_info["name"] == "test"

        # The query path's graceful "still loading" fallback depends on this
        failed_meta = runtime.execution_context.get_variable("_knowledge_test")
        assert failed_meta["_failed"] is True

    def test_error_message_includes_details(self):
        runtime = MockKnowledgeRuntime()
        runtime._knowledge_service.index_knowledge = MagicMock(
            side_effect=Exception("ChromaDB connection failed")
        )
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "text"
        source.content = "Test"

        node = KnowledgeNode()
        node.name = "test"
        node.sources = [source]

        with pytest.raises(ExecutorError, match="ChromaDB connection failed"):
            executor.execute(node, runtime.execution_context)


class TestModelConfiguration:
    """Test LLM model configuration"""

    def test_model_passed_to_metadata(self):
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "text"
        source.content = "Test"

        node = KnowledgeNode()
        node.name = "test"
        node.model = "gpt-4"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        info = runtime.execution_context.get_variable("test_info")
        assert info["model"] == "gpt-4"

    def test_model_none_by_default(self):
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "text"
        source.content = "Test"

        node = KnowledgeNode()
        node.name = "test"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        info = runtime.execution_context.get_variable("test_info")
        assert info["model"] is None
