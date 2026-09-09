"""
Dois atributos documentados que o alvo textual descartava em silencio.

1. `<ui:toast show="temErro">` — o binding virava um COMENTARIO no codigo
   gerado (`self.q_toast_1()  # show="temErro"`) e o toast disparava
   incondicionalmente. Um toast de erro aparecia em todo lancamento do app,
   tivesse erro ou nao. Nao e atributo faltando: e o oposto do que ele pede.

2. `<ui:step icon="OK">` — nunca chegava a lugar nenhum, nem no indicador
   nem no painel. O adapter html usa `step.icon if step.icon else str(i+1)`.

O primeiro exigiu um ponto unico de escrita de estado: os widgets escreviam
direto em `self._q_state`, entao nada podia REAGIR a uma mudanca, e era por
isso que `show=` so podia virar comentario.

Estes testes olham o codigo GERADO. Verificar que ele roda pediria Textual
headless; o que segura o defeito aqui e a diferenca entre "chama sempre" e
"chama sob condicao", que se ve na geracao.
"""

import pathlib
import tempfile

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.ui_builder import UIBuilder


def gerar(corpo):
    fonte = ('<q:application id="T" type="ui"><ui:window title="t">'
             + corpo + '</ui:window></q:application>')
    caminho = pathlib.Path(tempfile.mkdtemp()) / 't.q'
    caminho.write_text(fonte, encoding='utf-8')
    app = QuantumParser().parse_file(str(caminho))
    return UIBuilder().build(app, target='textual')


class TestOToastRespeitaOShow:
    def test_com_show_a_chamada_e_condicional(self):
        code = gerar('<ui:toast message="deu erro" show="temErro" variant="danger" />')
        assert '_q_truthy(self._q_state.get("temErro"))' in code

    def test_com_show_nao_dispara_incondicionalmente(self):
        code = gerar('<ui:toast message="deu erro" show="temErro" />')
        linhas = [l.strip() for l in code.splitlines()]
        # A chamada existe, mas nunca solta na coluna do corpo de
        # _q_show_toasts: ela vive dentro do if.
        soltas = [l for l in linhas if l == 'self.q_toast_1()']
        indentadas = [l for l in code.splitlines()
                      if l.strip() == 'self.q_toast_1()' and l.startswith('            ')]
        assert indentadas, "a chamada deveria estar dentro do if"
        assert len(soltas) == len(indentadas), (
            "ha uma chamada incondicional sobrando")

    def test_sem_show_continua_disparando(self):
        code = gerar('<ui:toast message="ola" variant="info" />')
        assert 'self.q_toast_1()' in code
        assert '_q_truthy' not in code.split('def q_toast_1')[0].split(
            'def _q_show_toasts')[-1]

    def test_o_binding_nao_e_mais_so_um_comentario(self):
        code = gerar('<ui:toast message="x" show="temErro" />')
        assert '# show="temErro"' not in code

    def test_ele_dispara_quando_a_variavel_muda_depois(self):
        # "escondido ate ficar verdadeiro" nao pode virar "nunca".
        code = gerar('<ui:toast message="x" show="temErro" />')
        assert 'def _q_toast_on_state' in code
        assert 'if name == "temErro"' in code

    def test_dispara_uma_vez_so(self):
        code = gerar('<ui:toast message="x" show="temErro" />')
        assert '_q_toasts_shown' in code, "sem memoria, repetiria a cada mudanca"


class TestOEstadoTemUmPontoUnicoDeEscrita:
    """Sem isso, nada consegue reagir a uma mudanca de estado."""

    def test_o_helper_existe(self):
        code = gerar('<ui:carousel><ui:slide>a</ui:slide></ui:carousel>')
        assert 'def _q_set_state' in code

    def test_os_widgets_escrevem_por_ele(self):
        code = gerar('<ui:carousel bind="atual"><ui:slide>a</ui:slide></ui:carousel>')
        assert 'self._q_set_state(info["bind"]' in code
        assert 'self._q_state[info["bind"]] =' not in code

    @pytest.mark.parametrize("valor,esperado", [
        ("", False), ("false", False), ("FALSE", False), ("0", False),
        ("no", False), ("off", False), ("  ", False),
        ("true", True), ("sim", True), ("qualquer texto", True),
        (None, False), (False, False), (True, True),
        (0, False), (1, True), ([], False), (["a"], True),
    ])
    def test_a_nocao_de_verdadeiro(self, valor, esperado):
        """A mesma nocao que o alvo html usa num binding.

        Executa o bloco de runtime do proprio modulo em vez de fatiar o
        codigo gerado: fatiar string quebra assim que a assinatura muda — foi
        o que aconteceu na primeira versao deste teste — e o que importa aqui
        e a semantica, nao o formato da geracao.
        """
        from quantum.runtime import ui_textual_adapter as mod

        ns = {}
        exec(mod._STATE_ACCESSOR, ns)
        assert ns["_q_truthy"](None, valor) is esperado


class TestOIconeDoPasso:
    def test_o_icone_aparece_no_indicador(self):
        code = gerar('<ui:stepper><ui:step title="Conta" icon="OK"/></ui:stepper>')
        assert 'OK' in code

    def test_sem_icone_usa_o_numero(self):
        code = gerar('<ui:stepper><ui:step title="Conta"/></ui:stepper>')
        assert '"1. Conta"' in code

    def test_o_icone_substitui_o_numero(self):
        # Mesmo contrato do html: `step.icon if step.icon else str(i + 1)`.
        code = gerar('<ui:stepper><ui:step title="Conta" icon="OK"/></ui:stepper>')
        assert '"OK. Conta"' in code
        assert '"1. Conta"' not in code
