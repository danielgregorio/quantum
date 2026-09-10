"""
A documentacao ensinava codigo que nao parseia.

Dez dos 82 exemplos completos em docs/guide nao passavam pelo parser — e um
deles estava no `quick-start.md`, a segunda pagina que alguem le. Para quem
esta avaliando o projeto, a primeira tentativa de copiar e colar falhava.

Oito eram a mesma causa: `<` cru dentro do valor de um atributo, que e o que
as pessoas naturalmente escrevem:

    <q:if condition="n < 0">
    <q:return value="<h1>Oi</h1>" />

Isso foi consertado no PARSER, nao na documentacao. `&` cru e atributo
booleano ja eram tolerados; `<` seguia a mesma logica e faltava. Consertar a
doc deixaria todo arquivo de usuario com a mesma sintaxe natural quebrado.

Este teste existe para que a doc nao volte a divergir do que o framework
aceita — nos dois sentidos. Se alguem escrever um exemplo que nao parseia,
falha aqui; se alguem apertar o parser, tambem.
"""

import pathlib
import re
import tempfile

import pytest

from quantum.core.parser import QuantumParser

REPO = pathlib.Path(__file__).resolve().parents[2]
GUIDE = REPO / "docs" / "guide"
FENCE = "`" * 3

# Trechos deliberadamente incompletos: ilustram convencao de nome com um
# `<!-- Good -->` / `<!-- Avoid -->` e uma linha cada, sem fechar a tag.
# Nao sao exemplos para copiar.
INCOMPLETOS = {"components.md"}


def exemplos():
    """Cada bloco cercado que contem um componente ou aplicacao completa."""
    for doc in sorted(GUIDE.glob("*.md")):
        texto = doc.read_text(encoding="utf-8", errors="replace")
        for i, (lingua, bloco) in enumerate(
                re.findall(FENCE + r"([a-z]*)\n(.*?)" + FENCE, texto, re.S)):
            if lingua == "text":        # saida de terminal, nao codigo
                continue
            if "<q:component" not in bloco and "<q:application" not in bloco:
                continue
            yield doc.name, i, bloco


TODOS = list(exemplos())


class TestOsExemplosDaDocumentacao:
    def test_existem_exemplos_para_checar(self):
        # Se a extracao quebrar, este arquivo passa a testar nada.
        assert len(TODOS) > 50, f"so achei {len(TODOS)} exemplos"

    @pytest.mark.parametrize(
        "nome,indice,bloco",
        [c for c in TODOS if c[0] not in INCOMPLETOS],
        ids=[f"{c[0]}#{c[1]}" for c in TODOS if c[0] not in INCOMPLETOS],
    )
    def test_parseia(self, nome, indice, bloco):
        caminho = pathlib.Path(tempfile.mkdtemp()) / "doc.q"
        caminho.write_text(bloco, encoding="utf-8")
        QuantumParser().parse_file(str(caminho))


class TestASintaxeNaturalEAceita:
    """O que a doc ensina tem de funcionar quando o usuario escreve igual."""

    def parse(self, fonte):
        caminho = pathlib.Path(tempfile.mkdtemp()) / "n.q"
        caminho.write_text(fonte, encoding="utf-8")
        return QuantumParser().parse_file(str(caminho))

    @pytest.mark.parametrize("condicao", [
        "n < 0", "n <= 1", "n > 0", "n >= 1",
        "a && b", "a || b", "a < b && c > d",
        "item.type == 'fruit' && item.price < 1.00",
    ])
    def test_operadores_em_condition(self, condicao):
        self.parse(f'<q:component name="C"><q:if condition="{condicao}">'
                   f'<p>x</p></q:if></q:component>')

    def test_html_dentro_de_um_valor(self):
        self.parse('<q:component name="C">'
                   '<q:return value="<h1>Oi</h1>" /></q:component>')

    def test_o_valor_chega_intacto_ao_autor(self):
        # `&lt;` faz round-trip: o parser XML desfaz a escapada, entao quem
        # escreveu `<h1>` recebe `<h1>` de volta.
        from quantum.runtime.component import ComponentRuntime

        node = self.parse('<q:component name="C">'
                          '<q:return value="<h1>Oi</h1>" /></q:component>')
        assert ComponentRuntime().execute_component(node, {}) == "<h1>Oi</h1>"

    def test_aspas_simples_tambem(self):
        self.parse("<q:component name=\"C\"><q:if condition='n < 3'>"
                   "<p>x</p></q:if></q:component>")

    def test_o_maior_que_continua_funcionando(self):
        # Ja era tolerado; a mudanca do `<` nao pode ter mexido nisso.
        self.parse('<q:component name="C">'
                   '<q:validator expression="parseInt(value) >= 18" />'
                   '</q:component>')
