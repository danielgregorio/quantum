"""docs/guide/services.md: the app it saves is served, and shows what it says.

The page introduces its files with "Save as `<path>`:" — the service module,
the config and two pages. This test writes exactly those files into a new
folder, serves it from there (as `quantum start` would), and checks the list,
the failure without a folder, and the page that handles the failure (SVC-1..3,
INV-2). The **Error:** block is run by test_guide_examples_run.py.
"""

import html
import re
import sys
from pathlib import Path

import pytest

from quantum import services

GUIDE = Path(__file__).resolve().parents[2] / 'docs' / 'guide' / 'services.md'
TEXT = GUIDE.read_text(encoding='utf-8')
F = '`' * 3


def saved_files():
    return {m['path']: m['body'] for m in re.finditer(
        r'Save as\s+`(?P<path>[^`]+)`:\s*\n\s*\n' + F + r'[a-z]*\n(?P<body>.*?)' + F, TEXT, re.S)}


def shown_after(label):
    """The ```text block right after the paragraph that ends with `label`."""
    m = re.search(re.escape(label) + r'\s*\n\s*\n' + F + r'text\n(?P<body>.*?)' + F, TEXT, re.S)
    return [line.strip() for line in m['body'].strip().splitlines()]


def text_of(response):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', response.get_data(as_text=True))))


@pytest.fixture
def app(tmp_path, monkeypatch):
    services._reset()
    for path, body in saved_files().items():
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding='utf-8')
    config = tmp_path / 'quantum.config.yaml'
    config.write_text(config.read_text(encoding='utf-8') +
                      'logging:\n  level: ERROR\n  console: false\n  file: false\n', encoding='utf-8')
    monkeypatch.chdir(tmp_path)                 # the module is found from the project folder
    path_before = list(sys.path)
    from quantum.runtime.web_server import QuantumWebServer
    server = QuantumWebServer(str(config))
    server.app.config['TESTING'] = True
    yield tmp_path, server.app.test_client()
    sys.path[:] = path_before
    for name in [m for m in sys.modules if m == 'myapp' or m.startswith('myapp.')]:
        sys.modules.pop(name)
    services._reset()


def add_reports(folder):
    (folder / 'reports').mkdir()
    (folder / 'reports' / 'annual.pdf').write_bytes(b'x' * 1200)
    (folder / 'reports' / 'q1.pdf').write_bytes(b'x' * 300)


def test_the_page_saves_the_app():
    assert set(saved_files()) == {'myapp/services.py', 'quantum.config.yaml',
                                  'components/reports.q', 'components/safe-reports.q'}


def test_the_page_lists_the_reports_as_shown(app):
    # SVC-1, SVC-2, SVC-3
    folder, client = app
    add_reports(folder)
    page = text_of(client.get('/reports'))
    for line in shown_after('`/reports` shows:'):
        assert line in page, (line, page)


def test_without_the_folder_the_page_stops_and_the_log_says_why(app, caplog):
    # SVC-3 / INV-2
    _, client = app
    with caplog.at_level('ERROR'):
        response = client.get('/reports')
    assert response.status_code == 500
    shown = re.search(r"server's log says\s+`([^`]+)`", TEXT).group(1)
    assert shown in caplog.text


def test_onerror_continue_lets_the_page_say_what_failed(app):
    # INV-2
    folder, client = app
    assert "Could not list reports: service 'reports.list' failed: no folder named reports" in \
        text_of(client.get('/safe-reports'))
    add_reports(folder)
    assert '2 reports' in text_of(client.get('/safe-reports'))
