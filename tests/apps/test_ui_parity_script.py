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
import json
import logging
import os
import shutil
import subprocess
import threading
from pathlib import Path

import pytest

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


def run_script(driver, script):
    for step, *args in script:
        if step == "sees":
            text = driver.text()
            missing = [t for t in args[0] if t not in text]
            assert not missing, f"{driver.name}: does not show {missing}"
        elif step == "does_not_see":
            text = driver.text()
            assert not [t for t in args[0] if t in text], f"{driver.name}: shows {args[0]}"
        else:
            getattr(driver, step)(*args)


# -- browser ------------------------------------------------------------------

class Browser:
    name = "browser"

    def __init__(self, page):
        self.p = page

    def text(self):
        return self.p.inner_text("body")

    def image(self, alt):
        assert self.p.locator(f'img[alt="{alt}"]').count() == 1

    def progress(self, ident, value):
        assert float(self.p.get_attribute(f"#{ident}", "value")) == value

    def values(self, expected):
        for field, value in expected.items():
            if isinstance(value, bool):
                assert self.p.is_checked(f'input[name="{field}"]') is value, field
            elif self.p.locator(f'input[type="radio"][name="{field}"]').count():
                assert self.p.locator(f'input[name="{field}"]:checked').get_attribute("value") == value
            else:
                assert self.p.input_value(f'[name="{field}"]') == value, field

    def fill(self, field, value):
        self.p.fill(f'[name="{field}"]', value)

    def check(self, field, on):
        box = self.p.locator(f'input[name="{field}"]')
        if box.is_checked() != on:
            # As a user does: click the label (the switch hides the box).
            self.p.locator("label", has=box).click()
        assert box.is_checked() is on

    def choose(self, field, value):
        if self.p.locator(f'select[name="{field}"]').count():
            self.p.select_option(f'select[name="{field}"]', value)
        else:
            self.p.check(f'input[name="{field}"][value="{value}"]', force=True)

    def click(self, label):
        with self.p.expect_navigation():
            self.p.get_by_role("button", name=label, exact=True).click()


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
            run_script(Browser(page), SCRIPT)
            assert errors == []
        finally:
            chromium.close()


# -- console ------------------------------------------------------------------

class Console:
    name = "console"

    def __init__(self, app, pilot):
        self.app, self.pilot = app, pilot

    def _visible(self, w):
        return all(getattr(n, "display", True) for n in [w, *w.ancestors])

    def _field(self, name, types):
        return [w for w in self.app.query(types) if getattr(w, "_quantum_name", None) == name][0]

    def text(self):
        from textual.widgets import Button, Checkbox, RadioButton, Static, Tab
        parts = []
        for w in self.app.query("*"):
            if not self._visible(w):
                continue
            if isinstance(w, (Checkbox, RadioButton)):
                parts.append(str(w.label))
            elif isinstance(w, Button):
                parts.append(str(w.label))
            elif isinstance(w, Tab):
                parts.append(str(w.label))
            elif isinstance(w, Static):
                parts.append(str(w.render()))
            if getattr(w, "border_title", None):
                parts.append(str(w.border_title))
        return " | ".join(parts)

    def image(self, alt):
        assert f"[{alt}]" in self.text()

    def progress(self, ident, value):
        from textual.widgets import ProgressBar
        assert self.app.query_one(f"#{ident}", ProgressBar).progress == value

    def values(self, expected):
        from textual.widgets import RadioSet
        for field, value in expected.items():
            w = self._field(field, "Input, Select, Checkbox, Switch, RadioSet")
            if isinstance(w, RadioSet):
                assert str(w.pressed_button.label) == value, field
            else:
                assert w.value == value, field

    def fill(self, field, value):
        self._field(field, "Input").value = value

    def check(self, field, on):
        self._field(field, "Checkbox, Switch").value = on

    def choose(self, field, value):
        from textual.widgets import RadioButton, RadioSet
        w = self._field(field, "Select, RadioSet")
        if isinstance(w, RadioSet):
            [b for b in w.query(RadioButton) if str(b.label) == value][0].value = True
        else:
            w.value = value

    def click(self, label):
        from textual.widgets import Button
        [b for b in self.app.query(Button) if str(b.label) == label][0].press()


def test_the_script_in_the_console(url):
    # UI-7
    from quantum.runtime.ui_console import ConsoleUI
    from tests.console_pilot import page_loaded

    async def main():
        app = ConsoleUI(url)
        async with app.run_test(size=(160, 120)) as pilot:
            await page_loaded(app, pilot)
            driver = Console(app, pilot)
            for step in SCRIPT:
                before = app.pages_loaded
                run_script(driver, [step])
                if step[0] == "click":          # a click posts an action: wait for ITS page
                    await page_loaded(app, pilot, before)
                else:
                    await pilot.pause()

    asyncio.run(main())


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
    pressed with Enter (a row's button through its table: a row, a column)."""
    name = "pixel"

    def __init__(self, screen):
        self.s = screen

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
        buttons = [i for i in self.window()["items"] if i["kind"] in ("button", "link") and i.get("label") == label]
        if buttons:
            self._focus(lambda i: i["kind"] in ("button", "link") and i.get("label") == label)
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
        run_script(Pixel(screen), SCRIPT)
        # Esc closes the page; the page's runtime ends with it
        screen.request({"op": "act", "tap": ["escape"]})
        runtime.join(10)
        assert not runtime.is_alive()
    finally:
        screen.end()
