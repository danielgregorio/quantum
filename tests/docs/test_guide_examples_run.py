"""
Every guide example that shows a result has to produce that result.

The outputs in docs/guide/loops.md were made up — none came out of the runtime
— and docs/guide/conditionals.md taught `a && b`, which parsed as an error and
made the condition false for any input. Reading the docs does not catch that;
running them does.

The recognised format, right after an ```xml block:

    **Output:** `["json", "on the same line"]`

    **Output:**
    ```
    ["or", "in a block"]
    ```

    **Error:** `part of the error message`

A result that is not JSON is compared with the text of the value.

A block without `<q:component>` runs as the body of a component.
`q:application` is experimental (SUPPORT_TIERS.md) and is left out.
"""

import contextlib
import io
import json
import pathlib
import re
import tempfile

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.component import ComponentRuntime

GUIDE = pathlib.Path(__file__).resolve().parents[2] / 'docs' / 'guide'
F = '`' * 3

EXAMPLE = re.compile(
    F + r'xml\n(?P<xml>(?:(?!' + F + r').)*)' + F + r'\s*\n'
    r'\*\*(?P<kind>Output|Error):\*\*[ \t]*'
    r'(?:`(?P<inline>[^`\n]+)`|\n' + F + r'[a-z]*\n(?P<block>.*?)' + F + r')',
    re.S)


def examples():
    for doc in sorted(GUIDE.glob('*.md')):
        text = doc.read_text(encoding='utf-8')
        for n, m in enumerate(EXAMPLE.finditer(text)):
            if '<q:application' in m['xml'] or '<q:route' in m['xml']:
                continue
            line = text[:m.start()].count('\n') + 1
            expected = (m['inline'] if m['inline'] is not None else m['block']).strip()
            yield pytest.param(m['xml'], m['kind'], expected, id=f'{doc.name}:{line}')


ALL = list(examples())


# The database docs/guide/query.md describes in "The example database". A
# block with datasource="db" runs against a fresh copy of it.
SCHEMA = """
create table users (id integer primary key, name text, email text, status text);
insert into users (name, email, status) values
  ('Ana', 'ana@example.com', 'active'),
  ('Bruno', 'bruno@example.com', 'active'),
  ('Carla', 'carla@example.com', 'inactive');
create table products (id integer primary key, name text, price real, stock integer);
insert into products (name, price, stock) values
  ('Notebook', 3500.0, 5), ('Mouse', 80.0, 40), ('Monitor', 1200.0, 0);
create table orders (id integer primary key, user_id integer, total real);
"""


def run_body(xml):
    if '<q:component' not in xml:
        xml = f'<q:component name="Doc" xmlns:q="https://quantum.lang/ns">{xml}</q:component>'
    folder = pathlib.Path(tempfile.mkdtemp())
    path = folder / 'doc.q'
    path.write_text(xml, encoding='utf-8')
    config = {}
    if 'datasource="db"' in xml:
        import sqlite3
        database = folder / 'app.db'
        connection = sqlite3.connect(database)
        connection.executescript(SCHEMA)
        connection.commit()
        connection.close()
        config = {'datasources': {'db': {'driver': 'sqlite', 'database': str(database)}}}
    with contextlib.redirect_stdout(io.StringIO()):
        return ComponentRuntime(config=config).execute_component(
            QuantumParser().parse_file(str(path)), {})


@pytest.mark.parametrize('xml,kind,expected', ALL)
def test_the_example_produces_what_the_docs_show(xml, kind, expected):
    if kind == 'Error':
        with pytest.raises(Exception) as error:
            run_body(xml)
        assert expected in str(error.value)
        return
    result = run_body(xml)
    try:
        assert result == json.loads(expected)
    except json.JSONDecodeError:
        # **Output:** `x = 10` — the text as it appears, without JSON quotes
        assert str(result) == expected


def test_the_extraction_finds_the_examples():
    # If the markdown format changes, the parametrize becomes zero cases and
    # passes in silence.
    per_page = {}
    for p in ALL:
        page = p.id.split(':')[0]
        per_page[page] = per_page.get(page, 0) + 1
    minimums = {'loops.md': 8, 'databinding.md': 8, 'conditionals.md': 6, 'functions.md': 6,
                'query.md': 9, 'state-management.md': 10, 'components.md': 4}
    missing = {p: (per_page.get(p, 0), n) for p, n in minimums.items() if per_page.get(p, 0) < n}
    assert not missing, f"pages with fewer run examples than expected: {missing}"
