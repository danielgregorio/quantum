"""An action's params from a table's schema (M17, UI-10).

`<q:action name="create" table="posts" datasource="db">` validates what it
receives by the table it writes to: a NOT NULL column without a default is
required, `CHECK (col IN (...))` is an enum, `VARCHAR(n)` a maxlength, the
column type the param type, and a foreign key must name an existing row. A
`q:param` written in the action wins over the one from the schema.

The schema is read from the database (quantum/runtime/db_schema.py) the first
time, and again when the database file changes. A form that posts to such an
action and has no fields of its own draws one for each param (UI-10).
"""

import os
import re
import threading
from pathlib import Path
from typing import Dict, List, Tuple

from quantum.core.ast_nodes import QuantumParam

_CACHE: Dict[tuple, Tuple[float, list]] = {}
_LOCK = threading.Lock()


class TableParamsError(Exception):
    """The table cannot be read (missing, unsupported driver)."""


def _param_type(column) -> str:
    t = (column.type or '').upper()
    if 'BOOL' in t:
        return 'boolean'
    if 'INT' in t:
        return 'integer'
    if any(x in t for x in ('REAL', 'FLOA', 'DOUB', 'NUMERIC', 'DECIMAL')):
        return 'decimal'
    if t.startswith('DATE') and 'TIME' not in t:
        return 'date'
    return 'string'


def _datasource(config: dict, name: str) -> dict:
    sources = (config or {}).get('datasources') or {}
    if name not in sources:
        raise TableParamsError(f'datasource {name!r} is not declared in quantum.config.yaml')
    return sources[name]


def _connect(config: dict, name: str):
    from quantum.runtime.db_schema import SchemaError, connect_readonly
    try:
        return connect_readonly(_datasource(config, name), Path.cwd())
    except SchemaError as exc:
        raise TableParamsError(f'datasource {name!r}: {exc}') from exc


def _read_columns(config: dict, name: str, table: str):
    from quantum.runtime.db_schema import read_schema
    conn = _connect(config, name)
    try:
        schema = read_schema(conn)
    finally:
        conn.close()
    if table not in schema:
        raise TableParamsError(f'table {table!r} does not exist in datasource {name!r} '
                               f'(tables: {", ".join(schema) or "none"})')
    return list(schema[table].columns.values())


def _mtime(config: dict, name: str) -> float:
    database = str(_datasource(config, name).get('database') or '')
    try:
        return os.path.getmtime(Path(database) if Path(database).is_absolute() else Path.cwd() / database)
    except OSError:
        return 0.0


def columns_of(config: dict, name: str, table: str) -> list:
    key = (str(Path.cwd()), name, table)
    mtime = _mtime(config, name)
    with _LOCK:
        cached = _CACHE.get(key)
        if cached and cached[0] == mtime:
            return cached[1]
    columns = _read_columns(config, name, table)
    with _LOCK:
        _CACHE[key] = (mtime, columns)
    return columns


def param_from_column(column) -> QuantumParam:
    param_type = _param_type(column)
    param = QuantumParam(
        name=column.name, type=param_type,
        required=bool(column.not_null and column.default is None and param_type != 'boolean'),
        enum=','.join(column.options) if column.options else None,
    )
    size = re.search(r'\((\d+)\)', column.type or '')
    if size and param_type == 'string':
        param.maxlength = int(size.group(1))
    if param_type == 'boolean':
        param.default = 'false'
    param.references = column.references            # (table, column) of a foreign key
    # A column that takes NULL: left blank, the action gets None (and writes NULL).
    param.nullable = not column.not_null
    return param


def params_of(action, config: dict) -> List[QuantumParam]:
    """The params an action validates: its own q:params, plus its table's (UI-10)."""
    own = list(getattr(action, 'params', None) or [])
    table = getattr(action, 'table', None)
    if not table:
        return own
    written = {p.name for p in own}
    allowed = getattr(action, 'table_columns', None)
    from_schema = []
    for column in columns_of(config, action.table_datasource, table):
        if column.primary_key or column.name in written:
            continue
        if allowed is not None and column.name not in allowed:
            continue
        from_schema.append(param_from_column(column))
    if allowed is not None:
        missing = [c for c in allowed if c not in {p.name for p in from_schema} | written]
        if missing:
            raise TableParamsError(f'<q:action name="{action.name}" columns=...>: table {table!r} has no '
                                   f'column {", ".join(missing)}')
        order = {name: i for i, name in enumerate(allowed)}
        from_schema.sort(key=lambda p: order.get(p.name, len(order)))
    return from_schema + own


def reference_options(config: dict, datasource: str, reference: Tuple[str, str]) -> List[Tuple[str, str]]:
    """(value, label) of the rows a foreign key may point to — label is the first text column."""
    table, column = reference
    columns = columns_of(config, datasource, table)
    preferred = ('nome', 'name', 'titulo', 'title', 'label', 'descricao', 'description')
    texts = [c.name for c in columns if _param_type(c) == 'string']
    label = next((p for p in preferred if p in texts), texts[0] if texts else column)
    conn = _connect(config, datasource)
    try:
        rows = conn.execute(
            f'SELECT "{column}", "{label}" FROM "{table}" ORDER BY "{label}" LIMIT 1000').fetchall()
    finally:
        conn.close()
    return [(str(v), str(r)) for v, r in rows]


def reference_exists(config: dict, datasource: str, reference: Tuple[str, str], value) -> bool:
    table, column = reference
    conn = _connect(config, datasource)
    try:
        return conn.execute(f'SELECT 1 FROM "{table}" WHERE "{column}" = ? LIMIT 1', (value,)).fetchone() is not None
    finally:
        conn.close()


def humanize(name: str) -> str:
    """'author_id' -> 'Author'; 'published_on' -> 'Published on'."""
    base = re.sub(r'_id$', '', name).replace('_', ' ').strip()
    return base[:1].upper() + base[1:] if base else name
