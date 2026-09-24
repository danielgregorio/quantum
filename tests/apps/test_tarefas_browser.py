"""projects/tarefas in a real browser: responsive layout (UI-2) and clicks.

Runs with Playwright + Chromium (installed in CI; locally, without them, the
tests are skipped with the reason). The server is the real one, on a free port.
"""

import logging
import shutil
import threading
from pathlib import Path

import pytest

TAREFAS = Path(__file__).resolve().parents[2] / "projects" / "tarefas"

playwright = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")


@pytest.fixture(scope="module")
def browser():
    with playwright.sync_playwright() as pw:
        try:
            chromium = pw.chromium.launch()
        except Exception as exc:   # browser not downloaded
            pytest.skip(f"Playwright's Chromium is not available: {exc}")
        yield chromium
        chromium.close()


@pytest.fixture
def url(tmp_path, monkeypatch):
    project = tmp_path / "tarefas"
    shutil.copytree(TAREFAS, project, ignore=shutil.ignore_patterns("data", "__pycache__"))
    monkeypatch.chdir(project)
    from quantum.cli.migrations import MigrationRunner
    MigrationRunner(project).up()
    from werkzeug.serving import make_server
    from quantum.runtime.web_server import QuantumWebServer
    logging.disable(logging.WARNING)
    app = QuantumWebServer(str(project / "quantum.config.yaml")).app
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/"
    server.shutdown()
    logging.disable(logging.NOTSET)


def box(page, selector):
    return page.locator(selector).first.bounding_box()


def test_side_by_side_on_a_wide_screen(browser, url):
    # UI-2
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    page.goto(url)
    side, content = box(page, "#lateral"), box(page, "#conteudo")
    assert content["x"] >= side["x"] + side["width"]                # to the right
    assert abs(content["y"] - side["y"]) < 2                          # same row
    assert content["width"] > 600                                     # grow: takes the rest
    assert page.evaluate("document.documentElement.scrollWidth") <= 1280


def test_stacked_on_a_phone_without_overflowing(browser, url):
    # UI-2
    page = browser.new_page(viewport={"width": 390, "height": 800})
    page.goto(url)
    side, content = box(page, "#lateral"), box(page, "#conteudo")
    assert content["y"] >= side["y"] + side["height"]                # below
    assert side["width"] > 300                                        # the fixed width goes when stacked
    assert page.evaluate("document.documentElement.scrollWidth") <= 390


def test_create_and_complete_by_clicking(browser, url):
    # UI-1, in the browser
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(url)
    page.fill("input[name=titulo]", "Clicada no navegador")
    page.click("text=Criar")
    page.wait_for_load_state()
    assert "Criada: Clicada no navegador" in page.inner_text("body")
    page.locator("form.q-action:has(input[value=alternar]) button").first.click()
    page.wait_for_load_state()
    assert page.inner_text("body").count("Reabrir") == 2
    assert errors == []
