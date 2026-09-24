"""`quantum migrate plan`: a declarative schema (M6, DB-10).

You edit `schema.sql` — the tables as they should be. `quantum migrate plan`
compares it with the schema the migrations produce, shows what changes, marks
what loses data, and `--write` saves the migration (and its rollback) after
confirmation. `quantum migrate up` applies it as any other.

Both sides are built in in-memory SQLite databases — the migrations applied in
order, and schema.sql — and compared with the schema reader of `quantum check`
(quantum/runtime/db_schema.py). The development database is not read: the
plan is the same on any machine and in CI.

SQLite can add a column but not change one, so any other change to a table
rebuilds it: create the new table, copy the columns both have, drop the old,
rename. Before a plan is written it is checked: applied to the migrations'
schema it must produce exactly schema.sql's.
"""

import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from quantum.runtime.db_schema import Column, read_schema

# Tables that belong to Quantum, not to the app's schema.
INTERNAL_TABLES = {'_migrations', 'quantum_history'}


class SchemaPlanError(Exception):
    """The plan cannot be made (no schema.sql, invalid SQL, a change it cannot express)."""


@dataclass
class Step:
    kind: str                 # add-table, drop-table, add-column, rebuild, add-index, drop-index
    target: str               # "posts" or "posts.summary"
    detail: str = ''
    sql: List[str] = field(default_factory=list)
    loses_data: bool = False
    warning: str = ''

    def line(self) -> str:
        mark = {'add-table': '+', 'add-column': '+', 'add-index': '+', 'drop-table': '-',
                'drop-index': '-', 'rebuild': '~'}.get(self.kind, '?')
        text = f'{mark} {self.kind.replace("-", " ")} {self.target}'
        if self.detail:
            text += f' ({self.detail})'
        if self.loses_data:
            text += '  !! loses data'
        if self.warning:
            text += f'  !! {self.warning}'
        return text


def _database(scripts: List[Tuple[str, str]]) -> sqlite3.Connection:
    conn = sqlite3.connect(':memory:')
    for origin, sql in scripts:
        try:
            conn.executescript(sql)
        except sqlite3.Error as exc:
            raise SchemaPlanError(f'{origin}: {exc}') from exc
    return conn


def _migration_scripts(migrations_dir: Path) -> List[Tuple[str, str]]:
    if not migrations_dir.exists():
        return []
    files = [f for f in sorted(migrations_dir.glob('*.sql')) if not f.name.endswith('.down.sql')]
    return [(f.name, f.read_text(encoding='utf-8')) for f in files if '_' in f.stem]


def _tables(conn) -> Dict[str, object]:
    return {name: t for name, t in read_schema(conn).items() if name not in INTERNAL_TABLES}


def _create_sql(conn, table: str) -> str:
    return conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
                        (table,)).fetchone()[0]


def _indexes(conn) -> Dict[str, Tuple[str, str]]:
    """Explicit indexes: name -> (table, sql)."""
    return {name: (table, sql) for name, table, sql in conn.execute(
        "SELECT name, tbl_name, sql FROM sqlite_master WHERE type = 'index' AND sql IS NOT NULL")
        if table not in INTERNAL_TABLES}


def _column_sql(column: Column) -> str:
    parts = [f'"{column.name}"']
    if column.type:
        parts.append(column.type)
    if column.not_null:
        parts.append('NOT NULL')
    if column.default is not None:
        parts.append(f'DEFAULT {column.default}')
    if column.options:
        options = ', '.join("'" + o.replace("'", "''") + "'" for o in column.options)
        parts.append(f'CHECK ("{column.name}" IN ({options}))')
    if column.references:
        parts.append(f'REFERENCES "{column.references[0]}"("{column.references[1]}")')
    return ' '.join(parts)


def _differences(a: Column, b: Column) -> List[str]:
    changed = []
    for label, x, y in (('type', (a.type or '').upper(), (b.type or '').upper()),
                        ('NOT NULL', a.not_null, b.not_null), ('default', a.default, b.default),
                        ('primary key', a.primary_key, b.primary_key), ('CHECK', a.options, b.options),
                        ('references', a.references, b.references)):
        if x != y:
            changed.append(label)
    return changed


def diff(current_db, desired_db) -> List[Step]:
    """The steps that turn the first database's schema into the second's."""
    current, desired = _tables(current_db), _tables(desired_db)
    steps: List[Step] = []
    rebuilt = set()

    for name in sorted(set(desired) - set(current)):
        steps.append(Step('add-table', name, sql=[_create_sql(desired_db, name) + ';']))

    for name in sorted(set(current) & set(desired)):
        before, after = current[name].columns, desired[name].columns
        added = [c for c in after if c not in before]
        removed = [c for c in before if c not in after]
        changed = {c: _differences(before[c], after[c]) for c in before
                   if c in after and _differences(before[c], after[c])}
        addable = all(not after[c].primary_key and (not after[c].not_null or after[c].default is not None)
                      for c in added)
        if not removed and not changed and addable:
            for c in added:
                steps.append(Step('add-column', f'{name}.{c}', after[c].type or '',
                                  [f'ALTER TABLE "{name}" ADD COLUMN {_column_sql(after[c])};']))
            continue
        if not (added or removed or changed):
            continue
        common = ', '.join(f'"{c}"' for c in after if c in before)
        create = re.sub(r'^\s*CREATE\s+TABLE\s+("?)' + re.escape(name) + r'\1',
                        f'CREATE TABLE "{name}__new"', _create_sql(desired_db, name), count=1, flags=re.I)
        details = [f'+ {c}' for c in added] + [f'- {c}' for c in removed] + \
                  [f'{c}: {", ".join(d)}' for c, d in changed.items()]
        warning = ''
        if any('NOT NULL' in d and after[c].not_null for c, d in changed.items()) or \
                any(after[c].not_null and after[c].default is None for c in added):
            warning = 'fails if existing rows have no value for a NOT NULL column'
        steps.append(Step('rebuild', name, '; '.join(details), [
            create + ';',
            f'INSERT INTO "{name}__new" ({common}) SELECT {common} FROM "{name}";',
            f'DROP TABLE "{name}";',
            f'ALTER TABLE "{name}__new" RENAME TO "{name}";',
        ], loses_data=bool(removed) or any('type' in d for d in changed.values()), warning=warning))
        rebuilt.add(name)

    for name in sorted(set(current) - set(desired)):
        steps.append(Step('drop-table', name, sql=[f'DROP TABLE "{name}";'], loses_data=True))

    # Indexes: a rebuilt table lost its own, so they are created again.
    before_idx, after_idx = _indexes(current_db), _indexes(desired_db)
    for name, (table, sql) in sorted(before_idx.items()):
        if table in desired and table not in rebuilt and after_idx.get(name, (None, None))[1] != sql:
            steps.append(Step('drop-index', name, sql=[f'DROP INDEX "{name}";']))
    for name, (table, sql) in sorted(after_idx.items()):
        if before_idx.get(name, (None, None))[1] != sql or table in rebuilt:
            steps.append(Step('add-index', name, sql=[sql + ';']))
    return steps


def _schema_only(conn) -> str:
    """The CREATE statements of a database, tables before indexes, without its rows."""
    rows = conn.execute("SELECT type, sql FROM sqlite_master WHERE sql IS NOT NULL "
                        "AND name NOT LIKE 'sqlite_%' ORDER BY type = 'index', rowid").fetchall()
    return '\n'.join(sql + ';' for _type, sql in rows)


def _signature(conn) -> tuple:
    tables = _tables(conn)
    return (tuple(sorted((n, tuple(sorted((c.name, (c.type or '').upper(), c.not_null, c.default, c.primary_key,
                                              tuple(c.options or ()), c.references)
                                             for c in t.columns.values()))) for n, t in tables.items())),
            tuple(sorted((n, s) for n, (_t, s) in _indexes(conn).items())))


@dataclass
class Plan:
    steps: List[Step]
    up_sql: str
    down_sql: str

    @property
    def loses_data(self) -> bool:
        return any(s.loses_data for s in self.steps)


def make_plan(schema_file: Path, migrations_dir: Path) -> Plan:
    if not schema_file.exists():
        raise SchemaPlanError(f'{schema_file} does not exist: write the tables as they should be, '
                              f'e.g. CREATE TABLE posts (id INTEGER PRIMARY KEY, title TEXT NOT NULL);')
    migrations = _migration_scripts(migrations_dir)
    current = _database(migrations)
    desired = _database([(schema_file.name, schema_file.read_text(encoding='utf-8'))])
    steps = diff(current, desired)
    up = '\n'.join(s for step in steps for s in step.sql)
    down = '\n'.join(s for step in diff(desired, current) for s in step.sql)
    if steps:
        # The plan must do what it says: applied, it yields schema.sql's schema.
        # Checked on the structure only — what existing rows may break is the
        # step's warning, shown in the plan, not a reason to hide the plan.
        check = _database([('migrations (schema only)', _schema_only(current)), ('plan', up)])
        if _signature(check) != _signature(desired):
            raise SchemaPlanError('the generated migration does not reproduce schema.sql — '
                                  'write this change as a migration by hand (quantum migrate create)')
    return Plan(steps, up, down)


def next_version(migrations_dir: Path) -> str:
    numbers = [int(m.group(1)) for f in migrations_dir.glob('V*.sql')
               for m in [re.match(r'V(\d+)_', f.name)] if m]
    return f'V{(max(numbers) + 1 if numbers else 1):03d}'


def write_plan(plan: Plan, migrations_dir: Path, name: str) -> Path:
    migrations_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r'[^a-z0-9_]+', '_', name.lower()).strip('_') or 'schema'
    version = next_version(migrations_dir)
    path = migrations_dir / f'{version}_{slug}.sql'
    header = '-- Generated by `quantum migrate plan` from schema.sql (DB-10)\n'
    summary = '\n'.join(f'-- {s.line()}' for s in plan.steps)
    path.write_text(f'{header}{summary}\n\n{plan.up_sql}\n', encoding='utf-8')
    (migrations_dir / f'{version}_{slug}.down.sql').write_text(
        f'{header}-- rollback\n\n{plan.down_sql}\n', encoding='utf-8')
    return path


def run_plan(project: Path, schema: Optional[str], write: Optional[str], yes: bool,
             allow_data_loss: bool, ask=input, interactive: bool = True) -> int:
    """The `quantum migrate plan` command. Returns the exit code."""
    from quantum.cli.migrations import _paths_migrations
    migrations_dir = project / _paths_migrations(project)
    schema_file = project / (schema or 'schema.sql')
    try:
        plan = make_plan(schema_file, migrations_dir)
    except SchemaPlanError as exc:
        print(f'[ERROR] {exc}')
        return 1
    if not plan.steps:
        print(f'Nothing to do: the migrations already produce {schema_file.name}.')
        return 0
    print(f'Plan: {schema_file.name} vs. the migrations in {migrations_dir.name}/\n')
    for step in plan.steps:
        print('  ' + step.line())
    print('\nSQL:\n' + plan.up_sql)
    if not write:
        print('\nNothing written. `quantum migrate plan --write <name>` saves it as a migration.')
        return 0
    if plan.loses_data and not allow_data_loss:
        print('\n[REFUSED] This plan loses data (marked !!). Check it, then run again with '
              '--allow-data-loss.')
        return 1
    if not yes:
        if not interactive:
            print('\n[REFUSED] Confirm with --yes (not a terminal: nobody to ask).')
            return 1
        answer = ask(f'\nWrite migration {next_version(migrations_dir)}_{write}? [y/N] ').strip().lower()
        if answer not in ('y', 'yes'):
            print('Nothing written.')
            return 1
    path = write_plan(plan, migrations_dir, write)
    print(f'Written: {path} (and {path.stem}.down.sql). Apply with `quantum migrate up`.')
    return 0
