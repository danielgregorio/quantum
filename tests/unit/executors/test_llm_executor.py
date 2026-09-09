"""
Tests for LLMExecutor - q:llm LLM invocation

Rewritten 2026-09-07: the previous version of this file mocked an `invoke()`
method that never existed on the real LLMService (which only ever had
generate()/chat()) — see FULL_AUDIT_2026-09.md, Cluster B. These tests mock
the real method names and call shapes.
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from quantum.runtime.executors.ai.llm_executor import LLMExecutor
from quantum.runtime.executors.base import ExecutorError
from quantum.core.ast_nodes import LLMNode

# Import fixtures from conftest.py
from tests.unit.executors.conftest import MockRuntime, MockExecutionContext


# =============================================================================
# Mock Objects for LLM Service — mirrors the real LLMService interface
# =============================================================================

class MockLLMService:
    """Mock LLM service matching the real generate()/chat() signatures."""

    def __init__(self):
        self.last_call: Optional[str] = None
        self.last_kwargs: Optional[Dict[str, Any]] = None
        self._responses: Dict[str, str] = {}

    def set_response(self, model: str, response: str):
        """Set mock response text for a model."""
        self._responses[model] = response

    def _respond(self, model: str, response_format: Optional[str]) -> Dict[str, Any]:
        data = self._responses.get(model, f"Mock response from {model}")
        result = {"success": True, "data": data, "model": model, "error": None}
        if response_format == "json":
            try:
                result["parsed"] = json.loads(data)
            except json.JSONDecodeError:
                result["parsed"] = None
        return result

    def generate(self, prompt, model=None, system=None, provider=None,
                 endpoint=None, api_key=None, temperature=None,
                 max_tokens=None, response_format=None, **kwargs) -> Dict[str, Any]:
        self.last_call = 'generate'
        self.last_kwargs = dict(prompt=prompt, model=model, system=system,
                                 provider=provider, endpoint=endpoint, api_key=api_key,
                                 temperature=temperature, max_tokens=max_tokens,
                                 response_format=response_format)
        return self._respond(model, response_format)

    def chat(self, messages, model=None, provider=None, endpoint=None,
             api_key=None, temperature=None, max_tokens=None,
             response_format=None, **kwargs) -> Dict[str, Any]:
        self.last_call = 'chat'
        self.last_kwargs = dict(messages=messages, model=model, provider=provider,
                                 endpoint=endpoint, api_key=api_key,
                                 temperature=temperature, max_tokens=max_tokens,
                                 response_format=response_format)
        return self._respond(model, response_format)


class MockLLMRuntime(MockRuntime):
    """Extended mock runtime with LLM service"""

    def __init__(self, variables: Dict[str, Any] = None):
        super().__init__(variables)
        self._llm_service = MockLLMService()
        self._services = MagicMock()
        # q:llm now uses the multi-provider service, like q:agent always did
        self._services.multi_llm = self._llm_service
        self._services.llm = self._llm_service
        from quantum.runtime.llm_cache import LLMCache
        self._services.llm_cache = LLMCache()

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
        runtime = MockLLMRuntime()
        executor = LLMExecutor(runtime)
        assert LLMNode in executor.handles

    def test_handles_returns_list(self):
        runtime = MockLLMRuntime()
        executor = LLMExecutor(runtime)
        assert isinstance(executor.handles, list)
        assert len(executor.handles) == 1


class TestCompletionMode:
    """Test completion mode (single prompt) — dispatches to generate()"""

    def test_simple_prompt(self):
        runtime = MockLLMRuntime()
        runtime._llm_service.set_response("phi3", "Hello there!")
        executor = LLMExecutor(runtime)

        node = LLMNode("greeting")
        node.prompt = "Say hello"

        result = executor.execute(node, runtime.execution_context)

        assert result == "Hello there!"
        assert runtime._llm_service.last_call == 'generate'
        assert runtime._llm_service.last_kwargs["model"] == "phi3"

    def test_prompt_with_databinding(self):
        runtime = MockLLMRuntime({"userName": "Alice"})
        runtime._llm_service.set_response("phi3", "Hello Alice!")
        executor = LLMExecutor(runtime)

        node = LLMNode("greeting")
        node.prompt = "Say hello to {userName}"

        executor.execute(node, runtime.execution_context)

        assert "Alice" in runtime._llm_service.last_kwargs["prompt"]

    def test_custom_model(self):
        runtime = MockLLMRuntime()
        runtime._llm_service.set_response("llama3", "Response from llama")
        executor = LLMExecutor(runtime)

        node = LLMNode("result")
        node.model = "llama3"
        node.prompt = "Test prompt"

        executor.execute(node, runtime.execution_context)

        assert runtime._llm_service.last_kwargs["model"] == "llama3"

    def test_default_model(self):
        runtime = MockLLMRuntime()
        executor = LLMExecutor(runtime)

        node = LLMNode("result")
        node.prompt = "Test"

        executor.execute(node, runtime.execution_context)

        assert runtime._llm_service.last_kwargs["model"] == "phi3"


class TestChatMode:
    """Test chat mode (messages array) — dispatches to chat()"""

    def test_chat_messages(self):
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

        assert runtime._llm_service.last_call == 'chat'
        messages = runtime._llm_service.last_kwargs["messages"]
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"

    def test_chat_with_databinding(self):
        runtime = MockLLMRuntime({"question": "What is the weather?"})
        executor = LLMExecutor(runtime)

        node = LLMNode("chat")
        node.messages = [MockMessageNode("user", "{question}")]

        executor.execute(node, runtime.execution_context)

        messages = runtime._llm_service.last_kwargs["messages"]
        assert messages[0]["content"] == "What is the weather?"


class TestSystemMessage:
    """Test system message handling — differs by mode"""

    def test_system_passed_to_generate_in_completion_mode(self):
        runtime = MockLLMRuntime()
        executor = LLMExecutor(runtime)

        node = LLMNode("result")
        node.system = "You are a helpful assistant"
        node.prompt = "Help me"

        executor.execute(node, runtime.execution_context)

        assert runtime._llm_service.last_call == 'generate'
        assert runtime._llm_service.last_kwargs["system"] == "You are a helpful assistant"
        assert runtime._llm_service.last_kwargs["prompt"] == "Help me"

    def test_system_with_databinding(self):
        runtime = MockLLMRuntime({"role": "Python expert"})
        executor = LLMExecutor(runtime)

        node = LLMNode("result")
        node.system = "You are a {role}"
        node.prompt = "Help me"

        executor.execute(node, runtime.execution_context)

        assert runtime._llm_service.last_kwargs["system"] == "You are a Python expert"

    def test_system_prepended_in_chat_mode(self):
        """A top-level node.system alongside node.messages prepends a
        system-role message rather than being silently dropped."""
        runtime = MockLLMRuntime()
        executor = LLMExecutor(runtime)

        node = LLMNode("chat")
        node.system = "Be concise"
        node.messages = [MockMessageNode("user", "Hi")]

        executor.execute(node, runtime.execution_context)

        assert runtime._llm_service.last_call == 'chat'
        messages = runtime._llm_service.last_kwargs["messages"]
        assert messages[0] == {"role": "system", "content": "Be concise"}
        assert messages[1] == {"role": "user", "content": "Hi"}


class TestOptions:
    """Test LLM options"""

    def test_temperature_option(self):
        runtime = MockLLMRuntime()
        executor = LLMExecutor(runtime)

        node = LLMNode("result")
        node.prompt = "Test"
        node.temperature = 0.7

        executor.execute(node, runtime.execution_context)

        assert runtime._llm_service.last_kwargs["temperature"] == 0.7

    def test_max_tokens_option(self):
        runtime = MockLLMRuntime()
        executor = LLMExecutor(runtime)

        node = LLMNode("result")
        node.prompt = "Test"
        node.max_tokens = 100

        executor.execute(node, runtime.execution_context)

        assert runtime._llm_service.last_kwargs["max_tokens"] == 100

    def test_combined_options(self):
        runtime = MockLLMRuntime()
        executor = LLMExecutor(runtime)

        node = LLMNode("result")
        node.prompt = "Test"
        node.temperature = 0.5
        node.max_tokens = 200

        executor.execute(node, runtime.execution_context)

        kwargs = runtime._llm_service.last_kwargs
        assert kwargs["temperature"] == 0.5
        assert kwargs["max_tokens"] == 200


class TestEndpoint:
    """Endpoint and provider now travel as kwargs to the shared
    multi-provider service, instead of constructing a scoped LLMService."""

    def test_custom_endpoint_passed(self):
        runtime = MockLLMRuntime()
        executor = LLMExecutor(runtime)

        node = LLMNode("result")
        node.endpoint = "http://localhost:11434"
        node.prompt = "Test"

        executor.execute(node, runtime.execution_context)

        assert runtime._llm_service.last_kwargs["endpoint"] == "http://localhost:11434"

    def test_endpoint_with_databinding(self):
        runtime = MockLLMRuntime({"llmUrl": "http://custom:8080"})
        executor = LLMExecutor(runtime)

        node = LLMNode("result")
        node.endpoint = "{llmUrl}"
        node.prompt = "Test"

        executor.execute(node, runtime.execution_context)

        assert runtime._llm_service.last_kwargs["endpoint"] == "http://custom:8080"

    def test_provider_and_api_key_passed(self):
        runtime = MockLLMRuntime({"key": "sk-123"})
        executor = LLMExecutor(runtime)

        node = LLMNode("result")
        node.provider = "openai"
        node.api_key = "{key}"
        node.prompt = "Test"

        executor.execute(node, runtime.execution_context)

        assert runtime._llm_service.last_kwargs["provider"] == "openai"
        assert runtime._llm_service.last_kwargs["api_key"] == "sk-123"

    def test_no_endpoint_uses_shared_service(self):
        runtime = MockLLMRuntime()
        runtime._llm_service.set_response("phi3", "shared service response")
        executor = LLMExecutor(runtime)

        node = LLMNode("result")
        node.prompt = "Test"

        assert executor.execute(node, runtime.execution_context) == "shared service response"


class TestCache:
    """node.cache was an attribute wired to nothing until 2026-09-07."""

    def test_second_identical_call_is_served_from_cache(self):
        runtime = MockLLMRuntime()
        runtime._llm_service.set_response("phi3", "cached answer")
        executor = LLMExecutor(runtime)

        node = LLMNode("a")
        node.prompt = "Same prompt"
        node.cache = True

        first = executor.execute(node, runtime.execution_context)
        runtime._llm_service.last_call = None  # must not be called again

        node2 = LLMNode("b")
        node2.prompt = "Same prompt"
        node2.cache = True
        second = executor.execute(node2, runtime.execution_context)

        assert first == second == "cached answer"
        assert runtime._llm_service.last_call is None
        assert runtime.execution_context.get_variable("b_result")["cached"] is True

    def test_different_prompt_is_not_a_cache_hit(self):
        runtime = MockLLMRuntime()
        executor = LLMExecutor(runtime)

        node = LLMNode("a")
        node.prompt = "Prompt one"
        node.cache = True
        executor.execute(node, runtime.execution_context)

        runtime._llm_service.last_call = None
        node2 = LLMNode("b")
        node2.prompt = "Prompt two"
        node2.cache = True
        executor.execute(node2, runtime.execution_context)

        assert runtime._llm_service.last_call == 'generate'

    def test_cache_disabled_by_default(self):
        runtime = MockLLMRuntime()
        executor = LLMExecutor(runtime)

        node = LLMNode("a")
        node.prompt = "Same prompt"
        executor.execute(node, runtime.execution_context)

        runtime._llm_service.last_call = None
        node2 = LLMNode("b")
        node2.prompt = "Same prompt"
        executor.execute(node2, runtime.execution_context)

        assert runtime._llm_service.last_call == 'generate'


class TestResultStorage:
    """Test result storage"""

    def test_stores_response(self):
        runtime = MockLLMRuntime()
        runtime._llm_service.set_response("phi3", "The answer is 42")
        executor = LLMExecutor(runtime)

        node = LLMNode("answer")
        node.prompt = "What is the meaning of life?"

        executor.execute(node, runtime.execution_context)

        stored = runtime.execution_context.get_variable("answer")
        assert stored == "The answer is 42"

    def test_stores_result_metadata(self):
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
        runtime = MockLLMRuntime()
        runtime._llm_service.set_response("phi3", '{"name": "test"}')
        executor = LLMExecutor(runtime)

        node = LLMNode("data")
        node.prompt = "Extract data"
        node.response_format = "json"

        result = executor.execute(node, runtime.execution_context)

        assert runtime._llm_service.last_kwargs["response_format"] == "json"
        assert result == {"name": "test"}

    def test_default_text_format(self):
        runtime = MockLLMRuntime()
        executor = LLMExecutor(runtime)

        node = LLMNode("result")
        node.prompt = "Test"

        executor.execute(node, runtime.execution_context)

        assert runtime._llm_service.last_kwargs["response_format"] == "text"


class TestResponseMetadata:
    """The provider layer reports which provider answered."""

    def test_provider_recorded_in_result(self):
        runtime = MockLLMRuntime()
        executor = LLMExecutor(runtime)

        node = LLMNode("result")
        node.prompt = "Test"

        executor.execute(node, runtime.execution_context)

        meta = runtime.execution_context.get_variable("result_result")
        assert meta["cached"] is False
        assert "provider" in meta


class TestErrorHandling:
    """Test error handling"""

    def test_error_stores_failure_result(self):
        runtime = MockLLMRuntime()
        runtime._llm_service.generate = MagicMock(side_effect=Exception("LLM error"))
        executor = LLMExecutor(runtime)

        node = LLMNode("result")
        node.model = "test-model"
        node.prompt = "Test"

        with pytest.raises(ExecutorError, match="LLM execution error"):
            executor.execute(node, runtime.execution_context)

        error_result = runtime.execution_context.get_variable("result_result")
        assert error_result["success"] is False
        assert "LLM error" in error_result["error"]
        assert error_result["model"] == "test-model"

    def test_error_message_includes_details(self):
        runtime = MockLLMRuntime()
        runtime._llm_service.generate = MagicMock(side_effect=Exception("Connection refused"))
        executor = LLMExecutor(runtime)

        node = LLMNode("result")
        node.prompt = "Test"

        with pytest.raises(ExecutorError, match="Connection refused"):
            executor.execute(node, runtime.execution_context)
