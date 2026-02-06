"""
Quantum CLI - Dev Command

Start development server with hot reload.
"""

import os
import sys
import time
import signal
import threading
from pathlib import Path
from typing import Optional, Set, List
from datetime import datetime

import click

from cli.utils import get_console, find_project_root, find_q_files


@click.command('dev')
@click.option('--port', '-p', type=int, default=8080, help='Port to run on')
@click.option('--host', '-h', type=str, default='0.0.0.0', help='Host to bind to')
@click.option('--no-reload', is_flag=True, help='Disable hot reload')
@click.option('--config', '-c', type=click.Path(), default='quantum.config.yaml',
              help='Config file path')
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.option('--quiet', '-q', is_flag=True, help='Quiet mode')
@click.option('--ws-port', type=int, default=35729, help='WebSocket port for hot reload')
@click.pass_context
def dev(ctx, port: int, host: str, no_reload: bool, config: str, debug: bool, quiet: bool, ws_port: int):
    """Start development server with hot reload.

    Watches .q files for changes and automatically reloads.

    Examples:

        quantum dev

        quantum dev --port 3000

        quantum dev --no-reload --debug

        quantum dev --ws-port 35730
    """
    console = get_console(quiet=quiet)

    # Find project root
    project_root = find_project_root()
    if not project_root:
        console.warning("No Quantum project found in current directory.")
        console.info("Creating a minimal dev server for current directory...")
        project_root = Path.cwd()

    config_path = project_root / config

    console.header(
        "Quantum Development Server",
        f"Project: {project_root.name}"
    )

    # Find .q files
    q_files = find_q_files(project_root)
    console.info(f"Found {len(q_files)} .q files")

    # Hot reload manager
    hot_reload_manager = None

    if not no_reload:
        try:
            from cli.hot_reload import HotReloadManager, ReloadType

            # Determine watch paths
            watch_paths = [project_root]

            # Also watch components directory if it exists
            components_dir = project_root / 'components'
            if components_dir.exists():
                watch_paths.append(components_dir)

            # Watch static directory for CSS/JS changes
            static_dir = project_root / 'static'
            if static_dir.exists():
                watch_paths.append(static_dir)

            def on_reload(changes, reload_type):
                """Callback when files change."""
                console.print()
                for change in changes:
                    try:
                        rel_path = change.path.relative_to(project_root)
                    except ValueError:
                        rel_path = change.path

                    timestamp = datetime.now().strftime('%H:%M:%S')
                    console.info(f"[dim]{timestamp}[/dim] {change.change_type}: [path]{rel_path}[/path]")

                if reload_type == ReloadType.CSS:
                    console.info("[bold green]CSS updated[/bold green] (no full reload)")
                else:
                    console.info("[bold blue]Reloading...[/bold blue]")

            hot_reload_manager = HotReloadManager(
                watch_paths=watch_paths,
                extensions=['.q', '.yaml', '.yml', '.css', '.js', '.html'],
                ws_host='localhost',
                ws_port=ws_port,
                debounce_ms=100,
                on_reload=on_reload,
                console=console
            )

            hot_reload_manager.start()

        except ImportError as e:
            console.warning(f"Hot reload dependencies not fully available: {e}")
            console.info("Install with: pip install watchdog websockets")
            hot_reload_manager = None

    # Display server info
    url = f"http://{host if host != '0.0.0.0' else 'localhost'}:{port}"

    info_lines = [
        f"[bold]Server:[/bold] {url}",
        f"[bold]Hot Reload:[/bold] {'Disabled' if no_reload else 'Enabled'}",
    ]

    if not no_reload and hot_reload_manager:
        info_lines.append(f"[bold]WebSocket:[/bold] ws://localhost:{ws_port}")

    info_lines.append(f"[bold]Debug:[/bold] {'On' if debug else 'Off'}")

    console.panel(
        '\n'.join(info_lines),
        title="Development Server",
        style="green"
    )

    # Setup signal handler
    def signal_handler(sig, frame):
        console.print()
        console.info("Shutting down...")
        if hot_reload_manager:
            hot_reload_manager.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Import and start server
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))

        from runtime.web_server import QuantumWebServer, start_server

        console.info(f"Starting server on {url}")
        console.print()
        console.print("[dim]Press Ctrl+C to stop[/dim]")
        console.print()

        # Start the server with hot reload config
        start_server(
            str(config_path),
            port=port,
            hot_reload=not no_reload,
            hot_reload_port=ws_port if not no_reload else None
        )

    except ImportError as e:
        console.error(f"Failed to import Quantum runtime: {e}")
        console.info("Make sure you're in the Quantum project directory")
        if hot_reload_manager:
            hot_reload_manager.stop()
        raise click.Abort()
    except Exception as e:
        console.error(f"Server error: {e}")
        if debug:
            import traceback
            console.print(traceback.format_exc())
        if hot_reload_manager:
            hot_reload_manager.stop()
        raise click.Abort()
    finally:
        if hot_reload_manager:
            hot_reload_manager.stop()
