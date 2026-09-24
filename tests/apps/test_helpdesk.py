"""projects/helpdesk: tickets with attachments and e-mail, served end to end.

The mail goes to a real SMTP server in the test (tests/fake_smtp.py), and the
attachment through a real multipart POST.
"""

import io
import logging
import re
import shutil
import sqlite3
from pathlib import Path

import pytest

from tests.apps.test_blog import page_text
from tests.fake_smtp import FakeSMTP

HELPDESK = Path(__file__).resolve().parents[2] / "projects" / "helpdesk"


@pytest.fixture
def smtp():
    with FakeSMTP() as server:
        yield server


@pytest.fixture
def app(tmp_path, monkeypatch, smtp):
    project = tmp_path / "helpdesk"
    shutil.copytree(HELPDESK, project, ignore=shutil.ignore_patterns("data", "__pycache__"))
    monkeypatch.chdir(project)
    monkeypatch.setenv("SMTP_HOST", "127.0.0.1")
    monkeypatch.setenv("SMTP_PORT", str(smtp.port))
    monkeypatch.setenv("SMTP_TLS", "false")
    from quantum.cli.migrations import MigrationRunner
    assert [r["status"] for r in MigrationRunner(project).up()] == ["applied"]
    from quantum.runtime.web_server import QuantumWebServer
    logging.disable(logging.WARNING)
    flask_app = QuantumWebServer(str(project / "quantum.config.yaml")).app
    flask_app.config["TESTING"] = True
    yield flask_app.test_client(), project
    logging.disable(logging.NOTSET)


def rows(project, sql):
    return sqlite3.connect(project / "data" / "helpdesk.db").execute(sql).fetchall()


TICKET = {"action": "open", "title": "Printer on fire", "email": "ana@example.com",
          "description": "It started smoking after the update."}


def test_the_form_can_send_a_file(app):
    # UI-14: a form whose action takes a file posts multipart; a long text is a textarea
    client, _ = app
    html = client.get("/").get_data(as_text=True)
    form = re.search(r'<form[^>]*class="q-form"[^>]*>', html).group(0)
    assert 'enctype="multipart/form-data"' in form
    assert re.search(r'<input[^>]*type="file"[^>]*name="attachment"|<input[^>]*name="attachment"[^>]*type="file"', html)
    assert re.search(r'accept="\.png,\.jpg,\.jpeg,\.pdf,\.txt,\.log"', html)
    assert re.search(r'<textarea[^>]*name="description"[^>]*rows="6"', html)


def test_opening_a_ticket_stores_it_and_sends_both_mails(app, smtp):
    # MAIL-1 + FILE-1
    client, project = app
    data = dict(TICKET, attachment=(io.BytesIO(b"smoke log"), "printer log.txt"))
    response = client.post("/", data=data, content_type="multipart/form-data")
    assert response.status_code == 302 and response.headers["Location"] == "/ticket/1"
    (title, stored, sent_as), = rows(project, "select title, attachment, attachment_name from tickets")
    assert title == "Printer on fire" and sent_as == "printer log.txt"
    assert (project / "data" / "attachments" / stored).read_bytes() == b"smoke log"

    to_support, to_requester = smtp.messages
    assert to_support.envelope_to == ["support@example.com"]
    assert to_support["Subject"] == "Ticket #1: Printer on fire"
    assert to_support["Reply-To"] == "ana@example.com" and to_support["From"] == "helpdesk@example.com"
    assert "It started smoking after the update." in to_support.get_body().get_content()
    assert to_requester.envelope_to == ["ana@example.com"]

    page = page_text(client.get("/ticket/1"))
    assert "Ticket #1 opened." in page and "Attachment: printer log.txt" in page


def test_the_attachment_is_served_only_through_its_ticket(app):
    # FILE-2
    client, project = app
    client.post("/", data=dict(TICKET, attachment=(io.BytesIO(b"%PDF-1.4 x"), "report.pdf")),
                content_type="multipart/form-data")
    with client.get("/attachment/1") as response:   # a file: close it
        assert response.status_code == 200 and response.data == b"%PDF-1.4 x"
        assert 'filename=report.pdf' in response.headers["Content-Disposition"]
        assert response.headers["Content-Type"] == "application/pdf"
    stored, = rows(project, "select attachment from tickets")[0]
    assert client.get(f"/uploads/{stored}").status_code == 404        # not a public folder
    assert client.get(f"/static/{stored}").status_code == 404
    assert "There is no attachment" in page_text(client.get("/attachment/2"))


def test_a_ticket_without_attachment(app, smtp):
    client, project = app
    assert client.post("/", data=TICKET).status_code == 302
    assert rows(project, "select attachment from tickets") == [(None,)]
    assert "Attachment:" not in page_text(client.get("/ticket/1"))


def test_an_attachment_too_big_or_of_the_wrong_kind_is_refused_next_to_the_field(app, smtp):
    # FILE-1: maxSize and accept are checked like any q:param rule (ACT-2)
    client, project = app
    for name, content, error in [("big.pdf", b"x" * (5 * 1024 * 1024 + 1), "5MB"),
                                 ("virus.exe", b"MZ", ".png")]:
        response = client.post("/", data=dict(TICKET, attachment=(io.BytesIO(content), name)),
                               content_type="multipart/form-data", headers={"Referer": "http://localhost/"})
        assert response.status_code == 302 and response.headers["Location"].endswith("/")
        page = page_text(client.get("/"))
        assert error in page
    assert rows(project, "select count(*) from tickets") == [(0,)]
    assert smtp.messages == []
    attachments = project / "data" / "attachments"
    assert not attachments.exists() or not any(attachments.iterdir())


def test_closing_tells_the_requester(app, smtp):
    client, _ = app
    client.post("/", data=TICKET)
    smtp.messages.clear()
    assert client.post("/ticket/1", data={"action": "close"}).status_code == 302
    assert "Status: closed." in page_text(client.get("/ticket/1"))
    (message,) = smtp.messages
    assert message.envelope_to == ["ana@example.com"] and message["Subject"] == "Ticket #1 closed"
    client.post("/ticket/1", data={"action": "close"})
    assert len(smtp.messages) == 1                      # closing twice does not write twice


def test_a_mail_server_that_refuses_is_said_and_the_ticket_is_kept(app, smtp):
    # MAIL-2 (the page handles it with onerror="continue")
    client, project = app
    smtp.refuse("mailbox unavailable")
    response = client.post("/", data=TICKET)
    assert response.status_code == 302
    assert rows(project, "select count(*) from tickets") == [(1,)]
    assert "Some e-mail could not be sent; the ticket is saved." in page_text(client.get("/ticket/1"))


def test_the_log_backend_writes_instead_of_sending(tmp_path, monkeypatch, caplog):
    # MAIL-1: host: log
    project = tmp_path / "helpdesk"
    shutil.copytree(HELPDESK, project, ignore=shutil.ignore_patterns("data", "__pycache__"))
    monkeypatch.chdir(project)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    from quantum.cli.migrations import MigrationRunner
    MigrationRunner(project).up()
    from quantum.runtime.web_server import QuantumWebServer
    client = QuantumWebServer(str(project / "quantum.config.yaml")).app.test_client()
    with caplog.at_level(logging.INFO, logger="quantum.mail"):
        assert client.post("/", data=TICKET).status_code == 302
    logged = [r.getMessage() for r in caplog.records if r.name == "quantum.mail"]
    assert len(logged) == 2 and "To: support@example.com" in logged[0] and "Printer on fire" in logged[0]


def test_a_ticket_from_the_console(tmp_path, monkeypatch):
    # UI-3 + UI-14: the description is a multi-line field; the file field says to use the browser
    import asyncio
    import threading
    from textual.widgets import Button, Input, TextArea
    from werkzeug.serving import make_server
    from quantum.runtime.ui_console import ConsoleUI
    from quantum.runtime.web_server import QuantumWebServer
    from tests.apps.test_tarefas_console import screen_text
    from tests.console_pilot import page_loaded, press

    project = tmp_path / "helpdesk"
    shutil.copytree(HELPDESK, project, ignore=shutil.ignore_patterns("data", "__pycache__"))
    monkeypatch.chdir(project)
    monkeypatch.delenv("SMTP_HOST", raising=False)            # host: log
    from quantum.cli.migrations import MigrationRunner
    MigrationRunner(project).up()
    logging.disable(logging.WARNING)
    server = make_server("127.0.0.1", 0, QuantumWebServer(str(project / "quantum.config.yaml")).app,
                         threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    async def main():
        app = ConsoleUI(f"http://127.0.0.1:{server.server_port}/")
        async with app.run_test(size=(140, 60)) as pilot:
            await page_loaded(app, pilot)
            assert "attachment: attach files from the browser" in screen_text(app)
            title, email = [i for i in app.query(Input)][:2]
            title.value, email.value = "Console ticket", "bruno@example.com"
            app.query_one(TextArea).text = "First line\nsecond line of the description"
            await press(app, pilot, [b for b in app.query(Button) if str(b.label) == "Open ticket"][0])
            assert "Ticket #1 opened." in screen_text(app)
            assert "second line of the description" in screen_text(app)

    try:
        asyncio.run(main())
    finally:
        server.shutdown()
        logging.disable(logging.NOTSET)
    assert rows(project, "select description from tickets") == [("First line\nsecond line of the description",)]
