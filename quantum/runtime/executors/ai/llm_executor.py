"""
LLM Executor - Execute q:llm statements

Handles LLM invocation across providers (Ollama, OpenAI, Anthropic, LM Studio).
"""

import json
import re
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

            # IA-1: the declared model (an expression, like endpoint= and apiKey=),
            # else the configured one — never a literal.
            declared = self.apply_databinding(node.model, context) if node.model else None
            model = self.services.llm_model(declared, f'<q:llm name="{node.name}">')
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

            sources = None
            if getattr(node, 'knowledge', None):
                # IA-6 (M5): answer from the knowledge base, citing its sources.
                question = next((m['content'] for m in reversed(messages) if m['role'] == 'user'), prompt_text)
                sources = self._retrieve(node, question or '', exec_context)
                if not sources:
                    # Nothing to answer from — an empty base, or no chunk as
                    # relevant as minRelevance (IA-9): the model is not asked (it
                    # would answer from memory, uncited). The page sees found=false.
                    return self._store(node, {'data': '', 'success': True, 'model': model}, exec_context,
                                       cached=False, extra={'found': False, 'sources': [], 'cited': [],
                                                            'grounded': False})
                grounding = self._grounding(sources)
                # Small models follow the last instruction best: repeat it with the question.
                reminder = ' (Answer from the sources and cite them like [1].)'
                if messages and messages[-1]['role'] == 'user':
                    messages[-1] = {'role': 'user', 'content': messages[-1]['content'] + reminder}
                elif prompt_text is not None:
                    prompt_text += reminder
                system_text = f'{grounding}\n\n{system_text}' if system_text else grounding
                if messages:
                    if messages[0]['role'] == 'system':
                        messages[0] = {'role': 'system', 'content': f"{grounding}\n\n{messages[0]['content']}"}
                    else:
                        messages.insert(0, {'role': 'system', 'content': grounding})

            temperature = float(node.temperature) if node.temperature is not None else None
            max_tokens = int(node.max_tokens) if node.max_tokens is not None else None
            response_format = node.response_format or 'text'

            if getattr(node, 'stream', False) and self._in_web_request():
                # IA-7: the page renders now; <ui:stream> reads the answer from /_stream/<token>.
                from quantum.runtime import llm_stream
                chat = messages or ([{'role': 'system', 'content': system_text}] if system_text else []) +                     [{'role': 'user', 'content': prompt_text or ''}]
                token = llm_stream.register({
                    'messages': chat, 'model': model, 'provider': provider, 'endpoint': endpoint,
                    'api_key': api_key, 'temperature': temperature, 'max_tokens': max_tokens,
                    'timeout': node.timeout,
                }, exec_context.session_vars)
                extra = {'stream': f'/_stream/{token}'}
                if sources is not None:
                    # The answer is not written yet: what it cites is not known (IA-9).
                    extra.update({'found': True, 'sources': sources, 'cited': [], 'grounded': None})
                return self._store(node, {'data': '', 'success': True, 'model': model}, exec_context,
                                   cached=False, extra=extra)

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
                    timeout=node.timeout,
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
                    timeout=node.timeout,
                )

            if cache is not None and response.get('success', True):
                cache.set(cache_key, response, ttl=node.ttl)

            extra = None
            if sources is not None:
                cited = self._cited(str(response.get('data', '')), len(sources))
                # IA-9: an answer that cites no source is not grounded in the base.
                extra = {'found': True, 'sources': sources, 'cited': cited, 'grounded': bool(cited)}
            return self._store(node, response, exec_context, cached=False, extra=extra)

        except Exception as e:
            # IA-5: same shape as q:invoke (INV-2): <name>_result.error.message.
            exec_context.set_variable(f"{node.name}_result", {
                'success': False,
                'error': {'message': str(e)},
                'model': node.model
            }, scope="component")
            if getattr(node, 'on_error', 'fail') == 'continue':
                exec_context.set_variable(node.name, '', scope="component")
                return None
            raise ExecutorError(f"LLM execution error: {e}. Add onerror=\"continue\" to handle it "
                                f"with {node.name}_result instead.")

    @staticmethod
    def _in_web_request() -> bool:
        """IA-7: streaming needs a browser (or the console) to read /_stream; `quantum run` waits."""
        try:
            from flask import has_request_context
            return has_request_context()
        except ImportError:
            return False

    # -- IA-6: answers grounded in a knowledge base --------------------------------

    def _retrieve(self, node: LLMNode, question: str, exec_context) -> list:
        """The top chunks for the question, numbered as the model will cite them.

        IA-9: a chunk less relevant than minRelevance is not retrieved. Vector
        search always returns the `top` nearest chunks, related or not, so
        without a floor `found` was false only on an EMPTY base and the model
        answered from whatever came back.
        """
        name = node.knowledge
        try:
            meta = exec_context.get_variable(f'_knowledge_{name}')
        except Exception:
            meta = None
        if not isinstance(meta, dict):
            raise ExecutorError(f'<q:llm knowledge="{name}">: there is no <q:knowledge name="{name}"> '
                                f'on this page')
        if meta.get('_failed'):
            raise ExecutorError(f"knowledge base '{name}' could not be built: {meta.get('error')}")
        hits = self.runtime.knowledge_service.search(
            name, question, int(getattr(node, 'top', 4) or 4), meta.get('embed_model', 'nomic-embed-text'))
        floor = getattr(node, 'min_relevance', None) or 0.0
        hits = [h for h in hits if (h.get('relevance') or 0.0) >= floor]
        from pathlib import PurePath
        return [{'n': i + 1, 'source': h.get('source') or 'unknown',
                 'name': PurePath(str(h.get('source') or 'unknown').replace('\\', '/')).name,
                 'text': h.get('content', ''), 'relevance': h.get('relevance')} for i, h in enumerate(hits)]

    @staticmethod
    def _grounding(sources: list) -> str:
        numbered = '\n\n'.join(f"[{s['n']}] ({s['name']})\n{s['text']}" for s in sources)
        return ('Answer using only the sources below. After each statement, cite the source it '
                'comes from by its number in brackets, like [1]. If the sources do not contain '
                'the answer, say that you do not know.\n\nSources:\n' + numbered)

    @staticmethod
    def _cited(text: str, count: int) -> list:
        return sorted({int(n) for n in re.findall(r'\[(\d+)\]', text) if 1 <= int(n) <= count})

    def _store(self, node: LLMNode, response: Dict[str, Any], exec_context, cached: bool,
               extra: Dict[str, Any] = None) -> Any:
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
            **(extra or {}),
        }, scope="component")

        return value
