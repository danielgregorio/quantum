#!/usr/bin/env python3
"""
Quantum Admin - Management CLI
Command-line interface for managing Quantum Admin
"""

import sys
import subprocess
import os
from pathlib import Path
import signal
import time

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich import print as rprint
except ImportError:
    print("Installing required dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rich", "-q"])
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich import print as rprint

console = Console()

# ============================================================================
# CONSTANTS
# ============================================================================

ROOT_DIR = Path(__file__).parent.absolute()
BACKEND_DIR = ROOT_DIR / "quantum_admin" / "backend"
PID_FILE = ROOT_DIR / "quantum.pid"

# ============================================================================
# COMMANDS
# ============================================================================

class QuantumCLI:
    """Quantum Admin CLI manager"""

    def __init__(self):
        self.console = console

    def start(self, port: int = 8000, reload: bool = False):
        """Start Quantum Admin server"""
        if self.is_running():
            console.print("[yellow]⚠ Quantum Admin is already running![/yellow]")
            return

        console.print("[bold cyan]🚀 Starting Quantum Admin...[/bold cyan]")

        cmd = [
            sys.executable,
            "-m", "uvicorn",
            "main:app",
            "--host", "0.0.0.0",
            "--port", str(port)
        ]

        if reload:
            cmd.append("--reload")

        # Start server
        try:
            process = subprocess.Popen(
                cmd,
                cwd=str(BACKEND_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # Save PID
            PID_FILE.write_text(str(process.pid))

            console.print(f"[green]✓ Server started on http://localhost:{port}[/green]")
            console.print(f"[dim]PID: {process.pid}[/dim]")
            console.print("\n[bold]Access points:[/bold]")
            console.print(f"  • Admin UI: http://localhost:{port}/static/login.html")
            console.print(f"  • API Docs: http://localhost:{port}/docs")
            console.print(f"  • WebSocket: ws://localhost:{port}/ws/{{client_id}}")

        except Exception as e:
            console.print(f"[red]✗ Failed to start server: {e}[/red]")

    def stop(self):
        """Stop Quantum Admin server"""
        if not self.is_running():
            console.print("[yellow]⚠ Quantum Admin is not running[/yellow]")
            return

        console.print("[bold cyan]🛑 Stopping Quantum Admin...[/bold cyan]")

        try:
            pid = int(PID_FILE.read_text())
            os.kill(pid, signal.SIGTERM)
            PID_FILE.unlink()
            console.print("[green]✓ Server stopped successfully[/green]")
        except ProcessLookupError:
            console.print("[yellow]⚠ Process not found (already stopped?)[/yellow]")
            if PID_FILE.exists():
                PID_FILE.unlink()
        except Exception as e:
            console.print(f"[red]✗ Failed to stop server: {e}[/red]")

    def restart(self, port: int = 8000):
        """Restart Quantum Admin server"""
        console.print("[bold cyan]🔄 Restarting Quantum Admin...[/bold cyan]")
        self.stop()
        time.sleep(2)
        self.start(port)

    def status(self):
        """Show Quantum Admin status"""
        if self.is_running():
            pid = int(PID_FILE.read_text())
            console.print("[green]✓ Quantum Admin is running[/green]")
            console.print(f"[dim]PID: {pid}[/dim]")

            # Show more details
            self.show_status_table()
        else:
            console.print("[red]✗ Quantum Admin is not running[/red]")

    def logs(self, follow: bool = False):
        """Show Quantum Admin logs"""
        log_file = BACKEND_DIR / "quantum.log"

        if not log_file.exists():
            console.print("[yellow]⚠ No log file found[/yellow]")
            return

        if follow:
            console.print("[bold cyan]📝 Following logs (Ctrl+C to stop)...[/bold cyan]\n")
            subprocess.run(["tail", "-f", str(log_file)])
        else:
            console.print("[bold cyan]📝 Recent logs:[/bold cyan]\n")
            subprocess.run(["tail", "-n", "50", str(log_file)])

    def show_status_table(self):
        """Show detailed status table"""
        table = Table(title="Service Status", show_header=True, header_style="bold cyan")
        table.add_column("Service", style="white")
        table.add_column("Status", style="white")
        table.add_column("Port", style="dim")

        # Check services
        services = [
            ("API Server", self.is_running(), "8000"),
            ("PostgreSQL", self.check_port(5432), "5432"),
            ("Redis", self.check_port(6379), "6379"),
        ]

        for name, running, port in services:
            status = "[green]Running[/green]" if running else "[red]Stopped[/red]"
            table.add_row(name, status, port)

        console.print()
        console.print(table)

    def is_running(self) -> bool:
        """Check if server is running"""
        if not PID_FILE.exists():
            return False

        try:
            pid = int(PID_FILE.read_text())
            os.kill(pid, 0)  # Check if process exists
            return True
        except (ProcessLookupError, ValueError):
            return False

    @staticmethod
    def check_port(port: int) -> bool:
        """Check if port is in use"""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0

    def shell(self):
        """Open interactive Python shell with Quantum context"""
        console.print("[bold cyan]🐍 Opening Quantum Admin shell...[/bold cyan]\n")

        # Create shell script
        shell_script = """
import sys
sys.path.insert(0, '{}')

from quantum_admin.backend.database import SessionLocal, init_db
from quantum_admin.backend import models, crud, schemas

# Initialize
db = SessionLocal()
init_db()

print("Quantum Admin Interactive Shell")
print("Available: db, models, crud, schemas")
print()
""".format(str(ROOT_DIR))

        # Run IPython if available, else python
        try:
            subprocess.run([sys.executable, "-m", "IPython", "-i", "-c", shell_script])
        except:
            subprocess.run([sys.executable, "-i", "-c", shell_script])

    def migrate(self):
        """Run database migrations"""
        console.print("[bold cyan]📊 Running database migrations...[/bold cyan]")

        try:
            result = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                cwd=str(BACKEND_DIR),
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                console.print("[green]✓ Migrations completed successfully[/green]")
            else:
                console.print(f"[red]✗ Migration failed: {result.stderr}[/red]")

        except Exception as e:
            console.print(f"[red]✗ Error: {e}[/red]")

    def test(self):
        """Run tests"""
        console.print("[bold cyan]🧪 Running tests...[/bold cyan]\n")

        subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-v", "--cov=quantum_admin"],
            cwd=str(ROOT_DIR)
        )

    def install_service(self):
        """Install as system service (systemd)"""
        console.print("[bold cyan]📦 Installing Quantum Admin as system service...[/bold cyan]")

        service_content = f"""[Unit]
Description=Quantum Admin Server
After=network.target

[Service]
Type=simple
User={os.environ.get('USER', 'quantum')}
WorkingDirectory={BACKEND_DIR}
ExecStart={sys.executable} -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
"""

        service_file = Path("/etc/systemd/system/quantum-admin.service")

        try:
            # Write service file
            subprocess.run(
                ["sudo", "tee", str(service_file)],
                input=service_content,
                text=True,
                capture_output=True
            )

            # Reload systemd
            subprocess.run(["sudo", "systemctl", "daemon-reload"])
            subprocess.run(["sudo", "systemctl", "enable", "quantum-admin"])

            console.print("[green]✓ Service installed successfully[/green]")
            console.print("\n[bold]Manage with:[/bold]")
            console.print("  sudo systemctl start quantum-admin")
            console.print("  sudo systemctl stop quantum-admin")
            console.print("  sudo systemctl status quantum-admin")

        except Exception as e:
            console.print(f"[red]✗ Failed to install service: {e}[/red]")

    def show_help(self):
        """Show help message"""
        help_text = """
[bold cyan]Quantum Admin - Management CLI[/bold cyan]

[bold]Usage:[/bold]
  quantum-cli.py <command> [options]

[bold]Commands:[/bold]

  [cyan]start[/cyan]           Start the Quantum Admin server
                  Options: --port <port> --reload

  [cyan]stop[/cyan]            Stop the Quantum Admin server

  [cyan]restart[/cyan]         Restart the Quantum Admin server

  [cyan]status[/cyan]          Show server status and service health

  [cyan]logs[/cyan]            Show recent logs
                  Options: --follow (tail -f mode)

  [cyan]shell[/cyan]           Open interactive Python shell with Quantum context

  [cyan]migrate[/cyan]         Run database migrations

  [cyan]test[/cyan]            Run test suite

  [cyan]install-service[/cyan] Install as systemd service (Linux only)

  [cyan]help[/cyan]            Show this help message

[bold]Examples:[/bold]

  # Start server on default port (8000)
  python quantum-cli.py start

  # Start with hot-reload for development
  python quantum-cli.py start --reload

  # Start on custom port
  python quantum-cli.py start --port 9000

  # Check status
  python quantum-cli.py status

  # Follow logs in real-time
  python quantum-cli.py logs --follow

  # Open interactive shell
  python quantum-cli.py shell

[bold]Documentation:[/bold]
  https://docs.quantum.com
"""

        panel = Panel(help_text, border_style="cyan", padding=(1, 2))
        console.print(panel)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point"""
    cli = QuantumCLI()

    if len(sys.argv) < 2:
        cli.show_help()
        return

    command = sys.argv[1]

    # Parse options
    options = {}
    for i, arg in enumerate(sys.argv[2:], start=2):
        if arg.startswith("--"):
            key = arg[2:]
            if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith("--"):
                options[key] = sys.argv[i + 1]
            else:
                options[key] = True

    # Execute command
    try:
        if command == "start":
            port = int(options.get("port", 8000))
            reload = options.get("reload", False)
            cli.start(port, reload)

        elif command == "stop":
            cli.stop()

        elif command == "restart":
            port = int(options.get("port", 8000))
            cli.restart(port)

        elif command == "status":
            cli.status()

        elif command == "logs":
            follow = options.get("follow", False)
            cli.logs(follow)

        elif command == "shell":
            cli.shell()

        elif command == "migrate":
            cli.migrate()

        elif command == "test":
            cli.test()

        elif command == "install-service":
            cli.install_service()

        elif command in ["help", "--help", "-h"]:
            cli.show_help()

        else:
            console.print(f"[red]Unknown command: {command}[/red]")
            console.print("Run 'quantum-cli.py help' for usage information")

    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())


if __name__ == "__main__":
    main()
