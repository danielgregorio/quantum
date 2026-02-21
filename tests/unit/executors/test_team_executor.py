"""
Tests for TeamExecutor - q:team multi-agent team execution

Coverage target: 20% -> 60%
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from runtime.executors.ai.team_executor import TeamExecutor
from runtime.executors.base import ExecutorError

# Import AgentTeamNode from the correct location
try:
    from core.features.agents.src.ast_node import AgentTeamNode
except ImportError:
    from core.features.agents.src import AgentTeamNode

# Import fixtures from conftest.py
from tests.unit.executors.conftest import MockRuntime, MockExecutionContext


# =============================================================================
# Mock Objects for Agent Service
# =============================================================================

class MockTeamService:
    """Mock agent service with team support"""

    def __init__(self):
        self.last_team_config = None
        self.last_task = None
        self._results = {}

    def set_result(self, task: str, result: Dict):
        """Set mock result for task"""
        self._results[task] = result

    def execute_team(self, team_config: Dict, task: str, exec_context, runtime) -> Dict:
        """Mock team execute"""
        self.last_team_config = team_config
        self.last_task = task

        if task in self._results:
            return self._results[task]

        return {
            'success': True,
            'finalResponse': f'Team completed: {task}',
            'handoffs': [],
            'totalIterations': 1
        }


class MockTeamRuntime(MockRuntime):
    """Extended mock runtime with team service"""

    def __init__(self, variables: Dict[str, Any] = None):
        super().__init__(variables)
        self._team_service = MockTeamService()
        self._services = MagicMock()
        self._services.agent = self._team_service

    @property
    def services(self):
        return self._services


# =============================================================================
# Mock AST Nodes
# =============================================================================

@dataclass
class MockTeamExecuteNode:
    """Mock team execute node"""
    task: str
    entry: Optional[str] = None


@dataclass
class MockInstructionNode:
    """Mock instruction node"""
    content: str


@dataclass
class MockToolNode:
    """Mock tool node"""
    name: str
    builtin: bool = False

    def get_schema(self) -> Dict:
        return {'name': self.name}


@dataclass
class MockSetNode:
    """Mock set node for shared context"""
    name: str
    value: str


@dataclass
class MockAgentNode:
    """Mock agent node for team member"""
    name: str
    model: str = "phi3"
    provider: str = "ollama"
    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    instruction: Optional[MockInstructionNode] = None
    tools: List[MockToolNode] = field(default_factory=list)
    max_iterations: int = 10
    timeout: int = 60000


# =============================================================================
# Test Classes
# =============================================================================

class TestTeamExecutorBasic:
    """Basic functionality tests"""

    def test_handles_team_node(self):
        """Test that TeamExecutor handles AgentTeamNode"""
        runtime = MockTeamRuntime()
        executor = TeamExecutor(runtime)
        assert AgentTeamNode in executor.handles

    def test_handles_returns_list(self):
        """Test that handles returns a list"""
        runtime = MockTeamRuntime()
        executor = TeamExecutor(runtime)
        assert isinstance(executor.handles, list)
        assert len(executor.handles) == 1


class TestExecuteNode:
    """Test execute node handling"""

    def test_requires_execute_node(self):
        """Test that team requires execute node"""
        runtime = MockTeamRuntime()
        executor = TeamExecutor(runtime)

        node = AgentTeamNode()
        node.name = "team"
        node.execute = None

        with pytest.raises(ExecutorError, match="requires <q:execute>"):
            executor.execute(node, runtime.execution_context)

    def test_task_from_execute(self):
        """Test task is extracted from execute node"""
        runtime = MockTeamRuntime()
        executor = TeamExecutor(runtime)

        node = AgentTeamNode()
        node.name = "team"
        node.execute = MockTeamExecuteNode("Research and write report")
        node.agents = []
        node.shared = []

        executor.execute(node, runtime.execution_context)

        assert runtime._team_service.last_task == "Research and write report"

    def test_task_with_databinding(self):
        """Test task with databinding"""
        runtime = MockTeamRuntime({"topic": "AI trends"})
        executor = TeamExecutor(runtime)

        node = AgentTeamNode()
        node.name = "team"
        node.execute = MockTeamExecuteNode("Research {topic}")
        node.agents = []
        node.shared = []

        executor.execute(node, runtime.execution_context)

        assert runtime._team_service.last_task == "Research AI trends"


class TestEntryAgent:
    """Test entry agent determination"""

    def test_entry_from_execute(self):
        """Test entry agent from execute node"""
        runtime = MockTeamRuntime()
        executor = TeamExecutor(runtime)

        node = AgentTeamNode()
        node.name = "team"
        node.execute = MockTeamExecuteNode("Task", entry="coordinator")
        node.agents = []
        node.shared = []

        executor.execute(node, runtime.execution_context)

        assert runtime._team_service.last_team_config["entry_agent"] == "coordinator"

    def test_entry_from_supervisor(self):
        """Test entry agent from supervisor attribute"""
        runtime = MockTeamRuntime()
        executor = TeamExecutor(runtime)

        node = AgentTeamNode()
        node.name = "team"
        node.supervisor = "manager"
        node.execute = MockTeamExecuteNode("Task")
        node.agents = []
        node.shared = []

        executor.execute(node, runtime.execution_context)

        assert runtime._team_service.last_team_config["entry_agent"] == "manager"

    def test_entry_defaults_to_first_agent(self):
        """Test entry defaults to first agent"""
        runtime = MockTeamRuntime()
        executor = TeamExecutor(runtime)

        node = AgentTeamNode()
        node.name = "team"
        node.execute = MockTeamExecuteNode("Task")
        node.agents = [MockAgentNode("researcher"), MockAgentNode("writer")]
        node.shared = []

        executor.execute(node, runtime.execution_context)

        assert runtime._team_service.last_team_config["entry_agent"] == "researcher"


class TestSharedContext:
    """Test shared context initialization"""

    def test_shared_context_built(self):
        """Test shared context is built from set nodes"""
        runtime = MockTeamRuntime()
        executor = TeamExecutor(runtime)

        node = AgentTeamNode()
        node.name = "team"
        node.execute = MockTeamExecuteNode("Task")
        node.agents = []
        node.shared = [
            MockSetNode("topic", "AI"),
            MockSetNode("deadline", "2024-01-01")
        ]

        executor.execute(node, runtime.execution_context)

        shared = runtime._team_service.last_team_config["shared"]
        assert shared["topic"] == "AI"
        assert shared["deadline"] == "2024-01-01"

    def test_shared_with_databinding(self):
        """Test shared context with databinding"""
        runtime = MockTeamRuntime({"projectName": "Quantum"})
        executor = TeamExecutor(runtime)

        node = AgentTeamNode()
        node.name = "team"
        node.execute = MockTeamExecuteNode("Task")
        node.agents = []
        node.shared = [MockSetNode("project", "{projectName}")]

        executor.execute(node, runtime.execution_context)

        shared = runtime._team_service.last_team_config["shared"]
        assert shared["project"] == "Quantum"


class TestAgentConfiguration:
    """Test agent configuration building"""

    def test_builds_agent_config(self):
        """Test agent configuration is built correctly"""
        runtime = MockTeamRuntime()
        executor = TeamExecutor(runtime)

        node = AgentTeamNode()
        node.name = "team"
        node.execute = MockTeamExecuteNode("Task")
        node.agents = [MockAgentNode(
            name="researcher",
            model="gpt-4",
            provider="openai",
            max_iterations=5,
            timeout=30000
        )]
        node.shared = []

        executor.execute(node, runtime.execution_context)

        agents = runtime._team_service.last_team_config["agents"]
        assert len(agents) == 1
        assert agents[0]["name"] == "researcher"
        assert agents[0]["model"] == "gpt-4"
        assert agents[0]["provider"] == "openai"
        assert agents[0]["max_iterations"] == 5

    def test_builds_multiple_agents(self):
        """Test multiple agents are configured"""
        runtime = MockTeamRuntime()
        executor = TeamExecutor(runtime)

        node = AgentTeamNode()
        node.name = "team"
        node.execute = MockTeamExecuteNode("Task")
        node.agents = [
            MockAgentNode("researcher"),
            MockAgentNode("writer"),
            MockAgentNode("reviewer")
        ]
        node.shared = []

        executor.execute(node, runtime.execution_context)

        agents = runtime._team_service.last_team_config["agents"]
        assert len(agents) == 3
        assert [a["name"] for a in agents] == ["researcher", "writer", "reviewer"]

    def test_agent_with_tools(self):
        """Test agent with tools configured"""
        runtime = MockTeamRuntime()
        executor = TeamExecutor(runtime)

        agent = MockAgentNode("researcher")
        agent.tools = [
            MockToolNode("web_search", builtin=True),
            MockToolNode("read_file", builtin=False)
        ]

        node = AgentTeamNode()
        node.name = "team"
        node.execute = MockTeamExecuteNode("Task")
        node.agents = [agent]
        node.shared = []

        executor.execute(node, runtime.execution_context)

        agent_config = runtime._team_service.last_team_config["agents"][0]
        assert len(agent_config["tools"]) == 2

    def test_agent_with_instruction(self):
        """Test agent with instruction"""
        runtime = MockTeamRuntime()
        executor = TeamExecutor(runtime)

        agent = MockAgentNode("expert")
        agent.instruction = MockInstructionNode("You are an expert researcher")

        node = AgentTeamNode()
        node.name = "team"
        node.execute = MockTeamExecuteNode("Task")
        node.agents = [agent]
        node.shared = []

        executor.execute(node, runtime.execution_context)

        agent_config = runtime._team_service.last_team_config["agents"][0]
        assert agent_config["instruction"] == "You are an expert researcher"


class TestLimits:
    """Test team limits"""

    def test_max_handoffs_passed(self):
        """Test max handoffs is passed"""
        runtime = MockTeamRuntime()
        executor = TeamExecutor(runtime)

        node = AgentTeamNode()
        node.name = "team"
        node.max_handoffs = 5
        node.execute = MockTeamExecuteNode("Task")
        node.agents = []
        node.shared = []

        executor.execute(node, runtime.execution_context)

        assert runtime._team_service.last_team_config["max_handoffs"] == 5

    def test_max_total_iterations_passed(self):
        """Test max total iterations is passed"""
        runtime = MockTeamRuntime()
        executor = TeamExecutor(runtime)

        node = AgentTeamNode()
        node.name = "team"
        node.max_total_iterations = 100
        node.execute = MockTeamExecuteNode("Task")
        node.agents = []
        node.shared = []

        executor.execute(node, runtime.execution_context)

        assert runtime._team_service.last_team_config["max_total_iterations"] == 100


class TestResultStorage:
    """Test result storage"""

    def test_stores_final_response(self):
        """Test that final response is stored"""
        runtime = MockTeamRuntime()
        runtime._team_service.set_result("Task", {
            'success': True,
            'finalResponse': 'Task completed by team',
            'handoffs': [],
            'totalIterations': 5
        })
        executor = TeamExecutor(runtime)

        node = AgentTeamNode()
        node.name = "myTeam"
        node.execute = MockTeamExecuteNode("Task")
        node.agents = []
        node.shared = []

        executor.execute(node, runtime.execution_context)

        stored = runtime.execution_context.get_variable("myTeam")
        assert stored == "Task completed by team"

    def test_stores_full_result(self):
        """Test that full result is stored"""
        runtime = MockTeamRuntime()
        runtime._team_service.set_result("Task", {
            'success': True,
            'finalResponse': 'Done',
            'handoffs': [{'from': 'a', 'to': 'b'}],
            'totalIterations': 10
        })
        executor = TeamExecutor(runtime)

        node = AgentTeamNode()
        node.name = "team"
        node.execute = MockTeamExecuteNode("Task")
        node.agents = []
        node.shared = []

        executor.execute(node, runtime.execution_context)

        full_result = runtime.execution_context.get_variable("team_result")
        assert full_result["success"] is True
        assert len(full_result["handoffs"]) == 1
        assert full_result["totalIterations"] == 10


class TestErrorHandling:
    """Test error handling"""

    def test_error_stores_failure_result(self):
        """Test that error stores failure result"""
        runtime = MockTeamRuntime()
        runtime._team_service.execute_team = MagicMock(side_effect=Exception("Team failed"))
        executor = TeamExecutor(runtime)

        node = AgentTeamNode()
        node.name = "team"
        node.execute = MockTeamExecuteNode("Task")
        node.agents = []
        node.shared = []

        with pytest.raises(ExecutorError, match="Team execution error"):
            executor.execute(node, runtime.execution_context)

        error_result = runtime.execution_context.get_variable("team_result")
        assert error_result["success"] is False
        assert "Team failed" in error_result["error"]["message"]

    def test_error_result_format(self):
        """Test error result has correct format"""
        runtime = MockTeamRuntime()
        runtime._team_service.execute_team = MagicMock(side_effect=Exception("Error"))
        executor = TeamExecutor(runtime)

        node = AgentTeamNode()
        node.name = "team"
        node.execute = MockTeamExecuteNode("Task")
        node.agents = []
        node.shared = []

        with pytest.raises(ExecutorError):
            executor.execute(node, runtime.execution_context)

        error_result = runtime.execution_context.get_variable("team_result")
        assert "finalResponse" in error_result
        assert "handoffs" in error_result
        assert "totalIterations" in error_result
