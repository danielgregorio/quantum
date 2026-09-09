"""Extract the real expression corpus from examples/ and record how the
CURRENT evaluator handles each one. This is the compatibility baseline the
new evaluator has to match (or deliberately, visibly improve on).

    python scripts/build-expression-corpus.py

Writes tests/fixtures/expression_corpus.json, which tests/unit/
test_expression_corpus.py asserts against. Regenerate it ONLY when you mean to
move the baseline — a regenerated corpus records whatever the evaluator does
today, including bugs, so running this to make a failing test pass would
silently bless a regression. Read the diff before committing it.
"""
import json
import pathlib
import re
import sys

from quantum.runtime.component import ComponentRuntime

EXPR = re.compile(r'\{([^{}\n]+)\}')

# Contexts where {...} is CSS or JavaScript, never a Quantum expression.
SKIP_INSIDE = re.compile(r'<(style|script)\b.*?</\1>', re.DOTALL | re.IGNORECASE)


def harvest():
    seen = {}
    for f in sorted(pathlib.Path('examples').rglob('*.q')):
        try:
            txt = f.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        # Strip style/script blocks first — their braces are not expressions
        txt = SKIP_INSIDE.sub('', txt)
        for raw in EXPR.findall(txt):
            e = raw.strip()
            if not e or len(e) > 80:
                continue
            # Obvious CSS/JS leftovers
            if ';' in e or ':' in e and not e.startswith(('session.', 'application.', 'request.')):
                continue
            seen.setdefault(e, str(f))
    return seen


CONTEXT = {
    'a': 17, 'b': 25, 'x': 10, 'count': 3, 'total': 100, 'price': 9.5,
    'name': 'Alice', 'title': 'Docs', 'hp': 100, 'i': 1, 'n': 2,
    'items': [1, 2, 3], 'users': [{'name': 'Ann'}, {'name': 'Bo'}],
    'user': {'name': 'Ann', 'age': 30, 'email': 'a@b.c'},
    'result': {'success': True, 'count': 2, 'data': [1, 2]},
    'flag': True, 'empty': '', 'zero': 0,
}


def main():
    runtime = ComponentRuntime()
    corpus = []
    for expr, origin in sorted(harvest().items()):
        entry = {'expr': expr, 'origin': origin}
        try:
            value = runtime._apply_databinding('{' + expr + '}', dict(CONTEXT))
            entry['result'] = repr(value)
            entry['status'] = 'ok'
        except Exception as exc:
            entry['result'] = f"{type(exc).__name__}: {exc}"
            entry['status'] = 'error'
        corpus.append(entry)

    out = pathlib.Path('tests/fixtures/expression_corpus.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(corpus, indent=2, ensure_ascii=False), encoding='utf-8')

    ok = sum(1 for c in corpus if c['status'] == 'ok')
    unresolved = sum(1 for c in corpus if c['status'] == 'ok' and c['result'].strip("'\"").startswith('{'))
    print(f"{len(corpus)} expressões únicas")
    print(f"  {ok} avaliaram sem exceção")
    print(f"  {len(corpus)-ok} lançaram exceção")
    print(f"  {unresolved} devolveram o placeholder literal (não resolveram)")


if __name__ == '__main__':
    main()
