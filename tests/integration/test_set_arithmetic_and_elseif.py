"""
Two critical correctness bugs the audit found, both reproduced before fixing.

1. q:set increment/decrement corrupted the value instead of failing.

   `_execute_decrement` wrapped BOTH the variable lookup and the numeric type
   check in one `try: ... except Exception: return -step`. So the ExecutorError
   it raised for a non-numeric value was caught by its own handler one line
   later and turned into the step. A stock of "7" decremented by 5 became -5.
   The detection was correct and then discarded.

   It also refused plain "7", because a .q attribute is a string unless the
   author remembered type="number" — so the ordinary case was the broken one.

2. q:elseif crashed the renderer.

   The parser stores elseif branches as dicts and IfExecutor reads them as
   dicts; HTMLRenderer read them as objects, so any page with q:elseif died
   with "'dict' object has no attribute 'condition'" during render. The two
   passes disagreed about the same structure.
"""

import io
import contextlib

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.component import ComponentRuntime
from quantum.runtime.renderer import HTMLRenderer


def _run(src):
    with contextlib.redirect_stdout(io.StringIO()):
        ast = QuantumParser().parse(src)
        rt = ComponentRuntime()
        rt.execute_component(ast)
        html = HTMLRenderer(rt.execution_context).render(ast)
    return rt, html


def _component(body):
    return f'<q:component name="X">{body}</q:component>'


class TestSetArithmetic:
    def test_decrement_a_string_valued_variable(self):
        """The stock case: 7 - 5 = 2, not -5."""
        rt, _ = _run(_component(
            '<q:set name="e" value="7" />'
            '<q:set name="e" operation="decrement" step="5" />'
        ))
        assert rt.execution_context.get_variable("e") == 2

    def test_increment_a_string_valued_variable(self):
        rt, _ = _run(_component(
            '<q:set name="c" value="10" />'
            '<q:set name="c" operation="increment" step="5" />'
        ))
        assert rt.execution_context.get_variable("c") == 15

    def test_typed_number_still_works(self):
        rt, _ = _run(_component(
            '<q:set name="e" value="7" type="number" />'
            '<q:set name="e" operation="decrement" step="5" />'
        ))
        assert rt.execution_context.get_variable("e") == 2

    def test_a_missing_variable_starts_from_the_step(self):
        """The behaviour the swallowed except was there to provide."""
        rt, _ = _run(_component('<q:set name="c" operation="increment" step="3" />'))
        assert rt.execution_context.get_variable("c") == 3

    def test_a_genuinely_non_numeric_value_fails_loudly(self):
        """It must raise, not silently produce -step."""
        with pytest.raises(Exception) as e:
            _run(_component(
                '<q:set name="e" value="abc" />'
                '<q:set name="e" operation="decrement" step="1" />'
            ))
        assert "non-numeric" in str(e.value)

    @pytest.mark.parametrize("op,start,operand,expected", [
        ("add", "10", "5", 15),
        ("multiply", "4", "3", 12),
    ])
    def test_add_and_multiply_coerce_too(self, op, start, operand, expected):
        rt, _ = _run(_component(
            f'<q:set name="t" value="{start}" />'
            f'<q:set name="t" operation="{op}" value="{operand}" />'
        ))
        assert rt.execution_context.get_variable("t") == expected


class TestElseIfRenders:
    TPL = (
        '<q:set name="n" value="{n}" type="number" />'
        '<q:if condition="n == 1"><p>one</p>'
        '<q:elseif condition="n == 2"><p>two</p></q:elseif>'
        '<q:elseif condition="n == 3"><p>three</p></q:elseif>'
        '<q:else><p>other</p></q:else>'
        '</q:if>'
    )

    @pytest.mark.parametrize("n,expected", [
        (1, "one"), (2, "two"), (3, "three"), (9, "other"),
    ])
    def test_each_branch(self, n, expected):
        _, html = _run(_component(self.TPL.format(n=n)))
        assert f"<p>{expected}</p>" in html

    def test_only_one_branch_renders(self):
        _, html = _run(_component(self.TPL.format(n=2)))
        assert html.count("<p>") == 1


class TestElseElseifSibling:
    """`<q:else>`/`<q:elseif>` as a SIBLING of `<q:if>` — the form the docs teach.

    Only the NESTED form (else inside the if) worked. The sibling — `</q:if>`
    and then `<q:else>` — had no registered parser (IfParser.tag_names =
    ['if']), fell into the fallback and was DROPPED without a word: the else
    simply did not happen. docs/guide/conditionals.md teaches the sibling form
    (the if-else and the elseif chain), and 7 shipped .q files used it.

    Now the parser attaches an else/elseif that follows a q:if to that if; both
    forms become the same thing. An else/elseif WITHOUT an if before it is an
    explicit error, instead of vanishing.
    """

    def test_a_sibling_else_picks_the_else_branch(self):
        _, html = _run(_component(
            '<q:set name="n" type="integer" value="5" />'
            '<q:if condition="n > 10"><p>BIG</p></q:if>'
            '<q:else><p>SMALL</p></q:else>'))
        assert 'SMALL' in html and 'BIG' not in html, html

    def test_a_sibling_else_picks_the_if_branch(self):
        _, html = _run(_component(
            '<q:set name="n" type="integer" value="20" />'
            '<q:if condition="n > 10"><p>BIG</p></q:if>'
            '<q:else><p>SMALL</p></q:else>'))
        assert 'BIG' in html and 'SMALL' not in html, html

    def test_a_sibling_elseif(self):
        # the verbatim example of docs/guide/conditionals.md (score)
        _, html = _run(_component(
            '<q:set name="score" type="integer" value="85" />'
            '<q:if condition="score >= 90"><p>A</p></q:if>'
            '<q:elseif condition="score >= 80"><p>B</p></q:elseif>'
            '<q:else><p>F</p></q:else>'))
        assert 'B' in html and 'A' not in html and 'F' not in html, html

    def test_the_nested_form_still_works(self):
        _, html = _run(_component(
            '<q:set name="n" type="integer" value="5" />'
            '<q:if condition="n > 10"><p>BIG</p>'
            '<q:else><p>SMALL</p></q:else></q:if>'))
        assert 'SMALL' in html and 'BIG' not in html, html

    def test_an_orphan_else_is_an_error_not_silence(self):
        from quantum.core.parser import QuantumParseError
        with pytest.raises(QuantumParseError, match="no matching <q:if>"):
            QuantumParser().parse(_component('<q:else><p>x</p></q:else>'))

    def test_an_orphan_elseif_too(self):
        from quantum.core.parser import QuantumParseError
        with pytest.raises(QuantumParseError, match="no matching <q:if>"):
            QuantumParser().parse(_component(
                '<q:elseif condition="1==1"><p>x</p></q:elseif>'))
