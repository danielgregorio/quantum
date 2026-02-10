"""
Settings Service for Quantum Admin
Manages global and project-specific settings with YAML persistence
"""
import os
import yaml
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger(__name__)

# Base paths
SETTINGS_DIR = Path(__file__).parent.parent / "settings"
GLOBAL_SETTINGS_FILE = SETTINGS_DIR / "global.yaml"
PROJECTS_SETTINGS_DIR = SETTINGS_DIR / "projects"


@dataclass
class ServerSettings:
    port: int = 8001
    host: str = "0.0.0.0"
    debug: bool = False
    reload: bool = True


@dataclass
class DockerSettings:
    host: str = ""  # Empty = local, or ssh://user@host
    registry: str = ""
    timeout: int = 30


@dataclass
class EmailSettings:
    enabled: bool = False
    provider: str = "smtp"
    host: str = ""
    port: int = 587
    use_tls: bool = True
    username: str = ""
    password: str = ""
    from_address: str = "noreply@quantum.local"


@dataclass
class SecuritySettings:
    secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24
    allowed_origins: list = field(default_factory=lambda: ["*"])
    rate_limit_enabled: bool = False
    rate_limit_requests: int = 100
    rate_limit_window: int = 60


@dataclass
class DeployEnvironment:
    name: str = ""
    host: str = ""
    user: str = ""
    ssh_key: str = "~/.ssh/id_ed25519"
    deploy_path: str = ""


@dataclass
class DeploymentSettings:
    default_dockerfile: str = "Dockerfile"
    default_port: int = 8080
    health_check_path: str = "/health"
    health_check_timeout: int = 30
    environments: list = field(default_factory=list)


@dataclass
class DatabaseSettings:
    url: str = "sqlite:///quantum_admin.db"
    echo: bool = False


@dataclass
class LoggingSettings:
    level: str = "INFO"
    format: str = "%(asctime)s [%(levelname)s] %(message)s"
    file: str = "logs/quantum_admin.log"


@dataclass
class GlobalSettings:
    server: ServerSettings = field(default_factory=ServerSettings)
    docker: DockerSettings = field(default_factory=DockerSettings)
    email: EmailSettings = field(default_factory=EmailSettings)
    security: SecuritySettings = field(default_factory=SecuritySettings)
    deployment: DeploymentSettings = field(default_factory=DeploymentSettings)
    database: DatabaseSettings = field(default_factory=DatabaseSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)


@dataclass
class ProjectSettings:
    name: str = ""
    description: str = ""
    default_datasource: str = ""
    dockerfile: str = "Dockerfile"
    port: int = 8080
    env_vars: Dict[str, str] = field(default_factory=dict)
    features: Dict[str, bool] = field(default_factory=lambda: {
        "htmx": True,
        "auth": False,
        "email": False
    })
    deployment: Dict[str, str] = field(default_factory=dict)


class SettingsService:
    """Service for managing application settings"""

    def __init__(self):
        self._ensure_directories()
        self._settings_cache: Optional[Dict] = None
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = 5  # seconds

    def _ensure_directories(self):
        """Ensure settings directories exist"""
        SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
        PROJECTS_SETTINGS_DIR.mkdir(parents=True, exist_ok=True)

    def _resolve_env_vars(self, value: Any) -> Any:
        """Resolve ${ENV_VAR} placeholders in values"""
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            return os.environ.get(env_var, value)
        elif isinstance(value, dict):
            return {k: self._resolve_env_vars(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._resolve_env_vars(v) for v in value]
        return value

    # =========================================================================
    # Global Settings
    # =========================================================================

    def get_global_settings(self, resolve_env: bool = True) -> Dict:
        """
        Load global settings from YAML file

        Args:
            resolve_env: Whether to resolve ${ENV_VAR} placeholders

        Returns:
            Dictionary of settings
        """
        # Check cache
        if self._settings_cache and self._cache_time:
            age = (datetime.now() - self._cache_time).total_seconds()
            if age < self._cache_ttl:
                return self._settings_cache

        if not GLOBAL_SETTINGS_FILE.exists():
            logger.warning("Global settings file not found, creating default")
            self._create_default_global_settings()

        try:
            with open(GLOBAL_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = yaml.safe_load(f) or {}

            if resolve_env:
                settings = self._resolve_env_vars(settings)

            # Update cache
            self._settings_cache = settings
            self._cache_time = datetime.now()

            return settings
        except Exception as e:
            logger.error(f"Error loading global settings: {e}")
            return {}

    def update_global_settings(self, updates: Dict) -> Dict:
        """
        Update global settings (partial update)

        Args:
            updates: Dictionary of settings to update (can be nested)

        Returns:
            Updated settings dictionary
        """
        current = self.get_global_settings(resolve_env=False)
        merged = self._deep_merge(current, updates)

        try:
            with open(GLOBAL_SETTINGS_FILE, 'w', encoding='utf-8') as f:
                yaml.dump(merged, f, default_flow_style=False, allow_unicode=True)

            # Invalidate cache
            self._settings_cache = None
            self._cache_time = None

            logger.info("Global settings updated successfully")
            return self.get_global_settings()
        except Exception as e:
            logger.error(f"Error saving global settings: {e}")
            raise

    def get_setting(self, path: str, default: Any = None) -> Any:
        """
        Get a specific setting by dot-notation path

        Args:
            path: Setting path (e.g., "server.port" or "docker.host")
            default: Default value if not found

        Returns:
            Setting value or default
        """
        settings = self.get_global_settings()
        keys = path.split(".")
        value = settings

        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def set_setting(self, path: str, value: Any) -> Dict:
        """
        Set a specific setting by dot-notation path

        Args:
            path: Setting path (e.g., "server.port")
            value: Value to set

        Returns:
            Updated settings
        """
        keys = path.split(".")
        updates = {}
        current = updates

        for i, key in enumerate(keys[:-1]):
            current[key] = {}
            current = current[key]

        current[keys[-1]] = value
        return self.update_global_settings(updates)

    def _create_default_global_settings(self):
        """Create default global settings file"""
        defaults = asdict(GlobalSettings())
        with open(GLOBAL_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(defaults, f, default_flow_style=False, allow_unicode=True)

    # =========================================================================
    # Project Settings
    # =========================================================================

    def get_project_settings(self, project_id: int) -> Dict:
        """Load settings for a specific project"""
        project_file = PROJECTS_SETTINGS_DIR / f"{project_id}.yaml"

        if not project_file.exists():
            return asdict(ProjectSettings())

        try:
            with open(project_file, 'r', encoding='utf-8') as f:
                settings = yaml.safe_load(f) or {}
            return self._resolve_env_vars(settings)
        except Exception as e:
            logger.error(f"Error loading project {project_id} settings: {e}")
            return asdict(ProjectSettings())

    def update_project_settings(self, project_id: int, updates: Dict) -> Dict:
        """Update settings for a specific project"""
        project_file = PROJECTS_SETTINGS_DIR / f"{project_id}.yaml"
        current = self.get_project_settings(project_id)
        merged = self._deep_merge(current, updates)

        try:
            with open(project_file, 'w', encoding='utf-8') as f:
                yaml.dump(merged, f, default_flow_style=False, allow_unicode=True)

            logger.info(f"Project {project_id} settings updated")
            return self.get_project_settings(project_id)
        except Exception as e:
            logger.error(f"Error saving project {project_id} settings: {e}")
            raise

    def delete_project_settings(self, project_id: int) -> bool:
        """Delete settings for a project"""
        project_file = PROJECTS_SETTINGS_DIR / f"{project_id}.yaml"

        if project_file.exists():
            project_file.unlink()
            logger.info(f"Project {project_id} settings deleted")
            return True
        return False

    def list_project_settings(self) -> Dict[int, Dict]:
        """List all project settings"""
        result = {}
        for file in PROJECTS_SETTINGS_DIR.glob("*.yaml"):
            try:
                project_id = int(file.stem)
                result[project_id] = self.get_project_settings(project_id)
            except ValueError:
                continue
        return result

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _deep_merge(self, base: Dict, updates: Dict) -> Dict:
        """Deep merge two dictionaries"""
        result = base.copy()

        for key, value in updates.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    # =========================================================================
    # Connectors
    # =========================================================================

    def get_connectors(self) -> list:
        """
        Get list of available connectors (email, LLM, storage, etc.)

        Returns:
            List of connector dictionaries with name, type, provider, scope
        """
        # Define available connector types
        connectors = [
            {
                "id": "email",
                "name": "Email Service",
                "type": "email",
                "provider": self.get_setting("email.provider", "SMTP"),
                "scope": "private",  # Requires explicit access
                "icon": "envelope"
            },
            {
                "id": "llm_openai",
                "name": "OpenAI API",
                "type": "llm",
                "provider": "OpenAI",
                "scope": "private",
                "icon": "robot"
            },
            {
                "id": "llm_anthropic",
                "name": "Anthropic API",
                "type": "llm",
                "provider": "Anthropic",
                "scope": "private",
                "icon": "brain"
            },
            {
                "id": "storage_s3",
                "name": "AWS S3",
                "type": "storage",
                "provider": "AWS",
                "scope": "private",
                "icon": "cloud"
            },
            {
                "id": "storage_local",
                "name": "Local Storage",
                "type": "storage",
                "provider": "Filesystem",
                "scope": "public",  # Available to all projects
                "icon": "folder"
            },
            {
                "id": "cache_redis",
                "name": "Redis Cache",
                "type": "cache",
                "provider": "Redis",
                "scope": "private",
                "icon": "bolt"
            },
            {
                "id": "queue_rabbitmq",
                "name": "RabbitMQ",
                "type": "queue",
                "provider": "RabbitMQ",
                "scope": "private",
                "icon": "share"
            },
            {
                "id": "webhook",
                "name": "Webhooks",
                "type": "integration",
                "provider": "HTTP",
                "scope": "public",  # Available to all projects
                "icon": "link"
            }
        ]

        return connectors

    def get_project_connectors(self, project_id: int) -> Dict[str, bool]:
        """
        Get which connectors are enabled for a specific project

        Args:
            project_id: Project ID

        Returns:
            Dictionary of connector_id -> enabled status
        """
        settings = self.get_project_settings(project_id)
        return settings.get("connectors", {})

    def update_project_connector(self, project_id: int, connector_id: str, enabled: bool) -> Dict:
        """
        Enable/disable a connector for a project

        Args:
            project_id: Project ID
            connector_id: Connector ID (e.g., "email", "llm_openai")
            enabled: Whether to enable the connector

        Returns:
            Updated project settings
        """
        settings = self.get_project_settings(project_id)
        if "connectors" not in settings:
            settings["connectors"] = {}
        settings["connectors"][connector_id] = enabled
        return self.update_project_settings(project_id, {"connectors": settings["connectors"]})

    def export_settings(self) -> Dict:
        """Export all settings (global + all projects)"""
        return {
            "global": self.get_global_settings(resolve_env=False),
            "projects": self.list_project_settings()
        }

    def import_settings(self, data: Dict) -> bool:
        """Import settings from export data"""
        try:
            if "global" in data:
                self.update_global_settings(data["global"])

            if "projects" in data:
                for project_id, settings in data["projects"].items():
                    self.update_project_settings(int(project_id), settings)

            return True
        except Exception as e:
            logger.error(f"Error importing settings: {e}")
            return False


# Singleton instance
_settings_service = None


def get_settings_service() -> SettingsService:
    """Get singleton instance of SettingsService"""
    global _settings_service
    if _settings_service is None:
        _settings_service = SettingsService()
    return _settings_service
