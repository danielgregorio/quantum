"""docs/guide/testing.md: the app and the tests it teaches run, and print what it shows.

The guide builds a notes app from blocks introduced by "Save as `<path>`:".
This test writes those blocks into a new folder, runs `quantum test` there,
and compares the report with the block after `<!-- report: pass -->` — then
makes the change the guide describes and compares with `<!-- report: fail -->`.
Timings differ from run to run and are compared as `(N ms)` (TEST-1, TEST-4).
"""

import re
from pathlib import Path

from quantum.runtime.app_testing import run_tests

GUIDE = Path(__file__).resolve().parents[2] / 'docs' / 'guide' / 'testing.md'
F = '`' * 3
TEXT = GUIDE.read_text(encoding='utf-8')


def saved_files():
    return {m['path']: m['body'] for m in re.finditer(
        r'Save as `(?P<path>[^`]+)`:\s*\n\s*\n' + F + r'[a-z]*\n(?P<body>.*?)' + F, TEXT, re.S)}


def shown_report(kind):
    m = re.search(r'<!-- report: ' + kind + r' -->\s*\n' + F + r'text\n(?P<body>.*?)' + F, TEXT, re.S)
    return normalize(m['body'])


def normalize(report):
    return re.sub(r'\(\d+ ms\)', '(N ms)', report.replace('\\', '/')).strip()


def build(tmp_path, monkeypatch):
    app = tmp_path / 'notes'
    for path, body in saved_files().items():
        target = app / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding='utf-8')
    monkeypatch.chdir(app)                     # the guide runs `quantum test` in the app's folder
    return app


def run():
    lines = []
    code = run_tests(['.'], out=lines.append)
    return code, normalize('\n'.join(lines))


def test_the_guide_saves_the_app_and_its_tests():
    assert set(saved_files()) == {'quantum.config.yaml', 'migrations/V001_notes.sql',
                                  'components/index.q', 'tests/notes.test.q'}


def test_the_tests_pass_as_the_guide_shows(tmp_path, monkeypatch):
    # TEST-1
    build(tmp_path, monkeypatch)
    code, report = run()
    assert code == 0, report
    assert report == shown_report('pass')


def test_the_failure_is_reported_as_the_guide_shows(tmp_path, monkeypatch):
    # TEST-1, TEST-4: "Change the flash in `add a note` to `flash="Added: Buy milk"`"
    app = build(tmp_path, monkeypatch)
    suite = app / 'tests' / 'notes.test.q'
    suite.write_text(suite.read_text(encoding='utf-8').replace(
        'flash="Added: Buy bread"', 'flash="Added: Buy milk"'), encoding='utf-8')
    code, report = run()
    assert code == 1
    assert report == shown_report('fail')


def test_the_parse_error_is_the_one_the_guide_shows(tmp_path, monkeypatch):
    # TEST-4: the block under "Nothing outside the vocabulary"
    app = build(tmp_path, monkeypatch)
    suite = app / 'tests' / 'notes.test.q'
    lines = suite.read_text(encoding='utf-8').splitlines()
    assert 'Read the guide (idea)' in lines[3]
    lines[3] = '  <test:click text="Add" />'
    suite.write_text('\n'.join(lines), encoding='utf-8')
    code, report = run()
    shown = re.search(r'Nothing outside the vocabulary.*?' + F + r'text\n(?P<body>.*?)' + F, TEXT, re.S)['body']
    assert code == 1
    assert shown.strip() in report
