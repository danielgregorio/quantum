"""docs/guide/project-structure.md: the page it saves is served at the URL it says (ROUTE-1).

The page saves `components/shop/[id].q`; this test serves it over the guide's
example database (the one docs/guide/query.md shows, as
test_guide_examples_run.py builds it) and checks what `/shop/2` shows and
that a URL with no file answers 404.
"""

import re
import sqlite3
from pathlib import Path

from tests.conformance.conftest import serve_pages  # noqa: F401 — the fixture
from tests.docs.test_guide_examples_run import SCHEMA

GUIDE = Path(__file__).resolve().parents[2] / 'docs' / 'guide' / 'project-structure.md'
TEXT = GUIDE.read_text(encoding='utf-8')
F = '`' * 3


def saved_files():
    return {m['path']: m['body'] for m in re.finditer(
        r'Save as\s+`(?P<path>[^`]+)`:\s*\n\s*\n' + F + r'xml\n(?P<body>.*?)' + F, TEXT, re.S)}


def test_the_product_page_is_served_at_its_path(serve_pages, tmp_path):
    files = saved_files()
    assert list(files) == ['components/shop/[id].q']
    db = tmp_path / 'app.db'
    connection = sqlite3.connect(db)
    connection.executescript(SCHEMA)
    connection.commit()
    connection.close()
    target = tmp_path / 'components' / 'shop' / '[id].q'
    target.parent.mkdir(parents=True)
    target.write_text(files['components/shop/[id].q'], encoding='utf-8')
    client = serve_pages(datasources_yaml=f'datasources:\n  db:\n    driver: sqlite\n    database: {db.as_posix()}\n')
    url, name = re.search(r'`(/shop/\d+)` shows\s+\*\*(\w+)\*\*', TEXT).groups()
    assert re.search(r'<h1>\s*' + name + r'\s*</h1>', client.get(url).get_data(as_text=True))
    assert client.get('/shop/2/reviews').status_code == 404
