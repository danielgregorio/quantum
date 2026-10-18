#!/usr/bin/env python
"""A saved game survives the page: Keep's web build, saved, reloaded, continued.

    python scripts/export-games.py keep --preset Web --out /tmp/games   # the web build
    python scripts/check-save-in-browser.py /tmp/games

A web build keeps a qg:save in the browser (Godot's user://, which is the
page's IndexedDB). Through the browser bridge (``WebPlaySession``), the check:

- presses New game on the title and walks east into room 2, which saves
  the game (``<qg:scene save="true">``);
- reloads the page: the title has Continue now;
- continues, and is in room 2 again, with the hearts it had.

A screenshot of the continued game is left next to the build (save.png).
"""

import functools
import http.server
import os
import sys
import threading
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main(argv) -> int:
    if not argv:
        print(__doc__)
        return 2
    root = Path(argv[0]).resolve()
    if not (root / 'keep' / 'index.html').is_file():
        print(f'no web build of keep in {root}')
        return 1
    from playwright.sync_api import sync_playwright

    from quantum.runtime.web_play import WebPlaySession

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(_Quiet, directory=str(root)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    problems = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.environ.get('CHROMIUM') or None,
                                     args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
                                           '--ignore-gpu-blocklist'])
        page = browser.new_page(viewport={'width': 1280, 'height': 720})
        logs = []
        page.on('console', lambda m: logs.append(m.text))
        try:
            page.goto(f'http://127.0.0.1:{server.server_address[1]}/keep/index.html')
            game = WebPlaySession(page)
            if game.ready()['scene'] != 'title':
                return _report([f'the game opened on {game.last["scene"]!r}, not the title'])
            if _shown(game.last, 'Continue'):
                problems.append('a fresh page offers Continue')
            for _ in range(5):                                       # New game (a press the page lost: again)
                seen = game.until("scene == 'room-1'", tap=['select'], max_ticks=30)
                if seen['scene'] == 'room-1':
                    break
            if seen['scene'] != 'room-1':
                return _report([f'New game did not start it: {seen["scene"]}, {seen["screen"]}'] + _errors(logs))
            seen = game.until("scene == 'room-2'", hold=['right'], max_ticks=900)
            if seen['scene'] != 'room-2':
                return _report([f'never reached room 2: {seen["scene"]}, {seen["state"].get("nodes", {})}'] + _errors(logs))
            hearts = seen['state']['game']['hearts']
            game.act(ticks=30)                                       # a moment for the browser to keep the file
            page.reload()
            game = WebPlaySession(page)
            if game.ready()['scene'] != 'title':
                problems.append(f'after the reload the game opened on {game.last["scene"]!r}')
            if not _shown(game.last, 'Continue'):
                problems.append(f'after the reload the title has no Continue: {game.last["screen"]}')
            game.act(tap=['down'], ticks=4)
            back = game.until("scene == 'room-2'", tap=['select'], max_ticks=60)
            if back['scene'] != 'room-2':
                problems.append(f'Continue went to {back["scene"]!r}, not room 2')
            elif back['state']['game']['hearts'] != hearts:
                problems.append(f'hearts {back["state"]["game"]["hearts"]} after Continue, {hearts} saved')
            page.screenshot(path=str(root / 'keep' / 'save.png'))
            problems += _errors(logs)
        finally:
            page.close()
            browser.close()
    server.shutdown()
    return _report(problems)


def _shown(obs: dict, label: str) -> bool:
    from quantum.runtime.web_play import WebPlaySession
    menu = WebPlaySession.screen(obs, 'menu') or {}
    return any(i.get('button') == label and i.get('shown', True) for i in menu.get('items', []))


def _errors(logs) -> list:
    return [f'console: {text}' for text in logs if 'ERROR' in text]


def _report(problems) -> int:
    for p in problems:
        print(f'FAIL {p}')
    print('ok   a saved game survives the page' if not problems else '')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
