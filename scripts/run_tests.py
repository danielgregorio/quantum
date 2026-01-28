#!/usr/bin/env python3
"""
Unified test runner for Quantum project.

Wrapper over pytest that provides convenient shortcuts for running
different test layers.

Usage:
    python scripts/run_tests.py                    # All tests (excl. Selenium)
    python scripts/run_tests.py --layer regression # Only .q regression tests
    python scripts/run_tests.py --layer dataset    # Only dataset tests
    python scripts/run_tests.py --layer transpiler # Only AS4 transpiler tests
    python scripts/run_tests.py --layer unit       # Only pytest unit tests
    python scripts/run_tests.py --feature loops    # Tests for a single feature
    python scripts/run_tests.py --collect          # Dry-run: list discovered tests
    python scripts/run_tests.py --quick            # Skip slow / external tests
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build_pytest_args(args) -> list[str]:
    """Build the pytest command-line arguments from parsed args."""
    cmd = [sys.executable, "-m", "pytest"]

    # Layer filtering
    if args.layer:
        layer_map = {
            "regression": ["-m", "regression"],
            "dataset": ["-m", "dataset"],
            "transpiler": ["-m", "transpiler"],
            "unit": ["tests/unit/", "tests/integration/"],
            "all": [],
        }
        extra = layer_map.get(args.layer, ["-m", args.layer])
        cmd.extend(extra)

    # Feature filtering
    if args.feature:
        cmd.extend(["-m", args.feature])

    # Collect-only mode
    if args.collect:
        cmd.append("--collect-only")

    # Quick mode: skip slow and selenium
    if args.quick:
        existing_marks = []
        for i, c in enumerate(cmd):
            if c == "-m" and i + 1 < len(cmd):
                existing_marks.append(cmd[i + 1])
        if existing_marks:
            # Combine with existing -m
            combined = f"({existing_marks[-1]}) and not slow and not selenium"
            # Find and replace the last -m value
            for i in range(len(cmd) - 1, -1, -1):
                if cmd[i] == "-m":
                    cmd[i + 1] = combined
                    break
        else:
            cmd.extend(["-m", "not slow and not selenium"])

    # Verbosity
    if args.verbose:
        cmd.append("-v")
    else:
        cmd.append("-v")  # Default to verbose

    # Additional pytest args
    if args.pytest_args:
        cmd.extend(args.pytest_args)

    return cmd


def main():
    parser = argparse.ArgumentParser(
        description="Quantum unified test runner",
        epilog="Any extra arguments are passed directly to pytest.",
    )
    parser.add_argument("--layer", choices=["regression", "dataset", "transpiler", "unit", "all"],
                        help="Run a specific test layer")
    parser.add_argument("--feature", type=str, help="Run tests for a specific feature")
    parser.add_argument("--collect", action="store_true", help="Only list discovered tests")
    parser.add_argument("--quick", action="store_true", help="Skip slow/selenium tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("pytest_args", nargs="*", help="Additional pytest arguments")

    args = parser.parse_args()
    cmd = build_pytest_args(args)

    print(f"[Quantum Test Runner] Executing: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, cwd=str(ROOT))
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
