"""
AST Nodes for Agents Feature

Represents q:agent and related tags in the AST.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class AgentToolNode:
    """Represents a tool available to an agent"""
    name: str
    tool_type: str = "search"  # "search", "function", "web", "query"
    knowledge_id: Optional[str] = None
    function_name: Optional[str] = None
    top_k: int = 5
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentNode:
    """
    Represents a <q:agent> tag - defines an AI agent

    Example:
        <q:agent id="helper" llm="assistant" knowledge="docs">
            <goal>Help users find information in documentation</goal>
            <tools>
                <tool name="search" knowledge="docs" />
            </tools>
        </q:agent>

    Attributes:
        agent_id: Unique identifier for this agent
        llm_id: ID of the LLM to use
        knowledge_ids: List of knowledge base IDs to access
        goal: Agent's goal/purpose (used in system prompt)
        tools: List of tools available to agent
        personality: Agent's personality/tone
        memory: Memory type ("session", "persistent", "none")
        max_iterations: Max reasoning iterations
    """
    agent_id: str
    llm_id: str
    knowledge_ids: List[str] = field(default_factory=list)
    goal: Optional[str] = None
    tools: List[AgentToolNode] = field(default_factory=list)
    personality: Optional[str] = None
    memory: str = "session"
    max_iterations: int = 5

    def validate(self) -> List[str]:
        """Validate agent configuration"""
        errors = []

        if not self.agent_id:
            errors.append("Agent must have an 'id' attribute")

        if not self.llm_id:
            errors.append("Agent must have an 'llm' attribute")

        if self.max_iterations < 1:
            errors.append(f"max_iterations must be >= 1, got {self.max_iterations}")

        if self.memory not in ["session", "persistent", "none"]:
            errors.append(f"memory must be 'session', 'persistent', or 'none', got '{self.memory}'")

        return errors


@dataclass
class AgentAskNode:
    """
    Represents a <q:agent-ask> tag - asks an agent a question

    Example:
        <q:agent-ask
            agent="helper"
            question="{userQuestion}"
            result="answer"
            sources="sources" />

    Attributes:
        agent_id: ID of the agent to ask
        question: Question text (can include databinding)
        result_var: Variable name to store answer
        sources_var: Variable name to store sources (optional)
        show_thinking: Whether to include agent's reasoning process
    """
    agent_id: str
    question: str
    result_var: str
    sources_var: Optional[str] = None
    show_thinking: bool = False

    def validate(self) -> List[str]:
        """Validate agent ask configuration"""
        errors = []

        if not self.agent_id:
            errors.append("agent-ask must have an 'agent' attribute")

        if not self.question:
            errors.append("agent-ask must have a 'question' attribute")

        if not self.result_var:
            errors.append("agent-ask must have a 'result' attribute")

        return errors


@dataclass
class AgentChatNode:
    """
    Represents a <q:agent-chat> tag - creates a chat interface with an agent

    Example:
        <q:agent-chat
            agent="helper"
            session="chat_history"
            show_sources="true"
            show_thinking="true" />

    Attributes:
        agent_id: ID of the agent
        session_var: Session variable for chat history
        show_sources: Show retrieved sources
        show_thinking: Show agent's reasoning
        welcome_message: Initial message from agent
    """
    agent_id: str
    session_var: str = "chat_history"
    show_sources: bool = True
    show_thinking: bool = False
    welcome_message: Optional[str] = None

    def validate(self) -> List[str]:
        """Validate agent chat configuration"""
        errors = []

        if not self.agent_id:
            errors.append("agent-chat must have an 'agent' attribute")

        return errors
