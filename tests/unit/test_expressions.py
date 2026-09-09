"""
Tests for the AST-whitelist expression evaluator.

Fase 2.1 of FRAMEWORK_PLAN.md. This module is standalone for now — nothing
calls it yet. Wiring it in place of the two existing evaluators is a separate,
riskier step, gated by tests/unit/test_expression_corpus.py.

The security tests matter most: `eval()` with an emptied __builtins__ was never
a sandbox, and PUBLIC_RELEASE_PLAN.md P0.1 exists because of it. A whitelist of
AST node types cannot be talked out of its own grammar, and these tests are
what proves it.
"""

import pytest
from datetime import datetime, timedelta

from quantum.core.expressions import (
    ExpressionEvaluator, ExpressionError, coerce_number,
)


@pytest.fixture
def ev():
    return ExpressionEvaluator()


CTX = {
    'a': 17, 'b': 25, 'name': 'Alice', 'items': [1, 2, 3],
    'user': {'name': 'Ann', 'age': 30, 'tags': ['x', 'y']},
    'flag': True, 'empty': '', 'zero': 0, 'price': 9.5,
}


class TestBasics:
    def test_variable(self, ev):
        assert ev.evaluate('a', CTX) == 17

    def test_literal(self, ev):
        assert ev.evaluate('42', CTX) == 42
        assert ev.evaluate("'hi'", CTX) == 'hi'

    def test_undefined_variable_raises(self, ev):
        with pytest.raises(ExpressionError, match="not defined"):
            ev.evaluate('nope', CTX)

    def test_try_evaluate_returns_default(self, ev):
        assert ev.try_evaluate('nope', CTX, default='—') == '—'

    def test_xml_friendly_literals(self, ev):
        assert ev.evaluate('true', CTX) is True
        assert ev.evaluate('false', CTX) is False
        assert ev.evaluate('null', CTX) is None


class TestArithmeticAndCoercion:
    """The bug this phase exists for."""

    def test_numbers_add(self, ev):
        assert ev.evaluate('a + b', CTX) == 42

    def test_numeric_strings_add_instead_of_concatenating(self, ev):
        # The exact failure found through q:agent: an LLM sends its tool
        # arguments as strings, so {a + b} used to produce 1725.
        assert ev.evaluate('a + b', {'a': '17', 'b': '25'}) == 42

    def test_real_strings_still_concatenate(self, ev):
        assert ev.evaluate("name + '!'", CTX) == 'Alice!'

    def test_mixed_numeric_string_and_number(self, ev):
        assert ev.evaluate('a * 2', {'a': '21'}) == 42

    def test_float_coercion(self, ev):
        assert ev.evaluate('a + b', {'a': '0.5', 'b': '0.25'}) == 0.75

    def test_division_by_zero_is_an_error_not_a_crash(self, ev):
        with pytest.raises(ExpressionError, match="division by zero"):
            ev.evaluate('a / 0', CTX)

    def test_booleans_are_not_treated_as_numbers(self, ev):
        assert ev.evaluate("flag + ''", {'flag': 'yes'}) == 'yes'


class TestAccess:
    def test_dotted_dict_access(self, ev):
        assert ev.evaluate('user.name', CTX) == 'Ann'

    def test_nested_dotted_access(self, ev):
        assert ev.evaluate('user.tags', CTX) == ['x', 'y']

    def test_length_on_array(self, ev):
        assert ev.evaluate('items.length', CTX) == 3

    def test_index(self, ev):
        assert ev.evaluate('items[0]', CTX) == 1

    def test_index_then_attribute(self, ev):
        ctx = {'rows': [{'id': 7}]}
        assert ev.evaluate('rows[0].id', ctx) == 7

    def test_missing_key_raises(self, ev):
        with pytest.raises(ExpressionError, match="not found"):
            ev.evaluate('user.missing', CTX)


class TestComparisonAndLogic:
    def test_comparison(self, ev):
        assert ev.evaluate('b > a', CTX) is True

    def test_comparison_coerces_numeric_strings(self, ev):
        assert ev.evaluate('a > b', {'a': '100', 'b': '9'}) is True

    def test_equality(self, ev):
        assert ev.evaluate("name == 'Alice'", CTX) is True

    def test_and_or_not(self, ev):
        assert ev.evaluate('flag and a > 0', CTX) is True
        assert ev.evaluate('not flag', CTX) is False
        assert ev.evaluate('zero or a', CTX) == 17

    def test_in(self, ev):
        assert ev.evaluate('2 in items', CTX) is True

    def test_ternary(self, ev):
        assert ev.evaluate("'yes' if flag else 'no'", CTX) == 'yes'


class TestJavaScriptStyleNegation:
    """`!x` appears in real .q files ({!result.success}), so it is part of the
    language surface whether or not it was ever specified."""

    def test_bang_negates(self, ev):
        assert ev.evaluate('!flag', CTX) is False

    def test_bang_on_dotted_access(self, ev):
        assert ev.evaluate('!r.success', {'r': {'success': False}}) is True

    def test_not_equal_is_untouched(self, ev):
        assert ev.evaluate('a != b', {'a': 5, 'b': 5}) is False

    def test_bang_inside_a_string_is_untouched(self, ev):
        assert ev.evaluate("'a!b'", {}) == 'a!b'

    def test_python_not_still_works(self, ev):
        assert ev.evaluate('not flag', CTX) is False


class TestStdlib:
    def test_now_exists(self, ev):
        assert isinstance(ev.evaluate('now()', {}), datetime)

    def test_date_add_is_what_session_expiry_needed(self, ev):
        """The absence of this is why session.sessionExpiry had to be
        hardcoded to make login work (AUDIT_FIX_PLAN.md Fase 1)."""
        result = ev.evaluate("dateAdd('h', 24)", {})
        delta = result - datetime.now()
        assert timedelta(hours=23, minutes=59) < delta <= timedelta(hours=24)

    def test_date_format(self, ev):
        ctx = {'d': datetime(2026, 9, 7, 14, 30)}
        assert ev.evaluate("dateFormat(d, '%Y-%m-%d')", ctx) == '2026-09-07'

    def test_string_helpers(self, ev):
        assert ev.evaluate('upper(name)', CTX) == 'ALICE'
        assert ev.evaluate("trim('  x  ')", CTX) == 'x'

    def test_collection_helpers(self, ev):
        assert ev.evaluate('len(items)', CTX) == 3
        assert ev.evaluate('first(items)', CTX) == 1
        assert ev.evaluate("join(items, '-')", CTX) == '1-2-3'

    def test_round(self, ev):
        assert ev.evaluate('round(price)', CTX) == 10
        assert ev.evaluate('round(price, 1)', CTX) == 9.5

    def test_user_functions_are_merged_in(self):
        ev = ExpressionEvaluator(functions={'double': lambda x: x * 2})
        assert ev.evaluate('double(21)', {}) == 42

    def test_unknown_function_raises(self, ev):
        with pytest.raises(ExpressionError, match="not defined"):
            ev.evaluate('nosuchfn(1)', {})


class TestSecurity:
    """Why this module exists. eval() with an emptied __builtins__ is not a
    sandbox — it is escapable through attribute traversal. A node whitelist is."""

    def test_dunder_attribute_is_refused(self, ev):
        with pytest.raises(ExpressionError, match="not accessible"):
            ev.evaluate("().__class__", {})

    def test_the_classic_sandbox_escape_is_refused(self, ev):
        with pytest.raises(ExpressionError):
            ev.evaluate("().__class__.__mro__[1].__subclasses__()", {})

    def test_import_is_not_expressible(self, ev):
        with pytest.raises(ExpressionError):
            ev.evaluate("__import__('os')", {})

    def test_lambda_is_refused(self, ev):
        with pytest.raises(ExpressionError, match="not allowed"):
            ev.evaluate("(lambda: 1)()", {})

    def test_comprehension_is_refused(self, ev):
        with pytest.raises(ExpressionError, match="not allowed"):
            ev.evaluate("[x for x in items]", CTX)

    def test_attribute_call_on_object_is_refused(self, ev):
        """Only named calls are allowed, so obj.method() cannot be reached."""
        with pytest.raises(ExpressionError, match="only named function calls"):
            ev.evaluate("name.upper()", CTX)

    def test_statements_are_not_expressions(self, ev):
        with pytest.raises(ExpressionError, match="invalid expression"):
            ev.evaluate("x = 1", {})

    def test_absurdly_long_input_is_refused(self, ev):
        with pytest.raises(ExpressionError, match="exceeds"):
            ev.evaluate("1+" * 2000 + "1", {})


class TestCoerceNumber:
    @pytest.mark.parametrize("value,expected", [
        ('17', 17), ('0.5', 0.5), ('  42  ', 42), ('-3', -3),
        ('abc', 'abc'), ('', ''), (17, 17), (True, True), (None, None),
    ])
    def test_coercion(self, value, expected):
        assert coerce_number(value) == expected

    def test_booleans_are_left_alone(self):
        assert coerce_number(True) is True


class TestItCannotHangTheRequest:
    """A template is evaluated inside a request, and nothing above the
    evaluator imposes a timeout.

    Found by attacking the evaluator directly rather than reading it — an
    earlier audit had only glanced at it, and it is now the single choke point
    every expression in the framework passes through. Every escape attempt was
    refused (dunder, mro walk, __import__, lambda, comprehension, f-string,
    walrus, the format() trick that defeats ExpressionCache's denylist). These
    two got through, and neither needs an attacker: a typo is enough.
    """

    @pytest.mark.parametrize("expr", [
        '9**9**9',          # did not return
        '10**100000000',    # did not return
        '2**4096',
    ])
    def test_huge_powers_are_refused_not_attempted(self, ev, expr):
        with pytest.raises(ExpressionError, match="too large"):
            ev.evaluate(expr, {})

    @pytest.mark.parametrize("expr,ctx", [
        ("'a' * 999999999", {}),        # allocated ~1 GB and returned
        ("items * 999999999", {'items': [1, 2, 3]}),
    ])
    def test_huge_repetition_is_refused(self, ev, expr, ctx):
        with pytest.raises(ExpressionError, match="exhaust memory"):
            ev.evaluate(expr, ctx)

    @pytest.mark.parametrize("expr,ctx,expected", [
        ('2**10', {}, 1024),
        ('price ** 2', {'price': 9}, 81),
        ('2 ** -1', {}, 0.5),
        ('1 ** 999999999', {}, 1),      # cheap regardless of the exponent
        ("'-' * 40", {}, '-' * 40),
        ('items * 3', {'items': [1, 2]}, [1, 2, 1, 2, 1, 2]),
    ])
    def test_real_arithmetic_is_untouched(self, ev, expr, ctx, expected):
        assert ev.evaluate(expr, ctx) == expected


class TestOsGuardasCobriamSoMetadeDosCasos:
    """As guardas de custo so valiam para inteiro ** inteiro.

    `_guard_pow` comecava com

        if not isinstance(left, int) or not isinstance(right, int):
            return

    entao QUALQUER mistura com float passava direto e chegava ao operador:
    `2.0 ** 100000000` levantava OverflowError, que nao e ExpressionError e
    portanto subia pelo handler da requisicao como um 500 sem explicacao —
    exatamente o que a guarda existe para evitar.

    E nada limitava a PROFUNDIDADE da arvore. `_eval` desce recursivamente e
    o limite do Python (~1000 quadros) e compartilhado com Flask, o executor
    e o renderer, entao `{---...1}` com mil sinais levantava RecursionError:
    de novo, nao e ExpressionError, e de novo vira 500 — com o interpretador
    raspando o limite da pilha no caminho.
    """

    @pytest.mark.parametrize("expr", [
        '2.0 ** 100000000',       # float ** int
        '2 ** 1e9',               # int ** float
        '2.5 ** 1e6',
    ])
    def test_potencia_com_float_tambem_e_recusada(self, ev, expr):
        with pytest.raises(ExpressionError, match="too large"):
            ev.evaluate(expr, {})

    def test_um_float_que_estoura_o_expoente_vira_ExpressionError(self):
        """`1e300 ** 2` cabe na estimativa de bits e estoura assim mesmo."""
        ev = ExpressionEvaluator()
        with pytest.raises(ExpressionError):
            ev.evaluate('1e300 ** 2', {})

    @pytest.mark.parametrize("expr,esperado", [
        ('2.0 ** 3', 8.0),
        ('0.5 ** 1e9', 0.0),
        ('(-2.0) ** 5', -32.0),
        ('2 ** -3', 0.125),
        ('1.0 ** 999999999', 1.0),
    ])
    def test_potencias_baratas_com_float_continuam_passando(
            self, ev, expr, esperado):
        assert ev.evaluate(expr, {}) == esperado

    def test_uma_expressao_funda_demais_e_recusada(self, ev):
        with pytest.raises(ExpressionError, match="nested more than"):
            ev.evaluate('-' * 500 + '1', {})

    def test_a_recusa_vem_antes_de_qualquer_recursao(self, ev):
        """Nao pode ser RecursionError: tem de ser ExpressionError."""
        try:
            ev.evaluate('-' * 500 + '1', {})
        except ExpressionError:
            pass
        except RecursionError:
            pytest.fail("RecursionError escapou como RecursionError")

    def test_profundidade_normal_continua_passando(self, ev):
        assert ev.evaluate('-' * 20 + '1', {}) == 1     # par: volta positivo
        assert ev.evaluate('-' * 21 + '1', {}) == -1
        assert ev.evaluate('(' * 30 + '1' + ')' * 30, {}) == 1
        assert ev.evaluate('1 + 2 * 3 - 4 / 2', {}) == 5.0


class TestEscapesThatWereTried:
    """Pinned so a future change to the whitelist cannot quietly reopen one.

    Each of these was run against the live evaluator; all were refused.
    """

    @pytest.mark.parametrize("expr,ctx", [
        ('().__class__', {}),
        ("getattr(x, '__class__')", {'x': ()}),
        ('().__class__.__mro__[1].__subclasses__()', {}),
        ("__import__('os')", {}),
        # The exact payload that walks past ExpressionCache's regex denylist,
        # because that denylist scans source text and this one does not
        # contain the dunder until Python concatenates the literals.
        ('("{0.__cla" "ss__}").format(x)', {'x': ()}),
        ('f"{x}"', {'x': 1}),
        ('(y := 1)', {}),
        ('(lambda: 1)()', {}),
        ('[i for i in items]', {'items': [1]}),
        ('(i for i in items)', {'items': [1]}),
        ('name.upper()', {'name': 'a'}),
        ('fns[0]()', {'fns': [print]}),
        ('f()', {'f': print}),
    ])
    def test_refused(self, ev, expr, ctx):
        with pytest.raises(ExpressionError):
            ev.evaluate(expr, ctx)
