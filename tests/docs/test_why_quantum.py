"""docs/guide/why-quantum.md: the example at the top does what the page says it does."""

import pathlib
import re
import sqlite3

from tests.conformance.conftest import serve_pages  # noqa: F401 — the fixture

PAGE = pathlib.Path(__file__).resolve().parents[2] / 'docs' / 'guide' / 'why-quantum.md'


def example() -> str:
    return re.search(r'```xml\n(.*?)```', PAGE.read_text(encoding='utf-8'), re.S).group(1)


def test_the_example_runs_as_the_page_says(serve_pages, tmp_path):
    # UI-9 + UI-10 + UI-3: the form draws its field from the action's q:param
    db = tmp_path / 'tasks.db'
    sqlite3.connect(db).execute('CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT NOT NULL)')
    client = serve_pages(datasources_yaml=f'datasources:\n  db:\n    driver: sqlite\n    database: {db.as_posix()}\n',
                      tasks=example())
    html = client.get('/tasks').get_data(as_text=True)
    field = re.search(r'<input[^>]*name="title"[^>]*>', html).group(0)
    assert 'required' in field and 'minlength="3"' in field
    assert '>Add<' in html

    assert client.post('/tasks', data={'action': 'add', 'title': 'Write the docs'}).status_code == 302
    page = client.get('/tasks').get_data(as_text=True)
    assert 'Added: Write the docs' in page
    assert re.search(r'<th>\s*Title\s*</th>', page)                  # UI-5: columns from the query
    assert re.search(r'<td>\s*Write the docs\s*</td>', page)
    client.post('/tasks', data={'action': 'add', 'title': 'x'}, headers={'Referer': 'http://localhost/tasks'})
    assert 'at least 3 characters' in client.get('/tasks').get_data(as_text=True)

    view = client.get('/tasks', headers={'Accept': 'application/vnd.quantum.view+json'}).get_json()
    assert view['title'] == 'Tasks'                                # the same page, for the console
    table = next(n for n in view['view'][0]['children'] if n['type'] == 'table')
    assert [c['label'] for c in table['columns']] == ['Id', 'Title']
