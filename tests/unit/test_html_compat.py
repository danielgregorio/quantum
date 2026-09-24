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

from quantum.core.html_compat import normalise_html
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

    @pytest.mark.parametrize("body,tag", [
        ('if (a && b) { x = "required" }', 'script'),
        ('.a { content: "&"; }', 'style'),
        # What did not parse: markup inside a template literal.
        ('l.innerHTML = t.map(x => `<div class="i">${x}</div>`).join("")',
         'script'),
        ('if (a < b && c > d) { required = 1 }', 'script'),
    ])
    def test_the_code_inside_script_and_style_arrives_intact(self, body, tag):
        """The assertion here used to be `normalise_html(src) == src` — TEXTUAL
        identity, a proxy for "the code was not corrupted".

        The proxy stopped holding when `<script>`/`<style>` started being
        wrapped in CDATA (without it, markup inside a template literal —
        `${x}` in an attribute, an unclosed `<div>` — made the whole file fail
        to parse: components/islands_demo.q returned HTTP 400). What matters is
        the CODE, and that is what the test looks at now: after normalising
        AND going through the XML parser, the body comes back character for
        character.
        """
        from xml.etree import ElementTree as ET

        source = f'<root><{tag}>{body}</{tag}></root>'
        tree = ET.fromstring(normalise_html(source))
        assert tree.find(tag).text == body

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


class TestWhatTheReAuditFound:
    """Three defects in the parser's tolerance, all reproduced first."""

    def parse(self, body):
        import pathlib
        import tempfile
        from quantum.core.parser import QuantumParser
        f = pathlib.Path(tempfile.mkdtemp()) / 'c.q'
        f.write_text(f'<q:component name="C">{body}</q:component>',
                     encoding='utf-8')
        return QuantumParser().parse_file(str(f))

    # --- PascalCase component vs void element ---

    @pytest.mark.parametrize("tag", ["Link", "Input", "Source", "Meta",
                                     "Base", "Col", "Area", "Track"])
    def test_a_pascalcase_component_does_not_become_void(self, tag):
        # `name.lower() in VOID_ELEMENTS` matched a component with a void
        # element: <Link>c</Link> became `<Link />c</Link>`, self-closed and
        # with an orphan closing tag. A void element is an HTML concept, and
        # HTML is written in lowercase.
        out = normalise_html(f'<{tag} t="x">content</{tag}>')
        assert out == f'<{tag} t="x">content</{tag}>'

    @pytest.mark.parametrize("tag", ["br", "input", "meta", "img", "hr"])
    def test_a_real_void_element_still_closes(self, tag):
        assert normalise_html(f'<{tag}>').rstrip().endswith('/>')

    # --- named HTML entities ---

    @pytest.mark.parametrize("entity,char", [
        ('&nbsp;', '\xa0'), ('&copy;', '©'), ('&mdash;', '—'),
        ('&rarr;', '→'), ('&eacute;', 'é'),
    ])
    def test_a_named_entity_parses(self, entity, char):
        # XML predefines FIVE entities; HTML defines thousands. `&nbsp;` — the
        # most used of all — gave "undefined entity" and HTTP 400. This module
        # exists to accept the HTML people write and stopped one step short of
        # its own mission.
        self.parse(f'<p>a{entity}b</p>')
        assert char in normalise_html(f'<p>a{entity}b</p>') or \
            f'&#{ord(char)};' in normalise_html(f'<p>a{entity}b</p>')

    @pytest.mark.parametrize("entity", ['&lt;', '&gt;', '&amp;', '&quot;'])
    def test_the_five_xml_ones_stay_as_they_are(self, entity):
        assert entity in normalise_html(f'<p>{entity}</p>')

    def test_a_nonexistent_entity_is_still_an_error(self):
        # A name that does not exist is a typo, and a typo has to show.
        with pytest.raises(Exception):
            self.parse('<p>&doesNotExistAtAll;</p>')

    def test_an_entity_in_an_attribute_value(self):
        self.parse('<p title="a&nbsp;b">x</p>')

    # --- an entity inside q:python ---

    def test_an_escaped_entity_inside_q_python(self):
        # The automatic CDATA wrapping turned decoding off: inside CDATA
        # nothing is decoded, so `if a &lt; 10:` reached exec() with the
        # literal `&lt;`. It broke 6 shipped .q files, which used the escaped
        # form because it was the only one that worked.
        from quantum.runtime.executors.scripting.python_executor import (
            normalise_python_source)
        node = self.parse(
            '<q:python>\na = 5\nif a &lt; 10:\n    q.r = 1\n</q:python>')
        code = next(st.code for st in node.statements
                    if type(st).__name__ == 'PythonNode')
        compile(normalise_python_source(code), '<t>', 'exec')

    def test_a_raw_sign_inside_q_python_still_works(self):
        from quantum.runtime.executors.scripting.python_executor import (
            normalise_python_source)
        node = self.parse(
            '<q:python>\na = 5\nif a < 10:\n    q.r = 1\n</q:python>')
        code = next(st.code for st in node.statements
                    if type(st).__name__ == 'PythonNode')
        compile(normalise_python_source(code), '<t>', 'exec')

    @pytest.mark.parametrize("path", [
        'examples/python-scripting.q',
        'quantum_admin/components/admin/applications.q',
        'quantum_admin/components/admin/connectors.q',
        'quantum_admin/components/admin/settings.q',
    ])
    def test_the_shipped_files_compile(self, path):
        import pathlib
        from quantum.core.parser import QuantumParser
        from quantum.runtime.executors.scripting.python_executor import (
            normalise_python_source)

        repo = pathlib.Path(__file__).resolve().parents[2]
        node = QuantumParser().parse_file(str(repo / path))
        for st in getattr(node, 'statements', []):
            if type(st).__name__ in ('PythonNode', 'PyClassNode'):
                compile(normalise_python_source(st.code), '<t>', 'exec')
