"""
Query Parser - Parse q:query statements

Handles SQL queries with parameter binding.
"""

import re
from typing import List
from xml.etree import ElementTree as ET
from quantum.core.parsers.base import BaseTagParser, ParserError
from quantum.core.ast_nodes import QueryNode, QueryParamNode


_NEVER_IMPLEMENTED = ('cache', 'ttl', 'reactive', 'interval', 'timeout', 'maxrows', 'batch')


class QueryParser(BaseTagParser):
    """
    Parser for q:query statements.

    Supports:
    - SQL queries with parameter binding
    - Query of Queries (source attribute)
    - Caching and pagination
    - RAG/knowledge base queries
    """

    @property
    def tag_names(self) -> List[str]:
        return ['query']

    def parse(self, element: ET.Element) -> QueryNode:
        """
        Parse q:query statement.

        Args:
            element: XML element for q:query

        Returns:
            QueryNode AST node
        """
        name = self.get_attr(element, 'name')
        datasource = self.get_attr(element, 'datasource')
        source = self.get_attr(element, 'source')

        # A write query (UPDATE/INSERT/DELETE) has no result set to bind, so
        # name is optional — requiring it rejected the ordinary CFML-style
        # idiom used across the job examples. Reads still want a name; without
        # one there is simply nothing to reference the rows by.
        if not name:
            name = ''
        if not datasource and not source:
            raise ParserError("Query requires either 'datasource' or 'source' attribute")

        # DB-5: attributes that were read into the AST and never used. The
        # guide sold cache="true" ttl="3600" and reactive="true" as features.
        for attr in _NEVER_IMPLEMENTED:
            if element.get(attr) is not None:
                raise ParserError(
                    f'<q:query name="{name}"> {attr}= is not supported: it was accepted '
                    f'and never did anything, and was removed in Quantum 0.11')

        # Extract SQL content
        sql_parts = []
        if element.text:
            sql_parts.append(element.text.strip())

        for child in element:
            if child.tail:
                sql_parts.append(child.tail.strip())

        sql = '\n'.join(part for part in sql_parts if part)

        # Create query node
        query_node = QueryNode(name, datasource or '', sql)

        # Parse attributes
        query_node.source = source
        query_node.paginate = self.get_bool_attr(element, 'paginate', False)
        # UI-13: ordered by the URL's ?sort=/&dir= (a <ui:table sort="true"> writes them)
        query_node.sortable = self.get_bool_attr(element, 'sortable', False)
        # DB-9: page= is an expression, resolved when the query runs; it was
        # read as an int at parse time, so page="{query.page}" was always
        # page 1. With paginate="true" and no page=, the page is the URL's
        # `page` parameter — the one <ui:pager> writes.
        page_attr = element.get('page')
        query_node.page = None
        query_node.page_expr = None
        if page_attr is not None:
            if '{' in page_attr:
                query_node.page_expr = page_attr
            elif page_attr.strip().isdigit():
                query_node.page = int(page_attr)
            else:
                from quantum.core.parser import QuantumParseError
                raise QuantumParseError(
                    f'<q:query name="{name}" page="{page_attr}">: a page number or an expression, '
                    f'e.g. page="{{query.page}}"')
        elif query_node.paginate:
            query_node.page_expr = '{query.page}'
        # Accept both spellings: the codebase convention is camelCase, but
        # snake_case reads naturally in XML and the examples used it —
        # the mismatch made page_size None and crashed pagination with
        # 'unsupported operand type(s) for +: int and NoneType'.
        query_node.page_size = (
            self.get_int_attr(element, 'pageSize', 0)
            or self.get_int_attr(element, 'page_size', 0)
            or None
        )
        query_node.result = self.get_attr(element, 'result')
        # IA-5 / DB: onerror="continue" hands a failure to the page as <name>_result.
        query_node.on_error = self.get_attr(element, 'onerror', 'fail')
        if query_node.on_error not in ('fail', 'continue'):
            from quantum.core.parser import QuantumParseError
            raise QuantumParseError(f'<q:query name="{name}"> onerror must be "fail" or "continue", '
                                    f'not "{query_node.on_error}"')

        # IA-3: mode="rag" answered from a knowledge base with no citations and
        # no `found` — a weaker copy of q:llm knowledge= (IA-6), so it left.
        if self.get_attr(element, 'mode') == 'rag':
            from quantum.core.parser import QuantumParseError
            base = (datasource or '').replace('knowledge:', '', 1) or 'base'
            raise QuantumParseError(
                f'<q:query name="{name}" mode="rag">: mode="rag" was removed — answer from a '
                f'knowledge base with <q:llm name="{name}" knowledge="{base}">, which cites its '
                f'sources (a q:query on knowledge:{base} still searches the chunks)')

        # Parse q:param children
        for child in element:
            child_type = self.get_element_name(child)
            if child_type == 'param':
                param_node = self._parse_query_param(child)
                query_node.add_param(param_node)

        # Validate: reject direct {var} interpolation (SQL injection risk)
        if sql and re.search(r'\{[a-zA-Z_]\w*\}', sql):
            raise ParserError(
                f"Query '{name}': direct {{var}} interpolation in SQL is not allowed. "
                "Use :param_name with <q:param> for safe parameter binding"
            )

        # Validate: all :param references must have matching <q:param>
        if sql:
            sql_params = self._named_params(sql)
            declared_params = {p.name for p in query_node.params}
            missing = sql_params - declared_params
            if missing:
                raise ParserError(
                    f"Query '{name}': SQL parameter(s) {', '.join(':' + p for p in sorted(missing))} "
                    "declared in SQL but no matching <q:param> element provided"
                )

        return query_node

    @staticmethod
    def _named_params(sql: str) -> set:
        """The `:name`s that are REALLY bind parameters.

        This was `re.findall(r':([a-zA-Z_]\\w*)', sql)` over the raw SQL, and it
        also scanned what is inside quotes and comments:

            TO_CHAR(c.created_at, 'YYYY-MM-DD HH24:MI')   -> found `:MI`
            SELECT x::text FROM t                        -> found `:text`

        Both forms are correct, common SQL — the first appears in
        projects/blog/components/post.q, which did not parse because of this:
        the file was refused with "SQL parameter(s) :MI declared in SQL but
        no matching <q:param>", and there was no parameter at all to declare.

        The scan skips text literals (with '' and "" escaped), PostgreSQL's
        `::` cast, and `--` line and block comments.
        """
        found = set()
        i, n = 0, len(sql)
        while i < n:
            c = sql[i]
            if c in ("'", '"'):
                quote = c
                i += 1
                while i < n:
                    if sql[i] == quote:
                        if i + 1 < n and sql[i + 1] == quote:
                            i += 2      # '' escapado dentro do literal
                            continue
                        i += 1
                        break
                    i += 1
                continue
            if sql.startswith('--', i):
                end = sql.find('\n', i)
                i = n if end == -1 else end + 1
                continue
            if sql.startswith('/*', i):
                end = sql.find('*/', i)
                i = n if end == -1 else end + 2
                continue
            if c == ':':
                if sql.startswith('::', i):
                    i += 2              # a PostgreSQL cast, not a parameter
                    continue
                m = re.match(r':([a-zA-Z_]\w*)', sql[i:])
                if m:
                    found.add(m.group(1))
                    i += m.end()
                    continue
            i += 1
        return found

    def _parse_query_param(self, element: ET.Element) -> QueryParamNode:
        """Parse q:param within q:query."""
        name = self.get_attr(element, 'name')
        value = self.get_attr(element, 'value')
        param_type = self.get_attr(element, 'type', 'string')

        if not name:
            raise ParserError("Query parameter requires 'name' attribute")
        if value is None:
            raise ParserError(f"Query parameter '{name}' requires 'value' attribute")

        from quantum.runtime.param_validation import QUERY_PARAM_TYPES, check_param_type
        check_param_type(f'<q:query> <q:param name="{name}">', param_type, QUERY_PARAM_TYPES, exact=True, element=element)
        param_node = QueryParamNode(name, value, param_type)
        param_node.null = self.get_bool_attr(element, 'null', False)
        param_node.max_length = self.get_int_attr(element, 'maxLength', 0) or None
        param_node.scale = self.get_int_attr(element, 'scale', 0) or None

        return param_node
