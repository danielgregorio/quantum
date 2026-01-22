"""
Environment Management System for Quantum Admin
Manages multiple environments (dev, staging, production) with configurations
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


class EnvironmentType(str, Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


@dataclass
class EnvironmentConfig:
    """Environment configuration"""
    name: str
    type: EnvironmentType
    api_url: str
    database_url: str
    redis_url: str
    debug: bool = False
    log_level: str = "INFO"
    allowed_hosts: List[str] = None
    cors_origins: List[str] = None
    max_workers: int = 4
    celery_broker_url: str = ""
    celery_result_backend: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    sentry_dsn: str = ""
    secret_key: str = ""

    def __post_init__(self):
        if self.allowed_hosts is None:
            self.allowed_hosts = ["*"]
        if self.cors_origins is None:
            self.cors_origins = ["*"]


class EnvironmentManager:
    """
    Manage multiple environments and their configurations

    Features:
    - Load/save environment configs
    - Environment switching
    - Configuration validation
    - Secrets management
    - Environment variables export
    """

    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir or os.getenv(
            "QUANTUM_CONFIG_DIR",
            "/opt/quantum/config"
        ))
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.environments: Dict[str, EnvironmentConfig] = {}
        self.current_env: Optional[str] = None

        # Load environments
        self._load_environments()

        # Detect current environment
        self.current_env = os.getenv("QUANTUM_ENV", "development")

    def _load_environments(self):
        """Load all environment configurations"""
        # Load from config files
        for env_file in self.config_dir.glob("*.env.json"):
            try:
                env_name = env_file.stem.replace(".env", "")
                with open(env_file, "r") as f:
                    config_data = json.load(f)

                env_config = EnvironmentConfig(**config_data)
                self.environments[env_name] = env_config

                logger.info(f"Loaded environment: {env_name}")

            except Exception as e:
                logger.error(f"Failed to load {env_file}: {e}")

        # If no environments loaded, create defaults
        if not self.environments:
            self._create_default_environments()

    def _create_default_environments(self):
        """Create default environment configurations"""
        # Development
        dev_config = EnvironmentConfig(
            name="development",
            type=EnvironmentType.DEVELOPMENT,
            api_url="http://localhost:8000",
            database_url="postgresql://quantum:quantum@localhost:5432/quantum_dev",
            redis_url="redis://localhost:6379/0",
            debug=True,
            log_level="DEBUG",
            allowed_hosts=["localhost", "127.0.0.1"],
            cors_origins=["http://localhost:3000", "http://localhost:8000"],
            celery_broker_url="redis://localhost:6379/1",
            celery_result_backend="redis://localhost:6379/2"
        )

        # Staging
        staging_config = EnvironmentConfig(
            name="staging",
            type=EnvironmentType.STAGING,
            api_url="https://staging-api.quantum-admin.example.com",
            database_url="postgresql://quantum:${DB_PASSWORD}@db-staging:5432/quantum_staging",
            redis_url="redis://redis-staging:6379/0",
            debug=False,
            log_level="INFO",
            allowed_hosts=["staging.quantum-admin.example.com"],
            cors_origins=["https://staging.quantum-admin.example.com"],
            celery_broker_url="redis://redis-staging:6379/1",
            celery_result_backend="redis://redis-staging:6379/2"
        )

        # Production
        prod_config = EnvironmentConfig(
            name="production",
            type=EnvironmentType.PRODUCTION,
            api_url="https://api.quantum-admin.example.com",
            database_url="postgresql://quantum:${DB_PASSWORD}@db-prod:5432/quantum_prod",
            redis_url="redis://redis-prod:6379/0",
            debug=False,
            log_level="WARNING",
            allowed_hosts=["quantum-admin.example.com"],
            cors_origins=["https://quantum-admin.example.com"],
            max_workers=8,
            celery_broker_url="redis://redis-prod:6379/1",
            celery_result_backend="redis://redis-prod:6379/2"
        )

        self.environments = {
            "development": dev_config,
            "staging": staging_config,
            "production": prod_config
        }

        # Save defaults
        for env_name, env_config in self.environments.items():
            self.save_environment(env_name)

    def get_environment(self, name: Optional[str] = None) -> Optional[EnvironmentConfig]:
        """
        Get environment configuration

        Args:
            name: Environment name (default: current)

        Returns:
            Environment configuration
        """
        env_name = name or self.current_env
        return self.environments.get(env_name)

    def set_current_environment(self, name: str) -> bool:
        """
        Set current environment

        Args:
            name: Environment name

        Returns:
            True if successful
        """
        if name not in self.environments:
            logger.error(f"Environment not found: {name}")
            return False

        self.current_env = name
        os.environ["QUANTUM_ENV"] = name

        logger.info(f"Switched to environment: {name}")
        return True

    def save_environment(self, name: str) -> bool:
        """
        Save environment configuration to file

        Args:
            name: Environment name

        Returns:
            True if successful
        """
        if name not in self.environments:
            logger.error(f"Environment not found: {name}")
            return False

        try:
            config = self.environments[name]
            config_file = self.config_dir / f"{name}.env.json"

            with open(config_file, "w") as f:
                json.dump(asdict(config), f, indent=2, default=str)

            logger.info(f"Saved environment config: {config_file}")
            return True

        except Exception as e:
            logger.error(f"Failed to save environment {name}: {e}")
            return False

    def create_environment(
        self,
        name: str,
        config: EnvironmentConfig
    ) -> bool:
        """
        Create new environment

        Args:
            name: Environment name
            config: Environment configuration

        Returns:
            True if successful
        """
        if name in self.environments:
            logger.error(f"Environment already exists: {name}")
            return False

        self.environments[name] = config
        return self.save_environment(name)

    def delete_environment(self, name: str) -> bool:
        """
        Delete environment

        Args:
            name: Environment name

        Returns:
            True if successful
        """
        if name not in self.environments:
            logger.error(f"Environment not found: {name}")
            return False

        if name == self.current_env:
            logger.error("Cannot delete current environment")
            return False

        try:
            # Delete config file
            config_file = self.config_dir / f"{name}.env.json"
            if config_file.exists():
                config_file.unlink()

            # Remove from memory
            del self.environments[name]

            logger.info(f"Deleted environment: {name}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete environment {name}: {e}")
            return False

    def list_environments(self) -> List[Dict[str, Any]]:
        """
        List all environments

        Returns:
            List of environment summaries
        """
        return [
            {
                "name": name,
                "type": config.type.value,
                "api_url": config.api_url,
                "debug": config.debug,
                "is_current": name == self.current_env
            }
            for name, config in self.environments.items()
        ]

    def export_env_file(self, name: Optional[str] = None) -> str:
        """
        Export environment as .env file format

        Args:
            name: Environment name (default: current)

        Returns:
            .env file content
        """
        config = self.get_environment(name)
        if not config:
            return ""

        env_lines = [
            f"QUANTUM_ENV={config.name}",
            f"API_URL={config.api_url}",
            f"DATABASE_URL={config.database_url}",
            f"REDIS_URL={config.redis_url}",
            f"DEBUG={str(config.debug).lower()}",
            f"LOG_LEVEL={config.log_level}",
            f"ALLOWED_HOSTS={','.join(config.allowed_hosts)}",
            f"CORS_ORIGINS={','.join(config.cors_origins)}",
            f"MAX_WORKERS={config.max_workers}",
            f"CELERY_BROKER_URL={config.celery_broker_url}",
            f"CELERY_RESULT_BACKEND={config.celery_result_backend}",
        ]

        if config.smtp_host:
            env_lines.extend([
                f"SMTP_HOST={config.smtp_host}",
                f"SMTP_PORT={config.smtp_port}",
                f"SMTP_USER={config.smtp_user}",
                f"SMTP_PASSWORD={config.smtp_password}",
            ])

        if config.sentry_dsn:
            env_lines.append(f"SENTRY_DSN={config.sentry_dsn}")

        if config.secret_key:
            env_lines.append(f"SECRET_KEY={config.secret_key}")

        return "\n".join(env_lines)

    def validate_environment(self, name: str) -> Dict[str, Any]:
        """
        Validate environment configuration

        Args:
            name: Environment name

        Returns:
            Validation result
        """
        config = self.get_environment(name)
        if not config:
            return {
                "valid": False,
                "errors": [f"Environment not found: {name}"]
            }

        errors = []

        # Check required fields
        if not config.api_url:
            errors.append("API URL is required")

        if not config.database_url:
            errors.append("Database URL is required")

        if not config.redis_url:
            errors.append("Redis URL is required")

        # Check production requirements
        if config.type == EnvironmentType.PRODUCTION:
            if config.debug:
                errors.append("Debug mode should be disabled in production")

            if "*" in config.allowed_hosts:
                errors.append("Allowed hosts should be restricted in production")

            if not config.sentry_dsn:
                errors.append("Sentry DSN recommended for production")

            if not config.secret_key or len(config.secret_key) < 32:
                errors.append("Strong secret key required for production")

        return {
            "valid": len(errors) == 0,
            "errors": errors
        }


# Global environment manager instance
_env_manager: Optional[EnvironmentManager] = None


def get_env_manager() -> EnvironmentManager:
    """Get or create environment manager instance"""
    global _env_manager

    if _env_manager is None:
        _env_manager = EnvironmentManager()

    return _env_manager


def get_current_env() -> EnvironmentConfig:
    """Get current environment configuration"""
    manager = get_env_manager()
    config = manager.get_environment()

    if not config:
        raise RuntimeError("No environment configured")

    return config


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    manager = EnvironmentManager()

    # List environments
    print("Available environments:")
    for env in manager.list_environments():
        print(f"  - {env['name']} ({env['type']})")

    # Get current environment
    current = manager.get_environment()
    print(f"\nCurrent environment: {current.name}")
    print(f"  API URL: {current.api_url}")
    print(f"  Debug: {current.debug}")

    # Export .env file
    env_file = manager.export_env_file()
    print(f"\n.env file:\n{env_file}")

    # Validate environment
    validation = manager.validate_environment("production")
    print(f"\nProduction validation: {validation}")
