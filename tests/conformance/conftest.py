"""Fixtures da suíte de conformidade: executar um componente, subir um servidor."""

import contextlib
import io
import pathlib
import tempfile

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.component import ComponentRuntime


def executar_componente(corpo, params=None):
    caminho = pathlib.Path(tempfile.mkdtemp()) / 'c.q'
    caminho.write_text(
        f'<q:component name="C" xmlns:q="https://quantum.lang/ns">{corpo}</q:component>',
        encoding='utf-8')
    with contextlib.redirect_stdout(io.StringIO()):
        return ComponentRuntime(config={}).execute_component(
            QuantumParser().parse_file(str(caminho)), params or {})


@pytest.fixture
def executar():
    return executar_componente


@pytest.fixture
def servidor(tmp_path):
    """montar(componentes={nome: fonte}, datasources=...) -> Flask test client."""
    from quantum.runtime.web_server import QuantumWebServer

    def montar(datasources_yaml='', **componentes):
        pasta = tmp_path / 'components'
        pasta.mkdir(exist_ok=True)
        for nome, fonte in componentes.items():
            (pasta / f'{nome}.q').write_text(fonte, encoding='utf-8')
        config = tmp_path / 'quantum.config.yaml'
        config.write_text(
            f"server:\n  debug: false\npaths:\n  components: {pasta.as_posix()}\n"
            "logging:\n  level: ERROR\n  console: false\n  file: false\n"
            + datasources_yaml, encoding='utf-8')
        server = QuantumWebServer(str(config))
        server.app.config['TESTING'] = True
        return server.app.test_client()
    return montar
