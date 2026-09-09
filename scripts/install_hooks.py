#!/usr/bin/env python3
"""
Install git hooks for Quantum project.

Creates a pre-commit hook that runs QA analysis on modified features.

Usage:
    python scripts/install_hooks.py          # Install hooks
    python scripts/install_hooks.py --remove # Remove hooks
"""

import argparse
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOKS_DIR = ROOT / ".git" / "hooks"
PRE_COMMIT = HOOKS_DIR / "pre-commit"

HOOK_CONTENT = """\
#!/bin/sh
# Quantum QA pre-commit hook
# Installed by scripts/install_hooks.py
# This hook WARNS about feature coverage but does NOT block commits.

echo "[Quantum QA] Checking feature coverage..."
python scripts/qa_hook.py
# Always allow commit (exit 0) – QA hook is advisory only
exit 0
"""


def install():
    """Install the pre-commit hook."""
    if not HOOKS_DIR.exists():
        print(f"ERROR: Git hooks directory not found: {HOOKS_DIR}")
        print("       Are you in a git repository?")
        sys.exit(1)

    if PRE_COMMIT.exists():
        existing = PRE_COMMIT.read_text(encoding="utf-8")
        if "Quantum QA" in existing:
            print("Hook already installed. Use --remove to reinstall.")
            return
        # Append to existing hook
        print("Appending to existing pre-commit hook...")
        with open(PRE_COMMIT, "a", encoding="utf-8") as f:
            f.write("\n\n# --- Quantum QA hook (appended) ---\n")
            f.write("python scripts/qa_hook.py\n")
    else:
        PRE_COMMIT.write_text(HOOK_CONTENT, encoding="utf-8")

    # Make executable (unix)
    try:
        PRE_COMMIT.chmod(PRE_COMMIT.stat().st_mode | stat.S_IEXEC)
    except Exception:
        pass  # Windows doesn't need chmod

    print(f"Pre-commit hook installed at {PRE_COMMIT}")
    print("The hook will warn about feature coverage on each commit.")


def remove():
    """Remove the pre-commit hook if it's ours."""
    if not PRE_COMMIT.exists():
        print("No pre-commit hook found.")
        return

    content = PRE_COMMIT.read_text(encoding="utf-8")
    if "Quantum QA" not in content:
        print("Pre-commit hook exists but is not from Quantum. Skipping.")
        return

    PRE_COMMIT.unlink()
    print("Pre-commit hook removed.")


def main():
    parser = argparse.ArgumentParser(description="Install Quantum git hooks")
    parser.add_argument("--remove", action="store_true", help="Remove hooks instead of installing")
    args = parser.parse_args()

    if args.remove:
        remove()
    else:
        install()


if __name__ == "__main__":
    main()
