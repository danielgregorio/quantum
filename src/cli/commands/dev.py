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
from typing import Optional, Set
from datetime import datetime

import click

from cli.utils import get_console, find_project_root, find_q_files


class FileWatcher:
    """Watch files for changes and trigger reload."""

    def __init__(self, paths: list[Path], extensions: list[str], callback):
        self.paths = paths
        self.extensions = extensions
        self.callback = callback
        self.running = False
        self._last_mtimes: dict[Path, float] = {}
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Start watching files."""
        self.running = True
        self._scan_files()
        self._thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop watching files."""
        self.running = False
        if self._thread:
            self._thread.join(timeout=1)

    def _scan_files(self) -> Set[Path]:
        """Scan for all matching files."""
        files = set()
        for path in self.paths:
            if path.is_file():
                files.add(path)
            else:
                for ext in self.extensions:
                    files.update(path.rglob(f'*{ext}'))
        return files

    def _watch_loop(self):
        """Main watch loop."""
        while self.running:
            try:
                files = self._scan_files()
                changed = []

                for file in files:
                    try:
                        mtime = file.stat().st_mtime
                        if file in self._last_mtimes:
                            if mtime > self._last_mtimes[file]:
                                changed.append(file)
                        self._last_mtimes[file] = mtime
                    except (OSError, IOError):
                        pass

                # Clean up deleted files
                current_files = set(files)
                for old_file in list(self._last_mtimes.keys()):
                    if old_file not in current_files:
                        del self._last_mtimes[old_file]

                if changed:
                    self.callback(changed)

            except Exception:
                pass

            time.sleep(0.5)


@click.command('dev')
@click.option('--port', '-p', type=int, default=8080, help='Port to run on')
@click.option('--host', '-h', type=str, default='0.0.0.0', help='Host to bind to')
@click.option('--no-reload', is_flag=True, help='Disable hot reload')
@click.option('--config', '-c', type=click.Path(), default='quantum.config.yaml',
              help='Config file path')
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.option('--quiet', '-q', is_flag=True, help='Quiet mode')
@click.pass_context
def dev(ctx, port: int, host: str, no_reload: bool, config: str, debug: bool, quiet: bool):
    """Start development server with hot reload.

    Watches .q files for changes and automatically reloads.

    Examples:

        quantum dev

        quantum dev --port 3000

        quantum dev --no-reload --debug
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

    # Display server info
    url = f"http://{host if host != '0.0.0.0' else 'localhost'}:{port}"
    console.panel(
        f"[bold]Server:[/bold] {url}\n"
        f"[bold]Hot Reload:[/bold] {'Disabled' if no_reload else 'Enabled'}\n"
        f"[bold]Debug:[/bold] {'On' if debug else 'Off'}",
        title="Development Server",
        style="green"
    )

    # Setup file watcher
    watcher = None
    if not no_reload:
        def on_change(changed_files):
            console.print()
            for f in changed_files:
                rel_path = f.relative_to(project_root) if f.is_relative_to(project_root) else f
                console.info(f"[dim]{datetime.now().strftime('%H:%M:%S')}[/dim] File changed: [path]{rel_path}[/path]")
            console.info("Reloading...")

        watcher = FileWatcher(
            paths=[project_root],
            extensions=['.q', '.yaml', '.yml', '.css', '.js'],
            callback=on_change
        )
        watcher.start()

    # Setup signal handler
    def signal_handler(sig, frame):
        console.print()
        console.info("Shutting down...")
        if watcher:
            watcher.stop()
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

        # Start the server
        start_server(str(config_path), port=port)

    except ImportError as e:
        console.error(f"Failed to import Quantum runtime: {e}")
        console.info("Make sure you're in the Quantum project directory")
        raise click.Abort()
    except Exception as e:
        console.error(f"Server error: {e}")
        if debug:
            import traceback
            console.print(traceback.format_exc())
        raise click.Abort()
    finally:
        if watcher:
            watcher.stop()
