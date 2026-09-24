"""Driving `quantum console` (ConsoleUI) from a test: wait for what an action asked for, never for a time.

A pilot's pause() waits for the messages queued when it was called. A button's
Pressed message then bubbles to the app as NEW messages, so the pause could
return before the app had even started the page load the click asked for:
`page_loading` was still False, the wait ended, and the next assertion read the
old page (tests/apps/test_ui_parity_script.py failed that way under -n auto).
ConsoleUI counts finished loads (pages_loaded); these helpers wait for the
count to pass the value read BEFORE the action.
"""

import time

HANG = 30          # seconds: only a guard against a load that never finishes


async def page_loaded(app, pilot, before: int = 0) -> None:
    """Until a page load finished after `before` loads, and its widgets are mounted."""
    deadline = time.monotonic() + HANG
    while app.pages_loaded <= before:
        assert time.monotonic() < deadline, f'no page load finished in {HANG}s'
        await pilot.pause(0.01)
    await pilot.pause()


async def searched(app, pilot, name: str, value: str) -> None:
    """Until the search as you type for `value` in field `name` is drawn, with the focus back.

    Not a count of loads: typing "ba" with a pause longer than the field's
    delay after "b" searches "b" first, and a wait for "a load" ended there —
    the page still said "Found: 4" (UI-12, under -n auto).
    """
    deadline = time.monotonic() + HANG
    while app.last_search != (name, value):
        assert time.monotonic() < deadline, f'the search for {value!r} did not finish in {HANG}s'
        await pilot.pause(0.01)
    await pilot.pause()


async def press(app, pilot, button) -> None:
    """Press a button that loads a page (an action, a link) and wait for that page."""
    before = app.pages_loaded
    button.press()
    await page_loaded(app, pilot, before)


async def enter(app, pilot) -> None:
    """Press Enter in the focused field (it submits a form) and wait for the page it loads."""
    before = app.pages_loaded
    await pilot.press('enter')
    await page_loaded(app, pilot, before)
