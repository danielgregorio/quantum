"""
Tests for LLMExecutor - q:llm LLM invocation

Coverage target: 21% -> 60%
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
from typing import Any, Dict, List

from runtime.executors.ai.llm_executor import LLMExecutor
from runtime.executors.base import ExecutorError
from core.ast_nodes import LLMNode

# Import fixtures from conftest.py
from tests.unit.executors.conftest import MockRuntime, MockExecutionContext


# =============================================================================
# Mock Objects for LLM Service
# =============================================================================

class MockLLMService:
    """Mock LLM service"""

    def __init__(self):
        self.last_model = None
        self.last_messages = None
        self.last_options = None
        self._responses = {}

    def set_response(self, model: str, response: str):
        """Set mock response for model"""
        self._responses[model] = response

    def invoke(self, model: str, messages: List[Dict], endpoint: str = None,
               options: Dict = None, response_format: str = "text",
               cache: bool = False, timeout: int = None) -> str:
        """Mock LLM invoke"""
        self.last_model = model
        self.last_messages = messages
        self.last_options = options

        if model in self._responses:
            return self._responses[model]

        return f"Mock response from {model}"


class MockLLMRuntime(MockRuntime):
    """Extended mock runtime with LLM service"""

    def __init__(self, variables: Dict[str, Any] = None):
        super().__init__(variables)
        self._llm_service = MockLLMService()
        self._services = MagicMock()
        self._services.llm = self._llm_service

    @property
    def services(self):
        return self._services


# =============================================================================
# Mock Message Node
# =============================================================================

@dataclass
class MockMessageNode:
    """Mock message for chat mode"""
    role: str
    content: str


# =============================================================================
# Test Classes
# =============================================================================

class TestLLMExecutorBasic:
    """Basic functionality tests"""

    def test_handles_llm_node(self):
        """Test that LLMExecutor handles LLMNode"""
        runtime = MockLLMRuntime()
        executor = LLMExecutor(runtime)
        assert LLMNode in executor.handles

    def test_handles_returns_list(self):
        """Test that handles returns a list"""
        runtime = MockLLMRuntime()
        executor = LLMExecutor(runtime)
        assert isinstance(executor.handles, list)
        assert len(executor.handles) == 1


class TestCompletionMode:
    """Test completion mode (single prompt)"""

    def test_simple_prompt(self):
        """Test simple prompt completion"""
        runtime = MockLLMRuntime()
        runtime._llm_service.set_response("phi3", "Hello there!")
        executor = LLMExecutor(runtime)

        node = LLMNode("greeting")
        node.prompt = "Say hello"

        result = executor.execute(node, runtime.execution_context)

        assert result == "Hello there!"
        assert runtime._llm_service.last_model == "phi3"

    def test_prompt_with_databinding(self):
        """Test prompt with variable interpolation"""
        runtime = MockLLMRuntime({"userName": "Alice"})
        runtime._llm_service.set_response("phi3", "Hello Alice!")
        executor = LLMExecutor(runtime)

        node = LLMNode("greeting")
        node.prompt = "Say hello to {userName}"

        executor.execute(node, runtime.execution_context)

        # Check that databinding was applied
        messages = runtime._llm_service.last_messages
        assert len(messages) == 1
        assert "Alice" in messages[0]["content"]

    def test_custom_model(self):
        """Test using custom model"""
        runtime = MockLLMRuntime()
        runtime._llm_service.set_response("llama3", "Response from llama")
        executor = LLMExecutor(runtime)

        node = LLMNode("result")
        node.model = "llama3"
        node.prompt = "Test prompt"

        executor.execute(node, runtime.execution_context)

        assert runtime._llm_service.last_model == "llama3"

    def test_default_model(self):
        """Test that default model is phi3"""
        runtime = MockLLMRuntime()
        executor = LLMExecutor(runtime)

        node = LLMNode("result")
        node.prompt = "Test"

        executor.execute(node, runtime.execution_context)

        assert runtime._llm_service.last_model == "phi3"


class TestChatMode:
    """Test chat mode (messages array)"""

    def test_chat_messages(self):
        """Test chat with multiple messages"""
        runtime = MockLLMRuntime()
        runtime._llm_service.set_response("phi3", "Chat response")
        executor = LLMExecutor(runtime)

        node = LLMNode("chat")
        node.messages = [
            MockMessageNode("user", "What is 2+2?"),
            MockMessageNode("assistant", "2+2 equals 4"),
            MockMessageNode("user", "And what is 3+3?")
        ]

        executor.execute(node, runtime.execution_context)

        messages = runtime._llm_service.last_messages
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"

    def test_chat_with_databinding(self):
        """Test chat messages with databinding"""
        runtime = MockLLMRuntime({"question": "What is the weather?"})
        executor = LLMExecutor(runtime)

        node = LLMNode("chat")
        node.messages = [MockMessageNode("user", "{question}")]

        executor.execute(node, runtime.execution_context)

        messages = runtime._llm_service.last_messages
        assert messages[0]["content"] == "What is the weather?"


class TestSystemMessage:
    """Test system message handling"""

    def test_system_message_prepended(self):
        """Test that system message is prepended"""
        runtime = MockLLMRuntime()
        executor = LLMExecutor(runtime)

        node = LLMNode("result")
        node.system = "You are a helpful assistant"
        node.prompt = "Help me"

        executor.execute(node, runtime.execution_context)

        messages = runtime._llm_service.last_messages
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a helpful assistant"
        assert messages[1]["role"] == "user"

    def test_system_with_databinding(self):
        """Test system message with databinding"""
        runtime = MockLLMRuntime({"role": "Python expert"})
        executor = LLMExecutor(runtime)

        node = LLMNode("result")
        node.system = "You are a {role}"
        node.prompt = "Help me"

        executor.execute(node, runtime.execution_context)

        messages = runtime._llm_service.last_messages
        assert messages[0]["content"] == "You are a Python expert"


class TestOptions:
    """Test LLM options"""

    def test_temperature_option(self):
        """Test temperature setting"""
        runtime = MockLLMRuntime()
        executor = LLMExecutor(runtime)

        node = LLMNode("result")
        node.prompt = "Test"
        node.temperature = 0.7

        executor.execute(node, runtime.execution_context)

        assert runtime._llm_service.last_options["temperature"] == 0.7

    def test_max_tokens_option(self):
        """Test max tokens setting"""
        runtime = MockLLMRuntime()
        executor = LLMExecutor(runtime)

        node = LLMNode("result")
        node.prompt = "Test"
        node.max_tokens = 100

        executor.execute(node, runtime.execution_context)

        assert runtime._llm_service.last_options["max_tokens"] == 100

    def test_combined_options(self):
        """Test multiple options together"""
        runtime = MockLLMRuntime()
        executor = LLMExecutor(runtime)

        node = LLMNode("result")
        node.prompt = "Test"
        node.temperature = 0.5
        node.max_tokens = 200

        executor.execute(node, runtime.execution_context)

        options = runtime._llm_service.last_options
        assert options["temperature"] == 0.5
        assert options["max_tokens"] == 200


class TestEndpoint:
    """Test custom endpoint"""

    def test_custom_endpoint(self):
        """Test custom LLM endpoint"""
        runtime = MockLLMRuntime()
        captured = {}

        def mock_invoke(**kwargs):
            captured.update(kwargs)
            return "response"

        runtime._llm_service.invoke = mock_invoke
        executor = LLMExecutor(runtime)

        node = LLMNode("result")
        node.endpoint = "http://localhost:11434"
        node.prompt = "Test"

        executor.execute(node, runtime.execution_context)

        assert captured["endpoint"] == "http://localhost:11434"

    def test_endpoint_with_databinding(self):
        """Test endpoint with databinding"""
        runtime = MockLLMRuntime({"llmUrl": "http://custom:8080"})
        captured = {}

        def mock_invoke(**kwargs):
            captured.update(kwargs)
            return "response"

        runtime._llm_service.invoke = mock_invoke
        executor = LLMExecutor(runtime)

        node = LLMNode("result")
        node.endpoint = "{llmUrl}"
        node.prompt = "Test"

        executor.execute(node, runtime.execution_context)

        assert captured["endpoint"] == "http://custom:8080"


class TestResultStorage:
    """Test result storage"""

    def test_stores_response(self):
        """Test that response is stored in named variable"""
        runtime = MockLLMRuntime()
        runtime._llm_service.set_response("phi3", "The answer is 42")
        executor = LLMExecutor(runtime)

        node = LLMNode("answer")
        node.prompt = "What is the meaning of life?"

        executor.execute(node, runtime.execution_context)

        stored = runtime.execution_context.get_variable("answer")
        assert stored == "The answer is 42"

    def test_stores_result_metadata(self):
        """Test that result metadata is stored"""
        runtime = MockLLMRuntime()
        runtime._llm_service.set_response("phi3", "response")
        executor = LLMExecutor(runtime)

        node = LLMNode("result")
        node.prompt = "Test"

        executor.execute(node, runtime.execution_context)

        metadata = runtime.execution_context.get_variable("result_result")
        assert metadata["success"] is True
        assert metadata["response"] == "response"
        assert metadata["model"] == "phi3"


class TestResponseFormat:
    """Test response format options"""

    def test_json_response_format(self):
        """Test JSON response format"""
        runtime = MockLLMRuntime()
        captured = {}

        def mock_invoke(**kwargs):
            captured.update(kwargs)
            return '{"name": "test"}'

        runtime._llm_service.invoke = mock_invoke
        executor = LLMExecutor(runtime)

        node = LLMNode("data")
        node.prompt = "Extract data"
        node.response_format = "json"

        executor.execute(node, runtime.execution_context)

        assert captured["response_format"] == "json"

    def test_default_text_format(self):
        """Test default text response format"""
        runtime = MockLLMRuntime()
        captured = {}

        def mock_invoke(**kwargs):
            captured.update(kwargs)
            return "text response"

        runtime._llm_service.invoke = mock_invoke
        executor = LLMExecutor(runtime)

        node = LLMNode("result")
        node.prompt = "Test"

        executor.execute(node, runtime.execution_context)

        assert captured["response_format"] == "text"


class TestCaching:
    """Test caching options"""

    def test_cache_flag_passed(self):
        """Test that cache flag is passed to service"""
        runtime = MockLLMRuntime()
        captured = {}

        def mock_invoke(**kwargs):
            captured.update(kwargs)
            return "response"

        runtime._llm_service.invoke = mock_invoke
        executor = LLMExecutor(runtime)

        node = LLMNode("result")
        node.prompt = "Test"
        node.cache = True

        executor.execute(node, runtime.execution_context)

        assert captured["cache"] is True

    def test_timeout_passed(self):
        """Test that timeout is passed to service"""
        runtime = MockLLMRuntime()
        captured = {}

        def mock_invoke(**kwargs):
            captured.update(kwargs)
            return "response"

        runtime._llm_service.invoke = mock_invoke
        executor = LLMExecutor(runtime)

        node = LLMNode("result")
        node.prompt = "Test"
        node.timeout = 30000

        executor.execute(node, runtime.execution_context)

        assert captured["timeout"] == 30000


class TestErrorHandling:
    """Test error handling"""

    def test_error_stores_failure_result(self):
        """Test that error stores failure result"""
        runtime = MockLLMRuntime()
        runtime._llm_service.invoke = MagicMock(side_effect=Exception("LLM error"))
        executor = LLMExecutor(runtime)

        node = LLMNode("result")
        node.model = "test-model"
        node.prompt = "Test"

        with pytest.raises(ExecutorError, match="LLM execution error"):
            executor.execute(node, runtime.execution_context)

        # Check error result was stored
        error_result = runtime.execution_context.get_variable("result_result")
        assert error_result["success"] is False
        assert "LLM error" in error_result["error"]
        assert error_result["model"] == "test-model"

    def test_error_message_includes_details(self):
        """Test that error message includes details"""
        runtime = MockLLMRuntime()
        runtime._llm_service.invoke = MagicMock(side_effect=Exception("Connection refused"))
        executor = LLMExecutor(runtime)

        node = LLMNode("result")
        node.prompt = "Test"

        with pytest.raises(ExecutorError, match="Connection refused"):
            executor.execute(node, runtime.execution_context)
