"""
Every q:param attribute except `required` was parsed and thrown away.

The parser collects default, type, min, max, minlength, maxlength, pattern
and enum from each q:param. The runtime's _validate_params looked at exactly
one of them. So

    <q:param name="idade" type="numeric" min="18" max="120" default="30" />

left `idade` undefined — "{idade} did not resolve" — accepted "abc" as a
number, and accepted 7 for a minimum of 18. A component could not trust a
single thing it declared about its own inputs.
"""

import pytest

from quantum.core.ast_nodes import QuantumParam
from quantum.core.parser import QuantumParser
from quantum.runtime.component import ComponentRuntime, ComponentExecutionError


def component(param_xml, body='<q:set name="x" value="1" />'):
    source = f'<q:component name="C">{param_xml}{body}</q:component>'
    return QuantumParser().parse(source)


def run(component_node, **params):
    """Execute and hand back what the component ended up seeing."""
    runtime = ComponentRuntime()
    runtime.execute_component(component_node, params)
    return runtime.execution_context.get_all_variables()


class TestDefaults:
    def test_a_default_defines_the_variable(self):
        node = component('<q:param name="idade" default="30" />')
        assert run(node)["idade"] == "30"

    def test_a_passed_value_wins_over_the_default(self):
        node = component('<q:param name="idade" default="30" />')
        assert run(node, idade="41")["idade"] == "41"

    def test_a_typed_default_is_coerced_like_a_passed_value(self):
        node = component('<q:param name="idade" type="integer" default="30" />')
        assert run(node)["idade"] == 30

    def test_no_default_and_not_required_stays_absent(self):
        node = component('<q:param name="opcional" />')
        assert "opcional" not in run(node)


class TestRequired:
    def test_a_missing_required_param_is_an_error(self):
        node = component('<q:param name="id" required="true" />')
        with pytest.raises(ComponentExecutionError, match="id"):
            run(node)

    def test_a_default_satisfies_required(self):
        node = component('<q:param name="id" required="true" default="7" />')
        assert run(node)["id"] == "7"


class TestTypes:
    def test_integer_arrives_as_an_int(self):
        node = component('<q:param name="n" type="integer" />')
        assert run(node, n="42")["n"] == 42

    def test_number_arrives_as_a_float(self):
        node = component('<q:param name="preco" type="number" />')
        assert run(node, preco="19.90")["preco"] == pytest.approx(19.90)

    def test_boolean_accepts_the_written_forms(self):
        node = component('<q:param name="ativo" type="boolean" />')
        for written in ("true", "yes", "1", "on"):
            assert run(node, ativo=written)["ativo"] is True
        for written in ("false", "no", "0", "off"):
            assert run(node, ativo=written)["ativo"] is False

    def test_a_non_numeric_value_for_a_number_is_an_error(self):
        node = component('<q:param name="n" type="integer" />')
        with pytest.raises(ComponentExecutionError, match="integer"):
            run(node, n="abc")

    def test_a_string_is_left_exactly_as_given(self):
        node = component('<q:param name="s" type="string" />')
        assert run(node, s="007")["s"] == "007"


class TestRanges:
    def test_below_the_minimum_is_refused(self):
        node = component('<q:param name="idade" type="integer" min="18" />')
        with pytest.raises(ComponentExecutionError, match="at least 18"):
            run(node, idade="7")

    def test_above_the_maximum_is_refused(self):
        node = component('<q:param name="idade" type="integer" max="120" />')
        with pytest.raises(ComponentExecutionError, match="at most 120"):
            run(node, idade="900")

    def test_inside_the_range_passes(self):
        node = component(
            '<q:param name="idade" type="integer" min="18" max="120" />')
        assert run(node, idade="41")["idade"] == 41

    def test_the_bounds_themselves_pass(self):
        node = component(
            '<q:param name="idade" type="integer" min="18" max="120" />')
        assert run(node, idade="18")["idade"] == 18
        assert run(node, idade="120")["idade"] == 120


class TestLengthPatternAndEnum:
    def test_minlength_is_enforced(self):
        node = component('<q:param name="senha" minlength="8" />')
        with pytest.raises(ComponentExecutionError, match="at least 8"):
            run(node, senha="curta")

    def test_maxlength_is_enforced(self):
        node = component('<q:param name="apelido" maxlength="4" />')
        with pytest.raises(ComponentExecutionError, match="at most 4"):
            run(node, apelido="comprido")

    def test_a_pattern_is_enforced(self):
        node = component(r'<q:param name="cep" pattern="^\d{5}-\d{3}$" />')
        with pytest.raises(ComponentExecutionError, match="match"):
            run(node, cep="abc")
        assert run(node, cep="01310-100")["cep"] == "01310-100"

    def test_an_invalid_pattern_does_not_reject_everything(self):
        # A broken regex in the source is the author's bug, not the caller's.
        node = component('<q:param name="campo" pattern="[unclosed" />')
        assert run(node, campo="qualquer")["campo"] == "qualquer"

    def test_enum_limits_the_accepted_values(self):
        node = component('<q:param name="cor" enum="azul,verde,vermelho" />')
        with pytest.raises(ComponentExecutionError, match="one of"):
            run(node, cor="roxo")
        assert run(node, cor="verde")["cor"] == "verde"


class TestTheRulesReachTheComponent:
    def test_the_coerced_value_is_what_the_body_sees(self):
        # The point is arithmetic, not string repetition: with n left as the
        # string "2", {n * 2} would be "22". (q:set renders to a string, so
        # the stored result is "4", not 4.)
        node = component(
            '<q:param name="n" type="integer" default="2" />',
            body='<q:set name="dobro" value="{n * 2}" />',
        )
        variables = run(node)
        assert variables["n"] == 2
        assert str(variables["dobro"]) == "4"

    def test_every_error_is_reported_not_just_the_first(self):
        node = component(
            '<q:param name="a" type="integer" min="10" />'
            '<q:param name="b" required="true" />'
        )
        with pytest.raises(ComponentExecutionError) as excinfo:
            run(node, a="1")
        message = str(excinfo.value)
        assert "at least 10" in message and "'b'" in message


class TestQuantumParamItself:
    def test_the_parser_still_collects_everything(self):
        # If this drifts, the runtime silently stops enforcing whatever was
        # dropped — which is exactly how this started.
        node = component(
            '<q:param name="p" type="integer" required="true" default="5" '
            'min="1" max="9" minlength="1" maxlength="3" pattern="\\d+" '
            'enum="1,5,9" />'
        )
        p = node.params[0]
        assert isinstance(p, QuantumParam)
        assert (p.name, p.type, p.required, p.default) == ("p", "integer", True, "5")
        assert (p.min, p.max) == ("1", "9")
        assert (p.minlength, p.maxlength) == (1, 3)
        assert p.pattern == "\\d+"
        assert p.enum == "1,5,9"
