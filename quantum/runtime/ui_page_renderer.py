"""`ui:*` inside a served page (UI-1).

The UI Engine used to be a separate world: `<q:application type="ui">`
compiled to a file, where each target translated the page's logic on its own.
Here the page's runtime does the logic — queries, actions, the SPEC's rules —
and this class only draws: it reuses the HTML adapter's drawing of each
`ui:*` element and hands everything else (q:loop, q:if, HTML, components)
back to the page renderer.

What changes from the standalone adapter:

- `{expressions}` are resolved by the page's runtime, and every resolved value
  is HTML-escaped (the adapter's builder escapes nothing).
- Events are actions: `<ui:button on-click="save">` posts to the page's
  `q:action name="save"`; `with="id={row.id}"` adds fields to that post.
  `<ui:form on-submit="create">` is a form that posts its fields to `create`.
  An event that names no q:action of the page is an error.
- The adapter's CSS for the elements comes once per page, without its global
  reset (the page keeps its own styles).
"""

import copy
import html
from typing import Any, Iterator, List, Optional

from quantum.core.features.ui_engine.src import ast_nodes as ui_nodes
from quantum.runtime.ui_html_adapter import UIHtmlAdapter
from quantum.runtime.ui_form_rules import FORM_CSS, form_context, generated_fields, prepare_field, sends_files
from quantum.runtime.ui_html_templates import CSS_THEME, RESPONSIVE_CSS, HtmlBuilder
from quantum.runtime.ui_pager import PAGER_CSS, pager_items
from quantum.runtime.ui_table_edit import CELL_CSS, cell_field, edit_plan, sort_link
from quantum.core.xml_lines import tag_error

# Attributes that name an action or a field, never text to resolve. `source`
# is data (a list), resolved by source_rows().
_NOT_TEXT = {'on_click', 'on_submit', 'on_change', 'on_select', 'bind', 'children', 'send', 'source',
             'values'}


is_ui_node = ui_nodes.is_ui_node


def source_rows(page, node, where: str, default_var: str) -> Iterator[Any]:
    """UI-5: once per row of a `source="{...}"`, with the row variable set as
    q:loop sets it (`row`, and `row.field` for dict rows). A source that is not
    a list is an error — never an empty table."""
    source = (node.source or '').strip()
    rows = page._apply_databinding(source) if source.startswith('{') and source.endswith('}') else None
    if not isinstance(rows, list):
        got = 'no {expression}' if rows is None and not source.startswith('{') else type(rows).__name__
        raise ValueError(
            f'<{where} source="{source}"> needs a list — a q:query or an array, as '
            f'source="{{rows}}" — and got {got} (UI-5).')
    var = node.as_var or default_var
    ctx = page.context
    original = ctx.local_vars.copy()
    try:
        for row in rows:
            ctx.set_variable(var, row, scope='local')
            if isinstance(row, dict):
                for field, value in row.items():
                    ctx.set_variable(f'{var}.{field}', value, scope='local')
            yield row
    finally:
        ctx.local_vars = original


def table_columns(page, node) -> list:
    """UI-5: a table's ui:columns; with none, one column per field of its rows,
    in the order the query returns them. Without columns every row drew empty."""
    columns = [c for c in node.children if isinstance(c, ui_nodes.UIColumnNode)]
    if columns:
        return columns
    source = (node.source or '').strip()
    rows = page._apply_databinding(source) if source.startswith('{') and source.endswith('}') else None
    first = rows[0] if isinstance(rows, list) and rows else None
    if not isinstance(first, dict):
        return []
    from quantum.runtime.table_params import humanize
    generated = []
    for field in first:
        column = ui_nodes.UIColumnNode()
        column.key, column.label = field, humanize(field)
        generated.append(column)
    return generated


def _single_name(expr) -> Optional[str]:
    import re as _re
    m = _re.fullmatch(r'\s*\{\s*(\w+)\s*\}\s*', expr or '')
    return m.group(1) if m else None


def stream_state(page, node):
    """(value, url) of the q:llm a <ui:stream> shows: url when the answer is still to come."""
    name = node.for_llm
    try:
        result = page.context.get_variable(f'{name}_result')
    except Exception:
        result = None
    if not isinstance(result, dict):
        raise ValueError(f'<ui:stream for="{name}">: there is no q:llm named "{name}" on this page (IA-7)')
    try:
        value = page.context.get_variable(name)
    except Exception:
        value = ''
    return ('' if value is None else str(value)), result.get('stream')


def cell_value(row: Any, column) -> str:
    """UI-5: the text of a `<ui:column key>` cell; a key the row lacks is an error."""
    if not isinstance(row, dict):
        return '' if row is None else str(row)
    if column.key not in row:
        raise ValueError(
            f'<ui:column key="{column.key}"> (UI-5): the row has no field "{column.key}" '
            f'(fields: {", ".join(map(str, row)) or "none"}).')
    value = row[column.key]
    return '' if value is None else str(value)


class UIPageRenderer(UIHtmlAdapter):

    def __init__(self, page, action_names: List[str]):
        super().__init__()
        self._page = page
        self._actions = set(action_names)

    # -- entry -------------------------------------------------------------

    def render(self, node) -> str:
        b = HtmlBuilder()
        self._render_node(node, b)
        return b.build()

    @staticmethod
    def css() -> str:
        return CSS_THEME + '\n' + RESPONSIVE_CSS + '\n' + FORM_CSS + '\n' + PAGER_CSS + '\n' + CELL_CSS

    # -- dispatch ----------------------------------------------------------

    def _render_node_ui(self, node, b: HtmlBuilder):
        try:
            if is_ui_node(node):
                super()._render_node(self._resolved(node), b)
            else:
                b.raw(self._page.render(node))
        except Exception as exc:
            # DEV-2: the innermost ui:* element that failed names its line.
            tag_error(exc, node)
            raise

    def _render_children(self, children: list, b: HtmlBuilder):
        for child in children:
            self._render_node(child, b)

    def _resolved(self, node):
        """A copy of the node with every `{expression}` resolved and escaped."""
        node_copy = copy.copy(node)
        for name, value in vars(node).items():
            if name in _NOT_TEXT or not isinstance(value, str) or '{' not in value:
                continue
            resolved = self._page._apply_databinding(value)
            setattr(node_copy, name, html.escape('' if resolved is None else str(resolved), quote=True))
        return node_copy

    # -- events are actions ------------------------------------------------

    def _action(self, name: str, where: str) -> str:
        name = (name or '').strip()
        if name.endswith('()'):
            name = name[:-2]
        if name not in self._actions:
            available = ', '.join(sorted(self._actions)) or 'none'
            raise ValueError(
                f'{where}="{name}" names no q:action of this page (UI-1; actions: {available}). '
                f'Inside a page, a ui:* event is a q:action.')
        return name

    def _hidden_fields(self, b: HtmlBuilder, action: str, send: str = None):
        b.open_tag('input', {'type': 'hidden', 'name': 'action', 'value': action}, self_closing=True)
        if send:
            resolved = str(self._page._apply_databinding(send))
            for pair in resolved.split(','):
                if '=' not in pair:
                    continue
                field, value = (p.strip() for p in pair.split('=', 1))
                b.open_tag('input', {'type': 'hidden', 'name': html.escape(field, quote=True),
                                     'value': html.escape(value, quote=True)}, self_closing=True)

    def _render_button(self, node, b: HtmlBuilder):
        if not node.on_click:
            return super()._render_button(node, b)
        action = self._action(node.on_click, '<ui:button on-click')
        b.open_tag('form', {'method': 'post', 'class': 'q-action', 'style': 'display: inline'})
        b.indent()
        self._hidden_fields(b, action, getattr(node, 'send', None))
        without_events = copy.copy(node)
        without_events.on_click = None
        super()._render_button(without_events, b)
        b.dedent()
        b.close_tag('form')

    def _render_form(self, node, b: HtmlBuilder):
        action = self._action(node.on_submit, '<ui:form on-submit') if node.on_submit else None
        context = form_context(self._page, node, action)             # UI-9
        fields = generated_fields(node, context)                   # UI-10
        attrs = {'class': 'q-form', 'method': 'post'}
        if sends_files(fields, context):
            attrs['enctype'] = 'multipart/form-data'                # UI-14
        b.open_tag('form', self._merge_attrs(attrs, self._layout_attrs(node)))
        b.indent()
        if action:
            self._hidden_fields(b, action, getattr(node, 'send', None))
        previous = getattr(self, '_form_ctx', None)
        self._form_ctx = context
        try:
            self._render_children(fields, b)
        finally:
            self._form_ctx = previous
        b.dedent()
        b.close_tag('form')

    # -- fields take the action's rules, the values sent back, their error (UI-9)

    def _field(self, draw, node, b: HtmlBuilder):
        node_copy, error = prepare_field(node, getattr(self, '_form_ctx', None), escape=True)
        draw(node_copy, b)
        if error:
            b.open_tag('span', {'class': 'q-field-error', 'role': 'alert'})
            b.text(html.escape(error))
            b.close_tag('span')

    def _render_input(self, node, b: HtmlBuilder):
        if getattr(node, 'search', None):
            return self._render_search(node, b)
        self._field(super()._render_input, node, b)

    # -- search as you type (UI-12) -------------------------------------------

    def _render_search(self, node, b: HtmlBuilder):
        """A GET form around the field: Enter searches without JavaScript; with
        htmx, each pause in typing asks for the same page and swaps only the
        target region. The other URL parameters are kept; `page` is not (a new
        search starts on page 1)."""
        if getattr(self, '_form_ctx', None) is not None:
            raise ValueError(f'<ui:input bind="{node.bind}" search=...> cannot be inside a ui:form: '
                             f'it is a form of its own (a GET search) (UI-12)')
        target = node.search
        self._page._search_targets = getattr(self._page, '_search_targets', set()) | {target}
        context = self._page.context
        path = (getattr(context, 'request_vars', None) or {}).get('path') or ''
        try:
            current = context.get_variable('query')
        except Exception:
            current = None
        current = current if isinstance(current, dict) else {}
        field = copy.copy(node)
        if field.value in (None, ''):
            value = current.get(node.bind)
            field.value = html.escape(str(value), quote=True) if value not in (None, '') else None
        field.input_type = 'search' if (field.input_type or 'text') == 'text' else field.input_type
        b.open_tag('form', {'method': 'get', 'role': 'search', 'class': 'q-search',
                            'action': html.escape(path, quote=True)})
        b.indent()
        for name, value in current.items():
            if name in (node.bind, 'page'):
                continue
            b.open_tag('input', {'type': 'hidden', 'name': html.escape(str(name), quote=True),
                                 'value': html.escape(str(value), quote=True)}, self_closing=True)
        inner = HtmlBuilder()
        super()._render_input(field, inner)
        hx = (f'hx-get="{html.escape(path, quote=True)}" '
              f'hx-trigger="input changed delay:{int(node.delay)}ms, search" '
              f'hx-target="#{html.escape(target, quote=True)}" hx-select="#{html.escape(target, quote=True)}" '
              f'hx-swap="outerHTML" hx-push-url="true" hx-include="closest form" ')
        b.raw(inner.build().replace('<input ', f'<input {hx}', 1))
        b.dedent()
        b.close_tag('form')

    def _render_select(self, node, b: HtmlBuilder):
        self._field(super()._render_select, node, b)

    def _render_radio(self, node, b: HtmlBuilder):
        self._field(super()._render_radio, node, b)

    def _render_checkbox(self, node, b: HtmlBuilder):
        self._field(super()._render_checkbox, node, b)

    def _render_switch(self, node, b: HtmlBuilder):
        self._field(super()._render_switch, node, b)

    # -- <ui:pager> (UI-11) ----------------------------------------------------

    def _render_node(self, node, b: HtmlBuilder):
        special = {ui_nodes.UIPagerNode: self._render_pager, ui_nodes.UIHistoryNode: self._render_history,
                   ui_nodes.UIStreamNode: self._render_stream}
        draw = special.get(type(node))
        if draw is not None:
            try:
                return draw(node, b)
            except Exception as exc:
                tag_error(exc, node)
                raise
        return self._render_node_ui(node, b)

    def _render_stream(self, node, b: HtmlBuilder):
        """IA-7: the answer's place; with a pending stream, the framework's script fills it."""
        from quantum.runtime.llm_stream import STREAM_CSS, STREAM_JS
        value, url = stream_state(self._page, node)
        attrs = {'class': 'q-stream', 'aria-live': 'polite'}
        if url:
            attrs['data-q-stream'] = html.escape(url, quote=True)
        else:
            attrs['class'] += ' q-stream-done'
        b.open_tag('div', self._merge_attrs(attrs, self._layout_attrs(node)))
        b.open_tag('span', {'class': 'q-stream-text'})
        b.text(html.escape(value))
        b.close_tag('span')
        if url:
            b.raw(f'<noscript><a href="{html.escape(url, quote=True)}">Read the answer</a></noscript>')
        b.close_tag('div')
        if url and not getattr(self._page, '_stream_script_done', False):
            self._page._stream_script_done = True
            b.raw(f'<style>{STREAM_CSS}</style><script>{STREAM_JS}</script>')

    def _render_history(self, node, b: HtmlBuilder):
        """DB-11: a row's change history."""
        from quantum.runtime.history import HEADERS, entries_for
        entries = entries_for(self._page, node)
        if not entries:
            b.open_tag('p', {'class': 'q-history-empty'})
            b.text('No changes recorded yet.')
            b.close_tag('p')
            return
        b.open_tag('table', self._merge_attrs({'class': 'q-table q-history'}, self._layout_attrs(node)))
        b.open_tag('thead')
        b.open_tag('tr')
        for _field, label in HEADERS:
            b.open_tag('th')
            b.text(label)
            b.close_tag('th')
        b.close_tag('tr')
        b.close_tag('thead')
        b.open_tag('tbody')
        for entry in entries:
            b.open_tag('tr')
            for field, _label in HEADERS:
                b.open_tag('td')
                b.text(html.escape(str(entry[field])))
                b.close_tag('td')
            b.close_tag('tr')
        b.close_tag('tbody')
        b.close_tag('table')

    def _render_pager(self, node, b: HtmlBuilder):
        items = pager_items(self._page, node)
        if not items:
            return
        b.open_tag('nav', self._merge_attrs({'class': 'q-pager', 'aria-label': 'Pages'}, self._layout_attrs(node)))
        for item in items:
            if item['href']:
                b.open_tag('a', {'href': html.escape(item['href'], quote=True),
                                 'aria-label': item['aria'], 'class': f"q-page-{item['kind']}"})
                b.text(html.escape(item['label']))
                b.close_tag('a')
            else:
                css_class = ('q-page-current' if item['current'] else
                             'q-page-gap' if item['kind'] == 'gap' else 'q-page-disabled')
                attrs = {'class': css_class}
                if item['current']:
                    attrs['aria-current'] = 'page'
                b.open_tag('span', attrs)
                b.text(html.escape(item['label']))
                b.close_tag('span')
        b.close_tag('nav')

    # -- a section is a titled group, open (UI-7) ------------------------------

    def _render_section(self, node, b: HtmlBuilder):
        # The standalone build draws a collapsed <details>: in a page its
        # content was hidden in the browser and shown in the console.
        b.open_tag('section', self._merge_attrs({'class': 'q-section-group'}, self._layout_attrs(node)))
        b.indent()
        if node.title:
            b.open_tag('div', {'class': 'q-section-title'})
            b.text(node.title)
            b.close_tag('div')
        self._render_children(node.children, b)
        b.dedent()
        b.close_tag('section')

    # -- data: source="{rows}" -----------------------------------------------

    def _render_table(self, node, b: HtmlBuilder):
        if not node.source:
            return super()._render_table(node, b)
        columns = table_columns(self._page, node)
        if getattr(node, 'sort', False):
            self._check_sortable(node)
        plan = edit_plan(self._page, node)                                    # UI-13
        state = getattr(self._page, 'form_state', None)
        b.open_tag('table', self._merge_attrs({'class': 'q-table'}, self._layout_attrs(node)))
        b.indent()
        b.open_tag('thead')
        b.open_tag('tr')
        for column in columns:
            style = f'text-align: {column.align}' if column.align else None
            b.open_tag('th', {'style': style} if style else None)
            label = html.escape(column.label or column.key or '')
            if getattr(node, 'sort', False) and column.key and not column.children:
                href, mark = sort_link(self._page, column.key)
                b.open_tag('a', {'href': html.escape(href, quote=True), 'class': 'q-sort'})
                b.text(label + (f' {mark}' if mark else ''))
                b.close_tag('a')
            else:
                b.text(label)
            b.close_tag('th')
        b.close_tag('tr')
        b.close_tag('thead')
        b.open_tag('tbody')
        b.indent()
        for row in source_rows(self._page, node, 'ui:table', 'row'):
            b.open_tag('tr')
            for column in columns:
                style = f'text-align: {column.align}' if column.align else None
                b.open_tag('td', {'style': style} if style else None)
                if column.children:
                    self._render_children(column.children, b)
                elif plan and column.key in plan['columns']:
                    self._render_cell_edit(plan, plan['columns'][column.key], row, state, b)
                else:
                    b.text(html.escape(cell_value(row, column)))
                b.close_tag('td')
            b.close_tag('tr')
        b.dedent()
        b.close_tag('tbody')
        b.dedent()
        b.close_tag('table')

    def _check_sortable(self, node):
        name = _single_name(node.source)
        query = (getattr(self._page, '_query_nodes', None) or {}).get(name)
        if query is not None and not getattr(query, 'sortable', False):
            raise ValueError(f'<ui:table sort="true" source="{node.source}">: the query "{name}" needs '
                             f'sortable="true" to order by a column in SQL (UI-13)')

    def _render_cell_edit(self, plan, column_schema, row, state, b: HtmlBuilder):
        """UI-13: a cell is a small form that posts to the generated __edit action."""
        field, hidden, error = cell_field(plan, column_schema, row, state, escape=True)
        b.open_tag('form', {'method': 'post', 'class': 'q-cell'})
        for name, value in hidden.items():
            b.open_tag('input', {'type': 'hidden', 'name': name, 'value': html.escape(value, quote=True)},
                       self_closing=True)
        previous = getattr(self, '_form_ctx', None)
        self._form_ctx = None                  # the field is prepared already
        try:
            super()._render_node(field, b)
        finally:
            self._form_ctx = previous
        b.open_tag('button', {'class': 'q-cell-save', 'aria-label': f'Save {column_schema.name}'})
        b.text('✓')
        b.close_tag('button')
        b.close_tag('form')
        if error:
            b.open_tag('span', {'class': 'q-field-error', 'role': 'alert'})
            b.text(html.escape(error))
            b.close_tag('span')

    def _render_list(self, node, b: HtmlBuilder):
        if not node.source:
            return super()._render_list(node, b)
        b.open_tag('ul', self._merge_attrs({'class': 'q-list'}, self._layout_attrs(node)))
        b.indent()
        for row in source_rows(self._page, node, 'ui:list', 'item'):
            if node.children:
                self._render_children(node.children, b)
            else:
                b.open_tag('li')
                b.text(html.escape('' if row is None else str(row)))
                b.close_tag('li')
        b.dedent()
        b.close_tag('ul')
