"""
The parser now accepts the HTML people actually write.

A .q file is XML but its body is HTML, and three things every HTML author
writes are invalid XML:

  - boolean attributes:  <input required autofocus />
  - bare ampersands:     Forms & Actions,  href="/x?a=1&b=2"
  - unclosed void tags:  <br>, <meta charset="utf-8">

TEN of the forty-eight components shipped WITH the framework failed to parse
for exactly these reasons — login.q among them — and returned HTTP 400. The
error told the author to escape the character, which is true and useless: the
file was written the way HTML is written.

The rewrite tests below are as important as the acceptance ones. A
source-rewriting pass is the riskiest change in this area, and my first two
attempts broke things that had been fine:

  - a greedy attribute run swallowed the `/` of an already self-closed tag, so
    `<meta ... />` became `<meta ... / />`;
  - the tag pattern did not understand quoted values, so the `>` inside
    `expression="parseInt(value) >= 18"` cut the tag short and ate a space.

Both are pinned here.
"""

import pytest

from quantum.core.html_compat import normalise_html, BOOLEAN_ATTRS, VOID_ELEMENTS
from quantum.core.parser import QuantumParser


class TestBooleanAttributes:
    @pytest.mark.parametrize("src,expected", [
        ('<input required />', '<input required="required" />'),
        ('<input type="text" required>', '<input type="text" required="required" />'),
        ('<option selected>a</option>', '<option selected="selected">a</option>'),
    ])
    def test_expanded(self, src, expected):
        assert normalise_html(src) == expected

    def test_a_word_in_text_is_not_an_attribute(self):
        assert normalise_html('<p>this is required reading</p>') == \
            '<p>this is required reading</p>'

    def test_a_value_containing_the_word_is_untouched(self):
        assert normalise_html('<input value="required" />') == \
            '<input value="required" />'

    def test_only_known_names_expand(self):
        """An arbitrary bare word must not become an attribute — that would
        turn a typo into something silently accepted."""
        out = normalise_html('<div bogusattr>x</div>')
        assert 'bogusattr="bogusattr"' not in out


class TestAmpersands:
    def test_in_text(self):
        assert normalise_html('<p>Forms & Actions</p>') == '<p>Forms &amp; Actions</p>'

    def test_in_an_attribute_value(self):
        assert normalise_html('<a href="/x?a=1&b=2">l</a>') == \
            '<a href="/x?a=1&amp;b=2">l</a>'

    @pytest.mark.parametrize("entity", ['&amp;', '&lt;', '&gt;', '&#39;', '&#x27;', '&quot;'])
    def test_real_entities_are_left_alone(self, entity):
        src = f'<p>{entity}</p>'
        assert normalise_html(src) == src


class TestVoidElements:
    @pytest.mark.parametrize("src,expected", [
        ('<br>', '<br/>'),
        ('<p>a<br>b</p>', '<p>a<br/>b</p>'),
        ('<img src="a.png">', '<img src="a.png" />'),
    ])
    def test_closed(self, src, expected):
        assert normalise_html(src) == expected

    def test_already_closed_is_not_doubled(self):
        """`<meta ... />` became `<meta ... / />` in the first attempt."""
        assert normalise_html('<meta charset="UTF-8" />') == '<meta charset="UTF-8" />'
        assert '/ /' not in normalise_html('<meta charset="UTF-8" />')

    def test_non_void_tags_are_not_self_closed(self):
        assert normalise_html('<div class="x">t</div>') == '<div class="x">t</div>'


class TestItDoesNotCorruptCode:
    def test_a_greater_than_inside_an_attribute_survives(self):
        """The regression a real test caught: `parseInt(value) >= 18` lost a
        space because the tag pattern stopped at the `>`."""
        src = '<q:validator expression="parseInt(value) >= 18" />'
        assert normalise_html(src) == src

    @pytest.mark.parametrize("src", [
        '<![CDATA[ if (a && b) required ]]>',
        '<!-- a & b, required -->',
    ])
    def test_protected_regions_are_untouched(self, src):
        assert normalise_html(src) == src

    @pytest.mark.parametrize("corpo,tag", [
        ('if (a && b) { x = "required" }', 'script'),
        ('.a { content: "&"; }', 'style'),
        # O que nao parseava: markup dentro de um template literal.
        ('l.innerHTML = t.map(x => `<div class="i">${x}</div>`).join("")',
         'script'),
        ('if (a < b && c > d) { required = 1 }', 'script'),
    ])
    def test_o_codigo_dentro_de_script_e_style_chega_intacto(self, corpo, tag):
        """A assercao aqui era `normalise_html(src) == src` — identidade
        TEXTUAL, um proxy para "o codigo nao foi corrompido".

        O proxy deixou de valer quando `<script>`/`<style>` passaram a ser
        embrulhados em CDATA (sem isso, markup dentro de um template
        literal — `${x}` num atributo, `<div>` nao fechado — fazia o
        arquivo inteiro nao parsear: components/islands_demo.q devolvia
        HTTP 400). O que importa e o CODIGO, e e nisso que o teste olha
        agora: depois de normalizar E de passar pelo parser XML, o corpo
        volta caractere por caractere.
        """
        from xml.etree import ElementTree as ET

        fonte = f'<root><{tag}>{corpo}</{tag}></root>'
        arvore = ET.fromstring(normalise_html(fonte))
        assert arvore.find(tag).text == corpo

    def test_closing_tags_are_untouched(self):
        assert normalise_html('</div>') == '</div>'


class TestTheShippedComponentsParse:
    """The measurement that motivated all of it."""

    @pytest.mark.parametrize("name", [
        "login.q", "contact_form.q", "htmx_demo.q", "products.q",
        "contact_success.q", "dev_tools_demo.q",
    ])
    def test_parses(self, name):
        import pathlib
        path = pathlib.Path(__file__).resolve().parents[2] / "components" / name
        if not path.exists():
            pytest.skip(f"{name} not present")
        QuantumParser().parse(path.read_text(encoding="utf-8", errors="ignore"))


class TestOQueAReAuditoriaAchou:
    """Tres defeitos da tolerancia do parser, todos reproduzidos antes."""

    def parse(self, corpo):
        import pathlib, tempfile
        from quantum.core.parser import QuantumParser
        f = pathlib.Path(tempfile.mkdtemp()) / 'c.q'
        f.write_text(f'<q:component name="C">{corpo}</q:component>',
                     encoding='utf-8')
        return QuantumParser().parse_file(str(f))

    # --- componente PascalCase x void element ---

    @pytest.mark.parametrize("tag", ["Link", "Input", "Source", "Meta",
                                     "Base", "Col", "Area", "Track"])
    def test_componente_pascalcase_nao_vira_void(self, tag):
        # `name.lower() in VOID_ELEMENTS` casava componente com void element:
        # <Link>c</Link> virava `<Link />c</Link>`, auto-fechado e com a tag
        # de fechamento orfa. Void element e conceito de HTML, e HTML se
        # escreve em minusculas.
        saida = normalise_html(f'<{tag} t="x">conteudo</{tag}>')
        assert saida == f'<{tag} t="x">conteudo</{tag}>'

    @pytest.mark.parametrize("tag", ["br", "input", "meta", "img", "hr"])
    def test_void_element_de_verdade_continua_fechando(self, tag):
        assert normalise_html(f'<{tag}>').rstrip().endswith('/>')

    # --- entidades HTML nomeadas ---

    @pytest.mark.parametrize("entidade,caractere", [
        ('&nbsp;', '\xa0'), ('&copy;', '©'), ('&mdash;', '—'),
        ('&rarr;', '→'), ('&eacute;', 'é'),
    ])
    def test_entidade_nomeada_parseia(self, entidade, caractere):
        # XML predefine CINCO entidades; HTML define milhares. `&nbsp;` — a
        # mais usada de todas — dava "undefined entity" e HTTP 400. Este
        # modulo existe para aceitar o HTML que as pessoas escrevem e parava
        # um passo antes da propria missao.
        self.parse(f'<p>a{entidade}b</p>')
        assert caractere in normalise_html(f'<p>a{entidade}b</p>') or \
            f'&#{ord(caractere)};' in normalise_html(f'<p>a{entidade}b</p>')

    @pytest.mark.parametrize("entidade", ['&lt;', '&gt;', '&amp;', '&quot;'])
    def test_as_cinco_do_xml_ficam_como_estao(self, entidade):
        assert entidade in normalise_html(f'<p>{entidade}</p>')

    def test_entidade_inexistente_ainda_e_erro(self):
        # Um nome que nao existe e typo, e typo tem de aparecer.
        import pytest as _p
        with _p.raises(Exception):
            self.parse('<p>&naoExisteMesmo;</p>')

    def test_entidade_no_valor_de_atributo(self):
        self.parse('<p title="a&nbsp;b">x</p>')

    # --- entidade dentro de q:python ---

    def test_entidade_escapada_dentro_de_q_python(self):
        # O embrulho automatico em CDATA desligou a decodificacao: dentro de
        # CDATA nada e decodificado, entao `if a &lt; 10:` chegava ao exec()
        # com o `&lt;` literal. Quebrou 6 arquivos .q entregues, que usavam a
        # forma escapada porque era a unica que funcionava.
        from quantum.runtime.executors.scripting.python_executor import (
            normalise_python_source)
        node = self.parse(
            '<q:python>\na = 5\nif a &lt; 10:\n    q.r = 1\n</q:python>')
        codigo = next(st.code for st in node.statements
                      if type(st).__name__ == 'PythonNode')
        compile(normalise_python_source(codigo), '<t>', 'exec')

    def test_sinal_cru_dentro_de_q_python_continua(self):
        from quantum.runtime.executors.scripting.python_executor import (
            normalise_python_source)
        node = self.parse(
            '<q:python>\na = 5\nif a < 10:\n    q.r = 1\n</q:python>')
        codigo = next(st.code for st in node.statements
                      if type(st).__name__ == 'PythonNode')
        compile(normalise_python_source(codigo), '<t>', 'exec')

    @pytest.mark.parametrize("caminho", [
        'examples/python-scripting.q',
        'components/admin/applications.q',
        'components/admin/connectors.q',
        'components/admin/settings.q',
    ])
    def test_os_arquivos_entregues_compilam(self, caminho):
        import pathlib
        from quantum.core.parser import QuantumParser
        from quantum.runtime.executors.scripting.python_executor import (
            normalise_python_source)

        repo = pathlib.Path(__file__).resolve().parents[2]
        node = QuantumParser().parse_file(str(repo / caminho))
        for st in getattr(node, 'statements', []):
            if type(st).__name__ in ('PythonNode', 'PyClassNode'):
                compile(normalise_python_source(st.code), '<t>', 'exec')
