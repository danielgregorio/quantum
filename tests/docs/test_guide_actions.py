"""docs/guide/actions.md: the pages it shows are served, and do what it says.

The contact page's post / redirect / get cycle and its validation message,
the page with two actions and the 400 for a missing or unknown one, and the
q:flash fragment inside an action. The page's blocks with an **Error:** are
run by test_guide_examples_run.py.
"""

import html
import re
from pathlib import Path

from tests.conformance.conftest import serve_pages  # noqa: F401 — the fixture

PAGE = Path(__file__).resolve().parents[2] / 'docs' / 'guide' / 'actions.md'
TEXT = PAGE.read_text(encoding='utf-8')
F = '`' * 3


def block_after(marker, fence='xml'):
    start = TEXT.index(marker)
    m = re.search(F + re.escape(fence) + r'[^\n]*\n(.*?)' + F, TEXT[start:], re.S)
    return m.group(1)


def visible(response):
    body = response.get_data(as_text=True)
    return html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', body)))


def test_the_contact_form_posts_redirects_and_shows_the_flash_once(serve_pages):
    client = serve_pages(contact=block_after('Save as `components/contact.q`'))
    assert 'Last contact:' in visible(client.get('/contact'))

    response = client.post('/contact', data={'name': 'Ana'})
    assert response.status_code == 302 and response.headers['Location'].endswith('/contact')
    page = visible(client.get('/contact'))
    assert 'Thank you, Ana!' in page and 'Last contact: Ana' in page
    assert 'Thank you, Ana!' not in visible(client.get('/contact'))     # once


def test_a_rule_that_fails_sends_the_reason_back(serve_pages):
    # The message the page quotes for a name that is too short.
    quoted = re.search(r"for example `([^`]+)`", TEXT).group(1)
    client = serve_pages(contact=block_after('Save as `components/contact.q`'))
    response = client.post('/contact', data={'name': 'A'}, headers={'Referer': '/contact'})
    assert response.status_code == 302
    page = visible(client.get('/contact'))
    assert quoted in page
    assert 'Last contact: A' not in page                                  # the action did not run


def test_the_form_says_which_action_it_wants(serve_pages):
    client = serve_pages(tasks=block_after('## Several actions on one page'))
    client.post('/tasks', data={'action': 'create', 'title': 'Buy bread'})
    assert 'Created: Buy bread' in visible(client.get('/tasks'))
    client.post('/tasks', data={'action': 'clear'})
    assert 'List cleared' in visible(client.get('/tasks'))


def test_a_missing_or_unknown_action_is_refused_with_400(serve_pages):
    client = serve_pages(tasks=block_after('## Several actions on one page'))
    for data in ({'title': 'x'}, {'action': 'archive', 'title': 'x'}):
        response = client.post('/tasks', data=data)
        text = response.get_data(as_text=True)
        assert response.status_code == 400
        assert 'create' in text and 'clear' in text                       # names the actions that exist


def test_q_flash_sets_a_flash_of_another_kind(serve_pages):
    fragment = block_after('use `q:flash` before the redirect:')
    page = ('<q:component name="login" xmlns:q="https://quantum.lang/ns">'
            f'<q:action name="signin" method="POST">{fragment}</q:action>'
            '<q:if condition="flash"><p class="{flashType}">{flash}</p></q:if></q:component>')
    client = serve_pages(login=page)
    response = client.post('/login', data={'action': 'signin'})
    assert response.status_code == 302 and response.headers['Location'].endswith('/login')
    body = client.get('/login').get_data(as_text=True)
    assert re.search(r'<p class="error">\s*Invalid credentials\s*</p>', body)
