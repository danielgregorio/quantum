"""
Quantum LLM Service - HTTP client for Ollama-compatible LLM APIs.

Provides generate (completion) and chat endpoints for the q:llm tag.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional

import requests

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Raised when LLM invocation fails"""
    pass


class LLMService:
    """HTTP client for Ollama-compatible LLM APIs."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        self.base_url = (
            base_url
            or os.getenv('QUANTUM_LLM_BASE_URL', 'http://localhost:11434')
        ).rstrip('/')
        self.default_model = (
            default_model
            or os.getenv('QUANTUM_LLM_DEFAULT_MODEL', 'phi3')
        )
        self.timeout = (
            timeout
            or int(os.getenv('QUANTUM_LLM_TIMEOUT', '60'))
        )

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Call Ollama /api/generate for single-turn completion.

        Args:
            prompt: The prompt text
            model: Model name (falls back to default_model)
            system: Optional system prompt
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            response_format: "text" or "json"
            timeout: Request timeout in seconds

        Returns:
            Dict with keys: success, data (response text), model, error
        """
        model = model or self.default_model
        timeout = timeout or self.timeout

        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }

        if system:
            payload["system"] = system

        options: Dict[str, Any] = {}
        if temperature is not None:
            options["temperature"] = temperature
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        if options:
            payload["options"] = options

        if response_format == "json":
            payload["format"] = "json"

        try:
            url = f"{self.base_url}/api/generate"
            logger.debug(f"LLM generate request: model={model}, url={url}")

            resp = requests.post(url, json=payload, timeout=timeout)
            resp.raise_for_status()

            data = resp.json()
            response_text = data.get("response", "")

            result = {
                "success": True,
                "data": response_text,
                "model": data.get("model", model),
                "done": data.get("done", True),
                "total_duration": data.get("total_duration"),
                "eval_count": data.get("eval_count"),
                "error": None,
            }

            # If JSON format requested, try to parse
            if response_format == "json":
                try:
                    result["parsed"] = json.loads(response_text)
                except json.JSONDecodeError:
                    result["parsed"] = None

            return result

        except requests.ConnectionError:
            raise LLMError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Ensure Ollama is running (ollama serve)"
            )
        except requests.Timeout:
            raise LLMError(
                f"LLM request timed out after {timeout}s. "
                "Try increasing timeout or using a smaller model"
            )
        except requests.HTTPError as e:
            raise LLMError(f"Ollama API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise LLMError(f"LLM generate error: {e}")

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[str] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Call Ollama /api/chat for multi-turn conversation.

        Args:
            messages: List of {"role": "...", "content": "..."} dicts
            model: Model name (falls back to default_model)
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            response_format: "text" or "json"
            timeout: Request timeout in seconds

        Returns:
            Dict with keys: success, data (response text), model, error
        """
        model = model or self.default_model
        timeout = timeout or self.timeout

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }

        options: Dict[str, Any] = {}
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
            logger.debug(f"LLM chat request: model={model}, url={url}, messages={len(messages)}")

            resp = requests.post(url, json=payload, timeout=timeout)
            resp.raise_for_status()

            data = resp.json()
            message = data.get("message", {})
            response_text = message.get("content", "")

            result = {
                "success": True,
                "data": response_text,
                "model": data.get("model", model),
                "role": message.get("role", "assistant"),
                "done": data.get("done", True),
                "total_duration": data.get("total_duration"),
                "eval_count": data.get("eval_count"),
                "error": None,
            }

            if response_format == "json":
                try:
                    result["parsed"] = json.loads(response_text)
                except json.JSONDecodeError:
                    result["parsed"] = None

            return result

        except requests.ConnectionError:
            raise LLMError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Ensure Ollama is running (ollama serve)"
            )
        except requests.Timeout:
            raise LLMError(
                f"LLM chat request timed out after {timeout}s. "
                "Try increasing timeout or using a smaller model"
            )
        except requests.HTTPError as e:
            raise LLMError(f"Ollama API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            raise LLMError(f"LLM chat error: {e}")

    def list_models(self) -> Dict[str, Any]:
        """
        List available models from Ollama /api/tags.

        Returns:
            Dict with "models" list
        """
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.ConnectionError:
            raise LLMError(f"Cannot connect to Ollama at {self.base_url}")
        except Exception as e:
            raise LLMError(f"Error listing models: {e}")

    def pull_model(self, model_name: str) -> Dict[str, Any]:
        """
        Pull a model from Ollama registry via /api/pull.

        Args:
            model_name: Name of the model to pull (e.g. "phi3", "mistral")

        Returns:
            Dict with pull status
        """
        try:
            resp = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name, "stream": False},
                timeout=600  # Model downloads can take a while
            )
            resp.raise_for_status()
            return {"success": True, "model": model_name}
        except requests.ConnectionError:
            raise LLMError(f"Cannot connect to Ollama at {self.base_url}")
        except Exception as e:
            raise LLMError(f"Error pulling model {model_name}: {e}")

    def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to Ollama server.

        Returns:
            Dict with online status and available models
        """
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            resp.raise_for_status()
            data = resp.json()
            models = [m.get("name", "") for m in data.get("models", [])]
            return {
                "online": True,
                "url": self.base_url,
                "models": models,
                "model_count": len(models)
            }
        except Exception:
            return {
                "online": False,
                "url": self.base_url,
                "models": [],
                "model_count": 0
            }
