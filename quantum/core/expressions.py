"""
Quantum expression evaluator.

One evaluator, built on `ast.parse` with a node whitelist, to replace the two
parallel hand-rolled ones (6 `_evaluate_*` methods in runtime/component.py, 4
more in runtime/renderer.py) and the six `eval()` calls they rely on. See
FRAMEWORK_PLAN.md Fase 2.1.

Two things this fixes by construction:

- **Security.** `eval()` with an emptied `__builtins__` is not a sandbox — it
  is bypassable through attribute traversal
  (`().__class__.__mro__[1].__subclasses__()`). A whitelist of AST node types
  cannot be talked out of its own grammar. This closes P0.1 of
  PUBLIC_RELEASE_PLAN.md.
- **Coercion.** `{a + b}` where the values arrived as strings — from an LLM
  tool call, a form field, a query parameter — concatenated instead of adding.
  Numeric-looking operands are coerced for arithmetic and comparison.

The grammar is deliberately small, and it was measured rather than guessed:
across 1,224 expressions in examples/*.q, 57% are a bare variable or a dotted
access, and the whole arithmetic/comparison/call surface is about 15%.
"""

import ast
import contextvars
import math
import operator
import re
from typing import Any, Callable, Dict, Optional

from quantum.core.expression_stdlib import STDLIB

# EXPR-8: in a condition, a key a scope does not have (`session.userId`
# before login) is absent, not a failure — see ExpressionEvaluator.evaluate.
_SCOPES = ('session', 'application', 'request', 'cookie', 'form', 'query')
_ABSENT_SCOPE_KEY_IS_NONE = contextvars.ContextVar('absent_scope_key_is_none', default=False)


class ExpressionError(Exception):
    """Raised when an expression cannot be evaluated."""


class UndefinedError(ExpressionError):
    """A name, key or attribute that does not exist.

    Kept apart from the other failures because a condition is a presence test
    (EXPR-5): `<q:if condition="flash">` is false before there is a flash, but
    `a === b` or a misspelled function is still an error.
    """


# `{n}`, `{n,}` and `{n,m}` are regex quantifiers, not Quantum expressions.
# They occur for real: examples/form_validation.q has pattern="\d{10,11}" and
# examples/python-scripting.q has r'[a-zA-Z]{2,}'. The old evaluator left them
# alone only by accident — it failed to evaluate them and handed the literal
# back. This evaluator would happily read `{10,11}` as the tuple (10, 11) and
# silently corrupt the validation pattern, so the case is excluded on purpose.
#
# The underlying gap is that Quantum has no escape for a literal brace. Until
# it has one, this heuristic is the seam, and it is deliberately narrow:
# digits and at most one comma, nothing else.
_REGEX_QUANTIFIER = re.compile(r'^\d+\s*(,\s*\d*)?$')


def is_regex_quantifier(content: str) -> bool:
    """True when a `{...}` group should be left as literal text.

    A q: attribute that is ONLY `{5}` is the number 5 (EXPR-7) — the runtime
    checks that case before calling this. Inside other text, `[0-9]{3}` stays a
    quantifier.
    """
    return bool(_REGEX_QUANTIFIER.match(content.strip()))


# Node types the evaluator accepts. Anything else is refused by construction —
# notably Lambda, comprehensions, walrus, imports, and any form of statement.
_ALLOWED_NODES = (
    ast.Expression, ast.Constant, ast.Name, ast.Load,
    ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.IfExp,
    ast.Attribute, ast.Subscript, ast.Slice,
    ast.Dict, ast.List, ast.Tuple, ast.Set,
    ast.Call, ast.keyword,
    # operators
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.USub, ast.UAdd, ast.Not,
    ast.And, ast.Or,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.In, ast.NotIn,
)

_BIN_OPS: Dict[type, Callable[[Any, Any], Any]] = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
}

_CMP_OPS: Dict[type, Callable[[Any, Any], Any]] = {
    ast.Eq: operator.eq, ast.NotEq: operator.ne,
    ast.Lt: operator.lt, ast.LtE: operator.le,
    ast.Gt: operator.gt, ast.GtE: operator.ge,
    ast.In: lambda a, b: _contains(b, a), ast.NotIn: lambda a, b: not _contains(b, a),
}

_UNARY_OPS: Dict[type, Callable[[Any], Any]] = {
    ast.USub: operator.neg, ast.UAdd: operator.pos, ast.Not: operator.not_,
}


def coerce_number(value: Any) -> Any:
    """Turn a numeric-looking string into a number, leave everything else.

    This is the difference between {a + b} adding and concatenating when the
    values came from an LLM, a form post or a query parameter — all of which
    deliver strings.
    """
    if isinstance(value, bool) or not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return value
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return value


def _names_of(target: Any) -> list:
    """The names a reader could plausibly have meant, for a suggestion."""
    if isinstance(target, dict):
        return [k for k in target if isinstance(k, str) and not k.startswith('_')]
    return [a for a in dir(target) if not a.startswith('_')]


def _suggest(wanted: str, target: Any, limit: int = 3) -> str:
    """`, did you mean x, y?` — or nothing when there is no near match.

    The reason this exists: writing a real screen against Quantum, the two
    failures that cost the most time were {p.name} (var= had been silently
    discarded, so `p` did not exist) and {projects.recordCount} (the metadata
    lives on `projects_result`). Both were resolvable in seconds from a list of
    what WAS in scope, and neither message offered one. See DOGFOOD_NOTES.md.
    """
    import difflib
    names = _names_of(target)
    if not names:
        return ""
    close = difflib.get_close_matches(wanted, names, n=limit, cutoff=0.6)
    if close:
        return ", did you mean " + " or ".join(repr(c) for c in close) + "?"
    # No near match: naming what IS available beats naming what is not, but
    # only while the list is short enough to read.
    if len(names) <= 8:
        return " (in scope: " + ", ".join(sorted(names)) + ")"
    return ""


# A template is evaluated inside a request. An expression that never returns
# is a hung worker, and these two do it with three characters:
#
#   {9**9**9}          -> does not return
#   {10**100000000}    -> does not return
#   ({'a' * 999999999} allocated ~1 GB; since EXPR-7 `*` needs numbers.)
#
# No dunder, no escape, no attacker — a typo in a template is enough, and there
# is no timeout anywhere above this to catch it. The caps are far above any
# real expression: 4096 bits is a 1233-digit number.
_MAX_POW_BITS = 4096


def _guard_pow(left: Any, right: Any) -> None:
    """Refuses an `a ** b` that is too large — integer OR float.

    It required `isinstance` int on BOTH sides, so any mix went straight
    through: `2.0 ** 100000000` and `2 ** 1e9` reached the operator and raised
    `OverflowError`, which is not an `ExpressionError` — it went up through the
    request handler as an unexplained 500, instead of the message this
    function exists to give.
    """
    if isinstance(left, bool) or isinstance(right, bool):
        return
    if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
        return
    if right < 0 or left in (0, 1, -1):
        return
    try:
        if isinstance(left, int) and isinstance(right, int):
            # bits(left**right) ≈ right * bits(left)
            bits = right * max(left.bit_length(), 1)
        else:
            base = abs(float(left))
            if base <= 1.0:
                return
            bits = float(right) * math.log2(base)
    except (OverflowError, ValueError):
        # O proprio calculo do tamanho estourou: e grande demais.
        bits = float('inf')

    if bits > _MAX_POW_BITS:
        raise ExpressionError(
            f"{left}**{right} is too large to compute "
            f"(over {_MAX_POW_BITS} bits); this would hang the request"
        )


def _both_numeric(left: Any, right: Any) -> bool:
    return isinstance(left, (int, float)) and isinstance(right, (int, float)) \
        and not isinstance(left, bool) and not isinstance(right, bool)


def _equal(left: Any, right: Any) -> bool:
    """`==` as expressions mean it: numeric-looking text equals its number."""
    cl, cr = coerce_number(left), coerce_number(right)
    return cl == cr if _both_numeric(cl, cr) else left == right


def _contains(container: Any, item: Any) -> bool:
    """EXPR-14: `in` compares like `==`. `'5' in [5]` was false while
    `'5' == 5` was true, so a value from a form never matched a list of numbers."""
    if isinstance(container, str):
        return (item if isinstance(item, str) else str(item)) in container
    if isinstance(container, (list, tuple, set, frozenset, dict)):
        return any(_equal(item, element) for element in container)
    raise TypeError(f"'in' needs a list, an object or a text, not {type(container).__name__}")



def _normalise_js_operators(source: str) -> str:
    """Rewrite JavaScript-style `!x`, `a && b` and `a || b` into Python's
    `not`, `and` and `or`.

    Real .q files use them ({!result.success} appears across the examples, and
    docs/guide/conditionals.md teaches `age >= 18 && hasLicense`), so they are
    part of the language surface. `&&` and `||` were never translated: the
    condition failed to parse and, read as false, took the else branch for
    every input. `!=` is left alone, and nothing inside a string literal is
    touched.
    """
    if '!' not in source and '&&' not in source and '||' not in source:
        return source

    out = []
    i = 0
    quote = None
    while i < len(source):
        ch = source[i]
        if quote:
            out.append(ch)
            if ch == quote and (i == 0 or source[i - 1] != "\\"):
                quote = None
            i += 1
            continue
        if ch in ('"', "'"):
            quote = ch
            out.append(ch)
            i += 1
            continue
        if ch == '!' and i + 1 < len(source) and source[i + 1] != '=':
            out.append('not ')
            i += 1
            continue
        if source[i:i + 2] in ('&&', '||'):
            out.append(' and ' if ch == '&' else ' or ')
            i += 2
            continue
        out.append(ch)
        i += 1
    return ''.join(out)


# EXPR-10: what a JavaScript habit is called here. `Math.ceil(x)` and
# `text.split(' ')` are the first things people write; the bare "only named
# function calls are allowed" did not say what to write instead.
_JS_EQUIVALENTS = {
    'Math.ceil': 'ceil(x)', 'Math.floor': 'floor(x)', 'Math.round': 'round(x)',
    'Math.max': 'max(a, b)', 'Math.min': 'min(a, b)', 'Math.abs': 'abs(x)',
    'Date.now': 'now()', 'parseInt': 'int(x)', 'parseFloat': 'float(x)',
    'split': "split(text, ' ')", 'join': "join(items, ', ')", 'toUpperCase': 'upper(text)',
    'toLowerCase': 'lower(text)', 'trim': 'trim(text)', 'replace': 'replace(text, old, new)',
    'includes': 'contains(text, part)', 'indexOf': 'contains(text, part)',
}


def _method_hint(func: ast.AST) -> str:
    if not isinstance(func, ast.Attribute):
        return ""
    base = func.value.id if isinstance(func.value, ast.Name) else None
    key = f"{base}.{func.attr}" if base in ('Math', 'Date') else func.attr
    if key in _JS_EQUIVALENTS:
        written = key if '.' in key else f"x.{func.attr}"
        return f"; write {_JS_EQUIVALENTS[key]} instead of {written}(...)"
    return f"; call functions by name, e.g. {func.attr}(x), not x.{func.attr}()"


def names_read(expression: str) -> set:
    """The root names an expression reads — `user` in `user.name > 1` — not the
    functions it calls. An expression that does not parse reads nothing here;
    evaluating it reports the error."""
    try:
        tree = ast.parse(_normalise_js_operators(expression.strip()), mode='eval')
    except SyntaxError:
        return set()
    called = {id(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    return {n.id for n in ast.walk(tree)
            if isinstance(n, ast.Name) and id(n) not in called}


class ExpressionEvaluator:
    """Evaluates Quantum `{...}` expressions against a variable context."""

    def __init__(self, functions: Optional[Dict[str, Callable]] = None,
                 max_length: int = 2000,
                 function_resolver: Optional[Callable[[str], Optional[Callable]]] = None):
        """
        Args:
            functions: extra callables available to expressions.
            max_length: refuse expressions longer than this.
            function_resolver: consulted for a name that is not in
                `functions`. This is how a component's own q:function
                becomes callable from `{somaTotal(itens)}` — the registry
                is filled while the component executes, so it cannot be
                handed over as a dict when the evaluator is built.
        """
        # Stdlib plus whatever the component registered (q:function).
        self.functions: Dict[str, Callable] = dict(STDLIB)
        if functions:
            self.functions.update(functions)
        self.max_length = max_length
        self.function_resolver = function_resolver

    # -- public API --------------------------------------------------------

    def evaluate(self, expression: str, context: Dict[str, Any],
                 absent_scope_key_is_none: bool = False) -> Any:
        """Evaluate an expression, raising ExpressionError on any failure.

        absent_scope_key_is_none (conditions, EXPR-8): `session.x` where the
        scope has no `x` reads as None instead of raising. A condition is a
        presence test, and a scope key that is not there yet is the ordinary
        case (a page runs before login) — raising made the WHOLE condition
        false, so `not session.authenticated` was false for a visitor with no
        session and a guard written that way never fired.
        """
        marca = _ABSENT_SCOPE_KEY_IS_NONE.set(absent_scope_key_is_none)
        try:
            return self._evaluate(expression, context)
        finally:
            _ABSENT_SCOPE_KEY_IS_NONE.reset(marca)

    def _evaluate(self, expression: str, context: Dict[str, Any]) -> Any:
        if expression is None:
            raise ExpressionError("expression is None")

        source = expression.strip()
        if not source:
            raise ExpressionError("empty expression")
        if len(source) > self.max_length:
            raise ExpressionError(f"expression exceeds {self.max_length} characters")

        source = _normalise_js_operators(source)

        try:
            tree = ast.parse(source, mode='eval')
        except SyntaxError as exc:
            raise ExpressionError(f"invalid expression {source!r}: {exc.msg}") from exc

        self._validate(tree, source)
        try:
            return self._eval(tree.body, context)
        except RecursionError as exc:
            # The depth guard covers the EXPRESSION; the context can be deep
            # too (a dict that refers to itself, for example). A template
            # expression must never bring the request down with an error that
            # is not an ExpressionError.
            raise ExpressionError(
                f"evaluating {source[:60]!r} ran out of stack") from exc

    def try_evaluate(self, expression: str, context: Dict[str, Any],
                     default: Any = None) -> Any:
        """Evaluate, returning `default` instead of raising.

        For render paths, where a bad expression should not take down the page.
        """
        try:
            return self.evaluate(expression, context)
        except ExpressionError:
            return default

    # -- validation --------------------------------------------------------

    # The tree's maximum depth. `_eval` recurses, and Python's recursion
    # limit is ~1000 frames SHARED with everything already on the stack
    # (Flask, the executor, the renderer). `{-------...1}` with a thousand
    # signs raised RecursionError — which is not an ExpressionError and so
    # became a 500 — and still left the interpreter scraping the limit. A
    # hundred levels is deeper than any real template expression and stays
    # well away from the edge.
    MAX_DEPTH = 100

    def _validate(self, tree: ast.AST, source: str):
        self._check_depth(tree.body if isinstance(tree, ast.Expression)
                          else tree, source)
        for node in ast.walk(tree):
            if not isinstance(node, _ALLOWED_NODES):
                raise ExpressionError(
                    f"{type(node).__name__} is not allowed in expressions "
                    f"({source!r})"
                )
            # Dunder traversal is the classic eval sandbox escape.
            if isinstance(node, ast.Attribute) and node.attr.startswith('__'):
                raise ExpressionError(
                    f"attribute {node.attr!r} is not accessible ({source!r})"
                )
            if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                    and node.value.startswith('__'):
                raise ExpressionError(f"dunder string is not allowed ({source!r})")

    def _check_depth(self, root: ast.AST, source: str) -> None:
        """Measures the depth without recursion — measuring recursively would
        have the same problem the measurement exists to avoid."""
        stack = [(root, 1)]
        while stack:
            node, level = stack.pop()
            if level > self.MAX_DEPTH:
                raise ExpressionError(
                    f"expression is nested more than {self.MAX_DEPTH} levels "
                    f"deep ({source[:60]!r}...); this would exhaust the stack"
                )
            for child in ast.iter_child_nodes(node):
                stack.append((child, level + 1))

    # -- evaluation --------------------------------------------------------

    def _eval(self, node: ast.AST, ctx: Dict[str, Any]) -> Any:
        if isinstance(node, ast.Constant):
            return node.value

        if isinstance(node, ast.Name):
            return self._lookup(node.id, ctx)

        if isinstance(node, ast.BinOp):
            left = self._eval(node.left, ctx)
            right = self._eval(node.right, ctx)
            op = _BIN_OPS.get(type(node.op))
            if op is None:
                raise ExpressionError(f"unsupported operator {type(node.op).__name__}")

            # String + string stays concatenation only when neither side is a
            # number in disguise.
            cl, cr = coerce_number(left), coerce_number(right)
            if _both_numeric(cl, cr):
                left, right = cl, cr
            elif isinstance(node.op, ast.Add) and not (
                    (isinstance(left, str) and isinstance(right, str))
                    or (isinstance(left, list) and isinstance(right, list))):
                # EXPR-7: '+' adds numbers or joins two texts / two lists. The
                # mixed case used to surface Python's "can only concatenate
                # str (not "int") to str".
                raise ExpressionError(
                    f"'+' needs two numbers, two texts or two lists, got {left!r} and {right!r}")
            elif not isinstance(node.op, ast.Add):
                # EXPR-7: arithmetic is on numbers. Python would repeat text
                # ('ab' * 3), format it ('%s' % x) or fail with its own
                # message; `n * factorial(n - 1)` whose base case returned the
                # text '{1}' produced '{1}{1}{1}{1}{1}' and no error.
                simbolo = {ast.Sub: '-', ast.Mult: '*', ast.Div: '/', ast.FloorDiv: '//',
                           ast.Mod: '%', ast.Pow: '**'}[type(node.op)]
                raise ExpressionError(
                    f"'{simbolo}' needs two numbers, got {left!r} and {right!r}")

            # Refuse what would not finish, before attempting it.
            if isinstance(node.op, ast.Pow):
                _guard_pow(left, right)

            try:
                return op(left, right)
            except ZeroDivisionError:
                raise ExpressionError("division by zero")
            except TypeError as exc:
                raise ExpressionError(f"cannot apply operator: {exc}") from exc
            except (OverflowError, MemoryError) as exc:
                # `1e300 ** 2` fits the bit estimate and overflows anyway,
                # because a float has a maximum exponent. Without this the
                # error is not an ExpressionError and goes up as a 500.
                raise ExpressionError(
                    f"the result is too large to represent: {exc}") from exc

        if isinstance(node, ast.UnaryOp):
            operand = self._eval(node.operand, ctx)
            op = _UNARY_OPS.get(type(node.op))
            if op is None:
                raise ExpressionError(f"unsupported unary {type(node.op).__name__}")
            if isinstance(node.op, (ast.USub, ast.UAdd)):
                operand = coerce_number(operand)
            return op(operand)

        if isinstance(node, ast.BoolOp):
            # EXPR-6: short-circuit, as in Python. Every operand used to be
            # evaluated first, so `user and user.name` failed with "variable
            # 'user' is not defined"-style errors exactly when the left side
            # was there to guard the right.
            value = False
            for operand in node.values:
                value = self._eval(operand, ctx)
                if isinstance(node.op, ast.And) and not value:
                    return value
                if isinstance(node.op, ast.Or) and value:
                    return value
            return value

        if isinstance(node, ast.Compare):
            left = self._eval(node.left, ctx)
            for op_node, comparator in zip(node.ops, node.comparators):
                right = self._eval(comparator, ctx)
                op = _CMP_OPS.get(type(op_node))
                if op is None:
                    raise ExpressionError(f"unsupported comparison {type(op_node).__name__}")
                cl, cr = coerce_number(left), coerce_number(right)
                if _both_numeric(cl, cr) and not isinstance(op_node, (ast.In, ast.NotIn)):
                    left_cmp, right_cmp = cl, cr
                else:
                    left_cmp, right_cmp = left, right
                try:
                    if not op(left_cmp, right_cmp):
                        return False
                except TypeError as exc:
                    raise ExpressionError(f"cannot compare: {exc}") from exc
                left = right
            return True

        if isinstance(node, ast.IfExp):
            return self._eval(node.body, ctx) if self._eval(node.test, ctx) \
                else self._eval(node.orelse, ctx)

        if isinstance(node, ast.Attribute):
            # `session.userId` is written as an attribute access, but the
            # context keeps the scope variable under the FLAT dotted KEY
            # 'session.userId' — there is no `session` object. Without this,
            # a PRESENT session variable raised, and the caller turned that
            # into '' or False: `<q:set value="{session.userId}"/>` wrote an
            # empty value in an INSERT, and `<q:if condition="{session.userRole
            # == 'admin'}">` was False on both branches. The documentation
            # teaches exactly those two patterns.
            flat = self._dotted_name(node)
            if flat is not None and flat in ctx:
                return ctx[flat]
            if (_ABSENT_SCOPE_KEY_IS_NONE.get() and isinstance(node.value, ast.Name)
                    and node.value.id in _SCOPES):
                scope = ctx.get(node.value.id)
                if scope is None or (isinstance(scope, dict) and node.attr not in scope):
                    return None
            return self._attribute(self._eval(node.value, ctx), node.attr)

        if isinstance(node, ast.Subscript):
            # EXPR-13: the step of a slice was silently dropped —
            # `[1, 2, 3][::-1]` returned [1, 2, 3].
            if isinstance(node.slice, ast.Slice) and node.slice.step is not None:
                raise ExpressionError(
                    "a slice with a step ([a:b:step]) is not supported; "
                    "use [a:b], or sort(x, true) to reverse a sorted list")
            target = self._eval(node.value, ctx)
            key = self._eval(node.slice, ctx) if not isinstance(node.slice, ast.Slice) \
                else slice(
                    self._eval(node.slice.lower, ctx) if node.slice.lower else None,
                    self._eval(node.slice.upper, ctx) if node.slice.upper else None,
                )
            try:
                if isinstance(target, dict):
                    # EXPR-16 (was G19): a missing key is the same error as
                    # `d.missing` (EXPR-1). It used to be null, so a typo in
                    # d['naem'] rendered nothing; an optional key is read with
                    # get(d, key, default) or tested with `key in d`.
                    if key in target:
                        return target[key]
                    raise UndefinedError(
                        f"key {key!r} not found"
                        f"{_suggest(key, target) if isinstance(key, str) else ''}")
                return target[key]
            except (IndexError, KeyError) as exc:
                raise UndefinedError(f"cannot index: {exc}") from exc
            except TypeError as exc:
                raise ExpressionError(f"cannot index: {exc}") from exc

        if isinstance(node, ast.Dict):
            return {self._eval(k, ctx): self._eval(v, ctx)
                    for k, v in zip(node.keys, node.values)}

        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            values = [self._eval(e, ctx) for e in node.elts]
            return set(values) if isinstance(node, ast.Set) else \
                (tuple(values) if isinstance(node, ast.Tuple) else values)

        if isinstance(node, ast.Call):
            return self._call(node, ctx)

        raise ExpressionError(f"cannot evaluate {type(node).__name__}")

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _dotted_name(node: ast.Attribute):
        """'session.userId' from an Attribute, or None if the base is not a name.

        Only a pure chain of names becomes a flat key: `a.b.c` yes, `f(x).b`
        or `items[0].name` no — there a key lookup would be wrong, and the
        real attribute access is what counts.
        """
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if not isinstance(current, ast.Name):
            return None
        parts.append(current.id)
        return '.'.join(reversed(parts))

    def _lookup(self, name: str, ctx: Dict[str, Any]) -> Any:
        if name in ctx:
            return ctx[name]
        if name == 'true':
            return True
        if name == 'false':
            return False
        if name == 'null':
            return None
        raise UndefinedError(
            f"variable {name!r} is not defined{_suggest(name, ctx)}"
        )

    def _attribute(self, target: Any, attr: str) -> Any:
        if isinstance(target, dict):
            if attr in target:
                return target[attr]
            raise UndefinedError(
                f"key {attr!r} not found{_suggest(attr, target)}"
            )
        if isinstance(target, (list, tuple, str)) and attr == 'length':
            return len(target)
        if hasattr(target, attr):
            value = getattr(target, attr)
            # An attribute must NEVER hand out a callable.
            #
            # `_call` only accepts a function by name (it blocks `x.method()`)
            # and there is a dunder guard over the AST — but both were
            # bypassed like this:
            #
            #     max([target], key='{0.__class__.__base__}'.format)
            #
            # `'...'.format` is an ATTRIBUTE ACCESS that returns a bound
            # method; passed as `key=` to a stdlib function, it INVOKES it,
            # and str.format does attribute traversal at run time — where the
            # dunder guard, which looks at the text, does not reach.
            # Reproduced: the expression above ran an @property of the
            # context's object.
            #
            # A template reads data (`user.name`); it does not pick up a
            # method to pass along. Refusing callables closes the whole class
            # of gadget, not just `format`.
            if callable(value) and not isinstance(value, type):
                raise ExpressionError(
                    f"attribute {attr!r} is a method, not data; expressions "
                    f"read values, they do not pass functions around"
                )
            return value
        if isinstance(target, (list, tuple)):
            # The q:query case: `projects` is the rows and `projects_result`
            # holds recordCount, so {projects.recordCount} is the natural
            # first guess and it is wrong. Say so instead of going quiet.
            raise ExpressionError(
                f"{type(target).__name__} of {len(target)} items has no "
                f"{attr!r}; use .length for the count, or the query's "
                f"<name>_result for its metadata"
            )
        raise UndefinedError(
            f"attribute {attr!r} not found on {type(target).__name__}"
            f"{_suggest(attr, target)}"
        )

    def _call(self, node: ast.Call, ctx: Dict[str, Any]) -> Any:
        if not isinstance(node.func, ast.Name):
            raise ExpressionError("only named function calls are allowed" + _method_hint(node.func))
        fn = self.functions.get(node.func.id)
        if fn is None and self.function_resolver is not None:
            # A q:function declared by the component being executed.
            # {countElements(myArray)} used to resolve to nothing at all: the
            # placeholder was left in the text and the surrounding q:set then
            # failed with "could not convert string to float:
            # '{sumNumbers(myNumbers)}'".
            fn = self.function_resolver(node.func.id)
        if fn is None:
            raise ExpressionError(
                f"function {node.func.id!r} is not defined"
                + (f"; write {_JS_EQUIVALENTS[node.func.id]}" if node.func.id in _JS_EQUIVALENTS
                   else _suggest(node.func.id, self.functions))
            )
        args = [self._eval(a, ctx) for a in node.args]
        kwargs = {kw.arg: self._eval(kw.value, ctx) for kw in node.keywords}
        try:
            return fn(*args, **kwargs)
        except ExpressionError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ExpressionError(f"{node.func.id}() failed: {exc}") from exc
