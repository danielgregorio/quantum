"""
Os tres alvos discordavam sobre o que `completed` significa num ui:stepper.

A regra certa (a do adapter html): o atributo explicito vence; sem atributo,
um passo esta concluido se esta atras do atual. `linear` nao entra nisso.

Cada alvo tinha a sua versao:

- desktop: `list(range(current)) if linear else []`. Num stepper NAO-linear
  emitia lista vazia, e como a ponte roda depois do markup estatico ela
  APAGAVA no boot as marcas que o html tinha desenhado certo. E
  `_as_bool(completed, False)` colapsava "nao setado" e "setado como false",
  entao um passo com `completed="false"` antes do atual ganhava a marca de
  volta.
- textual: `set_class(position < index, "q-step-done")` no on_mount,
  sobrescrevendo o que o compose tinha desenhado — `completed` nao tinha
  efeito nenhum.

Agora ha uma funcao so, `completed_step_indices`, e estes testes existem para
que os tres nao voltem a divergir: cada caso e verificado nos TRES alvos
contra a mesma expectativa.
"""

import pathlib
import re
import tempfile

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.ui_builder import UIBuilder
from quantum.runtime.ui_html_adapter import completed_step_indices


def build(corpo, target):
    fonte = ('<q:application id="T" type="ui"><ui:window title="t">'
             + corpo + '</ui:window></q:application>')
    caminho = pathlib.Path(tempfile.mkdtemp()) / 't.q'
    caminho.write_text(fonte, encoding='utf-8')
    app = QuantumParser().parse_file(str(caminho))
    return UIBuilder().build(app, target=target)


def marcados_no_html(corpo):
    html = build(corpo, 'html')
    classes = re.findall(r'class="(q-step-item[^"]*)"', html)
    return [i for i, c in enumerate(classes) if 'completed' in c]


def marcados_no_textual(corpo):
    tui = build(corpo, 'textual')
    classes = re.findall(r'classes="(q-step-indicator[^"]*)"', tui)
    return [i for i, c in enumerate(classes) if 'q-step-done' in c]


def marcados_na_ponte_desktop(corpo):
    """A lista do stepper, nao o booleano de cada passo.

    O spec sai como JSON (aspas duplas) e a chave `completed` aparece nos
    dois niveis: uma LISTA no stepper e um BOOLEANO em cada passo. Pegar a
    primeira ocorrencia dava o valor errado.
    """
    desk = build(corpo, 'desktop')
    achado = re.search(r'"completed":\s*\[([^\]]*)\]', desk)
    if not achado:
        return []
    dentro = achado.group(1).strip()
    return [int(n) for n in dentro.split(',') if n.strip()]


CASOS = {
    'progresso implicito':
        ('<ui:stepper current="2"><ui:step title="A"/><ui:step title="B"/>'
         '<ui:step title="C"/><ui:step title="D"/></ui:stepper>', [0, 1]),
    'nao-linear tem o mesmo progresso':
        ('<ui:stepper current="2" linear="false"><ui:step title="A"/>'
         '<ui:step title="B"/><ui:step title="C"/><ui:step title="D"/>'
         '</ui:stepper>', [0, 1]),
    'completed=false explicito vence a posicao':
        ('<ui:stepper current="2"><ui:step title="A" completed="false"/>'
         '<ui:step title="B"/><ui:step title="C"/></ui:stepper>', [1]),
    'completed=true vence a posicao':
        ('<ui:stepper current="0"><ui:step title="A"/>'
         '<ui:step title="B" completed="true"/></ui:stepper>', [1]),
    'primeiro passo, nada concluido':
        ('<ui:stepper current="0"><ui:step title="A"/><ui:step title="B"/>'
         '</ui:stepper>', []),
}


@pytest.mark.parametrize("nome", list(CASOS))
class TestOsTresAlvosConcordam:
    def test_html(self, nome):
        corpo, esperado = CASOS[nome]
        assert marcados_no_html(corpo) == esperado

    def test_textual(self, nome):
        corpo, esperado = CASOS[nome]
        assert marcados_no_textual(corpo) == esperado

    def test_desktop(self, nome):
        corpo, esperado = CASOS[nome]
        assert marcados_na_ponte_desktop(corpo) == esperado


class TestARegraSozinha:
    """A funcao compartilhada, sem passar por adapter nenhum."""

    class Passo:
        def __init__(self, completed=None):
            self.completed = completed

    def test_sem_atributo_usa_a_posicao(self):
        passos = [self.Passo(), self.Passo(), self.Passo()]
        assert completed_step_indices(passos, 2) == [0, 1]

    def test_explicito_true_vence(self):
        passos = [self.Passo(), self.Passo('true')]
        assert completed_step_indices(passos, 0) == [1]

    def test_explicito_false_vence(self):
        passos = [self.Passo('false'), self.Passo(), self.Passo()]
        assert completed_step_indices(passos, 2) == [1]

    def test_aceita_booleano_de_verdade(self):
        passos = [self.Passo(True), self.Passo(False)]
        assert completed_step_indices(passos, 2) == [0]

    @pytest.mark.parametrize("escrito", ['true', '1', 'yes', 'on', 'TRUE', ' true '])
    def test_as_formas_escritas_de_verdadeiro(self, escrito):
        assert completed_step_indices([self.Passo(escrito)], 0) == [0]

    @pytest.mark.parametrize("escrito", ['false', '0', 'no', 'off', 'talvez', ''])
    def test_qualquer_outra_coisa_e_falso(self, escrito):
        # Lista de PERMISSAO, igual a UIHtmlAdapter._as_bool. Uma lista de
        # negacao trataria "talvez" como concluido.
        assert completed_step_indices([self.Passo(escrito)], 1) == []

    def test_sem_passos(self):
        assert completed_step_indices([], 0) == []
