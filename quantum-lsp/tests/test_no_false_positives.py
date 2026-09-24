"""
The language server flagged correct code — en masse.

Measured at the start: **643 diagnostics in 129 of 253 .q files that the
framework parses cleanly**. Mass false positives are what makes someone turn
off the server, and then it stops being worth anything for the real errors too.

Three structural causes, all fixed:

1. The tag regex stopped at the FIRST `>`, even inside quotes, so
   `<q:if condition="a > b">` was cut and became "Missing required
   attribute 'condition'" on valid code.
2. The schema kept a list of tags BY HAND — 76 entries against 95 in the
   framework's registry — and reported `q:python`, `q:queue`, `ui:card-body`
   as unknown.
3. "Unknown tag" was emitted even on a document the FRAMEWORK accepts.
   Dozens of tags are children parsed by the parent's parser (q:tool inside
   q:agent, q:column inside q:data) and so will never be in the registry.
   What counts as a valid tag is decided by the framework.

The rest is data drift: an enum missing a value, an attribute marked required
that is not. This test exists so that this drift is VISIBLE and bounded,
instead of growing silently: it measures the rate against the repository's own
files and fails if it gets worse.
"""

import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
LSP = REPO / "quantum-lsp"
for path in (str(LSP), str(REPO)):
    if path not in sys.path:
        sys.path.insert(0, path)

from quantum.core.parser import QuantumParser  # noqa: E402
from quantum_lsp.analysis.document import QuantumDocument  # noqa: E402
from quantum_lsp.handlers.diagnostics import validate_document  # noqa: E402

# Current ceiling. Lower it when you fix more; never raise it without a written reason.
MAX_FILES_WITH_DIAGNOSTICS = 34
MAX_DIAGNOSTICS = 82


def files_the_framework_accepts():
    for folder in ("examples", "components"):
        for path in (REPO / folder).rglob("*.q"):
            text = path.read_text(encoding="utf-8", errors="replace")
            try:
                QuantumParser().parse_file(str(path))
            except Exception:
                continue          # the framework rejects it: not a false positive
            yield path, text


@pytest.fixture(scope="module")
def measurement():
    files = flagged = total = 0
    worst = []
    for path, text in files_the_framework_accepts():
        files += 1
        findings = validate_document(QuantumDocument("file:///x.q", text))
        if findings:
            flagged += 1
            total += len(findings)
            worst.append((path.name, len(findings), findings[0].message[:70]))
    worst.sort(key=lambda x: -x[1])
    return {"files": files, "flagged": flagged, "total": total, "worst": worst}


class TestTheFalsePositiveRate:
    def test_there_are_files_to_measure(self, measurement):
        assert measurement["files"] > 150, measurement["files"]

    def test_the_number_of_affected_files_did_not_get_worse(self, measurement):
        assert measurement["flagged"] <= MAX_FILES_WITH_DIAGNOSTICS, (
            f"{measurement['flagged']} correct files get a diagnostic "
            f"(ceiling {MAX_FILES_WITH_DIAGNOSTICS}). Worst: "
            f"{measurement['worst'][:3]}")

    def test_the_number_of_diagnostics_did_not_get_worse(self, measurement):
        assert measurement["total"] <= MAX_DIAGNOSTICS, (
            f"{measurement['total']} false diagnostics (ceiling {MAX_DIAGNOSTICS}). "
            f"Worst: {measurement['worst'][:3]}")


class TestTheStructuralCausesStayFixed:
    def diagnose(self, source):
        return [d.message for d in
                validate_document(QuantumDocument("file:///t.q", source))]

    @pytest.mark.parametrize("condition", ["a > b", "a >= b", "a < b", "x > 1 && y < 2"])
    def test_operator_in_the_attribute_value(self, condition):
        # The regex stopped at the first `>` and truncated the attribute list.
        source = (f'<q:component name="C"><q:if condition="{condition}">'
                  f'<p>x</p></q:if></q:component>')
        assert self.diagnose(source) == []

    @pytest.mark.parametrize("tag", ["q:python", "q:queue", "q:agent", "q:thread"])
    def test_tag_the_registry_knows(self, tag):
        # The hand-kept list had 76 entries; the registry has 95.
        from quantum_lsp.schema import is_known_tag
        assert is_known_tag(tag), f"{tag} is in the registry and the LSP does not know it"

    def test_child_tag_is_not_flagged(self):
        # q:tool is parsed by the q:agent parser and will never be in the
        # top-level tag registry; it comes from the NESTED_TAGS list.
        source = ('<q:component name="C"><q:agent name="a" model="m">'
                  '<q:tool name="t" description="d" /></q:agent></q:component>')
        assert not any("Unknown tag" in m for m in self.diagnose(source))

    def test_made_up_tag_is_still_flagged(self):
        # An intermediate version suppressed "unknown tag" whenever the
        # FRAMEWORK accepted the document — and the framework silently IGNORES
        # a `q:` tag it does not know: `<q:doesnotexist/>` becomes an HTMLNode
        # and disappears. That erased typo detection, which is valuable
        # precisely BECAUSE the framework is silent.
        source = '<q:component name="C"><q:doesNotExistAtAll /></q:component>'
        assert any("doesNotExistAtAll" in m for m in self.diagnose(source))

    @pytest.mark.parametrize("type_name", ["number", "integer", "decimal", "float",
                                           "string", "boolean"])
    def test_types_the_runtime_accepts(self, type_name):
        source = (f'<q:component name="C">'
                  f'<q:set name="n" value="1" type="{type_name}" /></q:component>')
        assert not any("Invalid value" in m for m in self.diagnose(source))

    def test_redirect_accepts_both_spellings(self):
        for attribute in ("url", "to"):
            source = (f'<q:component name="C"><q:action name="a">'
                      f'<q:redirect {attribute}="/x" /></q:action></q:component>')
            assert not any("required" in m for m in self.diagnose(source))
