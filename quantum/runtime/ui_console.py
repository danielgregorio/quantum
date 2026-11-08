"""The console renderer: a Quantum page as a terminal app (UI-3).

`quantum console` starts the application's server in this process and opens a
Textual app on it. The app asks each page for its view tree
(quantum/runtime/ui_view.py) instead of HTML, draws it with Textual widgets,
and sends the same q:action posts a browser sends — with a cookie jar, so
login, validation, flash and redirects are exactly the web's. Nothing of the
page's logic is translated: the runtime that serves the browser serves this.
"""

import asyncio
import calendar
import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests
from rich.style import Style
from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (Button, Checkbox, Collapsible, Input, ProgressBar, RadioButton, RadioSet,
                             Select, Static, Switch, TabbedContent, TabPane, TextArea)

from quantum.runtime.ui_more import MONTHS
from quantum.runtime.ui_motion import TerminalMotion, of_props, record

VIEW = 'application/vnd.quantum.view+json'

# UI-2 in a terminal: the breakpoints in columns (a column is ~8 px).
BREAKPOINT_COLUMNS = {'sm': 80, 'md': 96, 'lg': 128}


def _checked(value) -> bool:
    """UI-6: checked="true", or an expression that resolved to a true value."""
    return value is not None and str(value).strip().lower() in ('true', '1', 'on', 'yes', 'checked')


def _number(value, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _flag(value, default: bool) -> bool:
    """A yes or a no of the view (a bool, or the text of an expression); not given, the default."""
    return default if value is None or value == '' else _checked(value)


def _index(value, total: int) -> int:
    """Which of `total` is shown first (a carousel's slide, a stepper's step): `current`, kept in range."""
    return max(0, min(int(_number(value, 0)), total - 1)) if total else 0


def styled_text(text: str, props: dict) -> Text:
    """A text with its look: bold, a heading, code, a quote, muted (UI-21: a Markdown text's blocks), and
    its spans (bold, italic, code, a link's target in brackets — a terminal cannot follow it)."""
    base = 'bold' if props.get('weight') == 'bold' or props.get('heading') else ''
    if props.get('code'):
        return Text(text, style='dim')
    spans = props.get('spans')
    out = Text('│ ' if props.get('quote') else '', style='dim')
    if not spans:
        out.append(text, style=('italic ' if props.get('quote') else '') + base)
        return out
    for span in spans:
        style = ' '.join(filter(None, [base, 'bold' if span.get('bold') else '', 'italic' if span.get('italic') else '',
                                       'reverse' if span.get('code') else '', 'underline' if span.get('to') else '']))
        out.append(span['text'], style=style)
        if span.get('to'):
            out.append(f" ({span['to']})", style='dim')
    return out


class ChartBars(Static):
    """UI-21: a chart as a terminal draws one — a row a label, a bar as long as its share, its value (a pie's
    or a doughnut's share in percent)."""

    def __init__(self, node: dict, id=None):
        super().__init__('', classes='chart', id=id)
        self._node = node

    def render(self):
        props, bars = self._node.get('props') or {}, self._node.get('bars') or []
        share = props.get('chart_type') in ('pie', 'doughnut')
        out = Text()
        if props.get('title'):
            out.append(str(props['title']) + '\n', style='bold')
        names = max([len(b['label']) for b in bars] or [0])
        shown = [f"{b['percent']:g}%" if share else b['shown'] for b in bars]
        room = max(4, (self.size.width or 40) - names - max([len(v) for v in shown] or [0]) - 2)
        for n, (bar, value) in enumerate(zip(bars, shown)):
            out.append(bar['label'].ljust(names) + ' ')
            out.append('█' * max(1 if bar['percent'] else 0, round(room * bar['percent'] / 100)),
                       style=_chart_color(bar['color']))
            out.append(' ' + value + ('\n' if n < len(bars) - 1 else ''))
        return out


def _chart_color(color: str) -> str:
    return {'primary': 'blue', 'secondary': 'grey50', 'success': 'green', 'danger': 'red', 'warning': 'yellow',
            'info': 'cyan'}.get(color, color if color.startswith('#') or color.isalpha() else 'blue')


class Skeleton(Static):
    """UI-21: a skeleton — lines of shade where text is coming; a circle, a block."""

    def __init__(self, props: dict, id=None):
        super().__init__('', classes='skeleton', id=id)
        self._props = props

    def render(self):
        width = max(4, self.size.width or 40)
        variant = self._props.get('variant') or 'text'
        if variant == 'circle':
            return Text('(░░)', style='dim')
        lines = int(self._props.get('lines') or 1) if variant == 'text' else 3
        rows = ['░' * (width if n < lines - 1 or lines == 1 else max(1, width * 3 // 5)) for n in range(lines)]
        return Text('\n'.join(rows), style='dim')


class Loading(Static):
    """UI-21: a loading mark, turning, and what is loading."""
    FRAMES = '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'

    def __init__(self, text: str, id=None):
        super().__init__(f'{self.FRAMES[0]} {text}', classes='text', id=id)
        self._text, self._frame = text, 0

    def on_mount(self) -> None:
        self.set_interval(0.1, self._turn)

    def _turn(self) -> None:
        self._frame = (self._frame + 1) % len(self.FRAMES)
        self.update(f'{self.FRAMES[self._frame]} {self._text}')


# -- the tags with a state of their own (UI-21): the state is the console's, as it is the browser's ----------

class PageModal(ModalScreen):
    """UI-21: an open ui:modal, above the page, which it takes the focus from: its title, its content and,
    when `closable`, a close control (Esc too). Closed, it is gone until the page is loaded again."""

    BINDINGS = [Binding('escape', 'close', 'Close', show=False)]
    WIDTHS = {'sm': 40, 'md': 60, 'lg': 80, 'xl': 100, 'full': '100%'}

    def __init__(self, props: dict, content: List):
        super().__init__()
        self.modal_title = str(props.get('title') or '')
        self.closable = _flag(props.get('closable'), True)
        self._content, self._props = content, props

    def compose(self) -> ComposeResult:
        header = [Static(Text(self.modal_title, style='bold'), classes='modal-title')] if self.modal_title else []
        if self.closable:
            header.append(Button('✕', classes='link modal-close'))
        dialog = Vertical(*([Horizontal(*header, classes='modal-header')] if header else []),
                          Vertical(*self._content, classes='vbox modal-body'),
                          classes='modal', id=self._props.get('ui_id'))
        dialog.styles.width = self.WIDTHS.get(str(self._props.get('size') or ''), 60)
        yield dialog

    def check_action(self, action: str, parameters) -> bool:
        return self.closable if action == 'close' else True

    def action_close(self) -> None:
        self.dismiss()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.has_class('modal-close'):
            event.stop()
            self.dismiss()


TOAST_ICONS = {'info': 'ⓘ', 'success': '✓', 'warning': '⚠', 'danger': '✗'}


class PageToast(Vertical):
    """UI-21: a toast — its title and message for `duration` ms (0: until the page is loaded again), then
    gone; `dismissible` gives it a close control."""

    def __init__(self, props: dict):
        variant = str(props.get('variant') or 'info')
        title, message = str(props.get('title') or ''), str(props.get('message') or '')
        # its icon and title on the first line, its message under them; without a title, the message there
        first = Text(f"{props.get('icon') or TOAST_ICONS.get(variant, TOAST_ICONS['info'])} ", style='bold')
        first.append(title or message, style='bold' if title else '')
        header = [Static(first, classes='toast-title')]
        if _flag(props.get('dismissible'), True):
            header.append(Button('✕', classes='link toast-close'))
        super().__init__(Horizontal(*header, classes='toast-header'),
                         *([Static(Text(message), classes='toast-message')] if title and message else []),
                         classes=f'toast toast-{variant}', id=props.get('ui_id'))
        self._ms = _number(props.get('duration'), 3000)

    def on_mount(self) -> None:
        if self._ms > 0:
            self.set_timer(self._ms / 1000, self.go)

    def go(self) -> None:
        (self.parent if self.parent is not None and self.parent.has_class('toast-holder') else self).remove()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.has_class('toast-close'):
            event.stop()
            self.go()


class TipBox(Vertical):
    """UI-21: a tooltip — its children drawn; its tip shown under them only while they are pointed at or
    have the focus."""

    def __init__(self, tip: str, children: List, id=None):
        self.tip = Static(Text(tip), classes='tip')
        self.tip.display = False
        super().__init__(*children, self.tip, classes='tipbox', id=id)

    def _update(self) -> None:
        self.tip.display = self.is_mouse_over or self.has_focus_within

    def on_enter(self, event: events.Enter) -> None:
        self._update()

    def on_leave(self, event: events.Leave) -> None:
        self.call_after_refresh(self._update)

    def on_descendant_focus(self, event: events.DescendantFocus) -> None:
        self._update()

    def on_descendant_blur(self, event: events.DescendantBlur) -> None:
        self.call_after_refresh(self._update)


class Dropdown(Vertical):
    """UI-21: a dropdown — a button with its label that opens its options; an option posts its action (a
    link with an event, as a menu's); Esc, or the focus going elsewhere, closes them."""

    BINDINGS = [Binding('escape', 'close', 'Close', show=False)]

    def __init__(self, label: str, options: List, id=None):
        self.label = label
        self.trigger = Button(f'{label} ▾', classes='dropdown-trigger')
        self.menu = Vertical(*options, classes='dropdown-menu')
        self.menu.display = False
        super().__init__(self.trigger, self.menu, classes='dropdown', id=id)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button is not self.trigger:
            return                  # an option: its action goes on to the app
        event.stop()
        self.menu.display = not self.menu.display
        options = [b for b in self.menu.query(Button) if b.focusable]
        if self.menu.display and options:
            options[0].focus()

    def check_action(self, action: str, parameters) -> bool:
        return self.menu.display if action == 'close' else True

    def action_close(self) -> None:
        self.menu.display = False
        self.trigger.focus()

    def on_descendant_blur(self, event: events.DescendantBlur) -> None:
        self.call_after_refresh(self._close_when_left)

    def _close_when_left(self) -> None:
        if not self.has_focus_within:
            self.menu.display = False


class Carousel(Vertical):
    """UI-21: a carousel — one slide at a time (`current`), the arrows for the previous and the next (looping
    when `loop`), a dot for each slide that goes to it; `auto-play` moves it every `interval` ms, not while
    the mouse is over it."""

    def __init__(self, slides: List, props: dict, id=None):
        self.slides = slides
        self.current = _index(props.get('current'), len(slides))
        self.loop = _flag(props.get('loop'), True)
        self._auto = _flag(props.get('auto_play'), False) and len(slides) > 1
        self._interval = max(0.1, _number(props.get('interval'), 5000) / 1000)
        self.prev = self.next = None
        self.dots: List[Button] = []
        if len(slides) > 1 and _flag(props.get('show_arrows'), True):
            self.prev, self.next = Button('‹', classes='link carousel-prev'), Button('›', classes='link carousel-next')
        if len(slides) > 1 and _flag(props.get('show_indicators'), True):
            self.dots = [Button('○', classes='link carousel-dot') for _ in slides]
        controls = [w for w in [self.prev, *self.dots, self.next] if w is not None]
        super().__init__(*slides, *([Horizontal(*controls, classes='hbox carousel-controls')] if controls else []),
                         classes='vbox carousel', id=id)
        self._show()

    def on_mount(self) -> None:
        if self._auto:
            self.set_interval(self._interval, self._tick)

    def _tick(self) -> None:
        if not self.is_mouse_over:
            self.go(self.current + 1)

    def go(self, index: int) -> None:
        total = len(self.slides)
        if index < 0:
            index = total - 1 if self.loop else 0
        elif index >= total:
            index = 0 if self.loop else total - 1
        self.current = index
        self._show()

    def _show(self) -> None:
        for n, slide in enumerate(self.slides):
            slide.display = n == self.current
        for n, dot in enumerate(self.dots):
            dot.label = '●' if n == self.current else '○'
        if self.prev is not None and not self.loop:
            self.prev.disabled = self.current == 0
            self.next.disabled = self.current == len(self.slides) - 1

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button = event.button
        if button is self.prev:
            self.go(self.current - 1)
        elif button is self.next:
            self.go(self.current + 1)
        elif button in self.dots:
            self.go(self.dots.index(button))
        else:
            return                  # a button in a slide: its action goes on to the app
        event.stop()


class Stepper(Vertical):
    """UI-21: a stepper — the steps' titles in a row (a column when `orientation="vertical"`), the current one
    marked, a done one checked; only the current step's content; Back and Next move between them, Next marking
    the step done, as the browser's do. In a `linear` stepper a step after the current one opens only when the
    current one is done; `clickable` makes the titles go to their step."""

    def __init__(self, steps: List[dict], contents: List, props: dict, id=None):
        self.steps, self.contents = steps, contents
        self.current = _index(props.get('current'), len(steps))
        self.linear = _flag(props.get('linear'), True)
        clickable = _flag(props.get('clickable'), False)
        # the explicit `completed` wins; without it, a step behind the current one is done (completed_step_indices)
        self.done = {n for n, step in enumerate(steps)
                     if (_checked(step.get('completed')) if step.get('completed') is not None else n < self.current)}
        self.titles = [Button('', classes='link step-title') if clickable else Static('', classes='step-title')
                       for _ in steps]
        cells = []
        for title, step in zip(self.titles, steps):
            notes = [Static(Text(str(step['description']), style='dim'))] if step.get('description') else []
            if _checked(step.get('optional')):
                notes.append(Static(Text('Optional', style='dim italic')))
            if step.get('error'):
                notes.append(Static(Text(str(step['error'])), classes='field-error'))
            cells.append(Vertical(title, *notes, classes='step'))
        header = (Vertical if props.get('orientation') == 'vertical' else Horizontal)(*cells, classes='stepper-header')
        self.back = Button('Back', classes='stepper-back')
        self.forward = Button('Next', variant='primary', classes='stepper-next')
        super().__init__(header, *contents, Horizontal(self.back, self.forward, classes='hbox stepper-nav'),
                         classes='vbox stepper', id=id)
        self._show()

    def _can_go(self, index: int) -> bool:
        if not 0 <= index < len(self.steps):
            return False
        if not self.linear or index <= self.current:
            return True
        return index == self.current + 1 and self.current in self.done

    def go(self, index: int) -> None:
        if self._can_go(index):
            self.current = index
        self._show()

    def _title(self, n: int) -> Text:
        step, current = self.steps[n], n == self.current
        if step.get('error'):
            mark, style = '✗', 'bold red'
        elif n in self.done and not current:
            mark, style = '✓', 'bold green'
        else:
            mark, style = str(step.get('icon') or n + 1), 'bold' if current else 'dim'
        out = Text(f' {mark} ', style=style + (' reverse' if current else ''))
        out.append(' ' + str(step.get('title') or ''), style='bold' if current else '')
        return out

    def _show(self) -> None:
        for n, (title, content) in enumerate(zip(self.titles, self.contents)):
            if isinstance(title, Button):
                title.label = self._title(n)
            else:
                title.update(self._title(n))
            content.display = n == self.current
        self.back.disabled = self.current == 0

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button = event.button
        if button is self.back:
            self.go(self.current - 1)
        elif button is self.forward:
            self.done.add(self.current)
            self.go(self.current + 1)
        elif button in self.titles:
            self.go(self.titles.index(button))
        else:
            return                  # a button in a step: its action goes on to the app
        event.stop()


WEEKDAYS = ('Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa')


def _iso_date(text) -> Optional[datetime.date]:
    try:
        return datetime.date.fromisoformat(str(text or '').strip())
    except ValueError:
        return None


class PageCalendar(Vertical):
    """UI-21: a calendar is a date field shown as a month — its title ("November 2026") between the arrows to
    the previous and the next month, which move it here, as the browser's do; the weekdays from `first_day`;
    the days of the month, the one picked marked. A day before `min`, after `max`, in `disabled_dates` or on
    a weekday of `disabled_days` is dimmed and cannot be picked. The day picked is the field's value: its form
    sends it under `bind` (ConsoleUI._form_fields); outside a form, picking only marks it."""

    def __init__(self, props: dict, id=None):
        today = datetime.date.today()
        self._quantum_name = props.get('bind') or None
        picked = _iso_date(props.get('value'))
        self.value = picked.isoformat() if picked else ''
        month = _iso_date(f"{props.get('month') or ''}-01") or picked or today
        self.shown = month.replace(day=1)
        self.min_date, self.max_date = _iso_date(props.get('min')), _iso_date(props.get('max'))
        self.disabled_dates = {d for d in map(_iso_date, props.get('disabled_dates') or []) if d}
        self.disabled_days = {int(d) % 7 for d in props.get('disabled_days') or [] if str(d).lstrip('-').isdigit()}
        self.first_day = int(_number(props.get('first_day'), 0)) % 7
        self.week_numbers = _flag(props.get('week_numbers'), False)
        # the keyboard's day, in the month shown: the one picked, else today, else the first
        self.cursor = next(d for d in (picked, today, self.shown) if d and d.replace(day=1) == self.shown)
        self.prev = Button('‹', classes='link calendar-nav calendar-prev')
        self.next = Button('›', classes='link calendar-nav calendar-next')
        self.prev.tooltip, self.next.tooltip = 'Previous month', 'Next month'
        self.heading = Static('', classes='calendar-title')
        self.days = CalendarDays(self)
        header = Horizontal(self.prev, self.heading, self.next, classes='calendar-header')
        header.styles.width = self.days.WIDTH + (3 if self.week_numbers else 0)
        super().__init__(header, self.days, classes='calendar', id=id)
        self._show()

    def can_pick(self, day: datetime.date) -> bool:
        weekday = (day.weekday() + 1) % 7                   # 0 = Sunday, as the view says
        return not ((self.min_date and day < self.min_date) or (self.max_date and day > self.max_date)
                    or day in self.disabled_dates or weekday in self.disabled_days)

    def weeks(self) -> List[List[datetime.date]]:
        """The month shown, a week a row from `first_day`, always six rows: the grid does not jump as it moves.
        A day of another month is in its row (the row's week number is its first day's, as the browser's) and
        drawn blank."""
        # calendar.Calendar counts 0 = Monday; the view, 0 = Sunday
        weeks = calendar.Calendar((self.first_day + 6) % 7).monthdatescalendar(self.shown.year, self.shown.month)
        while len(weeks) < 6:
            last = weeks[-1][-1]
            weeks.append([last + datetime.timedelta(days=n) for n in range(1, 8)])
        return weeks

    def go_month(self, step: int) -> None:
        months = self.shown.year * 12 + self.shown.month - 1 + step
        self.shown = datetime.date(months // 12, months % 12 + 1, 1)
        if (self.cursor.year, self.cursor.month) != (self.shown.year, self.shown.month):
            # the keyboard's day keeps its number, within the new month's length
            length = calendar.monthrange(self.shown.year, self.shown.month)[1]
            self.cursor = self.shown.replace(day=min(self.cursor.day, length))
        self._show()

    def move_cursor(self, days: int) -> None:
        self.cursor += datetime.timedelta(days=days)
        if self.cursor.replace(day=1) != self.shown:
            self.shown = self.cursor.replace(day=1)
        self._show()

    def pick(self, day: datetime.date) -> bool:
        """Picks `day` (the field's value), unless it cannot be picked."""
        self.cursor = day
        if day.replace(day=1) == self.shown and self.can_pick(day):
            self.value = day.isoformat()
        self._show()
        return self.value == day.isoformat()

    def _show(self) -> None:
        self.heading.update(Text(f'{MONTHS[self.shown.month - 1]} {self.shown.year}', style='bold'))
        self.days.refresh(layout=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button is self.prev:
            self.go_month(-1)
        elif event.button is self.next:
            self.go_month(1)
        else:
            return
        event.stop()                # the month moves here, never through the server


class CalendarDays(Static):
    """UI-21: a calendar's grid — the weekdays, then six rows of days (`cal`'s layout: a day two columns, a
    space between). A click picks the day under the mouse; with the focus, the arrows move a cursor (into the
    next or the previous month), Page Up and Page Down move the month, Enter or Space picks."""

    WIDTH = 7 * 3 - 1
    can_focus = True
    COMPONENT_CLASSES = {'calendar--weekday', 'calendar--week', 'calendar--today', 'calendar--selected',
                         'calendar--disabled', 'calendar--cursor'}
    BINDINGS = [
        Binding('left', 'move(-1)', 'Previous day', show=False),
        Binding('right', 'move(1)', 'Next day', show=False),
        Binding('up', 'move(-7)', 'Previous week', show=False),
        Binding('down', 'move(7)', 'Next week', show=False),
        Binding('pageup', 'month(-1)', 'Previous month', show=False),
        Binding('pagedown', 'month(1)', 'Next month', show=False),
        Binding('enter,space', 'pick', 'Pick', show=False),
    ]
    DEFAULT_CSS = """
    CalendarDays { width: auto; height: auto; }
    CalendarDays > .calendar--weekday { color: $text-muted; text-style: bold; }
    CalendarDays > .calendar--week { color: $text-muted; }
    CalendarDays > .calendar--today { text-style: underline; }
    CalendarDays > .calendar--selected { background: $primary; color: $text; text-style: bold; }
    CalendarDays > .calendar--disabled { color: $text-disabled; text-style: dim; }
    CalendarDays > .calendar--cursor { text-style: bold reverse; }
    """

    def __init__(self, owner: PageCalendar):
        super().__init__('', classes='calendar-days')
        self.owner = owner

    def _left(self) -> int:
        return 3 if self.owner.week_numbers else 0

    def render(self):
        owner, today = self.owner, datetime.date.today()
        style = self.get_component_rich_style
        out = Text('Wk ' if owner.week_numbers else '', style=style('calendar--week'))
        out.append(' '.join(WEEKDAYS[(owner.first_day + n) % 7] for n in range(7)), style=style('calendar--weekday'))
        for week in owner.weeks():
            out.append('\n')
            if all(day.replace(day=1) != owner.shown for day in week):
                continue                    # a row that keeps the grid's height
            if owner.week_numbers:
                out.append(f'{week[0].isocalendar()[1]:>2} ', style=style('calendar--week'))
            for n, day in enumerate(week):
                if n:
                    out.append(' ')
                if day.replace(day=1) != owner.shown:
                    out.append('  ')
                    continue
                looks = [name for name, on in (
                    ('calendar--today', day == today),
                    ('calendar--disabled', not owner.can_pick(day)),
                    ('calendar--selected', day.isoformat() == owner.value),
                    ('calendar--cursor', day == owner.cursor and self.has_focus)) if on]
                out.append(f'{day.day:>2}', style=sum((style(name) for name in looks), Style()))
        return out

    def cell_of(self, day: datetime.date) -> Optional[tuple]:
        """Where `day` is drawn in the grid (x, y), or None when the month shown is another."""
        for row, week in enumerate(self.owner.weeks()):
            if day in week and day.replace(day=1) == self.owner.shown:
                return self._left() + week.index(day) * 3, row + 1
        return None

    def on_click(self, event: events.Click) -> None:
        offset = event.get_content_offset(self)
        if offset is None or offset.y < 1 or offset.x < self._left():
            return
        column, row = (offset.x - self._left()) // 3, offset.y - 1
        weeks = self.owner.weeks()
        if column < 7 and row < len(weeks):
            day = weeks[row][column]
            if day.replace(day=1) == self.owner.shown:
                self.owner.pick(day)

    def on_focus(self) -> None:
        self.refresh()

    def on_blur(self) -> None:
        self.refresh()

    def action_move(self, days: int) -> None:
        self.owner.move_cursor(days)

    def action_month(self, step: int) -> None:
        self.owner.go_month(step)

    def action_pick(self) -> None:
        self.owner.pick(self.owner.cursor)


class ConsoleUI(App):
    """Draws a page's view tree; buttons and forms post the page's actions."""

    CSS = """
    Screen { background: $surface; layers: default toasts; }
    #page { padding: 1 2; }
    .window { height: auto; }
    .hbox { height: auto; }
    .vbox { height: auto; }
    .hbox > Static { width: auto; margin-right: 1; }
    .hbox > Button, .hbox > Input, .hbox > Select { margin-right: 1; }
    .grow { width: 1fr; }
    .panel { border: round $primary; padding: 0 1; height: auto; margin-bottom: 1; }
    .flash { background: $success 30%; padding: 0 1; margin-bottom: 1; }
    .flash-error { background: $error 30%; }
    .badge { background: $secondary; color: $text; padding: 0 1; }
    .link { min-width: 0; height: 1; border: none; background: $surface; text-style: underline; }
    Button { min-width: 8; }
    .grid { height: auto; grid-rows: auto; grid-gutter: 0 1; }
    .table { height: auto; margin-bottom: 1; }
    .row { height: auto; }
    .row-head { border-bottom: solid $primary; }
    .cell { height: auto; padding: 0 1; }
    .label { color: $text-muted; }
    .unsupported { color: $warning; }
    .muted { color: $text-muted; }
    .vrule { width: 1; height: 100%; min-height: 1; border-left: solid $primary; margin-right: 1; }
    .chart, .skeleton { height: auto; width: 1fr; margin-bottom: 1; }
    .field-error { color: $error; }
    .invalid { border: tall $error; }
    TabbedContent { height: auto; }
    TabPane { height: auto; }
    /* UI-21: the tags with a state of their own; a page's toasts on the layer over it */
    PageModal { align: center middle; background: $background 60%; }
    .modal { height: auto; max-width: 100%; max-height: 90%; overflow-y: auto; border: round $primary;
             background: $surface; padding: 0 1; }
    .modal-header, .toast-header { height: auto; }
    .modal-title, .toast-title { width: 1fr; }
    .modal-close, .toast-close { text-style: bold; }
    .toasts { layer: toasts; width: 1fr; height: auto; visibility: hidden; }
    .toasts-top { dock: top; }
    .toasts-bottom { dock: bottom; }
    .toast-holder { width: 1fr; height: auto; visibility: hidden; align-horizontal: right; }
    .toast-holder-left { align-horizontal: left; }
    .toast-holder-center { align-horizontal: center; }
    .toast { visibility: visible; width: 44; max-width: 100%; height: auto; margin: 1 1 0 1; padding: 0 1;
             background: $panel; border-left: outer $primary; }
    .toast-success { border-left: outer $success; }
    .toast-warning { border-left: outer $warning; }
    .toast-danger { border-left: outer $error; }
    .toast .link { background: $panel; }
    Collapsible { height: auto; }
    .tipbox { height: auto; }
    .tip { overlay: screen; constrain: inside inflect; width: auto; background: $panel; color: $text;
           padding: 0 1; }
    .dropdown { height: auto; width: auto; }
    .dropdown-menu { overlay: screen; constrain: inside inflect; width: auto; min-width: 16; height: auto;
                     border: round $primary; background: $panel; padding: 0 1; }
    .dropdown-menu .link { background: $panel; }
    .carousel-controls > Button { margin-right: 1; text-style: bold; }
    .stepper-header { height: auto; margin-bottom: 1; }
    .step { width: auto; height: auto; margin-right: 3; }
    .step > Static { width: auto; }
    .step-title { height: 1; }
    .calendar { width: auto; height: auto; margin-bottom: 1; }
    .calendar-header { height: 1; }
    .calendar-header > .calendar-nav { text-style: bold; }
    .calendar-title { width: 1fr; content-align: center middle; }
    """

    def __init__(self, base_url: str, path: str = '/'):
        super().__init__()
        self.base_url = base_url
        self.path = path
        self.http = requests.Session()
        self._actions: Dict[int, Dict[str, Any]] = {}
        self.page_title = ''
        self._page_lock = asyncio.Lock()
        self.page_loading = False
        # Page loads finished so far. Whoever acts on the page (a person, a
        # test's pilot) can wait for the load IT caused: page_loading alone is
        # False before the load starts too — a button's Pressed message is
        # still bubbling to the app when a pilot's pause returns.
        self.pages_loaded = 0
        # UI-12: the last search as you type that finished — (field, value) —
        # set once its page is drawn AND the field has the focus back. Typing
        # "ba" with a pause longer than the field's delay after "b" makes two
        # searches, so a count of loads cannot tell which one the typist is
        # waiting for; the value can.
        self.last_search: Optional[tuple] = None
        # UI-19: the motions this page ran, in order ({kind, speed, what}), as the browser records them
        self.motions: List[Dict[str, str]] = []
        self.motion_on = True
        self._tabs_opened: set = set()
        # UI-21: what the page being drawn shows above itself once it is drawn — its open modals, its toasts
        self._modals: List[PageModal] = []
        self._toasts: List[dict] = []

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id='page')
        for side in ('top', 'bottom'):           # UI-21: where a page's toasts show, over it
            yield Vertical(classes=f'toasts toasts-{side}', id=f'toasts-{side}')

    async def on_mount(self) -> None:
        await self.load_page(self.path)

    # -- talking to the page --------------------------------------------------

    def _fetch(self, method: str, path: str, data: Optional[dict] = None) -> dict:
        url = urljoin(self.base_url, path)
        response = self.http.request(method, url, data=data, allow_redirects=True,
                                     headers={'Accept': VIEW, 'Referer': urljoin(self.base_url, self.path)},
                                     timeout=30)
        if response.headers.get('Content-Type', '').startswith(VIEW):
            self.path = response.url[len(self.base_url.rstrip('/')):] or '/'
            return response.json()
        # An error page, a 400 from an unknown action: show it as it is.
        return {'title': str(response.status_code), 'flash': f'{response.status_code} {response.reason}',
                'flashType': 'error', 'view': []}

    async def load_page(self, path: str, method: str = 'GET', data: Optional[dict] = None) -> None:
        # One page at a time: a second click while a page is still being
        # mounted removed half-mounted widgets (Textual's Select then fails).
        async with self._page_lock:
            self.page_loading = True
            try:
                await self._load_page(path, method, data)
                # Let the new widgets finish their own mounting (a Select
                # composes its label after mount) before anything replaces them.
                await asyncio.sleep(0)
            finally:
                self.page_loading = False
                self.pages_loaded += 1

    # UI-21: a page's ui:theme gives Textual's colours (the console's own when it has none)
    _TOKEN_VARIABLES = {'primary': 'primary', 'secondary': 'secondary', 'success': 'success',
                        'danger': 'error', 'warning': 'warning', 'info': 'accent'}

    def get_css_variables(self):
        variables = super().get_css_variables()
        for token, variable in self._TOKEN_VARIABLES.items():
            value = (getattr(self, 'page_tokens', None) or {}).get(token)
            if value:
                variables[variable] = value
        return variables

    async def _load_page(self, path: str, method: str, data: Optional[dict]) -> None:
        page = self._fetch(method, path, data)
        tokens = page.get('tokens') or None
        if tokens != getattr(self, 'page_tokens', None):
            self.page_tokens = tokens
            self.refresh_css(animate=False)
        self.motions = []
        self.motion_on = bool(page.get('motion', True))
        self._tabs_opened = set()
        self.page_title = page.get('title', '')
        self.title = self.page_title
        # UI-21: what the last page left open goes with it — its modals, its toasts
        while isinstance(self.screen, PageModal):
            await self.pop_screen()
        for rack in self.query('.toasts'):
            await rack.remove_children()
        self._modals, self._toasts = [], []
        body = self.query_one('#page', VerticalScroll)
        await body.remove_children()
        self._actions.clear()
        widgets: List = []
        if page.get('flash') and not page.get('flashShown'):      # UI-16: once
            classes = 'flash flash-error' if page.get('flashType') == 'error' else 'flash'
            widgets.append(Static(Text(str(page['flash'])), classes=classes, id='flash'))
        widgets.extend(self._build_widgets(page.get('view', [])))
        await body.mount_all(widgets)
        for props in self._toasts:
            position = str(props.get('position') or 'top-right')
            side = 'bottom' if position.startswith('bottom') else 'top'
            where = 'left' if position.endswith('left') else 'center' if position.endswith('center') else 'right'
            await self.query_one(f'#toasts-{side}').mount(
                Horizontal(PageToast(props), classes=f'toast-holder toast-holder-{where}'))
        for modal in self._modals:
            await self.push_screen(modal)

    # -- drawing --------------------------------------------------------------

    def _build_widgets(self, nodes: List[dict], form: Optional[dict] = None) -> List:
        widgets = [w for node in nodes for w in [self._widget(node, form)] if w is not None]
        for w in widgets:
            if form is not None and not hasattr(w, '_quantum_form'):
                w._quantum_form = form
        return widgets

    def _css_classes(self, props: dict, base: str) -> str:
        classes = [base]
        if str(props.get('grow', '')).lower() == 'true':
            classes.append('grow')
        return ' '.join(classes)

    def _widget(self, node: dict, form: Optional[dict]):
        props = node.get('props') or {}
        # UI-19: recorded before its children are built — in document order, as the browser does
        motion = of_props(node.get('type', ''), props) if self.motion_on else None
        if motion is not None:
            self.motions.append(record(motion))
        widget = self._widget_without_width(node, form)
        if motion is not None and widget is not None:
            moving = TerminalMotion(widget, motion['kind'])
            widget.call_after_refresh(lambda: moving.run(self, motion['ms']))
        width = str(props.get('width') or '')
        if widget is not None and width.isdigit():
            # A width in px becomes columns (~8 px each), as the breakpoints do.
            widget.styles.width = max(8, int(width) // 8)
        if widget is not None and props.get('error'):
            # UI-9: the server refused this field; its message under it.
            widget.add_class('invalid')
            return Vertical(widget, Static(Text(str(props['error'])), classes='field-error'), classes='vbox')
        return widget

    def _widget_without_width(self, node: dict, form: Optional[dict]):
        # UI-21: a tag beyond the layout set that is a composition of it says which kind it is drawn as
        kind, props = node.get('as') or node.get('type'), node.get('props', {})
        children = node.get('children', [])
        ident = props.get('ui_id')
        text = str(props.get('text') or '')

        if kind in ('window', 'vbox', 'scrollbox', 'cardbody', 'cardfooter', 'tab', 'animate'):
            return Vertical(*self._build_widgets(children, form), classes=self._css_classes(props, 'vbox'), id=ident)
        if kind == 'section':
            title = [Static(Text(str(props['title']), style='bold'), classes='text')] if props.get('title') else []
            return Vertical(*title, *self._build_widgets(children, form), classes=self._css_classes(props, 'vbox'),
                            id=ident)
        if kind == 'card':
            card = Vertical(*self._build_widgets(children, form), classes='panel', id=ident)
            card.border_title = props.get('title', '')
            return card
        if kind == 'hbox':
            stack = props.get('stack_below')
            narrow = stack and self.size.width < BREAKPOINT_COLUMNS.get(stack, 0)
            box_type = Vertical if narrow else Horizontal
            child_widgets = self._build_widgets(children, form)
            if narrow:
                # Stacked: fixed widths stop applying, as in the web's CSS (UI-2).
                for w in child_widgets:
                    w.styles.width = '100%'
            return box_type(*child_widgets,
                            classes=self._css_classes(props, 'vbox' if narrow else 'hbox'), id=ident)
        if kind == 'grid':
            grid = Grid(*self._build_widgets(children, form), classes='grid', id=ident)
            grid.styles.grid_size_columns = self._grid_columns(str(props.get('columns') or '1'))
            return grid
        if kind == 'panel':
            panel = Vertical(*self._build_widgets(children, form), classes='panel', id=ident)
            panel.border_title = props.get('title', '')
            return panel
        if kind == 'tabpanel':
            panes = [f for f in children if f.get('type') == 'tab']
            titles = [str(f.get('props', {}).get('title') or n + 1) for n, f in enumerate(panes)]
            # UI-17: the tab `open` names opens; else the first
            wanted = str(props.get('open') or '').strip()
            opened = titles.index(wanted) if wanted in titles else 0
            pane_id = f'tabpane-{id(node)}-'
            tabs = TabbedContent(id=ident, initial=f'{pane_id}{opened}' if panes else '')
            for n, (f, title) in enumerate(zip(panes, titles)):
                tabs.compose_add_child(TabPane(title, *self._build_widgets(f.get('children', []), form),
                                               id=f'{pane_id}{n}'))
            return tabs
        if kind == 'form':
            # The form's marker exists before its children, so each widget
            # inside can point to it; the marker keeps the box and the action.
            marker = {'event': node.get('event')}
            box = Vertical(*self._build_widgets(children, marker), classes='vbox', id=ident)
            marker['box'] = box
            return box
        if kind == 'formitem':
            label = [Static(Text(str(props['label'])), classes='label')] if props.get('label') else []
            return Vertical(*label, *self._build_widgets(children, form), classes='vbox', id=ident)
        if kind == 'button':
            button = Button(text or props.get('label') or '', id=ident,
                            variant='error' if props.get('variant') == 'danger' else
                            ('primary' if props.get('variant') == 'primary' else 'default'))
            if node.get('event'):
                self._actions[id(button)] = node['event']
            return button
        if kind == 'link':
            link = Button(text or props.get('to', ''), classes='link', id=ident)
            # UI-21: a link with an action (a menu's option) posts it; else it goes to its page
            self._actions[id(link)] = node['event'] if node.get('event') else {'navigate': props.get('to', '/')}
            return link
        if kind in ('avatar', 'chart', 'skeleton', 'loading', 'treeitem'):
            return self._more(kind, node, props, ident)
        if kind in ('modal', 'toast', 'accordion', 'tooltip', 'dropdown', 'carousel', 'stepper'):
            return self._stateful(kind, children, form, props, ident)
        if kind == 'calendar':
            return PageCalendar(props, id=ident)        # UI-21: a date field shown as a month
        if kind == 'input' and props.get('input_type') == 'file':
            # UI-14: a terminal has no file picker; the form posts without the file.
            return Static(Text(f"{props.get('bind') or 'file'}: attach files from the browser"),
                          classes='label', id=ident)
        if kind == 'input' and props.get('rows'):
            area = TextArea(str(props.get('value') or ''), id=ident, classes=self._css_classes(props, 'input'))
            area.styles.height = int(props['rows']) + 2
            area._quantum_name = props.get('bind')
            return area
        if kind == 'input':
            # UI-12: a search field is drawn again after each pause and gets the
            # focus back; Textual selects all of an Input's text on focus, so
            # the next key REPLACED what had been typed ("b", pause, "a" searched
            # "a"). It keeps the text and the cursor at the end instead.
            field = Input(value=str(props.get('value') or ''), placeholder=props.get('placeholder', ''),
                          id=ident, classes=self._css_classes(props, 'input'),
                          password=props.get('input_type') == 'password',
                          select_on_focus=not props.get('search'))
            field._quantum_name = props.get('bind')
            if props.get('search'):
                # UI-12: typing asks for the page again with ?bind=value.
                field._quantum_search = int(props.get('delay') or 300)
                field._quantum_initial = field.value
            return field
        if kind == 'select':
            options = [(o.strip(), o.strip()) for o in str(props.get('options') or '').split(',') if o.strip()]
            options += [(str(f['props'].get('label') or f['props'].get('value') or ''),
                         str(f['props'].get('value') or ''))
                       for f in children if f.get('type') == 'option']
            values = [v for _, v in options]
            chosen = str(props.get('value') or '')
            value = chosen if chosen in values else (values[0] if values else Select.BLANK)
            choice = Select(options, value=value, allow_blank=not options, id=ident)
            choice._quantum_name = props.get('bind')
            return choice
        if kind == 'checkbox':
            box = Checkbox(str(props.get('label') or ''), value=_checked(props.get('checked')), id=ident)
            box._quantum_name = props.get('bind')
            return box
        if kind == 'switch':
            switch = Switch(value=_checked(props.get('checked')))
            switch._quantum_name = props.get('bind')
            return Horizontal(switch, Static(Text(str(props.get('label') or '')), classes='text'),
                              classes='hbox', id=ident)
        if kind == 'radio':
            chosen = str(props.get('value') or '')
            options = [o.strip() for o in str(props.get('options') or '').split(',') if o.strip()]
            group = RadioSet(*[RadioButton(o, value=o == chosen) for o in options], id=ident)
            group._quantum_name = props.get('bind')
            return group
        if kind == 'stream':
            # IA-7: the answer arrives as it is written, as in the browser.
            box = Static(Text(text), classes='text stream', id=ident)
            if props.get('url'):
                self._read_stream(box, props['url'])
            return box
        if kind == 'table':
            return self._table(node, form, ident)
        if kind == 'list':
            return Vertical(*self._build_widgets(children, form), classes='vbox', id=ident)
        if kind == 'item':
            return Horizontal(Static(str(props.get('marker') or '•'), classes='text'),
                              *self._build_widgets(children, form), classes='hbox', id=ident)
        if kind == 'progress':
            bar = ProgressBar(total=_number(props.get('max'), 100), show_eta=False, id=ident)
            bar.progress = _number(props.get('value'), 0)
            return bar
        if kind == 'image':
            return Static(Text(f"[{props.get('alt') or props.get('src') or 'image'}]"), classes='text', id=ident)
        if kind in ('header', 'cardheader'):
            title = str(props.get('title') or text)
            return Vertical(Static(Text(title, style='bold'), classes='text'),
                            *self._build_widgets(children, form), classes='vbox', id=ident)
        if kind == 'alert':
            classes = 'flash flash-error' if props.get('variant') in ('danger', 'error') else 'flash'
            title = f"{props['title']}: " if props.get('title') else ''
            return Static(Text(title + text), classes=classes, id=ident)
        if kind == 'badge':
            return Static(Text(text), classes='badge', id=ident)
        if kind == 'text':
            return Static(styled_text(text, props), classes='muted' if props.get('muted') else 'text', id=ident)
        if kind == 'footer':
            return Static(Text(text, style='dim'), classes='text', id=ident)
        if kind == 'rule':
            if props.get('vertical'):
                return Static('', classes='vrule')          # UI-21: between the panes of a dividedbox
            return Static('─' * 40, classes='text')
        if kind == 'spacer':
            return Static('', classes='text')
        # UI-7: outside the core set, say so — never draw something else in its place.
        return Static(Text(f'[ui:{kind} is not drawn in the console]', style='italic'),
                      classes='unsupported', id=ident)

    def _more(self, kind: str, node: dict, props: dict, ident):
        """UI-21: the kinds that are not a composition of the layout set."""
        from quantum.runtime.ui_more import tree_guides
        if kind == 'avatar':
            mark = {'online': ('●', 'green'), 'away': ('◐', 'yellow'), 'busy': ('●', 'red'),
                    'offline': ('○', 'grey50')}.get(str(props.get('status') or ''))
            label = Text(f"({props.get('initials') or '?'})", style='bold')
            if mark:
                label.append(' ' + mark[0], style=mark[1])
            return Static(label, classes='text', id=ident)
        if kind == 'chart':
            return ChartBars(node, id=ident)
        if kind == 'skeleton':
            return Skeleton(props, id=ident)
        if kind == 'loading':
            return Loading(str(props.get('text') or 'Loading'), id=ident)
        # a row of a tree: its guides, then its label, a link when it goes somewhere or posts an action
        guides = Static(Text(tree_guides(props), style='dim'), classes='text')
        label = str(props.get('text') or '')
        if node.get('event') or props.get('to'):
            row = Button(label, classes='link')
            self._actions[id(row)] = node['event'] if node.get('event') else {'navigate': props['to']}
        else:
            row = Static(Text(label), classes='text')
        return Horizontal(guides, row, classes='hbox', id=ident)

    def _stateful(self, kind: str, children: List[dict], form: Optional[dict], props: dict, ident):
        """UI-21: the tags with a state of their own — what is open, which slide, which step, a toast that
        goes. The state is the console's, as it is the browser's: it starts again with the page."""
        if kind == 'modal':
            if _checked(props.get('open')):
                self._modals.append(PageModal(props, self._build_widgets(children, form)))
            return None                     # open, above the page once it is drawn; closed, nothing
        if kind == 'toast':
            self._toasts.append(props)
            return None                     # over the page once it is drawn
        if kind == 'accordion':
            folds: List = []
            for child in children:
                if child.get('type') != 'section':
                    folds.extend(self._build_widgets([child], form))
                    continue
                section = child.get('props') or {}
                # each fold opens and closes by itself; the first is open
                folds.append(Collapsible(*self._build_widgets(child.get('children', []), form),
                                         title=Text(str(section.get('title') or '')),
                                         collapsed=any(isinstance(f, Collapsible) for f in folds),
                                         id=section.get('ui_id')))
            return Vertical(*folds, classes='vbox accordion', id=ident)
        if kind == 'tooltip':
            return TipBox(str(props.get('text') or ''), self._build_widgets(children, form), id=ident)
        if kind == 'dropdown':
            return Dropdown(str(props.get('label') or 'Menu'), self._build_widgets(children, form), id=ident)
        if kind == 'carousel':
            # its ui:slides; without them, each child is a slide
            slides = [c for c in children if c.get('type') == 'slide'] or children
            return Carousel(self._build_widgets(slides, form), props, id=ident)
        steps = [c for c in children if c.get('type') == 'step']
        contents = [Vertical(*self._build_widgets(s.get('children', []), form), classes='vbox step-content',
                             id=(s.get('props') or {}).get('ui_id'))
                    for s in steps]
        return Stepper([s.get('props') or {} for s in steps], contents, props, id=ident)

    def _read_stream(self, box: Static, url: str) -> None:
        """Read /_stream/<token> in a thread and show each piece as it arrives."""
        from quantum.runtime.llm_stream import ERROR_MARK
        address = urljoin(self.base_url, url)

        def read():
            text = ''
            try:
                with self.http.get(address, stream=True, timeout=600) as response:
                    if response.status_code != 200:
                        self.call_from_thread(box.update, Text('This answer is no longer available.', style='red'))
                        return
                    for piece in response.iter_content(chunk_size=None, decode_unicode=True):
                        text += piece
                        if ERROR_MARK in text:
                            before, _, error = text.partition(ERROR_MARK)
                            self.call_from_thread(box.update, Text(before) + Text('\n' + error, style='red'))
                            return
                        self.call_from_thread(box.update, Text(text))
            except Exception as exc:          # the connection itself failed
                self.call_from_thread(box.update, Text(f'{text}\n{exc}', style='red'))

        self.run_worker(read, thread=True, group='stream')

    def _grid_columns(self, spec: str) -> int:
        """UI-2 `columns="1 sm:2 lg:3"` counted in terminal columns; "1fr 2fr" is 2."""
        parts = spec.split()
        if len(parts) > 1 and all(p.endswith('fr') for p in parts):
            return len(parts)
        columns = 1
        for part in parts:
            band, _, value = part.rpartition(':')
            if value.isdigit() and (not band or self.size.width >= BREAKPOINT_COLUMNS.get(band, 10 ** 6)):
                columns = int(value)
        return max(1, columns)

    def _table(self, node: dict, form: Optional[dict], ident):
        """UI-5: a header row and one row per record; a cell holds text or widgets."""
        columns = node.get('columns', [])

        def cell(widgets, column):
            box = Vertical(*widgets, classes='cell')
            width = str(column.get('width') or '')
            box.styles.width = max(4, int(width) // 8) if width.isdigit() else '1fr'
            return box

        def title(c):
            if c.get('to'):
                # UI-13: a sortable header is a link, as in the browser.
                link = Button(c['label'], classes='link')
                self._actions[id(link)] = {'navigate': c['to']}
                return link
            return Static(Text(c['label'], style='bold'))

        header = Horizontal(*[cell([title(c)], c) for c in columns], classes='row row-head')
        rows = [Horizontal(*[cell(self._build_widgets(cell_nodes, form), c) for cell_nodes, c in zip(row, columns)],
                    classes='row')
                for row in node.get('rows', [])]
        return Vertical(header, *rows, classes='table', id=ident)

    # -- events are the page's actions ---------------------------------------

    def _form_fields(self, form: dict) -> Dict[str, str]:
        """The fields a browser would post: a checked box posts 'on', an unchecked one nothing."""
        fields = {}
        for w in form['box'].query('Input, TextArea, Select, Checkbox, Switch, RadioSet, PageCalendar'):
            name = getattr(w, '_quantum_name', None)
            if not name:
                continue
            if isinstance(w, PageCalendar):
                fields[name] = w.value          # UI-21: the day picked, as the browser's hidden field
                continue
            if isinstance(w, (Checkbox, Switch)):
                if w.value:
                    fields[name] = 'on'
                continue
            if isinstance(w, RadioSet):
                if w.pressed_button is not None:
                    fields[name] = str(w.pressed_button.label)
                continue
            if isinstance(w, TextArea):
                fields[name] = w.text
                continue
            value = w.value
            fields[name] = '' if value is None or value is Select.BLANK else str(value)
        return fields

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button = event.button
        action = self._actions.get(id(button))
        if action and 'navigate' in action:
            await self.load_page(action['navigate'])
            return
        form = getattr(button, '_quantum_form', None)
        if action is None and form is not None:
            action = form.get('event')
            if action:
                data = {'action': action['action'], **action.get('fields', {}),
                        **self._form_fields(form)}
                await self.load_page(self.path, 'POST', data)
            return
        if action:
            await self.load_page(self.path, 'POST', {'action': action['action'], **action.get('fields', {})})

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """UI-19: a tab the user opens expands into view; the tab the page opens on does not."""
        tabs = event.tabbed_content
        if id(tabs) not in self._tabs_opened:
            self._tabs_opened.add(id(tabs))
            if event.pane.id == tabs._initial:          # the tab the page opens on (UI-17)
                return
        if self.motion_on and event.pane is not None:
            self.motions.append({'kind': 'expand', 'speed': 'normal', 'what': f'tab:{event.pane._title}'})
            TerminalMotion(event.pane, 'expand').run(self, 250)

    def on_input_changed(self, event: Input.Changed) -> None:
        """UI-12: search as you type — after a pause, the page with ?bind=value."""
        field = event.input
        delay = getattr(field, '_quantum_search', None)
        if delay is None or field.value == getattr(field, '_quantum_initial', None):
            return
        previous = getattr(self, '_search_timer', None)
        if previous is not None:
            previous.stop()
        name, value = field._quantum_name, field.value
        self._search_timer = self.set_timer(
            delay / 1000, lambda: self.run_worker(self._search_again(name, value), exclusive=True, group='search'))

    async def _search_again(self, name: str, value: str) -> None:
        from urllib.parse import parse_qsl, urlencode, urlsplit
        parts = urlsplit(self.path)
        params = {k: v for k, v in parse_qsl(parts.query) if k not in (name, 'page')}
        if value:
            params[name] = value
        await self.load_page(parts.path + ('?' + urlencode(params) if params else ''))
        # The page was drawn again: the field keeps the focus and the cursor at the end.
        for field in self.query(Input):
            if getattr(field, '_quantum_name', None) == name and getattr(field, '_quantum_search', None):
                field.focus()
                field.cursor_position = len(field.value)
                break
        self.last_search = (name, value)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        form = getattr(event.input, '_quantum_form', None)
        action = form.get('event') if form is not None else None
        if action:
            data = {'action': action['action'], **action.get('fields', {}), **self._form_fields(form)}
            await self.load_page(self.path, 'POST', data)


def run_console(config_path: str = 'quantum.config.yaml', path: str = '/') -> int:
    """`quantum console`: the application's server in a thread, the page in the terminal."""
    from quantum.runtime.local_server import local_server

    with local_server(config_path) as base_url:
        ConsoleUI(base_url, path).run()
    return 0
