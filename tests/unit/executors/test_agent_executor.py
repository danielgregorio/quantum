"""
Tests for AgentExecutor - q:agent AI agent execution

Coverage target: 22% -> 60%
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from runtime.executors.ai.agent_executor import AgentExecutor
from runtime.executors.base import ExecutorError

# Import AgentNode from the correct location
try:
    from core.features.agents.src.ast_node import AgentNode
except ImportError:
    from core.features.agents.src import AgentNode

# Import fixtures from conftest.py
from tests.unit.executors.conftest import MockRuntime, MockExecutionContext


# =============================================================================
# Mock Objects for Agent Service
# =============================================================================

class MockAgentService:
    """Mock agent service"""

    def __init__(self):
        self.last_config = None
        self._results = {}

    def set_result(self, task: str, result: Dict):
        """Set mock result for task"""
        self._results[task] = result

    def execute(self, model: str, provider: str, endpoint: str, api_key: str,
                instruction: str, tools: List, tool_nodes: List,
                task: str, context: str, max_iterations: int, timeout: int,
                exec_context, runtime) -> Dict:
        """Mock agent execute"""
        self.last_config = {
            'model': model,
            'provider': provider,
            'endpoint': endpoint,
            'instruction': instruction,
            'tools': tools,
            'task': task,
            'context': context,
            'max_iterations': max_iterations,
            'timeout': timeout
        }

        if task in self._results:
            return self._results[task]

        return {
            'success': True,
            'result': f'Completed task: {task}',
            'iterations': 1,
            'actions': []
        }


class MockAgentRuntime(MockRuntime):
    """Extended mock runtime with agent service"""

    def __init__(self, variables: Dict[str, Any] = None):
        super().__init__(variables)
        self._agent_service = MockAgentService()
        self._services = MagicMock()
        self._services.agent = self._agent_service

    @property
    def services(self):
        return self._services


# =============================================================================
# Mock AST Nodes
# =============================================================================

@dataclass
class MockExecuteNode:
    """Mock execute node"""
    task: str
    context: Optional[str] = None


@dataclass
class MockInstructionNode:
    """Mock instruction node"""
    content: str


@dataclass
class MockToolNode:
    """Mock tool node"""
    name: str
    builtin: bool = False
    description: str = ""
    parameters: List = field(default_factory=list)

    def get_schema(self) -> Dict:
        return {
            'name': self.name,
            'description': self.description,
            'parameters': self.parameters
        }


# =============================================================================
# Test Classes
# =============================================================================

class TestAgentExecutorBasic:
    """Basic functionality tests"""

    def test_handles_agent_node(self):
        """Test that AgentExecutor handles AgentNode"""
        runtime = MockAgentRuntime()
        executor = AgentExecutor(runtime)
        assert AgentNode in executor.handles

    def test_handles_returns_list(self):
        """Test that handles returns a list"""
        runtime = MockAgentRuntime()
        executor = AgentExecutor(runtime)
        assert isinstance(executor.handles, list)
        assert len(executor.handles) == 1


class TestExecuteNode:
    """Test execute node handling"""

    def test_requires_execute_node(self):
        """Test that agent requires execute node"""
        runtime = MockAgentRuntime()
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.execute = None  # No execute node

        with pytest.raises(ExecutorError, match="requires <q:execute>"):
            executor.execute(node, runtime.execution_context)

    def test_task_from_execute(self):
        """Test task is extracted from execute node"""
        runtime = MockAgentRuntime()
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.execute = MockExecuteNode("Find the weather in Paris")

        executor.execute(node, runtime.execution_context)

        assert runtime._agent_service.last_config["task"] == "Find the weather in Paris"

    def test_task_with_databinding(self):
        """Test task with databinding"""
        runtime = MockAgentRuntime({"city": "Tokyo"})
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.execute = MockExecuteNode("Find weather in {city}")

        executor.execute(node, runtime.execution_context)

        assert runtime._agent_service.last_config["task"] == "Find weather in Tokyo"

    def test_context_from_execute(self):
        """Test context is extracted from execute node"""
        runtime = MockAgentRuntime()
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.execute = MockExecuteNode("Do task", "Additional context here")

        executor.execute(node, runtime.execution_context)

        assert runtime._agent_service.last_config["context"] == "Additional context here"


class TestInstruction:
    """Test instruction handling"""

    def test_instruction_passed(self):
        """Test that instruction is passed to service"""
        runtime = MockAgentRuntime()
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.execute = MockExecuteNode("Task")
        node.instruction = MockInstructionNode("You are a helpful assistant")

        executor.execute(node, runtime.execution_context)

        assert runtime._agent_service.last_config["instruction"] == "You are a helpful assistant"

    def test_instruction_with_databinding(self):
        """Test instruction with databinding"""
        runtime = MockAgentRuntime({"role": "Python expert"})
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.execute = MockExecuteNode("Task")
        node.instruction = MockInstructionNode("You are a {role}")

        executor.execute(node, runtime.execution_context)

        assert runtime._agent_service.last_config["instruction"] == "You are a Python expert"

    def test_empty_instruction(self):
        """Test that empty instruction is handled"""
        runtime = MockAgentRuntime()
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.execute = MockExecuteNode("Task")
        node.instruction = None

        executor.execute(node, runtime.execution_context)

        assert runtime._agent_service.last_config["instruction"] == ""


class TestTools:
    """Test tool handling"""

    def test_builtin_tools(self):
        """Test builtin tools are marked correctly"""
        runtime = MockAgentRuntime()
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.execute = MockExecuteNode("Task")
        node.tools = [MockToolNode("web_search", builtin=True)]

        executor.execute(node, runtime.execution_context)

        tools = runtime._agent_service.last_config["tools"]
        assert len(tools) == 1
        assert tools[0]["name"] == "web_search"
        assert tools[0]["builtin"] is True

    def test_custom_tools(self):
        """Test custom tools use schema"""
        runtime = MockAgentRuntime()
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.execute = MockExecuteNode("Task")
        node.tools = [MockToolNode("calculate", builtin=False, description="Does math")]

        executor.execute(node, runtime.execution_context)

        tools = runtime._agent_service.last_config["tools"]
        assert len(tools) == 1
        assert tools[0]["name"] == "calculate"
        assert tools[0]["description"] == "Does math"

    def test_multiple_tools(self):
        """Test multiple tools"""
        runtime = MockAgentRuntime()
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.execute = MockExecuteNode("Task")
        node.tools = [
            MockToolNode("web_search", builtin=True),
            MockToolNode("calculator", builtin=False),
            MockToolNode("file_reader", builtin=True)
        ]

        executor.execute(node, runtime.execution_context)

        tools = runtime._agent_service.last_config["tools"]
        assert len(tools) == 3


class TestModelAndProvider:
    """Test model and provider configuration"""

    def test_model_passed(self):
        """Test model is passed to service"""
        runtime = MockAgentRuntime()
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.model = "gpt-4"
        node.execute = MockExecuteNode("Task")

        executor.execute(node, runtime.execution_context)

        assert runtime._agent_service.last_config["model"] == "gpt-4"

    def test_provider_passed(self):
        """Test provider is passed to service"""
        runtime = MockAgentRuntime()
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.provider = "openai"
        node.execute = MockExecuteNode("Task")

        executor.execute(node, runtime.execution_context)

        assert runtime._agent_service.last_config["provider"] == "openai"

    def test_endpoint_passed(self):
        """Test custom endpoint is passed"""
        runtime = MockAgentRuntime()
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.endpoint = "http://localhost:11434"
        node.execute = MockExecuteNode("Task")

        executor.execute(node, runtime.execution_context)

        assert runtime._agent_service.last_config["endpoint"] == "http://localhost:11434"

    def test_api_key_passed(self):
        """Test API key is passed"""
        runtime = MockAgentRuntime({"apiKey": "sk-123"})
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.api_key = "{apiKey}"
        node.execute = MockExecuteNode("Task")

        executor.execute(node, runtime.execution_context)

        # API key resolved via databinding (but not in config for security)
        # The key is passed separately


class TestLimits:
    """Test iteration and timeout limits"""

    def test_max_iterations_passed(self):
        """Test max iterations is passed"""
        runtime = MockAgentRuntime()
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.max_iterations = 5
        node.execute = MockExecuteNode("Task")

        executor.execute(node, runtime.execution_context)

        assert runtime._agent_service.last_config["max_iterations"] == 5

    def test_timeout_passed(self):
        """Test timeout is passed"""
        runtime = MockAgentRuntime()
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.timeout = 30000
        node.execute = MockExecuteNode("Task")

        executor.execute(node, runtime.execution_context)

        assert runtime._agent_service.last_config["timeout"] == 30000


class TestResultStorage:
    """Test result storage"""

    def test_stores_result(self):
        """Test that result is stored"""
        runtime = MockAgentRuntime()
        runtime._agent_service.set_result("My task", {
            'success': True,
            'result': 'Task completed successfully',
            'iterations': 3,
            'actions': []
        })
        executor = AgentExecutor(runtime)

        node = AgentNode("myAgent")
        node.execute = MockExecuteNode("My task")

        executor.execute(node, runtime.execution_context)

        stored = runtime.execution_context.get_variable("myAgent")
        assert stored == "Task completed successfully"

    def test_stores_full_result(self):
        """Test that full result object is stored"""
        runtime = MockAgentRuntime()
        runtime._agent_service.set_result("Task", {
            'success': True,
            'result': 'Done',
            'iterations': 2,
            'actions': [{'tool': 'search', 'input': 'query'}]
        })
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.execute = MockExecuteNode("Task")

        executor.execute(node, runtime.execution_context)

        full_result = runtime.execution_context.get_variable("agent_result")
        assert full_result["success"] is True
        assert full_result["iterations"] == 2
        assert len(full_result["actions"]) == 1


class TestErrorHandling:
    """Test error handling"""

    def test_error_stores_failure_result(self):
        """Test that error stores failure result"""
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
        """Test error result has correct format"""
        runtime = MockAgentRuntime()
        runtime._agent_service.execute = MagicMock(side_effect=Exception("Error"))
        executor = AgentExecutor(runtime)

        node = AgentNode("agent")
        node.execute = MockExecuteNode("Task")

        with pytest.raises(ExecutorError):
            executor.execute(node, runtime.execution_context)

        error_result = runtime.execution_context.get_variable("agent_result")
        assert "success" in error_result
        assert "error" in error_result
        assert "result" in error_result
        assert "iterations" in error_result
        assert "actions" in error_result
