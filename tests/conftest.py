"""
Pytest Configuration and Fixtures

Shared fixtures for all tests.
"""

import pytest
import sys
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
