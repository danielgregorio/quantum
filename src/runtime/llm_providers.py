"""
Quantum LLM Providers - Multi-provider LLM support

Supports:
- Ollama (local, default)
- LM Studio (local, OpenAI-compatible)
- OpenAI / ChatGPT (cloud)
- Anthropic / Claude (cloud)

Each provider implements a common interface for chat/generate operations.

Usage:
    from runtime.llm_providers import get_llm_provider, LLMProvider

    # Auto-detect provider from endpoint
    provider = get_llm_provider(endpoint="http://localhost:11434")  # Ollama
    provider = get_llm_provider(endpoint="http://localhost:1234/v1")  # LM Studio
    provider = get_llm_provider(provider="openai", api_key="sk-...")  # OpenAI
    provider = get_llm_provider(provider="anthropic", api_key="sk-ant-...")  # Claude

    # Use common interface
    result = provider.chat(messages=[...], model="gpt-4")
"""

import os
import json
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

import requests

logger = logging.getLogger(__name__)


class ProviderType(Enum):
    """Supported LLM providers."""
    OLLAMA = "ollama"
    OPENAI = "openai"       # Also works for LM Studio
    ANTHROPIC = "anthropic"
    AUTO = "auto"           # Auto-detect from endpoint


class LLMProviderError(Exception):
    """Error from LLM provider."""
    pass


@dataclass
class LLMResponse:
    """Unified response from any LLM provider."""
    success: bool
    content: str
    model: str
    provider: str
    usage: Optional[Dict[str, int]] = None
    error: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.content,
            "content": self.content,
            "model": self.model,
            "provider": self.provider,
            "usage": self.usage,
            "error": self.error,
        }


class BaseLLMProvider(ABC):
    """Base class for LLM providers."""

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout: int = 60
    ):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.default_model = default_model
        self.timeout = timeout

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier."""
        pass

    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Send chat completion request."""
        pass

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate completion from prompt (converts to chat format)."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages, model=model, **kwargs)

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers


class OllamaProvider(BaseLLMProvider):
    """
    Ollama provider - local LLM inference.

    Endpoints:
        - /api/generate (completion)
        - /api/chat (chat)
        - /api/tags (list models)
        - /api/embed (embeddings)

    Default URL: http://localhost:11434
    """

    @property
    def provider_name(self) -> str:
        return "ollama"

    def __init__(
        self,
        base_url: str = None,
        default_model: str = None,
        timeout: int = 60,
        **kwargs
    ):
        base_url = base_url or os.getenv('QUANTUM_LLM_BASE_URL', 'http://localhost:11434')
        default_model = default_model or os.getenv('QUANTUM_LLM_DEFAULT_MODEL', 'phi3')
        super().__init__(base_url, None, default_model, timeout)

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Send chat request to Ollama."""
        model = model or self.default_model

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
        }

        options = {}
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        if options:
            payload["options"] = options

        if response_format == "json":
            payload["format"] = "json"

        try:
            url = f"{self.base_url}/api/chat"
            logger.debug(f"Ollama chat: model={model}, messages={len(messages)}")

            resp = requests.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()

            data = resp.json()
            message = data.get("message", {})
            content = message.get("content", "")

            return LLMResponse(
                success=True,
                content=content,
                model=data.get("model", model),
                provider=self.provider_name,
                usage={
                    "prompt_tokens": data.get("prompt_eval_count", 0),
                    "completion_tokens": data.get("eval_count", 0),
                    "total_tokens": data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
                },
                raw=data
            )

        except requests.ConnectionError:
            raise LLMProviderError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Ensure Ollama is running: ollama serve"
            )
        except requests.Timeout:
            raise LLMProviderError(f"Ollama request timed out after {self.timeout}s")
        except requests.HTTPError as e:
            raise LLMProviderError(f"Ollama error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise LLMProviderError(f"Ollama error: {e}")

    def list_models(self) -> List[str]:
        """List available Ollama models."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return [m.get("name", "") for m in data.get("models", [])]
        except Exception as e:
            logger.error(f"Error listing Ollama models: {e}")
            return []


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI-compatible provider.

    Works with:
        - OpenAI API (api.openai.com)
        - LM Studio (localhost:1234)
        - Azure OpenAI
        - Any OpenAI-compatible API

    Endpoints:
        - /v1/chat/completions (chat)
        - /v1/completions (legacy)
        - /v1/embeddings (embeddings)

    Default URL: https://api.openai.com (or localhost:1234 for LM Studio)
    """

    @property
    def provider_name(self) -> str:
        return "openai"

    def __init__(
        self,
        base_url: str = None,
        api_key: str = None,
        default_model: str = None,
        timeout: int = 60,
        **kwargs
    ):
        # Check for LM Studio first (local), then OpenAI
        if base_url is None:
            # Try to detect LM Studio
            lm_studio_url = os.getenv('LM_STUDIO_URL', 'http://localhost:1234/v1')
            openai_url = os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1')
            base_url = lm_studio_url if self._is_local_available(lm_studio_url) else openai_url

        api_key = api_key or os.getenv('OPENAI_API_KEY', '')
        default_model = default_model or os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')

        super().__init__(base_url, api_key, default_model, timeout)

    def _is_local_available(self, url: str) -> bool:
        """Check if local LM Studio is running."""
        try:
            resp = requests.get(f"{url}/models", timeout=2)
            return resp.status_code == 200
        except:
            return False

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Send chat request to OpenAI-compatible API."""
        model = model or self.default_model

        payload = {
            "model": model,
            "messages": messages,
        }

        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if response_format == "json":
            payload["response_format"] = {"type": "json_object"}

        try:
            url = f"{self.base_url}/chat/completions"
            if not url.startswith("http"):
                url = f"https://{url}"

            logger.debug(f"OpenAI chat: model={model}, url={url}")

            resp = requests.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            resp.raise_for_status()

            data = resp.json()
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = message.get("content", "")

            usage = data.get("usage", {})

            return LLMResponse(
                success=True,
                content=content,
                model=data.get("model", model),
                provider=self.provider_name,
                usage={
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0)
                },
                raw=data
            )

        except requests.ConnectionError:
            raise LLMProviderError(f"Cannot connect to {self.base_url}")
        except requests.Timeout:
            raise LLMProviderError(f"Request timed out after {self.timeout}s")
        except requests.HTTPError as e:
            error_msg = e.response.text
            try:
                error_data = e.response.json()
                error_msg = error_data.get("error", {}).get("message", error_msg)
            except:
                pass
            raise LLMProviderError(f"OpenAI API error: {error_msg}")
        except Exception as e:
            raise LLMProviderError(f"OpenAI error: {e}")

    def list_models(self) -> List[str]:
        """List available models."""
        try:
            url = f"{self.base_url}/models"
            resp = requests.get(url, headers=self._get_headers(), timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return [m.get("id", "") for m in data.get("data", [])]
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []


class AnthropicProvider(BaseLLMProvider):
    """
    Anthropic provider for Claude models.

    Endpoints:
        - /v1/messages (chat)

    Default URL: https://api.anthropic.com
    """

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def __init__(
        self,
        base_url: str = None,
        api_key: str = None,
        default_model: str = None,
        timeout: int = 60,
        **kwargs
    ):
        base_url = base_url or os.getenv('ANTHROPIC_API_BASE', 'https://api.anthropic.com')
        api_key = api_key or os.getenv('ANTHROPIC_API_KEY', '')
        default_model = default_model or os.getenv('ANTHROPIC_MODEL', 'claude-3-haiku-20240307')

        super().__init__(base_url, api_key, default_model, timeout)

    def _get_headers(self) -> Dict[str, str]:
        """Anthropic uses different auth header."""
        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key or "",
            "anthropic-version": "2023-06-01"
        }

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> LLMResponse:
        """Send chat request to Anthropic API."""
        model = model or self.default_model

        # Anthropic requires system message to be separate
        system_content = ""
        chat_messages = []

        for msg in messages:
            if msg.get("role") == "system":
                system_content += msg.get("content", "") + "\n"
            else:
                chat_messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })

        payload = {
            "model": model,
            "messages": chat_messages,
            "max_tokens": max_tokens or 4096,
        }

        if system_content:
            payload["system"] = system_content.strip()

        if temperature is not None:
            payload["temperature"] = temperature

        try:
            url = f"{self.base_url}/v1/messages"
            logger.debug(f"Anthropic chat: model={model}")

            resp = requests.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            resp.raise_for_status()

            data = resp.json()

            # Extract content from Anthropic response format
            content_blocks = data.get("content", [])
            content = ""
            for block in content_blocks:
                if block.get("type") == "text":
                    content += block.get("text", "")

            usage = data.get("usage", {})

            return LLMResponse(
                success=True,
                content=content,
                model=data.get("model", model),
                provider=self.provider_name,
                usage={
                    "prompt_tokens": usage.get("input_tokens", 0),
                    "completion_tokens": usage.get("output_tokens", 0),
                    "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                },
                raw=data
            )

        except requests.ConnectionError:
            raise LLMProviderError(f"Cannot connect to Anthropic API at {self.base_url}")
        except requests.Timeout:
            raise LLMProviderError(f"Request timed out after {self.timeout}s")
        except requests.HTTPError as e:
            error_msg = e.response.text
            try:
                error_data = e.response.json()
                error_msg = error_data.get("error", {}).get("message", error_msg)
            except:
                pass
            raise LLMProviderError(f"Anthropic API error: {error_msg}")
        except Exception as e:
            raise LLMProviderError(f"Anthropic error: {e}")


# Provider Registry
_PROVIDERS = {
    "ollama": OllamaProvider,
    "openai": OpenAIProvider,
    "lmstudio": OpenAIProvider,  # LM Studio uses OpenAI-compatible API
    "anthropic": AnthropicProvider,
    "claude": AnthropicProvider,
}


def detect_provider(endpoint: str) -> str:
    """
    Auto-detect provider from endpoint URL.

    Args:
        endpoint: The API endpoint URL

    Returns:
        Provider name (ollama, openai, anthropic)
    """
    endpoint = endpoint.lower()

    # Anthropic
    if "anthropic" in endpoint:
        return "anthropic"

    # OpenAI
    if "openai" in endpoint or "api.openai.com" in endpoint:
        return "openai"

    # Check for OpenAI-compatible endpoints (LM Studio, etc.)
    if "/v1/" in endpoint or endpoint.endswith("/v1"):
        return "openai"

    # Default to Ollama for local endpoints
    if "localhost" in endpoint or "127.0.0.1" in endpoint:
        if "11434" in endpoint:
            return "ollama"
        if "1234" in endpoint:
            return "openai"  # LM Studio default port

    # Default
    return "ollama"


def get_llm_provider(
    provider: str = "auto",
    endpoint: Optional[str] = None,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    timeout: int = 60
) -> BaseLLMProvider:
    """
    Get an LLM provider instance.

    Args:
        provider: Provider name (ollama, openai, anthropic, auto)
        endpoint: API endpoint URL
        api_key: API key for cloud providers
        model: Default model name
        timeout: Request timeout in seconds

    Returns:
        BaseLLMProvider instance

    Examples:
        # Auto-detect from endpoint
        p = get_llm_provider(endpoint="http://localhost:11434")  # Ollama

        # Explicit provider
        p = get_llm_provider(provider="openai", api_key="sk-...")

        # LM Studio (uses OpenAI-compatible API)
        p = get_llm_provider(endpoint="http://localhost:1234/v1")
    """
    # Auto-detect provider from endpoint if not specified
    if provider == "auto" and endpoint:
        provider = detect_provider(endpoint)

    # Get provider class
    provider_cls = _PROVIDERS.get(provider.lower())
    if not provider_cls:
        raise ValueError(f"Unknown provider: {provider}. Valid: {list(_PROVIDERS.keys())}")

    # Create instance
    kwargs = {"timeout": timeout}
    if endpoint:
        kwargs["base_url"] = endpoint
    if api_key:
        kwargs["api_key"] = api_key
    if model:
        kwargs["default_model"] = model

    return provider_cls(**kwargs)


# Convenience function for backward compatibility with LLMService
class MultiProviderLLMService:
    """
    Drop-in replacement for LLMService with multi-provider support.

    Usage:
        service = MultiProviderLLMService()

        # Uses Ollama by default
        result = service.chat(messages=[...])

        # Use specific provider via endpoint
        result = service.chat(messages=[...], endpoint="http://localhost:1234/v1")

        # Use cloud provider
        result = service.chat(messages=[...], provider="openai", api_key="sk-...")
    """

    def __init__(
        self,
        default_provider: str = "ollama",
        default_endpoint: Optional[str] = None,
        default_api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout: int = 60
    ):
        self.default_provider = default_provider
        self.default_endpoint = default_endpoint
        self.default_api_key = default_api_key
        self.default_model = default_model
        self.timeout = timeout

        # Cache providers
        self._providers: Dict[str, BaseLLMProvider] = {}

    def _get_provider(
        self,
        provider: Optional[str] = None,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None
    ) -> BaseLLMProvider:
        """Get or create provider instance."""
        # Build cache key
        provider = provider or self.default_provider
        endpoint = endpoint or self.default_endpoint
        api_key = api_key or self.default_api_key

        cache_key = f"{provider}:{endpoint or 'default'}"

        if cache_key not in self._providers:
            self._providers[cache_key] = get_llm_provider(
                provider=provider,
                endpoint=endpoint,
                api_key=api_key,
                model=self.default_model,
                timeout=self.timeout
            )

        return self._providers[cache_key]

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        provider: Optional[str] = None,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send chat request to any provider.

        Returns dict compatible with existing LLMService.
        """
        llm = self._get_provider(provider, endpoint, api_key)
        result = llm.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            **kwargs
        )
        return result.to_dict()

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        provider: Optional[str] = None,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate completion from prompt."""
        llm = self._get_provider(provider, endpoint, api_key)
        result = llm.generate(prompt=prompt, model=model, system=system, **kwargs)
        return result.to_dict()


# Global instance
_multi_llm_service: Optional[MultiProviderLLMService] = None


def get_multi_llm_service() -> MultiProviderLLMService:
    """Get global multi-provider LLM service."""
    global _multi_llm_service
    if _multi_llm_service is None:
        _multi_llm_service = MultiProviderLLMService()
    return _multi_llm_service
