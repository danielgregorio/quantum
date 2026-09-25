"""docs/tutorial/tasks-app.md: every step builds an app that works as the page says.

The tutorial is a sequence of "## N." steps. Each step shows whole files after
"Save as `<path>`:"; a later block for the same path replaces the earlier one.
This test rebuilds the app as it stands at the end of each step, adds a small
suite that checks what that step claims, and runs it with `quantum test`
(TEST-1). The last step's own suites run as the page shows, with the report it
prints. The finished app is compared with projects/tarefas, which the page says
it ends up as: the same tags, file by file.
"""

import collections
import re
from pathlib import Path

import pytest

from quantum.runtime.app_testing import run_tests

REPO = Path(__file__).resolve().parents[2]
PAGE = REPO / 'docs' / 'tutorial' / 'tasks-app.md'
TEXT = PAGE.read_text(encoding='utf-8')
F = '`' * 3

SAVE = re.compile(r'Save as `(?P<path>[^`]+)`:\s*\n\s*\n' + F + r'[a-z]*\n(?P<body>.*?)' + F, re.S)
STEP = re.compile(r'^## (?P<n>\d+)\. ', re.M)


def files_at(step):
    """The app's files at the end of `step`: the last block shown for each path."""
    starts = [(int(m['n']), m.start()) for m in STEP.finditer(TEXT)]
    end = next((pos for n, pos in starts if n == step + 1), len(TEXT))
    files = {}
    for m in SAVE.finditer(TEXT[:end]):
        files[m['path']] = m['body']
    return files


def build(tmp_path, monkeypatch, files, extra_tests=None):
    app = tmp_path / 'tasks'
    for path, body in files.items():
        target = app / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding='utf-8')
    if extra_tests:
        (app / 'checks').mkdir(exist_ok=True)
        (app / 'checks' / 'step.test.q').write_text(extra_tests, encoding='utf-8')
    monkeypatch.chdir(app)          # the page runs its commands in the app's folder
    return app


def run(path='.'):
    lines = []
    code = run_tests([path], out=lines.append)
    return code, normalize('\n'.join(lines))


def normalize(report):
    return re.sub(r'\(\d+ ms\)', '(N ms)', report.replace('\\', '/')).strip()


# What each step says the app does, checked on the app as that step leaves it.
CHECKS = {
    1: """
<q:test name="the first page lists the tasks and counts them" page="/">
  <test:visit />
  <test:expect text="Total: 3" />
  <test:expect text="Open: 2" />
  <test:expect text="Done: 1" />
  <test:expect text="Read the Quantum guide" />
  <test:expect text="Install Quantum" />
</q:test>
""",
    2: """
<q:test name="a task is created, with a flash" page="/">
  <test:submit action="create" title="Water the plants" priority="low" />
  <test:expect redirect="/" flash="Created: Water the plants" />
  <test:expect table="tasks" count="1" where="title = 'Water the plants' AND priority = 'low'" />
  <test:expect text="Total: 4" />
</q:test>
<q:test name="an empty title and a one-letter title are refused on the field" page="/">
  <test:submit action="create" title="" />
  <test:expect error="title" />
  <test:submit action="create" title="x" />
  <test:expect error="title" />
  <test:expect text="at least 3 characters" />
  <test:expect table="tasks" count="3" />
</q:test>
""",
    3: """
<q:test name="finish and reopen a task" page="/">
  <test:submit action="toggle" id="1" />
  <test:expect redirect="/" />
  <test:expect table="tasks" count="1" where="id = 1 AND done = 1" />
  <test:submit action="toggle" id="1" />
  <test:expect table="tasks" count="1" where="id = 1 AND done = 0" />
</q:test>
<q:test name="delete a task" page="/">
  <test:submit action="delete" id="2" />
  <test:expect redirect="/" flash="Task deleted." />
  <test:expect table="tasks" count="0" where="id = 2" />
</q:test>
<q:test name="an id that is not a number is refused" page="/">
  <test:submit action="delete" id="abc" />
  <test:expect table="tasks" count="3" />
</q:test>
""",
    4: """
<q:test name="?show=done lists only the finished task" page="/">
  <test:visit show="done" />
  <test:expect text="Install Quantum" />
  <test:expect no-text="Read the Quantum guide" />
</q:test>
<q:test name="finishing keeps the filter" page="/">
  <test:submit action="toggle" id="1" show="open" />
  <test:expect redirect="/?show=open" />
  <test:expect no-text="Read the Quantum guide" />
</q:test>
<q:test name="an empty list says so" page="/">
  <test:submit action="delete" id="3" />
  <test:visit show="done" />
  <test:expect text="No tasks here." />
</q:test>
""",
    5: """
<q:test name="the sheet lists the tasks and is linked from the list" page="/">
  <test:visit />
  <test:expect text="Sheet" />
  <test:visit path="/sheet" />
  <!-- the cells are inputs, so the titles are values, not text: the columns are -->
  <test:expect text="Title" />
  <test:expect text="Priority" />
</q:test>
<q:test name="a cell edit is saved" page="/sheet">
  <test:submit action="__edit" __table="tasks" __key="1" __column="priority" value="low" />
  <test:expect redirect="/sheet" flash="Saved: priority" />
  <test:expect table="tasks" count="1" where="id = 1 AND priority = 'low'" />
</q:test>
<q:test name="a priority outside the CHECK list is refused" page="/sheet">
  <test:submit action="__edit" __table="tasks" __key="1" __column="priority" value="urgent" />
  <test:expect table="tasks" count="1" where="id = 1 AND priority = 'high'" />
</q:test>
""",
    6: """
<q:test name="the edit page saves, and the change shows in its history" page="/task/1">
  <test:as user="ana" />
  <test:submit action="save" title="Read the guide twice" priority="medium" />
  <test:expect redirect="/" flash="Saved: Read the guide twice" />
  <test:expect history="tasks" action="save" op="update" user="ana" where="id = 1" count="1" />
  <test:visit path="/task/1" />
  <test:expect text="title: Read the Quantum guide → Read the guide twice" />
</q:test>
<q:test name="the rules come from the schema" page="/task/1">
  <test:submit action="save" title="" priority="urgent" />
  <test:expect error="title" />
  <test:expect error="priority" />
</q:test>
<q:test name="each row links to its edit page" page="/">
  <test:visit />
  <test:expect text="Edit" />
</q:test>
""",
}


def test_the_page_has_the_steps_it_announces():
    steps = [int(m['n']) for m in STEP.finditer(TEXT)]
    assert steps == list(range(1, 9))
    assert set(files_at(7)) == {
        'quantum.config.yaml', 'migrations/V001_tasks.sql', 'components/index.q',
        'components/sheet.q', 'components/task/[id].q', 'tests/tasks.test.q',
        'components/sheet.test.q'}


@pytest.mark.parametrize('step', sorted(CHECKS))
def test_each_step_works_as_the_page_says(step, tmp_path, monkeypatch):
    # TEST-1: the app as the step leaves it, and what the step says it does
    files = {p: b for p, b in files_at(step).items() if not p.endswith('.test.q')}
    build(tmp_path, monkeypatch, files, CHECKS[step])
    code, report = run('checks')
    assert code == 0, report


def test_the_finished_app_passes_its_tests_as_the_page_shows(tmp_path, monkeypatch):
    # TEST-1
    build(tmp_path, monkeypatch, files_at(7))
    code, report = run()
    assert code == 0, report
    shown = re.search(r'<!-- report: pass -->\s*\n' + F + r'text\n(?P<body>.*?)' + F, TEXT, re.S)['body']
    assert report == normalize(shown)


def tags(text):
    text = re.sub(r'<!--.*?-->', '', text, flags=re.S)
    return collections.Counter(re.findall(r'<([a-zA-Z]+:[a-zA-Z-]+)\b', text))


@pytest.mark.parametrize('mine,tarefas', [
    ('components/index.q', 'components/index.q'),
    ('components/sheet.q', 'components/planilha.q'),
    ('components/task/[id].q', 'components/tarefa/[id].q'),
    ('tests/tasks.test.q', 'tests/tarefas.test.q'),
    ('components/sheet.test.q', 'components/planilha.test.q'),
])
def test_the_finished_app_is_projects_tarefas_in_english(mine, tarefas):
    theirs = (REPO / 'projects' / 'tarefas' / tarefas).read_text(encoding='utf-8')
    assert tags(files_at(7)[mine]) == tags(theirs)


def test_the_line_counts_the_page_gives_are_the_files():
    files = files_at(7)
    q = sum(len(body.splitlines()) for path, body in files.items()
            if path.endswith('.q') and not path.endswith('.test.q'))
    sql = len(files['migrations/V001_tasks.sql'].splitlines())
    assert f'{q} lines of `.q`, {sql} of SQL, 0 of JavaScript' in TEXT
