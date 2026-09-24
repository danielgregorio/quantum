"""HTML tolerance applied to one path that reads `.q` files, not three.

`normalise_html` exists because a `.q` is XML but its body is HTML, and the
HTML people write — `<input required>`, `<br>`, `Forms & Actions`,
`condition="n < 0"`, the Python body of a `<q:python>` — is not valid XML.
`QuantumParser.parse` calls it. Two other places read `.q` and called
`ET.fromstring` directly, without it:

  * `QuantumParser._parse_scene_include` (games' scene-include): a `<br>` or a
    raw `&` in a scene file gave "scene-include: parse error" on a file the
    normal parser accepts.
  * `component_discovery.QuantumParser._validate_xml` (admin): it marked the
    component with "XML parse error" on screen, with nothing for the author to
    fix. It failed 177 of the repository's 484 .q files.

The admin's validator was also wrong for two reasons of its own wrapping: it
put `<root>` before a `<?xml?>` declaration ("XML or text declaration not at
start of entity") and it only declared the `q:` prefix, so `qg:`, `qt:`,
`ui:` and `qtest:` gave "unbound prefix".
"""

import pathlib
import sys

import pytest

ADMIN = pathlib.Path(__file__).resolve().parents[2] / "quantum_admin"
for path in (str(ADMIN), str(ADMIN / "backend")):
    if path not in sys.path:
        sys.path.insert(0, path)


def _validator():
    import importlib
    module = importlib.import_module('backend.component_discovery')
    return module.QuantumParser._validate_xml


class TestTheAdminValidator:
    @pytest.mark.parametrize("source", [
        '<q:component name="A"><input required /></q:component>',
        '<q:component name="A"><p>Forms & Actions</p></q:component>',
        '<q:component name="A"><br></q:component>',
        '<q:component name="A"><meta charset="utf-8"></q:component>',
        '<q:component name="A"><q:if condition="n < 0">x</q:if></q:component>',
        '<q:component name="A"><p>a&nbsp;b</p></q:component>',
    ])
    def test_common_html_is_not_an_error(self, source):
        assert _validator()(source) == [], source

    def test_an_xml_declaration_at_the_top_is_not_an_error(self):
        source = '<?xml version="1.0" encoding="UTF-8"?>\n<q:component name="A" />'
        assert _validator()(source) == []

    @pytest.mark.parametrize("prefix", ['qg', 'qt', 'ui'])
    def test_the_framework_s_other_prefixes_are_not_errors(self, prefix):
        source = f'<q:component name="A"><{prefix}:thing x="1" /></q:component>'
        assert _validator()(source) == [], prefix

    def test_a_real_structural_error_is_still_reported(self):
        """Tolerance must not become "accept anything"."""
        assert _validator()('<q:component name="A"><div></q:component>')
        assert _validator()('<q:component name="A"><p>x</q:span></q:component>')

    def test_the_files_shipped_in_the_repository_pass(self):
        """177 of the repository's 484 .q files were failed."""
        root = pathlib.Path(__file__).resolve().parents[2]
        files = [a for a in root.rglob('*.q')
                 if 'node_modules' not in str(a)
                 and 'dataset' not in a.parts]
        failed = []
        for a in files:
            try:
                text = a.read_text(encoding='utf-8')
            except Exception:
                continue
            if _validator()(text):
                failed.append(a.relative_to(root))

        assert len(files) > 200, "the repository's .q files are gone?"
        # A few are left, and they are files the framework itself also refuses
        # (JS with loose markup inside <script>).
        assert len(failed) <= 10, (len(failed), failed[:15])


class TestJavaScriptWithMarkupInside:
    """`<script>` and `<style>` are raw text in HTML and not in XML.

    A template literal with markup inside is not XML — `${t.completed ?
    'checked' : ''}` inside a tag is an invalid token. And the author had
    nothing to do but write CDATA by hand around their own JavaScript.
    components/islands_demo.q, shipped in the repository, returned HTTP 400
    because of it.
    """

    def _parse(self, body):
        from quantum.core.parser import QuantumParser
        return QuantumParser(use_cache=False).parse(
            f'<q:component name="C">{body}</q:component>')

    def test_a_template_literal_with_markup_parses(self):
        self._parse(
            '<script>'
            'list.innerHTML = todos.map(t => `'
            '<div class="item ${t.completed ? "done" : ""}">'
            '<input type="checkbox" ${t.completed ? "checked" : ""} />'
            '</div>`).join("");'
            '</script>')

    def test_comparisons_with_less_than_parse(self):
        self._parse('<script>for (var i = 0; i < n; i++) { total += i; }</script>')

    def test_the_code_reaches_the_html_intact(self):
        from quantum.runtime.renderer import HTMLRenderer
        from quantum.runtime.execution_context import ExecutionContext
        code = 'if (a < b && c > d) { x = "1"; }'
        ast = self._parse(f'<script>{code}</script>')
        html = HTMLRenderer(ExecutionContext()).render(ast)
        assert code in html, html

    def test_the_repository_s_islands_demo_parses(self):
        from quantum.core.parser import QuantumParser
        root = pathlib.Path(__file__).resolve().parents[2]
        target = root / 'components' / 'islands_demo.q'
        if not target.exists():
            pytest.skip("the file is not in this checkout")
        QuantumParser(use_cache=False).parse_file(str(target))


class TestSceneInclude:
    def test_common_html_in_an_included_file_does_not_break(self, tmp_path):
        from quantum.core.parser import QuantumParser

        (tmp_path / "scene.q").write_text(
            '<qg:scene name="level1" xmlns:qg="https://quantum.lang/game">\n'
            '  <qg:sprite name="hero" x="0" y="0" />\n'
            '</qg:scene>\n',
            encoding='utf-8')
        game = tmp_path / "game.q"
        game.write_text(
            '<q:application id="j" type="game">\n'
            '  <qg:scene-include src="scene.q" />\n'
            '</q:application>\n',
            encoding='utf-8')

        ast = QuantumParser(use_cache=False).parse_file(str(game))
        assert [c.name for c in ast.scenes] == ["level1"]

    def test_a_raw_ampersand_in_an_included_file(self, tmp_path):
        """A raw `&`: valid in HTML, invalid in XML. It went straight to the
        scene-include's ET.fromstring."""
        from quantum.core.parser import QuantumParser

        (tmp_path / "scene.q").write_text(
            '<qg:scene name="level1" xmlns:qg="https://quantum.lang/game">\n'
            '  <qg:sprite name="Lives & Points" x="0" y="0" />\n'
            '</qg:scene>\n',
            encoding='utf-8')
        game = tmp_path / "game.q"
        game.write_text(
            '<q:application id="j" type="game">\n'
            '  <qg:scene-include src="scene.q" />\n'
            '</q:application>\n',
            encoding='utf-8')

        ast = QuantumParser(use_cache=False).parse_file(str(game))
        assert [c.name for c in ast.scenes] == ["level1"]


class TestTheNamespacesTheFrameworkInjects:
    """Detecting "it already has a namespace" was by SUBSTRING.

    `if 'xmlns:q' in content` matches `xmlns:qt=`, `xmlns:qg=` and
    `xmlns:qtest=`. A file that declared only its own engine's namespace fell
    into the "already declared" branch, where every injection was a
    `content.replace('xmlns:q="https://quantum.lang/ns"', ...)` that found
    nothing — so NO namespace was declared and the file died with "unbound
    prefix" at line 1, column 0.

    And only three roots were recognized (`q:component`, `q:application`,
    `q:job`): a file whose root is `<q:prefab>`, `<q:behavior>` or
    `<qg:scene>` — 15 files shipped in the repository — got no namespace at all.
    """

    def _parse(self, source):
        from quantum.core.parser import QuantumParser
        return QuantumParser(use_cache=False).parse(source)

    def test_declaring_only_qt_does_not_hide_q(self):
        self._parse('<q:application id="t" type="terminal" '
                    'xmlns:qt="https://quantum.lang/terminal">'
                    '<qt:screen name="m" /></q:application>')

    def test_declaring_only_qg_does_not_hide_q(self):
        self._parse('<q:application id="j" type="game" '
                    'xmlns:qg="https://quantum.lang/game">'
                    '<qg:scene name="s" /></q:application>')

    def test_an_unknown_root_gives_the_element_s_name(self):
        """Before: "unbound prefix: line 1, column 0". Now the parser gets to
        the message that says which root it is."""
        from quantum.core.parser import QuantumParseError
        with pytest.raises(QuantumParseError, match="Unknown root element: prefab"):
            self._parse('<q:prefab name="P"><qg:sprite src="x.png" /></q:prefab>')

    def test_a_comment_at_the_top_does_not_get_the_namespaces(self):
        """examples/python-scripting.q opens with a comment that mentions
        `<cfscript>`; injecting there would leave the component without a namespace."""
        source = (
            '<?xml version="1.0"?>' + chr(10) +
            '<!-- inspired by ColdFusion\'s <cfscript> -->' + chr(10) +
            '<q:component name="C"><p>hi</p></q:component>')
        assert self._parse(source).name == 'C'

    def test_the_namespace_the_author_declared_is_respected(self):
        source = ('<q:component name="C" xmlns:q="https://quantum.lang/ns">'
                  '<p>hi</p></q:component>')
        assert self._parse(source).name == 'C'
