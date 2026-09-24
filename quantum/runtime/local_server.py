"""The application's server on a free local port, for renderers that are not a browser.

`quantum console` (UI-3) and `quantum desktop` (UI-4) open the whole
application — pages, actions, sessions — through the same server that
`quantum start` runs. Only the drawing differs; nothing of a page's logic runs
anywhere else.
"""

import logging
import threading
from contextlib import contextmanager
from typing import Iterator


@contextmanager
def local_server(config_path: str = 'quantum.config.yaml') -> Iterator[str]:
    """Serve the application on 127.0.0.1 (a free port) in a thread; yield its base URL."""
    from werkzeug.serving import make_server
    from quantum.runtime.web_server import QuantumWebServer

    logging.getLogger('werkzeug').setLevel(logging.ERROR)
    app = QuantumWebServer(config_path).app
    server = make_server('127.0.0.1', 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield f'http://127.0.0.1:{server.server_port}/'
    finally:
        server.shutdown()
