"""Reading quantum.config.yaml into the server.

Part of QuantumWebServer (web_server.py), as a mixin."""

import logging
import os
import secrets
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


class ConfigError(Exception):
    """quantum.config.yaml is unreadable or invalid."""


# Top-level sections the engine understands. A typo like `servr:` used to be
# accepted in silence, so the whole section was ignored.
_KNOWN_SECTIONS = {
    'server', 'paths', 'defaults', 'datasources', 'database', 'llm',
    'performance', 'security', 'logging', 'development', 'deploy',
    'components', 'jobs', 'messaging', 'services', 'mail',
}

# The keys each of these sections actually has; anything else is a warning.
_KNOWN_KEYS = {
    'security': {'secret_key', 'login_url', 'python_scripting', 'max_content_length',
                 'xss_protection'},
    'performance': {'cache_templates', 'cache_ttl', 'cache_max_size'},
    'server': {'port', 'host', 'debug', 'reload'},
    'paths': {'components', 'static', 'logs', 'uploads', 'migrations'},
    'logging': {'level', 'format', 'console', 'file', 'filename'},
    'mail': {'host', 'port', 'username', 'password', 'tls', 'from', 'timeout'},
}

_DATASOURCE_KEYS = {'driver', 'type', 'database', 'host', 'port', 'username', 'user', 'password', 'history'}

# (section, key) -> expected python type(s)
_TYPED = {
    ('server', 'port'): int,
    ('server', 'host'): str,
    ('server', 'debug'): bool,
    ('server', 'reload'): bool,
    ('security', 'python_scripting'): bool,
    ('security', 'max_content_length'): int,
    ('llm', 'timeout'): int,
    ('llm', 'base_url'): str,
}


def _validate_config(config: dict, source: str) -> None:
    """Fail fast on a bad config instead of at the first request.

    `port: oitenta` used to be accepted and blew up much later inside
    app.run(); a datasource with no driver failed only when a query ran. The
    boot is where an operator is watching, so that is where it should break.
    """
    log = logging.getLogger('quantum')
    problems = []

    for section, key in _TYPED:
        block = config.get(section)
        if not isinstance(block, dict) or key not in block:
            continue
        value = block[key]
        expected = _TYPED[(section, key)]
        # bool is a subclass of int; check it first so True does not pass as a port
        if expected is int and isinstance(value, bool):
            problems.append(f"{section}.{key}: expected a number, got {value!r}")
        elif not isinstance(value, expected):
            problems.append(
                f"{section}.{key}: expected {expected.__name__}, got "
                f"{type(value).__name__} ({value!r})"
            )

    for name, ds in (config.get('datasources') or {}).items():
        if not isinstance(ds, dict):
            problems.append(f"datasources.{name}: expected a mapping")
            continue
        if not ds.get('driver'):
            problems.append(
                f"datasources.{name}: missing 'driver' (sqlite, postgresql, mysql)"
            )
        if not ds.get('database'):
            problems.append(f"datasources.{name}: missing 'database'")

    login_url = (config.get('security') or {}).get('login_url')
    if login_url is not None and (not isinstance(login_url, str) or not login_url.startswith('/')
                                  or login_url.startswith('//')):
        # A full URL would make every require_auth page an open redirect (AUTH-4).
        problems.append(f"security.login_url: must be a path on this server, like /login; got {login_url!r}")

    if problems:
        bullet = "\n  - "
        raise ConfigError(
            f"{source} has {len(problems)} problem(s):"
            + bullet + bullet.join(problems)
        )

    # Unknown sections are a warning, not an error: a newer config read by an
    # older engine is a real situation, and refusing to boot over it would be
    # worse than saying so.
    # DB-7: a datasource key nothing reads. The blog declared `sqlite_path:`
    # next to `database:`; the engine read `database:` and the sqlite_path was
    # the file with the tables.
    for name, ds in (config.get('datasources') or {}).items():
        ignored = sorted(k for k in (ds or {}) if k not in _DATASOURCE_KEYS) if isinstance(ds, dict) else []
        if ignored:
            log.warning("%s: datasources.%s: %s %s not read — the keys are: %s.",
                        source, name, ', '.join(ignored), 'is' if len(ignored) == 1 else 'are',
                        ', '.join(sorted(_DATASOURCE_KEYS)))

    # Keys nothing reads, in sections that promise protection or speed. A
    # `csrf_protection: true` that does nothing is worse than none: whoever
    # wrote it believes the app is protected.
    for secao, conhecidas in _KNOWN_KEYS.items():
        ignored = sorted(k for k in (config.get(secao) or {}) if k not in conhecidas)
        if ignored:
            log.warning(
                "%s: %s.%s %s not implemented and ignored — nothing enforces %s.",
                source, secao, ', '.join(ignored), 'is' if len(ignored) == 1 else 'are',
                'it' if len(ignored) == 1 else 'them')

    unknown = [k for k in config if k not in _KNOWN_SECTIONS]
    if unknown:
        log.warning(
            "%s has unrecognised top-level section(s): %s. They are ignored — "
            "check for a typo.", source, ', '.join(sorted(unknown))
        )


# Where a project's files go when quantum.config.yaml does not say: relative to
# the folder the server runs in. A module constant so the test suite can point
# them at a temporary folder (tests/conftest.py) — no test writes into the repository.
DEFAULT_PATHS = {
    'components': './components',
    'static': './static',
    'logs': './logs',
}


class ConfigLoading:
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Load configuration from YAML file with sensible defaults.

        Args:
            config_path: Path to config file

        Returns:
            Configuration dictionary
        """
        default_config = {
            'server': {
                'port': 8080,
                # Loopback and no debugger by default. The old defaults were
                # host 0.0.0.0 + debug True, which put the Werkzeug interactive
                # debugger — an eval console — on every network interface: RCE
                # over the LAN from an unauthenticated browser tab, on the very
                # first `quantum start`. Binding wider or turning the debugger
                # on is now an explicit choice in quantum.config.yaml, and
                # start() refuses the dangerous combination (see _guard_debug).
                'host': '127.0.0.1',
                'reload': True,
                'debug': False
            },
            'paths': dict(DEFAULT_PATHS),
            'defaults': {
                'component_type': 'pure',
                'interactive': False,
                'charset': 'utf-8',
                'timeout': 30
            },
            'performance': {
                'cache_templates': True,
                'cache_ttl': 300,
                'cache_max_size': 100
            },
            'security': {
                'xss_protection': True,
                'max_content_length': 16 * 1024 * 1024  # 16 MB
            },
            'logging': {
                'level': 'INFO',
                'console': True,
                'file': True,
                'filename': 'quantum.log'
            }
        }

        # Try to load config file
        config_file = Path(config_path)
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    from quantum.core.config_env import expand_env
                    user_config = expand_env(yaml.safe_load(f) or {})
                    # Deep merge user config with defaults
                    for key, value in user_config.items():
                        if key in default_config and isinstance(default_config[key], dict) and isinstance(value, dict):
                            default_config[key].update(value)
                        else:
                            default_config[key] = value
            except Exception as e:
                # Do NOT fall back to defaults. This used to log a warning and
                # carry on, which meant a single typo in quantum.config.yaml
                # silently discarded the operator's datasources, host binding
                # and security settings and ran the server on defaults — the
                # exact opposite of what they configured, with one WARNING
                # line as the only sign.
                raise ConfigError(
                    f"could not read {config_path}: {e}\n"
                    f"Fix the file, or move it aside to run on defaults "
                    f"deliberately."
                )

        _validate_config(default_config, config_path)
        return default_config

    @staticmethod
    def _dev_secret_key(config_path: str) -> Optional[str]:
        """The development session key, kept in .quantum/dev-secret-key next to the config.

        Only with `debug: true` and no configured key. Without it the key was
        random per process, and the reloader starts a new process on every
        save — every session (a login) was lost each time a file changed.
        """
        key_file = Path(config_path).resolve().parent / '.quantum' / 'dev-secret-key'
        try:
            if key_file.exists():
                key = key_file.read_text(encoding='utf-8').strip()
                if key:
                    return key
            key_file.parent.mkdir(parents=True, exist_ok=True)
            key = secrets.token_hex(32)
            key_file.write_text(key, encoding='utf-8')
            try:
                os.chmod(key_file, 0o600)
            except OSError:
                pass
            return key
        except OSError:
            return None                          # read-only folder: a random key, as before
