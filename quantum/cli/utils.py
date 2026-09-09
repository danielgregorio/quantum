"""
Quantum CLI Utilities

Color output, progress bars, and common CLI helpers using rich.
"""

import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

# Try to import rich, provide helpful error if missing
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
    from rich.syntax import Syntax
    from rich.tree import Tree
    from rich.text import Text
    from rich.theme import Theme
    from rich.markdown import Markdown
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


# Quantum theme colors
QUANTUM_THEME = Theme({
    "info": "cyan",
    "success": "green",
    "warning": "yellow",
    "error": "bold red",
    "highlight": "bold magenta",
    "dim": "dim white",
    "command": "bold blue",
    "path": "underline cyan",
})


class QuantumConsole:
    """Rich console wrapper for Quantum CLI output."""

    def __init__(self, quiet: bool = False, no_color: bool = False):
        """Initialize console with optional quiet/no-color modes."""
        self.quiet = quiet
        self.no_color = no_color or os.environ.get('NO_COLOR', '') != ''

        if RICH_AVAILABLE:
            self.console = Console(
                theme=QUANTUM_THEME,
                force_terminal=not no_color,
                no_color=no_color
            )
        else:
            self.console = None

    def _fallback_print(self, message: str, prefix: str = ""):
        """Fallback print when rich is not available."""
        if prefix:
            print(f"[{prefix}] {message}")
        else:
            print(message)

    def info(self, message: str) -> None:
        """Print info message."""
        if self.quiet:
            return
        if self.console:
            self.console.print(f"[info][INFO][/info] {message}")
        else:
            self._fallback_print(message, "INFO")

    def success(self, message: str) -> None:
        """Print success message."""
        if self.console:
            self.console.print(f"[success][SUCCESS][/success] {message}")
        else:
            self._fallback_print(message, "SUCCESS")

    def warning(self, message: str) -> None:
        """Print warning message."""
        if self.console:
            self.console.print(f"[warning][WARNING][/warning] {message}")
        else:
            self._fallback_print(message, "WARNING")

    def error(self, message: str) -> None:
        """Print error message."""
        if self.console:
            self.console.print(f"[error][ERROR][/error] {message}", style="error")
        else:
            self._fallback_print(message, "ERROR")

    def print(self, message: str = "", style: Optional[str] = None) -> None:
        """Print generic message."""
        if self.quiet:
            return
        if self.console:
            self.console.print(message, style=style)
        else:
            print(message)

    def header(self, title: str, subtitle: Optional[str] = None) -> None:
        """Print header with title and optional subtitle."""
        if self.quiet:
            return
        if self.console:
            text = f"[bold magenta]{title}[/bold magenta]"
            if subtitle:
                text += f"\n[dim]{subtitle}[/dim]"
            self.console.print(Panel(text, border_style="magenta"))
        else:
            print(f"\n=== {title} ===")
            if subtitle:
                print(f"    {subtitle}")
            print()

    def panel(self, content: str, title: Optional[str] = None, style: str = "blue") -> None:
        """Print content in a panel."""
        if self.quiet:
            return
        if self.console:
            self.console.print(Panel(content, title=title, border_style=style))
        else:
            if title:
                print(f"\n--- {title} ---")
            print(content)
            print()

    def table(self, headers: List[str], rows: List[List[str]], title: Optional[str] = None) -> None:
        """Print a table."""
        if self.console:
            table = Table(title=title, show_header=True, header_style="bold cyan")
            for header in headers:
                table.add_column(header)
            for row in rows:
                table.add_row(*row)
            self.console.print(table)
        else:
            if title:
                print(f"\n{title}")
            # Simple table fallback
            col_widths = [max(len(str(row[i])) for row in [headers] + rows) for i in range(len(headers))]
            header_line = " | ".join(h.ljust(w) for h, w in zip(headers, col_widths))
            print(header_line)
            print("-" * len(header_line))
            for row in rows:
                print(" | ".join(str(c).ljust(w) for c, w in zip(row, col_widths)))

    def tree(self, label: str, items: Dict[str, Any]) -> None:
        """Print a tree structure."""
        if self.console:
            tree = Tree(f"[bold]{label}[/bold]")
            self._build_tree(tree, items)
            self.console.print(tree)
        else:
            print(f"{label}")
            self._print_tree_fallback(items, indent=2)

    def _build_tree(self, parent, items: Dict[str, Any]) -> None:
        """Recursively build tree."""
        for key, value in items.items():
            if isinstance(value, dict):
                branch = parent.add(f"[cyan]{key}/[/cyan]")
                self._build_tree(branch, value)
            elif isinstance(value, list):
                branch = parent.add(f"[cyan]{key}/[/cyan]")
                for item in value:
                    if isinstance(item, dict):
                        self._build_tree(branch, item)
                    else:
                        branch.add(str(item))
            else:
                parent.add(f"{key}: [dim]{value}[/dim]")

    def _print_tree_fallback(self, items: Dict[str, Any], indent: int = 0) -> None:
        """Fallback tree printing."""
        for key, value in items.items():
            if isinstance(value, dict):
                print(" " * indent + f"{key}/")
                self._print_tree_fallback(value, indent + 2)
            elif isinstance(value, list):
                print(" " * indent + f"{key}/")
                for item in value:
                    print(" " * (indent + 2) + str(item))
            else:
                print(" " * indent + f"{key}: {value}")

    def code(self, code: str, language: str = "xml", title: Optional[str] = None) -> None:
        """Print syntax-highlighted code."""
        if self.quiet:
            return
        if self.console:
            syntax = Syntax(code, language, theme="monokai", line_numbers=True)
            if title:
                self.console.print(Panel(syntax, title=title, border_style="green"))
            else:
                self.console.print(syntax)
        else:
            if title:
                print(f"\n--- {title} ---")
            print(code)

    @contextmanager
    def progress(self, description: str = "Working...", total: Optional[int] = None):
        """Context manager for progress indication."""
        if self.quiet or not self.console:
            yield None
            return

        if total:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=self.console
            ) as progress:
                task = progress.add_task(description, total=total)
                yield lambda n=1: progress.update(task, advance=n)
        else:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console
            ) as progress:
                task = progress.add_task(description, total=None)
                yield lambda: None

    def spinner(self, description: str = "Working..."):
        """Create a spinner context manager."""
        if self.quiet or not self.console:
            @contextmanager
            def noop():
                yield
            return noop()

        return self.console.status(description, spinner="dots")


# Global console instance
console = QuantumConsole()


def get_console(quiet: bool = False, no_color: bool = False) -> QuantumConsole:
    """Get a configured console instance."""
    return QuantumConsole(quiet=quiet, no_color=no_color)


def validate_project_name(name: str) -> tuple[bool, str]:
    """Validate project name.

    Returns:
        Tuple of (is_valid, error_message)
    """
    import re

    if not name:
        return False, "Project name cannot be empty"

    if len(name) < 2:
        return False, "Project name must be at least 2 characters"

    if len(name) > 50:
        return False, "Project name must be 50 characters or less"

    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', name):
        return False, "Project name must start with a letter and contain only letters, numbers, underscores, and hyphens"

    # Check for reserved names
    reserved = ['quantum', 'src', 'dist', 'build', 'node_modules', 'test', 'tests']
    if name.lower() in reserved:
        return False, f"'{name}' is a reserved name"

    return True, ""


def find_project_root() -> Optional[Path]:
    """Find the project root by looking for quantum.config.yaml or .q files."""
    current = Path.cwd()

    # Check current and parent directories
    for path in [current] + list(current.parents):
        if (path / 'quantum.config.yaml').exists():
            return path
        if list(path.glob('*.q')):
            return path
        # Stop at home directory
        if path == Path.home():
            break

    return None


def find_q_files(path: Path, recursive: bool = True) -> List[Path]:
    """Find all .q files in a directory."""
    if recursive:
        return list(path.rglob('*.q'))
    return list(path.glob('*.q'))


def get_quantum_version() -> str:
    """Get Quantum version from package or default."""
    try:
        # Try to read from version file
        version_file = Path(__file__).parent.parent / '__version__.py'
        if version_file.exists():
            content = version_file.read_text()
            # Parse version = "x.y.z"
            for line in content.splitlines():
                if line.startswith('version'):
                    return line.split('=')[1].strip().strip('"\'')
    except Exception:
        pass

    return "1.0.0-dev"


def ensure_dependencies(*packages: str) -> bool:
    """Check if required packages are installed."""
    missing = []
    for pkg in packages:
        try:
            __import__(pkg.replace('-', '_'))
        except ImportError:
            missing.append(pkg)

    if missing:
        console.error(f"Missing dependencies: {', '.join(missing)}")
        console.info(f"Install with: pip install {' '.join(missing)}")
        return False
    return True
