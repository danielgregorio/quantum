"""Conformidade: SPEC.md seções 1 (Retorno) e 2 (Repetição)."""


class TestRetorno:
    def test_primeiro_return_em_ordem_de_documento_vence(self, executar):
        # RET-1 (era a lacuna G1: o return de topo era adiado e um q:if depois vencia)
        assert executar(
            '<q:return value="A"/><q:set name="n" value="1"/>'
            '<q:if condition="n == 1"><q:return value="B"/></q:if>') == 'A'

    def test_return_de_topo_depois_de_comandos(self, executar):
        # RET-1
        assert executar('<q:set name="x" value="ok"/><q:return value="{x}"/>'
                        '<q:return value="nunca"/>') == 'ok'

    def test_expressao_unica_mantem_o_tipo(self, executar):
        # RET-2
        assert executar('<q:set name="i" value="7" type="number"/>'
                        '<q:return value="{i}"/>') == 7

    def test_interpolacao_com_texto_e_texto(self, executar):
        # RET-2 (era G2: "{i}.{j}" virava o número 1.2)
        assert executar('<q:set name="i" value="1"/><q:set name="j" value="2"/>'
                        '<q:return value="{i}.{j}"/>') == '1.2'

    def test_literal_nao_e_convertido(self, executar):
        # RET-2 (era G2b: "007" virava 7)
        assert executar('<q:return value="007"/>') == '007'
        assert executar('<q:return value="01310-000"/>') == '01310-000'

    def test_return_dentro_de_if_encerra(self, executar):
        # RET-3
        assert executar('<q:set name="n" value="5" type="number"/>'
                        '<q:if condition="n > 3"><q:return value="MAIOR"/></q:if>'
                        '<q:return value="fallback"/>') == 'MAIOR'

    def test_if_sem_return_executado_segue(self, executar):
        # RET-3
        assert executar('<q:set name="n" value="1" type="number"/>'
                        '<q:if condition="n > 3"><q:return value="MAIOR"/></q:if>'
                        '<q:return value="fallback"/>') == 'fallback'


class TestRepeticao:
    def test_cada_return_vira_um_item(self, executar):
        # LOOP-1
        assert executar('<q:loop type="range" var="i" from="1" to="3">'
                        '<q:return value="n{i}"/></q:loop>') == ['n1', 'n2', 'n3']

    def test_loop_com_return_encerra_o_corpo(self, executar):
        # LOOP-2
        assert executar('<q:loop type="range" var="i" from="1" to="2">'
                        '<q:return value="{i}"/></q:loop><q:return value="depois"/>') == [1, 2]

    def test_loop_sem_return_deixa_seguir(self, executar):
        # LOOP-2
        assert executar('<q:loop type="range" var="i" from="1" to="3">'
                        '<q:if condition="i > 10"><q:return value="{i}"/></q:if>'
                        '</q:loop><q:return value="nenhum"/>') == 'nenhum'

    def test_loop_aninhado_achata(self, executar):
        # LOOP-3
        assert executar('<q:loop type="range" var="x" from="1" to="2">'
                        '<q:loop type="range" var="y" from="1" to="2">'
                        '<q:return value="({x},{y})"/></q:loop></q:loop>'
                        ) == ['(1,1)', '(1,2)', '(2,1)', '(2,2)']

    def test_valor_lista_entra_como_um_item(self, executar):
        # LOOP-3
        assert executar('''<q:set name="par" value='["a", "b"]' type="array"/>'''
                        '<q:loop type="range" var="i" from="1" to="2">'
                        '<q:if condition="i > 0"><q:return value="{par}"/></q:if>'
                        '</q:loop>') == [['a', 'b'], ['a', 'b']]
