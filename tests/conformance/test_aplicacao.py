"""Conformidade: SPEC.md seção 9a (q:application)."""

import os
import pathlib
import subprocess
import sys

import pytest

from quantum.core.parser import QuantumParser, QuantumParseError

REPO = pathlib.Path(__file__).resolve().parents[2]


class TestTiposRemovidos:
    @pytest.mark.parametrize('atributo,citado', [
        ('type="html"', 'type="html"'), ('type="api"', 'type="api"'),
        ('type="microservices"', 'type="microservices"'), ('', 'with no type='),
    ])
    def test_parse_recusa_e_aponta_components(self, atributo, citado):
        # APP-1 (eram G17: html nao subia; G18: api nao executava a rota)
        with pytest.raises(QuantumParseError) as erro:
            QuantumParser().parse(f'<q:application id="app" {atributo} xmlns:q="https://quantum.lang/ns">'
                                  '<q:route path="/" method="GET"><h1>oi</h1></q:route></q:application>')
        mensagem = str(erro.value)
        assert citado in mensagem and 'components/' in mensagem and 'quantum start' in mensagem

    def test_quantum_run_sai_com_erro_e_a_mensagem(self, tmp_path):
        # APP-1
        app = tmp_path / 'app.q'
        app.write_text('<q:application id="app" type="html" xmlns:q="https://quantum.lang/ns">'
                       '<q:route path="/" method="GET"><h1>oi</h1></q:route></q:application>',
                       encoding='utf-8')
        saida = subprocess.run([sys.executable, '-m', 'quantum.cli.runner', 'run', str(app)],
                               capture_output=True, text=True, cwd=tmp_path, timeout=60,
                               env=dict(os.environ, PYTHONPATH=str(REPO), PYTHONIOENCODING='utf-8'))
        assert saida.returncode == 1
        assert 'quantum start' in saida.stdout + saida.stderr
        assert 'Traceback' not in saida.stdout + saida.stderr

    @pytest.mark.parametrize('tipo', ['game', 'terminal', 'ui', 'testing'])
    def test_tipos_que_continuam(self, tipo):
        # APP-1
        assert QuantumParser().parse(
            f'<q:application id="a" type="{tipo}" xmlns:q="https://quantum.lang/ns"></q:application>'
        ).app_type == tipo
