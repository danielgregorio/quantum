"""projects/tarefas on the desktop (UI-4): the same .q in a window, with no code of its own.

`quantum desktop` starts the application's server and opens a window
(pywebview) on it. Here the window is fake — CI has no screen — but the server
is the real one: during `start`, the test does what the window would do.
"""

import re
import shutil
import sys
from pathlib import Path

import pytest
import requests

TAREFAS = Path(__file__).resolve().parents[2] / "projects" / "tarefas"


class Event:
    def __init__(self):
        self.listeners = []

    def __iadd__(self, function):
        self.listeners.append(function)
        return self

    def fire(self):
        for function in self.listeners:
            function()


class FakeWindow:
    def __init__(self, title, url, **options):
        self.title, self.url, self.options = title, url, options
        self.events = type("Events", (), {})()
        self.events.loaded = Event()
        self.document = ""

    def evaluate_js(self, code):
        assert code == "document.title"
        # Like the browser: document.title joins and trims the whitespace.
        return " ".join(re.search(r"<title>(.*?)</title>", self.document, re.S).group(1).split())

    def set_title(self, title):
        self.title = title


class FakeWebview:
    """What the launcher uses from pywebview; `start` runs the script with the server up."""

    def __init__(self, script):
        self.script = script
        self.windows = []
        self.start_options = None

    def create_window(self, title, url, **options):
        self.windows.append(FakeWindow(title, url, **options))
        return self.windows[-1]

    def start(self, **options):
        self.start_options = options
        self.script(self.windows[0])


@pytest.fixture
def project(tmp_path, monkeypatch):
    target = tmp_path / "tarefas"
    shutil.copytree(TAREFAS, target, ignore=shutil.ignore_patterns("data", "__pycache__"))
    monkeypatch.chdir(target)
    from quantum.cli.migrations import MigrationRunner
    MigrationRunner(target).up()
    return target


def test_opens_the_window_on_the_application_server(project):
    # UI-4: the window opens the served page; clicks and forms are the web's q:actions
    from quantum.runtime.ui_desktop import run_desktop
    seen = {}

    def script(window):
        http = requests.Session()
        page = http.get(window.url, timeout=10)
        seen["status"] = page.status_code
        window.document = page.text
        window.events.loaded.fire()
        assert "Total: 3" in page.text and "Ler o guia do Quantum" in page.text
        created = http.post(window.url, data={"action": "criar", "titulo": "Criada na janela"}, timeout=10)
        seen["after"] = created.text

    webview = FakeWebview(script)
    assert run_desktop(str(project / "quantum.config.yaml"), webview=webview) == 0
    window = webview.windows[0]
    assert seen["status"] == 200
    assert "Criada: Criada na janela" in seen["after"] and "Total: 4" in seen["after"]
    assert window.url.startswith("http://127.0.0.1:") and window.url.endswith("/")
    assert window.title == "Tarefas"                   # the title follows the page's <title>
    assert window.options["width"] == 1024 and window.options["height"] == 720
    assert webview.start_options == {"private_mode": True}


def test_the_server_stops_when_the_window_closes(project):
    # UI-4: closing the window ends the application's server
    from quantum.runtime.ui_desktop import run_desktop
    urls = []
    run_desktop(str(project / "quantum.config.yaml"), webview=FakeWebview(lambda w: urls.append(w.url)))
    with pytest.raises(requests.ConnectionError):
        requests.get(urls[0], timeout=2)


def test_opens_on_the_page_asked_for(project):
    # UI-4: `quantum desktop /?filtro=feitas` opens on that page
    from quantum.runtime.ui_desktop import run_desktop
    seen = {}

    def script(window):
        seen["url"] = window.url
        seen["text"] = requests.get(window.url, timeout=10).text

    run_desktop(str(project / "quantum.config.yaml"), "/?filtro=feitas", webview=FakeWebview(script))
    assert seen["url"].endswith("/?filtro=feitas")
    assert "Escrever a primeira página" not in seen["text"]


def test_without_pywebview_it_says_how_to_install(project, monkeypatch, capsys):
    # UI-4: without the [desktop] extra, an error that says what to install — not an ImportError
    from quantum.runtime.ui_desktop import run_desktop
    monkeypatch.setitem(sys.modules, "webview", None)
    assert run_desktop(str(project / "quantum.config.yaml")) == 1
    assert 'pip install "quantum-framework[desktop]"' in capsys.readouterr().err


def test_the_cli_command(project, monkeypatch):
    # UI-4: `quantum desktop` exists and passes on the page, the config and the size
    import quantum.runtime.ui_desktop as ui_desktop
    from quantum.cli import runner
    calls = []
    monkeypatch.setattr(ui_desktop, "run_desktop", lambda *a, **k: calls.append((a, k)) or 0)
    monkeypatch.setattr(sys, "argv", ["quantum", "desktop", "/sobre", "--width", "800"])
    with pytest.raises(SystemExit) as exit_:
        runner.main()
    assert exit_.value.code == 0
    assert calls == [(("quantum.config.yaml", "/sobre"), {"width": 800, "height": 720})]
