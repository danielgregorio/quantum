"""
Quantum CLI - Test Command

Run tests for Quantum applications.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, List

import click

from cli.utils import get_console, find_project_root


@click.command('test')
@click.argument('path', required=False, type=click.Path())
@click.option('--pattern', '-p', type=str, default='test_*.py',
              help='Test file pattern')
@click.option('--coverage', '-c', is_flag=True, help='Run with coverage')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
@click.option('--watch', '-w', is_flag=True, help='Watch mode - rerun on changes')
@click.option('--filter', '-k', type=str, help='Filter tests by name pattern')
@click.option('--markers', '-m', type=str, help='Run tests with specific markers')
@click.option('--fail-fast', '-x', is_flag=True, help='Stop on first failure')
@click.option('--quiet', '-q', is_flag=True, help='Quiet mode')
def test(
    path: Optional[str],
    pattern: str,
    coverage: bool,
    verbose: bool,
    watch: bool,
    filter: Optional[str],
    markers: Optional[str],
    fail_fast: bool,
    quiet: bool
):
    """Run tests for Quantum applications.

    Uses pytest to run tests from the tests/ directory.

    Examples:

        quantum test

        quantum test tests/unit/

        quantum test --coverage

        quantum test -k "test_parser" -v

        quantum test --watch
    """
    console = get_console(quiet=quiet)

    # Find project root
    project_root = find_project_root()
    if not project_root:
        console.error("No Quantum project found")
        raise click.Abort()

    # Determine test path
    if path:
        test_path = Path(path)
        if not test_path.is_absolute():
            test_path = project_root / path
    else:
        test_path = project_root / 'tests'

    if not test_path.exists():
        console.error(f"Test path not found: {test_path}")
        console.info("Create a 'tests/' directory with test files")
        raise click.Abort()

    console.header(
        "Running Quantum Tests",
        f"Path: {test_path}"
    )

    # Check for pytest
    try:
        subprocess.run(['pytest', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        console.error("pytest not found. Install with: pip install pytest")
        raise click.Abort()

    # Build pytest command
    cmd = ['pytest', str(test_path)]

    if verbose:
        cmd.append('-v')

    if fail_fast:
        cmd.append('-x')

    if filter:
        cmd.extend(['-k', filter])

    if markers:
        cmd.extend(['-m', markers])

    if coverage:
        # Check for pytest-cov
        try:
            import pytest_cov
        except ImportError:
            console.warning("pytest-cov not found. Install with: pip install pytest-cov")
            console.info("Running without coverage...")
        else:
            cmd.extend(['--cov=src', '--cov-report=term-missing', '--cov-report=html'])

    # Add src to PYTHONPATH
    env = os.environ.copy()
    src_path = str(project_root / 'src')
    env['PYTHONPATH'] = src_path + os.pathsep + env.get('PYTHONPATH', '')

    console.info(f"Running: {' '.join(cmd)}")
    console.print()

    if watch:
        _watch_and_test(project_root, cmd, env, console)
    else:
        # Run tests
        result = subprocess.run(cmd, cwd=project_root, env=env)

        if result.returncode == 0:
            console.print()
            console.success("All tests passed!")
        else:
            console.print()
            console.error(f"Tests failed with exit code {result.returncode}")
            sys.exit(result.returncode)


def _watch_and_test(project_root: Path, cmd: List[str], env: dict, console):
    """Watch for changes and rerun tests."""
    import time
    import signal

    last_mtimes = {}

    def get_file_mtimes():
        mtimes = {}
        for ext in ['.py', '.q']:
            for f in project_root.rglob(f'*{ext}'):
                # Skip __pycache__
                if '__pycache__' in str(f):
                    continue
                try:
                    mtimes[f] = f.stat().st_mtime
                except OSError:
                    pass
        return mtimes

    def run_tests():
        console.print()
        console.info("Running tests...")
        console.print()
        subprocess.run(cmd, cwd=project_root, env=env)

    def signal_handler(sig, frame):
        console.print()
        console.info("Stopping watch mode...")
        raise SystemExit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Initial run
    run_tests()
    last_mtimes = get_file_mtimes()

    console.print()
    console.info("Watching for changes... (Ctrl+C to stop)")

    while True:
        time.sleep(1)
        current_mtimes = get_file_mtimes()

        changed = []
        for f, mtime in current_mtimes.items():
            if f not in last_mtimes or mtime > last_mtimes[f]:
                changed.append(f)

        if changed:
            console.print()
            for f in changed:
                rel_path = f.relative_to(project_root)
                console.info(f"Changed: {rel_path}")

            run_tests()
            last_mtimes = current_mtimes
