"""
Tests for KnowledgeExecutor - q:knowledge knowledge base creation and RAG

Coverage target: 21% -> 60%
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from runtime.executors.ai.knowledge_executor import KnowledgeExecutor
from runtime.executors.base import ExecutorError

# Import KnowledgeNode from the correct location
try:
    from core.features.knowledge_base.src.ast_node import KnowledgeNode, KnowledgeSourceNode
except ImportError:
    from core.features.knowledge_base.src import KnowledgeNode, KnowledgeSourceNode

# Import fixtures from conftest.py
from tests.unit.executors.conftest import MockRuntime, MockExecutionContext


# =============================================================================
# Mock Objects for Knowledge Service
# =============================================================================

class MockKnowledgeService:
    """Mock knowledge service"""

    def __init__(self):
        self.last_config = None
        self._results = {}

    def set_result(self, name: str, result: Dict):
        """Set mock result for knowledge base"""
        self._results[name] = result

    def create(self, kb_config: Dict) -> Dict:
        """Mock knowledge base creation"""
        self.last_config = kb_config
        name = kb_config.get('name', '')

        if name in self._results:
            return self._results[name]

        return {
            'name': name,
            'document_count': 1,
            'chunk_count': 10,
            'status': 'created'
        }


class MockKnowledgeRuntime(MockRuntime):
    """Extended mock runtime with knowledge service"""

    def __init__(self, variables: Dict[str, Any] = None):
        super().__init__(variables)
        self._knowledge_service = MockKnowledgeService()
        self._services = MagicMock()
        self._services.knowledge = self._knowledge_service

    @property
    def services(self):
        return self._services


# =============================================================================
# Test Classes
# =============================================================================

class TestKnowledgeExecutorBasic:
    """Basic functionality tests"""

    def test_handles_knowledge_node(self):
        """Test that KnowledgeExecutor handles KnowledgeNode"""
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)
        assert KnowledgeNode in executor.handles

    def test_handles_returns_list(self):
        """Test that handles returns a list"""
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)
        assert isinstance(executor.handles, list)
        assert len(executor.handles) == 1


class TestTextSource:
    """Test text source type"""

    def test_text_source_basic(self):
        """Test basic text source"""
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "text"
        source.content = "Quantum Framework is a declarative web framework"

        node = KnowledgeNode()
        node.name = "docs"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        config = runtime._knowledge_service.last_config
        assert config["name"] == "docs"
        assert len(config["sources"]) == 1
        assert config["sources"][0]["type"] == "text"
        assert config["sources"][0]["content"] == "Quantum Framework is a declarative web framework"

    def test_text_source_with_databinding(self):
        """Test text source with databinding"""
        runtime = MockKnowledgeRuntime({"projectName": "Quantum"})
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "text"
        source.content = "{projectName} Framework documentation"

        node = KnowledgeNode()
        node.name = "docs"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        config = runtime._knowledge_service.last_config
        assert config["sources"][0]["content"] == "Quantum Framework documentation"


class TestFileSource:
    """Test file source type"""

    def test_file_source_basic(self):
        """Test basic file source"""
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "file"
        source.path = "./docs/guide.md"

        node = KnowledgeNode()
        node.name = "guide"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        config = runtime._knowledge_service.last_config
        assert config["sources"][0]["type"] == "file"
        assert config["sources"][0]["path"] == "./docs/guide.md"

    def test_file_source_with_databinding(self):
        """Test file source with databinding"""
        runtime = MockKnowledgeRuntime({"docPath": "./custom/docs.md"})
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "file"
        source.path = "{docPath}"

        node = KnowledgeNode()
        node.name = "custom"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        config = runtime._knowledge_service.last_config
        assert config["sources"][0]["path"] == "./custom/docs.md"


class TestDirectorySource:
    """Test directory source type"""

    def test_directory_source_basic(self):
        """Test basic directory source"""
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

        config = runtime._knowledge_service.last_config
        assert config["sources"][0]["type"] == "directory"
        assert config["sources"][0]["path"] == "./docs/"
        assert config["sources"][0]["pattern"] == "*.md"

    def test_directory_source_default_pattern(self):
        """Test directory source with default pattern"""
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "directory"
        source.path = "./docs/"
        source.pattern = None  # Should default to *.md

        node = KnowledgeNode()
        node.name = "docs"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        config = runtime._knowledge_service.last_config
        assert config["sources"][0]["pattern"] == "*.md"


class TestURLSource:
    """Test URL source type"""

    def test_url_source_basic(self):
        """Test basic URL source"""
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "url"
        source.url = "https://docs.quantum.dev/guide"

        node = KnowledgeNode()
        node.name = "web_docs"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        config = runtime._knowledge_service.last_config
        assert config["sources"][0]["type"] == "url"
        assert config["sources"][0]["url"] == "https://docs.quantum.dev/guide"

    def test_url_source_with_databinding(self):
        """Test URL source with databinding"""
        runtime = MockKnowledgeRuntime({"docsUrl": "https://example.com/docs"})
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "url"
        source.url = "{docsUrl}"

        node = KnowledgeNode()
        node.name = "external"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        config = runtime._knowledge_service.last_config
        assert config["sources"][0]["url"] == "https://example.com/docs"


class TestQuerySource:
    """Test query source type"""

    def test_query_source_basic(self):
        """Test basic query source"""
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

        config = runtime._knowledge_service.last_config
        assert config["sources"][0]["type"] == "query"
        assert config["sources"][0]["datasource"] == "mydb"
        assert config["sources"][0]["sql"] == "SELECT title, content FROM articles"

    def test_query_source_with_databinding(self):
        """Test query source with databinding in SQL"""
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

        config = runtime._knowledge_service.last_config
        assert "tech" in config["sources"][0]["sql"]


class TestMultipleSources:
    """Test multiple sources"""

    def test_multiple_sources(self):
        """Test knowledge base with multiple sources"""
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

        config = runtime._knowledge_service.last_config
        assert len(config["sources"]) == 3
        assert config["sources"][0]["type"] == "text"
        assert config["sources"][1]["type"] == "file"
        assert config["sources"][2]["type"] == "url"


class TestChunkConfiguration:
    """Test chunk size and overlap configuration"""

    def test_default_chunk_settings(self):
        """Test default chunk settings"""
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "text"
        source.content = "Test content"

        node = KnowledgeNode()
        node.name = "test"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        config = runtime._knowledge_service.last_config
        assert config["chunk_size"] == 500
        assert config["chunk_overlap"] == 50

    def test_custom_chunk_settings(self):
        """Test custom chunk settings"""
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

        config = runtime._knowledge_service.last_config
        assert config["chunk_size"] == 1000
        assert config["chunk_overlap"] == 100

    def test_source_chunk_override(self):
        """Test source-level chunk override"""
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "text"
        source.content = "Test content"
        source.chunk_size = 200
        source.chunk_overlap = 20

        node = KnowledgeNode()
        node.name = "test"
        node.chunk_size = 500  # Parent setting
        node.chunk_overlap = 50  # Parent setting
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        config = runtime._knowledge_service.last_config
        # Source overrides parent
        assert config["sources"][0]["chunk_size"] == 200
        assert config["sources"][0]["chunk_overlap"] == 20


class TestEmbeddingConfiguration:
    """Test embedding model configuration"""

    def test_default_embed_model(self):
        """Test default embedding model"""
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "text"
        source.content = "Test"

        node = KnowledgeNode()
        node.name = "test"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        config = runtime._knowledge_service.last_config
        assert config["embed_model"] == "nomic-embed-text"

    def test_custom_embed_model(self):
        """Test custom embedding model"""
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

        config = runtime._knowledge_service.last_config
        assert config["embed_model"] == "text-embedding-ada-002"


class TestPersistence:
    """Test persistence options"""

    def test_persist_disabled_by_default(self):
        """Test persistence is disabled by default"""
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "text"
        source.content = "Test"

        node = KnowledgeNode()
        node.name = "test"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        config = runtime._knowledge_service.last_config
        assert config["persist"] is False

    def test_persist_enabled(self):
        """Test persistence enabled"""
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

        config = runtime._knowledge_service.last_config
        assert config["persist"] is True
        assert config["persist_path"] == "./data/chromadb"

    def test_rebuild_flag(self):
        """Test rebuild flag"""
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

        config = runtime._knowledge_service.last_config
        assert config["rebuild"] is True


class TestResultStorage:
    """Test result storage"""

    def test_stores_knowledge_base_reference(self):
        """Test that knowledge base reference is stored"""
        runtime = MockKnowledgeRuntime()
        runtime._knowledge_service.set_result("myKB", {
            'name': 'myKB',
            'document_count': 5,
            'chunk_count': 50,
            'status': 'created'
        })
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "text"
        source.content = "Test"

        node = KnowledgeNode()
        node.name = "myKB"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        stored = runtime.execution_context.get_variable("myKB")
        assert stored["name"] == "myKB"
        assert stored["document_count"] == 5

    def test_stores_info_metadata(self):
        """Test that info metadata is stored"""
        runtime = MockKnowledgeRuntime()
        runtime._knowledge_service.set_result("docs", {
            'name': 'docs',
            'document_count': 3,
            'chunk_count': 30
        })
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
        assert info["sources"] == 2
        assert info["documents"] == 3
        assert info["chunks"] == 30


class TestErrorHandling:
    """Test error handling"""

    def test_error_stores_failure_info(self):
        """Test that error stores failure info"""
        runtime = MockKnowledgeRuntime()
        runtime._knowledge_service.create = MagicMock(side_effect=Exception("Embedding failed"))
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

    def test_error_message_includes_details(self):
        """Test that error message includes details"""
        runtime = MockKnowledgeRuntime()
        runtime._knowledge_service.create = MagicMock(side_effect=Exception("ChromaDB connection failed"))
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

    def test_model_passed(self):
        """Test that model is passed to config"""
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

        config = runtime._knowledge_service.last_config
        assert config["model"] == "gpt-4"

    def test_model_none_by_default(self):
        """Test that model is None by default"""
        runtime = MockKnowledgeRuntime()
        executor = KnowledgeExecutor(runtime)

        source = KnowledgeSourceNode()
        source.source_type = "text"
        source.content = "Test"

        node = KnowledgeNode()
        node.name = "test"
        node.sources = [source]

        executor.execute(node, runtime.execution_context)

        config = runtime._knowledge_service.last_config
        assert config["model"] is None

