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
import json
import re
from typing import Any, Iterator, List, Optional

from quantum.core.features.ui_engine.src import ast_nodes as ui_nodes
from quantum.runtime.ui_html_adapter import UIHtmlAdapter
from quantum.runtime.ui_form_rules import FORM_CSS, form_context, generated_fields, prepare_field, sends_files
from quantum.runtime.ui_html_templates import CSS_THEME, RESPONSIVE_CSS, HtmlBuilder
from quantum.runtime.ui_pager import PAGER_CSS, pager_items
from quantum.runtime import ui_more
from quantum.runtime.ui_motion import MOTION_CSS, html_attrs, motion_on, of_props
from quantum.runtime.ui_table_edit import CELL_CSS, cell_field, edit_plan, sort_link
from quantum.core.xml_lines import tag_error

# Attributes that name an action or a field, never text to resolve. `source`
# is data (a list), resolved by source_rows().
_NOT_TEXT = {'on_click', 'on_submit', 'on_change', 'on_select', 'bind', 'children', 'send', 'source',
             'values'}


is_ui_node = ui_nodes.is_ui_node


def with_attrs(markup: str, attrs: dict) -> str:
    """The markup with `attrs` on its first tag: a class and a style are added to the ones it has."""
    match = re.search(r'<([a-zA-Z][\w-]*)([^>]*?)(/?)>', markup)
    if match is None:
        return markup
    tag_attrs = match.group(2)
    for name, value in attrs.items():
        found = re.search(r'\s' + name + r'="([^"]*)"', tag_attrs)
        if found and name in ('class', 'style'):
            joined = f'{found.group(1)} {value}' if name == 'class' else f'{value}; {found.group(1)}'
            tag_attrs = tag_attrs[:found.start(1)] + joined + tag_attrs[found.end(1):]
        elif not found:
            tag_attrs += f' {name}="{html.escape(str(value), quote=True)}"'
    return markup[:match.start(2)] + tag_attrs + markup[match.end(2):]


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
        return (CSS_THEME + '\n' + RESPONSIVE_CSS + '\n' + FORM_CSS + '\n' + PAGER_CSS + '\n' + CELL_CSS
                + '\n' + MOTION_CSS + '\n' + ui_more.MORE_CSS)

    # -- dispatch ----------------------------------------------------------

    def _render_node_ui(self, node, b: HtmlBuilder):
        try:
            if is_ui_node(node):
                resolved = self._resolved(node)
                motion = self._motion(resolved)
                if motion is None:
                    super()._render_node(resolved, b)
                else:
                    inner = HtmlBuilder()
                    super()._render_node(resolved, inner)
                    b.raw(with_attrs(inner.build(), html_attrs(motion)))
            else:
                b.raw(self._page.render(node))
        except Exception as exc:
            # DEV-2: the innermost ui:* element that failed names its line.
            tag_error(exc, node)
            raise

    def _render_children(self, children: list, b: HtmlBuilder):
        for child in children:
            self._render_node(child, b)

    def _motion(self, node):
        """UI-19: the motion the element asks for, unless the application turned motion off."""
        if not motion_on(getattr(self._page, 'config', None)):
            return None
        from quantum.runtime.ui_view import _view_type
        props = {name: html.unescape(value) if isinstance(value, str) else value
                 for name, value in vars(node).items() if name in ('transition', 'enter', 'speed', 'anim_type', 'ui_id')}
        return of_props(_view_type(node), props)

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
                   ui_nodes.UIStreamNode: self._render_stream,
                   # UI-21: drawn from what ui_more works out, as the view tree sends it
                   ui_nodes.UIMarkdownNode: self._render_markdown_page, ui_nodes.UIChartNode: self._render_chart_page,
                   ui_nodes.UITreeNode: self._render_tree_page, ui_nodes.UILogNode: self._render_log_page,
                   ui_nodes.UIPaginationNode: self._render_pagination_page,
                   ui_nodes.UIMenuNode: self._render_menu_page, ui_nodes.UIDatePickerNode: self._render_date_page,
                   ui_nodes.UIAvatarNode: self._render_avatar_page,
                   ui_nodes.UIAccordionNode: self._render_accordion_page,
                   ui_nodes.UIModalNode: self._render_modal_page,
                   ui_nodes.UICalendarNode: self._render_calendar_page,
                   ui_nodes.UIDropdownNode: self._render_dropdown_page,
                   ui_nodes.UIToastNode: self._render_toast_page,
                   ui_nodes.UICarouselNode: self._render_moving_page, ui_nodes.UIStepperNode: self._render_moving_page}
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

    # -- the tags beyond the layout set (UI-21) --------------------------------------

    def _open(self, node, b: HtmlBuilder, tag: str, css_class: str, extra: Optional[dict] = None):
        b.open_tag(tag, self._merge_attrs({'class': css_class, **(extra or {})},
                                          self._layout_attrs(self._resolved(node))))

    def _render_markdown_page(self, node, b: HtmlBuilder):
        blocks = ui_more.markdown_blocks(ui_more._text(self._page, node.content))
        self._open(node, b, 'div', 'q-markdown')
        b.raw(ui_more.markdown_html(blocks))
        b.close_tag('div')

    def _render_chart_page(self, node, b: HtmlBuilder):
        bars = ui_more.chart_of(self._page, node)
        inner = HtmlBuilder()
        inner.raw(ui_more.chart_html(ui_more._text(self._page, node.chart_type) or 'bar',
                                     ui_more._text(self._page, node.title), bars))
        b.raw(with_attrs(inner.build(), self._layout_attrs(self._resolved(node))))

    def _render_tree_page(self, node, b: HtmlBuilder):
        action = self._action(node.on_select, '<ui:tree on-select') if node.on_select else None
        self._open(node, b, 'div', 'q-tree', {'role': 'tree'})
        for row in ui_more.tree_of(self._page, node):
            b.open_tag('div', {'class': 'q-tree-item', 'role': 'treeitem', 'aria-level': str(row['depth'] + 1)})
            guides = ui_more.tree_guides(row)
            if guides:
                b.raw(f'<span class="q-tree-guides" aria-hidden="true">{html.escape(guides)}</span>')
            label = html.escape(row['label'])
            to = ui_more.safe_link(row['to']) if row['to'] else None
            if to:
                b.raw(f'<a href="{html.escape(to, quote=True)}">{label}</a>')
            elif action:
                b.open_tag('form', {'method': 'post', 'class': 'q-action'})
                self._hidden_fields(b, action)
                b.open_tag('input', {'type': 'hidden', 'name': 'value', 'value': html.escape(row['value'], quote=True)},
                           self_closing=True)
                b.raw(f'<button type="submit" class="q-link-action">{label}</button>')
                b.close_tag('form')
            else:
                b.raw(f'<span>{label}</span>')
            b.close_tag('div')
        b.close_tag('div')

    def _render_log_page(self, node, b: HtmlBuilder):
        # on one line of the builder: it indents each line it is given, and a <pre> keeps that
        lines = html.escape('\n'.join(ui_more.log_of(self._page, node))).replace('\n', '&#10;')
        inner = HtmlBuilder()
        inner.raw(f'<pre class="q-log" role="log">{lines}</pre>')
        b.raw(with_attrs(inner.build(), self._layout_attrs(self._resolved(node))))

    def _render_pagination_page(self, node, b: HtmlBuilder):
        shape = ui_more.pagination_of(self._page, node)
        self._open(node, b, 'nav', 'q-pager', {'aria-label': 'Pages'})
        for item in shape['items']:
            if item['href']:
                b.raw(f'<a href="{html.escape(item["href"], quote=True)}" aria-label="{item["aria"]}" '
                      f'class="q-page-{item["kind"]}">{html.escape(item["label"])}</a>')
            else:
                css_class = ('q-page-current' if item['current'] else
                             'q-page-gap' if item['kind'] == 'gap' else 'q-page-disabled')
                current = ' aria-current="page"' if item['current'] else ''
                b.raw(f'<span class="{css_class}"{current}>{html.escape(item["label"])}</span>')
        if node.show_total:
            b.raw(f'<span class="q-pager-total">{html.escape(shape["total"])} items</span>')
        if node.show_jump and shape['pages'] > 1:
            # a GET form: the page number goes in the URL, as the links do
            b.raw(f'<form method="get" role="search"><input type="number" name="{html.escape(shape["param"], quote=True)}" '
                  f'min="1" max="{shape["pages"]}" placeholder="Page" aria-label="Go to page"></form>')
        b.close_tag('nav')

    def _render_menu_page(self, node, b: HtmlBuilder):
        self._open(node, b, 'nav', 'q-menu')
        self._options_html(node, b, 'q-menu-item')
        b.close_tag('nav')

    def _options_html(self, node, b: HtmlBuilder, css_class: str):
        """A menu's or a dropdown's options: each with an action is a button posting it, its value as `value`."""
        for option in node.children or []:
            if not isinstance(option, ui_nodes.UIOptionNode):
                self._render_node(option, b)
                continue
            label = html.escape(ui_more._text(self._page, option.label) or ui_more._text(self._page, option.value))
            if not option.on_click:
                b.raw(f'<span class="{css_class}">{label}</span>')
                continue
            action = self._action(option.on_click, '<ui:option on-click')
            b.open_tag('form', {'method': 'post', 'class': 'q-action'})
            self._hidden_fields(b, action)
            value = ui_more._text(self._page, option.value)
            if value:
                b.open_tag('input', {'type': 'hidden', 'name': 'value', 'value': html.escape(value, quote=True)},
                           self_closing=True)
            b.raw(f'<button type="submit" class="{css_class} q-link-action">{label}</button>')
            b.close_tag('form')

    def _render_accordion_page(self, node, b: HtmlBuilder):
        # UI-21: each section opens and closes by itself (<details>); the first is open
        self._open(node, b, 'div', 'q-accordion')
        first = True
        for child in node.children or []:
            if not isinstance(child, ui_nodes.UISectionNode):
                self._render_node(child, b)
                continue
            title = html.escape(ui_more._text(self._page, child.title))
            b.raw(f'<details class="q-accordion-item"{" open" if first else ""}>'
                  f'<summary class="q-accordion-title">{title}</summary>')
            b.open_tag('div', {'class': 'q-accordion-body'})
            self._render_children(child.children, b)
            b.close_tag('div')
            b.raw('</details>')
            first = False
        b.close_tag('div')

    def _render_dropdown_page(self, node, b: HtmlBuilder):
        # UI-21: a button that opens its options (<details>), each option a button posting its action
        label = html.escape(ui_more._text(self._page, node.label) or 'Menu')
        self._open(node, b, 'details', 'q-dropdown')
        b.raw(f'<summary class="q-dropdown-trigger">{label} <span class="q-dropdown-arrow">▾</span></summary>')
        b.open_tag('div', {'class': 'q-dropdown-menu', 'role': 'menu'})
        self._options_html(node, b, 'q-menu-item')
        b.close_tag('div')
        b.close_tag('details')

    def _render_calendar_page(self, node, b: HtmlBuilder):
        # UI-21: a date field shown as a month; the picked day goes with its form under `bind`, and comes back in
        # it with its error (UI-9)
        node, error = ui_more.calendar_field(node, getattr(self, '_form_ctx', None))
        shape = ui_more.calendar_of(self._page, node)
        inner = HtmlBuilder()
        self._render_node_ui(node, inner)
        markup = inner.build()
        b.raw(markup)
        found = re.search(r'<div[^>]*\bid="([^"]+)"[^>]*class="q-calendar\b|<div[^>]*class="q-calendar\b[^"]*"[^>]*\bid="([^"]+)"',
                          markup)
        if shape['bind'] and found:
            ident = html.unescape(found.group(1) or found.group(2))
            name = html.escape(shape['bind'], quote=True)
            b.raw(f'<input type="hidden" name="{name}" value="{html.escape(shape["value"], quote=True)}" '
                  f'data-calendar-for="{html.escape(ident, quote=True)}">')
            sync = ("document.addEventListener('click',function(e){var c=document.getElementById(" + json.dumps(ident)
                    + ");if(!c||!c.contains(e.target))return;setTimeout(function(){var s=window.__quantumState||{};"
                    "var f=document.querySelector('input[data-calendar-for=\"'+c.id+'\"]');"
                    "if(f&&s[" + json.dumps(shape['bind']) + "])f.value=s[" + json.dumps(shape['bind']) + "];},0);},true);")
            b.raw(f'<script>{sync}</script>')
        if error:
            b.open_tag('span', {'class': 'q-field-error', 'role': 'alert'})
            b.text(html.escape(error))
            b.close_tag('span')

    def _render_modal_page(self, node, b: HtmlBuilder):
        # UI-21: open as the page is drawn (`open`, or an expression); its close button closes it
        shown = copy.copy(node)
        shown.open = ui_more.modal_open(self._page, node)
        self._render_node_ui(shown, b)

    def _render_toast_page(self, node, b: HtmlBuilder):
        # UI-21: shown while `show` is true; it goes after `duration` (ui:toast's own script)
        ui_more.page_only_attrs(node, 'ui:toast', ('on_close',))
        if node.show and not ui_more.truthy(self._page._apply_databinding(node.show)):
            return
        shown = copy.copy(node)
        shown.show = None
        self._render_node_ui(shown, b)

    def _render_moving_page(self, node, b: HtmlBuilder):
        # UI-21: a carousel's slides and a stepper's steps move by themselves (their own script)
        where = 'ui:carousel' if isinstance(node, ui_nodes.UICarouselNode) else 'ui:stepper'
        ui_more.page_only_attrs(node, where, ('on_change', 'on_complete', 'bind'))
        if isinstance(node, ui_nodes.UICarouselNode):
            return self._render_node_ui(node, b)
        # a stepper's Back and Next: this step done, the one after (its script keeps which is shown)
        inner = HtmlBuilder()
        self._render_node_ui(node, inner)
        markup = inner.build()
        found = re.search(r'<div[^>]*\bclass="q-stepper\b[^"]*"[^>]*\bid="([^"]+)"', markup) or \
            re.search(r'<div[^>]*\bid="([^"]+)"[^>]*\bclass="q-stepper\b', markup)
        b.raw(markup)
        if found:
            ident = json.dumps(html.unescape(found.group(1)))
            move = ("var a=window.__quantumStepper&&__quantumStepper.get(" + ident + ");"
                    "if(a){{{step}}}")
            back = html.escape(move.format(step='a.prev();'), quote=True)
            forward = html.escape(move.format(step='a.complete();a.next();'), quote=True)
            b.raw(f'<div class="q-stepper-nav"><button type="button" class="q-btn q-stepper-back" onclick="{back}">'
                  f'Back</button> <button type="button" class="q-btn q-btn-primary q-stepper-next" '
                  f'onclick="{forward}">Next</button></div>')

    def _render_date_page(self, node, b: HtmlBuilder):
        from quantum.runtime.ui_view import date_field
        self._render_node_ui(date_field(node), b)

    def _render_avatar_page(self, node, b: HtmlBuilder):
        resolved = self._resolved(node)
        cls = 'q-avatar' + (f' q-avatar-{resolved.size}' if resolved.size else '')
        if resolved.shape == 'square':
            cls += ' q-avatar-square'
        b.open_tag('div', self._merge_attrs({'class': cls}, self._layout_attrs(resolved)))
        name = ui_more._text(self._page, node.name)
        if resolved.src:
            b.raw(f'<img src="{resolved.src}" alt="{html.escape(name, quote=True)}">')
        else:
            b.raw(f'<span class="q-avatar-initials" aria-label="{html.escape(name, quote=True)}">'
                  f'{html.escape(ui_more.initials(name))}</span>')
        status = ui_more._text(self._page, node.status)
        if status in ui_more.AVATAR_STATUSES:
            b.raw(f'<span class="q-avatar-status q-avatar-status-{status}" title="{status}"></span>')
        b.close_tag('div')

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
