"""The TUI drawn by Godot (SPEC.md UI-20, PLAN_PLATFORMS.md Phase 3), headless through its play protocol.

What the parity script (tests/apps/test_ui_parity_script.py) and the Kanban's (tests/apps/test_kanban_everywhere.py)
do not reach: search as you type, an editable table, a file field with a dialog of its own, an image, wide
characters, the mouse and the wheel, the motions, a resize, a kind it does not draw, and of the tags with a state
of their own (UI-21) Esc, a modal that takes the clicks, a tip on the focus, a toast that stays on the screen,
a carousel that plays and a calendar's weeks, its days that cannot be picked and its keys. And the layout check:
each page laid out at a size is the same cells as its reference frame in tests/tui/frames/
(UPDATE_FRAMES=1 writes them again), and no element sits on another or past the right edge.
"""

import os
import sqlite3
from pathlib import Path

import pytest

FRAMES = Path(__file__).parent / 'frames'


@pytest.fixture
def tui(godot, app_url):
    from quantum.runtime.ui_tui import TuiSession
    url, _project = app_url
    with TuiSession(url, cols=100, rows=30, binary=godot) as session:
        yield session


def frame_matches(name: str, screen: list) -> None:
    """UI-20's layout check: the cells as they were laid out when the frame was written."""
    path = FRAMES / f'{name}.txt'
    text = '\n'.join(screen) + '\n'
    if os.environ.get('UPDATE_FRAMES') or not path.exists():
        FRAMES.mkdir(exist_ok=True)
        path.write_text(text, encoding='utf-8')
    assert text == path.read_text(encoding='utf-8'), f'{name}: the layout changed (UPDATE_FRAMES=1 writes it again)'


def no_overlaps(seen: dict) -> None:
    """Every element inside the screen's width, none over another."""
    taken = {}
    for item in seen['items']:
        assert item['x'] >= 0 and item['x'] + item['w'] <= seen['cols'], item
        for row in range(item['y'], item['y'] + max(1, item['h'])):
            for col in range(item['x'], item['x'] + max(1, item['w'])):
                assert (col, row) not in taken, f"{item['kind']} {item['label']!r} over {taken[(col, row)]}"
                taken[(col, row)] = f"{item['kind']} {item['label']!r}"


class TestTheCoreSet:
    """UI-12, UI-13, UI-14: what the Core set asks of a renderer, in the TUI."""

    def test_search_as_you_type_keeps_the_field_and_its_cursor(self, tui):
        field = tui.item('input', bind='q')
        tui.click(field['x'], field['y'])
        seen = tui.type('an')
        assert seen['path'] == '/?q=an' and 'Banana' in tui.text() and 'Apple' not in tui.text()
        field = tui.item('input', bind='q')
        assert field['focus'] and field['value'] == 'an'
        seen = tui.type('a')                                   # what is typed next adds to it
        assert seen['path'] == '/?q=ana' and tui.item('input', bind='q')['value'] == 'ana'

    def test_an_editable_cell_is_its_own_form(self, tui, app_url):
        cell = tui.item('input', bind='value', value='Apple')
        tui.click(cell['x'], cell['y'])
        tui.key('ctrl+u')
        tui.type('Apricot')
        tui.key('enter')
        rows = sqlite3.connect(app_url[1] / 'fruits.db').execute('SELECT name FROM fruits ORDER BY id').fetchall()
        assert rows == [('Apricot',), ('Banana',), ('Cherry',)]
        assert 'Apricot' in tui.text()

    def test_a_file_field_has_a_dialog_of_its_own_and_the_form_sends_the_file(self, tui, app_url, tmp_path):
        note = tmp_path / 'note.txt'
        note.write_text('hello', encoding='utf-8')
        tui.attach('doc', note)                                # chosen in the TUI's file dialog
        assert tui.item('file', bind='doc')['file'] == str(note)
        assert 'note.txt' in tui.text()
        send = tui.item('button', 'Send')
        tui.click(send['x'], send['y'])
        assert 'Got note.txt' in tui.text()
        assert (app_url[1] / 'uploads' / 'note.txt').read_text(encoding='utf-8') == 'hello'

    def test_an_image_is_drawn_where_the_page_has_it(self, tui):
        image, = tui.observe()['images']
        assert image['alt'] == 'Brick' and image['loaded'] is True
        assert (image['w'], image['h']) == (3, 2)             # 30 x 40 pixels in cells of 10 x 20


class TestTheScreen:
    """A terminal's look without its limits: wide characters, the mouse, the wheel, the motions, a resize."""

    def test_wide_characters_take_two_cells_and_the_box_stays_closed(self, tui):
        screen = tui.observe()['screen']
        top = next(r for r in screen if '日本の果物' in r)
        text = next(r for r in screen if 'りんご' in r)
        bottom = screen[screen.index(text) + 1]

        def cells(row):
            from unicodedata import east_asian_width
            return sum(2 if east_asian_width(c) in 'WF' else 1 for c in row)
        assert cells(top) == cells(text) == cells(bottom) == 99    # the right border in the same column

    def test_the_mouse_hovers_and_clicks_and_the_wheel_scrolls(self, tui):
        seen = tui.visit('/long')
        assert seen['height'] == 81 and seen['scroll'] == 0
        seen = tui.wheel(5)
        assert seen['scroll'] == 15
        field = tui.item('input', bind='last')
        seen = tui.click(field['x'], field['y'])               # out of view: scrolled to, then clicked
        assert seen['scroll'] > 50 and tui.item('input', bind='last')['focus']
        seen = tui.hover(field['x'], field['y'])
        assert seen['items'][seen['hover']]['bind'] == 'last' and seen['cursor'] == 'pointing'

    def test_the_page_and_its_elements_move_as_they_ask(self, tui):
        # UI-19: the window slides in, the field fades in, the same list the browser records
        assert tui.visit('/long')['motions'] == [{'kind': 'slide', 'speed': 'normal', 'what': 'page'},
                                                 {'kind': 'fade', 'speed': 'normal', 'what': 'input'}]

    def test_a_kind_it_does_not_draw_says_so(self, tui):
        # UI-7: never something else in its place (every ui:* tag is drawn: a newer server's kind)
        assert tui.observe()['unsupported'] == []
        assert tui.visit('/hologram')['unsupported'] == ['hologram']
        assert '[ui:hologram is not drawn in the TUI]' in tui.text() and 'Still drawn' in tui.text()

    def test_a_resize_lays_the_page_out_again(self, tui):
        seen = tui.resize(60, 20)
        assert seen['cols'] == 60 and max(len(r) for r in seen['screen']) <= 60
        no_overlaps(seen)


class TestTheTagsWithAState:
    """UI-21: what the parity script's STATE does not reach: Esc, a modal that takes the clicks, a tooltip's tip
    on the focus, a toast that stays on the screen as the page scrolls, a carousel that plays, a calendar's weeks
    from another day with their numbers, its days that cannot be picked and its keys."""

    def test_a_modal_takes_the_clicks_until_esc_closes_it(self, tui):
        tui.visit('/layers')
        field = tui.item('input', bind='name')
        assert field['covered']
        tui.click(field['x'], field['y'])                      # under the modal: nothing takes the click
        assert not tui.item('input', bind='name')['focus'] and 'Type a name' not in tui.text()
        seen = tui.key('escape')
        assert 'In the modal' not in tui.text()
        assert [layer['kind'] for layer in seen['layers']] == ['tip', 'toast']    # the mouse is over the field
        tui.hover(0, 10)
        assert 'Type a name' not in tui.text()
        tui.key('tab')                                         # the tip shows on the focus too
        assert tui.item('input', bind='name')['focus'] and 'Type a name' in tui.text()

    def test_a_toast_stays_on_the_screen_and_a_carousel_plays(self, tui):
        tui.visit('/layers')
        tui.key('escape')
        seen = tui.wheel(5)
        toast, = [layer for layer in seen['layers'] if layer['kind'] == 'toast']
        assert seen['scroll'] == 15 and toast['y'] + toast['h'] == seen['scroll'] + seen['rows']
        assert 'Kept' in tui.text()
        tui.wait('Two')                                        # its interval past, the next slide

    def test_a_calendar_s_days_that_cannot_be_picked_and_its_keys(self, tui):
        seen = tui.visit('/dates')
        pages = seen['pages']
        title = tui.item('calendar')
        assert (title['label'], title['value']) == ('March 2026', '2026-03-04')
        rows = seen['screen'][title['y'] + 1:title['y'] + 4]
        # the weeks from Monday, each with its ISO number: March 1st 2026 is the Sunday of week 9
        assert [row.strip(' │').split() for row in rows] == [
            ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'], ['9', '1'], ['10', '2', '3', '4', '5', '6', '7', '8']]
        # drawn, but not to be picked: before min-date, a disabled date, the weekends (disabled-days)
        assert [d['label'] for d in tui.items('day')] == [
            '3', '4', '5', '6', '9', '10', '11', '13', '16', '17', '18', '19', '20', '23', '24', '25', '26', '27',
            '30', '31']
        friday = tui.item('day', '6')
        tui.click(friday['x'] + 3, friday['y'])                # Saturday the 7th: nothing takes the click
        assert tui.item('calendar')['value'] == '2026-03-04'
        eleven = tui.item('day', '11')
        tui.click(eleven['x'], eleven['y'])                    # outside a form a day picked is only marked
        assert tui.item('calendar')['value'] == '2026-03-11' and tui.item('day', '11')['selected']
        assert tui.observe()['pages'] == pages
        # the arrows move the focus over the days that cannot be picked, into the next month; Enter picks
        tui.key('right', 'right')
        assert tui.item('day', '16')['focus']
        tui.key('enter', 'down', 'down', 'down')
        title = tui.item('calendar')
        assert (title['label'], title['value']) == ('April 2026', '2026-03-16')
        assert tui.item('day', '6')['focus'] and tui.item('day', '6')['date'] == '2026-04-06'
        tui.key('down')                                        # past max-date: nothing to move to
        assert tui.item('day', '6')['focus']
        tui.key('tab')                                         # Tab leaves the days, to what follows them
        assert tui.item('month', 'Previous month')['focus']


class TestTheLayout:
    """UI-20's layout check: the same page at the same size gives the same cells."""

    @pytest.mark.parametrize('size', [(120, 40), (70, 30)])
    def test_the_showcase(self, godot, size):
        from tests.apps.test_ui_parity_script import SHOWCASE
        from quantum.runtime.ui_tui import TuiSession
        import logging
        import shutil
        import tempfile
        import threading
        from werkzeug.serving import make_server
        from quantum.runtime.web_server import QuantumWebServer
        project = Path(tempfile.mkdtemp()) / 'showcase'
        shutil.copytree(SHOWCASE, project, ignore=shutil.ignore_patterns('__pycache__', 'logs'))
        here = os.getcwd()
        os.chdir(project)
        logging.disable(logging.WARNING)
        server = make_server('127.0.0.1', 0, QuantumWebServer(str(project / 'quantum.config.yaml')).app, threaded=True)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with TuiSession(f'http://127.0.0.1:{server.server_port}/', cols=size[0], rows=size[1], binary=godot) as tui:
                seen = tui.observe()
                no_overlaps(seen)
                frame_matches(f'showcase-{size[0]}x{size[1]}', seen['screen'])
        finally:
            server.shutdown()
            os.chdir(here)
            logging.disable(logging.NOTSET)
            shutil.rmtree(project.parent, ignore_errors=True)

    def test_the_fruits(self, tui):
        seen = tui.observe()
        no_overlaps(seen)
        frame_matches('fruits-100x30', seen['screen'])


class TestTouch:
    """Phase 6: the phone's TUI (--touch here; a phone's export turns it on): a tap clicks where the finger was, a
    drag scrolls and clicks nothing, a field with the focus asks for the system's keyboard."""

    @pytest.fixture
    def finger(self, godot, app_url):
        from quantum.runtime.ui_tui import TuiSession
        url, _project = app_url
        with TuiSession(url, cols=60, rows=20, binary=godot, touch=True) as session:
            yield session

    def test_a_tap_on_a_field_asks_for_the_keyboard_and_types_into_it(self, finger):
        seen = finger.observe()
        assert seen['touch'] and not seen['keyboard'] and seen['status'] == 'tap to act · drag to scroll'
        field = finger.item('input', bind='q')
        seen = finger.tap(field['x'], field['y'])
        assert seen['keyboard'] and finger.item('input', bind='q')['focus']
        seen = finger.type('an')
        assert finger.item('input', bind='q')['value'] == 'an'

    def test_a_drag_scrolls_and_clicks_nothing(self, finger):
        seen = finger.visit('/long')
        assert seen['scroll'] == 0
        seen = finger.drag(2, 5, 10)
        assert seen['scroll'] == 10 and seen['path'] == '/long'
        seen = finger.drag(2, 15, -4)                                  # back up
        assert seen['scroll'] == 6

    def test_a_tap_on_a_field_out_of_view_scrolls_to_it(self, finger):
        finger.visit('/long')
        field = finger.item('input', bind='last')
        seen = finger.tap(field['x'], field['y'])                      # scrolled into view, then tapped
        assert finger.item('input', bind='last')['focus'] and seen['keyboard']
