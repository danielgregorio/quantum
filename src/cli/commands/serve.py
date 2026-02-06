"""
Quantum CLI - Serve Command

Serve built files with a static file server.
"""

import os
import sys
from pathlib import Path
from typing import Optional
import mimetypes

import click

from cli.utils import get_console, find_project_root


@click.command('serve')
@click.option('--port', '-p', type=int, default=8080, help='Port to serve on')
@click.option('--host', '-h', type=str, default='0.0.0.0', help='Host to bind to')
@click.option('--directory', '-d', type=click.Path(exists=True), default='./dist',
              help='Directory to serve')
@click.option('--cors', is_flag=True, help='Enable CORS headers')
@click.option('--spa', is_flag=True, help='SPA mode - serve index.html for all routes')
@click.option('--quiet', '-q', is_flag=True, help='Quiet mode')
def serve(port: int, host: str, directory: str, cors: bool, spa: bool, quiet: bool):
    """Serve built files with a static file server.

    Serves the contents of the dist directory (or specified directory).

    Examples:

        quantum serve

        quantum serve --port 3000

        quantum serve --directory ./build --cors

        quantum serve --spa  # For single-page applications
    """
    console = get_console(quiet=quiet)

    # Resolve directory path
    serve_dir = Path(directory)
    if not serve_dir.is_absolute():
        project_root = find_project_root() or Path.cwd()
        serve_dir = project_root / directory

    if not serve_dir.exists():
        console.error(f"Directory not found: {serve_dir}")
        console.info("Run 'quantum build' first to create build output")
        raise click.Abort()

    # Check for index.html
    index_file = serve_dir / 'index.html'
    if not index_file.exists():
        # Look for any .html file
        html_files = list(serve_dir.glob('*.html'))
        if html_files:
            console.warning(f"No index.html found, but found: {', '.join(f.name for f in html_files[:3])}")
        else:
            console.warning("No HTML files found in directory")

    url = f"http://{host if host != '0.0.0.0' else 'localhost'}:{port}"

    console.header(
        "Quantum Static Server",
        f"Serving: {serve_dir}"
    )

    console.panel(
        f"[bold]URL:[/bold] {url}\n"
        f"[bold]Directory:[/bold] {serve_dir}\n"
        f"[bold]CORS:[/bold] {'Enabled' if cors else 'Disabled'}\n"
        f"[bold]SPA Mode:[/bold] {'Enabled' if spa else 'Disabled'}",
        title="Server Configuration",
        style="green"
    )

    console.print()
    console.info(f"Server running at {url}")
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    console.print()

    # Start server
    try:
        _run_server(serve_dir, host, port, cors, spa, console)
    except KeyboardInterrupt:
        console.print()
        console.info("Server stopped")
    except Exception as e:
        console.error(f"Server error: {e}")
        raise click.Abort()


def _run_server(
    directory: Path,
    host: str,
    port: int,
    cors: bool,
    spa: bool,
    console
):
    """Run the static file server."""
    from http.server import HTTPServer, SimpleHTTPRequestHandler
    import urllib.parse

    class QuantumHandler(SimpleHTTPRequestHandler):
        """Custom handler with CORS and SPA support."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def log_message(self, format, *args):
            """Log requests to console."""
            message = format % args
            # Parse status code
            parts = message.split('"')
            if len(parts) >= 3:
                status = parts[2].strip().split()[0]
                method_path = parts[1]
                if status.startswith('2'):
                    console.print(f"[green]{status}[/green] {method_path}")
                elif status.startswith('3'):
                    console.print(f"[yellow]{status}[/yellow] {method_path}")
                elif status.startswith('4') or status.startswith('5'):
                    console.print(f"[red]{status}[/red] {method_path}")
                else:
                    console.print(f"{status} {method_path}")
            else:
                console.print(message)

        def end_headers(self):
            """Add CORS headers if enabled."""
            if cors:
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            super().end_headers()

        def do_OPTIONS(self):
            """Handle CORS preflight requests."""
            if cors:
                self.send_response(200)
                self.end_headers()
            else:
                self.send_error(405, "Method Not Allowed")

        def do_GET(self):
            """Handle GET requests with SPA support."""
            if spa:
                # Parse the URL path
                parsed = urllib.parse.urlparse(self.path)
                path = parsed.path

                # Check if file exists
                file_path = directory / path.lstrip('/')

                if not file_path.exists() and not path.startswith('/assets'):
                    # Check if it's a file request (has extension)
                    if '.' not in Path(path).name:
                        # Serve index.html for SPA routes
                        self.path = '/index.html'

            super().do_GET()

        def guess_type(self, path):
            """Guess content type with better defaults."""
            content_type, _ = mimetypes.guess_type(path)
            if content_type:
                return content_type

            # Additional mappings
            ext = Path(path).suffix.lower()
            type_map = {
                '.q': 'text/xml',
                '.yaml': 'text/yaml',
                '.yml': 'text/yaml',
                '.wasm': 'application/wasm',
                '.mjs': 'application/javascript',
            }
            return type_map.get(ext, 'application/octet-stream')

    # Create and start server
    server = HTTPServer((host, port), QuantumHandler)

    try:
        server.serve_forever()
    finally:
        server.server_close()
