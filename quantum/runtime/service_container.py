"""
Service Container - Dependency injection for runtime services

Centralizes initialization and access to all runtime services
(database, email, LLM, etc.) instead of having them scattered
across ComponentRuntime.__init__.
"""

import copy
from typing import Any, Dict, Optional, TYPE_CHECKING
import logging
import os

if TYPE_CHECKING:
    from quantum.runtime.database_service import DatabaseService
    from quantum.runtime.llm_service import LLMService
    from quantum.runtime.knowledge_service import KnowledgeService
    from quantum.runtime.message_queue_service import MessageQueueService
    from quantum.runtime.job_executor import JobExecutor
    from quantum.runtime.file_upload_service import FileUploadService
    from quantum.runtime.email_service import EmailService
    from quantum.runtime.function_registry import FunctionRegistry
    from quantum.core.features.invocation.src.runtime import InvocationService
    from quantum.core.features.data_import.src.runtime import DataImportService
    from quantum.core.features.logging.src import LoggingService
    from quantum.core.features.dump.src import DumpService

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_FILE = 'quantum.config.yaml'


_config_cache: Dict[str, Any] = {}


def load_project_config(config_path: str = _DEFAULT_CONFIG_FILE) -> Dict[str, Any]:
    """Read quantum.config.yaml from the working directory, if it is there.

    Missing file: empty configuration, no complaint — a .q file that uses no
    datasource needs none. Unreadable or invalid file: empty configuration
    and a warning, because silence there is how a typo in the YAML turns
    into "datasource not declared" three layers down.

    Cached by (path, mtime, size). Every ComponentRuntime() built without a
    config re-read and re-parsed the file — 200 runtimes meant 200 disk reads
    — and the suite builds thousands. Keying on mtime keeps the property that
    matters: edit the file and the next runtime sees the change.

    A copy is returned, not the cached dict: services mutate their config,
    and handing out the same object would let one runtime's changes leak into
    the next.
    """
    import os
    try:
        stat = os.stat(config_path)
    except OSError:
        return {}

    key = (os.path.abspath(config_path), stat.st_mtime_ns, stat.st_size)
    cached = _config_cache.get(key)
    if cached is not None:
        return copy.deepcopy(cached)

    try:
        import yaml
        with open(config_path, 'r', encoding='utf-8') as handle:
            loaded = yaml.safe_load(handle)
        if loaded is None:
            loaded = {}
        if not isinstance(loaded, dict):
            logger.warning("%s does not contain a mapping; ignoring it",
                           config_path)
            loaded = {}
    except Exception as exc:
        logger.warning("could not read %s: %s", config_path, exc)
        return {}

    _config_cache.clear()      # uma entrada basta; o arquivo e um so
    _config_cache[key] = loaded
    return copy.deepcopy(loaded)


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
            config: Configuration dictionary with service-specific settings.
                Omit it (None) to read quantum.config.yaml from the working
                directory; pass {} for a deliberately empty configuration.

        `None` used to mean "no configuration", so anything that built a
        runtime without passing one — the .q test plugin, library callers,
        the admin — could not see the `datasources:` declared in
        quantum.config.yaml, and every q:query and q:transaction fell through
        to the optional Admin API at localhost:8000 and failed with a
        connection error. `quantum run` was fixed to load the file; that fix
        did not reach anybody else. Now the default is the same either way,
        and passing {} still means empty.
        """
        self._config = load_project_config() if config is None else config
        self._services: Dict[str, Any] = {}

    # ==========================================================================
    # Core Services
    # ==========================================================================

    @property
    def database(self) -> 'DatabaseService':
        """Database service for query execution"""
        if 'database' not in self._services:
            from quantum.runtime.database_service import DatabaseService
            local_ds = self._config.get('datasources', {})
            self._services['database'] = DatabaseService(local_datasources=local_ds)
            logger.debug("Initialized DatabaseService")
        return self._services['database']

    @property
    def function_registry(self) -> 'FunctionRegistry':
        """Function registry for q:function"""
        if 'function_registry' not in self._services:
            from quantum.runtime.function_registry import FunctionRegistry
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
            from quantum.core.features.invocation.src.runtime import InvocationService
            self._services['invocation'] = InvocationService()
            logger.debug("Initialized InvocationService")
        return self._services['invocation']

    @property
    def data_import(self) -> 'DataImportService':
        """Data import service for q:data"""
        if 'data_import' not in self._services:
            from quantum.core.features.data_import.src.runtime import DataImportService
            self._services['data_import'] = DataImportService()
            logger.debug("Initialized DataImportService")
        return self._services['data_import']

    # ==========================================================================
    # AI Services
    # ==========================================================================

    @property
    def llm(self) -> 'LLMService':
        """Ollama-only LLM service, used by q:knowledge and the RAG path.

        It used to be constructed with NO arguments, so it fell back to its own
        default of http://localhost:11434 and ignored llm.base_url entirely —
        while multi_llm (q:llm, q:agent, q:team) honoured it. The two halves of
        the AI stack therefore pointed at DIFFERENT Ollama servers.

        Measured on this machine: config says http://localhost:11434, q:llm
        reached that host and answered, and q:knowledge silently went to
        localhost. In a deployment where only the configured host has models,
        q:llm works and RAG fails, with nothing explaining why.
        """
        if 'llm' not in self._services:
            from quantum.runtime.llm_service import LLMService
            llm_cfg = self._config.get('llm', {}) or {}
            self._services['llm'] = LLMService(
                base_url=self._llm_base_url(),
                default_model=llm_cfg.get('default_model'),
                timeout=llm_cfg.get('timeout', 60),
            )
            logger.debug("Initialized LLMService")
        return self._services['llm']

    @property
    def knowledge(self) -> 'KnowledgeService':
        """Knowledge service for RAG/ChromaDB"""
        if 'knowledge' not in self._services:
            from quantum.runtime.knowledge_service import KnowledgeService
            self._services['knowledge'] = KnowledgeService(self.llm)
            logger.debug("Initialized KnowledgeService")
        return self._services['knowledge']

    def _llm_base_url(self):
        """Where the model server is: QUANTUM_LLM_BASE_URL, then llm.base_url, then the default.

        One answer for every AI tag. They disagreed: q:llm read llm.base_url from
        quantum.config.yaml, while q:agent and q:team built their own service
        with no config and read only the environment. Measured with the repo's
        config (localhost) and QUANTUM_LLM_BASE_URL pointing at another host,
        in one program: q:llm went to the local Ollama and failed with "model
        'phi3' not found", q:agent went to the other host and answered.

        The environment wins over the file, so an operator can point a
        deployment at another server without editing the project.
        """
        llm_cfg = self._config.get('llm', {}) or {}
        return os.environ.get('QUANTUM_LLM_BASE_URL') or llm_cfg.get('base_url')

    @property
    def agent(self):
        """Agent service for q:agent — on this container's model server."""
        if 'agent' not in self._services:
            from quantum.runtime.agent_service import AgentService
            service = AgentService(self.llm)
            # Built by the global get_agent_service() it made its own
            # MultiProviderLLMService with no config; share this container's.
            service._multi_llm_service = self.multi_llm
            self._services['agent'] = service
            logger.debug("Initialized AgentService")
        return self._services['agent']

    @property
    def multi_agent(self):
        """Multi-agent service for q:team — on the same agent service."""
        if 'multi_agent' not in self._services:
            from quantum.runtime.agent_service import MultiAgentService
            self._services['multi_agent'] = MultiAgentService(self.agent)
            logger.debug("Initialized MultiAgentService")
        return self._services['multi_agent']

    # ==========================================================================
    # Communication Services
    # ==========================================================================

    @property
    def message_queue(self) -> 'MessageQueueService':
        """Message queue service for q:message, q:subscribe"""
        if 'message_queue' not in self._services:
            from quantum.runtime.message_queue_service import MessageQueueService
            mq_config = self._config.get('message_queue', {})
            self._services['message_queue'] = MessageQueueService(mq_config)
            logger.debug("Initialized MessageQueueService")
        return self._services['message_queue']

    @property
    def multi_llm(self) -> 'MultiProviderLLMService':
        """Multi-provider LLM service (Ollama, OpenAI, Anthropic, LM Studio).

        q:agent already used this; q:llm was stuck on the Ollama-only
        LLMService, which is why 'multi-provider' was only half true.
        """
        if 'multi_llm' not in self._services:
            from quantum.runtime.llm_providers import MultiProviderLLMService
            llm_cfg = self._config.get('llm', {}) or {}
            self._services['multi_llm'] = MultiProviderLLMService(
                default_endpoint=self._llm_base_url(),
                default_model=llm_cfg.get('default_model'),
                timeout=llm_cfg.get('timeout', 60),
            )
            logger.debug("Initialized MultiProviderLLMService")
        return self._services['multi_llm']

    @property
    def llm_cache(self) -> 'LLMCache':
        """TTL cache for q:llm responses (the `cache` attribute's backing)."""
        if 'llm_cache' not in self._services:
            from quantum.runtime.llm_cache import get_llm_cache
            self._services['llm_cache'] = get_llm_cache()
        return self._services['llm_cache']

    @property
    def config(self) -> Dict[str, Any]:
        """Raw configuration dict (quantum.config.yaml), for executors that
        need policy settings rather than a service."""
        return self._config

    @property
    def python_scripting_enabled(self) -> bool:
        """Whether q:python / q:pyclass / q:pyimport may execute.

        q:python is a full-trust escape hatch: it runs arbitrary Python in
        the server process with no sandbox. That is fine for code the
        application author wrote, and unacceptable for code anything else
        wrote — an LLM-generated or user-submitted template, a component
        from a marketplace, a .q file someone sent you.

        **Desligado por padrão.** Era ligado, o que fazia dele a última
        falha-aberta de configuração do framework: bastava executar um .q
        que você não escreveu para executar o Python dele. Um default
        precisa ser seguro para quem não leu a documentação — e quem usa
        q:python leu, porque teve de escrever a tag.

        Ligue com `security.python_scripting: true` no quantum.config.yaml,
        ou QUANTUM_PYTHON_SCRIPTING=1 no ambiente.
        """
        security = self._config.get('security', {}) or {}
        configured = security.get('python_scripting')
        if configured is not None:
            return configured is not False

        import os
        env = os.environ.get('QUANTUM_PYTHON_SCRIPTING', '').strip().lower()
        return env in ('1', 'true', 'yes', 'on')

    @property
    def websocket(self) -> 'WebSocketService':
        """WebSocket service for q:websocket, q:send, q:close.

        The service existed but was never exposed here, so every
        q:websocket tag raised AttributeError on services.websocket.
        """
        if 'websocket' not in self._services:
            from quantum.runtime.websocket_service import get_websocket_service
            self._services['websocket'] = get_websocket_service()
            logger.debug("Initialized WebSocketService")
        return self._services['websocket']

    @property
    def email(self) -> 'EmailService':
        """Email service for q:mail"""
        if 'email' not in self._services:
            from quantum.runtime.email_service import EmailService
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
            from quantum.runtime.job_executor import JobExecutor
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
            from quantum.runtime.file_upload_service import FileUploadService
            # Every path q:file touches is confined to this root. Configurable
            # via paths.uploads; ./uploads by default, which is where every
            # destination= in this repo already points.
            root = (self._config.get('paths', {}) or {}).get('uploads', 'uploads')
            self._services['file_upload'] = FileUploadService(root=root)
            logger.debug("Initialized FileUploadService")
        return self._services['file_upload']

    # ==========================================================================
    # Developer Experience Services
    # ==========================================================================

    @property
    def logging(self) -> 'LoggingService':
        """Logging service for q:log"""
        if 'logging' not in self._services:
            from quantum.core.features.logging.src import LoggingService
            self._services['logging'] = LoggingService()
            logger.debug("Initialized LoggingService")
        return self._services['logging']

    @property
    def dump(self) -> 'DumpService':
        """Dump service for q:dump"""
        if 'dump' not in self._services:
            from quantum.core.features.dump.src import DumpService
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
            from quantum.runtime.expression_cache import get_expression_cache
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
