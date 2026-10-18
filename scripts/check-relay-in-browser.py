#!/usr/bin/env python
"""Two people play Pong in their browsers, meeting at a relay.

    python scripts/export-games.py pong --preset Web --out /tmp/games   # the web build
    python scripts/check-relay-in-browser.py /tmp/games

A web page cannot host, so two browsers meet at `quantum relay`
(quantum/runtime/game_relay.py). Two headless Chromium pages open the web
build with ``?join=ws://127.0.0.1:PORT/pong/ROOM``: the title's address
field already holds the room, and each presses Join. The relay starts the
room's Godot, which takes no seat. The check asserts that:

- both pages reach the court, as players 1 and 2, in that order;
- they play about 20 seconds, each moving its paddle, with no desync (the
  lockstep compares both games every second; a page reports
  ``window.quantumNet``);
- when one page leaves, the other waits and says so on the screen, and a
  third page that opens the same link takes the free seat: it catches up the game so far and both
  play on, with no desync;
- when both leave, the relay closes the room.

A screenshot of each page is left next to the build (relay-1.png, relay-2.png,
and relay-3.png of the one who came back).
"""

import asyncio
import functools
import http.server
import os
import sys
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

BOOT = 90.0     # seconds for a page to start: SwiftShader is slow to compile shaders
PLAY = 20.0     # seconds of play
ROOM = 'ci-room'


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def _wait(page, expression: str, seconds: float) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if page.evaluate(expression):
            return True
        page.wait_for_timeout(250)
    return False


def _relay():
    """A relay on a free port, on its own event loop in a thread."""
    from quantum.runtime.game_relay import GameRelay
    from quantum.runtime.godot_replay import free_port
    relay, port, ready = GameRelay(), free_port(), threading.Event()
    loop = asyncio.new_event_loop()

    def run():
        asyncio.set_event_loop(loop)
        loop.run_until_complete(relay.serve('127.0.0.1', port))
        ready.set()
        loop.run_forever()

    threading.Thread(target=run, daemon=True).start()
    relay.build('pong')      # before the pages arrive: compiling takes a few seconds
    ready.wait(30)
    return relay, port, loop


def main(argv) -> int:
    if not argv:
        print(__doc__)
        return 2
    root = Path(argv[0]).resolve()
    if not (root / 'pong' / 'index.html').is_file():
        print(f'no web build of pong in {root}')
        return 1
    from playwright.sync_api import sync_playwright

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(_Quiet, directory=str(root)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    relay, port, loop = _relay()
    url = f'http://127.0.0.1:{server.server_address[1]}/pong/index.html?join=ws://127.0.0.1:{port}/pong/{ROOM}'
    problems = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.environ.get('CHROMIUM') or None, args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
                                           '--ignore-gpu-blocklist'])
        pages, logs = [], []
        try:
            for i in range(2):
                page = browser.new_page(viewport={'width': 1280, 'height': 720})
                page.on('console', lambda m, i=i: logs.append((i + 1, m.type, m.text)))
                page.goto(url)
                pages.append(page)
            for i, page in enumerate(pages):
                if not _wait(page, 'window.quantumScene === "title"', BOOT):
                    return _report([f'page {i + 1} did not open on the title in {BOOT:.0f} s'] + _console(logs))
            for page in pages:                       # one after the other: the seats go in that order
                page.wait_for_timeout(1500)
                page.mouse.click(4, 4)               # the canvas takes the keyboard
                page.wait_for_timeout(300)
                for _ in range(3):                   # one keyboard, Host, the address, Join
                    page.keyboard.press('s', delay=150)
                    page.wait_for_timeout(250)
                page.keyboard.press('Enter', delay=150)
                _wait(page, 'window.quantumNet === "connected" || window.quantumNet === "playing"', 30)
            for i, page in enumerate(pages):
                if not _wait(page, 'window.quantumScene === "court"', 60):
                    problems.append(f'page {i + 1} is on {page.evaluate("window.quantumScene")!r} '
                                    f'({page.evaluate("window.quantumNet")!r}), not the court')
            if problems:
                return _report(problems + _console(logs))
            end, turn = time.monotonic() + PLAY, 0
            while time.monotonic() < end:            # both move their paddles, now and then
                key = 'sw'[turn % 2]
                for page in pages:
                    page.keyboard.down(key)
                pages[0].wait_for_timeout(700)
                for page in pages:
                    page.keyboard.up(key)
                turn += 1
            for i, page in enumerate(pages):
                net = page.evaluate('window.quantumNet')
                page.screenshot(path=str(root / 'pong' / f'relay-{i + 1}.png'))
                if net != 'playing':
                    problems.append(f'page {i + 1} says {net!r} after {PLAY:.0f} s of play')
            pages[1].close()
            pages.pop()
            if not _wait(pages[0], 'window.quantumNet === "waiting"', 10):
                problems.append(f'page 1 did not wait for the other: {pages[0].evaluate("window.quantumNet")!r}')
            elif not str(pages[0].evaluate('window.quantumNotice') or '').startswith('Waiting for the other player'):
                problems.append(f'page 1 does not say it waits: {pages[0].evaluate("window.quantumNotice")!r}')
            pages[0].screenshot(path=str(root / 'pong' / 'relay-waiting.png'))
            # someone opens the same link and joins: they take the free seat
            page = browser.new_page(viewport={'width': 1280, 'height': 720})
            page.on('console', lambda m: logs.append((3, m.type, m.text)))
            page.goto(url)
            pages.append(page)
            if not _wait(page, 'window.quantumScene === "title"', BOOT):
                return _report(problems + ['page 3 did not open on the title'] + _console(logs))
            page.wait_for_timeout(1500)
            page.mouse.click(4, 4)
            page.wait_for_timeout(300)
            for _ in range(3):
                page.keyboard.press('s', delay=150)
                page.wait_for_timeout(250)
            page.keyboard.press('Enter', delay=150)
            for i, p in enumerate(pages):
                if not _wait(p, 'window.quantumNet === "playing"', 60):
                    problems.append(f'after the rejoin page {i * 2 + 1} says {p.evaluate("window.quantumNet")!r}')
            end, turn = time.monotonic() + 8.0, 0
            while time.monotonic() < end:
                for p in pages:
                    p.keyboard.down('sw'[turn % 2])
                pages[0].wait_for_timeout(700)
                for p in pages:
                    p.keyboard.up('sw'[turn % 2])
                turn += 1
            for i, p in enumerate(pages):
                net = p.evaluate('window.quantumNet')
                if net != 'playing':
                    problems.append(f'page {i * 2 + 1} says {net!r} after playing on')
                if p.evaluate('window.quantumNotice'):
                    problems.append(f'page {i * 2 + 1} still shows {p.evaluate("window.quantumNotice")!r}')
            page.screenshot(path=str(root / 'pong' / 'relay-3.png'))
            for p in list(pages):
                p.close()
                pages.remove(p)
            for _ in range(100):
                if not relay.rooms:
                    break
                time.sleep(0.1)
            if relay.rooms:
                problems.append(f'the room is still open: {list(relay.rooms)}')
            problems += _console(logs)
        finally:
            for page in pages:
                page.close()
            browser.close()
            loop.call_soon_threadsafe(loop.stop)
            relay.shutdown()
    server.shutdown()
    return _report(problems)


def _console(logs) -> list:
    # Godot's web build prints its warnings as console errors too: only its errors fail the check
    # (a player leaving is part of it)
    return [f'console {i}: {text}' for i, kind, text in logs if 'ERROR' in text]


def _report(problems) -> int:
    for p in problems:
        print(f'FAIL {p}')
    print('ok   two browsers played Pong through the relay' if not problems else '')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
