"""Conformance: motion, the same in every renderer (SPEC UI-19).

The same page in the browser and in the console: each records the motions it ran — kind, speed, what —
and the lists are the same; when the motions end, every element is where it belongs, fully shown.
"""

import asyncio
import logging
import threading

import pytest

NS = 'xmlns:q="https://quantum.lang/ns" xmlns:ui="https://quantum.lang/ui"'

PAGE = f'''<q:component name="m" {NS}>
  <q:set name="moved" value="{{query.moved}}" default="0" type="number" />
  <q:set name="ids" type="array" value="[1, 2, 3]" />
  <ui:window title="Motion" transition="slide">
    <ui:panel title="Cards">
      <q:loop items="{{ids}}" var="n">
        <ui:card title="Card {{n}}" enter="{{n == moved and 'slide' or ''}}" />
      </q:loop>
    </ui:panel>
    <ui:animate type="expand" speed="fast"><ui:text>Opened</ui:text></ui:animate>
    <ui:animate type="bounce"><ui:text>Only the browser bounces</ui:text></ui:animate>
    <ui:alert id="note" enter="fade">Noted</ui:alert>
    <ui:tabpanel>
      <ui:tab title="First"><ui:text>One</ui:text></ui:tab>
      <ui:tab title="Second"><ui:text>Two</ui:text></ui:tab>
    </ui:tabpanel>
  </ui:window>
</q:component>'''

ON_OPEN = [{'kind': 'slide', 'speed': 'normal', 'what': 'page'},
           {'kind': 'slide', 'speed': 'normal', 'what': 'card'},
           {'kind': 'expand', 'speed': 'fast', 'what': 'animate'},
           {'kind': 'fade', 'speed': 'normal', 'what': 'note'}]
TAB = {'kind': 'expand', 'speed': 'normal', 'what': 'tab:Second'}


@pytest.fixture
def served(serve_pages):
    """The page on a real local server (the browser and the console talk HTTP); its base URL."""
    from werkzeug.serving import make_server

    def serve(extra_yaml=''):
        client = serve_pages(datasources_yaml=extra_yaml, m=PAGE)
        server = make_server('127.0.0.1', 0, client.application, threaded=True)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        return f'http://127.0.0.1:{server.server_port}/'
    servers = []
    logging.disable(logging.WARNING)
    yield serve
    for server in servers:
        server.shutdown()
    logging.disable(logging.NOTSET)


def in_the_browser(url):
    playwright = pytest.importorskip('playwright.sync_api', reason='Playwright is not installed')
    with playwright.sync_playwright() as pw:
        try:
            chromium = pw.chromium.launch()
        except Exception as exc:   # browser not downloaded
            pytest.skip(f"Playwright's Chromium is not available: {exc}")
        try:
            page = chromium.new_page()
            page.goto(url + 'm?moved=2')
            opened = page.evaluate('window.quantumMotions')
            page.locator('.q-tab-header', has_text='Second').click()
            after_tab = page.evaluate('window.quantumMotions')
            page.wait_for_timeout(400)
            settled = page.evaluate("""() => [...document.querySelectorAll('[data-motion]')].map(e => {
                const s = getComputedStyle(e); return [s.opacity, s.transform]; })""")
            return opened, after_tab, settled
        finally:
            chromium.close()


def in_the_console(url):
    from quantum.runtime.ui_console import ConsoleUI
    from textual.widgets import TabbedContent, TabPane
    from tests.console_pilot import page_loaded

    async def main():
        app = ConsoleUI(url, '/m?moved=2')
        async with app.run_test(size=(120, 60)) as pilot:
            await page_loaded(app, pilot)
            opened = list(app.motions)
            tabs = app.query_one(TabbedContent)
            tabs.active = [p for p in tabs.query(TabPane) if str(p._title) == 'Second'][0].id
            await pilot.pause()
            after_tab = list(app.motions)
            await pilot.pause(0.5)
            settled = [(w.styles.opacity, tuple(w.styles.offset)) for w in app.query('*')
                       if w.styles.opacity < 1 or any(v.value for v in w.styles.offset)]
            return opened, after_tab, settled

    return asyncio.run(main())


def test_the_motions_of_a_page_in_the_browser(served):
    # UI-19
    opened, after_tab, settled = in_the_browser(served())
    assert opened == ON_OPEN and after_tab == ON_OPEN + [TAB]
    assert settled and all(opacity == '1' and transform in ('none', 'matrix(1, 0, 0, 1, 0, 0)')
                           for opacity, transform in settled)


def test_the_same_motions_in_the_console(served):
    # UI-19
    opened, after_tab, settled = in_the_console(served())
    assert opened == ON_OPEN and after_tab == ON_OPEN + [TAB]
    assert settled == []                         # every element shown, in its place


def test_motion_off_runs_none_and_draws_the_same(served):
    # UI-19: ui.motion: off in quantum.config.yaml
    url = served('ui:\n  motion: off\n')
    opened, after_tab, _ = in_the_console(url)
    assert opened == [] and after_tab == []
    import re
    import requests
    html = requests.get(url + 'm?moved=2', timeout=10).text
    assert 'Card 2' in html and 'data-motion=' not in html and 'q-m-slide' not in html
    scripts = ''.join(requests.get(url + src.lstrip('/'), timeout=10).text
                      for src in re.findall(r'<script src="([^"]+)"', html))
    assert 'var on = false' in scripts            # the browser records nothing either


@pytest.mark.parametrize('markup,message', [
    ('<ui:window transition="expand" />', 'transition="expand">: use fade or slide'),
    ('<ui:card enter="bounce" />', 'enter="bounce">: use fade, slide or expand'),
    ('<ui:card speed="slow" />', 'speed="slow">: use fast or normal'),
])
def test_a_motion_that_is_not_one_is_a_parse_error(markup, message):
    # UI-19
    from quantum.core.parser import QuantumParser
    with pytest.raises(Exception, match=message):
        QuantumParser(use_cache=False).parse(f'<q:component name="c" {NS}>{markup}</q:component>')


def test_an_expression_that_names_no_motion_is_an_error(serve_pages):
    # UI-19: '' is no motion; anything else that is not one is the page's error
    page = (f'<q:component name="m" {NS}><q:set name="kind" value="spin" />'
            '<ui:window title="M"><ui:card title="x" enter="{kind}" /></ui:window></q:component>')
    client = serve_pages(m=page)
    assert client.get('/m').status_code == 500
