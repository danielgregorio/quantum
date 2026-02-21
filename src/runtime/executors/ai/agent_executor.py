"""
Agent Executor - Execute q:agent statements

Handles AI agent execution with tool use capabilities.
"""

from typing import Any, List, Dict, Type
from runtime.executors.base import BaseExecutor, ExecutorError

# Import from features module
try:
    from core.features.agents.src.ast_node import AgentNode
except ImportError:
    from core.features.agents.src import AgentNode


class AgentExecutor(BaseExecutor):
    """
    Executor for q:agent statements.

    Supports:
    - Multi-turn agent reasoning loop
    - Tool calling and execution
    - Multiple LLM providers (Ollama, OpenAI, Anthropic)
    - Iteration limits and timeouts
    """

    @property
    def handles(self) -> List[Type]:
        return [AgentNode]

    def execute(self, node: AgentNode, exec_context) -> Any:
        """
        Execute AI agent.

        Args:
            node: AgentNode with agent configuration
            exec_context: Execution context

        Returns:
            Agent response dict with result and actions
        """
        try:
            context = exec_context.get_all_variables()

            # Resolve task from execute node
            if not node.execute:
                raise ExecutorError("Agent requires <q:execute> to run")

            task = self.apply_databinding(node.execute.task, context)
            task_context = ""
            if node.execute.context:
                task_context = self.apply_databinding(node.execute.context, context)

            # Build instruction
            instruction = ""
            if node.instruction:
                instruction = self.apply_databinding(node.instruction.content, context)

            # Build tools schema
            tools = []
            for tool in node.tools:
                if tool.builtin:
                    # Built-in tools are handled by the agent service
                    tools.append({
                        'name': tool.name,
                        'builtin': True
                    })
                else:
                    tools.append(tool.get_schema())

            # Resolve API key if provided
            api_key = None
            if node.api_key:
                api_key = self.apply_databinding(node.api_key, context)

            # Resolve endpoint if provided
            endpoint = None
            if node.endpoint:
                endpoint = self.apply_databinding(node.endpoint, context)

            # Execute agent
            result = self.services.agent.execute(
                model=node.model,
                provider=node.provider,
                endpoint=endpoint,
                api_key=api_key,
                instruction=instruction,
                tools=tools,
                tool_nodes=node.tools,
                task=task,
                context=task_context,
                max_iterations=node.max_iterations,
                timeout=node.timeout,
                exec_context=exec_context,
                runtime=self._runtime
            )

            # Store results
            exec_context.set_variable(node.name, result.get('result', ''), scope="component")
            exec_context.set_variable(f"{node.name}_result", result, scope="component")

            return result

        except Exception as e:
            error_result = {
                'success': False,
                'error': {'message': str(e)},
                'result': '',
                'iterations': 0,
                'actions': []
            }
            exec_context.set_variable(f"{node.name}_result", error_result, scope="component")
            raise ExecutorError(f"Agent execution error: {e}")
