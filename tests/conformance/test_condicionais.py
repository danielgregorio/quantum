"""Conformidade: SPEC.md seção 2a (Condicionais)."""

import re

import pytest

IRMAO = ('<q:if condition="n % 2 == 0"><q:return value="{n} par"/></q:if>'
         '<q:elseif condition="n == 3"><q:return value="{n} tres"/></q:elseif>'
         '<q:else><q:return value="{n} impar"/></q:else>')

ANINHADO = ('<q:if condition="n % 2 == 0"><q:return value="{n} par"/>'
            '<q:elseif condition="n == 3"><q:return value="{n} tres"/></q:elseif>'
            '<q:else><q:return value="{n} impar"/></q:else></q:if>')


class TestElseIrmaoEAninhado:
    @pytest.mark.parametrize('forma', [IRMAO, ANINHADO], ids=['irmao', 'aninhado'])
    def test_no_corpo_do_componente(self, executar, forma):
        # IF-1
        assert executar('<q:set name="n" value="3" type="number"/>' + forma) == '3 tres'

    @pytest.mark.parametrize('forma', [IRMAO, ANINHADO], ids=['irmao', 'aninhado'])
    def test_dentro_de_loop(self, executar, forma):
        # IF-1 (antes: o else irmao dentro de q:loop era descartado)
        assert executar(f'<q:loop type="range" var="n" from="1" to="4">{forma}</q:loop>') == \
            ['1 impar', '2 par', '3 tres', '4 par']

    @pytest.mark.parametrize('forma', [IRMAO, ANINHADO], ids=['irmao', 'aninhado'])
    def test_dentro_de_funcao(self, executar, forma):
        # IF-1 (antes: q:function com elseif/else irmao devolvia None)
        assert executar(f'<q:function name="f"><q:param name="n" type="number"/>{forma}</q:function>'
                        '<q:return value="{f(1)}|{f(2)}|{f(3)}"/>') == '1 impar|2 par|3 tres'

    def test_dentro_do_else_de_outro_if(self, executar):
        # IF-1
        assert executar('<q:set name="a" value="false" type="boolean"/><q:set name="n" value="5" type="number"/>'
                        '<q:if condition="a"><q:return value="a"/></q:if>'
                        f'<q:else>{IRMAO}</q:else>') == '5 impar'

    def test_em_html_renderizado(self, servidor):
        # IF-1 (antes: o <li> do else nunca aparecia na pagina)
        cliente = servidor(lista=(
            '<q:component name="lista" xmlns:q="https://quantum.lang/ns"><ul>'
            '<q:loop type="range" var="n" from="1" to="3">'
            '<q:if condition="n == 2"><li>dois</li></q:if>'
            '<q:else><li>outro {n}</li></q:else>'
            '</q:loop></ul></q:component>'))
        html = cliente.get('/lista').get_data(as_text=True)
        assert re.findall(r'<li>\s*(.*?)\s*</li>', html) == ['outro 1', 'dois', 'outro 3']

    @pytest.mark.parametrize('corpo', [
        '<q:else><q:return value="x"/></q:else>',
        '<q:loop type="range" var="n" from="1" to="2"><q:set name="x" value="1"/>'
        '<q:elseif condition="n"><q:return value="x"/></q:elseif></q:loop>',
    ], ids=['topo', 'loop'])
    def test_else_sem_if_antes_e_erro(self, executar, corpo):
        # IF-1
        with pytest.raises(Exception, match='has no matching <q:if>'):
            executar(corpo)
