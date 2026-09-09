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
        '<q:if condition="n == 1"><p>um</p>'
        '<q:elseif condition="n == 2"><p>dois</p></q:elseif>'
        '<q:elseif condition="n == 3"><p>tres</p></q:elseif>'
        '<q:else><p>outro</p></q:else>'
        '</q:if>'
    )

    @pytest.mark.parametrize("n,expected", [
        (1, "um"), (2, "dois"), (3, "tres"), (9, "outro"),
    ])
    def test_each_branch(self, n, expected):
        _, html = _run(_component(self.TPL.format(n=n)))
        assert f"<p>{expected}</p>" in html

    def test_only_one_branch_renders(self):
        _, html = _run(_component(self.TPL.format(n=2)))
        assert html.count("<p>") == 1
