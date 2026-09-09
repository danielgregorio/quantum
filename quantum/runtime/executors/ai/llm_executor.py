"""
LLM Executor - Execute q:llm statements

Handles LLM invocation across providers (Ollama, OpenAI, Anthropic, LM Studio).
"""

import json
from typing import Any, List, Dict, Type
from quantum.runtime.executors.base import BaseExecutor, ExecutorError
from quantum.core.ast_nodes import LLMNode


class LLMExecutor(BaseExecutor):
    """
    Executor for q:llm statements.

    Supports:
    - Completion mode (single prompt) and chat mode (messages array)
    - Multiple providers via provider= / endpoint= / apiKey=
    - JSON response format
    - Temperature and token limits
    - Response caching with TTL
    """

    @property
    def handles(self) -> List[Type]:
        return [LLMNode]

    def execute(self, node: LLMNode, exec_context) -> Any:
        """
        Execute LLM invocation.

        Args:
            node: LLMNode with LLM configuration
            exec_context: Execution context

        Returns:
            LLM response (text or parsed JSON)
        """
        try:
            context = exec_context.get_all_variables()

            model = node.model or 'phi3'
            provider = node.provider or None
            endpoint = self.apply_databinding(node.endpoint, context) if node.endpoint else None
            api_key = self.apply_databinding(node.api_key, context) if node.api_key else None

            system_text = None
            if node.system:
                system_text = self.apply_databinding(node.system, context)

            # Chat mode - build the messages array. node.system prepends a
            # system-role message (in addition to any explicit
            # <q:message role="system"> already in node.messages).
            messages = []
            if node.messages:
                if system_text:
                    messages.append({'role': 'system', 'content': system_text})
                for msg in node.messages:
                    content = self.apply_databinding(msg.content, context)
                    messages.append({'role': msg.role, 'content': content})

            prompt_text = None
            if not messages:
                prompt_text = self.apply_databinding(node.prompt, context) if node.prompt else ''

            temperature = float(node.temperature) if node.temperature is not None else None
            max_tokens = int(node.max_tokens) if node.max_tokens is not None else None
            response_format = node.response_format or 'text'

            cache = self.services.llm_cache if node.cache else None
            cache_key = None
            if cache is not None:
                cache_key = cache.build_key(
                    provider=provider, model=model, endpoint=endpoint,
                    messages=messages, prompt=prompt_text, system=system_text,
                    temperature=temperature, max_tokens=max_tokens,
                    response_format=response_format,
                )
                cached = cache.get(cache_key)
                if cached is not None:
                    return self._store(node, cached, exec_context, cached=True)

            # MultiProviderLLMService is what q:agent has always used; q:llm
            # was pinned to the Ollama-only LLMService, which is why
            # "multi-provider" was only half true.
            llm = self.services.multi_llm

            if messages:
                response = llm.chat(
                    messages=messages,
                    model=model,
                    provider=provider,
                    endpoint=endpoint,
                    api_key=api_key,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                )
            else:
                response = llm.generate(
                    prompt=prompt_text,
                    model=model,
                    system=system_text,
                    provider=provider,
                    endpoint=endpoint,
                    api_key=api_key,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                )

            if cache is not None and response.get('success', True):
                cache.set(cache_key, response, ttl=node.ttl)

            return self._store(node, response, exec_context, cached=False)

        except Exception as e:
            exec_context.set_variable(f"{node.name}_result", {
                'success': False,
                'error': str(e),
                'model': node.model
            }, scope="component")
            raise ExecutorError(f"LLM execution error: {e}")

    def _store(self, node: LLMNode, response: Dict[str, Any], exec_context, cached: bool) -> Any:
        """Unpack a provider response, store it, and return the value."""
        text = response.get('data', '')
        value = text

        # The provider layer returns raw text; JSON parsing is this executor's
        # job (the single-provider service used to do it, the shared one does not).
        if (node.response_format or 'text') == 'json':
            parsed = response.get('parsed')
            if parsed is None and isinstance(text, str) and text.strip():
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    parsed = None
            if parsed is not None:
                value = parsed

        exec_context.set_variable(node.name, value, scope="component")
        exec_context.set_variable(f"{node.name}_result", {
            'success': response.get('success', True),
            'response': value,
            'model': response.get('model', node.model),
            'provider': response.get('provider'),
            'usage': response.get('usage'),
            'cached': cached,
        }, scope="component")

        return value
