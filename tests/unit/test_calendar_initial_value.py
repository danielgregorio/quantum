"""A `ui:calendar`'s initial `value=` was erased on load.

The server renders the right selection in all three modes — `_calendar_settings`
splits the `value` by comma and builds `range_start`/`range_end`/`multiple`.
But CALENDAR_JS's `init` built the state like this:

    selected: options.value ? parseDate(options.value) : null,
    rangeStart: null,
    rangeEnd: null,
    multiple: [],

and called `render()`, which rewrites the calendar's `innerHTML`. That is:
with `mode="range" value="2026-01-05,2026-01-10"` the page showed the dates
marked for an instant and then went empty. `parseDate` also got the WHOLE
string, `"2026-01-05,2026-01-10"`, which becomes Invalid Date.

And `parseDate` read "2026-01-05" as midnight UTC while the rest of the module
uses the LOCAL getters: west of Greenwich the calendar marked a day earlier
than the server had rendered.

The JS here really runs, in node, against a minimal DOM — it is not an
assertion about the file's text.
"""

import json
import shutil
import subprocess

import pytest

from quantum.runtime.ui_html_templates import CALENDAR_JS

NODE = shutil.which('node')
pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")


def _state(options):
    """Runs the real init and returns the resulting state."""
    body = CALENDAR_JS.replace('<script>', '').replace('</script>', '')
    program = f"""
const window = globalThis;
const element = {{ innerHTML: '', querySelector: () => null,
                   querySelectorAll: () => [] }};
globalThis.document = {{ getElementById: () => element }};

{body}

__quantumCalendar.init('cal', {json.dumps(options)});
const s = __quantumCalendar.get('cal');
const iso = (d) => d ? d.getFullYear() + '-' +
    String(d.getMonth() + 1).padStart(2, '0') + '-' +
    String(d.getDate()).padStart(2, '0') : null;
console.log(JSON.stringify({{
    mode: s.mode,
    selected: iso(s.selected),
    rangeStart: iso(s.rangeStart),
    rangeEnd: iso(s.rangeEnd),
    multiple: s.multiple.map(iso),
    viewMonth: s.viewMonth,
    viewYear: s.viewYear,
    html: element.innerHTML,
}}));
"""
    result = subprocess.run([NODE, '--input-type=module', '-e', program],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout.strip().split('\n')[-1])


class TestRangeMode:
    def test_both_ends_of_the_range_survive_init(self):
        s = _state({'mode': 'range', 'value': '2026-01-05,2026-01-10'})
        assert s['rangeStart'] == '2026-01-05'
        assert s['rangeEnd'] == '2026-01-10'

    def test_the_rendered_grid_marks_the_range(self):
        s = _state({'mode': 'range', 'value': '2026-01-05,2026-01-10'})
        assert 'range-start' in s['html'], s['html'][:400]
        assert 'range-end' in s['html']
        assert 'in-range' in s['html']

    def test_only_the_start_works_too(self):
        s = _state({'mode': 'range', 'value': '2026-01-05'})
        assert s['rangeStart'] == '2026-01-05'
        assert s['rangeEnd'] is None

    def test_selected_does_not_get_the_whole_string(self):
        """parseDate("2026-01-05,2026-01-10") is Invalid Date."""
        s = _state({'mode': 'range', 'value': '2026-01-05,2026-01-10'})
        assert s['selected'] is None


class TestMultipleMode:
    def test_every_date_survives_init(self):
        s = _state({'mode': 'multiple',
                    'value': '2026-01-05,2026-01-10,2026-01-20'})
        assert s['multiple'] == ['2026-01-05', '2026-01-10', '2026-01-20']

    def test_the_grid_marks_them_all(self):
        s = _state({'mode': 'multiple', 'value': '2026-01-05,2026-01-10'})
        assert s['html'].count('selected') >= 2, s['html'][:400]

    def test_spaces_around_the_commas_do_not_get_in_the_way(self):
        s = _state({'mode': 'multiple', 'value': '2026-01-05 , 2026-01-10'})
        assert s['multiple'] == ['2026-01-05', '2026-01-10']


class TestSingleMode:
    def test_still_works(self):
        s = _state({'mode': 'single', 'value': '2026-01-05'})
        assert s['selected'] == '2026-01-05'
        assert s['rangeStart'] is None and s['multiple'] == []

    def test_the_view_opens_on_the_chosen_date_s_month(self):
        """It always opened on the CURRENT month, so the selection was invisible."""
        s = _state({'mode': 'single', 'value': '2020-03-15'})
        assert (s['viewYear'], s['viewMonth']) == (2020, 2)   # 2 = March

    def test_without_a_value_the_view_is_this_month(self):
        import datetime
        today = datetime.date.today()
        s = _state({'mode': 'single'})
        assert (s['viewYear'], s['viewMonth']) == (today.year, today.month - 1)

    def test_an_invalid_value_does_not_break_the_calendar(self):
        s = _state({'mode': 'single', 'value': 'not-a-date'})
        assert s['selected'] is None
        assert s['html'], "the calendar did not even render"


class TestTimeZone:
    """`new Date("2026-01-05")` is midnight UTC; formatDate uses local getters.
    West of Greenwich the date went back a day — and the server, which uses
    date.fromisoformat, does not. The two disagreed."""

    def test_the_date_read_is_the_date_written(self):
        s = _state({'mode': 'single', 'value': '2026-01-05'})
        assert s['selected'] == '2026-01-05'

    def test_the_first_day_of_the_year_does_not_fall_into_the_previous_year(self):
        s = _state({'mode': 'single', 'value': '2026-01-01'})
        assert s['selected'] == '2026-01-01'
        assert (s['viewYear'], s['viewMonth']) == (2026, 0)

    def test_a_date_with_a_time_is_still_accepted(self):
        s = _state({'mode': 'single', 'value': '2026-01-05T12:00:00'})
        assert s['selected'] == '2026-01-05'


class TestTheServerAndTheClientAgree:
    """The server's HTML and the JS state must mark the same dates."""

    def _server(self, source):
        from quantum.core.parser import QuantumParser
        from quantum.runtime.ui_html_adapter import UIHtmlAdapter
        app = QuantumParser(use_cache=False).parse(source)
        return UIHtmlAdapter().generate(app.ui_windows, app.ui_children, 'T')

    def test_range(self):
        html = self._server(
            '<q:application id="a" type="ui"><ui:window>'
            '<ui:calendar mode="range" value="2026-01-05,2026-01-10" />'
            '</ui:window></q:application>')
        assert 'range-start' in html and 'range-end' in html

        s = _state({'mode': 'range', 'value': '2026-01-05,2026-01-10'})
        assert 'range-start' in s['html'] and 'range-end' in s['html']

    def test_multiple(self):
        html = self._server(
            '<q:application id="a" type="ui"><ui:window>'
            '<ui:calendar mode="multiple" value="2026-01-05,2026-01-10" />'
            '</ui:window></q:application>')
        assert html.count('selected') >= 2

        s = _state({'mode': 'multiple', 'value': '2026-01-05,2026-01-10'})
        assert s['html'].count('selected') >= 2
