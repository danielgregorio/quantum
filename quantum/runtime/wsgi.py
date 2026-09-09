"""
Quantum WSGI Entry Point

Factory for creating Flask app instances for Gunicorn deployment.
Loads configuration from environment or config file.
"""

import os
import sys
from pathlib import Path

# Ensure src directory is in path

from quantum.runtime.web_server import QuantumWebServer


def _run_app_startup():
    """
    Run app-specific startup.py if present.

    This allows apps to initialize databases, apply runtime patches,
    and perform other setup before the web server starts.
    The startup module should define a run() function.

    Note that this executes a Python file from `/app` or from the CURRENT
    DIRECTORY, and that `app = create_app()` at the bottom of this module
    runs it at IMPORT time. Importing this module therefore executes the
    working directory's startup.py. That is the documented Docker convention
    and it is kept, but it is loud now: silently executing a file because it
    happens to sit in the directory you launched from is the kind of thing
    that should say so.
    """
    startup_path = Path('/app/startup.py')
    if not startup_path.exists():
        # Also check current working directory
        startup_path = Path('startup.py')
    if startup_path.exists():
        print(f"[WSGI] executing {startup_path.resolve()}", flush=True)
        import importlib.util
        spec = importlib.util.spec_from_file_location('app_startup', str(startup_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, 'run'):
            mod.run()
            print("[WSGI] App startup.py executed", flush=True)


def create_app(config_path: str = None) -> 'Flask':
    """
    Create and configure the Quantum Flask application.

    This is the factory function used by Gunicorn.

    Args:
        config_path: Path to quantum.config.yaml. If not provided,
                     uses QUANTUM_CONFIG env var or default path.

    Returns:
        Configured Flask application instance
    """
    # Run app startup hooks before creating the server
    _run_app_startup()

    # Determine config path
    if config_path is None:
        config_path = os.environ.get('QUANTUM_CONFIG', '/app/quantum.config.yaml')

    # Check for app-specific config first
    if os.path.exists(config_path):
        server = QuantumWebServer(config_path)
    else:
        # Fall back to default config
        server = QuantumWebServer()

    return server.app


# Create app instance for Gunicorn
#
# Usage: gunicorn "quantum.runtime.wsgi:app"
#
# This said `src.runtime.wsgi:app` — the layout that stopped existing when
# `src/` became the `quantum/` package. The command in the one file whose
# entire purpose is being that command did not import. (web_server.py's
# docstring had the same defect; this file was missed.)
app = create_app()


# Also support: gunicorn "quantum.runtime.wsgi:create_app()"
def get_app():
    """Alternative factory for Gunicorn."""
    return create_app()


if __name__ == '__main__':
    # For local testing
    app.run(
        host=os.environ.get('QUANTUM_HOST', '0.0.0.0'),
        port=int(os.environ.get('QUANTUM_PORT', 8080)),
        debug=os.environ.get('QUANTUM_DEBUG', 'false').lower() == 'true'
    )
