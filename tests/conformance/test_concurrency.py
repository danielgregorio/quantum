"""Conformance: each request runs in its own runtime (ACT-10)."""

import re
import threading

NS = 'xmlns:q="https://quantum.lang/ns"'


def page(name, value):
    return (f'<q:component name="{name}" {NS}>'
            f'<q:function name="who"><q:return value="{value}"/></q:function>'
            '<q:action name="a" method="POST"><q:set name="session.saw" value="{who()}"/>'
            '<q:redirect url="/see"/></q:action><p>x</p></q:component>')


SEE = f'<q:component name="see" {NS}><p>[{{session.saw}}]</p></q:component>'


def seen(client):
    return re.search(r'\[(.*?)\]', client.get('/see').get_data(as_text=True)).group(1)


def test_a_page_function_inside_the_action(serve_pages):
    # ACT-10 (before: 500 — the action ran in a runtime that never registered the page's functions)
    c = serve_pages(pa=page('pa', 'A'), pb=page('pb', 'B'), see=SEE)
    assert c.post('/pa', data={}).status_code == 302 and seen(c) == 'A'
    assert c.post('/pb', data={}).status_code == 302 and seen(c) == 'B'
    assert c.post('/pa', data={}).status_code == 302 and seen(c) == 'A'


def test_simultaneous_requests_do_not_mix(serve_pages):
    # ACT-10: two pages with a function of the same name, in several threads at once
    app = serve_pages(pa=page('pa', 'A'), pb=page('pb', 'B'), see=SEE).application
    wrong = []

    def run(name, expected):
        client = app.test_client()
        for _ in range(30):
            client.post('/' + name, data={})
            value = seen(client)
            if value != expected:
                wrong.append((name, value))

    threads = [threading.Thread(target=run, args=pair) for pair in [('pa', 'A'), ('pb', 'B')] * 4]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert wrong == []
