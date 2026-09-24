"""`quantum check`: every page parses, every q:query compiles against the database,
and every `{query.field}` a page reads is a column the query returns (M8, DEV-3).

A typo in SQL or in a field name used to surface only when someone opened the
page — `no such column` as a 500, or, for a field, an empty cell. This reads
the project the way the server would and reports each problem with its file
and line, without running anything: a query is compiled by the database
(EXPLAIN) and a SELECT's columns come from running it with LIMIT 0.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional

# Fields of `<name>_result` and of a query row that are not columns.
_META = {'recordCount', 'columnList', 'executionTime', 'success', 'error', 'sql', 'page',
         'totalPages', 'hasMore', 'cached', 'affectedRows', 'lastInsertId', 'data', 'length'}
_EXPR = re.compile(r'\{([^{}]*)\}')


@dataclass
class Problem:
    file: str
    line: Optional[int]
    message: str

    def __str__(self) -> str:
        return f'{self.file}:{self.line or "?"}: {self.message}'


def _config(config_path: Path) -> dict:
    import yaml
    from quantum.core.config_env import expand_env
    if not config_path.exists():
        return {}
    return expand_env(yaml.safe_load(config_path.read_text(encoding='utf-8')) or {})


def _children(node) -> Iterator:
    """The nodes inside a node, whatever the field is called."""
    for field in ('statements', 'body', 'if_body', 'else_body', 'children', 'tools'):
        for child in getattr(node, field, None) or []:
            if hasattr(child, '__dict__'):
                yield child
    for block in getattr(node, 'elseif_blocks', None) or []:
        body = block.get('body') if isinstance(block, dict) else getattr(block, 'body', None)
        for child in body or []:
            yield child


def _texts(node) -> List[str]:
    """The strings of a node that may hold {expressions}."""
    texts = []
    for field, value in vars(node).items():
        if field.startswith('_') or field in ('sql',):
            continue
        if isinstance(value, str) and '{' in value:
            texts.append(value)
        elif isinstance(value, dict):
            texts += [v for v in value.values() if isinstance(v, str) and '{' in v]
    return texts


class ProjectChecker:
    def __init__(self, project: Path, config_path: Path):
        self.project = project
        self.config = _config(config_path)
        self.datasources = self.config.get('datasources') or {}
        self._connections: Dict[str, object] = {}
        self.problems: List[Problem] = []
        self.notes: List[str] = []
        self.queries_checked = 0
        self.files = 0

    # -- the database ---------------------------------------------------------

    def _connection(self, name: str):
        from quantum.runtime.db_schema import SchemaError, connect_readonly
        if name not in self._connections:
            try:
                self._connections[name] = connect_readonly(self.datasources[name], self.project)
            except SchemaError as exc:
                self._connections[name] = None
                self.notes.append(f'datasource {name!r} not checked: {exc}')
        return self._connections[name]

    # -- a file ---------------------------------------------------------------

    def check_file(self, path: Path) -> None:
        from quantum.core.parser import QuantumParser
        rel = path.relative_to(self.project).as_posix() if path.is_relative_to(self.project) else str(path)
        self.files += 1
        try:
            ast = QuantumParser(use_cache=False).parse_file(str(path))
        except Exception as exc:        # a parse error is a problem like any other
            first_line = str(exc).split('\n')[0]
            self.problems.append(Problem(rel, getattr(exc, 'line', None), first_line))
            return
        columns: Dict[str, List[str]] = {}
        self._queries(ast, rel, columns)
        self._fields(ast, rel, columns, {name: name for name in columns}, None)

    def check_test_file(self, path: Path) -> None:
        """A *.test.q next to the pages: it parses as a test suite (TEST-4), not as a page."""
        from quantum.core.features.native_testing.src import TestParseError, parse_test_file
        rel = path.relative_to(self.project).as_posix() if path.is_relative_to(self.project) else str(path)
        self.files += 1
        try:
            parse_test_file(path)
        except TestParseError as exc:
            self.problems.append(Problem(rel, exc.line, str(exc).split('\n')[0]))

    def _queries(self, node, rel: str, columns: Dict[str, List[str]]) -> None:
        from quantum.core.ast_nodes import ActionNode, QueryNode
        from quantum.runtime.db_schema import check_sql, read_schema
        for child in _children(node):
            if isinstance(child, ActionNode) and getattr(child, 'table', None):
                # UI-10: the table the action takes its params from exists, with those columns.
                ds = child.table_datasource
                if ds not in self.datasources:
                    self.problems.append(Problem(rel, getattr(child, 'source_line', None),
                                                 f'<q:action name="{child.name}">: datasource {ds!r} is not '
                                                 f'declared in quantum.config.yaml'))
                elif self._connection(ds) is not None:
                    schema = read_schema(self._connection(ds))
                    table = schema.get(child.table)
                    if table is None:
                        self.problems.append(Problem(rel, getattr(child, 'source_line', None),
                                                     f'<q:action name="{child.name}" table="{child.table}">: '
                                                     f'no such table (tables: {", ".join(schema) or "none"})'))
                    else:
                        for column in child.table_columns or []:
                            if column not in table.columns:
                                self.problems.append(Problem(
                                    rel, getattr(child, 'source_line', None),
                                    f'<q:action name="{child.name}" columns=...>: table "{child.table}" '
                                    f'has no column "{column}"'))
            if isinstance(child, QueryNode):
                ds = child.datasource
                if not ds or ds.startswith('knowledge:') or getattr(child, 'source', None):
                    pass                                 # RAG or query of queries: not SQL on a database
                elif ds not in self.datasources:
                    self.problems.append(Problem(rel, getattr(child, 'source_line', None),
                                                 f'<q:query name="{child.name}">: datasource {ds!r} is not '
                                                 f'declared in quantum.config.yaml'))
                else:
                    conn = self._connection(ds)
                    if conn is not None:
                        self.queries_checked += 1
                        error, cols = check_sql(conn, child.sql or '')
                        if error:
                            self.problems.append(Problem(rel, getattr(child, 'source_line', None),
                                                         f'<q:query name="{child.name}">: {error}'))
                        elif cols is not None:
                            columns[child.name] = cols
            self._queries(child, rel, columns)

    def _fields(self, node, rel: str, columns: Dict[str, List[str]], bound: Dict[str, str],
                line: Optional[int]) -> None:
        """Each `{var.field}` where var is a query, or a row of one, names a column it returns."""
        from quantum.core.features.loops.src.ast_node import LoopNode
        from quantum.core.features.ui_engine.src.ast_nodes import UIColumnNode, UIListNode, UITableNode
        line = getattr(node, 'source_line', None) or line
        for text in _texts(node):
            for expr in _EXPR.findall(text):
                for var, field in re.findall(r'(?<![\w.])(\w+)\.(\w+)', expr):
                    self._field(rel, line, columns, bound, var, field)
        if isinstance(node, UIColumnNode) and node.key and '$table' in bound:
            self._field(rel, line, columns, bound, '$table', node.key, f'<ui:column key="{node.key}">')

        for child in _children(node):
            inner = dict(bound)
            source = None
            if isinstance(child, LoopNode):
                source = child.query_name if child.loop_type == 'query' else _single_name(child.items)
                if source in columns:
                    inner[child.var_name] = source
            elif isinstance(child, (UITableNode, UIListNode)):
                source = _single_name(child.source)
                if source in columns:
                    inner[child.as_var or ('row' if isinstance(child, UITableNode) else 'item')] = source
                    if isinstance(child, UITableNode):
                        inner['$table'] = source
            self._fields(child, rel, columns, inner, line)

    def _field(self, rel, line, columns, bound, var, field, label=None) -> None:
        query = bound.get(var)
        if query is None or field in _META:
            return
        cols = columns.get(query, [])
        if field not in cols:
            shown = label or f'{{{var}.{field}}}'
            self.problems.append(Problem(
                rel, line, f'{shown}: query "{query}" returns no column "{field}" '
                            f'(columns: {", ".join(cols) or "none"})'))

    # -- the project ----------------------------------------------------------

    def run(self) -> List[Problem]:
        folder = self.project / (self.config.get('paths', {}) or {}).get('components', 'components')
        if not folder.exists():
            self.notes.append(f'no components folder at {folder}')
            return self.problems
        for path in sorted(folder.rglob('*.q')):
            if path.name.endswith('.test.q'):
                self.check_test_file(path)       # a test suite next to its page (TEST-1)
                continue
            self.check_file(path)
        for conn in self._connections.values():
            if conn is not None:
                conn.close()
        return self.problems


def _single_name(expr: Optional[str]) -> Optional[str]:
    """`{tasks}` -> 'tasks'; anything more complex -> None."""
    m = re.fullmatch(r'\s*\{\s*(\w+)\s*\}\s*', expr or '')
    return m.group(1) if m else None


def run_check(config_path: str = 'quantum.config.yaml') -> int:
    """`quantum check`: print each problem as file:line: message; exit 1 if there is any."""
    path = Path(config_path).resolve()
    checker = ProjectChecker(path.parent, path)
    problems = checker.run()
    for note in checker.notes:
        print(f'[NOTE] {note}')
    for problem in problems:
        print(problem)
    summary = (f'{checker.files} file(s), {checker.queries_checked} query(ies) checked against the database')
    if problems:
        print(f'\n{len(problems)} problem(s) — {summary}.')
        return 1
    print(f'OK — {summary}.')
    return 0
