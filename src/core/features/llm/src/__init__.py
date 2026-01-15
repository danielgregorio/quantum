"""
LLM Feature - AI Integration with Ollama Support

Provides q:llm tag for defining and using LLMs in Quantum components.
"""

from .ast_node import LLMNode, LLMGenerateNode, LLMChatNode
from .parser import parse_llm, parse_llm_generate, parse_llm_chat
from .runtime import LLMRuntime

__all__ = ['LLMNode', 'LLMGenerateNode', 'LLMChatNode', 'parse_llm', 'parse_llm_generate', 'parse_llm_chat', 'LLMRuntime']
