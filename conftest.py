"""
Root conftest.py - Registers Quantum pytest plugins globally.

This file ensures that .q regression tests and dataset-driven tests
are all discovered by pytest.
"""

import sys
from pathlib import Path

import pytest

# Ensure src is importable from any test location

# Ensure project root is importable (for test_database.py etc.)

# Register custom plugins
pytest_plugins = [
    "tests.plugins.quantum_q_plugin",
]

TEST_DB = Path(__file__).parent / "test_data" / "quantum_test.db"


def pytest_sessionstart(session):
    """Rebuild test_data/quantum_test.db once per session.

    The .q examples that write — test-query-insert.q inserts a fixed email
    into a UNIQUE column — are only repeatable against a fresh database. They
    never showed it, because they had been failing earlier, on a connection
    to an Admin API nobody was running. Once that was fixed they passed once
    and then failed on every later run with "UNIQUE constraint failed".

    A suite that only passes on a clean checkout is not a suite. This is the
    setup those tests always assumed.

    It is a session hook, not a fixture: the .q tests are custom pytest.Item
    objects, and those never request fixtures — an autouse fixture here would
    simply not run for them.
    """
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        import test_database
        test_database.TestDatabase(str(TEST_DB)).setup()
    except Exception as exc:      # pragma: no cover - environment dependent
        # Not fatal: most of the suite does not touch the database, and a
        # failure here should not stop it from running.
        print(f"[WARN] could not rebuild {TEST_DB}: {exc}")


