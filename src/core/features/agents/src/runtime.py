"""
Runtime for Agents Feature

Agent orchestration with tools and reasoning.
"""

from typing import Dict, Any, List, Optional
import json


class AgentRegistry:
    """Registry for agent configurations"""

    def __init__(self):
        self.agents: Dict[str, Any] = {}

    def register(self, agent_id: str, agent):
        """Register an agent"""
        self.agents[agent_id] = agent

    def get(self, agent_id: str):
        """Get an agent by ID"""
        return self.agents.get(agent_id)


class AgentTool:
    """Represents a tool available to an agent"""

    def __init__(self, tool_node, llm_runtime=None, rag_runtime=None):
        self.name = tool_node.name
        self.tool_type = tool_node.tool_type
        self.knowledge_id = tool_node.knowledge_id
        self.function_name = tool_node.function_name
        self.top_k = tool_node.top_k
        self.parameters = tool_node.parameters

        self.llm_runtime = llm_runtime
        self.rag_runtime = rag_runtime

    def execute(self, input_data: str, context_vars: Dict[str, Any]) -> str:
        """
        Execute the tool

        Args:
            input_data: Input for the tool
            context_vars: Execution context variables

        Returns:
            Tool output as string
        """
        if self.tool_type == "search":
            return self._execute_search(input_data, context_vars)
        elif self.tool_type == "function":
            return self._execute_function(input_data, context_vars)
        else:
            return f"[ERROR: Unknown tool type '{self.tool_type}']"

    def _execute_search(self, query: str, context_vars: Dict[str, Any]) -> str:
        """Execute knowledge base search"""
        if not self.rag_runtime:
            return "[ERROR: RAG runtime not available]"

        if not self.knowledge_id:
            return "[ERROR: No knowledge base specified for search tool]"

        # Get knowledge base
        kb = self.rag_runtime.registry.get(self.knowledge_id)
        if not kb:
            return f"[ERROR: Knowledge base '{self.knowledge_id}' not found]"

        # Search
        results = kb.search(query=query, top_k=self.top_k)

        if not results:
            return "[No relevant information found]"

        # Format results
        output = []
        for i, result in enumerate(results, 1):
            output.append(f"[{i}] {result['content'][:500]}...")
            output.append(f"    (Score: {result['score']:.2f})")

        return "\n".join(output)

    def _execute_function(self, input_data: str, context_vars: Dict[str, Any]) -> str:
        """Execute custom function (TODO: implement)"""
        return f"[Function tool '{self.function_name}' not yet implemented]"

    def get_description(self) -> str:
        """Get tool description for LLM"""
        if self.tool_type == "search":
            return f"search(query: str) -> Searches the '{self.knowledge_id}' knowledge base and returns relevant information"
        elif self.tool_type == "function":
            return f"{self.function_name}() -> Calls the function {self.function_name}"
        else:
            return f"{self.name}() -> Tool description"


class Agent:
    """
    AI Agent with reasoning and tool usage

    Implements a ReAct-style agent (Reasoning + Acting)
    """

    def __init__(
        self,
        agent_node,
        llm_runtime=None,
        rag_runtime=None
    ):
        self.agent_id = agent_node.agent_id
        self.llm_id = agent_node.llm_id
        self.knowledge_ids = agent_node.knowledge_ids
        self.goal = agent_node.goal
        self.personality = agent_node.personality
        self.max_iterations = agent_node.max_iterations

        # Initialize tools
        self.tools = {}
        for tool_node in agent_node.tools:
            tool = AgentTool(tool_node, llm_runtime, rag_runtime)
            self.tools[tool.name] = tool

        # Runtimes
        self.llm_runtime = llm_runtime
        self.rag_runtime = rag_runtime

        # Memory
        self.conversation_history = []

    def ask(
        self,
        question: str,
        context_vars: Dict[str, Any],
        show_thinking: bool = False
    ) -> Dict[str, Any]:
        """
        Ask the agent a question

        Args:
            question: User's question
            context_vars: Execution context variables
            show_thinking: Include agent's reasoning process

        Returns:
            Dict with 'answer', 'sources', 'thinking'
        """
        # Build system prompt
        system_prompt = self._build_system_prompt()

        # Build initial prompt
        prompt = self._build_user_prompt(question)

        # Track thinking process
        thinking_steps = []
        sources = []

        # Reasoning loop (ReAct style)
        for iteration in range(self.max_iterations):
            thinking_steps.append(f"[Iteration {iteration + 1}]")

            # Get LLM response
            llm_config = self.llm_runtime.registry.get(self.llm_id)
            if not llm_config:
                return {
                    'answer': f"[ERROR: LLM '{self.llm_id}' not found]",
                    'sources': [],
                    'thinking': thinking_steps
                }

            # Generate response
            from ..llm.src.ast_node import LLMGenerateNode
            llm_gen = LLMGenerateNode(
                llm_id=self.llm_id,
                prompt=f"{system_prompt}\n\n{prompt}",
                result_var="agent_response",
                stream=False,
                cache=False
            )

            response = self.llm_runtime.generate(llm_gen, context_vars)
            thinking_steps.append(f"Agent: {response}")

            # Check if agent wants to use a tool
            if "USE_TOOL:" in response:
                # Parse tool usage (simple format: USE_TOOL: tool_name | input)
                try:
                    tool_part = response.split("USE_TOOL:")[1].strip()
                    tool_name, tool_input = tool_part.split("|", 1)
                    tool_name = tool_name.strip()
                    tool_input = tool_input.strip()

                    # Execute tool
                    if tool_name in self.tools:
                        tool = self.tools[tool_name]
                        tool_output = tool.execute(tool_input, context_vars)

                        thinking_steps.append(f"Tool '{tool_name}': {tool_output[:200]}...")
                        sources.append({
                            'tool': tool_name,
                            'input': tool_input,
                            'output': tool_output
                        })

                        # Update prompt with tool output
                        prompt += f"\n\nTool Output:\n{tool_output}\n\nBased on this, continue answering the question."
                    else:
                        thinking_steps.append(f"[ERROR: Tool '{tool_name}' not found]")
                        break
                except Exception as e:
                    thinking_steps.append(f"[ERROR parsing tool usage: {e}]")
                    break
            else:
                # Agent has given a final answer
                answer = response.replace("FINAL_ANSWER:", "").strip()

                return {
                    'answer': answer,
                    'sources': sources,
                    'thinking': thinking_steps if show_thinking else []
                }

        # Max iterations reached
        return {
            'answer': response,
            'sources': sources,
            'thinking': thinking_steps if show_thinking else []
        }

    def _build_system_prompt(self) -> str:
        """Build system prompt for agent"""
        parts = []

        if self.goal:
            parts.append(f"Goal: {self.goal}")

        if self.personality:
            parts.append(f"Personality: {self.personality}")

        if self.tools:
            parts.append("\nAvailable Tools:")
            for tool in self.tools.values():
                parts.append(f"- {tool.get_description()}")

            parts.append("\nTo use a tool, respond with:")
            parts.append("USE_TOOL: tool_name | input")
            parts.append("\nWhen you have the final answer, respond with:")
            parts.append("FINAL_ANSWER: your answer here")

        return "\n".join(parts)

    def _build_user_prompt(self, question: str) -> str:
        """Build user prompt"""
        return f"User Question: {question}\n\nThink step by step and use tools if needed."


class AgentRuntime:
    """Runtime for agent operations"""

    def __init__(self, llm_runtime=None, rag_runtime=None):
        self.registry = AgentRegistry()
        self.llm_runtime = llm_runtime
        self.rag_runtime = rag_runtime

    def register_agent(self, agent_node) -> Agent:
        """
        Register an agent from AgentNode

        Args:
            agent_node: AgentNode from parser

        Returns:
            Agent instance
        """
        agent = Agent(
            agent_node,
            llm_runtime=self.llm_runtime,
            rag_runtime=self.rag_runtime
        )

        self.registry.register(agent_node.agent_id, agent)

        return agent

    def ask_agent(
        self,
        agent_ask_node,
        context_vars: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Ask an agent a question

        Args:
            agent_ask_node: AgentAskNode from parser
            context_vars: Execution context variables

        Returns:
            Agent response with answer, sources, thinking
        """
        # Get agent
        agent = self.registry.get(agent_ask_node.agent_id)
        if not agent:
            return {
                'answer': f"[ERROR: Agent '{agent_ask_node.agent_id}' not found]",
                'sources': [],
                'thinking': []
            }

        # Apply databinding to question
        question = self._apply_databinding(agent_ask_node.question, context_vars)

        # Ask agent
        result = agent.ask(
            question=question,
            context_vars=context_vars,
            show_thinking=agent_ask_node.show_thinking
        )

        return result

    def _apply_databinding(self, text: str, context_vars: Dict[str, Any]) -> str:
        """Apply databinding to text"""
        import re

        def replace_var(match):
            var_name = match.group(1).strip()
            return str(context_vars.get(var_name, f'{{{var_name}}}'))

        return re.sub(r'\{([^}]+)\}', replace_var, text)
