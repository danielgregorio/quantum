"""
Pytest Configuration and Fixtures

Shared fixtures for all tests.
"""

import pytest
import sys
import sqlite3
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


@pytest.fixture
def parser():
    """Quantum parser instance"""
    from core.parser import QuantumParser
    return QuantumParser()


@pytest.fixture
def execution_context():
    """Clean execution context"""
    from runtime.execution_context import ExecutionContext
    return ExecutionContext()


@pytest.fixture
def component_resolver():
    """Component resolver with test components directory"""
    from runtime.component_resolver import ComponentResolver
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
    from runtime.web_server import QuantumWebServer
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
    from runtime.component import ComponentRuntime
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
    from core.parser import QuantumParser
    return QuantumParser()


@pytest.fixture
def game_builder():
    """GameBuilder instance."""
    from runtime.game_builder import GameBuilder
    return GameBuilder()


@pytest.fixture
def game_codegen():
    """GameCodeGenerator instance."""
    from runtime.game_code_generator import GameCodeGenerator
    return GameCodeGenerator()
