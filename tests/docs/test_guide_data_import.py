"""docs/guide/data-import.md: each import gives what the page says it holds.

The page shows its sample files (data/customers.csv, data/products.json,
data/books.xml) and, for each q:data, the records it holds. This writes those
files, runs each example with a <q:return> of its variable, and compares with
the page. The page's blocks with an **Error:** are run by
test_guide_examples_run.py.
"""

import json
import re
from pathlib import Path

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.component import ComponentRuntime

PAGE = Path(__file__).resolve().parents[2] / 'docs' / 'guide' / 'data-import.md'
TEXT = PAGE.read_text(encoding='utf-8')
F = '`' * 3
NS = 'xmlns:q="https://quantum.lang/ns"'


def sample_files():
    """{path: content} from the code group, e.g. ```text [data/customers.csv]."""
    return {m['path']: m['body'] for m in re.finditer(
        F + r'\w+ \[(?P<path>data/[^\]]+)\]\n(?P<body>.*?)' + F, TEXT, re.S)}


def block_after(marker):
    start = TEXT.index(marker)
    return re.search(F + r'xml\n(.*?)' + F, TEXT[start:], re.S).group(1)


def records(shown):
    """The page's notation — [{id: 1, name: "Ana"}] — as Python values."""
    as_json = re.sub(r'([{,]\s*)(\w+):', r'\1"\2":', shown)
    return json.loads(as_json)


@pytest.fixture
def folder(tmp_path, monkeypatch):
    for path, content in sample_files().items():
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
    monkeypatch.chdir(tmp_path)
    return tmp_path


def run(body, variable):
    source = f'<q:component name="Doc" {NS}>{body}<q:return value="{{{variable}}}" /></q:component>'
    return ComponentRuntime().execute_component(QuantumParser(use_cache=False).parse(source), {})


def test_the_page_shows_three_sample_files():
    assert set(sample_files()) == {'data/customers.csv', 'data/products.json', 'data/books.xml'}


def test_csv_with_declared_columns(folder):
    body = block_after('Declare the columns to get typed values.')
    shown = re.search(F + r'text\n(\[\{id: 1.*?\])\n' + F, TEXT, re.S).group(1)
    assert run(body, 'customers') == records(shown)


def test_json_is_the_list_as_it_is(folder):
    body = block_after('A JSON array becomes the list as it is')
    assert run(body, 'products') == json.loads(sample_files()['data/products.json'])


def test_xml_with_xpath_and_fields(folder):
    body = block_after('`xpath` on `q:data` selects the records')
    shown = re.search(r'`books` holds `(\[.*?\])`', TEXT).group(1)
    assert run(body, 'books') == records(shown)


def test_transform_runs_in_order(folder):
    body = block_after('Operations inside `q:transform` run in order')
    shown = records(re.search(r'`expensive` holds `(\[.*?\])`', TEXT).group(1))
    got = run(body, 'expensive')
    # "(and the id of each)": the page leaves the id out of what it shows.
    assert [{k: v for k, v in r.items() if k != 'id'} for r in got] == shown
    assert all('id' in r for r in got)


def test_onerror_continue_lets_the_page_say_what_happened(folder):
    body = block_after('say so with\n`onerror="continue"`')
    page = f'<q:component name="Doc" {NS}>{body}</q:component>'
    from quantum.runtime.renderer import HTMLRenderer  # noqa: F401 — the page renders through the runtime
    runtime = ComponentRuntime()
    ast = QuantumParser(use_cache=False).parse(page)
    runtime.execute_component(ast, {})
    assert runtime.execution_context.get_variable('customers_result')['recordCount'] == 3

    (folder / 'data' / 'customers.csv').unlink()
    runtime = ComponentRuntime()
    runtime.execute_component(QuantumParser(use_cache=False).parse(page), {})
    result = runtime.execution_context.get_variable('customers_result')
    assert result['success'] is False and result['error']['message']
