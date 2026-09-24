"""Fixtures of the conformance suite: run a component, serve pages."""

import contextlib
import io
import pathlib
import tempfile

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.component import ComponentRuntime


def run_component(body, params=None):
    path = pathlib.Path(tempfile.mkdtemp()) / 'c.q'
    path.write_text(
        f'<q:component name="C" xmlns:q="https://quantum.lang/ns">{body}</q:component>',
        encoding='utf-8')
    with contextlib.redirect_stdout(io.StringIO()):
        return ComponentRuntime(config={}).execute_component(
            QuantumParser().parse_file(str(path)), params or {})


@pytest.fixture
def run_body():
    return run_component


@pytest.fixture
def serve_pages(tmp_path):
    """serve_pages(datasources_yaml='', name=source, ...) -> a Flask test client."""
    from quantum.runtime.web_server import QuantumWebServer

    def build(datasources_yaml='', **components):
        folder = tmp_path / 'components'
        folder.mkdir(exist_ok=True)
        for name, source in components.items():
            (folder / f'{name}.q').write_text(source, encoding='utf-8')
        config = tmp_path / 'quantum.config.yaml'
        config.write_text(
            f"server:\n  debug: false\npaths:\n  components: {folder.as_posix()}\n"
            "logging:\n  level: ERROR\n  console: false\n  file: false\n"
            + datasources_yaml, encoding='utf-8')
        server = QuantumWebServer(str(config))
        server.app.config['TESTING'] = True
        return server.app.test_client()
    return build
