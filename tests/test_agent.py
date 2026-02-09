"""
Tests for q:agent - AI Agents with Tool Use

Tests the complete agent pipeline:
- AST node parsing
- AgentService reasoning loop
- Tool execution
- Result handling
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock

# Add src to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.features.agents.src.ast_node import (
    AgentNode, AgentToolNode, AgentToolParamNode,
    AgentInstructionNode, AgentExecuteNode
)
from runtime.agent_service import (
    AgentService, AgentResult, ToolCall, AgentError,
    get_agent_service, reset_agent_service
)


class TestAgentASTNodes:
    """Test AST node classes."""

    def test_agent_node_creation(self):
        """Test basic AgentNode creation."""
        agent = AgentNode(
            name="test_agent",
            model="phi3",
            max_iterations=5
        )
        assert agent.name == "test_agent"
        assert agent.model == "phi3"
        assert agent.max_iterations == 5
        assert agent.timeout == 60000  # default

    def test_agent_node_with_instruction(self):
        """Test AgentNode with instruction."""
        instruction = AgentInstructionNode(content="You are a helpful assistant.")
        agent = AgentNode(
            name="helper",
            model="phi3",
            instruction=instruction
        )
        assert agent.instruction is not None
        assert agent.instruction.content == "You are a helpful assistant."

    def test_agent_node_with_tools(self):
        """Test AgentNode with tools."""
        param = AgentToolParamNode(
            name="orderId",
            type="integer",
            required=True,
            description="The order ID"
        )
        tool = AgentToolNode(
            name="getOrder",
            description="Get order details",
            params=[param]
        )
        agent = AgentNode(
            name="support",
            model="phi3",
            tools=[tool]
        )
        assert len(agent.tools) == 1
        assert agent.tools[0].name == "getOrder"
        assert len(agent.tools[0].params) == 1
        assert agent.tools[0].params[0].name == "orderId"

    def test_agent_node_with_execute(self):
        """Test AgentNode with execute."""
        execute = AgentExecuteNode(
            task="Check order status",
            context="User ID: 123"
        )
        agent = AgentNode(
            name="support",
            model="phi3",
            execute=execute
        )
        assert agent.execute is not None
        assert agent.execute.task == "Check order status"
        assert agent.execute.context == "User ID: 123"

    def test_tool_node_get_schema(self):
        """Test tool schema generation for LLM."""
        tool = AgentToolNode(
            name="search",
            description="Search for items",
            params=[
                AgentToolParamNode(name="query", type="string", required=True),
                AgentToolParamNode(name="limit", type="integer", required=False, default=10)
            ]
        )
        schema = tool.get_schema()
        assert schema["name"] == "search"
        assert schema["description"] == "Search for items"
        assert "query" in schema["parameters"]["properties"]
        assert "query" in schema["parameters"]["required"]
        assert "limit" not in schema["parameters"]["required"]

    def test_agent_node_validation(self):
        """Test AgentNode validation."""
        # Missing name
        agent = AgentNode(name="", model="phi3")
        errors = agent.validate()
        assert any("name" in e.lower() for e in errors)

        # No tools
        agent = AgentNode(name="test", model="phi3")
        errors = agent.validate()
        assert any("tool" in e.lower() for e in errors)

        # No execute
        agent = AgentNode(
            name="test",
            model="phi3",
            tools=[AgentToolNode(name="tool1", description="A tool")]
        )
        errors = agent.validate()
        assert any("execute" in e.lower() for e in errors)

    def test_tool_param_validation(self):
        """Test parameter validation."""
        # Invalid type
        param = AgentToolParamNode(name="x", type="invalid_type")
        errors = param.validate()
        assert any("type" in e.lower() for e in errors)

        # Missing name
        param = AgentToolParamNode(name="", type="string")
        errors = param.validate()
        assert any("name" in e.lower() for e in errors)


class TestAgentService:
    """Test AgentService class."""

    @pytest.fixture
    def mock_llm_service(self):
        """Create mock LLM service (multi-provider compatible)."""
        service = Mock()
        # Return dict with 'content' key (MultiProviderLLMService format)
        service.chat.return_value = {"content": "", "success": True}
        return service

    @pytest.fixture
    def agent_service(self, mock_llm_service):
        """Create agent service with mock LLM."""
        reset_agent_service()
        service = AgentService()
        # Mock the multi_llm_service
        service._multi_llm_service = mock_llm_service
        return service

    def test_service_creation(self, agent_service):
        """Test service instantiation."""
        assert agent_service is not None

    def test_build_tools_description(self, agent_service):
        """Test tools description generation."""
        tools = [
            {
                "name": "getOrder",
                "description": "Get order by ID",
                "params": [
                    {"name": "orderId", "type": "integer", "required": True}
                ]
            }
        ]
        desc = agent_service._build_tools_description(tools)
        assert "getOrder" in desc
        assert "Get order by ID" in desc
        assert "orderId" in desc

    def test_extract_action_from_json_block(self, agent_service):
        """Test action extraction from JSON code block."""
        response = '''I'll look up the order.
```json
{"action": "getOrder", "args": {"orderId": 123}}
```'''
        action = agent_service._extract_action(response)
        assert action is not None
        assert action["action"] == "getOrder"
        assert action["args"]["orderId"] == 123

    def test_extract_action_finish(self, agent_service):
        """Test finish action extraction."""
        response = '''```json
{"action": "finish", "result": "The order is ready."}
```'''
        action = agent_service._extract_action(response)
        assert action is not None
        assert action["action"] == "finish"
        assert action["result"] == "The order is ready."

    def test_extract_action_raw_json(self, agent_service):
        """Test action extraction from raw JSON."""
        response = '{"action": "search", "args": {"query": "test"}}'
        action = agent_service._extract_action(response)
        assert action is not None
        assert action["action"] == "search"

    def test_extract_action_invalid(self, agent_service):
        """Test action extraction from invalid response."""
        response = "I don't know how to help with that."
        action = agent_service._extract_action(response)
        assert action is None

    def test_execute_tool_with_handler(self, agent_service):
        """Test tool execution with registered handler."""
        def mock_handler(args):
            return {"order_id": args["orderId"], "status": "shipped"}

        agent_service.register_tool_handler("getOrder", mock_handler)

        tool_def = {
            "name": "getOrder",
            "description": "Get order",
            "params": []
        }
        result = agent_service._execute_tool(
            "getOrder",
            {"orderId": 123},
            tool_def
        )
        assert result.tool == "getOrder"
        assert result.result["status"] == "shipped"
        assert result.error is None

    def test_execute_tool_error_handling(self, agent_service):
        """Test tool execution error handling."""
        def failing_handler(args):
            raise ValueError("Database connection failed")

        agent_service.register_tool_handler("getOrder", failing_handler)

        tool_def = {"name": "getOrder", "description": "Get order", "params": []}
        result = agent_service._execute_tool("getOrder", {}, tool_def)
        assert result.error is not None
        assert "Database connection failed" in result.error

    def test_execute_agent_success(self, agent_service, mock_llm_service):
        """Test successful agent execution."""
        # Setup mock LLM responses
        mock_llm_service.chat.side_effect = [
            # First call: agent decides to use tool
            {"content": '```json\n{"action": "getOrder", "args": {"orderId": 123}}\n```'},
            # Second call: agent finishes
            {"content": '```json\n{"action": "finish", "result": "Order 123 is shipped."}\n```'}
        ]

        # Register tool handler
        agent_service.register_tool_handler(
            "getOrder",
            lambda args: {"id": args["orderId"], "status": "shipped"}
        )

        result = agent_service.execute(
            instruction="Help with orders",
            tools=[{
                "name": "getOrder",
                "description": "Get order by ID",
                "params": [{"name": "orderId", "type": "integer", "required": True}]
            }],
            task="Check order 123",
            model="phi3",
            max_iterations=5
        )

        assert result.success is True
        assert "shipped" in result.result.lower() or "123" in result.result
        assert result.action_count == 1
        assert len(result.actions) == 1
        assert result.actions[0].tool == "getOrder"

    def test_execute_agent_max_iterations(self, agent_service, mock_llm_service):
        """Test agent stops at max iterations."""
        # Mock LLM always asks for tool
        mock_llm_service.chat.return_value = {
            "content": '```json\n{"action": "search", "args": {"q": "test"}}\n```'
        }

        agent_service.register_tool_handler("search", lambda args: "no results")

        result = agent_service.execute(
            instruction="Search forever",
            tools=[{"name": "search", "description": "Search", "params": []}],
            task="Find something",
            model="phi3",
            max_iterations=3
        )

        assert result.success is False
        assert result.iterations == 3
        assert result.error is not None
        assert "maximum iterations" in result.error["message"].lower()

    def test_execute_agent_timeout(self, agent_service, mock_llm_service):
        """Test agent timeout."""
        import time

        def slow_llm_call(*args, **kwargs):
            time.sleep(0.2)  # Simulate slow response
            return {"content": '{"action": "search", "args": {}}'}

        mock_llm_service.chat.side_effect = slow_llm_call
        agent_service.register_tool_handler("search", lambda args: "ok")

        result = agent_service.execute(
            instruction="Test",
            tools=[{"name": "search", "description": "Search", "params": []}],
            task="Do something",
            model="phi3",
            max_iterations=10,
            timeout_ms=100  # Very short timeout
        )

        assert result.success is False
        assert result.error is not None
        assert "timed out" in result.error["message"].lower()

    def test_execute_agent_unknown_tool(self, agent_service, mock_llm_service):
        """Test agent handles unknown tool gracefully."""
        mock_llm_service.chat.side_effect = [
            {"content": '{"action": "unknownTool", "args": {}}'},
            {"content": '{"action": "finish", "result": "Done"}'}
        ]

        result = agent_service.execute(
            instruction="Test",
            tools=[{"name": "validTool", "description": "Valid", "params": []}],
            task="Do something",
            model="phi3"
        )

        # Should still succeed after recovering
        assert result.success is True
        assert result.action_count == 0  # Unknown tool not counted

    def test_agent_result_to_dict(self):
        """Test AgentResult serialization."""
        result = AgentResult(
            success=True,
            result="Task completed",
            execution_time_ms=1500.5,
            iterations=3,
            action_count=2,
            actions=[
                ToolCall(tool="search", args={"q": "test"}, result="found"),
                ToolCall(tool="process", args={}, result="done")
            ]
        )
        d = result.to_dict()
        assert d["success"] is True
        assert d["result"] == "Task completed"
        assert d["executionTime"] == 1500.5
        assert d["iterations"] == 3
        assert d["actionCount"] == 2
        assert len(d["actions"]) == 2


class TestAgentParsing:
    """Test parser integration."""

    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        from core.parser import QuantumParser
        return QuantumParser(use_cache=False)

    def test_parse_simple_agent(self, parser):
        """Test parsing a simple agent."""
        xml = '''<?xml version="1.0"?>
<q:component name="Test" xmlns:q="urn:quantum">
    <q:agent name="helper" model="phi3">
        <q:instruction>You are helpful.</q:instruction>
        <q:tool name="greet" description="Say hello">
            <q:param name="name" type="string" required="true" />
        </q:tool>
        <q:execute task="Greet the user" />
    </q:agent>
</q:component>'''

        component = parser.parse(xml)
        assert component is not None

        # Find agent node
        agent = None
        for stmt in component.statements:
            if isinstance(stmt, AgentNode):
                agent = stmt
                break

        assert agent is not None
        assert agent.name == "helper"
        assert agent.model == "phi3"
        assert agent.instruction is not None
        assert len(agent.tools) == 1
        assert agent.tools[0].name == "greet"
        assert len(agent.tools[0].params) == 1
        assert agent.execute is not None

    def test_parse_agent_with_multiple_tools(self, parser):
        """Test parsing agent with multiple tools."""
        xml = '''<?xml version="1.0"?>
<q:component name="Test" xmlns:q="urn:quantum">
    <q:agent name="support" model="mistral" max_iterations="10" timeout="30000">
        <q:instruction>Customer support agent.</q:instruction>

        <q:tool name="getOrder" description="Get order details">
            <q:param name="orderId" type="integer" required="true" />
        </q:tool>

        <q:tool name="updateStatus" description="Update order status">
            <q:param name="orderId" type="integer" required="true" />
            <q:param name="status" type="string" required="true" />
        </q:tool>

        <q:execute task="Help the customer" context="Premium user" />
    </q:agent>
</q:component>'''

        component = parser.parse(xml)
        agent = next(s for s in component.statements if isinstance(s, AgentNode))

        assert agent.model == "mistral"
        assert agent.max_iterations == 10
        assert agent.timeout == 30000
        assert len(agent.tools) == 2
        assert agent.execute.context == "Premium user"


class TestAgentIntegration:
    """Integration tests with component runtime."""

    @pytest.fixture
    def mock_llm_response(self):
        """Setup mock for LLM service."""
        with patch('runtime.agent_service.AgentService.llm_service') as mock:
            mock.chat.side_effect = [
                {"content": '{"action": "finish", "result": "Hello, world!"}'}
            ]
            yield mock

    def test_agent_result_in_context(self):
        """Test that agent results are stored in context."""
        from runtime.agent_service import AgentService, reset_agent_service

        reset_agent_service()

        # Create mock multi-provider LLM service
        mock_llm = Mock()
        mock_llm.chat.return_value = {
            "content": '{"action": "finish", "result": "Task completed successfully."}',
            "success": True
        }

        service = AgentService()
        # Mock the multi_llm_service property
        service._multi_llm_service = mock_llm

        result = service.execute(
            instruction="Be helpful",
            tools=[{"name": "test", "description": "Test tool", "params": []}],
            task="Do something",
            model="phi3"
        )

        assert result.success is True
        assert result.result == "Task completed successfully."

        # Check result dict structure
        result_dict = result.to_dict()
        assert "success" in result_dict
        assert "result" in result_dict
        assert "actions" in result_dict
        assert "executionTime" in result_dict


class TestToolCall:
    """Test ToolCall dataclass."""

    def test_tool_call_creation(self):
        """Test ToolCall creation."""
        call = ToolCall(
            tool="search",
            args={"query": "test"},
            result={"items": [1, 2, 3]},
            duration_ms=150.5
        )
        assert call.tool == "search"
        assert call.args["query"] == "test"
        assert len(call.result["items"]) == 3
        assert call.error is None

    def test_tool_call_with_error(self):
        """Test ToolCall with error."""
        call = ToolCall(
            tool="failing_tool",
            args={},
            error="Connection refused"
        )
        assert call.error == "Connection refused"
        assert call.result is None

    def test_tool_call_to_dict(self):
        """Test ToolCall serialization."""
        call = ToolCall(
            tool="process",
            args={"x": 1},
            result="done",
            duration_ms=50.0
        )
        d = call.to_dict()
        assert d["tool"] == "process"
        assert d["args"] == {"x": 1}
        assert d["result"] == "done"


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
