"""The desktop renderer: a Quantum application in its own window (UI-4).

`quantum desktop` starts the application's server on a free local port and
opens a native window (pywebview) on it. The window is a browser without the
browser's chrome: pages, q:action, sessions and UI-2 layout are exactly the
web's, because it is the web's server that answers. Nothing of a page's logic
is translated.
"""

import sys
from urllib.parse import urljoin

INSTALL_HINT = 'pip install "quantum-framework[desktop]"'

DEFAULT_WIDTH = 1024
DEFAULT_HEIGHT = 720


def _webview():
    try:
        import webview
    except ImportError:
        return None
    return webview


def open_window(webview, url: str, title: str = 'Quantum',
                width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT):
    """Create the window on `url`; its title follows each page's <title>."""
    window = webview.create_window(title, url, width=width, height=height, min_size=(360, 480))

    def on_loaded():
        page_title = window.evaluate_js('document.title')
        if page_title:
            window.set_title(str(page_title))

    window.events.loaded += on_loaded
    return window


def run_desktop(config_path: str = 'quantum.config.yaml', path: str = '/',
                width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT,
                webview=None) -> int:
    """`quantum desktop`: the application's server in a thread, the pages in a window."""
    webview = webview or _webview()
    if webview is None:
        print(f'[ERROR] quantum desktop needs pywebview: {INSTALL_HINT}', file=sys.stderr)
        return 1
    from quantum.runtime.local_server import local_server

    with local_server(config_path) as base_url:
        open_window(webview, urljoin(base_url, path.lstrip('/')), width=width, height=height)
        # Blocks until the window closes; the server stops with it.
        webview.start(private_mode=True)
    return 0

