"""
Agent Service - Reasoning Loop and Tool Execution for AI Agents

Implements the ReAct (Reason + Act) pattern:
1. THINK: LLM analyzes task and decides next action
2. ACT: Execute the chosen tool
3. OBSERVE: Process tool result
4. REPEAT: Until task complete or max_iterations

Uses existing LLMService for LLM calls.

Multi-Agent Support:
- AgentRegistry: Central registry for agent discovery
- AgentTeam: Team of collaborating agents with shared context
- AgentHandoff: Record of agent-to-agent transfers
- MultiAgentService: Orchestrates team execution

Example:
    from runtime.agent_service import get_agent_service

    service = get_agent_service()
    result = service.execute(
        instruction="You are a helpful assistant",
        tools=[{"name": "search", "description": "Search docs", ...}],
        task="Find information about orders",
        model="phi3"
    )
    print(result.result)  # Agent's response
    print(result.actions)  # Tool calls made

Multi-Agent Example:
    from runtime.agent_service import get_multi_agent_service

    service = get_multi_agent_service()
    team = service.create_team(
        name="support",
        agents={"router": ..., "billing": ...},
        shared={"customerId": "123"},
        supervisor="router"
    )
    result = team.execute("Help with my bill", entry_agent="router")
"""

import json
import re
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Set
from dataclasses import dataclass, field
from collections import defaultdict

# Import multi-provider LLM support
from runtime.llm_providers import (
    get_llm_provider, MultiProviderLLMService, LLMProviderError,
    BaseLLMProvider
)

logger = logging.getLogger(__name__)


class AgentError(Exception):
    """Error during agent execution."""
    pass


@dataclass
class ToolCall:
    """Represents a single tool invocation."""
    tool: str
    args: Dict[str, Any]
    result: Any = None
    error: Optional[str] = None
    duration_ms: float = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tool": self.tool,
            "args": self.args,
            "result": self.result,
            "error": self.error,
            "duration_ms": self.duration_ms
        }


@dataclass
class AgentResult:
    """Result of agent execution."""
    success: bool = False
    result: str = ""
    error: Optional[Dict[str, str]] = None
    execution_time_ms: float = 0
    iterations: int = 0
    action_count: int = 0
    actions: List[ToolCall] = field(default_factory=list)
    token_usage: Dict[str, int] = field(default_factory=lambda: {"prompt": 0, "completion": 0, "total": 0})

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for template access."""
        return {
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "executionTime": self.execution_time_ms,
            "iterations": self.iterations,
            "actionCount": self.action_count,
            "actions": [a.to_dict() for a in self.actions],
            "tokenUsage": self.token_usage
        }


class AgentService:
    """
    Executes AI agents with tool use capabilities.

    Uses LLM to reason about which tools to use and when,
    then executes those tools and observes results.
    """

    # System prompt template for tool-using agents
    SYSTEM_PROMPT_TEMPLATE = '''You are an AI agent that completes tasks by using tools.

AVAILABLE TOOLS:
{tools_description}

INSTRUCTIONS:
{instruction}

RESPONSE FORMAT:
When you need to use a tool, respond with EXACTLY this JSON format (no other text):
```json
{{"action": "tool_name", "args": {{"param1": "value1", "param2": "value2"}}}}
```

When you have completed the task and have all the information needed, respond with EXACTLY:
```json
{{"action": "finish", "result": "Your complete and helpful response to the user"}}
```

RULES:
1. ONLY use the tools listed above - no other tools exist
2. Use ONE tool at a time, then wait for the result
3. After seeing a tool result, decide if you need more information or can finish
4. When you have enough information, use "finish" to provide your final answer
5. Be concise but complete in your final response
6. If a tool returns an error, try a different approach or explain the issue

IMPORTANT: Always respond with valid JSON in the format shown above. Nothing else.'''

    def __init__(self, llm_service=None):
        """
        Initialize agent service.

        Args:
            llm_service: LLMService instance for LLM calls (auto-created if None)
        """
        self._llm_service = llm_service
        self._multi_llm_service: Optional[MultiProviderLLMService] = None
        self._tool_handlers: Dict[str, Callable] = {}

    @property
    def llm_service(self):
        """Lazy-load LLM service (backward compatibility)."""
        if self._llm_service is None:
            from runtime.llm_service import get_llm_service
            self._llm_service = get_llm_service()
        return self._llm_service

    @property
    def multi_llm_service(self) -> MultiProviderLLMService:
        """Lazy-load multi-provider LLM service."""
        if self._multi_llm_service is None:
            self._multi_llm_service = MultiProviderLLMService()
        return self._multi_llm_service

    def register_tool_handler(self, name: str, handler: Callable):
        """
        Register a custom handler for a tool.

        Args:
            name: Tool name
            handler: Function(args: dict) -> Any
        """
        self._tool_handlers[name] = handler
        logger.debug(f"Registered tool handler: {name}")

    def execute(
        self,
        instruction: str,
        tools: List[Dict[str, Any]],
        task: str,
        context: str = "",
        model: str = "phi3",
        endpoint: str = "",
        provider: str = "auto",
        api_key: str = "",
        max_iterations: int = 10,
        timeout_ms: int = 60000,
        tool_executor: Optional[Callable] = None
    ) -> AgentResult:
        """
        Execute an agent with the given task.

        Args:
            instruction: System instruction for the agent
            tools: List of tool definitions with name, description, params, body
            task: The task to complete
            context: Additional context
            model: LLM model to use
            endpoint: LLM endpoint (optional, uses default if empty)
            provider: LLM provider (ollama, openai, anthropic, auto)
            api_key: API key for cloud providers
            max_iterations: Maximum tool calls
            timeout_ms: Total timeout in milliseconds
            tool_executor: Optional function to execute tool bodies

        Returns:
            AgentResult with success, result, actions, etc.
        """
        start_time = time.time()
        result = AgentResult()

        try:
            # Validate inputs
            if not task:
                raise AgentError("Task is required")
            if not tools:
                raise AgentError("At least one tool is required")

            # Build tools description for system prompt
            tools_desc = self._build_tools_description(tools)

            # Build system prompt
            system_prompt = self.SYSTEM_PROMPT_TEMPLATE.format(
                tools_description=tools_desc,
                instruction=instruction or "Complete the user's task accurately and helpfully."
            )

            # Build initial user message
            user_message = task
            if context:
                user_message = f"{task}\n\nContext: {context}"

            # Conversation history for multi-turn
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]

            # Tool lookup by name
            tools_by_name = {t["name"]: t for t in tools}

            # Reasoning loop
            iteration = 0

            while iteration < max_iterations:
                # Check timeout
                elapsed_ms = (time.time() - start_time) * 1000
                if elapsed_ms > timeout_ms:
                    raise AgentError(f"Agent timed out after {elapsed_ms:.0f}ms")

                iteration += 1
                result.iterations = iteration

                logger.debug(f"Agent iteration {iteration}/{max_iterations}")

                # Call LLM
                llm_response = self._call_llm(
                    messages=messages,
                    model=model,
                    endpoint=endpoint,
                    provider=provider,
                    api_key=api_key
                )

                # Get assistant message
                assistant_message = llm_response.get("content", "").strip()

                if not assistant_message:
                    logger.warning("LLM returned empty response")
                    continue

                # Add to conversation history
                messages.append({"role": "assistant", "content": assistant_message})

                # Parse action from response
                action = self._extract_action(assistant_message)

                if action is None:
                    # LLM didn't follow format - try to recover
                    logger.warning(f"Could not parse action from: {assistant_message[:100]}...")

                    # If it looks like a final answer, treat it as finish
                    if iteration > 1 and not any(t["name"] in assistant_message for t in tools):
                        result.success = True
                        result.result = assistant_message
                        break

                    # Ask LLM to try again
                    messages.append({
                        "role": "user",
                        "content": "Please respond with valid JSON in the format: {\"action\": \"tool_name\", \"args\": {...}} or {\"action\": \"finish\", \"result\": \"...\"}"
                    })
                    continue

                action_type = action.get("action", "")

                # Check for finish
                if action_type == "finish":
                    result.success = True
                    result.result = action.get("result", "Task completed.")
                    break

                # Execute tool
                tool_name = action_type
                tool_args = action.get("args", {})

                if tool_name not in tools_by_name:
                    # Unknown tool - inform LLM
                    messages.append({
                        "role": "user",
                        "content": f"Error: Unknown tool '{tool_name}'. Available tools: {list(tools_by_name.keys())}"
                    })
                    continue

                # Execute the tool
                tool_def = tools_by_name[tool_name]
                tool_call = self._execute_tool(
                    tool_name=tool_name,
                    tool_args=tool_args,
                    tool_def=tool_def,
                    tool_executor=tool_executor
                )

                result.actions.append(tool_call)
                result.action_count += 1

                # Format tool result for LLM
                if tool_call.error:
                    tool_result_msg = f"Tool '{tool_name}' failed with error: {tool_call.error}"
                else:
                    # Format result as string
                    if isinstance(tool_call.result, (dict, list)):
                        tool_result_str = json.dumps(tool_call.result, indent=2, default=str)
                    else:
                        tool_result_str = str(tool_call.result)
                    tool_result_msg = f"Tool '{tool_name}' returned:\n{tool_result_str}"

                messages.append({"role": "user", "content": tool_result_msg})

            # Check if we hit max iterations without finishing
            if not result.success and iteration >= max_iterations:
                result.error = {"message": f"Agent reached maximum iterations ({max_iterations}) without completing the task"}

                # Try to salvage a response from the last assistant message
                if messages and messages[-1].get("role") == "user":
                    # Last message was a tool result, look for previous assistant response
                    for msg in reversed(messages):
                        if msg.get("role") == "assistant":
                            result.result = f"[Incomplete] {msg.get('content', '')[:500]}"
                            break

        except AgentError as e:
            logger.error(f"Agent error: {e}")
            result.success = False
            result.error = {"message": str(e)}

        except Exception as e:
            logger.exception(f"Unexpected error in agent execution: {e}")
            result.success = False
            result.error = {"message": f"Internal error: {str(e)}"}

        result.execution_time_ms = (time.time() - start_time) * 1000
        logger.info(f"Agent completed in {result.execution_time_ms:.0f}ms, "
                   f"iterations={result.iterations}, actions={result.action_count}, "
                   f"success={result.success}")

        return result

    def _build_tools_description(self, tools: List[Dict[str, Any]]) -> str:
        """Build human-readable tools description for system prompt."""
        lines = []
        for tool in tools:
            name = tool.get("name", "unknown")
            desc = tool.get("description", "No description")
            params = tool.get("params", [])

            # Build parameter string
            param_parts = []
            for p in params:
                p_name = p.get("name", "")
                p_type = p.get("type", "string")
                p_req = " (required)" if p.get("required") else ""
                p_desc = f" - {p.get('description')}" if p.get("description") else ""
                param_parts.append(f"    - {p_name}: {p_type}{p_req}{p_desc}")

            params_str = "\n".join(param_parts) if param_parts else "    (no parameters)"

            lines.append(f"• {name}: {desc}")
            lines.append(f"  Parameters:\n{params_str}")
            lines.append("")

        return "\n".join(lines)

    def _call_llm(
        self,
        messages: List[Dict[str, str]],
        model: str,
        endpoint: str,
        provider: str = "auto",
        api_key: str = ""
    ) -> Dict[str, Any]:
        """
        Call LLM with messages using multi-provider support.

        Args:
            messages: Chat messages
            model: Model name
            endpoint: API endpoint (optional)
            provider: Provider name (ollama, openai, anthropic, auto)
            api_key: API key for cloud providers

        Returns:
            Dict with 'content' key containing the response
        """
        try:
            # Use multi-provider service
            response = self.multi_llm_service.chat(
                messages=messages,
                model=model,
                provider=provider if provider != "auto" else None,
                endpoint=endpoint if endpoint else None,
                api_key=api_key if api_key else None,
                temperature=0.1,  # Low temperature for deterministic tool use
            )

            # Handle response format from MultiProviderLLMService
            if isinstance(response, dict):
                if "content" in response:
                    return response
                elif "data" in response:
                    return {"content": response["data"]}

            return {"content": str(response)}

        except LLMProviderError as e:
            logger.error(f"LLM provider error: {e}")
            raise AgentError(f"LLM provider error: {e}")

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise AgentError(f"Failed to call LLM: {e}")

    def _extract_action(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract action JSON from LLM response."""
        # Try to find JSON in markdown code blocks first
        json_patterns = [
            r'```json\s*(\{.*?\})\s*```',  # ```json {...} ```
            r'```\s*(\{.*?\})\s*```',       # ``` {...} ```
            r'(\{[^{}]*"action"[^{}]*\})',  # Bare JSON with "action"
        ]

        for pattern in json_patterns:
            match = re.search(pattern, response, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group(1))
                    if "action" in parsed:
                        return parsed
                except json.JSONDecodeError:
                    continue

        # Try parsing the entire response as JSON
        try:
            parsed = json.loads(response.strip())
            if "action" in parsed:
                return parsed
        except json.JSONDecodeError:
            pass

        return None

    def _execute_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        tool_def: Dict[str, Any],
        tool_executor: Optional[Callable] = None
    ) -> ToolCall:
        """Execute a tool and return the result."""
        start = time.time()
        call = ToolCall(tool=tool_name, args=tool_args)

        try:
            # Check for registered handler first
            if tool_name in self._tool_handlers:
                handler = self._tool_handlers[tool_name]
                call.result = handler(tool_args)

            # Use provided executor for AST body execution
            elif tool_executor and "body" in tool_def:
                call.result = tool_executor(tool_name, tool_args, tool_def["body"])

            # Check for inline function/handler in tool definition
            elif "handler" in tool_def:
                handler = tool_def["handler"]
                if callable(handler):
                    call.result = handler(**tool_args)
                else:
                    call.error = "Tool handler is not callable"

            else:
                # No handler - return placeholder
                call.result = f"Tool '{tool_name}' executed with args: {tool_args}"
                logger.warning(f"No handler for tool '{tool_name}', returning placeholder")

        except Exception as e:
            call.error = str(e)
            logger.error(f"Tool '{tool_name}' execution failed: {e}")

        call.duration_ms = (time.time() - start) * 1000
        return call


# Global singleton
_agent_service: Optional[AgentService] = None


def get_agent_service(llm_service=None) -> AgentService:
    """
    Get or create the global AgentService instance.

    Args:
        llm_service: Optional LLMService to use (uses default if None)

    Returns:
        AgentService instance
    """
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService(llm_service)
    return _agent_service


def reset_agent_service():
    """Reset the global agent service (for testing)."""
    global _agent_service
    _agent_service = None


# ============================================
# MULTI-AGENT SYSTEM
# ============================================

@dataclass
class AgentHandoff:
    """Record of a handoff between agents."""
    from_agent: str
    to_agent: str
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "fromAgent": self.from_agent,
            "toAgent": self.to_agent,
            "message": self.message,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class TeamResult:
    """Result of multi-agent team execution."""
    success: bool = False
    final_response: str = ""
    final_agent: str = ""  # Which agent produced the final answer
    handoffs: List[AgentHandoff] = field(default_factory=list)
    total_iterations: int = 0
    execution_time_ms: float = 0
    agent_results: Dict[str, AgentResult] = field(default_factory=dict)
    shared_context: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for template access."""
        return {
            "success": self.success,
            "finalResponse": self.final_response,
            "finalAgent": self.final_agent,
            "handoffs": [h.to_dict() for h in self.handoffs],
            "totalIterations": self.total_iterations,
            "executionTime": self.execution_time_ms,
            "agentResults": {k: v.to_dict() for k, v in self.agent_results.items()},
            "sharedContext": self.shared_context,
            "error": self.error
        }


# Built-in tool definitions for multi-agent systems
BUILTIN_TOOLS = {
    "handoff": {
        "name": "handoff",
        "description": "Transfer the current task to another agent in the team. Use this when the task requires expertise from a different specialist.",
        "params": [
            {"name": "agent", "type": "string", "required": True,
             "description": "Name of the agent to hand off to"},
            {"name": "message", "type": "string", "required": False,
             "description": "Context or instructions for the next agent"}
        ]
    },
    "readShared": {
        "name": "readShared",
        "description": "Read a value from the team's shared memory. Use this to access information stored by other agents.",
        "params": [
            {"name": "key", "type": "string", "required": True,
             "description": "The key to read from shared memory"}
        ]
    },
    "writeShared": {
        "name": "writeShared",
        "description": "Write a value to the team's shared memory. Use this to store information for other agents.",
        "params": [
            {"name": "key", "type": "string", "required": True,
             "description": "The key to write to"},
            {"name": "value", "type": "string", "required": True,
             "description": "The value to store"}
        ]
    },
    "listAgents": {
        "name": "listAgents",
        "description": "List all available agents in the team and their roles.",
        "params": []
    }
}


class AgentRegistry:
    """
    Central registry for agent discovery.

    Allows agents to be registered and discovered by name,
    enabling dynamic handoffs between agents.
    """

    def __init__(self):
        self._agents: Dict[str, Dict[str, Any]] = {}  # name -> config
        self._teams: Dict[str, 'AgentTeam'] = {}

    def register(self, name: str, config: Dict[str, Any]):
        """Register an agent configuration."""
        self._agents[name] = config
        logger.debug(f"Registered agent: {name}")

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """Get an agent configuration by name."""
        return self._agents.get(name)

    def list_agents(self) -> List[str]:
        """List all registered agent names."""
        return list(self._agents.keys())

    def unregister(self, name: str):
        """Unregister an agent."""
        if name in self._agents:
            del self._agents[name]
            logger.debug(f"Unregistered agent: {name}")

    def register_team(self, name: str, team: 'AgentTeam'):
        """Register a team."""
        self._teams[name] = team
        logger.debug(f"Registered team: {name}")

    def get_team(self, name: str) -> Optional['AgentTeam']:
        """Get a team by name."""
        return self._teams.get(name)

    def clear(self):
        """Clear all registrations."""
        self._agents.clear()
        self._teams.clear()


class AgentTeam:
    """
    Team of collaborating agents with shared context.

    Manages:
    - Agent configurations and discovery
    - Shared memory between agents
    - Handoff execution and logging
    - Safety limits (max handoffs, cycle detection)
    """

    def __init__(
        self,
        name: str,
        agents: Dict[str, Dict[str, Any]],
        shared_context: Optional[Dict[str, Any]] = None,
        supervisor: str = "",
        max_handoffs: int = 10,
        max_total_iterations: int = 50,
        agent_service: Optional['AgentService'] = None
    ):
        """
        Initialize agent team.

        Args:
            name: Team name
            agents: Dict of agent name -> agent config
            shared_context: Initial shared state
            supervisor: Default entry agent
            max_handoffs: Maximum handoffs allowed
            max_total_iterations: Max iterations across all agents
            agent_service: AgentService for executing individual agents
        """
        self.name = name
        self.agents = agents
        self.shared_context = shared_context or {}
        self.supervisor = supervisor or (list(agents.keys())[0] if agents else "")
        self.max_handoffs = max_handoffs
        self.max_total_iterations = max_total_iterations
        self.handoff_log: List[AgentHandoff] = []
        self._agent_service = agent_service

        # Cycle detection: track handoff patterns
        self._handoff_counts: Dict[str, int] = defaultdict(int)

    @property
    def agent_service(self) -> 'AgentService':
        """Lazy-load agent service."""
        if self._agent_service is None:
            self._agent_service = get_agent_service()
        return self._agent_service

    def get_shared(self, key: str) -> Any:
        """Read from shared context."""
        return self.shared_context.get(key)

    def set_shared(self, key: str, value: Any):
        """Write to shared context."""
        self.shared_context[key] = value
        logger.debug(f"Team '{self.name}' shared['{key}'] = {value}")

    def list_agent_names(self) -> List[str]:
        """List all agent names in the team."""
        return list(self.agents.keys())

    def get_agent_info(self) -> List[Dict[str, str]]:
        """Get info about all agents for listAgents tool."""
        result = []
        for name, config in self.agents.items():
            info = {"name": name}
            if "instruction" in config:
                # Extract first line as role description
                instruction = config["instruction"]
                if isinstance(instruction, str):
                    info["role"] = instruction.split('\n')[0][:100]
            result.append(info)
        return result

    def _check_handoff_cycle(self, from_agent: str, to_agent: str) -> bool:
        """
        Check if this handoff would create a problematic cycle.

        Returns True if handoff should be blocked.
        """
        key = f"{from_agent}->{to_agent}"
        self._handoff_counts[key] += 1

        # Block after 2 cycles of same handoff pattern
        if self._handoff_counts[key] > 2:
            logger.warning(f"Handoff cycle detected: {key} occurred {self._handoff_counts[key]} times")
            return True
        return False

    def handoff(
        self,
        from_agent: str,
        to_agent: str,
        message: str = ""
    ) -> Optional[str]:
        """
        Execute a handoff from one agent to another.

        Args:
            from_agent: Source agent name
            to_agent: Target agent name
            message: Context message for target agent

        Returns:
            Error message if handoff blocked, None if successful
        """
        # Validate target agent exists
        if to_agent not in self.agents:
            return f"Unknown agent: {to_agent}. Available: {list(self.agents.keys())}"

        # Check handoff limit
        if len(self.handoff_log) >= self.max_handoffs:
            return f"Maximum handoffs ({self.max_handoffs}) reached"

        # Check for cycles
        if self._check_handoff_cycle(from_agent, to_agent):
            return f"Handoff cycle detected ({from_agent} -> {to_agent})"

        # Record handoff
        handoff = AgentHandoff(
            from_agent=from_agent,
            to_agent=to_agent,
            message=message
        )
        self.handoff_log.append(handoff)
        logger.info(f"Team '{self.name}': {from_agent} -> {to_agent}: {message}")

        return None

    def execute(
        self,
        task: str,
        entry_agent: Optional[str] = None,
        context: str = "",
        tool_executor: Optional[Callable] = None
    ) -> TeamResult:
        """
        Execute the team with a task.

        Args:
            task: The task to complete
            entry_agent: Starting agent (defaults to supervisor)
            context: Additional context
            tool_executor: Function to execute custom tool bodies

        Returns:
            TeamResult with final response and execution details
        """
        start_time = time.time()
        result = TeamResult(shared_context=dict(self.shared_context))

        current_agent = entry_agent or self.supervisor
        current_task = task
        current_context = context
        total_iterations = 0

        try:
            while True:
                # Check iteration limit
                if total_iterations >= self.max_total_iterations:
                    result.error = {
                        "message": f"Maximum total iterations ({self.max_total_iterations}) reached"
                    }
                    break

                # Check handoff limit
                if len(self.handoff_log) >= self.max_handoffs:
                    result.error = {
                        "message": f"Maximum handoffs ({self.max_handoffs}) reached"
                    }
                    break

                # Get agent config
                agent_config = self.agents.get(current_agent)
                if not agent_config:
                    result.error = {"message": f"Unknown agent: {current_agent}"}
                    break

                logger.info(f"Team '{self.name}': Executing agent '{current_agent}'")

                # Build tools with built-in handlers
                tools = self._build_agent_tools(current_agent, agent_config, tool_executor)

                # Create tool executor that handles built-in tools
                def team_tool_executor(tool_name: str, tool_args: dict, body: list):
                    return self._execute_tool(
                        tool_name, tool_args, body,
                        current_agent, tool_executor
                    )

                # Execute agent
                agent_result = self.agent_service.execute(
                    instruction=agent_config.get("instruction", ""),
                    tools=tools,
                    task=current_task,
                    context=current_context,
                    model=agent_config.get("model", "phi3"),
                    endpoint=agent_config.get("endpoint", ""),
                    provider=agent_config.get("provider", "auto"),
                    api_key=agent_config.get("api_key", ""),
                    max_iterations=agent_config.get("max_iterations", 10),
                    timeout_ms=agent_config.get("timeout", 60000),
                    tool_executor=team_tool_executor
                )

                # Store agent result
                result.agent_results[current_agent] = agent_result
                total_iterations += agent_result.iterations

                # Check for handoff in actions
                handoff_action = None
                for action in agent_result.actions:
                    if action.tool == "handoff" and action.result:
                        if isinstance(action.result, dict) and "next_agent" in action.result:
                            handoff_action = action.result
                            break

                if handoff_action:
                    # Execute handoff
                    next_agent = handoff_action["next_agent"]
                    handoff_message = handoff_action.get("message", "")

                    error = self.handoff(current_agent, next_agent, handoff_message)
                    if error:
                        result.error = {"message": error}
                        result.final_response = agent_result.result
                        result.final_agent = current_agent
                        break

                    # Continue with next agent
                    current_agent = next_agent
                    current_task = f"{task}\n\nHandoff context: {handoff_message}"
                    current_context = f"Previous agent ({current_agent}) handed off with message: {handoff_message}"

                else:
                    # No handoff - this is the final response
                    result.success = agent_result.success
                    result.final_response = agent_result.result
                    result.final_agent = current_agent
                    if agent_result.error:
                        result.error = agent_result.error
                    break

        except Exception as e:
            logger.exception(f"Team execution error: {e}")
            result.error = {"message": str(e)}

        result.handoffs = self.handoff_log.copy()
        result.total_iterations = total_iterations
        result.execution_time_ms = (time.time() - start_time) * 1000
        result.shared_context = dict(self.shared_context)

        logger.info(f"Team '{self.name}' completed: success={result.success}, "
                   f"handoffs={len(result.handoffs)}, iterations={total_iterations}, "
                   f"final_agent={result.final_agent}")

        return result

    def _build_agent_tools(
        self,
        agent_name: str,
        agent_config: Dict[str, Any],
        tool_executor: Optional[Callable]
    ) -> List[Dict[str, Any]]:
        """Build tool definitions for an agent, including built-in tools."""
        tools = []

        # Get tools from agent config
        config_tools = agent_config.get("tools", [])
        for tool in config_tools:
            if tool.get("builtin"):
                # Add built-in tool definition
                builtin_name = tool.get("name", "")
                if builtin_name in BUILTIN_TOOLS:
                    builtin_def = BUILTIN_TOOLS[builtin_name].copy()
                    tools.append(builtin_def)
            else:
                tools.append(tool)

        return tools

    def _execute_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        body: list,
        current_agent: str,
        tool_executor: Optional[Callable]
    ) -> Any:
        """Execute a tool, handling built-in tools specially."""

        # Handle built-in tools
        if tool_name == "handoff":
            target = tool_args.get("agent", "")
            message = tool_args.get("message", "")

            # Validate target exists
            if target not in self.agents:
                return {"error": f"Unknown agent: {target}. Available: {list(self.agents.keys())}"}

            # Return handoff instruction (will be processed by execute loop)
            return {"next_agent": target, "message": message}

        elif tool_name == "readShared":
            key = tool_args.get("key", "")
            value = self.get_shared(key)
            if value is None:
                return f"Key '{key}' not found in shared context"
            return value

        elif tool_name == "writeShared":
            key = tool_args.get("key", "")
            value = tool_args.get("value", "")
            self.set_shared(key, value)
            return f"Stored '{key}' in shared context"

        elif tool_name == "listAgents":
            agents_info = self.get_agent_info()
            return agents_info

        # Custom tool - use provided executor
        elif tool_executor and body:
            return tool_executor(tool_name, tool_args, body)

        else:
            return f"Tool '{tool_name}' executed with args: {tool_args}"


class MultiAgentService:
    """
    Service for managing multi-agent teams.

    Provides:
    - Team creation and registration
    - Team execution
    - Global agent registry
    """

    def __init__(self, agent_service: Optional[AgentService] = None):
        """Initialize multi-agent service."""
        self._agent_service = agent_service
        self.registry = AgentRegistry()

    @property
    def agent_service(self) -> AgentService:
        """Lazy-load agent service."""
        if self._agent_service is None:
            self._agent_service = get_agent_service()
        return self._agent_service

    def create_team(
        self,
        name: str,
        agents: Dict[str, Dict[str, Any]],
        shared: Optional[Dict[str, Any]] = None,
        supervisor: str = "",
        max_handoffs: int = 10,
        max_total_iterations: int = 50
    ) -> AgentTeam:
        """
        Create and register a new agent team.

        Args:
            name: Team name
            agents: Dict of agent name -> agent config
            shared: Initial shared context
            supervisor: Entry agent name
            max_handoffs: Maximum handoffs allowed
            max_total_iterations: Max total iterations

        Returns:
            AgentTeam instance
        """
        team = AgentTeam(
            name=name,
            agents=agents,
            shared_context=shared,
            supervisor=supervisor,
            max_handoffs=max_handoffs,
            max_total_iterations=max_total_iterations,
            agent_service=self.agent_service
        )

        self.registry.register_team(name, team)
        return team

    def get_team(self, name: str) -> Optional[AgentTeam]:
        """Get a registered team by name."""
        return self.registry.get_team(name)

    def execute_team(
        self,
        name: str,
        task: str,
        entry_agent: Optional[str] = None,
        context: str = "",
        tool_executor: Optional[Callable] = None
    ) -> TeamResult:
        """
        Execute a registered team.

        Args:
            name: Team name
            task: Task to complete
            entry_agent: Starting agent
            context: Additional context
            tool_executor: Custom tool executor

        Returns:
            TeamResult
        """
        team = self.get_team(name)
        if not team:
            result = TeamResult()
            result.error = {"message": f"Team '{name}' not found"}
            return result

        return team.execute(task, entry_agent, context, tool_executor)


# Global singleton for multi-agent service
_multi_agent_service: Optional[MultiAgentService] = None


def get_multi_agent_service(agent_service: Optional[AgentService] = None) -> MultiAgentService:
    """
    Get or create the global MultiAgentService instance.

    Args:
        agent_service: Optional AgentService to use

    Returns:
        MultiAgentService instance
    """
    global _multi_agent_service
    if _multi_agent_service is None:
        _multi_agent_service = MultiAgentService(agent_service)
    return _multi_agent_service


def reset_multi_agent_service():
    """Reset the global multi-agent service (for testing)."""
    global _multi_agent_service
    _multi_agent_service = None
