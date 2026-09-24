"""A table that sorts and edits itself (M16, UI-13).

`<ui:table source="{tasks}" sort="true">` — each header is a link that
orders the query in SQL (`q:query sortable="true"`, by the URL's ?sort= and
?dir=), so it works with pagination.

`<ui:table source="{tasks}" edit="tasks" datasource="db">` — each shown
column of that table (not the key, not a column with `edit="false"`) is a
small form in its cell. It posts to an action the page does not write:
`__edit`, handled by the server (web_server._edit_cell), which accepts only a
table and column this page declares editable, validates the value with the
column's rules from the schema (UI-10) and updates one row by its key. What it
does shows in /_dev like any action.
"""

from typing import Dict, Optional
from urllib.parse import urlencode

EDIT_ACTION = '__edit'


def _query_params(renderer) -> dict:
    try:
        query = renderer.context.get_variable('query')
    except Exception:
        query = None
    return query if isinstance(query, dict) else {}


def _path(renderer) -> str:
    return (getattr(renderer.context, 'request_vars', None) or {}).get('path') or ''


def sort_link(renderer, key: str):
    """(href, marker) of a header: the next order for this column, and ▲/▼ if it is the current one."""
    query = _query_params(renderer)
    current, direction = query.get('sort'), str(query.get('dir') or 'asc').lower()
    next_dir = 'desc' if current == key and direction == 'asc' else 'asc'
    params = {k: v for k, v in query.items() if k not in ('sort', 'dir', 'page')}
    params.update({'sort': key, 'dir': next_dir})
    mark = ('▲' if direction == 'asc' else '▼') if current == key else ''
    return f'{_path(renderer)}?{urlencode(params)}', mark


def edit_plan(renderer, table_node) -> Optional[dict]:
    """For an editable table: the key column and, per editable column key, its schema column."""
    if not getattr(table_node, 'edit', None):
        return None
    from quantum.core.features.ui_engine.src.ast_nodes import UIColumnNode
    from quantum.runtime.table_params import TableParamsError, columns_of
    config = getattr(renderer, 'config', None) or {}
    try:
        columns = {c.name: c for c in columns_of(config, table_node.edit_datasource, table_node.edit)}
    except TableParamsError as exc:
        raise ValueError(f'<ui:table edit="{table_node.edit}">: {exc} (UI-13)') from exc
    keys = [c for c in columns.values() if c.primary_key]
    if len(keys) != 1:
        raise ValueError(f'<ui:table edit="{table_node.edit}">: the table needs one primary key column '
                         f'to know which row a cell is (UI-13)')
    editable = {}
    for column in table_node.children:
        if isinstance(column, UIColumnNode) and column.key and column.edit and not column.children:
            if column.key in columns and not columns[column.key].primary_key:
                editable[column.key] = columns[column.key]
    return {'table': table_node.edit, 'key': keys[0].name, 'columns': editable}


def cell_field(plan: dict, column_schema, row: dict, state: Optional[dict], escape: bool):
    """The field of one cell (with the column's rules), its hidden fields, and its error."""
    from quantum.core.features.ui_engine.src.ast_nodes import UICheckboxNode, UIInputNode, UISelectNode
    from quantum.runtime.table_params import param_from_column
    from quantum.runtime.ui_form_rules import FormContext, prepare_field
    key = plan['key']
    if key not in row:
        raise ValueError(f'<ui:table edit=...>: the rows need the key column "{key}" '
                         f'(add it to the query\'s SELECT) (UI-13)')
    param = param_from_column(column_schema)
    param.name = 'value'
    if str(param.type) == 'boolean':
        field = UICheckboxNode()
    elif param.enum:
        field = UISelectNode()
    else:
        field = UIInputNode()
    field.bind = 'value'
    field.ui_id = f'cell-{column_schema.name}-{row.get(plan["key"])}'   # one id per cell
    current = row.get(column_schema.name)
    identity = f'{column_schema.name}@{row[key]}'
    errors, sent = {}, None
    if state and state.get('action') == EDIT_ACTION and state.get('cell') == identity:
        errors, sent = state.get('errors') or {}, state.get('values') or {}
    ctx = FormContext([param], {'errors': errors, 'values': sent} if sent is not None else None,
                      True, {'value': current})
    field, error = prepare_field(field, ctx, escape)
    hidden = {'action': EDIT_ACTION, '__table': plan['table'], '__key': str(row[key]),
              '__column': column_schema.name}
    return field, hidden, error


CELL_CSS = """
/* UI-13: a cell edited in place */
.q-cell { display: flex; gap: 4px; align-items: center; margin: 0; }
.q-cell .q-input, .q-cell .q-select { min-width: 0; padding: 2px 6px; }
.q-cell-save { padding: 2px 8px; border: 1px solid var(--q-border, #d0d7de); border-radius: 6px;
  background: transparent; cursor: pointer; }
.q-sort { color: inherit; text-decoration: none; }
.q-sort:hover { text-decoration: underline; }
"""


def _walk(nodes):
    for node in nodes or []:
        yield node
        for field in ('statements', 'children', 'body', 'if_body', 'else_body'):
            yield from _walk(getattr(node, field, None))
        for block in getattr(node, 'elseif_blocks', None) or []:
            yield from _walk(block.get('body') if isinstance(block, dict) else getattr(block, 'body', None))


def find_editable_table(ast, table: str, column: str):
    """The <ui:table edit="table"> of this page that shows `column` as editable, or None.

    The server edits only what the page declares: a post naming another table
    or column — a forged form — finds nothing and is refused."""
    from quantum.core.features.ui_engine.src.ast_nodes import UIColumnNode, UITableNode
    for node in _walk(getattr(ast, 'statements', None)):
        if isinstance(node, UITableNode) and node.edit == table:
            for child in node.children:
                if isinstance(child, UIColumnNode) and child.key == column and child.edit and not child.children:
                    return node
    return None


def query_nodes(ast) -> Dict[str, object]:
    """The page's q:query nodes by name (a sortable table checks its query)."""
    from quantum.core.ast_nodes import QueryNode
    return {n.name: n for n in _walk(getattr(ast, 'statements', None)) if isinstance(n, QueryNode)}
