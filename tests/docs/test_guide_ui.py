"""Every screen in the guide (docs/guide/*.md with **Shows:**) opens, and shows what the guide says — on the web and in the console.

The format, right after an ```xml block with a <q:component>:

    **Shows:** `text` · `other text`

The example is served as a real page; each text has to appear in the HTML (as
the browser shows it) and in the screen tree the console draws (UI-3).
"""

import html
import pathlib
import re

import pytest

from tests.conformance.conftest import serve_pages  # noqa: F401 — a fixture

GUIDE = pathlib.Path(__file__).resolve().parents[2] / 'docs' / 'guide'
F = '`' * 3
EXAMPLE = re.compile(F + r'xml\n(?P<xml>(?:(?!' + F + r').)*)' + F + r'\s*\n\*\*Shows:\*\*(?P<texts>[^\n]+)', re.S)


def examples():
    # Every guide page with **Shows:** (ui.md, how-a-page-runs.md...).
    for doc in sorted(GUIDE.glob('*.md')):
        text = doc.read_text(encoding='utf-8')
        for m in EXAMPLE.finditer(text):
            line = text[:m.start()].count('\n') + 1
            yield pytest.param(m['xml'], re.findall(r'`([^`]+)`', m['texts']), id=f'{doc.name}:{line}')


ALL = list(examples())


def test_the_guide_has_checked_examples():
    assert len(ALL) >= 5


def visible(page: str) -> str:
    body = page.split('<body', 1)[-1]
    body = re.sub(r'<(script|style)\b.*?</\1>', ' ', body, flags=re.S)
    return html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', body)))


def tree_texts(nodes) -> str:
    parts = []
    for node in nodes:
        props = node.get('props', {})
        parts += [str(props[c]) for c in ('text', 'title', 'label') if props.get(c)]
        parts += [c['label'] for c in node.get('columns', [])]
        for row in node.get('rows', []):
            for cell in row:
                parts.append(tree_texts(cell))
        if node.get('type') in ('radio', 'select') and props.get('options'):
            parts.append(str(props['options']).replace(',', ' '))
        parts.append(tree_texts(node.get('children', [])))
    return ' '.join(parts)


def guide_database(folder) -> str:
    """The database ui.md's examples use: its ```sql block after "use this database", built in `folder`."""
    import sqlite3
    text = (GUIDE / 'ui.md').read_text(encoding='utf-8')
    sql = re.search(r'use this\s+database.*?' + F + r'sql\n(?P<sql>.*?)' + F, text, re.S)['sql']
    path = folder / 'guide.db'
    connection = sqlite3.connect(path)
    connection.executescript(sql)
    connection.commit()
    connection.close()
    return f'datasources:\n  db:\n    driver: sqlite\n    database: {path.as_posix()}\n'


@pytest.mark.parametrize('source,texts', ALL)
def test_the_screen_shows_what_the_guide_says(serve_pages, tmp_path, source, texts):
    # UI-1, UI-3, UI-5, UI-6, UI-7
    datasources = guide_database(tmp_path) if 'datasource="db"' in source else ''
    c = serve_pages(datasources_yaml=datasources, screen=source)
    response = c.get('/screen')
    assert response.status_code == 200, visible(response.get_data(as_text=True))[:500]
    web = visible(response.get_data(as_text=True))
    tree = c.get('/screen', headers={'Accept': 'application/vnd.quantum.view+json'}).get_json()
    console = tree_texts(tree['view'])
    for t in texts:
        assert t in web, f'the browser does not show {t!r}'
        assert t in console, f'the console does not show {t!r}'
    assert not re.search(r'\{[a-z_.]+\}', web), 'a raw expression on the page'
