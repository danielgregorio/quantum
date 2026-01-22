"""
Runtime for LLM Feature

Executes LLM operations using Ollama or other providers.
"""

from typing import Dict, Any, Optional, List
import hashlib
import json


class LLMRegistry:
    """
    Registry for LLM configurations defined in components.

    Stores LLM configurations by ID for reuse.
    """

    def __init__(self):
        self.llms: Dict[str, Any] = {}
        self.cache: Dict[str, str] = {}

    def register(self, llm_node):
        """Register an LLM configuration"""
        self.llms[llm_node.llm_id] = llm_node

    def get(self, llm_id: str):
        """Get an LLM configuration by ID"""
        return self.llms.get(llm_id)

    def clear(self):
        """Clear all registrations"""
        self.llms.clear()
        self.cache.clear()


class OllamaProvider:
    """
    Provider for Ollama local LLMs

    Uses the ollama Python library to communicate with Ollama.
    """

    def __init__(self, host: str = "http://localhost:11434"):
        self.host = host
        self._ollama = None

    @property
    def ollama(self):
        """Lazy load ollama library"""
        if self._ollama is None:
            try:
                import ollama
                self._ollama = ollama
            except ImportError:
                raise ImportError(
                    "ollama library not installed. Install with: pip install ollama"
                )
        return self._ollama

    def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ) -> str:
        """
        Generate text using Ollama

        Args:
            model: Model name (e.g., "llama3", "codellama:13b")
            prompt: User prompt
            system: System prompt
            temperature: Temperature (0-1)
            max_tokens: Max tokens to generate
            stream: Whether to stream response

        Returns:
            Generated text
        """
        options = {
            "temperature": temperature
        }

        if max_tokens:
            options["num_predict"] = max_tokens

        try:
            response = self.ollama.generate(
                model=model,
                prompt=prompt,
                system=system,
                options=options,
                stream=stream
            )

            if stream:
                # For streaming, return generator
                return response
            else:
                return response['response']

        except Exception as e:
            # Handle errors gracefully
            error_msg = str(e)
            if "not found" in error_msg.lower():
                return f"[ERROR: Model '{model}' not found. Pull it with: ollama pull {model}]"
            elif "connection" in error_msg.lower():
                return f"[ERROR: Cannot connect to Ollama at {self.host}. Is Ollama running?]"
            else:
                return f"[ERROR: {error_msg}]"

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        stream: bool = False
    ) -> str:
        """
        Chat with an LLM using conversation history

        Args:
            model: Model name
            messages: List of message dicts with 'role' and 'content'
            temperature: Temperature
            stream: Whether to stream

        Returns:
            Assistant response
        """
        try:
            response = self.ollama.chat(
                model=model,
                messages=messages,
                options={"temperature": temperature},
                stream=stream
            )

            if stream:
                return response
            else:
                return response['message']['content']

        except Exception as e:
            error_msg = str(e)
            if "not found" in error_msg.lower():
                return f"[ERROR: Model '{model}' not found. Pull it with: ollama pull {model}]"
            elif "connection" in error_msg.lower():
                return f"[ERROR: Cannot connect to Ollama. Is Ollama running?]"
            else:
                return f"[ERROR: {error_msg}]"


class OpenAIProvider:
    """Provider for OpenAI API (GPT models)"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self._client = None

    @property
    def client(self):
        """Lazy load openai library"""
        if self._client is None:
            try:
                import openai
                self._client = openai.OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "openai library not installed. Install with: pip install openai"
                )
        return self._client

    def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Generate text using OpenAI"""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"[ERROR: {str(e)}]"


class LLMRuntime:
    """
    Runtime for executing LLM operations

    Manages LLM registry and providers.
    """

    def __init__(self, execution_context=None):
        self.context = execution_context
        self.registry = LLMRegistry()
        self.ollama_provider = OllamaProvider()
        self.openai_provider = None  # Lazy init

    def register_llm(self, llm_node):
        """Register an LLM configuration"""
        self.registry.register(llm_node)

    def generate(self, llm_generate_node, context_vars: Dict[str, Any]) -> str:
        """
        Execute LLM text generation

        Args:
            llm_generate_node: LLMGenerateNode
            context_vars: Variables for databinding in prompt

        Returns:
            Generated text
        """
        # Get LLM configuration
        llm_config = self.registry.get(llm_generate_node.llm_id)
        if not llm_config:
            return f"[ERROR: LLM '{llm_generate_node.llm_id}' not found. Define it with <q:llm id='{llm_generate_node.llm_id}' ...>]"

        # Apply databinding to prompt
        prompt = self._apply_databinding(llm_generate_node.prompt, context_vars)

        # Check cache
        if llm_generate_node.cache:
            cache_key = llm_generate_node.cache_key or self._generate_cache_key(
                llm_config.model, prompt
            )
            if cache_key in self.registry.cache:
                return self.registry.cache[cache_key]

        # Get provider
        provider = self._get_provider(llm_config.provider, llm_config.options)

        # Generate
        result = provider.generate(
            model=llm_config.model,
            prompt=prompt,
            system=llm_config.system_prompt,
            temperature=llm_config.temperature,
            max_tokens=llm_config.max_tokens,
            stream=llm_generate_node.stream
        )

        # Cache result
        if llm_generate_node.cache and not llm_generate_node.stream:
            cache_key = llm_generate_node.cache_key or self._generate_cache_key(
                llm_config.model, prompt
            )
            self.registry.cache[cache_key] = result

        return result

    def _get_provider(self, provider_name: str, options: Dict[str, Any]):
        """Get LLM provider by name"""
        if provider_name == "ollama":
            return self.ollama_provider
        elif provider_name == "openai":
            if not self.openai_provider:
                api_key = options.get('api_key')
                self.openai_provider = OpenAIProvider(api_key=api_key)
            return self.openai_provider
        else:
            # Default to Ollama
            return self.ollama_provider

    def _apply_databinding(self, text: str, context_vars: Dict[str, Any]) -> str:
        """Apply databinding to prompt text"""
        # Simple implementation - in real code use renderer's databinding
        import re

        def replace_var(match):
            var_name = match.group(1).strip()
            return str(context_vars.get(var_name, f'{{{var_name}}}'))

        return re.sub(r'\{([^}]+)\}', replace_var, text)

    def _generate_cache_key(self, model: str, prompt: str) -> str:
        """Generate cache key for LLM call"""
        content = f"{model}:{prompt}"
        return hashlib.md5(content.encode()).hexdigest()
