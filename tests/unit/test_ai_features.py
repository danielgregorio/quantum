"""
Unit Tests for AI Features (LLM, RAG, Agent)

Tests both old and new (unified) syntax:
- Old: <q:llm-generate>, <q:search>, <q:agent-ask>
- New: <q:query datasource="ai">, <q:query datasource="docs">
"""

import pytest
import sys
from pathlib import Path

# Fix imports
sys.path.append(str(Path(__file__).parent.parent.parent / 'src'))

from core.parser import QuantumParser, QuantumParseError
from core.ast_nodes import ComponentNode, ApplicationNode
from core.features.llm.src import LLMNode, LLMGenerateNode
from core.features.rag.src import KnowledgeNode, SearchNode
from core.features.agents.src import AgentNode, AgentAskNode


class TestLLMFeatureOldSyntax:
    """Test old LLM syntax (q:llm, q:llm-generate)"""

    def test_parse_llm_definition(self, tmp_path):
        """Test parsing <q:llm> definition"""
        component_file = tmp_path / "test.q"
        component_file.write_text("""
        <q:component name="TestLLM">
            <q:llm id="ai" model="llama3" provider="ollama" temperature="0.7">
                <default-prompt>You are helpful</default-prompt>
            </q:llm>
        </q:component>
        """)

        parser = QuantumParser()
        ast = parser.parse_file(str(component_file))

        assert isinstance(ast, ComponentNode)
        assert len(ast.statements) == 1

        llm_node = ast.statements[0]
        assert isinstance(llm_node, LLMNode)
        assert llm_node.llm_id == "ai"
        assert llm_node.model == "llama3"
        assert llm_node.provider == "ollama"
        assert llm_node.temperature == 0.7
        assert "You are helpful" in llm_node.system_prompt

    def test_parse_llm_generate(self, tmp_path):
        """Test parsing <q:llm-generate>"""
        component_file = tmp_path / "test.q"
        component_file.write_text("""
        <q:component name="TestGenerate">
            <q:llm-generate llm="ai" prompt="Explain quantum computing" result="answer" />
        </q:component>
        """)

        parser = QuantumParser()
        ast = parser.parse_file(str(component_file))

        assert isinstance(ast, ComponentNode)
        assert len(ast.statements) == 1

        gen_node = ast.statements[0]
        assert isinstance(gen_node, LLMGenerateNode)
        assert gen_node.llm_id == "ai"
        assert gen_node.prompt == "Explain quantum computing"
        assert gen_node.result_var == "answer"


class TestRAGFeatureOldSyntax:
    """Test old RAG syntax (q:knowledge, q:search)"""

    def test_parse_knowledge_definition(self, tmp_path):
        """Test parsing <q:knowledge> definition"""
        component_file = tmp_path / "test.q"
        component_file.write_text("""
        <q:component name="TestKnowledge">
            <q:knowledge id="docs" source="./docs/*.md"
                embedding="ollama" chunk_size="500" />
        </q:component>
        """)

        parser = QuantumParser()
        ast = parser.parse_file(str(component_file))

        assert isinstance(ast, ComponentNode)
        assert len(ast.statements) == 1

        kb_node = ast.statements[0]
        assert isinstance(kb_node, KnowledgeNode)
        assert kb_node.knowledge_id == "docs"
        assert kb_node.source == "./docs/*.md"
        assert kb_node.embedding == "ollama"
        assert kb_node.chunk_size == 500

    def test_parse_search(self, tmp_path):
        """Test parsing <q:search>"""
        component_file = tmp_path / "test.q"
        component_file.write_text("""
        <q:component name="TestSearch">
            <q:search knowledge="docs" query="authentication" result="results" top_k="5" />
        </q:component>
        """)

        parser = QuantumParser()
        ast = parser.parse_file(str(component_file))

        assert isinstance(ast, ComponentNode)
        assert len(ast.statements) == 1

        search_node = ast.statements[0]
        assert isinstance(search_node, SearchNode)
        assert search_node.knowledge_id == "docs"
        assert search_node.query == "authentication"
        assert search_node.result_var == "results"
        assert search_node.top_k == 5


class TestUnifiedQuerySyntax:
    """Test new unified query syntax - THE MAGIC!"""

    def test_parse_datasource_llm(self, tmp_path):
        """Test parsing <datasource type="llm">"""
        app_file = tmp_path / "Application.q"
        app_file.write_text("""
        <q:application id="app" type="html">
            <datasource id="ai" type="llm" provider="ollama" model="llama3" temperature="0.7">
                <system-prompt>You are helpful</system-prompt>
            </datasource>
        </q:application>
        """)

        parser = QuantumParser()
        ast = parser.parse_file(str(app_file))

        assert isinstance(ast, ApplicationNode)
        assert "ai" in ast.datasources

        ds = ast.datasources["ai"]
        assert ds.datasource_id == "ai"
        assert ds.datasource_type == "llm"
        assert ds.provider == "ollama"
        assert ds.model == "llama3"
        assert ds.temperature == 0.7
        assert "You are helpful" in ds.system_prompt

    def test_parse_datasource_knowledge(self, tmp_path):
        """Test parsing <datasource type="knowledge">"""
        app_file = tmp_path / "Application.q"
        app_file.write_text("""
        <q:application id="app" type="html">
            <datasource id="docs" type="knowledge"
                source="./docs/*.md"
                embedding="ollama"
                chunk_size="600"
                chunk_overlap="100" />
        </q:application>
        """)

        parser = QuantumParser()
        ast = parser.parse_file(str(app_file))

        assert isinstance(ast, ApplicationNode)
        assert "docs" in ast.datasources

        ds = ast.datasources["docs"]
        assert ds.datasource_id == "docs"
        assert ds.datasource_type == "knowledge"
        assert ds.source == "./docs/*.md"
        assert ds.embedding == "ollama"
        assert ds.chunk_size == 600
        assert ds.chunk_overlap == 100

    def test_query_converts_to_llm_generate(self, tmp_path):
        """Test q:query with datasource=llm converts to LLMGenerateNode"""
        # First create Application with datasource
        app_file = tmp_path / "Application.q"
        app_file.write_text("""
        <q:application id="app" type="html">
            <datasource id="ai" type="llm" model="llama3" />
        </q:application>
        """)

        # Parse application first to set current_application
        parser = QuantumParser()
        app_ast = parser.parse_file(str(app_file))

        # Now parse component that uses unified syntax
        component_file = tmp_path / "test.q"
        component_file.write_text("""
        <q:component name="UnifiedLLM">
            <q:query name="answer" datasource="ai">
                Explain quantum computing
            </q:query>
        </q:component>
        """)

        comp_ast = parser.parse_file(str(component_file))

        assert isinstance(comp_ast, ComponentNode)
        assert len(comp_ast.statements) == 1

        # ✨ MAGIC: Should be converted to LLMGenerateNode!
        statement = comp_ast.statements[0]
        assert isinstance(statement, LLMGenerateNode)
        assert statement.llm_id == "ai"
        assert "Explain quantum computing" in statement.prompt
        assert statement.result_var == "answer"

    def test_query_converts_to_search_node(self, tmp_path):
        """Test q:query with datasource=knowledge converts to SearchNode"""
        # First create Application with datasource
        app_file = tmp_path / "Application.q"
        app_file.write_text("""
        <q:application id="app" type="html">
            <datasource id="docs" type="knowledge" source="./docs/*.md" />
        </q:application>
        """)

        # Parse application first
        parser = QuantumParser()
        app_ast = parser.parse_file(str(app_file))

        # Now parse component with unified syntax
        component_file = tmp_path / "test.q"
        component_file.write_text("""
        <q:component name="UnifiedRAG">
            <q:query name="results" datasource="docs" top_k="10">
                authentication
            </q:query>
        </q:component>
        """)

        comp_ast = parser.parse_file(str(component_file))

        assert isinstance(comp_ast, ComponentNode)
        assert len(comp_ast.statements) == 1

        # ✨ MAGIC: Should be converted to SearchNode!
        statement = comp_ast.statements[0]
        assert isinstance(statement, SearchNode)
        assert statement.knowledge_id == "docs"
        assert "authentication" in statement.query
        assert statement.result_var == "results"
        assert statement.top_k == 10

    def test_unified_syntax_with_attributes(self, tmp_path):
        """Test unified syntax preserves type-specific attributes"""
        app_file = tmp_path / "Application.q"
        app_file.write_text("""
        <q:application id="app" type="html">
            <datasource id="ai" type="llm" model="llama3" />
            <datasource id="docs" type="knowledge" source="./docs/*.md" />
        </q:application>
        """)

        parser = QuantumParser()
        app_ast = parser.parse_file(str(app_file))

        # Test LLM with cache
        llm_component = tmp_path / "llm.q"
        llm_component.write_text("""
        <q:component name="CachedLLM">
            <q:query name="answer" datasource="ai" cache="true" stream="true">
                Prompt here
            </q:query>
        </q:component>
        """)

        llm_ast = parser.parse_file(str(llm_component))
        llm_node = llm_ast.statements[0]
        assert isinstance(llm_node, LLMGenerateNode)
        assert llm_node.cache == True
        assert llm_node.stream == True

        # Test RAG with min_score
        rag_component = tmp_path / "rag.q"
        rag_component.write_text("""
        <q:component name="FilteredRAG">
            <q:query name="results" datasource="docs" top_k="3" min_score="0.8">
                query
            </q:query>
        </q:component>
        """)

        rag_ast = parser.parse_file(str(rag_component))
        rag_node = rag_ast.statements[0]
        assert isinstance(rag_node, SearchNode)
        assert rag_node.top_k == 3
        assert rag_node.threshold == 0.8


class TestMixedSyntax:
    """Test that old and new syntax can coexist"""

    def test_both_syntaxes_in_same_component(self, tmp_path):
        """Test using both old and new syntax together"""
        app_file = tmp_path / "Application.q"
        app_file.write_text("""
        <q:application id="app" type="html">
            <datasource id="ai" type="llm" model="llama3" />
        </q:application>
        """)

        parser = QuantumParser()
        app_ast = parser.parse_file(str(app_file))

        component_file = tmp_path / "mixed.q"
        component_file.write_text("""
        <q:component name="MixedSyntax">
            <!-- Old syntax -->
            <q:llm id="local" model="codellama" />
            <q:llm-generate llm="local" prompt="Write code" result="code" />

            <!-- New unified syntax -->
            <q:query name="explanation" datasource="ai">
                Explain this code
            </q:query>
        </q:component>
        """)

        comp_ast = parser.parse_file(str(component_file))

        assert isinstance(comp_ast, ComponentNode)
        assert len(comp_ast.statements) == 3

        # Old syntax
        assert isinstance(comp_ast.statements[0], LLMNode)
        assert isinstance(comp_ast.statements[1], LLMGenerateNode)

        # New syntax (converted)
        assert isinstance(comp_ast.statements[2], LLMGenerateNode)


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_query_without_datasource_definition(self, tmp_path):
        """Test q:query when datasource not defined in Application"""
        # No Application.q, parser.current_application is None
        component_file = tmp_path / "test.q"
        component_file.write_text("""
        <q:component name="NoApp">
            <q:query name="result" datasource="undefined">
                query
            </q:query>
        </q:component>
        """)

        parser = QuantumParser()
        # Should not crash, just return regular QueryNode (SQL)
        ast = parser.parse_file(str(component_file))
        assert isinstance(ast, ComponentNode)

    def test_datasource_missing_required_attrs(self, tmp_path):
        """Test datasource without required attributes"""
        app_file = tmp_path / "Application.q"
        app_file.write_text("""
        <q:application id="app" type="html">
            <datasource id="broken" />
        </q:application>
        """)

        parser = QuantumParser()
        with pytest.raises(QuantumParseError, match="requires 'type' attribute"):
            parser.parse_file(str(app_file))

    def test_multiple_datasources(self, tmp_path):
        """Test multiple datasources of different types"""
        app_file = tmp_path / "Application.q"
        app_file.write_text("""
        <q:application id="app" type="html">
            <datasource id="db" type="postgres" host="localhost" />
            <datasource id="ai" type="llm" model="llama3" />
            <datasource id="docs" type="knowledge" source="./docs/*.md" />
            <datasource id="cache" type="redis" host="localhost" />
        </q:application>
        """)

        parser = QuantumParser()
        ast = parser.parse_file(str(app_file))

        assert isinstance(ast, ApplicationNode)
        assert len(ast.datasources) == 4
        assert "db" in ast.datasources
        assert "ai" in ast.datasources
        assert "docs" in ast.datasources
        assert "cache" in ast.datasources

        # Check types
        assert ast.datasources["db"].datasource_type == "postgres"
        assert ast.datasources["ai"].datasource_type == "llm"
        assert ast.datasources["docs"].datasource_type == "knowledge"
        assert ast.datasources["cache"].datasource_type == "redis"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
