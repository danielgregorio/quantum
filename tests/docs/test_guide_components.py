"""docs/guide/components.md: the component the guide imports is served as the guide says (COMP-1..COMP-4).

The section "Using one component inside another" introduces its files with
"Save as `<path>`:". This test writes exactly those files into a new app,
serves it, and checks what the guide says the page shows.
"""

import re
from pathlib import Path

GUIDE = Path(__file__).resolve().parents[2] / 'docs' / 'guide' / 'components.md'
F = '`' * 3


def saved_files():
    text = GUIDE.read_text(encoding='utf-8')
    return {m['path']: m['body'] for m in re.finditer(
        r'Save as `(?P<path>[^`]+)`:\s*\n\s*\n' + F + r'xml\n(?P<body>.*?)' + F, text, re.S)}


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
