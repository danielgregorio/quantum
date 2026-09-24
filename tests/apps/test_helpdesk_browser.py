"""projects/helpdesk in a real browser: a file chosen, a ticket opened, the
attachment downloaded (UI-14, FILE-1, FILE-2).

Runs with Playwright + Chromium (installed in CI; skipped locally without them).
"""

import logging
import shutil
import threading
from pathlib import Path

import pytest

from tests.fake_smtp import FakeSMTP

HELPDESK = Path(__file__).resolve().parents[2] / "projects" / "helpdesk"

playwright = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")


@pytest.fixture(scope="module")
def browser():
    with playwright.sync_playwright() as pw:
        try:
            chromium = pw.chromium.launch()
        except Exception as exc:
            pytest.skip(f"Playwright's Chromium is not available: {exc}")
        yield chromium
        chromium.close()


@pytest.fixture
def url(tmp_path, monkeypatch):
    project = tmp_path / "helpdesk"
    shutil.copytree(HELPDESK, project, ignore=shutil.ignore_patterns("data", "__pycache__"))
    monkeypatch.chdir(project)
    with FakeSMTP() as smtp:
        monkeypatch.setenv("SMTP_HOST", "127.0.0.1")
        monkeypatch.setenv("SMTP_PORT", str(smtp.port))
        monkeypatch.setenv("SMTP_TLS", "false")
        from quantum.cli.migrations import MigrationRunner
        MigrationRunner(project).up()
        from werkzeug.serving import make_server
        from quantum.runtime.web_server import QuantumWebServer
        logging.disable(logging.WARNING)
        server = make_server("127.0.0.1", 0, QuantumWebServer(str(project / "quantum.config.yaml")).app,
                             threaded=True)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        yield f"http://127.0.0.1:{server.server_port}/", smtp
        server.shutdown()
        logging.disable(logging.NOTSET)


def test_open_a_ticket_with_a_file_and_download_it(browser, url, tmp_path):
    base, smtp = url
    upload = tmp_path / "screen shot.png"
    upload.write_bytes(b"\x89PNG fake image")
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(base)
    page.fill("input[name=title]", "Screen goes black")
    page.fill("input[name=email]", "carla@example.com")
    page.fill("textarea[name=description]", "Every morning at nine.\nThen it comes back.")
    page.set_input_files("input[name=attachment]", str(upload))
    page.click("text=Open ticket")
    page.wait_for_url("**/ticket/1")
    assert "Ticket #1 opened." in page.content()
    assert "Then it comes back." in page.inner_text("#description")

    with page.expect_download() as info:
        page.click("#attachment")
    download = info.value
    assert download.suggested_filename == "screen shot.png"
    assert Path(download.path()).read_bytes() == b"\x89PNG fake image"
    assert len(smtp.messages) == 2 and errors == []
