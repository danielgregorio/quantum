"""docs/guide/sessions.md: the pages it saves are served, and show what it says.

The page introduces its files with "Save as `components/<name>.q`:". This test
serves exactly those files and checks the visits table (two visitors, the
session per visitor, the application scope shared) and the welcome page before
and after the session says the visitor is logged in. The page's blocks with an
**Output:** / **Error:** are run by test_guide_examples_run.py.
"""

import re
from pathlib import Path

from tests.conformance.conftest import serve_pages  # noqa: F401 — the fixture

GUIDE = Path(__file__).resolve().parents[2] / 'docs' / 'guide' / 'sessions.md'
TEXT = GUIDE.read_text(encoding='utf-8')
F = '`' * 3


def saved_files():
    return {m['path']: m['body'] for m in re.finditer(
        r'Save as\s+`(?P<path>[^`]+)`:\s*\n\s*\n' + F + r'xml\n(?P<body>.*?)' + F, TEXT, re.S)}


def visits_table():
    """[(visitor, mine, everyone)] from the table under "Counting visits"."""
    rows = re.findall(r'^\| visitor (\w), \w+ \| (\d+) \| (\d+) \|$', TEXT, re.M)
    return [(v, int(a), int(b)) for v, a, b in rows]


def text_of(response):
    """The page as the browser shows it: no tags, entities decoded."""
    import html
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', response.get_data(as_text=True))))


def serve(serve_pages, **extra):
    files = saved_files()
    pages = {Path(path).stem: body for path, body in files.items()}
    return serve_pages(**pages, **extra)


def test_the_page_saves_the_two_components():
    assert set(saved_files()) == {'components/visits.q', 'components/welcome.q'}
    assert len(visits_table()) == 3


def test_two_visitors_see_the_counts_the_table_shows(serve_pages):
    # SET-3 (increment from nothing), session per visitor, application shared
    client_a = serve(serve_pages)
    app = client_a.application
    visitors = {'A': client_a, 'B': app.test_client()}
    for visitor, mine, everyone in visits_table():
        page = text_of(visitors[visitor].get('/visits'))
        assert f'Your visits: {mine}' in page, (visitor, page)
        assert f"Everyone's visits: {everyone}" in page, (visitor, page)
        assert 'GET /visits' in page


def test_the_welcome_page_before_and_after_login(serve_pages):
    # EXPR-3: a session value that does not exist is false in a condition
    helper = ('<q:component name="login" xmlns:q="https://quantum.lang/ns">'
              '<q:set name="session.authenticated" value="{true}" /><p>ok</p></q:component>')
    client = serve(serve_pages, login=helper)
    first = text_of(client.get('/welcome'))
    assert 'Sign in' in first and 'Welcome back!' not in first
    client.get('/login')
    assert 'Welcome back!' in text_of(client.get('/welcome'))
