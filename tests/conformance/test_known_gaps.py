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


class TestRetorno:
    @lacuna("G1: o q:return de topo é avaliado só no fim; um q:if verdadeiro "
            "depois dele vence. Hoje devolve 'B'.")
    def test_primeiro_return_em_ordem_de_documento_vence(self):
        assert executar(
            '<q:return value="A"/><q:set name="n" value="1"/>'
            '<q:if condition="n == 1"><q:return value="B"/></q:if>') == 'A'


class TestTiposDaInterpolacao:
    @lacuna("G2: interpolação com texto literal vira número. Hoje '{i}.{j}' "
            "devolve 1.2 (float).")
    def test_interpolacao_com_texto_e_texto(self):
        assert executar('<q:set name="i" value="1"/><q:set name="j" value="2"/>'
                        '<q:return value="{i}.{j}"/>') == '1.2'

    @lacuna("G2b: literal que parece número perde o formato. Hoje '007' "
            "devolve 7 — um CEP '01310' viraria 1310.")
    def test_literal_nao_e_convertido(self):
        assert executar('<q:return value="007"/>') == '007'

    def test_expressao_unica_mantem_o_tipo(self):
        # Não é lacuna: '{i}' sozinho devolve o valor com o tipo dele. Fica
        # aqui para que a correção das duas acima não quebre este caso.
        assert executar('<q:set name="i" value="7" type="number"/>'
                        '<q:return value="{i}"/>') == 7


class TestErrosDeExpressao:
    @lacuna("G12: variável inexistente fica literal na saída, em silêncio. "
            "Hoje devolve 'x{nada}y'.")
    def test_variavel_inexistente_e_erro_que_nomeia_a_variavel(self):
        with pytest.raises(Exception, match="nada"):
            executar('<q:return value="x{nada}y"/>')

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


class TestAcoes:
    def test_o_campo_action_escolhe_a_action(self, servidor):
        # Não é lacuna: com o campo `action` no corpo, a escolha funciona.
        cliente = servidor(acoes=DUAS_ACOES)
        r = cliente.post('/acoes', data={'action': 'excluir'})
        assert r.headers['Location'].endswith('/excluido')

    @lacuna("G6: com várias q:action, um nome inexistente (ou ausente) cai em "
            "silêncio na PRIMEIRA action. Um POST para 'excluir' com erro de "
            "digitação executa 'criar'.")
    def test_action_inexistente_nao_executa_outra(self, servidor):
        cliente = servidor(acoes=DUAS_ACOES)
        r = cliente.post('/acoes', data={'action': 'exclir'})
        assert r.status_code == 400
        assert 'exclir' in r.get_data(as_text=True)

    @lacuna("G7: dentro de q:action, {form.campo} sai vazio sem aviso — só "
            "campos declarados com q:param chegam, e a doc (data-fetching.md) "
            "ensina {form.name}. Proposta: ou o escopo form existe, ou usá-lo "
            "é erro que manda declarar o q:param.")
    def test_escopo_form_dentro_da_action(self, servidor):
        cliente = servidor(
            eco=('<q:component name="eco" xmlns:q="https://quantum.lang/ns">'
                 '<q:action name="salvar" method="POST">'
                 '<q:set name="session.visto" value="{form.nome}"/>'
                 '<q:redirect url="/eco"/></q:action>'
                 '<p>VISTO={session.visto}</p></q:component>'))
        cliente.post('/eco', data={'action': 'salvar', 'nome': 'ana'})
        assert 'VISTO=ana' in cliente.get('/eco').get_data(as_text=True)


class TestAutenticacao:
    @lacuna("AUTH-1: autenticação é Core (D4), mas um .q não tem como verificar "
            "uma senha contra um hash bcrypt sem q:python. Os exemplos de login "
            "gravam session.authenticated=true sem checar credencial nenhuma. "
            "Proposta: uma forma declarada de verificar credencial.")
    def test_existe_forma_declarada_de_verificar_senha(self):
        from quantum.core.parser import QuantumParser
        registradas = set(getattr(QuantumParser()._parser_registry, '_parsers', {}))
        assert registradas & {'auth', 'login', 'authenticate', 'verify-password'}


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
