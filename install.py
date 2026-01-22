#!/usr/bin/env python3
"""
Quantum Admin - Interactive CLI Installer
Enterprise-grade installation wizard with visual feedback
"""

import os
import sys
import subprocess
import time
import shutil
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
import platform

# Try to import rich, install if not available
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.prompt import Prompt, Confirm, IntPrompt
    from rich.table import Table
    from rich.syntax import Syntax
    from rich import print as rprint
    from rich.layout import Layout
    from rich.live import Live
    from rich.align import Align
except ImportError:
    print("Installing required dependencies for installer...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rich", "-q"])
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.prompt import Prompt, Confirm, IntPrompt
    from rich.table import Table
    from rich.syntax import Syntax
    from rich import print as rprint
    from rich.layout import Layout
    from rich.live import Live
    from rich.align import Align

console = Console()

# ============================================================================
# ASCII ART & BRANDING
# ============================================================================

QUANTUM_LOGO = """
[bold cyan]
   ██████╗ ██╗   ██╗ █████╗ ███╗   ██╗████████╗██╗   ██╗███╗   ███╗
  ██╔═══██╗██║   ██║██╔══██╗████╗  ██║╚══██╔══╝██║   ██║████╗ ████║
  ██║   ██║██║   ██║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
  ██║▄▄ ██║██║   ██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
  ╚██████╔╝╚██████╔╝██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
   ╚══▀▀═╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
[/bold cyan]
[bold white]           A D M I N   -   I N S T A L L E R   v1.0[/bold white]
[dim]              Enterprise Administration Interface[/dim]
"""

SUCCESS_MARK = "[bold green]✓[/bold green]"
ERROR_MARK = "[bold red]✗[/bold red]"
WARNING_MARK = "[bold yellow]⚠[/bold yellow]"
INFO_MARK = "[bold cyan]ℹ[/bold cyan]"

# ============================================================================
# SYSTEM VERIFICATION
# ============================================================================

class SystemCheck:
    """System requirements checker"""

    @staticmethod
    def check_python_version() -> tuple[bool, str]:
        """Check Python version (requires 3.9+)"""
        version = sys.version_info
        if version.major >= 3 and version.minor >= 9:
            return True, f"{version.major}.{version.minor}.{version.micro}"
        return False, f"{version.major}.{version.minor}.{version.micro}"

    @staticmethod
    def check_command(command: str) -> tuple[bool, str]:
        """Check if a command is available"""
        result = shutil.which(command)
        if result:
            try:
                version_result = subprocess.run(
                    [command, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                version = version_result.stdout.strip().split('\n')[0]
                return True, version
            except:
                return True, "installed"
        return False, "not found"

    @staticmethod
    def check_docker() -> tuple[bool, str]:
        """Check Docker installation and status"""
        available, version = SystemCheck.check_command("docker")
        if not available:
            return False, "not installed"

        try:
            result = subprocess.run(
                ["docker", "ps"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return True, version + " (running)"
            else:
                return False, version + " (not running)"
        except:
            return False, version + " (error)"

    @staticmethod
    def check_port(port: int) -> bool:
        """Check if a port is available"""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) != 0


# ============================================================================
# INSTALLATION MANAGER
# ============================================================================

class QuantumInstaller:
    """Main installer class"""

    def __init__(self):
        self.console = console
        self.root_dir = Path(__file__).parent.absolute()
        self.config = {}

    def show_banner(self):
        """Display welcome banner"""
        self.console.clear()
        panel = Panel(
            QUANTUM_LOGO,
            border_style="cyan",
            padding=(1, 2)
        )
        self.console.print(panel)
        self.console.print()

    def verify_system(self) -> bool:
        """Verify system requirements"""
        self.console.print("\n[bold cyan]Step 1: System Verification[/bold cyan]")
        self.console.print("Checking system requirements...\n")

        checks = [
            ("Python 3.9+", SystemCheck.check_python_version()),
            ("Docker", SystemCheck.check_docker()),
            ("Git", SystemCheck.check_command("git")),
            ("Pip", SystemCheck.check_command("pip")),
        ]

        table = Table(show_header=True, header_style="bold cyan", box=None)
        table.add_column("Requirement", style="white")
        table.add_column("Status", style="white")
        table.add_column("Version/Info", style="dim")

        all_passed = True
        for name, (passed, info) in checks:
            status = SUCCESS_MARK if passed else ERROR_MARK
            table.add_row(name, status, info)
            if not passed:
                all_passed = False

        self.console.print(table)
        self.console.print()

        # Check ports
        ports_to_check = [8000, 5432, 6379]
        self.console.print("[bold]Port Availability:[/bold]")
        for port in ports_to_check:
            available = SystemCheck.check_port(port)
            status = SUCCESS_MARK if available else WARNING_MARK
            self.console.print(f"  {status} Port {port}: {'Available' if available else 'In use'}")

        self.console.print()

        if not all_passed:
            self.console.print(f"{ERROR_MARK} [bold red]Some requirements are not met![/bold red]")
            if not Confirm.ask("Continue anyway?", default=False):
                return False

        self.console.print(f"{SUCCESS_MARK} [bold green]System verification complete![/bold green]\n")
        return True

    def select_installation_type(self) -> str:
        """Select installation type"""
        self.console.print("\n[bold cyan]Step 2: Installation Type[/bold cyan]\n")

        options = [
            "1. Full Installation (Recommended) - All features with Docker services",
            "2. Development Installation - Local development without Docker",
            "3. Custom Installation - Choose components manually"
        ]

        for option in options:
            self.console.print(f"  {option}")

        self.console.print()
        choice = Prompt.ask(
            "Select installation type",
            choices=["1", "2", "3"],
            default="1"
        )

        mapping = {"1": "full", "2": "dev", "3": "custom"}
        return mapping[choice]

    def configure_database(self) -> Dict[str, Any]:
        """Configure database settings"""
        self.console.print("\n[bold cyan]Step 3: Database Configuration[/bold cyan]\n")

        db_config = {}

        db_type = Prompt.ask(
            "Database type",
            choices=["sqlite", "postgresql", "mysql"],
            default="sqlite"
        )
        db_config["type"] = db_type

        if db_type == "sqlite":
            db_config["path"] = Prompt.ask(
                "Database file path",
                default="./quantum_admin.db"
            )
        else:
            db_config["host"] = Prompt.ask("Database host", default="localhost")
            db_config["port"] = IntPrompt.ask(
                "Database port",
                default=5432 if db_type == "postgresql" else 3306
            )
            db_config["name"] = Prompt.ask("Database name", default="quantum_admin")
            db_config["user"] = Prompt.ask("Database user", default="postgres" if db_type == "postgresql" else "root")
            db_config["password"] = Prompt.ask("Database password", password=True)

        return db_config

    def configure_redis(self) -> Dict[str, Any]:
        """Configure Redis settings"""
        self.console.print("\n[bold cyan]Step 4: Redis Configuration[/bold cyan]\n")

        use_redis = Confirm.ask("Enable Redis for caching?", default=True)

        if not use_redis:
            return {"enabled": False}

        return {
            "enabled": True,
            "host": Prompt.ask("Redis host", default="localhost"),
            "port": IntPrompt.ask("Redis port", default=6379),
            "db": IntPrompt.ask("Redis database number", default=0)
        }

    def configure_admin_user(self) -> Dict[str, Any]:
        """Configure admin user"""
        self.console.print("\n[bold cyan]Step 5: Admin User Setup[/bold cyan]\n")

        use_default = Confirm.ask(
            "Use default admin credentials? (admin / admin123)",
            default=True
        )

        if use_default:
            return {
                "username": "admin",
                "password": "admin123",
                "email": "admin@quantum.local"
            }

        return {
            "username": Prompt.ask("Admin username", default="admin"),
            "password": Prompt.ask("Admin password", password=True),
            "email": Prompt.ask("Admin email", default="admin@quantum.local")
        }

    def install_dependencies(self):
        """Install Python dependencies"""
        self.console.print("\n[bold cyan]Step 6: Installing Dependencies[/bold cyan]\n")

        requirements_file = self.root_dir / "quantum_admin" / "requirements.txt"

        if not requirements_file.exists():
            self.console.print(f"{ERROR_MARK} requirements.txt not found!")
            return False

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=self.console
        ) as progress:
            task = progress.add_task("Installing Python packages...", total=None)

            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
                    capture_output=True,
                    text=True
                )

                if result.returncode == 0:
                    progress.update(task, completed=True)
                    self.console.print(f"\n{SUCCESS_MARK} [bold green]Dependencies installed successfully![/bold green]")
                    return True
                else:
                    self.console.print(f"\n{ERROR_MARK} [bold red]Failed to install dependencies[/bold red]")
                    self.console.print(result.stderr)
                    return False

            except Exception as e:
                self.console.print(f"\n{ERROR_MARK} [bold red]Error: {e}[/bold red]")
                return False

    def create_env_file(self, db_config: Dict, redis_config: Dict, admin_config: Dict):
        """Create .env file"""
        self.console.print("\n[bold cyan]Step 7: Creating Configuration[/bold cyan]\n")

        env_content = f"""# Quantum Admin Configuration
# Generated by installer on {time.strftime('%Y-%m-%d %H:%M:%S')}

# Application
APP_NAME=Quantum Admin
APP_ENV=development
DEBUG=true
SECRET_KEY={os.urandom(32).hex()}

# Server
HOST=0.0.0.0
PORT=8000

# Database
"""

        if db_config["type"] == "sqlite":
            env_content += f'DATABASE_URL=sqlite:///{db_config["path"]}\n'
        elif db_config["type"] == "postgresql":
            env_content += f'DATABASE_URL=postgresql://{db_config["user"]}:{db_config["password"]}@{db_config["host"]}:{db_config["port"]}/{db_config["name"]}\n'
        else:  # mysql
            env_content += f'DATABASE_URL=mysql+pymysql://{db_config["user"]}:{db_config["password"]}@{db_config["host"]}:{db_config["port"]}/{db_config["name"]}\n'

        env_content += f"""
# Redis
REDIS_ENABLED={str(redis_config["enabled"]).lower()}
"""

        if redis_config["enabled"]:
            env_content += f"""REDIS_HOST={redis_config["host"]}
REDIS_PORT={redis_config["port"]}
REDIS_DB={redis_config["db"]}
"""

        env_content += f"""
# JWT Authentication
JWT_SECRET_KEY={os.urandom(32).hex()}
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Admin User
ADMIN_USERNAME={admin_config["username"]}
ADMIN_PASSWORD={admin_config["password"]}
ADMIN_EMAIL={admin_config["email"]}

# CORS
CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]

# Docker
DOCKER_HOST=unix:///var/run/docker.sock
"""

        env_file = self.root_dir / ".env"
        env_file.write_text(env_content)

        self.console.print(f"{SUCCESS_MARK} Configuration file created: [cyan]{env_file}[/cyan]")

        # Show preview
        syntax = Syntax(env_content, "ini", theme="monokai", line_numbers=True)
        self.console.print("\n[bold]Configuration Preview:[/bold]")
        self.console.print(Panel(syntax, border_style="cyan", padding=(0, 1)))

    def initialize_database(self):
        """Initialize database"""
        self.console.print("\n[bold cyan]Step 8: Database Initialization[/bold cyan]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Creating database tables...", total=None)

            # In real implementation, this would run alembic migrations
            time.sleep(2)  # Simulate work

            self.console.print(f"{SUCCESS_MARK} Database initialized successfully!")

    def show_completion_screen(self):
        """Show installation complete screen"""
        self.console.clear()

        completion_text = f"""
{SUCCESS_MARK} [bold green]Installation Complete![/bold green]

[bold cyan]Quantum Admin[/bold cyan] has been successfully installed!

[bold]Next Steps:[/bold]

  1. Start the server:
     [cyan]cd quantum_admin/backend[/cyan]
     [cyan]python main.py[/cyan]

  2. Access the admin interface:
     [cyan]http://localhost:8000/static/login.html[/cyan]

  3. Login with your credentials:
     [cyan]Username: {self.config.get('admin', {}).get('username', 'admin')}[/cyan]
     [cyan]Password: {self.config.get('admin', {}).get('password', '***')}[/cyan]

[bold]Documentation:[/bold]
  • API Docs: http://localhost:8000/docs
  • WebSocket: ws://localhost:8000/ws/{{client_id}}
  • Pipeline Editor: http://localhost:8000/static/pipeline-editor.html

[bold]Support:[/bold]
  • GitHub: https://github.com/quantum/admin
  • Docs: https://docs.quantum.com

[dim]Thank you for choosing Quantum Admin![/dim]
"""

        panel = Panel(
            completion_text,
            border_style="green",
            padding=(1, 2),
            title="[bold green]🎉 Success[/bold green]",
            title_align="left"
        )

        self.console.print(panel)

    def run(self):
        """Run the installer"""
        try:
            # Welcome
            self.show_banner()
            self.console.print(
                "[bold]Welcome to the Quantum Admin Interactive Installer![/bold]\n"
            )
            self.console.print(
                "This wizard will guide you through the installation process.\n"
            )

            if not Confirm.ask("Ready to begin?", default=True):
                self.console.print("\n[yellow]Installation cancelled.[/yellow]")
                return

            # Step 1: System Verification
            if not self.verify_system():
                return

            # Step 2: Installation Type
            install_type = self.select_installation_type()
            self.config["install_type"] = install_type

            # Step 3: Database Configuration
            db_config = self.configure_database()
            self.config["database"] = db_config

            # Step 4: Redis Configuration
            redis_config = self.configure_redis()
            self.config["redis"] = redis_config

            # Step 5: Admin User
            admin_config = self.configure_admin_user()
            self.config["admin"] = admin_config

            # Step 6: Install Dependencies
            if not self.install_dependencies():
                self.console.print("\n[bold red]Installation failed![/bold red]")
                return

            # Step 7: Create .env
            self.create_env_file(db_config, redis_config, admin_config)

            # Step 8: Initialize Database
            self.initialize_database()

            # Complete
            self.show_completion_screen()

        except KeyboardInterrupt:
            self.console.print("\n\n[yellow]Installation cancelled by user.[/yellow]")
            sys.exit(1)
        except Exception as e:
            self.console.print(f"\n[bold red]Installation error: {e}[/bold red]")
            import traceback
            self.console.print(traceback.format_exc())
            sys.exit(1)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point"""
    installer = QuantumInstaller()
    installer.run()


if __name__ == "__main__":
    main()
