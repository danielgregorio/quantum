"""
Root conftest.py - Registers Quantum pytest plugins globally.

This file ensures that .q regression tests and dataset-driven tests
are all discovered by pytest.
"""

import sys
from pathlib import Path

# Ensure src is importable from any test location
_src_path = str(Path(__file__).parent / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

# Ensure project root is importable (for test_database.py etc.)
_root_path = str(Path(__file__).parent)
if _root_path not in sys.path:
    sys.path.insert(0, _root_path)

# Register custom plugins
pytest_plugins = [
    "tests.plugins.quantum_q_plugin",
]


