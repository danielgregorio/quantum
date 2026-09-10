"""
Declared services: Python functions a .q file calls by name (SVC-1..3).

    # myapp/services.py
    from quantum.services import service

    @service("projects.list")
    def list_projects(status: str = "active"):
        return [...]

    # quantum.config.yaml
    services:
      - myapp.services

    <!-- components/projects.q -->
    <q:invoke name="projects" service="projects.list">
      <q:param name="status" value="active" />
    </q:invoke>

This is the alternative to <q:python> for logic that belongs in Python — file
system, processes, third-party APIs. The Python is written, reviewed and tested
as ordinary Python; the page only names what it calls. A module runs only when
quantum.config.yaml lists it: nothing is discovered or imported implicitly.
"""

import importlib
import threading
from typing import Any, Callable, Dict, Iterable

_registry: Dict[str, Callable[..., Any]] = {}
_loaded_modules: set = set()
_lock = threading.Lock()


class ServiceError(Exception):
    """A declared service could not be registered, loaded or found."""


def service(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register a function under `name` (SVC-1). Returns the function unchanged."""
    if not isinstance(name, str) or not name.strip():
        raise ServiceError("@service needs a name, like @service('projects.list')")

    def register(func: Callable[..., Any]) -> Callable[..., Any]:
        with _lock:
            existing = _registry.get(name)
            if existing is not None and existing is not func and \
                    (existing.__module__, existing.__qualname__) != (func.__module__, func.__qualname__):
                raise ServiceError(
                    f"service '{name}' is already registered by "
                    f"{existing.__module__}.{existing.__qualname__}")
            _registry[name] = func
        return func

    return register


def load(modules: Iterable[str], project_dir: str = None) -> None:
    """Import the modules listed under `services:` in quantum.config.yaml (SVC-2).

    The project folder goes on sys.path first: the `quantum` console script,
    unlike `python -m`, does not put the current directory there, so
    `services: [myapp.services]` could not be imported by `quantum start`.
    """
    import os
    import sys
    if isinstance(modules, str):
        modules = [modules]
    raiz = os.path.abspath(project_dir or os.getcwd())
    if modules and raiz not in sys.path:
        sys.path.insert(0, raiz)
    for module in modules or []:
        if module in _loaded_modules:
            continue
        try:
            ja_importado = module in sys.modules
            modulo = importlib.import_module(module)
            if ja_importado and not any(f.__module__ == module for f in _registry.values()):
                # Imported before the registry was cleared (or before it
                # existed): its @service decorators already ran and would not
                # run again on a plain import.
                importlib.reload(modulo)
        except ImportError as exc:
            raise ServiceError(
                f"quantum.config.yaml lists service module '{module}', which could not "
                f"be imported: {exc}") from exc
        _loaded_modules.add(module)


def get(name: str) -> Callable[..., Any]:
    """The function registered as `name`, or an error listing what exists (SVC-3)."""
    func = _registry.get(name)
    if func is None:
        disponiveis = ', '.join(sorted(_registry)) or 'none'
        raise ServiceError(
            f"no service named '{name}' (registered: {disponiveis}). Declare it with "
            f"@service('{name}') in a module listed under services: in quantum.config.yaml")
    return func


def registered() -> Dict[str, Callable[..., Any]]:
    return dict(_registry)


def _reset() -> None:
    """Tests only."""
    with _lock:
        _registry.clear()
        _loaded_modules.clear()
