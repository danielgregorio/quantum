"""The pixel renderer: a Quantum page on the Hive's screen, the machine's console (UI-15).

`quantum pixel` starts the application's server in this process, as
`quantum console` does, and brings each page to hive-screen (the Quantum OS
daemon that draws the Hive's pixel-art scene on the console) over its pixel
socket. The daemon lays the page's view tree (quantum/runtime/ui_view.py)
out in cells of its font, draws it over the scene, and drives it with the
keyboard alone; what the user does comes back as events — a button
clicked, a form submitted with what the user left in it, a link, a search
field after a pause — and this process sends the same q:action posts a
browser sends, with a cookie jar, so login, validation, flash and redirects
are exactly the web's. Nothing of the page's logic runs anywhere else.

The protocol is JSON lines both ways (os/crates/hive-screen/src/pixel.rs):
`{"op":"show","page":{...}}` carries the whole page each time it changes;
`{"event":...}` lines come back. Esc on the console closes the page, and
this process ends with it.
"""

import json
import socket
import sys
from typing import Dict, Optional
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit

import requests

VIEW = 'application/vnd.quantum.view+json'
DEFAULT_SOCKET = '/run/hive-screen/pixel.sock'


def number_nodes(view: list) -> int:
    """Gives every node of a view tree an `id`, in document order (the cells
    of a table included): the screen names the element an event is about by it."""
    next_id = 1

    def walk(node: dict) -> None:
        nonlocal next_id
        node['id'] = next_id
        next_id += 1
        for child in node.get('children') or []:
            walk(child)
        for row in node.get('rows') or []:
            for cell in row:
                for item in cell:
                    walk(item)

    for node in view:
        walk(node)
    return next_id - 1


# What hive-screen last said of itself (its `status` event: the level, the
# cores, the keyboard, what a frame costs), for a page that asks (the Settings
# app's Screen tab); None until the screen said, or when the page is not on it.
_SCREEN_STATUS: Optional[dict] = None


def screen_status() -> Optional[dict]:
    """What the screen said of itself to this process, or None off the screen."""
    return dict(_SCREEN_STATUS) if _SCREEN_STATUS is not None else None


class PixelClient:
    """One page's runtime on the screen: fetches pages, shows them, answers events."""

    def __init__(self, base_url: str, path: str = '/', socket_path: str = DEFAULT_SOCKET,
                 log=None):
        self.base_url = base_url
        self.path = path
        self.socket_path = socket_path
        self.http = requests.Session()
        self.sock: Optional[socket.socket] = None
        self.reader = None
        self.pages_shown = 0
        self.log = log or (lambda line: print(line, file=sys.stderr))

    # -- the screen -----------------------------------------------------------

    def connect(self) -> None:
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(self.socket_path)
        self.reader = self.sock.makefile('r', encoding='utf-8')

    def send(self, request: dict) -> None:
        assert self.sock is not None
        self.sock.sendall((json.dumps(request, ensure_ascii=False) + '\n').encode('utf-8'))

    def show(self, page: dict) -> None:
        number_nodes(page.get('view') or [])
        self.send({'op': 'show', 'page': page})
        self.pages_shown += 1

    def close(self) -> None:
        if self.sock is None:
            return
        try:
            self.send({'op': 'close'})
        except OSError:
            pass
        try:
            self.sock.close()
        finally:
            self.sock = None

    # -- talking to the page --------------------------------------------------

    def fetch(self, method: str, path: str, data: Optional[dict] = None) -> dict:
        url = urljoin(self.base_url, path)
        response = self.http.request(method, url, data=data, allow_redirects=True,
                                     headers={'Accept': VIEW, 'Referer': urljoin(self.base_url, self.path)},
                                     timeout=30)
        if response.headers.get('Content-Type', '').startswith(VIEW):
            self.path = response.url[len(self.base_url.rstrip('/')):] or '/'
            return response.json()
        # An error page, a 400 from an unknown action: show it as it is.
        return {'title': str(response.status_code), 'flash': f'{response.status_code} {response.reason}',
                'flashType': 'error', 'view': []}

    def load(self, path: str, method: str = 'GET', data: Optional[dict] = None) -> None:
        self.show(self.fetch(method, path, data))

    def search(self, name: str, value: str) -> None:
        """UI-12: the page again with ?name=value (and without its page number)."""
        parts = urlsplit(self.path)
        params = {k: v for k, v in parse_qsl(parts.query) if k not in (name, 'page')}
        if value:
            params[name] = value
        self.load(parts.path + ('?' + urlencode(params) if params else ''))

    # -- what the user did ----------------------------------------------------

    def handle(self, event: dict) -> bool:
        """One event of the screen; whether the page stays open."""
        kind = event.get('event')
        if kind == 'close':
            return False
        if kind == 'status':
            global _SCREEN_STATUS
            _SCREEN_STATUS = {k: v for k, v in event.items() if k != 'event'}
            return True
        if kind in ('click', 'submit'):
            fields: Dict[str, str] = dict(event.get('fields') or {})
            self.load(self.path, 'POST', {'action': event.get('action'), **fields})
        elif kind == 'navigate':
            self.load(event.get('to') or self.path)
        elif kind == 'change':
            self.search(str(event.get('bind') or ''), str(event.get('value') or ''))
        elif kind == 'reload':
            self.load(self.path)
        elif 'error' in event:
            self.log(f'hive-screen: {event["error"]}')
        return True

    def run(self) -> None:
        """Connects, shows the first page and answers events until the page is closed or the screen goes."""
        self.connect()
        self.serve()

    def hear_status(self, wait: float = 0.5) -> None:
        """The screen says what it is as soon as a runtime connects; the first page
        waits that long for it, so a page that asks (the Settings app) is right from
        the start. A screen that says nothing is an older one: the page goes on."""
        assert self.sock is not None
        self.sock.settimeout(wait)
        try:
            line = self.reader.readline()
            if line.strip():
                self.handle(json.loads(line))
        except (socket.timeout, ValueError, OSError):
            pass
        finally:
            self.sock.settimeout(None)

    def serve(self) -> None:
        """Connected: shows the first page and answers events until the page is closed or the screen goes."""
        try:
            self.hear_status()
            self.load(self.path)
            while True:
                line = self.reader.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except ValueError:
                    self.log(f'hive-screen said something that is not an event: {line}')
                    continue
                if not self.handle(event):
                    break
        finally:
            self.close()


def run_pixel(config_path: str = 'quantum.config.yaml', path: str = '/',
              socket_path: str = DEFAULT_SOCKET) -> int:
    """`quantum pixel`: the application's server in a thread, the page on the Hive's screen."""
    from quantum.runtime.local_server import local_server

    # The screen first: without it there is nothing to start the server for.
    client = PixelClient('', path, socket_path)
    try:
        client.connect()
    except (FileNotFoundError, ConnectionRefusedError, PermissionError) as exc:
        print(f'The Hive\'s screen is not listening at {socket_path}: {exc}\n'
              'Is hive-screen running on this machine (systemctl status hive-screen)?',
              file=sys.stderr)
        return 1
    with local_server(config_path) as base_url:
        client.base_url = base_url
        client.serve()
    return 0
