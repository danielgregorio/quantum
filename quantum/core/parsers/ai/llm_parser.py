"""
LLM Parser - Parse q:llm statements

Handles LLM invocation configuration.
"""

from typing import List
from xml.etree import ElementTree as ET
from quantum.core.parsers.base import BaseTagParser, ParserError
from quantum.core.ast_nodes import LLMNode, LLMMessageNode


class LLMParser(BaseTagParser):
    """
    Parser for q:llm statements.

    Supports:
    - Completion mode (prompt)
    - Chat mode (messages)
    - Temperature/token configuration
    - Response formatting
    """

    @property
    def tag_names(self) -> List[str]:
        return ['llm']

    def parse(self, element: ET.Element) -> LLMNode:
        """
        Parse q:llm statement.

        Args:
            element: XML element for q:llm

        Returns:
            LLMNode AST node
        """
        name = self.get_attr(element, 'name')

        if not name:
            raise ParserError("LLM requires 'name' attribute")

        llm_node = LLMNode(name)
        llm_node.model = self.get_attr(element, 'model')
        llm_node.endpoint = self.get_attr(element, 'endpoint')

        # Temperature and tokens
        temp = self.get_attr(element, 'temperature')
        if temp:
            try:
                llm_node.temperature = float(temp)
            except ValueError:
                pass

        llm_node.max_tokens = self.get_int_attr(element, 'maxTokens', 0) or None
        llm_node.response_format = self.get_attr(element, 'responseFormat')
        llm_node.cache = self.get_bool_attr(element, 'cache', False)
        llm_node.ttl = self.get_int_attr(element, 'ttl', 0) or None
        # q:llm spoke only Ollama while q:agent was already multi-provider;
        # same attributes now work on both tags.
        llm_node.provider = self.get_attr(element, 'provider')
        llm_node.api_key = self.get_attr(element, 'apiKey')
        # Seconds to wait for the model; undeclared, the service default (60).
        llm_node.timeout = self.get_int_attr(element, 'timeout', 0) or None
        # M5 (IA-6): answer from a knowledge base, citing its sources.
        llm_node.knowledge = self.get_attr(element, 'knowledge')
        top = self.get_attr(element, 'top')
        if top is not None and not str(top).isdigit():
            raise ParserError(f'<q:llm name="{name}" top="{top}">: the number of sources to retrieve')
        llm_node.top = int(top) if top is not None else 4
        # IA-9: chunks less relevant than this (0–1) are not retrieved.
        min_relevance = self.get_attr(element, 'minRelevance')
        if min_relevance is not None:
            try:
                llm_node.min_relevance = float(min_relevance)
            except ValueError:
                llm_node.min_relevance = -1.0
            if not 0.0 <= llm_node.min_relevance <= 1.0:
                raise ParserError(f'<q:llm name="{name}" minRelevance="{min_relevance}">: '
                                  f'a relevance between 0 and 1, e.g. minRelevance="0.6"')
        # IA-7: in a web request, the answer arrives as it is written (<ui:stream>).
        llm_node.stream = self.get_bool_attr(element, 'stream', False)
        # IA-5: a failure stops the page unless the page handles it.
        llm_node.on_error = self.get_attr(element, 'onerror', 'fail')
        if llm_node.on_error not in ('fail', 'continue'):
            raise ParserError(f'<q:llm name="{name}"> onerror must be "fail" or "continue", '
                              f'not "{llm_node.on_error}"')

        # Parse children
        for child in element:
            child_type = self.get_element_name(child)

            if child_type == 'prompt':
                llm_node.prompt = self.get_text(child)
            elif child_type == 'system':
                llm_node.system = self.get_text(child)
            elif child_type == 'message':
                role = self.get_attr(child, 'role', 'user')
                content = self.get_text(child)
                llm_node.messages.append(LLMMessageNode(role, content))

        return llm_node
