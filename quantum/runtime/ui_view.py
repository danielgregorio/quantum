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
from typing import Any, Dict, List

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
            children = []
            for item in pager_items(self.r, node):
                if item['href']:
                    children.append({'type': 'link', 'props': {'to': item['href'], 'text': item['label']},
                                     'children': []})
                else:
                    text = f"[{item['label']}]" if item['current'] else item['label']
                    children.append({'type': 'text', 'props': {'text': text}, 'children': []})
            return {'type': 'hbox', 'props': {'ui_id': getattr(node, 'ui_id', None)}, 'children': children}
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
