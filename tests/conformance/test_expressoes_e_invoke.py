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

    @pytest.mark.parametrize('condicao', ['flash', 'session.user.is_admin', 'user.admin', 'itens[3]'])
    def test_condicao_com_nome_ausente_e_falsa(self, executar, condicao):
        # EXPR-5: <q:if condition="flash"> antes de existir flash
        assert executar('<q:set name="user" type="object" value=\'{"nome": "a"}\'/>'
                        '<q:set name="itens" type="array" value="[1]"/>'
                        f'<q:if condition="{condicao}"><q:return value="sim"/></q:if>'
                        '<q:return value="nao"/>') == 'nao'

    @pytest.mark.parametrize('condicao,esperado', [
        ('idade >= 18 && ok', 'sim'), ('idade < 18 || ok', 'sim'),
        ('!ok || idade > 30', 'nao'), ("nome != 'x' && !(idade == 3)", 'sim'),
        # dentro de string nao traduz: traduzido seria ' and ' in 'x&&y', falso
        ("'&&' in 'x&&y'", 'sim')])
    def test_operadores_estilo_javascript(self, executar, condicao, esperado):
        # EXPR-6 (antes: && e || nao parseavam e a condicao era falsa sempre)
        assert executar('<q:set name="idade" value="20" type="number"/>'
                        '<q:set name="ok" value="true" type="boolean"/>'
                        '<q:set name="nome" value="ana"/>'
                        f'<q:if condition="{condicao}"><q:return value="sim"/></q:if>'
                        '<q:return value="nao"/>') == esperado

    @pytest.mark.parametrize('condicao', ['idade === 18', 'maior(idade)'])
    def test_condicao_com_outro_erro_e_erro(self, executar, condicao):
        # EXPR-5: so ausencia vira falso; sintaxe ou funcao inexistente e erro
        with pytest.raises(Exception, match='could not be evaluated'):
            executar('<q:set name="idade" value="20" type="number"/>'
                     f'<q:if condition="{condicao}"><q:return value="sim"/></q:if>')


class TestAritmetica:
    @pytest.mark.parametrize('expressao', ["{'-' * 40}", "{nome * 2}", "{nome - 1}", "{'%s' % nome}"])
    def test_operador_aritmetico_em_texto_e_erro(self, executar, expressao):
        # EXPR-7 (antes: '-' * 40 repetia, '%s' % x formatava)
        with pytest.raises(Exception, match='needs two numbers'):
            executar(f'<q:set name="nome" value="ana"/><q:return value="{expressao}"/>')

    @pytest.mark.parametrize('expressao,esperado', [
        ("{'ab' + 'cd'}", 'abcd'), ('{n + 1}', 42), ('{t * 2}', 84), ('{7 // 2}', 3)])
    def test_o_que_continua(self, executar, expressao, esperado):
        # EXPR-7
        assert executar('<q:set name="n" value="41" type="number"/><q:set name="t" value="42"/>'
                        f'<q:return value="{expressao}"/>') == esperado

    def test_valor_so_com_digitos_e_numero(self, executar):
        # EXPR-7 (antes: {1} voltava como o texto '{1}', e n * '{1}' repetia)
        assert executar('<q:function name="fat"><q:param name="n" type="number"/>'
                        '<q:if condition="n <= 1"><q:return value="{1}"/></q:if>'
                        '<q:return value="{n * fat(n - 1)}"/></q:function>'
                        '<q:return value="{fat(5)}"/>') == 120

    def test_quantificador_dentro_de_texto_continua(self, executar):
        # EXPR-7 / EXPR-4
        assert executar('<q:return value="[0-9]{3}"/>') == '[0-9]{3}'


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

    def test_falha_http_e_erro(self, executar, api):
        # INV-2
        with pytest.raises(Exception, match='q:invoke .u. failed: HTTP 503.*onerror="continue"'):
            executar(f'<q:invoke name="u" url="{api}/falha"/><q:return value="nao chega"/>')

    def test_falha_http_com_continue_fica_em_nome_result(self, executar, api):
        # INV-2
        r = executar(f'<q:invoke name="u" url="{api}/falha" onerror="continue"/>'
                     '<q:return value="{u_result}"/>')
        assert r['success'] is False and '503' in r['error']['message']

    def test_onerror_invalido_e_erro_de_parse(self, executar, api):
        # INV-2
        with pytest.raises(Exception, match='onerror must be'):
            executar(f'<q:invoke name="u" url="{api}/u" onerror="ignore"/>')
