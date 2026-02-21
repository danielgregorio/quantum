"""
LLM Parser - Parse q:llm statements

Handles LLM invocation configuration.
"""

from typing import List
from xml.etree import ElementTree as ET
from core.parsers.base import BaseTagParser, ParserError
from core.ast_nodes import LLMNode, LLMMessageNode


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
        llm_node.timeout = self.get_int_attr(element, 'timeout', 30)

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
