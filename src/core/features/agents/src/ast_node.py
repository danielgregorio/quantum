"""
Agent AST Nodes

Defines the AST structure for AI agents with tool use capabilities.

Classes:
    AgentToolParamNode - Parameter definition for a tool
    AgentToolNode - Tool available to the agent
    AgentInstructionNode - System instruction for the agent
    AgentExecuteNode - Execute the agent with a task
    AgentNode - Main agent definition
    AgentHandoffNode - Built-in handoff tool for agent delegation
    AgentTeamNode - Team of collaborating agents
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any

# Import base class - handle both direct and package imports
try:
    from core.ast_nodes import QuantumNode
except ImportError:
    from ...ast_nodes import QuantumNode


@dataclass
class AgentToolParamNode(QuantumNode):
    """
    Parameter definition for an agent tool.

    Attributes:
        name: Parameter name (required)
        type: Parameter type (string, integer, number, boolean, array, object)
        required: Whether the parameter is required
        default: Default value if not provided
        description: Human-readable description for the LLM

    Example:
        <q:param name="orderId" type="integer" required="true"
                 description="The order ID to look up" />
    """
    name: str = ""
    type: str = "string"
    required: bool = False
    default: Optional[Any] = None
    description: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.type,
            "required": self.required,
            "default": self.default,
            "description": self.description
        }

    def validate(self) -> List[str]:
        """Validate the parameter node."""
        errors = []
        if not self.name:
            errors.append("AgentToolParamNode requires 'name' attribute")
        valid_types = {"string", "integer", "number", "boolean", "array", "object", "date", "decimal"}
        if self.type not in valid_types:
            errors.append(f"Invalid param type '{self.type}'. Must be one of: {valid_types}")
        return errors


@dataclass
class AgentToolNode(QuantumNode):
    """
    Tool available to the agent.

    A tool is a function that the agent can call to perform actions
    or retrieve information. Tools have parameters and a body that
    defines what happens when the tool is called.

    Attributes:
        name: Tool name (used by LLM to call it)
        description: What the tool does (helps LLM decide when to use it)
        params: List of parameter definitions
        body: List of AST nodes to execute when tool is called
        builtin: If True, this is a built-in tool (handoff, readShared, etc.)

    Built-in Tools (use builtin="true"):
        - handoff: Transfer to another agent in the team
        - readShared: Read from shared team memory
        - writeShared: Write to shared team memory
        - listAgents: List available agents in the team

    Example:
        <q:tool name="getOrder" description="Get order details by ID">
            <q:param name="orderId" type="integer" required="true" />
            <q:function name="fetchOrder">
                <q:query name="order" datasource="db">
                    SELECT * FROM orders WHERE id = :orderId
                </q:query>
                <q:return value="{order[0]}" />
            </q:function>
        </q:tool>

        <!-- Built-in tool -->
        <q:tool name="handoff" builtin="true" />
    """
    name: str = ""
    description: str = ""
    params: List[AgentToolParamNode] = field(default_factory=list)
    body: List[QuantumNode] = field(default_factory=list)
    builtin: bool = False  # True for built-in tools like handoff, readShared

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "params": [p.to_dict() for p in self.params],
            "body": [b.to_dict() if hasattr(b, 'to_dict') else str(b) for b in self.body],
            "builtin": self.builtin
        }

    def validate(self) -> List[str]:
        """Validate the tool node."""
        errors = []
        if not self.name:
            errors.append("AgentToolNode requires 'name' attribute")
        # Built-in tools get their description automatically
        if not self.description and not self.builtin:
            errors.append(f"Tool '{self.name}' should have a description for the LLM")
        for param in self.params:
            errors.extend(param.validate())
        return errors

    def is_builtin(self) -> bool:
        """Check if this is a built-in tool."""
        return self.builtin

    def get_schema(self) -> dict:
        """Get JSON Schema representation for LLM tool calling."""
        properties = {}
        required = []

        for param in self.params:
            prop = {"type": self._map_type(param.type)}
            if param.description:
                prop["description"] = param.description
            if param.default is not None:
                prop["default"] = param.default
            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required
            }
        }

    def _map_type(self, quantum_type: str) -> str:
        """Map Quantum types to JSON Schema types."""
        type_map = {
            "string": "string",
            "integer": "integer",
            "number": "number",
            "decimal": "number",
            "boolean": "boolean",
            "array": "array",
            "object": "object",
            "date": "string",
        }
        return type_map.get(quantum_type, "string")


@dataclass
class AgentInstructionNode(QuantumNode):
    """
    System instruction for the agent.

    Defines the agent's role, personality, and behavior guidelines.
    This becomes part of the system prompt sent to the LLM.

    Attributes:
        content: The instruction text (supports databinding)

    Example:
        <q:instruction>
            You are a helpful customer support agent.
            Be polite, concise, and helpful.
            Always verify information before taking action.
        </q:instruction>
    """
    content: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {"content": self.content}

    def validate(self) -> List[str]:
        """Validate the instruction node."""
        errors = []
        if not self.content.strip():
            errors.append("AgentInstructionNode should have content")
        return errors


@dataclass
class AgentExecuteNode(QuantumNode):
    """
    Execute the agent with a specific task.

    Triggers the agent's reasoning loop to complete the given task
    using the available tools.

    Attributes:
        task: The task/question for the agent (supports databinding)
        context: Additional context to provide (optional, supports databinding)
        entry: Entry agent name for team execution (optional)

    Example:
        <q:execute task="Check status of order #1234 and update if needed" />

        <q:execute task="{userMessage}" context="User ID: {userId}" />

        <!-- For team execution with specific entry point -->
        <q:execute task="{question}" entry="router" />
    """
    task: str = ""
    context: str = ""
    entry: str = ""  # Entry agent for team execution

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        result = {"task": self.task, "context": self.context}
        if self.entry:
            result["entry"] = self.entry
        return result

    def validate(self) -> List[str]:
        """Validate the execute node."""
        errors = []
        if not self.task:
            errors.append("AgentExecuteNode requires 'task' attribute or content")
        return errors


@dataclass
class AgentNode(QuantumNode):
    """
    AI Agent that can use tools to complete tasks.

    An agent is an autonomous AI that can:
    1. Receive a task from the user
    2. Reason about which tools to use
    3. Call tools to gather information or take actions
    4. Synthesize results into a coherent response

    Attributes:
        name: Variable name to store result (required)
        model: LLM model identifier (default: "phi3")
        endpoint: Custom LLM API endpoint (optional)
        provider: LLM provider (ollama, openai, anthropic, auto)
        api_key: API key for cloud providers (optional)
        max_iterations: Maximum tool calls allowed (default: 10)
        timeout: Total timeout in milliseconds (default: 60000)
        instruction: System instruction/prompt
        tools: List of available tools
        execute: Task to execute

    Result Object:
        {name}: The agent's final response (string)
        {name}_result: Full result object with:
            - success: bool
            - result: str
            - error: {message: str} or None
            - executionTime: float (ms)
            - iterations: int
            - actionCount: int
            - actions: [{tool, args, result}, ...]
            - tokenUsage: {prompt, completion, total}

    Supported Providers:
        - ollama: Local Ollama server (default: http://localhost:11434)
        - openai: OpenAI API or LM Studio (http://localhost:1234/v1)
        - anthropic: Anthropic Claude API
        - auto: Auto-detect from endpoint

    Example:
        <!-- Using Ollama (default) -->
        <q:agent name="support" model="phi3" max_iterations="5">
            ...
        </q:agent>

        <!-- Using OpenAI -->
        <q:agent name="helper" model="gpt-4" provider="openai"
                 api_key="{env.OPENAI_API_KEY}">
            ...
        </q:agent>

        <!-- Using LM Studio -->
        <q:agent name="local" model="mistral"
                 endpoint="http://localhost:1234/v1">
            ...
        </q:agent>

        <!-- Using Claude -->
        <q:agent name="claude" model="claude-3-haiku-20240307"
                 provider="anthropic" api_key="{env.ANTHROPIC_API_KEY}">
            ...
        </q:agent>
    """
    name: str = ""
    model: str = "phi3"
    endpoint: str = ""
    provider: str = "auto"  # ollama, openai, anthropic, auto
    api_key: str = ""  # For cloud providers
    max_iterations: int = 10
    timeout: int = 60000  # milliseconds

    instruction: Optional[AgentInstructionNode] = None
    tools: List[AgentToolNode] = field(default_factory=list)
    execute: Optional[AgentExecuteNode] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "model": self.model,
            "endpoint": self.endpoint,
            "provider": self.provider,
            "api_key": self.api_key,
            "max_iterations": self.max_iterations,
            "timeout": self.timeout,
            "instruction": self.instruction.to_dict() if self.instruction else None,
            "tools": [t.to_dict() for t in self.tools],
            "execute": self.execute.to_dict() if self.execute else None
        }

    def validate(self) -> List[str]:
        """Validate the agent node."""
        errors = []

        if not self.name:
            errors.append("AgentNode requires 'name' attribute")

        if not self.model:
            errors.append("AgentNode requires 'model' attribute")

        if self.max_iterations < 1:
            errors.append("max_iterations must be at least 1")

        if self.max_iterations > 100:
            errors.append("max_iterations should not exceed 100 for safety")

        if self.timeout < 1000:
            errors.append("timeout should be at least 1000ms (1 second)")

        if not self.tools:
            errors.append("AgentNode should have at least one tool")

        if not self.execute:
            errors.append("AgentNode requires <q:execute> to run")

        # Validate children
        if self.instruction:
            errors.extend(self.instruction.validate())

        for tool in self.tools:
            errors.extend(tool.validate())

        if self.execute:
            errors.extend(self.execute.validate())

        return errors

    def get_tools_schema(self) -> List[dict]:
        """Get JSON Schema for all tools (for LLM function calling)."""
        return [tool.get_schema() for tool in self.tools]


@dataclass
class AgentHandoffNode(QuantumNode):
    """
    Built-in handoff tool for agent delegation.

    Allows an agent to transfer control to another agent in a team,
    passing along context and the current task state.

    Attributes:
        target_agent: Name of the agent to hand off to
        context: Additional context/message for the target agent

    Example (used internally when agent calls handoff tool):
        {"action": "handoff", "args": {"agent": "billing", "message": "Customer needs invoice help"}}
    """
    target_agent: str = ""
    context: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "target_agent": self.target_agent,
            "context": self.context
        }

    def validate(self) -> List[str]:
        """Validate the handoff node."""
        errors = []
        if not self.target_agent:
            errors.append("AgentHandoffNode requires 'target_agent'")
        return errors


@dataclass
class AgentTeamNode(QuantumNode):
    """
    Team of collaborating agents that can hand off tasks to each other.

    A team provides:
    1. Shared context accessible by all agents
    2. Agent discovery and handoff capabilities
    3. Orchestration with entry point and handoff limits

    Attributes:
        name: Team name (used to store results)
        supervisor: Entry agent name (default entry point)
        shared: List of SetNode for shared state initialization
        agents: List of AgentNode team members
        execute: AgentExecuteNode with task and optional entry agent
        max_handoffs: Maximum handoffs allowed (safety limit, default 10)
        max_total_iterations: Sum of all agent iterations (default 50)

    Result Object:
        {name}: The final agent's response (string)
        {name}_result: Full result object with:
            - success: bool
            - finalResponse: str
            - finalAgent: str
            - handoffs: [{fromAgent, toAgent, message, timestamp}, ...]
            - totalIterations: int
            - executionTime: float (ms)
            - agentResults: {agentName: AgentResult, ...}
            - sharedContext: {key: value, ...}

    Example:
        <q:team name="support" supervisor="router">
            <q:shared>
                <q:set name="customerName" value="John" />
            </q:shared>

            <q:agent name="router" model="gpt-4">
                <q:instruction>Route to appropriate specialist</q:instruction>
                <q:tool name="handoff" builtin="true" />
            </q:agent>

            <q:agent name="billing" model="gpt-4">
                <q:instruction>Handle billing questions</q:instruction>
                <q:tool name="readShared" builtin="true" />
            </q:agent>

            <q:execute task="{question}" entry="router" />
        </q:team>
    """
    name: str = ""
    supervisor: str = ""  # Entry agent (default)
    shared: List[Any] = field(default_factory=list)  # SetNode list
    agents: List['AgentNode'] = field(default_factory=list)
    execute: Optional[AgentExecuteNode] = None
    max_handoffs: int = 10  # Safety limit for handoffs
    max_total_iterations: int = 50  # Total iterations across all agents

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "supervisor": self.supervisor,
            "shared": [s.to_dict() if hasattr(s, 'to_dict') else str(s) for s in self.shared],
            "agents": [a.to_dict() for a in self.agents],
            "execute": self.execute.to_dict() if self.execute else None,
            "max_handoffs": self.max_handoffs,
            "max_total_iterations": self.max_total_iterations
        }

    def validate(self) -> List[str]:
        """Validate the team node."""
        errors = []

        if not self.name:
            errors.append("AgentTeamNode requires 'name' attribute")

        if not self.agents:
            errors.append("AgentTeamNode requires at least one agent")

        if not self.execute:
            errors.append("AgentTeamNode requires <q:execute> to run")

        # Validate supervisor exists in agents
        agent_names = {a.name for a in self.agents}
        if self.supervisor and self.supervisor not in agent_names:
            errors.append(f"Supervisor '{self.supervisor}' not found in team agents: {agent_names}")

        # Validate entry agent if specified in execute
        if self.execute and hasattr(self.execute, 'entry'):
            entry = getattr(self.execute, 'entry', None)
            if entry and entry not in agent_names:
                errors.append(f"Entry agent '{entry}' not found in team agents: {agent_names}")

        if self.max_handoffs < 1:
            errors.append("max_handoffs must be at least 1")

        if self.max_handoffs > 100:
            errors.append("max_handoffs should not exceed 100 for safety")

        if self.max_total_iterations < 1:
            errors.append("max_total_iterations must be at least 1")

        # Validate child agents
        for agent in self.agents:
            errors.extend(agent.validate())

        return errors

    def get_agent(self, name: str) -> Optional['AgentNode']:
        """Get an agent by name."""
        for agent in self.agents:
            if agent.name == name:
                return agent
        return None

    def get_agent_names(self) -> List[str]:
        """Get list of all agent names in the team."""
        return [a.name for a in self.agents]
