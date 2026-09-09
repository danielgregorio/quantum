"""
Tests for TeamExecutor - q:team multi-agent execution

Rewritten 2026-09-07: the previous version mocked
services.agent.execute_team(team_config=...), but execute_team() lives on
MultiAgentService (services.multi_agent), takes a registered team name, and
requires create_team() first — see FULL_AUDIT_2026-09.md. These tests mock
the real two-call flow and use the real TeamResult dataclass.
"""

import pytest
from unittest.mock import MagicMock
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from quantum.runtime.executors.ai.team_executor import TeamExecutor
from quantum.runtime.executors.base import ExecutorError
from quantum.runtime.agent_service import TeamResult, AgentHandoff

try:
    from quantum.core.features.agents.src.ast_node import (
        AgentNode, AgentTeamNode, AgentToolNode,
    )
except ImportError:
    from quantum.core.features.agents.src import AgentNode, AgentTeamNode, AgentToolNode

from tests.unit.executors.conftest import MockRuntime


class MockMultiAgentService:
    """Mock matching the real MultiAgentService create_team/execute_team."""

    def __init__(self):
        self.created: Optional[Dict[str, Any]] = None
        self.executed: Optional[Dict[str, Any]] = None
        self._result: Optional[TeamResult] = None

    def set_result(self, result: TeamResult):
        self._result = result

    def create_team(self, name, agents, shared=None, supervisor="",
                    max_handoffs=10, max_total_iterations=50):
        self.created = dict(
            name=name, agents=agents, shared=shared, supervisor=supervisor,
            max_handoffs=max_handoffs, max_total_iterations=max_total_iterations,
        )
        return MagicMock()

    def execute_team(self, name, task, entry_agent=None, context="", tool_executor=None):
        self.executed = dict(
            name=name, task=task, entry_agent=entry_agent, context=context,
            tool_executor=tool_executor,
        )
        if self._result is not None:
            return self._result
        return TeamResult(success=True, final_response=f"Handled: {task}",
                          final_agent=entry_agent or "")


class MockTeamRuntime(MockRuntime):
    def __init__(self, variables: Dict[str, Any] = None):
        super().__init__(variables)
        self._multi_agent = MockMultiAgentService()
        self._services = MagicMock()
        self._services.multi_agent = self._multi_agent

    @property
    def services(self):
        return self._services


@dataclass
class MockExecuteNode:
    task: str
    entry: str = ""
    context: Optional[str] = None


@dataclass
class MockInstructionNode:
    content: str


@dataclass
class MockSetNode:
    name: str
    value: str


def _agent(name: str, **kwargs) -> AgentNode:
    agent = AgentNode(name)
    for key, value in kwargs.items():
        setattr(agent, key, value)
    return agent


class TestTeamExecutorBasic:
    def test_handles_team_node(self):
        executor = TeamExecutor(MockTeamRuntime())
        assert AgentTeamNode in executor.handles

    def test_handles_returns_list(self):
        executor = TeamExecutor(MockTeamRuntime())
        assert isinstance(executor.handles, list)
        assert len(executor.handles) == 1


class TestExecuteNode:
    def test_requires_execute_node(self):
        runtime = MockTeamRuntime()
        executor = TeamExecutor(runtime)

        node = AgentTeamNode(name="team")
        node.execute = None

        with pytest.raises(ExecutorError, match="requires <q:execute>"):
            executor.execute(node, runtime.execution_context)

    def test_task_from_execute(self):
        runtime = MockTeamRuntime()
        executor = TeamExecutor(runtime)

        node = AgentTeamNode(name="support")
        node.agents = [_agent("router")]
        node.execute = MockExecuteNode("Help with my bill")

        executor.execute(node, runtime.execution_context)

        assert runtime._multi_agent.executed["task"] == "Help with my bill"

    def test_task_with_databinding(self):
        runtime = MockTeamRuntime({"question": "Where is my order?"})
        executor = TeamExecutor(runtime)

        node = AgentTeamNode(name="support")
        node.agents = [_agent("router")]
        node.execute = MockExecuteNode("{question}")

        executor.execute(node, runtime.execution_context)

        assert runtime._multi_agent.executed["task"] == "Where is my order?"


class TestEntryAgent:
    def test_entry_from_execute(self):
        runtime = MockTeamRuntime()
        executor = TeamExecutor(runtime)

        node = AgentTeamNode(name="support", supervisor="router")
        node.agents = [_agent("router"), _agent("billing")]
        node.execute = MockExecuteNode("Task", entry="billing")

        executor.execute(node, runtime.execution_context)

        assert runtime._multi_agent.executed["entry_agent"] == "billing"

    def test_entry_from_supervisor(self):
        runtime = MockTeamRuntime()
        executor = TeamExecutor(runtime)

        node = AgentTeamNode(name="support", supervisor="router")
        node.agents = [_agent("router"), _agent("billing")]
        node.execute = MockExecuteNode("Task")

        executor.execute(node, runtime.execution_context)

        assert runtime._multi_agent.executed["entry_agent"] == "router"

    def test_entry_defaults_to_first_agent(self):
        runtime = MockTeamRuntime()
        executor = TeamExecutor(runtime)

        node = AgentTeamNode(name="support")
        node.agents = [_agent("first"), _agent("second")]
        node.execute = MockExecuteNode("Task")

        executor.execute(node, runtime.execution_context)

        assert runtime._multi_agent.executed["entry_agent"] == "first"


class TestSharedContext:
    def test_shared_context_built(self):
        runtime = MockTeamRuntime()
        executor = TeamExecutor(runtime)

        node = AgentTeamNode(name="support")
        node.agents = [_agent("router")]
        node.shared = [MockSetNode("customerName", "John Doe")]
        node.execute = MockExecuteNode("Task")

        executor.execute(node, runtime.execution_context)

        assert runtime._multi_agent.created["shared"]["customerName"] == "John Doe"

    def test_shared_with_databinding(self):
        runtime = MockTeamRuntime({"userId": "customer_12345"})
        executor = TeamExecutor(runtime)

        node = AgentTeamNode(name="support")
        node.agents = [_agent("router")]
        node.shared = [MockSetNode("customerId", "{userId}")]
        node.execute = MockExecuteNode("Task")

        executor.execute(node, runtime.execution_context)

        assert runtime._multi_agent.created["shared"]["customerId"] == "customer_12345"


class TestAgentConfiguration:
    def test_agents_passed_as_name_keyed_dict(self):
        """create_team() takes {name: config}, not a list."""
        runtime = MockTeamRuntime()
        executor = TeamExecutor(runtime)

        node = AgentTeamNode(name="support")
        node.agents = [_agent("router"), _agent("billing")]
        node.execute = MockExecuteNode("Task")

        executor.execute(node, runtime.execution_context)

        agents = runtime._multi_agent.created["agents"]
        assert isinstance(agents, dict)
        assert set(agents.keys()) == {"router", "billing"}

    def test_agent_config_keys_match_agentteam_reads(self):
        runtime = MockTeamRuntime()
        executor = TeamExecutor(runtime)

        agent = _agent("router", model="gpt-4", provider="openai",
                       max_iterations=7, timeout=45000)
        agent.instruction = MockInstructionNode("Route requests")

        node = AgentTeamNode(name="support")
        node.agents = [agent]
        node.execute = MockExecuteNode("Task")

        executor.execute(node, runtime.execution_context)

        config = runtime._multi_agent.created["agents"]["router"]
        assert config["model"] == "gpt-4"
        assert config["provider"] == "openai"
        assert config["instruction"] == "Route requests"
        assert config["max_iterations"] == 7
        # AgentTeam.execute() reads "timeout", not "timeout_ms", for team members
        assert config["timeout"] == 45000

    def test_agent_tools_carry_body_and_params(self):
        runtime = MockTeamRuntime()
        executor = TeamExecutor(runtime)

        tool = AgentToolNode(name="lookupInvoice", description="Look up invoice")
        tool.body = ["<statement>"]

        agent = _agent("billing")
        agent.tools = [tool, AgentToolNode(name="handoff", builtin=True)]

        node = AgentTeamNode(name="support")
        node.agents = [agent]
        node.execute = MockExecuteNode("Task")

        executor.execute(node, runtime.execution_context)

        tools = runtime._multi_agent.created["agents"]["billing"]["tools"]

        # The agent declares two (lookupInvoice + an explicit handoff) and the
        # team supplies the three remaining built-ins automatically, because a
        # q:team whose agents cannot hand off is not a team. This used to
        # assert len == 2, back when the built-ins had to be declared one by
        # one and the shipped example forgot to.
        names = {t["name"] for t in tools}
        assert names == {"lookupInvoice", "handoff", "readShared",
                         "writeShared", "listAgents"}
        assert len(tools) == len(names), "a tool was added twice"

        custom = [t for t in tools if t["name"] == "lookupInvoice"][0]
        assert custom["body"] == ["<statement>"]
        builtin = [t for t in tools if t["name"] == "handoff"][0]
        assert "description" in builtin


class TestLimits:
    def test_max_handoffs_passed(self):
        runtime = MockTeamRuntime()
        executor = TeamExecutor(runtime)

        node = AgentTeamNode(name="support", max_handoffs=3)
        node.agents = [_agent("router")]
        node.execute = MockExecuteNode("Task")

        executor.execute(node, runtime.execution_context)

        assert runtime._multi_agent.created["max_handoffs"] == 3

    def test_max_total_iterations_passed(self):
        runtime = MockTeamRuntime()
        executor = TeamExecutor(runtime)

        node = AgentTeamNode(name="support", max_total_iterations=25)
        node.agents = [_agent("router")]
        node.execute = MockExecuteNode("Task")

        executor.execute(node, runtime.execution_context)

        assert runtime._multi_agent.created["max_total_iterations"] == 25


class TestToolExecutor:
    def test_tool_executor_passed_to_execute_team(self):
        runtime = MockTeamRuntime()
        executor = TeamExecutor(runtime)

        node = AgentTeamNode(name="support")
        node.agents = [_agent("router")]
        node.execute = MockExecuteNode("Task")

        executor.execute(node, runtime.execution_context)

        assert callable(runtime._multi_agent.executed["tool_executor"])


class TestResultStorage:
    def test_stores_final_response(self):
        runtime = MockTeamRuntime()
        runtime._multi_agent.set_result(TeamResult(
            success=True, final_response="Your invoice is paid", final_agent="billing"
        ))
        executor = TeamExecutor(runtime)

        node = AgentTeamNode(name="support")
        node.agents = [_agent("router")]
        node.execute = MockExecuteNode("Task")

        executor.execute(node, runtime.execution_context)

        assert runtime.execution_context.get_variable("support") == "Your invoice is paid"

    def test_stores_full_result(self):
        runtime = MockTeamRuntime()
        result = TeamResult(success=True, final_response="Done", final_agent="billing",
                            total_iterations=4)
        result.handoffs = [AgentHandoff(from_agent="router", to_agent="billing")]
        runtime._multi_agent.set_result(result)
        executor = TeamExecutor(runtime)

        node = AgentTeamNode(name="support")
        node.agents = [_agent("router")]
        node.execute = MockExecuteNode("Task")

        executor.execute(node, runtime.execution_context)

        full = runtime.execution_context.get_variable("support_result")
        assert full["success"] is True
        assert full["finalAgent"] == "billing"
        assert full["totalIterations"] == 4
        assert full["handoffs"][0]["fromAgent"] == "router"


class TestErrorHandling:
    def test_error_stores_failure_result(self):
        runtime = MockTeamRuntime()
        runtime._multi_agent.execute_team = MagicMock(side_effect=Exception("Team failed"))
        executor = TeamExecutor(runtime)

        node = AgentTeamNode(name="support")
        node.agents = [_agent("router")]
        node.execute = MockExecuteNode("Task")

        with pytest.raises(ExecutorError, match="Team execution error"):
            executor.execute(node, runtime.execution_context)

        error_result = runtime.execution_context.get_variable("support_result")
        assert error_result["success"] is False
        assert "Team failed" in error_result["error"]["message"]

    def test_error_result_format(self):
        runtime = MockTeamRuntime()
        runtime._multi_agent.create_team = MagicMock(side_effect=Exception("boom"))
        executor = TeamExecutor(runtime)

        node = AgentTeamNode(name="support")
        node.agents = [_agent("router")]
        node.execute = MockExecuteNode("Task")

        with pytest.raises(ExecutorError):
            executor.execute(node, runtime.execution_context)

        error_result = runtime.execution_context.get_variable("support_result")
        for key in ("success", "error", "finalResponse", "handoffs", "totalIterations"):
            assert key in error_result
