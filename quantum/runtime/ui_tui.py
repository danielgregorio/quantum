"""The TUI: the application's pages on a text screen drawn by Godot (SPEC.md UI-20, PLAN_PLATFORMS.md Phase 3).

`quantum run <app> --on tui` serves the application on a local port, as `quantum console` does, and opens
the Godot project next to this file (quantum/runtime/tui/) on it. The TUI is a renderer like the browser:
it asks the server for each page's view tree, lays it out in cells of one font, draws it, and sends the
same posts a browser sends, with the cookies the server set. Nothing of the page's logic runs in it.

A ``TuiSession`` runs the same project headless, driven through its play protocol — a JSON request a line
on its stdin, each answered with what the screen shows — as the games' agents drive a game::

    with TuiSession('http://127.0.0.1:8000', cols=120, rows=40) as tui:
        seen = tui.observe()                          # the screen as text, its items, its motions
        button = tui.item('button', 'Save')
        seen = tui.click(button['x'], button['y'])    # a click of the mouse; answered when the page settled
        seen = tui.type('Carla')                      # typed into the field with the focus
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Callable, List, Optional

TUI_DIR = Path(__file__).with_name('tui')
PREFIX = 'QTP '


class TuiError(RuntimeError):
    """The TUI refused a request, or stopped answering."""


def design_tokens() -> dict:
    """The browser's colours (its CSS's --q-* custom properties), which the TUI draws with too (UI-20)."""
    from quantum.runtime.ui_html_templates import CSS_THEME
    return {name: value for name, value in re.findall(r'--q-(primary|secondary|success|danger|warning|info):\s*'
                                                      r'(#[0-9a-fA-F]{6})', CSS_THEME)}


def project_copy() -> Path:
    """The TUI's Godot project in a folder of its own: Godot may write next to a project it runs, and the
    installed package's folder may not be writable."""
    target = Path(tempfile.mkdtemp(prefix='quantum-tui-'))
    for item in TUI_DIR.iterdir():
        if item.is_file() and item.suffix in ('.gd', '.tscn', '.godot', '.ttf', '.txt'):
            shutil.copy2(item, target / item.name)
    return target


def godot_command(url: str, page: str = '/', cols: int = 120, rows: int = 40, play: bool = False,
                  binary: Optional[Path] = None, project: Optional[Path] = None, motion: bool = True,
                  window: bool = False) -> List[str]:
    from quantum.runtime.godot_bin import ensure_godot
    godot = [str(binary or ensure_godot())]
    if play and not window:
        godot.append('--headless')
    return [*godot, '--path', str(project or TUI_DIR), '--',
            f'--url={url.rstrip("/")}', f'--page={page}', f'--cols={cols}', f'--rows={rows}',
            f'--tokens={json.dumps(design_tokens())}', *(['--play'] if play else []),
            *([] if motion else ['--motion=off'])]


class TuiSession:
    """One TUI, headless, played request by request (the play protocol)."""

    def __init__(self, url: str = '', page: str = '/', cols: int = 120, rows: int = 40,
                 binary: Optional[Path] = None, timeout: float = 60, window: bool = False,
                 program: Optional[Path] = None, env: Optional[dict] = None):
        """`window`: drawn in a real window (a display is needed: xvfb-run), so `shot` can save its picture.
        `program`: a package's program (`quantum package`, UI-22) instead, which starts its own server; `url` is
        then where that server is, once the first page is shown."""
        self.url = url.rstrip('/')
        self.timeout = timeout
        self.log: List[str] = []
        if program is not None:
            self._project = None
            command = [str(program), '--headless', '--', '--play', f'--cols={cols}', f'--rows={rows}',
                       *([f'--page={page}'] if page != '/' else [])]
        else:
            self._project = project_copy()
            command = godot_command(self.url, page, cols, rows, play=True, binary=binary, project=self._project,
                                    window=window)
        self.started = time.monotonic()
        self._proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT, text=True, bufsize=1, env=env)
        self.last = self.request({'op': 'observe'})
        if not self.last.get('pages'):
            self.last = self.request({'op': 'wait', 'text': '', 'timeout': timeout})
        # how long the first page took to show, the server's start included for a package's program
        self.first_page = time.monotonic() - self.started
        self.url = self.url or str(self.last.get('url', '')).rstrip('/')

    def __enter__(self) -> 'TuiSession':
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def request(self, req: dict) -> dict:
        if self._proc.poll() is not None:
            raise TuiError('the TUI has stopped: ' + ' | '.join(self.log[-8:]))
        self._proc.stdin.write(json.dumps(req) + '\n')
        self._proc.stdin.flush()
        while True:
            line = self._proc.stdout.readline()
            if line == '':
                raise TuiError('the TUI stopped answering: ' + ' | '.join(self.log[-8:]))
            if line.startswith(PREFIX):
                answer = json.loads(line[len(PREFIX):])
                if 'error' in answer:
                    raise TuiError(answer['error'])
                if 'screen' in answer:
                    self.last = answer
                return answer
            self.log.append(line.rstrip('\n'))

    # -- requests ---------------------------------------------------------------

    def observe(self) -> dict:
        return self.request({'op': 'observe'})

    def visit(self, path: str) -> dict:
        return self.request({'op': 'visit', 'path': path})

    def click(self, x: int, y: int) -> dict:
        return self.request({'op': 'click', 'x': int(x), 'y': int(y)})

    def hover(self, x: int, y: int) -> dict:
        return self.request({'op': 'hover', 'x': int(x), 'y': int(y)})

    def wheel(self, by: int) -> dict:
        return self.request({'op': 'wheel', 'by': int(by)})

    def key(self, *keys: str) -> dict:
        return self.request({'op': 'key', 'keys': list(keys)})

    def type(self, text: str) -> dict:
        return self.request({'op': 'type', 'text': text})

    def attach(self, bind: str, file: str) -> dict:
        return self.request({'op': 'attach', 'bind': bind, 'path': str(file)})

    def resize(self, cols: int, rows: int) -> dict:
        return self.request({'op': 'resize', 'cols': cols, 'rows': rows})

    def wait(self, text: str, timeout: float = 15, gone: bool = False) -> dict:
        """Answered once `text` is on the screen, or with `gone` once it is not (a toast after its duration,
        UI-21); an error after `timeout` seconds."""
        return self.request({'op': 'wait', 'text': text, 'timeout': timeout, 'gone': gone})

    def shot(self, file: str) -> str:
        """The window's picture, saved as PNG once the page has settled (a session opened with window=True)."""
        return self.request({'op': 'shot', 'path': str(file)})['shot']

    # -- reading what it shows ------------------------------------------------

    def text(self, seen: Optional[dict] = None) -> str:
        seen = seen or self.last
        return '\n'.join([seen.get('title', ''), *seen.get('screen', [])])

    def items(self, kind: Optional[str] = None, seen: Optional[dict] = None,
              where: Optional[Callable[[dict], bool]] = None) -> List[dict]:
        return [i for i in (seen or self.last).get('items', [])
                if (kind is None or i['kind'] == kind) and (where is None or where(i))]

    def item(self, kind: str, label: Optional[str] = None, **match) -> dict:
        """The first item of that kind (and label, and fields) on the screen, one that is not under what is
        drawn over the page (a modal, a toast, UI-21) before one that is."""
        found = self.items(kind, where=lambda i: (label is None or i.get('label') == label)
                           and all(i.get(k) == v for k, v in match.items()))
        found.sort(key=lambda i: bool(i.get('covered')))
        if not found:
            raise TuiError(f'no {kind} {label or match!r} on the screen: '
                           + ', '.join(f"{i['kind']} {i.get('label')!r}" for i in self.items()))
        return found[0]

    def close(self) -> None:
        if self._proc.poll() is None:
            try:
                self.request({'op': 'end'})
            except (TuiError, OSError, ValueError):
                pass
            try:
                self._proc.stdin.close()
            except OSError:
                pass
            try:
                self._proc.wait(10)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        if self._project is not None:
            shutil.rmtree(self._project, ignore_errors=True)


def launch(url: str, page: str = '/') -> int:
    """The TUI's window on the application at `url`; its exit code when the window is closed."""
    project = project_copy()
    try:
        return subprocess.call(godot_command(url, page, project=project))
    finally:
        shutil.rmtree(project, ignore_errors=True)


def run_tui(config_path: str = 'quantum.config.yaml', path: str = '/') -> int:
    """`quantum run <app> --on tui`: the application's server in a thread, its pages in the TUI's window."""
    from quantum.runtime.godot_bin import GODOT_VERSION, GodotNotFound, ensure_godot
    from quantum.runtime.local_server import local_server
    try:
        ensure_godot()
    except GodotNotFound:
        # the first time: the pinned Godot is fetched into the user's cache, saying so
        print(f'--on tui draws with Godot {GODOT_VERSION}; fetching it once into the cache...', file=sys.stderr)
        try:
            ensure_godot(download=True, progress=lambda line: print(f'  {line}', file=sys.stderr))
        except (GodotNotFound, OSError) as exc:
            print(f'[ERROR] --on tui draws with Godot: {exc}', file=sys.stderr)
            return 2
    with local_server(config_path) as base_url:
        return launch(base_url, path)
