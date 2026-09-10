r"""
Dois jeitos de o runtime descartar codigo do autor em silencio.

1. `<q:return>` dentro de `<q:if>` / `<q:else>` / `<q:loop>` era DESCARTADO
   pelo parser. Nao ha parser registrado para 'return' — o nivel de
   componente coleta os returns a parte, com _find_all_elements — entao um
   return aninhado caia no `return None` do dispatcher e sumia. O componente
   seguia adiante e devolvia o return seguinte, ou nada.

   `<q:if condition="n > 3"><q:return value="MAIOR"/></q:if>` nao retornava
   MAIOR. Sem erro, sem log.

2. Uma expressao que COMECAVA com chamada de q:function tinha o resto
   descartado. O desvio casava `^\s*(\w+)\s*\(` e mandava para
   _evaluate_function_call, cujo regex `(\w+)\((.*)\)` pega ate o ultimo
   parentese e ignora o que vem depois.

   `{dobro(a) * 10}` devolvia 10 em vez de 100 — e `{10 * dobro(a)}` dava
   100, porque nao comecava com a chamada. A MESMA conta com resultados
   diferentes conforme a ordem dos fatores.
"""

import pathlib
import tempfile

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.component import ComponentRuntime


def executar(corpo):
    caminho = pathlib.Path(tempfile.mkdtemp()) / 'c.q'
    caminho.write_text(f'<q:component name="C">{corpo}</q:component>',
                       encoding='utf-8')
    node = QuantumParser().parse_file(str(caminho))
    return ComponentRuntime().execute_component(node, {})


class TestReturnAninhado:
    def test_dentro_de_if_verdadeiro(self):
        assert executar(
            '<q:set name="n" value="5" type="number"/>'
            '<q:if condition="n > 3"><q:return value="MAIOR"/></q:if>'
            '<q:return value="fallback"/>') == 'MAIOR'

    def test_if_falso_segue_para_o_proximo(self):
        assert executar(
            '<q:set name="n" value="1" type="number"/>'
            '<q:if condition="n > 3"><q:return value="MAIOR"/></q:if>'
            '<q:return value="fallback"/>') == 'fallback'

    def test_dentro_de_else(self):
        assert executar(
            '<q:set name="n" value="1" type="number"/>'
            '<q:if condition="n > 3"><q:return value="MAIOR"/>'
            '<q:else><q:return value="MENOR"/></q:else></q:if>') == 'MENOR'

    def test_o_return_de_topo_continua_funcionando(self):
        assert executar('<q:return value="TOPO"/>') == 'TOPO'

    def test_o_parser_nao_descarta_mais_o_no(self):
        caminho = pathlib.Path(tempfile.mkdtemp()) / 'c.q'
        caminho.write_text(
            '<q:component name="C"><q:if condition="1 == 1">'
            '<q:return value="X"/></q:if></q:component>', encoding='utf-8')
        node = QuantumParser().parse_file(str(caminho))
        corpo = node.statements[0].if_body
        assert any(type(n).__name__ == 'QuantumReturn' for n in corpo), (
            f'o q:return sumiu do if_body: {[type(n).__name__ for n in corpo]}')


class TestReturnDentroDeLoop:
    """`<q:return>` dentro de `<q:loop>` era avaliado e JOGADO FORA.

    O LoopExecutor ate juntava os valores, mas o componente (e a funcao, e o
    q:if em volta) so tratava q:if como return — o resultado do loop era
    ignorado e o componente devolvia None. Os 7 exemplos do repo com esse
    padrao davam "Component executed without return", e o getting-started.md
    documentava uma saida que nenhuma versao do codigo produzia.

    A regra agora e a mesma do q:if: um loop que executou pelo menos um
    q:return encerra o corpo com a lista dos valores; um loop que nao
    executou nenhum deixa a execucao seguir.
    """

    def test_o_exemplo_do_getting_started(self):
        # docs/guide/getting-started.md, "Adding Dynamic Content", verbatim.
        assert executar(
            '<q:set name="greeting" value="Hello" />'
            '<q:loop type="list" var="name" items="Alice,Bob,Charlie">'
            '<q:return value="{greeting} {name}!" />'
            '</q:loop>') == ['Hello Alice!', 'Hello Bob!', 'Hello Charlie!']

    def test_if_dentro_do_loop_filtra(self):
        assert executar(
            '<q:loop type="range" var="i" from="1" to="5">'
            '<q:if condition="i % 2 == 0"><q:return value="par {i}"/></q:if>'
            '</q:loop>') == ['par 2', 'par 4']

    def test_loop_sem_return_segue_para_o_proximo(self):
        assert executar(
            '<q:set name="t" value="0" type="number"/>'
            '<q:loop type="range" var="i" from="1" to="3">'
            '<q:set name="t" operation="add" value="{i}"/></q:loop>'
            '<q:return value="Total {t}"/>') == 'Total 6'

    def test_filtro_que_nao_casa_segue_para_o_proximo(self):
        assert executar(
            '<q:loop type="range" var="i" from="1" to="3">'
            '<q:if condition="i > 10"><q:return value="{i}"/></q:if>'
            '</q:loop><q:return value="nenhum"/>') == 'nenhum'

    def test_loop_dentro_de_if_encerra_o_if(self):
        assert executar(
            '<q:set name="n" value="5" type="number"/>'
            '<q:if condition="n > 3">'
            '<q:loop type="range" var="i" from="1" to="2">'
            '<q:return value="x{i}"/></q:loop></q:if>'
            '<q:return value="fallback"/>') == ['x1', 'x2']

    def test_loop_aninhado_achata_como_o_guia_documenta(self):
        # docs/guide/loops.md, "Nested Loops": ["(1,1)", "(1,2)", "(2,1)", "(2,2)"]
        assert executar(
            '<q:loop type="range" var="x" from="1" to="2">'
            '<q:loop type="range" var="y" from="1" to="2">'
            '<q:return value="({x},{y})"/></q:loop></q:loop>'
        ) == ['(1,1)', '(1,2)', '(2,1)', '(2,2)']

    def test_return_de_uma_lista_continua_sendo_um_item(self):
        # So o resultado de um loop e achatado; um valor que por acaso e uma
        # lista entra inteiro.
        resultado = executar(
            '''<q:set name="par" value='["a", "b"]' type="array"/>'''
            '<q:loop type="range" var="i" from="1" to="2">'
            '<q:if condition="i > 0"><q:return value="{par}"/></q:if>'
            '</q:loop>')
        assert resultado == [['a', 'b'], ['a', 'b']]

    def test_funcao_devolve_a_lista_do_loop(self):
        assert str(executar(
            '<q:function name="pares">'
            '<q:loop type="range" var="i" from="1" to="6">'
            '<q:if condition="i % 2 == 0"><q:return value="{i}"/></q:if>'
            '</q:loop></q:function>'
            '<q:return value="{len(pares())}"/>')) == '3'

    def test_o_resultado_e_uma_lista_comum(self):
        # LoopReturns e um marcador interno; nao deve vazar para quem chama.
        resultado = executar(
            '<q:loop type="range" var="i" from="1" to="2">'
            '<q:return value="{i}"/></q:loop>')
        assert type(resultado) is list

    def test_valor_de_statement_que_nao_e_return_nao_entra(self):
        # Um q:query dentro do loop devolve linhas; isso nao e return e nao
        # pode fazer o loop "retornar" as linhas.
        from quantum.core.features.state_management.src.ast_node import SetNode
        from quantum.runtime.executors.control_flow.loop_executor import (
            LoopExecutor, LoopReturns)
        coletados = LoopReturns()
        LoopExecutor._collect(coletados, SetNode('x'), [{'linha': 1}])
        assert coletados == []


# Os outputs de docs/guide/loops.md (que eram fabricados) sao conferidos por
# tests/docs/test_guide_examples_run.py, junto com os das outras paginas.


class TestChamadaDeFuncaoEmExpressao:
    FUNCAO = ('<q:function name="dobro"><q:param name="x" type="number"/>'
              '<q:return value="{x * 2}"/></q:function>'
              '<q:set name="a" value="5" type="number"/>')

    @pytest.mark.parametrize("expressao,esperado", [
        ('{dobro(a)}', '10'),
        ('{dobro(a) * 10}', '100'),
        ('{10 * dobro(a)}', '100'),
        ('{dobro(a) + dobro(a)}', '20'),
        ('{dobro(a) - 1}', '9'),
    ])
    def test_a_expressao_inteira_e_avaliada(self, expressao, esperado):
        resultado = executar(
            self.FUNCAO + f'<q:set name="r" value="{expressao}"/>'
            '<q:return value="{r}"/>')
        assert str(resultado) == esperado

    def test_a_ordem_dos_fatores_nao_muda_o_resultado(self):
        # O sintoma que denunciou: `dobro(a) * 10` dava 10 e `10 * dobro(a)`
        # dava 100.
        um = executar(self.FUNCAO + '<q:return value="{dobro(a) * 10}"/>')
        outro = executar(self.FUNCAO + '<q:return value="{10 * dobro(a)}"/>')
        assert str(um) == str(outro) == '100'
