#!/usr/bin/env python
"""Play the web builds of the games in Chromium, as a visitor of /games/ would.

    python scripts/export-games.py --preset Web --out /tmp/games     # the builds
    python scripts/check-games-in-browser.py /tmp/games              # every game
    python scripts/check-games-in-browser.py /tmp/games hopper chess # some

The replay tests (tests/godot/) run each game in Godot on the desktop, with
its files on disk. A browser build is different: its pictures, sounds and
fonts are Godot's imports only, and its keys arrive as browser events between
two ticks. Both broke on the site once while every test was green. Here each
game's index.html is served, opened in a headless Chromium (WebGL by
SwiftShader), and must:

- start, and open on the scene projects/games.json names (`check.scene`);
- print no error to the console (Godot's push_error, a script error, a
  picture, sound or font it "cannot load");
- after the keys of `check.press`, go to the scene `check.then`, or have
  seen the actions of `check.actions`.

The game reports its scene and the actions it saw in window.quantumScene and
window.quantumActions (Q.web_report, only in a browser). A screenshot of each
game is left next to its build (check.png), for a person to look at.
"""

import functools
import http.server
import json
import os
import sys
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BOOT = 90.0     # seconds for a game to start: SwiftShader is slow to compile shaders
ERRORS = ('cannot load', 'SCRIPT ERROR', 'Parse Error')


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve(root: Path) -> tuple:
    handler = functools.partial(_Quiet, directory=str(root))
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f'http://127.0.0.1:{server.server_address[1]}'


def _wait(page, expression: str, seconds: float) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if page.evaluate(expression):
            return True
        page.wait_for_timeout(250)
    return False


def check(browser, base: str, root: Path, game: dict) -> list:
    """What is wrong with the game in the browser: [] when nothing."""
    name, want = game['name'], game['check']
    page = browser.new_page(viewport={'width': 1280, 'height': 720})
    logs = []
    page.on('console', lambda m: logs.append((m.type, m.text)))
    page.on('pageerror', lambda e: logs.append(('error', f'the page: {e}')))
    problems = []
    try:
        page.goto(f'{base}/{name}/index.html')
        if not _wait(page, 'typeof window.quantumScene === "string"', BOOT):
            return [f'{name}: did not start in {BOOT:.0f} s']
        scene = page.evaluate('window.quantumScene')
        if scene != want['scene']:
            problems.append(f'{name}: opened on {scene!r}, not {want["scene"]!r}')
        page.wait_for_timeout(1500)
        page.mouse.click(4, 4)                  # the canvas takes the keyboard
        page.wait_for_timeout(300)              # a key in the click's tick would be part of the click
        for key in want['press']:
            page.keyboard.down(key)
            page.wait_for_timeout(300)
            page.keyboard.up(key)
            page.wait_for_timeout(200)
        if 'then' in want:
            js = f'window.quantumScene === {json.dumps(want["then"])}'
            if not _wait(page, js, 10):
                problems.append(f'{name}: after {"+".join(want["press"])} the scene is '
                                f'{page.evaluate("window.quantumScene")!r}, not {want["then"]!r} '
                                f'(the game saw {page.evaluate("window.quantumActions")!r})')
        for action in want.get('actions', []):
            js = f'(window.quantumActions || "").split(",").includes({json.dumps(action)})'
            if not _wait(page, js, 5):
                problems.append(f'{name}: the game never saw {action!r} '
                                f'(it saw {page.evaluate("window.quantumActions")!r})')
        page.wait_for_timeout(1000)
        page.screenshot(path=str(root / name / 'check.png'))
        problems += [f'{name}: console: {text}' for kind, text in logs
                     if kind == 'error' or any(e in text for e in ERRORS)]
    finally:
        page.close()
    return problems


def main(argv) -> int:
    if not argv:
        print(__doc__)
        return 2
    root, only = Path(argv[0]).resolve(), set(argv[1:])
    games = [g for g in json.loads((REPO / 'projects' / 'games.json').read_text())['games']
             if (not only or g['name'] in only)]
    missing = [g['name'] for g in games if not (root / g['name'] / 'index.html').is_file()]
    if missing:
        print(f'no web build in {root} for: {", ".join(missing)}')
        return 1
    from playwright.sync_api import sync_playwright
    server, base = serve(root)
    problems = []
    with sync_playwright() as pw:
        exe = os.environ.get('CHROMIUM')    # a Chromium of one's own, instead of Playwright's
        browser = pw.chromium.launch(executable_path=exe or None, args=[
            '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
            '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'])
        for game in games:
            started = time.monotonic()
            found = check(browser, base, root, game)
            print(f'{"FAIL" if found else "ok  "} {game["name"]} ({time.monotonic() - started:.0f} s)')
            for p in found:
                print(f'     {p}')
            problems += found
        browser.close()
    server.shutdown()
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
