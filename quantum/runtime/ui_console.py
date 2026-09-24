"""The console renderer: a Quantum page as a terminal app (UI-3).

`quantum console` starts the application's server in this process and opens a
Textual app on it. The app asks each page for its view tree
(quantum/runtime/ui_view.py) instead of HTML, draws it with Textual widgets,
and sends the same q:action posts a browser sends — with a cookie jar, so
login, validation, flash and redirects are exactly the web's. Nothing of the
page's logic is translated: the runtime that serves the browser serves this.
"""

import asyncio
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests
from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual.widgets import (Button, Checkbox, Input, ProgressBar, RadioButton, RadioSet,
                             Select, Static, Switch, TabbedContent, TabPane, TextArea)

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


class ConsoleUI(App):
    """Draws a page's view tree; buttons and forms post the page's actions."""

    CSS = """
    Screen { background: $surface; }
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
    .field-error { color: $error; }
    .invalid { border: tall $error; }
    TabbedContent { height: auto; }
    TabPane { height: auto; }
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

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id='page')

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

    async def _load_page(self, path: str, method: str, data: Optional[dict]) -> None:
        page = self._fetch(method, path, data)
        self.page_title = page.get('title', '')
        self.title = self.page_title
        body = self.query_one('#page', VerticalScroll)
        await body.remove_children()
        self._actions.clear()
        widgets: List = []
        if page.get('flash'):
            classes = 'flash flash-error' if page.get('flashType') == 'error' else 'flash'
            widgets.append(Static(Text(str(page['flash'])), classes=classes, id='flash'))
        widgets.extend(self._build_widgets(page.get('view', [])))
        await body.mount_all(widgets)

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
        widget = self._widget_without_width(node, form)
        props = node.get('props') or {}
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
        kind, props = node.get('type'), node.get('props', {})
        children = node.get('children', [])
        ident = props.get('ui_id')
        text = str(props.get('text') or '')

        if kind in ('window', 'vbox', 'scrollbox', 'cardbody', 'cardfooter', 'tab'):
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
            tabs = TabbedContent(id=ident)
            for n, f in enumerate(f for f in children if f.get('type') == 'tab'):
                tabs.compose_add_child(TabPane(str(f.get('props', {}).get('title') or n + 1),
                                               *self._build_widgets(f.get('children', []), form)))
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
            self._actions[id(link)] = {'navigate': props.get('to', '/')}
            return link
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
            return Horizontal(Static('•', classes='text'), *self._build_widgets(children, form),
                              classes='hbox', id=ident)
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
            return Static(Text(text, style='bold' if props.get('weight') == 'bold' else ''),
                          classes='text', id=ident)
        if kind == 'footer':
            return Static(Text(text, style='dim'), classes='text', id=ident)
        if kind == 'rule':
            return Static('─' * 40, classes='text')
        if kind == 'spacer':
            return Static('', classes='text')
        # UI-7: outside the core set, say so — never draw something else in its place.
        return Static(Text(f'[ui:{kind} is not drawn in the console]', style='italic'),
                      classes='unsupported', id=ident)

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
        for w in form['box'].query('Input, TextArea, Select, Checkbox, Switch, RadioSet'):
            name = getattr(w, '_quantum_name', None)
            if not name:
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
