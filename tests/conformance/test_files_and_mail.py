"""Conformance: uploads, sending a file, and e-mail (SPEC FILE-1, FILE-2, MAIL-1, MAIL-2, UI-14)."""

import io
import logging

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.component import ComponentRuntime
from tests.fake_smtp import FakeSMTP

NS = 'xmlns:q="https://quantum.lang/ns" xmlns:ui="https://quantum.lang/ui"'


def page(body):
    return f'<q:component name="p" {NS}>{body}</q:component>'


def run(body, config):
    return ComponentRuntime(config=config).execute_component(QuantumParser().parse(page(body)), {})


MAIL = '<q:mail to="ana@example.com" subject="Hi {{n}}" type="text" {extra}>Hello {{n}}</q:mail>'


class TestMail:
    def test_without_a_mail_server_it_says_what_to_configure(self):
        # MAIL-1 (before: "[MOCK] Email sent" printed, success returned, nothing sent)
        with pytest.raises(Exception, match=r'q:mail needs a mail server: add `mail:`.*host: log'):
            run('<q:set name="n" value="1"/>' + MAIL.format(extra=''), {})

    def test_it_sends_through_the_configured_server(self):
        # MAIL-1
        with FakeSMTP() as smtp:
            config = {'mail': {'host': '127.0.0.1', 'port': smtp.port, 'tls': 'false', 'from': 'app@example.com'}}
            result = run('<q:set name="n" value="7"/>' + MAIL.format(extra='') +
                         '<q:return value="{mail_result.success}"/>', config)
        assert result is True
        (message,) = smtp.messages
        assert message['Subject'] == 'Hi 7' and message['From'] == 'app@example.com'
        assert message.envelope_to == ['ana@example.com'] and 'Hello 7' in message.get_body().get_content()

    def test_host_log_writes_the_message_instead(self, caplog):
        # MAIL-1
        with caplog.at_level(logging.INFO, logger='quantum.mail'):
            result = run('<q:set name="n" value="2"/>' + MAIL.format(extra='') +
                         '<q:return value="{mail_result.logged}"/>', {'mail': {'host': 'log', 'from': 'a@b.c'}})
        assert result is True
        assert any('To: ana@example.com' in r.getMessage() and 'Hello 2' in r.getMessage() for r in caplog.records)

    def test_no_sender_is_an_error(self):
        # MAIL-1
        with pytest.raises(Exception, match='q:mail has no sender'):
            run('<q:set name="n" value="1"/>' + MAIL.format(extra=''), {'mail': {'host': 'log'}})

    def test_a_refusal_stops_the_page_unless_the_page_handles_it(self):
        # MAIL-2
        with FakeSMTP() as smtp:
            smtp.refuse('mailbox unavailable')
            config = {'mail': {'host': '127.0.0.1', 'port': smtp.port, 'tls': 'false', 'from': 'a@b.c'}}
            with pytest.raises(Exception, match=r'refused every recipient: ana@example.com \(550 mailbox '
                                                r'unavailable\).*onerror="continue"'):
                run('<q:set name="n" value="1"/>' + MAIL.format(extra=''), config)
            result = run('<q:set name="n" value="1"/>' + MAIL.format(extra='name="hello" onerror="continue"') +
                         '<q:return value="{[hello_result.success, hello_result.error.message]}"/>', config)
        assert result[0] is False and '550 mailbox unavailable' in result[1]

    def test_a_page_bug_is_not_a_mail_failure(self):
        # MAIL-2: onerror="continue" does not hide an expression that cannot be evaluated
        with pytest.raises(Exception, match="'missing' is not defined"):
            run(MAIL.format(extra='onerror="continue"').replace('{n}', '{missing}'),
                {'mail': {'host': 'log', 'from': 'a@b.c'}})

    def test_onerror_takes_fail_or_continue(self):
        # MAIL-2
        with pytest.raises(Exception, match='onerror must be "fail" or "continue"'):
            QuantumParser().parse(page(MAIL.format(extra='onerror="skip"')))


UPLOAD = '''
<q:action name="send" method="POST">
  <q:param name="doc" type="file" required="true" {rules} />
  <q:file action="upload" file="{{doc}}" result="saved" />
  <q:redirect url="/p?saved={{saved.filename}}" />
</q:action>
<q:set name="note" value="{{query.note}}" default="" />
<ui:window title="U"><ui:form on-submit="send" submit="Send">
  <ui:input bind="doc" /><ui:input bind="note" rows="3" value="{{note}}" />
</ui:form></ui:window>'''


def upload_client(serve_pages, tmp_path, rules=''):
    return serve_pages(p=page(UPLOAD.format(rules=rules)))


class TestUpload:
    def test_a_form_for_a_file_posts_multipart_and_accepts_what_the_param_accepts(self, serve_pages, tmp_path):
        # UI-14
        html = upload_client(serve_pages, tmp_path, 'accept=".pdf"').get('/p').get_data(as_text=True)
        assert 'enctype="multipart/form-data"' in html
        assert 'type="file"' in html and 'accept=".pdf"' in html
        assert '<textarea' in html and 'rows="3"' in html

    def test_a_multi_line_value_is_escaped(self, serve_pages, tmp_path):
        # UI-14
        html = upload_client(serve_pages, tmp_path).get('/p?note=</textarea><script>x</script>').get_data(as_text=True)
        assert '<script>x</script>' not in html and '&lt;/textarea&gt;' in html

    def test_the_file_is_saved_under_paths_uploads(self, serve_pages, tmp_path, monkeypatch):
        # FILE-1: without destination=, paths.uploads itself (./uploads)
        monkeypatch.chdir(tmp_path)
        client = upload_client(serve_pages, tmp_path)
        r = client.post('/p', data={'action': 'send', 'doc': (io.BytesIO(b'abc'), 'a b.txt')},
                        content_type='multipart/form-data')
        assert r.status_code == 302 and r.headers['Location'] == '/p?saved=a_b.txt'
        assert (tmp_path / 'uploads' / 'a_b.txt').read_bytes() == b'abc'

    def test_maxsize_is_checked(self, serve_pages, tmp_path, monkeypatch):
        # FILE-1 (before: maxsize= was parsed and never checked)
        monkeypatch.chdir(tmp_path)
        client = upload_client(serve_pages, tmp_path, 'maxsize="1KB"')
        r = client.post('/p', data={'action': 'send', 'doc': (io.BytesIO(b'x' * 2048), 'big.txt')},
                        content_type='multipart/form-data', headers={'Referer': 'http://localhost/p'})
        assert r.headers['Location'].endswith('/p')
        assert "at most 1KB; &#x27;big.txt&#x27; has 2KB" in client.get('/p').get_data(as_text=True)
        assert not (tmp_path / 'uploads').exists()

    @pytest.mark.parametrize('attr, error', [('maxsize="lots"', 'a size like 500KB'),
                                             ('maxSize="1MB"', 'the attribute is maxsize')])
    def test_maxsize_must_be_a_size(self, attr, error):
        # FILE-1
        with pytest.raises(Exception, match=error):
            QuantumParser().parse(page(f'<q:action name="a"><q:param name="f" type="file" {attr}/></q:action>'))

    def test_rows_is_a_number_of_lines(self):
        # UI-14
        with pytest.raises(Exception, match=r'rows="1".*2 or more'):
            QuantumParser().parse(page('<ui:window><ui:input bind="x" rows="1"/></ui:window>'))


SEND = page('<q:file action="send" file="{query.f}" name="{query.n}" /><p>after</p>')


class TestSend:
    def test_a_page_answers_with_the_file(self, serve_pages, tmp_path, monkeypatch):
        # FILE-2
        monkeypatch.chdir(tmp_path)
        (tmp_path / 'uploads').mkdir()
        (tmp_path / 'uploads' / 'x1.pdf').write_bytes(b'%PDF')
        with serve_pages(s=SEND).get('/s?f=x1.pdf&n=report.pdf') as r:   # a file: close it
            assert r.status_code == 200 and r.data == b'%PDF'
            assert r.headers['Content-Type'] == 'application/pdf'
            assert 'attachment; filename=report.pdf' in r.headers['Content-Disposition']

    def test_a_missing_file_is_404(self, serve_pages, tmp_path, monkeypatch):
        # FILE-2
        monkeypatch.chdir(tmp_path)
        assert serve_pages(s=SEND).get('/s?f=nothing.pdf&n=x').status_code == 404

    def test_nothing_outside_paths_uploads(self, serve_pages, tmp_path, monkeypatch):
        # FILE-2
        monkeypatch.chdir(tmp_path)
        (tmp_path / 'secret.txt').write_text('no')
        r = serve_pages(s=SEND).get('/s?f=../secret.txt&n=x')
        assert r.status_code == 500 and b'no' != r.data

    def test_send_is_an_action_of_q_file(self):
        # FILE-2
        with pytest.raises(Exception, match='use upload, delete or send'):
            QuantumParser().parse(page('<q:file action="download" file="x"/>'))


# ------------------------------------------------------------------ MAIL-1: the message

def test_cc_bcc_reply_to_and_type():
    # MAIL-1: bcc receives it without being named in it
    with FakeSMTP() as smtp:
        config = {'mail': {'host': '127.0.0.1', 'port': smtp.port, 'tls': 'false', 'from': 'app@example.com'}}
        run('<q:mail to="ana@example.com" cc="bia@example.com" bcc="caio@example.com" replyTo="help@example.com" '
            'subject="Hi">Hello</q:mail>', config)
    (message,) = smtp.messages
    assert sorted(message.envelope_to) == ['ana@example.com', 'bia@example.com', 'caio@example.com']
    assert message['Cc'] == 'bia@example.com' and message['Reply-To'] == 'help@example.com'
    assert 'caio@example.com' not in message.as_string()
    assert message.get_body().get_content_type() == 'text/html'


@pytest.mark.parametrize('attributes,missing', [('subject="x"', "'to'"), ('to="a@b.co"', "'subject'")])
def test_to_and_subject_are_required(attributes, missing):
    # MAIL-1
    with pytest.raises(Exception, match=missing):
        QuantumParser().parse(page(f'<q:mail {attributes}>x</q:mail>'))


# ------------------------------------------------------------------ FILE-1: nameConflict

@pytest.mark.parametrize('mode,second', [('makeUnique', r'\[same_\w+\.txt\|\]'), ('overwrite', r'\[same\.txt\|\]'),
                                         ('skip', r'\[same\.txt\|\]'), ('error', r'already exists')])
def test_name_conflict(serve_pages, tmp_path, monkeypatch, mode, second):
    # FILE-1
    import re
    monkeypatch.chdir(tmp_path)
    client = serve_pages(p=page(
        f'<q:action name="a" method="POST"><q:param name="doc" type="file"/>'
        f'<q:file action="upload" file="{{doc}}" nameConflict="{mode}" result="r"/>'
        f'<q:set name="session.r" value="{{r.filename}}"/><q:redirect url="/p"/></q:action>'
        f'<p>[{{session.r}}|{{flash}}]</p>'))
    for content in (b'one', b'two'):
        client.post('/p', data={'doc': (io.BytesIO(content), 'same.txt')}, content_type='multipart/form-data')
    assert re.search(second, client.get('/p').get_data(as_text=True))
    stored = (tmp_path / 'uploads' / 'same.txt').read_bytes()
    assert stored == (b'two' if mode == 'overwrite' else b'one')


def test_a_text_message_and_the_body_attribute():
    # MAIL-1: HTML unless type="text"; body= when the tag has no content
    with FakeSMTP() as smtp:
        config = {'mail': {'host': '127.0.0.1', 'port': smtp.port, 'tls': 'false', 'from': 'app@example.com'}}
        run('<q:set name="n" value="3"/><q:mail to="ana@example.com" subject="s" type="text" body="Total {n}"/>', config)
    (message,) = smtp.messages
    assert message.get_body().get_content_type() == 'text/plain' and 'Total 3' in message.get_body().get_content()
