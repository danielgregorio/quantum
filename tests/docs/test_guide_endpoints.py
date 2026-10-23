"""docs/guide/endpoints.md: the API it saves is served, and answers what its table says.

The page saves `components/api/notes.q` and shows, in a table, each request and its answer. This test serves
that file with a SQLite datasource `db` holding the page's table, sends each request in order and compares
the status and the JSON with the table's.
"""

import json
import re
import sqlite3
from pathlib import Path

GUIDE = Path(__file__).resolve().parents[2] / 'docs' / 'guide' / 'endpoints.md'
TEXT = GUIDE.read_text(encoding='utf-8')
F = '`' * 3


def saved_files():
    return {m['path']: m['body'] for m in re.finditer(
        r'save as\s+`(?P<path>[^`]+)`:\s*\n\s*\n' + F + r'xml\n(?P<body>.*?)' + F, TEXT, re.S | re.I)}


def exchanges():
    """[(method, path, body or None, status, answer)] from the table under "Notes, listed and added"."""
    rows = re.findall(r'^\| `(GET|POST|PUT|DELETE|PATCH) ([^`]+)`(?: `(\{.*?\})`)? \| `(\d{3})` `(.*)` \|$',
                      TEXT, re.M)
    return [(m, p, json.loads(b) if b else None, int(s), json.loads(a)) for m, p, b, s, a in rows]


def test_the_page_saves_one_api_and_shows_five_exchanges():
    assert list(saved_files()) == ['components/api/notes.q']
    assert len(exchanges()) == 5


def test_each_request_answers_what_the_table_says(tmp_path):
    from quantum.runtime.web_server import QuantumWebServer
    for path, body in saved_files().items():
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding='utf-8')
    database = tmp_path / 'notes.db'
    with sqlite3.connect(database) as db:
        db.execute('CREATE TABLE notes (id INTEGER PRIMARY KEY, text TEXT, stars INTEGER)')
    config = tmp_path / 'quantum.config.yaml'
    config.write_text(
        f'server:\n  debug: false\npaths:\n  components: {(tmp_path / "components").as_posix()}\n'
        f'logging:\n  level: ERROR\n  console: false\n  file: false\n'
        f'datasources:\n  db:\n    driver: sqlite\n    database: {database.as_posix()}\n', encoding='utf-8')
    server = QuantumWebServer(str(config))
    server.app.config['TESTING'] = True
    client = server.app.test_client()
    for method, path, body, status, answer in exchanges():
        response = client.open(path, method=method, json=body)
        assert (response.status_code, response.get_json()) == (status, answer), (method, path, body)
