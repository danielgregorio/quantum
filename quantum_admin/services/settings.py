"""Services of the Settings area (admin.settings.*, admin.system.*).

Two different configurations, which the old interface mixed under the same name:

  - the root's quantum.config.yaml: the configuration of the Quantum SERVER
    that `quantum start` uses. components/admin/settings.q edited this one.
  - settings/global.yaml: the settings of the admin itself (the backend's
    settings_service). The FastAPI edited this one.

What settings.q did wrong and changed:
  - it rewrote quantum.config.yaml with yaml.dump, erasing every comment
    (including the security warnings) — now only the value's line changes
    (_yaml_editor, which checks the result before writing);
  - an invalid port silently became 8080 and a write error was swallowed —
    now it is an error;
  - it accepted debug with a host outside the loopback, which the server
    refuses at startup — now it refuses already when saving;
  - it counted parsers and executors in src/core/parsers, a folder that no
    longer exists: it always showed 0 — now it asks the real registries.
"""

import platform
import sys

import yaml

from quantum.services import service
from quantum_admin.services._base import root
from quantum_admin.services._yaml_editor import write_values

LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
LOOPBACK = ("127.0.0.1", "localhost", "::1")


class SettingsError(ValueError):
    """Invalid configuration value."""


def _file():
    return root() / "quantum.config.yaml"


@service("admin.settings.server_config")
def server_config():
    """The root's quantum.config.yaml, as it is in the file (without expanding ${VAR})."""
    file = _file()
    if not file.is_file():
        return {"found": False, "path": str(file)}
    try:
        cfg = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        return {"found": True, "path": str(file), "error": str(exc)}
    server = cfg.get("server") or {}
    return {
        "found": True, "path": str(file),
        "server": {"port": server.get("port", 8080), "host": server.get("host", "127.0.0.1"),
                   "debug": bool(server.get("debug", False)), "reload": bool(server.get("reload", False))},
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
    """Writes the form's values changing only their lines in the file."""
    try:
        port_number = int(port)
    except (TypeError, ValueError):
        raise SettingsError(f"port must be a number, got {port!r}")
    if not 1 <= port_number <= 65535:
        raise SettingsError(f"port must be between 1 and 65535, got {port_number}")
    address = (host or "").strip()
    if not address:
        raise SettingsError("host is required (127.0.0.1 keeps the server local)")
    if debug and address not in LOOPBACK:
        raise SettingsError(
            f"debug cannot be on with host {address}: the debugger runs code for anyone who reaches "
            f"the port, and quantum start refuses it. Use 127.0.0.1, or turn debug off.")
    level = (log_level or "").upper()
    if level not in LOG_LEVELS:
        raise SettingsError(f"log_level must be one of {', '.join(LOG_LEVELS)}")
    ttl = int(cache_ttl)
    if ttl < 0:
        raise SettingsError("cache_ttl cannot be negative")
    write_values(_file(), {
        ("server", "port"): port_number, ("server", "host"): address,
        ("server", "debug"): bool(debug), ("server", "reload"): bool(reload),
        ("performance", "cache_templates"): bool(cache_templates), ("performance", "cache_ttl"): ttl,
        ("logging", "level"): level,
        ("security", "xss_protection"): bool(xss_protection), ("security", "cors_enabled"): bool(cors_enabled),
    })
    return server_config()


_SECRET_KEY = ("password", "secret", "token", "api_key", "apikey", "private_key")


def _mask(value, key=""):
    """Replaces the value of keys that look like secrets with '****' (a ${VAR} reference stays visible)."""
    if isinstance(value, dict):
        return {k: _mask(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [_mask(v, key) for v in value]
    if any(p in key.lower() for p in _SECRET_KEY) and value not in (None, "") \
            and not (isinstance(value, str) and value.startswith("${")):
        return "****"
    return value


@service("admin.settings.global_get")
def global_get():
    """The admin's settings/global.yaml (settings_service), with secrets masked.

    The library returns the values as they are in the file; passwords and
    tokens written there would show up on the page. A ${VAR} reference stays visible.
    """
    from quantum_admin.core.settings_service import get_settings_service
    return _mask(get_settings_service().get_global_settings(resolve_env=False))


@service("admin.system.info")
def system_info():
    """Versions and what the language has registered — measured in the registries, not in folders."""
    from quantum.core.parser import QuantumParser
    from quantum.runtime.component import ComponentRuntime
    try:
        from importlib.metadata import version
        quantum_version = version("quantum-framework")
    except Exception:  # noqa: BLE001 — running from a clone without installing
        quantum_version = None
    parser = QuantumParser()
    runtime = ComponentRuntime(config={})
    return {
        "quantum_version": quantum_version,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "root": str(root()).replace("\\", "/"),
        # only language tags: the registry also keeps the HTML tag names
        "parser_tags": sum(1 for tag in parser._parser_registry.registered_tags
                           if type(parser._parser_registry.get_parser(tag)).__name__ != "HTMLParser"),
        "executors": runtime._executor_registry.executor_count,
    }
