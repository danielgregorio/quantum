"""Serviços da área Configurações (admin.settings.*, admin.system.*).

Duas configurações diferentes, que a interface antiga misturava sob o mesmo nome:

  - quantum.config.yaml da raiz: a configuração do SERVIDOR Quantum que
    `quantum start` usa. components/admin/settings.q editava esta.
  - settings/global.yaml: as configurações do próprio admin
    (settings_service do backend). O FastAPI editava esta.

O que settings.q fazia de errado e mudou:
  - regravava quantum.config.yaml com yaml.dump, apagando todos os
    comentários (incluindo os avisos de segurança) — agora só a linha do
    valor muda (_yaml_editor, que confere o resultado antes de gravar);
  - porta inválida virava 8080 em silêncio e erro de escrita era engolido —
    agora é erro;
  - aceitava debug com host fora do loopback, que o servidor recusa ao
    subir — agora recusa já ao salvar;
  - contava parsers e executores em src/core/parsers, pasta que não existe
    mais: mostrava sempre 0 — agora pergunta aos registros reais.
"""

import platform
import sys

import yaml

from quantum.services import service
from quantum_admin.services._base import raiz
from quantum_admin.services._yaml_editor import gravar_valores

NIVEIS_DE_LOG = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
LOOPBACK = ("127.0.0.1", "localhost", "::1")


class SettingsError(ValueError):
    """Valor de configuração inválido."""


def _arquivo():
    return raiz() / "quantum.config.yaml"


@service("admin.settings.server_config")
def server_config():
    """O quantum.config.yaml da raiz, como está no arquivo (sem expandir ${VAR})."""
    arquivo = _arquivo()
    if not arquivo.is_file():
        return {"found": False, "path": str(arquivo)}
    try:
        cfg = yaml.safe_load(arquivo.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return {"found": True, "path": str(arquivo), "error": str(exc)}
    servidor = cfg.get("server") or {}
    return {
        "found": True, "path": str(arquivo),
        "server": {"port": servidor.get("port", 8080), "host": servidor.get("host", "127.0.0.1"),
                   "debug": bool(servidor.get("debug", False)), "reload": bool(servidor.get("reload", False))},
        "paths": {"components": "./components", "static": "./static", "logs": "./logs", **(cfg.get("paths") or {})},
        "performance": {"cache_templates": False, "cache_ttl": 0, "cache_max_size": 0, **(cfg.get("performance") or {})},
        "security": {"xss_protection": False, "cors_enabled": False, "max_content_length": 0,
                     **(cfg.get("security") or {})},
        "llm": cfg.get("llm") or {},
        "logging": {"level": "INFO", "console": False, "file": False, **(cfg.get("logging") or {})},
        "datasources": sorted((cfg.get("datasources") or {}).keys()),
        "services": list(cfg.get("services") or []),
    }


@service("admin.settings.save_server_config")
def save_server_config(port: int, host: str, debug: bool = False, reload: bool = False,
                       cache_templates: bool = False, cache_ttl: int = 300, log_level: str = "INFO",
                       xss_protection: bool = True, cors_enabled: bool = False):
    """Grava os valores do formulário mudando só as linhas deles no arquivo."""
    try:
        porta = int(port)
    except (TypeError, ValueError):
        raise SettingsError(f"port must be a number, got {port!r}")
    if not 1 <= porta <= 65535:
        raise SettingsError(f"port must be between 1 and 65535, got {porta}")
    endereco = (host or "").strip()
    if not endereco:
        raise SettingsError("host is required (127.0.0.1 keeps the server local)")
    if debug and endereco not in LOOPBACK:
        raise SettingsError(
            f"debug cannot be on with host {endereco}: the debugger runs code for anyone who reaches "
            f"the port, and quantum start refuses it. Use 127.0.0.1, or turn debug off.")
    nivel = (log_level or "").upper()
    if nivel not in NIVEIS_DE_LOG:
        raise SettingsError(f"log_level must be one of {', '.join(NIVEIS_DE_LOG)}")
    ttl = int(cache_ttl)
    if ttl < 0:
        raise SettingsError("cache_ttl cannot be negative")
    gravar_valores(_arquivo(), {
        ("server", "port"): porta, ("server", "host"): endereco,
        ("server", "debug"): bool(debug), ("server", "reload"): bool(reload),
        ("performance", "cache_templates"): bool(cache_templates), ("performance", "cache_ttl"): ttl,
        ("logging", "level"): nivel,
        ("security", "xss_protection"): bool(xss_protection), ("security", "cors_enabled"): bool(cors_enabled),
    })
    return server_config()


_CHAVE_SECRETA = ("password", "secret", "token", "api_key", "apikey", "private_key")


def _mascarar(valor, chave=""):
    """Troca o valor de chaves que parecem segredo por '****' (uma referência ${VAR} fica visível)."""
    if isinstance(valor, dict):
        return {k: _mascarar(v, str(k)) for k, v in valor.items()}
    if isinstance(valor, list):
        return [_mascarar(v, chave) for v in valor]
    if any(p in chave.lower() for p in _CHAVE_SECRETA) and valor not in (None, "") \
            and not (isinstance(valor, str) and valor.startswith("${")):
        return "****"
    return valor


@service("admin.settings.global_get")
def global_get():
    """settings/global.yaml do admin (settings_service), com segredos mascarados.

    A biblioteca devolve os valores como estão no arquivo; senhas e tokens
    escritos ali sairiam na página. Uma referência ${VAR} continua visível.
    """
    from quantum_admin.backend.settings_service import get_settings_service
    return _mascarar(get_settings_service().get_global_settings(resolve_env=False))


@service("admin.system.info")
def system_info():
    """Versões e o que a linguagem tem registrado — medido nos registros, não em pastas."""
    from quantum.core.parser import QuantumParser
    from quantum.runtime.component import ComponentRuntime
    try:
        from importlib.metadata import version
        versao = version("quantum-framework")
    except Exception:  # noqa: BLE001 — rodando de um clone sem instalar
        versao = None
    parser = QuantumParser()
    runtime = ComponentRuntime(config={})
    return {
        "quantum_version": versao,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "root": str(raiz()).replace("\\", "/"),
        # só tags da linguagem: o registro também guarda os nomes de tags HTML
        "parser_tags": sum(1 for tag in parser._parser_registry.registered_tags
                           if type(parser._parser_registry.get_parser(tag)).__name__ != "HTMLParser"),
        "executors": runtime._executor_registry.executor_count,
    }
