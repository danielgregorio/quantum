"""A tolerancia de HTML valia para um caminho de leitura de `.q`, nao tres.

`normalise_html` existe porque um `.q` e XML mas o corpo dele e HTML, e o
HTML que as pessoas escrevem — `<input required>`, `<br>`, `Forms &
Actions`, `condition="n < 0"`, o corpo Python de um `<q:python>` — nao e XML
valido. `QuantumParser.parse` a chama. Outros dois lugares leem `.q` e
chamam `ET.fromstring` direto, sem ela:

  * `QuantumParser._parse_scene_include` (scene-include de jogos): um `<br>`
    ou um `&` cru num arquivo de cena dava "scene-include: parse error" num
    arquivo que o parser normal aceita.
  * `component_discovery.QuantumParser._validate_xml` (admin): marcava o
    componente com "XML parse error" na tela, sem nada para o autor
    consertar. Reprovava 177 dos 484 arquivos .q do repositorio.

O validador do admin errava ainda por duas razoes do proprio embrulho:
ele punha `<root>` na frente de uma declaracao `<?xml?>` ("XML or text
declaration not at start of entity") e so declarava o prefixo `q:`, entao
`qg:`, `qt:`, `ui:` e `qtest:` davam "unbound prefix".
"""

import pathlib
import sys

import pytest

ADMIN = pathlib.Path(__file__).resolve().parents[2] / "quantum_admin"
for path in (str(ADMIN), str(ADMIN / "backend")):
    if path not in sys.path:
        sys.path.insert(0, path)


def _validador():
    import importlib
    modulo = importlib.import_module('backend.component_discovery')
    return modulo.QuantumParser._validate_xml


class TestOValidadorDoAdmin:
    @pytest.mark.parametrize("fonte", [
        '<q:component name="A"><input required /></q:component>',
        '<q:component name="A"><p>Forms & Actions</p></q:component>',
        '<q:component name="A"><br></q:component>',
        '<q:component name="A"><meta charset="utf-8"></q:component>',
        '<q:component name="A"><q:if condition="n < 0">x</q:if></q:component>',
        '<q:component name="A"><p>a&nbsp;b</p></q:component>',
    ])
    def test_html_comum_nao_e_erro(self, fonte):
        assert _validador()(fonte) == [], fonte

    def test_uma_declaracao_xml_no_topo_nao_e_erro(self):
        fonte = '<?xml version="1.0" encoding="UTF-8"?>\n<q:component name="A" />'
        assert _validador()(fonte) == []

    @pytest.mark.parametrize("prefixo", ['qg', 'qt', 'ui', 'qtest'])
    def test_os_outros_prefixos_do_framework_nao_sao_erro(self, prefixo):
        fonte = f'<q:component name="A"><{prefixo}:algo x="1" /></q:component>'
        assert _validador()(fonte) == [], prefixo

    def test_um_erro_estrutural_de_verdade_continua_sendo_reportado(self):
        """A tolerancia nao pode virar "aceita tudo"."""
        assert _validador()('<q:component name="A"><div></q:component>')
        assert _validador()('<q:component name="A"><p>x</q:span></q:component>')

    def test_os_arquivos_entregues_no_repositorio_passam(self):
        """177 dos 484 .q do repositorio eram reprovados."""
        raiz = pathlib.Path(__file__).resolve().parents[2]
        arquivos = [a for a in raiz.rglob('*.q')
                    if 'node_modules' not in str(a)
                    and 'dataset' not in a.parts]
        reprovados = []
        for a in arquivos:
            try:
                texto = a.read_text(encoding='utf-8')
            except Exception:
                continue
            if _validador()(texto):
                reprovados.append(a.relative_to(raiz))

        assert len(arquivos) > 200, "os .q do repositorio sumiram?"
        # Sobram poucos, e sao arquivos que o proprio framework tambem
        # recusa (JS com markup solto dentro de <script>).
        assert len(reprovados) <= 10, (len(reprovados), reprovados[:15])


class TestJavaScriptComMarkupDentro:
    """`<script>` e `<style>` sao texto cru em HTML e nao em XML.

    Um template literal com markup dentro nao e XML — `${t.completed ?
    'checked' : ''}` dentro de uma tag e um token invalido. E o autor nao
    tinha o que fazer a nao ser escrever CDATA a mao em volta do proprio
    JavaScript. components/islands_demo.q, entregue no repositorio,
    devolvia HTTP 400 por isso.
    """

    def _parse(self, corpo):
        from quantum.core.parser import QuantumParser
        return QuantumParser(use_cache=False).parse(
            f'<q:component name="C">{corpo}</q:component>')

    def test_um_template_literal_com_markup_parseia(self):
        self._parse(
            '<script>'
            'lista.innerHTML = todos.map(t => `'
            '<div class="item ${t.completed ? "done" : ""}">'
            '<input type="checkbox" ${t.completed ? "checked" : ""} />'
            '</div>`).join("");'
            '</script>')

    def test_comparacoes_com_menor_que_parseiam(self):
        self._parse('<script>for (var i = 0; i < n; i++) { soma += i; }</script>')

    def test_o_codigo_chega_intacto_ao_html(self):
        from quantum.runtime.renderer import HTMLRenderer
        from quantum.runtime.execution_context import ExecutionContext
        codigo = 'if (a < b && c > d) { x = "1"; }'
        ast = self._parse(f'<script>{codigo}</script>')
        html = HTMLRenderer(ExecutionContext()).render(ast)
        assert codigo in html, html

    def test_o_islands_demo_do_repositorio_parseia(self):
        from quantum.core.parser import QuantumParser
        raiz = pathlib.Path(__file__).resolve().parents[2]
        alvo = raiz / 'components' / 'islands_demo.q'
        if not alvo.exists():
            pytest.skip("o arquivo nao esta neste checkout")
        QuantumParser(use_cache=False).parse_file(str(alvo))


class TestSceneInclude:
    def test_html_comum_num_arquivo_incluido_nao_quebra(self, tmp_path):
        from quantum.core.parser import QuantumParser

        (tmp_path / "cena.q").write_text(
            '<qg:scene name="fase1" xmlns:qg="https://quantum.lang/game">\n'
            '  <qg:sprite name="heroi" x="0" y="0" />\n'
            '</qg:scene>\n',
            encoding='utf-8')
        jogo = tmp_path / "jogo.q"
        jogo.write_text(
            '<q:application id="j" type="game">\n'
            '  <qg:scene-include src="cena.q" />\n'
            '</q:application>\n',
            encoding='utf-8')

        ast = QuantumParser(use_cache=False).parse_file(str(jogo))
        assert [c.name for c in ast.scenes] == ["fase1"]

    def test_um_e_comercial_cru_num_arquivo_incluido(self, tmp_path):
        """`&` cru: valido em HTML, invalido em XML. Ia direto para o
        ET.fromstring do scene-include."""
        from quantum.core.parser import QuantumParser

        (tmp_path / "cena.q").write_text(
            '<qg:scene name="fase1" xmlns:qg="https://quantum.lang/game">\n'
            '  <qg:sprite name="Vidas & Pontos" x="0" y="0" />\n'
            '</qg:scene>\n',
            encoding='utf-8')
        jogo = tmp_path / "jogo.q"
        jogo.write_text(
            '<q:application id="j" type="game">\n'
            '  <qg:scene-include src="cena.q" />\n'
            '</q:application>\n',
            encoding='utf-8')

        ast = QuantumParser(use_cache=False).parse_file(str(jogo))
        assert [c.name for c in ast.scenes] == ["fase1"]


class TestOsNamespacesQueOFrameworkInjeta:
    """A deteccao de "ja tem namespace" era por SUBSTRING.

    `if 'xmlns:q' in content` casa com `xmlns:qt=`, `xmlns:qg=` e
    `xmlns:qtest=`. Um arquivo que declarava so o namespace da propria
    engine caia no ramo "ja declarado", onde toda injecao era um
    `content.replace('xmlns:q="https://quantum.lang/ns"', ...)` que nao
    achava nada — entao NENHUM namespace era declarado e o arquivo morria
    com "unbound prefix" na linha 1, coluna 0.

    E so tres raizes eram reconhecidas (`q:component`, `q:application`,
    `q:job`): um arquivo cuja raiz e `<q:prefab>`, `<q:behavior>` ou
    `<qg:scene>` — 15 arquivos entregues no repositorio — nao recebia
    namespace nenhum.
    """

    def _parse(self, fonte):
        from quantum.core.parser import QuantumParser
        return QuantumParser(use_cache=False).parse(fonte)

    def test_declarar_so_o_qt_nao_esconde_o_q(self):
        self._parse('<q:application id="t" type="terminal" '
                    'xmlns:qt="https://quantum.lang/terminal">'
                    '<qt:screen name="m" /></q:application>')

    def test_declarar_so_o_qg_nao_esconde_o_q(self):
        self._parse('<q:application id="j" type="game" '
                    'xmlns:qg="https://quantum.lang/game">'
                    '<qg:scene name="s" /></q:application>')

    def test_declarar_so_o_qtest_nao_esconde_o_q(self):
        self._parse('<q:application id="t" type="testing" '
                    'xmlns:qtest="https://quantum.lang/testing">'
                    '<q:set name="x" value="1" /></q:application>')

    def test_uma_raiz_desconhecida_da_o_nome_do_elemento(self):
        """Antes: "unbound prefix: line 1, column 0". Agora o parser chega
        ate a mensagem que diz qual e a raiz."""
        from quantum.core.parser import QuantumParseError
        with pytest.raises(QuantumParseError, match="Unknown root element: prefab"):
            self._parse('<q:prefab name="P"><qg:sprite src="x.png" /></q:prefab>')

    def test_um_comentario_no_topo_nao_recebe_os_namespaces(self):
        """examples/python-scripting.q abre com um comentario que menciona
        `<cfscript>`; injetar ali deixaria o componente sem namespace."""
        fonte = (
            '<?xml version="1.0"?>' + chr(10) +
            '<!-- inspirado no <cfscript> do ColdFusion -->' + chr(10) +
            '<q:component name="C"><p>oi</p></q:component>')
        assert self._parse(fonte).name == 'C'

    def test_o_namespace_que_o_autor_declarou_e_respeitado(self):
        fonte = ('<q:component name="C" xmlns:q="https://quantum.lang/ns">'
                 '<p>oi</p></q:component>')
        assert self._parse(fonte).name == 'C'

    def test_os_arquivos_de_cena_e_prefab_do_repositorio_sao_bem_formados(self):
        """Eles nao sao raizes validas (sao includes), mas o XML tem de
        estar correto: o erro deve ser "Unknown root element", nunca um
        erro de parse."""
        from quantum.core.parser import QuantumParser, QuantumParseError
        raiz = pathlib.Path(__file__).resolve().parents[2]
        arquivos = (list((raiz / 'examples').rglob('prefabs/*.q'))
                    + list((raiz / 'examples').rglob('behaviors/*.q'))
                    + list((raiz / 'examples').rglob('scenes/*.q')))
        assert arquivos, "os fragmentos sumiram?"
        for a in arquivos:
            try:
                QuantumParser(use_cache=False).parse_file(str(a))
            except QuantumParseError as exc:
                assert 'Unknown root element' in str(exc), (a, str(exc)[:120])
