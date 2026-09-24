"""Conformance: answers that arrive as they are written (M5, SPEC IA-7).

No model server here: the page, the token rules and the failure path are what
is specified in CI. The streamed text itself is tested live (tests/live_ai).
"""

import asyncio
import logging
import re
import threading

import pytest

NS = 'xmlns:q="https://quantum.lang/ns" xmlns:ui="https://quantum.lang/ui"'

PAGE = (f'<q:component name="a" {NS}>'
        '<q:llm name="answer" model="phi3" stream="true" timeout="5">'
        '<q:message role="user">hello</q:message></q:llm>'
        '<ui:window title="A"><ui:stream for="answer"/></ui:window></q:component>')


@pytest.fixture(autouse=True)
def no_model_server(monkeypatch):
    monkeypatch.setenv('QUANTUM_LLM_BASE_URL', 'http://127.0.0.1:9')


def stream_url(html):
    return re.search(r'data-q-stream="([^"]+)"', html).group(1)


def test_the_page_renders_without_waiting_for_the_model(serve_pages):
    # IA-7
    html = serve_pages(a=PAGE).get('/a').get_data(as_text=True)
    assert re.search(r'data-q-stream="/_stream/[\w-]{20,}"', html)
    assert 'aria-live="polite"' in html
    assert re.search(r'<noscript>\s*<a href="/_stream/', html)            # without JavaScript: a link
    assert 'q-stream' in html


def test_a_failure_while_streaming_is_an_error_not_part_of_the_answer(serve_pages):
    # IA-7
    from quantum.runtime.llm_stream import ERROR_MARK
    c = serve_pages(a=PAGE)
    body = c.get(stream_url(c.get('/a').get_data(as_text=True))).get_data(as_text=True)
    assert body.startswith(ERROR_MARK) and 'Cannot connect' in body


def test_a_token_is_read_once_and_only_by_its_session(serve_pages):
    # IA-7
    c = serve_pages(a=PAGE)
    url = stream_url(c.get('/a').get_data(as_text=True))
    assert c.application.test_client().get(url).status_code == 404          # another visitor
    assert c.get(url).status_code == 200
    assert c.get(url).status_code == 404                                     # once
    assert c.get('/_stream/not-a-token').status_code == 404


def test_without_stream_ui_stream_shows_the_value(serve_pages):
    # IA-7: the same element shows a finished answer (here: a handled failure, value '')
    page = PAGE.replace('stream="true"', 'onerror="continue"')
    html = serve_pages(a=page).get('/a').get_data(as_text=True)
    assert 'data-q-stream' not in html and 'q-stream-done' in html


def test_ui_stream_for_an_llm_that_is_not_there_is_an_error(serve_pages, caplog):
    # IA-7
    c = serve_pages(a=PAGE.replace('for="answer"', 'for="missing"'))
    with caplog.at_level(logging.ERROR, logger='quantum.server'):
        assert c.get('/a').status_code == 500
    assert any('there is no q:llm named "missing"' in r.getMessage() for r in caplog.records)


def test_outside_a_web_request_the_llm_answers_normally():
    # IA-7: `quantum run` has nobody to read a stream — it waits for the model
    from quantum.core.parser import QuantumParser
    from quantum.runtime.component import ComponentRuntime
    with pytest.raises(Exception, match='Cannot connect'):
        ComponentRuntime(config={}).execute_component(QuantumParser().parse(PAGE), {})


def test_the_console_reads_the_stream_and_shows_the_error(tmp_path, monkeypatch):
    # IA-7 + UI-3
    from textual.widgets import Static
    from werkzeug.serving import make_server
    from quantum.runtime.ui_console import ConsoleUI
    from quantum.runtime.web_server import QuantumWebServer
    (tmp_path / 'components').mkdir()
    (tmp_path / 'components' / 'a.q').write_text(PAGE, encoding='utf-8')
    (tmp_path / 'quantum.config.yaml').write_text('paths: {components: ./components}\n', encoding='utf-8')
    monkeypatch.chdir(tmp_path)
    logging.disable(logging.WARNING)
    server = make_server('127.0.0.1', 0, QuantumWebServer('quantum.config.yaml').app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    async def main():
        app = ConsoleUI(f'http://127.0.0.1:{server.server_port}/', '/a')
        async with app.run_test() as pilot:
            for _ in range(100):
                await pilot.pause(0.05)
                texts = [str(w.render()) for w in app.query(Static)]
                if any('Cannot connect' in t for t in texts):
                    return texts
            return [str(w.render()) for w in app.query(Static)]

    try:
        texts = asyncio.run(main())
    finally:
        server.shutdown()
        logging.disable(logging.NOTSET)
    assert any('Cannot connect' in t for t in texts)
