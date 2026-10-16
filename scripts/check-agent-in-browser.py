#!/usr/bin/env python
"""An agent plays Pong against a person in the browser (PLAN_PLAY_PROTOCOL.md, phase 6).

    python scripts/export-games.py pong --preset Web --out /tmp/games   # the web build
    python scripts/check-agent-in-browser.py /tmp/games

The agent hosts the game through the play protocol, live (the game does
not wait for it) and over WebSocket, the transport a browser can join.
The person is a headless Chromium on the web build: it opens Pong, goes
to the title's Join (the address field already says 127.0.0.1:7777) and
plays the right paddle with W and S while the agent plays the left one
with reflexes. It must:

- start the networked game on both sides (the agent's observation says
  `playing`, the page says `court`);
- go on without a desync, the lockstep comparing both games every second;
- have the agent return the ball at least twice and never miss it.

A screenshot of the page is left next to the build (agent.png).
"""

import functools
import http.server
import socket
import sys
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

PORT = 7777     # what the title's address field says
BOOT = 90.0     # seconds for the page to start: SwiftShader is slow to compile shaders
PLAY = 1500     # ticks of play, about 25 seconds


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


def misses(touches: list) -> list:
    """Who let the ball past, from the touches in order ('left', 'right', 'wall')."""
    heading, out = 'left', []          # the ball starts towards the left paddle
    for t in touches:
        if t == 'wall':
            out.append('left' if heading == 'left' else 'right')
            heading = 'left'           # back to the middle, as it was
        else:
            heading = 'right' if t == 'left' else 'left'
    return out


def main(argv) -> int:
    if not argv:
        print(__doc__)
        return 2
    root = Path(argv[0]).resolve()
    if not (root / 'pong' / 'index.html').is_file():
        print(f'no web build of pong in {root}')
        return 1
    with socket.socket() as s:
        if s.connect_ex(('127.0.0.1', PORT)) == 0:
            print(f'port {PORT} is taken: the title joins there')
            return 1
    from playwright.sync_api import sync_playwright

    from quantum.runtime.godot_play import PlaySession

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(_Quiet, directory=str(root)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_address[1]}'
    problems = []
    with PlaySession.open(REPO / 'projects' / 'pong' / 'pong.q', host=PORT, transport='websocket') as agent, \
            sync_playwright() as pw:
        browser = pw.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
                                           '--ignore-gpu-blocklist'])
        page = browser.new_page(viewport={'width': 1280, 'height': 720})
        logs = []
        page.on('console', lambda m: logs.append((m.type, m.text)))
        try:
            page.goto(f'{base}/pong/index.html')
            if not _wait(page, 'window.quantumScene === "title"', BOOT):
                return _report([f'the page did not open on the title in {BOOT:.0f} s'])
            page.wait_for_timeout(1500)
            page.mouse.click(4, 4)                      # the canvas takes the keyboard
            page.wait_for_timeout(300)
            for _ in range(3):                          # one keyboard, Host, the address, Join
                page.keyboard.press('s', delay=150)
                page.wait_for_timeout(250)
            page.keyboard.press('Enter', delay=150)
            seen = agent.until("net.status == 'playing'", max_ticks=60 * 60)
            if seen.get('net', {}).get('status') != 'playing':
                return _report([f'the person never joined: {seen.get("net")}'] + _console(logs))
            if not _wait(page, 'window.quantumScene === "court"', 30):
                problems.append(f'the page is on {page.evaluate("window.quantumScene")!r}, not the court')
            agent.act(ticks=0, reflex=[{'when': 'ball.y < left.y - 2', 'hold': ['up']},
                                       {'when': 'ball.y > left.y + 2', 'hold': ['down']}])
            touches, keys, started = [], 'sw', seen['tick']
            while seen['tick'] - started < PLAY and seen['net']['status'] == 'playing' and not seen['net']['desync']:
                page.keyboard.down(keys[len(touches) % 2])  # the person moves, now and then
                seen = agent.until(['event:touch with=ball', 'event:touch with=wall', "net.status != 'playing'",
                                    'net.desync'], max_ticks=PLAY)
                page.keyboard.up(keys[len(touches) % 2])
                touches += [e['who'] if e['with'] == 'ball' else 'wall' for e in seen.get('events', [])
                            if e['kind'] == 'touch' and e['with'] in ('ball', 'wall')]
            page.screenshot(path=str(root / 'pong' / 'agent.png'))
            if seen['net']['desync']:
                problems.append('the two games differ (a desync)')
            if touches.count('left') < 2:
                problems.append(f'the agent returned the ball {touches.count("left")} times: {touches}')
            if 'left' in misses(touches):
                problems.append(f'the agent let the ball past: {touches}')
            print(f'played {seen["tick"] - started} ticks: {touches}')
            problems += _console(logs)
        finally:
            page.close()
            browser.close()
    server.shutdown()
    return _report(problems)


def _console(logs) -> list:
    return [f'console: {text}' for kind, text in logs if kind == 'error' or 'SCRIPT ERROR' in text]


def _report(problems) -> int:
    for p in problems:
        print(f'FAIL {p}')
    print('ok   the agent played Pong against the browser' if not problems else '')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
