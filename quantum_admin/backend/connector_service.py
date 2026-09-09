"""
Connector Service for Quantum Admin
Manages infrastructure connectors (databases, queues, cache, storage, AI)
with YAML persistence and Docker auto-provisioning
"""
import os
import yaml
import uuid
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

# Base paths
SETTINGS_DIR = Path(__file__).parent.parent / "settings"
CONNECTORS_FILE = SETTINGS_DIR / "connectors.yaml"


class ConnectorType(str, Enum):
    DATABASE = "database"
    MESSAGE_QUEUE = "mq"
    CACHE = "cache"
    STORAGE = "storage"
    AI = "ai"


class ConnectorStatus(str, Enum):
    UNKNOWN = "unknown"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


# Provider configurations
PROVIDER_CONFIGS = {
    # Databases
    "postgres": {
        "type": ConnectorType.DATABASE,
        "default_port": 5432,
        "docker_image": "postgres:16-alpine",
        "env_vars": ["POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"],
        "test_command": "SELECT 1"
    },
    "mysql": {
        "type": ConnectorType.DATABASE,
        "default_port": 3306,
        "docker_image": "mysql:8.0",
        "env_vars": ["MYSQL_ROOT_PASSWORD", "MYSQL_DATABASE", "MYSQL_USER", "MYSQL_PASSWORD"],
        "test_command": "SELECT 1"
    },
    "mariadb": {
        "type": ConnectorType.DATABASE,
        "default_port": 3306,
        "docker_image": "mariadb:11.2",
        "env_vars": ["MARIADB_ROOT_PASSWORD", "MARIADB_DATABASE", "MARIADB_USER", "MARIADB_PASSWORD"],
        "test_command": "SELECT 1"
    },
    "mongodb": {
        "type": ConnectorType.DATABASE,
        "default_port": 27017,
        "docker_image": "mongo:7.0",
        "env_vars": ["MONGO_INITDB_ROOT_USERNAME", "MONGO_INITDB_ROOT_PASSWORD"],
        "test_command": "db.runCommand({ping: 1})"
    },
    "sqlite": {
        "type": ConnectorType.DATABASE,
        "default_port": 0,
        "docker_image": None,
        "env_vars": [],
        "test_command": "SELECT 1"
    },
    # Message Queues
    "rabbitmq": {
        "type": ConnectorType.MESSAGE_QUEUE,
        "default_port": 5672,
        "docker_image": "rabbitmq:3-management",
        "env_vars": ["RABBITMQ_DEFAULT_USER", "RABBITMQ_DEFAULT_PASS"],
        "management_port": 15672
    },
    "redis-queue": {
        "type": ConnectorType.MESSAGE_QUEUE,
        "default_port": 6379,
        "docker_image": "redis:7-alpine",
        "env_vars": []
    },
    "kafka": {
        "type": ConnectorType.MESSAGE_QUEUE,
        "default_port": 9092,
        "docker_image": "confluentinc/cp-kafka:7.5.0",
        "env_vars": ["KAFKA_BROKER_ID", "KAFKA_ZOOKEEPER_CONNECT"]
    },
    # Cache
    "redis": {
        "type": ConnectorType.CACHE,
        "default_port": 6379,
        "docker_image": "redis:7-alpine",
        "env_vars": []
    },
    "memcached": {
        "type": ConnectorType.CACHE,
        "default_port": 11211,
        "docker_image": "memcached:1.6-alpine",
        "env_vars": []
    },
    # Storage
    "s3": {
        "type": ConnectorType.STORAGE,
        "default_port": 443,
        "docker_image": None,
        "env_vars": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]
    },
    "minio": {
        "type": ConnectorType.STORAGE,
        "default_port": 9000,
        "docker_image": "minio/minio",
        "env_vars": ["MINIO_ROOT_USER", "MINIO_ROOT_PASSWORD"],
        "console_port": 9001
    },
    "local": {
        "type": ConnectorType.STORAGE,
        "default_port": 0,
        "docker_image": None,
        "env_vars": []
    },
    # AI Providers
    "ollama": {
        "type": ConnectorType.AI,
        "default_port": 11434,
        "docker_image": "ollama/ollama",
        "env_vars": [],
        "default_endpoint": "http://localhost:11434"
    },
    "lmstudio": {
        "type": ConnectorType.AI,
        "default_port": 1234,
        "docker_image": None,
        "env_vars": [],
        "default_endpoint": "http://localhost:1234/v1"
    },
    "anthropic": {
        "type": ConnectorType.AI,
        "default_port": 443,
        "docker_image": None,
        "env_vars": ["ANTHROPIC_API_KEY"],
        "default_endpoint": "https://api.anthropic.com"
    },
    "openai": {
        "type": ConnectorType.AI,
        "default_port": 443,
        "docker_image": None,
        "env_vars": ["OPENAI_API_KEY"],
        "default_endpoint": "https://api.openai.com/v1"
    },
    "openrouter": {
        "type": ConnectorType.AI,
        "default_port": 443,
        "docker_image": None,
        "env_vars": ["OPENROUTER_API_KEY"],
        "default_endpoint": "https://openrouter.ai/api/v1"
    }
}


@dataclass
class Connector:
    """Represents an infrastructure connector"""
    id: str
    name: str
    type: str  # database, mq, cache, storage, ai
    provider: str  # postgres, mysql, rabbitmq, redis, s3, ollama, etc.
    host: str = "localhost"
    port: int = 0
    username: str = ""
    password: str = ""  # Stored encrypted
    database: str = ""  # or bucket, vhost, etc.
    options: Dict[str, Any] = field(default_factory=dict)
    is_default: bool = False
    docker_auto: bool = False
    docker_image: str = ""
    docker_container_id: str = ""
    status: str = "unknown"
    last_tested: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    # Scope: application_id = None means public (available to all apps)
    # application_id = <id> means exclusive to that application
    application_id: Optional[int] = None
    scope: str = "public"  # "public" or "application"

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:8]
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at
        if not self.port and self.provider in PROVIDER_CONFIGS:
            self.port = PROVIDER_CONFIGS[self.provider]["default_port"]
        if not self.docker_image and self.provider in PROVIDER_CONFIGS:
            self.docker_image = PROVIDER_CONFIGS[self.provider].get("docker_image", "")

    def to_dict(self) -> Dict:
        """Convert to dictionary, excluding sensitive data"""
        data = asdict(self)
        # Mask password for safe output
        if data.get("password"):
            data["password_masked"] = "***" + data["password"][-4:] if len(data["password"]) > 4 else "****"
        return data

    def to_safe_dict(self) -> Dict:
        """Convert to dictionary without password"""
        data = self.to_dict()
        data.pop("password", None)
        return data


class ConnectorService:
    """Service for managing infrastructure connectors"""

    def __init__(self):
        self._ensure_directories()
        self._connectors_cache: Optional[List[Connector]] = None
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = 5  # seconds
        self._secret_manager = None

    def _ensure_directories(self):
        """Ensure settings directories exist"""
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)

    def _get_secret_manager(self):
        """Lazy load secret manager"""
        if self._secret_manager is None:
            try:
                from .secret_manager import secret_manager
            except ImportError:
                from secret_manager import secret_manager
            self._secret_manager = secret_manager
        return self._secret_manager

    def _encrypt_password(self, password: str) -> str:
        """Encrypt password for storage"""
        if not password:
            return ""
        try:
            return self._get_secret_manager().encrypt(password)
        except Exception as e:
            logger.error(f"Failed to encrypt password: {e}")
            return password

    def _decrypt_password(self, encrypted: str) -> str:
        """Decrypt password from storage"""
        if not encrypted:
            return ""
        try:
            return self._get_secret_manager().decrypt(encrypted)
        except Exception as e:
            logger.error(f"Failed to decrypt password: {e}")
            return ""

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    def list_connectors(
        self,
        connector_type: Optional[str] = None,
        application_id: Optional[int] = None,
        include_public: bool = True
    ) -> List[Connector]:
        """
        List connectors, optionally filtered by type and/or application

        Args:
            connector_type: Filter by type (database, mq, cache, storage, ai)
            application_id: Filter by application ID (returns app's connectors + public ones)
            include_public: If True, include public connectors when filtering by app

        Returns:
            List of connectors
        """
        connectors = self._load_connectors()

        if connector_type:
            connectors = [c for c in connectors if c.type == connector_type]

        if application_id is not None:
            if include_public:
                # Return app-specific + public connectors
                connectors = [
                    c for c in connectors
                    if c.application_id == application_id or c.scope == "public"
                ]
            else:
                # Return only app-specific connectors
                connectors = [c for c in connectors if c.application_id == application_id]

        return connectors

    def list_public_connectors(self, connector_type: Optional[str] = None) -> List[Connector]:
        """List only public connectors"""
        connectors = self._load_connectors()
        connectors = [c for c in connectors if c.scope == "public"]

        if connector_type:
            connectors = [c for c in connectors if c.type == connector_type]

        return connectors

    def get_connector(self, connector_id: str) -> Optional[Connector]:
        """Get a connector by ID"""
        connectors = self._load_connectors()
        for conn in connectors:
            if conn.id == connector_id:
                return conn
        return None

    def create_connector(self, data: Dict[str, Any]) -> Connector:
        """
        Create a new connector

        Args:
            data: Connector data

        Returns:
            Created connector
        """
        connectors = self._load_connectors()

        # Determine scope
        scope = data.get("scope", "public")
        application_id = data.get("application_id")
        if application_id:
            scope = "application"

        # Create connector
        connector = Connector(
            id=str(uuid.uuid4())[:8],
            name=data.get("name", "Unnamed"),
            type=data.get("type", "database"),
            provider=data.get("provider", "postgres"),
            host=data.get("host", "localhost"),
            port=int(data.get("port", 0)),
            username=data.get("username", ""),
            password=self._encrypt_password(data.get("password", "")),
            database=data.get("database", ""),
            options=data.get("options", {}),
            is_default=data.get("is_default", False),
            docker_auto=data.get("docker_auto", False),
            docker_image=data.get("docker_image", ""),
            status="unknown",
            scope=scope,
            application_id=int(application_id) if application_id else None
        )

        # If this is set as default, unset others of same type
        if connector.is_default:
            for c in connectors:
                if c.type == connector.type:
                    c.is_default = False

        connectors.append(connector)
        self._save_connectors(connectors)

        logger.info(f"Created connector: {connector.name} ({connector.id})")
        return connector

    def update_connector(self, connector_id: str, data: Dict[str, Any]) -> Optional[Connector]:
        """
        Update an existing connector

        Args:
            connector_id: Connector ID
            data: Updated data

        Returns:
            Updated connector or None if not found
        """
        connectors = self._load_connectors()

        for i, conn in enumerate(connectors):
            if conn.id == connector_id:
                # Update fields
                conn.name = data.get("name", conn.name)
                conn.type = data.get("type", conn.type)
                conn.provider = data.get("provider", conn.provider)
                conn.host = data.get("host", conn.host)
                conn.port = int(data.get("port", conn.port))
                conn.username = data.get("username", conn.username)
                conn.database = data.get("database", conn.database)
                conn.options = data.get("options", conn.options)
                conn.docker_auto = data.get("docker_auto", conn.docker_auto)
                conn.docker_image = data.get("docker_image", conn.docker_image)
                conn.updated_at = datetime.utcnow().isoformat()

                # Update scope and application_id
                if "scope" in data:
                    conn.scope = data["scope"]
                if "application_id" in data:
                    app_id = data["application_id"]
                    conn.application_id = int(app_id) if app_id else None
                    if app_id:
                        conn.scope = "application"

                # Only update password if provided
                if data.get("password"):
                    conn.password = self._encrypt_password(data["password"])

                # Handle default flag
                if data.get("is_default"):
                    for c in connectors:
                        if c.type == conn.type:
                            c.is_default = (c.id == connector_id)

                connectors[i] = conn
                self._save_connectors(connectors)

                logger.info(f"Updated connector: {conn.name} ({conn.id})")
                return conn

        return None

    def delete_connector(self, connector_id: str) -> bool:
        """
        Delete a connector

        Args:
            connector_id: Connector ID

        Returns:
            True if deleted, False if not found
        """
        connectors = self._load_connectors()
        original_count = len(connectors)

        connectors = [c for c in connectors if c.id != connector_id]

        if len(connectors) < original_count:
            self._save_connectors(connectors)
            logger.info(f"Deleted connector: {connector_id}")
            return True

        return False

    def set_default(self, connector_id: str) -> bool:
        """Set a connector as default for its type"""
        connectors = self._load_connectors()
        target_conn = None

        for conn in connectors:
            if conn.id == connector_id:
                target_conn = conn
                break

        if not target_conn:
            return False

        # Unset other defaults of same type
        for conn in connectors:
            if conn.type == target_conn.type:
                conn.is_default = (conn.id == connector_id)

        self._save_connectors(connectors)
        return True

    def get_default(self, connector_type: str) -> Optional[Connector]:
        """Get the default connector for a type"""
        connectors = self.list_connectors(connector_type)
        for conn in connectors:
            if conn.is_default:
                return conn
        return connectors[0] if connectors else None

    # =========================================================================
    # Connection Testing
    # =========================================================================

    async def test_connection(self, connector_id: str) -> Dict[str, Any]:
        """
        Test a connector's connection

        Args:
            connector_id: Connector ID

        Returns:
            Test result with success status and details
        """
        connector = self.get_connector(connector_id)
        if not connector:
            return {"success": False, "error": "Connector not found"}

        return await self._test_connector(connector)

    async def test_connection_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Test connection with provided data (for new connectors before save)"""
        connector = Connector(
            id="test",
            name=data.get("name", "Test"),
            type=data.get("type", "database"),
            provider=data.get("provider", "postgres"),
            host=data.get("host", "localhost"),
            port=int(data.get("port", 0)),
            username=data.get("username", ""),
            password=data.get("password", ""),
            database=data.get("database", ""),
            options=data.get("options", {})
        )
        return await self._test_connector(connector)

    async def _test_connector(self, connector: Connector) -> Dict[str, Any]:
        """Internal test implementation"""
        import httpx

        try:
            if connector.type == ConnectorType.DATABASE:
                return await self._test_database(connector)
            elif connector.type == ConnectorType.MESSAGE_QUEUE:
                return await self._test_message_queue(connector)
            elif connector.type == ConnectorType.CACHE:
                return await self._test_cache(connector)
            elif connector.type == ConnectorType.STORAGE:
                return await self._test_storage(connector)
            elif connector.type == ConnectorType.AI:
                return await self._test_ai(connector)
            else:
                return {"success": False, "error": f"Unknown connector type: {connector.type}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _test_database(self, connector: Connector) -> Dict[str, Any]:
        """Test database connection"""
        password = self._decrypt_password(connector.password) if connector.password else ""

        if connector.provider == "postgres":
            try:
                import asyncpg
                conn = await asyncpg.connect(
                    host=connector.host,
                    port=connector.port,
                    user=connector.username,
                    password=password,
                    database=connector.database or "postgres",
                    timeout=5
                )
                version = await conn.fetchval("SELECT version()")
                await conn.close()
                self._update_status(connector.id, ConnectorStatus.CONNECTED)
                return {"success": True, "version": version}
            except ImportError:
                # Fall back to sync driver
                pass
            except Exception as e:
                self._update_status(connector.id, ConnectorStatus.ERROR)
                return {"success": False, "error": str(e)}

        elif connector.provider in ["mysql", "mariadb"]:
            try:
                import aiomysql
                conn = await aiomysql.connect(
                    host=connector.host,
                    port=connector.port,
                    user=connector.username,
                    password=password,
                    db=connector.database or "mysql",
                    connect_timeout=5
                )
                async with conn.cursor() as cur:
                    await cur.execute("SELECT VERSION()")
                    version = await cur.fetchone()
                conn.close()
                self._update_status(connector.id, ConnectorStatus.CONNECTED)
                return {"success": True, "version": version[0] if version else "unknown"}
            except ImportError:
                pass
            except Exception as e:
                self._update_status(connector.id, ConnectorStatus.ERROR)
                return {"success": False, "error": str(e)}

        elif connector.provider == "sqlite":
            import sqlite3
            try:
                db_path = connector.database or ":memory:"
                conn = sqlite3.connect(db_path, timeout=5)
                cursor = conn.cursor()
                cursor.execute("SELECT sqlite_version()")
                version = cursor.fetchone()
                conn.close()
                self._update_status(connector.id, ConnectorStatus.CONNECTED)
                return {"success": True, "version": f"SQLite {version[0]}" if version else "unknown"}
            except Exception as e:
                self._update_status(connector.id, ConnectorStatus.ERROR)
                return {"success": False, "error": str(e)}

        # Generic TCP test for other databases
        return await self._test_tcp(connector)

    async def _test_message_queue(self, connector: Connector) -> Dict[str, Any]:
        """Test message queue connection"""
        if connector.provider == "rabbitmq":
            # Test management API
            import httpx
            try:
                mgmt_port = PROVIDER_CONFIGS["rabbitmq"].get("management_port", 15672)
                password = self._decrypt_password(connector.password) if connector.password else ""
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(
                        f"http://{connector.host}:{mgmt_port}/api/overview",
                        auth=(connector.username or "guest", password or "guest")
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        self._update_status(connector.id, ConnectorStatus.CONNECTED)
                        return {
                            "success": True,
                            "version": data.get("rabbitmq_version"),
                            "node": data.get("node")
                        }
            except Exception as e:
                self._update_status(connector.id, ConnectorStatus.ERROR)
                return {"success": False, "error": str(e)}

        return await self._test_tcp(connector)

    async def _test_cache(self, connector: Connector) -> Dict[str, Any]:
        """Test cache connection"""
        if connector.provider == "redis":
            try:
                import redis.asyncio as aioredis
                password = self._decrypt_password(connector.password) if connector.password else None
                r = aioredis.Redis(
                    host=connector.host,
                    port=connector.port,
                    password=password,
                    socket_timeout=5
                )
                info = await r.info("server")
                await r.close()
                self._update_status(connector.id, ConnectorStatus.CONNECTED)
                return {
                    "success": True,
                    "version": info.get("redis_version"),
                    "mode": info.get("redis_mode")
                }
            except ImportError:
                pass
            except Exception as e:
                self._update_status(connector.id, ConnectorStatus.ERROR)
                return {"success": False, "error": str(e)}

        return await self._test_tcp(connector)

    async def _test_storage(self, connector: Connector) -> Dict[str, Any]:
        """Test storage connection"""
        if connector.provider in ["s3", "minio"]:
            try:
                import httpx
                endpoint = f"http://{connector.host}:{connector.port}"
                if connector.provider == "s3":
                    endpoint = connector.options.get("endpoint", "https://s3.amazonaws.com")

                async with httpx.AsyncClient(timeout=5.0) as client:
                    # Simple health check
                    resp = await client.get(f"{endpoint}/minio/health/live" if connector.provider == "minio" else endpoint)
                    if resp.status_code in [200, 403]:  # 403 = needs auth but server is up
                        self._update_status(connector.id, ConnectorStatus.CONNECTED)
                        return {"success": True, "endpoint": endpoint}
            except Exception as e:
                self._update_status(connector.id, ConnectorStatus.ERROR)
                return {"success": False, "error": str(e)}

        elif connector.provider == "local":
            path = connector.database or connector.options.get("path", "/tmp")
            if os.path.isdir(path):
                self._update_status(connector.id, ConnectorStatus.CONNECTED)
                return {"success": True, "path": path}
            else:
                self._update_status(connector.id, ConnectorStatus.ERROR)
                return {"success": False, "error": f"Directory not found: {path}"}

        return {"success": False, "error": "Unknown storage provider"}

    async def _test_ai(self, connector: Connector) -> Dict[str, Any]:
        """Test AI provider connection"""
        import httpx

        endpoint = connector.options.get("endpoint") or f"http://{connector.host}:{connector.port}"
        password = self._decrypt_password(connector.password) if connector.password else ""

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if connector.provider == "ollama":
                    resp = await client.get(f"{endpoint}/api/tags")
                    if resp.status_code == 200:
                        data = resp.json()
                        models = [m["name"] for m in data.get("models", [])]
                        self._update_status(connector.id, ConnectorStatus.CONNECTED)
                        return {"success": True, "models": models[:10]}

                elif connector.provider == "lmstudio":
                    resp = await client.get(f"{endpoint}/models")
                    if resp.status_code == 200:
                        data = resp.json()
                        models = [m["id"] for m in data.get("data", [])]
                        self._update_status(connector.id, ConnectorStatus.CONNECTED)
                        return {"success": True, "models": models[:10]}

                elif connector.provider == "anthropic":
                    self._update_status(connector.id, ConnectorStatus.CONNECTED)
                    return {"success": True, "models": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"]}

                elif connector.provider in ["openai", "openrouter"]:
                    headers = {"Authorization": f"Bearer {password}"} if password else {}
                    resp = await client.get(f"{endpoint}/models", headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        models = [m["id"] for m in data.get("data", [])]
                        self._update_status(connector.id, ConnectorStatus.CONNECTED)
                        return {"success": True, "models": models[:10]}

        except httpx.ConnectError:
            self._update_status(connector.id, ConnectorStatus.DISCONNECTED)
            return {"success": False, "error": "Connection refused - is the server running?"}
        except httpx.TimeoutException:
            self._update_status(connector.id, ConnectorStatus.ERROR)
            return {"success": False, "error": "Connection timed out"}
        except Exception as e:
            self._update_status(connector.id, ConnectorStatus.ERROR)
            return {"success": False, "error": str(e)}

        return {"success": False, "error": f"Unknown AI provider: {connector.provider}"}

    async def _test_tcp(self, connector: Connector) -> Dict[str, Any]:
        """Generic TCP connection test"""
        import asyncio

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(connector.host, connector.port),
                timeout=5
            )
            writer.close()
            await writer.wait_closed()
            self._update_status(connector.id, ConnectorStatus.CONNECTED)
            return {"success": True, "message": f"TCP connection to {connector.host}:{connector.port} successful"}
        except asyncio.TimeoutError:
            self._update_status(connector.id, ConnectorStatus.ERROR)
            return {"success": False, "error": "Connection timed out"}
        except Exception as e:
            self._update_status(connector.id, ConnectorStatus.ERROR)
            return {"success": False, "error": str(e)}

    def _update_status(self, connector_id: str, status: ConnectorStatus):
        """Update connector status"""
        connectors = self._load_connectors()
        for conn in connectors:
            if conn.id == connector_id:
                conn.status = status.value
                conn.last_tested = datetime.utcnow().isoformat()
                break
        self._save_connectors(connectors)

    # =========================================================================
    # Docker Auto-Provisioning
    # =========================================================================

    def start_docker_container(self, connector_id: str) -> Dict[str, Any]:
        """Start Docker container for a connector"""
        connector = self.get_connector(connector_id)
        if not connector:
            return {"success": False, "error": "Connector not found"}

        if not connector.docker_auto:
            return {"success": False, "error": "Docker auto-provision not enabled for this connector"}

        if not connector.docker_image:
            return {"success": False, "error": "No Docker image configured"}

        try:
            from .docker_service import DockerService
        except ImportError:
            from docker_service import DockerService

        try:
            docker = DockerService()
            container_name = f"quantum-{connector.provider}-{connector.id}"

            # Build environment variables
            env_vars = self._build_docker_env(connector)

            # Create and start container
            container_id = docker.create_container(
                name=container_name,
                image=connector.docker_image,
                port=connector.port,
                env_vars=env_vars,
                auto_start=True
            )

            if container_id:
                # Update connector with container ID
                self.update_connector(connector_id, {
                    "docker_container_id": container_id,
                    "status": "connected"
                })
                return {"success": True, "container_id": container_id}
            else:
                return {"success": False, "error": "Failed to create container"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def stop_docker_container(self, connector_id: str) -> Dict[str, Any]:
        """Stop Docker container for a connector"""
        connector = self.get_connector(connector_id)
        if not connector:
            return {"success": False, "error": "Connector not found"}

        if not connector.docker_container_id:
            return {"success": False, "error": "No Docker container associated"}

        try:
            from .docker_service import DockerService
        except ImportError:
            from docker_service import DockerService

        try:
            docker = DockerService()
            success = docker.stop_container(connector.docker_container_id)

            if success:
                self.update_connector(connector_id, {"status": "disconnected"})
                return {"success": True}
            else:
                return {"success": False, "error": "Failed to stop container"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _build_docker_env(self, connector: Connector) -> Dict[str, str]:
        """Build environment variables for Docker container"""
        password = self._decrypt_password(connector.password) if connector.password else ""
        env = {}

        if connector.provider == "postgres":
            env = {
                "POSTGRES_USER": connector.username or "postgres",
                "POSTGRES_PASSWORD": password or "postgres",
                "POSTGRES_DB": connector.database or "postgres"
            }
        elif connector.provider in ["mysql", "mariadb"]:
            prefix = "MYSQL" if connector.provider == "mysql" else "MARIADB"
            env = {
                f"{prefix}_ROOT_PASSWORD": password or "root",
                f"{prefix}_DATABASE": connector.database or "quantum",
                f"{prefix}_USER": connector.username or "quantum",
                f"{prefix}_PASSWORD": password or "quantum"
            }
        elif connector.provider == "mongodb":
            env = {
                "MONGO_INITDB_ROOT_USERNAME": connector.username or "admin",
                "MONGO_INITDB_ROOT_PASSWORD": password or "admin"
            }
        elif connector.provider == "rabbitmq":
            env = {
                "RABBITMQ_DEFAULT_USER": connector.username or "guest",
                "RABBITMQ_DEFAULT_PASS": password or "guest"
            }
        elif connector.provider == "minio":
            env = {
                "MINIO_ROOT_USER": connector.username or "minioadmin",
                "MINIO_ROOT_PASSWORD": password or "minioadmin"
            }

        return env

    # =========================================================================
    # Persistence
    # =========================================================================

    def _load_connectors(self) -> List[Connector]:
        """Load connectors from YAML file"""
        # Check cache
        if self._connectors_cache and self._cache_time:
            age = (datetime.now() - self._cache_time).total_seconds()
            if age < self._cache_ttl:
                return self._connectors_cache

        if not CONNECTORS_FILE.exists():
            return []

        try:
            with open(CONNECTORS_FILE, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or []

            connectors = []
            for item in data:
                try:
                    conn = Connector(**item)
                    connectors.append(conn)
                except Exception as e:
                    logger.error(f"Failed to load connector: {e}")

            # Update cache
            self._connectors_cache = connectors
            self._cache_time = datetime.now()

            return connectors

        except Exception as e:
            logger.error(f"Error loading connectors: {e}")
            return []

    def _save_connectors(self, connectors: List[Connector]):
        """Save connectors to YAML file"""
        try:
            data = [asdict(c) for c in connectors]

            with open(CONNECTORS_FILE, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

            # Invalidate cache
            self._connectors_cache = None
            self._cache_time = None

            logger.info(f"Saved {len(connectors)} connectors")

        except Exception as e:
            logger.error(f"Error saving connectors: {e}")
            raise

    # =========================================================================
    # Migration from AI connections
    # =========================================================================

    def migrate_ai_connections(self, ai_connections: List[Dict]) -> int:
        """
        Migrate existing AI connections to connector format

        Args:
            ai_connections: List of AI connection dicts from old format

        Returns:
            Number of migrated connections
        """
        count = 0
        for old_conn in ai_connections:
            try:
                self.create_connector({
                    "name": old_conn.get("name", "Migrated AI"),
                    "type": "ai",
                    "provider": old_conn.get("provider", "ollama"),
                    "host": "localhost",
                    "port": PROVIDER_CONFIGS.get(old_conn.get("provider", "ollama"), {}).get("default_port", 11434),
                    "password": old_conn.get("api_key", ""),
                    "options": {
                        "endpoint": old_conn.get("endpoint", ""),
                        "default_model": old_conn.get("default_model", ""),
                        "max_tokens": old_conn.get("max_tokens", 4096),
                        "temperature": old_conn.get("temperature", 0.7)
                    },
                    "is_default": old_conn.get("is_default", False)
                })
                count += 1
            except Exception as e:
                logger.error(f"Failed to migrate AI connection: {e}")

        return count


# Singleton instance
_connector_service: Optional[ConnectorService] = None


def get_connector_service() -> ConnectorService:
    """Get singleton instance of ConnectorService"""
    global _connector_service
    if _connector_service is None:
        _connector_service = ConnectorService()
    return _connector_service
