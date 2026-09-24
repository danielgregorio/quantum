"""
The documentation taught code that did not parse.

Ten of the 82 complete examples in docs/guide did not get through the parser
— and one of them was in `quick-start.md`, the second page anyone reads. For
someone evaluating the project, the first copy-and-paste failed.

Eight had the same cause: a raw `<` inside an attribute value, which is what
people naturally write:

    <q:if condition="n < 0">
    <q:return value="<h1>Hi</h1>" />

That was fixed in the PARSER, not in the documentation. A raw `&` and boolean
attributes were already tolerated; `<` followed the same logic and was
missing. Fixing the docs would have left every user file with the same natural
syntax broken.

This test exists so the docs do not drift from what the framework accepts
again — both ways. If someone writes an example that does not parse, it fails
here; if someone tightens the parser, too.
"""

import pathlib
import re
import tempfile

import pytest

from quantum.core.parser import QuantumParser

REPO = pathlib.Path(__file__).resolve().parents[2]
GUIDE = REPO / "docs" / "guide"
FENCE = "`" * 3

# Deliberately incomplete snippets: they illustrate a naming convention with a
# `<!-- Good -->` / `<!-- Avoid -->` and one line each, without closing the tag.
# They are not examples to copy.
INCOMPLETE = {"components.md"}


def examples():
    """Each fenced block that holds a complete component or application."""
    for doc in sorted(GUIDE.glob("*.md")):
        text = doc.read_text(encoding="utf-8", errors="replace")
        for i, m in enumerate(re.finditer(FENCE + r"([a-z]*)\n(.*?)" + FENCE, text, re.S)):
            language, block = m.group(1), m.group(2)
            if language == "text":        # terminal output, not code
                continue
            if re.match(r"\s*\*\*(Error|Erro):\*\*", text[m.end():]):
                # An example of the error, on purpose: tests/docs checks that the
                # error is the one announced.
                continue
            if "<q:component" not in block and "<q:application" not in block:
                continue
            yield doc.name, i, block


ALL = list(examples())


class TestTheDocumentationExamples:
    def test_there_are_examples_to_check(self):
        # If extraction breaks, this file ends up testing nothing.
        assert len(ALL) > 50, f"only found {len(ALL)} examples"

    @pytest.mark.parametrize(
        "name,index,block",
        [c for c in ALL if c[0] not in INCOMPLETE],
        ids=[f"{c[0]}#{c[1]}" for c in ALL if c[0] not in INCOMPLETE],
    )
    def test_it_parses(self, name, index, block):
        path = pathlib.Path(tempfile.mkdtemp()) / "doc.q"
        path.write_text(block, encoding="utf-8")
        QuantumParser().parse_file(str(path))


class TestTheNaturalSyntaxIsAccepted:
    """What the docs teach must work when the user writes it the same way."""

    def parse(self, source):
        path = pathlib.Path(tempfile.mkdtemp()) / "n.q"
        path.write_text(source, encoding="utf-8")
        return QuantumParser().parse_file(str(path))

    @pytest.mark.parametrize("condition", [
        "n < 0", "n <= 1", "n > 0", "n >= 1",
        "a && b", "a || b", "a < b && c > d",
        "item.type == 'fruit' && item.price < 1.00",
    ])
    def test_operators_in_a_condition(self, condition):
        self.parse(f'<q:component name="C"><q:if condition="{condition}">'
                   f'<p>x</p></q:if></q:component>')

    def test_html_inside_a_value(self):
        self.parse('<q:component name="C">'
                   '<q:return value="<h1>Hi</h1>" /></q:component>')

    def test_the_value_reaches_the_author_intact(self):
        # `&lt;` round-trips: the XML parser undoes the escape, so whoever
        # wrote `<h1>` gets `<h1>` back.
        from quantum.runtime.component import ComponentRuntime

        node = self.parse('<q:component name="C">'
                          '<q:return value="<h1>Hi</h1>" /></q:component>')
        assert ComponentRuntime().execute_component(node, {}) == "<h1>Hi</h1>"

    def test_single_quotes_too(self):
        self.parse("<q:component name=\"C\"><q:if condition='n < 3'>"
                   "<p>x</p></q:if></q:component>")

    def test_greater_than_still_works(self):
        # Already tolerated; the `<` change must not have touched it.
        # (it used <q:validator>, which was never a tag: the parser dropped it
        # silently, and the test passed without parsing any expression — PARSE-1)
        self.parse('<q:component name="C">'
                   '<q:set name="adult" value="{age >= 18}" />'
                   '</q:component>')
