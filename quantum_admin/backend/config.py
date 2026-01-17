"""
Quantum Admin - Configuration Management

Loads configuration from environment variables with sensible defaults.
"""

import os
import secrets
from typing import List, Optional
from functools import lru_cache


class Settings:
    """Application settings loaded from environment"""

    # ========================================================================
    # Application
    # ========================================================================
    APP_NAME: str = "Quantum Admin"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("QUANTUM_ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Secret key for JWT, CSRF, etc.
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY",
        # Generate a random key if not set (for development only!)
        secrets.token_urlsafe(32) if os.getenv("QUANTUM_ENV") == "development"
        else None
    )

    if SECRET_KEY is None:
        raise ValueError(
            "SECRET_KEY environment variable must be set in production! "
            "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )

    # ========================================================================
    # Server
    # ========================================================================
    WEB_PORT: int = int(os.getenv("WEB_PORT", "8000"))
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "4"))
    ALLOWED_HOSTS: List[str] = os.getenv("ALLOWED_HOSTS", "*").split(",")
    CORS_ORIGINS: List[str] = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")

    # ========================================================================
    # Security
    # ========================================================================
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    RATE_LIMIT_BURST: int = int(os.getenv("RATE_LIMIT_BURST", "10"))

    # HTTPS/HSTS
    FORCE_HTTPS: bool = os.getenv("FORCE_HTTPS", "false").lower() == "true"
    HSTS_MAX_AGE: int = int(os.getenv("HSTS_MAX_AGE", "31536000"))  # 1 year
    HSTS_INCLUDE_SUBDOMAINS: bool = os.getenv("HSTS_INCLUDE_SUBDOMAINS", "true").lower() == "true"
    HSTS_PRELOAD: bool = os.getenv("HSTS_PRELOAD", "true").lower() == "true"

    # CSRF
    CSRF_ENABLED: bool = os.getenv("CSRF_ENABLED", "true").lower() == "true"
    CSRF_COOKIE_NAME: str = os.getenv("CSRF_COOKIE_NAME", "csrf_token")
    CSRF_HEADER_NAME: str = os.getenv("CSRF_HEADER_NAME", "X-CSRF-Token")

    # CSP (Content Security Policy)
    CSP_ENABLED: bool = os.getenv("CSP_ENABLED", "true").lower() == "true"

    # ========================================================================
    # Database
    # ========================================================================
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://quantum:quantum_dev@localhost:5432/quantum"
    )
    DB_ECHO: bool = DEBUG and os.getenv("DB_ECHO", "false").lower() == "true"

    # ========================================================================
    # Redis
    # ========================================================================
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD") or None
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PREFIX: str = os.getenv("REDIS_PREFIX", "quantum:")

    @property
    def REDIS_URL(self) -> str:
        """Build Redis connection URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ========================================================================
    # Celery
    # ========================================================================
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
    CELERY_WORKERS: int = int(os.getenv("CELERY_WORKERS", "4"))

    # ========================================================================
    # JWT Authentication
    # ========================================================================
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # ========================================================================
    # AI/LLM
    # ========================================================================
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "llama2")

    # ========================================================================
    # Docker
    # ========================================================================
    DOCKER_HOST: Optional[str] = os.getenv("DOCKER_HOST")  # None = use default socket

    # ========================================================================
    # Monitoring
    # ========================================================================
    SENTRY_DSN: Optional[str] = os.getenv("SENTRY_DSN") or None
    PROMETHEUS_PORT: int = int(os.getenv("PROMETHEUS_PORT", "9090"))
    PROMETHEUS_ENABLED: bool = os.getenv("PROMETHEUS_ENABLED", "true").lower() == "true"

    # ========================================================================
    # Email
    # ========================================================================
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: Optional[str] = os.getenv("SMTP_USER")
    SMTP_PASSWORD: Optional[str] = os.getenv("SMTP_PASSWORD")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "noreply@quantum-admin.com")

    # ========================================================================
    # Webhooks
    # ========================================================================
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", secrets.token_urlsafe(32))
    AUTO_DEPLOY_BRANCHES: List[str] = os.getenv("AUTO_DEPLOY_BRANCHES", "main,staging,develop").split(",")
    DEPLOYMENT_DIR: str = os.getenv("DEPLOYMENT_DIR", "/opt/quantum")

    # ========================================================================
    # Methods
    # ========================================================================
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT == "development"

    @property
    def is_testing(self) -> bool:
        """Check if running in test mode"""
        return os.getenv("TESTING", "false").lower() == "true"

    def get_database_url(self) -> str:
        """Get database URL (with test database override)"""
        if self.is_testing:
            return os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")
        return self.DATABASE_URL


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Settings instance
    """
    return Settings()


# Convenience instance
settings = get_settings()


# ============================================================================
# Validation
# ============================================================================

def validate_settings():
    """
    Validate critical settings.

    Raises:
        ValueError: If critical settings are missing or invalid
    """
    if settings.is_production:
        # Production-specific validations
        if settings.SECRET_KEY == "your-secret-key-here-change-in-production":
            raise ValueError("SECRET_KEY must be changed in production!")

        if settings.DEBUG:
            raise ValueError("DEBUG must be False in production!")

        if "*" in settings.ALLOWED_HOSTS:
            raise ValueError("ALLOWED_HOSTS cannot be '*' in production!")

        if not settings.FORCE_HTTPS:
            import warnings
            warnings.warn("FORCE_HTTPS should be enabled in production!")

        if not settings.DATABASE_URL.startswith("postgresql://"):
            import warnings
            warnings.warn("Using non-PostgreSQL database in production is not recommended!")


# Validate on import
if not settings.is_testing:
    try:
        validate_settings()
    except ValueError as e:
        if settings.is_production:
            raise
        else:
            import warnings
            warnings.warn(f"Configuration warning: {e}")


__all__ = ["settings", "get_settings", "validate_settings", "Settings"]
