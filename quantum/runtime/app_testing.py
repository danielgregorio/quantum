"""`quantum test`: run the `*.test.q` suites of an app (TEST-1..TEST-4).

Each `q:test` gets a world of its own: a temporary folder, a fresh SQLite
database per datasource built by the app's migrations (DB-10), a new server
object and a new browser session. The steps go through the real server
in-process — the same Flask app `quantum start` serves, with the per-request
runtime (ACT-10) — so a `test:submit` takes exactly the path a browser post
takes: guards, the action's rules, history, redirect and flash. Nothing listens
on a port.

What the server did in each request (queries, variables, the page's error and
line) comes from the /_dev recorder (DEV-1), attached to the test server
whatever `server.debug` says.
"""

import copy
import os
import re
import sqlite3
import tempfile
import time
from dataclasses import dataclass, field
from html import unescape
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode, urlsplit

import yaml

from quantum.core.features.native_testing.src import (
    TestCaseNode, TestFileNode, TestParseError, TestStepNode, is_test_file, parse_test_source)
from quantum.core.features.native_testing.src.parser import QUERIES

# Folders never searched for tests.
_SKIP_DIRS = {'.git', 'node_modules', '__pycache__', 'data', '.quantum', '.venv', 'venv', 'dist'}
_MAX_REDIRECTS = 10


class StepFailure(Exception):
    """A step did not hold. `where` is the page line a failing request points at (DEV-2)."""

    def __init__(self, message: str, where: Optional[Tuple[str, int]] = None):
        super().__init__(message)
        self.where = where


@dataclass
class TestResult:
    __test__ = False                     # not a pytest class
    file: str
    name: str
    line: Optional[int]
    passed: bool
    ms: float = 0.0
    message: str = ''
    step: Optional[TestStepNode] = None
    where: Optional[Tuple[str, int]] = None


@dataclass
class RunReport:
    results: List[TestResult] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)      # files that could not be read or run

    @property
    def failed(self) -> List[TestResult]:
        return [r for r in self.results if not r.passed]

    @property
    def ok(self) -> bool:
        return bool(self.results) and not self.failed and not self.errors


# -- finding the tests --------------------------------------------------------

def find_test_files(paths: List[str]) -> Tuple[List[Path], List[str]]:
    """The `*.test.q` files under `paths` (TEST-1), and the paths that are not tests."""
    found: List[Path] = []
    problems: List[str] = []
    for raw in paths or ['.']:
        path = Path(raw)
        if path.is_file():
            if is_test_file(path):
                found.append(path)
            else:
                problems.append(f'{raw}: not a test file (test files are named *.test.q)')
        elif path.is_dir():
            for candidate in sorted(path.rglob('*.test.q')):
                if not _SKIP_DIRS & set(candidate.relative_to(path).parts[:-1]):
                    found.append(candidate)
        else:
            problems.append(f'{raw}: no such file or folder')
    unique = list(dict.fromkeys(p.resolve() for p in found))
    return unique, problems


def app_root_of(test_file: Path) -> Optional[Path]:
    """The folder with the quantum.config.yaml the test file belongs to."""
    for folder in [test_file.parent, *test_file.parent.parents]:
        if (folder / 'quantum.config.yaml').is_file():
            return folder
    return None


# -- one test's world ---------------------------------------------------------

class TestWorld:
    """A fresh database, a new server and a new session, for one q:test (TEST-1)."""
    __test__ = False

    def __init__(self, app_root: Path):
        self.app_root = app_root
        self._tmp = tempfile.TemporaryDirectory(prefix='quantum-test-', ignore_cleanup_errors=True)
        self.tmp = Path(self._tmp.name)
        self._cwd = os.getcwd()
        self._env: Dict[str, Optional[str]] = {}
        self.databases: Dict[str, Path] = {}
        self.history_datasources: set = set()
        self._generated = 0
        try:
            self._build()
        except Exception:
            self.close()
            raise

    # -- setup ----------------------------------------------------------------

    def _build(self) -> None:
        from quantum.core.config_env import expand_env
        config_file = self.app_root / 'quantum.config.yaml'
        config = expand_env(yaml.safe_load(config_file.read_text(encoding='utf-8')) or {})
        config = copy.deepcopy(config)
        datasources = config.get('datasources') or {}
        for name, ds in datasources.items():
            driver = str((ds or {}).get('driver') or (ds or {}).get('type') or '').lower()
            if driver != 'sqlite':
                raise StepFailure(f'datasource "{name}" is {driver or "?"}: quantum test builds a fresh '
                                  f'SQLite database for each test, and supports only sqlite datasources for now')
            db = self.tmp / f'{name}.db'
            ds['database'] = str(db)
            self.databases[name] = db
            if ds.get('history'):
                self.history_datasources.add(name)
            # database_service lets QUANTUM_<NAME>_PATH replace the path: never the real database.
            self._set_env(f'QUANTUM_{name.upper()}_PATH', str(db))
        paths = config.setdefault('paths', {}) or {}
        config['paths'] = paths
        migrations = self.app_root / (paths.get('migrations') or 'migrations')
        paths['migrations'] = str(migrations)
        # Whatever the server writes goes to the test's folder, never the app's:
        # uploads, logs, and the CSS/JS it extracts from the pages into static/.
        paths['uploads'] = str(self.tmp / 'uploads')
        paths['static'] = str(self.tmp / 'static')
        paths['logs'] = str(self.tmp / 'logs')
        config['logging'] = {'level': 'WARNING', 'console': False, 'file': False}
        (self.tmp / 'quantum.config.yaml').write_text(yaml.safe_dump(config, allow_unicode=True),
                                                      encoding='utf-8')
        for db in self.databases.values():
            sqlite3.connect(db).close()                       # the server opens existing files only (DB-7)
        self._migrate(migrations)

        os.chdir(self.app_root)                               # the app's relative paths are its folder's
        from quantum.runtime.dev_panel import DevPanel
        from quantum.runtime.web_server import QuantumWebServer
        self.server = QuantumWebServer(str(self.tmp / 'quantum.config.yaml'))
        self.server.app.config['TESTING'] = True
        # DEV-1's recorder, attached whatever server.debug says: the report reads
        # queries, variables and the page's error from it. /_dev itself stays off.
        self.server.dev_panel = DevPanel(keep=_MAX_REDIRECTS + 2)
        self.client = self.server.app.test_client()

    def _migrate(self, migrations: Path) -> None:
        if not migrations.is_dir() or not any(migrations.glob('*.sql')):
            return
        if not self.databases:
            raise StepFailure(f'{migrations.name}/ has migrations, but quantum.config.yaml declares no '
                              f'datasource for them to build')
        if len(self.databases) != 1:
            raise StepFailure(f'several datasources are declared ({", ".join(self.databases)}): quantum test '
                              f'applies the migrations in {migrations.name}/ to one, and cannot tell which')
        import contextlib
        import io
        from quantum.cli.migrations import MigrationRunner
        with contextlib.redirect_stdout(io.StringIO()):          # "Applying V001…" is noise in a report
            results = MigrationRunner(self.tmp).up()
        failed = [r for r in results if r.get('status') != 'applied']
        if failed:
            raise StepFailure(f'the migrations did not apply: {failed[0]}')

    def _set_env(self, key: str, value: str) -> None:
        self._env.setdefault(key, os.environ.get(key))
        os.environ[key] = value

    def close(self) -> None:
        self.server = self.client = None
        import gc
        gc.collect()                                          # the runtimes' SQLite connections, before the files go
        os.chdir(self._cwd)
        for key, value in self._env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self._tmp.cleanup()

    # -- the database ---------------------------------------------------------

    def datasource(self, name: Optional[str], step: TestStepNode) -> Tuple[str, Path]:
        if name:
            if name not in self.databases:
                raise StepFailure(f'no datasource "{name}"; declared: {", ".join(self.databases) or "none"}')
            return name, self.databases[name]
        if len(self.databases) == 1:
            return next(iter(self.databases.items()))
        if not self.databases:
            raise StepFailure('the app declares no datasource')
        raise StepFailure(f'several datasources are declared ({", ".join(self.databases)}): '
                          f'say which with datasource="…"')

    def connect(self, path: Path) -> sqlite3.Connection:
        return sqlite3.connect(path, timeout=30.0)

    def next_generated(self) -> int:
        self._generated += 1
        return self._generated


# -- running ------------------------------------------------------------------

class TestRun:
    """The steps of one q:test, in order, against its world."""
    __test__ = False

    def __init__(self, test: TestCaseNode, world: TestWorld):
        self.test = test
        self.world = world
        self.current = test.page                 # where a test:submit posts, like the form on the page
        self.last: Optional[Dict[str, Any]] = None

    # -- requests -------------------------------------------------------------

    def _record(self):
        requests = self.world.server.dev_panel.requests
        return requests[0] if requests else None

    def _session(self) -> Dict[str, Any]:
        with self.world.client.session_transaction() as sess:
            return {'flash': copy.deepcopy(sess.get('flash')),
                    'form_state': copy.deepcopy(sess.get('form_state'))}

    def _follow(self, response, result: Dict[str, Any]) -> None:
        """Follow redirects like a browser; the page shown is the last response."""
        hops = 0
        while response.status_code in (301, 302, 303, 307, 308) and response.headers.get('Location'):
            hops += 1
            if hops > _MAX_REDIRECTS:
                raise StepFailure(f'more than {_MAX_REDIRECTS} redirects in a row (a redirect loop?)')
            target = _local_url(response.headers['Location'])
            response = self.world.client.get(target, headers={'Referer': 'http://localhost' + self.current})
            self.current = target
        result['page_status'] = response.status_code
        result['page_html'] = response.get_data(as_text=True)
        result['page_record'] = self._record()

    def _request(self, method: str, url: str, data=None) -> Dict[str, Any]:
        client = self.world.client
        headers = {'Referer': 'http://localhost' + self.current}
        response = (client.post(url, data=data, headers=headers) if method == 'POST'
                    else client.get(url, headers=headers))
        record = self._record()
        state = self._session()
        result = {'status': response.status_code, 'location': response.headers.get('Location'),
                  'record': record, 'flash': state['flash'], 'form_state': state['form_state'],
                  'method': method, 'url': url}
        if method == 'GET':
            self.current = url
        self._follow(response, result)
        return result

    # -- steps ----------------------------------------------------------------

    def run(self) -> None:
        steps = self.test.steps
        for index, step in enumerate(steps):
            self.step = step
            getattr(self, f'_{step.kind}')(step)
            if step.kind in ('visit', 'submit'):
                following = steps[index + 1] if index + 1 < len(steps) else None
                expects_status = following is not None and following.kind == 'expect' and 'status' in following.attrs
                if not expects_status:
                    self._fail_on_server_error()

    def _fail_on_server_error(self) -> None:
        """A request that answers an error fails the step, with the page's line (DEV-2).

        Unless the test says it expects it: a `test:expect status="…"` right after."""
        last = self.last
        for status, record in ((last['status'], last['record']), (last['page_status'], last['page_record'])):
            if status >= 400:
                error = (record or {}).get('error')
                if not error and status == 404:
                    error = 'no such page'
                if not error and status == 400:
                    error = _clip(page_text(last['page_html']), 200)
                raise StepFailure(f'the server answered {status}' + (f': {error.rstrip(".")}' if error else '')
                                  + '. If that is what this test expects, say so with '
                                  f'<test:expect status="{status}"/> right after', _where(record))

    def _given(self, step: TestStepNode) -> None:
        from quantum.runtime.db_schema import read_schema
        attrs = dict(step.attrs)
        table_name = attrs.pop('table')
        name, path = self.world.datasource(attrs.pop('datasource', None), step)
        conn = self.world.connect(path)
        try:
            schema = read_schema(conn)
            table = schema.get(table_name)
            if table is None:
                raise StepFailure(f'no table "{table_name}" in datasource "{name}" '
                                  f'(tables: {", ".join(sorted(schema)) or "none"})')
            row: Dict[str, Any] = {}
            for column, value in attrs.items():
                col = table.columns.get(column)
                if col is None:
                    raise StepFailure(f'table "{table_name}" has no column "{column}" '
                                      f'(columns: {", ".join(table.columns)})')
                row[column] = _checked_value(conn, table_name, col, value)
            for col in table.columns.values():
                if col.name in row or not col.not_null or col.default is not None or col.primary_key:
                    continue
                row[col.name] = self._generated_value(conn, table_name, col)
            columns = ', '.join(f'"{c}"' for c in row)
            marks = ', '.join('?' for _ in row)
            sql = (f'INSERT INTO "{table_name}" ({columns}) VALUES ({marks})' if row
                   else f'INSERT INTO "{table_name}" DEFAULT VALUES')
            try:
                conn.execute(sql, list(row.values()))
                conn.commit()
            except sqlite3.Error as exc:
                raise StepFailure(f'the schema rejects this row of "{table_name}": {exc}') from None
        finally:
            conn.close()

    def _generated_value(self, conn, table_name: str, col) -> Any:
        """A value for a required column the test did not give (TEST-2)."""
        if col.options:
            return col.options[0]
        if col.references:
            target, key = col.references
            found = conn.execute(f'SELECT "{key}" FROM "{target}" LIMIT 1').fetchone()
            if found is None:
                raise StepFailure(f'"{table_name}.{col.name}" references "{target}", which has no rows: '
                                  f'add a test:given for {target} first, or give {col.name}="…"')
            return found[0]
        n = self.world.next_generated()
        kind = col.type.upper()
        if 'INT' in kind:
            return n
        if any(t in kind for t in ('REAL', 'FLOA', 'DOUB', 'NUM', 'DEC')):
            return float(n)
        return f'{col.name} {n}'

    def _as(self, step: TestStepNode) -> None:
        from quantum.runtime.auth_service import AuthService
        attrs = dict(step.attrs)
        user = attrs.pop('user', None)
        role = attrs.pop('role', None)
        user_id = attrs.pop('id', None)
        with self.world.client.session_transaction() as sess:
            data = dict(sess.get('quantum_session') or {})
            if user is not None or role is not None or user_id is not None:
                AuthService.login(data, user_id=_number_or_text(user_id if user_id is not None else user),
                                  user_name=user if user is not None else str(user_id or ''),
                                  user_role=role or 'user')
            for key, value in attrs.items():
                data[key] = value
            sess['quantum_session'] = data

    def _visit(self, step: TestStepNode) -> None:
        attrs = dict(step.attrs)
        path = attrs.pop('path', None) or self.test.page
        url = path + (('&' if '?' in path else '?') + urlencode(attrs) if attrs else '')
        self.last = self._request('GET', url)

    def _submit(self, step: TestStepNode) -> None:
        attrs = dict(step.attrs)
        data = {'action': attrs.pop('action'), **attrs}
        self.last = self._request('POST', self.current, data)
        # A page with one q:action runs it whatever name was posted (ACT-1): a
        # test that names another action would pass while testing the wrong one.
        ran = (self.last['record'] or {}).get('action')
        if ran and ran.split(' ')[0] != data['action']:          # the cell edit notes "__edit table.column"
            raise StepFailure(f'the page ran q:action "{ran}", not "{data["action"]}": '
                              f'there is no action by that name on {self.last["url"]}')

    def _expect(self, step: TestStepNode) -> None:
        a = step.attrs
        if any(k in a for k in ('redirect', 'flash', 'status', 'text', 'no-text', 'error', 'var', 'queries')) \
                and self.last is None:
            raise StepFailure('nothing was requested yet: add a <test:visit/> or a <test:submit/> before this')
        last = self.last
        if 'status' in a and last['status'] != int(a['status']):
            raise StepFailure(f'expected status {a["status"]}, got {last["status"]}'
                              + _error_detail(last['record']), _where(last['record']))
        if 'redirect' in a:
            location = _local_url(last['location'], keep_fragment=True) if last['location'] else None
            if location != a['redirect']:
                raise StepFailure(f'expected a redirect to {a["redirect"]}, '
                                  + (f'got {location}' if location else f'got status {last["status"]} and no redirect')
                                  + _error_detail(last['record']), _where(last['record']))
        if 'flash' in a:
            flash = (last['flash'] or {}).get('message') if isinstance(last['flash'], dict) else None
            if flash is None:
                flash = _page_var(last['page_record'], 'flash') or None
            if flash != a['flash']:
                raise StepFailure(f'expected flash "{a["flash"]}", got '
                                  + (f'"{flash}"' if flash else 'no flash') + _error_detail(last['record']),
                                  _where(last['record']))
        if 'text' in a or 'no-text' in a:
            page = page_text(last['page_html'])
            if 'text' in a and _norm(a['text']) not in page:
                raise StepFailure(f'expected the page ({self.current}) to show "{a["text"]}"; '
                                  f'it shows: {_clip(page)}')
            if 'no-text' in a and _norm(a['no-text']) in page:
                raise StepFailure(f'expected the page ({self.current}) not to show "{a["no-text"]}"')
        if 'error' in a:
            self._expect_error(a)
        if 'var' in a:
            self._expect_var(a)
        if 'queries' in a:
            record = last['record'] or {}
            count = len(record.get('queries') or [])
            at_most, limit = QUERIES.match(a['queries']).groups()
            limit = int(limit)
            if (count > limit) if at_most else (count != limit):
                sqls = '; '.join(q['sql'][:80] for q in record.get('queries') or [])
                raise StepFailure(f'expected {a["queries"]} queries in {last["method"]} {last["url"]}, '
                                  f'it ran {count}: {sqls}')
        if 'table' in a:
            self._expect_table(a)
        if 'history' in a:
            self._expect_history(a)

    def _expect_error(self, a: Dict[str, str]) -> None:
        state = self.last['form_state'] or {}
        errors = state.get('errors') or {}
        field_name = a['error']
        if field_name not in errors:
            if errors:
                shown = ', '.join(f'{k}: {v}' for k, v in errors.items())
                raise StepFailure(f'expected an error on field "{field_name}"; the errors are on: {shown}')
            raise StepFailure(f'expected an error on field "{field_name}"; the submit was accepted'
                              + (f' (status {self.last["status"]})'))
        if 'message' in a and errors[field_name] != a['message']:
            raise StepFailure(f'expected the error on "{field_name}" to be "{a["message"]}", '
                              f'got "{errors[field_name]}"')

    def _expect_var(self, a: Dict[str, str]) -> None:
        name = a['var']
        for record in (self.last['page_record'], self.last['record']):
            for scope in ('page', 'action'):
                variables = ((record or {}).get('scopes') or {}).get(scope) or {}
                if name in variables:
                    if variables[name] != a['value']:
                        raise StepFailure(f'expected {name} = "{a["value"]}", got "{variables[name]}"')
                    return
        raise StepFailure(f'no variable "{name}" in the page or the action of the last request')

    def _expect_table(self, a: Dict[str, str]) -> None:
        name, path = self.world.datasource(a.get('datasource'), self.step)
        sql = f'SELECT COUNT(*) FROM "{a["table"]}"' + (f' WHERE {a["where"]}' if a.get('where') else '')
        count = self._count(path, sql)
        self._check_count(count, a, f'rows in "{a["table"]}"' + (f' where {a["where"]}' if a.get('where') else ''))

    def _expect_history(self, a: Dict[str, str]) -> None:
        name, path = self.world.datasource(a.get('datasource'), self.step)
        table = a['history']
        if name not in self.world.history_datasources:
            raise StepFailure(f'datasource "{name}" does not record history: add history: true to it (DB-11)')
        conditions, params = ['table_name = ?'], [table]
        for attr, column in (('action', 'action'), ('op', 'op'), ('user', 'user')):
            if attr in a:
                conditions.append(f'{column} = ?')
                params.append(a[attr])
        if a.get('where'):
            conn = self.world.connect(path)
            try:
                from quantum.runtime.history import _primary_key
                key = _primary_key(conn, table) or 'rowid'
                keys = [str(r[0]) for r in conn.execute(f'SELECT "{key}" FROM "{table}" WHERE {a["where"]}')]
            except sqlite3.Error as exc:
                raise StepFailure(f'history where="{a["where"]}": {exc}') from None
            finally:
                conn.close()
            conditions.append('row_key IN (%s)' % ', '.join('?' for _ in keys) if keys else '0')
            params.extend(keys)
        sql = 'SELECT COUNT(*) FROM quantum_history WHERE ' + ' AND '.join(conditions)
        conn = self.world.connect(path)
        try:
            recorded = conn.execute("SELECT 1 FROM sqlite_master WHERE name = 'quantum_history'").fetchone()
        finally:
            conn.close()
        count = self._count(path, sql, params) if recorded else 0     # nothing written yet
        what = ', '.join(f'{k}={a[k]}' for k in ('action', 'op', 'user', 'where') if k in a)
        self._check_count(count, a, f'history entries of "{table}"' + (f' ({what})' if what else ''))

    def _count(self, path: Path, sql: str, params=()) -> int:
        conn = self.world.connect(path)
        try:
            return conn.execute(sql, list(params)).fetchone()[0]
        except sqlite3.Error as exc:
            raise StepFailure(f'{exc} in: {sql}') from None
        finally:
            conn.close()

    @staticmethod
    def _check_count(count: int, a: Dict[str, str], what: str) -> None:
        if 'count' in a:
            if count != int(a['count']):
                raise StepFailure(f'expected {a["count"]} {what}, found {count}')
        elif count == 0:
            raise StepFailure(f'expected {what}, found none')


# -- helpers ------------------------------------------------------------------

def _local_url(location: str, keep_fragment: bool = False) -> str:
    parts = urlsplit(location)
    url = parts.path or '/'
    if parts.query:
        url += '?' + parts.query
    if keep_fragment and parts.fragment:
        url += '#' + parts.fragment
    return url


def _where(record) -> Optional[Tuple[str, int]]:
    where = (record or {}).get('where')
    return tuple(where) if where else None


def _error_detail(record) -> str:
    error = (record or {}).get('error')
    return f' — the request failed: {error}' if error else ''


def _page_var(record, name: str) -> Optional[str]:
    return (((record or {}).get('scopes') or {}).get('page') or {}).get(name)


def _number_or_text(value):
    return int(value) if isinstance(value, str) and value.isdigit() else value


def _checked_value(conn, table_name: str, col, value: str) -> Any:
    """A given value, checked against the column (TEST-2)."""
    if col.options and value not in col.options:
        raise StepFailure(f'"{table_name}.{col.name}" does not accept "{value}": '
                          f'it is one of {", ".join(col.options)}')
    kind = col.type.upper()
    if 'INT' in kind:
        if not re.fullmatch(r'-?\d+', value.strip()):
            raise StepFailure(f'"{table_name}.{col.name}" is {col.type}: "{value}" is not an integer')
        value = int(value)
    elif any(t in kind for t in ('REAL', 'FLOA', 'DOUB', 'NUM', 'DEC')):
        try:
            value = float(value)
        except ValueError:
            raise StepFailure(f'"{table_name}.{col.name}" is {col.type}: "{value}" is not a number') from None
    if col.references:
        target, key = col.references
        if conn.execute(f'SELECT 1 FROM "{target}" WHERE "{key}" = ?', (value,)).fetchone() is None:
            raise StepFailure(f'"{table_name}.{col.name}" = {value} references {target}.{key}, '
                              f'and there is no such row')
    return value


def _norm(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def page_text(html: str) -> str:
    """The text a person sees on the page: no tags, scripts or styles; spaces collapsed."""
    html = re.sub(r'<(style|script)\b.*?</\1>', '', html or '', flags=re.S | re.I)
    return _norm(unescape(re.sub(r'<[^>]+>', ' ', html)))


def _clip(text: str, size: int = 300) -> str:
    return text if len(text) <= size else text[:size] + '…'


# -- the command ----------------------------------------------------------------

def run_file(path: Path, report: RunReport) -> None:
    try:
        suite: TestFileNode = parse_test_source(path.read_text(encoding='utf-8'), _shown(path))
    except TestParseError as exc:
        report.errors.append(str(exc))
        return
    root = app_root_of(path)
    if root is None:
        report.errors.append(f'{path}: no quantum.config.yaml in its folder or above it — '
                             f'a test file belongs to an app')
        return
    for test in suite.tests:
        report.results.append(run_test(test, path, root))


def run_test(test: TestCaseNode, path: Path, root: Path) -> TestResult:
    start = time.perf_counter()
    result = TestResult(file=str(path), name=test.name, line=test.line, passed=True)
    run = None
    world = None
    try:
        world = TestWorld(root)
        run = TestRun(test, world)
        run.run()
    except StepFailure as exc:
        result.passed = False
        result.message = str(exc)
        result.where = exc.where
        result.step = getattr(run, 'step', None) if run else None
    except Exception as exc:                                   # noqa: BLE001 — reported, never swallowed
        result.passed = False
        result.message = f'{type(exc).__name__}: {exc}'
        result.step = getattr(run, 'step', None) if run else None
    finally:
        if world is not None:
            world.close()
    result.ms = (time.perf_counter() - start) * 1000
    return result


def _shown(path: str) -> str:
    """Relative to the current folder when the file is inside it; absolute otherwise."""
    try:
        rel = os.path.relpath(path)
    except ValueError:                                         # another drive (Windows)
        return str(path)
    return str(path) if rel.startswith('..') else rel


def format_report(report: RunReport) -> str:
    lines: List[str] = []
    by_file: Dict[str, List[TestResult]] = {}
    for r in report.results:
        by_file.setdefault(r.file, []).append(r)
    for file, results in by_file.items():
        lines.append(_shown(file))
        for r in results:
            lines.append(f'  {"PASS" if r.passed else "FAIL"}  {r.name}  ({r.ms:.0f} ms)')
            if not r.passed:
                line = r.step.line if r.step else r.line
                lines.append(f'        {_shown(file)}:{line or "?"}'
                             + (f'  {r.step.source()}' if r.step else ''))
                lines.append(f'        {r.message}')
                if r.where:
                    lines.append(f'        page: {_shown(r.where[0])}:{r.where[1]}')
    for error in report.errors:
        lines.append(f'ERROR  {error}')
    passed = sum(1 for r in report.results if r.passed)
    failed = len(report.failed)
    summary = f'{passed} passed, {failed} failed'
    if report.errors:
        summary += f', {len(report.errors)} file error(s)'
    lines.append(summary)
    return '\n'.join(lines)


def run_tests(paths: List[str], out=print) -> int:
    """`quantum test [path…]`: 0 when every test passed, 1 otherwise (TEST-1)."""
    import logging
    files, problems = find_test_files(paths)
    report = RunReport(errors=list(problems))
    if not files and not problems:
        out(f'no *.test.q files under {", ".join(paths or ["."])}')
        return 1
    previous = logging.root.manager.disable
    logging.disable(logging.CRITICAL)            # the report says what failed; the server's log is noise here
    try:
        for path in files:
            run_file(path, report)
    finally:
        logging.disable(previous)
    out(format_report(report))
    return 0 if report.ok else 1
