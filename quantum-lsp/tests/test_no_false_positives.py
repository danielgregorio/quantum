"""
O language server acusava codigo correto — em massa.

Medido no comeco: **643 diagnosticos em 129 de 253 arquivos .q que o framework
parseia limpo**. Falso positivo em massa e o que faz alguem desligar o
servidor, e ai ele deixa de valer para os erros de verdade tambem.

Tres causas estruturais, todas consertadas:

1. O regex de tag parava no PRIMEIRO `>`, mesmo dentro de aspas, entao
   `<q:if condition="a > b">` era cortado e virava "Missing required
   attribute 'condition'" em codigo valido.
2. O esquema mantinha uma lista de tags A MAO — 76 entradas contra 95 no
   registry do framework — e acusava `q:python`, `q:queue`, `ui:card-body`
   como desconhecidas.
3. "Tag desconhecida" era emitida mesmo em documento que o FRAMEWORK aceita.
   Dezenas de tags sao filhas parseadas pelo parser do pai (q:tool dentro de
   q:agent, q:column dentro de q:data) e por isso nunca estarao no registry.
   Quem decide o que e tag valida e o framework.

O resto e deriva de dados: enum sem um valor, atributo marcado obrigatorio
que nao e. Este teste existe para que essa deriva seja VISIVEL e limitada, em
vez de crescer calada: ele mede a taxa contra os proprios arquivos do
repositorio e falha se ela piorar.
"""

import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
LSP = REPO / "quantum-lsp"
for caminho in (str(LSP), str(REPO)):
    if caminho not in sys.path:
        sys.path.insert(0, caminho)

from quantum.core.parser import QuantumParser  # noqa: E402
from quantum_lsp.analysis.document import QuantumDocument  # noqa: E402
from quantum_lsp.handlers.diagnostics import validate_document  # noqa: E402

# Teto atual. Baixe-o quando consertar mais; nunca suba sem motivo escrito.
MAX_ARQUIVOS_COM_DIAGNOSTICO = 34
MAX_DIAGNOSTICOS = 82


def arquivos_que_o_framework_aceita():
    for pasta in ("examples", "components"):
        for caminho in (REPO / pasta).rglob("*.q"):
            texto = caminho.read_text(encoding="utf-8", errors="replace")
            try:
                QuantumParser().parse_file(str(caminho))
            except Exception:
                continue          # o framework rejeita: nao e falso positivo
            yield caminho, texto


@pytest.fixture(scope="module")
def medicao():
    arquivos = com = total = 0
    piores = []
    for caminho, texto in arquivos_que_o_framework_aceita():
        arquivos += 1
        achados = validate_document(QuantumDocument("file:///x.q", texto))
        if achados:
            com += 1
            total += len(achados)
            piores.append((caminho.name, len(achados), achados[0].message[:70]))
    piores.sort(key=lambda x: -x[1])
    return {"arquivos": arquivos, "com": com, "total": total, "piores": piores}


class TestATaxaDeFalsoPositivo:
    def test_ha_arquivos_para_medir(self, medicao):
        assert medicao["arquivos"] > 200, medicao["arquivos"]

    def test_o_numero_de_arquivos_afetados_nao_piorou(self, medicao):
        assert medicao["com"] <= MAX_ARQUIVOS_COM_DIAGNOSTICO, (
            f"{medicao['com']} arquivos corretos recebem diagnostico "
            f"(teto {MAX_ARQUIVOS_COM_DIAGNOSTICO}). Piores: "
            f"{medicao['piores'][:3]}")

    def test_o_numero_de_diagnosticos_nao_piorou(self, medicao):
        assert medicao["total"] <= MAX_DIAGNOSTICOS, (
            f"{medicao['total']} diagnosticos falsos (teto {MAX_DIAGNOSTICOS}). "
            f"Piores: {medicao['piores'][:3]}")


class TestAsCausasEstruturaisContinuamConsertadas:
    def diagnosticar(self, fonte):
        return [d.message for d in
                validate_document(QuantumDocument("file:///t.q", fonte))]

    @pytest.mark.parametrize("condicao", ["a > b", "a >= b", "a < b", "x > 1 && y < 2"])
    def test_operador_no_valor_do_atributo(self, condicao):
        # O regex parava no primeiro `>` e truncava a lista de atributos.
        fonte = (f'<q:component name="C"><q:if condition="{condicao}">'
                 f'<p>x</p></q:if></q:component>')
        assert self.diagnosticar(fonte) == []

    @pytest.mark.parametrize("tag", ["q:python", "q:queue", "q:agent", "q:thread"])
    def test_tag_que_o_registry_conhece(self, tag):
        # A lista a mao tinha 76 entradas; o registry tem 95.
        from quantum_lsp.schema import is_known_tag
        assert is_known_tag(tag), f"{tag} esta no registry e o LSP nao conhece"

    def test_tag_filha_nao_e_acusada(self):
        # q:tool e parseada pelo parser de q:agent e nunca estara no registry
        # de tags de topo; vem da lista NESTED_TAGS.
        fonte = ('<q:component name="C"><q:agent name="a" model="m">'
                 '<q:tool name="t" description="d" /></q:agent></q:component>')
        assert not any("Unknown tag" in m for m in self.diagnosticar(fonte))

    def test_tag_inventada_continua_sendo_acusada(self):
        # Uma versao intermediaria suprimia "tag desconhecida" sempre que o
        # FRAMEWORK aceitasse o documento — e o framework IGNORA em silencio
        # uma tag `q:` que nao conhece: `<q:naoexiste/>` vira HTMLNode e some.
        # Aquilo apagava a deteccao de digitacao, que e valiosa exatamente
        # PORQUE o framework e silencioso.
        fonte = '<q:component name="C"><q:naoExisteMesmo /></q:component>'
        assert any("naoExisteMesmo" in m for m in self.diagnosticar(fonte))

    @pytest.mark.parametrize("tipo", ["number", "integer", "decimal", "float",
                                      "string", "boolean"])
    def test_tipos_que_o_runtime_aceita(self, tipo):
        fonte = (f'<q:component name="C">'
                 f'<q:set name="n" value="1" type="{tipo}" /></q:component>')
        assert not any("Invalid value" in m for m in self.diagnosticar(fonte))

    def test_redirect_aceita_as_duas_grafias(self):
        for atributo in ("url", "to"):
            fonte = (f'<q:component name="C"><q:action name="a">'
                     f'<q:redirect {atributo}="/x" /></q:action></q:component>')
            assert not any("required" in m for m in self.diagnosticar(fonte))
