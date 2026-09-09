"""
Uma variavel de sessao PRESENTE era lida como vazia.

Regressao introduzida nesta sessao pela migracao para o avaliador AST. O
contexto guarda a variavel de escopo sob a CHAVE PLANA pontilhada
('session.userId') porque e uma BUSCA; o avaliador le `session.userId` como
Attribute(Name('session'), 'userId'), nao acha objeto `session` nenhum, e
levanta. Quem chamava traduzia isso em '' (databinding) ou False (condicao).

O codigo anterior tinha `if expr in context: return context[expr]` e
resolvia. A migracao removeu esse atalho do runtime e o manteve no
HTMLRenderer — entao a MESMA pagina mostrava:

    copia=[]  direto=[42]

O `copia` vinha de `<q:set value="{session.userId}"/>` e o `direto` da
interpolacao do renderer. Dois caminhos, duas verdades.

Consequencias reproduzidas: um INSERT gravou `user_id=''` com
session.userId='42', sem erro e sem log; e `<q:if condition="{session.papel
== 'admin'}">` era False nos DOIS ramos, entao nem o conteudo de admin nem a
mensagem de acesso negado apareciam.

Por que a suite nao viu: os testes de escopo so cobriam a variavel AUSENTE
(resolver para '' e o contrato) e as condicoes so usavam contexto vazio, onde
falhar para False parece seguro. Nenhum testava o caso PRESENTE.

A documentacao ensina exatamente estes padroes — docs/guide/query.md,
docs/guide/conditionals.md, docs/examples/authentication.md — entao o defeito
atingia quem seguia o guia.
"""

import pathlib
import tempfile

import pytest

from quantum.core.expressions import ExpressionEvaluator, ExpressionError
from quantum.core.parser import QuantumParser
from quantum.runtime.component import ComponentRuntime
from quantum.runtime.renderer import HTMLRenderer

ESCOPOS = ['session', 'application', 'request']


def executar(corpo, escopo='session', variaveis=None):
    fonte = f'<q:component name="S">{corpo}</q:component>'
    caminho = pathlib.Path(tempfile.mkdtemp()) / 's.q'
    caminho.write_text(fonte, encoding='utf-8')
    node = QuantumParser().parse_file(str(caminho))

    runtime = ComponentRuntime()
    runtime.execute_component(node, {f'_{escopo}_scope': variaveis or {}})
    html = HTMLRenderer(runtime.execution_context).render(node)
    return runtime, html


class TestOValorPresenteChega:
    def test_q_set_copia_o_valor(self):
        runtime, _ = executar('<q:set name="copia" value="{session.userId}" />',
                              variaveis={'userId': '42'})
        assert runtime.execution_context.get_all_variables()['copia'] == '42'

    def test_a_interpolacao_mostra_o_valor(self):
        _, html = executar('<p>[{session.userId}]</p>', variaveis={'userId': '42'})
        assert '[42]' in html

    def test_os_dois_caminhos_concordam(self):
        # O sintoma que denunciou o bug: copia=[] e direto=[42] na MESMA
        # pagina. Um valor so pode ter uma verdade.
        _, html = executar(
            '<q:set name="copia" value="{session.userId}" />'
            '<p>copia=[{copia}] direto=[{session.userId}]</p>',
            variaveis={'userId': '42'})
        assert 'copia=[42] direto=[42]' in html

    @pytest.mark.parametrize("escopo", ESCOPOS)
    def test_vale_para_todos_os_escopos(self, escopo):
        runtime, _ = executar(f'<q:set name="c" value="{{{escopo}.chave}}" />',
                              escopo=escopo, variaveis={'chave': 'valor'})
        assert runtime.execution_context.get_all_variables()['c'] == 'valor'

    def test_o_valor_chega_a_um_parametro_de_query(self):
        # Foi assim que o dado errado chegou ao banco: o parametro recebia ''.
        runtime, _ = executar(
            '<q:set name="p" value="{session.userId}" />',
            variaveis={'userId': '42'})
        assert runtime.execution_context.get_all_variables()['p'] != ''


class TestAsCondicoesEnxergamOEscopo:
    def test_condicao_simples_verdadeira(self):
        _, html = executar(
            '<q:if condition="{session.autenticado}"><p>ENTROU</p></q:if>',
            variaveis={'autenticado': True})
        assert 'ENTROU' in html

    def test_comparacao_com_igual(self):
        _, html = executar(
            '<q:if condition="{session.papel == \'admin\'}"><p>ADMIN</p></q:if>',
            variaveis={'papel': 'admin'})
        assert 'ADMIN' in html

    def test_o_ramo_negativo_tambem_funciona(self):
        # O pior sintoma: os DOIS ramos eram falsos, entao nem o conteudo
        # protegido nem a mensagem de acesso negado apareciam.
        _, html = executar(
            '<q:if condition="{session.papel != \'admin\'}"><p>NEGADO</p></q:if>',
            variaveis={'papel': 'leitor'})
        assert 'NEGADO' in html

    def test_a_guarda_nao_deixa_passar_quem_nao_deve(self):
        _, html = executar(
            '<q:if condition="{session.papel == \'admin\'}"><p>ADMIN</p></q:if>',
            variaveis={'papel': 'leitor'})
        assert 'ADMIN' not in html


class TestOContratoDoAusenteContinua:
    """Resolver '' quando a variavel NAO existe e proposital: a pagina
    renderiza antes do login. O conserto nao pode ter apagado isso."""

    def test_ausente_vira_vazio(self):
        runtime, _ = executar('<q:set name="c" value="{session.naoExiste}" />',
                              variaveis={'userId': '42'})
        assert runtime.execution_context.get_all_variables()['c'] == ''

    def test_escopo_inteiro_ausente_vira_vazio(self):
        runtime, _ = executar('<q:set name="c" value="{session.qualquer}" />')
        assert runtime.execution_context.get_all_variables()['c'] == ''

    def test_condicao_sobre_ausente_e_falsa(self):
        _, html = executar(
            '<q:if condition="{session.naoExiste}"><p>X</p></q:if>')
        assert '<p>X</p>' not in html


class TestOAcessoAAtributoDeVerdadeContinua:
    """A chave plana nao pode ter atropelado o acesso a atributo real."""

    def avaliar(self, expr, ctx):
        return ExpressionEvaluator().evaluate(expr, ctx)

    def test_atributo_de_objeto(self):
        objeto = type('O', (), {'nome': 'ok'})()
        assert self.avaliar('obj.nome', {'obj': objeto}) == 'ok'

    def test_chave_de_dicionario_por_ponto(self):
        assert self.avaliar('d.a', {'d': {'a': 1}}) == 1

    def test_a_chave_plana_vence_quando_existe(self):
        # Se as duas existirem, a chave plana e a que o framework grava.
        ctx = {'session.x': 'plana', 'session': type('O', (), {'x': 'objeto'})()}
        assert self.avaliar('session.x', ctx) == 'plana'

    def test_encadeamento_sobre_chamada_nao_vira_chave(self):
        # `f(x).nome` nao pode virar busca pela chave "f(x).nome".
        with pytest.raises(ExpressionError):
            self.avaliar('naoExiste(1).nome', {})

    def test_atributo_inexistente_ainda_levanta(self):
        with pytest.raises(ExpressionError):
            self.avaliar('d.b', {'d': {'a': 1}})
