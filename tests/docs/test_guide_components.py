"""docs/guide/components.md: its components do what the page says (COMP-1..COMP-4).

The section "Using one component inside another" introduces its files with
"Save as `<path>`:". This test writes exactly those files into a new app,
serves it, and checks what the guide says the page shows.

The blocks with an **Output:** or **Error:** are run by
test_guide_examples_run.py, without parameters; the components that take
parameters are run here with the ones the page's prose names.
"""

import re
from pathlib import Path

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.component import ComponentRuntime

GUIDE = Path(__file__).resolve().parents[2] / 'docs' / 'guide' / 'components.md'
TEXT = GUIDE.read_text(encoding='utf-8')
F = '`' * 3


def saved_files():
    return {m['path']: m['body'] for m in re.finditer(
        r'Save as `(?P<path>[^`]+)`:\s*\n\s*\n' + F + r'xml\n(?P<body>.*?)' + F, TEXT, re.S)}


def test_the_page_shows_the_card_with_its_title_and_content(tmp_path, monkeypatch):
    # COMP-1, COMP-2, COMP-3
    files = saved_files()
    assert set(files) == {'components/_parts/Card.q', 'components/index.q'}
    for path, body in files.items():
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text(body, encoding='utf-8')
    (tmp_path / 'quantum.config.yaml').write_text(
        'paths:\n  components: ./components\nlogging:\n  console: false\n  file: false\n', encoding='utf-8')
    monkeypatch.chdir(tmp_path)
    from quantum.runtime.web_server import QuantumWebServer
    client = QuantumWebServer('quantum.config.yaml').app.test_client()
    html = client.get('/').get_data(as_text=True)
    flat = re.sub(r'\s+', ' ', re.sub(r'>\s+|\s+<', lambda m: m.group().strip(), html))
    assert '<section class="card"><h2>Open tickets: 3</h2><p>The oldest is from Monday.</p></section>' in flat
    assert client.get('/_parts/Card').status_code == 404            # ROUTE-3: a part, not a page


def component(name):
    """The page's block that declares component `name`."""
    for block in re.findall(F + r'xml\n(.*?)' + F, TEXT, re.S):
        if f'<q:component name="{name}"' in block:
            return block
    raise LookupError(name)


def run(name, params):
    return ComponentRuntime().execute_component(
        QuantumParser(use_cache=False).parse(component(name)), params)


@pytest.mark.parametrize('name,params,expected', [
    ('Greeting', {'name': 'Ana'}, 'Hey Ana!'),
    ('Greeting', {'name': 'Ana', 'formal': 'true'}, 'Good day, Ana.'),
    ('AgeCheck', {'age': 20}, 'Adult'),
    ('AgeCheck', {'age': 15}, 'Minor'),
    ('Grade', {'score': 85}, 'B'),
    ('Grade', {'score': 42}, 'F'),
    ('UserEmail', {'email': 'ana@example.com'}, 'ana@example.com'),
    ('PriceFormatter', {'amount': '19.999'}, 'USD 20.0'),
    ('SafeComponent', {'count': 3}, '3 item(s)'),
    ('SafeComponent', {'count': -1}, 'Error: count must be at least 1'),
])
def test_the_component_returns_what_the_page_says(name, params, expected):
    assert run(name, params) == expected


@pytest.mark.parametrize('name,params,message', [
    ('Greeting', {}, "Required parameter 'name' is missing"),
    ('UserEmail', {'email': 'not-an-email'}, "Parameter 'email' must be a valid email"),
    ('SafeComponent', {'count': 'abc'}, "Parameter 'count' must be an integer, got 'abc'"),
])
def test_a_parameter_that_does_not_fit_is_the_error_the_page_quotes(name, params, message):
    assert message in TEXT
    with pytest.raises(Exception, match=re.escape(message)):
        run(name, params)


def test_the_types_section_quotes_a_real_error():
    message = "Parameter 'age' must be a number, got 'abc'"
    assert message in TEXT
    source = ('<q:component name="D" xmlns:q="https://quantum.lang/ns">'
              '<q:param name="age" type="number" required="true" /><q:return value="{age}" />'
              '</q:component>')
    with pytest.raises(Exception, match=re.escape(message)):
        ComponentRuntime().execute_component(QuantumParser(use_cache=False).parse(source), {'age': 'abc'})


@pytest.mark.parametrize('name,value,message', [
    ('status', 'gone', 'Value must be one of: active, inactive, pending'),
    ('email', 'not-an-email', 'Invalid email format'),
])
def test_the_validation_example_refuses_what_the_page_says(name, value, message):
    assert message in TEXT
    written = re.search(rf'<q:set name="{name}".*?/>', TEXT, re.S).group(0)
    changed = re.sub(r'value="[^"]*"', f'value="{value}"', written)
    source = f'<q:component name="D" xmlns:q="https://quantum.lang/ns">{changed}</q:component>'
    with pytest.raises(Exception, match=re.escape(message)):
        ComponentRuntime().execute_component(QuantumParser(use_cache=False).parse(source), {})
