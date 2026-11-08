"""The desktop's package program (SPEC.md UI-22, PLAN_PLATFORMS.md Phase 5b): the application's server in this
process and its pages in a window of their own (pywebview: WebView2 on Windows, WKWebView on a Mac), as
`quantum desktop` does — run by the package's own Python.

A package made with `quantum package <app> --on desktop` starts this from its program (Kanban.exe on Windows, a
launcher that runs its Python; Kanban.app on a Mac, a script that does). The package's server folder is found
from the Python running it (the folder above it that holds package.json); what the application writes goes to the
user's folder (quantum.runtime.packaged_server), and so does everything this process prints (server.log), since a
window's Python has no standard output.

A package made with --server (a hosted application's client) has no app folder: package.json names the server,
and the window opens on it.

QUANTUM_PACKAGE_CHECK=<file> makes no window: the server starts, the first page is asked, the window's library is
imported, and what happened is written to that file as JSON, for a machine with no one at it (CI).
"""

from __future__ import annotations

import html
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional


def server_folder() -> Path:
    """The package's server folder: the folder above this Python that holds package.json."""
    for folder in Path(sys.executable).resolve().parents:
        if (folder / 'package.json').is_file():
            return folder
    raise RuntimeError(f'no package.json above {sys.executable}: this is not a package made by quantum package')


def window_library() -> str:
    """The module of pywebview's window for this system, imported (a missing piece shows here, not later)."""
    import importlib
    name = {'win32': 'webview.platforms.edgechromium', 'darwin': 'webview.platforms.cocoa'}.get(
        sys.platform, 'webview.platforms.qt')
    importlib.import_module(name)
    return name


def check(result: Path, url: str, page: str, started: float) -> int:
    """No window: the first page and the window's library, said in `result` (JSON)."""
    import requests
    said = {'url': url}
    try:
        answer = requests.get(url.rstrip('/') + page, timeout=30)
        title = answer.text.split('<title>', 1)[-1].split('</title>', 1)[0] if '<title>' in answer.text else ''
        said.update(status=answer.status_code, first_page=round(time.monotonic() - started, 3),
                    title=' '.join(html.unescape(title).split()))
        said['window'] = window_library()
    except Exception as exc:
        said['error'] = f'{type(exc).__name__}: {exc}'
    result.write_text(json.dumps(said), encoding='utf-8')
    return 0 if said.get('status') == 200 and 'error' not in said else 1


def main(argv: Optional[list] = None) -> int:
    started = time.monotonic()
    from quantum.runtime.packaged_server import data_dir, log_to, start
    server = server_folder()
    conf = json.loads((server / 'package.json').read_text(encoding='utf-8'))
    name, title, page = conf['name'], conf.get('title') or conf['name'], conf.get('page') or '/'
    log_to(data_dir(name) / 'server.log')
    wanted = os.environ.get('QUANTUM_PACKAGE_CHECK')
    if conf.get('server'):
        # a hosted application's window (Phase 6): no server here, the window asks that one
        url = conf['server'].rstrip('/') + '/'
        if wanted:
            return check(Path(wanted), url, page, started)
        import webview
        from quantum.runtime.ui_desktop import open_window
        open_window(webview, url.rstrip('/') + page, title=title)
        webview.start(private_mode=True)
        return 0
    try:
        httpd, url = start(server / 'app', name)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        if wanted:
            Path(wanted).write_text(json.dumps({'error': f'{type(exc).__name__}: {exc}'}), encoding='utf-8')
        return 1
    try:
        if wanted:
            return check(Path(wanted), url, page, started)
        import webview
        from quantum.runtime.ui_desktop import open_window
        open_window(webview, url.rstrip('/') + page, title=title)
        webview.start(private_mode=True)         # until the window closes; the server goes with it
        return 0
    finally:
        httpd.shutdown()


if __name__ == '__main__':
    raise SystemExit(main())
