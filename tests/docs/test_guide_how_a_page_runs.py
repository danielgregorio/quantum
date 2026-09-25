"""docs/guide/how-a-page-runs.md: a page variable does not exist in an action.

The page's example sets `total` on the page and reads it in an action. This
serves the example as the page shows it, checks the page renders the total,
and posts the action: it must fail with the message the page quotes (ACT-9).
The page's **Shows:** blocks are run by test_guide_ui.py.
"""

import logging
import re
from pathlib import Path

from tests.conformance.conftest import serve_pages  # noqa: F401 — the fixture

PAGE = Path(__file__).resolve().parents[2] / 'docs' / 'guide' / 'how-a-page-runs.md'
TEXT = PAGE.read_text(encoding='utf-8')
F = '`' * 3


def shown(after):
    """The first ```xml block after `after`, and the ```text block after it."""
    start = TEXT.index(after)
    xml = re.search(F + r'xml\n(.*?)' + F, TEXT[start:], re.S)
    message = re.search(F + r'text\n(.*?)\n' + F, TEXT[start + xml.end():], re.S)
    return xml.group(1), message.group(1)


class Messages(logging.Handler):
    def __init__(self):
        super().__init__()
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


def test_a_page_variable_does_not_exist_in_an_action(serve_pages):
    # ACT-9
    source, message = shown('a variable the page\nsets does not exist there:')
    client = serve_pages(order=source)
    assert 'Total: 42' in client.get('/order').get_data(as_text=True)

    handler = Messages()
    log = logging.getLogger('quantum')
    log.addHandler(handler)
    try:
        response = client.post('/order', data={'action': 'pay'})
    finally:
        log.removeHandler(handler)
    assert response.status_code == 500
    assert any(message in m for m in handler.messages), handler.messages
