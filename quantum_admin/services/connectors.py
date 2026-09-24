"""Services of the Connectors area (admin.connectors.*).

They wrap quantum_admin/backend/connector_service.py, which persists to
settings/connectors.yaml — the same file components/admin/connectors.q edited
in q:python. The screen reimplemented everything, with one serious
difference: the password went into the YAML in plain text; connector_service
encrypts it.

What the screen did and still holds:
  - name, type and provider are required;
  - marking one as default unmarks the others of the same type;
  - when editing, a blank password keeps the current one;
  - testing stores status and last_tested.

No service returns a password, encrypted or not: only `has_password`.
"""

import asyncio

from quantum.services import service
from quantum_admin.services._base import connectors as _service


PROVIDER_NAMES = {
    "postgres": "PostgreSQL", "mysql": "MySQL", "mariadb": "MariaDB", "mongodb": "MongoDB", "sqlite": "SQLite",
    "influxdb": "InfluxDB", "rabbitmq": "RabbitMQ", "redis_queue": "Redis Queue", "kafka": "Kafka",
    "redis": "Redis", "memcached": "Memcached", "s3": "Amazon S3", "minio": "MinIO", "local": "Local filesystem",
    "ollama": "Ollama", "lmstudio": "LM Studio", "anthropic": "Anthropic", "openai": "OpenAI",
    "openrouter": "OpenRouter",
}
# In the order the screen shows the types.
TYPES = (("database", "Database"), ("mq", "Message Queue"), ("cache", "Cache"), ("storage", "Storage"),
         ("ai", "AI"))


class ConnectorError(ValueError):
    """Invalid request for the Connectors area."""


def _public(connector) -> dict:
    data = connector.to_safe_dict()
    data.pop("password_masked", None)       # came from the last 4 characters of the ENCRYPTED text
    data["has_password"] = bool(connector.password)
    data["provider_name"] = PROVIDER_NAMES.get(connector.provider, connector.provider)
    data["type_label"] = dict(TYPES).get(connector.type, connector.type)
    return data


def _valid_provider(provider):
    from quantum_admin.core.connector_service import PROVIDER_CONFIGS
    if provider not in PROVIDER_CONFIGS:
        raise ConnectorError(f"unknown provider {provider!r}; known: {', '.join(sorted(PROVIDER_CONFIGS))}")
    return PROVIDER_CONFIGS[provider]


@service("admin.connectors.providers")
def providers():
    """Known providers, for the form: type, default port, Docker image."""
    from quantum_admin.core.connector_service import PROVIDER_CONFIGS
    return [{"provider": name, "type": getattr(cfg["type"], "value", cfg["type"]),
             "default_port": cfg.get("default_port", 0), "docker_image": cfg.get("docker_image", ""),
             "name": PROVIDER_NAMES.get(name, name)}
            for name, cfg in sorted(PROVIDER_CONFIGS.items())]


@service("admin.connectors.list")
def list_connectors(type: str = "", application_id: int = None):
    """Connectors, filtered by type and/or application (the application's own and the public ones)."""
    items = _service().list_connectors(connector_type=type or None,
                                       application_id=int(application_id) if application_id else None)
    return [_public(c) for c in sorted(items, key=lambda c: (c.type, c.name.lower()))]


@service("admin.connectors.overview")
def overview():
    """The whole Connectors screen: by type, with each type's connectors and providers."""
    all_connectors = list_connectors()
    all_providers = providers()
    return {
        "total": len(all_connectors),
        "connected": sum(1 for c in all_connectors if c["status"] == "connected"),
        "errors": sum(1 for c in all_connectors if c["status"] == "error"),
        "types": [{"type": kind, "label": label,
                   "connectors": [c for c in all_connectors if c["type"] == kind],
                   "providers": [p for p in all_providers if p["type"] == kind]} for kind, label in TYPES],
    }


@service("admin.connectors.get")
def get_connector(connector_id: str):
    connector = _service().get_connector(str(connector_id))
    if connector is None:
        raise ConnectorError(f"no connector with id {connector_id!r}")
    return _public(connector)


@service("admin.connectors.create")
def create_connector(name: str, type: str, provider: str, host: str = "", port: int = 0,
                     database: str = "", username: str = "", password: str = "",
                     scope: str = "public", application_id: int = None, is_default: bool = False):
    if not (name or "").strip() or not (type or "").strip() or not (provider or "").strip():
        raise ConnectorError("name, type and provider are required")
    config = _valid_provider(provider)
    connector = _service().create_connector({
        "name": name.strip(), "type": type.strip(), "provider": provider,
        "host": (host or "").strip() or "localhost", "port": int(port or config.get("default_port", 0)),
        "database": (database or "").strip(), "username": (username or "").strip(),
        # A connector with an application belongs to it: `scope` follows application_id.
        "password": password or "", "scope": "application" if application_id else (scope or "public"),
        "application_id": int(application_id) if application_id else None,
        "is_default": bool(is_default), "docker_image": config.get("docker_image", ""),
    })
    return _public(connector)


@service("admin.connectors.update")
def update_connector(connector_id: str, name: str = None, type: str = None, provider: str = None,
                     host: str = None, port: int = None, database: str = None, username: str = None,
                     password: str = "", is_default: bool = False):
    """Only the given fields change; a blank password keeps the current one."""
    if provider:
        _valid_provider(provider)
    data = {key: value for key, value in {
        "name": name, "type": type, "provider": provider, "host": host, "port": port,
        "database": database, "username": username}.items() if value not in (None, "")}
    if password:
        data["password"] = password
    if is_default:
        data["is_default"] = True
    connector = _service().update_connector(str(connector_id), data)
    if connector is None:
        raise ConnectorError(f"no connector with id {connector_id!r}")
    return _public(connector)


@service("admin.connectors.detach")
def detach_connector(connector_id: str):
    """Detaches the connector from the application: it becomes public (the screen called it detach)."""
    connector = _service().update_connector(str(connector_id), {"application_id": None, "scope": "public"})
    if connector is None:
        raise ConnectorError(f"no connector with id {connector_id!r}")
    return _public(connector)


@service("admin.connectors.delete")
def delete_connector(connector_id: str):
    if not _service().delete_connector(str(connector_id)):
        raise ConnectorError(f"no connector with id {connector_id!r}")
    return {"deleted": str(connector_id)}


@service("admin.connectors.test")
def test_connector(connector_id: str):
    """Really tests it (driver, HTTP or folder, depending on the type) and stores the status."""
    if _service().get_connector(str(connector_id)) is None:
        raise ConnectorError(f"no connector with id {connector_id!r}")
    result = asyncio.run(_service().test_connection(str(connector_id)))
    return {"success": bool(result.get("success")),
            "error": result.get("error"),
            "details": {k: v for k, v in result.items() if k not in ("success", "error")}}


@service("admin.connectors.test_all")
def test_all():
    return {c["id"]: test_connector(c["id"]) for c in list_connectors()}
