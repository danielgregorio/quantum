"""
Tests for LLM Providers - Multi-provider LLM support

Tests the provider implementations:
- OllamaProvider
- OpenAIProvider
- AnthropicProvider
- MultiProviderLLMService

Uses mocking for API calls.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json

# Add src to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from runtime.llm_providers import (
    OllamaProvider, OpenAIProvider, AnthropicProvider,
    MultiProviderLLMService, get_llm_provider, detect_provider,
    LLMResponse, LLMProviderError, BaseLLMProvider, ProviderType
)


class TestProviderDetection:
    """Test auto-detection of providers from endpoints."""

    def test_detect_ollama_from_port(self):
        """Test Ollama detection from default port."""
        assert detect_provider("http://localhost:11434") == "ollama"
        assert detect_provider("http://127.0.0.1:11434/api/chat") == "ollama"

    def test_detect_openai_from_url(self):
        """Test OpenAI detection from URL."""
        assert detect_provider("https://api.openai.com/v1") == "openai"
        assert detect_provider("https://api.openai.com/v1/chat/completions") == "openai"

    def test_detect_lm_studio_from_port(self):
        """Test LM Studio detection from default port."""
        assert detect_provider("http://localhost:1234/v1") == "openai"
        assert detect_provider("http://127.0.0.1:1234/v1/chat/completions") == "openai"

    def test_detect_openai_compatible(self):
        """Test OpenAI-compatible API detection from /v1 path."""
        assert detect_provider("http://myserver.com/v1") == "openai"
        assert detect_provider("https://custom-llm.example.com/v1/") == "openai"

    def test_detect_anthropic(self):
        """Test Anthropic detection from URL."""
        assert detect_provider("https://api.anthropic.com") == "anthropic"
        assert detect_provider("https://api.anthropic.com/v1/messages") == "anthropic"

    def test_default_to_ollama(self):
        """Test default provider is Ollama."""
        assert detect_provider("http://localhost:8080") == "ollama"
        assert detect_provider("http://unknown-llm.local") == "ollama"


class TestLLMResponse:
    """Test LLMResponse dataclass."""

    def test_response_creation(self):
        """Test response creation."""
        resp = LLMResponse(
            success=True,
            content="Hello, world!",
            model="gpt-4",
            provider="openai",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        )
        assert resp.success
        assert resp.content == "Hello, world!"
        assert resp.model == "gpt-4"
        assert resp.provider == "openai"
        assert resp.usage["total_tokens"] == 15

    def test_response_to_dict(self):
        """Test response serialization."""
        resp = LLMResponse(
            success=True,
            content="Test response",
            model="phi3",
            provider="ollama"
        )
        d = resp.to_dict()
        assert d["success"] is True
        assert d["content"] == "Test response"
        assert d["data"] == "Test response"  # Alias for backward compatibility
        assert d["model"] == "phi3"
        assert d["provider"] == "ollama"

    def test_response_with_error(self):
        """Test response with error."""
        resp = LLMResponse(
            success=False,
            content="",
            model="gpt-4",
            provider="openai",
            error="API rate limit exceeded"
        )
        assert not resp.success
        assert resp.error == "API rate limit exceeded"


class TestOllamaProvider:
    """Test OllamaProvider."""

    @pytest.fixture
    def provider(self):
        """Create provider instance."""
        return OllamaProvider(
            base_url="http://localhost:11434",
            default_model="phi3"
        )

    def test_provider_name(self, provider):
        """Test provider name."""
        assert provider.provider_name == "ollama"

    @patch('requests.post')
    def test_chat_success(self, mock_post, provider):
        """Test successful chat request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "model": "phi3",
            "message": {"role": "assistant", "content": "Hello!"},
            "prompt_eval_count": 10,
            "eval_count": 5
        }
        mock_post.return_value = mock_response

        result = provider.chat(
            messages=[{"role": "user", "content": "Hi"}],
            model="phi3"
        )

        assert result.success
        assert result.content == "Hello!"
        assert result.model == "phi3"
        assert result.provider == "ollama"
        assert result.usage["total_tokens"] == 15

    @patch('requests.post')
    def test_chat_connection_error(self, mock_post, provider):
        """Test chat with connection error."""
        import requests
        mock_post.side_effect = requests.ConnectionError()

        with pytest.raises(LLMProviderError) as exc_info:
            provider.chat(
                messages=[{"role": "user", "content": "Hi"}]
            )

        assert "Cannot connect to Ollama" in str(exc_info.value)

    @patch('requests.post')
    def test_chat_with_json_format(self, mock_post, provider):
        """Test chat with JSON response format."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "model": "phi3",
            "message": {"role": "assistant", "content": '{"key": "value"}'}
        }
        mock_post.return_value = mock_response

        result = provider.chat(
            messages=[{"role": "user", "content": "Return JSON"}],
            response_format="json"
        )

        # Verify format was passed
        call_args = mock_post.call_args
        assert call_args[1]["json"]["format"] == "json"


class TestOpenAIProvider:
    """Test OpenAIProvider."""

    @pytest.fixture
    def provider(self):
        """Create provider instance."""
        return OpenAIProvider(
            base_url="https://api.openai.com/v1",
            api_key="test-key",
            default_model="gpt-3.5-turbo"
        )

    def test_provider_name(self, provider):
        """Test provider name."""
        assert provider.provider_name == "openai"

    @patch('requests.post')
    def test_chat_success(self, mock_post, provider):
        """Test successful chat request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "chatcmpl-123",
            "model": "gpt-3.5-turbo",
            "choices": [{
                "message": {"role": "assistant", "content": "Hello!"}
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            }
        }
        mock_post.return_value = mock_response

        result = provider.chat(
            messages=[{"role": "user", "content": "Hi"}],
            model="gpt-3.5-turbo"
        )

        assert result.success
        assert result.content == "Hello!"
        assert result.provider == "openai"
        assert result.usage["total_tokens"] == 15

        # Verify auth header
        call_args = mock_post.call_args
        assert "Authorization" in call_args[1]["headers"]
        assert "Bearer test-key" in call_args[1]["headers"]["Authorization"]

    @patch('requests.post')
    def test_chat_with_temperature(self, mock_post, provider):
        """Test chat with temperature parameter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response"}}],
            "usage": {}
        }
        mock_post.return_value = mock_response

        provider.chat(
            messages=[{"role": "user", "content": "Hi"}],
            temperature=0.8,
            max_tokens=100
        )

        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        assert payload["temperature"] == 0.8
        assert payload["max_tokens"] == 100


class TestAnthropicProvider:
    """Test AnthropicProvider."""

    @pytest.fixture
    def provider(self):
        """Create provider instance."""
        return AnthropicProvider(
            base_url="https://api.anthropic.com",
            api_key="test-anthropic-key",
            default_model="claude-3-haiku-20240307"
        )

    def test_provider_name(self, provider):
        """Test provider name."""
        assert provider.provider_name == "anthropic"

    @patch('requests.post')
    def test_chat_success(self, mock_post, provider):
        """Test successful chat request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "msg_123",
            "model": "claude-3-haiku-20240307",
            "content": [{"type": "text", "text": "Hello from Claude!"}],
            "usage": {
                "input_tokens": 10,
                "output_tokens": 5
            }
        }
        mock_post.return_value = mock_response

        result = provider.chat(
            messages=[{"role": "user", "content": "Hi Claude"}]
        )

        assert result.success
        assert result.content == "Hello from Claude!"
        assert result.provider == "anthropic"
        assert result.usage["total_tokens"] == 15

    @patch('requests.post')
    def test_chat_with_system_message(self, mock_post, provider):
        """Test chat separates system message for Anthropic."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "content": [{"type": "text", "text": "Response"}],
            "usage": {}
        }
        mock_post.return_value = mock_response

        provider.chat(
            messages=[
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Hi"}
            ]
        )

        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        assert payload["system"] == "You are helpful."
        assert len(payload["messages"]) == 1  # Only user message
        assert payload["messages"][0]["role"] == "user"

    def test_anthropic_headers(self, provider):
        """Test Anthropic uses x-api-key header."""
        headers = provider._get_headers()
        assert "x-api-key" in headers
        assert headers["x-api-key"] == "test-anthropic-key"
        assert "anthropic-version" in headers


class TestGetLLMProvider:
    """Test get_llm_provider factory function."""

    def test_get_ollama_provider(self):
        """Test getting Ollama provider."""
        provider = get_llm_provider(
            provider="ollama",
            endpoint="http://localhost:11434"
        )
        assert isinstance(provider, OllamaProvider)
        assert provider.provider_name == "ollama"

    def test_get_openai_provider(self):
        """Test getting OpenAI provider."""
        provider = get_llm_provider(
            provider="openai",
            api_key="test-key"
        )
        assert isinstance(provider, OpenAIProvider)

    def test_get_anthropic_provider(self):
        """Test getting Anthropic provider."""
        provider = get_llm_provider(
            provider="anthropic",
            api_key="test-key"
        )
        assert isinstance(provider, AnthropicProvider)

    def test_get_lmstudio_provider(self):
        """Test LM Studio uses OpenAI provider."""
        provider = get_llm_provider(
            provider="lmstudio",
            endpoint="http://localhost:1234/v1"
        )
        assert isinstance(provider, OpenAIProvider)

    def test_auto_detect_provider(self):
        """Test auto-detection from endpoint."""
        provider = get_llm_provider(
            provider="auto",
            endpoint="https://api.anthropic.com/v1/messages"
        )
        assert isinstance(provider, AnthropicProvider)

    def test_invalid_provider(self):
        """Test invalid provider raises error."""
        with pytest.raises(ValueError) as exc_info:
            get_llm_provider(provider="invalid_provider")
        assert "Unknown provider" in str(exc_info.value)


class TestMultiProviderLLMService:
    """Test MultiProviderLLMService."""

    @pytest.fixture
    def service(self):
        """Create service instance."""
        return MultiProviderLLMService(
            default_provider="ollama",
            timeout=30
        )

    def test_service_creation(self, service):
        """Test service instantiation."""
        assert service is not None
        assert service.default_provider == "ollama"

    @patch('runtime.llm_providers.OllamaProvider.chat')
    def test_chat_with_default_provider(self, mock_chat, service):
        """Test chat uses default provider."""
        mock_chat.return_value = LLMResponse(
            success=True,
            content="Hello",
            model="phi3",
            provider="ollama"
        )

        result = service.chat(
            messages=[{"role": "user", "content": "Hi"}],
            model="phi3"
        )

        assert result["success"]
        assert result["content"] == "Hello"
        mock_chat.assert_called_once()

    @patch('runtime.llm_providers.OpenAIProvider.chat')
    def test_chat_with_specific_provider(self, mock_chat, service):
        """Test chat with specific provider."""
        mock_chat.return_value = LLMResponse(
            success=True,
            content="Hello from GPT",
            model="gpt-4",
            provider="openai"
        )

        result = service.chat(
            messages=[{"role": "user", "content": "Hi"}],
            provider="openai",
            api_key="test-key"
        )

        assert result["success"]
        assert result["content"] == "Hello from GPT"

    @patch('runtime.llm_providers.OllamaProvider.generate')
    def test_generate(self, mock_generate, service):
        """Test generate method."""
        mock_generate.return_value = LLMResponse(
            success=True,
            content="Generated text",
            model="phi3",
            provider="ollama"
        )

        result = service.generate(
            prompt="Complete this:",
            system="You are helpful"
        )

        assert result["success"]
        assert result["content"] == "Generated text"

    def test_provider_caching(self, service):
        """Test providers are cached."""
        # Get same provider twice
        p1 = service._get_provider("ollama")
        p2 = service._get_provider("ollama")

        # Should be same instance
        assert p1 is p2


class TestAgentServiceIntegration:
    """Test integration with AgentService."""

    @pytest.fixture
    def agent_service(self):
        """Create agent service with mock."""
        from runtime.agent_service import AgentService, reset_agent_service
        reset_agent_service()
        return AgentService()

    @patch('runtime.llm_providers.OllamaProvider.chat')
    def test_agent_uses_multi_provider(self, mock_chat, agent_service):
        """Test agent uses multi-provider service."""
        mock_chat.return_value = LLMResponse(
            success=True,
            content='{"action": "finish", "result": "Done!"}',
            model="phi3",
            provider="ollama"
        )

        agent_service.register_tool_handler("test_tool", lambda args: "ok")

        result = agent_service.execute(
            instruction="Test",
            tools=[{"name": "test_tool", "description": "Test", "params": []}],
            task="Do something",
            model="phi3",
            provider="ollama"
        )

        assert result.success
        mock_chat.assert_called()

    @patch('runtime.llm_providers.OpenAIProvider.chat')
    def test_agent_with_openai_provider(self, mock_chat, agent_service):
        """Test agent with OpenAI provider."""
        mock_chat.return_value = LLMResponse(
            success=True,
            content='{"action": "finish", "result": "Done with GPT!"}',
            model="gpt-4",
            provider="openai"
        )

        result = agent_service.execute(
            instruction="Test",
            tools=[{"name": "test_tool", "description": "Test", "params": []}],
            task="Do something",
            model="gpt-4",
            provider="openai",
            api_key="test-key"
        )

        assert result.success
        assert "GPT" in result.result


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
