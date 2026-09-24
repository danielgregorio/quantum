"""The database as it is: tables, columns, constraints — and SQL checked against it (M8).

One schema reader for the tools that need to know the database: `quantum
check` (M8) compiles each q:query against it, the declarative schema (M6)
diffs against it, and forms from a table (M17) read NOT NULL, CHECK … IN and
foreign keys from it.

Nothing here writes: SQLite is opened read-only, and a query is compiled
(EXPLAIN) — never run. A SELECT's result columns come from running it with
LIMIT 0, which returns no row.
"""

import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class SchemaError(Exception):
    """The database cannot be read (missing file, unsupported driver)."""


@dataclass
class Column:
    name: str
    type: str = ''
    not_null: bool = False
    default: Optional[str] = None
    primary_key: bool = False
    options: Optional[List[str]] = None           # CHECK (col IN ('a', 'b'))
    references: Optional[Tuple[str, str]] = None  # (table, column) of a foreign key


@dataclass
class Table:
    name: str
    columns: Dict[str, Column] = field(default_factory=dict)


def connect_readonly(config: dict, base: Path):
    """A read-only connection to a datasource. SQLite only, for now."""
    driver = str(config.get('driver') or config.get('type') or '').lower()
    if driver != 'sqlite':
        raise SchemaError(f'driver {driver or "?"!r} is not supported yet (sqlite is)')
    database = config.get('database')
    if not database:
        raise SchemaError('the datasource has no database: path')
    db_path = Path(database)
    if not db_path.is_absolute():
        db_path = base / db_path
    if not db_path.exists():
        raise SchemaError(f'{db_path} does not exist — run `quantum migrate up` first')
    return sqlite3.connect(f'{db_path.resolve().as_uri()}?mode=ro', uri=True)


_CHECK_IN = re.compile(r'CHECK\s*\(\s*"?(\w+)"?\s+IN\s*\(([^)]*)\)\s*\)', re.I)


def read_schema(conn) -> Dict[str, Table]:
    """Every user table with its columns, NOT NULL, defaults, keys, CHECK … IN and foreign keys."""
    tables: Dict[str, Table] = {}
    for table_name, sql in conn.execute(
            "SELECT name, sql FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"):
        table = Table(table_name)
        for _cid, col_name, col_type, not_null, default, pk in conn.execute(f'PRAGMA table_info("{table_name}")'):
            table.columns[col_name] = Column(col_name, col_type or '', bool(not_null), default, bool(pk))
        for col_name, values in _CHECK_IN.findall(sql or ''):
            if col_name in table.columns:
                table.columns[col_name].options = [v.strip().strip("'\"") for v in values.split(',') if v.strip()]
        for fk in conn.execute(f'PRAGMA foreign_key_list("{table_name}")'):
            _id, _seq, target, from_col, to_col = fk[:5]
            if from_col in table.columns:
                table.columns[from_col].references = (target, to_col)
        tables[table_name] = table
    return tables


_PARAM = re.compile(r'(?<![:\w]):(\w+)')


def check_sql(conn, sql: str) -> Tuple[Optional[str], Optional[List[str]]]:
    """(error, result columns) of a q:query's SQL, compiled against the database.

    The error is the database's own ("no such column: title"); columns is
    None for a statement that returns no rows (INSERT, UPDATE, DELETE).
    """
    params = {name: None for name in _PARAM.findall(sql)}
    try:
        conn.execute(f'EXPLAIN {sql}', params)
    except sqlite3.Error as exc:
        return str(exc), None
    if not re.match(r'\s*(SELECT|WITH)\b', sql, re.I):
        return None, None
    try:
        cursor = conn.execute(f'SELECT * FROM ({sql.strip().rstrip(";")}) LIMIT 0', params)
    except sqlite3.Error:
        return None, None                       # compiles, but cannot be wrapped (rare): no columns
    return None, [d[0] for d in cursor.description or []]
