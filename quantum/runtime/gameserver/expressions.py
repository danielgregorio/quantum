"""A world's expressions: the Core's own (quantum/core/expressions.py), parsed once each, with the world's functions.

A world runs the same expression thousands of times a second, so its tree is parsed and checked the first time and
kept. The language is the Core's: the same operators, the same stdlib, the same refusal of anything that is not
data. What a world adds are its functions (walkable, ahead, near...: rules.py), and a random of its own: a world is
replayed from its log, so its chance is the world's seeded source, never the machine's.
"""

from __future__ import annotations

import ast
from typing import Any, Callable, Dict, List, Optional, Tuple

from quantum.core.expressions import ExpressionError, ExpressionEvaluator, _normalise_js_operators
from quantum.runtime.gameserver.errors import GameServerError


class WorldEvaluator(ExpressionEvaluator):
    """The Core's evaluator, with each expression's tree kept after its first parse."""

    def __init__(self, functions: Optional[Dict[str, Callable]] = None,
                 function_resolver: Optional[Callable[[str], Optional[Callable]]] = None):
        super().__init__(functions, max_length=4000, function_resolver=function_resolver)
        self._trees: Dict[str, ast.Expression] = {}

    def compile(self, expression: str) -> ast.Expression:
        tree = self._trees.get(expression)
        if tree is None:
            source = _normalise_js_operators(expression.strip())
            if not source:
                raise ExpressionError('empty expression')
            try:
                tree = ast.parse(source, mode='eval')
            except SyntaxError as exc:
                raise ExpressionError(f'invalid expression {source!r}: {exc.msg}') from exc
            self._validate(tree, source)
            self._trees[expression] = tree
        return tree

    def _evaluate(self, expression: str, context: Dict[str, Any]) -> Any:
        tree = self.compile(expression)
        try:
            return self._eval(tree.body, context)
        except RecursionError as exc:
            raise ExpressionError(f'evaluating {expression[:60]!r} ran out of stack') from exc


_CHECKER = WorldEvaluator()


def validate(expression: str, braced: bool = True) -> None:
    """The expression parses and holds only what an expression may: else a GameServerError. An attribute's text may
    have its braces (braced); what parts_of took out of them has none, and a { there is a record's."""
    try:
        _CHECKER.compile(unbraced(expression) if braced else expression)
    except ExpressionError as e:
        raise GameServerError(str(e))


def unbraced(raw: str) -> str:
    """An expression attribute's text, with or without its braces."""
    text = raw.strip()
    parts = parts_of(text)
    if len(parts) == 1 and parts[0][0] == '' and parts[0][1] is not None:
        return parts[0][1]
    return text


def parts_of(raw: str) -> List[Tuple[str, Optional[str]]]:
    """A text as its pieces: (a literal, None) and ('', an expression) for each {...} in it, braces matched."""
    out: List[Tuple[str, Optional[str]]] = []
    literal = []
    i, n = 0, len(raw)
    while i < n:
        c = raw[i]
        if c == '{':
            depth, j = 1, i + 1
            quote = None
            while j < n and depth:
                d = raw[j]
                if quote:
                    if d == quote:
                        quote = None
                elif d in '\'"':
                    quote = d
                elif d == '{':
                    depth += 1
                elif d == '}':
                    depth -= 1
                j += 1
            if depth:
                raise GameServerError(f'a {{ with no }} in {raw!r}')
            if literal:
                out.append((''.join(literal), None))
                literal = []
            out.append(('', raw[i + 1:j - 1]))
            i = j
        else:
            literal.append(c)
            i += 1
    if literal:
        out.append((''.join(literal), None))
    return out or [('', None)]


def text_of(value: Any) -> str:
    """A value as a text says it: 3 for 3.0, true and false, nothing for null."""
    if value is None:
        return ''
    if value is True:
        return 'true'
    if value is False:
        return 'false'
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def literal(raw: str) -> Any:
    """A value as written, with no braces: a number, true, false, null, or the text itself."""
    text = raw.strip()
    if text in ('true', 'false'):
        return text == 'true'
    if text == 'null':
        return None
    try:
        return int(text)
    except ValueError:
        pass
    try:
        number = float(text)
        if number == number and abs(number) != float('inf'):
            return number
    except ValueError:
        pass
    return raw
