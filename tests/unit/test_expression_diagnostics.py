"""
Tests for unresolved-expression diagnostics.

FRAMEWORK_PLAN.md Fase 2.2, prioritised by Fase 4's measurement: six of the
eleven frictions found while writing one real screen were the same disease,
silent failure, and three of the four bugs produced no message at all.

The two cases that cost the most time there are pinned by name below, because
"the error message is good now" is not a claim a test can make in general — but
"these two specific failures explain themselves" is.
"""

import logging

import pytest

from quantum.core import expression_diagnostics
from quantum.core.expressions import ExpressionEvaluator, ExpressionError
from quantum.runtime.component import ComponentRuntime
from quantum.runtime.execution_context import ExecutionContext
from quantum.runtime.renderer import HTMLRenderer


@pytest.fixture(autouse=True)
def fresh():
    """Reports are deduplicated process-wide, so tests must not inherit."""
    expression_diagnostics.reset()
    yield
    expression_diagnostics.reset()


@pytest.fixture
def runtime():
    return ComponentRuntime()


class TestTheTwoFailuresThatCostTheMostTime:
    """Both from DOGFOOD_NOTES.md, reproduced exactly."""

    def test_undefined_row_variable_names_what_is_in_scope(self, runtime, caplog):
        """<q:loop query="projects" var="p"> discarded var=, so `p` did not
        exist and every {p.field} rendered as literal text. Naming what IS in
        scope makes the cause obvious in one line."""
        # EXPR-1: the diagnosis travels in the raised error, not a log line.
        with pytest.raises(ExpressionError) as erro:
            runtime._apply_databinding(
                '{p.name}',
                {'projects': [1, 2, 3], 'projects_result': {}, 'total': 3},
            )
        message = str(erro.value)
        assert '{p.name}' in message
        assert "'p' is not defined" in message
        assert 'projects' in message and 'total' in message

    def test_recordcount_on_the_rows_says_where_it_actually_lives(self, runtime, caplog):
        """q:query publishes `projects` (rows) and `projects_result`
        (metadata). {projects.recordCount} is the natural first guess."""
        with pytest.raises(ExpressionError) as erro:
            runtime._apply_databinding(
                '{projects.recordCount}', {'projects': [{'a': 1}, {'a': 2}]}
            )
        message = str(erro.value)
        assert '.length' in message
        assert '_result' in message


class TestSuggestions:
    def test_a_typo_in_a_key_is_suggested(self):
        ev = ExpressionEvaluator()
        with pytest.raises(ExpressionError, match="did you mean 'name'"):
            ev.evaluate('user.nmae', {'user': {'name': 'Ann', 'age': 30}})

    def test_a_typo_in_a_stdlib_function_is_suggested(self):
        ev = ExpressionEvaluator()
        with pytest.raises(ExpressionError, match="did you mean 'dateFormat'"):
            ev.evaluate('dateFrmat(x)', {'x': 1})

    def test_a_short_scope_is_listed_when_nothing_is_close(self):
        ev = ExpressionEvaluator()
        with pytest.raises(ExpressionError, match="in scope: alpha, beta"):
            ev.evaluate('zzz', {'alpha': 1, 'beta': 2})

    def test_a_large_scope_is_not_dumped(self):
        """A wall of forty names is not a diagnosis."""
        ev = ExpressionEvaluator()
        ctx = {f'var{i}': i for i in range(40)}
        with pytest.raises(ExpressionError) as excinfo:
            ev.evaluate('zzz', ctx)
        assert 'in scope' not in str(excinfo.value)


class TestItDoesNotFloodOrCryWolf:
    def test_one_report_per_distinct_problem(self, caplog):
        """A q:loop over 1,000 rows renders the same broken expression 1,000
        times. One line is a diagnosis; a thousand is noise. (EXPR-4: HTML
        content logs; a q: attribute raises instead, so it cannot flood.)"""
        renderer = HTMLRenderer(ExecutionContext())
        with caplog.at_level(logging.WARNING, logger='quantum.databinding'):
            for _ in range(1000):
                renderer._apply_databinding('{nope}')
        assert len(caplog.records) == 1

    @pytest.mark.parametrize("expr", [
        'session.user', 'application.config', 'request.id',
        'form.email', 'query.page', 'cookie.token',
    ])
    def test_absent_scoped_variables_stay_quiet(self, runtime, caplog, expr):
        """A template rendering before login is the documented contract, not a
        mistake. Warning about it would make the log unreadable."""
        with caplog.at_level(logging.WARNING, logger='quantum.databinding'):
            runtime._apply_databinding('{' + expr + '}', {})
        assert not caplog.records

    def test_a_real_failure_is_still_reported(self, runtime, caplog):
        # EXPR-4: in HTML content, logged. EXPR-1: in a q: attribute, raised.
        with caplog.at_level(logging.WARNING, logger='quantum.databinding'):
            HTMLRenderer(ExecutionContext())._apply_databinding('{nope}')
        assert len(caplog.records) == 1
        with pytest.raises(ExpressionError, match="nope"):
            runtime._apply_databinding('{nope}', {})


class TestOneRepresentationForOneFailure:
    """The same broken expression used to render two different ways depending
    on whether it shared a text node with other content."""

    @pytest.fixture
    def renderer(self):
        return HTMLRenderer(ExecutionContext())

    def test_pure_expression_returns_the_placeholder(self, renderer):
        assert renderer._apply_databinding('{nope}') == '{nope}'

    def test_mixed_content_returns_the_placeholder_too(self, renderer):
        assert renderer._apply_databinding('id #{nope} here') == 'id #{nope} here'

    def test_the_error_marker_no_longer_leaks_to_the_page(self, renderer):
        """'{ERROR: nope}' put an internal variable name in front of the end
        user. The diagnosis belongs in the log."""
        assert 'ERROR' not in renderer._apply_databinding('id #{nope} here')

    @pytest.mark.parametrize("text", [
        # The scoped roots are what actually diverged: the runtime honoured
        # the resolve-to-'' contract and the renderer did not, so the same
        # {form.email} rendered as '' in the execute pass and as literal text
        # in the render pass. The original version of this test checked two
        # inputs, both of which agreed, so it passed while the bug stood.
        '{session.user}', '{application.config}', '{request.id}',
        '{form.email}', '{query.page}', '{cookie.token}',
    ])
    def test_the_runtime_agrees_with_the_renderer(self, runtime, renderer, text):
        # EXPR-3
        assert runtime._apply_databinding(text, {}) == \
            renderer._apply_databinding(text)

    @pytest.mark.parametrize("text", [
        '{nope}', 'id #{nope} here', '{user.missing}', '{items[9]}',
    ])
    def test_undefined_names_raise_in_attributes_and_stay_literal_in_content(
            self, runtime, renderer, text):
        # EXPR-1 vs EXPR-4, deliberately different: a q: attribute is always
        # an expression, so failing there is an error; HTML content also holds
        # code samples and stray braces, so it renders the text and logs.
        with pytest.raises(ExpressionError):
            runtime._apply_databinding(text, {})
        assert renderer._apply_databinding(text) == text


class TestJsonLiteralsAreNotExpressions:
    """A JSON object written into a value is not a broken expression.

    Quantum has no escape for a brace, so `value='[{"a": 1}, {"b": 2}]'` is
    read as databinding: each object fails to parse, is reported, and is then
    left alone (which is why JSON in a .q file still works). The shipped
    examples/python-data-processing.q produced ten warnings for one data
    table, none of them pointing at anything the author could fix.
    """

    @pytest.mark.parametrize("text", [
        '"product": "Laptop", "price": 999',
        '"a": 1',
        "'chave': 'valor'",
        '\n  "multi": "linha",\n  "outra": 2\n',
    ])
    def test_json_object_bodies_are_recognised(self, text):
        from quantum.core import expression_diagnostics as diag
        assert diag.looks_like_json_object(text)

    @pytest.mark.parametrize("text", [
        'user.name', 'items[0]', 'a if b else c', 'total * 2',
        # A dict display in a real expression still gets diagnosed: the
        # quieting is for a value that OPENS with a quoted key.
        'x["chave"]',
    ])
    def test_real_expressions_are_not_mistaken_for_json(self, text):
        from quantum.core import expression_diagnostics as diag
        assert not diag.looks_like_json_object(text)

    def test_a_json_literal_logs_nothing(self, caplog):
        from quantum.core import expression_diagnostics as diag
        diag.reset()
        with caplog.at_level(logging.WARNING):
            diag.report_unresolved('"product": "Laptop"', ValueError("nope"))
        assert caplog.text == ""

    def test_a_real_mistake_still_logs(self, caplog):
        from quantum.core import expression_diagnostics as diag
        diag.reset()
        with caplog.at_level(logging.WARNING):
            diag.report_unresolved('usuario.nome', ValueError("not defined"))
        assert "usuario.nome" in caplog.text

    def test_the_json_survives_databinding_untouched(self, runtime):
        # The warning was noise, not damage — this is what must not change.
        raw = '[{"a": 1}, {"b": 2}]'
        assert runtime._apply_databinding(raw, {}) == raw
