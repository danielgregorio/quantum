"""
Parser for Agents Feature

Parses q:agent, q:agent-ask, q:agent-chat tags.
"""

import xml.etree.ElementTree as ET
from typing import List
from .ast_node import AgentNode, AgentToolNode, AgentAskNode, AgentChatNode


def parse_agent(element: ET.Element) -> AgentNode:
    """
    Parse <q:agent> tag

    Example:
        <q:agent id="helper" llm="assistant" knowledge="docs">
            <goal>Help users find information</goal>
            <tools>
                <tool name="search" knowledge="docs" />
            </tools>
            <personality>Be helpful and friendly</personality>
        </q:agent>
    """
    agent_id = element.get('id')
    llm_id = element.get('llm')
    knowledge = element.get('knowledge', '')
    memory = element.get('memory', 'session')
    max_iterations = int(element.get('max_iterations', '5'))

    # Parse knowledge IDs (comma-separated)
    knowledge_ids = [k.strip() for k in knowledge.split(',') if k.strip()]

    # Parse goal
    goal = None
    goal_elem = element.find('.//goal')
    if goal_elem is not None:
        goal = goal_elem.text or ""

    # Parse personality
    personality = None
    personality_elem = element.find('.//personality')
    if personality_elem is not None:
        personality = personality_elem.text or ""

    # Parse tools
    tools = []
    tools_elem = element.find('.//tools')
    if tools_elem is not None:
        for tool_elem in tools_elem.findall('.//tool'):
            tool = parse_agent_tool(tool_elem)
            tools.append(tool)

    return AgentNode(
        agent_id=agent_id,
        llm_id=llm_id,
        knowledge_ids=knowledge_ids,
        goal=goal,
        tools=tools,
        personality=personality,
        memory=memory,
        max_iterations=max_iterations
    )


def parse_agent_tool(element: ET.Element) -> AgentToolNode:
    """
    Parse <tool> tag within q:agent

    Examples:
        <tool name="search" knowledge="docs" top_k="5" />
        <tool name="query_db" function="getUserData" />
    """
    name = element.get('name')
    knowledge_id = element.get('knowledge')
    function_name = element.get('function')
    top_k = int(element.get('top_k', '5'))

    # Determine tool type
    if knowledge_id:
        tool_type = "search"
    elif function_name:
        tool_type = "function"
    else:
        tool_type = "search"

    # Parse additional parameters
    parameters = {}
    for key, value in element.attrib.items():
        if key not in ['name', 'knowledge', 'function', 'top_k']:
            parameters[key] = value

    return AgentToolNode(
        name=name,
        tool_type=tool_type,
        knowledge_id=knowledge_id,
        function_name=function_name,
        top_k=top_k,
        parameters=parameters
    )


def parse_agent_ask(element: ET.Element) -> AgentAskNode:
    """
    Parse <q:agent-ask> tag

    Example:
        <q:agent-ask
            agent="helper"
            question="{userQuestion}"
            result="answer"
            sources="sources" />
    """
    agent_id = element.get('agent')
    question = element.get('question')
    result_var = element.get('result')
    sources_var = element.get('sources')
    show_thinking = element.get('show_thinking', 'false').lower() == 'true'

    return AgentAskNode(
        agent_id=agent_id,
        question=question,
        result_var=result_var,
        sources_var=sources_var,
        show_thinking=show_thinking
    )


def parse_agent_chat(element: ET.Element) -> AgentChatNode:
    """
    Parse <q:agent-chat> tag

    Example:
        <q:agent-chat
            agent="helper"
            session="chat_history"
            show_sources="true"
            show_thinking="true">
            <welcome>Hi! I'm here to help.</welcome>
        </q:agent-chat>
    """
    agent_id = element.get('agent')
    session_var = element.get('session', 'chat_history')
    show_sources = element.get('show_sources', 'true').lower() == 'true'
    show_thinking = element.get('show_thinking', 'false').lower() == 'true'

    # Parse welcome message
    welcome_message = None
    welcome_elem = element.find('.//welcome')
    if welcome_elem is not None:
        welcome_message = welcome_elem.text or ""

    return AgentChatNode(
        agent_id=agent_id,
        session_var=session_var,
        show_sources=show_sources,
        show_thinking=show_thinking,
        welcome_message=welcome_message
    )
