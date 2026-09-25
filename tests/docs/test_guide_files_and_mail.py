"""docs/guide/files-and-mail.md: the upload action and the attachment page do what it says.

The upload example is served as a page and posted a real multipart file: a
PDF is saved under paths.uploads, a file type outside `accept` and a title
that breaks `minlength` never reach the action. The attachment page (a
dynamic route, components/attachment/[id].q) sends the stored file as a
download, says when there is none, and answers 404 when the file is gone.
The mail examples on the page are imported from tested Cookbook recipes; its
**Error:** blocks are run by test_guide_examples_run.py.
"""

import io
import re
import sqlite3
from pathlib import Path

import pytest

PAGE = Path(__file__).resolve().parents[2] / 'docs' / 'guide' / 'files-and-mail.md'
TEXT = PAGE.read_text(encoding='utf-8')
F = '`' * 3
NS = 'xmlns:q="https://quantum.lang/ns"'


def block_after(marker):
    start = TEXT.index(marker)
    return re.search(F + r'xml\n(.*?)' + F, TEXT[start:], re.S).group(1)


@pytest.fixture
def app(tmp_path):
    """A client for an app in tmp_path: app(pages={'path/name': source})."""
    from quantum.runtime.web_server import QuantumWebServer

    def build(pages):
        components = tmp_path / 'components'
        for rel, source in pages.items():
            target = components / f'{rel}.q'
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source, encoding='utf-8')
        db = tmp_path / 'app.db'
        config = tmp_path / 'quantum.config.yaml'
        config.write_text(
            f"server:\n  debug: false\n"
            f"paths:\n  components: {components.as_posix()}\n  uploads: {(tmp_path / 'uploads').as_posix()}\n"
            f"logging:\n  level: ERROR\n  console: false\n  file: false\n"
            f"datasources:\n  db:\n    driver: sqlite\n    database: {db.as_posix()}\n",
            encoding='utf-8')
        server = QuantumWebServer(str(config))
        server.app.config['TESTING'] = True
        return server.app.test_client()
    return build


def upload_page():
    # The example is an action and a form; a page holds them.
    return f'<q:component name="ticket" {NS}>{block_after("## Taking a file")}</q:component>'


def post(client, title, filename, content=b'%PDF-1.4 test'):
    return client.post('/ticket', data={'title': title, 'attachment': (io.BytesIO(content), filename)},
                       content_type='multipart/form-data', headers={'Referer': '/ticket'})


def test_the_form_posts_the_file_and_offers_the_accepted_types(app):
    body = app({'ticket': upload_page()}).get('/ticket').get_data(as_text=True)
    assert 'multipart/form-data' in body
    assert re.search(r'<input[^>]*type="file"[^>]*accept="\.png,\.jpg,\.pdf"', body) or \
        re.search(r'<input[^>]*accept="\.png,\.jpg,\.pdf"[^>]*type="file"', body)


def test_a_pdf_is_saved_under_paths_uploads(app, tmp_path):
    client = app({'ticket': upload_page()})
    assert post(client, 'Printer is broken', 'receipt.pdf').status_code == 302
    saved = list((tmp_path / 'uploads').rglob('*'))
    assert [p.read_bytes() for p in saved if p.is_file()] == [b'%PDF-1.4 test']


def test_a_file_outside_accept_or_a_short_title_never_reaches_the_action(app, tmp_path):
    client = app({'ticket': upload_page()})
    post(client, 'Printer is broken', 'virus.exe')
    post(client, 'Oops', 'receipt.pdf')
    assert not [p for p in (tmp_path / 'uploads').rglob('*') if p.is_file()]


def test_the_attachment_page_sends_the_file_to_whoever_the_page_allows(app, tmp_path):
    (tmp_path / 'uploads').mkdir()
    (tmp_path / 'uploads' / 'a1b2.pdf').write_bytes(b'%PDF-1.4 stored')
    db = sqlite3.connect(tmp_path / 'app.db')
    db.execute('CREATE TABLE tickets (id INTEGER PRIMARY KEY, attachment TEXT, attachment_name TEXT)')
    db.execute("INSERT INTO tickets VALUES (1, 'a1b2.pdf', 'receipt.pdf'), (2, NULL, NULL), "
               "(3, 'gone.pdf', 'gone.pdf')")
    db.commit()
    db.close()
    client = app({'attachment/[id]': block_after('A page sends one, and decides who may have it:')})

    response = client.get('/attachment/1')
    assert response.status_code == 200 and response.data == b'%PDF-1.4 stored'
    assert 'attachment' in response.headers['Content-Disposition']
    assert 'receipt.pdf' in response.headers['Content-Disposition']

    assert 'There is no attachment for ticket #2.' in client.get('/attachment/2').get_data(as_text=True)
    assert client.get('/attachment/3').status_code == 404       # a missing file answers 404
