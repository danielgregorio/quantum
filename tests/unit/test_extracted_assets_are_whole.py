"""A page's extracted stylesheet is never served half written.

The server moves a page's inline <style> to static/styles-<hash>.css and links
it as soon as that file exists. It used to write the file in place, so while
one request was writing it, a second request saw it, linked it, and its
browser got an empty stylesheet: an unstyled page, cached under a name that
never changes.
"""

import threading

from tests.conformance.conftest import serve_pages  # noqa: F401 — the fixture

PAGE = ('<q:component name="p" xmlns:q="https://quantum.lang/ns">'
        '<html><head><style>.wide { width: 948px; }</style></head>'
        '<body><p class="wide">Hi</p></body></html></q:component>')


def test_a_second_request_while_the_first_writes_gets_the_whole_stylesheet(serve_pages, monkeypatch):
    client = serve_pages(p=PAGE)
    from quantum.runtime import web_html
    writing, finish = threading.Event(), threading.Event()
    first = []

    class PausedFile:
        """The first stylesheet write stops halfway until the test lets it go."""

        def __init__(self, f):
            self.f = f

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            self.f.close()

        def write(self, text):
            self.f.write(text[:3])
            self.f.flush()
            writing.set()
            finish.wait(10)
            self.f.write(text[3:])

    def open_(path, *args, **kwargs):
        f = open(path, *args, **kwargs)
        if str(path).endswith(('.css', '.tmp')) and not first:
            first.append(path)
            return PausedFile(f)
        return f

    monkeypatch.setattr(web_html, 'open', open_, raising=False)
    a = threading.Thread(target=lambda: client.get('/p'))
    a.start()
    try:
        assert writing.wait(10), 'the first request never wrote the stylesheet'
        html = client.get('/p').get_data(as_text=True)          # the second request, meanwhile
        href = html.split('href="', 1)[1].split('"', 1)[0]
        assert '.wide { width: 948px; }' in client.get(href).get_data(as_text=True)
    finally:
        finish.set()
        a.join(10)
