#!/usr/bin/env python
"""An agent wins the RPG's web build through the browser bridge (PLAN_PLAY_PROTOCOL.md).

    python scripts/export-games.py rpg --preset Web --out /tmp/games   # the web build
    python scripts/check-play-in-browser.py /tmp/games

The exported game answers the play protocol through ``window.quantumPlay``
(addons/quantum/web_play.gd), and ``WebPlaySession`` (quantum/runtime/web_play.py)
plays it from a headless Chromium, in real time: it walks down to row 7,
right into the opponent, reads its three lines, attacks on each of its
turns and wins. Each step is decided from the last observation, as the
agents of tests/godot/test_godot_play.py decide theirs, but the game here
is what the site serves. The check asserts that:

- the observations carry the scene, the state and the screen;
- the events reach the page (a step, the opponent's say, the scene change);
- the fight is won, and the opponent says so on the map.

A screenshot is left next to the build (bridge.png).
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
    if not (root / 'rpg' / 'index.html').is_file():
        print(f'no web build of rpg in {root}')
        return 1
    from playwright.sync_api import sync_playwright

    from quantum.runtime.web_play import WebPlaySession

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(_Quiet, directory=str(root)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    problems = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path=os.environ.get('CHROMIUM') or None,
                                     args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
                                           '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'])
        page = browser.new_page(viewport={'width': 1280, 'height': 720})
        logs = []
        page.on('console', lambda m: logs.append(m.text))
        try:
            page.goto(f'http://127.0.0.1:{server.server_address[1]}/rpg/index.html')
            game = WebPlaySession(page)
            start = game.ready()
            if start['scene'] != 'exploration' or 'nodes' not in start['state']:
                problems.append(f'the first observation: {start}')
            game.until('player.row == 7', hold=['down'], max_ticks=600)
            seen = game.until('talking', hold=['right'], max_ticks=900)
            if not seen['state'].get('talking'):
                return _report([f'the opponent never talked: {seen["state"]}'] + _errors(logs))
            for _ in range(10):                       # its three lines, and the fight
                if seen['scene'] == 'combat':
                    break
                seen = game.act(tap=['select'], ticks=8)
            for _ in range(60):
                if seen['scene'] != 'combat':
                    break
                if seen['state'].get('turn') == 'player':
                    seen = game.act(tap=['select'], ticks=8)   # Attack, the menu's first button
                else:
                    seen = game.until(["turn == 'player'", 'changed scene'], max_ticks=240)
            seen = game.until('talking', max_ticks=120)
            said = WebPlaySession.screen(seen, 'dialogue')
            if not said or said.get('text') != 'Congratulations, you won!':
                problems.append(f'the end: {seen["scene"]}, {said}')
            kinds = {e['kind'] for e in game.events}
            for kind in ('step', 'say', 'scene', 'choose'):
                if kind not in kinds:
                    problems.append(f'no {kind!r} event reached the page (saw {sorted(kinds)})')
            page.screenshot(path=str(root / 'rpg' / 'bridge.png'))
            print(f'won at tick {seen["tick"]}, {len(game.events)} events')
            problems += _errors(logs)
        finally:
            page.close()
            browser.close()
    server.shutdown()
    return _report(problems)


def _errors(logs) -> list:
    return [f'console: {text}' for text in logs if 'ERROR' in text]


def _report(problems) -> int:
    for p in problems:
        print(f'FAIL {p}')
    print('ok   an agent won the RPG in the browser' if not problems else '')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
