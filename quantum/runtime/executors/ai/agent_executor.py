"""
Agent Executor - Execute q:agent statements

Handles AI agent execution with tool use capabilities.
"""

from typing import Any, List, Dict, Type
from quantum.runtime.executors.base import BaseExecutor, ExecutorError
from quantum.core.ast_nodes import (
    QuantumReturn,
    HTMLNode, TextNode, DocTypeNode, CommentNode,
)

# Import from features module
try:
    from quantum.core.features.agents.src.ast_node import AgentNode
except ImportError:
    from quantum.core.features.agents.src import AgentNode

_RENDER_ONLY_NODE_TYPES = (HTMLNode, TextNode, DocTypeNode, CommentNode)


def build_tool_definitions(tool_nodes) -> List[Dict[str, Any]]:
    """
    Build the tool definitions AgentService actually consumes.

    AgentService._build_tools_description() reads name/description/params
    (a list of param dicts), and AgentService._execute_tool() reads
    tool_def["body"] to hand the AST statements to tool_executor. The
    JSON-Schema shape from AgentToolNode.get_schema() has neither, which is
    why tools used to silently degrade to the "no handler" placeholder.
    """
    from quantum.runtime.agent_service import BUILTIN_TOOLS

    tools = []
    for tool in tool_nodes:
        if tool.builtin:
            builtin_def = BUILTIN_TOOLS.get(tool.name)
            if builtin_def:
                tools.append(dict(builtin_def))
            continue

        tools.append({
            'name': tool.name,
            'description': tool.description,
            'params': [p.to_dict() for p in tool.params],
            'body': tool.body,
        })
    return tools


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

            tools = build_tool_definitions(node.tools)

            api_key = ""
            if node.api_key:
                api_key = self.apply_databinding(node.api_key, context)

            endpoint = ""
            if node.endpoint:
                endpoint = self.apply_databinding(node.endpoint, context)

            agent_result = self.services.agent.execute(
                instruction=instruction,
                tools=tools,
                task=task,
                context=task_context,
                model=node.model,
                endpoint=endpoint,
                provider=node.provider,
                api_key=api_key,
                max_iterations=node.max_iterations,
                timeout_ms=node.timeout,
                tool_executor=build_tool_executor(self, exec_context, node.tools),
            )

            result = agent_result.to_dict()

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


def coerce_tool_args(params, tool_args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Coerce LLM-supplied tool arguments to their declared q:param types.

    An LLM sends every argument as a string ({"a": "17"}), so a tool body
    doing {a + b} would concatenate instead of adding. The declared
    <q:param type="number"> is what tells us the intent.
    """
    by_name = {p.name: p for p in (params or [])}
    coerced = {}

    for key, value in (tool_args or {}).items():
        param = by_name.get(key)
        if param is None or not isinstance(value, str):
            coerced[key] = value
            continue

        try:
            if param.type in ('number', 'decimal'):
                coerced[key] = float(value) if '.' in value else int(value)
            elif param.type == 'integer':
                coerced[key] = int(value)
            elif param.type == 'boolean':
                coerced[key] = value.strip().lower() in ('true', '1', 'yes', 'on')
            elif param.type in ('array', 'object'):
                import json
                coerced[key] = json.loads(value)
            else:
                coerced[key] = value
        except (ValueError, TypeError):
            # Leave the raw value in place — the tool body may still handle it,
            # and a hard failure here would be worse than a best-effort pass.
            coerced[key] = value

    return coerced


def build_tool_executor(executor: BaseExecutor, exec_context, tool_nodes=None):
    """
    Build the tool_executor callable AgentService/AgentTeam expect:
    tool_executor(tool_name, tool_args, body) -> Any

    Runs the tool's AST body in a child context with the LLM-supplied
    arguments coerced to their declared types and bound as local variables.
    """
    params_by_tool = {
        tool.name: tool.params for tool in (tool_nodes or []) if not tool.builtin
    }

    def tool_executor(tool_name: str, tool_args: Dict[str, Any], body: List[Any]) -> Any:
        child_context = exec_context.create_child_context()
        args = coerce_tool_args(params_by_tool.get(tool_name), tool_args)
        for key, value in args.items():
            child_context.set_variable(key, value, scope="local")
        return _run_tool_body(executor, body, child_context)

    return tool_executor


def _run_tool_body(executor: BaseExecutor, body: List[Any], child_context) -> Any:
    """Execute a tool body, returning the first q:return value found."""
    for statement in body or []:
        if isinstance(statement, QuantumReturn):
            return executor.resolve_value(statement.value, child_context.get_all_variables())

        if isinstance(statement, _RENDER_ONLY_NODE_TYPES):
            continue

        # <q:tool> commonly wraps its implementation in a <q:function> —
        # descend into it rather than registering it as a callable function.
        if type(statement).__name__ == 'FunctionNode':
            result = _run_tool_body(executor, getattr(statement, 'body', []), child_context)
            if result is not None:
                return result
            continue

        executor.runtime.executor_registry.execute(statement, child_context)

    return None
