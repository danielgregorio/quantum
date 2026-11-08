"""UI Engine parity (UI-7): one script, every renderer.

The app tests/apps/showcase uses the whole Core set of ui:*. The same SCRIPT
runs in a real browser (Playwright + Chromium; installed in CI, skipped locally
without them), in the console (Textual's pilot) and on the Hive's screen
(hive-screen, the Quantum OS daemon, built from os/ — skipped without it —
driven through its play protocol with `quantum pixel` as its client, UI-15).
The desktop is the system's browser over the same server — what holds for the
browser holds for it (UI-4).

Each step is data; each renderer has a driver that knows how to do it.
"""

import asyncio
import datetime
import json
import logging
import os
import re
import shutil
import subprocess
import threading
from pathlib import Path

import pytest
import requests

from tests.apps.ui_drivers import WAIT, Browser, Tui, run_console_script, run_script

SHOWCASE = Path(__file__).resolve().parent / "showcase"
OS_DIR = Path(__file__).resolve().parents[2] / "os"

VISIBLE_ON_OPEN = [
    "Showcase header", "Panel", "Bold text", "Badge", "Go to about",
    "Section", "Section text", "Cell A", "Cell B",
    "Card", "Card top", "Card body", "Card footer",
    "First tab", "Second tab", "Content of the first",
    "Fruit: piña", "Fruit: grape",
    "Name", "Age", "Actions", "Ana", "30", "Bia", "25", "Remove Ana", "Remove Bia",
    "Active", "Get notifications", "free", "pro", "Save", "Showcase footer",
]

SCRIPT = [
    ("sees", VISIBLE_ON_OPEN),
    ("does_not_see", ["Content of the second"]),     # a closed tab
    ("image", "Logo"),
    ("progress", "bar", 40),
    ("values", {"name": "Ana", "active": True, "notify": False, "plan": "free", "color": "green"}),
    # The form sends what the user left: checked goes as "on", unchecked does not go.
    ("fill", "name", "Carla"),
    ("check", "active", False),
    ("check", "notify", True),
    ("choose", "plan", "pro"),
    ("choose", "color", "blue"),
    ("click", "Save"),
    ("sees", ["Saved: Carla, active=off, notify=on, plan=pro, color=blue"]),
    # The row's button sends the action with the row's field.
    ("click", "Remove Bia"),
    ("sees", ["Removed: 2"]),
    # Validation is the action's, the same in both: the field comes back with the
    # value sent and the error next to it (UI-9).
    ("fill", "name", "carla"),
    ("click", "Save"),
    ("sees", ["does not match '^[A-Z]'", "Does not match '^[A-Z]'"]),
    ("values", {"name": "carla"}),
    # A tab opens its content and closes the other's.
    ("tab", "Second tab"),
    ("sees", ["Content of the second"]),
    ("does_not_see", ["Content of the first"]),
]

# UI-21: the tags beyond the layout set (tests/apps/showcase/components/more.q)
MORE = [
    ("visit", "/more"),
    ("sees", ["Home", "Library", "Shelf", "New file", "Open file", "AL", "Signed in as Ana Lima",
              "Notes", "bold", "words", "first point", "second point",
              "Sales", "Mon", "Tue", "Share", "Red", "Blue", "25%", "75%",
              "Docs", "Guide", "Reference", "Archive",
              "started", "listening on 8080", "Left pane", "Right pane", "45 items", "Fetching"]),
    ("does_not_see", ["booting", "is not drawn"]),          # the log shows its last two lines
    # a menu's option and a tree's row post their action with their value
    ("follow", "New file"),
    ("sees", ["Picked: new"]),
    ("follow", "Guide"),
    ("sees", ["Picked: guide"]),
    # a date picker is a date field: what is typed goes with the form
    ("fill", "day", "2026-12-24"),
    ("click", "Book"),
    ("sees", ["Booked: 2026-12-24"]),
    # a breadcrumb's items are links
    ("follow", "Home"),
    ("sees", ["Showcase header"]),
]

# UI-21: the tags with a state of their own (tests/apps/showcase/components/state.q)
STATE = [
    ("visit", "/state?welcome=1"),
    ("sees", ["All changes kept", "Welcome", "Read this first"]),
    # a modal that is open shows over the page until it is closed
    ("close", "Welcome"),
    ("does_not_see", ["Read this first"]),
    # an accordion: its first fold open, the others closed until opened
    ("sees", ["First fold", "Inside the first", "Second fold"]),
    ("does_not_see", ["Inside the second"]),
    ("fold", "Second fold"),
    ("sees", ["Inside the second"]),
    # a tooltip says its tip when its element is pointed at, or has the focus
    ("sees", ["Hover me"]),
    ("does_not_see", ["A tip for the badge"]),
    ("tip", "Hover me", "A tip for the badge"),
    # a carousel shows one slide, the next on its arrow
    ("sees", ["Slide one"]),
    ("does_not_see", ["Slide two"]),
    ("next", "carousel"),
    ("sees", ["Slide two"]),
    # a stepper shows one step's content, the next on Next
    ("sees", ["Account", "Profile", "Step one body"]),
    ("does_not_see", ["Step two body"]),
    ("next", "stepper"),
    ("sees", ["Step two body"]),
    # a toast goes after its duration
    ("gone", "All changes kept"),
    # a dropdown opens on its button, and its option posts the action
    ("sees", ["Actions"]),
    ("does_not_see", ["Move"]),
    ("pick", "Actions", "Move"),
    ("sees", ["Picked: move"]),
    # a form's ui:validators: the server checks them, and the error comes back by its field
    ("fill", "code", "abc"),
    ("fill", "again", "abc"),
    ("click", "Join"),
    ("sees", ["Three capital letters"]),
    ("fill", "code", "ABC"),
    ("fill", "again", "ABD"),
    ("click", "Join"),
    ("sees", ["The codes differ"]),
    ("fill", "again", "ABC"),
    ("click", "Join"),
    ("sees", ["Joined with ABC"]),
    # a calendar: a month, the next on its arrow, a day picked goes with the form; one its validator refuses
    # comes back in it (its month shown), with the error by it
    ("sees", ["November 2026"]),
    ("month", "next"),
    ("sees", ["December 2026"]),
    ("day", "25"),
    ("click", "Book"),
    ("sees", ["Closed on the 25th", "December 2026"]),
    ("day", "24"),
    ("click", "Book"),
    ("sees", ["Booked: 2026-12-24"]),
]


@pytest.fixture
def url(tmp_path, monkeypatch):
    project = tmp_path / "showcase"
    shutil.copytree(SHOWCASE, project, ignore=shutil.ignore_patterns("__pycache__", "logs"))
    monkeypatch.chdir(project)
    from werkzeug.serving import make_server
    from quantum.runtime.web_server import QuantumWebServer
    logging.disable(logging.WARNING)
    app = QuantumWebServer(str(project / "quantum.config.yaml")).app
    server = make_server("127.0.0.1", 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/"
    server.shutdown()
    logging.disable(logging.NOTSET)


# -- browser ------------------------------------------------------------------

def test_the_script_in_the_browser(url):
    # UI-7
    playwright = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")
    with playwright.sync_playwright() as pw:
        try:
            chromium = pw.chromium.launch()
        except Exception as exc:   # browser not downloaded
            pytest.skip(f"Playwright's Chromium is not available: {exc}")
        try:
            page = chromium.new_page(viewport={"width": 1280, "height": 900})
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(url)
            run_script(Browser(page, url), SCRIPT)
            run_script(Browser(page, url), MORE)
            run_script(Browser(page, url), STATE)
            assert errors == []
        finally:
            chromium.close()


# -- console ------------------------------------------------------------------

def test_the_script_in_the_console(url):
    # UI-7
    from quantum.runtime.ui_console import ConsoleUI
    from tests.console_pilot import page_loaded

    async def main():
        app = ConsoleUI(url)
        async with app.run_test(size=(160, 120)) as pilot:
            await page_loaded(app, pilot)
            await run_console_script(app, pilot, SCRIPT)
            await run_console_script(app, pilot, MORE)
            await run_console_script(app, pilot, STATE)

    asyncio.run(main())


# -- the TUI drawn by Godot ------------------------------------------------------

def test_the_script_in_the_tui(url):
    # UI-7, UI-20: the same script, the TUI headless through its play protocol
    from quantum.runtime.godot_bin import GodotNotFound, ensure_godot
    from quantum.runtime.ui_tui import TuiSession
    try:
        ensure_godot()
    except GodotNotFound as exc:
        pytest.skip(str(exc))
    with TuiSession(url, cols=160, rows=60) as tui:
        run_script(Tui(tui), SCRIPT)
        assert tui.observe()["unsupported"] == []          # the whole Core set is drawn
        run_script(Tui(tui), MORE)
        run_script(Tui(tui), STATE)


# -- the Hive's screen (quantum pixel) -------------------------------------------

class Screen:
    """hive-screen with no display, driven from its stdin (os/crates/hive-screen/src/play.rs),
    with a pixel socket for the page's runtime."""

    def __init__(self, binary, socket_path):
        self.proc = subprocess.Popen(
            [binary, "--scene", str(OS_DIR / "config/screen/screen.toml"), "--no-hive", "--play",
             "--pixel-socket", socket_path],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        self.request({"op": "observe"})     # answered once the socket is bound

    def request(self, req):
        self.proc.stdin.write(json.dumps(req) + "\n")
        self.proc.stdin.flush()
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise RuntimeError(f"hive-screen ended without answering {req}")
            if line.startswith("QPP "):
                answer = json.loads(line[4:])
                assert "error" not in answer, answer
                return answer

    def end(self):
        try:
            self.request({"op": "end"})
        finally:
            self.proc.wait(10)


class Pixel:
    """The screen is keyboard-only: a field is reached with Tab, typed into,
    a box marked with Space, an option chosen with the arrows, a button
    pressed with Enter (a row's button through its table: a row, a column),
    a calendar's month moved with PgUp and PgDn and its day picked with the
    arrows and Enter (UI-21)."""
    name = "pixel"

    def __init__(self, screen, client=None):
        self.s, self.client = screen, client

    def visit(self, path):
        # the screen has no address bar: the page's runtime shows the page, as after a link
        before = self.window()["shown"]
        self.client.load(path)
        obs = self.s.request({"op": "until", "shown": before + 1, "max_ticks": 600})
        assert obs["stopped"] == "condition", f"the screen did not show {path}"

    def window(self):
        w = self.s.request({"op": "observe"})["window"]
        assert w, "no page on the screen"
        return w

    def text(self):
        return " | ".join(self.window()["texts"])

    def image(self, alt):
        assert f"[{alt}]" in self.text()

    def progress(self, ident, value):
        assert {"id": ident, "value": value} in self.window()["progress"]

    def values(self, expected):
        items = {i["bind"]: i for i in self.window()["items"] if i.get("bind")}
        for field, value in expected.items():
            if isinstance(value, bool):
                assert items[field]["checked"] is value, field
            else:
                assert items[field]["value"] == value, field

    def _focus(self, wanted):
        """Tab until the element `wanted` picks has the focus; the element."""
        items = self.window()["items"]
        target = [n for n, i in enumerate(items) if wanted(i)][0]
        current = [n for n, i in enumerate(items) if i["focus"]][0]
        steps = (target - current) % len(items)
        if steps:
            self.s.request({"op": "act", "tap": ["tab"] * steps})
        return items[target]

    def fill(self, field, value):
        self._focus(lambda i: i["kind"] == "input" and i.get("bind") == field)
        self.s.request({"op": "act", "tap": ["ctrl-u"]})      # what was there goes
        self.s.request({"op": "act", "type": value})

    def check(self, field, on):
        item = self._focus(lambda i: i["kind"] in ("checkbox", "switch") and i.get("bind") == field)
        if item["checked"] != on:
            self.s.request({"op": "act", "tap": ["space"]})

    def choose(self, field, value):
        item = self._focus(lambda i: i["kind"] in ("radio", "select") and i.get("bind") == field)
        now, wanted = item["options"].index(item["value"]), item["options"].index(value)
        keys = ["right"] * (wanted - now) if wanted > now else ["left"] * (now - wanted)
        if keys:
            self.s.request({"op": "act", "tap": keys})

    def click(self, label):
        before = self.window()["shown"]
        buttons = [i for i in self.window()["items"] if i["kind"] in ("button", "link", "treeitem") and i.get("label") == label]
        if buttons:
            self._focus(lambda i: i["kind"] in ("button", "link", "treeitem") and i.get("label") == label)
        else:
            # a row's button: the table, then the row, then the button in it
            table = self._focus(lambda i: i["kind"] == "table" and any(label in r for r in i["rows"]))
            row = [n for n, r in enumerate(table["rows"]) if label in r][0]
            col = table["rows"][row].index(label)
            keys = ["down"] * (row - table["row"]) if row > table["row"] else ["up"] * (table["row"] - row)
            keys += ["right"] * (col - table["col"]) if col > table["col"] else ["left"] * (table["col"] - col)
            if keys:
                self.s.request({"op": "act", "tap": keys})
        self.s.request({"op": "act", "tap": ["enter"]})
        # the action posted, the page came back: the screen shows it again
        obs = self.s.request({"op": "until", "shown": before + 1, "max_ticks": 600})
        assert obs["stopped"] == "condition", f"the page did not come back after {label}"

    def follow(self, label):
        # a link is reached and pressed as a button is: Tab to it, Enter
        self.click(label)

    def tab(self, title):
        panel = self._focus(lambda i: i["kind"] == "tabpanel")
        steps = panel["tabs"].index(title) - panel["tab"]
        if steps:
            self.s.request({"op": "act", "tap": ["right"] * steps if steps > 0 else ["left"] * -steps})

    # UI-21: what a tag with a state of its own does, from the keyboard

    def close(self, title):
        # an open modal has the keyboard: its close control, Enter
        self._focus(lambda i: i["kind"] == "modal" and i.get("label") == title)
        self.s.request({"op": "act", "tap": ["enter"]})

    def fold(self, title):
        self._focus(lambda i: i["kind"] == "section" and i.get("label") == title)
        self.s.request({"op": "act", "tap": ["enter"]})

    def tip(self, label, text):
        # the tip shows while its element has the focus
        self._focus(lambda i: i.get("label") == label)
        assert text in self.text(), f"the tip {text!r} does not show"

    def next(self, kind):
        if kind == "carousel":
            self._focus(lambda i: i["kind"] == "carousel")
            self.s.request({"op": "act", "tap": ["right"]})
        else:
            self._focus(lambda i: i.get("moves") == kind and i.get("label") == "Next")
            self.s.request({"op": "act", "tap": ["enter"]})

    def gone(self, text):
        obs = self.s.request({"op": "until", "gone": text, "max_ticks": WAIT * 60})
        assert obs["stopped"] == "condition", f"{text!r} did not go"

    def pick(self, label, option):
        self._focus(lambda i: i["kind"] == "dropdown" and i.get("label") == label)
        self.s.request({"op": "act", "tap": ["enter"]})
        self.click(option)

    def month(self, way):
        # a calendar with the focus shows the next month on PgDn, the one before on PgUp
        self._focus(lambda i: i["kind"] == "calendar")
        self.s.request({"op": "act", "tap": ["pgdn" if way == "next" else "pgup"]})

    def day(self, number):
        # the arrows move its cursor a day or a week, Enter picks the day under it
        calendar = self._focus(lambda i: i["kind"] == "calendar")
        wanted = datetime.date.fromisoformat(f"{calendar['month']}-{int(number):02d}")
        days = (wanted - datetime.date.fromisoformat(calendar["cursor"])).days
        weeks, rest = divmod(abs(days), 7)
        keys = ["down"] * weeks + ["right"] * rest if days > 0 else ["up"] * weeks + ["left"] * rest
        self.s.request({"op": "act", "tap": keys + ["enter"]})
        picked = [i for i in self.window()["items"] if i["kind"] == "calendar" and i["focus"]][0]
        assert picked["value"] == wanted.isoformat(), f"the calendar did not pick {wanted}: {picked}"


def test_the_script_on_the_pixel_screen(url, tmp_path):
    # UI-7, UI-15
    binary = os.environ.get("HIVE_SCREEN") or str(OS_DIR / "target/debug/hive-screen")
    if not Path(binary).is_file():
        pytest.skip("hive-screen is not built (cd os && cargo build -p hive-screen, or HIVE_SCREEN=...)")
    from quantum.runtime.ui_pixel import PixelClient

    socket_path = str(tmp_path / "pixel.sock")
    screen = Screen(binary, socket_path)
    try:
        client = PixelClient(url, "/", socket_path)
        runtime = threading.Thread(target=client.run, daemon=True)
        runtime.start()
        first = screen.request({"op": "until", "shown": 1, "max_ticks": 600})
        assert first["stopped"] == "condition", "quantum pixel did not bring the page"
        run_script(Pixel(screen, client), SCRIPT)
        run_script(Pixel(screen, client), MORE)
        run_script(Pixel(screen, client), STATE)
        # Esc closes the page; the page's runtime ends with it
        screen.request({"op": "act", "tap": ["escape"]})
        runtime.join(10)
        assert not runtime.is_alive()
    finally:
        screen.end()


# -- every tag: each renderer says what it does not draw (UI-7, UI_PARITY.md) -------------

NOT_DRAWN = re.compile(r"\[ui:([a-z]+) is not drawn ")


def test_every_tag_in_the_browser(url):
    # UI-7: the browser draws every tag of a page
    html = requests.get(url + "every", timeout=30).text
    assert "is not drawn" not in html and "Toast" in html and "Markdown" in html


def test_every_tag_in_the_console(url):
    from quantum.runtime.ui_console import ConsoleUI
    from quantum.runtime.ui_parity import not_drawn
    from tests.console_pilot import page_loaded
    from textual.widgets import Static

    async def main():
        app = ConsoleUI(url, "/every")
        async with app.run_test(size=(160, 200)) as pilot:
            await page_loaded(app, pilot)
            return {m.group(1) for w in app.query(Static) for m in NOT_DRAWN.finditer(str(w.render()))}

    assert asyncio.run(main()) == not_drawn("console")


def test_every_tag_in_the_tui(url):
    from quantum.runtime.godot_bin import GodotNotFound, ensure_godot
    from quantum.runtime.ui_parity import not_drawn
    from quantum.runtime.ui_tui import TuiSession
    try:
        ensure_godot()
    except GodotNotFound as exc:
        pytest.skip(str(exc))
    with TuiSession(url, page="/every", cols=160, rows=60) as tui:
        seen = tui.observe()
        assert set(seen["unsupported"]) == not_drawn("tui")
        assert {m.group(1) for m in NOT_DRAWN.finditer(tui.text(seen))} == not_drawn("tui")


def test_every_tag_on_the_screen(url, tmp_path):
    binary = os.environ.get("HIVE_SCREEN") or str(OS_DIR / "target/debug/hive-screen")
    if not Path(binary).is_file():
        pytest.skip("hive-screen is not built (cd os && cargo build -p hive-screen, or HIVE_SCREEN=...)")
    from quantum.runtime.ui_parity import not_drawn
    from quantum.runtime.ui_pixel import PixelClient

    socket_path = str(tmp_path / "pixel.sock")
    screen = Screen(binary, socket_path)
    try:
        client = PixelClient(url, "/every", socket_path, log=lambda line: None)
        threading.Thread(target=client.run, daemon=True).start()
        assert screen.request({"op": "until", "shown": 1, "max_ticks": 600})["stopped"] == "condition"
        texts = " | ".join(screen.request({"op": "observe"})["window"]["texts"])
        assert {m.group(1) for m in NOT_DRAWN.finditer(texts)} == not_drawn("screen")
    finally:
        screen.end()


# -- a page's ui:theme (UI-21): its colours in the browser, the console and the TUI ------------

def test_a_page_s_theme_in_the_browser(url):
    playwright = pytest.importorskip("playwright.sync_api", reason="Playwright is not installed")
    with playwright.sync_playwright() as pw:
        try:
            chromium = pw.chromium.launch()
        except Exception as exc:   # browser not downloaded
            pytest.skip(f"Playwright's Chromium is not available: {exc}")
        try:
            page = chromium.new_page()
            page.goto(url + "themed")
            primary = page.evaluate(
                "getComputedStyle(document.documentElement).getPropertyValue('--q-primary').trim()")
            assert primary == "#ff00aa"
        finally:
            chromium.close()


def test_a_page_s_theme_in_the_console(url):
    from quantum.runtime.ui_console import ConsoleUI
    from tests.console_pilot import page_loaded

    async def main():
        app = ConsoleUI(url, "/themed")
        async with app.run_test(size=(100, 40)) as pilot:
            await page_loaded(app, pilot)
            return app.get_css_variables()["primary"]

    assert asyncio.run(main()).lower() == "#ff00aa"


def test_a_page_s_theme_in_the_tui(url):
    from quantum.runtime.godot_bin import GodotNotFound, ensure_godot
    from quantum.runtime.ui_tui import TuiSession
    try:
        ensure_godot()
    except GodotNotFound as exc:
        pytest.skip(str(exc))
    with TuiSession(url, page="/themed", cols=80, rows=20) as tui:
        assert tui.observe()["palette"]["primary"] == "#ff00aa"
        tui.visit("/state")                                       # a page without a theme: the TUI's own
        assert tui.observe()["palette"]["primary"] != "#ff00aa"
