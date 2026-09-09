# Runtime Quantum modules
#
# NOTE: Do NOT add eager imports here. This package has circular dependencies
# (web_server -> component -> database_service -> ... -> __init__ -> web_server)
# that cause Python to deadlock during import resolution.
#
# All consumers already import directly from submodules:
#   from runtime.component import ComponentRuntime
#   from runtime.web_server import QuantumWebServer
#
# Lazy accessors are provided below for backward compatibility only.


def __getattr__(name):
    """Lazy import to avoid circular dependency deadlock."""
    if name == 'ComponentRuntime':
        from .component import ComponentRuntime
        return ComponentRuntime
    if name == 'ComponentExecutionError':
        from .component import ComponentExecutionError
        return ComponentExecutionError
    if name == 'QuantumWebServer':
        from .web_server import QuantumWebServer
        return QuantumWebServer
    if name == 'QuantumAPIServer':
        from .api_server import QuantumAPIServer
        return QuantumAPIServer
    raise AttributeError(f"module 'runtime' has no attribute {name!r}")
