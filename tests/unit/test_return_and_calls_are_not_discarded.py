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
