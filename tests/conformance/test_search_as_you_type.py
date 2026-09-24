"""Conformance: search as you type (M15, SPEC UI-12)."""

import asyncio
import logging
import re
import sqlite3
import threading

import pytest

NS = 'xmlns:q="https://quantum.lang/ns" xmlns:ui="https://quantum.lang/ui"'

PAGE = (f'<q:component name="b" {NS}>'
        '<q:set name="term" value="{query.q}" default=""/>'
        '<q:query name="found" datasource="db">SELECT n FROM fruits WHERE n LIKE :p ORDER BY n'
        '<q:param name="p" value="%{term}%" type="string"/></q:query>'
        '<ui:window title="Search"><ui:input bind="q" search="results" placeholder="Search" delay="150"/>'
        '<ui:vbox id="results"><ui:text>Found: {found_result.recordCount}</ui:text>'
        '<ui:list source="{found}" as="f"><ui:item><ui:text>{f.n}</ui:text></ui:item></ui:list>'
        '</ui:vbox></ui:window></q:component>')


@pytest.fixture
def db(tmp_path):
    path = tmp_path / 'f.db'
    c = sqlite3.connect(path)
    c.execute('CREATE TABLE fruits (n TEXT)')
    c.executemany('INSERT INTO fruits VALUES (?)', [('banana',), ('bacuri',), ('cashew',), ('grape',)])
    c.commit()
    c.close()
    return path


@pytest.fixture
def open_page(serve_pages, db):
    ds = f'datasources:\n  db:\n    driver: sqlite\n    database: {db.as_posix()}\n'
    return lambda **p: serve_pages(datasources_yaml=ds, **p)


class TestServer:
    def test_the_field_becomes_a_get_form_with_htmx(self, open_page):
        # UI-12
        html = open_page(b=PAGE).get('/b?q=ba&order=az&page=4').get_data(as_text=True)
        form = re.search(r'<form[^>]*role="search".*?</form>', html, re.S).group(0)
        assert 'method="get"' in form and 'action="/b"' in form
        assert '<input type="hidden" name="order" value="az" />' in form and 'name="page"' not in form
        assert 'hx-trigger="input changed delay:150ms, search"' in form
        assert 'hx-target="#results"' in form and 'hx-select="#results"' in form and 'hx-push-url="true"' in form
        assert 'value="ba"' in form and 'name="q"' in form
        assert 'Found: 2' in html
        assert 'htmx' in html.split('</head>')[0] or 'htmx' in html          # the library is on the page

    def test_without_javascript_enter_searches(self, open_page):
        # UI-12: the GET form is the real search; htmx only makes it faster
        assert 'Found: 1' in open_page(b=PAGE).get('/b?q=cash').get_data(as_text=True)

    def test_a_target_that_does_not_exist_is_an_error(self, open_page, caplog):
        # UI-12
        c = open_page(b=PAGE.replace('id="results"', 'id="other"'))
        with caplog.at_level(logging.ERROR, logger='quantum.server'):
            assert c.get('/b').status_code == 500
        assert any('there is no element with id="results"' in r.getMessage() for r in caplog.records)

    def test_inside_a_ui_form_it_is_an_error(self, open_page, caplog):
        # UI-12
        page = PAGE.replace('<ui:input bind="q" search="results" placeholder="Search" delay="150"/>',
                            '<ui:form on-submit="a"><ui:input bind="q" search="results"/></ui:form>')
        page = page.replace('<ui:window', '<q:action name="a" method="POST"><q:redirect url="/b"/></q:action><ui:window')
        c = open_page(b=page)
        with caplog.at_level(logging.ERROR, logger='quantum.server'):
            assert c.get('/b').status_code == 500
        assert any('cannot be inside a ui:form' in r.getMessage() for r in caplog.records)

    @pytest.mark.parametrize('attributes,message', [('search="results" delay="fast"', 'milliseconds'),
                                                    ('search="results"', 'needs bind=')])
    def test_invalid_attributes_are_parse_errors(self, attributes, message):
        # UI-12
        from quantum.core.parser import QuantumParser
        source = PAGE.replace('<ui:input bind="q" search="results" placeholder="Search" delay="150"/>',
                              f'<ui:input {"bind=" + chr(34) + "q" + chr(34) if "delay" in attributes else ""} {attributes}/>')
        with pytest.raises(Exception, match=message):
            QuantumParser().parse(source)


def serve(tmp_path, db, monkeypatch):
    from werkzeug.serving import make_server
    from quantum.runtime.web_server import QuantumWebServer
    (tmp_path / 'components').mkdir(exist_ok=True)
    (tmp_path / 'components' / 'b.q').write_text(PAGE, encoding='utf-8')
    (tmp_path / 'quantum.config.yaml').write_text(
        'paths: {components: ./components}\n'
        f'datasources:\n  db:\n    driver: sqlite\n    database: {db.as_posix()}\n', encoding='utf-8')
    monkeypatch.chdir(tmp_path)
    logging.disable(logging.WARNING)
    server = make_server('127.0.0.1', 0, QuantumWebServer('quantum.config.yaml').app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def test_the_console_searches_on_each_pause_and_keeps_the_focus(tmp_path, db, monkeypatch):
    # UI-12, UI-3
    from textual.widgets import Input, Static
    from quantum.runtime.ui_console import ConsoleUI
    from tests.console_pilot import page_loaded, searched
    server = serve(tmp_path, db, monkeypatch)

    async def main():
        app = ConsoleUI(f'http://127.0.0.1:{server.server_port}/', '/b')
        async with app.run_test(size=(100, 40)) as pilot:
            await page_loaded(app, pilot)
            field = app.query_one(Input)
            field.focus()
            await pilot.press('b', 'a')
            await searched(app, pilot, 'q', 'ba')          # the search for what was typed, not the first load
            texts = [str(w.render()) for w in app.query(Static)]
            new = app.query_one(Input)
            return texts, app.path, new.value, app.focused is new

    try:
        texts, path, value, focused = asyncio.run(main())
    finally:
        server.shutdown()
        logging.disable(logging.NOTSET)
    assert 'Found: 2' in texts and 'banana' in texts and 'cashew' not in texts
    assert path == '/b?q=ba' and value == 'ba' and focused


def test_typing_after_a_pause_adds_to_the_text(tmp_path, db, monkeypatch):
    # UI-12: a pause after "b" searches "b"; typing "a" then searches "ba". The
    # redrawn field got the focus with its text selected, so "a" REPLACED "b"
    # and searched "a". A busy machine hit this by accident (a keystroke later
    # than the delay), and a wait for "a page load" read the page before it.
    from textual.widgets import Input, Static
    from quantum.runtime.ui_console import ConsoleUI
    from tests.console_pilot import page_loaded, searched
    server = serve(tmp_path, db, monkeypatch)

    async def main():
        app = ConsoleUI(f'http://127.0.0.1:{server.server_port}/', '/b')
        async with app.run_test(size=(100, 40)) as pilot:
            await page_loaded(app, pilot)
            app.query_one(Input).focus()
            await pilot.press('b')
            await searched(app, pilot, 'q', 'b')
            after_b = ([str(w.render()) for w in app.query(Static)], app.path)
            await pilot.press('a')
            await searched(app, pilot, 'q', 'ba')
            after_ba = ([str(w.render()) for w in app.query(Static)], app.path, app.focused is app.query_one(Input))
            return after_b, after_ba

    try:
        (b_texts, b_path), (ba_texts, ba_path, focused) = asyncio.run(main())
    finally:
        server.shutdown()
        logging.disable(logging.NOTSET)
    assert 'Found: 2' in b_texts and b_path == '/b?q=b'
    assert 'Found: 2' in ba_texts and ba_path == '/b?q=ba' and focused


def test_the_browser_swaps_only_the_list_while_typing(tmp_path, db, monkeypatch):
    # UI-12: real htmx in Chromium
    playwright = pytest.importorskip('playwright.sync_api', reason='Playwright is not installed')
    server = serve(tmp_path, db, monkeypatch)
    try:
        with playwright.sync_playwright() as pw:
            try:
                browser = pw.chromium.launch()
            except Exception as exc:
                pytest.skip(f"Playwright's Chromium is not available: {exc}")
            page = browser.new_page()
            page.goto(f'http://127.0.0.1:{server.server_port}/b')
            if not page.evaluate('typeof window.htmx !== "undefined"'):
                browser.close()
                pytest.skip('htmx did not load (no network for the CDN)')
            page.evaluate('window.__mark = 1')                        # gone if the whole page reloads
            page.locator('input[name=q]').press_sequentially('cash', delay=40)
            # The search for everything typed: on a busy machine a pause after
            # "cas" searches "cas" first, which also says "Found: 1" — a wait
            # for that text alone ended there, and the URL still said q=cas.
            page.wait_for_function('location.search === "?q=cash" && '
                                   'document.querySelector("#results").innerText.includes("Found: 1")',
                                   timeout=5000)
            assert page.evaluate('window.__mark') == 1                 # only the region was swapped
            assert page.url.endswith('/b?q=cash')                      # hx-push-url
            assert page.locator('#results').inner_text().count('cashew') == 1
            browser.close()
    finally:
        server.shutdown()
        logging.disable(logging.NOTSET)
