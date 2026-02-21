"""
LLM Executor - Execute q:llm statements

Handles LLM invocation via Ollama/compatible API.
"""

from typing import Any, List, Dict, Type
from runtime.executors.base import BaseExecutor, ExecutorError
from core.ast_nodes import LLMNode


class LLMExecutor(BaseExecutor):
    """
    Executor for q:llm statements.

    Supports:
    - Completion mode (single prompt)
    - Chat mode (messages array)
    - JSON response format
    - Temperature and token limits
    - Response caching
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

            # Resolve model and endpoint
            model = node.model or 'phi3'
            endpoint = None
            if node.endpoint:
                endpoint = self.apply_databinding(node.endpoint, context)

            # Build messages array
            messages = []

            # System message
            if node.system:
                system_text = self.apply_databinding(node.system, context)
                messages.append({'role': 'system', 'content': system_text})

            # Chat mode - use messages
            if node.messages:
                for msg in node.messages:
                    role = msg.role
                    content = self.apply_databinding(msg.content, context)
                    messages.append({'role': role, 'content': content})
            # Completion mode - use prompt
            elif node.prompt:
                prompt_text = self.apply_databinding(node.prompt, context)
                messages.append({'role': 'user', 'content': prompt_text})

            # Build options
            options = {}
            if node.temperature is not None:
                options['temperature'] = float(node.temperature)
            if node.max_tokens is not None:
                options['max_tokens'] = int(node.max_tokens)

            # Response format
            response_format = node.response_format or 'text'

            # Call LLM service
            result = self.services.llm.invoke(
                model=model,
                messages=messages,
                endpoint=endpoint,
                options=options,
                response_format=response_format,
                cache=node.cache,
                timeout=node.timeout
            )

            # Store result
            exec_context.set_variable(node.name, result, scope="component")

            # Store full result object
            exec_context.set_variable(f"{node.name}_result", {
                'success': True,
                'response': result,
                'model': model,
                'cached': False
            }, scope="component")

            return result

        except Exception as e:
            # Store error result
            exec_context.set_variable(f"{node.name}_result", {
                'success': False,
                'error': str(e),
                'model': node.model
            }, scope="component")
            raise ExecutorError(f"LLM execution error: {e}")
