"""
A PRESENT session variable was read as empty.

A regression brought in by the move to the AST evaluator. The context keeps
the scope variable under the FLAT dotted KEY ('session.userId') because it is
a LOOKUP; the evaluator reads `session.userId` as
Attribute(Name('session'), 'userId'), finds no `session` object, and raises.
Callers turned that into '' (databinding) or False (a condition).

The previous code had `if expr in context: return context[expr]` and
resolved it. The move removed that shortcut from the runtime and kept it in
HTMLRenderer — so the SAME page showed:

    copy=[]  direct=[42]

The `copy` came from `<q:set value="{session.userId}"/>` and the `direct` from
the renderer's interpolation. Two paths, two truths.

Consequences reproduced: an INSERT wrote `user_id=''` with session.userId='42',
with no error and no log; and `<q:if condition="{session.role == 'admin'}">`
was False in BOTH branches, so neither the admin content nor the access
denied message showed.

Why the suite did not see it: the scope tests only covered the MISSING
variable (resolving to '' is the contract) and the conditions only used an
empty context, where failing to False looks safe. None tested the PRESENT case.

The documentation teaches exactly these patterns — docs/guide/query.md,
docs/guide/conditionals.md, docs/examples/authentication.md — so the defect
hit whoever followed the guide.
"""

import pathlib
import tempfile

import pytest

from quantum.core.expressions import ExpressionEvaluator, ExpressionError
from quantum.core.parser import QuantumParser
from quantum.runtime.component import ComponentRuntime
from quantum.runtime.renderer import HTMLRenderer

SCOPES = ['session', 'application', 'request']


def run_body(body, scope='session', variables=None):
    source = f'<q:component name="S">{body}</q:component>'
    path = pathlib.Path(tempfile.mkdtemp()) / 's.q'
    path.write_text(source, encoding='utf-8')
    node = QuantumParser().parse_file(str(path))

    runtime = ComponentRuntime()
    runtime.execute_component(node, {f'_{scope}_scope': variables or {}})
    html = HTMLRenderer(runtime.execution_context).render(node)
    return runtime, html


class TestThePresentValueArrives:
    def test_q_set_copies_the_value(self):
        runtime, _ = run_body('<q:set name="copy" value="{session.userId}" />',
                              variables={'userId': '42'})
        assert runtime.execution_context.get_all_variables()['copy'] == '42'

    def test_interpolation_shows_the_value(self):
        _, html = run_body('<p>[{session.userId}]</p>', variables={'userId': '42'})
        assert '[42]' in html

    def test_the_two_paths_agree(self):
        # The symptom that gave the bug away: copy=[] and direct=[42] on the SAME
        # page. A value can only have one truth.
        _, html = run_body(
            '<q:set name="copy" value="{session.userId}" />'
            '<p>copy=[{copy}] direct=[{session.userId}]</p>',
            variables={'userId': '42'})
        assert 'copy=[42] direct=[42]' in html

    @pytest.mark.parametrize("scope", SCOPES)
    def test_it_holds_for_every_scope(self, scope):
        runtime, _ = run_body(f'<q:set name="c" value="{{{scope}.key}}" />',
                              scope=scope, variables={'key': 'value'})
        assert runtime.execution_context.get_all_variables()['c'] == 'value'

    def test_the_value_reaches_a_query_parameter(self):
        # That is how the wrong data reached the database: the parameter got ''.
        runtime, _ = run_body(
            '<q:set name="p" value="{session.userId}" />',
            variables={'userId': '42'})
        assert runtime.execution_context.get_all_variables()['p'] != ''


class TestConditionsSeeTheScope:
    def test_a_simple_true_condition(self):
        _, html = run_body(
            '<q:if condition="{session.authenticated}"><p>IN</p></q:if>',
            variables={'authenticated': True})
        assert 'IN' in html

    def test_a_comparison_with_equality(self):
        _, html = run_body(
            '<q:if condition="{session.role == \'admin\'}"><p>ADMIN</p></q:if>',
            variables={'role': 'admin'})
        assert 'ADMIN' in html

    def test_the_negative_branch_works_too(self):
        # The worst symptom: BOTH branches were false, so neither the protected
        # content nor the access denied message showed.
        _, html = run_body(
            '<q:if condition="{session.role != \'admin\'}"><p>DENIED</p></q:if>',
            variables={'role': 'reader'})
        assert 'DENIED' in html

    def test_the_guard_does_not_let_the_wrong_one_through(self):
        _, html = run_body(
            '<q:if condition="{session.role == \'admin\'}"><p>ADMIN</p></q:if>',
            variables={'role': 'reader'})
        assert 'ADMIN' not in html


class TestTheMissingContractStays:
    """Resolving '' when the variable does NOT exist is on purpose: the page
    renders before login. The fix must not have erased that."""

    def test_missing_becomes_empty(self):
        runtime, _ = run_body('<q:set name="c" value="{session.missing}" />',
                              variables={'userId': '42'})
        assert runtime.execution_context.get_all_variables()['c'] == ''

    def test_a_whole_missing_scope_becomes_empty(self):
        runtime, _ = run_body('<q:set name="c" value="{session.anything}" />')
        assert runtime.execution_context.get_all_variables()['c'] == ''

    def test_a_condition_over_a_missing_one_is_false(self):
        _, html = run_body(
            '<q:if condition="{session.missing}"><p>X</p></q:if>')
        assert '<p>X</p>' not in html


class TestRealAttributeAccessStays:
    """The flat key must not have run over real attribute access."""

    def evaluate(self, expr, ctx):
        return ExpressionEvaluator().evaluate(expr, ctx)

    def test_an_object_attribute(self):
        obj = type('O', (), {'name': 'ok'})()
        assert self.evaluate('obj.name', {'obj': obj}) == 'ok'

    def test_a_dictionary_key_by_dot(self):
        assert self.evaluate('d.a', {'d': {'a': 1}}) == 1

    def test_the_flat_key_wins_when_it_exists(self):
        # If both exist, the flat key is the one the framework writes.
        ctx = {'session.x': 'flat', 'session': type('O', (), {'x': 'object'})()}
        assert self.evaluate('session.x', ctx) == 'flat'

    def test_chaining_over_a_call_does_not_become_a_key(self):
        # `f(x).name` must not become a lookup of the key "f(x).name".
        with pytest.raises(ExpressionError):
            self.evaluate('missing(1).name', {})

    def test_a_missing_attribute_still_raises(self):
        with pytest.raises(ExpressionError):
            self.evaluate('d.b', {'d': {'a': 1}})
