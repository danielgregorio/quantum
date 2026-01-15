"""
Parser for LLM Feature

Parses q:llm, q:llm-generate, and q:llm-chat tags.
"""

import xml.etree.ElementTree as ET
from typing import Optional
from .ast_node import LLMNode, LLMGenerateNode, LLMChatNode


def parse_llm(element: ET.Element) -> LLMNode:
    """
    Parse <q:llm> tag

    Example:
        <q:llm id="assistant" model="llama3" provider="ollama" temperature="0.7">
            <default-prompt>You are a helpful AI assistant.</default-prompt>
        </q:llm>
    """
    llm_id = element.get('id')
    model = element.get('model')
    provider = element.get('provider', 'ollama')
    temperature = float(element.get('temperature', '0.7'))
    max_tokens = element.get('max_tokens')

    if max_tokens:
        max_tokens = int(max_tokens)

    # Parse system prompt from <default-prompt> child element
    system_prompt = None
    default_prompt_elem = element.find('.//default-prompt')
    if default_prompt_elem is not None:
        system_prompt = default_prompt_elem.text or ""

    # Parse additional options
    options = {}
    for key, value in element.attrib.items():
        if key not in ['id', 'model', 'provider', 'temperature', 'max_tokens']:
            options[key] = value

    return LLMNode(
        llm_id=llm_id,
        model=model,
        provider=provider,
        temperature=temperature,
        max_tokens=max_tokens,
        system_prompt=system_prompt,
        options=options
    )


def parse_llm_generate(element: ET.Element) -> LLMGenerateNode:
    """
    Parse <q:llm-generate> tag

    Example:
        <q:llm-generate llm="assistant" prompt="Summarize: {article}" result="summary" />
    """
    llm_id = element.get('llm')
    prompt = element.get('prompt')
    result_var = element.get('result')
    stream = element.get('stream', 'false').lower() == 'true'
    cache = element.get('cache', 'false').lower() == 'true'
    cache_key = element.get('cache_key')

    # Support prompt as text content
    if not prompt and element.text:
        prompt = element.text.strip()

    return LLMGenerateNode(
        llm_id=llm_id,
        prompt=prompt,
        result_var=result_var,
        stream=stream,
        cache=cache,
        cache_key=cache_key
    )


def parse_llm_chat(element: ET.Element) -> LLMChatNode:
    """
    Parse <q:llm-chat> tag

    Example:
        <q:llm-chat llm="assistant" session="chat_history" />
    """
    llm_id = element.get('llm')
    session_var = element.get('session', 'chat_history')
    max_history = int(element.get('max_history', '50'))
    show_ui = element.get('show_ui', 'true').lower() == 'true'

    return LLMChatNode(
        llm_id=llm_id,
        session_var=session_var,
        max_history=max_history,
        show_ui=show_ui
    )
