"""
Make an unresolved `{expression}` say something.

FRAMEWORK_PLAN.md Fase 2.2. Both databinding paths catch every exception and
hand back the literal placeholder, which is the right thing to RENDER — a page
should not 500 because one field is missing — but it threw the diagnosis away.
The evaluator already knew that `p` was not defined, or that `projects` is a
list with no `recordCount`; nobody was told.

That silence was the single biggest cost measured in Fase 4: six of the eleven
frictions found while writing one real screen were the same disease, and three
of the four bugs produced no message at all. The time went into discovering
what was wrong, not into fixing it. See DOGFOOD_NOTES.md.

Two things this has to get right to be worth having:

- **Not flood.** A `q:loop` over 1,000 rows evaluates the same broken
  expression 1,000 times. Each distinct problem is reported once.
- **Not cry wolf.** A missing `session.`/`form.` variable is a documented
  contract, not a mistake — templates render before login on purpose. Those
  stay quiet, or the log becomes noise nobody reads.
"""

import logging
import re
import threading

logger = logging.getLogger('quantum.databinding')

# Scopes whose absence is normal: a template renders before login, before a
# form is posted, before a request has query parameters.
QUIET_SCOPES = ('session', 'application', 'request', 'cookie', 'form', 'query')


def root_scope(expression: str) -> str:
    """The leading scope name of an expression, if it has one."""
    return expression.split('.')[0].split('[')[0].strip()


def is_absent_scope(expression: str) -> bool:
    """Whether an unresolved expression is an ABSENT SCOPED VARIABLE.

    Those resolve to '' rather than failing — a template renders before login
    on purpose. Both databinding paths have to agree on this or the same
    {form.email} renders as '' in one pass and as literal text in the other,
    which is exactly what happened: the runtime honoured the contract and the
    renderer leaked the placeholder onto the page.
    """
    return root_scope(expression) in QUIET_SCOPES


# `{"product": "Laptop", "price": 999}` — a JSON object written inside a
# value, not an expression that failed. Quantum has no escape for a brace, so
# a JSON literal in a .q file is read as databinding, complained about once
# per object, and then left alone (which is why it still works). Ten objects
# meant ten warnings pointing at nothing the author can fix.
_JSON_OBJECT_BODY = re.compile(r'^\s*(["\'])(?:(?!\1).)*\1\s*:', re.DOTALL)


def looks_like_json_object(expression: str) -> bool:
    """Whether this is the inside of a JSON object, not an expression."""
    return bool(_JSON_OBJECT_BODY.match(expression))


_seen = set()
_lock = threading.Lock()


def report_unresolved(expression: str, error: BaseException) -> None:
    """Log why a `{expression}` did not resolve, once per distinct problem."""
    if is_absent_scope(expression) or looks_like_json_object(expression):
        return

    reason = str(error) or type(error).__name__
    key = (expression, reason)
    with _lock:
        if key in _seen:
            return
        _seen.add(key)

    logger.warning("{%s} did not resolve: %s", expression, reason)


def reset() -> None:
    """Forget what has been reported. For tests, and for a reloading server."""
    with _lock:
        _seen.clear()
