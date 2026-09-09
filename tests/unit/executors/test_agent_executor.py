"""
Tests for AgentExecutor - q:agent AI agent execution

Rewritten 2026-09-07: the previous version mocked an AgentService.execute()
signature that never existed (tool_nodes=/exec_context=/runtime=/timeout=),
so it could not catch the TypeError the real call raised on every request —
see FULL_AUDIT_2026-09.md. These tests mock the real signature and use the
real AgentResult dataclass so the result shape can't drift either.
"""

import pytest
from unittest.mock import MagicMock
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from quantum.runtime.executors.ai.agent_executor import AgentExecutor, build_tool_definitions
from quantum.runtime.executors.base import ExecutorError
from quantum.runtime.agent_service import AgentResult, ToolCall

try:
    from quantum.core.features.agents.src.ast_node import AgentNode, AgentToolNode, AgentToolParamNode
except ImportError:
    from quantum.core.features.agents.src import AgentNode, AgentToolNode, AgentToolParamNode

from tests.unit.executors.conftest import MockRuntime, MockExecutionContext


class MockAgentService:
    """Mock agent service matching the real AgentService.execute signature."""

    def __init__(self):
        self.last_kwargs: Optional[Dict[str, Any]] = None
        self._results: Dict[str, AgentResult] = {}

    def set_result(self, task: str, result: AgentResult):
        self._results[task] = result

    def execute(self, instruction, tools, task, context="", model="phi3",
                endpoint="", provider="auto", api_key="", max_iterations=10,
                timeout_ms=60000, tool_executor=None) -> AgentResult:
        self.last_kwargs = dict(
            instruction=instruction, tools=tools, task=task, context=context,
            model=model, endpoint=endpoint, provider=provider, api_key=api_key,
            max_iterations=max_iterations, timeout_ms=timeout_ms,
            tool_executor=tool_executor,
        )
        if task in self._results:
            return self._results[task]
        return AgentResult(success=True, result=f"Completed task: {task}", iterations=1)


class MockAgentRuntime(MockRuntime):
    def __init__(self, variables: Dict[str, Any] = None):
        super().__init__(variables)
        self._agent_service = MockAgentService()
        self._services = MagicMock()
        self._services.agent = self._agent_service

    @property
    def services(self):
        return self._services


@dataclass
class MockExecuteNode:
    task: str
    context: Optional[str] = None
    entry: str = ""


@dataclass
class MockInstructionNode:
    content: str


class TestAgentExecutorBasic:
    def test_handles_agent_node(self):
        executor = AgentExecutor(MockAgentRuntime())
        assert AgentNode in executor.handles

    def test_handles_returns_list(self):
        executor = AgentExecutor(MockAgentRuntime())
        assert isinstance(executor.handles, list)
        assert len(executor.handles) == 1


class TestExecuteNode:
    def test_requires_execute_node(self):
        runtime = MockAgentRuntime()
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.execute = None

        with pytest.raises(ExecutorError, match="requires <q:execute>"):
            executor.execute(node, runtime.execution_context)

    def test_task_from_execute(self):
        runtime = MockAgentRuntime()
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.execute = MockExecuteNode("Find the weather in Paris")

        executor.execute(node, runtime.execution_context)

        assert runtime._agent_service.last_kwargs["task"] == "Find the weather in Paris"

    def test_task_with_databinding(self):
        runtime = MockAgentRuntime({"city": "Tokyo"})
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.execute = MockExecuteNode("Find weather in {city}")

        executor.execute(node, runtime.execution_context)

        assert runtime._agent_service.last_kwargs["task"] == "Find weather in Tokyo"

    def test_context_from_execute(self):
        runtime = MockAgentRuntime()
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.execute = MockExecuteNode("Do task", "Additional context here")

        executor.execute(node, runtime.execution_context)

        assert runtime._agent_service.last_kwargs["context"] == "Additional context here"


class TestInstruction:
    def test_instruction_passed(self):
        runtime = MockAgentRuntime()
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.execute = MockExecuteNode("Task")
        node.instruction = MockInstructionNode("You are a helpful assistant")

        executor.execute(node, runtime.execution_context)

        assert runtime._agent_service.last_kwargs["instruction"] == "You are a helpful assistant"

    def test_instruction_with_databinding(self):
        runtime = MockAgentRuntime({"role": "Python expert"})
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.execute = MockExecuteNode("Task")
        node.instruction = MockInstructionNode("You are a {role}")

        executor.execute(node, runtime.execution_context)

        assert runtime._agent_service.last_kwargs["instruction"] == "You are a Python expert"

    def test_empty_instruction(self):
        runtime = MockAgentRuntime()
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.execute = MockExecuteNode("Task")
        node.instruction = None

        executor.execute(node, runtime.execution_context)

        assert runtime._agent_service.last_kwargs["instruction"] == ""


class TestToolDefinitions:
    """Tool dicts must carry name/description/params/body — the shape
    AgentService._build_tools_description() and _execute_tool() read."""

    def test_custom_tool_shape(self):
        runtime = MockAgentRuntime()
        executor = AgentExecutor(runtime)

        tool = AgentToolNode(name="add", description="Adds numbers")
        tool.params = [AgentToolParamNode(name="a", type="number", required=True)]
        tool.body = ["<statement>"]

        node = AgentNode("agent")
        node.execute = MockExecuteNode("Task")
        node.tools = [tool]

        executor.execute(node, runtime.execution_context)

        tools = runtime._agent_service.last_kwargs["tools"]
        assert len(tools) == 1
        assert tools[0]["name"] == "add"
        assert tools[0]["description"] == "Adds numbers"
        assert tools[0]["params"][0]["name"] == "a"
        # body must be present or AgentService falls back to a placeholder
        assert tools[0]["body"] == ["<statement>"]

    def test_builtin_tool_resolves_to_builtin_definition(self):
        runtime = MockAgentRuntime()
        executor = AgentExecutor(runtime)

        tool = AgentToolNode(name="handoff", builtin=True)

        node = AgentNode("agent")
        node.execute = MockExecuteNode("Task")
        node.tools = [tool]

        executor.execute(node, runtime.execution_context)

        tools = runtime._agent_service.last_kwargs["tools"]
        assert len(tools) == 1
        assert tools[0]["name"] == "handoff"
        assert "description" in tools[0]
        assert tools[0]["params"][0]["name"] == "agent"

    def test_unknown_builtin_is_skipped(self):
        tools = build_tool_definitions([AgentToolNode(name="nope", builtin=True)])
        assert tools == []

    def test_multiple_tools(self):
        runtime = MockAgentRuntime()
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.execute = MockExecuteNode("Task")
        node.tools = [
            AgentToolNode(name="handoff", builtin=True),
            AgentToolNode(name="calculator", description="math"),
            AgentToolNode(name="listAgents", builtin=True),
        ]

        executor.execute(node, runtime.execution_context)

        assert len(runtime._agent_service.last_kwargs["tools"]) == 3


class TestToolExecutor:
    """The tool_executor closure is what actually runs a tool's AST body."""

    def test_tool_executor_is_passed(self):
        runtime = MockAgentRuntime()
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.execute = MockExecuteNode("Task")

        executor.execute(node, runtime.execution_context)

        assert callable(runtime._agent_service.last_kwargs["tool_executor"])

    def test_tool_executor_returns_q_return_value(self):
        from quantum.core.ast_nodes import QuantumReturn

        runtime = MockAgentRuntime()
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.execute = MockExecuteNode("Task")
        executor.execute(node, runtime.execution_context)

        tool_executor = runtime._agent_service.last_kwargs["tool_executor"]
        result = tool_executor("add", {"a": 2}, [QuantumReturn(value="{a}")])

        assert result == 2

    def test_tool_executor_descends_into_function_wrapper(self):
        """<q:tool> usually wraps its body in a <q:function> — the executor
        must descend into it, not try to register it as a function."""
        from quantum.core.ast_nodes import QuantumReturn
        from quantum.core.features.functions.src.ast_node import FunctionNode

        runtime = MockAgentRuntime()
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.execute = MockExecuteNode("Task")
        executor.execute(node, runtime.execution_context)

        fn = FunctionNode("doAdd")
        fn.body = [QuantumReturn(value="{value}")]

        tool_executor = runtime._agent_service.last_kwargs["tool_executor"]
        result = tool_executor("add", {"value": 42}, [fn])

        assert result == 42


class TestModelAndProvider:
    def test_model_passed(self):
        runtime = MockAgentRuntime()
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.model = "gpt-4"
        node.execute = MockExecuteNode("Task")

        executor.execute(node, runtime.execution_context)

        assert runtime._agent_service.last_kwargs["model"] == "gpt-4"

    def test_provider_passed(self):
        runtime = MockAgentRuntime()
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.provider = "openai"
        node.execute = MockExecuteNode("Task")

        executor.execute(node, runtime.execution_context)

        assert runtime._agent_service.last_kwargs["provider"] == "openai"

    def test_endpoint_passed(self):
        runtime = MockAgentRuntime()
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.endpoint = "http://localhost:11434"
        node.execute = MockExecuteNode("Task")

        executor.execute(node, runtime.execution_context)

        assert runtime._agent_service.last_kwargs["endpoint"] == "http://localhost:11434"

    def test_api_key_resolved_via_databinding(self):
        runtime = MockAgentRuntime({"apiKey": "sk-123"})
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.api_key = "{apiKey}"
        node.execute = MockExecuteNode("Task")

        executor.execute(node, runtime.execution_context)

        assert runtime._agent_service.last_kwargs["api_key"] == "sk-123"


class TestLimits:
    def test_max_iterations_passed(self):
        runtime = MockAgentRuntime()
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.max_iterations = 5
        node.execute = MockExecuteNode("Task")

        executor.execute(node, runtime.execution_context)

        assert runtime._agent_service.last_kwargs["max_iterations"] == 5

    def test_timeout_passed_as_timeout_ms(self):
        runtime = MockAgentRuntime()
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.timeout = 30000
        node.execute = MockExecuteNode("Task")

        executor.execute(node, runtime.execution_context)

        assert runtime._agent_service.last_kwargs["timeout_ms"] == 30000


class TestResultStorage:
    def test_stores_result(self):
        runtime = MockAgentRuntime()
        runtime._agent_service.set_result("My task", AgentResult(
            success=True, result="Task completed successfully", iterations=3
        ))
        executor = AgentExecutor(runtime)

        node = AgentNode("myAgent")
        node.execute = MockExecuteNode("My task")

        executor.execute(node, runtime.execution_context)

        assert runtime.execution_context.get_variable("myAgent") == "Task completed successfully"

    def test_stores_full_result(self):
        runtime = MockAgentRuntime()
        result = AgentResult(success=True, result="Done", iterations=2, action_count=1)
        result.actions = [ToolCall(tool="search", args={"q": "query"}, result="ok")]
        runtime._agent_service.set_result("Task", result)
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.execute = MockExecuteNode("Task")

        executor.execute(node, runtime.execution_context)

        full_result = runtime.execution_context.get_variable("agent_result")
        assert full_result["success"] is True
        assert full_result["iterations"] == 2
        assert len(full_result["actions"]) == 1
        assert full_result["actions"][0]["tool"] == "search"


class TestErrorHandling:
    def test_error_stores_failure_result(self):
        runtime = MockAgentRuntime()
        runtime._agent_service.execute = MagicMock(side_effect=Exception("Agent failed"))
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.execute = MockExecuteNode("Task")

        with pytest.raises(ExecutorError, match="Agent execution error"):
            executor.execute(node, runtime.execution_context)

        error_result = runtime.execution_context.get_variable("agent_result")
        assert error_result["success"] is False
        assert "Agent failed" in error_result["error"]["message"]

    def test_error_result_format(self):
        runtime = MockAgentRuntime()
        runtime._agent_service.execute = MagicMock(side_effect=Exception("Error"))
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.execute = MockExecuteNode("Task")

        with pytest.raises(ExecutorError):
            executor.execute(node, runtime.execution_context)

        error_result = runtime.execution_context.get_variable("agent_result")
        for key in ("success", "error", "result", "iterations", "actions"):
            assert key in error_result
