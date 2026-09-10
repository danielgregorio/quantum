"""Conformidade: SPEC.md seção 2b (Funções)."""

import pytest

from quantum.core.parser import QuantumParser, QuantumParseError

DOBRO = ('<q:function name="dobro"><q:param name="x" type="number" required="true"/>'
         '<q:return value="{x * 2}"/></q:function>')


class TestParametros:
    def test_argumento_convertido_para_o_tipo(self, executar):
        # FN-1: "21" vira numero antes do corpo
        assert executar(DOBRO + '<q:set name="t" value="21"/><q:return value="{dobro(t)}"/>') == 42

    @pytest.mark.parametrize('chamada,motivo', [
        ("reg('nao-email', 30)", "must be a valid email"),
        ("reg('a@b.co', 150)", "must be at most 100"),
        ("reg('a@b.co', 'abc')", "must be a number"),
    ])
    def test_regras_do_param_sempre_valem(self, executar, chamada, motivo):
        # FN-1 (antes: so com validate="true", e mesmo assim sem email e min/max)
        with pytest.raises(Exception, match=motivo):
            executar('<q:function name="reg"><q:param name="email" type="email" required="true"/>'
                     '<q:param name="idade" type="number" min="0" max="100"/>'
                     '<q:return value="ok"/></q:function>'
                     f'<q:return value="{{{chamada}}}"/>')

    def test_obrigatorio_ausente_e_erro(self, executar):
        # FN-1
        with pytest.raises(Exception, match="Required parameter 'x' not provided"):
            executar(DOBRO + '<q:return value="{dobro()}"/>')

    def test_argumento_por_nome(self, executar):
        # FN-1
        assert executar('<q:function name="f"><q:param name="a"/><q:param name="b" default="B"/>'
                        '<q:return value="{a}-{b}"/></q:function>'
                        '<q:return value="{f(b=\'y\', a=\'x\')} {f(\'z\')}"/>') == 'x-y z-B'


class TestAtributosQueNuncaFuncionaram:
    @pytest.mark.parametrize('atributo', [
        'memoize="true"', 'cache="60s"', 'async="true"', 'pure="true"', 'retry="3"',
        'access="private"', 'endpoint="/api/x"', 'scope="global"', 'validate="true"'])
    def test_sao_erro_de_parse(self, atributo):
        # FN-2
        with pytest.raises(QuantumParseError, match='is not supported'):
            QuantumParser().parse(f'<q:component name="C" xmlns:q="https://quantum.lang/ns">'
                                  f'<q:function name="f" {atributo}><q:return value="1"/></q:function>'
                                  '</q:component>')


class TestFuncaoNoHtml:
    def test_chamada_no_conteudo_da_pagina(self, servidor):
        # FN-3 (antes: <p>{dobro(21)}</p> saia literal)
        cliente = servidor(p='<q:component name="p" xmlns:q="https://quantum.lang/ns">'
                             + DOBRO + '<p>R={dobro(21)}</p></q:component>')
        assert 'R=42' in cliente.get('/p').get_data(as_text=True)
