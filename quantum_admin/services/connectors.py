"""Serviços da área Connectors (admin.connectors.*).

Envolvem quantum_admin/backend/connector_service.py, que persiste em
settings/connectors.yaml — o mesmo arquivo que components/admin/connectors.q
editava em q:python. A tela reimplementava tudo, e com uma diferença grave: a
senha ia para o YAML em texto puro; connector_service cifra.

O que a tela fazia e continua valendo:
  - nome, tipo e provider são obrigatórios;
  - marcar como padrão desmarca os outros do mesmo tipo;
  - ao editar, senha em branco mantém a atual;
  - testar grava status e last_tested.

Nenhum serviço devolve senha, cifrada ou não: só `has_password`.
"""

import asyncio

from quantum.services import service
from quantum_admin.services._base import connectors as _servico


NOMES_DE_PROVIDER = {
    "postgres": "PostgreSQL", "mysql": "MySQL", "mariadb": "MariaDB", "mongodb": "MongoDB", "sqlite": "SQLite",
    "influxdb": "InfluxDB", "rabbitmq": "RabbitMQ", "redis_queue": "Redis Queue", "kafka": "Kafka",
    "redis": "Redis", "memcached": "Memcached", "s3": "Amazon S3", "minio": "MinIO", "local": "Local filesystem",
    "ollama": "Ollama", "lmstudio": "LM Studio", "anthropic": "Anthropic", "openai": "OpenAI",
    "openrouter": "OpenRouter",
}
# Na ordem em que a tela mostra os tipos.
TIPOS = (("database", "Database"), ("mq", "Message Queue"), ("cache", "Cache"), ("storage", "Storage"),
         ("ai", "AI"))


class ConnectorError(ValueError):
    """Pedido inválido para a área Connectors."""


def _publico(conector) -> dict:
    dados = conector.to_safe_dict()
    dados.pop("password_masked", None)       # vinha dos 4 últimos caracteres do texto CIFRADO
    dados["has_password"] = bool(conector.password)
    dados["provider_name"] = NOMES_DE_PROVIDER.get(conector.provider, conector.provider)
    dados["type_label"] = dict(TIPOS).get(conector.type, conector.type)
    return dados


def _provider_valido(provider):
    from quantum_admin.backend.connector_service import PROVIDER_CONFIGS
    if provider not in PROVIDER_CONFIGS:
        raise ConnectorError(f"unknown provider {provider!r}; known: {', '.join(sorted(PROVIDER_CONFIGS))}")
    return PROVIDER_CONFIGS[provider]


@service("admin.connectors.providers")
def providers():
    """Providers conhecidos, para o formulário: tipo, porta padrão, imagem Docker."""
    from quantum_admin.backend.connector_service import PROVIDER_CONFIGS
    return [{"provider": nome, "type": getattr(cfg["type"], "value", cfg["type"]),
             "default_port": cfg.get("default_port", 0), "docker_image": cfg.get("docker_image", ""),
             "name": NOMES_DE_PROVIDER.get(nome, nome)}
            for nome, cfg in sorted(PROVIDER_CONFIGS.items())]


@service("admin.connectors.list")
def list_connectors(type: str = "", application_id: int = None):
    """Connectors, filtrados por tipo e/ou aplicação (a da aplicação e os públicos)."""
    lista = _servico().list_connectors(connector_type=type or None,
                                       application_id=int(application_id) if application_id else None)
    return [_publico(c) for c in sorted(lista, key=lambda c: (c.type, c.name.lower()))]


@service("admin.connectors.overview")
def overview():
    """A tela de Connectors inteira: por tipo, com os connectors e os providers de cada um."""
    todos = list_connectors()
    todos_providers = providers()
    return {
        "total": len(todos),
        "connected": sum(1 for c in todos if c["status"] == "connected"),
        "errors": sum(1 for c in todos if c["status"] == "error"),
        "types": [{"type": tipo, "label": rotulo,
                   "connectors": [c for c in todos if c["type"] == tipo],
                   "providers": [p for p in todos_providers if p["type"] == tipo]} for tipo, rotulo in TIPOS],
    }


@service("admin.connectors.get")
def get_connector(connector_id: str):
    conector = _servico().get_connector(str(connector_id))
    if conector is None:
        raise ConnectorError(f"no connector with id {connector_id!r}")
    return _publico(conector)


@service("admin.connectors.create")
def create_connector(name: str, type: str, provider: str, host: str = "", port: int = 0,
                     database: str = "", username: str = "", password: str = "",
                     scope: str = "public", application_id: int = None, is_default: bool = False):
    if not (name or "").strip() or not (type or "").strip() or not (provider or "").strip():
        raise ConnectorError("name, type and provider are required")
    config = _provider_valido(provider)
    conector = _servico().create_connector({
        "name": name.strip(), "type": type.strip(), "provider": provider,
        "host": (host or "").strip() or "localhost", "port": int(port or config.get("default_port", 0)),
        "database": (database or "").strip(), "username": (username or "").strip(),
        # Um connector com aplicação é dela: `scope` segue o application_id.
        "password": password or "", "scope": "application" if application_id else (scope or "public"),
        "application_id": int(application_id) if application_id else None,
        "is_default": bool(is_default), "docker_image": config.get("docker_image", ""),
    })
    return _publico(conector)


@service("admin.connectors.update")
def update_connector(connector_id: str, name: str = None, type: str = None, provider: str = None,
                     host: str = None, port: int = None, database: str = None, username: str = None,
                     password: str = "", is_default: bool = False):
    """Só os campos informados mudam; senha em branco mantém a atual."""
    if provider:
        _provider_valido(provider)
    dados = {chave: valor for chave, valor in {
        "name": name, "type": type, "provider": provider, "host": host, "port": port,
        "database": database, "username": username}.items() if valor not in (None, "")}
    if password:
        dados["password"] = password
    if is_default:
        dados["is_default"] = True
    conector = _servico().update_connector(str(connector_id), dados)
    if conector is None:
        raise ConnectorError(f"no connector with id {connector_id!r}")
    return _publico(conector)


@service("admin.connectors.detach")
def detach_connector(connector_id: str):
    """Desliga o connector da aplicação: ele passa a ser público (a tela chamava de detach)."""
    conector = _servico().update_connector(str(connector_id), {"application_id": None, "scope": "public"})
    if conector is None:
        raise ConnectorError(f"no connector with id {connector_id!r}")
    return _publico(conector)


@service("admin.connectors.delete")
def delete_connector(connector_id: str):
    if not _servico().delete_connector(str(connector_id)):
        raise ConnectorError(f"no connector with id {connector_id!r}")
    return {"deleted": str(connector_id)}


@service("admin.connectors.test")
def test_connector(connector_id: str):
    """Testa de verdade (driver, HTTP ou pasta, conforme o tipo) e grava o status."""
    if _servico().get_connector(str(connector_id)) is None:
        raise ConnectorError(f"no connector with id {connector_id!r}")
    resultado = asyncio.run(_servico().test_connection(str(connector_id)))
    return {"success": bool(resultado.get("success")),
            "error": resultado.get("error"),
            "details": {k: v for k, v in resultado.items() if k not in ("success", "error")}}


@service("admin.connectors.test_all")
def test_all():
    return {c["id"]: test_connector(c["id"]) for c in list_connectors()}
