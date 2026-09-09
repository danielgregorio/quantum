"""
Team Executor - Execute q:team statements

Handles multi-agent team execution with handoffs.
"""

from typing import Any, List, Dict, Type
from quantum.runtime.executors.base import BaseExecutor, ExecutorError
from quantum.runtime.executors.ai.agent_executor import build_tool_definitions, build_tool_executor

# Import from features module
try:
    from quantum.core.features.agents.src.ast_node import AgentTeamNode
except ImportError:
    from quantum.core.features.agents.src import AgentTeamNode



# The tools that make a team a team. An agent inside <q:team> gets them
# automatically.
#
# They used to require an explicit <q:tool name="handoff" builtin="true" /> on
# every agent, and nobody wrote it — examples/multi_agent_support.q advertises
# "Built-in handoff, readShared, writeShared, listAgents tools" in its header
# and instructs the router to "use the handoff tool", while declaring none of
# them. So the tool did not exist, the model could not call it, and the team
# ended at its first agent reporting success. A q:team exists in order to hand
# off; making that opt-in was boilerplate everyone forgets.
#
# An agent that declares a tool of the same name wins, so this cannot shadow a
# deliberate override.
_TEAM_BUILTINS = ('handoff', 'readShared', 'writeShared', 'listAgents')


def _team_tools(agent):
    """Explicit tools first, then any team builtin the agent did not define."""
    from quantum.runtime.agent_service import BUILTIN_TOOLS

    tools = build_tool_definitions(agent.tools)
    declared = {t.get('name') for t in tools}
    for name in _TEAM_BUILTINS:
        if name not in declared and name in BUILTIN_TOOLS:
            tools.append(dict(BUILTIN_TOOLS[name]))
    return tools


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

            # MultiAgentService.create_team() takes a {name: config} dict —
            # not a list, and not the team_config dict this executor used to
            # build. execute_team() also lives on services.multi_agent, not
            # services.agent (which is the single-agent AgentService).
            agents = {
                agent.name: self._build_agent_config(agent, context)
                for agent in node.agents
            }

            multi_agent = self.services.multi_agent
            multi_agent.create_team(
                name=node.name,
                agents=agents,
                shared=shared_context,
                supervisor=node.supervisor or entry_agent,
                max_handoffs=node.max_handoffs,
                max_total_iterations=node.max_total_iterations,
            )

            team_result = multi_agent.execute_team(
                name=node.name,
                task=task,
                entry_agent=entry_agent,
                context="",
                tool_executor=build_tool_executor(
                    self, exec_context,
                    [tool for agent in node.agents for tool in agent.tools],
                ),
            )

            result = team_result.to_dict()

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
        """Build agent configuration dict from AgentNode.

        Key names must match what AgentTeam.execute() reads:
        instruction/model/endpoint/provider/api_key/max_iterations/timeout/tools.
        """
        instruction = ""
        if agent.instruction:
            instruction = self.apply_databinding(agent.instruction.content, context)

        api_key = ""
        if agent.api_key:
            api_key = self.apply_databinding(agent.api_key, context)

        endpoint = ""
        if agent.endpoint:
            endpoint = self.apply_databinding(agent.endpoint, context)

        return {
            'name': agent.name,
            'model': agent.model,
            'provider': agent.provider,
            'endpoint': endpoint,
            'api_key': api_key,
            'instruction': instruction,
            'tools': _team_tools(agent),
            'max_iterations': agent.max_iterations,
            'timeout': agent.timeout,
        }
