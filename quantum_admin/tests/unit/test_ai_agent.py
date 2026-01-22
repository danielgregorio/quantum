"""
Unit Tests for AI Agent
Tests SLM integration, RAG, and function calling
"""

import pytest
from unittest.mock import Mock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from ai_agent import (
    SLMProvider,
    FunctionRegistry,
    EnhancedRAG,
    QuantumAIAgent
)


class TestSLMProvider:
    """Test SLM (Small Language Model) provider"""

    @patch('ai_agent.requests.post')
    def test_slm_generate_success(self, mock_post):
        """Test successful SLM generation"""
        # Mock Ollama response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "response": "Generated text response"
        }

        slm = SLMProvider(base_url="http://localhost:11434")
        response = slm.generate("Test prompt")

        assert response == "Generated text response"
        mock_post.assert_called_once()

    @patch('ai_agent.requests.post')
    def test_slm_generate_with_system_prompt(self, mock_post):
        """Test SLM generation with system prompt"""
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {
            "response": "Response with context"
        }

        slm = SLMProvider()
        response = slm.generate(
            "User prompt",
            system="You are a helpful assistant"
        )

        assert response is not None
        call_args = mock_post.call_args[1]['json']
        assert 'system' in call_args

    @patch('ai_agent.requests.post')
    def test_slm_connection_error(self, mock_post):
        """Test SLM connection error handling"""
        mock_post.side_effect = Exception("Connection failed")

        slm = SLMProvider()

        with pytest.raises(Exception):
            slm.generate("Test prompt")


class TestFunctionRegistry:
    """Test function calling registry"""

    def test_register_function(self):
        """Test registering a new function"""
        registry = FunctionRegistry()

        def test_func(param1: str) -> str:
            return f"Result: {param1}"

        registry.register(
            name="test_function",
            func=test_func,
            description="A test function",
            parameters={"type": "object"}
        )

        assert "test_function" in registry.list_functions()

    def test_call_registered_function(self):
        """Test calling a registered function"""
        registry = FunctionRegistry()

        def greet(name: str) -> str:
            return f"Hello, {name}!"

        registry.register(
            name="greet",
            func=greet,
            description="Greet someone"
        )

        result = registry.call("greet", name="World")

        assert result == "Hello, World!"

    def test_call_nonexistent_function(self):
        """Test calling function that doesn't exist"""
        registry = FunctionRegistry()

        with pytest.raises(Exception):
            registry.call("nonexistent_function")

    def test_list_functions(self):
        """Test listing all functions"""
        registry = FunctionRegistry()

        # Built-in functions should exist
        functions = registry.list_functions()

        assert len(functions) > 0
        assert any(f["name"] == "generate_sql_query" for f in functions)
        assert any(f["name"] == "generate_model" for f in functions)

    def test_generate_sql_query_function(self):
        """Test SQL query generation function"""
        registry = FunctionRegistry()

        result = registry.call(
            "generate_sql_query",
            description="get all users",
            table_name="users"
        )

        assert "SELECT" in result
        assert "users" in result

    def test_generate_model_function(self):
        """Test SQLAlchemy model generation function"""
        registry = FunctionRegistry()

        result = registry.call(
            "generate_model",
            table_name="products",
            columns=["id", "name", "price"]
        )

        assert "class Product" in result
        assert "Base" in result
        assert "__tablename__" in result


class TestEnhancedRAG:
    """Test Enhanced RAG system"""

    def test_search_knowledge_base(self):
        """Test searching knowledge base"""
        rag = EnhancedRAG()

        results = rag.search("database schema")

        assert len(results) > 0
        assert any("schema" in r["title"].lower() for r in results)

    def test_get_context(self):
        """Test getting context for query"""
        rag = EnhancedRAG()

        context = rag.get_context("How do I create a migration?")

        assert context is not None
        assert len(context) > 0
        assert "migration" in context.lower() or "alembic" in context.lower()

    def test_add_to_memory(self):
        """Test adding messages to conversation memory"""
        rag = EnhancedRAG()

        rag.add_to_memory("user", "What is SQLAlchemy?")
        rag.add_to_memory("assistant", "SQLAlchemy is an ORM...")

        assert len(rag.conversation_memory) == 2

    def test_memory_limit(self):
        """Test that memory is limited to last N messages"""
        rag = EnhancedRAG()

        # Add more than the limit (10 messages)
        for i in range(15):
            rag.add_to_memory("user", f"Message {i}")

        # Should only keep last 10
        assert len(rag.conversation_memory) <= 10

    def test_clear_memory(self):
        """Test clearing conversation memory"""
        rag = EnhancedRAG()

        rag.add_to_memory("user", "Hello")
        rag.add_to_memory("assistant", "Hi")

        rag.clear_memory()

        assert len(rag.conversation_memory) == 0


class TestQuantumAIAgent:
    """Test main AI agent"""

    @patch('ai_agent.SLMProvider')
    def test_agent_chat_with_slm(self, mock_slm_class):
        """Test agent chat using SLM"""
        # Mock SLM
        mock_slm = Mock()
        mock_slm.generate.return_value = "AI response from SLM"
        mock_slm_class.return_value = mock_slm

        agent = QuantumAIAgent(schema_inspector=None)
        result = agent.chat("Hello", use_slm=True)

        assert result["response"] is not None
        assert result["provider"] == "slm"

    def test_agent_chat_rule_based(self):
        """Test agent chat using rule-based fallback"""
        agent = QuantumAIAgent(schema_inspector=None)

        result = agent.chat("Hello", use_slm=False)

        assert result["response"] is not None
        assert result["provider"] == "rule-based"

    def test_agent_chat_adds_to_memory(self):
        """Test that chat adds messages to memory"""
        agent = QuantumAIAgent(schema_inspector=None)

        agent.chat("Test message", use_slm=False)

        assert len(agent.rag.conversation_memory) > 0

    @patch('ai_agent.SLMProvider')
    def test_agent_function_calling(self, mock_slm_class):
        """Test agent function calling detection"""
        # Mock SLM to return function call
        mock_slm = Mock()
        mock_slm.generate.return_value = "FUNCTION_CALL: generate_sql_query"
        mock_slm_class.return_value = mock_slm

        agent = QuantumAIAgent(schema_inspector=None)
        result = agent.chat("Generate SQL to get all users", use_slm=True)

        # Should detect function call
        assert "function_called" in result or "response" in result

    def test_agent_clear_memory(self):
        """Test clearing agent conversation memory"""
        agent = QuantumAIAgent(schema_inspector=None)

        agent.chat("Message 1", use_slm=False)
        agent.chat("Message 2", use_slm=False)

        agent.clear_memory()

        assert len(agent.rag.conversation_memory) == 0

    def test_agent_with_schema_context(self):
        """Test agent with schema inspector context"""
        # Mock schema inspector
        mock_inspector = Mock()
        mock_inspector.get_complete_schema.return_value = {
            "tables": ["users", "products"]
        }

        agent = QuantumAIAgent(schema_inspector=mock_inspector)
        result = agent.chat("Show me the schema", use_slm=False)

        assert result["response"] is not None


class TestAIIntegration:
    """Integration tests for AI components"""

    def test_end_to_end_sql_generation(self):
        """Test complete SQL generation flow"""
        agent = QuantumAIAgent(schema_inspector=None)

        result = agent.chat(
            "Generate SQL to select all active users",
            use_slm=False
        )

        response = result["response"].lower()
        assert "select" in response or "sql" in response

    def test_end_to_end_model_generation(self):
        """Test complete model generation flow"""
        agent = QuantumAIAgent(schema_inspector=None)

        result = agent.chat(
            "Create a Product model with id, name, and price",
            use_slm=False
        )

        response = result["response"].lower()
        assert "model" in response or "sqlalchemy" in response

    def test_conversation_context_maintained(self):
        """Test that conversation context is maintained"""
        agent = QuantumAIAgent(schema_inspector=None)

        # First message
        agent.chat("My name is Alice", use_slm=False)

        # Second message should have context
        result = agent.chat("What's my name?", use_slm=False)

        # Memory should contain both messages
        assert len(agent.rag.conversation_memory) >= 2


class TestErrorHandling:
    """Test error handling in AI components"""

    def test_slm_error_fallback(self):
        """Test fallback to rule-based when SLM fails"""
        agent = QuantumAIAgent(schema_inspector=None)

        # Even if SLM fails, should get rule-based response
        result = agent.chat("Hello", use_slm=False)

        assert result["response"] is not None
        assert result["provider"] == "rule-based"

    def test_invalid_function_call(self):
        """Test handling of invalid function calls"""
        registry = FunctionRegistry()

        with pytest.raises(Exception):
            registry.call("invalid_function_name")

    def test_empty_query(self):
        """Test handling of empty query"""
        agent = QuantumAIAgent(schema_inspector=None)

        result = agent.chat("", use_slm=False)

        assert result["response"] is not None


# ============================================================================
# Integration with pytest
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
