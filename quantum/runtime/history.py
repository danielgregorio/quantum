"""Change history, per datasource (M22, DB-11).

With `history: true` on a datasource, every write an action makes to it —
INSERT, UPDATE, DELETE, including the cells of an editable table (UI-13) — is
recorded in a `quantum_history` table of that same database: when, who (the
session's user), which action, which row, and the row before and after, as
JSON. The record is written on the same connection, before the commit, so a
write and its history commit or roll back together.

Only writes made by actions are recorded: page statements do not write in a
well-formed app, and migrations are not changes to records. A write whose
shape is not a single-table INSERT/UPDATE/DELETE is still recorded, with its
SQL and no before/after — never skipped silently.

`<ui:history table="posts" key="{post.id}" datasource="db">` shows a row's
history on any page.
"""

import contextvars
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

TABLE = 'quantum_history'

CREATE_SQL = (f'CREATE TABLE IF NOT EXISTS {TABLE} ('
              'id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, user TEXT, action TEXT, '
              'table_name TEXT NOT NULL, row_key TEXT, op TEXT NOT NULL, before TEXT, after TEXT, '
              'sql TEXT)')

_ACTION = contextvars.ContextVar('quantum_history_action', default=None)

_WRITE = re.compile(r'^\s*(INSERT\s+(?:OR\s+\w+\s+)?INTO|UPDATE|DELETE\s+FROM)\s+"?(\w+)"?', re.I)
_WHERE = re.compile(r'\bWHERE\b(.*)$', re.I | re.S)


def enter(action: str, session_vars: Optional[dict]):
    """Mark the writes that follow as made by this action, for this user."""
    session = session_vars or {}
    user = session.get('userName') or session.get('userId')
    return _ACTION.set({'action': action, 'user': None if user is None else str(user)})


def leave(token) -> None:
    _ACTION.reset(token)


def current() -> Optional[dict]:
    return _ACTION.get()


def parse_write(sql: str):
    """(op, table, where) of a single-table write, or None when it is not one."""
    m = _WRITE.match(sql)
    if not m:
        return None
    op = {'INSERT': 'insert', 'UPDATE': 'update', 'DELETE': 'delete'}[m.group(1).split()[0].upper()]
    where = _WHERE.search(sql)
    return op, m.group(2), (where.group(1).strip().rstrip(';') if where else None)


class Capture:
    """One write being recorded: the rows before, then the rows after."""

    def __init__(self, op: str, table: str, sql: str, key: Optional[str], before: List[dict], shaped: bool):
        self.op, self.table, self.sql, self.key = op, table, sql, key
        self.before, self.shaped = before, shaped


def _rows(cursor) -> List[dict]:
    columns = [d[0] for d in cursor.description or []]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _primary_key(conn, table: str) -> Optional[str]:
    keys = [row[1] for row in conn.execute(f'PRAGMA table_info("{table}")') if row[5]]
    return keys[0] if len(keys) == 1 else None


def begin(conn, sql: str, params, prepare) -> Optional[Capture]:
    """Before a write: which rows it will touch, as they are. None when nothing is recorded."""
    state = current()
    if state is None:
        return None
    shape = parse_write(sql)
    if shape is None:
        table = re.search(r'\b(?:INTO|UPDATE|FROM)\s+"?(\w+)"?', sql, re.I)
        if not table or table.group(1) == TABLE:
            return None
        return Capture('write', table.group(1), sql, None, [], shaped=False)
    op, table, where = shape
    if table == TABLE:
        return None
    key = _primary_key(conn, table)
    before: List[dict] = []
    if op in ('update', 'delete'):
        query, args = prepare(f'SELECT * FROM "{table}"' + (f' WHERE {where}' if where else ''), params)
        cursor = conn.cursor()
        cursor.execute(query, args)
        before = _rows(cursor)
        cursor.close()
    return Capture(op, table, sql, key, before, shaped=True)


def finish(conn, capture: Optional[Capture], last_row_id: Optional[int]) -> None:
    """After the write, before the commit: record each row it changed."""
    if capture is None:
        return
    state = current() or {}
    conn.execute(CREATE_SQL)
    records = []
    if not capture.shaped:
        records.append((None, None, None))
    elif capture.op == 'insert':
        row = None
        if last_row_id:
            cursor = conn.execute(f'SELECT * FROM "{capture.table}" WHERE rowid = ?', (last_row_id,))
            found = _rows(cursor)
            row = found[0] if found else None
        key = row.get(capture.key) if (row and capture.key) else last_row_id
        records.append((key, None, row))
    else:
        for before in capture.before:
            key = before.get(capture.key) if capture.key else None
            after = None
            if capture.op == 'update' and capture.key:
                cursor = conn.execute(f'SELECT * FROM "{capture.table}" WHERE "{capture.key}" = ?', (key,))
                found = _rows(cursor)
                after = found[0] if found else None
            records.append((key, before, after))
    now = datetime.now().isoformat(timespec='seconds')
    for key, before, after in records:
        conn.execute(
            f'INSERT INTO {TABLE} (at, user, action, table_name, row_key, op, before, after, sql) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (now, state.get('user'), state.get('action'), capture.table,
             None if key is None else str(key), capture.op,
             None if before is None else json.dumps(before, default=str, ensure_ascii=False),
             None if after is None else json.dumps(after, default=str, ensure_ascii=False),
             None if capture.shaped else capture.sql))


def changes(before: Optional[dict], after: Optional[dict]) -> List[tuple]:
    """(column, old, new) of what an update changed."""
    if not before or not after:
        return []
    return [(c, before.get(c), after.get(c)) for c in after if before.get(c) != after.get(c)]


def read(conn, table: str, key: Any, limit: int = 50) -> List[dict]:
    """A row's history, newest first; empty when nothing was ever recorded."""
    exists = conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (TABLE,)).fetchone()
    if not exists:
        return []
    cursor = conn.execute(
        f'SELECT at, user, action, op, before, after, sql FROM {TABLE} '
        'WHERE table_name = ? AND row_key = ? ORDER BY id DESC LIMIT ?', (table, str(key), limit))
    result = []
    for at, user, action, op, before, after, sql in cursor.fetchall():
        result.append({'at': at, 'user': user, 'action': action, 'op': op,
                          'before': json.loads(before) if before else None,
                          'after': json.loads(after) if after else None, 'sql': sql})
    return result


def entries_for(renderer, node) -> List[Dict[str, str]]:
    """<ui:history>: the row's entries as text — when, who, action, change (web and console)."""
    from pathlib import Path
    from quantum.runtime.db_schema import SchemaError, connect_readonly
    config = getattr(renderer, 'config', None) or {}
    sources = config.get('datasources') or {}
    if node.datasource not in sources:
        raise ValueError(f'<ui:history datasource="{node.datasource}">: not declared in quantum.config.yaml')
    if not sources[node.datasource].get('history'):
        raise ValueError(f'<ui:history>: datasource "{node.datasource}" does not record history — '
                         f'add `history: true` to it (DB-11)')
    key = renderer._apply_databinding(node.key) if '{' in (node.key or '') else node.key
    try:
        conn = connect_readonly(sources[node.datasource], Path.cwd())
    except SchemaError as exc:
        raise ValueError(f'<ui:history>: {exc}') from exc
    try:
        entries = read(conn, node.table, key, node.limit)
    finally:
        conn.close()
    lines = []
    for entry in entries:
        if entry['op'] == 'insert':
            change = 'created'
        elif entry['op'] == 'delete':
            change = 'deleted'
        elif entry['op'] == 'update':
            change = '; '.join(f'{c}: {old} → {new}' for c, old, new in changes(entry['before'], entry['after']))                 or 'no change'
        else:
            change = entry.get('sql') or entry['op']
        lines.append({'at': entry['at'].replace('T', ' '), 'user': entry['user'] or '—',
                      'action': entry['action'] or '—', 'change': change})
    return lines


HEADERS = (('at', 'When'), ('user', 'Who'), ('action', 'Action'), ('change', 'Change'))

