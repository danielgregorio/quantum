"""
Tests for ExecutorRegistry

Validates the registry pattern for node execution dispatch.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestExecutorRegistry:
    """Test ExecutorRegistry functionality"""

    def test_import_registry(self):
        """Test that ExecutorRegistry can be imported"""
        from runtime.executor_registry import ExecutorRegistry
        assert ExecutorRegistry is not None

    def test_create_empty_registry(self):
        """Test creating an empty registry"""
        from runtime.executor_registry import ExecutorRegistry
        registry = ExecutorRegistry()
        assert registry.executor_count == 0
        assert registry.registered_types == []

    def test_register_executor(self):
        """Test registering an executor"""
        from runtime.executor_registry import ExecutorRegistry
        from runtime.executors.base import BaseExecutor

        # Create mock executor
        mock_executor = MagicMock(spec=BaseExecutor)
        mock_executor.handles = [str]  # Handle string type for testing

        registry = ExecutorRegistry()
        registry.register(mock_executor)

        assert str in registry.registered_types
        assert registry.has_executor(str)

    def test_register_multiple_types(self):
        """Test executor handling multiple types"""
        from runtime.executor_registry import ExecutorRegistry
        from runtime.executors.base import BaseExecutor

        mock_executor = MagicMock(spec=BaseExecutor)
        mock_executor.handles = [str, int, float]

        registry = ExecutorRegistry()
        registry.register(mock_executor)

        assert registry.has_executor(str)
        assert registry.has_executor(int)
        assert registry.has_executor(float)
        assert not registry.has_executor(list)

    def test_execute_dispatches_to_executor(self):
        """Test that execute calls the correct executor"""
        from runtime.executor_registry import ExecutorRegistry
        from runtime.executors.base import BaseExecutor

        mock_executor = MagicMock(spec=BaseExecutor)
        mock_executor.handles = [str]
        mock_executor.execute.return_value = "executed"

        registry = ExecutorRegistry()
        registry.register(mock_executor)

        mock_context = MagicMock()
        result = registry.execute("test", mock_context)

        mock_executor.execute.assert_called_once_with("test", mock_context)
        assert result == "executed"

    def test_execute_raises_for_unknown_type(self):
        """Test that execute raises for unregistered types"""
        from runtime.executor_registry import ExecutorRegistry, ExecutorNotFoundError

        registry = ExecutorRegistry()

        with pytest.raises(ExecutorNotFoundError):
            registry.execute("test", MagicMock())

    def test_fallback_executor(self):
        """Test fallback executor for unknown types"""
        from runtime.executor_registry import ExecutorRegistry
        from runtime.executors.base import BaseExecutor

        fallback = MagicMock(spec=BaseExecutor)
        fallback.execute.return_value = "fallback_result"

        registry = ExecutorRegistry()
        registry.set_fallback(fallback)

        mock_context = MagicMock()
        result = registry.execute("test", mock_context)

        fallback.execute.assert_called_once()
        assert result == "fallback_result"

    def test_register_all(self):
        """Test registering multiple executors at once"""
        from runtime.executor_registry import ExecutorRegistry
        from runtime.executors.base import BaseExecutor

        exec1 = MagicMock(spec=BaseExecutor)
        exec1.handles = [str]

        exec2 = MagicMock(spec=BaseExecutor)
        exec2.handles = [int]

        registry = ExecutorRegistry()
        registry.register_all([exec1, exec2])

        assert registry.has_executor(str)
        assert registry.has_executor(int)

    def test_can_execute(self):
        """Test can_execute check"""
        from runtime.executor_registry import ExecutorRegistry
        from runtime.executors.base import BaseExecutor

        mock_executor = MagicMock(spec=BaseExecutor)
        mock_executor.handles = [str]

        registry = ExecutorRegistry()
        registry.register(mock_executor)

        assert registry.can_execute("test")
        assert not registry.can_execute(123)


class TestBaseExecutor:
    """Test BaseExecutor abstract class"""

    def test_import_base_executor(self):
        """Test that BaseExecutor can be imported"""
        from runtime.executors.base import BaseExecutor
        assert BaseExecutor is not None

    def test_cannot_instantiate_directly(self):
        """Test that BaseExecutor cannot be instantiated"""
        from runtime.executors.base import BaseExecutor

        with pytest.raises(TypeError):
            BaseExecutor(MagicMock())


class TestServiceContainer:
    """Test ServiceContainer functionality"""

    def test_import_service_container(self):
        """Test that ServiceContainer can be imported"""
        from runtime.service_container import ServiceContainer
        assert ServiceContainer is not None

    def test_create_container(self):
        """Test creating a service container"""
        from runtime.service_container import ServiceContainer
        container = ServiceContainer()
        assert container.initialized_services == []

    def test_create_with_config(self):
        """Test creating container with config"""
        from runtime.service_container import ServiceContainer
        config = {'job_db_path': 'test.db'}
        container = ServiceContainer(config)
        assert container._config == config

    def test_register_custom_service(self):
        """Test registering a custom service"""
        from runtime.service_container import ServiceContainer

        container = ServiceContainer()
        mock_service = MagicMock()
        container.register('custom', mock_service)

        assert container.is_initialized('custom')
        assert container.get('custom') == mock_service

    def test_lazy_initialization(self):
        """Test that services are lazily initialized"""
        from runtime.service_container import ServiceContainer

        container = ServiceContainer()
        # Services should not be initialized until accessed
        assert not container.is_initialized('logging')
        assert not container.is_initialized('dump')


class TestControlFlowExecutors:
    """Test control flow executors"""

    def test_import_if_executor(self):
        """Test that IfExecutor can be imported"""
        from runtime.executors.control_flow import IfExecutor
        assert IfExecutor is not None

    def test_import_loop_executor(self):
        """Test that LoopExecutor can be imported"""
        from runtime.executors.control_flow import LoopExecutor
        assert LoopExecutor is not None

    def test_import_set_executor(self):
        """Test that SetExecutor can be imported"""
        from runtime.executors.control_flow import SetExecutor
        assert SetExecutor is not None

    def test_if_executor_handles_if_node(self):
        """Test that IfExecutor handles IfNode"""
        from runtime.executors.control_flow import IfExecutor
        from core.features.conditionals.src.ast_node import IfNode

        mock_runtime = MagicMock()
        executor = IfExecutor(mock_runtime)

        assert IfNode in executor.handles

    def test_loop_executor_handles_loop_node(self):
        """Test that LoopExecutor handles LoopNode"""
        from runtime.executors.control_flow import LoopExecutor
        from core.features.loops.src.ast_node import LoopNode

        mock_runtime = MagicMock()
        executor = LoopExecutor(mock_runtime)

        assert LoopNode in executor.handles

    def test_set_executor_handles_set_node(self):
        """Test that SetExecutor handles SetNode"""
        from runtime.executors.control_flow import SetExecutor
        from core.features.state_management.src.ast_node import SetNode

        mock_runtime = MagicMock()
        executor = SetExecutor(mock_runtime)

        assert SetNode in executor.handles


class TestDataExecutors:
    """Test data executors"""

    def test_import_query_executor(self):
        """Test that QueryExecutor can be imported"""
        from runtime.executors.data import QueryExecutor
        assert QueryExecutor is not None

    def test_import_invoke_executor(self):
        """Test that InvokeExecutor can be imported"""
        from runtime.executors.data import InvokeExecutor
        assert InvokeExecutor is not None

    def test_import_data_executor(self):
        """Test that DataExecutor can be imported"""
        from runtime.executors.data import DataExecutor
        assert DataExecutor is not None

    def test_import_transaction_executor(self):
        """Test that TransactionExecutor can be imported"""
        from runtime.executors.data import TransactionExecutor
        assert TransactionExecutor is not None

    def test_query_executor_handles_query_node(self):
        """Test that QueryExecutor handles QueryNode"""
        from runtime.executors.data import QueryExecutor
        from core.ast_nodes import QueryNode

        mock_runtime = MagicMock()
        executor = QueryExecutor(mock_runtime)

        assert QueryNode in executor.handles

    def test_invoke_executor_handles_invoke_node(self):
        """Test that InvokeExecutor handles InvokeNode"""
        from runtime.executors.data import InvokeExecutor
        from core.features.invocation.src.ast_node import InvokeNode

        mock_runtime = MagicMock()
        executor = InvokeExecutor(mock_runtime)

        assert InvokeNode in executor.handles

    def test_data_executor_handles_data_node(self):
        """Test that DataExecutor handles DataNode"""
        from runtime.executors.data import DataExecutor
        from core.ast_nodes import DataNode

        mock_runtime = MagicMock()
        executor = DataExecutor(mock_runtime)

        assert DataNode in executor.handles

    def test_transaction_executor_handles_transaction_node(self):
        """Test that TransactionExecutor handles TransactionNode"""
        from runtime.executors.data import TransactionExecutor
        from core.ast_nodes import TransactionNode

        mock_runtime = MagicMock()
        executor = TransactionExecutor(mock_runtime)

        assert TransactionNode in executor.handles


class TestParserRegistry:
    """Test ParserRegistry functionality"""

    def test_import_parser_registry(self):
        """Test that ParserRegistry can be imported"""
        from core.parser_registry import ParserRegistry
        assert ParserRegistry is not None

    def test_create_empty_registry(self):
        """Test creating an empty registry"""
        from core.parser_registry import ParserRegistry
        registry = ParserRegistry()
        assert registry.parser_count == 0
        assert registry.registered_tags == []

    def test_register_parser(self):
        """Test registering a parser"""
        from core.parser_registry import ParserRegistry
        from core.parsers.base import BaseTagParser

        mock_parser = MagicMock(spec=BaseTagParser)
        mock_parser.tag_names = ['test']

        registry = ParserRegistry()
        registry.register(mock_parser)

        assert 'test' in registry.registered_tags
        assert registry.has_parser('test')

    def test_register_multiple_tags(self):
        """Test parser handling multiple tags"""
        from core.parser_registry import ParserRegistry
        from core.parsers.base import BaseTagParser

        mock_parser = MagicMock(spec=BaseTagParser)
        mock_parser.tag_names = ['loop', 'for', 'while']

        registry = ParserRegistry()
        registry.register(mock_parser)

        assert registry.has_parser('loop')
        assert registry.has_parser('for')
        assert registry.has_parser('while')
        assert not registry.has_parser('if')

    def test_is_uppercase(self):
        """Test uppercase detection for component calls"""
        from core.parser_registry import ParserRegistry

        registry = ParserRegistry()

        assert registry.is_uppercase('MyComponent')
        assert registry.is_uppercase('Button')
        assert not registry.is_uppercase('div')
        assert not registry.is_uppercase('set')


class TestBaseTagParser:
    """Test BaseTagParser abstract class"""

    def test_import_base_tag_parser(self):
        """Test that BaseTagParser can be imported"""
        from core.parsers.base import BaseTagParser
        assert BaseTagParser is not None

    def test_cannot_instantiate_directly(self):
        """Test that BaseTagParser cannot be instantiated"""
        from core.parsers.base import BaseTagParser

        with pytest.raises(TypeError):
            BaseTagParser(MagicMock())


class TestServiceExecutors:
    """Test service executors"""

    def test_import_log_executor(self):
        """Test that LogExecutor can be imported"""
        from runtime.executors.services import LogExecutor
        assert LogExecutor is not None

    def test_import_dump_executor(self):
        """Test that DumpExecutor can be imported"""
        from runtime.executors.services import DumpExecutor
        assert DumpExecutor is not None

    def test_import_file_executor(self):
        """Test that FileExecutor can be imported"""
        from runtime.executors.services import FileExecutor
        assert FileExecutor is not None

    def test_import_mail_executor(self):
        """Test that MailExecutor can be imported"""
        from runtime.executors.services import MailExecutor
        assert MailExecutor is not None

    def test_log_executor_handles_log_node(self):
        """Test that LogExecutor handles LogNode"""
        from runtime.executors.services import LogExecutor
        from core.features.logging.src import LogNode

        mock_runtime = MagicMock()
        executor = LogExecutor(mock_runtime)

        assert LogNode in executor.handles

    def test_file_executor_handles_file_node(self):
        """Test that FileExecutor handles FileNode"""
        from runtime.executors.services import FileExecutor
        from core.ast_nodes import FileNode

        mock_runtime = MagicMock()
        executor = FileExecutor(mock_runtime)

        assert FileNode in executor.handles

    def test_mail_executor_handles_mail_node(self):
        """Test that MailExecutor handles MailNode"""
        from runtime.executors.services import MailExecutor
        from core.ast_nodes import MailNode

        mock_runtime = MagicMock()
        executor = MailExecutor(mock_runtime)

        assert MailNode in executor.handles


class TestAIExecutors:
    """Test AI executors"""

    def test_import_llm_executor(self):
        """Test that LLMExecutor can be imported"""
        from runtime.executors.ai import LLMExecutor
        assert LLMExecutor is not None

    def test_import_agent_executor(self):
        """Test that AgentExecutor can be imported"""
        from runtime.executors.ai import AgentExecutor
        assert AgentExecutor is not None

    def test_import_team_executor(self):
        """Test that TeamExecutor can be imported"""
        from runtime.executors.ai import TeamExecutor
        assert TeamExecutor is not None

    def test_import_knowledge_executor(self):
        """Test that KnowledgeExecutor can be imported"""
        from runtime.executors.ai import KnowledgeExecutor
        assert KnowledgeExecutor is not None

    def test_llm_executor_handles_llm_node(self):
        """Test that LLMExecutor handles LLMNode"""
        from runtime.executors.ai import LLMExecutor
        from core.ast_nodes import LLMNode

        mock_runtime = MagicMock()
        executor = LLMExecutor(mock_runtime)

        assert LLMNode in executor.handles

    def test_agent_executor_handles_agent_node(self):
        """Test that AgentExecutor handles AgentNode"""
        from runtime.executors.ai import AgentExecutor
        from core.features.agents.src.ast_node import AgentNode

        mock_runtime = MagicMock()
        executor = AgentExecutor(mock_runtime)

        assert AgentNode in executor.handles

    def test_team_executor_handles_team_node(self):
        """Test that TeamExecutor handles AgentTeamNode"""
        from runtime.executors.ai import TeamExecutor
        from core.features.agents.src.ast_node import AgentTeamNode

        mock_runtime = MagicMock()
        executor = TeamExecutor(mock_runtime)

        assert AgentTeamNode in executor.handles

    def test_knowledge_executor_handles_knowledge_node(self):
        """Test that KnowledgeExecutor handles KnowledgeNode"""
        from runtime.executors.ai import KnowledgeExecutor
        from core.features.knowledge_base.src.ast_node import KnowledgeNode

        mock_runtime = MagicMock()
        executor = KnowledgeExecutor(mock_runtime)

        assert KnowledgeNode in executor.handles


class TestMessagingExecutors:
    """Test messaging executors"""

    def test_import_websocket_executor(self):
        """Test that WebSocketExecutor can be imported"""
        from runtime.executors.messaging import WebSocketExecutor
        assert WebSocketExecutor is not None

    def test_import_message_executor(self):
        """Test that MessageExecutor can be imported"""
        from runtime.executors.messaging import MessageExecutor
        assert MessageExecutor is not None

    def test_import_queue_executor(self):
        """Test that QueueExecutor can be imported"""
        from runtime.executors.messaging import QueueExecutor
        assert QueueExecutor is not None

    def test_import_subscribe_executor(self):
        """Test that SubscribeExecutor can be imported"""
        from runtime.executors.messaging import SubscribeExecutor
        assert SubscribeExecutor is not None

    def test_websocket_executor_handles_websocket_node(self):
        """Test that WebSocketExecutor handles WebSocketNode"""
        from runtime.executors.messaging import WebSocketExecutor
        from core.features.websocket.src.ast_node import WebSocketNode

        mock_runtime = MagicMock()
        executor = WebSocketExecutor(mock_runtime)

        assert WebSocketNode in executor.handles

    def test_message_executor_handles_message_node(self):
        """Test that MessageExecutor handles MessageNode"""
        from runtime.executors.messaging import MessageExecutor
        from core.ast_nodes import MessageNode

        mock_runtime = MagicMock()
        executor = MessageExecutor(mock_runtime)

        assert MessageNode in executor.handles

    def test_queue_executor_handles_queue_node(self):
        """Test that QueueExecutor handles QueueNode"""
        from runtime.executors.messaging import QueueExecutor
        from core.ast_nodes import QueueNode

        mock_runtime = MagicMock()
        executor = QueueExecutor(mock_runtime)

        assert QueueNode in executor.handles


class TestJobsExecutors:
    """Test jobs executors"""

    def test_import_schedule_executor(self):
        """Test that ScheduleExecutor can be imported"""
        from runtime.executors.jobs import ScheduleExecutor
        assert ScheduleExecutor is not None

    def test_import_thread_executor(self):
        """Test that ThreadExecutor can be imported"""
        from runtime.executors.jobs import ThreadExecutor
        assert ThreadExecutor is not None

    def test_import_job_executor(self):
        """Test that JobExecutor can be imported"""
        from runtime.executors.jobs import JobExecutor
        assert JobExecutor is not None

    def test_schedule_executor_handles_schedule_node(self):
        """Test that ScheduleExecutor handles ScheduleNode"""
        from runtime.executors.jobs import ScheduleExecutor
        from core.ast_nodes import ScheduleNode

        mock_runtime = MagicMock()
        executor = ScheduleExecutor(mock_runtime)

        assert ScheduleNode in executor.handles

    def test_thread_executor_handles_thread_node(self):
        """Test that ThreadExecutor handles ThreadNode"""
        from runtime.executors.jobs import ThreadExecutor
        from core.ast_nodes import ThreadNode

        mock_runtime = MagicMock()
        executor = ThreadExecutor(mock_runtime)

        assert ThreadNode in executor.handles

    def test_job_executor_handles_job_node(self):
        """Test that JobExecutor handles JobNode"""
        from runtime.executors.jobs import JobExecutor
        from core.ast_nodes import JobNode

        mock_runtime = MagicMock()
        executor = JobExecutor(mock_runtime)

        assert JobNode in executor.handles


class TestScriptingExecutors:
    """Test scripting executors"""

    def test_import_python_executor(self):
        """Test that PythonExecutor can be imported"""
        from runtime.executors.scripting import PythonExecutor
        assert PythonExecutor is not None

    def test_import_pyimport_executor(self):
        """Test that PyImportExecutor can be imported"""
        from runtime.executors.scripting import PyImportExecutor
        assert PyImportExecutor is not None

    def test_import_pyclass_executor(self):
        """Test that PyClassExecutor can be imported"""
        from runtime.executors.scripting import PyClassExecutor
        assert PyClassExecutor is not None

    def test_python_executor_handles_python_node(self):
        """Test that PythonExecutor handles PythonNode"""
        from runtime.executors.scripting import PythonExecutor
        from core.ast_nodes import PythonNode

        mock_runtime = MagicMock()
        executor = PythonExecutor(mock_runtime)

        assert PythonNode in executor.handles

    def test_pyimport_executor_handles_pyimport_node(self):
        """Test that PyImportExecutor handles PyImportNode"""
        from runtime.executors.scripting import PyImportExecutor
        from core.ast_nodes import PyImportNode

        mock_runtime = MagicMock()
        executor = PyImportExecutor(mock_runtime)

        assert PyImportNode in executor.handles

    def test_pyclass_executor_handles_pyclass_node(self):
        """Test that PyClassExecutor handles PyClassNode"""
        from runtime.executors.scripting import PyClassExecutor
        from core.ast_nodes import PyClassNode

        mock_runtime = MagicMock()
        executor = PyClassExecutor(mock_runtime)

        assert PyClassNode in executor.handles


class TestAllExecutorsImport:
    """Test that all executors can be imported from main package"""

    def test_import_all_executors_from_package(self):
        """Test importing all executors from executors package"""
        from runtime.executors import (
            # Base
            BaseExecutor, ExecutorError,
            # Control flow
            IfExecutor, LoopExecutor, SetExecutor,
            # Data
            QueryExecutor, InvokeExecutor, DataExecutor, TransactionExecutor,
            # Services
            LogExecutor, DumpExecutor, FileExecutor, MailExecutor,
            # AI
            LLMExecutor, AgentExecutor, TeamExecutor, KnowledgeExecutor,
            # Messaging
            WebSocketExecutor, WebSocketSendExecutor, WebSocketCloseExecutor,
            MessageExecutor, SubscribeExecutor, QueueExecutor,
            # Jobs
            ScheduleExecutor, ThreadExecutor, JobExecutor,
            # Scripting
            PythonExecutor, PyImportExecutor, PyClassExecutor,
        )

        # Verify all are not None
        assert BaseExecutor is not None
        assert ExecutorError is not None
        assert IfExecutor is not None
        assert LoopExecutor is not None
        assert SetExecutor is not None
        assert QueryExecutor is not None
        assert InvokeExecutor is not None
        assert DataExecutor is not None
        assert TransactionExecutor is not None
        assert LogExecutor is not None
        assert DumpExecutor is not None
        assert FileExecutor is not None
        assert MailExecutor is not None
        assert LLMExecutor is not None
        assert AgentExecutor is not None
        assert TeamExecutor is not None
        assert KnowledgeExecutor is not None
        assert WebSocketExecutor is not None
        assert WebSocketSendExecutor is not None
        assert WebSocketCloseExecutor is not None
        assert MessageExecutor is not None
        assert SubscribeExecutor is not None
        assert QueueExecutor is not None
        assert ScheduleExecutor is not None
        assert ThreadExecutor is not None
        assert JobExecutor is not None
        assert PythonExecutor is not None
        assert PyImportExecutor is not None
        assert PyClassExecutor is not None


class TestControlFlowParsers:
    """Test control flow parsers"""

    def test_import_if_parser(self):
        """Test that IfParser can be imported"""
        from core.parsers.control_flow import IfParser
        assert IfParser is not None

    def test_import_loop_parser(self):
        """Test that LoopParser can be imported"""
        from core.parsers.control_flow import LoopParser
        assert LoopParser is not None

    def test_import_set_parser(self):
        """Test that SetParser can be imported"""
        from core.parsers.control_flow import SetParser
        assert SetParser is not None


class TestDataParsers:
    """Test data parsers"""

    def test_import_query_parser(self):
        """Test that QueryParser can be imported"""
        from core.parsers.data import QueryParser
        assert QueryParser is not None

    def test_import_invoke_parser(self):
        """Test that InvokeParser can be imported"""
        from core.parsers.data import InvokeParser
        assert InvokeParser is not None

    def test_import_data_parser(self):
        """Test that DataParser can be imported"""
        from core.parsers.data import DataParser
        assert DataParser is not None

    def test_import_transaction_parser(self):
        """Test that TransactionParser can be imported"""
        from core.parsers.data import TransactionParser
        assert TransactionParser is not None


class TestServiceParsers:
    """Test service parsers"""

    def test_import_log_parser(self):
        """Test that LogParser can be imported"""
        from core.parsers.services import LogParser
        assert LogParser is not None

    def test_import_dump_parser(self):
        """Test that DumpParser can be imported"""
        from core.parsers.services import DumpParser
        assert DumpParser is not None

    def test_import_file_parser(self):
        """Test that FileParser can be imported"""
        from core.parsers.services import FileParser
        assert FileParser is not None

    def test_import_mail_parser(self):
        """Test that MailParser can be imported"""
        from core.parsers.services import MailParser
        assert MailParser is not None


class TestAIParsers:
    """Test AI parsers"""

    def test_import_llm_parser(self):
        """Test that LLMParser can be imported"""
        from core.parsers.ai import LLMParser
        assert LLMParser is not None

    def test_import_agent_parser(self):
        """Test that AgentParser can be imported"""
        from core.parsers.ai import AgentParser
        assert AgentParser is not None

    def test_import_team_parser(self):
        """Test that TeamParser can be imported"""
        from core.parsers.ai import TeamParser
        assert TeamParser is not None

    def test_import_knowledge_parser(self):
        """Test that KnowledgeParser can be imported"""
        from core.parsers.ai import KnowledgeParser
        assert KnowledgeParser is not None


class TestMessagingParsers:
    """Test messaging parsers"""

    def test_import_websocket_parser(self):
        """Test that WebSocketParser can be imported"""
        from core.parsers.messaging import WebSocketParser
        assert WebSocketParser is not None

    def test_import_message_parser(self):
        """Test that MessageParser can be imported"""
        from core.parsers.messaging import MessageParser
        assert MessageParser is not None

    def test_import_subscribe_parser(self):
        """Test that SubscribeParser can be imported"""
        from core.parsers.messaging import SubscribeParser
        assert SubscribeParser is not None

    def test_import_queue_parser(self):
        """Test that QueueParser can be imported"""
        from core.parsers.messaging import QueueParser
        assert QueueParser is not None


class TestJobsParsers:
    """Test jobs parsers"""

    def test_import_schedule_parser(self):
        """Test that ScheduleParser can be imported"""
        from core.parsers.jobs import ScheduleParser
        assert ScheduleParser is not None

    def test_import_thread_parser(self):
        """Test that ThreadParser can be imported"""
        from core.parsers.jobs import ThreadParser
        assert ThreadParser is not None

    def test_import_job_parser(self):
        """Test that JobParser can be imported"""
        from core.parsers.jobs import JobParser
        assert JobParser is not None


class TestScriptingParsers:
    """Test scripting parsers"""

    def test_import_python_parser(self):
        """Test that PythonParser can be imported"""
        from core.parsers.scripting import PythonParser
        assert PythonParser is not None

    def test_import_pyimport_parser(self):
        """Test that PyImportParser can be imported"""
        from core.parsers.scripting import PyImportParser
        assert PyImportParser is not None

    def test_import_pyclass_parser(self):
        """Test that PyClassParser can be imported"""
        from core.parsers.scripting import PyClassParser
        assert PyClassParser is not None


class TestAllParsersImport:
    """Test that all parsers can be imported from main package"""

    def test_import_all_parsers_from_package(self):
        """Test importing all parsers from parsers package"""
        from core.parsers import (
            # Base
            BaseTagParser, ParserError,
            # Control flow
            IfParser, LoopParser, SetParser,
            # Data
            QueryParser, InvokeParser, DataParser, TransactionParser,
            # Services
            LogParser, DumpParser, FileParser, MailParser,
            # AI
            LLMParser, AgentParser, TeamParser, KnowledgeParser,
            # Messaging
            WebSocketParser, WebSocketSendParser, WebSocketCloseParser,
            MessageParser, SubscribeParser, QueueParser,
            # Jobs
            ScheduleParser, ThreadParser, JobParser,
            # Scripting
            PythonParser, PyImportParser, PyClassParser,
        )

        # Verify all are not None
        assert BaseTagParser is not None
        assert ParserError is not None
        assert IfParser is not None
        assert LoopParser is not None
        assert SetParser is not None
        assert QueryParser is not None
        assert InvokeParser is not None
        assert DataParser is not None
        assert TransactionParser is not None
        assert LogParser is not None
        assert DumpParser is not None
        assert FileParser is not None
        assert MailParser is not None
        assert LLMParser is not None
        assert AgentParser is not None
        assert TeamParser is not None
        assert KnowledgeParser is not None
        assert WebSocketParser is not None
        assert WebSocketSendParser is not None
        assert WebSocketCloseParser is not None
        assert MessageParser is not None
        assert SubscribeParser is not None
        assert QueueParser is not None
        assert ScheduleParser is not None
        assert ThreadParser is not None
        assert JobParser is not None
        assert PythonParser is not None
        assert PyImportParser is not None
        assert PyClassParser is not None
