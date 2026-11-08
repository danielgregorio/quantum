"""One script, every renderer: the steps are data, each renderer has a driver that knows how to do them.

Used by tests/apps/test_ui_parity_script.py (the Core set of ui:*, UI-7, in the browser, the console, the
Hive's screen and the TUI),
tests/apps/test_settings.py and tests/apps/test_kanban_everywhere.py (one
application in each of its versions, UI-18). A step is a tuple: ("sees", [texts]), ("does_not_see",
[texts]), ("visit", path), ("fill", field, value), ("click", button),
("follow", link), ("click_in", card, button), ("follow_in", card, link),
("tab", title), ("waits_for", text), ("motions", [(kind, speed, what), ...]) — the
motions the page ran (UI-19) —, ("api", method, path, json, status[, [texts]]) — another
program calling the application's API (q:endpoint, API-1) beside the page, with a session of
its own —, and the parity script's own (image, progress, values, check, choose).
"""

import asyncio
import os
import time

import requests

# The steps that load a page: the driver waits for it before the next step.
LOADS_A_PAGE = {"click", "follow", "click_in", "follow_in"}
WAIT = 15          # seconds: a guard for waits_for, never a pause


def run_script(driver, script):
    for step, *args in script:
        if step == "sees":
            text = driver.text()
            missing = [t for t in args[0] if t not in text]
            assert not missing, f"{driver.name}: does not show {missing}"
        elif step == "does_not_see":
            text = driver.text()
            assert not [t for t in args[0] if t in text], f"{driver.name}: shows {args[0]}"
        elif step == "motions":
            # UI-19: the motions the page ran since it was shown, the same list in every renderer
            ran = [(m["kind"], m["speed"], m["what"]) for m in driver.motions()]
            assert ran == args[0], f"{driver.name}: ran {ran}"
        elif step == "api":
            # API-1: another program calls the application's API while the page is open; its own cookies
            method, path, body, status, *shows = args
            client = driver.__dict__.setdefault("api_client", requests.Session())
            response = client.request(method, driver.base_url() + path, json=body, timeout=30)
            assert response.status_code == status, \
                f"{driver.name}: {method} {path} answered {response.status_code}: {response.text[:300]}"
            missing = [t for t in (shows[0] if shows else []) if t not in response.text]
            assert not missing, f"{driver.name}: {method} {path} does not answer {missing}"
        else:
            getattr(driver, step)(*args)


# -- browser ------------------------------------------------------------------

class Browser:
    name = "browser"

    def __init__(self, page, base_url=""):
        self.p, self.base = page, base_url.rstrip("/")

    def text(self):
        return self.p.inner_text("body")

    def base_url(self):
        return self.base

    def visit(self, path):
        self.p.goto(self.base + path)

    def motions(self):
        return self.p.evaluate("window.quantumMotions || []")

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
        self.p.locator(f'[name="{field}"]:visible').fill(value)

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

    def _go(self, target):
        with self.p.expect_navigation():
            target.click()

    def _button(self, within, label):
        # a tab's header is a button too: "Ask" the tab is not "Ask" the form's button
        return within.get_by_role("button", name=label, exact=True).and_(self.p.locator(":not(.q-tab-header)"))

    def click(self, label):
        self._go(self._button(self.p, label))

    def follow(self, label):
        # UI-21: a menu's option or a tree's row with an action is a link that posts: a button in a form
        posts = self.p.get_by_role("button", name=label, exact=True).and_(self.p.locator(".q-link-action"))
        self._go(self.p.get_by_role("link", name=label, exact=True).or_(posts))

    def _card(self, title):
        return self.p.locator(".q-card").filter(has=self.p.locator(".q-card-title", has_text=title))

    def click_in(self, card, label):
        self._go(self._button(self._card(card), label))

    def follow_in(self, card, label):
        self._go(self._card(card).get_by_role("link", name=label, exact=True))

    def tab(self, title):
        self.p.locator(".q-tab-header", has_text=title).click()

    def waits_for(self, text):
        self.p.wait_for_function("t => document.body.innerText.includes(t)", arg=text, timeout=WAIT * 1000)


# -- console ------------------------------------------------------------------

class Console:
    name = "console"

    def __init__(self, app, pilot):
        self.app, self.pilot = app, pilot

    def base_url(self):
        return self.app.base_url.rstrip("/")

    def _visible(self, w):
        return all(getattr(n, "display", True) for n in [w, *w.ancestors])

    def _field(self, name, types):
        return [w for w in self.app.query(types)
                if getattr(w, "_quantum_name", None) == name and self._visible(w)][0]

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

    def motions(self):
        return list(self.app.motions)

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

    def _press(self, within, label, link):
        from textual.widgets import Button
        buttons = [b for b in within.query(Button)
                   if str(b.label) == label and b.has_class("link") == link and self._visible(b)]
        assert buttons, f"console: no {'link' if link else 'button'} {label!r}"
        buttons[0].press()

    def click(self, label):
        self._press(self.app, label, link=False)

    def follow(self, label):
        self._press(self.app, label, link=True)

    def _card(self, title):
        cards = [w for w in self.app.query(".panel") if str(getattr(w, "border_title", "")) == title]
        assert cards, f"console: no card {title!r}"
        return cards[0]

    def click_in(self, card, label):
        self._press(self._card(card), label, link=False)

    def follow_in(self, card, label):
        self._press(self._card(card), label, link=True)

    def tab(self, title):
        from textual.widgets import TabbedContent, TabPane
        tabs = self.app.query_one(TabbedContent)
        tabs.active = [p for p in tabs.query(TabPane) if str(p._title) == title][0].id


def tui_godot():
    """Godot for the TUI's tests (UI-20): skipped without it, a failure where CI requires it."""
    import pytest
    from quantum.runtime.godot_bin import GodotNotFound, ensure_godot
    try:
        return ensure_godot()
    except GodotNotFound as exc:
        if os.environ.get("QUANTUM_GODOT_REQUIRED"):
            pytest.fail(str(exc))
        pytest.skip(str(exc))


class Tui:
    """The TUI drawn by Godot (UI-20), headless, through its play protocol (quantum/runtime/ui_tui.py):
    a button, a link or a tab is clicked with the mouse on its cell, a field clicked and typed into, a
    box clicked, a select opened and its option clicked."""
    name = "tui"

    def __init__(self, session):
        self.s = session

    def base_url(self):
        return self.s.url

    def text(self):
        return self.s.text(self.s.observe())

    def visit(self, path):
        self.s.visit(path)

    def motions(self):
        return self.s.observe()["motions"]

    def waits_for(self, text):
        self.s.wait(text, timeout=WAIT)

    def _field(self, field):
        found = self.s.items(where=lambda i: i.get("bind") == field and i["kind"] != "radio")
        assert found, f"tui: no field {field!r}"
        return found[0]

    def _click(self, item):
        self.s.click(item["x"], item["y"])

    def click(self, label):
        self._click(self.s.item("button", label))

    def follow(self, label):
        self._click(self.s.item("link", label))

    def click_in(self, card, label):
        self._click(self.s.item("button", label, card=card))

    def follow_in(self, card, label):
        self._click(self.s.item("link", label, card=card))

    def tab(self, title):
        self._click(self.s.item("tab", title))

    def fill(self, field, value):
        self._click(self._field(field))
        self.s.key("ctrl+u")              # what was there goes
        self.s.type(value)

    def check(self, field, on):
        box = self._field(field)
        if box["checked"] != on:
            self._click(box)
        assert self._field(field)["checked"] is on

    def choose(self, field, value):
        radios = self.s.items("radio", where=lambda i: i.get("bind") == field and i["value"] == value)
        if radios:
            self._click(radios[0])
            return
        select = self._field(field)
        self._click(select)                                  # the options open under it
        index = self.s.last["dropdown"].index(value)
        self.s.click(select["x"] + 1, select["y"] + 1 + index)

    def values(self, expected):
        for field, value in expected.items():
            radios = self.s.items("radio", where=lambda i: i.get("bind") == field)
            if radios:
                assert [r["value"] for r in radios if r["checked"]] == [value], field
            elif isinstance(value, bool):
                assert self._field(field)["checked"] is value, field
            else:
                assert self._field(field)["value"] == value, field

    def image(self, alt):
        assert alt in [i["alt"] for i in self.s.observe()["images"]]

    def progress(self, ident, value):
        assert any(p["id"] == ident and p["value"] == value for p in self.s.observe()["progress"])


async def run_console_script(app, pilot, script):
    """The script in the console: a step that loads a page waits for THAT page (tests/console_pilot.py)."""
    from tests.console_pilot import page_loaded
    driver = Console(app, pilot)
    for step in script:
        before = app.pages_loaded
        if step[0] == "visit":
            await app.load_page(step[1])
            await pilot.pause()
        elif step[0] == "waits_for":
            deadline = time.monotonic() + WAIT
            while step[1] not in driver.text():
                assert time.monotonic() < deadline, f"console: {step[1]!r} did not appear in {WAIT}s"
                await asyncio.sleep(0.05)
                await pilot.pause()
        else:
            run_script(driver, [step])
            if step[0] in LOADS_A_PAGE:
                await page_loaded(app, pilot, before)
            else:
                await pilot.pause()
