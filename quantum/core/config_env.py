"""
`${VAR}` in quantum.config.yaml (CFG-1).

    datasources:
      db:
        password: ${DB_PASSWORD}
        host: ${DB_HOST:-localhost}

A config file is the place people put secrets by reference, and every loader
used to read `${DB_PASSWORD}` as the literal password. There were four loaders
(the CLI, the web server, the service container, migrations); they all go
through expand_env now.
"""

import os
import re
from typing import Any

_REFERENCE = re.compile(r'\$\$|\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}')


class ConfigEnvError(ValueError):
    """A `${VAR}` with no value and no default."""


def expand_env(value: Any, path: str = '') -> Any:
    """Replace `${NAME}` and `${NAME:-default}` in every string of a loaded config.

    `$$` is a literal `$`. A variable that is not set and has no default is an
    error naming the variable and where it was used — an empty password or
    database path would otherwise fail much later, somewhere else.
    """
    if isinstance(value, dict):
        return {k: expand_env(v, f'{path}.{k}' if path else str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [expand_env(v, f'{path}[{i}]') for i, v in enumerate(value)]
    if not isinstance(value, str) or '$' not in value:
        return value

    def substitute(match):
        if match.group(0) == '$$':
            return '$'
        name, default = match.group(1), match.group(2)
        if name in os.environ:
            return os.environ[name]
        if default is not None:
            return default
        raise ConfigEnvError(
            f"quantum.config.yaml: {path or 'value'} uses ${{{name}}}, but the "
            f"environment variable {name} is not set. Set it, or give a default: "
            f"${{{name}:-value}}")

    return _REFERENCE.sub(substitute, value)
