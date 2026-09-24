"""The apps' own test suites, run by `quantum test` (TEST-1).

projects/tarefas, projects/blog, projects/quantum-chat and projects/bank-transfer are tested in their own language: *.test.q
files next to their pages and in their tests/ folder. This runs them the way a
person would — `python -m quantum.cli.runner test <app>`, in a subprocess, so
the exit code is the real one — and fails with the report when a test fails.
This is how CI runs `quantum test`: the suite is part of the pytest run.
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]


def quantum_test(*paths):
    return subprocess.run([sys.executable, '-m', 'quantum.cli.runner', 'test', *paths],
                          capture_output=True, text=True, encoding='utf-8', errors='replace',
                          cwd=str(REPO), timeout=300)


@pytest.mark.parametrize('app,at_least', [('tarefas', 13), ('blog', 16), ('quantum-chat', 4), ('bank-transfer', 6)])
def test_the_apps_suite_passes(app, at_least):
    # TEST-1: exit code 0, every test passed — and the suites did not shrink by accident
    result = quantum_test(f'projects/{app}')
    report = result.stdout + result.stderr
    assert result.returncode == 0, report
    passed = int(result.stdout.strip().splitlines()[-1].split(' passed')[0])
    assert passed >= at_least, report


def test_a_failing_suite_exits_with_1(tmp_path):
    # TEST-1: the exit code is what CI reads
    app = tmp_path / 'app'
    (app / 'components').mkdir(parents=True)
    (app / 'components' / 'index.q').write_text('<q:component name="i"><p>Hi</p></q:component>',
                                                encoding='utf-8')
    (app / 'quantum.config.yaml').write_text('server:\n  debug: false\n', encoding='utf-8')
    (app / 'home.test.q').write_text('<q:test name="greets">\n  <test:visit/>\n'
                                     '  <test:expect text="Bye"/>\n</q:test>\n', encoding='utf-8')
    result = quantum_test(str(app))
    assert result.returncode == 1
    assert 'FAIL  greets' in result.stdout and 'home.test.q:3' in result.stdout
