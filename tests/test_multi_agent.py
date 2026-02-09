"""
Tests for Multi-Agent Systems - q:team with Agent Handoffs

Tests the complete multi-agent pipeline:
- AgentTeamNode and AgentHandoffNode AST nodes
- AgentTeam and MultiAgentService
- Team parsing from XML
- Handoff mechanism
- Shared context operations
- Safety limits (max_handoffs, cycle detection)
"""

import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Add src to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.features.agents.src.ast_node import (
    AgentNode, AgentToolNode, AgentToolParamNode,
    AgentInstructionNode, AgentExecuteNode,
    AgentTeamNode, AgentHandoffNode
)
from runtime.agent_service import (
    AgentService, AgentResult, ToolCall, AgentError,
    AgentTeam, AgentHandoff, TeamResult, AgentRegistry,
    MultiAgentService, BUILTIN_TOOLS,
    get_agent_service, reset_agent_service,
    get_multi_agent_service, reset_multi_agent_service
)


class TestAgentTeamASTNodes:
    """Test AST node classes for multi-agent systems."""

    def test_agent_handoff_node_creation(self):
        """Test AgentHandoffNode creation."""
        handoff = AgentHandoffNode(
            target_agent="billing",
            context="Customer needs invoice help"
        )
        assert handoff.target_agent == "billing"
        assert handoff.context == "Customer needs invoice help"

    def test_agent_handoff_node_validation(self):
        """Test AgentHandoffNode validation."""
        # Missing target_agent
        handoff = AgentHandoffNode(target_agent="")
        errors = handoff.validate()
        assert any("target_agent" in e.lower() for e in errors)

        # Valid handoff
        handoff = AgentHandoffNode(target_agent="billing")
        errors = handoff.validate()
        assert len(errors) == 0

    def test_agent_team_node_creation(self):
        """Test AgentTeamNode creation."""
        agent1 = AgentNode(name="router", model="gpt-4")
        agent2 = AgentNode(name="billing", model="gpt-4")

        team = AgentTeamNode(
            name="support",
            supervisor="router",
            agents=[agent1, agent2],
            max_handoffs=5
        )

        assert team.name == "support"
        assert team.supervisor == "router"
        assert len(team.agents) == 2
        assert team.max_handoffs == 5
        assert team.max_total_iterations == 50  # default

    def test_agent_team_node_with_shared(self):
        """Test AgentTeamNode with shared state."""
        from core.features.state_management.src.ast_node import SetNode

        # SetNode uses a different constructor pattern
        set1 = SetNode(name="customerId")
        set1.value = "123"

        set2 = SetNode(name="customerName")
        set2.value = "John"

        shared = [set1, set2]

        team = AgentTeamNode(
            name="support",
            shared=shared,
            agents=[AgentNode(name="agent1", model="gpt-4")]
        )

        assert len(team.shared) == 2

    def test_agent_team_node_validation(self):
        """Test AgentTeamNode validation."""
        # Missing name
        team = AgentTeamNode(name="")
        errors = team.validate()
        assert any("name" in e.lower() for e in errors)

        # No agents
        team = AgentTeamNode(name="empty", agents=[])
        errors = team.validate()
        assert any("agent" in e.lower() for e in errors)

        # Supervisor not in agents
        team = AgentTeamNode(
            name="test",
            supervisor="missing",
            agents=[AgentNode(name="agent1", model="gpt-4")],
            execute=AgentExecuteNode(task="test")
        )
        errors = team.validate()
        assert any("supervisor" in e.lower() and "missing" in e.lower() for e in errors)

        # max_handoffs too low
        team = AgentTeamNode(
            name="test",
            agents=[AgentNode(name="agent1", model="gpt-4")],
            max_handoffs=0
        )
        errors = team.validate()
        assert any("max_handoffs" in e.lower() for e in errors)

    def test_agent_team_get_agent(self):
        """Test getting agent by name."""
        agent1 = AgentNode(name="router", model="gpt-4")
        agent2 = AgentNode(name="billing", model="gpt-4")

        team = AgentTeamNode(
            name="support",
            agents=[agent1, agent2]
        )

        found = team.get_agent("billing")
        assert found is not None
        assert found.name == "billing"

        not_found = team.get_agent("unknown")
        assert not_found is None

    def test_agent_team_get_agent_names(self):
        """Test getting all agent names."""
        team = AgentTeamNode(
            name="support",
            agents=[
                AgentNode(name="router", model="gpt-4"),
                AgentNode(name="billing", model="gpt-4"),
                AgentNode(name="technical", model="gpt-4")
            ]
        )

        names = team.get_agent_names()
        assert len(names) == 3
        assert "router" in names
        assert "billing" in names
        assert "technical" in names

    def test_agent_tool_builtin_flag(self):
        """Test AgentToolNode with builtin flag."""
        # Built-in tool
        builtin_tool = AgentToolNode(name="handoff", builtin=True)
        assert builtin_tool.builtin is True
        assert builtin_tool.is_builtin() is True

        # Validation should not require description for builtin
        errors = builtin_tool.validate()
        assert not any("description" in e.lower() for e in errors)

        # Custom tool requires description
        custom_tool = AgentToolNode(name="custom", builtin=False)
        errors = custom_tool.validate()
        assert any("description" in e.lower() for e in errors)

    def test_agent_execute_node_with_entry(self):
        """Test AgentExecuteNode with entry attribute."""
        execute = AgentExecuteNode(
            task="Help the user",
            context="Premium customer",
            entry="router"
        )

        assert execute.task == "Help the user"
        assert execute.context == "Premium customer"
        assert execute.entry == "router"

        # to_dict should include entry
        d = execute.to_dict()
        assert d["entry"] == "router"


class TestAgentHandoff:
    """Test AgentHandoff dataclass."""

    def test_handoff_creation(self):
        """Test AgentHandoff creation."""
        handoff = AgentHandoff(
            from_agent="router",
            to_agent="billing",
            message="Customer needs help with invoice"
        )

        assert handoff.from_agent == "router"
        assert handoff.to_agent == "billing"
        assert handoff.message == "Customer needs help with invoice"
        assert isinstance(handoff.timestamp, datetime)

    def test_handoff_to_dict(self):
        """Test AgentHandoff serialization."""
        handoff = AgentHandoff(
            from_agent="router",
            to_agent="billing",
            message="Help needed"
        )

        d = handoff.to_dict()
        assert d["fromAgent"] == "router"
        assert d["toAgent"] == "billing"
        assert d["message"] == "Help needed"
        assert "timestamp" in d


class TestTeamResult:
    """Test TeamResult dataclass."""

    def test_team_result_creation(self):
        """Test TeamResult creation."""
        result = TeamResult(
            success=True,
            final_response="Issue resolved",
            final_agent="billing",
            total_iterations=5,
            execution_time_ms=1500.0
        )

        assert result.success is True
        assert result.final_response == "Issue resolved"
        assert result.final_agent == "billing"

    def test_team_result_with_handoffs(self):
        """Test TeamResult with handoff log."""
        result = TeamResult(
            success=True,
            final_response="Done",
            handoffs=[
                AgentHandoff(from_agent="router", to_agent="billing"),
                AgentHandoff(from_agent="billing", to_agent="technical")
            ]
        )

        assert len(result.handoffs) == 2

    def test_team_result_to_dict(self):
        """Test TeamResult serialization."""
        result = TeamResult(
            success=True,
            final_response="Task completed",
            final_agent="billing",
            handoffs=[
                AgentHandoff(from_agent="router", to_agent="billing", message="Invoice help")
            ],
            total_iterations=3,
            execution_time_ms=2000.0,
            shared_context={"customerId": "123"}
        )

        d = result.to_dict()
        assert d["success"] is True
        assert d["finalResponse"] == "Task completed"
        assert d["finalAgent"] == "billing"
        assert len(d["handoffs"]) == 1
        assert d["totalIterations"] == 3
        assert d["executionTime"] == 2000.0
        assert d["sharedContext"]["customerId"] == "123"


class TestAgentRegistry:
    """Test AgentRegistry class."""

    def test_registry_register_and_get(self):
        """Test agent registration and retrieval."""
        registry = AgentRegistry()

        config = {"model": "gpt-4", "instruction": "Be helpful"}
        registry.register("helper", config)

        retrieved = registry.get("helper")
        assert retrieved == config

    def test_registry_list_agents(self):
        """Test listing registered agents."""
        registry = AgentRegistry()

        registry.register("agent1", {})
        registry.register("agent2", {})
        registry.register("agent3", {})

        agents = registry.list_agents()
        assert len(agents) == 3
        assert "agent1" in agents
        assert "agent2" in agents
        assert "agent3" in agents

    def test_registry_unregister(self):
        """Test agent unregistration."""
        registry = AgentRegistry()

        registry.register("temp", {"model": "test"})
        assert registry.get("temp") is not None

        registry.unregister("temp")
        assert registry.get("temp") is None

    def test_registry_team_operations(self):
        """Test team registration in registry."""
        registry = AgentRegistry()

        team = Mock(spec=AgentTeam)
        team.name = "support"

        registry.register_team("support", team)
        retrieved = registry.get_team("support")

        assert retrieved == team

    def test_registry_clear(self):
        """Test clearing all registrations."""
        registry = AgentRegistry()

        registry.register("agent1", {})
        registry.register("agent2", {})

        registry.clear()

        assert len(registry.list_agents()) == 0


class TestBuiltinTools:
    """Test built-in tool definitions."""

    def test_handoff_tool_defined(self):
        """Test handoff tool definition exists."""
        assert "handoff" in BUILTIN_TOOLS

        handoff = BUILTIN_TOOLS["handoff"]
        assert handoff["name"] == "handoff"
        assert "agent" in [p["name"] for p in handoff["params"]]

    def test_read_shared_tool_defined(self):
        """Test readShared tool definition exists."""
        assert "readShared" in BUILTIN_TOOLS

        read_shared = BUILTIN_TOOLS["readShared"]
        assert read_shared["name"] == "readShared"
        assert "key" in [p["name"] for p in read_shared["params"]]

    def test_write_shared_tool_defined(self):
        """Test writeShared tool definition exists."""
        assert "writeShared" in BUILTIN_TOOLS

        write_shared = BUILTIN_TOOLS["writeShared"]
        assert write_shared["name"] == "writeShared"
        param_names = [p["name"] for p in write_shared["params"]]
        assert "key" in param_names
        assert "value" in param_names

    def test_list_agents_tool_defined(self):
        """Test listAgents tool definition exists."""
        assert "listAgents" in BUILTIN_TOOLS

        list_agents = BUILTIN_TOOLS["listAgents"]
        assert list_agents["name"] == "listAgents"


class TestAgentTeam:
    """Test AgentTeam class."""

    @pytest.fixture
    def mock_agent_service(self):
        """Create mock agent service."""
        service = Mock(spec=AgentService)
        return service

    @pytest.fixture
    def basic_team(self, mock_agent_service):
        """Create a basic team for testing."""
        return AgentTeam(
            name="support",
            agents={
                "router": {"instruction": "Route requests", "model": "gpt-4"},
                "billing": {"instruction": "Handle billing", "model": "gpt-4"},
                "technical": {"instruction": "Handle technical", "model": "gpt-4"}
            },
            shared_context={"customerId": "123"},
            supervisor="router",
            max_handoffs=5,
            agent_service=mock_agent_service
        )

    def test_team_creation(self, basic_team):
        """Test team creation."""
        assert basic_team.name == "support"
        assert len(basic_team.agents) == 3
        assert basic_team.supervisor == "router"
        assert basic_team.max_handoffs == 5

    def test_shared_context_operations(self, basic_team):
        """Test shared context read/write."""
        # Read existing value
        value = basic_team.get_shared("customerId")
        assert value == "123"

        # Write new value
        basic_team.set_shared("customerName", "John Doe")
        assert basic_team.get_shared("customerName") == "John Doe"

        # Read non-existent key
        missing = basic_team.get_shared("missing")
        assert missing is None

    def test_list_agent_names(self, basic_team):
        """Test listing agent names."""
        names = basic_team.list_agent_names()
        assert len(names) == 3
        assert "router" in names
        assert "billing" in names
        assert "technical" in names

    def test_get_agent_info(self, basic_team):
        """Test getting agent info for listAgents tool."""
        info = basic_team.get_agent_info()
        assert len(info) == 3

        names = [i["name"] for i in info]
        assert "router" in names
        assert "billing" in names

    def test_handoff_success(self, basic_team):
        """Test successful handoff."""
        error = basic_team.handoff("router", "billing", "Help with invoice")

        assert error is None
        assert len(basic_team.handoff_log) == 1
        assert basic_team.handoff_log[0].from_agent == "router"
        assert basic_team.handoff_log[0].to_agent == "billing"

    def test_handoff_to_unknown_agent(self, basic_team):
        """Test handoff to unknown agent."""
        error = basic_team.handoff("router", "unknown", "Help")

        assert error is not None
        assert "unknown" in error.lower()
        assert len(basic_team.handoff_log) == 0

    def test_handoff_limit_reached(self, basic_team):
        """Test handoff limit enforcement."""
        # Fill up handoff log to max
        for i in range(basic_team.max_handoffs):
            basic_team.handoff_log.append(
                AgentHandoff(from_agent="a", to_agent="b")
            )

        # Next handoff should fail
        error = basic_team.handoff("router", "billing", "Help")

        assert error is not None
        assert "maximum" in error.lower()

    def test_handoff_cycle_detection(self, basic_team):
        """Test cycle detection blocks repeated handoffs."""
        # First handoff A -> B
        basic_team.handoff("router", "billing")
        # Second handoff A -> B
        basic_team.handoff("router", "billing")
        # Third handoff A -> B should be blocked
        error = basic_team.handoff("router", "billing")

        assert error is not None
        assert "cycle" in error.lower()


class TestMultiAgentService:
    """Test MultiAgentService class."""

    @pytest.fixture
    def service(self):
        """Create multi-agent service."""
        reset_multi_agent_service()
        return get_multi_agent_service()

    def test_service_creation(self, service):
        """Test service instantiation."""
        assert service is not None
        assert service.registry is not None

    def test_create_team(self, service):
        """Test team creation through service."""
        team = service.create_team(
            name="support",
            agents={
                "router": {"instruction": "Route", "model": "gpt-4"},
                "helper": {"instruction": "Help", "model": "gpt-4"}
            },
            shared={"key": "value"},
            supervisor="router"
        )

        assert team.name == "support"
        assert len(team.agents) == 2
        assert team.supervisor == "router"

    def test_get_team(self, service):
        """Test team retrieval."""
        service.create_team(
            name="test_team",
            agents={"agent1": {"model": "gpt-4"}}
        )

        team = service.get_team("test_team")
        assert team is not None
        assert team.name == "test_team"

        missing = service.get_team("missing")
        assert missing is None

    def test_execute_missing_team(self, service):
        """Test executing non-existent team."""
        result = service.execute_team("missing", "Do something")

        assert result.success is False
        assert result.error is not None
        assert "not found" in result.error["message"].lower()


class TestTeamParsing:
    """Test parser integration for q:team."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        from core.parser import QuantumParser
        return QuantumParser(use_cache=False)

    def test_parse_simple_team(self, parser):
        """Test parsing a simple team."""
        xml = '''<?xml version="1.0"?>
<q:component name="Test" xmlns:q="urn:quantum">
    <q:team name="support" supervisor="router">
        <q:agent name="router" model="gpt-4">
            <q:instruction>Route requests</q:instruction>
            <q:tool name="handoff" builtin="true" />
        </q:agent>

        <q:agent name="helper" model="gpt-4">
            <q:instruction>Help users</q:instruction>
            <q:tool name="readShared" builtin="true" />
        </q:agent>

        <q:execute task="Help the user" entry="router" />
    </q:team>
</q:component>'''

        component = parser.parse(xml)
        assert component is not None

        # Find team node
        team = None
        for stmt in component.statements:
            if isinstance(stmt, AgentTeamNode):
                team = stmt
                break

        assert team is not None
        assert team.name == "support"
        assert team.supervisor == "router"
        assert len(team.agents) == 2
        assert team.execute is not None
        assert team.execute.entry == "router"

    def test_parse_team_with_shared(self, parser):
        """Test parsing team with shared context."""
        xml = '''<?xml version="1.0"?>
<q:component name="Test" xmlns:q="urn:quantum">
    <q:team name="support">
        <q:shared>
            <q:set name="customerId" value="123" />
            <q:set name="customerName" value="John" />
        </q:shared>

        <q:agent name="helper" model="gpt-4">
            <q:instruction>Help</q:instruction>
            <q:tool name="readShared" builtin="true" />
        </q:agent>

        <q:execute task="Assist" />
    </q:team>
</q:component>'''

        component = parser.parse(xml)
        team = next(s for s in component.statements if isinstance(s, AgentTeamNode))

        assert len(team.shared) == 2

    def test_parse_team_with_builtin_tools(self, parser):
        """Test parsing team with builtin tools."""
        xml = '''<?xml version="1.0"?>
<q:component name="Test" xmlns:q="urn:quantum">
    <q:team name="support">
        <q:agent name="router" model="gpt-4">
            <q:instruction>Route requests</q:instruction>
            <q:tool name="handoff" builtin="true" />
            <q:tool name="listAgents" builtin="true" />
        </q:agent>

        <q:agent name="worker" model="gpt-4">
            <q:instruction>Do work</q:instruction>
            <q:tool name="readShared" builtin="true" />
            <q:tool name="writeShared" builtin="true" />
        </q:agent>

        <q:execute task="Work" />
    </q:team>
</q:component>'''

        component = parser.parse(xml)
        team = next(s for s in component.statements if isinstance(s, AgentTeamNode))

        router = team.get_agent("router")
        assert router is not None
        assert len(router.tools) == 2
        assert all(t.builtin for t in router.tools)

        worker = team.get_agent("worker")
        assert worker is not None
        assert len(worker.tools) == 2

    def test_parse_team_with_limits(self, parser):
        """Test parsing team with safety limits."""
        xml = '''<?xml version="1.0"?>
<q:component name="Test" xmlns:q="urn:quantum">
    <q:team name="support" max_handoffs="3" max_total_iterations="20">
        <q:agent name="agent" model="gpt-4">
            <q:instruction>Work</q:instruction>
            <q:tool name="process" description="Process data" />
        </q:agent>

        <q:execute task="Work" />
    </q:team>
</q:component>'''

        component = parser.parse(xml)
        team = next(s for s in component.statements if isinstance(s, AgentTeamNode))

        assert team.max_handoffs == 3
        assert team.max_total_iterations == 20


class TestTeamExecution:
    """Test team execution integration."""

    @pytest.fixture
    def mock_agent_service(self):
        """Create mock agent service."""
        reset_agent_service()
        reset_multi_agent_service()

        service = Mock(spec=AgentService)
        return service

    def test_team_execution_no_handoff(self, mock_agent_service):
        """Test team execution where first agent completes task."""
        # Mock agent service to return successful result with no handoff
        mock_agent_service.execute.return_value = AgentResult(
            success=True,
            result="Task completed by router",
            iterations=2,
            actions=[]
        )

        team = AgentTeam(
            name="support",
            agents={
                "router": {"instruction": "Route", "model": "gpt-4", "tools": []},
                "helper": {"instruction": "Help", "model": "gpt-4", "tools": []}
            },
            supervisor="router",
            agent_service=mock_agent_service
        )

        result = team.execute("Help the user")

        assert result.success is True
        assert result.final_agent == "router"
        assert len(result.handoffs) == 0

    def test_team_execution_with_handoff(self, mock_agent_service):
        """Test team execution with handoff."""
        # First agent returns handoff, second completes
        mock_agent_service.execute.side_effect = [
            AgentResult(
                success=True,
                result="Handing off to billing",
                iterations=1,
                actions=[
                    ToolCall(
                        tool="handoff",
                        args={"agent": "billing", "message": "Invoice help"},
                        result={"next_agent": "billing", "message": "Invoice help"}
                    )
                ]
            ),
            AgentResult(
                success=True,
                result="Invoice issue resolved",
                iterations=2,
                actions=[]
            )
        ]

        team = AgentTeam(
            name="support",
            agents={
                "router": {"instruction": "Route", "model": "gpt-4", "tools": []},
                "billing": {"instruction": "Billing", "model": "gpt-4", "tools": []}
            },
            supervisor="router",
            agent_service=mock_agent_service
        )

        result = team.execute("Help with my bill")

        assert result.success is True
        assert result.final_agent == "billing"
        assert len(result.handoffs) == 1
        assert result.handoffs[0].from_agent == "router"
        assert result.handoffs[0].to_agent == "billing"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
