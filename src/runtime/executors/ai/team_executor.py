"""
Team Executor - Execute q:team statements

Handles multi-agent team execution with handoffs.
"""

from typing import Any, List, Dict, Type
from runtime.executors.base import BaseExecutor, ExecutorError

# Import from features module
try:
    from core.features.agents.src.ast_node import AgentTeamNode
except ImportError:
    from core.features.agents.src import AgentTeamNode


class TeamExecutor(BaseExecutor):
    """
    Executor for q:team statements.

    Supports:
    - Multi-agent orchestration
    - Agent handoffs
    - Shared team context
    - Entry point routing
    """

    @property
    def handles(self) -> List[Type]:
        return [AgentTeamNode]

    def execute(self, node: AgentTeamNode, exec_context) -> Any:
        """
        Execute agent team.

        Args:
            node: AgentTeamNode with team configuration
            exec_context: Execution context

        Returns:
            Team execution result dict
        """
        try:
            context = exec_context.get_all_variables()

            # Resolve task from execute node
            if not node.execute:
                raise ExecutorError("Team requires <q:execute> to run")

            task = self.apply_databinding(node.execute.task, context)

            # Determine entry agent
            entry_agent = node.execute.entry or node.supervisor
            if not entry_agent and node.agents:
                entry_agent = node.agents[0].name

            # Initialize shared context
            shared_context = {}
            for set_node in node.shared:
                if hasattr(set_node, 'name') and hasattr(set_node, 'value'):
                    value = self.apply_databinding(set_node.value, context)
                    shared_context[set_node.name] = value

            # Build team configuration
            team_config = {
                'name': node.name,
                'agents': [self._build_agent_config(agent, context) for agent in node.agents],
                'shared': shared_context,
                'entry_agent': entry_agent,
                'max_handoffs': node.max_handoffs,
                'max_total_iterations': node.max_total_iterations
            }

            # Execute team
            result = self.services.agent.execute_team(
                team_config=team_config,
                task=task,
                exec_context=exec_context,
                runtime=self._runtime
            )

            # Store results
            exec_context.set_variable(node.name, result.get('finalResponse', ''), scope="component")
            exec_context.set_variable(f"{node.name}_result", result, scope="component")

            return result

        except Exception as e:
            error_result = {
                'success': False,
                'error': {'message': str(e)},
                'finalResponse': '',
                'handoffs': [],
                'totalIterations': 0
            }
            exec_context.set_variable(f"{node.name}_result", error_result, scope="component")
            raise ExecutorError(f"Team execution error: {e}")

    def _build_agent_config(self, agent, context: Dict[str, Any]) -> Dict[str, Any]:
        """Build agent configuration dict from AgentNode."""
        instruction = ""
        if agent.instruction:
            instruction = self.apply_databinding(agent.instruction.content, context)

        tools = []
        for tool in agent.tools:
            if tool.builtin:
                tools.append({'name': tool.name, 'builtin': True})
            else:
                tools.append(tool.get_schema())

        api_key = None
        if agent.api_key:
            api_key = self.apply_databinding(agent.api_key, context)

        endpoint = None
        if agent.endpoint:
            endpoint = self.apply_databinding(agent.endpoint, context)

        return {
            'name': agent.name,
            'model': agent.model,
            'provider': agent.provider,
            'endpoint': endpoint,
            'api_key': api_key,
            'instruction': instruction,
            'tools': tools,
            'tool_nodes': agent.tools,
            'max_iterations': agent.max_iterations,
            'timeout': agent.timeout
        }
