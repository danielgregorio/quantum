"""
The language server produced no diagnostics for any document, ever.

validate_document called

    doc.symbols.get_symbols_by_kind(doc.symbols._by_kind)

— the whole dict passed as the kind — with `pass` for a body. A dict is
unhashable, so the lookup raised TypeError, validate_document raised with it,
and nothing was ever published: not an unknown tag, not a missing required
attribute, not malformed XML. The server's main job was dead on every file.

And it could not have reported malformed XML anyway: _parse_elements is regex
based (it tracks positions, which ElementTree does not), so an unclosed tag
produced no error at all. The editor said nothing about a file the framework
rejects outright.
"""

import pathlib
import sys

import pytest

LSP = pathlib.Path(__file__).resolve().parents[1]
REPO = LSP.parent
for path in (str(LSP), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

from quantum_lsp.analysis.document import QuantumDocument  # noqa: E402
from quantum_lsp.handlers.diagnostics import validate_document  # noqa: E402


def diagnose(source):
    return validate_document(QuantumDocument("file:///t.q", source))


def messages(source):
    return [d.message for d in diagnose(source)]


class TestItRunsAtAll:
    @pytest.mark.parametrize("source", [
        '<q:component name="C"><q:set name="a" value="1" /></q:component>',
        '<q:component name="C"><q:naoexiste /></q:component>',
        '<q:component name="C"><q:set value="1" /></q:component>',
        '<q:component name="C"><p>{x}</p></q:component>',
        "",
    ])
    def test_it_does_not_raise(self, source):
        # It raised TypeError on every one of these.
        diagnose(source)

    def test_a_correct_document_is_clean(self):
        assert diagnose(
            '<q:component name="C"><q:set name="a" value="1" /></q:component>'
        ) == []


class TestItFindsRealMistakes:
    def test_an_unknown_tag(self):
        assert any("naoexiste" in m
                   for m in messages('<q:component name="C">'
                                     '<q:naoexiste /></q:component>'))

    def test_a_missing_required_attribute(self):
        found = messages('<q:component name="C"><q:set value="1" /></q:component>')
        assert any("name" in m and "q:set" in m for m in found), found

    def test_an_unclosed_tag(self):
        found = messages('<q:component name="C"><q:set name="a"></q:component>')
        assert any("mismatched" in m.lower() or "parse error" in m.lower()
                   for m in found), found

    def test_a_mismatched_closing_tag(self):
        found = messages('<q:component name="C"><p>oi</div></q:component>')
        assert any("parse error" in m.lower() for m in found), found


class TestItDoesNotCryWolf:
    """A false error is worse than no error: it gets the server turned off."""

    def test_a_missing_xmlns_is_not_an_error(self):
        # .q files do not have to declare xmlns:q — the framework injects it.
        # A raw ET.fromstring says "unbound prefix" for every single file.
        assert diagnose('<q:component name="C"><p>oi</p></q:component>') == []

    @pytest.mark.parametrize("source", [
        '<q:component name="C"><br><p>oi</p></q:component>',
        '<q:component name="C"><input disabled></q:component>',
        '<q:component name="C"><p>Tom & Jerry</p></q:component>',
        '<q:component name="C"><meta charset="utf-8"></q:component>',
    ])
    def test_html_the_framework_accepts_is_not_flagged(self, source):
        assert diagnose(source) == [], source

    def test_it_agrees_with_the_real_parser_on_every_file_in_the_repo(self):
        from quantum.core.parser import QuantumParser

        files = sorted(list((REPO / "examples").glob("*.q")) +
                       list((REPO / "components").rglob("*.q")))
        assert files, "no .q files found to check against"

        disagreements = []
        for path in files:
            text = path.read_text(encoding="utf-8", errors="replace")
            lsp_error = QuantumDocument("file:///x.q", text).get_parse_error()
            try:
                QuantumParser().parse_file(str(path))
                framework_error = None
            except Exception as exc:
                framework_error = str(exc)

            if lsp_error and not framework_error:
                disagreements.append(f"false positive on {path.name}: {lsp_error}")
            elif (framework_error and "XML parse error" in framework_error
                    and not lsp_error):
                disagreements.append(f"missed the error in {path.name}")

        assert disagreements == [], disagreements


class TestFragmentsAreNotDocuments:
    """An editor sees half-typed files constantly."""

    def test_a_bare_tag_is_not_reported_as_broken(self):
        # The namespace injector only adds xmlns to a q:component /
        # q:application root, so a fragment came back "unbound prefix".
        doc = QuantumDocument("file:///t.q", '<q:set type="string" />')
        assert doc.get_parse_error() is None

    def test_a_fragment_still_gets_its_real_diagnostic(self):
        # get_diagnostics returns EARLY on a parse error, so a false parse
        # error also HID the useful message.
        found = messages('<q:set type="string" />')
        assert any("name" in m.lower() for m in found), found
