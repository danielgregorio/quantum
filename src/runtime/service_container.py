"""
Service Container - Dependency injection for runtime services

Centralizes initialization and access to all runtime services
(database, email, LLM, etc.) instead of having them scattered
across ComponentRuntime.__init__.
"""

from typing import Any, Dict, Optional, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from runtime.database_service import DatabaseService
    from runtime.llm_service import LLMService
    from runtime.knowledge_service import KnowledgeService
    from runtime.message_queue_service import MessageQueueService
    from runtime.job_executor import JobExecutor
    from runtime.file_upload_service import FileUploadService
    from runtime.email_service import EmailService
    from runtime.function_registry import FunctionRegistry
    from core.features.invocation.src.runtime import InvocationService
    from core.features.data_import.src.runtime import DataImportService
    from core.features.logging.src import LoggingService
    from core.features.dump.src import DumpService

logger = logging.getLogger(__name__)


class ServiceContainer:
    """
    Container for all runtime services.

    Provides lazy initialization and centralized access to services.
    Services are initialized on first access to avoid unnecessary overhead.

    Example:
        services = ServiceContainer(config)
        db = services.database  # Initialized on first access
        llm = services.llm
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize service container.

        Args:
            config: Configuration dictionary with service-specific settings
        """
        self._config = config or {}
        self._services: Dict[str, Any] = {}

    # ==========================================================================
    # Core Services
    # ==========================================================================

    @property
    def database(self) -> 'DatabaseService':
        """Database service for query execution"""
        if 'database' not in self._services:
            from runtime.database_service import DatabaseService
            local_ds = self._config.get('datasources', {})
            self._services['database'] = DatabaseService(local_datasources=local_ds)
            logger.debug("Initialized DatabaseService")
        return self._services['database']

    @property
    def function_registry(self) -> 'FunctionRegistry':
        """Function registry for q:function"""
        if 'function_registry' not in self._services:
            from runtime.function_registry import FunctionRegistry
            self._services['function_registry'] = FunctionRegistry()
            logger.debug("Initialized FunctionRegistry")
        return self._services['function_registry']

    # ==========================================================================
    # Invocation & Data Services
    # ==========================================================================

    @property
    def invocation(self) -> 'InvocationService':
        """Invocation service for q:invoke"""
        if 'invocation' not in self._services:
            from core.features.invocation.src.runtime import InvocationService
            self._services['invocation'] = InvocationService()
            logger.debug("Initialized InvocationService")
        return self._services['invocation']

    @property
    def data_import(self) -> 'DataImportService':
        """Data import service for q:data"""
        if 'data_import' not in self._services:
            from core.features.data_import.src.runtime import DataImportService
            self._services['data_import'] = DataImportService()
            logger.debug("Initialized DataImportService")
        return self._services['data_import']

    # ==========================================================================
    # AI Services
    # ==========================================================================

    @property
    def llm(self) -> 'LLMService':
        """LLM service for q:llm"""
        if 'llm' not in self._services:
            from runtime.llm_service import LLMService
            self._services['llm'] = LLMService()
            logger.debug("Initialized LLMService")
        return self._services['llm']

    @property
    def knowledge(self) -> 'KnowledgeService':
        """Knowledge service for RAG/ChromaDB"""
        if 'knowledge' not in self._services:
            from runtime.knowledge_service import KnowledgeService
            self._services['knowledge'] = KnowledgeService(self.llm)
            logger.debug("Initialized KnowledgeService")
        return self._services['knowledge']

    @property
    def agent(self):
        """Agent service for q:agent"""
        if 'agent' not in self._services:
            from runtime.agent_service import get_agent_service
            self._services['agent'] = get_agent_service()
            logger.debug("Initialized AgentService")
        return self._services['agent']

    @property
    def multi_agent(self):
        """Multi-agent service for q:team"""
        if 'multi_agent' not in self._services:
            from runtime.agent_service import get_multi_agent_service
            self._services['multi_agent'] = get_multi_agent_service()
            logger.debug("Initialized MultiAgentService")
        return self._services['multi_agent']

    # ==========================================================================
    # Communication Services
    # ==========================================================================

    @property
    def message_queue(self) -> 'MessageQueueService':
        """Message queue service for q:message, q:subscribe"""
        if 'message_queue' not in self._services:
            from runtime.message_queue_service import MessageQueueService
            mq_config = self._config.get('message_queue', {})
            self._services['message_queue'] = MessageQueueService(mq_config)
            logger.debug("Initialized MessageQueueService")
        return self._services['message_queue']

    @property
    def email(self) -> 'EmailService':
        """Email service for q:mail"""
        if 'email' not in self._services:
            from runtime.email_service import EmailService
            self._services['email'] = EmailService()
            logger.debug("Initialized EmailService")
        return self._services['email']

    # ==========================================================================
    # Job & Scheduling Services
    # ==========================================================================

    @property
    def job_executor(self) -> 'JobExecutor':
        """Job executor for q:schedule, q:thread, q:job"""
        if 'job_executor' not in self._services:
            from runtime.job_executor import JobExecutor
            job_db_path = self._config.get('job_db_path', 'quantum_jobs.db')
            max_workers = self._config.get('max_thread_workers', 10)
            self._services['job_executor'] = JobExecutor(
                max_thread_workers=max_workers,
                job_db_path=job_db_path
            )
            logger.debug("Initialized JobExecutor")
        return self._services['job_executor']

    # ==========================================================================
    # File & Upload Services
    # ==========================================================================

    @property
    def file_upload(self) -> 'FileUploadService':
        """File upload service for q:file"""
        if 'file_upload' not in self._services:
            from runtime.file_upload_service import FileUploadService
            self._services['file_upload'] = FileUploadService()
            logger.debug("Initialized FileUploadService")
        return self._services['file_upload']

    # ==========================================================================
    # Developer Experience Services
    # ==========================================================================

    @property
    def logging(self) -> 'LoggingService':
        """Logging service for q:log"""
        if 'logging' not in self._services:
            from core.features.logging.src import LoggingService
            self._services['logging'] = LoggingService()
            logger.debug("Initialized LoggingService")
        return self._services['logging']

    @property
    def dump(self) -> 'DumpService':
        """Dump service for q:dump"""
        if 'dump' not in self._services:
            from core.features.dump.src import DumpService
            self._services['dump'] = DumpService()
            logger.debug("Initialized DumpService")
        return self._services['dump']

    # ==========================================================================
    # Cache Services
    # ==========================================================================

    @property
    def expression_cache(self):
        """Expression cache for performance"""
        if 'expression_cache' not in self._services:
            from runtime.expression_cache import get_expression_cache
            self._services['expression_cache'] = get_expression_cache()
            logger.debug("Initialized ExpressionCache")
        return self._services['expression_cache']

    # ==========================================================================
    # Utility Methods
    # ==========================================================================

    def get(self, name: str, default: Any = None) -> Any:
        """
        Get a service by name.

        Args:
            name: Service name (e.g., 'database', 'llm')
            default: Default value if not found

        Returns:
            Service instance or default
        """
        # Try property access first
        if hasattr(self, name):
            return getattr(self, name)
        return self._services.get(name, default)

    def register(self, name: str, service: Any) -> 'ServiceContainer':
        """
        Register a custom service.

        Args:
            name: Service name
            service: Service instance

        Returns:
            Self for chaining
        """
        self._services[name] = service
        return self

    def is_initialized(self, name: str) -> bool:
        """Check if a service has been initialized"""
        return name in self._services

    @property
    def initialized_services(self) -> list:
        """Get list of initialized service names"""
        return list(self._services.keys())

    def shutdown(self):
        """
        Shutdown all services that support it.

        Call this when the runtime is being destroyed.
        """
        for name, service in self._services.items():
            if hasattr(service, 'shutdown'):
                try:
                    service.shutdown()
                    logger.debug(f"Shutdown {name}")
                except Exception as e:
                    logger.warning(f"Error shutting down {name}: {e}")

        self._services.clear()

    def __repr__(self) -> str:
        initialized = list(self._services.keys())
        return f"ServiceContainer(initialized={initialized})"
