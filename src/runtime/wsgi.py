"""
Quantum WSGI Entry Point

Factory for creating Flask app instances for Gunicorn deployment.
Loads configuration from environment or config file.
"""

import os
import sys
from pathlib import Path

# Ensure src directory is in path
sys.path.insert(0, str(Path(__file__).parent.parent))

from runtime.web_server import QuantumWebServer


def _run_app_startup():
    """
    Run app-specific startup.py if present.

    This allows apps to initialize databases, apply runtime patches,
    and perform other setup before the web server starts.
    The startup module should define a run() function.
    """
    startup_path = Path('/app/startup.py')
    if not startup_path.exists():
        # Also check current working directory
        startup_path = Path('startup.py')
    if startup_path.exists():
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
# Usage: gunicorn "src.runtime.wsgi:app"
app = create_app()


# Also support: gunicorn "src.runtime.wsgi:create_app()"
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
