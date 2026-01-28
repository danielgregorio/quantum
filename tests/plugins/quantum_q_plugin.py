"""
Pytest plugin that discovers and executes .q regression test files.

Scans examples/ for test-*.q files, wraps each as a pytest.Item,
and executes via QuantumParser + ComponentRuntime.
"""

import sys
import pytest
from pathlib import Path

# Ensure src is importable
_src_path = str(Path(__file__).resolve().parent.parent.parent / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)


# ---------- Feature classification (mirrors test_runner.py) ----------

_PREFIX_TO_FEATURE = {
    "test-action-": "actions",
    "test-transaction-": "transactions",
    "test-session-": "sessions",
    "test-application-": "sessions",
    "test-request-": "sessions",
    "test-auth-": "authentication",
    "test-upload-": "uploads",
    "test-email-": "emails",
    "test-htmx-": "htmx",
    "test-island-": "islands",
    "test-if-": "conditionals",
    "test-else": "conditionals",
    "test-conditionals": "conditionals",
    "test-loop-": "loops",
    "test-databinding-": "databinding",
    "test-function-": "functions",
    "test-set-": "state_management",
    "test-query-": "query",
    "test-invoke-": "invoke",
    "test-data-": "data_import",
    "test-log-": "logging",
    "test-dump-": "dump",
    "test-false-": "conditionals",
}

# Files that are expected to fail (negative tests)
_EXPECTED_FAILURES = {
    "test-conditionals.q",
}


def _classify_feature(filename: str) -> str:
    """Return the feature marker name for a given test-*.q file."""
    for prefix, feature in _PREFIX_TO_FEATURE.items():
        if filename.startswith(prefix):
            return feature
    return "uncategorized"


# ---------- pytest hooks ----------

def pytest_collect_file(parent, file_path):
    """Collect test-*.q files from examples/."""
    if file_path.suffix == ".q" and file_path.name.startswith("test-"):
        return QuantumQFile.from_parent(parent, path=file_path)


class QuantumQFile(pytest.File):
    """Collector for a single .q test file."""

    def collect(self):
        yield QuantumQItem.from_parent(self, name=self.path.name)


class QuantumQItem(pytest.Item):
    """A single .q regression test."""

    def __init__(self, name, parent):
        super().__init__(name, parent)
        feature = _classify_feature(name)
        self.add_marker(pytest.mark.regression)
        self.add_marker(pytest.mark.q_file)
        if feature != "uncategorized":
            self.add_marker(getattr(pytest.mark, feature))
        self._expected_failure = name in _EXPECTED_FAILURES

    def runtest(self):
        from core.parser import QuantumParser
        from runtime.component import ComponentRuntime

        parser = QuantumParser()
        ast = parser.parse_file(str(self.path))
        runtime = ComponentRuntime()

        # Mock datasource for query tests
        self._mock_datasource(runtime)

        try:
            runtime.execute_component(ast)
        except Exception:
            if self._expected_failure:
                return  # expected to fail
            raise

        if self._expected_failure:
            pytest.fail(f"{self.name} was expected to fail but passed")

    def _mock_datasource(self, runtime: "ComponentRuntime"):
        """Provide a test-sqlite datasource if test_database is available."""
        try:
            # test_database.py lives in the project root
            root = Path(__file__).resolve().parent.parent.parent
            if str(root) not in sys.path:
                sys.path.insert(0, str(root))
            from test_database import TestDatabase

            db = TestDatabase()
            test_config = db.get_config()
            original = runtime.database_service.get_datasource_config

            def patched(datasource_name: str):
                if datasource_name == "test-sqlite":
                    return test_config
                return original(datasource_name)

            runtime.database_service.get_datasource_config = patched
        except Exception:
            pass  # No test database available – query tests may fail

    def repr_failure(self, excinfo):
        return f"Quantum .q test failed: {self.name}\n{excinfo.getrepr()}"

    def reportinfo(self):
        return self.path, None, f"q:{self.name}"
