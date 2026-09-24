"""
The UI components' shared JavaScript came out of Python invalid.

TOAST_JS and CALENDAR_JS lived in NON-raw triple strings. A line like

    html += '<button onclick="__quantumToast.dismiss(\\'' + id + '\\')">'

loses its backslashes when Python compiles it, and the browser gets

    dismiss('' + id + '')

which is a syntax error. A syntax error brings down the WHOLE MODULE: neither
`__quantumToast` nor `__quantumCalendar` ever existed, so no toast closed and no
calendar navigated — on any page, ever.

Nobody saw it because the emitted JS was never checked by anything. These tests
check the output, not the source, and cover every runtime — the defect is in
the WAY the template is written, and the next runtime written the same way
would fail the same way.
"""

import re

import pytest

from quantum.runtime import ui_html_templates as templates

# `('' + x + '')` — collapsed quotes. The right pair is `('\' + x + '\')`.
COLLAPSED = re.compile(r"\(''\s*\+|\+\s*''\)")

RUNTIMES = [name for name in dir(templates)
            if name.endswith('_JS') and isinstance(getattr(templates, name), str)]


def code_lines(source):
    return [line for line in source.splitlines()
            if not line.strip().startswith('//')]


class TestTheSharedRuntimes:
    def test_there_are_runtimes_to_check(self):
        # If the module is renamed, this file ends up testing nothing.
        assert RUNTIMES, "no *_JS found in ui_html_templates"

    @pytest.mark.parametrize("name", RUNTIMES)
    def test_no_collapsed_quote(self, name):
        source = getattr(templates, name)
        bad = [l.strip() for l in code_lines(source) if COLLAPSED.search(l)]
        assert bad == [], f"{name} emits invalid JS: {bad[:3]}"

    @pytest.mark.parametrize("name", RUNTIMES)
    def test_nested_quotes_survive(self, name):
        # The right pattern in the emitted JS is `('\' + id + '\')`.
        source = getattr(templates, name)
        nested = [l for l in code_lines(source)
                  if re.search(r"\\'\s*\+", l)]
        collapsed = [l for l in code_lines(source) if COLLAPSED.search(l)]
        if nested or collapsed:
            assert not collapsed, f"{name} has a collapsed nested quote"

    def test_the_toast_can_be_closed(self):
        # The handler the close button calls must come out with the id really quoted.
        assert re.search(r"dismiss\(\\'", templates.TOAST_JS), \
            "the close button's onclick comes out with invalid syntax"

    def test_the_calendar_can_navigate(self):
        for function in ('prevMonth', 'nextMonth', 'selectDate'):
            assert re.search(function + r"\(\\'", templates.CALENDAR_JS), \
                f"{function} comes out with invalid syntax"


# Module level, built once: a class-scoped fixture written as a method is
# deprecated (pytest 9 warns, pytest 10 removes it) and this one needs no `self`.
@pytest.fixture(scope="module")
def page():
    import pathlib
    from quantum.core.parser import QuantumParser
    from quantum.runtime.ui_builder import UIBuilder

    repo = pathlib.Path(__file__).resolve().parents[2]
    app = QuantumParser().parse_file(
        str(repo / "examples" / "test-ui-components-new.q"))
    return UIBuilder().build(app, target='html')


class TestTheGeneratedPage:
    """The source being right is not enough: what matters is what reaches the browser."""

    def test_the_page_carries_no_invalid_js(self, page):
        bad = [l.strip() for l in page.splitlines()
               if COLLAPSED.search(l) and not l.strip().startswith('//')]
        assert bad == [], bad

    def test_the_adapter_does_not_fix_the_output(self):
        # There was a regex in the adapter repairing the JS AFTER it was
        # generated. Fixing the output leaves the cause standing: the next
        # runtime written the same way breaks again, silently.
        from quantum.runtime.ui_html_adapter import UIHtmlAdapter

        dirty = "dismiss('' + id + '')"
        assert UIHtmlAdapter()._emit_runtime(dirty) == dirty, (
            "_emit_runtime is patching the output instead of the source being right")
