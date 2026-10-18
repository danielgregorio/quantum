"""Play an exported web build: the play protocol's browser bridge (PLAN_PLAY_PROTOCOL.md).

A web build answers the play protocol through ``window.quantumPlay``
(``addons/quantum/web_play.gd``). ``WebPlaySession`` drives it from a
Playwright page, with the requests of ``PlaySession`` that make sense in
real time::

    with sync_playwright() as pw:
        page = pw.chromium.launch().new_page()
        page.goto('http://localhost:8000/rpg/index.html')
        game = WebPlaySession(page)
        game.ready()                                         # the game has started
        seen = game.until('player.row == 7', hold=['down'])  # walk down
        seen = game.until('talking', hold=['right'])         # into the opponent

The game does not wait: it runs at its own speed, as a person plays it, and
an observation is what the page shows when it is read. ``act`` holds actions
for about that many ticks; ``until`` holds them, reading the page, until a
condition holds (the same conditions as ``PlaySession.until``, evaluated
here). This plays the exported game itself: what the site serves, its
JavaScript, its renderer, its audio.
"""

from __future__ import annotations

import json
import time
from typing import Iterable, List, Optional, Union

from quantum.runtime.godot_play import PlayError, condition

OBSERVE = '() => { window.quantumPlay.observe(); return window.quantumObservation; }'


class WebPlaySession:
    """A web build in a Playwright page, played through ``window.quantumPlay``."""

    def __init__(self, page, poll_ms: int = 50):
        self.page = page
        self.poll_ms = poll_ms
        self.last: Optional[dict] = None
        self.events: List[dict] = []    # every event read so far, in order

    def ready(self, seconds: float = 90.0) -> dict:
        """Waits for the game to start (``window.quantumPlay`` is there), and starts tracing."""
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if self.page.evaluate('() => !!(window.quantumPlay && window.quantumScene)'):
                self.page.evaluate('() => window.quantumPlay.trace(true)')
                return self.observe()
            self.page.wait_for_timeout(250)
        raise PlayError(f'the web build did not start in {seconds:.0f} s')

    def observe(self) -> dict:
        obs = json.loads(self.page.evaluate(OBSERVE))
        self.events.extend(obs.get('events', []))
        self.last = obs
        return obs

    def press(self, actions: Iterable[str]) -> None:
        for a in actions:
            self.page.evaluate('(a) => window.quantumPlay.press(a)', a)

    def release(self, actions: Iterable[str]) -> None:
        for a in actions:
            self.page.evaluate('(a) => window.quantumPlay.release(a)', a)

    def act(self, hold: Iterable[str] = (), tap: Iterable[str] = (), ticks: int = 1) -> dict:
        """Holds ``hold`` (and ``tap`` for its first tick) for about ``ticks`` ticks of the
        game's own time, then lets go. Answers the observation then, with its events."""
        hold, tap = list(hold), list(tap)
        start = self.observe()
        events = []
        self.press(hold + tap)
        try:
            tapped = False
            while True:
                seen = self.observe()
                events += seen.get('events', [])
                if tap and not tapped and seen['tick'] > start['tick']:
                    self.release([a for a in tap if a not in hold])
                    tapped = True
                if seen['tick'] - start['tick'] >= ticks:
                    break
                self.page.wait_for_timeout(self.poll_ms)
        finally:
            self.release(hold + tap)
        seen['events'] = events
        seen['stopped'] = 'ticks'
        return seen

    def until(self, cond: Union[str, dict, list], hold: Iterable[str] = (), tap: Iterable[str] = (),
              max_ticks: int = 600) -> dict:
        """As ``act``, but until ``cond`` holds (read every ``poll_ms``) or ``max_ticks`` ticks
        have run; ``stopped`` says which. Every event of the way counts for an ``event:`` condition."""
        hold, tap = list(hold), list(tap)
        cond = condition(cond)
        start = self.observe()
        events: List[dict] = []
        self.press(hold + tap)
        stopped = 'ticks'
        try:
            tapped = False
            while True:
                seen = self.observe()
                events += seen.get('events', [])
                if tap and not tapped and seen['tick'] > start['tick']:
                    self.release([a for a in tap if a not in hold])
                    tapped = True
                if holds(cond, seen, start, events):
                    stopped = 'condition'
                    break
                if seen['tick'] - start['tick'] >= max_ticks:
                    break
                self.page.wait_for_timeout(self.poll_ms)
        finally:
            self.release(hold + tap)
        seen['events'] = events
        seen['stopped'] = stopped
        return seen

    @staticmethod
    def screen(obs: dict, kind: str) -> Optional[dict]:
        for v in obs.get('screen', []):
            if v.get('kind') == kind and v.get('shown', True):
                return v
        return None


# --- conditions, as the driver reads them (godot_play.gd's _holds) ---

def holds(cond: dict, obs: dict, start: dict, events: List[dict]) -> bool:
    if 'any' in cond:
        return any(holds(c, obs, start, events) for c in cond['any'])
    if 'all' in cond:
        return all(holds(c, obs, start, events) for c in cond['all'])
    if 'event' in cond:
        return any(e.get('kind') == str(cond['event'])
                   and all(k in e and str(e[k]) == str(v) for k, v in cond.items() if k != 'event')
                   for e in events)
    if 'changed' in cond:
        return json.dumps(lookup(obs, cond['changed'])) != json.dumps(lookup(start, cond['changed']))
    if 'path' in cond:
        v = lookup(obs, cond['path'])
        op = cond.get('op', 'truthy')
        w = cond.get('value')
        if isinstance(w, dict) and 'path' in w:
            plus = w.get('plus', 0)
            w = lookup(obs, w['path'])
            if _number(w) and _number(plus):
                w = w + plus
        if op == 'truthy':
            return _truthy(v)
        if op == 'falsy':
            return not _truthy(v)
        if op == '==':
            return _same(v, w)
        if op == '!=':
            return not _same(v, w)
        if not (_number(v) and _number(w)):
            return False
        return {'<': v < w, '<=': v <= w, '>': v > w, '>=': v >= w}.get(op, False)
    return False


def lookup(obs: dict, path: str):
    """``player.col``: the observation's keys, then the state, its nodes, its named things,
    the game's state; ``dialogue.text``: the screen's view of that kind."""
    parts = path.split('.')
    state = obs.get('state', {}) or {}
    views = {}
    for v in obs.get('screen', []):
        views.setdefault(v.get('kind'), v)
    for base in (obs, state, state.get('nodes', {}), state.get('named', {}), state.get('game', {}), views):
        if isinstance(base, dict) and parts[0] in base:
            cur, ok = base, True
            for p in parts:
                if isinstance(cur, dict) and p in cur:
                    cur = cur[p]
                elif isinstance(cur, list) and p.isdigit() and int(p) < len(cur):
                    cur = cur[int(p)]
                else:
                    ok = False
                    break
            if ok:
                return cur
    return None


def _number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _truthy(v) -> bool:
    if v is None:
        return False
    if isinstance(v, (str, list, dict)):
        return len(v) > 0
    return bool(v)


def _same(v, w) -> bool:
    if _number(v) and _number(w):
        return abs(float(v) - float(w)) < 1e-5
    return json.dumps(v) == json.dumps(w)
