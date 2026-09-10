"""Conformidade: SPEC.md seções 6 (Expressões) e 7 (Invocação)."""

import http.server
import json
import logging
import threading
import urllib.parse

import pytest

from quantum.core import expression_diagnostics
from quantum.runtime.execution_context import ExecutionContext
from quantum.runtime.renderer import HTMLRenderer


@pytest.fixture(autouse=True)
def diagnosticos_limpos():
    expression_diagnostics.reset()
    yield
    expression_diagnostics.reset()


class TestExpressoes:
    def test_nome_inexistente_em_atributo_e_erro_que_o_nomeia(self, executar):
        # EXPR-1 (era G12: devolvia 'x{nada}y' em silêncio)
        with pytest.raises(Exception, match="nada"):
            executar('<q:return value="x{nada}y"/>')

    def test_nome_inexistente_sugere_o_parecido(self, executar):
        # EXPR-1
        with pytest.raises(Exception, match="did you mean 'total'"):
            executar('<q:set name="total" value="3" type="number"/>'
                     '<q:set name="r" value="{totl + 1}"/>')

    def test_erro_de_avaliacao_e_erro(self, executar):
        # EXPR-2 (era G14: {10 / z} voltava com as chaves cruas)
        with pytest.raises(Exception, match="division by zero"):
            executar('<q:set name="z" value="0" type="number"/>'
                     '<q:return value="{10 / z}"/>')

    def test_referencia_de_escopo_ausente_e_vazia(self, executar):
        # EXPR-3
        assert executar('<q:return value="[{session.nome}]"/>') == '[]'

    def test_conta_com_escopo_ausente_e_erro_com_dica(self, executar):
        # EXPR-3 (era G15: '' e depois "could not convert string to float")
        with pytest.raises(Exception) as erro:
            executar('<q:set name="session.visitas" value="{session.visitas + 1}" type="number"/>')
        mensagem = str(erro.value)
        assert 'session.visitas + 1' in mensagem and 'is not set' in mensagem
        assert 'operation="increment"' in mensagem
        assert 'float' not in mensagem

    def test_contador_de_sessao_com_increment(self, executar):
        # EXPR-3: o caminho indicado pela mensagem funciona na primeira visita
        assert executar('<q:set name="session.visitas" operation="increment"/>'
                        '<q:return value="{session.visitas}"/>') == 1

    def test_conteudo_html_fica_literal_e_registra_uma_vez(self, caplog):
        # EXPR-4
        renderer = HTMLRenderer(ExecutionContext())
        with caplog.at_level(logging.WARNING, logger='quantum.databinding'):
            for _ in range(50):
                assert renderer._apply_databinding('A={nada}') == 'A={nada}'
        assert len(caplog.records) == 1 and 'nada' in caplog.text

    def test_pagina_servida_com_codigo_no_conteudo(self, servidor):
        # EXPR-4: chaves de código num <code> não quebram a página
        cliente = servidor(p='<q:component name="p" xmlns:q="https://quantum.lang/ns">'
                             '<p>function f() { return 1; }</p></q:component>')
        r = cliente.get('/p')
        assert r.status_code == 200 and 'function f() { return 1; }' in r.get_data(as_text=True)

    @pytest.mark.parametrize('valor', ['[{"a": 1}, {"b": 2}]', r'\d{10,11}'])
    def test_json_e_quantificador_nao_sao_expressoes(self, executar, valor):
        # EXPR-4
        assert executar(f"<q:return value='{valor}'/>") == valor

    def test_condicao_que_nao_avalia_e_falsa(self, executar):
        # EXPR-5: <q:if condition="flash"> antes de existir flash
        assert executar('<q:if condition="{flash}"><q:return value="sim"/></q:if>'
                        '<q:return value="nao"/>') == 'nao'


class _Api(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        if url.path == '/falha':
            self.send_response(503)
            self.end_headers()
            return
        corpo = json.dumps({'nome': 'Ana', 'query': dict(urllib.parse.parse_qsl(url.query))}).encode()
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def log_message(self, *args):
        pass


@pytest.fixture
def api():
    servidor = http.server.ThreadingHTTPServer(('127.0.0.1', 0), _Api)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    yield f'http://127.0.0.1:{servidor.server_address[1]}'
    servidor.shutdown()
    servidor.server_close()


class TestInvocacao:
    def test_url_sem_timeout_declarado_executa(self, executar, api):
        # INV-1 (nunca funcionou: timeout ausente virava None / 1000)
        assert executar(f'<q:invoke name="u" url="{api}/u"/>'
                        '<q:return value="{u.nome}"/>') == 'Ana'

    def test_param_vira_query_string(self, executar, api):
        # INV-1
        assert executar(f'<q:invoke name="u" url="{api}/u"><q:param name="q" value="x y"/></q:invoke>'
                        '<q:return value="{u.query.q}"/>') == 'x y'

    def test_falha_http_fica_em_nome_result(self, executar, api):
        # INV-2
        r = executar(f'<q:invoke name="u" url="{api}/falha"/>'
                     '<q:return value="{u_result}"/>')
        assert r['success'] is False and '503' in r['error']['message']
