"""The view of a page as data, for renderers that are not a browser (UI-3).

The web server executes a page as always, and — when asked with
`Accept: application/vnd.quantum.view+json` — answers with this tree instead
of HTML. The console renderer (quantum/runtime/ui_console.py) draws it and
sends the same q:action posts a browser would. One runtime, two renderers:
nothing about the page's logic is translated.

A view node is a dict:

    {"type": "hbox", "props": {...}, "children": [...]}
    {"type": "button", "props": {"text": "Save"},
     "event": {"action": "save", "fields": {"id": "3"}}}
    {"type": "text", "props": {"text": "..."}}        # also plain text/HTML
"""

import copy
from typing import Any, Dict, List, Optional

from quantum.core.ast_nodes import CommentNode, HTMLNode, TextNode
from quantum.core.features.conditionals.src.ast_node import IfNode
from quantum.core.features.loops.src.ast_node import LoopNode
from quantum.core.features.ui_engine.src.ast_nodes import (
    UIFormNode, UIHistoryNode, UIListNode, UIPagerNode, UIStreamNode, UITableNode, UIWindowNode,
    is_ui_node)
from quantum.runtime.ui_pager import pager_items
from quantum.runtime.ui_table_edit import cell_field, edit_plan, sort_link
from quantum.runtime.ui_form_rules import FIELDS, form_context, generated_fields, prepare_field
from quantum.runtime.ui_page_renderer import cell_value, source_rows, table_columns

# Fields that are structure or events, not props.
_NOT_PROPS = {'children', 'on_click', 'on_submit', 'on_change', 'on_select', 'send', 'source', 'as_var', 'values',
              'edit', 'edit_datasource', 'sort',
              # DEV-2: where the element is in the .q — never sent to a client
              'source_line', 'source_file'}


def _view_type(node) -> str:
    name = type(node).__name__
    return name[2:-4].lower() if name.startswith('UI') and name.endswith('Node') else name.lower()


def page_title(ast, renderer) -> str:
    """UI-4: a page's title, the same for every renderer — the first ui:window's
    `title` (bindings resolved), else the component's name."""
    for node in getattr(ast, 'statements', []):
        if isinstance(node, UIWindowNode) and node.title:
            title = renderer._apply_databinding(node.title)
            if title not in (None, ''):
                return str(title)
    return getattr(ast, 'name', '') or ''


def shows_text(view, text: str) -> bool:
    """UI-16: whether an element of the view says exactly `text` — a page that
    shows its flash (`<ui:alert>{flash}</ui:alert>`) shows it once, so the
    console and the screen do not draw it again on a line of their own."""
    wanted = str(text).strip()
    for node in view:
        if isinstance(node, dict):
            if str((node.get('props') or {}).get('text', '')).strip() == wanted:
                return True
            if shows_text(node.get('children') or [], wanted):
                return True
    return False


class UIViewBuilder:
    """Walks a page's nodes with the page renderer's evaluation (loops, ifs, bindings)."""

    def __init__(self, renderer):
        self.r = renderer

    def build(self, nodes) -> List[Dict[str, Any]]:
        view: List[Dict[str, Any]] = []
        for node in nodes:
            view.extend(self._node(node))
        return view

    def _text(self, value: str) -> str:
        resolved = self.r._apply_databinding(value)
        return '' if resolved is None else str(resolved)

    def _fields(self, send) -> Dict[str, str]:
        fields = {}
        if send:
            for pair in self._text(send).split(','):
                if '=' in pair:
                    field, value = (p.strip() for p in pair.split('=', 1))
                    fields[field] = value
        return fields

    def _node(self, node) -> List[Dict[str, Any]]:
        if is_ui_node(node):
            return [self._ui(node)]
        if isinstance(node, LoopNode):
            return self._loop(node)
        if isinstance(node, IfNode):
            return self.build(self._branch(node))
        if isinstance(node, TextNode):
            text = self._text(node.content).strip()
            return [{'type': 'text', 'props': {'text': text}}] if text else []
        if isinstance(node, HTMLNode):
            # HTML inside a UI page: its text, in order (a terminal draws no tags).
            children = self.build(node.children or [])
            return children
        if isinstance(node, CommentNode):
            return []
        return []

    def _ui(self, node) -> Dict[str, Any]:
        if isinstance(node, UIStreamNode):
            # IA-7: the console reads the same /_stream/<token> the browser does.
            from quantum.runtime.ui_page_renderer import stream_state
            value, url = stream_state(self.r, node)
            return {'type': 'stream', 'props': {'text': value, 'url': url, 'ui_id': getattr(node, 'ui_id', None)},
                    'children': []}
        if isinstance(node, UIHistoryNode):
            # DB-11: the same entries the browser gets, as a table.
            from quantum.runtime.history import HEADERS, entries_for
            entries = entries_for(self.r, node)
            if not entries:
                return {'type': 'text', 'props': {'text': 'No changes recorded yet.'}, 'children': []}
            return {'type': 'table', 'props': {}, 'children': [],
                    'columns': [{'label': label, 'align': None, 'width': None} for _f, label in HEADERS],
                    'rows': [[[{'type': 'text', 'props': {'text': str(e[f])}}] for f, _l in HEADERS]
                             for e in entries]}
        if isinstance(node, UIPagerNode):
            # UI-11: the same items the browser gets, as links the console follows.
            children = _pager_children(pager_items(self.r, node))
            return {'type': 'hbox', 'props': {'ui_id': getattr(node, 'ui_id', None)}, 'children': children}
        more = self._more(node)
        if more is not None:
            return more
        error = None
        if getattr(node, 'search', None) and getattr(node, 'value', None) in (None, ''):
            # UI-12: the search field shows the search in the URL, as in the browser.
            try:
                current = self.r.context.get_variable('query')
            except Exception:
                current = None
            if isinstance(current, dict) and current.get(node.bind) not in (None, ''):
                node = copy.copy(node)
                node.value = str(current[node.bind])
        if isinstance(node, FIELDS):
            # UI-9: the same rules, values and errors the browser's form gets.
            node, error = prepare_field(node, getattr(self, '_form_ctx', None), escape=False)
        if isinstance(node, UIFormNode):
            previous = getattr(self, '_form_ctx', None)
            action = (node.on_submit or '').strip().rstrip('()') or None
            self._form_ctx = form_context(self.r, node, action)
            try:
                with_fields = copy.copy(node)
                with_fields.children = generated_fields(node, self._form_ctx)      # UI-10
                return self._ui_without_context(with_fields, None)
            finally:
                self._form_ctx = previous
        return self._ui_without_context(node, error)

    def _ui_without_context(self, node, error) -> Dict[str, Any]:
        props = {}
        for name, value in vars(node).items():
            if name in _NOT_PROPS or name.startswith('_') or value is None:
                continue
            if isinstance(value, str):
                props[name] = self._text(value) if '{' in value else value
            elif isinstance(value, (bool, int, float)):
                props[name] = value
        if 'content' in props:
            props['text'] = props.pop('content')
        if isinstance(node, UITableNode) and node.source:
            return self._table(node, props)
        if isinstance(node, UIListNode) and node.source:
            children = []
            for row in source_rows(self.r, node, 'ui:list', 'item'):
                children.extend(self.build(node.children) if node.children
                                else [{'type': 'item', 'props': {}, 'children': [
                                  {'type': 'text', 'props': {'text': '' if row is None else str(row)}}]}])
            return {'type': 'list', 'props': props, 'children': children}
        if error:
            props['error'] = error
        view = {'type': _view_type(node), 'props': props,
                'children': self.build(getattr(node, 'children', None) or [])}
        action = getattr(node, 'on_click', None) or getattr(node, 'on_submit', None)
        if action:
            view['event'] = {'action': action.strip().rstrip('()'), 'fields': self._fields(getattr(node, 'send', None))}
        return view

    # -- the tags beyond the layout set (UI-21) ------------------------------------

    def _layout_props(self, node) -> Dict[str, Any]:
        """The node's props without its children and events — what any element sends."""
        view = self._ui_without_context(_without_children(node), None)
        view.pop('event', None)
        return view['props']

    def _more(self, node) -> Optional[Dict[str, Any]]:
        """The view of a tag beyond the layout set, or None for the others. `as` names the Core kind a
        renderer draws it as, when it is a composition of them (ui_more.py)."""
        from quantum.core.features.ui_engine.src import ast_nodes as ui
        from quantum.runtime import ui_more
        if isinstance(node, ui.UIBreadcrumbNode):
            return {'type': 'breadcrumb', 'as': 'hbox', 'props': self._layout_props(node),
                    'children': ui_more.breadcrumb(ui_more.breadcrumb_items(self.r, node),
                                                   self._text(node.separator) or '/')}
        if isinstance(node, ui.UIAvatarNode):
            props = self._layout_props(node)
            props['initials'] = ui_more.initials(props.get('name'))
            return {'type': 'avatar', 'props': props, 'children': []}
        if isinstance(node, ui.UIMarkdownNode):
            blocks = ui_more.markdown_blocks(self._text(node.content))
            props = self._layout_props(node)
            props.pop('text', None)
            return {'type': 'markdown', 'as': 'vbox', 'props': props, 'children': ui_more.markdown_view(blocks)}
        if isinstance(node, ui.UIChartNode):
            props = self._layout_props(node)
            for name in ('labels', 'values', 'colors'):
                props.pop(name, None)
            return {'type': 'chart', 'props': props, 'bars': ui_more.chart_of(self.r, node), 'children': []}
        if isinstance(node, ui.UITreeNode):
            items = []
            for row in ui_more.tree_of(self.r, node):
                item = {'type': 'treeitem', 'props': {'text': row['label'], 'depth': row['depth'],
                                                      'last': row['last'], 'lines': row['lines']},
                        'children': []}
                if row['to']:
                    item['props']['to'] = row['to']
                elif node.on_select:
                    item['event'] = {'action': node.on_select.strip().rstrip('()'), 'fields': {'value': row['value']}}
                items.append(item)
            return {'type': 'tree', 'as': 'vbox', 'props': self._layout_props(node), 'children': items}
        if isinstance(node, ui.UILogNode):
            props = self._layout_props(node)
            props.pop('text', None)
            lines = [{'type': 'text', 'props': {'text': line, 'code': True}, 'children': []}
                     for line in ui_more.log_of(self.r, node)]
            return {'type': 'log', 'as': 'panel', 'props': props, 'children': lines}
        if isinstance(node, ui.UIDividedBoxNode):
            vertical = (self._text(node.direction) or 'horizontal') == 'vertical'
            children: List[Dict[str, Any]] = []
            for child in self.build(node.children or []):
                if children:
                    children.append({'type': 'rule', 'props': {} if vertical else {'vertical': True}, 'children': []})
                children.append(child)
            return {'type': 'dividedbox', 'as': 'vbox' if vertical else 'hbox', 'props': self._layout_props(node),
                    'children': children}
        if isinstance(node, ui.UIPaginationNode):
            shape = ui_more.pagination_of(self.r, node)
            children = _pager_children(shape['items'])
            if node.show_total:
                children.append({'type': 'text', 'props': {'text': f"{shape['total']} items", 'muted': True},
                                 'children': []})
            if node.show_jump and shape['pages'] > 1:
                children.append({'type': 'input', 'props': {'bind': shape['param'], 'search': 'pagination',
                                                            'input_type': 'number', 'placeholder': 'Page',
                                                            'min': '1', 'max': str(shape['pages'])},
                                 'children': []})
            props = {k: v for k, v in self._layout_props(node).items()
                     if k not in ('total', 'page_size', 'current', 'bind', 'show_total', 'show_jump')}
            return {'type': 'pagination', 'as': 'hbox', 'props': props, 'children': children}
        if isinstance(node, (ui.UIMenuNode, ui.UIDropdownNode)):
            # a menu is a row of its options; a dropdown, a button that opens them (UI-21)
            options = []
            for option in node.children or []:
                if not isinstance(option, ui.UIOptionNode):
                    options.extend(self.build([option]))
                    continue
                label = self._text(option.label) or self._text(option.value)
                view = {'type': 'option', 'props': {'text': label}, 'children': []}
                if option.on_click:
                    view['as'] = 'link'
                    value = self._text(option.value)
                    view['event'] = {'action': option.on_click.strip().rstrip('()'),
                                     'fields': {'value': value} if value else {}}
                else:
                    view['as'] = 'text'
                options.append(view)
            if isinstance(node, ui.UIDropdownNode):
                return {'type': 'dropdown', 'props': self._layout_props(node), 'children': options}
            return {'type': 'menu', 'as': 'hbox', 'props': self._layout_props(node), 'children': options}
        if isinstance(node, ui.UIModalNode):
            from quantum.runtime.ui_more import modal_open
            view = self._ui_without_context(node, None)
            view['props']['open'] = modal_open(self.r, node)
            return view
        if isinstance(node, ui.UIToastNode):
            from quantum.runtime.ui_more import page_only_attrs, truthy
            page_only_attrs(node, 'ui:toast', ('on_close',))
            if node.show and not truthy(self.r._apply_databinding(node.show)):
                return {'type': 'text', 'props': {'text': ''}, 'children': []}   # not shown: nothing
            props = self._layout_props(node)
            props.pop('show', None)
            return {'type': 'toast', 'props': props, 'children': []}
        if isinstance(node, (ui.UICarouselNode, ui.UIStepperNode)):
            from quantum.runtime.ui_more import page_only_attrs
            page_only_attrs(node, 'ui:carousel' if isinstance(node, ui.UICarouselNode) else 'ui:stepper',
                            ('on_change', 'on_complete', 'bind'))
            view = self._ui_without_context(node, None)
            view.pop('event', None)
            for child in view['children']:
                if child['type'] == 'slide':
                    child['as'] = 'vbox'
            return view
        if isinstance(node, ui.UIToastContainerNode):
            view = self._ui_without_context(node, None)
            view['as'] = 'vbox'
            return view
        if isinstance(node, ui.UIDatePickerNode):
            field = date_field(node)
            view = self._ui(field)
            view['type'], view['as'] = 'datepicker', 'input'
            return view
        if isinstance(node, ui.UIAnimateNode):
            view = self._ui_without_context(node, None)
            view['as'] = 'vbox'
            return view
        return None

    def _table(self, node: UITableNode, props: Dict[str, Any]) -> Dict[str, Any]:
        """UI-5: a table with its rows; each cell is a list of view nodes.
        UI-13: sortable headers carry the link; an editable cell is a form."""
        columns = table_columns(self.r, node)
        plan = edit_plan(self.r, node)
        state = getattr(self.r, 'form_state', None)
        rows = []
        for row in source_rows(self.r, node, 'ui:table', 'row'):
            cells = []
            for c in columns:
                if c.children:
                    cells.append(self.build(c.children))
                elif plan and c.key in plan['columns']:
                    field, hidden, error = cell_field(plan, plan['columns'][c.key], row, state, escape=False)
                    field_view = self._ui(field)
                    if error:
                        field_view['props']['error'] = error
                    cells.append([{'type': 'form', 'props': {},
                                   'event': {'action': hidden.pop('action'), 'fields': hidden},
                                   'children': [field_view]}])
                else:
                    cells.append([{'type': 'text', 'props': {'text': cell_value(row, c)}}])
            rows.append(cells)
        header = []
        for c in columns:
            column = {'label': c.label or c.key or '', 'align': c.align, 'width': c.column_width}
            if getattr(node, 'sort', False) and c.key and not c.children:
                href, mark = sort_link(self.r, c.key)
                column['to'] = href
                column['label'] += f' {mark}' if mark else ''
            header.append(column)
        return {'type': 'table', 'props': props, 'columns': header, 'rows': rows, 'children': []}

    def _branch(self, node: IfNode) -> list:
        if self.r._evaluate_condition(node.condition):
            return list(node.if_body)
        for block in node.elseif_blocks or []:
            cond = block.get('condition') if isinstance(block, dict) else getattr(block, 'condition', None)
            body = block.get('body') if isinstance(block, dict) else getattr(block, 'body', None)
            if cond is not None and self.r._evaluate_condition(cond):
                return list(body or [])
        return list(node.else_body or [])

    def _loop(self, node: LoopNode) -> List[Dict[str, Any]]:
        # The same iteration as HTMLRenderer._render_loop.
        view: List[Dict[str, Any]] = []
        ctx = self.r.context
        original = ctx.local_vars.copy()
        try:
            for index, item in enumerate(self.r._get_loop_items(node) or []):
                ctx.set_variable(node.var_name, item, scope='local')
                if node.loop_type == 'query' and isinstance(item, dict):
                    for field, value in item.items():
                        ctx.set_variable(f'{node.var_name}.{field}', value, scope='local')
                if node.index_name:
                    ctx.set_variable(node.index_name, index, scope='local')
                view.extend(self.build(node.body))
        finally:
            ctx.local_vars = original
        return view


def _without_children(node):
    bare = copy.copy(node)
    for name in ('children', 'on_click', 'on_submit'):
        if hasattr(bare, name):
            setattr(bare, name, [] if name == 'children' else None)
    return bare


def _pager_children(items) -> List[Dict[str, Any]]:
    """UI-11: a pager's items as links the console follows, the current page and the gaps as text."""
    children = []
    for item in items:
        if item['href']:
            children.append({'type': 'link', 'props': {'to': item['href'], 'text': item['label']}, 'children': []})
        else:
            text = f"[{item['label']}]" if item['current'] else item['label']
            children.append({'type': 'text', 'props': {'text': text}, 'children': []})
    return children


def date_field(node):
    """UI-21: a ui:date-picker is a date field — a ui:input of type date, with its rules (UI-9)."""
    from quantum.core.features.ui_engine.src.ast_nodes import UIInputNode
    field = UIInputNode()
    field.bind, field.value, field.placeholder = node.bind, node.value, node.placeholder
    field.input_type = 'date'
    field.min, field.max = node.min_date, node.max_date
    field.required = bool(node.required)
    layout = set(vars(UIInputNode())) - {'bind', 'value', 'placeholder', 'input_type', 'min', 'max', 'required'}
    for name in ('source_line', 'source_file', *sorted(layout)):     # where it is, and its layout
        if name in vars(node) and getattr(node, name) is not None and not isinstance(getattr(node, name), list):
            setattr(field, name, getattr(node, name))
    return field
