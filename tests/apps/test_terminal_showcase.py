"""projects/quantum-terminal: a page that shows four terminal apps and offers them for download.

The terminal engine (`q:application type="terminal"`) is Laboratory; the page
itself is an ordinary page. The download links pointed to /terminal/static/…,
the path the showcase had on an old deployment, and answered 404 on
`quantum start`. This serves the project, follows each download link and
checks the file it gets is Python that compiles.
"""

import logging
import re
import shutil
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[2] / 'projects' / 'quantum-terminal'


@pytest.fixture
def client(tmp_path, monkeypatch):
    app = tmp_path / 'quantum-terminal'
    shutil.copytree(APP, app)
    monkeypatch.chdir(app)
    from quantum.runtime.web_server import QuantumWebServer
    logging.disable(logging.WARNING)
    yield QuantumWebServer(str(app / 'quantum.config.yaml')).app.test_client()
    logging.disable(logging.NOTSET)


def test_the_page_and_every_download(client):
    page = client.get('/')
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert 'Download .py' in html
    downloads = re.findall(r'href="(/static/[\w-]+\.py)"', html)
    assert len(downloads) == 4, downloads
    for url in downloads:
        response = client.get(url)
        assert response.status_code == 200, url
        compile(response.get_data(as_text=True), url, 'exec')
