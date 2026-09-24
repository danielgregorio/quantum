"""DEV-4: `quantum start --hot-reload`, end to end.

The page script, the file watcher and the WebSocket server all existed, but
the CLI had no --hot-reload and nothing started the watcher: the documented
command did not exist, and a page with the script connected to nothing.
"""

import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
PAGE = '<q:component name="index" xmlns:q="https://quantum.lang/ns"><p>{text}</p></q:component>'


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def get(url):
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            return response.read().decode('utf-8')
    except OSError:
        return None


def kill_tree(proc):
    """Only the process this test started, and its children."""
    if proc.poll() is not None:
        return
    if os.name == 'nt':
        subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)], capture_output=True)
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    proc.wait(timeout=10)


@pytest.fixture
def project(tmp_path):
    (tmp_path / 'components').mkdir()
    (tmp_path / 'static').mkdir()
    (tmp_path / 'components' / 'index.q').write_text(PAGE.format(text='FIRST'), encoding='utf-8')
    (tmp_path / 'static' / 'site.css').write_text('p { color: black; }', encoding='utf-8')
    port = free_port()
    (tmp_path / 'quantum.config.yaml').write_text(yaml.safe_dump({
        'server': {'port': port, 'host': '127.0.0.1', 'reload': False, 'debug': False},
        'paths': {'components': './components', 'static': './static'},
        'logging': {'level': 'ERROR', 'console': False, 'file': False},
    }), encoding='utf-8')
    return tmp_path, port


def start(folder, *flags):
    return subprocess.Popen(
        [sys.executable, '-m', 'quantum.cli.runner', 'start', *flags],
        cwd=folder, env=dict(os.environ, PYTHONPATH=str(REPO)),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=(os.name != 'nt'),
    )


def wait_for_page(proc, url, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        assert proc.poll() is None, f'the server exited with {proc.returncode}'
        html = get(url)
        if html is not None:
            return html
        time.sleep(0.3)
    pytest.fail('the server did not answer in time')


def next_message(ws, wanted, timeout=15):
    """The next message of type `wanted` (others, like 'connected', are skipped)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            data = json.loads(ws.recv(timeout=max(0.1, deadline - time.monotonic())))
        except TimeoutError:
            break
        if data.get('type') == wanted:
            return data
    pytest.fail(f'no {wanted!r} message within {timeout}s')


def test_a_change_reloads_the_open_pages(project):
    # DEV-4
    from websockets.sync.client import connect

    folder, port = project
    ws_port = free_port()
    proc = start(folder, '--hot-reload', '--hot-reload-port', str(ws_port))
    try:
        html = wait_for_page(proc, f'http://127.0.0.1:{port}/')
        assert 'FIRST' in html
        assert 'Quantum Hot Reload Client' in html
        # The server moves inline scripts to a static file; the port is there.
        scripts = ''.join(get(f'http://127.0.0.1:{port}{src}') or ''
                          for src in re.findall(r'<script src="(/static/[^"]+\.js)"', html))
        assert f'port: {ws_port}' in scripts

        with connect(f'ws://127.0.0.1:{ws_port}', open_timeout=10) as ws:
            next_message(ws, 'connected')

            (folder / 'components' / 'index.q').write_text(PAGE.format(text='SECOND'), encoding='utf-8')
            message = next_message(ws, 'reload')
            assert message['reloadType'] == 'full'
            assert any(f['path'].endswith('index.q') for f in message['files'])
            assert 'SECOND' in get(f'http://127.0.0.1:{port}/')

            # A .q that no longer parses: the error, not a reload.
            (folder / 'components' / 'index.q').write_text('<q:component name="index">', encoding='utf-8')
            error = next_message(ws, 'error')
            assert error['error']['file'].endswith('index.q')

            # Only CSS: the styles, not the page.
            (folder / 'static' / 'site.css').write_text('p { color: red; }', encoding='utf-8')
            assert next_message(ws, 'reload')['reloadType'] == 'css'
    finally:
        kill_tree(proc)


def test_without_the_flag_nothing_is_added_to_the_page(project):
    # DEV-4
    folder, port = project
    proc = start(folder)
    try:
        html = wait_for_page(proc, f'http://127.0.0.1:{port}/')
        assert 'FIRST' in html
        assert 'Hot Reload' not in html
    finally:
        kill_tree(proc)
