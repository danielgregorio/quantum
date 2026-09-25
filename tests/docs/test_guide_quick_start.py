"""docs/guide/quick-start.md: every step does what the page says.

Steps 1-3 return what their **Output:** shows (test_guide_examples_run.py);
here `quantum run counter.q` prints the line the page shows. Steps 4-6 build
the app the page describes — its files ("Create `<path>`:", "Replace `<path>`
with:"), the database made by the page's own command, its config — serve it,
and check what the page says the browser shows, the form included.
"""

import html
import re
import shlex
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
GUIDE = REPO / 'docs' / 'guide' / 'quick-start.md'
TEXT = GUIDE.read_text(encoding='utf-8')
F = '`' * 3

FILE = re.compile(r'(?:Create(?: a file called)?|Replace)\s+`(?P<path>[^`]+)`(?: with)?:\s*\n\s*\n'
                  + F + r'xml\n(?P<body>.*?)' + F, re.S)


def files(upto=None):
    """The page's files, the last version of each, in the text before `upto`."""
    out = {}
    for m in FILE.finditer(TEXT[:TEXT.index(upto)] if upto else TEXT):
        out[m['path']] = m['body']
    return out


def block_after(label, lang):
    return re.search(re.escape(label) + r'.*?' + F + lang + r'\n(?P<body>.*?)' + F, TEXT, re.S)['body'].strip()


def text_of(response):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', response.get_data(as_text=True))))


def write(folder, found):
    for path, body in found.items():
        target = folder / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding='utf-8')


def test_quantum_run_prints_what_the_page_shows(tmp_path):
    write(tmp_path, {'counter.q': files()['counter.q']})
    shown = block_after('quantum run counter.q', 'text')
    run = subprocess.run([sys.executable, '-m', 'quantum.cli.runner', 'run', 'counter.q'], cwd=tmp_path,
                         capture_output=True, text=True, timeout=120,
                         env={**__import__('os').environ, 'PYTHONPATH': str(REPO)})
    assert run.returncode == 0, run.stderr
    assert shown in run.stdout.splitlines(), run.stdout


@pytest.fixture
def app(tmp_path, monkeypatch):
    """The web app of steps 4 and 5: pages, the database the page's command makes, the config."""
    monkeypatch.chdir(tmp_path)
    write(tmp_path, {p: b for p, b in files('## Step 6').items() if p.startswith('components/')})
    command = shlex.split(block_after('Create a SQLite database', 'bash'))
    assert command[0] == 'python'
    subprocess.run([sys.executable] + command[1:], cwd=tmp_path, check=True, timeout=60)
    config = block_after('Declare it in `quantum.config.yaml`', 'yaml')
    (tmp_path / 'quantum.config.yaml').write_text(
        config + '\nlogging:\n  level: ERROR\n  console: false\n  file: false\n', encoding='utf-8')
    return tmp_path


def serve(folder):
    from quantum.runtime.web_server import QuantumWebServer
    server = QuantumWebServer(str(folder / 'quantum.config.yaml'))
    server.app.config['TESTING'] = True
    return server.app.test_client()


def test_step_4_the_home_page(app):
    page = text_of(serve(app).get('/'))
    assert 'Welcome to Quantum' in page
    assert 'Apple Banana Cherry' in page and '10 + 5 = 15' in page


def test_step_5_the_users_page(app):
    page = text_of(serve(app).get('/users'))
    assert '2 users' in page and 'Ana ana@example.com' in page and 'Bruno bruno@example.com' in page


def test_step_6_the_form_adds_a_user_and_refuses_a_short_name(app):
    write(app, {'components/users.q': files()['components/users.q']})
    client = serve(app)
    assert client.post('/users', data={'name': 'Carla', 'email': 'carla@example.com'}).status_code == 302
    page = text_of(client.get('/users'))
    assert 'Added Carla' in page and 'Carla carla@example.com' in page
    client.post('/users', data={'name': 'X', 'email': 'x@example.com'}, headers={'Referer': 'http://localhost/users'})
    connection = sqlite3.connect(app / 'data' / 'app.db')
    assert connection.execute("SELECT count(*) FROM users WHERE name = 'X'").fetchone()[0] == 0
    connection.close()
