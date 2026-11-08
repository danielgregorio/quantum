"""`quantum package` (SPEC.md UI-22, PLAN_PLATFORMS.md Phase 5): what it carries and what the server in it does.

The whole package — Godot's export, a Python of its own, pip's libraries — is built and its program driven by
the Kanban's script in tests/package/test_package_kanban.py (CI's package job); here, the parts that need no
network: what the application carries and leaves out, the user's folder, the server's line and its end.
"""

import io
import os
import shutil
import sqlite3
import stat
import subprocess
import sys
import threading
import zipfile
from pathlib import Path

import pytest
import requests
import yaml

from quantum.runtime import package, packaged_server

APP_CONFIG = """
server:
  port: 8090
paths:
  components: ./components
  migrations: ./migrations
datasources:
  db:
    driver: sqlite
    database: ./data/notes.db
  big:
    driver: postgres
    host: ${PGHOST:-localhost}
    database: notes
llm:
  base_url: ${QUANTUM_LLM_BASE_URL:-http://localhost:11434}
api:
  title: Notes
"""

PAGE = """<q:component name="Index" xmlns:q="https://quantum.lang/ns" xmlns:ui="https://quantum.lang/ui">
  <q:query name="notes" datasource="db">SELECT text FROM notes ORDER BY id</q:query>
  <ui:window title="Notes">
    <q:loop query="notes"><ui:text>{notes.text}</ui:text></q:loop>
  </ui:window>
</q:component>"""


@pytest.fixture
def app(tmp_path):
    folder = tmp_path / 'My Notes'
    (folder / 'components').mkdir(parents=True)
    (folder / 'migrations').mkdir()
    (folder / 'data').mkdir()
    (folder / '__pycache__').mkdir()
    (folder / 'quantum.config.yaml').write_text(APP_CONFIG, encoding='utf-8')
    (folder / 'components' / 'index.q').write_text(PAGE, encoding='utf-8')
    (folder / 'migrations' / 'V001__notes.sql').write_text(
        "CREATE TABLE notes (id INTEGER PRIMARY KEY, text TEXT);\nINSERT INTO notes (text) VALUES ('first note');\n",
        encoding='utf-8')
    db = sqlite3.connect(folder / 'data' / 'notes.db')
    db.executescript("CREATE TABLE notes (id INTEGER PRIMARY KEY, text TEXT); INSERT INTO notes (text) "
                     "VALUES ('my private note');")
    db.close()
    (folder / '.quantum.pid').write_text('123')
    return folder


@pytest.fixture
def user_data(tmp_path, monkeypatch):
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path / 'xdg'))
    monkeypatch.setattr(sys, 'platform', 'linux')
    return tmp_path / 'xdg' / 'quantum'


def test_its_name_and_title(app):
    config = yaml.safe_load((app / 'quantum.config.yaml').read_text())
    assert package.app_name(app) == 'my-notes'
    assert package.app_title(app, config) == 'Notes'                  # the API's title, else the folder's
    assert package.app_title(app, {}) == 'My Notes'


def test_the_libraries_are_the_servers_and_its_drivers(app):
    config = yaml.safe_load((app / 'quantum.config.yaml').read_text())
    names = package.libraries_for(config)
    assert names[:5] == ['flask', 'pyyaml', 'sqlparse', 'requests', 'bcrypt']
    assert 'psycopg2-binary' in names and 'textual' not in names and 'gunicorn' not in names


def test_the_application_is_carried_without_its_data(app, tmp_path):
    config = yaml.safe_load((app / 'quantum.config.yaml').read_text())
    (app / 'static' / 'tui').mkdir(parents=True)              # the TUI made for the browser (--target web)
    (app / 'static' / 'tui' / 'index.wasm').write_bytes(b'\0asm')
    (app / 'static' / 'logo.png').write_bytes(b'png')
    left_out = package.copy_app(app, tmp_path / 'out', config, with_data=False)
    assert left_out == [str(Path('data') / 'notes.db')]
    assert (tmp_path / 'out' / 'components' / 'index.q').is_file()
    assert (tmp_path / 'out' / 'static' / 'logo.png').is_file() and not (tmp_path / 'out' / 'static' / 'tui').exists()
    assert not (tmp_path / 'out' / 'data' / 'notes.db').exists()
    assert not (tmp_path / 'out' / '__pycache__').exists() and not (tmp_path / 'out' / '.quantum.pid').exists()
    assert package.copy_app(app, tmp_path / 'with', config, with_data=True) == []
    assert (tmp_path / 'with' / 'data' / 'notes.db').is_file()


def test_the_users_folder_by_system(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, 'platform', 'linux')
    monkeypatch.setenv('XDG_DATA_HOME', str(tmp_path))
    assert packaged_server.data_dir('notes') == tmp_path / 'quantum' / 'notes'
    monkeypatch.setattr(sys, 'platform', 'win32')
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path / 'local'))
    assert packaged_server.data_dir('notes') == tmp_path / 'local' / 'Quantum' / 'notes'
    monkeypatch.setattr(sys, 'platform', 'darwin')
    assert packaged_server.data_dir('notes').parts[-4:] == ('Library', 'Application Support', 'Quantum', 'notes')


def test_the_users_folder_points_into_the_package(app, tmp_path):
    data = tmp_path / 'data-dir'
    config = packaged_server.prepare(app, data)
    written = yaml.safe_load((data / 'quantum.config.yaml').read_text())
    assert written['paths']['components'] == (app / 'components').resolve().as_posix()
    assert written['paths']['migrations'] == (app / 'migrations').resolve().as_posix()
    assert 'static' not in written['paths']                  # the package has none: the user's folder keeps it
    assert written['llm']['base_url'] == '${QUANTUM_LLM_BASE_URL:-http://localhost:11434}'   # read at each start
    assert written['datasources']['db']['database'] == './data/notes.db'                    # the user's
    # a database the package carries is copied once, never over the user's
    assert (data / 'data' / 'notes.db').is_file() and config['api']['title'] == 'Notes'
    (data / 'data' / 'notes.db').write_bytes(b'mine')
    packaged_server.prepare(app, data)
    assert (data / 'data' / 'notes.db').read_bytes() == b'mine'


def test_the_server_says_where_it_is_and_ends_with_its_input(app, tmp_path, user_data):
    (app / 'data' / 'notes.db').unlink()              # as a package carries it: the migrations make it
    out, (reader, writer) = io.StringIO(), os.pipe()
    stdin = os.fdopen(reader, 'r')
    done = threading.Event()

    def run():
        try:
            packaged_server.serve(app, 'my-notes', out=out, stdin=stdin)
        finally:
            done.set()

    cwd = os.getcwd()
    thread = threading.Thread(target=run, daemon=True)
    try:
        thread.start()
        for _ in range(200):
            if out.getvalue():
                break
            done.wait(0.05)
        line = out.getvalue()
        assert line.startswith(packaged_server.READY) and line.endswith('/\n'), line
        page = requests.get(line[len(packaged_server.READY):].strip(), timeout=10)
        assert page.status_code == 200 and 'first note' in page.text and 'my private note' not in page.text
        assert (user_data / 'my-notes' / 'data' / 'notes.db').is_file()
        os.close(writer)                                # the client goes: the server ends
        assert done.wait(10)
    finally:
        os.chdir(cwd)


def test_a_server_that_cannot_start_says_why(tmp_path):
    # the client shows the line rather than wait for one that never comes; the rest is in its log
    broken = tmp_path / 'broken'
    broken.mkdir()
    done = subprocess.run([sys.executable, '-m', 'quantum.runtime.packaged_server', '--app', str(broken),
                           '--name', 'broken'], capture_output=True, text=True, timeout=60,
                          env={**os.environ, 'XDG_DATA_HOME': str(tmp_path / 'xdg')})
    assert done.returncode == 1 and done.stderr == ''
    assert done.stdout.startswith(packaged_server.ERROR) and 'quantum.config.yaml' in done.stdout
    log = tmp_path / 'xdg' / 'quantum' / 'broken' / 'server.log'
    assert str(log) in done.stdout and 'Traceback' in log.read_text()


def test_the_archive_keeps_programs_runnable_and_links_as_links(tmp_path):
    folder = tmp_path / 'notes'
    (folder / 'bin').mkdir(parents=True)
    program = folder / 'bin' / 'python3.12'
    program.write_text('#!/bin/sh\n')
    program.chmod(0o755)
    (folder / 'bin' / 'python3').symlink_to('python3.12')
    package._zip(folder, tmp_path / 'notes.zip')
    with zipfile.ZipFile(tmp_path / 'notes.zip') as z:
        infos = {i.filename: i for i in z.infolist()}
        assert stat.S_IMODE(infos['notes/bin/python3.12'].external_attr >> 16) == 0o755
        link = infos['notes/bin/python3']
        assert stat.S_ISLNK(link.external_attr >> 16) and z.read(link) == b'python3.12'


def test_what_cannot_be_packaged_says_so(tmp_path):
    with pytest.raises(package.PackageError, match='quantum.config.yaml'):
        package.build(tmp_path, progress=lambda line: None)
    with pytest.raises(package.PackageError, match='the TUI .* or a window'):
        package.build(tmp_path, on='phone', progress=lambda line: None)
    with pytest.raises(package.PackageError, match="Qt WebEngine, about 550 MB; Linux's package is the TUI"):
        package.build(tmp_path, on='desktop', target='linux', progress=lambda line: None)
    with pytest.raises(package.PackageError, match='linux, windows, macos, web'):
        package.build(tmp_path, target='beos', progress=lambda line: None)


def test_the_desktops_program_checks_itself_with_no_window(app, tmp_path):
    # QUANTUM_PACKAGE_CHECK: the server starts in the program's process, the first page is asked, and what
    # happened is written down (CI's Windows and macOS runners run the real packages so)
    import json
    server = tmp_path / 'package' / 'server'
    (server / 'python' / 'bin').mkdir(parents=True)
    shutil.copytree(app, server / 'app')
    (server / 'app' / 'data' / 'notes.db').unlink()
    (server / 'package.json').write_text(json.dumps({'name': 'notes', 'title': 'Notes', 'page': '/'}))
    result = tmp_path / 'check.json'
    code = ("import sys; sys.executable = sys.argv[1]\n"
            "from quantum.runtime import packaged_desktop as d\n"
            "d.window_library = lambda: 'webview.platforms.test'\n"
            "raise SystemExit(d.main())")
    done = subprocess.run([sys.executable, '-c', code, str(server / 'python' / 'bin' / 'python3')], timeout=60,
                          capture_output=True, text=True,
                          env={**os.environ, 'QUANTUM_PACKAGE_CHECK': str(result), 'XDG_DATA_HOME': str(tmp_path / 'xdg')})
    said = json.loads(result.read_text())
    assert done.returncode == 0, said
    assert said['status'] == 200 and said['title'] == 'Notes' and said['window'] == 'webview.platforms.test'
    assert (tmp_path / 'xdg' / 'quantum' / 'notes' / 'data' / 'notes.db').is_file()
    assert 'GET /' in (tmp_path / 'xdg' / 'quantum' / 'notes' / 'server.log').read_text()


def test_the_tui_for_the_browser_goes_into_the_applications_static_folder(app, tmp_path, monkeypatch, capsys):
    # UI-22, --target web: the application's own server serves it (/static/tui/), and nothing else is carried;
    # Godot's export is tests/package/test_tui_in_browser.py's
    def export(target, title, name, out, progress):
        assert (target, title, name) == ('web', 'Notes', 'my-notes')
        out.mkdir(parents=True, exist_ok=True)
        (out / 'index.html').write_text('<canvas>')
        (out / 'index.wasm').write_bytes(b'\0asm')
        return out / 'index.html'

    monkeypatch.setattr(package, 'export_tui', export)
    made = package.build(app, target='web', progress=lambda line: None)
    assert made.folder == (app / 'static' / 'tui').resolve() and made.path == made.folder / 'index.html'
    assert made.size == len('<canvas>') + 4
    assert not (app / 'dist').exists()                          # no server, no Python, no archive
    assert package.web_folder(app, {'paths': {'static': './public'}}) == (app / 'public' / 'tui').resolve()
    package.main(type('Args', (), {'app': str(app), 'on': 'tui', 'target': 'web', 'out': None, 'with_data': False}))
    assert capsys.readouterr().out.rstrip().endswith('the application serves it at /static/tui/index.html')
    elsewhere = package.build(app, target='web', out=tmp_path / 'elsewhere', progress=lambda line: None)
    assert elsewhere.folder == (tmp_path / 'elsewhere').resolve()


def test_a_window_in_a_browser_says_the_web_is_the_tuis(tmp_path):
    with pytest.raises(package.PackageError, match='--target web puts the TUI there'):
        package.build(tmp_path, on='desktop', target='web', progress=lambda line: None)


def test_a_hosted_applications_address_is_checked():
    # Phase 6: --server is where the client's program asks for the pages
    assert package.server_url('https://kanban.example.com/') == 'https://kanban.example.com'
    assert package.server_url('http://127.0.0.1:8095') == 'http://127.0.0.1:8095'
    assert package.server_url('https://example.com/apps/kanban/') == 'https://example.com/apps/kanban'
    for wrong in ('kanban.example.com', 'ftp://example.com', 'https://', 'https://example.com/?a=1'):
        with pytest.raises(package.PackageError, match='the address of the application'):
            package.server_url(wrong)


def test_a_client_in_a_browser_is_the_hosted_applications_own(tmp_path):
    with pytest.raises(package.PackageError, match='asks the server that serves it'):
        package.build(tmp_path, target='web', server='https://example.com', progress=lambda line: None)


def test_the_clients_tui_names_its_server(app, tmp_path, monkeypatch):
    # the exported project carries the address (project.godot's quantum/server) and the colours; nothing beside it
    from quantum.runtime import godot_bin, godot_export
    seen = {}

    def export(project, preset, target, godot, options=None, include=''):
        seen['settings'] = (project / 'project.godot').read_text()
        target.write_bytes(b'\x7fELF')
        return target

    monkeypatch.setattr(godot_export, 'export_project', export)
    monkeypatch.setattr(godot_export, 'have_templates', lambda preset=None: True)
    monkeypatch.setattr(godot_bin, 'ensure_godot', lambda **kw: Path('/bin/true'))
    made = package.build(app, target='linux', out=tmp_path / 'dist', server='https://notes.example.com/',
                         progress=lambda line: None)
    assert made.path.name == 'my-notes-linux-client.tar.gz'
    assert '[quantum]' in seen['settings'] and 'server="https://notes.example.com"' in seen['settings']
    assert 'tokens="{\\"primary\\"' in seen['settings']
    assert sorted(p.name for p in made.folder.iterdir()) == ['my-notes']     # the program alone
    assert made.libraries == {} and made.left_out == []


def test_the_desktops_client_needs_none_of_the_servers_libraries(tmp_path):
    # Phase 6: a hosted application's window carries the window's libraries and requests, not the server's
    # (PyYAML, Flask): its program must start without them (it did not, on Windows and macOS)
    import http.server
    import json
    server = tmp_path / 'package' / 'server'
    (server / 'python' / 'bin').mkdir(parents=True)

    class Page(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'<html><head><title>Hosted Notes</title></head></html>')

        def log_message(self, *args):
            pass

    hosted = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Page)
    threading.Thread(target=hosted.serve_forever, daemon=True).start()
    try:
        (server / 'package.json').write_text(json.dumps({
            'name': 'notes', 'title': 'Notes', 'page': '/', 'server': f'http://127.0.0.1:{hosted.server_port}'}))
        result = tmp_path / 'check.json'
        code = ("import sys; sys.executable = sys.argv[1]\n"
                "sys.modules['yaml'] = None; sys.modules['flask'] = None; sys.modules['werkzeug'] = None\n"
                "from quantum.runtime import packaged_desktop as d\n"
                "d.window_library = lambda: 'webview.platforms.test'\n"
                "raise SystemExit(d.main())")
        done = subprocess.run([sys.executable, '-c', code, str(server / 'python' / 'bin' / 'python3')], timeout=60,
                              capture_output=True, text=True,
                              env={**os.environ, 'QUANTUM_PACKAGE_CHECK': str(result),
                                   'XDG_DATA_HOME': str(tmp_path / 'xdg')})
        assert result.is_file(), (done.stdout, done.stderr,
                                  (tmp_path / 'xdg' / 'quantum' / 'notes' / 'server.log').read_text())
        said = json.loads(result.read_text())
        assert done.returncode == 0 and said['status'] == 200 and said['title'] == 'Hosted Notes', said
    finally:
        hosted.shutdown()
