"""
Every rule of SPEC.md has a test, and every test that cites a rule cites one that exists.

The specification only holds if each rule is locked by running code. A rule
without a test is a promise nobody checks — that is exactly how Quantum's
documentation spent months teaching output the code never produced.

A test declares the rule it covers by citing the ID in a comment or docstring
(`# RET-1`). IDs are looked for in every file under tests/.
"""

import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]
ID = re.compile(r'\b(PARSE|RET|LOOP|IF|FN|ACT|ROUTE|COMP|DB|SET|AUTH|DATA|IA|EXPR|INV|RUN|SCOPE|ERR|CFG|APP|SVC|UI|EXEC|DEV|FILE|MAIL|TEST)-(\d+)\b')


def spec_ids():
    text = (REPO / 'SPEC.md').read_text(encoding='utf-8')
    return {f'{a}-{n}' for a, n in re.findall(r'\*\*([A-Z]+)-(\d+)\*\*', text)}


def ids_cited_in_tests():
    cited = {}
    for path in (REPO / 'tests').rglob('*.py'):
        if path.name == 'test_spec_ids.py':
            continue
        for a, n in ID.findall(path.read_text(encoding='utf-8', errors='ignore')):
            cited.setdefault(f'{a}-{n}', set()).add(path.relative_to(REPO).as_posix())
    return cited


def test_the_spec_has_rules():
    assert len(spec_ids()) >= 10


def test_every_rule_has_a_test():
    untested = sorted(spec_ids() - set(ids_cited_in_tests()))
    assert untested == [], f'SPEC.md rules with no test citing them: {untested}'


def test_every_cited_id_exists_in_the_spec():
    ghosts = {i: sorted(paths) for i, paths in ids_cited_in_tests().items()
              if i not in spec_ids()}
    assert ghosts == {}, f'tests cite rules that do not exist in SPEC.md: {ghosts}'
