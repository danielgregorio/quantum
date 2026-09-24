"""
Compatibility corpus for the expression evaluator.

Step 1 of FRAMEWORK_PLAN.md Fase 2.1. Before replacing the two parallel
evaluators (6 _evaluate_* methods in component.py, 4 more in renderer.py) with
one, the current behaviour has to be pinned — including the parts that are
wrong, marked as such. Otherwise there is no way to tell a fix from a
regression.

The corpus in tests/fixtures/expression_corpus.json is 503 expressions
harvested from examples/*.q, with style/script blocks stripped (their braces
are CSS and JavaScript, not Quantum expressions — a distinction the new
evaluator must also make).

The KNOWN_WRONG cases below are the failure modes this phase exists to fix.
They are asserted as currently-wrong on purpose: when the new evaluator lands,
these flip, and that flip is the proof it worked.
"""

import json
import pathlib

import pytest

from quantum.core.expressions import ExpressionError
from quantum.runtime.component import ComponentRuntime

CORPUS_PATH = pathlib.Path(__file__).resolve().parent.parent / "fixtures" / "expression_corpus.json"

# The context the corpus baseline was recorded against.
CONTEXT = {
    'a': 17, 'b': 25, 'x': 10, 'count': 3, 'total': 100, 'price': 9.5,
    'name': 'Alice', 'title': 'Docs', 'hp': 100, 'i': 1, 'n': 2,
    'items': [1, 2, 3], 'users': [{'name': 'Ann'}, {'name': 'Bo'}],
    'user': {'name': 'Ann', 'age': 30, 'email': 'a@b.c'},
    'result': {'success': True, 'count': 2, 'data': [1, 2]},
    'flag': True, 'empty': '', 'zero': 0,
}


@pytest.fixture(scope="module")
def runtime():
    return ComponentRuntime()


@pytest.fixture(scope="module")
def corpus():
    if not CORPUS_PATH.exists():
        pytest.skip("expression corpus not generated")
    return json.loads(CORPUS_PATH.read_text(encoding="utf-8"))


def test_corpus_is_present_and_substantial(corpus):
    assert len(corpus) > 400, (
        "the corpus should cover the real expression surface of examples/"
    )


def test_no_expression_crashes(runtime, corpus):
    """Whatever else it does, the evaluator must not blow up on real input.

    Since EXPR-1/EXPR-2 an expression that cannot be evaluated raises
    ExpressionError, the declared failure naming the expression. Anything else
    (TypeError, KeyError...) is a crash inside the evaluator.
    """
    failures = []
    for entry in corpus:
        try:
            runtime._apply_databinding('{' + entry['expr'] + '}', dict(CONTEXT))
        except ExpressionError:
            pass
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{entry['expr']!r}: {type(exc).__name__}: {exc}")

    assert not failures, "expressions crashed:\n  " + "\n  ".join(failures[:20])


# The only expressions whose behaviour the Fase 2.1 migration deliberately
# changed. Two out of 503 — the rest of the corpus is byte-identical.
#
#   false   -> used to resolve to the STRING '{false}', which is truthy. So
#             <q:set name="gameOver" value="{false}"> set a true value and the
#             game could never end. examples/kenney_platformer.q line 550.
#   now()   -> no date function existed, so the placeholder came back verbatim.
#
# Anything else that drifts is a regression, not a fix.
DELIBERATE_CHANGES = {
    'false': 'resolves to the boolean False instead of the truthy string "{false}"',
    'now()': 'resolves to a real datetime instead of the literal placeholder',
}


def test_corpus_results_are_stable(runtime, corpus):
    """Every expression still evaluates to what the baseline recorded.

    This is the gate that let the new evaluator be swapped in: any difference
    is either a deliberate fix (listed in DELIBERATE_CHANGES with the reason)
    or a regression.
    """
    drifted = []
    for entry in corpus:
        if entry['expr'] in DELIBERATE_CHANGES:
            continue
        if entry['expr'].isdigit():
            # EXPR-7: a whole value `{3}` is the number 3, no longer the
            # literal text '{3}' (it was read as a regex quantifier).
            assert runtime._apply_databinding('{' + entry['expr'] + '}', {}) == int(entry['expr'])
            continue
        try:
            got = repr(runtime._apply_databinding('{' + entry['expr'] + '}', dict(CONTEXT)))
        except ExpressionError:
            # EXPR-1/2/3: what used to come back as the placeholder (or as ''
            # for arithmetic on an absent scope value) is now an error. That is
            # the one deliberate change; every other result must be identical.
            if entry['result'] in (repr('{' + entry['expr'] + '}'), repr('')):
                continue
            got = 'an error'
        if got != entry['result']:
            drifted.append(f"{entry['expr']!r}: baseline {entry['result']} -> now {got}")

    assert not drifted, (
        f"{len(drifted)} expressions changed behaviour:\n  " + "\n  ".join(drifted[:20])
    )


def test_regex_quantifiers_are_not_evaluated(runtime):
    """`pattern="\\d{10,11}"` must survive databinding untouched.

    The new evaluator would read {10,11} as the tuple (10, 11) and silently
    corrupt the validation pattern. examples/form_validation.q depends on this,
    as does the email regex in examples/python-scripting.q.
    """
    assert runtime._apply_databinding(r'\d{10,11}', {}) == r'\d{10,11}'
    assert runtime._apply_databinding(r'[a-zA-Z]{2,}$', {}) == r'[a-zA-Z]{2,}$'
    assert runtime._apply_databinding(r'[a-zA-Z\d]{8,}$', {}) == r'[a-zA-Z\d]{8,}$'


class TestFixedByTheMigration:
    """The failure modes Fase 2.1 existed to fix.

    These were written asserting the old, wrong behaviour. They started failing
    the moment the new evaluator was wired in — that failure was the proof the
    swap worked, and they are flipped here to pin the correct behaviour.
    """

    def test_numeric_strings_now_add_instead_of_concatenating(self, runtime):
        """The exact bug found via q:agent: an LLM sends tool arguments as
        strings, so {a + b} used to produce 1725. Same for form input."""
        assert runtime._apply_databinding('{a + b}', {'a': '17', 'b': '25'}) == 42

    def test_date_functions_exist(self, runtime):
        """Their absence is why session expiry had to be hardcoded during the
        q:action fix (AUDIT_FIX_PLAN.md Fase 1)."""
        from datetime import datetime, timedelta
        assert isinstance(runtime._apply_databinding('{now()}', {}), datetime)
        expiry = runtime._apply_databinding("{dateAdd('h', 24)}", {})
        assert timedelta(hours=23) < expiry - datetime.now() <= timedelta(hours=24)

    def test_boolean_literals_resolve(self, runtime):
        """<q:set name="gameOver" value="{false}"> used to store the string
        '{false}', which is truthy — so the flag could never be false."""
        assert runtime._apply_databinding('{false}', {}) is False
        assert runtime._apply_databinding('{true}', {}) is True


class TestContractsDecidedAfterTheMigration:
    """The migration preserved these on purpose and left each as its own
    decision. Both were decided in SPEC.md (EXPR-1, EXPR-3)."""

    def test_missing_scoped_reference_becomes_empty_string(self, runtime):
        """EXPR-3. Templates render before login on purpose, so reading an
        absent session./application. value is ''."""
        assert runtime._apply_databinding('{session.missingCounter}', {}) == ''

    def test_arithmetic_on_a_missing_scoped_value_is_an_error(self, runtime):
        """EXPR-3. This used to pin '' for {session.missingCounter + 1}, called
        "arguably wrong". The '' surfaced later, far from the cause."""
        with pytest.raises(ExpressionError, match="session"):
            runtime._apply_databinding('{session.missingCounter + 1}', {})

    def test_unresolvable_expression_is_an_error_that_names_it(self, runtime):
        """EXPR-1. Handing the text back put literal braces on the page or in a
        database row, with nothing pointing at the typo."""
        with pytest.raises(ExpressionError, match="nosuchvar"):
            runtime._apply_databinding('{nosuchvar}', {})
        with pytest.raises(ExpressionError, match="JSON"):
            runtime._apply_databinding('{JSON.stringify(x)}', {})
