"""docs/guide/query.md, "Change history": the page it saves records a rename and shows it (DB-11).

The section saves `components/post.q`; this test serves it over a datasource
with `history: true`, signs `ana` in, renames the post as the page says, and
checks the history table the page shows: its columns, and the row's who,
action and change (the time is the time of the run).
"""

import html
import re
import sqlite3
from pathlib import Path

from tests.conformance.conftest import serve_pages  # noqa: F401 — the fixture

GUIDE = Path(__file__).resolve().parents[2] / 'docs' / 'guide' / 'query.md'
TEXT = GUIDE.read_text(encoding='utf-8')
F = '`' * 3


def saved_page():
    m = re.search(r'Save as\s+`components/post\.q`:\s*\n\s*\n' + F + r'xml\n(?P<body>.*?)' + F, TEXT, re.S)
    return m['body']


def shown_table():
    """(headers, first row) of the markdown table under "the page shows:"."""
    m = re.search(r'the page\s+shows:\s*\n\s*\n(?P<table>(?:\|.*\|\n)+)', TEXT)
    rows = [[c.strip() for c in line.strip('|').split('|')] for line in m['table'].strip().splitlines()]
    return rows[0], rows[2]


def cells(page):
    return [html.unescape(re.sub(r'<[^>]+>', '', c)).strip()
            for c in re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', page, re.S)]


def test_the_rename_is_recorded_and_shown_as_the_page_says(serve_pages, tmp_path):
    db = tmp_path / 'app.db'
    connection = sqlite3.connect(db)
    connection.executescript("CREATE TABLE posts (id INTEGER PRIMARY KEY, title TEXT NOT NULL);"
                             "INSERT INTO posts (title) VALUES ('First');")
    connection.commit()
    connection.close()
    signin = ('<q:component name="signin" xmlns:q="https://quantum.lang/ns">'
              '<q:set name="session.userName" value="ana" /><p>ok</p></q:component>')
    client = serve_pages(
        datasources_yaml=f'datasources:\n  db:\n    driver: sqlite\n    database: {db.as_posix()}\n    history: true\n',
        post=saved_page(), signin=signin)
    client.get('/signin')
    headers, row = shown_table()
    before, after = re.match(r'title: (.*) → (.*)', row[3]).groups()
    assert client.post('/post', data={'action': 'rename', 'title': after}).status_code == 302
    page = client.get('/post').get_data(as_text=True)
    found = cells(page)
    assert found[:4] == headers, found
    assert found[5:8] == [row[1], row[2], f'title: {before} → {after}'], found
