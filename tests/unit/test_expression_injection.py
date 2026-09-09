"""
Proof that a variable's VALUE is never parsed as expression syntax.

PUBLIC_RELEASE_PLAN.md P0.1. HTMLRenderer._evaluate_condition used to resolve
a condition by substituting variable values into the condition string and
calling eval() on the result. That is not comparison, it is code assembly.

Getting this tested honestly took two attempts. The obvious test — feed a
`().__class__.__mro__[1].__subclasses__()` payload through a condition and
assert the result is False — passes on the vulnerable code too, because the
payload evaluates to a list that is genuinely != 'admin'. Asserting the result
cannot distinguish "was not executed" from "was executed and happened to be
false".

So these tests detect EXECUTION instead:

- Probe carries a property that records being read. If the engine parses the
  value as syntax, the property runs and the probe knows.
- The quoted-value test checks whether the quote characters in a value are
  treated as delimiters or as data — the same shape as SQL injection.

Both were confirmed to FAIL against the pre-migration renderer, which is what
makes them worth having.
"""

import pytest

from quantum.core.expressions import ExpressionEvaluator, ExpressionError
from quantum.runtime.component import ComponentRuntime
from quantum.runtime.execution_context import ExecutionContext
from quantum.runtime.renderer import HTMLRenderer

# The classic escape from eval() with emptied builtins: removing the names
# does not remove the object graph, and this walks from a literal to every
# loaded class, including the ones holding os and subprocess.
MRO_WALK = "().__class__.__mro__[1].__subclasses__()"

PAYLOADS = [
    MRO_WALK,
    "().__class__",
    "[].__class__.__base__.__subclasses__()",
    "__import__('os').getcwd()",
]


class Probe:
    """Records whether anything read its property.

    Reading `probe.poke` is only possible by executing code. If it comes back
    touched, the engine parsed data as syntax.
    """

    def __init__(self):
        self.touched = False

    @property
    def poke(self):
        self.touched = True
        return True


@pytest.fixture
def runtime():
    return ComponentRuntime()


@pytest.fixture
def renderer():
    return HTMLRenderer(ExecutionContext())


class TestValuesAreNotExecuted:
    """The load-bearing tests: they detect execution, not the result."""

    def test_a_value_is_not_executed_by_the_renderer(self, renderer):
        probe = Probe()
        renderer.context.set_variable('probe', probe)
        renderer.context.set_variable('username', 'probe.poke')

        renderer._evaluate_condition("{username} == 'admin'")

        assert not probe.touched, (
            "the value of `username` was parsed as an expression and run"
        )

    def test_a_value_is_not_executed_by_the_runtime(self, runtime):
        probe = Probe()
        runtime._evaluate_condition(
            "{username} == 'admin'", {'probe': probe, 'username': 'probe.poke'}
        )
        assert not probe.touched

    def test_quotes_inside_a_value_are_data_not_delimiters(self, renderer):
        """username is the 7-character string "'admin'", quotes included. It is
        not equal to admin. Only an engine that parses the value as syntax
        would strip the quotes and call it a match."""
        renderer.context.set_variable('username', "'admin'")
        assert renderer._evaluate_condition("{username} == 'admin'") is False

    def test_quotes_inside_a_value_are_data_in_the_runtime(self, runtime):
        assert runtime._evaluate_condition(
            "{username} == 'admin'", {'username': "'admin'"}
        ) is False

    @pytest.mark.parametrize("payload", PAYLOADS)
    def test_a_hostile_value_does_not_match(self, runtime, renderer, payload):
        assert runtime._evaluate_condition(
            "{username} == 'admin'", {'username': payload}
        ) is False
        renderer.context.set_variable('username', payload)
        assert renderer._evaluate_condition("{username} == 'admin'") is False

    def test_the_ordinary_case_still_works(self, runtime, renderer):
        """A defence that breaks the thing it protects is not a defence."""
        assert runtime._evaluate_condition(
            "{username} == 'admin'", {'username': 'admin'}
        ) is True
        renderer.context.set_variable('username', 'admin')
        assert renderer._evaluate_condition("{username} == 'admin'") is True


class TestImportedDataIsNotExecuted:
    """q:data filters were the worst instance of the same bug.

    For every imported record, DataImportService interpolated the field values
    into the filter condition — quoting strings as f"'{value}'" — and called a
    BARE eval() on the result. No restricted globals, no emptied builtins. A
    single quote anywhere in a CSV cell closed the literal and the rest of the
    cell ran as Python, with __import__ available.

    This is the least trusted input the framework handles, so it got the
    weakest defence in the codebase. Verified exploitable before the fix.
    """

    @pytest.fixture
    def data_service(self):
        from quantum.core.features.data_import.src.runtime import DataImportService
        return DataImportService()

    def test_a_hostile_cell_does_not_execute(self, data_service):
        probe = Probe()
        # Breaks out of f"'{value}'" and reads the property, the way an
        # imported CSV cell used to be able to.
        cell = "x' + str(probe.poke) + 'y"
        assert data_service._evaluate_condition(
            "{name} == 'bob'", {'name': cell, 'probe': probe}, None
        ) is False
        assert not probe.touched

    def test_quotes_in_a_cell_are_data(self, data_service):
        assert data_service._evaluate_condition(
            "{name} == 'bob'", {'name': "'bob'"}, None
        ) is False

    def test_ordinary_filters_still_work(self, data_service):
        assert data_service._evaluate_condition(
            "{name} == 'bob'", {'name': 'bob'}, None
        ) is True
        assert data_service._evaluate_condition(
            "{age} > 18", {'age': 30}, None
        ) is True

    def test_numeric_strings_compare_as_numbers(self, data_service):
        """CSV delivers everything as a string, so {age} > 18 used to compare
        '30' against 18 and raise, which the bare except turned into False."""
        assert data_service._evaluate_condition(
            "{age} > 18", {'age': '30'}, None
        ) is True

    def test_computed_fields_still_work(self, data_service):
        assert data_service._evaluate_expression(
            "{price} * {qty}", {'price': 3, 'qty': 4}, None
        ) == 12


class TestPayloadsWrittenIntoTemplatesAreRefused:
    """Lower severity — the template author is more trusted than a form post —
    but a template is not supposed to be able to reach the object graph either,
    and {().__class__} used to evaluate to a real class."""

    @pytest.mark.parametrize("payload", PAYLOADS)
    def test_the_evaluator_refuses_it(self, payload):
        with pytest.raises(ExpressionError):
            ExpressionEvaluator().evaluate(payload, {})

    @pytest.mark.parametrize("payload", PAYLOADS)
    def test_a_condition_written_as_the_payload_is_false(self, runtime, payload):
        assert runtime._evaluate_condition('{' + payload + '}', {}) is False

    def test_databinding_hands_the_payload_back_as_text(self, runtime):
        out = runtime._apply_databinding('{' + MRO_WALK + '}', {})
        assert out == '{' + MRO_WALK + '}'

    def test_dunder_access_on_a_context_object_is_refused(self):
        """Attribute access on real objects stays allowed — query rows need it
        — so closing the graph is done by refusing dunders specifically."""
        with pytest.raises(ExpressionError, match="not accessible"):
            ExpressionEvaluator().evaluate("obj.__class__", {'obj': object()})
