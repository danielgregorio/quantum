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
import math
import operator
import re
from typing import Any, Callable, Dict, Optional

from quantum.core.expression_stdlib import STDLIB


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
    ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b,
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
    """Recusa `a ** b` grande demais — inteiro OU float.

    Exigia `isinstance` int nos DOIS lados, entao qualquer mistura passava
    direto: `2.0 ** 100000000` e `2 ** 1e9` chegavam ao operador e
    levantavam `OverflowError`, que nao e `ExpressionError` — subia pelo
    handler da requisicao como um 500 sem explicacao, em vez da mensagem que
    esta funcao existe para dar.
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

    def evaluate(self, expression: str, context: Dict[str, Any]) -> Any:
        """Evaluate an expression, raising ExpressionError on any failure."""
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
            # A guarda de profundidade cobre a EXPRESSAO; o contexto tambem
            # pode ser fundo (um dict que referencia a si mesmo, por
            # exemplo). Uma expressao de template nunca pode derrubar a
            # requisicao com um erro que nao seja ExpressionError.
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

    # Profundidade maxima da arvore. `_eval` desce recursivamente, e o
    # limite de recursao do Python e ~1000 quadros COMPARTILHADOS com tudo
    # que ja esta na pilha (Flask, o executor, o renderer). `{-------...1}`
    # com mil sinais levantava RecursionError — que nao e ExpressionError e
    # portanto virava 500 — e ainda deixava o interpretador raspando o
    # limite. Cem niveis e mais fundo do que qualquer expressao de template
    # real e fica bem longe da borda.
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
        """Mede a profundidade sem recursao — medir recursivamente teria o
        mesmo problema que a medicao existe para evitar."""
        pilha = [(root, 1)]
        while pilha:
            node, nivel = pilha.pop()
            if nivel > self.MAX_DEPTH:
                raise ExpressionError(
                    f"expression is nested more than {self.MAX_DEPTH} levels "
                    f"deep ({source[:60]!r}...); this would exhaust the stack"
                )
            for filho in ast.iter_child_nodes(node):
                pilha.append((filho, nivel + 1))

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
                # `1e300 ** 2` cabe na estimativa de bits e estoura assim
                # mesmo, porque float tem expoente maximo. Sem isto o erro
                # nao e ExpressionError e sobe como 500.
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
            valor = False
            for operando in node.values:
                valor = self._eval(operando, ctx)
                if isinstance(node.op, ast.And) and not valor:
                    return valor
                if isinstance(node.op, ast.Or) and valor:
                    return valor
            return valor

        if isinstance(node, ast.Compare):
            left = self._eval(node.left, ctx)
            for op_node, comparator in zip(node.ops, node.comparators):
                right = self._eval(comparator, ctx)
                op = _CMP_OPS.get(type(op_node))
                if op is None:
                    raise ExpressionError(f"unsupported comparison {type(op_node).__name__}")
                cl, cr = coerce_number(left), coerce_number(right)
                if _both_numeric(cl, cr):
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
            # `session.userId` e escrito como acesso a atributo, mas o
            # contexto guarda a variavel de escopo sob a CHAVE PLANA
            # pontilhada 'session.userId' — nao existe objeto `session`.
            # Sem isto, uma variavel de sessao PRESENTE levantava, e quem
            # chamava traduzia isso em '' ou em False: `<q:set
            # value="{session.userId}"/>` gravava vazio num INSERT, e
            # `<q:if condition="{session.userRole == 'admin'}">` era False
            # nos dois ramos. A documentacao ensina exatamente esses dois
            # padroes.
            plano = self._dotted_name(node)
            if plano is not None and plano in ctx:
                return ctx[plano]
            return self._attribute(self._eval(node.value, ctx), node.attr)

        if isinstance(node, ast.Subscript):
            target = self._eval(node.value, ctx)
            key = self._eval(node.slice, ctx) if not isinstance(node.slice, ast.Slice) \
                else slice(
                    self._eval(node.slice.lower, ctx) if node.slice.lower else None,
                    self._eval(node.slice.upper, ctx) if node.slice.upper else None,
                )
            try:
                if isinstance(target, dict):
                    return target.get(key)
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
        """'session.userId' de um Attribute, ou None se a base nao for um nome.

        So encadeamento puro de nomes vira chave plana: `a.b.c` sim,
        `f(x).b` ou `itens[0].nome` nao — nesses a busca por chave seria
        errada, e o acesso a atributo de verdade e que vale.
        """
        partes = []
        atual = node
        while isinstance(atual, ast.Attribute):
            partes.append(atual.attr)
            atual = atual.value
        if not isinstance(atual, ast.Name):
            return None
        partes.append(atual.id)
        return '.'.join(reversed(partes))

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
            valor = getattr(target, attr)
            # Um atributo NUNCA pode entregar um callable.
            #
            # `_call` so aceita funcao com nome (bloqueia `x.metodo()`) e ha
            # guarda de dunder sobre a AST — mas ambos eram contornados assim:
            #
            #     max([alvo], key='{0.__class__.__base__}'.format)
            #
            # `'...'.format` e um ACESSO A ATRIBUTO que devolve um metodo
            # ligado; passado como `key=` para uma funcao da stdlib, ela o
            # INVOCA, e str.format faz travessia de atributo em tempo de
            # execucao — onde a guarda de dunder, que olha o texto, nao
            # alcanca. Reproduzido: a expressao acima executou uma @property
            # do objeto do contexto.
            #
            # Um template le dado (`user.nome`), nao pega metodo para passar
            # adiante. Recusar callable fecha a classe inteira de gadget, nao
            # so o `format`.
            if callable(valor) and not isinstance(valor, type):
                raise ExpressionError(
                    f"attribute {attr!r} is a method, not data; expressions "
                    f"read values, they do not pass functions around"
                )
            return valor
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
            raise ExpressionError("only named function calls are allowed")
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
                f"{_suggest(node.func.id, self.functions)}"
            )
        args = [self._eval(a, ctx) for a in node.args]
        kwargs = {kw.arg: self._eval(kw.value, ctx) for kw in node.keywords}
        try:
            return fn(*args, **kwargs)
        except ExpressionError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ExpressionError(f"{node.func.id}() failed: {exc}") from exc
