"""
Pytest plugin that discovers and executes .q regression test files.

Scans examples/ for test-*.q files, wraps each as a pytest.Item,
and executes via QuantumParser + ComponentRuntime.
"""

import sys
import pytest
from pathlib import Path

# Ensure src is importable


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
#
# test-set-validation-email-invalid.q sets an invalid address with
# validate="email" and says "Invalid email - should fail" in its own comment.
# The framework does reject it, correctly — the harness just did not know
# this was a negative test, so a working validator was counted as a failing
# test. That is worse than a missing test: it trains you to ignore the list.
# Examples that call a public HTTP API. They are skipped when that API is not
# reachable, instead of failing — and they used to PASS offline for the wrong
# reason: q:invoke raised before sending any request, and the unresolved
# {users.name} was handed back as literal text, which counted as success.
_NEEDS_NETWORK = {
    "test-invoke-http-get.q",
    "test-invoke-http-post.q",
    "test-invoke-complete.q",
}
_network_ok = None


def _network_available() -> bool:
    global _network_ok
    if _network_ok is None:
        import socket
        try:
            socket.create_connection(("jsonplaceholder.typicode.com", 443), timeout=3).close()
            _network_ok = True
        except OSError:
            _network_ok = False
    return _network_ok


_EXPECTED_FAILURES = {
    "test-conditionals.q",
    "test-set-validation-email-invalid.q",
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
        if self.name in _NEEDS_NETWORK and not _network_available():
            pytest.skip("needs internet access (calls jsonplaceholder.typicode.com)")
        from quantum.core.parser import QuantumParser
        from quantum.core.ast_nodes import ApplicationNode
        from quantum.runtime.component import ComponentRuntime

        parser = QuantumParser()
        ast = parser.parse_file(str(self.path))
        runtime = ComponentRuntime()

        # Mock datasource for query tests
        self._mock_datasource(runtime)

        try:
            if isinstance(ast, ApplicationNode):
                # A q:application is not a component. Calling
                # execute_component on one raised "'ApplicationNode' object
                # has no attribute 'params'" and then "... no attribute
                # 'statements'" — seven test-ui-*.q and test-mobile.q failed
                # there, before reaching anything they were written to check.
                self._run_application(ast, runtime)
            else:
                runtime.execute_component(ast)
        except Exception:
            if self._expected_failure:
                return  # expected to fail
            raise

        if self._expected_failure:
            pytest.fail(f"{self.name} was expected to fail but passed")

    def _run_application(self, app, runtime):
        """Exercise a q:application the way `quantum run` would.

        Building is the real check for a ui/game/terminal application — it is
        what the CLI does with one — and UIBuilder.build() returns a string,
        so the test never writes to the project.
        """
        app_type = getattr(app, 'app_type', '')

        if app_type == 'ui':
            from quantum.runtime.ui_builder import UIBuilder
            output = UIBuilder().build(app, target='html')
            assert output and output.strip(), (
                f"{self.name}: the UI builder produced nothing")
            return

        # Other application types: execute the components it declares, which
        # is the part this harness can check without starting a server or
        # writing a build to disk.
        for component in getattr(app, 'components', None) or []:
            runtime.execute_component(component)

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
