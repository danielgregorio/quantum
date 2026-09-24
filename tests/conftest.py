"""
Pytest Configuration and Fixtures

Shared fixtures for all tests.
"""

import os
import pytest
import sqlite3
import tempfile
from pathlib import Path

# The admin's database defaults to quantum_admin/quantum_admin.db — the file the
# admin really serves. Set here, before any test imports the admin backend, so
# no test run writes into it. An explicit value still wins.
#
# The same for quantum_admin/settings (connectors.yaml, global.yaml). A fresh
# clone has no global.yaml, and the first test that reached settings_service
# created one in the real directory — the guard in tests/admin/conftest.py
# caught it on CI.
#
# One per process: pytest-xdist workers inherit the controller's environment,
# so a value set there was shared by every worker, and two of them creating
# the admin's tables at once failed with "table ... already exists".
def _per_process(name, make):
    ours = os.environ.get("_QUANTUM_TESTS_" + name)
    if name not in os.environ or os.environ[name] == ours:
        os.environ[name] = os.environ["_QUANTUM_TESTS_" + name] = make()


_per_process("QUANTUM_ADMIN_DATABASE_URL", lambda: "sqlite:///" + str(
    Path(tempfile.mkdtemp(prefix="quantum-admin-tests-")) / "admin.db"))
_per_process("QUANTUM_ADMIN_SETTINGS_DIR", lambda: str(
    Path(tempfile.mkdtemp(prefix="quantum-admin-settings-tests-"))))


@pytest.fixture
def parser():
    """Quantum parser instance"""
    from quantum.core.parser import QuantumParser
    return QuantumParser()


@pytest.fixture
def execution_context():
    """Clean execution context"""
    from quantum.runtime.execution_context import ExecutionContext
    return ExecutionContext()


@pytest.fixture
def component_resolver():
    """Component resolver with test components directory"""
    from quantum.runtime.component_resolver import ComponentResolver
    return ComponentResolver(components_dir="./tests/fixtures/components")


@pytest.fixture
def sample_component_path(tmp_path):
    """Create a temporary component file"""
    component_dir = tmp_path / "components"
    component_dir.mkdir()

    component_file = component_dir / "TestComponent.q"
    component_file.write_text("""
<q:component name="TestComponent">
  <q:param name="title" type="string" required="true" />
  <h1>{title}</h1>
</q:component>
""")

    return component_file


@pytest.fixture
def flask_app():
    """Flask test app"""
    from quantum.runtime.web_server import QuantumWebServer
    server = QuantumWebServer()
    server.app.config['TESTING'] = True
    return server.app


@pytest.fixture
def client(flask_app):
    """Flask test client"""
    return flask_app.test_client()


# ---------- New unified fixtures ----------


@pytest.fixture
def test_database(tmp_path):
    """Provide a temporary SQLite database with sample data.

    Returns a dict with 'path' and 'connection' keys.
    The database includes a 'users' and 'products' table with sample rows.
    """
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT,
            role TEXT DEFAULT 'user'
        )
    """)
    cursor.executemany("INSERT INTO users (name, email, role) VALUES (?, ?, ?)", [
        ("Alice", "alice@example.com", "admin"),
        ("Bob", "bob@example.com", "user"),
        ("Carol", "carol@example.com", "user"),
    ])

    cursor.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            price REAL,
            category TEXT
        )
    """)
    cursor.executemany("INSERT INTO products (name, price, category) VALUES (?, ?, ?)", [
        ("Widget", 9.99, "tools"),
        ("Gadget", 24.99, "electronics"),
        ("Doohickey", 4.99, "tools"),
    ])

    conn.commit()
    yield {"path": str(db_path), "connection": conn}
    conn.close()


@pytest.fixture
def quantum_runtime():
    """A fresh ComponentRuntime instance ready for testing."""
    from quantum.runtime.component import ComponentRuntime
    return ComponentRuntime()


@pytest.fixture
def parse_and_execute(parser, quantum_runtime):
    """Convenience fixture: parse source code and execute it.

    Returns a callable: parse_and_execute(source: str) -> result
    """
    def _run(source: str):
        ast = parser.parse(source)
        return quantum_runtime.execute_component(ast)
    return _run


# ---------- Game Engine 2D fixtures ----------


@pytest.fixture
def game_parser():
    """Parser instance for game .q files."""
    from quantum.core.parser import QuantumParser
    return QuantumParser()


@pytest.fixture
def game_builder():
    """GameBuilder instance."""
    from quantum.runtime.game_builder import GameBuilder
    return GameBuilder()


@pytest.fixture
def game_codegen():
    """GameCodeGenerator instance."""
    from quantum.runtime.game_code_generator import GameCodeGenerator
    return GameCodeGenerator()


@pytest.fixture(autouse=True)
def _stop_job_threads():
    """A test that ran q:job, q:schedule or q:thread leaves its threads stopped and joined.

    The job executor is the process's (shared_job_executor); its threads used
    to outlive the test that started them and log after pytest had closed its
    streams ("--- Logging error ---").
    """
    yield
    from quantum.runtime.job_executor import shutdown_job_executors
    shutdown_job_executors()
