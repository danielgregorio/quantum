"""
O JavaScript compartilhado dos componentes UI saia invalido do Python.

TOAST_JS e CALENDAR_JS viviam em strings triplas NAO-raw. Uma linha como

    html += '<button onclick="__quantumToast.dismiss(\\'' + id + '\\')">'

perde as barras na compilacao do Python, e o browser recebe

    dismiss('' + id + '')

que e erro de sintaxe. Erro de sintaxe derruba o MODULO INTEIRO: nem
`__quantumToast` nem `__quantumCalendar` chegavam a existir, entao nenhum
toast fechava e nenhum calendario navegava — em nenhuma pagina, desde sempre.

Ninguem viu porque o JS emitido nunca foi verificado por nada. Estes testes
verificam a saida, nao a fonte, e cobrem os runtimes todos — o defeito e da
FORMA de escrever o template, e o proximo runtime escrito do mesmo jeito
falharia igual.
"""

import re

import pytest

from quantum.runtime import ui_html_templates as templates

# `('' + x + '')` — aspas que colapsaram. O par correto e `('\' + x + '\')`.
COLAPSADO = re.compile(r"\(''\s*\+|\+\s*''\)")

RUNTIMES = [name for name in dir(templates)
            if name.endswith('_JS') and isinstance(getattr(templates, name), str)]


def linhas_de_codigo(source):
    return [line for line in source.splitlines()
            if not line.strip().startswith('//')]


class TestOsRuntimesCompartilhados:
    def test_existem_runtimes_para_checar(self):
        # Se o modulo for renomeado, este arquivo passa a testar nada.
        assert RUNTIMES, "nenhum *_JS encontrado em ui_html_templates"

    @pytest.mark.parametrize("nome", RUNTIMES)
    def test_nenhuma_aspa_colapsada(self, nome):
        source = getattr(templates, nome)
        ruins = [l.strip() for l in linhas_de_codigo(source) if COLAPSADO.search(l)]
        assert ruins == [], f"{nome} emite JS invalido: {ruins[:3]}"

    @pytest.mark.parametrize("nome", RUNTIMES)
    def test_as_aspas_aninhadas_sobrevivem(self, nome):
        # O padrao correto no JS emitido e `('\' + id + '\')`.
        source = getattr(templates, nome)
        aninhadas = [l for l in linhas_de_codigo(source)
                     if re.search(r"\\'\s*\+", l)]
        colapsadas = [l for l in linhas_de_codigo(source) if COLAPSADO.search(l)]
        if aninhadas or colapsadas:
            assert not colapsadas, f"{nome} tem aspa aninhada colapsada"

    def test_o_toast_consegue_ser_fechado(self):
        # O handler que o botao de fechar chama tem de sair com o id entre
        # aspas de verdade.
        assert re.search(r"dismiss\(\\'", templates.TOAST_JS), \
            "o onclick do botao de fechar sai com sintaxe invalida"

    def test_o_calendario_consegue_navegar(self):
        for funcao in ('prevMonth', 'nextMonth', 'selectDate'):
            assert re.search(funcao + r"\(\\'", templates.CALENDAR_JS), \
                f"{funcao} sai com sintaxe invalida"


class TestAPaginaGerada:
    """A fonte estar certa nao basta: o que importa e o que chega no browser."""

    @pytest.fixture(scope="class")
    def pagina(self):
        import pathlib
        from quantum.core.parser import QuantumParser
        from quantum.runtime.ui_builder import UIBuilder

        repo = pathlib.Path(__file__).resolve().parents[2]
        app = QuantumParser().parse_file(
            str(repo / "examples" / "test-ui-components-new.q"))
        return UIBuilder().build(app, target='html')

    def test_a_pagina_nao_leva_js_invalido(self, pagina):
        ruins = [l.strip() for l in pagina.splitlines()
                 if COLAPSADO.search(l) and not l.strip().startswith('//')]
        assert ruins == [], ruins

    def test_o_adapter_nao_conserta_a_saida(self):
        # Houve um regex no adapter reparando o JS DEPOIS de gerado. Consertar
        # a saida deixa a causa de pe: o proximo runtime escrito do mesmo
        # jeito volta a quebrar, em silencio.
        from quantum.runtime.ui_html_adapter import UIHtmlAdapter

        sujo = "dismiss('' + id + '')"
        assert UIHtmlAdapter()._emit_runtime(sujo) == sujo, (
            "_emit_runtime esta remendando a saida em vez de a fonte estar certa")
