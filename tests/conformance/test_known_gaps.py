"""
Lacunas semânticas conhecidas — o inventário da Fase 0.3, executável.

Cada teste descreve o comportamento PROPOSTO e está marcado
`xfail(strict=True)`: hoje o runtime faz outra coisa. Quando alguém corrigir,
o teste passa inesperadamente e o `strict` derruba a suíte — a lacuna tem de
sair daqui e virar regra com ID na SPEC (Fase 2), com o teste movido para a
seção dela.

O comportamento esperado é PROPOSTA, não decisão. A Fase 2 pode escolher
outra regra; nesse caso o teste muda junto. O que não pode acontecer é a
lacuna sumir sem ninguém decidir.

Todos os casos foram reproduzidos por execução em 2026-09-10.
"""

import os
import pathlib
import subprocess
import sys
import tempfile

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.component import ComponentRuntime

REPO = pathlib.Path(__file__).resolve().parents[2]


def executar(corpo, params=None):
    caminho = pathlib.Path(tempfile.mkdtemp()) / 'c.q'
    caminho.write_text(
        f'<q:component name="C" xmlns:q="https://quantum.lang/ns">{corpo}</q:component>',
        encoding='utf-8')
    return ComponentRuntime().execute_component(
        QuantumParser().parse_file(str(caminho)), params or {})


def lacuna(reason):
    return pytest.mark.xfail(strict=True, reason=reason)


class TestErrosDeExpressao:
    @lacuna("G12: variável inexistente fica literal na saída, em silêncio. "
            "Hoje devolve 'x{nada}y'.")
    def test_variavel_inexistente_e_erro_que_nomeia_a_variavel(self):
        with pytest.raises(Exception, match="nada"):
            executar('<q:return value="x{nada}y"/>')

    @lacuna("G15: variável de escopo ausente numa conta vira '' e a conversão "
            "falha com texto interno do Python. O contador clássico "
            "{session.visitas + 1} quebra na primeira visita; hoje só "
            "operation=\"increment\" funciona.")
    def test_contador_de_sessao_na_primeira_visita(self):
        assert executar(
            '<q:set name="session.visitas" value="{session.visitas + 1}" type="number"/>'
            '<q:return value="{session.visitas}"/>') == 1

    @lacuna("G14: erro de avaliação é engolido e as chaves cruas vão para a "
            "saída. Hoje {10 / z} com z=0 devolve '{10 / z}'.")
    def test_divisao_por_zero_e_erro(self):
        with pytest.raises(Exception):
            executar('<q:set name="z" value="0" type="number"/>'
                     '<q:return value="{10 / z}"/>')


class TestMensagensDeErro:
    @lacuna("G3: '{a} + {b}' é interpolação ('10 + 20'), e a conversão para "
            "número falha com mensagem interna do Python ('could not convert "
            "string to float'), sem dizer como escrever a soma.")
    def test_conversao_para_numero_ensina_a_sintaxe_da_expressao(self):
        with pytest.raises(Exception) as erro:
            executar('<q:set name="a" value="10"/><q:set name="b" value="20"/>'
                     '<q:set name="r" value="{a} + {b}" type="number"/>')
        assert '{a + b}' in str(erro.value)
        assert 'float' not in str(erro.value)

    @lacuna("G13: array com aspas simples falha com o texto do parser JSON "
            "('Expecting property name enclosed in double quotes').")
    def test_array_invalido_diz_para_usar_aspas_duplas(self):
        with pytest.raises(Exception) as erro:
            executar('''<q:set name="a" type="array" value="[{'x': 1}]"/>''')
        assert 'aspas duplas' in str(erro.value) or 'double quotes' in str(erro.value)
        assert 'Expecting property name' not in str(erro.value)

    @lacuna("G5: falha em q:invoke imprime traceback do Python para o usuário.")
    def test_falha_de_invoke_nao_mostra_traceback(self, tmp_path):
        arquivo = tmp_path / 'invoke.q'
        arquivo.write_text(
            '<q:component name="I" xmlns:q="https://quantum.lang/ns">'
            '<q:function name="soma"><q:param name="a" type="number" required="true"/>'
            '<q:set name="r" value="{a} + 1" type="number"/><q:return value="{r}"/>'
            '</q:function>'
            '<q:invoke name="x" function="soma"><q:param name="a" default="1"/></q:invoke>'
            '<q:return value="{x}"/></q:component>', encoding='utf-8')
        saida = subprocess.run(
            [sys.executable, '-m', 'quantum.cli.runner', 'run', str(arquivo)],
            capture_output=True, text=True, cwd=tmp_path, timeout=120,
            env=dict(os.environ, PYTHONPATH=str(REPO)))
        texto = saida.stdout + saida.stderr
        assert 'Traceback (most recent call last)' not in texto


@pytest.fixture
def servidor(tmp_path):
    """Servidor web real, em processo, com os componentes que o teste escrever."""
    from quantum.runtime.web_server import QuantumWebServer
    componentes = tmp_path / 'components'
    componentes.mkdir()
    config = tmp_path / 'config.yaml'
    config.write_text(
        f"server:\n  debug: true\npaths:\n  components: {componentes.as_posix()}\n"
        "  static: ./static\n  logs: ./logs\n"
        "logging:\n  level: ERROR\n  console: false\n  file: false\n",
        encoding='utf-8')

    def montar(**arquivos):
        for nome, conteudo in arquivos.items():
            (componentes / f'{nome}.q').write_text(conteudo, encoding='utf-8')
        server = QuantumWebServer(str(config))
        server.app.config['TESTING'] = True
        return server.app.test_client()
    return montar


DUAS_ACOES = (
    '<q:component name="acoes" xmlns:q="https://quantum.lang/ns">'
    '<q:action name="criar" method="POST"><q:redirect url="/criado"/></q:action>'
    '<q:action name="excluir" method="POST"><q:redirect url="/excluido"/></q:action>'
    '<p>x</p></q:component>')


class TestAplicacaoHtml:
    @lacuna("G17: `quantum run app.q` com q:application type=\"html\" e q:route "
            "falha na hora: QuantumWebServer.__init__() got an unexpected keyword "
            "argument 'port', e a linha seguinte chama configure_from_ast, que "
            "não existe. O modelo que funciona é components/ + quantum start. "
            "Decidir: implementar as rotas declaradas ou remover o tipo.")
    def test_aplicacao_html_sobe_o_servidor(self, tmp_path):
        app = tmp_path / 'app.q'
        app.write_text(
            '<q:application id="app" type="html" xmlns:q="https://quantum.lang/ns">'
            '<q:route path="/" method="GET"><h1>oi</h1></q:route></q:application>',
            encoding='utf-8')
        try:
            saida = subprocess.run(
                [sys.executable, '-m', 'quantum.cli.runner', 'run', str(app)],
                capture_output=True, text=True, cwd=tmp_path, timeout=10,
                env=dict(os.environ, PYTHONPATH=str(REPO)))
        except subprocess.TimeoutExpired:
            return      # continuou de pé servindo: é o comportamento esperado
        assert saida.returncode == 0, (saida.stdout + saida.stderr)[-300:]


class TestAplicacaoApi:
    @lacuna("G18: o servidor de q:application type=\"api\" não executa o corpo "
            "da rota — devolve o texto literal do primeiro q:return como JSON "
            "(ou {}), ignorando q:set, q:loop e q:query. E sobe em 0.0.0.0.")
    def test_rota_executa_o_corpo(self):
        from quantum.core.parser import QuantumParser
        from quantum.runtime.api_server import QuantumAPIServer
        app = QuantumParser().parse(
            '<q:application id="api" type="api" xmlns:q="https://quantum.lang/ns">'
            '<q:route path="/n" method="GET"><q:set name="n" value="41" type="number"/>'
            '<q:return value="{n + 1}"/></q:route></q:application>')
        server = QuantumAPIServer(port=0)
        server.configure_from_ast(app)
        resposta = server.app.test_client().get('/n')
        assert resposta.get_json() == 42


class TestImportDeDados:
    @lacuna("G16: q:data com arquivo inexistente devolve None em silêncio; o "
            "motivo só aparece em {nome_result.error}. Proposta: erro por "
            "padrão, nomeando o arquivo, com opt-in explícito para seguir.")
    def test_arquivo_inexistente_e_erro(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(Exception, match="naoexiste.csv"):
            executar('<q:data name="x" source="naoexiste.csv" type="csv"/>'
                     '<q:return value="{x}"/>')


class TestConfig:
    @lacuna("G4: ${VAR} em quantum.config.yaml é lido literalmente. A proposta "
            "é substituir pela variável de ambiente, ou recusar com erro que "
            "nomeie a variável ausente.")
    def test_variavel_de_ambiente_na_config_e_substituida(self, tmp_path, monkeypatch):
        from quantum.cli.runner import load_config
        (tmp_path / 'quantum.config.yaml').write_text(
            'datasources:\n  db:\n    driver: sqlite\n    database: ${QUANTUM_GAP_DB}\n',
            encoding='utf-8')
        monkeypatch.setenv('QUANTUM_GAP_DB', './data/app.db')
        config = load_config(str(tmp_path / 'quantum.config.yaml'))
        assert config['datasources']['db']['database'] == './data/app.db'
