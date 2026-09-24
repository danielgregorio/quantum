"""The one place a `condition` is evaluated (q:if, q:elseif, guards).

ComponentRuntime (statements) and HTMLRenderer (markup) each had their own
copy of this function. They drifted: IF-2 (`condition="1"` was false) existed
in one and not the other. Both call this now.
"""

import re
from typing import Any, Dict

from quantum.core.expression_diagnostics import report_unresolved
from quantum.core.expressions import ExpressionError, ExpressionEvaluator, UndefinedError

_BRACES = re.compile(r'\{([^}]+)\}')


def evaluate_condition(evaluator: ExpressionEvaluator, condition: str,
                       variables: Dict[str, Any], guard: bool = False) -> bool:
    """True or False for a condition, by the rules of SPEC IF-2, EXPR-5, EXPR-8, AUTH-6.

    The condition is evaluated as an expression with the braces stripped:
    the variable NAMES stay in place for the evaluator to resolve, so no
    value is ever parsed as syntax. (It used to interpolate the values into
    the text and eval() the result — code assembled out of data; a record
    named "'; __import__(...)" became executable. PUBLIC_RELEASE_PLAN P0.1.)
    """
    if not condition:
        return False
    stripped = _BRACES.sub(lambda m: m.group(1), condition).strip()
    try:
        # EXPR-8: a key a scope does not have (session.userId before login)
        # is None here, so `not session.authenticated` is true for a visitor.
        return bool(evaluator.evaluate(stripped, variables or {}, absent_scope_key_is_none=True))
    except UndefinedError as exc:
        if guard:
            # AUTH-6: a guard decides whether the page and its actions run.
            # Reading a failure as false would let everything through, so in
            # a guard it is an error: the page fails closed.
            raise ExpressionError(
                f"guard condition {condition!r} could not be evaluated: {exc}. A guard "
                f"must decide; test each part first, e.g. "
                f"`not session.user or not session.user.is_admin`") from exc
        # EXPR-5: a condition is a presence test — a missing name, key or
        # attribute makes it FALSE, never true. Before, the literal
        # placeholder 'session.user.is_admin' came back as a non-empty string,
        # read as true: the admin branch rendered for a logged-out visitor.
        report_unresolved(stripped, ExpressionError(
            f"condition {condition!r} could not be evaluated; treated as false"))
        return False
    except ExpressionError as exc:
        # A syntax error or a function that does not exist is an error:
        # reading it as false is how `age >= 18 && ok` took the else branch
        # for every input.
        raise ExpressionError(f"condition {condition!r} could not be evaluated: {exc}") from exc
