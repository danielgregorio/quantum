"""
Agents Feature - AI Agents with Tool Use

This module provides AST nodes for the q:agent feature,
enabling autonomous AI agents that can use tools to complete tasks.

Multi-Agent Systems:
- AgentTeamNode: Team of collaborating agents
- AgentHandoffNode: Built-in handoff tool for agent delegation
"""

from .ast_node import (
    AgentNode,
    AgentInstructionNode,
    AgentToolNode,
    AgentToolParamNode,
    AgentExecuteNode,
    AgentTeamNode,
    AgentHandoffNode,
)

__all__ = [
    'AgentNode',
    'AgentInstructionNode',
    'AgentToolNode',
    'AgentToolParamNode',
    'AgentExecuteNode',
    'AgentTeamNode',
    'AgentHandoffNode',
]
