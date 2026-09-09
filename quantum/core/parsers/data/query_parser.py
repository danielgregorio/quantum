"""
Query Parser - Parse q:query statements

Handles SQL queries with parameter binding and RAG mode.
"""

import re
from typing import List
from xml.etree import ElementTree as ET
from quantum.core.parsers.base import BaseTagParser, ParserError
from quantum.core.ast_nodes import QueryNode, QueryParamNode


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
        query_node.cache = self.get_bool_attr(element, 'cache', False)
        query_node.ttl = self.get_int_attr(element, 'ttl', 0) or None
        query_node.reactive = self.get_bool_attr(element, 'reactive', False)
        query_node.interval = self.get_int_attr(element, 'interval', 0) or None
        query_node.paginate = self.get_bool_attr(element, 'paginate', False)
        query_node.page = self.get_int_attr(element, 'page', 0) or None
        # Accept both spellings: the codebase convention is camelCase, but
        # snake_case reads naturally in XML and the examples used it —
        # the mismatch made page_size None and crashed pagination with
        # 'unsupported operand type(s) for +: int and NoneType'.
        query_node.page_size = (
            self.get_int_attr(element, 'pageSize', 0)
            or self.get_int_attr(element, 'page_size', 0)
            or None
        )
        query_node.timeout = self.get_int_attr(element, 'timeout', 0) or None
        query_node.maxrows = self.get_int_attr(element, 'maxrows', 0) or None
        query_node.result = self.get_attr(element, 'result')

        # RAG/Knowledge attributes
        query_node.mode = self.get_attr(element, 'mode')
        query_node.rag_model = self.get_attr(element, 'model')

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
        """Os `:nome` que sao REALMENTE parametros de bind.

        Isto era `re.findall(r':([a-zA-Z_]\\w*)', sql)` sobre o SQL cru, e
        varria tambem o que esta dentro de aspas e de comentarios:

            TO_CHAR(c.created_at, 'YYYY-MM-DD HH24:MI')   -> achava `:MI`
            SELECT x::text FROM t                        -> achava `:text`

        As duas formas sao SQL correto e comum — a primeira aparece em
        projects/blog/components/post.q, que por causa disto nao parseava:
        o arquivo era recusado com "SQL parameter(s) :MI declared in SQL but
        no matching <q:param>", e nao havia parametro nenhum para declarar.

        A varredura pula literais de texto (com '' e "" escapados), o cast
        `::` do PostgreSQL, comentarios de linha `--` e de bloco.
        """
        encontrados = set()
        i, n = 0, len(sql)
        while i < n:
            c = sql[i]
            if c in ("'", '"'):
                aspas = c
                i += 1
                while i < n:
                    if sql[i] == aspas:
                        if i + 1 < n and sql[i + 1] == aspas:
                            i += 2      # '' escapado dentro do literal
                            continue
                        i += 1
                        break
                    i += 1
                continue
            if sql.startswith('--', i):
                fim = sql.find('\n', i)
                i = n if fim == -1 else fim + 1
                continue
            if sql.startswith('/*', i):
                fim = sql.find('*/', i)
                i = n if fim == -1 else fim + 2
                continue
            if c == ':':
                if sql.startswith('::', i):
                    i += 2              # cast do PostgreSQL, nao parametro
                    continue
                m = re.match(r':([a-zA-Z_]\w*)', sql[i:])
                if m:
                    encontrados.add(m.group(1))
                    i += m.end()
                    continue
            i += 1
        return encontrados

    def _parse_query_param(self, element: ET.Element) -> QueryParamNode:
        """Parse q:param within q:query."""
        name = self.get_attr(element, 'name')
        value = self.get_attr(element, 'value')
        param_type = self.get_attr(element, 'type', 'string')

        if not name:
            raise ParserError("Query parameter requires 'name' attribute")
        if value is None:
            raise ParserError(f"Query parameter '{name}' requires 'value' attribute")

        param_node = QueryParamNode(name, value, param_type)
        param_node.null = self.get_bool_attr(element, 'null', False)
        param_node.max_length = self.get_int_attr(element, 'maxLength', 0) or None
        param_node.scale = self.get_int_attr(element, 'scale', 0) or None

        return param_node
